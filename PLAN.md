# Portfolio Manager — Master Plan

> **Status:** Foundation, Core Logic, Analytics & Visualization Complete. React UI Phase In Progress. 🚀
> **Last Updated:** June 08, 2026
> **Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy (Async), SQLite, HTMX/Tailwind (legacy), Plotly, yfinance, React (new).
> **Tests:** 41/41 passing (pytest).
> **Docker:** Dockerfile + docker-compose.yaml ready for deployment.

---

## 1. Vision & Scope

Build a professional, self-hosted portfolio management tool that mirrors the capabilities of Schwab's brokerage interface for personal tracking.

**Key Capabilities:**
- Multi-asset-class support (Equities, Options, Futures, Bonds, ETFs, MFs, ADRs, CFDs, Crypto, Cash).
- Real-time price fetching via `yfinance` (extensible to paid APIs).
- Advanced risk analytics (Sharpe, Sortino, VaR, Beta, Alpha, etc.).
- Benchmark comparison (Portfolio vs. S&P 500, Custom indices).
- Interactive visualizations (Plotly charts for NAV, allocation, drawdowns).
- Clean, dark-themed web UI with HTMX for dynamic updates without SPA complexity.

---

## 2. System Architecture & Components

```text
portfolio-manager/
├── src/portfolio_manager/
│   ├── main.py              # [CORE] FastAPI app factory, lifespan, middleware
│   ├── config.py            # [CORE] Pydantic settings (.env, DB URL, toggles)
│   ├── database.py          # [CORE] Async SQLAlchemy engine, session, Base
│   ├── models/              # [DATA] ORM definitions (Asset, Portfolio, Position, Transaction, Benchmark)
│   ├── routes/              # [API] HTTP handlers (CRUD, Dashboard, Transactions, WS)
│   ├── services/            # [LOGIC] Business rules (Risk engine, Calculations, Data feeds)
│   ├── templates/           # [UI-LEGACY] Jinja2 + Tailwind + HTMX (deprecated)
│   └── static/              # [UI-NEW] Vite React build output (served by FastAPI)
├── frontend/                # [UI-NEW] Vite + React + TypeScript SPA
│   ├── src/
│   │   ├── components/      # React components (PortfolioCard, PositionTable, SellModal)
│   │   ├── hooks/           # Custom hooks (useWebSocket, usePortfolio, useMarketData)
│   │   ├── pages/           # Route pages (Dashboard, Positions, Analytics, TradeAudit, Settings)
│   │   ├── store/           # Zustand stores (portfolioStore, positionStore, tradeStore)
│   │   ├── services/        # API client (axios, WebSocket manager)
│   │   ├── charts/          # Chart components (Lightweight Charts, Recharts)
│   │   └── App.tsx          # Root component with TanStack Router
│   ├── package.json         # Frontend dependencies
│   └── vite.config.ts       # Vite configuration
├── tests/                   # [QA] Pytest suite
├── migrations/              # [DB] Alembic migrations
├── pyproject.toml           # [DEPS] Hatch configuration, dependencies
└── PLAN.md                  # [DOC] This file
```

---

## 3. Phased Implementation Roadmap

### Phase 1: Foundation & Core Infrastructure
**Goal:** Set up the project, database models, and basic app structure.
- [x] Project skeleton (`pyproject.toml`, venv, FastAPI setup)
- [x] Database configuration (Async SQLAlchemy, SQLite)
- [x] Core models (`Asset`, `Portfolio`, `Position`, `Transaction`, `Benchmark`, `base`)
- [x] Basic API structure (Portfolios CRUD)
- [x] Basic UI structure (Jinja2, Tailwind, HTMX, Dark theme)
**Status:** ✅ 100% Complete

### Phase 2: Core Business Logic & Data Integration
**Goal:** Implement risk metrics, price fetching, and transaction handling.
- [x] Risk metrics engine (`risk.py`: Sharpe, Sortino, Max DD, VaR, Beta, Alpha, Treynor, Calmar, Ulcer)
- [x] Portfolio calculation service (`portfolio_calc.py`: NAV, returns, allocation, P&L)
- [x] Data feed abstraction & implementation (`data_feed.py`: yfinance integration)
- [x] Transaction recording API (Buy, Sell, Dividend, Split, Fee)
- [x] Price refresh endpoint
- [x] Dashboard UI with position table and P&L coloring
**Status:** ✅ 100% Complete

