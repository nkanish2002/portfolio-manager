# Portfolio Manager - Solara Frontend Design Docs

## Overview

This document provides detailed technical specifications for the Solara frontend implementation.

## Architecture

### Component Structure

```
solara-ui/
├── app.py                    # Main application entry point
├── components/
│   ├── __init__.py
│   ├── dashboard.py          # Portfolio overview component
│   ├── positions.py          # Position management component
│   ├── trades.py             # Trade audit component
│   ├── analytics.py          # Charts and metrics component
│   ├── portfolio_selector.py # Portfolio dropdown widget
│   └── nav_header.py         # Navigation header component
├── services/
│   └── api.py                # API client service
└── models/
    └── schemas.py            # Shared Pydantic models
```

## Component Design

### Widget Components (ipyvuetify-based)

Widget components are pre-built UI elements from ipyvuetify.

### ⚠️ IMPORTANT: Solara API Conventions

All code examples in this document follow the **correct** Solara patterns:

- **State**: `portfolios, set_portfolios = solara.use_state([])` or `portfolios = solara.reactive([])`
- **Async data fetching**: Use `solara.lab.use_task()` — **never** `asyncio.run()` (Solara runs inside Tornado's event loop)
- **Effects**: Use `solara.Effect` decorator with dependency lists

#### Correct Async Data-Fetch Pattern (canonical reference)

```python
import solara
from solara.lab import use_task
from solara_ui.services.api import PortfolioAPI

@solara.component
def PortfolioList():
    portfolios, set_portfolios = solara.use_state([])
    error = solara.reactive(None)

    @solara.effect
    def load():
        async def _fetch():
            try:
                data = await PortfolioAPI().list_portfolios()
                set_portfolios(data)
                error.value = None
            except Exception as e:
                error.value = str(e)
        solara.lab.use_task(_fetch(), dependencies=[])

    return solara.Html("div", children=[
        solara.Alert(f"Error: {error.value}", type="error") if error.value else None,
        *[solara.Html("div", children=[p.name]) for p in portfolios]
    ])
```

### PortfolioSelector Widget

```python
import solara
from solara_ui.services.api import PortfolioAPI

@solara.component
def PortfolioSelector():
    """Portfolio dropdown widget using ipyvuetify.Select"""
    portfolios, set_portfolios = solara.use_state([])
    current_portfolio = solara.reactive(None)
    loading = solara.reactive(True)

    @solara.effect
    def load():
        async def _fetch():
            data = await PortfolioAPI().list_portfolios()
            set_portfolios(data)
            loading.value = False
        solara.lab.use_task(_fetch(), dependencies=[])

    def on_select(value):
        portfolio = next((p for p in portfolios if p.id == value), None)
        current_portfolio.value = portfolio

    options = [{"text": p.name, "value": p.id} for p in portfolios]

    return solara.Html("div", children=[
        solara.Select(
            label="Select Portfolio",
            v_model=current_portfolio.value.id if current_portfolio.value else None,
            items=options,
            on_v_model=on_select,
        ),
        solara.ProgressCircular(indeterminate=True) if loading.value else None
    ])
```

### NavHeader Widget

```python
import solara
from ipyvuetify import VAppBar, VToolbarTitle, VBtn

@solara.component
def NavHeader(current_portfolio):
    """Navigation header with logo and portfolio context"""
    name = current_portfolio.value.name if current_portfolio.value else "No Portfolio"

    return VAppBar(
        app=True,
        clipped_left=True,
        color="primary",
        children=[
            VToolbarTitle(children=["Portfolio Manager"]),
            VBtn(
                children=[f"📁 {name}"],
                on_click=lambda: print("Portfolio info")  # TODO: Add modal
            )
        ]
    )
```

### Function Components (Custom Logic)

#### Dashboard Component

```python
import solara
from solara_ui.services.api import PortfolioAPI

@solara.component
def Dashboard(portfolio_id):
    """Portfolio overview dashboard"""
    portfolio = solara.reactive(None)
    positions = solara.reactive([])
    metrics = solara.reactive({})

    @solara.effect
    def load():
        async def _fetch():
            if portfolio_id:
                result = await PortfolioAPI().get_portfolio(portfolio_id)
                portfolio.value = result.get("portfolio")
                metrics.value = result
        solara.lab.use_task(_fetch(), dependencies=[portfolio_id])

    total_value = metrics.value.get("total_value", 0.0)
    pnl = metrics.value.get("unrealized_pnl", 0.0)
    count = len(positions.value)

    return solara.Html("div", children=[
        solara.Html("h3", children=["Dashboard"]),
        solara.Html("div", children=[f"Total Value: ${total_value:,.2f}"]),
        solara.Html("div", children=[f"P&L: ${pnl:,.2f}"]),
        solara.Html("div", children=[f"Positions: {count}"])
    ])
```

#### Positions Component

```python
import solara
from solara_ui.services.api import PortfolioAPI

@solara.component
def Positions(portfolio_id):
    """Position management component"""
    positions = solara.reactive([])
    loading = solara.reactive(True)

    @solara.effect
    def load():
        async def _fetch():
            data = await PortfolioAPI().get_positions(portfolio_id)
            positions.value = data
            loading.value = False
        solara.lab.use_task(_fetch(), dependencies=[portfolio_id])

    def on_sell(position_id):
        async def _sell():
            await PortfolioAPI().sell_position(portfolio_id, position_id)
            positions.value = await PortfolioAPI().get_positions(portfolio_id)
        solara.lab.use_task(_sell(), dependencies=[])

    # Build table from positions data
    headers = [
        {"text": "Symbol", "value": "symbol"},
        {"text": "Quantity", "value": "quantity"},
        {"text": "Avg Price", "value": "buy_price"},
        {"text": "Current", "value": "current_price"},
        {"text": "P&L", "value": "unrealized_pnl"},
        {"text": "Actions", "value": "actions"}
    ]

    rows = positions.value or []
    table_children = []
    for item in rows:
        table_children.extend([
            solara.Html("div", children=[item.get("symbol", "")]),
            solara.Html("div", children=[str(item.get("quantity", 0))]),
            solara.Html("div", children=[f"${item.get('buy_price', 0):.2f}"]),
            solara.Html("div", children=[f"${item.get('current_price', 0):.2f}"]),
            solara.Html("div", children=[f"${item.get('unrealized_pnl', 0):.2f}"]),
            solara.Html("div", children=[
                solara.Button("Sell", on_click=lambda _pid=item.get("id"): on_sell(_pid)),
            ])
        ])

    return solara.Html("div", children=[
        solara.Html("h3", children=["Positions"]),
        solara.Html("div", children=table_children)
    ])
```

#### Analytics Component

```python
import solara
from solara_ui.services.api import PortfolioAPI

@solara.component
def Analytics(portfolio_id):
    """Charts and metrics component"""
    nav_data = solara.reactive([])
    risk_metrics = solara.reactive({})
    loading = solara.reactive(True)

    @solara.effect
    def load():
        async def _fetch():
            try:
                nav = await PortfolioAPI().get_nav_history(portfolio_id)
                risk = await PortfolioAPI().get_risk_report(portfolio_id)
                nav_data.value = nav
                risk_metrics.value = risk
                loading.value = False
            except Exception as e:
                print(f"Analytics load error: {e}")
                loading.value = False
        solara.lab.use_task(_fetch(), dependencies=[portfolio_id])

    return solara.Html("div", children=[
        solara.Html("h3", children=["Analytics"]),
        solara.ProgressCircular(indeterminate=True) if loading.value else None,
        solara.Html("div", children=[f"Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 'N/A')}"]),
        solara.Html("div", children=[f"Max Drawdown: {risk_metrics.get('max_drawdown', 'N/A')}%"]),
    ])
```

## State Management

### Reactive State Pattern

Solara's state management is reactive — components automatically update when state changes:

```python
import solara

@solara.component
def PortfolioApp():
    portfolios, set_portfolios = solara.use_state([])
    current_portfolio = solara.reactive(None)

    @solara.effect
    def load():
        async def _fetch():
            data = await PortfolioAPI().list_portfolios()
            set_portfolios(data)
        solara.lab.use_task(_fetch(), dependencies=[])

    def navigate_to_analytics():
        current_portfolio.value = portfolios[0] if portfolios else None

    return solara.Html("div", children=[
        solara.Button("Go to Analytics", on_click=navigate_to_analytics),
        solara.Html("div", children=[f"Selected: {current_portfolio.value.name if current_portfolio.value else 'None'}"])
    ])
```

### State Updates

State updates are batched and trigger re-renders automatically:

```python
def update_portfolio(portfolio_id):
    # This update will trigger re-render of all components using current_portfolio
    current_portfolio.value = next((p for p in portfolios if p.id == portfolio_id), None)
```

## API Integration

### Service Layer

```python
# solara-ui/services/api.py
import httpx
from solara_ui.models.schemas import Portfolio, Position, Trade, TradeSummary

class PortfolioAPI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.client = httpx.AsyncClient(base_url=base_url)

    # ── Portfolios ──────────────────────────────────────────────
    async def list_portfolios(self) -> list[Portfolio]:
        """GET /api/v1/portfolios/"""
        response = await self.client.get("/api/v1/portfolios/")
        return [Portfolio(**p) for p in response.json()]

    async def create_portfolio(self, name: str) -> Portfolio:
        """POST /api/v1/portfolios/"""
        response = await self.client.post(
            "/api/v1/portfolios/",
            json={"name": name}
        )
        return Portfolio(**response.json())

    async def get_portfolio(self, portfolio_id: str) -> dict:
        """GET /api/v1/{portfolio_id} — returns portfolio + total_value, unrealized_pnl"""
        response = await self.client.get(f"/api/v1/{portfolio_id}")
        return response.json()

    async def delete_portfolio(self, portfolio_id: str) -> None:
        """DELETE /api/v1/{portfolio_id}"""
        await self.client.delete(f"/api/v1/{portfolio_id}")

    # ── Positions ───────────────────────────────────────────────
    async def get_positions(self, portfolio_id: str) -> list[Position]:
        """GET /api/v1/{portfolio_id}/positions"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/positions")
        return [Position(**p) for p in response.json()]

    async def buy_position(self, portfolio_id: str, symbol: str, quantity: float, price: float) -> Position:
        """POST /api/v1/{portfolio_id}/positions"""
        response = await self.client.post(
            f"/api/v1/{portfolio_id}/positions",
            json={"symbol": symbol, "quantity": quantity, "price": price}
        )
        return Position(**response.json())

    async def sell_position(self, portfolio_id: str, position_id: str, quantity: float, price: float) -> dict:
        """POST /api/v1/{portfolio_id}/positions/sell"""
        response = await self.client.post(
            f"/api/v1/{portfolio_id}/positions/sell",
            json={"position_id": position_id, "quantity": quantity, "price": price}
        )
        return response.json()

    async def refresh_prices(self, portfolio_id: str) -> list[dict]:
        """POST /api/v1/{portfolio_id}/positions/refresh"""
        response = await self.client.post(f"/api/v1/{portfolio_id}/positions/refresh")
        return response.json()

    # ── Charts ──────────────────────────────────────────────────
    async def get_nav_history(self, portfolio_id: str, benchmark: str = "SPY") -> list[dict]:
        """GET /api/v1/{portfolio_id}/charts/nav-history"""
        response = await self.client.get(
            f"/api/v1/{portfolio_id}/charts/nav-history",
            params={"benchmark": benchmark}
        )
        return response.json().get("data", [])

    async def get_nav(self, portfolio_id: str) -> list[dict]:
        """GET /api/v1/{portfolio_id}/charts/nav"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/charts/nav")
        return response.json()

    async def get_drawdown(self, portfolio_id: str) -> list[dict]:
        """GET /api/v1/{portfolio_id}/charts/drawdown"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/charts/drawdown")
        return response.json()

    async def get_allocation(self, portfolio_id: str) -> list[dict]:
        """GET /api/v1/{portfolio_id}/charts/allocation"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/charts/allocation")
        return response.json()

    async def get_monthly_returns(self, portfolio_id: str) -> list[dict]:
        """GET /api/v1/{portfolio_id}/charts/monthly-returns"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/charts/monthly-returns")
        return response.json()

    async def get_returns_distribution(self, portfolio_id: str) -> list[dict]:
        """GET /api/v1/{portfolio_id}/charts/returns-distribution"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/charts/returns-distribution")
        return response.json()

    async def get_benchmark_comparison(self, portfolio_id: str) -> list[dict]:
        """GET /api/v1/{portfolio_id}/charts/benchmark-comparison"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/charts/benchmark-comparison")
        return response.json()

    # ── Risk Report ─────────────────────────────────────────────
    async def get_risk_report(self, portfolio_id: str) -> dict:
        """GET /api/v1/{portfolio_id}/risk-report"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/risk-report")
        return response.json()

    # ── Trade Audit ─────────────────────────────────────────────
    async def get_trades(self, portfolio_id: str) -> list[Trade]:
        """GET /api/v1/{portfolio_id}/trades"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/trades")
        return [Trade(**t) for t in response.json()]

    async def get_trade_summary(self, portfolio_id: str) -> TradeSummary:
        """GET /api/v1/{portfolio_id}/trades/summary"""
        response = await self.client.get(f"/api/v1/{portfolio_id}/trades/summary")
        return TradeSummary(**response.json())

    # ── Transactions ────────────────────────────────────────────
    async def create_transaction(self, portfolio_id: str, symbol: str, quantity: float,
                                  price: float, side: str) -> dict:
        """POST /api/v1/{portfolio_id}/transactions"""
        response = await self.client.post(
            f"/api/v1/{portfolio_id}/transactions",
            json={"symbol": symbol, "quantity": quantity, "price": price, "side": side}
        )
        return response.json()
```

### Route Summary (all routes prefixed with `/api/v1`)

| Category | Method | Route | Description |
|----------|--------|-------|-------------|
| Portfolios | GET | `/{portfolio_id}` | Get portfolio details |
| Portfolios | POST | `/{portfolio_id}` | Create portfolio |
| Portfolios | DELETE | `/{portfolio_id}` | Delete portfolio |
| Positions | GET | `/{portfolio_id}/positions` | List positions |
| Positions | POST | `/{portfolio_id}/positions` | Buy position |
| Positions | POST | `/{portfolio_id}/positions/sell` | Sell position |
| Positions | POST | `/{portfolio_id}/positions/refresh` | Refresh prices |
| Transactions | POST | `/{portfolio_id}/transactions` | Record transaction |
| Charts | GET | `/{portfolio_id}/charts/nav-history` | NAV history with benchmark |
| Charts | GET | `/{portfolio_id}/charts/nav` | NAV history (simplified) |
| Charts | GET | `/{portfolio_id}/charts/drawdown` | Drawdown history |
| Charts | GET | `/{portfolio_id}/charts/allocation` | Asset allocation |
| Charts | GET | `/{portfolio_id}/charts/monthly-returns` | Monthly returns |
| Charts | GET | `/{portfolio_id}/charts/returns-distribution` | Returns distribution |
| Charts | GET | `/{portfolio_id}/charts/benchmark-comparison` | Benchmark comparison |
| Risk | GET | `/{portfolio_id}/risk-report` | 9 risk metrics |
| Trades | GET | `/{portfolio_id}/trades` | FIFO trade audit |
| Trades | GET | `/{portfolio_id}/trades/summary` | Trade summary stats |

### Model Schemas

```python
# solara-ui/models/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class Portfolio(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    # Populated via /{portfolio_id} response
    total_value: float = 0.0
    unrealized_pnl: float = 0.0

class Position(BaseModel):
    id: str
    portfolio_id: str
    symbol: str
    quantity: float
    buy_price: float
    current_price: float
    created_at: datetime
    # Derived fields
    current_value: float = 0.0
    unrealized_pnl: float = 0.0

class Trade(BaseModel):
    id: str
    portfolio_id: str
    symbol: str
    transaction_type: str  # "buy" or "sell"
    quantity: float
    price: float
    date: datetime

class TradeSummary(BaseModel):
    total_buys: int
    total_sells: int
    realized_gains: float
    realized_losses: float
    total_realized_pnl: float

class ChartData(BaseModel):
    date: datetime
    portfolio_value: float
    benchmark_value: float

class RiskMetrics(BaseModel):
    portfolio_id: str
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float
    beta: float
    alpha: float
    annualized_return: float
    treynor_ratio: float
    calmar_ratio: float
    ulcer_index: float
```

## Chart Integration

### Plotly Charts

```python
# solara-ui/components/charts.py
import plotly.express as px
import solara

@solara.component
def NavChart(data: list[dict]):
    """NAV history chart using Plotly"""
    if not data:
        return solara.Alert("No data available", type="info")

    import pandas as pd
    df = pd.DataFrame(data)

    fig = px.line(
        df,
        x="date",
        y=["portfolio_value", "benchmark_value"],
        title="NAV History"
    )
    fig.update_layout(template="plotly_dark")

    return solara.PlotlyComponent(fig=fig)
```

### Reactive Updates

Charts automatically update when data changes:

```python
@solara.component
def Analytics(portfolio_id):
    nav_data = solara.reactive([])
    loading = solara.reactive(True)

    @solara.effect
    def load():
        async def _fetch():
            data = await PortfolioAPI().get_nav_history(portfolio_id)
            nav_data.value = data
            loading.value = False
        solara.lab.use_task(_fetch(), dependencies=[portfolio_id])

    if loading.value:
        return solara.ProgressCircular(indeterminate=True)

    return NavChart(data=nav_data.value)
```

## Deployment

### Solara Server Setup

```bash
# Install dependencies
uv pip install -e . --with solara[all]

# Run development server
solara-server run solara-ui/app.py --reload

# Build for production
solara-server build solara-ui/app.py

# Run production server
solara-server run solara-ui/dist/app.py
```

### Docker Deployment

```dockerfile
# docker-compose.yml for Solara frontend
version: '3.8'
services:
  portfolio-manager:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PORTFOLIO_API_URL=http://backend:8000

  solara-frontend:
    image: python:3.11-slim
    command: solara-server run /app/solara-ui/app.py
    ports:
      - "8001:8001"
    volumes:
      - ./solara-ui:/app/solara-ui
    depends_on:
      - portfolio-manager
```

## Testing

### Unit Tests

```python
# tests/test_components.py
import pytest
from solara import mount
from solara_ui.components.dashboard import Dashboard

@pytest.mark.asyncio
async def test_dashboard_component():
    component = Dashboard(portfolio_id="test-1")
    instance = await mount(component)

    # Test component renders
    assert instance is not None

    # Test state initialization
    assert component.portfolio.value is None
    assert component.positions.value == []
```

### End-to-End Tests

```python
# tests/e2e/test_navigation.py
import pytest
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_portfolio_selection():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:8001")

        # Select portfolio
        await page.click("text=Select Portfolio")
        await page.click("text=Test Portfolio")

        # Verify navigation
        await page.wait_for_selector(".dashboard")

        await browser.close()
```

## Development Workflow

### Local Development

```bash
# Create virtual environment
python -m venv solara-env
source solara-env/bin/activate

# Install dependencies
uv pip install -e . --with solara[dev,all]

# Run development server
solara-server run solara-ui/app.py --reload

# Run tests
pytest tests/
```

### Hot Reloading

Solara's development server supports hot reloading:

```bash
solara-server run solara-ui/app.py --reload
```

Changes to component files automatically trigger re-render.

## Future Enhancements

### Mobile Support

```python
# solara-ui/mobile.py
from solara import WebView

@solara.component
def MobileApp():
    return WebView(
        src="https://solara.example.com",
        enable_javascript=True,
        enable_inspector=True
    )
```

### Plugin System

```python
# solara-ui/plugins/custom_charts.py
from solara import component

@solara.component
def CustomChart():
    """Custom chart plugin"""
    return solara.Html("div", children=["Custom Chart Implementation"])
```

## Conclusion

This design document provides the technical specifications for the Solara frontend implementation. The architecture emphasizes:

- **Reactive state management**: Automatic UI updates via `solara.reactive` and `@solara.effect`
- **Component-based design**: Reusable and maintainable with `@solara.component`
- **Type safety**: Pydantic models shared between frontend and backend
- **Production-ready**: Built on Starlette and ipyvuetify
- **Correct async patterns**: `solara.lab.use_task()` instead of `asyncio.run()`
- **Testable**: Unit and end-to-end testing support

The implementation will follow the patterns described here, ensuring consistency and maintainability.
