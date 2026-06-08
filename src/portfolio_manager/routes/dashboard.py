"""Dashboard HTML pages via Jinja2 templates + HTMX."""

from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.database import get_db, templates
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position
from portfolio_manager.services.portfolio_calc import calculate_portfolio_value

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
    if portfolios:
        first_id = portfolios[0].id
        pos_result = await db.execute(
            select(Position).where(Position.portfolio_id == first_id)
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

    return templates.TemplateResponse(request, "index.html", {
        "portfolios": portfolios,
        "portfolio_data": portfolio_data,
    })


@router.get("/dashboard/{portfolio_id}", response_class=HTMLResponse)
async def portfolio_dashboard_page(
    request: Request,
    portfolio_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Single portfolio detail dashboard."""
    from fastapi import HTTPException

    result = await db.execute(select(Portfolio).where(Portfolio.id == UUID(portfolio_id)))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    pos_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
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
        })

    import pandas as pd
    df = pd.DataFrame(rows)
    portfolio_data = calculate_portfolio_value(df) if not df.empty else {}

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

    return templates.TemplateResponse(request, "dashboard.html", {
        "portfolio": portfolio,
        "position_rows": position_rows,
        "portfolio_data": portfolio_data,
    })
