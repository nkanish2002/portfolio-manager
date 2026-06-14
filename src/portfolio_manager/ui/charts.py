"""Charts component — Portfolio Manager chart views.

This component renders chart visualizations using Solara's
web component integration. It calls ChartService directly.
"""

import asyncio
from typing import Optional

import solara
from solara import component, html

from portfolio_manager.services.charts import ChartService


class ChartsView:
    """Chart view component for portfolios."""

    def __init__(self):
        self.chart_service = ChartService()
        self.selected_portfolio: Optional[str] = None
        self.charts_data: dict = {}

    @component
    def render(self, portfolio_id: Optional[str] = None):
        """Render chart views for selected portfolio."""
        self.selected_portfolio = portfolio_id

        if not self.selected_portfolio:
            return html.div(
                {"class": "charts-placeholder"},
                [
                    html.p(
                        {"class": "placeholder-text"},
                        ["Select a portfolio to view charts"],
                    )
                ],
            )

        # Load charts data
        asyncio.run(self._load_charts())

        return html.div(
            {"class": "charts-container"},
            [
                self._render_navigation(),
                self._render_charts_grid(),
            ],
        )

    async def _load_charts(self):
        """Load charts data from service."""
        try:
            self.charts_data = {
                "allocation": await self.chart_service.get_allocation_data(self.selected_portfolio),
                "trend": await self.chart_service.get_trend_data(self.selected_portfolio),
                "risk": await self.chart_service.get_risk_metrics(self.selected_portfolio),
            }
        except Exception as e:
            self.charts_data = {"error": str(e)}

    def _render_navigation(self):
        """Render chart type navigation tabs."""
        tabs = ["Allocation", "Trend", "Risk"]
        return html.div(
            {"class": "chart-tabs"},
            [html.button({"class": "tab", "onclick": self._switch_tab}, [tab]) for tab in tabs],
        )

    def _switch_tab(self, event):
        """Switch between chart types."""
        # Tab switching logic
        pass

    def _render_charts_grid(self):
        """Render the charts grid."""
        if "error" in self.charts_data:
            return html.div(
                {"class": "charts-error"},
                [html.p({"class": "error-text"}, [f"Error loading charts: {self.charts_data['error']}"])],
            )

        return html.div(
            {"class": "charts-grid"},
            [
                self._render_allocation_chart(),
                self._render_trend_chart(),
                self._render_risk_chart(),
            ],
        )

    def _render_allocation_chart(self):
        """Render asset allocation chart."""
        return html.div(
            {"class": "chart-card"},
            [
                html.h3({"class": "chart-title"}, ["Asset Allocation"]),
                html.div({"class": "chart-content"}, ["Allocation chart placeholder"]),
            ],
        )

    def _render_trend_chart(self):
        """Render portfolio trend chart."""
        return html.div(
            {"class": "chart-card"},
            [
                html.h3({"class": "chart-title"}, ["Portfolio Trend"]),
                html.div({"class": "chart-content"}, ["Trend chart placeholder"]),
            ],
        )

    def _render_risk_chart(self):
        """Render risk metrics chart."""
        return html.div(
            {"class": "chart-card"},
            [
                html.h3({"class": "chart-title"}, ["Risk Metrics"]),
                html.div({"class": "chart-content"}, ["Risk chart placeholder"]),
            ],
        )


def get_charts_view():
    """Return a charts view instance for Solara components."""
    return ChartsView()
