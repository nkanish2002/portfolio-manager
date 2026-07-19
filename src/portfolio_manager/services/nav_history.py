"""NAV history — reconstruct a daily NAV series from transactions.

Strategy: replay transactions chronologically to derive per-asset share
counts and cash, then mark-to-market at each timestamp using a price map.
The price provider is pluggable so tests can supply synthetic prices.

For Phase 2 this is a deterministic, transaction-driven builder. The live
price refresh (yfinance) is layered in by the analytics route.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass
class NavPoint:
    """A single point on the NAV curve."""

    date: date
    nav: float
    cash: float
    holdings_value: float


@dataclass
class _Holdings:
    shares: dict[str, Decimal] = field(default_factory=dict)
    cash: Decimal = Decimal("0")

    def apply(self, txn: dict) -> None:
        ttype = txn["type"]
        asset = str(txn["asset_id"])
        qty = Decimal(txn["quantity"])
        price = Decimal(txn["price"])
        fees = Decimal(txn.get("fees") or 0)

        if ttype == "buy":
            self.shares[asset] = self.shares.get(asset, Decimal("0")) + qty
            self.cash -= qty * price + fees
        elif ttype == "sell":
            self.shares[asset] = self.shares.get(asset, Decimal("0")) - qty
            self.cash += qty * price - fees
        elif ttype in ("deposit", "interest", "dividend"):
            # cash inflows; dividend credited as cash for the NAV-history model
            self.cash += qty * price + (Decimal("0") if ttype == "deposit" else qty * price)
        elif ttype in ("withdrawal", "fee"):
            self.cash -= qty * price + fees


PriceProvider = Callable[[str, date], Decimal | None]
"""Return a per-share price for an asset on a date, or None if unavailable."""


def build_nav_history(
    transactions: Sequence[dict],
    *,
    price_provider: PriceProvider,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[NavPoint]:
    """Build a NAV series by replaying transactions and marking to market.

    Transactions are dicts with keys: ``asset_id``, ``type``, ``quantity``,
    ``price``, ``fees``, ``trade_date`` (datetime). NAV at each event timestamp
    is ``cash + Σ shares * price(provider)``. Events where the price provider
    returns None for a held asset are skipped (treated as no-data days).
    """
    if not transactions:
        return []

    # sort chronologically by trade_date
    txns = sorted(transactions, key=lambda t: t["trade_date"])
    first_date = start_date or _as_date(txns[0]["trade_date"])
    last_date = end_date or _as_date(txns[-1]["trade_date"])

    holdings = _Holdings()
    points: list[NavPoint] = []

    # seed cash with the first deposit if present (common pattern)
    for txn in txns:
        d = _as_date(txn["trade_date"])
        if d < first_date:
            continue
        holdings.apply(txn)
        # mark to market at this date using the price provider
        hv = Decimal("0")
        complete = True
        for asset, shares in holdings.shares.items():
            if shares == 0:
                continue
            price = price_provider(asset, d)
            if price is None:
                complete = False
                break
            hv += shares * price
        if not complete:
            continue
        nav = holdings.cash + hv
        points.append(
            NavPoint(
                date=d,
                nav=float(nav),
                cash=float(holdings.cash),
                holdings_value=float(hv),
            )
        )
        if d >= last_date:
            break

    return points


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # try to parse
    return datetime.fromisoformat(str(value)).date()
