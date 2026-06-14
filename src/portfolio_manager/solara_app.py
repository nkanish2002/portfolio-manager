"""Portfolio Manager Solara UI app.

Main Solara application with routing, layout, and page components.
Uses solara.routing for URL-based navigation between Dashboard, Charts, and Trades views.
"""

import solara

from portfolio_manager.database import init_db
from portfolio_manager.ui.dashboard import Dashboard
from portfolio_manager.ui.charts import ChartsView
from portfolio_manager.ui.trades import TradesView


# ── Lifespan ───────────────────────────────────────────────────────────────

async def lifespan():
    """Initialize DB on startup."""
    await init_db()
    yield


# ── Layout ────────────────────────────────────────────────────────────────

@solara.component
def Layout(children):
    """Main app layout with header and content area."""
    router = solara.use_router()

    with solara.AppLayout(
        title="Portfolio Manager",
        left_drawer=False,
        color="primary",
    ) as layout:
        with layout.header():
            Header(router=router)
        with layout.content():
            solara.HTML("div", {"style": {"padding": "2rem", "max-width": "1200px", "margin": "0 auto"}}, children)


@solara.component
def Header(router):
    """Navigation header."""
    with solara.Row(justify="space-between", align="center"):
        solara.Title("Portfolio Manager", size=5)
        with solara.Row(style={"gap": "0.5rem"}):
            solara.Button(
                "Dashboard",
                text=True,
                color="white",
                on_click=lambda: router.push("/"),
            )


# ── Pages ─────────────────────────────────────────────────────────────────

@solara.component
def Page():
    """Default page — redirects to Dashboard."""
    return Dashboard()


@solara.component
def ChartsPage():
    """Charts page — extracts portfolio_id from route."""
    route, _ = solara.use_route()
    portfolio_id = route.path.strip("/") if route else None

    if not portfolio_id:
        return Dashboard()

    return ChartsView(portfolio_id=portfolio_id)


@solara.component
def TradesPage():
    """Trades page — extracts portfolio_id from route."""
    route, _ = solara.use_route()
    portfolio_id = route.path.strip("/") if route else None

    if not portfolio_id:
        return Dashboard()

    return TradesView(portfolio_id=portfolio_id)


# ── Routes ────────────────────────────────────────────────────────────────

routes = [
    solara.Route(path="/", component=Page, label="Dashboard"),
    solara.Route(
        path="charts",
        component=ChartsPage,
        label="Charts",
        children=[
            solara.Route(path="/<portfolio_id>", component=ChartsPage),
        ],
    ),
    solara.Route(
        path="trades",
        component=TradesPage,
        label="Trades",
        children=[
            solara.Route(path="/<portfolio_id>", component=TradesPage),
        ],
    ),
]


@solara.component
def PortfolioManagerApp():
    """Main Solara app component with routing."""
    return solara.routing.Routed(
        routes=routes,
        layout=Layout,
    )
