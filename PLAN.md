# Portfolio Manager — Master Plan

> **Status:** Foundation, Core Logic, Analytics & Visualization Complete. 🎉
> **Last Updated:** June 08, 2026
> **Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy (Async), SQLite, HTMX, Tailwind CSS, Plotly, yfinance.
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
│   ├── routes/              # [API] HTTP handlers (CRUD, Dashboard, Transactions)
│   ├── services/            # [LOGIC] Business rules (Risk engine, Calculations, Data feeds)
│   └── templates/           # [UI] Jinja2 + Tailwind + HTMX + Plotly
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

### Phase 4: Robustness, Testing & Polish ✅ **COMPLETED**
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
| **P1** | **Global Exception Handlers** | Add FastAPI exception handlers for consistent error responses across all endpoints. |
| **P1** | **Production Data Feed** | Replace `yfinance` with a paid API provider (e.g., Polygon, Alpha Vantage, IEX Cloud) for reliability. |
| **P2** | **Benchmark Data Integration** | Wire up actual benchmark data (SPY, QQQ) from data feed service. |
| **P2** | **Portfolio Classification Enhancement** | Integrate with a free ticker API (e.g., financialmodelingprep) for live sector/industry lookups. |
| **P2** | **Docker Volume Mounts** | Update docker-compose.yaml to mount the SQLite database and templates directories. |
| **P3** | **Export/Import** | CSV/Excel export for positions, import from broker statements. |
| **P3** | **User Authentication** | Multi-user support with JWT auth. |

---

## 5. Next Steps

1. **Phase 5 (Production Readiness)**: Global exception handlers, production data feed (paid API), and Docker volume mount updates.
2. **Phase 6 (Enhanced Features)**: Benchmark data integration with actual SPY/QQQ data, enhanced portfolio classification via live API.
3. **Phase 7 (Exporter)**: CSV/Excel export for positions, import from broker statements.
4. **Phase 8 (Multi-User)**: JWT authentication, user registration, portfolio sharing.

*Ready to proceed with Phase 5 (Production Readiness)?*
