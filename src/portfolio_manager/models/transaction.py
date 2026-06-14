"""Trade history — buys, sells, dividends, splits, fees."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_manager.database import Base
from portfolio_manager.models.base import TimestampMixin, UuidMixin

if TYPE_CHECKING:
    from portfolio_manager.models.asset import Asset  # noqa: F821
    from portfolio_manager.models.portfolio import Portfolio  # noqa: F821


class TransactionType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"
    INTEREST = "interest"
    FEE = "fee"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    REINVEST = "reinvest"


class Transaction(UuidMixin, TimestampMixin, Base):
    """Records every financial event for a portfolio."""

    __tablename__ = "transactions"

    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=False, index=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False, index=True
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="transactions")  # noqa: F821
    asset: Mapped["Asset"] = relationship(back_populates="transactions")  # noqa: F821

    @property
    def total_amount(self) -> Decimal:
        if self.transaction_type in (TransactionType.BUY, TransactionType.DEPOSIT):
            return self.quantity * self.price + self.fees
        elif self.transaction_type in (
            TransactionType.SELL,
            TransactionType.DIVIDEND,
            TransactionType.INTEREST,
        ):
            return self.quantity * self.price - self.fees
        return self.quantity * self.price

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_type} {self.asset_id} @ {self.transaction_date}>"
