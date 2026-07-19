"""Basket CRUD — user-scoped allocation buckets with color + target validation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Basket, BasketCreate, BasketRead, BasketUpdate
from portfolio_manager.models.user import User

router = APIRouter(prefix="/api/v1/baskets", tags=["baskets"])


@router.get("/", response_model=list[BasketRead])
async def list_baskets(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    result = await session.execute(
        select(Basket).where(Basket.user_id == user.id).order_by(Basket.sort_order, Basket.created_at)
    )
    return result.scalars().all()


@router.post("/", response_model=BasketRead, status_code=status.HTTP_201_CREATED)
async def create_basket(
    payload: BasketCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    basket = Basket(**payload.model_dump(), user_id=user.id)
    session.add(basket)
    await session.commit()
    await session.refresh(basket)
    return basket


@router.get("/{basket_id}", response_model=BasketRead)
async def get_basket(
    basket_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    return await _get_owned(session, basket_id, user.id)


@router.put("/{basket_id}", response_model=BasketRead)
async def update_basket(
    basket_id: str,
    payload: BasketUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    basket = await _get_owned(session, basket_id, user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(basket, key, value)
    session.add(basket)
    await session.commit()
    await session.refresh(basket)
    return basket


@router.delete("/{basket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_basket(
    basket_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    basket = await _get_owned(session, basket_id, user.id)
    # Deleting a basket: portfolios referencing it become unassigned (SET NULL FK).
    await session.delete(basket)
    await session.commit()


@router.get("/{basket_id}/analytics")
async def basket_analytics(
    basket_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Basket-level P&L, allocation, and risk metrics across its portfolios."""
    basket = await _get_owned(session, basket_id, user.id)
    # Lazy import to avoid a circular dependency with the analytics service
    from portfolio_manager.routes.analytics import compute_basket_analytics

    return await compute_basket_analytics(session, user, basket)


async def _get_owned(session: AsyncSession, basket_id: str, user_id) -> Basket:
    from uuid import UUID

    try:
        uid = UUID(str(basket_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Basket not found") from e
    result = await session.execute(
        select(Basket).where(Basket.id == uid, Basket.user_id == user_id)
    )
    basket = result.scalar_one_or_none()
    if basket is None:
        raise HTTPException(status_code=404, detail="Basket not found")
    return basket
