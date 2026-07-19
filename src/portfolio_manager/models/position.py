"""Position model — user-scoped via portfolio.

A position is the current holding of a specific asset in a portfolio.
Computed fields (market_value, unrealized_gain, unrealized_gain_pct) are updated
on price refresh.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel


class Position(SQLModel, table=True):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_id", name="uq_portfolio_asset"),
    )

    id: UUID = Field(default_factory=uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    portfolio_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
    )
    asset_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False),
    )
    quantity: float = Field(sa_column=Column(Numeric(18, 6)), ge=0)
    avg_cost_basis: float = Field(sa_column=Column(Numeric(18, 6)), ge=0)
    current_price: float = Field(sa_column=Column(Numeric(18, 6)), ge=0)
    market_value: float = Field(sa_column=Column(Numeric(18, 6)), description="computed: quantity * current_price")
    unrealized_gain: float = Field(sa_column=Column(Numeric(18, 6)))
    unrealized_gain_pct: float = Field(sa_column=Column(Numeric(10, 4)))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": "now()"},
    )

    # Relationships
    portfolio: "Portfolio" = Relationship(back_populates="positions")
    asset: "Asset" = Relationship(back_populates="positions")

    class Config:
        from_attributes = True


# ── Pydantic schemas (no table) ─────────────────────────────────────────


class PositionCreate(SQLModel):
    """Schema for creating a new position."""

    portfolio_id: UUID
    asset_id: UUID
    quantity: float = Field(ge=0)
    avg_cost_basis: float = Field(ge=0)
    current_price: float = Field(ge=0)


class PositionUpdate(SQLModel):
    """Schema for updating a position (e.g., price refresh)."""

    quantity: float | None = Field(default=None, ge=0)
    avg_cost_basis: float | None = Field(default=None, ge=0)
    current_price: float | None = Field(default=None, ge=0)


class PositionRead(SQLModel, table=False):
    """Schema for reading a position."""

    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    quantity: float
    avg_cost_basis: float
    current_price: float
    market_value: float
    unrealized_gain: float
    unrealized_gain_pct: float
    created_at: datetime
    updated_at: datetime
