"""Account CRUD — user-scoped brokerage accounts."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Account, AccountCreate, AccountRead, AccountUpdate
from portfolio_manager.models.user import User

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.get("/", response_model=list[AccountRead])
async def list_accounts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    result = await session.execute(select(Account).where(Account.user_id == user.id))
    return result.scalars().all()


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    account = Account(**payload.model_dump(), user_id=user.id)
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    account = await _get_owned(session, account_id, user.id)
    return account


@router.put("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: str,
    payload: AccountUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    account = await _get_owned(session, account_id, user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    account = await _get_owned(session, account_id, user.id)
    await session.delete(account)
    await session.commit()


async def _get_owned(session: AsyncSession, account_id: str, user_id) -> Account:
    from uuid import UUID

    try:
        uid = UUID(str(account_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Account not found") from e
    result = await session.execute(
        select(Account).where(Account.id == uid, Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account
