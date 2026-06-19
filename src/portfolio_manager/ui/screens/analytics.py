"""Analytics screen -- risk gauges, six textual-plotext charts,
benchmark/range selectors, and real data wiring.

Key bindings:
    [B] Cycle benchmark (SPY -> QQQ -> Custom -> SPY)
    [1] 1-month range
    [3] 3-month range
    [6] 6-month range
    [y] 1-year range
    [a] All time
    [R] Refresh all data
    [?] Show help
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import async_sessionmaker
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label
from textual_plotext import PlotextPlot

from portfolio_manager.services.analytics_service import AnalyticsService
from portfolio_manager.services.risk_gauges import render_risk_report

# ── Constants ────────────────────────────────────────────────────────────

RANGES = ["1M", "3M", "6M", "1Y", "ALL"]
BENCHMARKS = ["SPY", "QQQ", "Custom"]
DEFAULT_BENCHMARK = "SPY"
DEFAULT_RANGE = "1Y"


class AnalyticsScreen(Screen):
    """Analytics screen with risk gauges, charts, and selectors."""

    BINDINGS = [
        Binding("b", "toggle_benchmark", "Benchmark"),
        Binding("1", "range_1m", "1M"),
        Binding("3", "range_3m", "3M"),
        Binding("6", "range_6m", "6M"),
        Binding("y", "range_1y", "1Y"),
        Binding("a", "range_all", "All"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    AnalyticsScreen {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1 2;
        grid-pattern: Row;
    }

    #gauges-area {
        width: 100%;
        height: 15;
        border: solid #334155;
        background: #000;
        padding: 1 2;
    }

    #charts-area {
        width: 100%;
        height: 85%;
    }

    #controls {
        width: 100%;
        height: auto;
        dock: top;
        layout: horizontal;
        padding: 0 1;
    }

    #controls > Label {
        margin: 0 1;
    }

    #chart-container {
        width: 100%;
        height: 100%;
        layout: horizontal;
        padding: 0 1;
    }

    .chart-label {
        color: #10B981;
        width: 100%;
        text-align: center;
        padding: 1 0;
    }

    .chart-row {
        width: 50%;
        height: 100%;
        padding: 0 0.5;
    }
    """

    def __init__(
        self,
        session_factory: async_sessionmaker | None = None,
        portfolio_id: str | None = None,
    ) -> None:
        """Initialize analytics screen.

        Args:
            session_factory: Async session factory for DB access.
            portfolio_id: Optional portfolio ID. None = use first available.
        """
        super().__init__()
        self._session_factory = session_factory
        self.portfolio_id = portfolio_id
        self.current_benchmark = DEFAULT_BENCHMARK
        self.current_range = DEFAULT_RANGE
        self._portfolios: list[dict] = []
        self._portfolio_ids: list[str] = []
        self._current_portfolio_index = 0
        self._service: AnalyticsService | None = None

        # Chart widget references
        self._nav_chart: PlotextPlot | None = None
        self._dd_chart: PlotextPlot | None = None
        self._alloc_chart: PlotextPlot | None = None
        self._monthly_chart: PlotextPlot | None = None
        self._dist_chart: PlotextPlot | None = None
        self._bench_chart: PlotextPlot | None = None

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get_service(self) -> AnalyticsService:
        """Return the AnalyticsService instance."""
        if self._service is None:
            self._service = AnalyticsService(
                session_factory=self._session_factory
            )
        return self._service

    # ── Lifecycle ────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Load portfolio list and start data loading."""
        self.call_later(self._load_portfolios)
        # Periodically check if we have a portfolio_id set
        self.set_interval(0.5, self._check_and_load_data)

    async def _load_portfolios(self) -> None:
        """Load portfolio list from the database."""
        from portfolio_manager.services.portfolios import _list_portfolios

        try:
            async with self._get_service()._get_session_factory()() as session:
                self._portfolios = await _list_portfolios(session)
                self._portfolio_ids = [p["id"] for p in self._portfolios]
        except Exception:
            self._portfolios = []
            self._portfolio_ids = []

        # Set default portfolio if none specified
        if not self.portfolio_id and self._portfolio_ids:
            self.portfolio_id = self._portfolio_ids[0]
            self._current_portfolio_index = 0

        self.call_from_thread(self._update_controls)

    async def _check_and_load_data(self) -> None:
        """Periodically check and load data."""
        if self.portfolio_id:
            self.call_later(self._load_data)

    def compose(self) -> ComposeResult:
        """Compose the analytics layout."""
        yield Header()

        # ── Controls row ───────────────────────────────────────────────
        with Container(id="controls"):
            yield Label(
                "Benchmark: SPY [B]  |  Range: 1Y [1][3][6][y][a]",
                classes="chart-label",
                id="controls-label",
            )

        # ── Risk gauges area ───────────────────────────────────────────
        with Container(id="gauges-area"):
            yield Label(
                "Loading risk metrics...",
                id="gauges-display",
            )

        # ── Charts area (6 charts in 3 rows of 2) ─────────────────────
        with Vertical(id="charts-area"):
            # Row 1: NAV History (left) + Drawdown (right)
            with Container(id="chart-container"):
                yield Label("NAV History + Benchmark", classes="chart-label")
                self._nav_chart = PlotextPlot()
                yield self._nav_chart

                yield Label("Drawdown", classes="chart-label")
                self._dd_chart = PlotextPlot()
                yield self._dd_chart

            # Row 2: Allocation (left) + Monthly Returns (right)
            with Container(id="chart-container"):
                yield Label("Allocation", classes="chart-label")
                self._alloc_chart = PlotextPlot()
                yield self._alloc_chart

                yield Label("Monthly Returns", classes="chart-label")
                self._monthly_chart = PlotextPlot()
                yield self._monthly_chart

            # Row 3: Returns Distribution (left) + Benchmark Comparison (right)
            with Container(id="chart-container"):
                yield Label("Returns Distribution", classes="chart-label")
                self._dist_chart = PlotextPlot()
                yield self._dist_chart

                yield Label("Benchmark Comparison", classes="chart-label")
                self._bench_chart = PlotextPlot()
                yield self._bench_chart

        yield Footer()

    # ── Data loading ─────────────────────────────────────────────────────

    async def _load_data(self) -> None:
        """Load all data for the current portfolio/benchmark/range."""
        if not self.portfolio_id:
            return

        try:
            await self._run_load_tasks()
        except Exception:
            self.call_from_thread(self._show_error, "Failed to load analytics data")

    async def _run_load_tasks(self) -> None:
        """Run all data-loading coroutines and update UI."""
        if not self.portfolio_id:
            return

        svc = self._get_service()

        # Load risk report and benchmark comparison in parallel
        risk_coro = svc.get_risk_report(self.portfolio_id)
        nav_coro = svc.get_nav_history(
            self.portfolio_id, self.current_benchmark, self.current_range
        )
        bench_coro = svc.get_benchmark_comparison(
            self.portfolio_id, self.current_benchmark, self.current_range
        )
        dd_coro = svc.get_drawdown(self.portfolio_id, self.current_range)

        nav_data, risk_report, benchmark_data, drawdown_data = (
            await asyncio.gather(nav_coro, risk_coro, bench_coro, dd_coro)
        )

        # Load remaining chart data
        alloc_coro = svc.get_allocation(self.portfolio_id)
        monthly_coro = svc.get_monthly_returns(self.portfolio_id)
        dist_coro = svc.get_returns_distribution(self.portfolio_id)

        alloc_data, monthly_data, dist_data = await asyncio.gather(
            alloc_coro, monthly_coro, dist_coro
        )

        # Update all widgets in the main thread
        self.call_from_thread(
            self._update_all,
            nav_data,
            risk_report,
            benchmark_data,
            drawdown_data,
            alloc_data,
            monthly_data,
            dist_data,
        )

    # ── UI updates ───────────────────────────────────────────────────────

    def _update_all(
        self,
        nav_data: dict,
        risk_report: dict,
        benchmark_data: dict,
        drawdown_data: dict,
        alloc_data: dict,
        monthly_data: dict,
        dist_data: dict,
    ) -> None:
        """Update all widgets with loaded data."""
        # Risk gauges
        gauges_lines = render_risk_report(risk_report, width=78)
        gauges_str = "\n".join(gauges_lines) if gauges_lines else "No data"
        try:
            gauges_display = self.query_one("#gauges-display", Label)
            gauges_display.update(gauges_str)
        except Exception:
            pass

        # Chart 1: NAV History + Benchmark
        if self._nav_chart:
            self._render_nav_chart(nav_data, benchmark_data)

        # Chart 2: Drawdown
        if self._dd_chart:
            self._render_drawdown_chart(drawdown_data)

        # Chart 3: Allocation
        if self._alloc_chart:
            self._render_allocation_chart(alloc_data)

        # Chart 4: Monthly Returns
        if self._monthly_chart:
            self._render_monthly_chart(monthly_data)

        # Chart 5: Returns Distribution
        if self._dist_chart:
            self._render_distribution_chart(dist_data)

        # Chart 6: Benchmark Comparison
        if self._bench_chart:
            self._render_benchmark_chart(benchmark_data)

    # ── Chart renderers (using chart.plt API) ────────────────────────────

    def _render_nav_chart(
        self, nav_data: dict, bm_comparison: dict
    ) -> None:
        """Render NAV history chart with benchmark overlay."""
        chart = self._nav_chart
        if chart is None:
            return
        plt = chart.plt

        plt.clear_data()
        plt.title("NAV History + Benchmark")
        plt.xlabel("Date")
        plt.ylabel("Normalized Value (100)")
        plt.canvas_color("black")
        plt.ticks_color("#10B981")

        portfolio_nav = nav_data.get("portfolio_nav", [])
        dates = nav_data.get("dates", [])

        if portfolio_nav and len(portfolio_nav) > 0:
            x_axis = list(range(len(portfolio_nav)))
            plt.plot(x_axis, portfolio_nav, label="Portfolio", color="#10B981")
            step = max(1, len(dates) // 6) if len(dates) > 6 else 1
            plt.xticks(
                x_axis[::step],
                [dates[i] for i in range(0, len(dates), step)],
            )

        # Benchmark overlay
        bm_nav = bm_comparison.get("benchmark", [])
        if bm_nav and len(bm_nav) > 0:
            bm_dates = bm_comparison.get("dates", [])
            x_bench = list(range(len(bm_nav)))
            plt.plot(
                x_bench, bm_nav,
                label=f"Benchmark ({self.current_benchmark})",
                color="#EF4444",
            )
            all_dates = dates if len(dates) >= len(bm_dates) else bm_dates
            step = max(1, len(all_dates) // 6) if len(all_dates) > 6 else 1
            plt.xticks(
                x_axis[::step],
                [all_dates[i] for i in range(0, len(all_dates), step)],
            )

        plt.show()

    def _render_drawdown_chart(self, data: dict) -> None:
        """Render drawdown area chart."""
        chart = self._dd_chart
        if chart is None:
            return
        plt = chart.plt

        plt.clear_data()
        plt.title("Drawdown")
        plt.xlabel("Date")
        plt.ylabel("Drawdown %")
        plt.canvas_color("black")
        plt.ticks_color("#10B981")

        dd = data.get("drawdown", [])
        dates = data.get("dates", [])

        if dd and len(dd) > 0:
            x_axis = list(range(len(dd)))
            plt.plot(x_axis, dd, label="Drawdown", color="#EF4444")
            step = max(1, len(dates) // 6) if len(dates) > 6 else 1
            plt.xticks(
                x_axis[::step],
                [dates[i] for i in range(0, len(dates), step)],
            )

        plt.show()

    def _render_allocation_chart(self, data: dict) -> None:
        """Render allocation bar chart."""
        chart = self._alloc_chart
        if chart is None:
            return
        plt = chart.plt

        plt.clear_data()
        plt.title("Allocation")
        plt.xlabel("Asset Class")
        plt.ylabel("Value ($)")
        plt.canvas_color("black")
        plt.ticks_color("#10B981")

        labels = data.get("labels", [])
        values = data.get("values", [])

        if labels and values and len(labels) > 0:
            plt.bar(labels, values, label="Allocation", color="#10B981")
            step = max(1, len(labels) // 4) if len(labels) > 4 else 1
            plt.xticks(
                list(range(0, len(labels), step)),
                labels[::step],
            )

        plt.show()

    def _render_monthly_chart(self, data: dict) -> None:
        """Render monthly returns heatmap.

        The data dict contains 'values' as a 2D list
        [[year1_month1, year1_month2, ...], [year2_month1, ...], ...].
        """
        chart = self._monthly_chart
        if chart is None:
            return
        plt = chart.plt

        plt.clear_data()
        plt.title("Monthly Returns (%)")
        plt.xlabel("Month")
        plt.ylabel("Year")
        plt.canvas_color("black")
        plt.ticks_color("#10B981")

        values = data.get("values", [])

        if values and len(values) > 0:
            plt.heatmap(values, cmap="red_blue")

            months = data.get("months", [])
            years = data.get("years", [])

            if months:
                plt.xticks(
                    list(range(len(months))),
                    months,
                )
            if years:
                plt.yticks(
                    list(range(len(years))),
                    [str(y) for y in years],
                )

        plt.show()

    def _render_distribution_chart(self, data: dict) -> None:
        """Render returns distribution histogram."""
        chart = self._dist_chart
        if chart is None:
            return
        plt = chart.plt

        plt.clear_data()
        plt.title("Returns Distribution")
        plt.xlabel("Return %")
        plt.ylabel("Frequency")
        plt.canvas_color("black")
        plt.ticks_color("#10B981")

        bins = data.get("bins", [])
        counts = data.get("counts", [])

        if bins and counts and len(bins) > 0:
            plt.hist(bins, counts, label="Daily Returns", color="#10B981")

        plt.show()

    def _render_benchmark_chart(self, data: dict) -> None:
        """Render benchmark comparison line chart."""
        chart = self._bench_chart
        if chart is None:
            return
        plt = chart.plt

        plt.clear_data()
        plt.title(f"vs {self.current_benchmark}")
        plt.xlabel("Date")
        plt.ylabel("Normalized (100)")
        plt.canvas_color("black")
        plt.ticks_color("#10B981")

        portfolio = data.get("portfolio", [])
        benchmark = data.get("benchmark", [])
        dates = data.get("dates", [])

        if portfolio and len(portfolio) > 0:
            x_port = list(range(len(portfolio)))
            plt.plot(x_port, portfolio, label="Portfolio", color="#10B981")

        if benchmark and len(benchmark) > 0:
            x_bm = list(range(len(benchmark)))
            plt.plot(x_bm, benchmark, label=self.current_benchmark, color="#EF4444")

        # Set x-axis labels from whichever data source has dates
        all_dates = dates if len(dates) > 0 else []
        if all_dates:
            x_axis = list(range(len(portfolio))) if portfolio else []
            step = max(1, len(all_dates) // 6) if len(all_dates) > 6 else 1
            plt.xticks(
                x_axis[::step],
                [all_dates[i] for i in range(0, len(all_dates), step)],
            )

        plt.show()

    # ── Controls ─────────────────────────────────────────────────────────

    def _update_controls(self) -> None:
        """Update the benchmark and range label displays."""
        try:
            label = self.query_one("#controls-label", Label)
            label.update(
                f"Benchmark: {self.current_benchmark} [B]  |  "
                f"Range: {self.current_range} [1][3][6][y][a]"
            )
        except Exception:
            pass

    def action_toggle_benchmark(self) -> None:
        """Cycle benchmark selector."""
        idx = (
            BENCHMARKS.index(self.current_benchmark)
            if self.current_benchmark in BENCHMARKS
            else 0
        )
        self.current_benchmark = BENCHMARKS[(idx + 1) % len(BENCHMARKS)]
        self._update_controls()
        self.call_later(self._load_data)

    def action_range_1m(self) -> None:
        self.current_range = "1M"
        self._update_controls()
        self.call_later(self._load_data)

    def action_range_3m(self) -> None:
        self.current_range = "3M"
        self._update_controls()
        self.call_later(self._load_data)

    def action_range_6m(self) -> None:
        self.current_range = "6M"
        self._update_controls()
        self.call_later(self._load_data)

    def action_range_1y(self) -> None:
        self.current_range = "1Y"
        self._update_controls()
        self.call_later(self._load_data)

    def action_range_all(self) -> None:
        self.current_range = "ALL"
        self._update_controls()
        self.call_later(self._load_data)

    def action_refresh(self) -> None:
        """Refresh all analytics data."""
        self.call_later(self._load_data)

    def _show_error(self, message: str) -> None:
        """Show an error notification."""
        self.notify(message, title="Error", severity="error")

    def action_help(self) -> None:
        """Show help."""
        self.notify(
            "[B] Cycle benchmark (SPY/QQQ/Custom) | "
            "[1][3][6][y][a] Change range | "
            "[R] Refresh | "
            "[A] Analytics | [T] Trades | [Q] Quit",
            title="Analytics Shortcuts",
        )
