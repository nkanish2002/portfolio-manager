# Portfolio Manager - Solara Frontend Migration Plan

## Overview
Replace the React hash-router frontend with Solara, a modern Python web framework that builds high-quality web applications in pure Python. This eliminates JavaScript complexity, hash routing issues, and provides a consistent, maintainable solution.

## Why Solara?
- **No hash router issues**: Solara uses direct navigation, no `#/analytics/:id` complexity
- **Python-first**: Same stack as backend, shared models, no TypeScript bridging
- **Production-ready**: Built on fast, production-grade tooling (Starlette, ipyvuetify)
- **Fully reactive**: Automatic UI updates like spreadsheets - no manual re-rendering
- **Type-safe**: Python's optional typing throughout state management to UI components
- **Testable**: Unit tests and end-to-end tests without browser
- **Component library**: Built-in components (ipyvuetify) + custom function components
- **Browser support**: Runs in browser natively, no separate frontend build process

## Architecture

```
portfolio-manager/
├── src/portfolio_manager/
│   ├── main.py                    # FastAPI backend (unchanged)
│   └── routes/                    # API endpoints (unchanged)
├── solara-ui/                       # NEW: Solara frontend
│   ├── __init__.py
│   ├── app.py                       # Main SolaraApp
│   ├── components/
│   │   ├── __init__.py
│   │   ├── dashboard.py             # Portfolio overview (Function Component)
│   │   ├── positions.py             # Position list/management
│   │   ├── trades.py                # Trade audit log
│   │   ├── analytics.py             # Charts/metrics (Solara charts)
│   │   ├── portfolio_selector.py    # Portfolio dropdown (Widget Component)
│   │   └── nav_header.py            # Navigation bar
│   ├── services/
│   │   └── api.py                   # Async HTTP client
│   └── models/
│       └── schemas.py               # Pydantic models (shared with backend)
└── pyproject.toml                   # Solara dependencies
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| UI Framework | Solara (Python web framework) |
| Widget Components | ipyvuetify (Vuetify/Vue components) |
| HTTP Client | `httpx` (async) |
| Data Validation | Pydantic (shared with backend) |
| Charts | Solara's built-in reactive charts or Plotly |
| Build | uv + `solara-server` (Starlette-based) |
| Styling | ipyvuetify themes, CSS-in-Python |

## Key Changes

### 1. Routing (No Hash Router!)
Solara uses direct component composition, no URL parsing needed:
```python
# Instead of: navigate('/analytics/:id')
# Solara uses component composition - no routing needed for internal navigation

@component
def PortfolioApp():
    return VStack([
        PortfolioSelector(),
        DashboardScreen() if show_dashboard else PositionsScreen() if show_positions else AnalyticsScreen()
    ])
```

### 2. Portfolio Context
Store current portfolio in component state:
```python
@component
def PortfolioApp():
    portfolios = use_state(list[Portfolio], [])
    current_portfolio = use_state(Portfolio | None, None)
    
    # Auto-updates UI when state changes
    def on_portfolio_select(id):
        current_portfolio.value = next(p for p in portfolios.value if p.id == id)
```

### 3. Charts (Reactive)
Solara's built-in reactive charts:
- **Plotly charts** (reactive, browser-native)
- **Solara charts** (built-in reactive visualizations)
- **Custom components** for specialized charts
- **Automatic updates** when data changes

Example:
```
NAV History (SPY Benchmark)
┌─────────────────────┬────────────┬────────────┐
│ Date                │ Portfolio  │ Benchmark  │
├─────────────────────┼────────────┼────────────┤
│ 2026-06-09          │ $100.00    │ $100.00    │
│ 2026-06-10          │ $1,300.00  │ $100.06    │
└─────────────────────┴────────────┴────────────┘
```

### 4. API Integration
```python
# textual-ui/services/api.py
import httpx
from portfolio_manager.models.schemas import Portfolio, Position

class PortfolioAPI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.client = httpx.AsyncClient(base_url=base_url)
    
    async def list_portfolios(self) -> list[Portfolio]:
        response = await self.client.get("/api/v1/portfolios/")
        return [Portfolio(**p) for p in response.json()]
    
    async def get_positions(self, portfolio_id: str) -> list[Position]:
        response = await self.client.get(f"/api/v1/portfolios/{portfolio_id}/positions")
        return [Position(**p) for p in response.json()]
