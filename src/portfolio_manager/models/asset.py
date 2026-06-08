"""Asset definitions — equities, options, futures, bonds, ETFs, mutual funds, ADRs, CFDs, crypto, cash."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_manager.models.base import TimestampMixin, UuidMixin
from portfolio_manager.database import Base


if TYPE_CHECKING:
    from portfolio_manager.models.position import Position  # noqa: F821
    from portfolio_manager.models.transaction import Transaction  # noqa: F821
    from portfolio_manager.models.benchmark import Benchmark  # noqa: F821


class AssetClass(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    OPTION = "option"
    FUTURE = "future"
    BOND = "bond"
    ADR = "adr"
    CFD = "cfd"
    CRYPTO = "crypto"
    CASH = "cash"


class Asset(UuidMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(
        Enum(AssetClass), nullable=False, default=AssetClass.EQUITY
    )
    exchange: Mapped[str | None] = mapped_column(String(10), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    positions: Mapped[list["Position"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    benchmarks: Mapped[list["Benchmark"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset {self.symbol} ({self.asset_class})>"
