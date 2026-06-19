"""Tests for the analytics service."""

from datetime import date, timedelta

import pytest


async def _create_portfolio_and_asset(session):
    print(f"\n=== _create_portfolio_and_asset called, session: {session} ===")
    from portfolio_manager.models.portfolio import Portfolio
    from portfolio_manager.models.asset import Asset, AssetClass

    pf = Portfolio(name="test", description=None, currency="USD")
    asset = Asset(symbol="TEST", name="Test Asset", asset_class=AssetClass.EQUITY)
    session.add_all([pf, asset])
    await session.commit()
    await session.refresh(pf)
    await session.refresh(asset)
    print(f"=== Created pf_id: {pf.id}, asset_id: {asset.id}")
    return str(pf.id), str(asset.id)


async def _add_deposit_transactions(session, portfolio_id, asset_id, count=30):
    """Add DEPOSIT transactions for testing NAV history. Adds one at a time to avoid aiosqlite UUID bug."""
    from portfolio_manager.models.transaction import Transaction, TransactionType

    base_date = date(2024, 1, 1)
    for i in range(count):
        txn = Transaction(
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            transaction_type=TransactionType.DEPOSIT,
            transaction_date=base_date + timedelta(days=i),
            quantity=100.0 + i * 10,
            price=1.0,
        )
        session.add(txn)
        await session.commit()  # Commit each to avoid bulk INSERT UUID bug


