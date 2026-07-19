"""Model tests — field validation, relationships, schema invariants.

These tests exercise the SQLModel/SQLAlchemy definitions directly (no HTTP).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select


class TestModelRegistry:
    def test_all_tables_registered(self):
        from portfolio_manager.database import Base

        expected = {
            "users",
            "assets",
            "accounts",
            "baskets",
            "portfolios",
            "positions",
            "transactions",
            "benchmarks",
            "benchmark_data",
            "portfolio_benchmarks",
        }
        assert set(Base.metadata.tables.keys()) == expected

    def test_financial_columns_are_numeric(self):
        from portfolio_manager.models import BenchmarkData, Position, Transaction

        for model in (Position, Transaction, BenchmarkData):
            for col in model.__table__.columns:
                if col.name in {
                    "quantity", "avg_cost_basis", "current_price", "market_value",
                    "unrealized_gain", "unrealized_gain_pct", "price", "fees",
                    "realized_gain", "close",
                }:
                    assert type(col.type).__name__ == "Numeric", (
                        f"{model.__name__}.{col.name} should be Numeric"
                    )

    def test_timestamps_are_timezone_aware(self):
        from portfolio_manager.models import (
            Account,
            Asset,
            Basket,
            Benchmark,
            Portfolio,
            Position,
            Transaction,
        )

        for model in (Asset, Account, Basket, Portfolio, Position, Transaction, Benchmark):
            for col in model.__table__.columns:
                if col.name in ("created_at", "updated_at", "trade_date"):
                    assert getattr(col.type, "timezone", False) is True, (
                        f"{model.__name__}.{col.name} should be timezone-aware"
                    )

    def test_benchmark_data_date_is_date(self):
        from portfolio_manager.models import BenchmarkData

        col = BenchmarkData.__table__.columns["date"]
        assert type(col.type).__name__ == "Date"


class TestRelationships:
    """Relationships resolve without circular import / mapper errors."""

    def test_portfolio_relationships(self):
        from portfolio_manager.models import Portfolio

        rels = {r.key for r in Portfolio.__mapper__.relationships}
        assert {"positions", "transactions", "benchmarks"}.issubset(rels)

    def test_asset_relationships(self):
        from portfolio_manager.models import Asset

        rels = {r.key for r in Asset.__mapper__.relationships}
        assert {"positions", "transactions"}.issubset(rels)

    def test_user_relationships(self):
        from portfolio_manager.models import User

        rels = {r.key for r in User.__mapper__.relationships}
        assert {"accounts", "baskets", "portfolios"}.issubset(rels)


class TestSchemas:
    def test_user_create_has_display_name(self):
        from portfolio_manager.auth import UserCreate, UserRead, UserUpdate

        for schema in (UserCreate, UserRead, UserUpdate):
            assert "display_name" in schema.model_fields

    def test_asset_create_validates(self):
        from portfolio_manager.models import AssetCreate

        a = AssetCreate(symbol="AAPL", name="Apple Inc", asset_class="equity")
        assert a.symbol == "AAPL"
        assert a.asset_class == "equity"

    def test_position_create_decimal(self):
        from uuid import uuid4

        from portfolio_manager.models import PositionCreate

        p = PositionCreate(
            portfolio_id=uuid4(),
            asset_id=uuid4(),
            quantity=Decimal("10.5"),
            avg_cost_basis=Decimal("150.25"),
            current_price=Decimal("175.00"),
        )
        # Decimals preserved (not coerced to float)
        assert isinstance(p.quantity, Decimal)
        assert p.quantity == Decimal("10.5")


class TestDBRoundTrip:
    """Persistence smoke test against the (clean) test database."""

    async def test_asset_create_read(self, db_session):
        from portfolio_manager.models import Asset

        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class="equity",
            exchange="NASDAQ",
            sector="Technology",
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)

        result = await db_session.execute(select(Asset).where(Asset.symbol == "AAPL"))
        fetched = result.scalar_one()
        assert fetched.id is not None
        assert fetched.name == "Apple Inc"
        assert fetched.created_at is not None

    async def test_user_persists(self, db_session):
        from portfolio_manager.models.user import User

        user = User(
            email="persist@example.com",
            hashed_password="fakehash",
            is_active=True,
            is_superuser=False,
            is_verified=False,
            display_name="Persisted",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        result = await db_session.execute(select(User).where(User.email == "persist@example.com"))
        fetched = result.scalar_one()
        assert fetched.display_name == "Persisted"
        assert fetched.id is not None

    async def test_unique_benchmark_date_constraint(self, db_session):
        from sqlalchemy.exc import IntegrityError

        from portfolio_manager.models import Benchmark, BenchmarkData

        bench = Benchmark(symbol="SPY", name="S&P 500 ETF")
        db_session.add(bench)
        await db_session.commit()
        await db_session.refresh(bench)

        from datetime import date

        b1 = BenchmarkData(benchmark_id=bench.id, data_date=date(2026, 1, 1), close=Decimal("450.0"))
        db_session.add(b1)
        await db_session.commit()

        b2 = BenchmarkData(benchmark_id=bench.id, data_date=date(2026, 1, 1), close=Decimal("455.0"))
        db_session.add(b2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
