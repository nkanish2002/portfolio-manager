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

Widget components are pre-built UI elements from ipyvuetify:

#### PortfolioSelector Widget
```python
@component
def PortfolioSelector():
    """Portfolio dropdown widget using ipyvuetify.Select"""
    portfolios = use_state(list[Portfolio], [])
    current_portfolio = use_state(Portfolio | None, None)
    
    # Load portfolios on mount
    @effect
    def load_portfolios():
        async def _load():
            portfolios.value = await PortfolioAPI().list_portfolios()
        asyncio.run(_load())
    
    # Handle selection change
    def on_select(portfolio_id):
        current_portfolio.value = next(
            p for p in portfolios.value if p.id == portfolio_id
        )
    
    # Build options
    options = [{"text": p.name, "value": p.id} for p in portfolios.value]
    
    return VSelect(
        v_model=current_portfolio.value.id if current_portfolio.value else None,
        items=options,
        label="Select Portfolio",
        on_change=on_select
    )
```

#### NavHeader Widget
```python
@component
def NavHeader():
    """Navigation header with logo and portfolio context"""
    current_portfolio = use_state(Portfolio | None, None)
    
    return VAppBar(
        app=True,
        clipped_left=True,
        color="primary",
        children=[
            VToolbarTitle(children=["Portfolio Manager"]),
            VBtn(
                icon="mdi-account-circle",
                text=True,
                children=[current_portfolio.value.name if current_portfolio.value else "No Portfolio"],
                on_click=lambda: print("Portfolio info")  # TODO: Add modal
            )
        ]
    )
```

### Function Components (Custom Logic)

Function components combine state, widgets, and business logic:

#### Dashboard Component
```python
@component
def Dashboard():
    """Portfolio overview dashboard"""
    portfolio = use_state(Portfolio | None, None)
    positions = use_state(list[Position], [])
    metrics = use_state(dict, {})
    
    @effect([portfolio])
    def load_dashboard():
        async def _load():
            if portfolio.value:
                positions.value = await PortfolioAPI().get_positions(portfolio.value.id)
                metrics.value = await PortfolioAPI().get_metrics(portfolio.value.id)
        asyncio.run(_load())
    
    return VContainer(
        fluid=True,
        children=[
            VRow([
                VCol(cols=4, children=[
                    MetricCard(title="Portfolio Value", value=metrics.get("total_value", "$0"))
                ]),
                VCol(cols=4, children=[
                    MetricCard(title="P&L", value=metrics.get("pnl", "$0"))
                ]),
                VCol(cols=4, children=[
                    MetricCard(title="Position Count", value=str(len(positions.value)))
                ])
            ]),
            VRow(children=[
                VCol(cols=12, children=[
                    PositionsTable(positions=positions.value)
                ])
            ])
        ]
    )
```

#### Positions Component
```python
@component
def Positions():
    """Position management component"""
    positions = use_state(list[Position], [])
    
    @effect
    def load_positions():
        async def _load():
            positions.value = await PortfolioAPI().get_positions()
        asyncio.run(_load())
    
    def on_sell(position_id):
        # TODO: Add confirmation dialog and API call
        print(f"Selling position {position_id}")
    
    def on_edit(position_id):
        # TODO: Add edit modal
        print(f"Editing position {position_id}")
    
    return VTable(
        headers=[
            {"text": "Symbol", "value": "symbol"},
            {"text": "Quantity", "value": "quantity"},
            {"text": "Avg Price", "value": "avg_price"},
            {"text": "Current Value", "value": "current_value"},
            {"text": "P&L", "value": "pnl"},
            {"text": "Actions", "value": "actions"}
        ],
        items=positions.value,
        children=[
            lambda item: VBtn(icon="mdi-pencil", small=True, on_click=lambda: on_edit(item.id)),
            lambda item: VBtn(icon="mdi-close", small=True, color="error", on_click=lambda: on_sell(item.id))
        ]
    )
```

#### Analytics Component
```python
@component
def Analytics():
    """Charts and metrics component"""
    portfolio = use_state(Portfolio | None, None)
    nav_data = use_state(list, [])
    risk_metrics = use_state(dict, {})
    
    @effect([portfolio])
    def load_analytics():
        async def _load():
            if portfolio.value:
                nav_data.value = await PortfolioAPI().get_nav_history(portfolio.value.id)
                risk_metrics.value = await PortfolioAPI().get_risk_metrics(portfolio.value.id)
        asyncio.run(_load())
    
    return VContainer(
        fluid=True,
        children=[
            VRow(children=[
                VCol(cols=8, children=[
                    NavChart(data=nav_data.value)
                ]),
                VCol(cols=4, children=[
                    RiskMetricsCard(metrics=risk_metrics.value)
                ])
            ])
        ]
    )
```

