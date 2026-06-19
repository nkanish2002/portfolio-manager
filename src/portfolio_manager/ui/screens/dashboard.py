"""Dashboard screen -- portfolio overview and position table with real data."""


from sqlalchemy.ext.asyncio import async_sessionmaker
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
)

from portfolio_manager.services.data_feed import YFinanceSource
from portfolio_manager.services.portfolio_calc import calculate_portfolio_value
from portfolio_manager.ui.screens.analytics import AnalyticsScreen
from portfolio_manager.ui.screens.settings import SettingsScreen
from portfolio_manager.ui.screens.trades import TradesScreen
from portfolio_manager.ui.widgets.portfolio_modal import (
    CreatePortfolioModal,
    DeletePortfolioModal,
)
from portfolio_manager.ui.widgets.position_table import PositionTable


class DashboardScreen(Screen):
    """Main dashboard screen showing portfolio overview and positions."""

    BINDINGS = [
        Binding("a", "analytics", "Analytics"),
        Binding("t", "trades", "Trades"),
        Binding("c", "create_portfolio", "Create Portfolio"),
        Binding("d", "delete_portfolio", "Delete Portfolio"),
        Binding("s", "settings", "Settings"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        portfolio_id: str | None = None,
        session_factory: async_sessionmaker | None = None,
    ) -> None:
        """Initialize dashboard screen.

        Args:
            portfolio_id: Optional portfolio ID to display. None = use first available.
            session_factory: Async session factory for DB access.
                Uses the global async_session if not provided.
        """
        super().__init__()
        self.portfolio_id = portfolio_id
        self._session_factory = session_factory
        self.current_portfolio_index = 0
        self._portfolios: list[dict] = []
        self._portfolio_ids: list[str] = []
        self._price_cache: dict[str, float] = {}
        self._portfolio_values: dict | None = None
        self._positions_loaded = False
        self._online = True
        self._consecutive_failures = 0
        self._connection_source = YFinanceSource()

    def _get_session_factory(self) -> async_sessionmaker:
        """Return the DB session factory, falling back to the global."""
        if self._session_factory is not None:
            return self._session_factory
        from portfolio_manager.database import async_session

        return async_session

    def on_mount(self) -> None:
        """Load portfolio list on mount."""
        self.call_later(self._load_portfolios)
        self.set_interval(60, self._check_connection)

    async def _load_portfolios(self) -> None:
        """Load portfolio list from the database, then load initial positions."""
        from portfolio_manager.services.portfolios import _list_portfolios

        try:
            async with self._get_session_factory() as session:
                self._portfolios = await _list_portfolios(session)
                self._portfolio_ids = [p["id"] for p in self._portfolios]
        except Exception:
            self._portfolios = []
            self._portfolio_ids = []

        # Update the selector label and status bar
        self.call_from_thread(self._update_portfolio_selector)
        self.call_from_thread(self._update_status_bar)

        # Auto-load positions/stats for the first portfolio if available
        if self._portfolio_ids:
            self.call_later(self._load_initial_data)
        else:
            self.call_from_thread(self._update_empty_state)

    def _update_portfolio_selector(self) -> None:
        """Update the portfolio selector label."""
        try:
            selector = self.query_one("#portfolio-selector", Label)
            if not self._portfolio_ids:
                selector.update(
                    "No portfolios yet -- press [C] to create one"
                )
            else:
                idx = self.current_portfolio_index % len(self._portfolio_ids)
                portfolio = self._portfolios[idx]
                name = portfolio["name"]
                count = portfolio.get("position_count", 0)
                selector.update(
                    f"[{idx + 1}] {name} ({count} positions)  [ESC] Switch  [D] Delete"
                )
        except Exception:
            pass

    def _update_status_bar(self) -> None:
        """Update the status bar with connection status and shortcuts."""
        try:
            status = self.query_one("#status-bar", Label)
            conn = "ONLINE" if self._online else "OFFLINE"
            conn_color = "positive" if self._online else "negative"
            status.update(
                f"[{conn}] Press [1-9] to switch | [R] Refresh | [C] Create | [D] Delete"
            )
            status.remove_class("positive", "negative", "warning")
            status.add_class(conn_color)
        except Exception:
            pass

    def _check_connection(self) -> None:
        """Periodic connectivity check."""
        online = self._connection_source.check_connection()
        if online:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

        if online != self._online:
            self._online = online
            self.call_from_thread(self._update_status_bar)
            if not online:
                self.notify(
                    "Cannot reach Yahoo Finance -- prices will use cached values.",
                    title="Connection",
                    severity="warning",
                )

    async def _load_positions_and_allocation(self) -> None:
        """Load positions, prices, and allocation for the current portfolio."""
        if not self._portfolio_ids:
            self.call_from_thread(self._update_empty_state)
            return

        idx = self.current_portfolio_index % len(self._portfolio_ids)
        portfolio_id = self._portfolio_ids[idx]

        try:
            from decimal import Decimal

            import pandas as pd
            from sqlalchemy import select

            from portfolio_manager.models.asset import Asset
            from portfolio_manager.models.position import Position

            source = YFinanceSource()

            async with self._get_session_factory() as session:
                result = await session.execute(
                    select(Position, Asset.symbol, Asset.name).join(
                        Asset, Position.asset_id == Asset.id, isouter=True
                    ).where(Position.portfolio_id == portfolio_id)
                )
                rows = result.all()

                positions_data = []
                calc_rows = []
                for row in rows:
                    pos = row[0]
                    symbol = row[1] if row[1] else pos.asset_id
                    asset_name = row[2] if row[2] else symbol

                    # Fetch current price from yfinance
                    current_price = None
                    if symbol and symbol not in ("N/A", "UNKNOWN"):
                        try:
                            fetched = source.get_price(symbol)
                            if fetched:
                                current_price = float(fetched)
                        except Exception:
                            pass

                    # Update position price in DB if changed
                    if current_price is not None and (
                        pos.current_price is None
                        or float(pos.current_price) != current_price
                    ):
                        pos.current_price = Decimal(str(current_price))
                        await session.commit()

                    quantity = float(pos.quantity) if pos.quantity else 0
                    avg_cost = float(pos.avg_cost_basis) if pos.avg_cost_basis else 0
                    price = current_price or (
                        float(pos.current_price) if pos.current_price else 0
                    )
                    market_value = quantity * price
                    cost_basis = quantity * avg_cost
                    gain = market_value - cost_basis
                    gain_pct = (gain / cost_basis * 100) if cost_basis != 0 else 0

                    positions_data.append({
                        "symbol": symbol,
                        "asset_name": asset_name,
                        "quantity": quantity,
                        "avg_cost_basis": avg_cost,
                        "current_price": price,
                        "market_value": market_value,
                        "unrealized_gain": gain,
                        "unrealized_gain_pct": gain_pct,
                        "last_price_date": pos.last_price_date,
                    })

                    asset_class = getattr(pos, "asset_class", "Unknown")
                    calc_rows.append({
                        "symbol": symbol,
                        "quantity": quantity,
                        "price": price,
                        "cost_basis": avg_cost,
                        "asset_class": asset_class,
                    })

                    self._price_cache[symbol] = price

                # Use portfolio_calc to compute allocation breakdown
                calc_df = pd.DataFrame(calc_rows) if calc_rows else pd.DataFrame()
                allocation_result = calculate_portfolio_value(calc_df)
                self._portfolio_values = allocation_result

            self.call_from_thread(self._update_positions_table, positions_data)
            self.call_from_thread(
                self._update_portfolio_summary, positions_data
            )
            self.call_from_thread(
                self._update_allocation_breakdown,
                allocation_result.get("allocation_pct", []),
                allocation_result.get("top_holdings", []),
            )
            self._consecutive_failures = 0

        except Exception as e:
            self._consecutive_failures += 1
            self.call_from_thread(self._show_error, f"Failed to load positions: {e}")

    def _update_empty_state(self) -> None:
        """Show empty state when no portfolios or no positions."""
        try:
            summary = self.query_one("#portfolio-summary", Label)
            stats = self.query_one("#portfolio-stats", Label)
            alloc = self.query_one("#allocation-breakdown", Label)

            if not self._portfolio_ids:
                summary.update("No portfolios -- press [C] to create one")
                summary.remove_class("positive", "negative", "warning")
                summary.add_class("warning")
                stats.update("Positions: 0             Unrealized P&L: $0.00")
                alloc.update("Allocation: No portfolios available")
            else:
                summary.update("Total Value: $0.00    Day Change: $0.00 (0.00%)")
                summary.remove_class("positive", "negative")
                summary.add_class("warning")
                stats.update("Positions: 0             Unrealized P&L: $0.00")
                alloc.update("Allocation: No positions in current portfolio")
                alloc.remove_class("positive", "negative")
                alloc.add_class("warning")
        except Exception:
            pass

    def _show_error(self, message: str) -> None:
        """Show error notification from main thread."""
        self.notify(message, title="Error", severity="error")

    def _update_allocation_breakdown(
        self, allocation_data: list[dict], top_holdings: list[dict]
    ) -> None:
        """Update the allocation breakdown label with real data."""
        try:
            alloc_label = self.query_one("#allocation-breakdown", Label)
            if not allocation_data:
                alloc_label.update(
                    "Allocation: No positions in current portfolio"
                )
                alloc_label.remove_class("positive", "negative")
                alloc_label.add_class("warning")
                return

            # Build allocation string: class -> value
            by_class: dict[str, float] = {}
            for item in allocation_data:
                asset_class = item.get("asset_class", "Unknown")
                pct = item.get("allocation_pct", 0.0)
                by_class[asset_class] = round(
                    by_class.get(asset_class, 0.0) + pct, 1
                )

            alloc_str = "Allocation: " + " | ".join(
                f"{cls}={pct}%"
                for cls, pct in sorted(by_class.items(), key=lambda x: -x[1])
            )

            # Add top holdings summary
            if top_holdings:
                top_str = " | Top: " + " | ".join(
                    f"{h['symbol']}={h['allocation_pct']}%"
                    for h in top_holdings[:5]
                )
                alloc_str += top_str

            alloc_label.update(alloc_str)
            alloc_label.remove_class("warning", "negative")
            alloc_label.add_class("accent")

        except Exception:
            pass

    async def _load_initial_data(self) -> None:
        """Load positions, prices, and allocation for the first portfolio."""
        if not self._portfolio_ids:
            return
        await self._load_positions_and_allocation()

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header()

        with Container():
            yield Label("PORTFOLIO MANAGER", classes="header")

            # Portfolio selector
            yield Label(
                "Loading portfolios...",
                id="portfolio-selector",
                classes="accent",
            )

            # Portfolio summary
            yield Label(
                "Loading portfolios...",
                id="portfolio-summary",
                classes="positive",
            )
            yield Label(
                "Loading portfolios...",
                id="portfolio-stats",
            )
            yield Label(
                "Loading allocation data...",
                id="allocation-breakdown",
                classes="accent",
            )

            # Status bar
            yield Label(
                "[CHECKING] Press [1-9] to switch | [R] Refresh | [C] Create | [D] Delete",
                id="status-bar",
                classes="warning",
            )

            # Position table (uses PositionTable widget with sortable headers, gain/loss coloring)
            table = PositionTable(id="positions-table")
            yield table

            # Action buttons
            with Container(id="action-buttons"):
                yield Button("Refresh Prices", id="btn-refresh", variant="primary")
                yield Button("Create Portfolio", id="btn-create")
                yield Button("Delete Portfolio", id="btn-delete")
                yield Button("Analytics", id="btn-analytics")
                yield Button("Trades", id="btn-trades")
                yield Button("Settings", id="btn-settings")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-refresh":
            self.refresh_prices()
        elif event.button.id == "btn-create":
            self.action_create_portfolio()
        elif event.button.id == "btn-delete":
            self.action_delete_portfolio()
        elif event.button.id == "btn-analytics":
            self.action_analytics()
        elif event.button.id == "btn-trades":
            self.action_trades()
        elif event.button.id == "btn-settings":
            self.action_settings()

    def action_refresh(self) -> None:
        """Refresh prices."""
        self.refresh_prices()

    def refresh_prices(self) -> None:
        """Fetch latest prices and update the table."""
        self.notify("Refreshing prices...", title="Refresh")
        self.call_later(self._refresh_prices_async)

    async def _refresh_prices_async(self) -> None:
        """Fetch prices from yfinance and update the table."""
        if not self._portfolio_ids:
            return

        idx = self.current_portfolio_index % len(self._portfolio_ids)
        portfolio_id = self._portfolio_ids[idx]

        try:
            from decimal import Decimal

            from sqlalchemy import select

            from portfolio_manager.models.asset import Asset
            from portfolio_manager.models.position import Position

            source = YFinanceSource()

            async with self._get_session_factory() as session:
                result = await session.execute(
                    select(Position, Asset.symbol, Asset.name).join(
                        Asset, Position.asset_id == Asset.id, isouter=True
                    ).where(Position.portfolio_id == portfolio_id)
                )
                rows = result.all()

                positions_data = []
                for row in rows:
                    pos = row[0]
                    symbol = row[1] if row[1] else pos.asset_id
                    asset_name = row[2] if row[2] else symbol

                    current_price = None
                    if symbol and symbol not in ("N/A", "UNKNOWN"):
                        try:
                            fetched = source.get_price(symbol)
                            if fetched:
                                current_price = float(fetched)
                        except Exception:
                            pass

                    if current_price is not None and (
                        pos.current_price is None
                        or float(pos.current_price) != current_price
                    ):
                        pos.current_price = Decimal(str(current_price))
                        await session.commit()

                    quantity = float(pos.quantity) if pos.quantity else 0
                    avg_cost = float(pos.avg_cost_basis) if pos.avg_cost_basis else 0
                    price = current_price or (
                        float(pos.current_price) if pos.current_price else 0
                    )
                    market_value = quantity * price
                    cost_basis = quantity * avg_cost
                    gain = market_value - cost_basis
                    gain_pct = (gain / cost_basis * 100) if cost_basis != 0 else 0

                    positions_data.append({
                        "symbol": symbol,
                        "asset_name": asset_name,
                        "quantity": quantity,
                        "avg_cost_basis": avg_cost,
                        "current_price": price,
                        "market_value": market_value,
                        "unrealized_gain": gain,
                        "unrealized_gain_pct": gain_pct,
                        "last_price_date": pos.last_price_date,
                    })
                    self._price_cache[symbol] = price

            self.call_from_thread(self._update_positions_table, positions_data)
            self.call_from_thread(
                self._update_portfolio_summary, positions_data
            )
            self.call_from_thread(
                self._update_allocation_breakdown,
                self._portfolio_values.get("allocation_pct", [])
                if self._portfolio_values
                else [],
                self._portfolio_values.get("top_holdings", [])
                if self._portfolio_values
                else [],
            )

            self._consecutive_failures = 0
            self.notify(
                f"Prices refreshed for {len(positions_data)} positions",
                title="Refresh",
            )

        except Exception as e:
            self._consecutive_failures += 1
            self.notify(f"Price refresh failed: {e}", title="Error", severity="error")

    def refresh_positions(self) -> None:
        """Refresh positions from database (without fetching prices)."""
        self.call_later(self._load_positions_and_allocation)

    def _update_positions_table(self, positions_data: list[dict]) -> None:
        """Update the positions table with data."""
        try:
            table = self.query_one("#positions-table", PositionTable)
            table.set_positions(positions_data)
            # Flash updated rows
            for pos in positions_data:
                symbol = pos.get("symbol", "?")
                if symbol in self._price_cache:
                    table.flash_price(symbol)
                    table.clear_flash()
        except Exception:
            pass

    def _update_portfolio_summary(self, positions_data: list[dict]) -> None:
        """Update the portfolio summary labels."""
        total_value = sum(p.get("market_value", 0) for p in positions_data)
        total_gain = sum(p.get("unrealized_gain", 0) for p in positions_data)
        total_gain_pct = (
            total_gain / total_value * 100 if total_value > 0 else 0
        )
        position_count = len(positions_data)

        try:
            summary = self.query_one("#portfolio-summary", Label)
            stats = self.query_one("#portfolio-stats", Label)

            sign = "+" if total_gain >= 0 else ""
            summary.update(
                f"Total Value: ${total_value:,.2f}    "
                f"Day Change: {sign}${total_gain:,.2f} "
                f"({sign}{total_gain_pct:.2f}%)"
            )
            stats.update(
                f"Positions: {position_count}             "
                f"Unrealized P&L: {sign}${total_gain:,.2f}"
            )

            summary.remove_class("positive", "negative", "warning")
            summary.add_class("positive" if total_gain >= 0 else "negative")
        except Exception:
            pass

    def action_create_portfolio(self) -> None:
        """Create a new portfolio."""

        def on_created(result) -> None:
            if result:
                self._portfolios.append(result)
                self._portfolio_ids.append(result["id"])
                self.current_portfolio_index = len(self._portfolios) - 1
                self.call_from_thread(self._update_portfolio_selector)
                self.call_from_thread(self._update_status_bar)
                self.call_later(self._load_positions_and_allocation)

        self.app.push_screen(
            CreatePortfolioModal(session_factory=self._get_session_factory()),
            on_created,
        )

    def action_delete_portfolio(self) -> None:
        """Delete the current portfolio."""
        if not self._portfolio_ids:
            self.notify("No portfolios to delete.", title="Info")
            return

        idx = self.current_portfolio_index % len(self._portfolio_ids)
        portfolio = self._portfolios[idx]

        def on_deleted(deleted: bool) -> None:
            if deleted:
                self._portfolios.pop(idx)
                self._portfolio_ids.pop(idx)
                if self._portfolio_ids:
                    self.current_portfolio_index = min(
                        idx, len(self._portfolios) - 1
                    )
                else:
                    self.current_portfolio_index = 0
                self.call_from_thread(self._update_portfolio_selector)
                self.call_from_thread(self._update_status_bar)
                self.call_later(self._load_positions_and_allocation)

        self.app.push_screen(
            DeletePortfolioModal(
                portfolio["name"],
                portfolio["id"],
                session_factory=self._get_session_factory(),
            ),
            on_deleted,
        )

    def action_analytics(self) -> None:
        """Navigate to analytics screen."""
        self.app.push_screen(
            AnalyticsScreen(session_factory=self._get_session_factory())
        )

    def action_trades(self) -> None:
        """Navigate to trades screen."""
        portfolio_id = None
        if self._portfolio_ids:
            idx = self.current_portfolio_index % len(self._portfolio_ids)
            portfolio_id = self._portfolio_ids[idx]
        self.app.push_screen(TradesScreen(portfolio_id=portfolio_id))

    def action_settings(self) -> None:
        """Navigate to settings screen."""
        self.app.push_screen(
            SettingsScreen(session_factory=self._get_session_factory())
        )

    def action_help(self) -> None:
        """Show help dialog."""
        self.notify(
            "[1-9] Switch | [R] Refresh | [C] Create | [D] Delete | "
            "[A] Analytics | [T] Trades | [S] Settings | [Q] Quit",
            title="Help",
        )

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts for portfolio switching."""
        if event.key.isdigit() and event.key != "0":
            num = int(event.key)
            if self._portfolio_ids:
                idx = (num - 1) % len(self._portfolio_ids)
                self.current_portfolio_index = idx
                self.call_from_thread(self._update_portfolio_selector)
                self.call_from_thread(self._update_status_bar)
                self.call_later(self._load_positions_and_allocation)
                event.stop()
                return

        if event.key == "escape":
            if self._portfolio_ids and len(self._portfolio_ids) > 1:
                self.current_portfolio_index = (
                    self.current_portfolio_index + 1
                ) % len(self._portfolio_ids)
                self.call_from_thread(self._update_portfolio_selector)
                self.call_from_thread(self._update_status_bar)
                self.call_later(self._load_positions_and_allocation)
                event.stop()
                return
