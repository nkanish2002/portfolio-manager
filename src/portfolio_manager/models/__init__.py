"""SQLModel model registry.

All table models are imported here so SQLAlchemy's declarative system
can discover them. This module is the single entry point for model imports.

Import order matters:
  1. User (SQLAlchemy, depends on nothing)
  2. Asset (shared lookup, no user_id)
  3. Account, Basket (user-scoped)
  4. Portfolio (depends on Account + Basket)
  5. Position, Transaction (depend on Portfolio + Asset)
  6. Benchmark, BenchmarkData (shared, with m2m to Portfolio)
"""

from portfolio_manager.models.account import Account, AccountCreate, AccountRead, AccountUpdate

# Core SQLModel table models
from portfolio_manager.models.asset import Asset, AssetCreate, AssetRead, AssetUpdate
from portfolio_manager.models.basket import Basket, BasketCreate, BasketRead, BasketUpdate
from portfolio_manager.models.benchmark import (
    Benchmark,
    BenchmarkCreate,
    BenchmarkData,
    BenchmarkDataRead,
    BenchmarkRead,
    portfolio_benchmarks,
)
from portfolio_manager.models.portfolio import Portfolio, PortfolioCreate, PortfolioRead, PortfolioUpdate

# Holdings + benchmarks
from portfolio_manager.models.position import Position, PositionCreate, PositionRead, PositionUpdate
from portfolio_manager.models.transaction import Transaction, TransactionCreate, TransactionRead
from portfolio_manager.models.user import User

__all__ = [
    # Core ORM models
    "User",
    "Asset",
    "Account",
    "Basket",
    "Portfolio",
    "Position",
    "Transaction",
    "Benchmark",
    "BenchmarkData",
    "portfolio_benchmarks",
    # Asset schemas
    "AssetCreate",
    "AssetRead",
    "AssetUpdate",
    # Account schemas
    "AccountCreate",
    "AccountRead",
    "AccountUpdate",
    # Basket schemas
    "BasketCreate",
    "BasketRead",
    "BasketUpdate",
    # Portfolio schemas
    "PortfolioCreate",
    "PortfolioRead",
    "PortfolioUpdate",
    # Position schemas
    "PositionCreate",
    "PositionRead",
    "PositionUpdate",
    # Transaction schemas
    "TransactionCreate",
    "TransactionRead",
    # Benchmark schemas
    "BenchmarkCreate",
    "BenchmarkRead",
    "BenchmarkDataRead",
]