### Phase 3: Advanced Analytics & Visualization ✅ **COMPLETED**
**Goal:** Add benchmark comparison, interactive charts, and portfolio classification.
- [x] **Benchmark Comparison Service** (`benchmark.py`): Calculate excess returns, tracking error, information ratio, correlation, benchmark overlay data.
- [x] **Plotly Chart Integration**: Backend chart data generation (`chart_data.py`) + frontend rendering in `dashboard.html`:
  - Asset allocation pie chart (donut style)
  - Drawdown waterfall bar chart
  - NAV growth line chart (ready for benchmark overlay)
  - Returns distribution histogram
  - Monthly returns heatmap
- [x] **Portfolio Classification** (`classification.py`): Sector/industry/region mapping for 150+ tickers including equities, ETFs, and crypto.
- [x] **API Endpoints** (`charts.py`): `/api/v1/{portfolio_id}/charts/*` for all chart data, `/api/v1/{portfolio_id}/risk-report` for comprehensive risk metrics.
- [x] **Dashboard Template**: Enhanced with Plotly charts, classification cards, and interactive risk report section.
- [x] **Dockerfile**: Multi-stage build with uv, Python 3.11, health check, volume persistence.
- [x] **docker-compose.yaml**: Service definition with named volume, port mapping, environment config.
- [x] **.dockerignore**: Proper exclusions for clean builds.
**Status:** ✅ 100% Complete

### Phase 5: React Frontend SPA ✅ **COMPLETED**
**Goal:** Replace the Jinja2/HTMX UI with a modern React + TypeScript SPA alongside the FastAPI backend.
- [x] **Vite + React + TypeScript**: Scaffold the frontend project
  - [x] Vite configuration (dev server, proxy to FastAPI `/api/v1/`)
  - [x] Tailwind CSS setup (port existing dark theme colors)
  - [x] **React Router v7** for client-side routing (Dashboard, Positions, Analytics, Settings)
  - [x] **Axios** API client (configured for base URL `/api/v1/`)
- [x] **Zustand State Management**: Lightweight stores
  - [x] `portfolioStore` — fetched portfolios, current portfolio state, create portfolio
  - [x] `positionStore` — local position cache, optimistic updates
- [x] **Page Components**: Mirror existing Jinja2 pages in React
  - [x] `DashboardPage` — portfolio cards with Total Value, Positions, date info, "+ New Portfolio" modal
  - [x] `PositionsPage` — portfolio detail view with summary stats, Plotly charts, positions table
  - [x] `AnalyticsPage` — placeholder UI (portfolio comparison, risk metrics)
  - [x] `SettingsPage` — data sources, display preferences
- [x] **Reusable Components**:
  - [x] `PortfolioCard` — portfolio summary card with Total Value, Positions, dates
  - [x] `PositionTable` — positions table with gain/loss coloring, calculated metrics from backend
  - [x] `CreatePortfolioModal` — modal for creating new portfolios with name, currency
- [x] **Chart Integration**: Plotly.js charts rendered in React
  - [x] `AllocationChart` — donut pie chart via Plotly.js
  - [x] `DrawdownChart` — waterfall bar chart
  - [x] `NavChart` — NAV growth line chart
  - [x] `ReturnsDistributionChart` — histogram
  - [x] `MonthlyReturnsChart` — heatmap
  - [x] `BenchmarkComparisonChart` — overlay chart
- [x] **API Endpoints Fixed**: Added missing `GET /api/v1/portfolios/{id}/positions` endpoint
- [x] **SPA Fallback Route**: FastAPI properly serves React SPA for non-API routes
- [x] **Docker Update**: Multi-stage build with Vite + Python, serves React static files from FastAPI
**Status:** ✅ 100% Complete

### Phase 6: Real-Time Market Data Streaming
**Goal:** Replace the "Refresh Prices" button with live WebSocket market data.
- [ ] **FastAPI WebSocket Service**: `/ws/quotes/{symbol}` endpoint
  - [ ] Accept multiple symbol subscriptions per connection
  - [ ] Debounce + batch updates (1s window) to avoid overwhelming the server
  - [ ] Reconnect logic on the server side
- [ ] **React WebSocket Hook**: `useWebSocket`
  - [ ] Auto-connect on component mount
  - [ ] Exponential backoff reconnection
  - [ ] Message parsing and dispatch to stores
- [ ] **Live Price Updates in UI**:
  - [ ] Flash highlight on price change (green for up, red for down)
  - [ ] Auto-refresh positions table when portfolio ID changes
  - [ ] Fallback to manual refresh if WebSocket unavailable
- [ ] **Price Caching Layer**:
  - [ ] Server-side cache (in-memory TTL dict) to avoid repeated yfinance calls
  - [ ] Cache invalidation on new position creation
**Status:** 📋 Pending

