"""Portfolio Manager — Textual TUI Application.

Main entry point for the Textual-based portfolio management tool.
Provides dashboard, analytics, trades, and settings screens.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual import events
from textual.widgets import Footer, Header, Static
from textual_plotext import PlotextPlot
from portfolio_manager.ui.screens.dashboard import DashboardScreen
from portfolio_manager.ui.screens.analytics import AnalyticsScreen
from portfolio_manager.ui.screens.trades import TradesScreen
from portfolio_manager.ui.screens.settings import SettingsScreen
import asyncio


class PortfolioManagerApp(App):
    """Main Textual application for portfolio management."""

    CSS = """
    Screen {
        background: #000;
        color: #E2E8F0;
    }

    .header {
        width: 100%;
        height: auto;
        background: #1E293B;
        color: #E2E8F0;
        text-align: center;
        padding: 1;
    }

    .accent {
        color: #10B981;
    }

    .positive {
        color: #22C55E;
    }

    .negative {
        color: #EF4444;
    }

    .warning {
        color: #F59E0B;
    }

    Button {
        background: #1E293B;
        color: #E2E8F0;
        border: solid #334155;
        padding: 0 2;
        margin: 1;
    }

    Button:hover {
        background: #334155;
        color: #10B981;
        border: solid #10B981;
    }

    Button#primary {
        background: #10B981;
        color: #000;
        border: none;
    }

    Button#primary:hover {
        background: #059669;
    }

    DataTable {
        border: solid #334155;
    }

    DataTable .data-table--header {
        background: #1E293B;
        color: #10B981;
    }

    Input {
        border: solid #334155;
        background: #1E293B;
        color: #E2E8F0;
        padding: 0 1;
    }

    Input:focus {
        border: solid #10B981;
    }

    Chart {
        border: solid #334155;
        background: #000;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "show_help", "Help", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("a", "analytics", "Analytics", priority=True),
        Binding("t", "trades", "Trades", priority=True),
        Binding("c", "create_portfolio", "Create Portfolio", priority=True),
        Binding("s", "settings", "Settings", priority=True),
    ]

    TITLE = "Portfolio Manager"
    SUB_TITLE = "Textual TUI"

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        self._db_initialized = False
        self._price_cache = {}

    def compose(self) -> ComposeResult:
        """Compose the initial layout."""
        # Start with dashboard screen
        yield DashboardScreen()

    def on_mount(self) -> None:
        """Initialize app on mount."""
        # Initialize database connection
        self._initialize_database()
        
        # Start background price refresh
        self.set_interval(30, self._refresh_prices_task)

    def _initialize_database(self) -> None:
        """Initialize database connection."""
        # TODO: Connect to SQLite database
        self._db_initialized = True

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_show_help(self) -> None:
        """Show help dialog."""
        self.notify("Help: Use keyboard shortcuts or click buttons.", title="Help")

    def action_refresh(self) -> None:
        """Refresh all prices."""
        self.notify("Refreshing prices...", title="Refresh")
        self._refresh_prices()

    def action_analytics(self) -> None:
        """Navigate to analytics."""
        self.push_screen(AnalyticsScreen())

    def action_trades(self) -> None:
        """Navigate to trades."""
        self.push_screen(TradesScreen())

    def action_create_portfolio(self) -> None:
        """Create new portfolio."""
        # TODO: Show create portfolio modal
        pass

    def action_settings(self) -> None:
        """Navigate to settings."""
        self.push_screen(SettingsScreen())

    async def _refresh_prices_task(self) -> None:
        """Background task to refresh prices."""
        # TODO: Fetch prices from yfinance and update cache
        pass

    def _refresh_prices(self) -> None:
        """Synchronously refresh prices."""
        # TODO: Implement price refresh logic
        pass

    def _update_positions_table(self) -> None:
        """Update the positions table with latest data."""
        # TODO: Update DataTable with current positions
        pass


def run() -> None:
    """Run the Portfolio Manager application."""
    app = PortfolioManagerApp()
    app.run()


if __name__ == "__main__":
    run()
