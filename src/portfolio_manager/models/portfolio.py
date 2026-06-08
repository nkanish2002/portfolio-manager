"""Portfolio definitions — named collections of positions."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_manager.models.base import TimestampMixin, UuidMixin
from portfolio_manager.database import Base


if TYPE_CHECKING:
    from portfolio_manager.models.position import Position  # noqa: F821
    from portfolio_manager.models.transaction import Transaction  # noqa: F821
    from portfolio_manager.models.benchmark import Benchmark  # noqa: F821


class Portfolio(UuidMixin, TimestampMixin, Base):
    """A named portfolio (e.g., IRA, Taxable, Margin)."""

    __tablename__ = "portfolios"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    positions: Mapped[list["Position"]] = relationship(  # noqa: F821
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    benchmarks: Mapped[list["Benchmark"]] = relationship(  # noqa: F821
        secondary="benchmark_portfolios", back_populates="portfolios"
    )

    def __repr__(self) -> str:
        return f"<Portfolio {self.name}>"
