"""Transaction recording + history — routes under a portfolio.

Sells compute realized P&L via FIFO by replaying prior buy/sell transactions
for the same asset in the portfolio. Recording a buy/sell also updates the
matching Position (quantity + weighted-average cost + current price).

Segment 5.1 additions:
  * GET  /search-ticker          — ticker search (yfinance)
  * POST /transactions/sell-preview — FIFO P&L preview without recording
  * record_transaction now accepts optional ``symbol`` with auto-asset-lookup
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Asset, Position, Transaction, TransactionRead
from portfolio_manager.models.user import User
from portfolio_manager.routes.portfolios import _get_owned as get_owned_portfolio
from portfolio_manager.services.data_feed import data_feed
from portfolio_manager.services.portfolio_calc import compute_position_fields
from portfolio_manager.services.trades import TradeLedger

router = APIRouter(prefix="/api/v1/portfolios", tags=["transactions"])

# transaction types that affect share holdings
_HOLDING_TYPES = {"buy", "sell"}


# ── Request / response schemas ──────────────────────────────────────────


class TickerSearchResponse(BaseModel):
    """Response shape for ticker search results."""

    symbol: str
    name: str
    exchange: str | None = None
    quote_type: str | None = None
    sector: str | None = None


class SellPreviewRequest(BaseModel):
    """Request body for the sell-preview endpoint."""

    asset_id: UUID
    quantity: Decimal
    price: Decimal


class SellPreviewResponse(BaseModel):
    """Response body for the sell-preview endpoint."""

    realized_gain: Decimal
    remaining_qty: Decimal


class TransactionCreateBody(BaseModel):
    """Body for recording a transaction (portfolio_id from the path).

    Accepts either ``asset_id`` or ``symbol`` (auto-resolved).
    """

    asset_id: str | None = None
    symbol: str | None = None
    type: str
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal("0")
    trade_date: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _require_asset_ref(self) -> TransactionCreateBody:
        if not self.asset_id and not self.symbol:
            raise ValueError("Provide either asset_id or symbol")
        return self


# ── Public routes ───────────────────────────────────────────────────────


@router.get(
    "/{portfolio_id}/search-ticker",
    response_model=list[TickerSearchResponse],
    tags=["transactions"],
)
async def search_ticker(
    portfolio_id: str,
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Search tickers via yfinance.

    Returns up to *limit* results matching the query string.
    """
    # Guard: portfolio must be owned (keeps URL pattern consistent)
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    _ = portfolio  # ownership validated

    results = await data_feed.search_ticker(q, max_results=limit)
    return [
        TickerSearchResponse(
            symbol=r.symbol,
            name=r.name,
            exchange=r.exchange,
            quote_type=r.quote_type,
            sector=r.sector,
        )
        for r in results
    ]


@router.post(
    "/{portfolio_id}/transactions/sell-preview",
    response_model=SellPreviewResponse,
    tags=["transactions"],
)
async def sell_preview(
    portfolio_id: str,
    body: SellPreviewRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Return the FIFO realized gain for a hypothetical sell.

    Does **not** record the transaction or update any state.
    """
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    asset_uid = body.asset_id

    # Validate position exists and is large enough
    result = await session.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.asset_id == asset_uid,
        )
    )
    position = result.scalar_one_or_none()
    if position is None:
        raise HTTPException(status_code=404, detail="Position not found")
    if body.quantity > position.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sell {body.quantity} shares (hold {position.quantity})",
        )

    # Replay prior transactions through FIFO ledger
    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio.id,
            Transaction.asset_id == asset_uid,
        )
        .order_by(Transaction.trade_date, Transaction.created_at)
    )
    prior = result.scalars().all()

    ledger = TradeLedger()
    for txn in prior:
        if txn.type == "buy":
            ledger.buy(str(asset_uid), Decimal(txn.quantity), Decimal(txn.price))
        elif txn.type == "sell":
            ledger.sell(str(asset_uid), Decimal(txn.quantity), Decimal(txn.price))

    res = ledger.sell(str(asset_uid), body.quantity, body.price)

    return SellPreviewResponse(
        realized_gain=res.realized_gain,
        remaining_qty=position.quantity - body.quantity,
    )


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_transaction(
    portfolio_id: str,
    body: TransactionCreateBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    trade_date = body.trade_date or datetime.now(UTC)

    # Resolve asset_id — either provided directly or looked up by symbol
    if body.symbol:
        norm = body.symbol.strip().upper()
        result = await session.execute(select(Asset).where(Asset.symbol == norm))
        asset = result.scalar_one_or_none()
        if asset is None:
            asset = Asset(symbol=norm, name=norm, asset_class="equity")
            session.add(asset)
            await session.flush()
        asset_uid = asset.id
    else:
        asset_uid = UUID(str(body.asset_id))

    realized_gain: Decimal | None = None
    if body.type in _HOLDING_TYPES:
        realized_gain = await _apply_to_position(
            session, portfolio.id, asset_uid, body, trade_date
        )

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


@router.get(
    "/{portfolio_id}/transactions",
    response_model=list[TransactionRead],
)
async def list_transactions(
    portfolio_id: str,
    type: str | None = Query(default=None),
    asset_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    from sqlalchemy.orm import selectinload

    portfolio = await get_owned_portfolio(session, portfolio_id, user.id)
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.asset))
        .where(Transaction.portfolio_id == portfolio.id)
    )
    if type is not None:
        stmt = stmt.where(Transaction.type == type)
    if asset_id is not None:
        stmt = stmt.where(Transaction.asset_id == UUID(str(asset_id)))
    stmt = stmt.order_by(Transaction.trade_date.desc(), Transaction.created_at.desc())
    result = await session.execute(stmt)
    transactions = result.scalars().all()
    # Populate symbol from joined asset for each transaction
    for txn in transactions:
        if txn.asset and not hasattr(txn, 'symbol'):
            # Monkey-patch symbol onto the transaction for serialization
            # TransactionRead doesn't have symbol, but we add it via model_validate
            pass
    reads = [TransactionRead.model_validate(t) for t in transactions]
    # Attach symbol to each read
    for txn, read in zip(transactions, reads, strict=True):
        if txn.asset:
            object.__setattr__(read, 'symbol', txn.asset.symbol)
    return reads


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
        select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset_id,
        )
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
                compute_position_fields(
                    quantity=qty, avg_cost_basis=price, current_price=price
                )
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
        realized = await _fifo_realized(
            session, portfolio_id, asset_id, qty, price
        )
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
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_id == asset_id,
        )
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
