"""Trades component — Portfolio Manager trades table.

This component displays trades in a sortable, filterable table.
It calls TradeService directly — no FastAPI routes.
"""

import asyncio
from typing import Optional, List

import solara
from solara import component, html

from portfolio_manager.services.trades import TradeService


class TradesView:
    """Trades table component for portfolios."""

    def __init__(self):
        self.trade_service = TradeService()
        self.selected_portfolio: Optional[str] = None
        self.trades_data: List[dict] = []
        self.filter_status: Optional[str] = None

    @component
    def render(self, portfolio_id: Optional[str] = None):
        """Render trades table for selected portfolio."""
        self.selected_portfolio = portfolio_id

        if not self.selected_portfolio:
            return html.div(
                {"class": "trades-placeholder"},
                [
                    html.p(
                        {"class": "placeholder-text"},
                        ["Select a portfolio to view trades"],
                    )
                ],
            )

        # Load trades data
        asyncio.run(self._load_trades())

        return html.div(
            {"class": "trades-container"},
            [
                self._render_toolbar(),
                self._render_trades_table(),
            ],
        )

    async def _load_trades(self):
        """Load trades data from service."""
        try:
            self.trades_data = await self.trade_service.list_trades(self.selected_portfolio)
        except Exception as e:
            self.trades_data = [{"error": str(e)}]

    def _render_toolbar(self):
        """Render the trades toolbar with filters."""
        return html.div(
            {"class": "trades-toolbar"},
            [
                html.div(
                    {"class": "filter-group"},
                    [
                        html.label({"for": "status-filter"}, ["Status:"]),
                        html.select(
                            {
                                "id": "status-filter",
                                "on_change": self._on_status_change,
                            },
                            [
                                html.option({"value": "", "selected": True}, ["All"]),
                                html.option({"value": "active"}, ["Active"]),
                                html.option({"value": "completed"}, ["Completed"]),
                                html.option({"value": "pending"}, ["Pending"]),
                            ],
                        ),
                    ],
                ),
                html.div({"class": "search-group"}, [html.input({"type": "text", "placeholder": "Search trades..."})]),
            ],
        )

    def _on_status_change(self, event):
        """Handle status filter change."""
        self.filter_status = event.target.value
        # Reload trades with filter
        pass

    def _render_trades_table(self):
        """Render the trades table."""
        if not self.trades_data:
            return html.div(
                {"class": "empty-state"},
                [html.p({"class": "empty-text"}, ["No trades found"])],
            )

        if "error" in self.trades_data[0]:
            return html.div(
                {"class": "trades-error"},
                [html.p({"class": "error-text"}, [f"Error loading trades: {self.trades_data[0]['error']}"])],
            )

        return html.div(
            {"class": "trades-table-wrapper"},
            [
                html.table(
                    {"class": "trades-table"},
                    [
                        self._render_table_header(),
                        self._render_table_body(),
                    ],
                ),
            ],
        )

    def _render_table_header(self):
        """Render the table header row."""
        headers = ["Date", "Type", "Portfolio", "Asset", "Quantity", "Price", "Status"]
        return html.thead(
            [html.tr([html.th({"class": "header-cell"}, [h]) for h in headers])],
        )

    def _render_table_body(self):
        """Render the table body rows."""
        rows = []
        for trade in self.trades_data:
            rows.append(
                html.tr(
                    {
                        "class": "trade-row",
                        "onclick": lambda t=trade: self._on_trade_click(t),
                    },
                    [
                        html.td({"class": "date-cell"}, [trade.get("date", "")]),
                        html.td({"class": "type-cell"}, [trade.get("type", "")]),
                        html.td({"class": "portfolio-cell"}, [trade.get("portfolio", "")]),
                        html.td({"class": "asset-cell"}, [trade.get("asset", "")]),
                        html.td({"class": "quantity-cell"}, [trade.get("quantity", "")]),
                        html.td({"class": "price-cell"}, [trade.get("price", "")]),
                        html.td({"class": "status-cell"}, [trade.get("status", "")]),
                    ],
                )
            )
        return html.tbody(rows)

    def _on_trade_click(self, trade):
        """Handle trade row click."""
        # Open trade details modal
        pass


def get_trades_view():
    """Return a trades view instance for Solara components."""
    return TradesView()
