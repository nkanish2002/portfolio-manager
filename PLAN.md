# Portfolio Manager — Master Plan

||> **Status:** Backend services complete. Solara UI removed. Textual TUI migration planned. 🔄
||> **Last Updated:** June 17, 2026
||> **Tech Stack:** Python 3.11+, SQLAlchemy (Async), SQLite, yfinance, Plotly.
||> **UI:** Textual TUI (planned) — Solara UI removed June 17, 2026.
|> **Tests:** 73/73 passing (pytest).
|> **Docker:** Dockerfile + docker-compose.yaml ready for deployment.
|> **UI:** Sharp square corners (no rounded edges), pure black bg (#000), off-white text, emerald accents.

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

### Phase 5.1: Mobile-First Responsive Design
**Goal:** Ensure the entire React SPA works seamlessly on mobile devices (320px–768px).
- [x] **Navigation Bar Mobile Optimization**:
  - [x] Hamburger menu on mobile (≤768px) with smooth open/close
  - [x] Touch-friendly close button (≥44px)
  - [x] Full-width nav items in dropdown (≥44px tap targets)
  - [x] Touch target sizes ≥44px (iOS/Android guidelines)
- [x] **Grid Layout Adjustments**:
  - [x] Dashboard cards: single column on mobile, 2-column on tablet (sm:), 3-column on desktop (lg:)
  - [x] Analytics page: stacked chart cards vertically on mobile
  - [x] Settings page: stacked form rows, full-width inputs on mobile
- [x] **Table Responsiveness**:
  - [x] Horizontal scroll for positions table on mobile with sticky first column (Symbol)
  - [x] Card view fallback for positions on mobile (<768px) — each position as a styled card
  - [x] Hide non-essential columns on mobile (show: Symbol, Qty, Value, P&L)
- [x] **Chart Responsiveness**:
  - [x] Reduced container heights on mobile (h-48 vs h-64)
  - [x] Scrollable containers for overflow content
  - [x] Responsive text sizing in chart areas (text-sm vs text-base)
- [x] **Form & Modal Mobile UX**:
  - [x] "+ New Portfolio" modal: centered overlay with close button, scrollable content
  - [x] Larger tap targets for all buttons (py-3 vs py-2)
  - [x] Numeric inputs ready for inputmode (future enhancement)
- [x] **Safe Area & Viewport**:
  - [x] `env(safe-area-inset-*)` padding for notched phones (iPhone X+)
  - [x] `viewport-fit=cover` meta tag
  - [x] `overscroll-behavior-y: contain` to prevent bounce
  - [x] `touch-action: manipulation` to prevent double-tap zoom
  - [x] `text-size-adjust: 100%` to prevent orientation text scaling
- [x] **Mobile Testing**:
  - [x] Responsive breakpoints tested (320px, 375px, 414px, 768px)
  - [x] All pages functional on mobile viewport
**Status:** ✅ 100% Complete

### Phase 6: Real-Time Market Data Streaming ✅ **COMPLETED**
**Goal:** Replace the "Refresh Prices" button with live WebSocket market data.
- [x] **FastAPI WebSocket Service**: `/ws/quotes` endpoint
  - [x] Accept multiple symbol subscriptions per connection
  - [x] Debounce + batch updates (1s window) to avoid overwhelming the server
  - [x] Background polling loop (every 2s via yfinance)
- [x] **React WebSocket Hook**: `useWebSocket`
  - [x] Auto-connect on component mount
  - [x] Exponential backoff reconnection (1s base, 30s max)
  - [x] Message parsing and dispatch to stores
- [x] **Live Price Updates in UI**:
  - [x] Green/red flash highlight on price change
  - [x] Live status indicator (connected/disconnected) in PositionsPage
  - [x] Fallback to manual refresh if WebSocket unavailable
- [x] **Price Caching Layer**:
  - [x] Server-side in-memory TTL cache (30s default) to avoid repeated yfinance calls
  - [x] Cache invalidation on new position creation
**Status:** ✅ 100% Complete

### Phase 7: Sell Operations & Trade Audit Trail ✅ **COMPLETED**
**Goal:** Complete buy/sell workflow with full trade history and P&L tracking.
- [x] **Backend — Sell Endpoint**:
  - [x] `POST /api/v1/portfolios/{id}/positions/sell` — partial or full sell
  - [x] Validate quantity ≤ current position quantity
  - [x] Calculate realized P&L (FIFO — matches earliest buys first)
  - [x] Create Sell transaction record
  - [x] Update position: reduce quantity, remove if fully liquidated
  - [x] Return updated position with P&L delta
- [x] **Frontend — Sell Modal** (`SellModal.tsx`):
  - [x] Quantity slider + input (max = current quantity, step=1)
  - [x] Price input (pre-filled with live price from store)
  - [x] Fee input (default $0)
  - [x] **P&L Preview**: Live calculated realized gain/loss before confirming
  - [x] Confirmation step with summary (symbol, qty, price, fees, net proceeds, P&L)
  - [x] Visual P&L coloring (green for gain, red for loss)
- [x] **Trade Audit Trail**:
  - [x] `GET /api/v1/portfolios/{id}/trades` — paginated trade history
  - [x] Frontend `TradeAuditPage` with filterable table (date, symbol, type, qty, price, fees, P&L, notes)
  - [x] Sort by date/symbol/type (asc/desc)
  - [x] Filter by date range, transaction type (Buy/Sell/Dividend)
  - [x] CSV export button
  - [x] Realized P&L summary widget (total gains, total losses, net P&L)
  - [x] FIFO P&L calculation from transaction history (works even after position fully liquidated)
- [x] **Bonus: BUY transaction recording** — `add_position` now creates BUY transactions automatically for trade audit integrity
- [x] **PositionTable integration** — "Sell" button on each row, opens SellModal
- [x] **Nav link** — "Trade Audit" added to PageLayout navigation
**Status:** ✅ 100% Complete

### Phase 7.1: Sharp Edges UI (No Rounded Corners) ✅ **COMPLETED**
**Goal:** Replace all rounded corners across the UI with sharp square edges for a clean, professional look.
- [x] **Global CSS Replacement**: Replaced all `rounded-*` Tailwind classes with `rounded-none` across:
  - [x] Navigation bar links (`.rounded-none` on nav items)
  - [x] Portfolio cards (`rounded-none` on card containers)
  - [x] Modals (`rounded-none` on modal containers and buttons)
  - [x] Position tables (`rounded-none` on table headers, cells, buttons)
  - [x] Forms and inputs (`rounded-none` on input fields)
  - [x] Loaders/spinners (`rounded-none` on spinner elements)
- [x] **SPA Serving Fix**: Dashboard routes now properly serve the React SPA instead of deprecated Jinja2 templates
  - [x] `/dashboard` → React SPA (was serving Jinja2 with Tailwind CDN)
  - [x] `/dashboard/{id}` → React SPA (was serving Jinja2 with Plotly/HTMX CDN)
  - [x] Removed unused Jinja2 template rendering from dashboard routes
  - [x] React SPA now handles all client-side routing
- [x] **Theme Consistency**: Pure black background (`#000`), off-white text (`#E2E8F0`), emerald accents, sharp edges throughout
**Status:** ✅ 100% Complete

### Phase 8: Professional Charting & Benchmark Visualization ✅ **COMPLETED**
**Goal:** Upgrade from basic Plotly charts to professional-grade financial visualizations using TradingView Lightweight Charts.
- [x] **Charting Library**: Installed TradingView Lightweight Charts v4 (industry standard for financial charting)
- [x] **Backend NAV Enhancement**: New `nav_history.py` service that builds proper historical NAV from transaction records
  - Processes BUY/SELL/DIVIDEND/FEE/DEPOSIT/WITHDRAWAL transactions chronologically
  - Computes cumulative portfolio value after each event
  - Supports SPY/QQQ benchmark overlay from yfinance
- [x] **New Chart API Endpoints**:
  - `GET /{id}/charts/nav-history` — NAV + benchmark overlay data for TradingView
  - `GET /{id}/charts/nav` — Enhanced NAV with benchmark support
  - `GET /{id}/charts/drawdown` — Drawdown time series from transaction history
  - `GET /{id}/charts/allocation` — Asset allocation with color-coded asset classes
  - `GET /{id}/charts/monthly-returns` — Monthly returns heatmap data
  - `GET /{id}/charts/returns-distribution` — Returns histogram
  - `GET /{id}/charts/benchmark-comparison` — Stats + aligned price series for overlay
  - `GET /{id}/risk-report` — 9 professional risk metrics
- [x] **Frontend — NAV + Benchmark Overlay Chart** (`NavBenchmarkChart`):
  - Line chart with portfolio (emerald) and benchmark (amber, dashed) series
  - Interactive crosshair, zoom, pan
  - Time range selector: 1M, 3M, 6M, 1Y, ALL
  - Summary stats (start, end, change %)
- [x] **Frontend — Drawdown Chart** (`DrawdownChart`):
  - Area chart showing portfolio drawdown over time
  - Color-coded by severity (light red → deep red)
  - Max drawdown display
- [x] **Frontend — Monthly Returns Heatmap** (`MonthlyReturnsChart`):
  - Grid showing performance by month/year
  - Green for positive, red for negative returns
  - Color intensity scales with magnitude
  - Hover tooltips with exact percentages
- [x] **Frontend — Benchmark Comparison Panel** (`BenchmarkComparison`):
  - Overlay chart with portfolio vs benchmark
  - Stats: Excess Return, Tracking Error, Information Ratio, Correlation
  - Color-coded correlation (green >0.7, amber >0.4, red <0.4)
- [x] **Frontend — Risk Metrics Widget** (`RiskMetricsWidget`):
  - 9 metrics in color-coded grid: Sharpe, Sortino, Max DD, VaR, Beta, Alpha, Treynor, Calmar, Ulcer Index
  - Threshold-based coloring (green/yellow/red)
  - Descriptive subtext for each metric
- [x] **AnalyticsPage**: Completely rebuilt with all professional charts, organized in responsive grid layout
- [x] **API Service**: Updated with new chart types and endpoints in `api.ts`
**Status:** ✅ 100% Complete

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
| **Database** | Async SQLAlchemy setup, SQLite file, 6 fully defined ORM models with relationships. |
| **Services** | PortfolioService, TradeService, ChartService — direct async SQLAlchemy (no framework). |
| **Risk Engine** | 9 professional-grade metrics implemented (`risk.py`). |
| **Calc Engine** | NAV, returns, allocation, P&L calculations (`portfolio_calc.py`). |
| **Data Feed** | `yfinance` wrapper with price lookup and historical data fetching (`data_feed.py`). |
| **Price Cache** | Server-side in-memory TTL cache for market data. |
| **Chart Data** | Allocation pie, NAV history, drawdown, monthly returns, returns distribution, benchmark comparison. |
| **Portfolio Classification** | Sector/industry/region mapping for 150+ tickers. |
| **Sell Operations** | Partial/full sell with FIFO P&L in TradeService. |
| **Tests** | 5 passing test files (chart_service, portfolio_calc, portfolio_service, risk_metrics, trades_service). |

### What Was Removed 🔧 (June 17, 2026)
| Component | Reason |
|---|---|
| **Solara UI** (`solara_app.py`, `ui/`) | Solara routing broken, no working UI. |
| **FastAPI routes** (`routes/`) | Orphaned — not used by Solara. |
| **FastAPI exception handlers** (`exceptions.py`) | FastAPI-specific, not needed for Textual. |
| **Solara test files** (8 files) | Tested deleted routes/UI components. |
| **test_server.py** | Ran Solara server, no longer applicable. |
| **docs/solara/DESIGN.md** | Solara-specific design doc. |
| **`solara[assets]` dep** | No longer in pyproject.toml. |
| **`httpx` dep** | Not needed for Textual UI. |

### What is Left to Build ❌
| Priority | Component | Description |
|---|---|---|
| **P0** | **Textual TUI UI** | Build terminal-based UI replacing Solara — dashboard, positions, charts, trades. |
|**P2** | **Production Data Feed** | ✅ Keep `yfinance` — already working, robust, no API key required. |
|**P2** | **Benchmark Data Integration** | Wire up actual benchmark data (SPY, QQQ) from yfinance. |
|**P3** | **Export/Import** | CSV export for positions, transactions. |
|**P3** | **Portfolio Classification Enhancement** | Integrate with a free ticker API for live sector/industry lookups. |

---

## 5. Next Steps

1. ✅ **Phase 0 (Cleanup)** — June 17, 2026: Removed Solara UI, FastAPI routes, orphaned code. Clean backend services remain.
2. **Phase 1 (Textual UI)** — Build terminal UI with Textual: portfolio dashboard, positions table, charts, trade history.
3. **Phase 2 (Enhanced Features)** — Benchmark data, CSV export, portfolio classification.
