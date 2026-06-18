"""Dashboard screen — portfolio overview and position table."""

from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Button, Static
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.message import Message
from typing import Optional


class DashboardScreen(Screen):
    """Main dashboard screen showing portfolio overview and positions."""

    BINDINGS = [
        Binding("a", "analytics", "Analytics"),
        Binding("t", "trades", "Trades"),
        Binding("c", "create_portfolio", "Create Portfolio"),
        Binding("s", "settings", "Settings"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, portfolio_id: Optional[int] = None) -> None:
        """Initialize dashboard screen.
        
        Args:
            portfolio_id: Optional portfolio ID to display. None = show portfolio list.
        """
        super().__init__()
        self.portfolio_id = portfolio_id
        self.current_portfolio_index = 0

    def compose(self):
        """Compose the dashboard layout."""
        yield Header()
        
        with Container():
            # Portfolio selector
            yield Label("PORTFOLIO MANAGER", classes="header")
            yield Label("1) Wacky  2) Stable  [ESC] Switch", classes="accent")
            
            # Portfolio summary
            yield Label("Portfolio: Wacky (1/2)", classes="accent")
            yield Label("Total Value: $542,318.42    Day Change: +$1,234.56 (+0.23%)", classes="positive")
            yield Label("Positions: 15             Unrealized P&L: +$12,345.67")
            
            # Positions table
            yield Label("Symbol    Qty    Price    Value    P&L    Action")
            
            table = DataTable(id="positions-table")
            table.add_columns("Symbol", "Qty", "Price", "Value", "P&L", "Action")
            table.add_row("AAPL", "100", "$198.5", "$19,850", "+$1,230", "[S]ell")
            table.add_row("MSFT", "50", "$420.1", "$21,005", "+$2,100", "[S]ell")
            table.add_row("SPY", "200", "$540.2", "$108,040", "+$5,400", "[S]ell")
            yield table
            
            # Action buttons
            with Vertical():
                yield Button("Refresh Prices", id="btn-refresh", variant="primary")
                yield Button("Create Portfolio", id="btn-create")
                yield Button("Analytics", id="btn-analytics")
                yield Button("Trades", id="btn-trades")
                yield Button("Settings", id="btn-settings")
        
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-refresh":
            self.refresh_prices()
        elif event.button.id == "btn-create":
            self.create_portfolio()
        elif event.button.id == "btn-analytics":
            self.app.push_screen("analytics")
        elif event.button.id == "btn-trades":
            self.app.push_screen("trades")
        elif event.button.id == "btn-settings":
            self.app.push_screen("settings")

    def action_refresh(self) -> None:
        """Refresh prices."""
        self.refresh_prices()

    def refresh_prices(self) -> None:
        """Fetch latest prices and update the table."""
        # TODO: Implement price refresh logic
        pass

    def action_create_portfolio(self) -> None:
        """Create a new portfolio."""
        # TODO: Show create portfolio modal
        pass

    def action_analytics(self) -> None:
        """Navigate to analytics screen."""
        self.app.push_screen("analytics")

    def action_trades(self) -> None:
        """Navigate to trades screen."""
        self.app.push_screen("trades")

    def action_settings(self) -> None:
        """Navigate to settings screen."""
        self.app.push_screen("settings")
