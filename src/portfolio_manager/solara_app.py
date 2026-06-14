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


def get_services():
    """Return service instances for Solara components."""
    return {
        "portfolio": PortfolioService(),
        "chart": ChartService(),
        "trade": TradeService(),
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
        title=settings.app_name,
        version="0.1.0",
    )
