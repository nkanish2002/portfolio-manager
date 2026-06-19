"""Trade modals — buy and sell with validation + P&L preview."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Select,
)


class BuyTradeModal(ModalScreen):
    """Modal for buying a security."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Buy"),
    ]

    CSS = """
    BuyTradeModal {
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

    .modal-field {
        width: 100%;
        margin-bottom: 1;
    }

    .modal-field > Label {
        width: 100%;
        margin-left: 1;
        margin-bottom: 0;
        color: $accent;
        text-style: bold;
    }

    .preview-panel {
        width: 100%;
        background: #1E293B;
        border: solid #334155;
        padding: 1 2;
        margin-bottom: 1;
        margin-top: 1;
    }

    .preview-row {
        width: 100%;
        margin: 0;
    }

    .preview-row Label {
        margin: 0;
    }

    .preview-label {
        width: 40%;
        color: #94A3B8;
    }

    .preview-value {
        width: 60%;
        text-align: right;
        color: #E2E8F0;
    }

    .modal-actions {
        margin-top: 1;
        width: 100%;
        align: center middle;
    }

    #buy-error {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, session_factory: async_sessionmaker | None = None) -> None:
        """Initialize the buy trade modal.

        Args:
            session_factory: Async session factory for DB access.
        """
        super().__init__()
        self._session_factory = session_factory
        self._portfolio_id: str | None = None
        self._total_cost: float = 0
        self._errors: list[str] = []

    def _get_session_factory(self) -> async_sessionmaker:
        """Return the DB session factory."""
        if self._session_factory is not None:
            return self._session_factory
        from portfolio_manager.database import async_session
        return async_session

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        yield Header()

        with Container(classes="modal-container"):
            yield Label("BUY SECURITY", classes="modal-title")

            with Vertical():
                symbol_input = Input(
                    placeholder="Ticker symbol (e.g., AAPL)",
                    id="symbol-input",
                )
                symbol_input.focus()
                yield symbol_input

                qty_input = Input(
                    placeholder="Quantity",
                    id="qty-input",
                    valid_empty=True,
                )
                qty_input.add_class("modal-field")
                yield qty_input

                price_input = Input(
                    placeholder="Price per share",
                    id="price-input",
                    valid_empty=True,
                )
                price_input.add_class("modal-field")
                yield price_input

                fees_input = Input(
                    placeholder="Commission fees (optional, default: 0)",
                    id="fees-input",
                    valid_empty=True,
                )
                fees_input.value = "0"
                fees_input.add_class("modal-field")
                yield fees_input

                # P&L preview panel
                preview = Container(classes="preview-panel", id="buy-preview")
                yield Label("Transaction Summary", classes="modal-title")
                yield Label("Enter symbol, quantity, and price to see summary",
                           id="buy-preview-text", classes="accent")
                preview.add_class("modal-field")
                yield preview

                yield Label("", id="buy-error", classes="negative")

                with Container(classes="modal-actions"):
                    yield Button("Buy", variant="primary", id="btn-buy")
                    yield Button("Cancel", id="btn-cancel")

        yield Footer()

    def on_mount(self) -> None:
        """Set up input watchers."""
        pass  # CSS classes handled in compose

    def on_input_changed(self, event: Input.Changed) -> None:
        """Recalculate preview on input changes."""
        asyncio.create_task(self._update_preview())

    async def _update_preview(self) -> None:
        """Update the preview panel with calculated values."""
        symbol = self.query_one("#symbol-input", Input).value.strip()
        qty_str = self.query_one("#qty-input", Input).value.strip()
        price_str = self.query_one("#price-input", Input).value.strip()
        fees_str = self.query_one("#fees-input", Input).value.strip() or "0"

        if not symbol or not qty_str or not price_str:
            self.query_one("#buy-preview-text", Label).update(
                "Enter symbol, quantity, and price to see summary"
            )
            return

        try:
            qty = float(qty_str)
            price = float(price_str)
            fees = float(fees_str)
        except ValueError:
            self.query_one("#buy-preview-text", Label).update(
                "Invalid input — enter numbers for qty and price"
            )
            return

        if qty <= 0 or price <= 0:
            self.query_one("#buy-preview-text", Label).update(
                "Quantity and price must be positive"
            )
            return

        total_cost = qty * price + fees
        self._total_cost = total_cost

        self.query_one("#buy-preview-text", Label).update(
            f"{qty:.2f} x ${price:.2f} + ${fees:.2f} fees = ${total_cost:.2f} total"
        )

    async def _validate_and_execute(self) -> bool:
        """Validate inputs and attempt the buy."""
        symbol = self.query_one("#symbol-input", Input).value.strip()
        qty_str = self.query_one("#qty-input", Input).value.strip()
        price_str = self.query_one("#price-input", Input).value.strip()
        fees_str = self.query_one("#fees-input", Input).value.strip() or "0"

        error_label = self.query_one("#buy-error", Label)

        # Validate required fields
        if not symbol:
            error_label.update("Symbol is required")
            self.query_one("#symbol-input", Input).focus()
            return False

        try:
            qty = float(qty_str)
            price = float(price_str)
            fees = float(fees_str)
        except (ValueError, TypeError):
            error_label.update("Quantity, price, and fees must be valid numbers")
            self.query_one("#qty-input", Input).focus()
            return False

        if qty <= 0:
            error_label.update("Quantity must be greater than 0")
            self.query_one("#qty-input", Input).focus()
            return False

        if price <= 0:
            error_label.update("Price must be greater than 0")
            self.query_one("#price-input", Input).focus()
            return False

        if fees < 0:
            error_label.update("Fees cannot be negative")
            self.query_one("#fees-input", Input).focus()
            return False

        # Check cash availability if portfolio_id is set
        if self._portfolio_id:
            try:
                from portfolio_manager.services.trades import TradeService
                available = await TradeService().get_portfolio_available_cash(
                    self._portfolio_id
                )
                total_cost = qty * price + fees
                if total_cost > available + 0.01:  # small float tolerance
                    error_label.update(
                        f"Insufficient funds. Available: ${available:.2f}, "
                        f"Required: ${total_cost:.2f}"
                    )
                    return False
            except Exception:
                pass  # If we can't check cash, allow the buy (conservative)

        return True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-buy":
            asyncio.create_task(self._handle_buy())
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    async def _handle_buy(self) -> None:
        """Execute the buy transaction."""
        symbol = self.query_one("#symbol-input", Input).value.strip()
        qty = float(self.query_one("#qty-input", Input).value.strip())
        price = float(self.query_one("#price-input", Input).value.strip())
        fees = float(self.query_one("#fees-input", Input).value.strip() or "0")

        error_label = self.query_one("#buy-error", Label)

        # Check cash availability
        if self._portfolio_id:
            try:
                from portfolio_manager.services.trades import TradeService
                available = await TradeService().get_portfolio_available_cash(
                    self._portfolio_id
                )
                total_cost = qty * price + fees
                if total_cost > available + 0.01:
                    error_label.update(
                        f"Insufficient funds. Available: ${available:.2f}, "
                        f"Required: ${total_cost:.2f}"
                    )
                    return
            except Exception:
                pass

        try:
            from portfolio_manager.models.transaction import TransactionType
            from portfolio_manager.services.trades import TradeService

            result = await TradeService().add_transaction(
                portfolio_id=self._portfolio_id,
                asset_id=symbol.upper(),
                transaction_type=TransactionType.BUY,
                quantity=qty,
                price=price,
                fees=fees,
                notes=f"Buy {qty:.0f} x {symbol.upper()} @ ${price:.2f}",
            )
            self.query_one("#buy-error", Label).update("")
            self.notify(
                f"Bought {qty:.0f} x {symbol.upper()} @ ${price:.2f}",
                title="Trade Executed",
                severity="information",
            )
            self.dismiss(result)
        except Exception as e:
            error_label.update(f"Trade failed: {e}")

    def action_cancel(self) -> None:
        """Handle cancel key."""
        self.dismiss(None)

    def set_portfolio_id(self, portfolio_id: str) -> None:
        """Set the portfolio ID for cash availability check."""
        self._portfolio_id = portfolio_id


class SellTradeModal(ModalScreen):
    """Modal for selling a security position."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Sell"),
    ]

    CSS = """
    SellTradeModal {
        align: center middle;
    }

    .modal-container {
        width: 60%;
        height: auto;
        background: $surface;
        border: solid $error;
        padding: 2;
        margin: 1;
    }

    .modal-title {
        text-align: center;
        color: #EF4444;
        text-style: bold;
        margin-bottom: 1;
    }

    .modal-field {
        width: 100%;
        margin-bottom: 1;
    }

    .modal-field > Label {
        width: 100%;
        margin-left: 1;
        margin-bottom: 0;
        color: #EF4444;
        text-style: bold;
    }

    .position-info {
        width: 100%;
        background: #1E293B;
        border: solid #334155;
        padding: 1 2;
        margin-bottom: 1;
    }

    .position-info Label {
        margin: 0;
    }

    .sell-preview-panel {
        width: 100%;
        background: #1E293B;
        border: solid #334155;
        padding: 1 2;
        margin-bottom: 1;
    }

    .preview-row {
        width: 100%;
        margin: 0;
    }

    .preview-label {
        width: 50%;
        color: #94A3B8;
    }

    .preview-value {
        width: 50%;
        text-align: right;
    }

    .positive {
        color: #22C55E;
    }

    .negative {
        color: #EF4444;
    }

    .modal-actions {
        margin-top: 1;
        width: 100%;
        align: center middle;
    }

    #sell-error {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, session_factory: async_sessionmaker | None = None) -> None:
        """Initialize the sell trade modal.

        Args:
            session_factory: Async session factory for DB access.
        """
        super().__init__()
        self._session_factory = session_factory
        self._portfolio_id: str | None = None
        self._positions: list[dict] = []
        self._selected_asset_id: str | None = None
        self._pnl: float = 0
        self._max_qty: float = 0.0

    def _get_session_factory(self) -> async_sessionmaker:
        """Return the DB session factory."""
        if self._session_factory is not None:
            return self._session_factory
        from portfolio_manager.database import async_session
        return async_session

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        yield Header()

        with Container(classes="modal-container"):
            yield Label("SELL POSITION", classes="modal-title")

            with Vertical():
                # Asset selector
                yield Label("Position", id="asset-label")
                asset_select = Select(
                    [(str(i), p["asset_id"]) for i, p in enumerate(self._positions)],
                    prompt="Select a position to sell",
                    id="asset-select",
                )
                asset_select.add_class("modal-field")
                yield asset_select

                # Position info
                pos_info = Container(classes="position-info", id="pos-info")
                yield pos_info

                # Qty input
                qty_input = Input(
                    placeholder="Quantity to sell",
                    id="qty-input",
                    valid_empty=True,
                )
                qty_input.add_class("modal-field")
                yield qty_input

                # Price input
                price_input = Input(
                    placeholder="Sell price per share",
                    id="price-input",
                    valid_empty=True,
                )
                price_input.add_class("modal-field")
                yield price_input

                # Fees input
                fees_input = Input(
                    placeholder="Commission fees (optional, default: 0)",
                    id="fees-input",
                    valid_empty=True,
                )
                fees_input.value = "0"
                fees_input.add_class("modal-field")
                yield fees_input

                # P&L preview
                preview = Container(classes="sell-preview-panel", id="sell-preview")
                yield Label("Projected Proceeds", classes="modal-title")
                yield Label("Enter quantity and price to see preview",
                           id="sell-preview-text", classes="accent")
                preview.add_class("modal-field")
                yield preview

                yield Label("", id="sell-error", classes="negative")

                with Container(classes="modal-actions"):
                    yield Button("Sell", variant="error", id="btn-sell")
                    yield Button("Cancel", id="btn-cancel")

        yield Footer()

    def on_mount(self) -> None:
        """Load positions and set up watchers."""
        self.call_later(self._load_positions)

    async def _load_positions(self) -> None:
        """Load available positions for the portfolio."""
        if not self._portfolio_id:
            self.query_one("#asset-label", Label).update("No portfolio selected")
            return

        try:
            from portfolio_manager.services.trades import TradeService
            service = TradeService()

            # List all positions by querying via the service
            # We need to get all positions for this portfolio
            from portfolio_manager.models.position import Position
            from portfolio_manager.database import async_session
            from sqlalchemy import select

            session_factory = self._get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Position).where(
                        Position.portfolio_id == self._portfolio_id,
                        Position.quantity > 0,
                    )
                )
                positions = result.scalars().all()

            self._positions = []
            options = []
            for p in positions:
                quantity = float(p.quantity) if p.quantity else 0
                if quantity > 0:
                    asset_id = str(p.asset_id)
                    avg_cost = float(p.avg_cost_basis) if p.avg_cost_basis else 0
                    self._positions.append({
                        "asset_id": asset_id,
                        "quantity": quantity,
                        "avg_cost_basis": avg_cost,
                    })
                    options.append((f"{asset_id} ({quantity:.0f} shares)", asset_id))

            if not options:
                self.query_one("#asset-label", Label).update("No sellable positions")
                return

            # Update the select widget - rebuild with new options
            asset_select = self.query_one("#asset-select", Select)
            new_options = [(f"{p['asset_id']} ({p['quantity']:.0f} shares)", p["asset_id"])
                          for p in self._positions]
            # Rebuild the Select widget with new options
            if new_options:
                new_select = Select(
                    [(label, value) for label, value in new_options],
                    prompt="Select a position to sell",
                    id="asset-select",
                )
                asset_select.replace_with(new_select)
                new_select.value = new_options[0][1]

        except Exception as e:
            self.query_one("#asset-label", Label).update(f"Error loading positions: {e}")

    def on_select_changed(self, event: Select.Changed) -> None:
        """When asset selection changes, update position info."""
        asset_id = event.value
        if not asset_id or not isinstance(asset_id, str):
            return
        self._selected_asset_id = asset_id

        for pos in self._positions:
            if pos["asset_id"] == asset_id:
                self._update_position_info(pos)
                break

        # Also update preview
        asyncio.create_task(self._update_preview())

    def _update_position_info(self, pos: dict) -> None:
        """Update the position info panel."""
        try:
            pos_container = self.query_one("#pos-info", Container)
            pos_container.remove_children()
            pos_container.mount(
                Label(f"Owned:     {pos['quantity']:.2f} shares"),
                Label(f"Avg Cost:   ${pos['avg_cost_basis']:.2f}"),
                Label(f"Cost Basis: ${pos['quantity'] * pos['avg_cost_basis']:.2f}"),
            )
            self._max_qty = pos["quantity"]
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Recalculate preview on input changes."""
        if self._selected_asset_id:
            asyncio.create_task(self._update_preview())

    async def _update_preview(self) -> None:
        """Update the sell preview panel with projected P&L."""
        if not self._selected_asset_id:
            return

        qty_str = self.query_one("#qty-input", Input).value.strip()
        price_str = self.query_one("#price-input", Input).value.strip()
        fees_str = self.query_one("#fees-input", Input).value.strip() or "0"

        if not qty_str or not price_str:
            self.query_one("#sell-preview-text", Label).update(
                "Enter quantity and price to see preview"
            )
            return

        try:
            qty = float(qty_str)
            price = float(price_str)
            fees = float(fees_str)
        except (ValueError, TypeError):
            self.query_one("#sell-preview-text", Label).update(
                "Invalid input"
            )
            return

        # Find the position
        pos_data = None
        for pos in self._positions:
            if pos["asset_id"] == self._selected_asset_id:
                pos_data = pos
                break

        if not pos_data:
            self.query_one("#sell-preview-text", Label).update("No position selected")
            return

        max_qty = pos_data["quantity"]
        avg_cost = pos_data["avg_cost_basis"]

        # Validate
        if qty <= 0 or price <= 0:
            self.query_one("#sell-preview-text", Label).update(
                "Quantity and price must be positive"
            )
            return

        if qty > self._max_qty:
            self.query_one("#sell-preview-text", Label).update(
                f"Cannot sell {qty:.2f} shares. Max: {self._max_qty:.2f} shares"
            )
            return

        # Calculate preview
        pos_data = None
        for pos in self._positions:
            if pos["asset_id"] == self._selected_asset_id:
                pos_data = pos
                break

        if not pos_data:
            self.query_one("#sell-preview-text", Label).update("No position selected")
            return

        avg_cost = pos_data["avg_cost_basis"]
        proceeds = price * qty
        cost_of_sold = avg_cost * qty
        pnl = proceeds - cost_of_sold - fees
        self._pnl = pnl

        remaining = self._max_qty - qty
        pnl_class = "positive" if pnl >= 0 else "negative"

        pnl_label = self.query_one("#sell-preview-text", Label)
        pnl_label.add_class(pnl_class)
        pnl_label.remove_class("positive", "negative")
        pnl_label.add_class(pnl_class)
        pnl_label.update(
            f"Proceeds: ${proceeds:.2f} | Cost: ${cost_of_sold:.2f} | "
            f"P&L: ${pnl:+.2f} | Remaining: {remaining:.2f} shares"
        )

    async def _handle_sell(self) -> None:
        """Execute the sell transaction."""
        error_label = self.query_one("#sell-error", Label)

        if not self._selected_asset_id:
            error_label.update("Please select a position to sell")
            return

        qty_str = self.query_one("#qty-input", Input).value.strip()
        price_str = self.query_one("#price-input", Input).value.strip()
        fees_str = self.query_one("#fees-input", Input).value.strip() or "0"

        try:
            qty = float(qty_str)
            price = float(price_str)
            fees = float(fees_str)
        except (ValueError, TypeError):
            error_label.update("Quantity and price must be valid numbers")
            return

        if qty <= 0:
            error_label.update("Quantity must be greater than 0")
            return

        if price <= 0:
            error_label.update("Price must be greater than 0")
            return

        # Get position to validate quantity
        pos_data = None
        for pos in self._positions:
            if pos["asset_id"] == self._selected_asset_id:
                pos_data = pos
                break

        if not pos_data or qty > pos_data["quantity"]:
            error_label.update(
                f"Cannot sell {qty:.2f} shares. Available: {pos_data['quantity']:.2f}"
                if pos_data
                else "Position not found"
            )
            return

        try:
            from portfolio_manager.services.trades import TradeService
            result = await TradeService().sell_position(
                portfolio_id=self._portfolio_id,
                asset_id=self._selected_asset_id,
                quantity=qty,
                price=price,
                fees=fees,
            )
            error_label.update("")
            pnl_str = f"${result['realized_pnl']:+.2f}"
            self.notify(
                f"Sold {qty:.0f} x {self._selected_asset_id} | P&L: {pnl_str}",
                title="Trade Executed",
                severity="information" if result["realized_pnl"] >= 0 else "warning",
            )
            self.dismiss(result)
        except Exception as e:
            error_label.update(f"Trade failed: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-sell":
            asyncio.create_task(self._handle_sell())
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Handle cancel key."""
        self.dismiss(None)

    def set_portfolio_id(self, portfolio_id: str) -> None:
        """Set the portfolio ID."""
        self._portfolio_id = portfolio_id
        self.call_later(self._load_positions)
