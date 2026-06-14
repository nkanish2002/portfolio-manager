"""Dashboard component — main Portfolio Manager UI.

Proper Solara function-based component with reactive state and async data loading
via solara.lab.use_task.
"""

import solara
from solara.lab import use_task

from portfolio_manager.services.portfolios import PortfolioService


portfolio_service = PortfolioService()


@solara.component
def Dashboard():
    """Main dashboard component with portfolio selector and summary."""
    router = solara.use_router()
    portfolios, set_portfolios = solara.use_state([])
    selected_id = solara.reactive(None)
    error = solara.reactive(None)

    async def _fetch():
        try:
            data = await portfolio_service.list_portfolios()
            set_portfolios(data)
            error.value = None
        except Exception as e:
            error.value = str(e)

    task = use_task(_fetch, dependencies=[])  # noqa: SH104 — pass function, not coroutine

    def on_select(value):
        selected_id.value = value

    if task.pending:
        return solara.SpinnerSolara()

    if error.value:
        return solara.alert(f"Error loading portfolios: {error.value}", type="error")

    options = [{"label": p["name"], "value": p["id"]} for p in portfolios]

    with solara.Column():
        solara.Title("Portfolio Manager")

        if portfolios:
            solara.Select(
                label="Select Portfolio",
                value=selected_id.value,
                on_value=on_select,
                values=options,
            )
        else:
            solara.alert("No portfolios found. Create one to get started.", type="info")

        if selected_id.value:
            selected = next((p for p in portfolios if p["id"] == selected_id.value), None)
            if selected:
                DashboardSummary(portfolio=selected)

                with solara.Row(justify="center", style={"margin-top": "2rem"}):
                    solara.Button(
                        "View Charts",
                        color="primary",
                        outlined=True,
                        on_click=lambda: router.push(f"/charts/{selected_id.value}"),
                    )
                    solara.Button(
                        "View Trades",
                        color="primary",
                        outlined=True,
                        on_click=lambda: router.push(f"/trades/{selected_id.value}"),
                    )


@solara.component
def DashboardSummary(portfolio: dict):
    """Summary cards for the selected portfolio."""
    total_value = portfolio.get("total_value", 0.0)
    position_count = portfolio.get("position_count", 0)

    with solara.Row(wrap=True, style={"margin-top": "1.5rem"}):
        SummaryCard(title="Portfolio", value=portfolio["name"])
        SummaryCard(title="Total Value", value=f"${total_value:,.2f}")
        SummaryCard(title="Positions", value=str(position_count))


@solara.component
def SummaryCard(title: str, value: str):
    """A single summary card."""
    with solara.Card(
        style={
            "flex": "1",
            "min-width": "200px",
            "margin": "0.5rem",
            "text-align": "center",
        }
    ):
        solara.HTML("h3", {"style": {"margin-bottom": "0.5rem", "color": "#666"}}, [title])
        solara.HTML("h2", {"style": {"margin": 0}}, [value])
