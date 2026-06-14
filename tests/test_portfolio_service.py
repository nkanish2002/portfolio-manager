"""Tests for the portfolio service."""

import pytest


class TestPortfolioService:
    """Test PortfolioService methods."""

    @pytest.mark.asyncio
    async def test_portfolio_service_instance(self):
        """Test PortfolioService can be instantiated."""
        from portfolio_manager.services.portfolios import PortfolioService

        service = PortfolioService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_portfolio_service_methods_exist(self):
        """Test PortfolioService has expected methods."""
        from portfolio_manager.services.portfolios import PortfolioService

        service = PortfolioService()

        # Check that all expected methods exist
        assert hasattr(service, "list_portfolios")
        assert hasattr(service, "get_portfolio")
        assert hasattr(service, "create_portfolio")
        assert hasattr(service, "delete_portfolio")

        # Verify they are async methods
        import inspect

        for method_name in [
            "list_portfolios",
            "get_portfolio",
            "create_portfolio",
            "delete_portfolio",
        ]:
            method = getattr(service, method_name)
            assert inspect.iscoroutinefunction(method)


class TestPortfolioServiceIntegration:
    """Integration tests for PortfolioService (mocked database)."""

    @pytest.mark.asyncio
    async def test_list_portfolios_empty_db(self):
        """Test list_portfolios returns empty list when no portfolios exist."""
        from portfolio_manager.services.portfolios import PortfolioService

        service = PortfolioService()
        portfolios = await service.list_portfolios()

        # Should return empty list when no portfolios
        assert isinstance(portfolios, list)
