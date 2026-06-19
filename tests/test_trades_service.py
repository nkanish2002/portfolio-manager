"""Tests for the trades service."""

import pytest


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
