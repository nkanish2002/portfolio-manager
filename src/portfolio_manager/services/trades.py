"""Trade service — business logic for trade operations."""

import structlog
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.database import async_session
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position
from portfolio_manager.models.transaction import Transaction, TransactionType

logger = structlog.getLogger(__name__)


class TradeService:
    """Trade business logic service."""

    async def add_transaction(
        self,
        portfolio_id: str,
        asset_id: str,
        transaction_type: TransactionType,
        quantity: float,
        price: float,
        fees: float = 0,
        notes: str | None = None,
    ) -> dict:
        """Record a trade transaction."""
        async with async_session() as session:
            return await _add_transaction(
                session, portfolio_id, asset_id, transaction_type, quantity, price, fees, notes
            )

    async def sell_position(
        self,
        portfolio_id: str,
        asset_id: str,
        quantity: float,
        price: float,
        fees: float = 0,
        notes: str | None = None,
    ) -> dict:
        """Sell a quantity of an existing position."""
        async with async_session() as session:
            return await _sell_position(
                session, portfolio_id, asset_id, quantity, price, fees, notes
            )

    async def list_trades(self, portfolio_id: str) -> list[dict]:
        """List all trades for a portfolio."""
        async with async_session() as session:
            return await _list_trades(session, portfolio_id)

    async def get_trades_summary(self, portfolio_id: str) -> dict:
        """Get trades summary statistics."""
        async with async_session() as session:
            return await _get_trades_summary(session, portfolio_id)


async def _add_transaction(
    db: AsyncSession,
    portfolio_id: str,
    asset_id: str,
    transaction_type: TransactionType,
    quantity: float,
    price: float,
    fees: float = 0,
    notes: str | None = None,
) -> dict:
    """Record a trade transaction. BUYs also update Position avg-cost basis."""
    transaction = Transaction(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        transaction_type=transaction_type,
        transaction_date=date.today(),
        quantity=quantity,
        price=price,
        fees=fees,
        notes=notes,
    )
    db.add(transaction)

    if transaction_type == TransactionType.BUY:
        await _apply_buy_to_position(db, portfolio_id, asset_id, quantity, price, fees)

    await db.commit()
    await db.refresh(transaction)

    return {"id": str(transaction.id), "status": "recorded"}


async def _apply_buy_to_position(
    db: AsyncSession,
    portfolio_id: str,
    asset_id: str,
    quantity: float,
    price: float,
    fees: float,
) -> None:
    """Update the Position row with a running weighted-average cost basis.

    new_avg = (old_qty * old_avg + buy_qty * buy_price + fees) / (old_qty + buy_qty)
    Fees roll into cost basis (matches the symmetric treatment in `_sell_position`,
    which subtracts fees from sale proceeds).
    """
    qty = Decimal(str(quantity))
    px = Decimal(str(price))
    fee = Decimal(str(fees))
    if qty <= 0:
        raise ValueError("Quantity must be positive")

    buy_cost = qty * px + fee

    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset_id,
        )
    )
    position = result.scalar_one_or_none()

    if position is None:
        db.add(
            Position(
                portfolio_id=portfolio_id,
                asset_id=asset_id,
                quantity=qty,
                avg_cost_basis=buy_cost / qty,
                current_price=px,
                last_price_date=date.today(),
            )
        )
        return

    old_qty = position.quantity or Decimal(0)
    old_avg = position.avg_cost_basis or Decimal(0)
    total_qty = old_qty + qty
    position.avg_cost_basis = (old_qty * old_avg + buy_cost) / total_qty
    position.quantity = total_qty
    position.current_price = px
    position.last_price_date = date.today()


async def _sell_position(
    db: AsyncSession,
    portfolio_id: str,
    asset_id: str,
    quantity: float,
    price: float,
    fees: float = 0,
    notes: str | None = None,
) -> dict:
    """Sell a quantity of an existing position."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise ValueError("Portfolio not found")

    pos_result = await db.execute(
        select(Position)
        .where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset_id,
        )
    )
    position = pos_result.scalar_one_or_none()
    if not position:
        raise ValueError("Position not found")

    current_qty = float(position.quantity)
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if quantity > current_qty:
        raise ValueError(
            f"Cannot sell {quantity} shares. Current position: {current_qty} shares"
        )

    avg_cost = float(position.avg_cost_basis) if position.avg_cost_basis else 0
    sell_price = float(price)
    cost_of_sold = avg_cost * quantity
    proceeds = sell_price * quantity
    realized_pnl = proceeds - cost_of_sold - fees

    new_qty = current_qty - quantity
    position.quantity = new_qty

    if new_qty <= 0:
        await db.delete(position)
    else:
        position.current_price = sell_price

    sell_transaction = Transaction(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        transaction_type=TransactionType.SELL,
        transaction_date=date.today(),
        quantity=quantity,
        price=sell_price,
        fees=fees,
        notes=notes,
    )
    db.add(sell_transaction)
    await db.commit()
    await db.refresh(sell_transaction)

    return {
        "status": "sold",
        "quantity_sold": quantity,
        "price": sell_price,
        "fees": fees,
        "proceeds": proceeds,
        "realized_pnl": round(realized_pnl, 2),
        "remaining_quantity": new_qty,
        "avg_cost_basis": avg_cost,
    }


async def _list_trades(db: AsyncSession, portfolio_id: str) -> list[dict]:
    """List all trades for a portfolio."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.desc())
    )
    transactions = result.scalars().all()

    out = []
    for tx in transactions:
        out.append(
            {
                "id": str(tx.id),
                "portfolio_id": str(tx.portfolio_id),
                "asset_id": str(tx.asset_id),
                "type": tx.transaction_type,
                "date": str(tx.transaction_date),
                "quantity": float(tx.quantity),
                "price": float(tx.price),
                "fees": float(tx.fees),
                "p_and_l": float(tx.p_and_l or 0),
                "notes": tx.notes,
            }
        )
    return out


async def _get_trades_summary(db: AsyncSession, portfolio_id: str) -> dict:
    """Get trades summary statistics."""
    result = await db.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    )
    transactions = result.scalars().all()

    total_buys = 0
    total_sells = 0
    realized_gain = 0.0
    realized_loss = 0.0
    net_realized_pnl = 0.0

    for tx in transactions:
        if tx.transaction_type == TransactionType.BUY:
            total_buys += 1
        elif tx.transaction_type == TransactionType.SELL:
            total_sells += 1
            pnl = float(tx.p_and_l or 0)
            if pnl > 0:
                realized_gain += pnl
            else:
                realized_loss += pnl
            net_realized_pnl += pnl

    return {
        "total_trades": len(transactions),
        "total_buys": total_buys,
        "total_sells": total_sells,
        "realized_gain": round(realized_gain, 2),
        "realized_loss": round(realized_loss, 2),
        "net_realized_p_and_l": round(net_realized_pnl, 2),
    }
