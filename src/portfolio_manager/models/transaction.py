"""Transaction model — user-scoped via portfolio.

Records every trade event (buy, sell, dividend, split, etc.) for audit trail
and FIFO P&L calculation.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    portfolio_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    asset_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False),
    )
    type: str = Field(
        max_length=20,
        description="buy, sell, dividend, split, interest, fee, deposit, withdrawal",
    )
    quantity: float = Field(sa_column=Column(Numeric(18, 6)))
    price: float = Field(sa_column=Column(Numeric(18, 6)))
    fees: float = Field(default=0, sa_column=Column(Numeric(18, 6)))
    trade_date: datetime = Field(sa_column=Column("trade_date"))
    notes: str | None = Field(default=None, max_length=1000)
    realized_gain: float | None = Field(
        default=None,
        sa_column=Column(Numeric(18, 6)),
        description="computed via FIFO for sells",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    portfolio: "Portfolio" = Relationship(back_populates="transactions")
    asset: "Asset" = Relationship(back_populates="transactions")

    class Config:
        from_attributes = True


# ── Pydantic schemas (no table) ─────────────────────────────────────────


class TransactionCreate(SQLModel):
    """Schema for recording a new transaction."""

    portfolio_id: UUID
    asset_id: UUID
    type: str = Field(max_length=20)
    quantity: float
    price: float
    fees: float = Field(default=0)
    trade_date: datetime
    notes: str | None = None


class TransactionRead(SQLModel, table=False):
    """Schema for reading a transaction."""

    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    type: str
    quantity: float
    price: float
    fees: float
    trade_date: datetime
    notes: str | None = None
    realized_gain: float | None = None
    created_at: datetime
