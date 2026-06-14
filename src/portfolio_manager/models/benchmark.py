"""Benchmark definitions for portfolio performance comparison."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_manager.database import Base
from portfolio_manager.models.base import UuidMixin

if TYPE_CHECKING:
    from portfolio_manager.models.asset import Asset  # noqa: F821
    from portfolio_manager.models.portfolio import Portfolio  # noqa: F821


class Benchmark(UuidMixin, Base):
    """Defines a benchmark with historical NAV data for comparison."""

    __tablename__ = "benchmarks"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=False, index=True
    )
    default_portfolio_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("portfolios.id"), nullable=True
    )

    asset: Mapped["Asset"] = relationship(back_populates="benchmarks")  # noqa: F821
    portfolios: Mapped[list["Portfolio"]] = relationship(  # noqa: F821
        secondary="benchmark_portfolios", back_populates="benchmarks"
    )

    def __repr__(self) -> str:
        return f"<Benchmark {self.name}>"


class BenchmarkPortfolioAssociation(UuidMixin, Base):
    """Many-to-many: benchmarks ↔ portfolios."""

    __tablename__ = "benchmark_portfolios"

    benchmark_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("benchmarks.id", ondelete="CASCADE"), primary_key=True
    )
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), primary_key=True
    )


class BenchmarkData(UuidMixin, Base):
    """Historical benchmark NAV/prices — date + price."""

    __tablename__ = "benchmark_data"

    benchmark_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)

    __table_args__ = ()

    def __repr__(self) -> str:
        return f"<BenchmarkData {self.benchmark_id} @ {self.date}>"
