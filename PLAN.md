# Portfolio Manager — Master Plan

> **Status:** Foundation, Core Logic, and Robustness Complete. Analytics & Visualization Pending.
> **Last Updated:** June 08, 2026
> **Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy (Async), SQLite, HTMX, Tailwind CSS, Plotly, yfinance.
> **Tests:** 41/41 passing (pytest).

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

### Phase 3: Advanced Analytics & Visualization
**Goal:** Add benchmark comparison, interactive charts, and portfolio classification.
- [ ] **Benchmark Comparison Service**: Calculate excess returns, tracking error, and benchmark overlay.
- [ ] **Plotly Chart Integration**: Render NAV growth, asset allocation pie charts, and drawdown waterfalls in the UI.
- [ ] **Portfolio Classification**: Categorize holdings by sector/industry based on ticker lookup.
- [ ] **Portfolio Detail Page**: Enhance `dashboard.html` to show charts alongside the table.
**Status:** ⬜ 0% Complete

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
- [ ] **Dockerfile**: Containerize the application for deployment.
**Status:** ✅ 90% Complete

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
| **P1** | **Charts** | Plotly is installed but not wired up. Need backend functions to generate chart data and frontend components to render them. |
| **P1** | **Benchmark Engine** | `Benchmark` model exists but no service logic to compare portfolio returns vs benchmark returns. |
| **P1** | **Classification** | No logic to categorize assets into sectors/industries yet. |
| **P2** | **Global Exception Handlers** | Add FastAPI exception handlers for consistent error responses. |
| **P2** | **Docker** | No `Dockerfile` for easy deployment. |

---

## 5. Next Steps

1. **Phase 3 (Analytics)**: Implement benchmark comparison service and Plotly chart integration.
2. **Portfolio Classification**: Add sector/industry categorization.
3. **Global Exception Handlers**: Add FastAPI exception handlers for consistent error responses.
4. **Dockerization**: Create `Dockerfile` and `docker-compose.yml` for deployment.

*Ready to proceed with Phase 3 (Analytics & Visualization)?*
