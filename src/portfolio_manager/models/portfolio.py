"""Portfolio model — user-scoped.

A portfolio belongs to a user, an account, and is optionally assigned to a basket.
"""


from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from portfolio_manager.database import portfolio_benchmarks


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    user_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    name: str = Field(max_length=100)
    account_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
    )
    basket_id: UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("baskets.id", ondelete="SET NULL"), nullable=True),
    )
    currency: str = Field(default="USD", max_length=3)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )

    # Relationships
    user: User = Relationship(back_populates="portfolios")
    account: Account = Relationship(back_populates="portfolios")
    basket: Basket = Relationship(back_populates="portfolios")
    positions: Mapped[list[Position]] = Relationship(back_populates="portfolio")
    transactions: Mapped[list[Transaction]] = Relationship(back_populates="portfolio")
    benchmarks: Mapped[list[Benchmark]] = Relationship(
        back_populates="portfolios",
        sa_relationship_kwargs={"secondary": portfolio_benchmarks},
    )


# ── Pydantic schemas (no table) ─────────────────────────────────────────


class PortfolioCreate(SQLModel):
    """Schema for creating a new portfolio."""

    name: str = Field(max_length=100)
    account_id: UUID
    basket_id: UUID | None = None
    currency: str = Field(default="USD", max_length=3)


class PortfolioUpdate(SQLModel):
    """Schema for updating a portfolio."""

    name: str | None = None
    basket_id: UUID | None = None
    currency: str | None = None


class PortfolioRead(SQLModel, table=False):
    """Schema for reading a portfolio."""

    id: UUID
    user_id: UUID
    name: str
    account_id: UUID
    basket_id: UUID | None = None
    currency: str
    created_at: datetime
    updated_at: datetime
