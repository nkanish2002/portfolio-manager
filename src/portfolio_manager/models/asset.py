"""Asset master — shared lookup table (NOT user-scoped).

Maps ticker symbols to metadata (asset class, exchange, sector, etc.).
Populated via yfinance lookups and statement imports.
"""


from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    symbol: str = Field(max_length=10, unique=True, index=True)
    name: str = Field(max_length=255)
    asset_class: str = Field(
        max_length=20,
        description="equity, etf, mutual_fund, option, future, bond, adr, cfd, crypto, cash",
    )
    exchange: str | None = Field(default=None, max_length=50)
    cusip: str | None = Field(default=None, max_length=20)
    sector: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=50)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )

    # Relationships
    positions: Mapped[list['Position']] = Relationship(back_populates="asset")
    transactions: Mapped[list['Transaction']] = Relationship(back_populates="asset")


# ── Pydantic schemas (no table) ─────────────────────────────────────────


class AssetCreate(SQLModel):
    """Schema for creating a new asset."""

    symbol: str = Field(max_length=10)
    name: str = Field(max_length=255)
    asset_class: str = Field(max_length=20)
    exchange: str | None = None
    cusip: str | None = None
    sector: str | None = None
    industry: str | None = None
    region: str | None = None


class AssetUpdate(SQLModel):
    """Schema for updating an asset."""

    name: str | None = None
    asset_class: str | None = None
    exchange: str | None = None
    cusip: str | None = None
    sector: str | None = None
    industry: str | None = None
    region: str | None = None


class AssetRead(SQLModel, table=False):
    """Schema for reading an asset."""

    id: UUID
    symbol: str
    name: str
    asset_class: str
    exchange: str | None = None
    cusip: str | None = None
    sector: str | None = None
    industry: str | None = None
    region: str | None = None