```

## Migration Steps

### Phase 1: Core Infrastructure (3-5 days)
1. **Setup Solara project structure**
   - Create `solara-ui/` directory
   - Set up `pyproject.toml` with Solara dependencies
   - Configure `uv` for dependency management
   - Install `solara[assets]` for air-gapped environments if needed

2. **API Service Layer**
   - Create `PortfolioAPI` client
   - Implement async methods for all endpoints
   - Add error handling and retry logic

3. **Shared Models**
   - Move Pydantic schemas to shared location
   - Ensure backend/frontend model compatibility

### Phase 2: Core Components (5-7 days)
4. **Dashboard Component**
   - Portfolio overview cards
   - Total value, P&L, position count
   - Portfolio dropdown selector (Widget Component)

5. **Positions Component**
   - Position table with columns
   - Edit/sell functionality
   - Refresh prices button

6. **Trades Component**
   - Trade history table
   - Filtering by type/date
   - Summary statistics

7. **Analytics Component**
   - Reactive charts (Plotly/Solara)
   - Risk metrics display
   - Monthly returns table

8. **Settings Component**
   - API URL configuration
   - Theme settings

### Phase 3: State Management (2-3 days)
9. **App State**
   - Global portfolio state
   - Auto-refresh on switch
   - Clean shutdown

### Phase 4: Deployment (3-5 days)
10. **Solara Server Setup**
    - Configure `solara-server[starlette,dev]`
    - Set up reverse proxy (if needed)
    - Test browser compatibility

12. **Responsive UI**
    - Mobile-friendly layouts
    - Touch support
    - Adaptive navigation

### Phase 5: Polish & Testing (3-5 days)
11. **Styling**
    - Custom theme
    - Dark mode support
    - Consistent spacing

12. **Error Handling**
    - Network errors
    - Validation errors
    - User-friendly messages

13. **Testing**
    - Manual testing
    - Edge cases
    - Performance tuning

## Dependencies (pyproject.toml)

```toml
[project]
name = "portfolio-manager-solara"
version = "0.1.0"
description = "Portfolio Manager Solara Frontend"
requires-python = ">=3.11"

dependencies = [
    "solara>=0.1.0",
    "solara-ui[all]",
    "solara-server[starlette,dev]",
    "httpx>=0.24.0",
    "pydantic>=2.0",
    "plotly>=6.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
]
```

## Browser Access

### Option 1: Solara Server Direct
```bash
# Run solara-server
solara-server run solara-ui/app.py --host 0.0.0.0 --port 8001
```

### Option 2: Reverse Proxy
```nginx
# nginx config
location /solara/ {
    proxy_pass http://localhost:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    # WebSocket support
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Option 3: Docker
```dockerfile
# In docker-compose.yml
solara-server:
    image: python:3.11-slim
    command: solara-server run /app/solara-ui/app.py
    ports:
        - "8001:8001"
    volumes:
        - ./solara-ui:/app/solara-ui
```

## Benefits of This Approach

| Issue | React Solution | Solara Solution |
|-------|---------------|-----------------|
| Hash routing bugs | Complex router logic | Direct component composition |
| JavaScript complexity | TypeScript, React, Vite | Pure Python |
| Build process | npm, webpack, build steps | `uv run solara` |
| Browser compatibility | Cross-browser testing | One codebase |
| Performance | React re-renders | Automatic reactive updates |
| Debugging | Browser devtools | Terminal logs, print |
| Deployment | Static files, CDN | Single Python process |

## Estimated Timeline

- **Phase 1**: 3-5 days
- **Phase 2**: 5-7 days
- **Phase 3**: 2-3 days
- **Phase 4**: 3-5 days
- **Phase 5**: 3-5 days
- **Total**: 16-25 days (3-4 weeks)

## Risk Mitigation

1. **Keep backend unchanged**: No API modifications needed
2. **Incremental migration**: Both frontends can coexist
3. **Feature parity**: Textual supports all React features
4. **Testing**: Manual testing before full deployment
5. **Rollback**: React frontend remains available

## Future Enhancements

- **Mobile app**: Solara + WebView for iOS/Android
- **Plugin system**: Custom components, themes
- **Offline mode**: Local caching, queue operations
- **Dark mode**: ipyvuetify dark theme support
- **Export functionality**: PDF reports, CSV exports

## Conclusion

This migration replaces a complex React frontend with a simpler, more maintainable Solara solution that:
- Eliminates routing bugs
- Uses Python throughout
- Runs in browser natively (no separate frontend build)
- Provides automatic reactive updates (like spreadsheets)
- Reduces technical debt
- Offers production-grade tooling (Starlette, ipyvuetify)

The investment of 3-4 weeks will save ongoing maintenance of React hash router issues and provide a more robust, maintainable codebase.
