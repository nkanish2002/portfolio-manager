"""UI page routes — HTML templates for main navigation sections."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.database import get_db, templates
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position
from portfolio_manager.models.transaction import Transaction
from sqlalchemy.orm import selectinload

router = APIRouter()


# ---- Positions Page ----

@router.get("/positions", response_class=HTMLResponse)
async def positions_page(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Show all positions across all portfolios."""
    result = await db.execute(select(Portfolio).order_by(Portfolio.created_at.desc()))
    portfolios = result.scalars().all()

    all_positions = []
    for p in portfolios:
        pos_result = await db.execute(
            select(Position)
            .options(selectinload(Position.asset))
            .where(Position.portfolio_id == p.id)
        )
        positions = pos_result.scalars().all()
        for pos in positions:
            asset = pos.asset
            market_val = float(pos.quantity) * float(pos.current_price or 0)
            cost = float(pos.quantity) * float(pos.avg_cost_basis)
            gain = market_val - cost
            gain_pct = (gain / cost * 100) if cost > 0 else 0
            all_positions.append({
                "portfolio_name": p.name,
                "portfolio_id": str(p.id),
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

    # Sort by market_value descending
    all_positions.sort(key=lambda x: x["market_value"], reverse=True)

    return templates.TemplateResponse(request, "positions.html", {
        "positions": all_positions,
        "total_value": round(sum(p["market_value"] for p in all_positions), 2),
        "total_gain": round(sum(p["gain"] for p in all_positions), 2),
    })


# ---- Analytics Page ----

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Show portfolio analytics overview."""
    result = await db.execute(select(Portfolio).order_by(Portfolio.created_at.desc()))
    portfolios = result.scalars().all()

    portfolio_summaries = []
    for p in portfolios:
        pos_result = await db.execute(
            select(Position)
            .options(selectinload(Position.asset))
            .where(Position.portfolio_id == p.id)
        )
        positions = pos_result.scalars().all()
        total_value = 0
        total_gain = 0
        for pos in positions:
            mv = float(pos.quantity) * float(pos.current_price or 0)
            cost = float(pos.quantity) * float(pos.avg_cost_basis)
            total_value += mv
            total_gain += mv - cost

        portfolio_summaries.append({
            "id": str(p.id),
            "name": p.name,
            "currency": p.currency,
            "position_count": len(positions),
            "total_value": round(total_value, 2),
            "total_gain": round(total_gain, 2),
            "return_pct": round(total_gain / total_value * 100, 2) if total_value > 0 else 0,
        })

    # Precompute aggregates (Jinja2 can't do generator expressions)
    all_values = [p["total_value"] for p in portfolio_summaries]
    all_gains = [p["total_gain"] for p in portfolio_summaries]
    grand_total_value = round(sum(all_values), 2) if all_values else 0
    grand_total_gain = round(sum(all_gains), 2) if all_gains else 0
    overall_return_pct = round(grand_total_gain / grand_total_value * 100, 2) if grand_total_value > 0 else None

    return templates.TemplateResponse(request, "analytics.html", {
        "portfolios": portfolio_summaries,
        "grand_total_value": grand_total_value,
        "grand_total_gain": grand_total_gain,
        "overall_return_pct": overall_return_pct,
    })


# ---- Settings Page ----

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page — data sources, API keys, preferences."""
    return templates.TemplateResponse(request, "settings.html", {})
