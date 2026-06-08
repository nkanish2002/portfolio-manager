"""Portfolio CRUD API."""

from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.database import async_session, get_db
from portfolio_manager.models.asset import Asset, AssetClass
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position
from portfolio_manager.models.transaction import Transaction, TransactionType
from portfolio_manager.services.data_feed import get_price

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


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
    symbol: str
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    notes: str | None = None


class PositionResponse(BaseModel):
    id: str
    symbol: str
    quantity: float
    price: float
    cost_basis: float
    market_value: float
    gain: float
    gain_pct: float

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    symbol: str
    transaction_type: TransactionType
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fees: float = 0
    notes: str | None = None


# --- Endpoints ---

@router.get("/", response_model=list[PortfolioResponse])
async def list_portfolios(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Portfolio).order_by(Portfolio.created_at.desc()))
    portfolios = result.scalars().all()
    # Convert ORM objects to dicts to avoid Pydantic from_attributes issues
    return [{"id": str(p.id), "name": p.name, "description": p.description,
             "currency": p.currency, "position_count": 0, "total_value": 0.0}
            for p in portfolios]


@router.post("/", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(data: PortfolioCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    portfolio = Portfolio(name=data.name, description=data.description, currency=data.currency)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return {"id": str(portfolio.id), "name": portfolio.name,
            "description": portfolio.description, "currency": portfolio.currency,
            "position_count": 0, "total_value": 0.0}


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(portfolio_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {"id": str(portfolio.id), "name": portfolio.name,
            "description": portfolio.description, "currency": portfolio.currency,
            "position_count": 0, "total_value": 0.0}


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
async def add_position(portfolio_id: str, data: PositionCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """Add or update a position in a portfolio."""
    from sqlalchemy.orm import selectinload

    # Ensure portfolio exists
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Upsert asset
    asset_result = await db.execute(select(Asset).where(Asset.symbol == data.symbol.upper()))
    asset = asset_result.scalar_one_or_none()
    if not asset:
        asset = Asset(
            symbol=data.symbol.upper(),
            name=data.symbol.upper(),
            asset_class=AssetClass.EQUITY,
        )
        db.add(asset)
        await db.flush()

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
        # Update existing
        old_qty = position.quantity
        old_cost = position.avg_cost_basis * old_qty
        new_qty = old_qty + data.quantity
        position.avg_cost_basis = (old_cost + data.quantity * data.price) / new_qty if new_qty > 0 else 0
        position.quantity = new_qty
        position.current_price = data.price
    else:
        # Create new
        position = Position(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            quantity=data.quantity,
            avg_cost_basis=data.price,
            current_price=data.price,
        )
        db.add(position)

    await db.commit()
    await db.refresh(position, {"asset"})
    market_val = float(position.quantity) * float(position.current_price or 0)
    cost = float(position.quantity) * float(position.avg_cost_basis)
    gain = market_val - cost
    gain_pct = (gain / cost * 100) if cost > 0 else 0
    return {"id": str(position.id), "symbol": position.asset.symbol if position.asset else "?",
            "quantity": float(position.quantity), "price": float(position.current_price or 0),
            "cost_basis": float(position.avg_cost_basis), "market_value": round(market_val, 2),
            "gain": round(gain, 2), "gain_pct": round(gain_pct, 2)}


@router.post("/{portfolio_id}/transactions", response_model=dict, status_code=201)
async def add_transaction(portfolio_id: str, data: TransactionCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """Record a trade transaction."""
    # Upsert asset
    asset_result = await db.execute(select(Asset).where(Asset.symbol == data.symbol.upper()))
    asset = asset_result.scalar_one_or_none()
    if not asset:
        asset = Asset(
            symbol=data.symbol.upper(),
            name=data.symbol.upper(),
            asset_class=AssetClass.EQUITY,
        )
        db.add(asset)
        await db.flush()

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


@router.get("/{portfolio_id}/positions/refresh", response_model=list[dict])
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
        if pos.asset and pos.asset.asset_class == AssetClass.EQUITY:
            price = get_price(pos.asset.symbol)
            if price is not None:
                pos.current_price = price

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
        out.append({
            "id": str(pos.id), "symbol": pos.asset.symbol if pos.asset else "?",
            "quantity": float(pos.quantity), "price": float(pos.current_price or 0),
            "cost_basis": float(pos.avg_cost_basis), "market_value": round(market_val, 2),
            "gain": round(gain, 2), "gain_pct": round(gain_pct, 2),
        })
    return out
