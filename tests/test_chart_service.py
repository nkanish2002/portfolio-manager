"""Tests for the chart service."""

import pandas as pd
import pytest

from portfolio_manager.services.charts import (
    ChartService,
    _generate_monthly_from_nav,
)


class TestChartService:
    """Test ChartService methods."""

    def test_generate_monthly_from_nav_basic(self):
        """Test monthly returns generation from NAV series."""
        # Create a simple NAV series with known returns
        nav_series = pd.Series(
            [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            index=pd.date_range("2024-01-01", periods=11, freq="D"),
        )

        result = _generate_monthly_from_nav(nav_series)

        # Should have data since we have > 5 points
        assert result["insufficient_data"] is False
        assert len(result["years"]) > 0
        assert len(result["months"]) > 0
        assert len(result["values"]) > 0

    def test_generate_monthly_from_nav_insufficient(self):
        """Test that < 5 points returns insufficient data."""
        nav_series = pd.Series(
            [100, 101, 102],  # Only 3 points
            index=pd.date_range("2024-01-01", periods=3, freq="D"),
        )

        result = _generate_monthly_from_nav(nav_series)

        assert result["insufficient_data"] is True
        assert len(result["years"]) == 0
        assert len(result["months"]) == 0

    def test_generate_monthly_from_nav_empty(self):
        """Test empty NAV series."""
        nav_series = pd.Series([], dtype=float)

        result = _generate_monthly_from_nav(nav_series)

        assert result["insufficient_data"] is True
        assert len(result["years"]) == 0


class TestChartServiceIntegration:
    """Integration tests for ChartService (mocked database)."""

    @pytest.mark.asyncio
    async def test_chart_service_instance(self):
        """Test ChartService can be instantiated."""
        service = ChartService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_chart_service_methods_exist(self):
        """Test ChartService has expected methods."""
        service = ChartService()

        # Check that all expected methods exist
        assert hasattr(service, "get_nav_history")
        assert hasattr(service, "get_drawdown")
        assert hasattr(service, "get_allocation")
        assert hasattr(service, "get_monthly_returns")
        assert hasattr(service, "get_returns_distribution")
        assert hasattr(service, "get_benchmark_comparison")
        assert hasattr(service, "get_risk_report")

        # Verify they are async methods
        import inspect

        for method_name in [
            "get_nav_history",
            "get_drawdown",
            "get_allocation",
            "get_monthly_returns",
            "get_returns_distribution",
            "get_benchmark_comparison",
            "get_risk_report",
        ]:
            method = getattr(service, method_name)
            assert inspect.iscoroutinefunction(method)
