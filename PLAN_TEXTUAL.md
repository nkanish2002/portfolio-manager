# Portfolio Manager - Textual Frontend Migration Plan

## Overview
Replace the React hash-router frontend with Textual (desktop) and Textual-Web (browser), using Python as the primary stack. This eliminates JavaScript complexity, hash routing issues, and provides a consistent terminal-first UI.

## Why Textual?
- **No hash router issues**: Textual uses direct navigation, no `#/analytics/:id` complexity
- **Python-first**: Same stack as backend, shared models, no TypeScript bridging
- **Terminal-first**: Works in terminal, SSH, Docker, no browser dependencies
- **Textual-Web**: Browser version via `textual-web` (HTTP/WS streaming)
- **Responsive**: Built-in responsive layouts, works on mobile/desktop

## Architecture

```
portfolio-manager/
├── src/portfolio_manager/
│   ├── main.py                    # FastAPI backend (unchanged)
│   └── routes/                    # API endpoints (unchanged)
├── textual-ui/                      # NEW: Textual frontend
│   ├── __init__.py
│   ├── app.py                       # Main TextualApp
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── dashboard.py             # Portfolio overview
│   │   ├── positions.py             # Position list/management
│   │   ├── trades.py                # Trade audit log
│   │   ├── analytics.py             # Charts/metrics (text-based)
│   │   └── settings.py              # App settings
│   ├── widgets/
│   │   ├── portfolio_dropdown.py    # Portfolio selector
│   │   ├── nav_header.py            # Navigation bar
│   │   └── data_tables.py           # Custom tables
│   ├── services/
│   │   └── api.py                   # Async HTTP client
│   └── models/
│       └── schemas.py               # Pydantic models (shared with backend)
└── pyproject.toml                   # Textual dependencies
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| UI Framework | Textual (desktop), Textual-Web (browser) |
| HTTP Client | `httpx` (async) |
| Data Validation | Pydantic (shared with backend) |
| Styling | Textual CSS (CSS-like syntax) |
| Charts | Rich + text-based visualization (ASCII plots) |
| Build | uv + textual-web for browser |

## Key Changes

### 1. Routing (No Hash Router!)
Textual uses direct screen navigation:
```python
# Instead of: navigate('/analytics/:id')
await self.push_screen(AnalyticsScreen(portfolio_id=id))

# Navigation is explicit, no URL parsing needed
```

### 2. Portfolio Context
Store current portfolio in app state:
```python
class PortfolioApp(App):
    current_portfolio: Portfolio | None = None
    portfolios: list[Portfolio] = []
```

### 3. Charts (Text-Based)
For terminal compatibility, use:
- **ASCII plots** with `rich` library
- **Text tables** for data
- **Progress bars** for loading
- **Markdown rendering** for reports

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
1. **Setup Textual project structure**
   - Create `textual-ui/` directory
   - Set up `pyproject.toml` with Textual dependencies
   - Configure `uv` for dependency management

2. **API Service Layer**
   - Create `PortfolioAPI` client
   - Implement async methods for all endpoints
   - Add error handling and retry logic

3. **Shared Models**
   - Move Pydantic schemas to shared location
   - Ensure backend/frontend model compatibility

### Phase 2: Core Screens (5-7 days)
4. **Dashboard Screen**
   - Portfolio overview cards
   - Total value, P&L, position count
   - Portfolio dropdown selector

5. **Positions Screen**
   - Position table with columns
   - Edit/sell functionality
   - Refresh prices button

6. **Trades Screen**
   - Trade history table
   - Filtering by type/date
   - Summary statistics

7. **Analytics Screen**
   - Text-based charts (ASCII plots)
   - Risk metrics display
   - Monthly returns table

8. **Settings Screen**
   - API URL configuration
   - Theme settings

### Phase 3: Navigation & State (2-3 days)
9. **App Navigation**
   - Sidebar navigation
   - Portfolio switching
   - Screen routing

10. **Portfolio Context**
    - Global portfolio state
    - Auto-refresh on switch
    - Clean shutdown

### Phase 4: Browser Support (3-5 days)
11. **Textual-Web Setup**
    - Configure `textual-web` for HTTP/WS
    - Set up reverse proxy (if needed)
    - Test browser compatibility

12. **Responsive UI**
    - Mobile-friendly layouts
    - Touch support
    - Adaptive navigation

### Phase 5: Polish & Testing (3-5 days)
13. **Styling**
    - Custom theme
    - Dark mode support
    - Consistent spacing

14. **Error Handling**
    - Network errors
    - Validation errors
    - User-friendly messages

15. **Testing**
    - Manual testing
    - Edge cases
    - Performance tuning

## Dependencies (pyproject.toml)

```toml
[project]
name = "portfolio-manager-textual"
version = "0.1.0"
description = "Portfolio Manager Textual Frontend"
requires-python = ">=3.11"

dependencies = [
    "textual>=1.0.0",
    "textual-web>=0.1.0",
    "httpx>=0.24.0",
    "pydantic>=2.0",
    "rich>=13.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
]
```

## Browser Access

### Option 1: Textual-Web Direct
```bash
# Run textual-web server
textual-web run textual-ui/app.py --host 0.0.0.0 --port 8001
```

### Option 2: Reverse Proxy
```nginx
# nginx config
location /textual/ {
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
textual-web:
    image: python:3.11-slim
    command: textual-web run /app/textual-ui/app.py
    ports:
        - "8001:8001"
    volumes:
        - ./textual-ui:/app/textual-ui
```

## Benefits of This Approach

| Issue | React Solution | Textual Solution |
|-------|---------------|------------------|
| Hash routing bugs | Complex router logic | Direct screen navigation |
| JavaScript complexity | TypeScript, React, Vite | Pure Python |
| Build process | npm, webpack, build steps | `uv run textual` |
| Browser compatibility | Cross-browser testing | One codebase |
| Performance | React re-renders | Direct DOM updates |
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

- **Desktop app**: Package with PyInstaller
- **Mobile app**: Textual + BeeWare for iOS/Android
- **Plugin system**: Custom widgets, themes
- **Offline mode**: Local caching, queue operations

## Conclusion

This migration replaces a complex React frontend with a simpler, more maintainable Textual solution that:
- Eliminates routing bugs
- Uses Python throughout
- Works in terminal, SSH, and browser
- Provides consistent user experience
- Reduces technical debt

The investment of 3-4 weeks will save ongoing maintenance of React hash router issues and provide a more robust, maintainable codebase.
