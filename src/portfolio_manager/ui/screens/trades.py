"""Trades screen — trade history and audit trail."""

from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, Button
from textual.binding import Binding
from textual.containers import Container
from typing import Optional
from datetime import datetime


class TradesScreen(Screen):
    """Trades screen with trade history and audit trail."""

    BINDINGS = [
        Binding("b", "buy", "Buy"),
        Binding("s", "sell", "Sell"),
        Binding("e", "export", "Export CSV"),
        Binding("?", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, portfolio_id: Optional[int] = None) -> None:
        """Initialize trades screen.
        
        Args:
            portfolio_id: Portfolio ID to show trades for.
        """
        super().__init__()
        self.portfolio_id = portfolio_id
        self.current_filter = "ALL"  # ALL, BUY, SELL, DIVIDEND, FEE

    def compose(self):
        """Compose the trades layout."""
        yield Header()
        
        with Container():
            yield Label("PORTFOLIO MANAGER > Trades", classes="header")
            
            # Trade summary
            yield Label("Total Gains: $12,345.67  Total Losses: -$3,456.78  Net P&L: $8,888.89", classes="positive")
            yield Label("")
            
            # Filter controls
            yield Label(f"Filter: {self.current_filter} [ALL] [BUY] [SELL] [DIVIDEND] [FEE]")
            yield Label("")
            
            # Trades table
            trades_table = DataTable()
            trades_table.add_columns("Date", "Symbol", "Type", "Qty", "Price", "Fees", "P&L", "Notes")
            
            # Sample trades
            trades_table.add_row("2026-06-18", "AAPL", "BUY", "100", "$198.5", "$0", "—", "Initial purchase")
            trades_table.add_row("2026-06-17", "MSFT", "BUY", "50", "$420.1", "$0", "—", "Added position")
            trades_table.add_row("2026-06-15", "SPY", "BUY", "200", "$540.2", "$0", "—", "Index exposure")
            trades_table.add_row("2026-06-14", "TSLA", "SELL", "50", "$280.3", "$5", "+$1,250", "Partial profit")
            trades_table.add_row("2026-06-10", "AAPL", "DIVIDEND", "100", "$0.24", "$0", "+$24", "Q2 dividend")
            
            yield trades_table
            
            # Action buttons
            yield Button("Buy Position", id="btn-buy", variant="primary")
            yield Button("Sell Position", id="btn-sell")
            yield Button("Export CSV", id="btn-export")
        
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-buy":
            self.buy_action()
        elif event.button.id == "btn-sell":
            self.sell_action()
        elif event.button.id == "btn-export":
            self.export_csv()

    def action_buy(self) -> None:
        """Buy action."""
        self.buy_action()

    def action_sell(self) -> None:
        """Sell action."""
        self.sell_action()

    def action_export(self) -> None:
        """Export trades to CSV."""
        self.export_csv()

    def buy_action(self) -> None:
        """Show buy dialog."""
        # TODO: Implement buy modal
        pass

    def sell_action(self) -> None:
        """Show sell dialog."""
        # TODO: Implement sell modal
        pass

    def export_csv(self) -> None:
        """Export trade history to CSV."""
        # TODO: Implement CSV export
        pass

    def filter_trades(self, trade_type: str) -> None:
        """Filter trades by type.
        
        Args:
            trade_type: Filter type (ALL, BUY, SELL, DIVIDEND, FEE)
        """
        self.current_filter = trade_type
        # TODO: Apply filter to table
        pass
