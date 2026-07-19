"""Benchmark models — shared (NOT user-scoped).

Benchmark: comparison index (SPY, QQQ, etc.).
BenchmarkData: historical daily close prices.
portfolio_benchmarks: many-to-many association between Portfolio and Benchmark.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from portfolio_manager.database import Base, portfolio_benchmarks



class Benchmark(SQLModel, table=True):
    __tablename__ = "benchmarks"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    symbol: str = Field(max_length=10, unique=True, index=True)
    name: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    data: list["BenchmarkData"] = Relationship(back_populates="benchmark")
    portfolios: list["Portfolio"] = Relationship(
        back_populates="benchmarks",
        sa_relationship_kwargs={"secondary": portfolio_benchmarks},
    )

    class Config:
        from_attributes = True


class BenchmarkData(SQLModel, table=True):
    """Historical daily close prices for a benchmark."""

    __tablename__ = "benchmark_data"
    __table_args__ = (
        UniqueConstraint("benchmark_id", "date", name="uq_benchmark_date"),
    )

    id: UUID = Field(default_factory=uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    benchmark_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    date: datetime = Field(sa_column=Column("date"))
    close: float = Field(sa_column=Column(Numeric(18, 6)))

    # Relationships
    benchmark: "Benchmark" = Relationship(back_populates="data")

    class Config:
        from_attributes = True


# ── Pydantic schemas (no table) ─────────────────────────────────────────


class BenchmarkCreate(SQLModel):
    """Schema for creating a new benchmark."""

    symbol: str = Field(max_length=10)
    name: str = Field(max_length=255)


class BenchmarkRead(SQLModel, table=False):
    """Schema for reading a benchmark."""

    id: UUID
    symbol: str
    name: str


class BenchmarkDataRead(SQLModel, table=False):
    """Schema for reading benchmark historical data."""

    id: UUID
    benchmark_id: UUID
    date: datetime
    close: float
