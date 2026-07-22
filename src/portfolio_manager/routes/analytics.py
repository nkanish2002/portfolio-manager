"""Analytics routes — risk metrics, allocation breakdowns, chart data.

Historical series are sourced from the data feed (yfinance). The ``data_feed``
singleton is referenced at module level so tests can patch it with a fake for
deterministic, network-free coverage.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Portfolio, Position
from portfolio_manager.models.user import User
from portfolio_manager.routes.portfolios import _get_owned as get_owned_portfolio
from portfolio_manager.services.benchmark import compare_to_benchmark
from portfolio_manager.services.classification import infer_region
from portfolio_manager.services.data_feed import data_feed
from portfolio_manager.services.portfolio_calc import (
    compute_nav,
    position_value,
    simple_returns,
)
from portfolio_manager.services.risk import compute_risk_metrics, max_drawdown

router = APIRouter(prefix="/api/v1/portfolios", tags=["analytics"])

DEFAULT_PERIOD = "1y"


# ── shared helpers ─────────────────────────────────────────────────────────


async def _load_positions(session: AsyncSession, portfolio: Portfolio) -> list[Position]:
    """Load a portfolio's positions with their assets eagerly loaded."""
    result = await session.execute(
        select(Position).where(Position.portfolio_id == portfolio.id)
    )
    positions = result.scalars().all()
    for pos in positions:
        await session.refresh(pos, attribute_names=["asset"])
    return list(positions)


async def _build_nav_series(positions: list[Position], period: str) -> list[dict]:
    """Build a daily portfolio NAV series from per-asset historical bars.

    Returns ``[{date, nav}]`` aligned to the union of available dates. Returns
    an empty list when no price history is available (e.g. feed disabled).
    """
    if not positions:
        return []
    # collect per-asset close series: {date: {asset_symbol: close}}
    by_date: dict[date, dict[str, Decimal]] = defaultdict(dict)
    for pos in positions:
        symbol = pos.asset.symbol if pos.asset else None
        if not symbol:
            continue
        bars = await data_feed.get_historical(symbol, period)
        if not bars:
            continue
        shares = Decimal(pos.quantity)
        for bar in bars:
            by_date[bar.date][symbol] = shares * Decimal(str(bar.close))

    if not by_date:
        return []
    # nav per date = sum of (shares*close) across assets present that day
    series: list[dict] = []
    for d in sorted(by_date):
        nav = float(sum(by_date[d].values(), Decimal("0")))
        series.append({"date": d.isoformat(), "nav": nav})
    return series


def _position_values(positions: list[Position]) -> list:
    return [
        position_value(
            quantity=pos.quantity,
            avg_cost_basis=pos.avg_cost_basis,
            current_price=pos.current_price,
            asset_id=str(pos.asset_id),
        )
        for pos in positions
    ]


# ── risk ──────────────────────────────────────────────────────────────────


