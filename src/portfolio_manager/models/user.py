"""User model extending fastapi-users SQLAlchemy base.

fastapi-users 15.x uses SQLAlchemy 2.0 Mapped columns via fastapi_users_db_sqlalchemy.
This model inherits from SQLAlchemyBaseUserTableUUID for the core user fields,
then mixes in our shared Base (from database.py) so it shares the same SQLAlchemy
registry as all SQLModel models. This ensures Alembic sees all tables in one migration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_manager.database import Base

if TYPE_CHECKING:
    from portfolio_manager.models.account import Account
    from portfolio_manager.models.basket import Basket
    from portfolio_manager.models.portfolio import Portfolio


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model — extends fastapi-users base with display name + relationships."""

    __tablename__ = "users"

    # Extended fields beyond BaseUser
    display_name: Mapped[str | None] = mapped_column(String(100), default=None)

    # Relationships (lazy load by default)
    accounts: Mapped[list[Account]] = relationship(back_populates="user")
    baskets: Mapped[list[Basket]] = relationship(back_populates="user")
    portfolios: Mapped[list[Portfolio]] = relationship(back_populates="user")
