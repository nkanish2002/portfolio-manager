"""SQLModel model registry.

All table models are imported here so SQLAlchemy's declarative system
can discover them. This module is the single entry point for model imports.
"""

from portfolio_manager.models.user import User

# SQLModel table models (import order matters for relationship resolution)
from portfolio_manager.models.asset import Asset, AssetCreate, AssetRead, AssetUpdate
from portfolio_manager.models.account import Account, AccountCreate, AccountRead, AccountUpdate
from portfolio_manager.models.basket import Basket, BasketCreate, BasketRead, BasketUpdate
from portfolio_manager.models.portfolio import Portfolio, PortfolioCreate, PortfolioRead, PortfolioUpdate

__all__ = [
    # Core ORM models
    "User",
    "Asset",
    "Account",
    "Basket",
    "Portfolio",
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
]
