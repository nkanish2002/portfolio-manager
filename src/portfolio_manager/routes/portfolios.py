"""Portfolio CRUD API with CUSIP support."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.database import get_db
from portfolio_manager.models.asset import Asset, AssetClass
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position
from portfolio_manager.models.transaction import Transaction, TransactionType
from portfolio_manager.services.data_feed import get_price

logger = structlog.getLogger(__name__)
router = APIRouter(prefix="/portfolios", tags=["portfolios"])


async def _portfolio_stats(db: AsyncSession, portfolio_id: str) -> dict:
    """Compute position_count and total_value for a portfolio."""
    from sqlalchemy import func as sql_func

    pos_count_result = await db.execute(
        select(sql_func.count(Position.id)).where(Position.portfolio_id == portfolio_id)
    )
    pos_count = pos_count_result.scalar_one() or 0

    # total_value = sum(quantity * current_price) for all positions
    pos_val_result = await db.execute(
        select(
            sql_func.sum(Position.quantity * sql_func.coalesce(Position.current_price, 0))
        ).where(Position.portfolio_id == portfolio_id)
    )
    total_value = round(float(pos_val_result.scalar_one() or 0), 2)

    return {"position_count": pos_count, "total_value": total_value}


# --- Pydantic schemas ---


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    currency: str = "USD"


class PortfolioResponse(BaseModel):
    id: str
    name: str
    description: str | None
    currency: str
    position_count: int = 0
    total_value: float = 0.0

    model_config = {"from_attributes": True}


class PositionCreate(BaseModel):
    cusip: str | None = Field(
        None, description="CUSIP identifier (optional, will be fetched from symbol if missing)"
    )
    symbol: str | None = None
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    name: str | None = None
    notes: str | None = None
    asset_class: str = "equity"

    @model_validator(mode="after")
    def normalize(self):
        if self.symbol:
            self.symbol = self.symbol.upper()
        if self.cusip:
            self.cusip = self.cusip.upper().replace("-", "")
        return self


class PositionResponse(BaseModel):
    id: str
    cusip: str
    symbol: str
    name: str
    quantity: float
    price: float
    cost_basis: float
    market_value: float
    gain: float
    gain_pct: float

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    cusip: str | None = Field(
        None, description="CUSIP identifier (optional, will be fetched from symbol if missing)"
    )
    symbol: str | None = None
    transaction_type: TransactionType
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fees: float = 0
    notes: str | None = None


class SellRequest(BaseModel):
    """Sell position request."""

    cusip: str | None = Field(
        None,
        description="CUSIP of security to sell (optional, will be fetched from symbol if missing)",
    )
    symbol: str | None = None
    quantity: float = Field(..., gt=0, description="Quantity to sell")
    price: float = Field(..., gt=0, description="Sell price per share")
    fees: float = 0
    notes: str | None = None


async def _find_or_create_asset(
    db: AsyncSession,
    cusip: str | None,
    symbol: str | None = None,
    name: str | None = None,
    asset_class: str = "equity",
) -> Asset:
    """Look up asset by CUSIP first, then symbol. Create if not found."""
    if cusip:
        cusip_clean = cusip.upper().replace("-", "")
    else:
        cusip_clean = None

    # Try CUSIP first
    if cusip_clean:
        asset_result = await db.execute(select(Asset).where(Asset.cusip == cusip_clean))
        asset = asset_result.scalars().first()

        if not asset and symbol:
            # Try symbol
            symbol_upper = symbol.upper()
            asset_result = await db.execute(select(Asset).where(Asset.symbol == symbol_upper))
            asset = asset_result.scalars().first()
    elif symbol:
        # Only symbol provided, look up by symbol
        symbol_upper = symbol.upper()
        asset_result = await db.execute(select(Asset).where(Asset.symbol == symbol_upper))
        asset = asset_result.scalars().first()
    else:
        # Neither CUSIP nor symbol provided
        raise ValueError("Either 'cusip' or 'symbol' must be provided")

    if not asset:
        # Create new asset
        asset = Asset(
            cusip=cusip_clean,
            symbol=symbol.upper() if symbol else None,
            name=name or (symbol.upper() if symbol else cusip_clean or "Unknown"),
            asset_class=AssetClass(asset_class.lower()),
        )
        db.add(asset)
        await db.flush()

    return asset


# --- Endpoints ---


@router.get("/", response_model=list[PortfolioResponse])
async def list_portfolios(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Portfolio).order_by(Portfolio.created_at.desc()))
    portfolios = result.scalars().all()

    portfolio_responses = []
    for p in portfolios:
        stats = await _portfolio_stats(db, str(p.id))
        portfolio_responses.append(
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "currency": p.currency,
                "position_count": stats["position_count"],
                "total_value": stats["total_value"],
            }
        )
    return portfolio_responses


@router.post("/", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(data: PortfolioCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # Check for duplicate name
    existing = await db.execute(select(Portfolio).where(Portfolio.name == data.name))
    if existing.scalar_one_or_none():
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail=f"Portfolio '{data.name}' already exists")

    portfolio = Portfolio(name=data.name, description=data.description, currency=data.currency)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "description": portfolio.description,
        "currency": portfolio.currency,
        "position_count": 0,
        "total_value": 0.0,
    }


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Portfolio not found")
    stats = await _portfolio_stats(db, portfolio_id)
    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "description": portfolio.description,
        "currency": portfolio.currency,
        "position_count": stats["position_count"],
        "total_value": stats["total_value"],
    }


@router.delete("/{portfolio_id}", status_code=204)
async def delete_portfolio(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Portfolio not found")
    await db.delete(portfolio)
    await db.commit()


@router.post("/{portfolio_id}/positions", response_model=PositionResponse, status_code=201)
async def add_position(
    portfolio_id: str, data: PositionCreate, db: Annotated[AsyncSession, Depends(get_db)]
):
    """Add or update a position in a portfolio."""
    from datetime import date

    from sqlalchemy.orm import selectinload

    # Ensure portfolio exists
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Find or create asset
    asset = await _find_or_create_asset(db, data.cusip, data.symbol, data.name, data.asset_class)

    # Check for existing position
    pos_result = await db.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset.id,
        )
    )
    position = pos_result.scalar_one_or_none()

    if position:
        # Update existing — record buy transaction for additional quantity
        old_qty = float(position.quantity)
        old_cost = float(position.avg_cost_basis) * old_qty
        new_qty = old_qty + float(data.quantity)
        position.avg_cost_basis = (
            (old_cost + float(data.quantity) * float(data.price)) / new_qty if new_qty > 0 else 0
        )
        position.quantity = new_qty
        position.current_price = float(data.price)

        # Record buy transaction
        buy_transaction = Transaction(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            transaction_date=date.today(),
            quantity=data.quantity,
            price=data.price,
            fees=0,
        )
        db.add(buy_transaction)
    else:
        # Create new position and buy transaction
        position = Position(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            quantity=data.quantity,
            avg_cost_basis=data.price,
            current_price=data.price,
        )
        db.add(position)

        buy_transaction = Transaction(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            transaction_date=date.today(),
            quantity=data.quantity,
            price=data.price,
            fees=0,
        )
        db.add(buy_transaction)

    await db.commit()
    await db.refresh(position, {"asset"})
    market_val = float(position.quantity) * float(position.current_price or 0)
    cost = float(position.quantity) * float(position.avg_cost_basis)
    gain = market_val - cost
    gain_pct = (gain / cost * 100) if cost > 0 else 0

    return {
        "id": str(position.id),
        "cusip": asset.cusip or "",
        "symbol": asset.symbol or "",
        "name": asset.name or "",
        "quantity": float(position.quantity),
        "price": float(position.current_price or 0),
        "cost_basis": float(position.avg_cost_basis),
        "market_value": round(market_val, 2),
        "gain": round(gain, 2),
        "gain_pct": round(gain_pct, 2),
    }


@router.get("/{portfolio_id}/positions", response_model=list[PositionResponse])
async def list_positions(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """List all positions in a portfolio."""
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(Position.portfolio_id == portfolio_id)
    )
    positions = result.scalars().all()

    out = []
    for pos in positions:
        market_val = float(pos.quantity) * float(pos.current_price or 0)
        cost = float(pos.quantity) * float(pos.avg_cost_basis)
        gain = market_val - cost
        gain_pct = (gain / cost * 100) if cost > 0 else 0
        out.append(
            {
                "id": str(pos.id),
                "cusip": pos.asset.cusip or "",
                "symbol": pos.asset.symbol or "",
                "name": pos.asset.name or "",
                "quantity": float(pos.quantity),
                "price": float(pos.current_price or 0),
                "cost_basis": float(pos.avg_cost_basis),
                "market_value": round(market_val, 2),
                "gain": round(gain, 2),
                "gain_pct": round(gain_pct, 2),
            }
        )
    return out


@router.post("/{portfolio_id}/transactions", response_model=dict, status_code=201)
async def add_transaction(
    portfolio_id: str, data: TransactionCreate, db: Annotated[AsyncSession, Depends(get_db)]
):
    """Record a trade transaction."""
    # Find or create asset (use default asset_class 'equity', not transaction_type)
    asset = await _find_or_create_asset(db, data.cusip, data.symbol)

    from datetime import date

    transaction = Transaction(
        portfolio_id=portfolio_id,
        asset_id=asset.id,
        transaction_type=data.transaction_type,
        transaction_date=date.today(),
        quantity=data.quantity,
        price=data.price,
        fees=data.fees,
        notes=data.notes,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    return {"id": str(transaction.id), "status": "recorded"}


@router.post("/{portfolio_id}/positions/sell", response_model=dict, status_code=201)
async def sell_position(
    portfolio_id: str,
    data: SellRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Sell a quantity of an existing position (partial or full).

    Uses weighted average cost basis for P&L calculation.
    """
    from datetime import date

    from fastapi import HTTPException
    from sqlalchemy.orm import selectinload

    # Handle both CUSIP and symbol
    if data.cusip:
        cusip_clean = data.cusip.upper().replace("-", "")
    else:
        cusip_clean = None

    # Ensure portfolio exists
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Find asset by CUSIP or symbol
    asset = None
    if cusip_clean:
        asset_result = await db.execute(select(Asset).where(Asset.cusip == cusip_clean))
        asset = asset_result.scalar_one_or_none()

    if not asset and data.symbol:
        asset_result = await db.execute(select(Asset).where(Asset.symbol == data.symbol.upper()))
        asset = asset_result.scalar_one_or_none()

    if not asset:
        cusip_str = data.cusip or "N/A"
        symbol_str = data.symbol or "N/A"
        detail = f"Asset not found for CUSIP: {cusip_str}, symbol: {symbol_str}"
        raise HTTPException(status_code=404, detail=detail)

    # Find the position to sell
    pos_result = await db.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset.id,
        )
    )
    position = pos_result.scalar_one_or_none()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    # Validate quantity
    qty_to_sell = float(data.quantity)
    current_qty = float(position.quantity)

    if qty_to_sell <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    if qty_to_sell > current_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sell {qty_to_sell} shares. Current position: {current_qty} shares",
        )

    # Calculate realized P&L using weighted average cost
    avg_cost = float(position.avg_cost_basis) if position.avg_cost_basis else 0
    sell_price = float(data.price)
    cost_of_sold = avg_cost * qty_to_sell
    proceeds = sell_price * qty_to_sell
    realized_pnl = proceeds - cost_of_sold - float(data.fees)

    # Update position quantity
    new_qty = current_qty - qty_to_sell
    position.quantity = new_qty

    # If fully liquidated, remove the position
    if new_qty <= 0:
        await db.delete(position)
    # If partially sold, update current price
    else:
        position.current_price = sell_price

    # Record the sell transaction
    sell_transaction = Transaction(
        portfolio_id=portfolio_id,
        asset_id=position.asset_id,
        transaction_type=TransactionType.SELL,
        transaction_date=date.today(),
        quantity=qty_to_sell,
        price=sell_price,
        fees=float(data.fees),
        notes=data.notes,
    )
    db.add(sell_transaction)

    await db.commit()

    return {
        "status": "sold",
        "cusip": asset.cusip,
        "symbol": asset.symbol or "",
        "name": asset.name,
        "quantity_sold": qty_to_sell,
        "price": sell_price,
        "fees": float(data.fees),
        "proceeds": round(proceeds, 2),
        "realized_pnl": round(realized_pnl, 2),
        "remaining_quantity": max(new_qty, 0),
        "avg_cost_basis": avg_cost,
    }


