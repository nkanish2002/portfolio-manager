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
    cusip: str
    symbol: str
    name: str
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
    """Calculate realized P&L for a sell using FIFO with cumulative lot tracking.

    Processes ALL transactions for the symbol chronologically, tracking
    how many shares have been consumed by prior sells. This ensures that
    if you buy 10 shares, sell 5, then sell 5 again, each sell matches
    against the correct remaining lots.
    """
    if sell_tx.transaction_type != TransactionType.SELL:
        return 0.0

    fees = float(sell_tx.fees or 0)
    sell_price = float(sell_tx.price)
    sell_qty = float(sell_tx.quantity)

    # Collect all transactions for this symbol, sorted chronologically
    symbol_txns = [
        t for t in all_transactions
        if t.asset and t.asset.symbol == symbol and t.transaction_type in (TransactionType.BUY, TransactionType.SELL)
    ]
    symbol_txns.sort(key=lambda t: t.transaction_date or date.min)

    # Build a lookup: transaction_id -> shares consumed by that sell
    # Process all sells in order, tracking cumulative consumption
    cumulative_consumed = 0.0  # total shares sold so far (across ALL sells for this symbol)

    # Pre-pass: calculate how much was consumed BEFORE this specific sell
    for t in symbol_txns:
        if t is sell_tx:
            break  # stop before processing our target sell
        if t.transaction_type == TransactionType.SELL:
            cumulative_consumed += float(t.quantity)

    # Now match this sell's quantity against buy lots (FIFO), starting from
    # the point after cumulative_consumed shares have already been sold
    buys = [
        t for t in symbol_txns
        if t.transaction_type == TransactionType.BUY
    ]

    # Track how many buy shares have been consumed across ALL sells
    # We need to know what's already been consumed before this sell
    # Build a running map: for each buy, how many shares consumed by sells BEFORE this one
    buy_consumed_map: dict[int, float] = {id(buy): 0.0 for buy in buys}

    # Walk through all transactions before this sell and distribute buy consumption
    for t in symbol_txns:
        if t is sell_tx:
            break
        if t.transaction_type == TransactionType.SELL:
            sell_remaining = float(t.quantity)
            for buy in buys:
                if sell_remaining <= 0:
                    break
                available = float(buy.quantity) - buy_consumed_map[id(buy)]
                if available <= 0:
                    continue
                take = min(sell_remaining, available)
                buy_consumed_map[id(buy)] += take
                sell_remaining -= take

    # Now calculate cost basis for THIS sell using remaining buy shares
    qty_to_match = sell_qty
    cost_basis = 0.0
    for buy in buys:
        if qty_to_match <= 0:
            break
        available = float(buy.quantity) - buy_consumed_map[id(buy)]
        if available <= 0:
            continue
        take = min(qty_to_match, available)
        cost_basis += take * float(buy.price)
        qty_to_match -= take

    if cost_basis > 0:
        return round(sell_price * sell_qty - cost_basis - fees, 2)
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
        asset = t.asset
        sym = asset.symbol or ""
        cusip = asset.cusip or ""
        name = asset.name or "?"

        # Calculate P&L from transaction history
        p_and_l = _calc_pnl_from_history(t, all_txns, sym)

        out.append(TradeResponse(
            id=str(t.id),
            portfolio_id=str(t.portfolio_id),
            cusip=cusip,
            symbol=sym,
            name=name,
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
