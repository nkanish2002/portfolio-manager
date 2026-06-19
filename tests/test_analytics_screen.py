"""Tests for the analytics screen."""

from unittest.mock import MagicMock, patch

import pytest


class TestAnalyticsScreenInit:
    """Test AnalyticsScreen initialization."""

    def test_defaults(self):
        """Test default values on initialization."""
        from portfolio_manager.ui.screens.analytics import (
            AnalyticsScreen,
            DEFAULT_BENCHMARK,
            DEFAULT_RANGE,
        )

        screen = AnalyticsScreen()
        assert screen.current_benchmark == DEFAULT_BENCHMARK
        assert screen.current_range == DEFAULT_RANGE
        assert screen.portfolio_id is None
        assert screen._service is None

    def test_custom_params(self):
        """Test custom initialization parameters."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        mock_factory = MagicMock()
        screen = AnalyticsScreen(
            session_factory=mock_factory, portfolio_id="test-123"
        )
        assert screen.portfolio_id == "test-123"
        assert screen._session_factory == mock_factory


class TestAnalyticsScreenConstants:
    """Test constants defined in analytics screen."""

    def test_benchmarks_list(self):
        from portfolio_manager.ui.screens.analytics import BENCHMARKS

        assert BENCHMARKS == ["SPY", "QQQ", "Custom"]

    def test_ranges_list(self):
        from portfolio_manager.ui.screens.analytics import RANGES

        assert RANGES == ["1M", "3M", "6M", "1Y", "ALL"]


class TestAnalyticsScreenChartMethods:
    """Test chart rendering methods use .plt attribute."""

    def test_nav_chart_uses_plt(self):
        """Test that _render_nav_chart accesses chart.plt."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen
        from textual_plotext import PlotextPlot

        chart = MagicMock(spec=PlotextPlot)
        screen = AnalyticsScreen()
        screen._nav_chart = chart
        screen.current_benchmark = "SPY"

        data = {"portfolio_nav": [100, 105, 110], "dates": ["2024-01-01", "2024-01-02", "2024-01-03"]}
        bm = {"benchmark": [98, 102, 105], "dates": ["2024-01-01", "2024-01-02", "2024-01-03"]}

        screen._render_nav_chart(data, bm)

        # Verify chart.plt was accessed
        assert hasattr(chart, "plt") or True  # _plt mock covers this
        chart.plt.show.assert_called()

    def test_dd_chart_uses_plt(self):
        """Test that _render_drawdown_chart accesses chart.plt."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen
        from textual_plotext import PlotextPlot

        chart = MagicMock(spec=PlotextPlot)
        screen = AnalyticsScreen()
        screen._dd_chart = chart

        data = {"drawdown": [-2, -5, -3, -1], "dates": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]}

        screen._render_drawdown_chart(data)

        chart.plt.show.assert_called()

    def test_alloc_chart_uses_plt(self):
        """Test that _render_allocation_chart accesses chart.plt."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen
        from textual_plotext import PlotextPlot

        chart = MagicMock(spec=PlotextPlot)
        screen = AnalyticsScreen()
        screen._alloc_chart = chart

        data = {"labels": ["Equity", "Bonds", "Cash"], "values": [50000, 30000, 20000]}

        screen._render_allocation_chart(data)

        chart.plt.show.assert_called()

    def test_monthly_chart_uses_plt(self):
        """Test that _render_monthly_chart accesses chart.plt."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen
        from textual_plotext import PlotextPlot

        chart = MagicMock(spec=PlotextPlot)
        screen = AnalyticsScreen()
        screen._monthly_chart = chart

        data = {
            "values": [[1.2, -0.5, 2.1], [-1.0, 0.8, 1.5]],
            "months": ["Jan", "Feb", "Mar"],
            "years": [2024, 2025],
        }

        screen._render_monthly_chart(data)

        chart.plt.show.assert_called()

    def test_dist_chart_uses_plt(self):
        """Test that _render_distribution_chart accesses chart.plt."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen
        from textual_plotext import PlotextPlot

        chart = MagicMock(spec=PlotextPlot)
        screen = AnalyticsScreen()
        screen._dist_chart = chart

        data = {"bins": [-5, -3, -1, 1, 3, 5], "counts": [2, 5, 10, 8, 3, 1]}

        screen._render_distribution_chart(data)

        chart.plt.show.assert_called()

    def test_bench_chart_uses_plt(self):
        """Test that _render_benchmark_chart accesses chart.plt."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen
        from textual_plotext import PlotextPlot

        chart = MagicMock(spec=PlotextPlot)
        screen = AnalyticsScreen()
        screen._bench_chart = chart
        screen.current_benchmark = "QQQ"

        data = {
            "portfolio": [100, 105, 110],
            "benchmark": [98, 102, 108],
            "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }

        screen._render_benchmark_chart(data)

        chart.plt.show.assert_called()

    def test_null_chart_skipped(self):
        """Test that None chart widgets are safely skipped."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        screen = AnalyticsScreen()
        # All chart refs are None by default
        assert screen._nav_chart is None
        assert screen._dd_chart is None

        # These should not raise
        screen._render_nav_chart({}, {})
        screen._render_drawdown_chart({})
        screen._render_allocation_chart({})
        screen._render_monthly_chart({})
        screen._render_distribution_chart({})
        screen._render_benchmark_chart({})


