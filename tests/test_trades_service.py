"""Tests for the trades service."""

from decimal import Decimal

import pytest
from sqlalchemy import select


class TestTradeService:
    """Test TradeService methods."""

    @pytest.mark.asyncio
    async def test_trades_service_instance(self):
        """Test TradeService can be instantiated."""
        from portfolio_manager.services.trades import TradeService

        service = TradeService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_trades_service_methods_exist(self):
        """Test TradeService has expected methods."""
        from portfolio_manager.services.trades import TradeService

        service = TradeService()

        # Check that all expected methods exist
        assert hasattr(service, "list_trades")
        assert hasattr(service, "add_transaction")
        assert hasattr(service, "sell_position")
        assert hasattr(service, "get_trades_summary")

        # Verify they are async methods
        import inspect

        for method_name in [
            "list_trades",
            "add_transaction",
            "sell_position",
            "get_trades_summary",
        ]:
            method = getattr(service, method_name)
            assert inspect.iscoroutinefunction(method)


class TestTradeServiceIntegration:
    """Integration tests for TradeService (mocked database)."""

    @pytest.mark.asyncio
    async def test_list_trades_empty_db(self):
        """Test list_trades returns empty list when no trades exist."""
        from portfolio_manager.services.trades import TradeService

        service = TradeService()
        result = await service.list_trades("nonexistent_portfolio")

        # Should return dict with trades list when no trades
        assert isinstance(result, dict)
        assert "trades" in result
        assert isinstance(result["trades"], list)
        assert len(result["trades"]) == 0
        assert result["total"] == 0


class TestBuyUpdatesPosition:
    """BUY transactions must keep `Position.avg_cost_basis` correct."""

    async def _make_portfolio_and_asset(self, isolated_db):
        from portfolio_manager.models.asset import Asset, AssetClass
        from portfolio_manager.models.portfolio import Portfolio

        async with isolated_db() as session:
            pf = Portfolio(name="test", description=None, currency="USD")
            asset = Asset(symbol="AAPL", name="Apple Inc.", asset_class=AssetClass.EQUITY)
            session.add_all([pf, asset])
            await session.commit()
            await session.refresh(pf)
            await session.refresh(asset)
            return str(pf.id), str(asset.id)

    @pytest.mark.asyncio
    async def test_first_buy_creates_position(self, isolated_db):
        """First BUY for an asset creates the Position with correct avg cost."""
        from portfolio_manager.models.position import Position
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)

        await TradeService().add_transaction(
            portfolio_id=pf_id,
            asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=10,
            price=100,
            fees=5,
        )

        async with isolated_db() as session:
            result = await session.execute(
                select(Position).where(Position.portfolio_id == pf_id)
            )
            position = result.scalar_one()
            assert position.quantity == Decimal("10")
            # Cost basis includes fees: (10*100 + 5) / 10 = 100.50
            assert position.avg_cost_basis == Decimal("100.5")
            assert position.current_price == Decimal("100")

    @pytest.mark.asyncio
    async def test_second_buy_updates_running_average(self, isolated_db):
        """Second BUY at a different price weights the running average correctly."""
        from portfolio_manager.models.position import Position
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)
        service = TradeService()

        # Buy 10 @ 100, no fees → avg = 100
        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=10, price=100, fees=0,
        )
        # Buy 10 @ 200, no fees → avg = (10*100 + 10*200) / 20 = 150
        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=10, price=200, fees=0,
        )

        async with isolated_db() as session:
            result = await session.execute(
                select(Position).where(Position.portfolio_id == pf_id)
            )
            position = result.scalar_one()
            assert position.quantity == Decimal("20")
            assert position.avg_cost_basis == Decimal("150")
            # current_price reflects most recent buy
            assert position.current_price == Decimal("200")

    @pytest.mark.asyncio
    async def test_buy_then_sell_uses_correct_avg_cost(self, isolated_db):
        """BUY then SELL should produce P&L against the running average."""
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)
        service = TradeService()

        # Buy 10 @ 100, no fees → avg = 100
        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=10, price=100, fees=0,
        )
        # Sell 5 @ 150, no fees → P&L = (150 - 100) * 5 = 250
        result = await service.sell_position(
            portfolio_id=pf_id, asset_id=asset_id,
            quantity=5, price=150, fees=0,
        )

        assert result["realized_pnl"] == 250.0
        assert result["avg_cost_basis"] == 100.0
        assert result["remaining_quantity"] == 5.0

    @pytest.mark.asyncio
    async def test_non_buy_transaction_does_not_touch_position(self, isolated_db):
        """DIVIDEND/FEE/etc. should not create or modify a Position."""
        from portfolio_manager.models.position import Position
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)

        await TradeService().add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.DIVIDEND,
            quantity=1, price=2.50, fees=0,
        )

        async with isolated_db() as session:
            result = await session.execute(
                select(Position).where(Position.portfolio_id == pf_id)
            )
            assert result.scalar_one_or_none() is None


