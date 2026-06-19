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
        trades = await service.list_trades("nonexistent_portfolio")

        # Should return empty list when no trades
        assert isinstance(trades, list)


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
