# AGENTS.md — Coding Agent Reference

> **Project:** Portfolio Manager
> **Status:** Phase 7 — Custom Basket Framework (7.1, 7.2, 7.3 complete)
> **Location:** `~/Work/portfolio-manager`
> **Full spec:** `PLAN.md`

---

## Quick Start

```bash
# Install deps
uv sync

# Start Postgres (podman — no Docker on this machine)
podman-compose up -d postgres

# Verify
uv run python -c "from portfolio_manager.config import settings; print(settings.DATABASE_URL)"
```

## Container Tool

- **podman + podman-compose** — Docker is NOT available. Always use `podman-compose` for containers.
- Use fully-qualified image names (e.g., `docker.io/library/postgres:16-alpine`) to avoid short-name resolution prompts.

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI (async), Python 3.14+ |
| ORM | SQLModel (model + schema in one class) |
| DB | PostgreSQL 16 (local), Supabase (prod) |
| Driver | asyncpg |
| Config | Dynaconf (`settings.yaml` + `.env`, prefix `PORTFOLIO_MANAGER_`) |
| Auth | fastapi-users (JWT + OAuth2) |
| Data | yfinance (dev), Polars for analytics |
| Migrations | Alembic |
| Frontend | React 19 + TS + Vite + Tailwind v4 |

## Conventions

### SQLModel
- One class = both ORM model AND Pydantic schema (`table=True`)
- Separate `XCreate` / `XUpdate` classes for CRUD operations (no `table`)
- `UUID` PKs, `TIMESTAMPTZ` timestamps, `NUMERIC` for financial values
- Every user-scoped table has `user_id: UUID` FK to `users`
- `created_at` + `updated_at` on all mutable tables

### Auth
- All API routes require auth via fastapi-users dependency injection
- `current_active_user` for active users, `current_user` for any logged-in user
- Multi-tenant: all queries filter by `current_user.id`

### Config
- `settings.yaml`: committed, has `[default]`, `[development]`, `[production]` sections
- `.env`: gitignored, dev overrides
- Switch env: `ENV_FOR_DYNACONF=production`
- Access via `from portfolio_manager.config import settings`

### Database
- `database.py` exports: `engine`, `async_session_factory`, `get_session()`
- All DB operations are async (asyncpg)

### Code Style
- Ruff: line-length 120, py314 target
- Type hints everywhere
- `structlog` for structured logging

## Segment Progress

| Segment | Status | Description |
|---|---|---|
| **1.1** | ✅ Done | Project init, deps, config, Docker Compose |
| **1.2** | ✅ Done | SQLModel models: User, Asset, Account, Basket, Portfolio |
| **1.3** | ✅ Done | SQLModel models: Position, Transaction, Benchmark |
| **1.4** | ✅ Done | Auth setup (fastapi-users, JWT, user manager) |
| **1.5** | ✅ Done | Main app + health check + route registration |
| **1.6** | ✅ Done | Alembic migration + apply to local Postgres |
| **1.7** | ✅ Done | Test fixtures + model/auth tests (26 tests passing) |
| **2.1** | ✅ Done | Data feed + price cache services (yfinance, TTL cache) |
| **2.2** | ✅ Done | Portfolio calc + risk services (NAV, 9 risk metrics) |
| **2.3** | ✅ Done | Trades (FIFO) + nav history + benchmark + classification services |
| **2.4** | ✅ Done | Basket + portfolio + account CRUD routes (user-scoped) |
| **2.5** | ✅ Done | Position + transaction routes (refresh, move, FIFO P&L) |
| **2.6** | ✅ Done | Analytics routes (risk, allocations, charts, basket analytics) |
| **3.1** | ✅ Done | Vite scaffold + Tailwind v4 + Axios API client + TS interfaces |
| **3.2** | ✅ Done | Auth store (Zustand), login/register pages, route guards |
| **3.3** | ✅ Done | Layout + Dashboard + KPI cards, Settings, Positions |
| **4.1** | ✅ Done | WebSocket backend: ws_service, ws route, auth via JWT query param |
| 4.2 | ✅ Done | Frontend WebSocket hook + live price updates |
| 5.1 | ✅ Done | Buy/Sell modals: ticker search, trade execution, FIFO P&L preview |
| 5.2 | ✅ Done | Trade audit page: filters, pagination, CSV export |
| 6.1 | ✅ Done | Analytics page + risk metrics table |
| 6.2 | ✅ Done | NAV + Allocation + Drawdown Charts |
| 6.3 | ✅ Done | Monthly Returns Heatmap + Benchmark Comparison |
| 7.1 | ✅ Done | Basket seed (3-basket preset on register) + target-allocation summary/warning + CRUD tests |
| 7.2 | ✅ Done | BasketsPage: dynamic cards, create/edit/delete modals, allocation bars, analytics, sector breakdown |
| 7.3 | ✅ Done | Move position between baskets (dropdown per row) + rebalancing suggestions panel |