class TestAnalyticsServiceInit:

    @pytest.mark.asyncio
    async def test_service_creation(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService(session_factory=isolated_db)
        assert service._session_factory == isolated_db

    @pytest.mark.asyncio
    async def test_service_creation_no_factory(self):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService()
        assert service._session_factory is None


class TestGetPortfolioId:

    @pytest.mark.asyncio
    async def test_returns_id_when_portfolio_exists(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService

        async with isolated_db() as session:
            pf_id, asset_id = await _create_portfolio_and_asset(session)
            print(f"\n=== Created pf_id: {pf_id}, asset_id: {asset_id} ===\n")

        service = AnalyticsService(session_factory=isolated_db)
        portfolio_id = await service.get_current_portfolio_id()
        print(f"\n=== Got portfolio_id: {portfolio_id} ===\n")
        assert portfolio_id is not None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_portfolio(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService(session_factory=isolated_db)
        portfolio_id = await service.get_current_portfolio_id()
        assert portfolio_id is None


class TestGetRiskReport:

    @pytest.mark.asyncio
    async def test_insufficient_data(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService(session_factory=isolated_db)
        report = await service.get_risk_report("nonexistent")
        assert report.get("insufficient_data") is True

    @pytest.mark.asyncio
    async def test_returns_risk_metrics(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService

        # Create portfolio and single transaction
        async with isolated_db() as session:
            from portfolio_manager.models.portfolio import Portfolio
            from portfolio_manager.models.asset import Asset, AssetClass
            from portfolio_manager.models.transaction import Transaction, TransactionType

            pf = Portfolio(name="test_risk", description=None, currency="USD")
            asset = Asset(symbol="TEST", name="Test", asset_class=AssetClass.EQUITY)
            session.add_all([pf, asset])
            await session.commit()
            await session.refresh(pf)
            await session.refresh(asset)
            pf_id = str(pf.id)
            asset_id = str(asset.id)

            # Add 30 transactions one at a time
            from datetime import date, timedelta
            base_date = date(2024, 1, 1)
            for i in range(30):
                txn = Transaction(
                    portfolio_id=pf_id,
                    asset_id=asset_id,
                    transaction_type=TransactionType.DEPOSIT,
                    transaction_date=base_date + timedelta(days=i),
                    quantity=100.0 + i * 10,
                    price=1.0,
                )
                session.add(txn)
                await session.commit()

        service = AnalyticsService(session_factory=isolated_db)
        report = await service.get_risk_report(pf_id)

        assert "sharpe_ratio" in report
        assert "sortino_ratio" in report
        assert "max_drawdown" in report
        assert "ulcer_index" in report
        assert "var" in report
        assert "calmar_ratio" in report


class TestGetNavHistory:

    @pytest.mark.asyncio
    async def test_returns_data_with_transactions(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService

        async with isolated_db() as session:
            pf_id, asset_id = await _create_portfolio_and_asset(session)
            await _add_deposit_transactions(session, pf_id, asset_id, count=30)

        service = AnalyticsService(session_factory=isolated_db)
        nav_data = await service.get_nav_history(pf_id, "SPY", "1Y")

        assert len(nav_data["dates"]) > 0
        assert len(nav_data["portfolio_nav"]) > 0
        assert nav_data["benchmark_symbol"] == "SPY"
        assert "benchmark_nav" in nav_data

    @pytest.mark.asyncio
    async def test_empty_when_no_transactions(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService(session_factory=isolated_db)
        nav_data = await service.get_nav_history("nonexistent", "SPY", "1Y")
        assert nav_data["dates"] == []
        assert nav_data["portfolio_nav"] == []


class TestGetDrawdown:

    @pytest.mark.asyncio
    async def test_returns_drawdown_data(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService

        async with isolated_db() as session:
            pf_id, asset_id = await _create_portfolio_and_asset(session)
            await _add_deposit_transactions(session, pf_id, asset_id, count=30)

        service = AnalyticsService(session_factory=isolated_db)
        dd = await service.get_drawdown(pf_id, "1Y")

        assert len(dd["dates"]) > 0
        assert len(dd["drawdown"]) > 0
        assert len(dd["nav"]) > 0

    @pytest.mark.asyncio
    async def test_empty_when_no_transactions(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService(session_factory=isolated_db)
        dd = await service.get_drawdown("nonexistent")
        assert dd["dates"] == []
        assert dd["drawdown"] == []


class TestGetAllocation:

    @pytest.mark.asyncio
    async def test_returns_allocation_with_positions(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        from portfolio_manager.models.portfolio import Portfolio
        from portfolio_manager.models.asset import Asset, AssetClass
        from portfolio_manager.models.position import Position

        async with isolated_db() as session:
            pf = Portfolio(name="test_alloc", description=None, currency="USD")
            asset1 = Asset(symbol="AAPL", name="Apple", asset_class=AssetClass.EQUITY)
            asset2 = Asset(symbol="BND", name="Bonds", asset_class=AssetClass.BOND)
            session.add_all([pf, asset1, asset2])
            await session.commit()
            await session.refresh(pf)
            await session.refresh(asset1)
            await session.refresh(asset2)
            pf_id = str(pf.id)
            asset_id_1 = str(asset1.id)
            asset_id_2 = str(asset2.id)

            pos1 = Position(portfolio_id=pf_id, asset_id=asset_id_1,
                           quantity=100, avg_cost_basis=150, current_price=175)
            pos2 = Position(portfolio_id=pf_id, asset_id=asset_id_2,
                           quantity=50, avg_cost_basis=80, current_price=82)
            session.add_all([pos1, pos2])
            await session.commit()

        service = AnalyticsService(session_factory=isolated_db)
        alloc = await service.get_allocation(pf_id)

        assert len(alloc["labels"]) > 0
        assert len(alloc["values"]) > 0
        assert len(alloc["colors"]) == len(alloc["labels"])
        assert alloc["total_value"] > 0

    @pytest.mark.asyncio
    async def test_empty_when_no_positions(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService(session_factory=isolated_db)
        alloc = await service.get_allocation("nonexistent")
        assert alloc["labels"] == []
        assert alloc["values"] == []


class TestGetMonthlyReturns:

    @pytest.mark.asyncio
    async def test_returns_insufficient_data(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        from portfolio_manager.models.portfolio import Portfolio
        from portfolio_manager.models.asset import Asset, AssetClass
        from portfolio_manager.models.transaction import Transaction, TransactionType

        async with isolated_db() as session:
            pf = Portfolio(name="test_mr", description=None, currency="USD")
            asset = Asset(symbol="TEST", name="Test", asset_class=AssetClass.EQUITY)
            session.add_all([pf, asset])
            await session.commit()
            await session.refresh(pf)
            await session.refresh(asset)
            pf_id = str(pf.id)
            asset_id = str(asset.id)

            txn = Transaction(
                portfolio_id=pf_id, asset_id=asset_id,
                transaction_type=TransactionType.DEPOSIT,
                transaction_date=date(2024, 1, 1),
                quantity=100, price=1.0,
            )
            session.add(txn)
            await session.commit()

        service = AnalyticsService(session_factory=isolated_db)
        mr = await service.get_monthly_returns(pf_id)
        assert mr.get("insufficient_data") is True

    @pytest.mark.asyncio
    async def test_returns_data_with_weekly_transactions(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        from portfolio_manager.models.transaction import Transaction, TransactionType

        async with isolated_db() as session:
            pf_id, asset_id = await _create_portfolio_and_asset(session)
            base = date(2023, 1, 1)
            for i in range(52):
                txn = Transaction(
                    portfolio_id=pf_id, asset_id=asset_id,
                    transaction_type=TransactionType.DEPOSIT,
                    transaction_date=base + timedelta(days=i * 7),
                    quantity=1000.0, price=1.0,
                )
                session.add(txn)
            await session.commit()

        service = AnalyticsService(session_factory=isolated_db)
        mr = await service.get_monthly_returns(pf_id)
        assert "years" in mr
        assert "months" in mr
        assert "values" in mr


class TestGetReturnsDistribution:

    @pytest.mark.asyncio
    async def test_returns_insufficient_data(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService(session_factory=isolated_db)
        dist = await service.get_returns_distribution("nonexistent")
        assert dist["bins"] == []
        assert dist["counts"] == []

    @pytest.mark.asyncio
    async def test_returns_distribution_structure(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService

        async with isolated_db() as session:
            pf_id, asset_id = await _create_portfolio_and_asset(session)
            await _add_deposit_transactions(session, pf_id, asset_id, count=50)

        service = AnalyticsService(session_factory=isolated_db)
        dist = await service.get_returns_distribution(pf_id)

        assert "mean_return" in dist
        assert "std_return" in dist
        assert "bins" in dist
        assert "counts" in dist


class TestGetBenchmarkComparison:

    @pytest.mark.asyncio
    async def test_returns_insufficient_data(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        service = AnalyticsService(session_factory=isolated_db)
        comp = await service.get_benchmark_comparison("nonexistent", "SPY")
        assert comp["dates"] == []
        assert comp["portfolio"] == []


class TestApplyRange:

    @pytest.mark.asyncio
    async def test_all_range_returns_full_series(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        import pandas as pd
        series = pd.Series(range(100), index=pd.date_range("2024-01-01", periods=100))
        result = AnalyticsService()._apply_range(series, "ALL")
        assert len(result) == 100

    @pytest.mark.asyncio
    async def test_1y_range_truncates(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        import pandas as pd
        series = pd.Series(range(500), index=pd.date_range("2024-01-01", periods=500))
        result = AnalyticsService()._apply_range(series, "1Y")
        assert len(result) == 365

    @pytest.mark.asyncio
    async def test_short_series_returns_full(self, isolated_db):
        from portfolio_manager.services.analytics_service import AnalyticsService
        import pandas as pd
        series = pd.Series(range(10), index=pd.date_range("2024-01-01", periods=10))
        result = AnalyticsService()._apply_range(series, "1Y")
        assert len(result) == 10
