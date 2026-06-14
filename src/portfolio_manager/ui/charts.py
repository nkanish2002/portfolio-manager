"""Charts component — Portfolio Manager chart views.

Proper Solara function-based component with Plotly chart rendering
and async data loading via solara.lab.use_task.
"""

import solara
from solara.lab import use_task

from portfolio_manager.services.charts import ChartService


chart_service = ChartService()


@solara.component
def ChartsView(portfolio_id: str):
    """Chart view component for a specific portfolio."""
    if not portfolio_id:
        return solara.alert("Select a portfolio to view charts", type="info")

    active_tab = solara.reactive("allocation")

    def set_tab(tab: str):
        active_tab.value = tab

    with solara.Column():
        solara.Title("Charts")

        with solara.Row(justify="center", style={"margin-bottom": "1rem"}):
            solara.Button(
                "Allocation",
                color="primary",
                outlined=active_tab.value != "allocation",
                on_click=lambda: set_tab("allocation"),
            )
            solara.Button(
                "NAV History",
                color="primary",
                outlined=active_tab.value != "nav",
                on_click=lambda: set_tab("nav"),
            )
            solara.Button(
                "Drawdown",
                color="primary",
                outlined=active_tab.value != "drawdown",
                on_click=lambda: set_tab("drawdown"),
            )
            solara.Button(
                "Monthly Returns",
                color="primary",
                outlined=active_tab.value != "monthly",
                on_click=lambda: set_tab("monthly"),
            )
            solara.Button(
                "Risk Report",
                color="primary",
                outlined=active_tab.value != "risk",
                on_click=lambda: set_tab("risk"),
            )

        if active_tab.value == "allocation":
            AllocationChart(portfolio_id=portfolio_id)
        elif active_tab.value == "nav":
            NavChart(portfolio_id=portfolio_id)
        elif active_tab.value == "drawdown":
            DrawdownChart(portfolio_id=portfolio_id)
        elif active_tab.value == "monthly":
            MonthlyReturnsChart(portfolio_id=portfolio_id)
        elif active_tab.value == "risk":
            RiskReport(portfolio_id=portfolio_id)


@solara.component
def AllocationChart(portfolio_id: str):
    """Asset allocation pie chart."""
    data = solara.reactive(None)
    loading = solara.reactive(True)
    error = solara.reactive(None)

    async def _fetch():
        try:
            result = await chart_service.get_allocation(portfolio_id)
            data.value = result
            error.value = None
        except Exception as e:
            error.value = str(e)
        finally:
            loading.value = False

    use_task(_fetch, dependencies=[portfolio_id])  # noqa: SH104

    if loading.value:
        return solara.SpinnerSolara(label="Loading allocation data...")
    if error.value:
        return solara.alert(f"Error: {error.value}", type="error")
    if not data.value:
        return solara.alert("No allocation data available", type="info")

    import plotly.express as px

    labels = data.value.get("labels", [])
    values = data.value.get("values", [])
    colors = data.value.get("colors", [])

    if not labels:
        return solara.alert("No positions to display allocation", type="info")

    fig = px.pie(
        values=values,
        names=labels,
        color=labels,
        color_discrete_map=dict(zip(labels, colors)) if colors else None,
        title="Asset Allocation",
        hole=0.3,
    )
    fig.update_layout(template="plotly_dark", height=400)

    with solara.Card():
        solara.FigurePlotly(fig, style={"width": "100%"})


@solara.component
def NavChart(portfolio_id: str):
    """NAV history line chart with benchmark overlay."""
    data = solara.reactive(None)
    loading = solara.reactive(True)
    error = solara.reactive(None)

    async def _fetch():
        try:
            result = await chart_service.get_nav_history(portfolio_id, benchmark="SPY")
            data.value = result
            error.value = None
        except Exception as e:
            error.value = str(e)
        finally:
            loading.value = False

    use_task(_fetch, dependencies=[portfolio_id])  # noqa: SH104

    if loading.value:
        return solara.SpinnerSolara(label="Loading NAV history...")
    if error.value:
        return solara.alert(f"Error: {error.value}", type="error")

    import plotly.graph_objects as go

    portfolio_dates = data.value.get("portfolio_dates", [])
    portfolio_nav = data.value.get("portfolio_nav", [])
    benchmark_dates = data.value.get("benchmark_dates", [])
    benchmark_nav = data.value.get("benchmark_nav", [])

    fig = go.Figure()

    if portfolio_dates and portfolio_nav:
        fig.add_trace(go.Scatter(
            x=portfolio_dates,
            y=portfolio_nav,
            mode="lines",
            name="Portfolio",
            line=dict(color="#00CC96", width=2),
        ))

    if benchmark_dates and benchmark_nav:
        fig.add_trace(go.Scatter(
            x=benchmark_dates,
            y=benchmark_nav,
            mode="lines",
            name="SPY Benchmark",
            line=dict(color="#EF553B", width=2, dash="dash"),
        ))

    fig.update_layout(
        title="NAV History",
        xaxis_title="Date",
        yaxis_title="Value",
        template="plotly_dark",
        height=400,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    with solara.Card():
        solara.FigurePlotly(fig, style={"width": "100%"})


@solara.component
def DrawdownChart(portfolio_id: str):
    """Drawdown area chart."""
    data = solara.reactive(None)
    loading = solara.reactive(True)
    error = solara.reactive(None)

    async def _fetch():
        try:
            result = await chart_service.get_drawdown(portfolio_id)
            data.value = result
            error.value = None
        except Exception as e:
            error.value = str(e)
        finally:
            loading.value = False

    use_task(_fetch, dependencies=[portfolio_id])  # noqa: SH104

    if loading.value:
        return solara.SpinnerSolara(label="Loading drawdown data...")
    if error.value:
        return solara.alert(f"Error: {error.value}", type="error")

    import plotly.graph_objects as go

    dates = data.value.get("dates", [])
    drawdown = data.value.get("drawdown", [])

    if not dates:
        return solara.alert("No drawdown data available", type="info")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=drawdown,
        mode="lines",
        fill="tozeroy",
        name="Drawdown",
        line=dict(color="#EF553B", width=1.5),
        fillcolor="rgba(239, 85, 59, 0.3)",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=1)
    fig.update_layout(
        title="Drawdown",
        xaxis_title="Date",
        yaxis_title="Drawdown %",
        template="plotly_dark",
        height=400,
    )

    with solara.Card():
        solara.FigurePlotly(fig, style={"width": "100%"})