## State Management

### Reactive State Pattern

Solara's state management is reactive - components automatically update when state changes:

```python
@component
def PortfolioApp():
    portfolios = use_state(list[Portfolio], [])
    current_portfolio = use_state(Portfolio | None, None)
    
    # Load portfolios once
    @effect
    def load_portfolios():
        async def _load():
            portfolios.value = await PortfolioAPI().list_portfolios()
        asyncio.run(_load())
    
    # Navigation based on current portfolio
    def navigate_to_analytics():
        current_portfolio.value = portfolios.value[0] if portfolios.value else None
    
    return VAppBar(
        children=[
            VBtn(
                text="Analytics",
                on_click=navigate_to_analytics
            )
        ]
    )
```

### State Updates

State updates are batched and trigger re-renders automatically:

```python
def update_portfolio(portfolio_id):
    # This update will trigger re-render of all components using current_portfolio
    current_portfolio.value = next(p for p in portfolios.value if p.id == portfolio_id)
```

## API Integration

### Service Layer

```python
# solara-ui/services/api.py
import httpx
from portfolio_manager.models.schemas import Portfolio, Position, ChartData

class PortfolioAPI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.client = httpx.AsyncClient(base_url=base_url)
    
    async def list_portfolios(self) -> list[Portfolio]:
        response = await self.client.get("/api/v1/portfolios/")
        return [Portfolio(**p) for p in response.json()]
    
    async def get_positions(self, portfolio_id: str | None = None) -> list[Position]:
        if portfolio_id:
            response = await self.client.get(f"/api/v1/portfolios/{portfolio_id}/positions")
        else:
            response = await self.client.get("/api/v1/portfolios/")
        return [Position(**p) for p in response.json()]
    
    async def get_nav_history(self, portfolio_id: str, benchmark: str = "SPY") -> list[ChartData]:
        response = await self.client.get(
            "/api/v1/charts/nav-history",
            params={"portfolio_id": portfolio_id, "benchmark": benchmark}
        )
        return [ChartData(**d) for d in response.json().get("data", [])]
    
    async def get_risk_metrics(self, portfolio_id: str) -> dict:
        response = await self.client.get(
            "/api/v1/risk-report",
            params={"portfolio_id": portfolio_id}
        )
        return response.json()
    
    async def get_metrics(self, portfolio_id: str) -> dict:
        response = await self.client.get(f"/api/v1/portfolios/{portfolio_id}/metrics")
        return response.json()
```

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

class Position(BaseModel):
    id: str
    portfolio_id: str
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    created_at: datetime

class ChartData(BaseModel):
    date: datetime
    portfolio_value: float
    benchmark_value: float

class RiskMetrics(BaseModel):
    portfolio_id: str
    sharpe_ratio: float
    max_drawdown: float
    annualized_return: float
```

## Chart Integration

### Plotly Charts

```python
# solara-ui/components/charts.py
import plotly.express as px
import solara as sl

@component
def NavChart(data: list[ChartData]):
    """NAV history chart using Plotly"""
    if not data:
        return sl.VAlert(children=["No data available"], type="info")
    
    # Convert to DataFrame for Plotly
    import pandas as pd
    df = pd.DataFrame([{
        "date": d.date,
        "portfolio": d.portfolio_value,
        "benchmark": d.benchmark_value
    } for d in data])
    
    # Create Plotly figure
    fig = px.line(
        df,
        x="date",
        y=["portfolio", "benchmark"],
        title="NAV History"
    )
    
    # Convert to Solara component
    return sl.PlotlyComponent(fig=fig)
```

### Reactive Updates

Charts automatically update when data changes:

```python
@component
def Analytics():
    nav_data = use_state(list, [])
    
    @effect([portfolio])
    def load_data():
        async def _load():
            nav_data.value = await PortfolioAPI().get_nav_history(portfolio.value.id)
        asyncio.run(_load())
    
    # Chart updates automatically when nav_data changes
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
# docker-compose.yml
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
    component = Dashboard()
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

@component
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

@component
def CustomChart():
    """Custom chart plugin"""
    return VContainer(children=["Custom Chart Implementation"])
```

## Conclusion

This design document provides the technical specifications for the Solara frontend implementation. The architecture emphasizes:

- **Reactive state management**: Automatic UI updates
- **Component-based design**: Reusable and maintainable
- **Type safety**: Python's optional typing
- **Production-ready**: Built on Starlette and ipyvuetify
- **Testable**: Unit and end-to-end testing support

The implementation will follow the patterns described here, ensuring consistency and maintainability.