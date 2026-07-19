"""Portfolio CRUD — user-scoped, linked to an account + optional basket."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Account, Basket, Portfolio, PortfolioCreate, PortfolioRead, PortfolioUpdate
from portfolio_manager.models.user import User

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])


@router.get("/", response_model=list[PortfolioRead])
async def list_portfolios(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    result = await session.execute(
        select(Portfolio).where(Portfolio.user_id == user.id).order_by(Portfolio.created_at)
    )
    return result.scalars().all()


@router.post("/", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    payload: PortfolioCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    await _validate_account(session, payload.account_id, user.id)
    if payload.basket_id is not None:
        await _validate_basket(session, payload.basket_id, user.id)
    portfolio = Portfolio(**payload.model_dump(), user_id=user.id)
    session.add(portfolio)
    await session.commit()
    await session.refresh(portfolio)
    return portfolio


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Portfolio detail with its current positions."""
    portfolio = await _get_owned(session, portfolio_id, user.id)
    # eagerly load positions
    await session.refresh(portfolio, attribute_names=["positions"])
    return {
        **portfolio.model_dump(),
        "positions": [p.model_dump() for p in portfolio.positions],
    }


@router.put("/{portfolio_id}", response_model=PortfolioRead)
async def update_portfolio(
    portfolio_id: str,
    payload: PortfolioUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await _get_owned(session, portfolio_id, user.id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("basket_id") is not None:
        await _validate_basket(session, data["basket_id"], user.id)
    for key, value in data.items():
        setattr(portfolio, key, value)
    session.add(portfolio)
    await session.commit()
    await session.refresh(portfolio)
    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await _get_owned(session, portfolio_id, user.id)
    await session.delete(portfolio)
    await session.commit()


# ── helpers ──────────────────────────────────────────────────────────────


async def _get_owned(session: AsyncSession, portfolio_id: str, user_id) -> Portfolio:
    from uuid import UUID

    try:
        uid = UUID(str(portfolio_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Portfolio not found") from e
    result = await session.execute(
        select(Portfolio).where(Portfolio.id == uid, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


async def _validate_account(session: AsyncSession, account_id, user_id) -> None:
    from uuid import UUID

    try:
        uid = UUID(str(account_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid account_id") from e
    result = await session.execute(
        select(Account).where(Account.id == uid, Account.user_id == user_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Account not found or not owned by user")


async def _validate_basket(session: AsyncSession, basket_id, user_id) -> None:
    from uuid import UUID

    try:
        uid = UUID(str(basket_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid basket_id") from e
    result = await session.execute(
        select(Basket).where(Basket.id == uid, Basket.user_id == user_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Basket not found or not owned by user")
