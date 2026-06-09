"""Dashboard HTML pages via Jinja2 templates + HTMX."""

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse
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

# Path to React SPA build
SPA_INDEX = Path(__file__).parent.parent.parent.parent / "frontend" / "dist" / "index.html"


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Main dashboard — serve React SPA (client-side routing handles content)."""
    if SPA_INDEX.exists():
        return FileResponse(str(SPA_INDEX))
    return {"error": "Frontend not built"}


@router.get("/dashboard/{portfolio_id}", response_class=HTMLResponse)
async def portfolio_dashboard_page(
    request: Request,
    portfolio_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Single portfolio detail — serve React SPA (client-side routing handles content)."""
    if SPA_INDEX.exists():
        return FileResponse(str(SPA_INDEX))
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Frontend not built")
