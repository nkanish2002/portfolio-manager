"""Settings screen — user preferences and configuration."""

from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Input, Static, Button
from textual.binding import Binding
from textual.containers import Container, Vertical


class SettingsScreen(Screen):
    """Settings screen for user preferences."""

    BINDINGS = [
        Binding("t", "toggle_theme", "Toggle Theme"),
        Binding("d", "default_portfolio", "Default Portfolio"),
        Binding("r", "refresh_interval", "Refresh Interval"),
        Binding("s", "data_source", "Data Source"),
        Binding("?", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        """Initialize settings screen."""
        super().__init__()
        self.current_theme = "dark"
        self.refresh_interval = 30  # seconds
        self.data_source = "yfinance"

    def compose(self):
        """Compose the settings layout."""
        yield Header()
        
        with Container():
            yield Label("PORTFOLIO MANAGER > Settings", classes="header")
            
            # Theme setting
            yield Label("Theme", classes="accent")
            yield Label(f"Current: {self.current_theme} [DARK] [LIGHT]")
            
            # Refresh interval
            yield Label("")
            yield Label("Refresh Interval", classes="accent")
            yield Label(f"Current: {self.refresh_interval}s")
            input_ref = Input(str(self.refresh_interval), id="refresh-interval-input")
            input_ref.placeholder = "Enter interval in seconds"
            yield input_ref
            
            # Data source
            yield Label("")
            yield Label("Data Source", classes="accent")
            yield Label(f"Current: {self.data_source} [YFINANCE] [API_KEY]")
            
            # Database info
            yield Label("")
            yield Label("Database", classes="accent")
            yield Label("Type: SQLite")
            yield Label("Path: ./portfolio.db")
            
            # Action buttons
            yield Button("Save Settings", id="btn-save", variant="primary")
            yield Button("Reset to Defaults", id="btn-reset")
        
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-save":
            self.save_settings()
        elif event.button.id == "btn-reset":
            self.reset_settings()

    def action_toggle_theme(self) -> None:
        """Toggle between dark and light theme."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"

    def action_default_portfolio(self) -> None:
        """Set default portfolio."""
        # TODO: Show portfolio selector
        pass

    def action_refresh_interval(self) -> None:
        """Set refresh interval."""
        # TODO: Show interval selector
        pass

    def action_data_source(self) -> None:
        """Toggle data source."""
        sources = ["yfinance", "api_key"]
        idx = sources.index(self.data_source) if self.data_source in sources else 0
        self.data_source = sources[(idx + 1) % len(sources)]

    def save_settings(self) -> None:
        """Save current settings."""
        # TODO: Persist settings
        pass

    def reset_settings(self) -> None:
        """Reset settings to defaults."""
        self.current_theme = "dark"
        self.refresh_interval = 30
        self.data_source = "yfinance"
