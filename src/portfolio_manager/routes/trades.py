"""Trade audit trail — list & filter transactions."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from portfolio_manager.database import get_db
from portfolio_manager.models.asset import Asset
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position
from portfolio_manager.models.transaction import Transaction, TransactionType

router = APIRouter(tags=["trades"])


class TradeResponse(BaseModel):
    """A single trade record."""
    id: str
    portfolio_id: str
    symbol: str
    type: str
    quantity: float
    price: float
    fees: float
    p_and_l: float = 0.0
    notes: str | None = None
    transaction_date: str

    model_config = {"from_attributes": True}


class TradeSummary(BaseModel):
    """Aggregated trade stats."""
    total_trades: int
    total_buys: int
    total_sells: int
    realized_gain: float = 0.0
    realized_loss: float = 0.0
    net_realized_p_and_l: float = 0.0


def _calc_pnl_from_history(
    sell_tx: Transaction,
    all_transactions: list[Transaction],
    symbol: str,
) -> float:
    """Calculate realized P&L for a sell by matching against buy transactions (FIFO)."""
    if sell_tx.transaction_type != TransactionType.SELL:
        return 0.0

    qty_remaining = float(sell_tx.quantity)
    fees = float(sell_tx.fees or 0)
    sell_price = float(sell_tx.price)

    # Collect all BUY transactions for this symbol, sorted oldest first (FIFO)
    buys = sorted(
        [t for t in all_transactions if t.asset and t.asset.symbol == symbol and t.transaction_type == TransactionType.BUY],
        key=lambda t: t.transaction_date,
    )

    cost_basis = 0.0
    for buy in buys:
        if qty_remaining <= 0:
            break
        buy_qty = float(buy.quantity)
        buy_price = float(buy.price)
        take_qty = min(qty_remaining, buy_qty)
        cost_basis += take_qty * buy_price
        qty_remaining -= take_qty
        if take_qty == buy_qty:
            # Fully consumed this buy
            pass
        # If partial, we still keep the remainder for next buy

    if cost_basis > 0 and sell_tx.quantity > 0:
        return round(sell_price * float(sell_tx.quantity) - cost_basis - fees, 2)
    return 0.0


@router.get("/portfolios/{portfolio_id}/trades", response_model=list[TradeResponse])
async def list_trades(
    portfolio_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    symbol: str | None = Query(None, description="Filter by symbol"),
    trade_type: str | None = Query(None, description="Filter by transaction type (buy/sell/dividend)"),
    start_date: date | None = Query(None, description="Start date (inclusive)"),
    end_date: date | None = Query(None, description="End date (inclusive)"),
    sort_by: str = Query("date", description="Sort by: date, symbol, type"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
):
    """List trades for a portfolio with optional filtering."""
    # Verify portfolio exists
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    if not result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Build query with joins
    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.asset),
        )
        .join(Asset, Transaction.asset_id == Asset.id)
        .where(Transaction.portfolio_id == portfolio_id)
    )

    # Apply symbol filter
    if symbol:
        query = query.where(Asset.symbol == symbol.upper())

    # Apply trade_type filter (normalize to lowercase)
    if trade_type:
        try:
            normalized_type = TransactionType(trade_type.lower())
            query = query.where(Transaction.transaction_type == normalized_type)
        except ValueError:
            pass

    # Apply date filters
    if start_date:
        query = query.where(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.where(Transaction.transaction_date <= end_date)

    # Apply sorting
    if sort_by == "date":
        sort_key = Transaction.transaction_date
    elif sort_by == "symbol":
        sort_key = Asset.symbol
    elif sort_by == "type":
        sort_key = Transaction.transaction_type
    else:
        sort_key = Transaction.transaction_date

    if sort_order.lower() == "asc":
        query = query.order_by(sort_key.asc())
    else:
        query = query.order_by(sort_key.desc())

    result = await db.execute(query)
    transactions = result.scalars().all()

    # Fetch ALL transactions for the portfolio to calculate P&L from history (FIFO)
    all_txns_result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.asset))
        .where(Transaction.portfolio_id == portfolio_id)
    )
    all_txns = all_txns_result.scalars().all()

    # Convert to response objects using FIFO P&L calculation
    out = []
    for t in transactions:
        sym = t.asset.symbol if t.asset else "?"

        # Calculate P&L from transaction history
        p_and_l = _calc_pnl_from_history(t, all_txns, sym)

        out.append(TradeResponse(
            id=str(t.id),
            portfolio_id=str(t.portfolio_id),
            symbol=sym,
            type=t.transaction_type.value.upper(),
            quantity=float(t.quantity),
            price=float(t.price),
            fees=float(t.fees or 0),
            p_and_l=p_and_l,
            notes=t.notes,
            transaction_date=t.transaction_date.isoformat() if t.transaction_date else "",
        ))

    return out


@router.get("/portfolios/{portfolio_id}/trades/summary", response_model=TradeSummary)
async def trade_summary(
    portfolio_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get aggregated trade statistics for a portfolio."""
    # Verify portfolio exists
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    if not result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Fetch all transactions with assets
    all_result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.asset))
        .where(Transaction.portfolio_id == portfolio_id)
    )
    all_transactions = all_result.scalars().all()

    total_buys = sum(1 for t in all_transactions if t.transaction_type == TransactionType.BUY)
    total_sells = sum(1 for t in all_transactions if t.transaction_type == TransactionType.SELL)
    realized_gain = 0.0
    realized_loss = 0.0

    # Calculate P&L for each SELL using FIFO from transaction history
    for t in all_transactions:
        if t.transaction_type == TransactionType.SELL and t.asset:
            pnl = _calc_pnl_from_history(t, all_transactions, t.asset.symbol)
            if pnl > 0:
                realized_gain += pnl
            else:
                realized_loss += abs(pnl)  # Store magnitude

    return TradeSummary(
        total_trades=len(all_transactions),
        total_buys=total_buys,
        total_sells=total_sells,
        realized_gain=round(realized_gain, 2),
        realized_loss=round(realized_loss, 2),
        net_realized_p_and_l=round(realized_gain - realized_loss, 2),
    )
