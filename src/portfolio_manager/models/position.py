"""Current holdings — shares, cost basis, market value."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_manager.models.base import TimestampMixin, UuidMixin
from portfolio_manager.database import Base


if TYPE_CHECKING:
    from portfolio_manager.models.asset import Asset  # noqa: F821
    from portfolio_manager.models.portfolio import Portfolio  # noqa: F821


class Position(UuidMixin, TimestampMixin, Base):
    """Tracks current holdings for a portfolio+asset combination."""

    __tablename__ = "positions"

    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    avg_cost_basis: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    last_price_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="positions")  # noqa: F821
    asset: Mapped["Asset"] = relationship(back_populates="positions")  # noqa: F821

    @property
    def market_value(self) -> Decimal:
        if self.current_price is None:
            return Decimal(0)
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.avg_cost_basis

    @property
    def unrealized_gain(self) -> Decimal:
        return self.market_value - self.cost_basis

    @property
    def unrealized_gain_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return float((self.unrealized_gain / self.cost_basis) * 100)

    def __repr__(self) -> str:
        return f"<Position {self.portfolio_id}/{self.asset_id} qty={self.quantity}>"
