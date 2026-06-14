"""Portfolio service — business logic for portfolio operations.

This service is called directly by Solara components. No FastAPI routes.
"""

import structlog
from sqlalchemy import func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.database import async_session
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position

logger = structlog.getLogger(__name__)


class PortfolioService:
    """Portfolio business logic service."""

    async def list_portfolios(self) -> list[dict]:
        """List all portfolios with stats."""
        async with async_session() as session:
            return await _list_portfolios(session)

    async def get_portfolio(self, portfolio_id: str) -> dict | None:
        """Get a portfolio by ID with stats."""
        async with async_session() as session:
            return await _get_portfolio(session, portfolio_id)

    async def create_portfolio(self, name: str, description: str | None, currency: str) -> dict:
        """Create a new portfolio."""
        async with async_session() as session:
            return await _create_portfolio(session, name, description, currency)

    async def delete_portfolio(self, portfolio_id: str) -> bool:
        """Delete a portfolio."""
        async with async_session() as session:
            return await _delete_portfolio(session, portfolio_id)


async def _list_portfolios(db: AsyncSession) -> list[dict]:
    """List all portfolios with stats."""
    result = await db.execute(
        sql_func.select(Portfolio).order_by(Portfolio.created_at.desc())
    )
    portfolios = result.scalars().all()

    out = []
    for p in portfolios:
        stats = await _portfolio_stats(db, str(p.id))
        out.append(
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "currency": p.currency,
                "position_count": stats["position_count"],
                "total_value": stats["total_value"],
            }
        )
    return out


async def _get_portfolio(db: AsyncSession, portfolio_id: str) -> dict | None:
    """Get a portfolio by ID with stats."""
    result = await db.execute(sql_func.select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return None

    stats = await _portfolio_stats(db, portfolio_id)
    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "description": portfolio.description,
        "currency": portfolio.currency,
        "position_count": stats["position_count"],
        "total_value": stats["total_value"],
    }


async def _portfolio_stats(db: AsyncSession, portfolio_id: str) -> dict:
    """Compute position_count and total_value for a portfolio."""
    pos_count_result = await db.execute(
        sql_func.select(sql_func.count(Position.id)).where(
            Position.portfolio_id == portfolio_id
        )
    )
    pos_count = pos_count_result.scalar_one() or 0

    # total_value = sum(quantity * current_price) for all positions
    pos_val_result = await db.execute(
        sql_func.select(
            sql_func.sum(
                Position.quantity * sql_func.coalesce(Position.current_price, 0)
            )
        ).where(Position.portfolio_id == portfolio_id)
    )
    total_value = round(float(pos_val_result.scalar_one() or 0), 2)

    return {"position_count": pos_count, "total_value": total_value}


async def _create_portfolio(
    db: AsyncSession, name: str, description: str | None, currency: str
) -> dict:
    """Create a new portfolio."""
    portfolio = Portfolio(name=name, description=description, currency=currency)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)

    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "description": portfolio.description,
        "currency": portfolio.currency,
        "position_count": 0,
        "total_value": 0.0,
    }


async def _delete_portfolio(db: AsyncSession, portfolio_id: str) -> bool:
    """Delete a portfolio."""
    result = await db.execute(
        sql_func.select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return False

    await db.delete(portfolio)
    await db.commit()
    return True
