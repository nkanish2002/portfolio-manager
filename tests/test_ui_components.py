"""Tests for UI components."""

import pytest


class TestDashboardComponent:
    """Test Dashboard component."""

    def test_dashboard_instance(self):
        """Test Dashboard can be instantiated."""
        from portfolio_manager.ui.dashboard import Dashboard

        dashboard = Dashboard()
        assert dashboard is not None

    def test_dashboard_has_expected_methods(self):
        """Test Dashboard has expected methods."""
        from portfolio_manager.ui.dashboard import Dashboard

        dashboard = Dashboard()

        # Check that all expected methods exist
        assert hasattr(dashboard, "render")
        assert hasattr(dashboard, "_render_header")
        assert hasattr(dashboard, "_render_portfolio_selector")
        assert hasattr(dashboard, "_render_main_content")

    def test_dashboard_selected_portfolio_default(self):
        """Test selected_portfolio defaults to None."""
        from portfolio_manager.ui.dashboard import Dashboard

        dashboard = Dashboard()
        assert dashboard.selected_portfolio is None


class TestChartsViewComponent:
    """Test ChartsView component."""

    def test_charts_view_instance(self):
        """Test ChartsView can be instantiated."""
        from portfolio_manager.ui.charts import ChartsView

        charts = ChartsView()
        assert charts is not None

    def test_charts_view_has_expected_methods(self):
        """Test ChartsView has expected methods."""
        from portfolio_manager.ui.charts import ChartsView

        charts = ChartsView()

        # Check that all expected methods exist
        assert hasattr(charts, "render")
        assert hasattr(charts, "_load_charts")
        assert hasattr(charts, "_render_navigation")
        assert hasattr(charts, "_render_charts_grid")

    def test_charts_view_selected_portfolio_default(self):
        """Test selected_portfolio defaults to None."""
        from portfolio_manager.ui.charts import ChartsView

        charts = ChartsView()
        assert charts.selected_portfolio is None


class TestTradesViewComponent:
    """Test TradesView component."""

    def test_trades_view_instance(self):
        """Test TradesView can be instantiated."""
        from portfolio_manager.ui.trades import TradesView

        trades = TradesView()
        assert trades is not None

    def test_trades_view_has_expected_methods(self):
        """Test TradesView has expected methods."""
        from portfolio_manager.ui.trades import TradesView

        trades = TradesView()

        # Check that all expected methods exist
        assert hasattr(trades, "render")
        assert hasattr(trades, "_load_trades")
        assert hasattr(trades, "_render_toolbar")
        assert hasattr(trades, "_render_trades_table")

    def test_trades_view_selected_portfolio_default(self):
        """Test selected_portfolio defaults to None."""
        from portfolio_manager.ui.trades import TradesView

        trades = TradesView()
        assert trades.selected_portfolio is None