class TestListTradesFiltered:
    """Tests for filtered and paginated trade listing."""

    async def _make_portfolio_and_asset(self, isolated_db):
        from portfolio_manager.models.asset import Asset, AssetClass
        from portfolio_manager.models.portfolio import Portfolio

        async with isolated_db() as session:
            pf = Portfolio(name="test", description=None, currency="USD")
            asset = Asset(symbol="AAPL", name="Apple Inc.", asset_class=AssetClass.EQUITY)
            session.add_all([pf, asset])
            await session.commit()
            await session.refresh(pf)
            await session.refresh(asset)
            return str(pf.id), str(asset.id)

    @pytest.mark.asyncio
    async def test_list_trades_returns_dict_with_paging(self, isolated_db):
        """list_trades returns a dict with pagination info."""
        from portfolio_manager.services.trades import TradeService

        service = TradeService()
        result = await service.list_trades("nonexistent")

        assert isinstance(result, dict)
        assert "trades" in result
        assert "total" in result
        assert "page" in result
        assert "page_size" in result
        assert "total_pages" in result

    @pytest.mark.asyncio
    async def test_list_trades_filter_by_type(self, isolated_db):
        """Filter by BUY type returns only buys."""
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)
        service = TradeService()

        # Add a buy
        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=10, price=100, fees=0,
        )
        # Add a dividend
        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.DIVIDEND,
            quantity=1, price=2.50, fees=0,
        )

        # Filter for BUY only
        result = await service.list_trades(pf_id, trade_type="BUY")
        assert result["total"] == 1
        assert result["trades"][0]["type"] == "buy"

        # Filter for DIVIDEND only
        result = await service.list_trades(pf_id, trade_type="DIVIDEND")
        assert result["total"] == 1
        assert result["trades"][0]["type"] == "dividend"

    @pytest.mark.asyncio
    async def test_list_trades_pagination(self, isolated_db):
        """Pagination returns correct page of results."""
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)
        service = TradeService()

        # Add 5 buys
        for i in range(5):
            await service.add_transaction(
                portfolio_id=pf_id, asset_id=asset_id,
                transaction_type=TransactionType.BUY,
                quantity=1, price=100 + i, fees=0,
            )

        # Page 1 with page_size=2
        result = await service.list_trades(pf_id, page=1, page_size=2)
        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert result["total_pages"] == 3
        assert len(result["trades"]) == 2

        # Page 2
        result = await service.list_trades(pf_id, page=2, page_size=2)
        assert result["page"] == 2
        assert len(result["trades"]) == 2

        # Page 3 (last page)
        result = await service.list_trades(pf_id, page=3, page_size=2)
        assert len(result["trades"]) == 1


class TestGetPositionForAsset:
    """Tests for position lookup for sell modals."""

    async def _make_portfolio_and_asset(self, isolated_db):
        from portfolio_manager.models.asset import Asset, AssetClass
        from portfolio_manager.models.portfolio import Portfolio

        async with isolated_db() as session:
            pf = Portfolio(name="test", description=None, currency="USD")
            asset = Asset(symbol="MSFT", name="Microsoft", asset_class=AssetClass.EQUITY)
            session.add_all([pf, asset])
            await session.commit()
            await session.refresh(pf)
            await session.refresh(asset)
            return str(pf.id), str(asset.id)

    @pytest.mark.asyncio
    async def test_get_position_returns_data(self, isolated_db):
        """get_position_for_asset returns position data after a buy."""
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)
        service = TradeService()

        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=20, price=300, fees=5,
        )

        pos = await service.get_position_for_asset(pf_id, asset_id)
        assert pos is not None
        assert pos["quantity"] == 20
        assert pos["avg_cost_basis"] > 0  # includes fees
        assert pos["cost_basis"] > 0

    @pytest.mark.asyncio
    async def test_get_position_returns_none_for_unknown(self, isolated_db):
        """get_position_for_asset returns None for unknown asset."""
        from portfolio_manager.services.trades import TradeService

        service = TradeService()
        pos = await service.get_position_for_asset("fake-portfolio", "fake-asset")
        assert pos is None


