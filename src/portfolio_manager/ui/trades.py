"""Trades component — Portfolio Manager trades table.

Proper Solara function-based component with async data loading
via solara.lab.use_task and Solara DataTable for the trades table.
"""

import solara
from solara.lab import use_task

from portfolio_manager.services.trades import TradeService


trade_service = TradeService()


@solara.component
def TradesView(portfolio_id: str):
    """Trades table component for a specific portfolio."""
    trades = solara.reactive([])
    summary = solara.reactive({})
    loading = solara.reactive(True)
    error = solara.reactive(None)

    async def _fetch():
        if not portfolio_id:
            loading.value = False
            return
        try:
            trades_data, summary_data = await solara.thread.run(
                _load_trades_and_summary,
                portfolio_id,
            )
            trades.value = trades_data
            summary.value = summary_data
            error.value = None
        except Exception as e:
            error.value = str(e)
        finally:
            loading.value = False

    use_task(_fetch, dependencies=[portfolio_id])  # noqa: SH104

    async def _load_trades_and_summary(pid):
        t = await trade_service.list_trades(pid)
        s = await trade_service.get_trades_summary(pid)
        return t, s

    if not portfolio_id:
        return solara.alert("Select a portfolio to view trades", type="info")

    with solara.Column():
        solara.Title("Trades", subtitle=f"Transaction history for {portfolio_id}")

        if loading.value:
            return solara.SpinnerSolara(label="Loading trades...")
        if error.value:
            return solara.alert(f"Error: {error.value}", type="error")

        # Summary cards
        with solara.Row(wrap=True, style={"margin-bottom": "1.5rem"}):
            SummaryCard(title="Total Trades", value=str(summary.value.get("total_trades", 0)))
            SummaryCard(title="Buys", value=str(summary.value.get("total_buys", 0)))
            SummaryCard(title="Sells", value=str(summary.value.get("total_sells", 0)))
            SummaryCard(
                title="Net Realized P&L",
                value=f"${summary.value.get('net_realized_p_and_l', 0):,.2f}",
            )
            SummaryCard(
                title="Realized Gains",
                value=f"${summary.value.get('realized_gain', 0):,.2f}",
            )
            SummaryCard(
                title="Realized Losses",
                value=f"${summary.value.get('realized_loss', 0):,.2f}",
            )

        # Trades table
        if not trades.value:
            solara.alert("No trades found", type="info")
        else:
            with solara.Card():
                solara.HTML("h3", {"style": {"margin-bottom": "1rem"}}, ["Transaction History"])
                columns = [
                    {"name": "date", "label": "Date", "align": "left"},
                    {"name": "type", "label": "Type", "align": "left"},
                    {"name": "asset_id", "label": "Asset", "align": "left"},
                    {"name": "quantity", "label": "Qty", "align": "right"},
                    {"name": "price", "label": "Price", "align": "right"},
                    {"name": "fees", "label": "Fees", "align": "right"},
                    {"name": "p_and_l", "label": "P&L", "align": "right"},
                ]
                solara.DataTable(
                    columns=columns,
                    items=trades.value,
                    density="comfortable",
                    hover=True,
                )


@solara.component
def SummaryCard(title: str, value: str):
    """A single summary card."""
    with solara.Card(
        style={"flex": "1", "min-width": "150px", "margin": "0.3rem", "text-align": "center"}
    ):
        solara.HTML("h4", {"style": {"margin-bottom": "0.3rem", "color": "#666", "font-size": "0.85rem"}}, [title])
        solara.HTML("h3", {"style": {"margin": 0, "font-size": "1.1rem"}}, [value])
