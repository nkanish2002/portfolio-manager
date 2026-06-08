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

### Phase 5: React Frontend Rebuild & Real-Time Features
**Goal:** Replace the Jinja2/HTMX UI with a modern React SPA, add live market data streaming, sell operations, and trade audit trail.
- [ ] **React SPA Architecture**: Set up Vite + React frontend serving as a reverse proxy / static SPA alongside the FastAPI backend
  - [ ] Use **Vite** + **React** + **TypeScript** for fast development
  - [ ] **TanStack Router** for client-side routing (Dashboard, Positions, Analytics, Settings, Trade Audit)
  - [ ] **Tailwind CSS** for styling (keep existing dark theme colors)
  - [ ] **Zustand** for lightweight state management (portfolio data, positions, auth)
  - [ ] **Axios** for API calls to FastAPI backend
- [ ] **Real-Time Market Data Streaming**: Replace "Refresh Prices" button with live WebSocket connections
  - [ ] **FastAPI WebSockets** endpoint (`/ws/quotes/{symbol}`) for streaming prices
  - [ ] **React WebSocket hook** (`useWebSocket`) for managing connections
  - [ ] **Debounce + batching** to avoid overwhelming the server during price updates
  - [ ] **Reconnection logic** with exponential backoff for dropped connections
- [ ] **Sell Button & Trade Feature**: Full sell/short sell workflow
  - [ ] **Sell modal**: Quantity picker, price input (pre-filled with current), fee input
  - [ ] **Partial sell**: Sell only a portion of existing position
  - [ ] **Full sell**: Liquidate entire position
  - [ ] **Sell confirmation**: Show P&L impact before executing
  - [ ] **Record as transaction**: Automatically creates a Sell transaction in the DB
  - [ ] **Position update**: Reduces quantity (or removes if full sell), updates avg cost basis
- [ ] **Trade Audit Trail**: Complete history of all buy/sell/dividend operations
  - [ ] **Trade history table**: Date, symbol, type, qty, price, fees, total, P&L, notes
  - [ ] **Filter & sort**: By date range, symbol, transaction type
  - [ ] **Export trades**: CSV/Excel download of trade history
  - [ ] **Edit/delete trades**: Admin-only ability to correct mistakes
  - [ ] **P&L calculation**: Realized gains/losses from completed sell transactions
- [ ] **Visual Design Updates**: Black background with off-white text
  - [ ] **Background**: Pure black `#000000` instead of slate-950
  - [ ] **Text**: Off-white `#E2E8F0` instead of slate-200/slate-300
  - [ ] **Borders**: Subtle `#1E293B` instead of slate-700
  - [ ] **Accent**: Keep emerald-500/emerald-400 for positive, red-500/red-400 for negative
  - [ ] **Cards**: Semi-transparent `bg-gray-900/80` with backdrop blur for depth
- [ ] **Graphing & Benchmark Visualization**: Professional-grade charts
  - [ ] **Charting library**: **Lightweight Charts** (TradingView) or **Recharts** for React-native charting
  - [ ] **Portfolio NAV chart**: Line chart with benchmark overlay
  - [ ] **Drawdown chart**: Waterfall-style showing drawdown periods
  - [ ] **Sector allocation**: Donut/pie chart with interactive legend
  - [ ] **Monthly returns**: Heatmap showing performance by month/year
  - [ ] **Benchmark comparison**: S&P 500 / custom index overlay with tracking error stats
  - [ ] **Risk metrics panel**: Sharpe, Sortino, Max DD, VaR, Beta, Alpha displayed in a dashboard widget
**Status:** 🚧 In Progress

### Phase 6: Robustness, Testing & Polish ✅ **COMPLETED**
**Goal:** Ensure reliability, maintainability, and production-readiness.
- [x] **Git Repository**: Initialized, `.gitignore` added, commits tracking all changes.
- [x] **Alembic Migrations**: Configured for async SQLAlchemy with `aiosqlite`. Initial schema + UUID type fix migrations.
- [x] **Unit & Integration Tests**: 41 passing tests covering:
  - 9 API endpoint tests (portfolios CRUD, positions, transactions, health, refresh prices)
  - 8 portfolio calculation tests (value, returns, price series, empty DataFrame handling)
  - 24 risk metric tests (Sharpe, Sortino, MaxDrawdown, VaR, Beta, Alpha, Treynor, Calmar, Ulcer, FullReport)
- [x] **SQLite UUID Adapter**: Registered for proper UUID storage in `aiosqlite`.
- [x] **Edge Case Handling**: Empty DataFrames, zero-variance benchmarks, no-drawdown portfolios, NaN Sortino.
- [x] **Lazy-Loading Fix**: Eager loading with `selectinload` for asset relationships.
- [ ] **Global Exception Handlers**: TODO
- [x] **Dockerfile**: Multi-stage build with uv, Python 3.11, health check.
- [x] **docker-compose.yaml**: Service definition with volume persistence.
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
| **P1** | **React Frontend Rebuild** | Replace Jinja2/HTMX with Vite + React + TypeScript SPA. See Phase 5 breakdown above. |
| **P1** | **Sell Operations** | Sell modal, partial/full sell, P&L preview, transaction recording, position updates. |
| **P1** | **Trade Audit Trail** | Trade history table, filtering, export, P&L calculation from realized gains. |
| **P1** | **WebSocket Market Data** | Real-time price streaming via FastAPI WebSockets + React hook with reconnect logic. |
| **P1** | **Professional Charts** | TradingView Lightweight Charts or Recharts for NAV, drawdown, benchmark overlay. |
| **P2** | **Global Exception Handlers** | Add FastAPI exception handlers for consistent error responses across all endpoints. |
| **P2** | **Production Data Feed** | Replace `yfinance` with a paid API provider (e.g., Polygon, Alpha Vantage, IEX Cloud) for reliability. |
| **P2** | **Benchmark Data Integration** | Wire up actual benchmark data (SPY, QQQ) from data feed service. |
| **P2** | **Portfolio Classification Enhancement** | Integrate with a free ticker API (e.g., financialmodelingprep) for live sector/industry lookups. |
| **P3** | **Export/Import** | CSV/Excel export for positions, import from broker statements. |
| **P3** | **User Authentication** | Multi-user support with JWT auth. |

---

## 5. Next Steps

1. **Phase 5 (React Frontend & Real-Time Features)** — The active development phase. This is a significant rewrite:
   - Scaffold Vite + React + TypeScript project
   - Build WebSocket service for live market data streaming
   - Implement sell operations with P&L preview
   - Create trade audit trail with filtering and export
   - Professional charting with TradingView Lightweight Charts or Recharts
   - Black/off-white visual theme
   
2. **Phase 6 (Production Readiness)**: Global exception handlers, production data feed (paid API), and Docker volume mount updates.
3. **Phase 7 (Enhanced Features)**: Benchmark data integration with actual SPY/QQQ data, enhanced portfolio classification via live API.
4. **Phase 8 (Exporter)**: CSV/Excel export for positions, import from broker statements.
5. **Phase 9 (Multi-User)**: JWT authentication, user registration, portfolio sharing.

*Phase 5 (React Frontend) is the next milestone. Ready to scaffold?*
