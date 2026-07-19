"""Portfolio calculation helpers — NAV, returns, allocation, P&L.

Pure functions over positions / transactions / NAV series. Financial inputs
come in as ``Decimal`` (matching the SQLModel columns); outputs are ``Decimal``
for monetary aggregates and ``float`` for ratios / return series so they're
JSON-friendly and analytics-ready.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

# ── position-level ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PositionValue:
    """Snapshot of a single position's value + P&L."""

    asset_id: str
    quantity: Decimal
    avg_cost_basis: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_gain: Decimal
    unrealized_gain_pct: float


def position_value(
    *,
    quantity: Decimal,
    avg_cost_basis: Decimal,
    current_price: Decimal,
    asset_id: str = "",
) -> PositionValue:
    """Compute market value + unrealized P&L for a single position."""
    qty = Decimal(quantity)
    cost = Decimal(avg_cost_basis)
    price = Decimal(current_price)
    market_value = qty * price
    cost_basis = qty * cost
    gain = market_value - cost_basis
    gain_pct = float(gain / cost_basis) if cost_basis != 0 else 0.0
    return PositionValue(
        asset_id=asset_id,
        quantity=qty,
        avg_cost_basis=cost,
        current_price=price,
        market_value=market_value,
        unrealized_gain=gain,
        unrealized_gain_pct=gain_pct,
    )


def compute_position_fields(
    *, quantity: Decimal, avg_cost_basis: Decimal, current_price: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (market_value, unrealized_gain, unrealized_gain_pct).

    Used by the routes/services when persisting a refreshed position back
    to the DB columns.
    """
    pv = position_value(
        quantity=quantity, avg_cost_basis=avg_cost_basis, current_price=current_price
    )
    return pv.market_value, pv.unrealized_gain, Decimal(str(round(pv.unrealized_gain_pct, 4)))


# ── portfolio-level ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class PortfolioSummary:
    """Aggregate snapshot of a portfolio."""

    nav: Decimal  # net asset value = sum of market values
    cost_basis: Decimal  # sum of qty * avg_cost
    unrealized_gain: Decimal
    unrealized_gain_pct: float
    position_count: int


def compute_nav(positions: Iterable[PositionValue]) -> Decimal:
    """NAV = Σ market_value across positions."""
    return sum((p.market_value for p in positions), Decimal("0"))


def compute_pnl(positions: Iterable[PositionValue]) -> tuple[Decimal, float]:
    """Total unrealized P&L (currency) and percentage."""
    total_cost = Decimal("0")
    total_gain = Decimal("0")
    for p in positions:
        total_cost += p.quantity * p.avg_cost_basis
        total_gain += p.unrealized_gain
    pct = float(total_gain / total_cost) if total_cost != 0 else 0.0
    return total_gain, pct


def summarize_portfolio(positions: Iterable[PositionValue]) -> PortfolioSummary:
    """Build a full portfolio summary from a list of position snapshots."""
    pos = list(positions)
    nav = compute_nav(pos)
    cost = sum((p.quantity * p.avg_cost_basis for p in pos), Decimal("0"))
    gain, pct = compute_pnl(pos)
    return PortfolioSummary(
        nav=nav,
        cost_basis=cost,
        unrealized_gain=gain,
        unrealized_gain_pct=pct,
        position_count=len(pos),
    )


# ── allocation ────────────────────────────────────────────────────────────


def compute_allocation(
    positions: Iterable[PositionValue],
    *,
    keys: Iterable[str],
) -> dict[str, float]:
    """Allocation by a key function — returns ``{key: percent_of_nav}``.

    ``keys`` is a parallel iterable of bucket labels (e.g. sector, asset_class,
    basket name) for each position. Positions with zero NAV contribute 0%.
    """
    pos = list(positions)
    key_list = list(keys)
    if len(pos) != len(key_list):
        raise ValueError("positions and keys must be the same length")
    nav = compute_nav(pos)
    buckets: dict[str, Decimal] = {}
    for p, k in zip(pos, key_list, strict=True):
        buckets[k] = buckets.get(k, Decimal("0")) + p.market_value
    if nav == 0:
        return {k: 0.0 for k in buckets}
    return {k: float(v / nav) for k, v in buckets.items()}


# ── returns from a NAV series ─────────────────────────────────────────────


def simple_returns(nav: Sequence[float]) -> list[float]:
    """Period-over-period simple returns from a NAV/price series.

    Returns ``len(nav) - 1`` values. An empty/length-1 series yields ``[]``.
    """
    arr = np.asarray([float(v) for v in nav], dtype=float)
    if arr.size < 2:
        return []
    prev = arr[:-1]
    # guard against zero/None previous values to avoid div-by-zero infinities
    prev_safe = np.where(prev == 0, np.nan, prev)
    rets = (arr[1:] - prev) / prev_safe
    return [float(r) if r == r else 0.0 for r in rets]  # NaN → 0.0


def cumulative_nav(returns: Sequence[float], start_value: float = 1.0) -> list[float]:
    """Compound a return series into a NAV series starting at ``start_value``."""
    arr = np.asarray([float(r) for r in returns], dtype=float)
    if arr.size == 0:
        return [float(start_value)]
    nav = np.concatenate(([float(start_value)], start_value * np.cumprod(1.0 + arr)))
    return [float(v) for v in nav]