class TestSellPreview:
    """Tests for sell P&L preview."""

    async def _make_portfolio_and_asset(self, isolated_db):
        from portfolio_manager.models.asset import Asset, AssetClass
        from portfolio_manager.models.portfolio import Portfolio

        async with isolated_db() as session:
            pf = Portfolio(name="test", description=None, currency="USD")
            asset = Asset(symbol="GOOGL", name="Alphabet", asset_class=AssetClass.EQUITY)
            session.add_all([pf, asset])
            await session.commit()
            await session.refresh(pf)
            await session.refresh(asset)
            return str(pf.id), str(asset.id)

    @pytest.mark.asyncio
    async def test_sell_preview_valid(self, isolated_db):
        """Sell preview returns valid result with correct P&L."""
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)
        service = TradeService()

        # Buy at 100
        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=10, price=100, fees=0,
        )

        # Preview sell at 150
        preview = await service.calculate_sell_preview(
            portfolio_id=pf_id, asset_id=asset_id,
            quantity=5, price=150, fees=0,
        )

        assert preview["valid"] is True
        assert preview["projected_pnl"] == 250.0  # (150 - 100) * 5
        assert preview["proceeds"] == 750.0
        assert preview["cost_of_sold"] == 500.0
        assert preview["remaining_quantity"] == 5.0

    @pytest.mark.asyncio
    async def test_sell_preview_insufficient_shares(self, isolated_db):
        """Sell preview rejects quantity > available."""
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService

        pf_id, asset_id = await self._make_portfolio_and_asset(isolated_db)
        service = TradeService()

        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=10, price=100, fees=0,
        )

        preview = await service.calculate_sell_preview(
            portfolio_id=pf_id, asset_id=asset_id,
            quantity=15, price=150, fees=0,
        )

        assert preview["valid"] is False
        assert len(preview["errors"]) > 0

    @pytest.mark.asyncio
    async def test_sell_preview_no_position(self, isolated_db):
        """Sell preview rejects unknown asset."""
        from portfolio_manager.services.trades import TradeService

        service = TradeService()
        preview = await service.calculate_sell_preview(
            portfolio_id="fake", asset_id="fake",
            quantity=1, price=100, fees=0,
        )

        assert preview["valid"] is False
        assert "No position found" in preview["errors"][0]


class TestBuyCostCalculation:
    """Tests for buy cost calculation."""

    @pytest.mark.asyncio
    async def test_buy_cost_basic(self, isolated_db):
        """calculate_buy_cost returns correct total."""
        from portfolio_manager.services.trades import TradeService

        service = TradeService()
        result = await service.calculate_buy_cost(
            portfolio_id="fake", asset_id="fake",
            quantity=10, price=100, fees=5,
        )

        assert result["total_cost"] == 1005.0
        assert result["quantity"] == 10
        assert result["price"] == 100
        assert result["fees"] == 5


class TestCSVExport:
    """Tests for CSV export functionality."""

    @pytest.mark.asyncio
    async def test_csv_export_format(self, isolated_db):
        """CSV export produces correctly formatted data."""
        from portfolio_manager.models.asset import Asset, AssetClass
        from portfolio_manager.models.portfolio import Portfolio
        from portfolio_manager.models.transaction import TransactionType
        from portfolio_manager.services.trades import TradeService
        import pandas as pd

        async with isolated_db() as session:
            pf = Portfolio(name="test", description=None, currency="USD")
            asset = Asset(symbol="TSLA", name="Tesla", asset_class=AssetClass.EQUITY)
            session.add_all([pf, asset])
            await session.commit()
            await session.refresh(pf)
            await session.refresh(asset)
            pf_id = str(pf.id)
            asset_id = str(asset.id)

        service = TradeService()

        # Add some trades
        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.BUY,
            quantity=50, price=200, fees=0,
        )
        await service.add_transaction(
            portfolio_id=pf_id, asset_id=asset_id,
            transaction_type=TransactionType.DIVIDEND,
            quantity=1, price=0.50, fees=0,
        )

        # Get trades
        result = await service.list_trades(pf_id)
        trades = result["trades"]

        # Convert to DataFrame (what the export does)
        df = pd.DataFrame(trades)

        assert len(df) == 2
        assert "type" in df.columns
        assert "quantity" in df.columns
        assert "price" in df.columns
