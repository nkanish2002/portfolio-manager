"""Report generation route — standalone HTML portfolio report.

Endpoint:
  GET /api/v1/reports/portfolio/{portfolio_id}

Generates a self-contained HTML report covering:
  - Portfolio summary (NAV, P&L, position count)
  - Basket allocation (target vs actual, color-coded)
  - Position table (symbol, qty, price, value, P&L, sector)
  - Risk metrics (9 metrics with benchmark comparison)
  - Sector allocation breakdown

The report is returned as an ``application/html`` response with a
``Content-Disposition: attachment`` header for direct download.
"""

from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Basket, Portfolio, Position
from portfolio_manager.models.user import User
from portfolio_manager.routes.portfolios import _get_owned as get_owned_portfolio
from portfolio_manager.services.data_feed import data_feed
from portfolio_manager.services.portfolio_calc import (
    compute_nav,
    position_value,
    simple_returns,
)
from portfolio_manager.services.report_generator import (
    generate_portfolio_report,
    generate_report_filename,
)
from portfolio_manager.services.risk import compute_risk_metrics

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

DEFAULT_PERIOD = "1y"
DEFAULT_BENCHMARK = "SPY"


# ── shared helpers ──────────────────────────────────────────────────────


async def _load_positions(session: AsyncSession, portfolio: Portfolio) -> list[Position]:
    """Load positions with assets eagerly loaded."""
    result = await session.execute(select(Position).where(Position.portfolio_id == portfolio.id))
    positions = result.scalars().all()
    for pos in positions:
        await session.refresh(pos, attribute_names=["asset"])
    return list(positions)


async def _build_nav_series(positions: list[Position], period: str) -> list[dict]:
    """Build daily portfolio NAV series from per-asset historical bars."""
    if not positions:
        return []
    by_date: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for pos in positions:
        symbol = pos.asset.symbol if pos.asset else None
        if not symbol:
            continue
        bars = await data_feed.get_historical(symbol, period)
        if not bars:
            continue
        shares = Decimal(pos.quantity)
        for bar in bars:
            by_date[bar.date.isoformat()][symbol] = shares * Decimal(str(bar.close))
    if not by_date:
        return []
    return [{"date": d, "nav": float(sum(by_date[d].values(), Decimal("0")))} for d in sorted(by_date)]


async def _load_user_baskets(session: AsyncSession, user_id) -> list[Basket]:
    """Load all baskets for the current user."""
    result = await session.execute(select(Basket).where(Basket.user_id == user_id).order_by(Basket.sort_order))
    return list(result.scalars().all())


# ── Report endpoint ─────────────────────────────────────────────────────


@router.get("/portfolio/{portfolio_id}")
async def generate_portfolio_html_report(
    portfolio_id: str,
    period: str = Query(default=DEFAULT_PERIOD, description="History period for risk metrics"),
    benchmark: str = Query(default=DEFAULT_BENCHMARK, description="Benchmark ticker for comparison"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
) -> Response:
    """Generate and download a standalone HTML portfolio report."""
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    # Eagerly load the basket relationship (lazy access in async raises MissingGreenlet)
    await session.refresh(portfolio, attribute_names=["basket"])
    positions = await _load_positions(session, portfolio)
    baskets = await _load_user_baskets(session, user.id)

    # ── Compute NAV and P&L ──────────────────────────────────────
    pvs = [
        position_value(
            quantity=pos.quantity,
            avg_cost_basis=pos.avg_cost_basis,
            current_price=pos.current_price,
            asset_id=str(pos.asset_id),
        )
        for pos in positions
    ]
    total_value = float(compute_nav(pvs))
    total_cost = float(sum((pv.quantity * pv.avg_cost_basis for pv in pvs), Decimal("0")))
    total_pnl = total_value - total_cost

    # ── Basket allocation (target vs actual) ──────────────────────
    basket_nav: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for pos in positions:
        # Portfolio is assigned to a basket via basket_id
        basket_name = portfolio.basket.name if portfolio.basket else "Unassigned"
        basket_nav[basket_name] += pos.quantity * pos.current_price

    basket_rows = []
    for b in baskets:
        actual = float(basket_nav.get(b.name, Decimal("0"))) / total_value * 100 if total_value else 0.0
        basket_rows.append(
            {
                "name": b.name,
                "color": b.color,
                "target_allocation": float(b.target_allocation),
                "actual_allocation": actual,
            }
        )

    # ── Positions table ──────────────────────────────────────────
    position_rows = []
    for pos in positions:
        asset = pos.asset
        gain = float(pos.unrealized_gain)
        gain_pct = float(pos.unrealized_gain_pct)
        position_rows.append(
            {
                "symbol": asset.symbol,
                "quantity": float(pos.quantity),
                "current_price": float(pos.current_price),
                "market_value": float(pos.quantity * pos.current_price),
                "unrealized_gain": gain,
                "unrealized_gain_pct": gain_pct,
                "sector": asset.sector or "Unknown",
            }
        )

    # ── Risk metrics ─────────────────────────────────────────────
    nav_series = await _build_nav_series(positions, period)
    nav_values = [p["nav"] for p in nav_series] or [1.0]
    returns = simple_returns(nav_values)

    risk_metrics: dict[str, float] = {}
    bench_returns: list[float] | None = None
    bench_bars = await data_feed.get_historical(benchmark, period)
    if bench_bars:
        bench_returns = simple_returns([float(b.close) for b in bench_bars])

    if returns:
        risk_metrics = compute_risk_metrics(
            returns,
            benchmark_returns=bench_returns,
            portfolio_value=total_value or 1.0,
            nav_series=nav_values,
        )

    # ── Sector allocation ────────────────────────────────────────
    sector_vals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for pos in positions:
        asset = pos.asset
        sector_vals[asset.sector or "Unknown"] += pos.quantity * pos.current_price
    sector_allocation = {k: (float(v) / total_value if total_value else 0.0) for k, v in sector_vals.items()}

    # ── Generate HTML report ─────────────────────────────────────
    report_data = {
        "portfolio_name": portfolio.name,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "position_count": len(positions),
        "basket_count": len(baskets),
        "baskets": basket_rows,
        "positions": position_rows,
        "risk_metrics": risk_metrics,
        "benchmark": benchmark,
        "risk_period": period.upper(),
        "sector_allocation": sector_allocation,
    }

    html_bytes = generate_portfolio_report(report_data)
    filename = generate_report_filename(portfolio.name)

    return Response(
        content=html_bytes,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
