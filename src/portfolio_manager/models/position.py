"""Position model — user-scoped via portfolio.

A position is the current holding of a specific asset in a portfolio.
Computed fields (market_value, unrealized_gain, unrealized_gain_pct) are updated
on price refresh.
"""


from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, UniqueConstraint, func
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
    quantity: Decimal = Field(sa_column=Column(Numeric(18, 6)), ge=0)
    avg_cost_basis: Decimal = Field(sa_column=Column(Numeric(18, 6)), ge=0)
    current_price: Decimal = Field(sa_column=Column(Numeric(18, 6)), ge=0)
    market_value: Decimal = Field(sa_column=Column(Numeric(18, 6)), description="computed: quantity * current_price")
    unrealized_gain: Decimal = Field(sa_column=Column(Numeric(18, 6)))
    unrealized_gain_pct: Decimal = Field(sa_column=Column(Numeric(10, 4)))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )

    # Relationships
    portfolio: Portfolio = Relationship(back_populates="positions")
    asset: Asset = Relationship(back_populates="positions")


# ── Pydantic schemas (no table) ─────────────────────────────────────────


class PositionCreate(SQLModel):
    """Schema for creating a new position."""

    portfolio_id: UUID
    asset_id: UUID
    quantity: Decimal = Field(ge=0)
    avg_cost_basis: Decimal = Field(ge=0)
    current_price: Decimal = Field(ge=0)


class PositionUpdate(SQLModel):
    """Schema for updating a position (e.g., price refresh)."""

    quantity: Decimal | None = Field(default=None, ge=0)
    avg_cost_basis: Decimal | None = Field(default=None, ge=0)
    current_price: Decimal | None = Field(default=None, ge=0)


class PositionRead(SQLModel, table=False):
    """Schema for reading a position.

    ``symbol`` is the joined ``Asset.symbol`` (ticker). It is populated by the
    read routes that eagerly load the asset relationship; routes that return a
    freshly created/updated position without the join will leave it as ``None``.
    The frontend WebSocket client keys live price updates off this ticker.
    """

    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    symbol: str | None = None
    quantity: Decimal
    avg_cost_basis: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_gain: Decimal
    unrealized_gain_pct: Decimal
    created_at: datetime
    updated_at: datetime
