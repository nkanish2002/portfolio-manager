"""Portfolio Manager -- Textual TUI Application.

Main entry point for the Textual-based portfolio management tool.
Provides dashboard, analytics, trades, and settings screens.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Label

from portfolio_manager.config import settings
from portfolio_manager.database import async_session as _default_session
from portfolio_manager.database import init_db
from portfolio_manager.services.settings_service import load_settings
from portfolio_manager.ui.screens.analytics import AnalyticsScreen
from portfolio_manager.ui.screens.dashboard import DashboardScreen
from portfolio_manager.ui.screens.settings import SettingsScreen
from portfolio_manager.ui.screens.trades import TradesScreen


# ---------------------------------------------------------------------------
# Theme CSS fragments
# ---------------------------------------------------------------------------

_THEME_CSS = {
    "dark": {
        "Screen": {"background": "#0F172A", "color": "#E2E8F0"},
        ".header": {"background": "#1E293B", "color": "#E2E8F0"},
        "DataTable .data-table--header": {"background": "#1E293B", "color": "#10B981"},
        "DataTable .data-table--selected": {"background": "#1E3A5F"},
        "Button": {"background": "#1E293B", "color": "#E2E8F0", "border": "solid #334155"},
        "Button:hover": {"background": "#334155", "color": "#10B981", "border": "solid #10B981"},
        "Button#primary": {"background": "#10B981", "color": "#000", "border": "none"},
        "Button#primary:hover": {"background": "#059669"},
        "DataTable": {"border": "solid #334155"},
        "Input": {"background": "#1E293B", "color": "#E2E8F0", "border": "solid #334155"},
        "Input:focus": {"border": "solid #10B981"},
        "#connection-indicator": {"background": "#1E293B", "color": "#F59E0B"},
        "#status-bar": {"background": "#334155", "color": "#94A3B8"},
        "#save-status": {"background": "transparent"},
    },
    "light": {
        "Screen": {"background": "#F8FAFC", "color": "#1E293B"},
        ".header": {"background": "#E2E8F0", "color": "#1E293B"},
        "DataTable .data-table--header": {"background": "#E2E8F0", "color": "#059669"},
        "DataTable .data-table--selected": {"background": "#DBEAFE"},
        "Button": {"background": "#E2E8F0", "color": "#1E293B", "border": "solid #CBD5E1"},
        "Button:hover": {"background": "#CBD5E1", "color": "#059669", "border": "solid #059669"},
        "Button#primary": {"background": "#059669", "color": "#fff", "border": "none"},
        "Button#primary:hover": {"background": "#047857"},
        "DataTable": {"border": "solid #CBD5E1"},
        "Input": {"background": "#F1F5F9", "color": "#1E293B", "border": "solid #CBD5E1"},
        "Input:focus": {"border": "solid #059669"},
        "#connection-indicator": {"background": "#E2E8F0", "color": "#D97706"},
        "#status-bar": {"background": "#CBD5E1", "color": "#475569"},
        "#save-status": {"background": "transparent"},
    },
}


class PortfolioManagerApp(App):
    """Main Textual application for portfolio management."""

    CSS = """
    Screen {
        background: #0F172A;
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

    .flash {
        color: #60A5FA;
        background: #1E3A5F;
    }

    DataTable .flash {
        background: #1E3A5F;
        color: #60A5FA;
    }

    #connection-indicator {
        width: 100%;
        height: 1;
        background: #1E293B;
        color: #F59E0B;
        padding: 0 2;
        content-align: center middle;
        text-align: center;
    }

    #connection-indicator.positive {
        color: #22C55E;
        background: #064E3B;
    }

    #connection-indicator.negative {
        color: #EF4444;
        background: #7F1D1D;
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

    DataTable .data-table--selected {
        background: #1E3A5F;
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

    #status-bar {
        width: 100%;
        height: 1;
        background: #334155;
        color: #94A3B8;
        padding: 0 1;
        content-align: center middle;
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

    def __init__(
        self,
        session_factory: async_sessionmaker | None = None,
        user_settings: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the application.

        Args:
            session_factory: Optional async session factory for DB access.
                Uses the global async_session from database module if not provided.
            user_settings: Optional pre-loaded settings dict.  Loaded from
                ``.settings.json`` on startup if not provided.
        """
        super().__init__()
        self._settings = user_settings or load_settings()
        self._db_initialized = False
        self._session_factory = session_factory or _default_session
        self._portfolio_ids: list[str] = []
        self._current_portfolio_index = 0
        self._refresh_interval: int = self._settings.get(
            "price_refresh_interval", 30
        )
        self._yfinance_enabled: bool = self._settings.get(
            "yfinance_enabled", True
        )
        self._default_portfolio_id: str = self._settings.get(
            "default_portfolio_id", ""
        )
        self._theme: str = self._settings.get("theme", "dark")

    @property
    def session_factory(self) -> async_sessionmaker:
        """Return the DB session factory."""
        return self._session_factory

    @property
    def settings(self) -> dict[str, Any]:
        """Return the current user settings."""
        return self._settings

    async def _initialize_database(self) -> None:
        """Initialize the database and prepare the session factory."""
        await init_db()
        self._db_initialized = True

    def _apply_theme(self, theme: str) -> None:
        """Apply a theme by injecting CSS rules."""
        if theme not in _THEME_CSS:
            return
        # Merge theme CSS on top of existing styles
        for selector, declarations in _THEME_CSS[theme].items():
            # Build CSS block: "selector { k: v; k: v; }"
            parts = "; ".join(f"{k}: {v}" for k, v in declarations.items())
            self.add_css(f"{selector} {{ {parts} }}")

    def compose(self) -> ComposeResult:
        """Compose the initial layout."""
        # Apply the loaded theme
        self._apply_theme(self._theme)
        yield DashboardScreen(
            session_factory=self._session_factory,
            refresh_interval=self._refresh_interval,
            yfinance_enabled=self._yfinance_enabled,
            default_portfolio_id=self._default_portfolio_id,
        )

    async def on_mount(self) -> None:
        """Initialize app on mount."""
        # Initialize database connection (async)
        await self._initialize_database()

        # Fetch initial portfolio list
        await self._load_portfolios()

        # If a default portfolio is set, switch to it
        if self._default_portfolio_id and self._portfolio_ids:
            try:
                idx = self._portfolio_ids.index(self._default_portfolio_id)
                self._current_portfolio_index = idx
                try:
                    dashboard = self.query_one(DashboardScreen)
                    dashboard.portfolio_id = self._default_portfolio_id
                    dashboard.current_portfolio_index = idx
                    dashboard.refresh_positions()
                except Exception:
                    pass
            except ValueError:
                # Default portfolio no longer exists — fall back to first
                self._default_portfolio_id = ""
                self._settings["default_portfolio_id"] = ""

    async def _load_portfolios(self) -> None:
        """Load portfolio list from the database."""
        if not self._db_initialized:
            return
        from portfolio_manager.services.portfolios import _list_portfolios

        try:
            async with self.session_factory() as session:
                portfolios = await _list_portfolios(session)
                self._portfolio_ids = [p["id"] for p in portfolios]
        except Exception:
            self._portfolio_ids = []

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_show_help(self) -> None:
        """Show help dialog."""
        self.notify(
            "Shortcuts: [R] Refresh | [C] Create Portfolio | "
            "[A] Analytics | [T] Trades | [S] Settings | "
            "[1-9] Switch Portfolio | [Q] Quit",
            title="Help",
        )

    def action_refresh(self) -> None:
        """Refresh all prices."""
        self.notify("Refreshing prices... (bypassing cache)", title="Refresh")
        try:
            dashboard = self.query_one(DashboardScreen)
            dashboard.action_refresh()
        except Exception:
            pass

    def action_analytics(self) -> None:
        """Navigate to analytics."""
        self.push_screen(AnalyticsScreen(session_factory=self._session_factory))

    def action_trades(self) -> None:
        """Navigate to trades."""
        portfolio_id = None
        if self._portfolio_ids:
            idx = self._current_portfolio_index % len(self._portfolio_ids)
            portfolio_id = self._portfolio_ids[idx]
        self.push_screen(TradesScreen(portfolio_id=portfolio_id))

    def action_create_portfolio(self) -> None:
        """Show create portfolio modal."""
        from portfolio_manager.ui.widgets.portfolio_modal import CreatePortfolioModal

        def on_created(result) -> None:
            if result:
                self._portfolio_ids.append(result["id"])
                self._current_portfolio_index = len(self._portfolio_ids) - 1

        self.push_screen(
            CreatePortfolioModal(session_factory=self._session_factory),
            on_created,
        )

    def action_settings(self) -> None:
        """Show settings screen."""
        # Build portfolio list for the selector
        portfolio_list = []
        if self._portfolio_ids:
            try:
                from portfolio_manager.services.portfolios import _list_portfolios

                async def _fetch():
                    async with self.session_factory() as session:
                        return await _list_portfolios(session)

                portfolio_list = asyncio.run(_fetch())
            except Exception:
                portfolio_list = []

        # Pass current settings so the screen shows live values
        settings_screen = SettingsScreen(
            session_factory=self._session_factory,
            portfolio_list=portfolio_list,
        )

        def on_saved(_result=None) -> None:
            """Called after the user saves settings."""
            # Apply the new theme immediately
            theme = settings_screen._settings.get("theme", "dark")
            self._apply_theme(theme)

        self.push_screen(settings_screen, on_saved)

    def _switch_portfolio(self, index: int) -> None:
        """Switch to a portfolio by index (1-based key, 0-based internally)."""
        if not self._portfolio_ids:
            self.notify("No portfolios available.", title="Info")
            return
        idx = (index - 1) % len(self._portfolio_ids)
        self._current_portfolio_index = idx
        self.notify(f"Switched to portfolio #{idx + 1}", title="Portfolio")
        try:
            dashboard = self.query_one(DashboardScreen)
            portfolio_id = self._portfolio_ids[idx]
            dashboard.portfolio_id = portfolio_id
            dashboard.current_portfolio_index = idx
            dashboard.refresh_positions()
        except Exception:
            pass


def run() -> None:
    """Run the Portfolio Manager application."""
    app = PortfolioManagerApp()
    app.run()


if __name__ == "__main__":
    run()