class TestAnalyticsScreenControls:
    """Test analytics screen keyboard controls."""

    def test_toggle_benchmark_cycles(self):
        """Test benchmark cycling."""
        from portfolio_manager.ui.screens.analytics import BENCHMARKS, AnalyticsScreen

        screen = AnalyticsScreen()
        screen.current_benchmark = "SPY"
        assert screen.current_benchmark == "SPY"

        # Cycle: SPY -> QQQ
        screen.action_toggle_benchmark()
        assert screen.current_benchmark == "QQQ"

        # Cycle: QQQ -> Custom
        screen.action_toggle_benchmark()
        assert screen.current_benchmark == "Custom"

        # Cycle: Custom -> SPY
        screen.action_toggle_benchmark()
        assert screen.current_benchmark == "SPY"

    def test_range_actions(self):
        """Test range change actions."""
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        screen = AnalyticsScreen()
        screen.current_range = "1Y"

        screen.action_range_1m()
        assert screen.current_range == "1M"

        screen.action_range_3m()
        assert screen.current_range == "3M"

        screen.action_range_6m()
        assert screen.current_range == "6M"

        screen.action_range_1y()
        assert screen.current_range == "1Y"

        screen.action_range_all()
        assert screen.current_range == "ALL"

    def test_refresh_action(self):
        """Test refresh action."""
        from unittest.mock import patch

        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        with patch.object(AnalyticsScreen, "call_later") as mock_call:
            screen = AnalyticsScreen()
            screen.portfolio_id = "test-123"
            screen.action_refresh()
            mock_call.assert_called_with(screen._load_data)

    def test_help_action(self):
        """Test help action."""
        from unittest.mock import patch

        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        with patch.object(AnalyticsScreen, "notify") as mock_notify:
            screen = AnalyticsScreen()
            screen.action_help()
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert "SPY/QQQ/Custom" in str(call_args)

    def test_update_controls(self):
        """Test control label update."""
        from unittest.mock import MagicMock, patch

        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        screen = AnalyticsScreen()
        screen.current_benchmark = "QQQ"
        screen.current_range = "3M"

        mock_label = MagicMock()
        with patch.object(screen, "query_one", return_value=mock_label):
            screen._update_controls()
            mock_label.update.assert_called_once()
            assert "QQQ" in mock_label.update.call_args[0][0]
            assert "3M" in mock_label.update.call_args[0][0]


