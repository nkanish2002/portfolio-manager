"""Settings screen -- user preferences and configuration.

Handles theme toggle, refresh interval, yfinance toggle, and default
portfolio selection. All settings persist to ``.settings.json``.
"""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.events import Mount
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from portfolio_manager.services.settings_service import (
    load_settings,
    reset_settings,
    save_settings,
    update_setting,
)


class SettingsScreen(Screen):
    """Settings screen for user preferences."""

    BINDINGS = [
        Binding("t", "toggle_theme", "Theme"),
        Binding("y", "toggle_yfinance", "Data Source"),
        Binding("i", "focus_interval", "Interval"),
        Binding("p", "select_portfolio", "Default Portfolio"),
        Binding("s", "save_settings", "Save"),
        Binding("?", "help", "Help"),
        Binding("Escape", "dismiss", "Back", show=False),
    ]

    CSS = """
    #settings-title {
        text-align: center;
        width: 100%;
        padding: 1;
        color: #10B981;
        text-style: bold;
    }

    .setting-group {
        margin-bottom: 2;
        padding: 0 2;
        border-left: heavy #334155;
        padding-left: 2;
    }

    .setting-label {
        color: #10B981;
        text-style: bold;
        margin-left: 1;
    }

    .setting-value {
        margin-left: 2;
    }

    .setting-value .on {
        color: #22C55E;
        text-style: bold;
    }

    .setting-value .off {
        color: #EF4444;
    }

    #refresh-input {
        width: 20;
        margin-left: 2;
    }

    #error-label {
        color: #EF4444;
        margin: 1 2;
        display: none;
    }

    #error-label.visible {
        display: block;
    }

    #portfolio-selector-display {
        color: #94A3B8;
        margin-left: 2;
    }

    #save-status {
        text-align: center;
        width: 100%;
        padding: 1;
        display: none;
    }

    #save-status.success {
        color: #22C55E;
        display: block;
    }

    #save-status.error {
        color: #EF4444;
        display: block;
    }

    Button {
        margin: 1 2;
    }

    #btn-save {
        background: #10B981;
        color: #000;
        border: solid #10B981;
    }

    #btn-save:hover {
        background: #059669;
    }

    #btn-reset {
        background: #1E293B;
        color: #94A3B8;
        border: solid #334155;
    }

    #btn-reset:hover {
        background: #334155;
        color: #E2E8F0;
    }
    """

    def __init__(
        self,
        session_factory: async_sessionmaker | None = None,
        portfolio_list: list[dict] | None = None,
    ) -> None:
        """Initialize settings screen.

        Args:
            session_factory: Optional DB session factory (unused here;
                portfolio list is passed directly for offline rendering).
            portfolio_list: Optional list of portfolio dicts for the
                default-portfolio selector modal.
        """
        super().__init__()
        self._settings = load_settings()
        self._portfolio_list = portfolio_list or []
        self._saved = False

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Compose the settings layout."""
        yield Header()

        with Container(id="settings-container"):
            yield Label("PORTFOLIO MANAGER > Settings", id="settings-title")

            # ---- Theme ----
            with Container(classes="setting-group"):
                yield Label("THEME", classes="setting-label")
                theme_value = f"[{self._settings['theme'].upper()}]"
                yield Label(
                    f"Active: {theme_value}  [Press T to toggle]",
                    id="theme-display",
                    classes="setting-value",
                )

            # ---- Refresh Interval ----
            with Container(classes="setting-group"):
                yield Label("REFRESH INTERVAL", classes="setting-label")
                yield Label(
                    f"Current: {self._settings['price_refresh_interval']}s  [Press I to change]",
                    id="interval-display",
                    classes="setting-value",
                )
                yield Label(
                    "Enter interval in seconds (5-3600):",
                    id="interval-hint",
                    classes="setting-value",
                )

            # ---- yfinance Toggle ----
            with Container(classes="setting-group"):
                yield Label("DATA SOURCE", classes="setting-label")
                yf = self._settings.get("yfinance_enabled", True)
                yf_label = "ENABLED (auto-refresh)" if yf else "DISABLED (cached only)"
                yf_cls = "on" if yf else "off"
                yield Label(
                    f"Source: {yf_label}  [Press Y to toggle]",
                    id="yfinance-display",
                    classes=f"setting-value {yf_cls}",
                )

            # ---- Default Portfolio ----
            with Container(classes="setting-group"):
                yield Label("DEFAULT PORTFOLIO", classes="setting-label")
                portfolio_display = self._format_default_portfolio()
                yield Label(
                    f"Default: {portfolio_display}  [Press P to select]",
                    id="portfolio-display",
                    classes="setting-value",
                )

            # ---- Error / Status ----
            yield Label("", id="error-label")
            yield Label("", id="save-status")

            # ---- Buttons ----
            with Container(id="settings-buttons"):
                yield Button("Save Settings", id="btn-save")
                yield Button("Reset to Defaults", id="btn-reset")

        yield Footer()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Clear any leftover error on mount."""
        self._hide_error()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-save":
            self.action_save_settings()
        elif event.button.id == "btn-reset":
            self._do_reset()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_toggle_theme(self) -> None:
        """Toggle between dark and light theme."""
        current = self._settings["theme"]
        self._settings["theme"] = "light" if current == "dark" else "dark"
        self._refresh_theme_display()
        self._hide_error()

    def action_toggle_yfinance(self) -> None:
        """Toggle yfinance auto-refresh on/off."""
        current = self._settings.get("yfinance_enabled", True)
        self._settings["yfinance_enabled"] = not current
        self._refresh_yfinance_display()
        self._hide_error()

    def action_focus_interval(self) -> None:
        """Show the refresh interval input for editing."""
        current = self._settings["price_refresh_interval"]
        interval_input = ModalIntervalInput(
            initial_value=current,
            on_submitted=self._on_interval_submitted,
        )
        self.push_screen(interval_input)

    def action_select_portfolio(self) -> None:
        """Show the portfolio selector modal."""
        if not self._portfolio_list:
            self.notify("No portfolios available. Create one first.", title="Info")
            return
        portfolio_modal = DefaultPortfolioSelector(
            portfolios=self._portfolio_list,
            current_default=self._settings.get("default_portfolio_id", ""),
            on_selected=self._on_default_portfolio_selected,
        )
        self.push_screen(portfolio_modal)

    def action_save_settings(self) -> None:
        """Save current settings to disk."""
        error = save_settings(self._settings)
        if error:
            self._show_error(error)
            self._save_status("error", "Failed to save settings.")
        else:
            self._hide_error()
            self._save_status("success", "Settings saved.")
            self._saved = True

    def action_help(self) -> None:
        """Show help notification."""
        self.notify(
            "Shortcuts:\n"
            "[T] Toggle Theme\n"
            "[Y] Toggle Data Source\n"
            "[I] Set Refresh Interval\n"
            "[P] Select Default Portfolio\n"
            "[S] Save Settings\n"
            "[Esc] Back",
            title="Settings Help",
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_interval_submitted(self, value: int) -> None:
        """Handle submitted interval from the modal."""
        self._settings["price_refresh_interval"] = value
        self._refresh_interval_display()
        self._hide_error()

    def _on_default_portfolio_selected(self, portfolio_id: str) -> None:
        """Handle selected default portfolio."""
        self._settings["default_portfolio_id"] = portfolio_id
        self._refresh_portfolio_display()
        self._hide_error()

    # ------------------------------------------------------------------
    # Display refresh
    # ------------------------------------------------------------------

    def _refresh_theme_display(self) -> None:
        try:
            el = self.query_one("#theme-display", Label)
            el.update(
                f"Active: [{self._settings['theme'].upper()}]  "
                "[Press T to toggle]"
            )
        except Exception:
            pass

    def _refresh_yfinance_display(self) -> None:
        try:
            el = self.query_one("#yfinance-display", Label)
            yf = self._settings.get("yfinance_enabled", True)
            label = "ENABLED (auto-refresh)" if yf else "DISABLED (cached only)"
            cls = "on" if yf else "off"
            el.update(f"Source: {label}  [Press Y to toggle]")
            el.remove_class("on", "off")
            el.add_class(cls)
        except Exception:
            pass

    def _refresh_interval_display(self) -> None:
        try:
            el = self.query_one("#interval-display", Label)
            el.update(
                f"Current: {self._settings['price_refresh_interval']}s  "
                "[Press I to change]"
            )
        except Exception:
            pass

    def _refresh_portfolio_display(self) -> None:
        try:
            self.query_one("#portfolio-display", Label).update(
                f"Default: {self._format_default_portfolio()}  [Press P to select]"
            )
        except Exception:
            pass

    def _format_default_portfolio(self) -> str:
        """Format the current default portfolio label."""
        pid = self._settings.get("default_portfolio_id", "")
        if not pid:
            return "(none — use first available)"
        for p in self._portfolio_list:
            if p.get("id") == pid:
                name = p.get("name", pid)
                count = p.get("position_count", "?")
                return f"{name} ({count} positions)"
        return f"Unknown ({pid[:12]}...)"

    # ------------------------------------------------------------------
    # Error / status helpers
    # ------------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        try:
            el = self.query_one("#error-label", Label)
            el.update(message)
            el.add_class("visible")
        except Exception:
            pass

    def _hide_error(self) -> None:
        try:
            el = self.query_one("#error-label", Label)
            el.update("")
            el.remove_class("visible")
        except Exception:
            pass

    def _save_status(self, kind: str, message: str) -> None:
        try:
            el = self.query_one("#save-status", Label)
            el.update(message)
            el.remove_class("success", "error")
            el.add_class(kind)
            # Auto-clear after 3 seconds
            self.set_timeout(3, lambda: el.remove_class("success", "error"))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def _do_reset(self) -> None:
        """Reset settings to defaults."""
        self._settings = reset_settings(self._settings)
        self._refresh_theme_display()
        self._refresh_yfinance_display()
        self._refresh_interval_display()
        self._refresh_portfolio_display()
        self._hide_error()
        self.notify("Settings reset to defaults. Press [S] to save.", title="Reset")


# ---------------------------------------------------------------------------
# Supporting modals
# ---------------------------------------------------------------------------


class ModalIntervalInput(ModalScreen):
    """Modal for entering a refresh interval value."""

    CSS = """
    ModalIntervalInput {
        align: center middle;
    }

    #interval-modal-title {
        text-align: center;
        width: 100%;
        color: #10B981;
        text-style: bold;
        margin-bottom: 1;
    }

    #interval-input {
        width: 20;
        margin-left: 2;
    }

    #interval-hint {
        color: #94A3B8;
        margin: 1 2;
    }

    #interval-error {
        color: #EF4444;
        margin: 1 2;
        display: none;
    }

    #interval-error.visible {
        display: block;
    }

    Button {
        margin: 1 2;
    }

    #btn-confirm {
        background: #10B981;
        color: #000;
        border: solid #10B981;
    }

    #btn-confirm:hover {
        background: #059669;
    }

    #btn-cancel {
        background: #1E293B;
        color: #94A3B8;
        border: solid #334155;
    }
    """

    def __init__(
        self,
        initial_value: int = 30,
        on_submitted: Callable[[int], None] | None = None,
    ) -> None:
        """Initialize the interval input modal.

        Args:
            initial_value: The current interval value.
            on_submitted: Callback called with the new interval on confirm.
        """
        super().__init__()
        self._initial_value = initial_value
        self._on_submitted = on_submitted

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        with Container(id="modal-container"):
            yield Label("REFRESH INTERVAL", id="interval-modal-title")
            yield Label(
                f"Current: {self._initial_value}s. Enter new value (5-3600):",
                id="interval-hint",
            )
            yield Input(
                str(self._initial_value),
                id="interval-input",
                placeholder="Enter seconds",
            )
            yield Label("", id="interval-error")
            with Container(id="modal-buttons"):
                yield Button("Confirm", id="btn-confirm")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self._submit()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Submit when Enter is pressed."""
        self._submit()

    def _submit(self) -> None:
        """Validate and submit the interval value."""
        raw = self.query_one("#interval-input", Input).value
        error_label = self.query_one("#interval-error", Label)

        try:
            value = int(raw)
        except (ValueError, TypeError):
            error_label.update("Please enter a whole number.")
            error_label.add_class("visible")
            return

        if value < 5 or value > 3600:
            error_label.update("Must be between 5 and 3600 seconds.")
            error_label.add_class("visible")
            return

        error_label.update("")
        error_label.remove_class("visible")
        self.dismiss(value)
        if self._on_submitted is not None:
            self._on_submitted(value)


class DefaultPortfolioSelector(ModalScreen):
    """Modal for selecting the default starting portfolio."""

    CSS = """
    DefaultPortfolioSelector {
        align: center middle;
    }

    #portfolio-modal-title {
        text-align: center;
        width: 100%;
        color: #10B981;
        text-style: bold;
        margin-bottom: 1;
    }

    #portfolio-list {
        width: 60;
        height: 10;
        border: solid #334155;
        margin: 1 2;
    }

    #portfolio-list .option--highlight {
        background: #1E3A5F;
        color: #10B981;
    }

    #selected-display {
        color: #94A3B8;
        margin: 1 2;
        padding: 0 2;
    }

    Button {
        margin: 1 2;
    }

    #btn-confirm {
        background: #10B981;
        color: #000;
        border: solid #10B981;
    }

    #btn-confirm:hover {
        background: #059669;
    }

    #btn-cancel {
        background: #1E293B;
        color: #94A3B8;
        border: solid #334155;
    }
    """

    def __init__(
        self,
        portfolios: list[dict],
        current_default: str,
        on_selected: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the portfolio selector.

        Args:
            portfolios: List of portfolio dicts with ``id`` and ``name``.
            current_default: The currently selected default portfolio ID.
            on_selected: Callback called with the new default portfolio ID.
        """
        super().__init__()
        self._portfolios = portfolios
        self._current_default = current_default
        self._on_selected = on_selected
        self._selected_id: str = current_default

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        with Container(id="modal-container"):
            yield Label("DEFAULT STARTING PORTFOLIO", id="portfolio-modal-title")
            yield Label(
                "Select which portfolio to load on startup (Esc to cancel):",
                id="portfolio-hint",
            )
            yield Label(
                f"Current: {self._format_current()}",
                id="selected-display",
            )
            with Container(id="modal-buttons"):
                yield Button("Confirm", id="btn-confirm")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.dismiss(self._selected_id)
            if self._on_selected is not None:
                self._on_selected(self._selected_id)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def _format_current(self) -> str:
        """Format the currently selected portfolio label."""
        if not self._selected_id:
            return "(none — use first available)"
        for p in self._portfolios:
            if p.get("id") == self._selected_id:
                name = p.get("name", self._selected_id)
                count = p.get("position_count", "?")
                return f"{name} ({count} positions)"
        return f"Unknown ({self._selected_id[:12]}...)"