### Phase 7: Sell Operations & Trade Audit Trail
**Goal:** Complete buy/sell workflow with full trade history and P&L tracking.
- [ ] **Backend — Sell Endpoint**:
  - [ ] `POST /api/v1/portfolios/{id}/positions/sell` — partial or full sell
  - [ ] Validate quantity ≤ current position quantity
  - [ ] Calculate realized P&L (FIFO or weighted avg cost)
  - [ ] Create Sell transaction record
  - [ ] Update position: reduce quantity, remove if fully liquidated, update avg cost basis
  - [ ] Return updated position with P&L delta
- [ ] **Frontend — Sell Modal**:
  - [ ] Quantity picker (slider + input, max = current quantity)
  - [ ] Price input (pre-filled with current market price)
  - [ ] Fee input
  - [ ] **P&L Preview**: Show estimated realized gain/loss before confirming
  - [ ] Confirmation step with summary (symbol, qty, price, fees, net proceeds, P&L)
- [ ] **Trade Audit Trail**:
  - [ ] `GET /api/v1/portfolios/{id}/trades` — paginated trade history
  - [ ] Frontend `TradeAuditPage` with filterable table (date, symbol, type, qty, price, fees, P&L, notes)
  - [ ] Sort by date/symbol/type
  - [ ] Filter by date range, transaction type (Buy/Sell/Dividend)
  - [ ] CSV export button
  - [ ] Edit/delete trade (admin-only, with reason field)
  - [ ] Realized P&L summary widget (total gains, total losses, net P&L)
**Status:** 📋 Pending

### Phase 8: Professional Charting & Benchmark Visualization
**Goal:** Upgrade from basic Plotly charts to professional-grade financial visualizations.
- [ ] **Charting Library Selection & Setup**:
  - [ ] Evaluate **TradingView Lightweight Charts** (lightweight, professional, free) vs **Recharts** (React-native, customizable)
  - [ ] Install and configure in React frontend
- [ ] **Portfolio NAV Chart**:
  - [ ] Line chart showing portfolio value over time
  - [ ] Benchmark overlay (SPY, QQQ, or custom index) on same chart
  - [ ] Interactive crosshair, zoom, pan
  - [ ] Time range selector (1W, 1M, 3M, 1Y, ALL)
- [ ] **Drawdown Chart**:
  - [ ] Waterfall-style bar chart showing drawdown periods
  - [ ] Color-coded (green = recovering, red = deepening)
- [ ] **Sector Allocation**:
  - [ ] Donut/pie chart with interactive legend
  - [ ] Click to highlight/filter positions by sector
- [ ] **Monthly Returns Heatmap**:
  - [ ] Grid showing performance by month/year (green/red cells)
  - [ ] Hover to see exact percentage
- [ ] **Benchmark Comparison Panel**:
  - [ ] Stats sidebar: Tracking error, Information ratio, Correlation, Excess returns
  - [ ] Visual benchmark line overlay on NAV chart
- [ ] **Risk Metrics Dashboard Widget**:
  - [ ] Grid display: Sharpe, Sortino, Max DD, VaR, Beta, Alpha, Treynor, Calmar, Ulcer Index
  - [ ] Color-coded thresholds (green/yellow/red)
**Status:** 📋 Pending

### Phase 9: Visual Theme Overhaul
**Goal:** Switch to a pure black background with off-white text for a cleaner, more professional look.
- [ ] **Tailwind Theme Configuration**:
  - [ ] Background: `#000000` (pure black)
  - [ ] Text: `#E2E8F0` (off-white)
  - [ ] Borders: `#1E293B` (subtle slate)
  - [ ] Cards: `bg-gray-900/80` with `backdrop-blur` for depth
  - [ ] Accent: Keep emerald-500/emerald-400 for positive, red-500/red-400 for negative
- [ ] **Component Updates**:
  - [ ] Nav bar — transparent bg, white text, hover effects
  - [ ] Cards — dark with subtle borders, hover elevation
  - [ ] Tables — zebra striping with semi-transparent rows
  - [ ] Charts — dark background, white grid lines, high-contrast data series
  - [ ] Modals — frosted glass effect over black backdrop
- [ ] **Consistency Pass**:
  - [ ] Ensure all pages (Dashboard, Positions, Analytics, Trade Audit, Settings) use new theme
  - [ ] Dark mode only (no toggle needed — this IS the theme)
**Status:** 📋 Pending

