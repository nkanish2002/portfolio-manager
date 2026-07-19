"""Trade execution + FIFO realized P&L.

Maintains per-asset lot queues and computes realized gain on sells using
FIFO cost-basis matching. Pure data — no DB access — so it can be unit-tested
in isolation and reused by the transactions route + NAV-history builder.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Lot:
    """An open (unconsumed) purchase lot."""

    quantity: Decimal
    price: Decimal  # cost per share, excluding fees


@dataclass
class SellResult:
    """Outcome of matching a sell against the FIFO lot queue."""

    realized_gain: Decimal
    cost_basis: Decimal  # cost of the shares sold
    proceeds: Decimal  # value of shares sold (excl. fees)
    remaining_quantity: Decimal  # shares left to sell (no lots available)
    lots_consumed: int


@dataclass
class TradeLedger:
    """Per-asset FIFO lot queues.

    Buys append lots; sells consume from the front. Splits/merges adjust the
    queue. Fees are treated as part of the trade cost/proceeds (not the lot
    price) to keep per-share cost clean.
    """

    lots: dict[str, deque[Lot]] = field(default_factory=dict)

    def _queue(self, asset: str) -> deque[Lot]:
        return self.lots.setdefault(asset, deque())

    def buy(self, asset: str, quantity: Decimal, price: Decimal, fees: Decimal = Decimal("0")) -> None:
        """Append a lot. Per-share cost is the trade price; fees tracked separately."""
        if quantity <= 0:
            return
        self._queue(asset).append(Lot(quantity=Decimal(quantity), price=Decimal(price)))
        # fees are not amortized into lot price (kept out of cost basis to match
        # the Position model, which uses avg_cost_basis per share)

    def sell(
        self,
        asset: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal = Decimal("0"),
    ) -> SellResult:
        """Sell ``quantity`` shares at ``price`` (FIFO).

        If there aren't enough lots, the matched portion is realized and the
        unmatched remainder is returned in ``remaining_quantity`` (caller
        decides whether to reject short sells).
        """
        q = Decimal(quantity)
        if q <= 0:
            return SellResult(Decimal("0"), Decimal("0"), Decimal("0"), q, 0)

        queue = self._queue(asset)
        sell_price = Decimal(price)
        to_sell = q
        cost_basis = Decimal("0")
        proceeds = Decimal("0")
        consumed = 0

        while to_sell > 0 and queue:
            lot = queue[0]
            if lot.quantity <= to_sell:
                # consume whole lot
                cost_basis += lot.quantity * lot.price
                proceeds += lot.quantity * sell_price
                to_sell -= lot.quantity
                queue.popleft()
                consumed += 1
            else:
                # consume part of the lot
                cost_basis += to_sell * lot.price
                proceeds += to_sell * sell_price
                lot.quantity -= to_sell
                to_sell = Decimal("0")
                consumed += 1
                break

        realized = proceeds - cost_basis
        return SellResult(
            realized_gain=realized,
            cost_basis=cost_basis,
            proceeds=proceeds,
            remaining_quantity=to_sell,
            lots_consumed=consumed,
        )

    def split(self, asset: str, ratio: Decimal) -> None:
        """Apply a stock split (ratio > 1 forward, < 1 reverse) to open lots."""
        queue = self._queue(asset)
        if not queue:
            return
        for lot in queue:
            lot.quantity = lot.quantity * ratio
            lot.price = lot.price / ratio

    def position_quantity(self, asset: str) -> Decimal:
        """Total open quantity for an asset across all lots."""
        return sum((lot.quantity for lot in self._queue(asset)), Decimal("0"))

    def avg_cost_basis(self, asset: str) -> Decimal:
        """Volume-weighted average cost of open lots (0 if no position)."""
        queue = self._queue(asset)
        total_qty = Decimal("0")
        total_cost = Decimal("0")
        for lot in queue:
            total_qty += lot.quantity
            total_cost += lot.quantity * lot.price
        if total_qty == 0:
            return Decimal("0")
        return total_cost / total_qty


def build_ledger(transactions: Iterable) -> tuple[TradeLedger, list]:
    """Replay a sequence of transactions through a FIFO ledger.

    Each transaction is expected to expose ``asset_id`` (str), ``type``,
    ``quantity`` (Decimal), ``price`` (Decimal), ``fees`` (Decimal). Returns
    the ledger and a list of (txn_index, realized_gain) for sells.
    """
    ledger = TradeLedger()
    realized: list[tuple[int, Decimal]] = []
    for i, txn in enumerate(transactions):
        asset = str(getattr(txn, "asset_id", txn.get("asset_id") if isinstance(txn, dict) else ""))
        ttype = getattr(txn, "type", txn.get("type") if isinstance(txn, dict) else "")
        qty = Decimal(getattr(txn, "quantity", txn.get("quantity") if isinstance(txn, dict) else 0))
        price = Decimal(getattr(txn, "price", txn.get("price") if isinstance(txn, dict) else 0))
        fees = Decimal(getattr(txn, "fees", txn.get("fees") if isinstance(txn, dict) else 0) or 0)

        if ttype == "buy":
            ledger.buy(asset, qty, price, fees)
        elif ttype == "sell":
            result = ledger.sell(asset, qty, price, fees)
            realized.append((i, result.realized_gain))
        elif ttype == "split":
            ledger.split(asset, qty)  # qty used as the split ratio
    return ledger, realized


def fifo_realized_gain(buys: list[tuple[Decimal, Decimal]], sell: tuple[Decimal, Decimal]) -> Decimal:
    """Convenience: realized P&L for one sell against a list of prior buys.

    ``buys`` = [(qty, price), ...]; ``sell`` = (qty, price). FIFO matching.
    """
    ledger = TradeLedger()
    for q, p in buys:
        ledger.buy("X", Decimal(q), Decimal(p))
    res = ledger.sell("X", Decimal(sell[0]), Decimal(sell[1]))
    return res.realized_gain
