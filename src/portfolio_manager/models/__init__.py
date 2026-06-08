"""Models package — imports all models so they register with SQLAlchemy Base.metadata."""

from portfolio_manager.database import Base  # noqa: F401 -- registers models
from portfolio_manager.models.base import TimestampMixin, UuidMixin
from portfolio_manager.models.asset import Asset, AssetClass
from portfolio_manager.models.benchmark import (
    Benchmark,
    BenchmarkData,
    BenchmarkPortfolioAssociation,
)
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.position import Position
from portfolio_manager.models.transaction import Transaction, TransactionType

__all__ = [
    "Asset",
    "AssetClass",
    "Benchmark",
    "BenchmarkData",
    "BenchmarkPortfolioAssociation",
    "Base",
    "Portfolio",
    "Position",
    "TimestampMixin",
    "Transaction",
    "TransactionType",
    "UuidMixin",
]
