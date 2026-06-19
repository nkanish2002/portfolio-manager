"""Base screen class with common functionality for all TUI screens."""

from textual.screen import Screen
from textual.app import App
from textual.widgets import Footer, Header
from textual.binding import Binding


class BaseScreen(Screen):
    """Base screen class with common functionality."""

    # Common keybindings for all screens
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "help", "Help", priority=True),
        Binding("esc", "go_back", "Back", priority=True),
    ]

    def __init__(self, app: App) -> None:
        """Initialize base screen.
        
        Args:
            app: The parent Textual app instance.
        """
        super().__init__()
        self.app = app

    def on_mount(self) -> None:
        """Set up common UI elements on mount."""
        # Header and footer are added by the app, not per-screen
        pass

    def action_go_back(self) -> None:
        """Handle back navigation."""
        # Default: do nothing (screens override this if they have navigation)
        pass

    def action_help(self) -> None:
        """Show help dialog."""
        # Default: show basic keybinding help
        self.app.push_screen("help")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
