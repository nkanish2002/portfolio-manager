"""Trades screen — trade history with pagination, filters, and export."""

import asyncio
import csv
import os

from sqlalchemy.ext.asyncio import async_sessionmaker
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    Button,
    Static,
)
from typing import Optional


class TradesScreen(Screen):
    """Trades screen with trade history, pagination, filters, and export."""

    BINDINGS = [
        Binding("b", "buy", "Buy"),
        Binding("s", "sell", "Sell"),
        Binding("e", "export", "Export CSV"),
        Binding("escape", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    FILTERS = ["ALL", "BUY", "SELL", "DIVIDEND", "FEE"]

    CSS = """
    TradesScreen {
        background: #000;
    }

    .trades-container {
        width: 100%;
        height: 100%;
        layout: vertical;
    }

    .trades-header {
        width: 100%;
        height: auto;
        background: #1E293B;
        color: #E2E8F0;
        text-align: center;
        padding: 1;
    }

    .summary-row {
        width: 100%;
        padding: 0 2;
        margin: 0;
    }

    .summary-row Label {
        margin: 0 1;
    }

    .filter-row {
        width: 100%;
        height: auto;
        padding: 0 2;
        margin: 0;
    }

    .filter-row Button {
        margin: 0 0.5;
        min-width: 10;
    }

    .filter-row Button--button--variant-primary {
        background: #10B981;
        color: #000;
    }

    .filter-row Button--button--variant-warning {
        background: #F59E0B;
        color: #000;
    }

    #trades-table {
        width: 100%;
        height: auto;
    }

    .pagination-bar {
        width: 100%;
        height: auto;
        padding: 0 2;
        margin: 0;
        background: #1E293B;
    }

    .pagination-bar Label {
        margin: 0 1;
    }

    .action-row {
        width: 100%;
        height: auto;
        padding: 0 2;
        margin: 1 0;
    }

    .action-row Button {
        margin: 0 0.5;
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

    DataTable .data-table--hover {
        background: #1E293B;
    }
    """

    def __init__(
        self,
        portfolio_id: Optional[str] = None,
        session_factory: async_sessionmaker | None = None,
    ) -> None:
        """Initialize trades screen.

        Args:
            portfolio_id: Portfolio ID to show trades for.
            session_factory: Async session factory for DB access.
        """
        super().__init__()
        self.portfolio_id = portfolio_id
        self.current_filter = "ALL"
        self.current_page = 1
        self.page_size = 50
        self._trades_data: dict = {}
        self._total_trades = 0
        self._total_pages = 0
        self._session_factory = session_factory
        self._positions_cache: dict[str, dict] = {}

    def _get_session_factory(self) -> async_sessionmaker:
        """Return the DB session factory."""
        if self._session_factory is not None:
            return self._session_factory
        from portfolio_manager.database import async_session
        return async_session

    def on_mount(self) -> None:
        """Load trade data on mount."""
        if self.portfolio_id:
            self.call_later(self._load_trades)
        else:
            self._show_no_portfolio()

    def _show_no_portfolio(self) -> None:
        """Show message when no portfolio is selected."""
        try:
            table = self.query_one("#trades-table", DataTable)
            table.clear()
            summary = self.query_one("#trades-summary", Label)
            summary.update("No portfolio selected")
            summary.remove_class("positive", "negative", "warning")
            summary.add_class("warning")
            page_info = self.query_one("#page-info", Label)
            page_info.update("No data")
        except Exception:
            pass

    async def _load_trades(self) -> None:
        """Load trades from the database."""
        if not self.portfolio_id:
            return

        try:
            from portfolio_manager.services.trades import TradeService

            service = TradeService()
            self._trades_data = await service.list_trades(
                portfolio_id=self.portfolio_id,
                trade_type=self.current_filter if self.current_filter != "ALL" else None,
                page=self.current_page,
                page_size=self.page_size,
            )
            self._total_trades = self._trades_data.get("total", 0)
            self._total_pages = self._trades_data.get("total_pages", 1)

            # Also load trades summary
            summary = await service.get_trades_summary(self.portfolio_id)

            # Load positions for P&L calculation
            await self._load_positions()

            # Update UI
            self.call_from_thread(
                self._update_trades_table,
                self._trades_data.get("trades", []),
            )
            self.call_from_thread(
                self._update_summary,
                summary,
            )
            self.call_from_thread(
                self._update_pagination,
                self.current_page,
                self._total_pages,
                self._total_trades,
            )
        except Exception as e:
            self.notify(f"Failed to load trades: {e}", title="Error", severity="error")

    async def _load_positions(self) -> None:
        """Cache current positions for P&L calculation."""
        try:
            from portfolio_manager.models.position import Position
            from sqlalchemy import select

            session_factory = self._get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Position).where(
                        Position.portfolio_id == self.portfolio_id,
                    )
                )
                positions = result.scalars().all()
                self._positions_cache = {
                    str(p.asset_id): {
                        "quantity": float(p.quantity) if p.quantity else 0,
                        "avg_cost_basis": float(p.avg_cost_basis) if p.avg_cost_basis else 0,
                    }
                    for p in positions
                }
        except Exception:
            self._positions_cache = {}

    def _update_trades_table(self, trades: list[dict]) -> None:
        """Update the trades DataTable."""
        table = self.query_one("#trades-table", DataTable)
        table.clear()
        table.add_columns("Date", "Type", "Symbol", "Qty", "Price", "Fees", "Total", "Notes")

        for trade in trades:
            trade_type = trade.get("type", "BUY")
            symbol = trade.get("asset_id", "???")
            qty = trade.get("quantity", 0)
            price = trade.get("price", 0)
            fees = trade.get("fees", 0)
            total = qty * price + fees if trade_type == "BUY" else qty * price - fees
            notes = trade.get("notes", "") or ""

            # Format total with color
            total_str = f"${total:,.2f}"
            if trade_type == "SELL":
                table.add_row(
                    trade["date"],
                    trade_type,
                    symbol,
                    f"{qty:.2f}",
                    f"${price:.2f}",
                    f"${fees:.2f}",
                    total_str,
                    notes[:30],
                )
            else:
                table.add_row(
                    trade["date"],
                    trade_type,
                    symbol,
                    f"{qty:.2f}",
                    f"${price:.2f}",
                    f"${fees:.2f}",
                    f"${total:,.2f}",
                    notes[:30],
                )

    def _update_summary(self, summary: dict) -> None:
        """Update the trades summary."""
        try:
            summary_label = self.query_one("#trades-summary", Label)
            total_buys = summary.get("total_buys", 0)
            total_sells = summary.get("total_sells", 0)
            total_trades = summary.get("total_trades", 0)

            summary_label.update(
                f"Total Trades: {total_trades} | Buys: {total_buys} | Sells: {total_sells}"
            )
            summary_label.remove_class("warning", "negative")
            summary_label.add_class("accent")
        except Exception:
            pass

    def _update_pagination(self, page: int, total_pages: int, total: int) -> None:
        """Update pagination info."""
        try:
            page_info = self.query_one("#page-info", Label)
            page_info.update(f"Page {page}/{total_pages} ({total} total trades)")

            # Update nav buttons
            prev_btn = self.query_one("#btn-prev", Button)
            next_btn = self.query_one("#btn-next", Button)

            prev_btn.disabled = page <= 1
            next_btn.disabled = page >= total_pages
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        """Compose the trades layout."""
        yield Header()

        with Container(classes="trades-container"):
            yield Label("PORTFOLIO MANAGER > TRADES", classes="header")

            # Summary
            yield Label("Loading...", id="trades-summary", classes="accent")

            # Filter buttons
            with Container(classes="filter-row"):
                for f in self.FILTERS:
                    variant = "primary" if f == "ALL" else "default"
                    yield Button(f, id=f"filter-{f}", variant=variant)

            # Trades table
            trades_table = DataTable(id="trades-table", zebra_stripes=True)
            trades_table.add_columns("Date", "Type", "Symbol", "Qty", "Price", "Fees", "Total", "Notes")
            yield trades_table

            # Pagination
            with Container(classes="pagination-bar"):
                yield Button("<<", id="btn-first")
                yield Button("<", id="btn-prev")
                yield Label("Page 0/0 (0 total)", id="page-info")
                yield Button(">", id="btn-next")
                yield Button(">>", id="btn-last")

            # Action buttons
            with Container(classes="action-row"):
                yield Button("Buy Position", id="btn-buy", variant="primary")
                yield Button("Sell Position", id="btn-sell")
                yield Button("Export CSV", id="btn-export")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        btn_id = event.button.id
        if not btn_id:
            return

        if btn_id.startswith("filter-"):
            filter_type = btn_id.replace("filter-", "")
            self._apply_filter(filter_type)
        elif btn_id == "btn-buy":
            self._open_buy_modal()
        elif btn_id == "btn-sell":
            self._open_sell_modal()
        elif btn_id == "btn-export":
            self._export_csv()
        elif btn_id == "btn-prev":
            self._go_to_page(self.current_page - 1)
        elif btn_id == "btn-next":
            self._go_to_page(self.current_page + 1)
        elif btn_id == "btn-first":
            self._go_to_page(1)
        elif btn_id == "btn-last":
            self._go_to_page(self._total_pages)

    def _apply_filter(self, filter_type: str) -> None:
        """Apply a trade type filter."""
        self.current_filter = filter_type
        self.current_page = 1

        # Update button variants
        for f in self.FILTERS:
            btn = self.query_one(f"#filter-{f}", Button)
            btn.variant = "primary" if f == filter_type else "default"

        # Reload trades
        if self.portfolio_id:
            self.call_later(self._load_trades)

    def _go_to_page(self, page: int) -> None:
        """Navigate to a specific page."""
        if 1 <= page <= self._total_pages:
            self.current_page = page
            if self.portfolio_id:
                self.call_later(self._load_trades)

    def _open_buy_modal(self) -> None:
        """Open the buy trade modal."""
        from portfolio_manager.ui.widgets.trade_modal import BuyTradeModal

        modal = BuyTradeModal(session_factory=self._get_session_factory())
        if self.portfolio_id:
            modal.set_portfolio_id(self.portfolio_id)

        def on_result(result) -> None:
            if result:
                self.notify("Buy executed!", title="Success")
                self.call_later(self._load_trades)

        self.push_screen(modal, on_result)

    def _open_sell_modal(self) -> None:
        """Open the sell trade modal."""
        from portfolio_manager.ui.widgets.trade_modal import SellTradeModal

        if not self.portfolio_id:
            self.notify("No portfolio selected", title="Info")
            return

        modal = SellTradeModal(session_factory=self._get_session_factory())
        modal.set_portfolio_id(self.portfolio_id)

        def on_result(result) -> None:
            if result:
                self.notify("Sell executed!", title="Success")
                self.call_later(self._load_trades)

        self.push_screen(modal, on_result)

    def _export_csv(self) -> None:
        """Export trade history to CSV."""
        if not self._trades_data or "trades" not in self._trades_data:
            self.notify("No trades to export", title="Info")
            return

        trades = self._trades_data["trades"]
        if not trades:
            self.notify("No trades to export", title="Info")
            return

        # Build CSV content using pandas for precision
        try:
            import pandas as pd

            df = pd.DataFrame(trades)

            # Format columns for better readability
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            if "quantity" in df.columns:
                df["quantity"] = df["quantity"].apply(lambda x: f"{x:,.4f}")
            if "price" in df.columns:
                df["price"] = df["price"].apply(lambda x: f"${x:,.2f}")
            if "fees" in df.columns:
                df["fees"] = df["fees"].apply(lambda x: f"${x:,.2f}")

            # Generate CSV
            csv_content = df.to_csv(index=False)

            # Save to home directory
            home = os.path.expanduser("~")
            filename = os.path.join(home, f"trades_export_{self.portfolio_id or 'all'}.csv")
            with open(filename, "w", newline="") as f:
                f.write(csv_content)

            self.notify(
                f"Exported {len(trades)} trades to {filename}",
                title="Export Complete",
                severity="information",
            )
        except ImportError:
            # Fallback: use csv module
            home = os.path.expanduser("~")
            filename = os.path.join(home, f"trades_export_{self.portfolio_id or 'all'}.csv")
            with open(filename, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                writer.writeheader()
                writer.writerows(trades)
            self.notify(
                f"Exported {len(trades)} trades to {filename}",
                title="Export Complete",
                severity="information",
            )

    def action_buy(self) -> None:
        """Handle buy key."""
        self._open_buy_modal()

    def action_sell(self) -> None:
        """Handle sell key."""
        self._open_sell_modal()

    def action_export(self) -> None:
        """Handle export key."""
        self._export_csv()

    def action_back(self) -> None:
        """Handle back key."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Handle quit key."""
        self.app.pop_screen()