@router.get("/{portfolio_id}/analytics/risk")
async def portfolio_risk(
    portfolio_id: str,
    period: str = Query(default=DEFAULT_PERIOD),
    benchmark: str = Query(default="SPY"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Risk metrics (Sharpe, Sortino, Max DD, VaR, Beta, Alpha, Treynor, Calmar, Ulcer)."""
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    positions = await _load_positions(session, portfolio)
    nav_series = await _build_nav_series(positions, period)
    nav_values = [p["nav"] for p in nav_series] or [1.0]
    returns = simple_returns(nav_values)

    bench_returns: list[float] | None = None
    bench_bars = await data_feed.get_historical(benchmark, period)
    if bench_bars:
        bench_returns = simple_returns([float(b.close) for b in bench_bars])

    # current portfolio value for VaR scaling
    pvs = _position_values(positions)
    nav_currency = float(compute_nav(pvs))
    value = nav_currency or (nav_values[-1] if nav_values else 1.0)

    metrics = compute_risk_metrics(
        returns, benchmark_returns=bench_returns, portfolio_value=value, nav_series=nav_values
    )
    return {"period": period, "benchmark": benchmark, "metrics": metrics}


# ── allocations ───────────────────────────────────────────────────────────


@router.get("/{portfolio_id}/analytics/allocations")
async def portfolio_allocations(
    portfolio_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Allocation breakdown by sector, region, asset class, and basket."""
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    # Eager-load basket to avoid lazy-load in async context
    await session.refresh(portfolio, attribute_names=["basket"])
    positions = await _load_positions(session, portfolio)
    pvs = _position_values(positions)
    nav = compute_nav(pvs)

    def _pct(group: dict[str, Decimal]) -> dict[str, float]:
        if nav == 0:
            return {k: 0.0 for k in group}
        return {k: float(v / nav) for k, v in group.items()}

    by_sector: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_region: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_class: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_basket: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for pos, pv in zip(positions, pvs, strict=True):
        asset = pos.asset
        by_sector[asset.sector or "Unknown"] += pv.market_value
        by_region[asset.region or infer_region(asset.symbol)] += pv.market_value
        by_class[asset.asset_class] += pv.market_value
        basket_name = portfolio.basket.name if portfolio.basket else "Unassigned"
        by_basket[basket_name] += pv.market_value

    return {
        "by_sector": _pct(dict(by_sector)),
        "by_region": _pct(dict(by_region)),
        "by_asset_class": _pct(dict(by_class)),
        "by_basket": _pct(dict(by_basket)),
        "nav": float(nav),
    }


# ── charts ────────────────────────────────────────────────────────────────


@router.get("/{portfolio_id}/charts/nav")
async def chart_nav(
    portfolio_id: str,
    period: str = Query(default=DEFAULT_PERIOD),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    positions = await _load_positions(session, portfolio)
    return {"series": await _build_nav_series(positions, period)}


@router.get("/{portfolio_id}/charts/drawdown")
async def chart_drawdown(
    portfolio_id: str,
    period: str = Query(default=DEFAULT_PERIOD),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    positions = await _load_positions(session, portfolio)
    nav_series = await _build_nav_series(positions, period)
    if len(nav_series) < 2:
        return {"series": [], "max_drawdown": 0.0}
    mdd = max_drawdown([p["nav"] for p in nav_series])
    # per-point drawdown from running max
    values = [p["nav"] for p in nav_series]
    running_max = values[0]
    dd_series = []
    for i, v in enumerate(values):
        running_max = max(running_max, v)
        dd = (v - running_max) / running_max if running_max else 0.0
        dd_series.append({"date": nav_series[i]["date"], "drawdown": dd})
    return {"series": dd_series, "max_drawdown": mdd.value}


@router.get("/{portfolio_id}/charts/allocation")
async def chart_allocation(
    portfolio_id: str,
    group_by: str = Query(default="sector"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    await session.refresh(portfolio, attribute_names=["basket"])
    positions = await _load_positions(session, portfolio)
    pvs = _position_values(positions)
    nav = float(compute_nav(pvs))

    buckets: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for pos, pv in zip(positions, pvs, strict=True):
        asset = pos.asset
        key = {
            "sector": asset.sector or "Unknown",
            "region": asset.region or infer_region(asset.symbol),
            "asset_class": asset.asset_class,
            "basket": (portfolio.basket.name if portfolio.basket else "Unassigned"),
        }.get(group_by, asset.sector or "Unknown")
        buckets[key] += pv.market_value

    slices = [
        {"key": k, "value": float(v), "pct": (float(v) / nav) if nav else 0.0}
        for k, v in buckets.items()
    ]
    return {"group_by": group_by, "slices": slices}


@router.get("/{portfolio_id}/charts/monthly-returns")
async def chart_monthly_returns(
    portfolio_id: str,
    period: str = Query(default=DEFAULT_PERIOD),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    positions = await _load_positions(session, portfolio)
    nav_series = await _build_nav_series(positions, period)
    if len(nav_series) < 2:
        return {"series": []}
    # bucket last nav of each (year, month)
    monthly: dict[tuple[int, int], float] = {}
    for point in nav_series:
        d = date.fromisoformat(point["date"])
        monthly[(d.year, d.month)] = point["nav"]
    sorted_months = sorted(monthly.items())
    rets = []
    for i in range(1, len(sorted_months)):
        prev_nav = sorted_months[i - 1][1]
        cur = sorted_months[i]
        cur_nav = cur[1]
        r = (cur_nav - prev_nav) / prev_nav if prev_nav else 0.0
        rets.append({"month": f"{cur[0][0]:04d}-{cur[0][1]:02d}", "return": r})
    return {"series": rets}


@router.get("/{portfolio_id}/charts/benchmark-comparison")
async def chart_benchmark_comparison(
    portfolio_id: str,
    period: str = Query(default=DEFAULT_PERIOD),
    benchmark: str = Query(default="SPY"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    positions = await _load_positions(session, portfolio)
    nav_series = await _build_nav_series(positions, period)
    bench_bars = await data_feed.get_historical(benchmark, period)

    # normalize both to start at 1.0 for overlay
    def _normalize(values: list[float]) -> list[float]:
        if not values or values[0] == 0:
            return values
        base = values[0]
        return [v / base for v in values]

    port_values = _normalize([p["nav"] for p in nav_series])
    bench_values = _normalize([float(b.close) for b in bench_bars])
    # align by index (truncation)
    n = min(len(port_values), len(bench_values))
    series = []
    for i in range(n):
        series.append(
            {
                "date": nav_series[i]["date"] if i < len(nav_series) else None,
                "portfolio": port_values[i],
                "benchmark": bench_values[i],
            }
        )
    # comparison metrics
    port_returns = simple_returns([p["nav"] for p in nav_series])
    bench_returns = simple_returns([float(b.close) for b in bench_bars])
    comparison = compare_to_benchmark(port_returns, bench_returns)
    return {"series": series, "benchmark": benchmark, "comparison": comparison}


# ── basket-level analytics (called by baskets router) ────────────────────


async def compute_basket_analytics(session: AsyncSession, user: User, basket) -> dict:
    """Aggregate P&L + allocation across all of a user's portfolios in this basket."""
    result = await session.execute(
        select(Portfolio).where(Portfolio.user_id == user.id, Portfolio.basket_id == basket.id)
    )
    portfolios = result.scalars().all()

    all_positions: list[Position] = []
    for pf in portfolios:
        all_positions.extend(await _load_positions(session, pf))

    pvs = _position_values(all_positions)
    nav = compute_nav(pvs)
    cost = sum((pv.quantity * pv.avg_cost_basis for pv in pvs), Decimal("0"))
    gain = nav - cost
    pct = float(gain / cost) if cost != 0 else 0.0

    by_sector: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for pos in all_positions:
        asset = pos.asset
        mv = pos.quantity * pos.current_price
        by_sector[asset.sector or "Unknown"] += mv

    return {
        "basket_id": str(basket.id),
        "basket_name": basket.name,
        "portfolio_count": len(portfolios),
        "nav": float(nav),
        "cost_basis": float(cost),
        "unrealized_gain": float(gain),
        "unrealized_gain_pct": pct,
        "position_count": len(all_positions),
        "allocation_by_sector": (
            {k: float(v / nav) for k, v in by_sector.items()} if nav else {k: 0.0 for k in by_sector}
        ),
    }
