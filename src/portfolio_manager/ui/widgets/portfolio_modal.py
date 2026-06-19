"""Portfolio modals — create and delete portfolios."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
)


class CreatePortfolioModal(ModalScreen):
    """Modal for creating a new portfolio."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Create"),
    ]

    CSS = """
    CreatePortfolioModal {
        align: center middle;
    }

    .modal-container {
        width: 60%;
        height: auto;
        background: $surface;
        border: solid $primary;
        padding: 2;
        margin: 1;
    }

    .modal-title {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }

    .modal-input {
        width: 100%;
        margin-bottom: 1;
    }

    .modal-actions {
        margin-top: 2;
        width: 100%;
        align: center middle;
    }
    """

    def __init__(self, session_factory: async_sessionmaker | None = None) -> None:
        """Initialize the create portfolio modal.

        Args:
            session_factory: Async session factory for DB access.
                Uses the global async_session if not provided.
        """
        super().__init__()
        self._session_factory = session_factory
        self._created_id: str | None = None

    def _get_session_factory(self) -> async_sessionmaker:
        """Return the DB session factory, falling back to the global."""
        if self._session_factory is not None:
            return self._session_factory
        from portfolio_manager.database import async_session

        return async_session

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        yield Header()

        with Container(classes="modal-container"):
            yield Label("Create New Portfolio", classes="modal-title")

            with Vertical():
                name_input = Input(
                    placeholder="Portfolio name (e.g., IRA, Taxable)", id="name-input"
                )
                name_input.focus()
                yield name_input

                desc_input = Input(placeholder="Description (optional)", id="desc-input")
                yield desc_input

                currency_input = Input("USD", placeholder="Currency", id="currency-input")
                yield currency_input

                yield Label("", id="error-msg", classes="negative")

                with Container(classes="modal-actions"):
                    yield Button("Create", variant="primary", id="btn-create")
                    yield Button("Cancel", id="btn-cancel")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-create":
            asyncio.create_task(self._handle_create())
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    async def _handle_create(self) -> None:
        """Create the portfolio asynchronously."""
        from portfolio_manager.services.portfolios import _create_portfolio

        name = self.query_one("#name-input", Input).value.strip()
        description = self.query_one("#desc-input", Input).value.strip() or None
        currency = self.query_one("#currency-input", Input).value.strip() or "USD"

        # Validate
        if not name:
            self.query_one("#error-msg", Label).update("Name is required")
            self.query_one("#name-input", Input).focus()
            return

        try:
            async with self._get_session_factory() as session:
                result = await _create_portfolio(session, name, description, currency)
            self._created_id = result["id"]
            self.dismiss(result)
            self.notify(f"Portfolio '{name}' created!", title="Success")
        except Exception as e:
            error_msg = str(e)
            if "UNIQUE constraint" in error_msg or "unique" in error_msg.lower():
                error_msg = "A portfolio with this name already exists"
            self.query_one("#error-msg", Label).update(error_msg)

    def action_cancel(self) -> None:
        """Handle cancel key."""
        self.dismiss(None)


class DeletePortfolioModal(ModalScreen):
    """Modal for confirming portfolio deletion."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("y", "confirm_delete", "Delete"),
    ]

    CSS = """
    DeletePortfolioModal {
        align: center middle;
    }

    .modal-container {
        width: 50%;
        height: auto;
        background: $surface;
        border: solid $error;
        padding: 2;
        margin: 1;
    }

    .modal-title {
        text-align: center;
        color: $error;
        text-style: bold;
        margin-bottom: 1;
    }

    .modal-message {
        text-align: center;
        margin-bottom: 2;
    }

    .modal-actions {
        margin-top: 2;
        width: 100%;
        align: center middle;
    }
    """

    def __init__(
        self,
        portfolio_name: str,
        portfolio_id: str,
        session_factory: async_sessionmaker | None = None,
    ) -> None:
        """Initialize the delete modal.

        Args:
            portfolio_name: Name of the portfolio to delete.
            portfolio_id: ID of the portfolio to delete.
            session_factory: Async session factory for DB access.
                Uses the global async_session if not provided.
        """
        super().__init__()
        self._portfolio_name = portfolio_name
        self._portfolio_id = portfolio_id
        self._session_factory = session_factory

    def _get_session_factory(self) -> async_sessionmaker:
        """Return the DB session factory, falling back to the global."""
        if self._session_factory is not None:
            return self._session_factory
        from portfolio_manager.database import async_session

        return async_session

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        yield Header()

        with Container(classes="modal-container"):
            yield Label("Delete Portfolio", classes="modal-title")

            with Vertical():
                yield Label(
                    f"Are you sure you want to delete '{self._portfolio_name}'?",
                    classes="modal-message",
                )
                yield Label(
                    "This action cannot be undone. All positions and transactions will be lost.",
                    classes="negative",
                )

                with Container(classes="modal-actions"):
                    yield Button("Delete", variant="error", id="btn-delete")
                    yield Button("Cancel", id="btn-cancel")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-delete":
            asyncio.create_task(self._handle_delete())
        elif event.button.id == "btn-cancel":
            self.dismiss(False)

    async def _handle_delete(self) -> None:
        """Delete the portfolio asynchronously."""
        from portfolio_manager.services.portfolios import _delete_portfolio

        try:
            async with self._get_session_factory() as session:
                result = await _delete_portfolio(session, self._portfolio_id)
            self.dismiss(result)
            self.notify(
                f"Portfolio '{self._portfolio_name}' deleted!",
                title="Success" if result else "Not Found",
            )
        except Exception as e:
            self.notify(f"Delete failed: {e}", title="Error", severity="error")
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Handle cancel key."""
        self.dismiss(False)

    def action_confirm_delete(self) -> None:
        """Handle y key."""
        self.notify("Press Enter to confirm deletion", title="Confirm")
