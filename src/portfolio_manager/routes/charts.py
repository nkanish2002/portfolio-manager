"""Chart data API endpoints for Plotly visualizations."""

import pandas as pd
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from portfolio_manager.database import get_db
from portfolio_manager.models.position import Position
from portfolio_manager.services.benchmark import (
    generate_allocation_pie,
    generate_drawdown_chart,
    calculate_risk_report,
)
from portfolio_manager.services.chart_data import (
    generate_nav_chart,
    generate_returns_distribution,
    generate_monthly_returns_heatmap,
)

router = APIRouter(tags=["charts"])


async def get_positions_for_portfolio(portfolio_id: str, db: AsyncSession) -> list[Position] | None:
    """Helper: get positions for a portfolio."""
    pos_result = await db.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(Position.portfolio_id == portfolio_id)
    )
    positions = pos_result.scalars().all()
    return positions if positions else None


def build_nav_from_positions(positions: list[Position]) -> pd.Series:
    """Build NAV time series from positions (simplified: uses current prices as proxy)."""
    if not positions:
        return pd.Series(dtype=float)

    # For simplicity, create a synthetic time series based on position quantities and prices
    # In production, this would use historical transaction data
    values = []
    for pos in positions:
        val = float(pos.quantity) * float(pos.current_price or 0)
        values.append(val)

    return pd.Series(values)


@router.get("/{portfolio_id}/charts/nav")
async def get_nav_chart(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Get NAV (Net Asset Value) chart data for a portfolio."""
    positions = await get_positions_for_portfolio(portfolio_id, db)

    if not positions:
        return {"dates": [], "portfolio_nav": [], "benchmark_nav": None}

    # Build a simple NAV series from current positions
    nav = build_nav_from_positions(positions)
    nav_df = pd.DataFrame({"nav": nav})

    return generate_nav_chart(nav_df)


@router.get("/{portfolio_id}/charts/allocation")
async def get_allocation_chart(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Get asset allocation pie chart data."""
    positions = await get_positions_for_portfolio(portfolio_id, db)

    if not positions:
        return {"labels": [], "values": [], "colors": [], "total_value": 0}

    rows = []
    for pos in positions:
        rows.append({
            "symbol": pos.asset.symbol if pos.asset else "?",
            "quantity": float(pos.quantity),
            "price": float(pos.current_price or 0),
            "asset_class": pos.asset.asset_class if pos.asset else "equity",
        })

    df = pd.DataFrame(rows)
    return generate_allocation_pie(df)


@router.get("/{portfolio_id}/charts/drawdown")
async def get_drawdown_chart(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Get drawdown chart data."""
    positions = await get_positions_for_portfolio(portfolio_id, db)

    if not positions:
        return {"dates": [], "drawdown": [], "nav": []}

    nav = build_nav_from_positions(positions)
    if len(nav) < 2:
        return {"dates": [], "drawdown": [], "nav": []}

    result = generate_drawdown_chart(nav)
    result["nav"] = [round(float(v), 2) for v in nav]
    return result


@router.get("/{portfolio_id}/charts/returns-distribution")
async def get_returns_distribution(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Get returns distribution histogram data."""
    positions = await get_positions_for_portfolio(portfolio_id, db)

    if not positions:
        return {"bins": [], "counts": [], "mean_return": 0.0, "std_return": 0.0}

    nav = build_nav_from_positions(positions)
    if len(nav) < 2:
        return {"bins": [], "counts": [], "mean_return": 0.0, "std_return": 0.0}

    nav_df = pd.DataFrame({"nav": nav})
    return generate_returns_distribution(nav_df)


@router.get("/{portfolio_id}/charts/monthly-returns")
async def get_monthly_returns(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Get monthly returns heatmap data."""
    positions = await get_positions_for_portfolio(portfolio_id, db)

    if not positions:
        return {"years": [], "months": [], "values": [], "labels": []}

    nav = build_nav_from_positions(positions)
    if len(nav) < 60:
        return {"years": [], "months": [], "values": [], "labels": []}

    nav_df = pd.DataFrame({"nav": nav})
    return generate_monthly_returns_heatmap(nav_df)


@router.get("/{portfolio_id}/charts/benchmark-comparison")
async def get_benchmark_comparison(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Get benchmark comparison data."""
    # In production, fetch benchmark data from a data source
    # For now, return empty data
    return {"dates": [], "portfolio": [], "benchmark": [], "excess": []}


@router.get("/{portfolio_id}/risk-report")
async def get_risk_report(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Get comprehensive risk report for a portfolio."""
    positions = await get_positions_for_portfolio(portfolio_id, db)

    if not positions:
        return {"error": "No positions found"}

    nav = build_nav_from_positions(positions)
    if len(nav) < 2:
        return {"error": "Insufficient data for risk report"}

    returns = nav.pct_change().dropna()
    report = calculate_risk_report(returns, nav)
    report["portfolio_id"] = portfolio_id
    return report
