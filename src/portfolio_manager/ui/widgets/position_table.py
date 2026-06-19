"""PositionTable widget — sortable, gain/loss coloring, live flash on price updates."""

from typing import Any

from textual.app import ComposeResult
from textual.widgets import DataTable
from textual.binding import Binding


class PositionTable(DataTable):
    """A DataTable specialized for displaying portfolio positions.

    Features:
    - Clickable column headers to sort
    - Green/red coloring for gain/loss via CSS
    - Flash effect when prices update
    """

    BINDINGS = [
        Binding("l", "toggle_last", "Sort by Last"),
    ]

    def __init__(self, id: str = "positions-table") -> None:
        """Initialize the position table."""
        super().__init__(id=id)
        self.allow_header_sort = True
        self.cursor_type = "row"
        self._flash_rows: set[int] = set()

    def compose(self) -> ComposeResult:
        """Compose the table layout."""
        self.add_columns("Symbol", "Qty", "Avg Cost", "Price", "Value", "P&L", "P&L %", "Last")
        yield self

    def set_positions(self, positions: list[dict[str, Any]]) -> None:
        """Populate the table with position data.

        Args:
            positions: List of position dicts with keys:
                symbol, asset_name, quantity, avg_cost_basis,
                current_price, unrealized_gain, unrealized_gain_pct,
                market_value
        """
        self.clear()
        for pos in positions:
            qty = str(pos.get("quantity", 0))
            avg_cost = f"${pos.get('avg_cost_basis', 0):.2f}"
            price = f"${pos.get('current_price', 0):.2f}"
            market_value = f"${pos.get('market_value', 0):.2f}"
            gain = pos.get("unrealized_gain", 0)
            gain_pct = pos.get("unrealized_gain_pct", 0)

            if gain > 0:
                pnl_str = f"+${gain:,.2f}"
                pnl_pct_str = f"+{gain_pct:.2f}%"
            elif gain < 0:
                pnl_str = f"-${abs(gain):,.2f}"
                pnl_pct_str = f"{gain_pct:.2f}%"
            else:
                pnl_str = "$0.00"
                pnl_pct_str = "0.00%"

            last = pos.get("last_price_date", "N/A")
            if hasattr(last, "strftime"):
                last = last.strftime("%Y-%m-%d")

            # Colorize rows via CSS classes (positive = green, negative = red)
            self.add_row(
                str(pos.get("symbol", "?")),
                qty,
                avg_cost,
                price,
                market_value,
                pnl_str,
                pnl_pct_str,
                str(last),
                classes="positive" if gain >= 0 else "negative",
            )

    def flash_price(self, symbol: str) -> None:
        """Mark a row for flash effect (price updated).

        Args:
            symbol: The symbol whose price was updated.
        """
        for row_index in range(self.row_count):
            if self.get_cell_at(row_index, 0) == symbol:
                self._flash_rows.add(row_index)
                break

    def clear_flash(self) -> None:
        """Clear all flash marks."""
        self._flash_rows.clear()

    def action_toggle_last(self) -> None:
        """Toggle sort order on last-updated column."""
        try:
            self.sort("Last", reverse=True)
        except Exception:
            pass
