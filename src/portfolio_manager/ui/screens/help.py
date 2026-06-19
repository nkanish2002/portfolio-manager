"""Help screen -- auto-generated from BINDINGS across all screens.

Displays a scrollable keybinding reference organized by screen.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static


class HelpScreen(Screen):
    """Help screen auto-generated from all registered screen BINDINGS."""

    CSS = """
    HelpScreen {
        background: #0F172A;
    }

    #help-title {
        text-align: center;
        width: 100%;
        padding: 1;
        color: #10B981;
        text-style: bold;
    }

    #help-content {
        width: 100%;
        height: 100%;
    }

    .screen-group {
        margin: 1 2;
        border: solid #334155;
        padding: 1 2;
    }

    .screen-title {
        color: #10B981;
        text-style: bold;
        margin-bottom: 1;
    }

    .binding-row {
        margin: 0 1;
    }

    .binding-key {
        color: #F59E0B;
        text-style: bold;
        width: 8;
    }

    .binding-desc {
        color: #E2E8F0;
    }

    #help-footer {
        text-align: center;
        color: #94A3B8;
        margin: 1 0;
    }
    """

    # Class-level registry: (title, screen_class)
    _registry: list[tuple[str, type]] = []

    @classmethod
    def register_screen(cls, title: str, screen_class: type) -> None:
        """Register a screen class for help-screen inclusion."""
        cls._registry.append((title, screen_class))

    def _collect_bindings(self, screen_class: type) -> list[tuple[str, str]]:
        """Extract (key, action_label) pairs from a screen's BINDINGS."""
        bindings: list[tuple[str, str]] = []
        for b in getattr(screen_class, "BINDINGS", []):
            if isinstance(b, Binding) and b.priority is not True:
                bindings.append((b.key, b.description))
        return bindings

    def on_mount(self) -> None:
        """Collect bindings from all registered screens."""
        self._sections: list[tuple[str, list[tuple[str, str]]]] = []
        for title, screen_class in HelpScreen._registry:
            bindings = self._collect_bindings(screen_class)
            if bindings:
                self._sections.append((title, bindings))

    def compose(self) -> ComposeResult:
        """Compose the help layout."""
        yield Header()
        yield Label("KEYBOARD SHORTCUTS", id="help-title")

        with ScrollableContainer(id="help-content"):
            if not self._sections:
                yield Label("No keybindings registered.", id="help-footer")
            else:
                for screen_title, bindings in self._sections:
                    with Container(classes="screen-group"):
                        yield Label(screen_title, classes="screen-title")
                        for key, desc in bindings:
                            with Container(classes="binding-row"):
                                yield Static(f"[{key}]", classes="binding-key")
                                yield Label(desc, classes="binding-desc")

        yield Label("[Esc] or [Q] to close", id="help-footer")
        yield Footer()

    def action_back(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()
