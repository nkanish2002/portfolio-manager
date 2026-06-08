"""Dashboard HTML pages via Jinja2 templates + HTMX."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from portfolio_manager.database import get_db, templates
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position
from portfolio_manager.services.portfolio_calc import calculate_portfolio_value, calculate_returns, build_price_series
from portfolio_manager.services.benchmark import calculate_risk_report, generate_allocation_pie, generate_drawdown_chart
from portfolio_manager.services.classification import classify_positions

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Main dashboard — portfolio overview with charts."""
    result = await db.execute(select(Portfolio).order_by(Portfolio.created_at.desc()))
    portfolios = result.scalars().all()

    portfolio_data = None
    chart_data = None
    if portfolios:
        first_id = portfolios[0].id
        pos_result = await db.execute(
            select(Position)
            .options(selectinload(Position.asset))
            .where(Position.portfolio_id == first_id)
        )
        positions = pos_result.scalars().all()
        if positions:
            rows = []
            for pos in positions:
                rows.append({
                    "symbol": pos.asset.symbol if pos.asset else "?",
                    "quantity": float(pos.quantity),
                    "price": float(pos.current_price or 0),
                    "cost_basis": float(pos.avg_cost_basis),
                    "asset_class": pos.asset.asset_class if pos.asset else "equity",
                })

            import pandas as pd
            df = pd.DataFrame(rows)
            if not df.empty:
                portfolio_data = calculate_portfolio_value(df)

                # Generate chart data
                nav_series = (1 + df["price"].pct_change().fillna(0)).cumsum()
                nav_series.index = df.index
                nav_df = pd.DataFrame({"nav": nav_series})

                chart_data = {
                    "nav": json.dumps(generate_drawdown_chart(nav_df["nav"])),
                    "allocation": json.dumps(generate_allocation_pie(df)),
                }

    return templates.TemplateResponse(request, "index.html", {
        "portfolios": portfolios,
        "portfolio_data": portfolio_data,
        "chart_data": chart_data,
    })


@router.get("/dashboard/{portfolio_id}", response_class=HTMLResponse)
async def portfolio_dashboard_page(
    request: Request,
    portfolio_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Single portfolio detail dashboard."""
    from fastapi import HTTPException

    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    pos_result = await db.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(Position.portfolio_id == portfolio_id)
    )
    positions = pos_result.scalars().all()

    rows = []
    for pos in positions:
        rows.append({
            "symbol": pos.asset.symbol if pos.asset else "?",
            "quantity": float(pos.quantity),
            "price": float(pos.current_price or 0),
            "cost_basis": float(pos.avg_cost_basis),
            "asset_class": pos.asset.asset_class if pos.asset else "equity",
            "exchange": pos.asset.exchange if pos.asset else "US",
        })

    import pandas as pd
    df = pd.DataFrame(rows)
    portfolio_data = calculate_portfolio_value(df) if not df.empty else {}

    # Classify positions
    classified_positions = classify_positions(rows) if not df.empty else []

    position_rows = []
    for pos in positions:
        asset = pos.asset
        market_val = float(pos.quantity) * float(pos.current_price or 0)
        cost = float(pos.quantity) * float(pos.avg_cost_basis)
        gain = market_val - cost
        gain_pct = (gain / cost * 100) if cost > 0 else 0
        position_rows.append({
            "symbol": asset.symbol if asset else "?",
            "name": asset.name if asset else "?",
            "asset_class": asset.asset_class if asset else "equity",
            "quantity": float(pos.quantity),
            "price": float(pos.current_price or 0),
            "cost_basis": float(pos.avg_cost_basis),
            "market_value": round(market_val, 2),
            "gain": round(gain, 2),
            "gain_pct": round(gain_pct, 2),
        })

    # Generate chart data for template
    chart_data = None
    if not df.empty:
        nav_series = (1 + df["price"].pct_change().fillna(0)).cumsum()
        nav_series.index = df.index
        nav_df = pd.DataFrame({"nav": nav_series})

        chart_data = {
            "nav": json.dumps(generate_drawdown_chart(nav_df["nav"])),
            "allocation": json.dumps(generate_allocation_pie(df)),
        }

    return templates.TemplateResponse(request, "dashboard.html", {
        "portfolio": portfolio,
        "position_rows": position_rows,
        "classified_positions": classified_positions,
        "portfolio_data": portfolio_data,
        "chart_data": chart_data,
    })