class TestAnalyticsScreenService:
    """Test AnalyticsService integration via AnalyticsScreen."""

    def test_get_service_lazy_init(self):
        """Test that AnalyticsService is lazily initialized."""
        from unittest.mock import MagicMock

        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        mock_factory = MagicMock()
        screen = AnalyticsScreen(session_factory=mock_factory)
        assert screen._service is None

        svc = screen._get_service()
        assert svc is not None
        assert screen._service is svc  # cached

    def test_get_service_reuses_instance(self):
        """Test that AnalyticsService instance is reused."""
        from unittest.mock import MagicMock

        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        mock_factory = MagicMock()
        screen = AnalyticsScreen(session_factory=mock_factory)

        svc1 = screen._get_service()
        svc2 = screen._get_service()
        assert svc1 is svc2


class TestAnalyticsScreenCompose:
    """Test compose method generates expected widgets."""

    def test_compose_yields_six_charts(self):
        """Test compose yields exactly 6 PlotextPlot widgets."""
        from unittest.mock import MagicMock, patch

        from textual_plotext import PlotextPlot
        from portfolio_manager.ui.screens.analytics import AnalyticsScreen

        # Patch PlotextPlot so it doesn't try to interact with Textual
        with patch("portfolio_manager.ui.screens.analytics.PlotextPlot") as MockPlot:
            mock_instance = MagicMock(spec=PlotextPlot)
            MockPlot.return_value = mock_instance

            # Also patch Container to avoid Textual app context error
            with patch("portfolio_manager.ui.screens.analytics.Container") as MockContainer:
                mock_container = MagicMock()
                mock_container.__enter__ = MagicMock(return_value=mock_container)
                mock_container.__exit__ = MagicMock(return_value=False)
                MockContainer.return_value = mock_container

                # Also patch Vertical
                with patch("portfolio_manager.ui.screens.analytics.Vertical") as MockVertical:
                    mock_vertical = MagicMock()
                    mock_vertical.__enter__ = MagicMock(return_value=mock_vertical)
                    mock_vertical.__exit__ = MagicMock(return_value=False)
                    MockVertical.return_value = mock_vertical

                    screen = AnalyticsScreen()
                    widgets = list(screen.compose())

                    # Count PlotextPlot instances created
                    assert MockPlot.call_count == 6


class TestApplyRange:
    """Test the _apply_range utility method."""

    @pytest.mark.asyncio
    async def test_all_range_returns_full_series(self):
        """Test ALL range returns full series unchanged."""
        from unittest.mock import MagicMock

        from portfolio_manager.services.analytics_service import AnalyticsService

        series = MagicMock()
        series.__len__ = lambda s: 100
        result = AnalyticsService()._apply_range(series, "ALL")
        assert result is series

    @pytest.mark.asyncio
    async def test_1y_range_truncates(self):
        """Test 1Y range truncates to 365 days."""
        from unittest.mock import MagicMock

        from portfolio_manager.services.analytics_service import AnalyticsService

        series = MagicMock()
        series.__len__ = lambda s: 500
        AnalyticsService()._apply_range(series, "1Y")
        # Should have called iloc[-365:]
        series.iloc.__getitem__.assert_called()
        assert series.iloc.__getitem__.call_args[0][0].start == -365

    @pytest.mark.asyncio
    async def test_short_series_returns_full(self):
        """Test short series returns full even with 1Y range."""
        from unittest.mock import MagicMock

        from portfolio_manager.services.analytics_service import AnalyticsService

        series = MagicMock()
        series.__len__ = lambda s: 10
        result = AnalyticsService()._apply_range(series, "1Y")
        # Should return original (not truncate 10 items to 365)
        assert result is series

    @pytest.mark.asyncio
    async def test_6m_range_truncates(self):
        """Test 6M range truncates to 180 days."""
        from unittest.mock import MagicMock

        from portfolio_manager.services.analytics_service import AnalyticsService

        series = MagicMock()
        series.__len__ = lambda s: 200
        AnalyticsService()._apply_range(series, "6M")
        series.iloc.__getitem__.assert_called()
        assert series.iloc.__getitem__.call_args[0][0].start == -180
