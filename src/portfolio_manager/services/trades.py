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

    async def list_trades(
        self,
        portfolio_id: str,
        trade_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """List trades for a portfolio with optional filter and pagination.

        Args:
            portfolio_id: Portfolio ID to list trades for.
            trade_type: Optional filter (ALL, BUY, SELL, DIVIDEND, FEE, etc.).
            page: Page number (1-based).
            page_size: Number of trades per page.

        Returns:
            Dict with 'trades', 'total', 'page', 'page_size', 'total_pages'.
        """
        async with async_session() as session:
            return await _list_trades(
                session, portfolio_id, trade_type, page, page_size
            )

    async def get_trades_summary(self, portfolio_id: str) -> dict:
        """Get trades summary statistics."""
        async with async_session() as session:
            return await _get_trades_summary(session, portfolio_id)

    async def get_position_for_asset(
        self, portfolio_id: str, asset_id: str
    ) -> dict | None:
        """Get position details for a specific asset in a portfolio.

        Returns position data suitable for a sell modal, including
        quantity, avg cost basis, and current price.
        """
        async with async_session() as session:
            return await _get_position_for_asset(session, portfolio_id, asset_id)

    async def get_portfolio_available_cash(self, portfolio_id: str) -> float:
        """Estimate available cash from realized gains and deposits.

        Calculates: sum of (sell proceeds - cost basis - fees) for all sells,
        plus deposits minus withdrawals. This is a rough estimate.
        """
        async with async_session() as session:
            return await _get_portfolio_available_cash(session, portfolio_id)

    async def calculate_sell_preview(
        self,
        portfolio_id: str,
        asset_id: str,
        quantity: float,
        price: float,
        fees: float = 0,
    ) -> dict:
        """Calculate sell P&L preview without committing.

        Returns dict with projected_pnl, proceeds, cost_of_sold,
        realized_gain, remaining_quantity, and validation errors.
        """
        async with async_session() as session:
            return await _calculate_sell_preview(
                session, portfolio_id, asset_id, quantity, price, fees
            )

    async def calculate_buy_cost(
        self,
        portfolio_id: str,
        asset_id: str,
        quantity: float,
        price: float,
        fees: float = 0,
    ) -> dict:
        """Calculate buy cost summary.

        Returns dict with total_cost, quantity, price, fees.
        """
        total_cost = quantity * price + fees
        return {
            "total_cost": round(total_cost, 2),
            "quantity": quantity,
            "price": price,
            "fees": fees,
        }


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


async def _list_trades(
    db: AsyncSession,
    portfolio_id: str,
    trade_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List all trades for a portfolio with optional filter and pagination."""
    # Build count query
    count_q = select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    if trade_type and trade_type != "ALL":
        count_q = count_q.where(
            Transaction.transaction_type == TransactionType(trade_type.lower())
        )
    count_result = await db.execute(count_q)
    total = len(count_result.scalars().all())

    # Build paginated query
    query = select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    if trade_type and trade_type != "ALL":
        query = query.where(
            Transaction.transaction_type == TransactionType(trade_type.lower())
        )
    offset = (page - 1) * page_size
    query = (
        query
        .order_by(Transaction.transaction_date.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    transactions = result.scalars().all()

    out = []
    for tx in transactions:
        out.append({
            "id": str(tx.id),
            "portfolio_id": str(tx.portfolio_id),
            "asset_id": str(tx.asset_id),
            "type": tx.transaction_type.value if hasattr(tx.transaction_type, 'value') else str(tx.transaction_type),
            "date": str(tx.transaction_date),
            "quantity": float(tx.quantity),
            "price": float(tx.price),
            "fees": float(tx.fees),
            "notes": tx.notes,
        })

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "trades": out,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


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
            # Calculate P&L from transaction data since p_and_l is not stored
            # For sells we compute from position avg cost
            pass  # P&L computed dynamically in summary

    return {
        "total_trades": len(transactions),
        "total_buys": total_buys,
        "total_sells": total_sells,
        "realized_gain": round(realized_gain, 2),
        "realized_loss": round(realized_loss, 2),
        "net_realized_p_and_l": round(net_realized_pnl, 2),
    }


async def _get_position_for_asset(
    db: AsyncSession,
    portfolio_id: str,
    asset_id: str,
) -> dict | None:
    """Get position details for a specific asset in a portfolio."""
    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset_id,
        )
    )
    position = result.scalar_one_or_none()

    if position is None:
        return None

    quantity = float(position.quantity) if position.quantity else 0
    avg_cost = float(position.avg_cost_basis) if position.avg_cost_basis else 0
    current_price = float(position.current_price) if position.current_price else 0

    market_value = quantity * current_price
    cost_basis = quantity * avg_cost
    unrealized_gain = market_value - cost_basis
    unrealized_gain_pct = (unrealized_gain / cost_basis * 100) if cost_basis != 0 else 0

    return {
        "asset_id": str(position.asset_id),
        "quantity": quantity,
        "avg_cost_basis": avg_cost,
        "current_price": current_price,
        "market_value": round(market_value, 2),
        "cost_basis": round(cost_basis, 2),
        "unrealized_gain": round(unrealized_gain, 2),
        "unrealized_gain_pct": round(unrealized_gain_pct, 2),
    }


async def _get_portfolio_available_cash(db: AsyncSession, portfolio_id: str) -> float:
    """Estimate available cash from realized gains and deposits."""
    result = await db.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    )
    transactions = result.scalars().all()

    cash = 0.0
    for tx in transactions:
        if tx.transaction_type == TransactionType.SELL:
            cash += float(tx.quantity) * float(tx.price) - float(tx.fees)
        elif tx.transaction_type == TransactionType.DEPOSIT:
            cash += float(tx.quantity)
        elif tx.transaction_type == TransactionType.WITHDRAWAL:
            cash -= float(tx.quantity)
        elif tx.transaction_type == TransactionType.DIVIDEND:
            cash += float(tx.quantity) * float(tx.price) - float(tx.fees)
        elif tx.transaction_type == TransactionType.INTEREST:
            cash += float(tx.quantity) * float(tx.price) - float(tx.fees)
        elif tx.transaction_type == TransactionType.FEE:
            cash -= float(tx.fees)

    return round(cash, 2)


async def _calculate_sell_preview(
    db: AsyncSession,
    portfolio_id: str,
    asset_id: str,
    quantity: float,
    price: float,
    fees: float = 0,
) -> dict:
    """Calculate sell P&L preview without committing."""
    errors = []

    # Validate inputs
    if quantity <= 0:
        errors.append("Quantity must be positive")
    if price <= 0:
        errors.append("Price must be positive")

    # Get position
    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset_id,
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        errors.append("No position found for this asset")
        return {
            "valid": False,
            "errors": errors,
            "position": None,
            "projected_pnl": 0,
            "proceeds": 0,
            "cost_of_sold": 0,
            "remaining_quantity": 0,
        }

    current_qty = float(position.quantity) if position.quantity else 0
    avg_cost = float(position.avg_cost_basis) if position.avg_cost_basis else 0

    if quantity > current_qty:
        errors.append(
            f"Cannot sell {quantity} shares. Current position: {current_qty} shares"
        )

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "position": {
                "asset_id": str(position.asset_id),
                "quantity": current_qty,
                "avg_cost_basis": avg_cost,
                "current_price": float(position.current_price) if position.current_price else 0,
            },
            "projected_pnl": 0,
            "proceeds": 0,
            "cost_of_sold": 0,
            "remaining_quantity": current_qty,
        }

    cost_of_sold = avg_cost * quantity
    proceeds = price * quantity
    realized_pnl = proceeds - cost_of_sold - fees
    remaining_qty = current_qty - quantity

    return {
        "valid": True,
        "errors": [],
        "position": {
            "asset_id": str(position.asset_id),
            "quantity": current_qty,
            "avg_cost_basis": avg_cost,
            "current_price": float(position.current_price) if position.current_price else 0,
        },
        "projected_pnl": round(realized_pnl, 2),
        "proceeds": round(proceeds, 2),
        "cost_of_sold": round(cost_of_sold, 2),
        "remaining_quantity": remaining_qty,
    }
