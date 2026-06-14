"""Portfolio Manager Solara UI app.

This is the Solara frontend entry point. It defines the main app component
and orchestrates the Solara services layer.

Solara runs on Starlette, serving both the UI and backend services.
No FastAPI routes — all calls are direct Python function invocations.
"""

import solara

from portfolio_manager.services.portfolios import PortfolioService
from portfolio_manager.services.charts import ChartService
from portfolio_manager.services.trades import TradeService
from portfolio_manager.ui.dashboard import Dashboard
from portfolio_manager.ui.charts import ChartsView
from portfolio_manager.ui.trades import TradesView


def get_services():
    """Return service instances for Solara components."""
    return {
        "portfolio": PortfolioService(),
        "chart": ChartService(),
        "trade": TradeService(),
    }


def get_ui_components():
    """Return UI component instances for Solara rendering."""
    return {
        "dashboard": Dashboard(),
        "charts": ChartsView(),
        "trades": TradesView(),
    }


@solara.component
def PortfolioManagerApp():
    """Main Solara app component."""
    return solara.Html("div", children=[
        solara.Html("h1", children=["Portfolio Manager"]),
        solara.Html("p", children=["Loading..."]),
    ])


def solara_app():
    """Return the Solara app for uvicorn serving."""
    return solara.Server(
        solara_app=PortfolioManagerApp,
        title="Portfolio Manager",
        version="0.1.0",
    )
