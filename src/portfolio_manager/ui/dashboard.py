"""Dashboard component — main Portfolio Manager UI.

This component orchestrates the Solara services layer and renders
the main dashboard layout. It calls services directly — no FastAPI routes.
"""

import asyncio
from typing import Optional

import solara
from solara import component, html

from portfolio_manager.services.portfolios import PortfolioService
from portfolio_manager.services.charts import ChartService
from portfolio_manager.services.trades import TradeService


class Dashboard:
    """Main dashboard component."""

    def __init__(self):
        self.portfolio_service = PortfolioService()
        self.chart_service = ChartService()
        self.trade_service = TradeService()
        self.selected_portfolio: Optional[str] = None

    @component
    def render(self):
        """Render the dashboard layout."""
        return html.div(
            {"class": "dashboard"},
            [
                self._render_header(),
                self._render_portfolio_selector(),
                self._render_main_content(),
            ],
        )

    def _render_header(self):
        """Render the header section."""
        return html.header(
            {"class": "dashboard-header"},
            [
                html.h1({"class": "title"}, ["Portfolio Manager"]),
                html.p({"class": "subtitle"}, ["Manage portfolios, track charts, and view trades"]),
            ],
        )

    def _render_portfolio_selector(self):
        """Render the portfolio selector dropdown."""
        portfolios = asyncio.run(self.portfolio_service.list_portfolios())

        options = [
            html.option({"value": "", "disabled": True, "selected": True}, ["Select a portfolio"])
        ]
        for p in portfolios:
            options.append(html.option({"value": p["id"]}, [p["name"]]))

        return html.div(
            {"class": "portfolio-selector"},
            [
                html.label({"for": "portfolio-select"}, ["Select Portfolio:"]),
                html.select(
                    {
                        "id": "portfolio-select",
                        "on_change": self._on_portfolio_change,
                    },
                    options,
                ),
            ],
        )

    def _on_portfolio_change(self, event):
        """Handle portfolio selection change."""
        self.selected_portfolio = event.target.value
        # Trigger re-render of main content
        return True

    def _render_main_content(self):
        """Render the main content area."""
        if not self.selected_portfolio:
            return html.div(
                {"class": "placeholder-content"},
                [
                    html.p(
                        {"class": "placeholder-text"},
                        ["Select a portfolio to view charts and trades"],
                    )
                ],
            )

        # Render portfolio summary cards
        return html.div(
            {"class": "main-content"},
            [
                html.div(
                    {"class": "summary-cards"},
                    [
                        self._render_summary_card("Total Assets", "$0.00"),
                        self._render_summary_card("Active Trades", "0"),
                        self._render_summary_card("Risk Score", "Low"),
                    ],
                ),
                html.div(
                    {"class": "charts-container"},
                    [
                        html.h2(["Portfolio Charts"]),
                        html.div({"class": "chart-placeholder"}, ["Charts will load here"]),
                    ],
                ),
                html.div(
                    {"class": "trades-container"},
                    [
                        html.h2(["Recent Trades"]),
                        html.div({"class": "trades-placeholder"}, ["Trades table will load here"]),
                    ],
                ),
            ],
        )

    def _render_summary_card(self, title, value):
        """Render a summary card component."""
        return html.div(
            {"class": "summary-card"},
            [html.h3({"class": "card-title"}, [title]), html.p({"class": "card-value"}, [value])],
        )


def get_dashboard():
    """Return a dashboard instance for Solara components."""
    return Dashboard()
