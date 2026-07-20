"""Position management + price refresh — routes under a portfolio."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Position, PositionRead
from portfolio_manager.models.user import User
from portfolio_manager.routes.portfolios import _get_owned as get_owned_portfolio
from portfolio_manager.services.data_feed import data_feed
from portfolio_manager.services.portfolio_calc import compute_position_fields

router = APIRouter(prefix="/api/v1/portfolios", tags=["positions"])


class PositionCreateBody(BaseModel):
    """Body for adding/updating a position (portfolio_id comes from the path)."""

    asset_id: str
    quantity: Decimal
    avg_cost_basis: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")


class PositionMoveBody(BaseModel):
    """Move a position to another portfolio (which determines its basket)."""

    target_portfolio_id: str


@router.get("/{portfolio_id}/positions", response_model=list[PositionRead])
async def list_positions(
    portfolio_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    result = await session.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(Position.portfolio_id == portfolio.id)
        .order_by(Position.created_at)
    )
    positions = result.scalars().all()
    reads = [PositionRead.model_validate(p) for p in positions]
    for p, r in zip(positions, reads, strict=True):
        r.symbol = p.asset.symbol if p.asset else None
    return reads


@router.post("/{portfolio_id}/positions", response_model=PositionRead, status_code=status.HTTP_201_CREATED)
async def upsert_position(
    portfolio_id: str,
    body: PositionCreateBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Add a position, or update quantity/cost if one exists for this asset."""
    from uuid import UUID

    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    asset_uid = UUID(str(body.asset_id))
    result = await session.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id, Position.asset_id == asset_uid
        )
    )
    position = result.scalar_one_or_none()

    market_value, unrealized_gain, gain_pct = compute_position_fields(
        quantity=body.quantity,
        avg_cost_basis=body.avg_cost_basis,
        current_price=body.current_price,
    )
    if position is None:
        position = Position(
            portfolio_id=portfolio.id,
            asset_id=asset_uid,
            quantity=body.quantity,
            avg_cost_basis=body.avg_cost_basis,
            current_price=body.current_price,
            market_value=market_value,
            unrealized_gain=unrealized_gain,
            unrealized_gain_pct=gain_pct,
        )
        session.add(position)
    else:
        position.quantity = body.quantity
        position.avg_cost_basis = body.avg_cost_basis
        position.current_price = body.current_price
        position.market_value = market_value
        position.unrealized_gain = unrealized_gain
        position.unrealized_gain_pct = gain_pct
        session.add(position)
    await session.commit()
    await session.refresh(position)
    return position


@router.post("/{portfolio_id}/positions/refresh", response_model=list[PositionRead])
async def refresh_prices(
    portfolio_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Refresh all position prices via the data feed (yfinance)."""
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    result = await session.execute(
        select(Position).where(Position.portfolio_id == portfolio.id)
    )
    positions = result.scalars().all()
    refreshed: list[Position] = []
    for pos in positions:
        # load the asset to get its ticker symbol
        await session.refresh(pos, attribute_names=["asset"])
        symbol = pos.asset.symbol if pos.asset else None
        if not symbol:
            refreshed.append(pos)
            continue
        quote = await data_feed.get_price(symbol)
        if quote is None:
            refreshed.append(pos)
            continue
        pos.current_price = Decimal(str(quote.price))
        pos.market_value, pos.unrealized_gain, pos.unrealized_gain_pct = compute_position_fields(
            quantity=pos.quantity,
            avg_cost_basis=pos.avg_cost_basis,
            current_price=pos.current_price,
        )
        session.add(pos)
        refreshed.append(pos)
        # invalidate stale cache so the WS poller refetches
        data_feed.invalidate(symbol)
    await session.commit()
    for pos in refreshed:
        await session.refresh(pos)
    return refreshed


@router.post("/{portfolio_id}/positions/{position_id}/move", response_model=PositionRead)
async def move_position(
    portfolio_id: str,
    position_id: str,
    body: PositionMoveBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Reassign a position to a different portfolio (i.e. a different basket)."""
    from uuid import UUID

    src_portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    target_portfolio = await get_owned_portfolio(session, body.target_portfolio_id, user.id)

    result = await session.execute(
        select(Position).where(
            Position.id == UUID(str(position_id)), Position.portfolio_id == src_portfolio.id
        )
    )
    position = result.scalar_one_or_none()
    if position is None:
        raise HTTPException(status_code=404, detail="Position not found")

    # honor the (portfolio_id, asset_id) uniqueness — merge if a position exists
    existing = await session.execute(
        select(Position).where(
            Position.portfolio_id == target_portfolio.id, Position.asset_id == position.asset_id
        )
    )
    target_pos = existing.scalar_one_or_none()
    if target_pos is not None and target_pos.id != position.id:
        # merge into the existing target position (sum quantities, weighted cost)
        total_qty = target_pos.quantity + position.quantity
        if total_qty != 0:
            target_pos.avg_cost_basis = (
                target_pos.quantity * target_pos.avg_cost_basis + position.quantity * position.avg_cost_basis
            ) / total_qty
        target_pos.quantity = total_qty
        target_pos.current_price = position.current_price
        target_pos.market_value, target_pos.unrealized_gain, target_pos.unrealized_gain_pct = (
            compute_position_fields(
                quantity=total_qty,
                avg_cost_basis=target_pos.avg_cost_basis,
                current_price=target_pos.current_price,
            )
        )
        await session.delete(position)
        session.add(target_pos)
        await session.commit()
        await session.refresh(target_pos)
        return target_pos

    position.portfolio_id = target_portfolio.id
    session.add(position)
    await session.commit()
    await session.refresh(position)
    return position