@solara.component
def MonthlyReturnsChart(portfolio_id: str):
    """Monthly returns heatmap."""
    data = solara.reactive(None)
    loading = solara.reactive(True)
    error = solara.reactive(None)

    async def _fetch():
        try:
            result = await chart_service.get_monthly_returns(portfolio_id)
            data.value = result
            error.value = None
        except Exception as e:
            error.value = str(e)
        finally:
            loading.value = False

    use_task(_fetch, dependencies=[portfolio_id])  # noqa: SH104

    if loading.value:
        return solara.SpinnerSolara(label="Loading monthly returns...")
    if error.value:
        return solara.alert(f"Error: {error.value}", type="error")

    import plotly.express as px

    years = data.value.get("years", [])
    months = data.value.get("months", [])
    values = data.value.get("values", [])

    if not years or not months:
        insufficient = data.value.get("insufficient_data", False)
        msg = "Insufficient data for monthly returns (need at least 5 data points)" if insufficient else "No monthly returns data"
        return solara.alert(msg, type="info")

    fig = px.imshow(
        values,
        labels=dict(x="Month", y="Year"),
        x=months,
        y=[str(y) for y in reversed(years)],
        color_continuous_scale="RdYlGn",
        text_auto=True,
        title="Monthly Returns %",
    )
    fig.update_layout(template="plotly_dark", height=400)

    with solara.Card():
        solara.FigurePlotly(fig, style={"width": "100%"})


@solara.component
def RiskReport(portfolio_id: str):
    """Risk metrics report."""
    data = solara.reactive(None)
    loading = solara.reactive(True)
    error = solara.reactive(None)

    async def _fetch():
        try:
            result = await chart_service.get_risk_report(portfolio_id)
            data.value = result
            error.value = None
        except Exception as e:
            error.value = str(e)
        finally:
            loading.value = False

    use_task(_fetch, dependencies=[portfolio_id])  # noqa: SH104

    if loading.value:
        return solara.SpinnerSolara(label="Loading risk report...")
    if error.value:
        return solara.alert(f"Error: {error.value}", type="error")
    if not data.value:
        return solara.alert("No risk report data", type="info")

    metrics = [
        ("Sharpe Ratio", data.value.get("sharpe_ratio", "N/A")),
        ("Sortino Ratio", data.value.get("sortino_ratio", "N/A")),
        ("Max Drawdown", f"{data.value.get('max_drawdown', 'N/A')}%" if data.value.get("max_drawdown") is not None else "N/A"),
        ("VaR 95%", data.value.get("var_95", "N/A")),
        ("Beta", data.value.get("beta", "N/A")),
        ("Alpha", data.value.get("alpha", "N/A")),
        ("Annualized Return", f"{data.value.get('annualized_return', 'N/A')}%" if data.value.get("annualized_return") is not None else "N/A"),
        ("Treynor Ratio", data.value.get("treynor_ratio", "N/A")),
        ("Calmar Ratio", data.value.get("calmar_ratio", "N/A")),
        ("Ulcer Index", data.value.get("ulcer_index", "N/A")),
    ]

    with solara.Card():
        solara.HTML("h3", {"style": {"margin-bottom": "1rem"}}, ["Risk Metrics"])
        for label, value in metrics:
            with solara.Row(style={"margin-bottom": "0.5rem", "justify-content": "space-between"}):
                solara.HTML("span", {"style": {"flex": 1, "color": "#aaa"}}, [label])
                solara.HTML(
                    "span",
                    {"style": {"flex": 1, "text-align": "right", "font-weight": "bold"}},
                    [f"{value:.4f}" if isinstance(value, float) else str(value)],
                )
