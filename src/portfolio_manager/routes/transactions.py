"""Transaction recording + history — routes under a portfolio.

Sells compute realized P&L via FIFO by replaying prior buy/sell transactions
for the same asset in the portfolio. Recording a buy/sell also updates the
matching Position (quantity + weighted-average cost + current price).
"""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Position, Transaction, TransactionRead
from portfolio_manager.models.user import User
from portfolio_manager.routes.portfolios import _get_owned as get_owned_portfolio
from portfolio_manager.services.portfolio_calc import compute_position_fields
from portfolio_manager.services.trades import TradeLedger

router = APIRouter(prefix="/api/v1/portfolios", tags=["transactions"])

# transaction types that affect share holdings
_HOLDING_TYPES = {"buy", "sell"}


class TransactionCreateBody(BaseModel):
    """Body for recording a transaction (portfolio_id from the path)."""

    asset_id: str
    type: str
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal("0")
    trade_date: datetime | None = None
    notes: str | None = None


@router.post("/{portfolio_id}/transactions", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def record_transaction(
    portfolio_id: str,
    body: TransactionCreateBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    from uuid import UUID

    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    asset_uid = UUID(str(body.asset_id))
    trade_date = body.trade_date or datetime.now(UTC)

    realized_gain: Decimal | None = None
    if body.type in _HOLDING_TYPES:
        realized_gain = await _apply_to_position(session, portfolio.id, asset_uid, body, trade_date)

    txn = Transaction(
        portfolio_id=portfolio.id,
        asset_id=asset_uid,
        type=body.type,
        quantity=body.quantity,
        price=body.price,
        fees=body.fees,
        trade_date=trade_date,
        notes=body.notes,
        realized_gain=realized_gain,
    )
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    return txn


@router.get("/{portfolio_id}/transactions", response_model=list[TransactionRead])
async def list_transactions(
    portfolio_id: str,
    type: str | None = Query(default=None),
    asset_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    stmt = select(Transaction).where(Transaction.portfolio_id == portfolio.id)
    if type is not None:
        stmt = stmt.where(Transaction.type == type)
    if asset_id is not None:
        from uuid import UUID

        stmt = stmt.where(Transaction.asset_id == UUID(str(asset_id)))
    stmt = stmt.order_by(Transaction.trade_date.desc(), Transaction.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


# ── position + FIFO helpers ───────────────────────────────────────────────


async def _apply_to_position(
    session: AsyncSession,
    portfolio_id,
    asset_id,
    body: TransactionCreateBody,
    trade_date: datetime,
) -> Decimal | None:
    """Update the Position for a buy/sell and return realized gain (sells only)."""
    result = await session.execute(
        select(Position).where(Position.portfolio_id == portfolio_id, Position.asset_id == asset_id)
    )
    position = result.scalar_one_or_none()

    qty = body.quantity
    price = body.price

    if body.type == "buy":
        if position is None:
            position = Position(
                portfolio_id=portfolio_id,
                asset_id=asset_id,
                quantity=qty,
                avg_cost_basis=price,
                current_price=price,
            )
            position.market_value, position.unrealized_gain, position.unrealized_gain_pct = (
                compute_position_fields(quantity=qty, avg_cost_basis=price, current_price=price)
            )
        else:
            new_qty = position.quantity + qty
            if new_qty != 0:
                position.avg_cost_basis = (
                    position.quantity * position.avg_cost_basis + qty * price
                ) / new_qty
            position.quantity = new_qty
            position.current_price = price
            position.market_value, position.unrealized_gain, position.unrealized_gain_pct = (
                compute_position_fields(
                    quantity=position.quantity,
                    avg_cost_basis=position.avg_cost_basis,
                    current_price=price,
                )
            )
        session.add(position)
        return None

    # sell
    realized = Decimal("0")
    if position is not None:
        # FIFO: replay prior transactions for this asset to compute realized gain
        realized = await _fifo_realized(session, portfolio_id, asset_id, qty, price)
        position.quantity = position.quantity - qty
        position.current_price = price
        position.market_value, position.unrealized_gain, position.unrealized_gain_pct = (
            compute_position_fields(
                quantity=position.quantity,
                avg_cost_basis=position.avg_cost_basis,
                current_price=price,
            )
        )
        session.add(position)
    return realized


async def _fifo_realized(
    session: AsyncSession,
    portfolio_id,
    asset_id,
    sell_qty: Decimal,
    sell_price: Decimal,
) -> Decimal:
    """Replay prior buys/sells for the asset, then apply this sell (FIFO)."""
    result = await session.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id, Transaction.asset_id == asset_id)
        .order_by(Transaction.trade_date, Transaction.created_at)
    )
    prior = result.scalars().all()
    ledger = TradeLedger()
    for txn in prior:
        if txn.type == "buy":
            ledger.buy(str(asset_id), Decimal(txn.quantity), Decimal(txn.price))
        elif txn.type == "sell":
            ledger.sell(str(asset_id), Decimal(txn.quantity), Decimal(txn.price))
    res = ledger.sell(str(asset_id), Decimal(sell_qty), Decimal(sell_price))
    return res.realized_gain
