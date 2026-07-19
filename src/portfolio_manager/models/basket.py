"""Basket model — user-scoped.

Users create any number of baskets with custom names, colors, and target allocations.
Examples: 3 baskets (Super Stable / Stable Alpha / High Beta) at 40/40/20,
or 4 baskets (Core / Growth / Speculative / Cash) at 30/30/20/20.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel


class Basket(SQLModel, table=True):
    __tablename__ = "baskets"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    user_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    color: str = Field(default="#58a6ff", max_length=7, description="Hex color for UI")
    target_allocation: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(5, 2)),
        ge=0,
        le=100,
        description="Target percent of total portfolio (0-100)",
    )
    sort_order: int = Field(default=0, ge=0)
    is_preset: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": "now()"},
    )

    # Relationships
    user: "User" = Relationship(back_populates="baskets")
    portfolios: list["Portfolio"] = Relationship(back_populates="basket")

    class Config:
        from_attributes = True


# ── Pydantic schemas (no table) ─────────────────────────────────────────


class BasketCreate(SQLModel):
    """Schema for creating a new basket."""

    name: str = Field(max_length=100)
    description: str | None = None
    color: str = Field(default="#58a6ff", max_length=7)
    target_allocation: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    sort_order: int = Field(default=0, ge=0)


class BasketUpdate(SQLModel):
    """Schema for updating a basket."""

    name: str | None = None
    description: str | None = None
    color: str | None = None
    target_allocation: Decimal | None = Field(default=None, ge=0, le=100)
    sort_order: int | None = None


class BasketRead(SQLModel, table=False):
    """Schema for reading a basket."""

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    color: str
    target_allocation: Decimal
    sort_order: int
    is_preset: bool
    created_at: datetime
    updated_at: datetime