### Phase 10: Robustness, Testing & Polish ✅ **COMPLETED**
**Goal:** Ensure reliability, maintainability, and production-readiness.
- [x] **Git Repository**: Initialized, `.gitignore` added, commits tracking all changes.
- [x] **Alembic Migrations**: Configured for async SQLAlchemy with `aiosqlite`. Initial schema + UUID type fix migrations.
- [x] **Unit & Integration Tests**: 62 passing tests covering:
  - 10 API endpoint tests (portfolios CRUD, positions, transactions, health, refresh prices, integration)
  - 8 portfolio calculation tests (value, returns, price series, empty DataFrame handling)
  - 24 risk metric tests (Sharpe, Sortino, MaxDrawdown, VaR, Beta, Alpha, Treynor, Calmar, Ulcer, FullReport)
  - 20 portfolio integration tests (create, read, update, delete, duplicate, empty, error cases)
- [x] **SQLite UUID Adapter**: Registered for proper UUID storage in `aiosqlite`.
- [x] **Edge Case Handling**: Empty DataFrames, zero-variance benchmarks, no-drawdown portfolios, NaN Sortino.
- [x] **Lazy-Loading Fix**: Eager loading with `selectinload` for asset relationships.
- [x] **Dockerfile**: Multi-stage build with uv, Python 3.11.
- [x] **docker-compose.yaml**: Service definition with volume persistence.
- [x] **.dockerignore**: Proper exclusions.
**Status:** ✅ 100% Complete

---

## 4. Current State & Gap Analysis

### What's Already Done ✅
| Component | Details |
|---|---|
| **App Skeleton** | FastAPI app, lifespan management, config loading. |
| **Database** | Async SQLAlchemy setup, SQLite file, 6 fully defined ORM models with relationships. |
| **API Endpoints** | 8 functional REST endpoints (Portfolios CRUD, Positions, Transactions, Refresh). |
| **Risk Engine** | 9 professional-grade metrics implemented (`risk.py`, 175 lines). |
| **Calc Engine** | NAV, returns, allocation, P&L calculations (`portfolio_calc.py`, 125 lines). |
| **Data Feed** | `yfinance` wrapper with price lookup and historical data fetching (`data_feed.py`, 71 lines). |
| **Web UI** | Dark-themed layout, responsive design, dynamic nav, create portfolio modal, position table with conditional formatting. |
| **Dependencies** | All dev/production deps installed in `.venv`. |

### What is Left to Build ❌
| Priority | Component | Description |
|---|---|---|
| **P1** | **React Frontend SPA (Phase 5)** | Vite + React + TypeScript SPA. Replace Jinja2/HTMX. See Phase 5 breakdown. |
| **P1** | **Sell Operations (Phase 7)** | Sell endpoint, modal, P&L preview, transaction recording. |
| **P1** | **Trade Audit Trail (Phase 7)** | Trade history, filtering, export, realized P&L. |
| **P2** | **Real-Time Market Data (Phase 6)** | WebSocket streaming + React hook + price caching. |
| **P2** | **Professional Charts (Phase 8)** | TradingView Lightweight Charts or Recharts, NAV + benchmark overlay. |
| **P3** | **Visual Theme Overhaul (Phase 9)** | Pure black bg, off-white text, frosted glass cards. |
| **P2** | **Global Exception Handlers** | FastAPI exception handlers for consistent error responses. |
| **P3** | **Production Data Feed** | Replace `yfinance` with a paid API provider (Polygon, Alpha Vantage, IEX Cloud). |
| **P3** | **Benchmark Data Integration** | Wire up actual benchmark data (SPY, QQQ) from data feed service. |
| **P4** | **Portfolio Classification Enhancement** | Integrate with a free ticker API for live sector/industry lookups. |
| **P4** | **Export/Import** | CSV/Excel export for positions, import from broker statements. |
| **P4** | **User Authentication** | Multi-user support with JWT auth. |

---

## 5. Next Steps

1. **Phase 6 (Real-Time Market Data)** — Next milestone. WebSocket service for live price streaming, React hook, price caching layer.
2. **Phase 7 (Sell Operations & Trade Audit)** — Sell endpoint/modal with P&L preview, trade history table with filtering and export.
3. **Phase 8 (Professional Charting)** — Upgrade to TradingView Lightweight Charts or Recharts, benchmark overlay, risk metrics dashboard widget.
4. **Phase 9 (Visual Theme Overhaul)** — Pure black background, off-white text, frosted glass cards, consistent across all pages.
5. **Phase 10 (Production Readiness)** — Global exception handlers, production data feed (paid API), Docker volume mount updates.
6. **Phase 11 (Enhanced Features)** — Benchmark data integration (SPY/QQQ), enhanced portfolio classification via live API.
7. **Phase 12 (Exporter)** — CSV/Excel export for positions, import from broker statements.
8. **Phase 13 (Multi-User)** — JWT authentication, user registration, portfolio sharing.

*Phase 6 (Real-Time Market Data) is the next milestone. Ready to build?*