## File Map (Created So Far)

```
portfolio-manager/
├── pyproject.toml                    # Python deps (uv)
├── settings.yaml                     # Dynaconf: default/dev/prod
├── .env                              # Dev overrides (gitignored)
├── .gitignore                        # toptal Python + Node patterns
├── alembic.ini                       # Alembic config (URL set from settings in env.py)
├── docker-compose.yaml               # Postgres 16 (podman)
├── PLAN.md                           # Full project spec
├── AGENTS.md                         # This file
├── migrations/
│   ├── env.py                        # Async Alembic env (uses shared Base.metadata)
│   ├── script.py.mako                # Migration template
│   └── versions/
│       └── 998c35d6e512_initial_schema.py  # Initial migration (all 10 tables)
├── src/portfolio_manager/
│   ├── __init__.py
│   ├── config.py                     # Dynaconf instance
│   ├── database.py                   # async engine + session factory + shared Base + association tables
│   ├── auth.py                       # fastapi-users setup (JWT, user manager)
│   ├── main.py                       # FastAPI app factory + lifespan + CORS + auth/health routers
│   ├── services/                     # Service layer (business logic)
│   │   ├── __init__.py               # Service exports
│   │   ├── data_feed.py              # Async yfinance wrapper + DTOs + cache integration
│   │   ├── price_cache.py            # In-memory TTL cache (monotonic clock, thread-safe)
│   │   ├── portfolio_calc.py         # NAV, P&L, allocation, returns
│   │   ├── risk.py                    # Sharpe, Sortino, Max DD, VaR, Beta, Alpha, Treynor, Calmar, Ulcer
│   │   ├── trades.py                 # FIFO trade ledger + realized P&L
│   │   ├── nav_history.py            # NAV series from transactions
│   │   ├── benchmark.py             # Excess returns, tracking error, information ratio
│   │   ├── classification.py         # Sector/region classification
│   │   ├── basket_seed.py            # 3-basket preset seed + target-allocation summary/warning
│   │   └── ws_service.py            # WebSocket manager: clients, subscriptions, poll loop
│   ├── routes/                       # API v1 routers (all auth-gated, user-scoped)
│   │   ├── __init__.py               # api_router aggregator + ws export
│   │   ├── accounts.py               # Account CRUD
│   │   ├── baskets.py                # Basket CRUD + basket analytics
│   │   ├── portfolios.py             # Portfolio CRUD (ownership-validated)
│   │   ├── positions.py              # Positions: add/refresh/move
│   │   ├── transactions.py           # Record buy/sell w/ FIFO realized P&L + history
│   │   ├── analytics.py             # Risk, allocations, charts, benchmark comparison
│   │   └── ws.py                     # WebSocket endpoint: /ws/quotes (JWT auth via query param)
│   └── models/                       # All 9 models + 1 association table
│       ├── __init__.py               # Single entry point for model imports
│       ├── user.py                   # User (fastapi-users base)
│       ├── asset.py                  # Asset (shared lookup)
│       ├── account.py                # Account (user-scoped)
│       ├── basket.py                 # Basket (user-scoped)
│       ├── portfolio.py              # Portfolio (user-scoped)
│       ├── position.py               # Position (user-scoped via portfolio)
│       ├── transaction.py            # Transaction (user-scoped via portfolio)
│       └── benchmark.py              # Benchmark + BenchmarkData (shared)
└── tests/
    ├── conftest.py                   # Async Postgres test DB, client + auth fixtures
    ├── test_auth.py                  # Registration, login, JWT, protected routes
    ├── test_models.py                # Model registry, types, relationships, DB round-trip
    ├── test_data_feed.py             # DataFeed: get_price/get_historical/search (fake + live)
    ├── test_price_cache.py           # PriceCache: get/set/invalidate, TTL expiry, batch
    ├── test_risk_metrics.py          # 9 risk metrics (Sharpe, Sortino, VaR, Max DD, ...)
    ├── test_portfolio_calc.py        # NAV, P&L, allocation, returns
    ├── test_trades.py                # FIFO ledger: realized P&L, lots, splits
    ├── test_benchmark.py             # Tracking error, information ratio, classification
    ├── test_baskets.py               # Basket CRUD routes (user-scoping, color/target)
    ├── test_portfolios.py            # Account + Portfolio CRUD routes
    ├── test_positions.py             # Position add/refresh/move routes
    ├── test_transactions.py          # Transaction record + FIFO realized P&L + history
    ├── test_analytics.py             # Risk, allocations, charts, basket analytics routes
    └── test_ws.py                    # WebSocket: manager, auth, subscriptions, broadcast
└── frontend/                          # React 19 + TS + Vite + Tailwind v4
    ├── package.json                   # React 19, TS, Vite 6, Tailwind v4, Zustand 5, React Router 7
    ├── vite.config.ts                 # Vite + @tailwindcss/vite plugin + API proxy to :8000
    ├── tsconfig.json                  # Strict TS + @ path alias
    ├── index.html                     # Vite entry point
    └── src/
        ├── main.tsx                   # React root + HashRouter
        ├── App.tsx                    # Routes with auth guard (login/register/protected)
        ├── vite-env.d.ts              # Vite client types
        ├── index.css                  # Tailwind v4 @import + @theme tokens + flash animations
        ├── store/
        │   ├── authStore.ts           # Zustand: login, register, logout, init (hydrate)
        │   ├── portfolioStore.ts      # Portfolio list, current selection
        │   ├── basketStore.ts         # Basket list + CRUD
        │   └── tradeStore.ts          # Buy/Sell modal state + trade execution
        ├── hooks/
        │   └── useAuth.ts             # useAuth, useRequireAuth, useRequireGuest
        ├── pages/
        │   ├── LoginPage.tsx          # Email/password form with error/loading states
        │   ├── RegisterPage.tsx       # Registration form with confirm password
        │   ├── DashboardPage.tsx      # KPI cards, basket allocation, position table
        │   ├── PositionsPage.tsx      # Full position table with buy/sell actions
        │   ├── TradesPage.tsx         # Trade history: filters, pagination, CSV export
        │   ├── BasketsPage.tsx        # Basket management: cards, create/edit/delete modals, analytics, sector breakdown
        │   └── SettingsPage.tsx       # Profile editor + basket CRUD
        ├── components/
        │   ├── Layout.tsx              # Nav bar, portfolio selector, user menu
        │   ├── BuyModal.tsx           # Buy modal: symbol search, qty, price, fees
        │   ├── SellModal.tsx          # Sell modal: qty, price, FIFO P&L preview
        │   └── BasketAllocation.tsx   # Reusable allocation row: color, target/actual bar, NAV, P&L, sector breakdown
        └── services/
            └── api.ts                 # Axios instance (JWT interceptor, 401 redirect) + TS interfaces
```