@router.post("/{portfolio_id}/positions/refresh", response_model=list[dict])
async def refresh_prices(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Fetch latest prices for all positions in a portfolio."""
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(Position.portfolio_id == portfolio_id)
    )
    positions = result.scalars().all()

    for pos in positions:
        # Get asset symbol
        if pos.asset and pos.asset.asset_class == AssetClass.EQUITY and pos.asset.symbol:
            try:
                price = get_price(pos.asset.symbol)
                if price is not None:
                    pos.current_price = price
            except Exception as e:
                logger.warning("failed_to_fetch_price", symbol=pos.asset.symbol, error=str(e))

    await db.commit()

    result = await db.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(Position.portfolio_id == portfolio_id)
    )
    positions = result.scalars().all()
    out = []
    for pos in positions:
        market_val = float(pos.quantity) * float(pos.current_price or 0)
        cost = float(pos.quantity) * float(pos.avg_cost_basis)
        gain = market_val - cost
        gain_pct = (gain / cost * 100) if cost > 0 else 0
        out.append(
            {
                "id": str(pos.id),
                "cusip": pos.asset.cusip or "",
                "symbol": pos.asset.symbol or "",
                "name": pos.asset.name or "",
                "quantity": float(pos.quantity),
                "price": float(pos.current_price or 0),
                "cost_basis": float(pos.avg_cost_basis),
                "market_value": round(market_val, 2),
                "gain": round(gain, 2),
                "gain_pct": round(gain_pct, 2),
            }
        )
    return out
