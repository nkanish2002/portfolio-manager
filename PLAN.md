# Portfolio Manager — Project Plan

> **Status:** Planning phase — fresh project
> **Created:** July 19, 2026
> **Location:** `~/Work/portfolio-manager`

---

## 1. Vision

A web-based portfolio management application for tracking and analyzing investment portfolios across multiple accounts (e.g., "Wacky" high-beta, "Long-term stable"), with support for the 3-basket strategy (Super Stable / Stable Alpha / High Beta), real-time pricing, risk analytics, benchmark comparison, and interactive visualizations.

Built from lessons learned across 10+ prior sessions of portfolio analysis, statement parsing, HTML report generation, and a previous (abandoned) portfolio-manager implementation.

### Key Capabilities

- **Multi-account, multi-portfolio** support — track holdings across Schwab accounts
- **Custom basket framework** — create any number of baskets (3, 4, or more) with custom names, colors, and target allocations. The 3-basket model (Super Stable / Stable Alpha / High Beta) is a preset, not a hard limit
- **All Schwab asset classes** — equities, ETFs, mutual funds, bonds, options, cash, money market
- **Real-time pricing** via yfinance (extensible to paid APIs later)
- **Risk analytics** — Sharpe, Sortino, Max Drawdown, VaR, Beta, Alpha, Treynor, Calmar, Ulcer Index
- **Benchmark comparison** — portfolio vs SPY, QQQ, or custom indices
- **Interactive charts** — NAV growth, drawdown, allocation pie, monthly returns heatmap, benchmark overlay
- **Trade tracking** — buy/sell with FIFO P&L, trade audit trail, CSV export
- **Statement import** — parse Schwab PDF statements into holdings (via existing `portfolio-statement-analyzer` skill)
- **Report generation** — generate standalone HTML reports (like the 3-basket restructuring report from July 17)

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Backend** | FastAPI (Python 3.12+) | Async, type-safe, auto OpenAPI docs, WebSocket. Python ecosystem is unmatched for financial data (yfinance, polars, PDF parsing). Any non-Python stack would require a Python microservice anyway — splitting the stack = more work, not less. |
| **ORM/DB** | SQLModel + PostgreSQL (local dev → Supabase prod) | SQLModel combines Pydantic + SQLAlchemy in one class — halves model/schema boilerplate. Local Postgres via Docker Compose for dev (fast, no network latency, offline-capable). Supabase managed Postgres for production. Switching is just a `.env` connection string change — zero code changes. |
| **Migrations** | Alembic | Versioned schema management — runs against local Postgres in dev, Supabase in prod |
| **Config** | Dynaconf (YAML + .env) | Multi-env config via `settings.yaml` with `[default]`, `[development]`, `[production]` sections. `.env` / `.env.production` override YAML defaults. Custom prefix `PORTFOLIO_MANAGER_` for env vars. Switch env: `ENV_FOR_DYNACONF=production`. Layered priority: YAML defaults → env-specific YAML → .env file → env vars (highest). |
| **Auth** | fastapi-users (JWT + OAuth2) | Registration, login, JWT tokens, password reset, OAuth2 (Google/GitHub) — all out of the box. Zero auth code to write. Supabase has its own auth, but it's designed for JS clients — fastapi-users integrates cleanly with FastAPI backend. |
| **Frontend** | React 19 + TypeScript + Vite | Modern SPA, fast HMR, type safety. Simpler than Next.js for a dashboard app behind auth — no SSR/SSG/API routes needed. |
| **Routing** | React Router v7 | HashRouter mode (SPA served behind FastAPI catch-all) |
| **State** | Zustand | Lightweight, no boilerplate, works great with async |
| **API Client** | Axios | Interceptors, typed responses, easy error handling |
| **Charts** | TradingView Lightweight Charts + Recharts | Pro financial charts (candlesticks, NAV) + React-native charts (pie, bar) |
| **Styling** | Tailwind CSS v4 | Dark theme, responsive, utility-first |
| **Real-time** | FastAPI WebSockets + TTL price cache | Background polling of yfinance, batch push to clients |
| **Data Source** | yfinance (dev), extensible to FMP/Polygon (prod) | Free, broad Schwab coverage |
| **Calculations** | Polars | Rust-based DataFrame library — 10-100x faster than pandas for financial computations. Lazy evaluation, type safety, zero-copy operations. Native support for time series resampling (daily returns, NAV history). Replaces both pandas AND numpy. |
| **Container** | Docker Compose (Postgres + backend) | Dev: local Postgres container + backend. Prod: backend only (connects to Supabase). Same codebase, just `.env` swap. |
| **Dependency Mgmt** | uv (Python) + npm (JS) | Fast, modern, lockfile-based |
| **Testing** | pytest + pytest-asyncio + httpx (backend), vitest (frontend) | Async API tests + unit tests |
| **Linting** | ruff (Python) + eslint (TS) | Fast, modern linters |
| **Logging** | structlog | Structured JSON logging |

### Why Not a Different Stack?

| Alternative | Why It's More Work |
|---|---|
| **Next.js full-stack (no Python)** | yfinance, PDF parsing, Polars risk calculations are Python-only. Would need a separate Python microservice anyway → two stacks instead of one. |
| **Go + HTMX** | No yfinance, no Polars, no PDF parsing. Would call Python as subprocess. More work, worse DX for financial logic. |
| **Supabase + Next.js** | Supabase handles auth + DB + realtime, but you still need Python for yfinance/PDF/risk calc. Two systems = more complexity, vendor lock-in. |
| **T3 Stack (Next.js + tRPC + Prisma)** | Great for CRUD apps, but no Python ecosystem for financial data. Would split into TS backend + Python microservice. |

### Why FastAPI Still Wins (Optimized)

FastAPI is the right backend — but we optimize the workflow to minimize effort:

1. **SQLModel** (by the FastAPI author) — one Python class is BOTH the Pydantic response schema AND the SQLAlchemy ORM model. No separate `models/` + `schemas/` directories. ~40% less code.
2. **fastapi-users** — registration, login, JWT, password reset, OAuth2 (Google login) all included. Write ~20 lines of config, not 500 lines of auth code.
3. **Dynaconf (YAML + .env)** — `settings.yaml` has `[default]`, `[development]`, `[production]` environment sections with all defaults. `.env` (dev) and `.env.production` (prod) override YAML values with secrets. Env vars prefixed `PORTFOLIO_MANAGER_` override everything. Switch env: `export ENV_FOR_DYNACONF=production`. Priority: YAML `[default]` → YAML `[development]` → `.env` → env vars.
4. **Polars** — Rust-based DataFrame library replacing both pandas AND numpy. 10-100x faster for financial computations (NAV resampling, rolling returns, risk metrics). Lazy evaluation, type safety, zero-copy.
5. **Local Postgres for dev, Supabase for prod** — Docker Compose includes a `postgres:16-alpine` container for local development. For production, set `ENV_FOR_DYNACONF=production` and Dynaconf loads `.env.production` with the Supabase connection string. Zero code changes.
6. **Keep Vite + React** (not Next.js) — for an auth-protected dashboard app, Next.js's SSR/SSG/API routes add ceremony without benefit. Vite + React Router is simpler and faster to build.

---

## 3. Project Structure

```
portfolio-manager/
├── src/portfolio_manager/           # Backend (FastAPI + SQLModel)
│   ├── main.py                      # App factory, lifespan, middleware, route registration
│   ├── config.py                     # Dynaconf instance (settings.yaml + .env layering, PORTFOLIO_MANAGER_ prefix)
│   ├── database.py                   # Async SQLAlchemy engine (asyncpg), session, Base
│   ├── auth.py                       # fastapi-users setup (JWT, OAuth2 Google/GitHub, user model)
│   ├── models/                       # SQLModel definitions (model + schema in one class)
│   │   ├── user.py                   # User (fastapi-users base, extended with display name)
│   │   ├── asset.py                  # Asset (symbol, name, asset_class, exchange, cusip, sector)
│   │   ├── basket.py                 # Basket (user_id FK, name, color, target_allocation, sort_order)
│   │   ├── portfolio.py              # Portfolio (user_id FK, account_id FK, basket_id FK)
│   │   ├── account.py                # Account (user_id FK, name, institution, account_number)
│   │   ├── position.py               # Position (portfolio_id FK, asset_id FK, qty, cost, price)
│   │   ├── transaction.py            # Transaction (portfolio_id FK, type, qty, price, fees, FIFO P&L)
│   │   └── benchmark.py              # Benchmark + BenchmarkData + portfolio associations
│   ├── routes/                       # FastAPI routers (all require auth via fastapi-users dependency)
│   │   ├── auth.py                   # fastapi-users routes (register, login, reset, verify, OAuth)
│   │   ├── baskets.py                # Basket CRUD (create/edit/delete, target allocations)
│   │   ├── portfolios.py             # Portfolio CRUD
│   │   ├── positions.py              # Position management + price refresh + move between baskets
│   │   ├── transactions.py           # Trade entry + audit trail
│   │   ├── analytics.py              # Risk metrics, chart data, benchmark comparison, basket-level
│   │   ├── ws.py                     # WebSocket endpoint for live prices (auth via query token)
│   │   └── dashboard.py              # SPA catch-all route (serves React build, requires auth)
│   ├── services/                     # Business logic (framework-agnostic, async)
│   │   ├── data_feed.py              # yfinance wrapper (get_price, get_historical, search)
│   │   ├── price_cache.py            # In-memory TTL cache for market data
│   │   ├── ws_service.py             # WebSocket manager (subscriptions, batch push)
│   │   ├── portfolio_calc.py         # NAV, returns, allocation, P&L
│   │   ├── risk.py                    # Sharpe, Sortino, Max DD, VaR, Beta, Alpha, Treynor, Calmar, Ulcer
│   │   ├── benchmark.py              # Excess returns, tracking error, information ratio
│   │   ├── classification.py         # Sector/industry/region mapping for tickers
│   │   ├── nav_history.py            # Historical NAV from transactions
│   │   ├── trades.py                 # Buy/sell execution, FIFO P&L, trade audit
│   │   ├── statement_import.py       # Parse Schwab PDF → holdings (via existing skill)
│   │   └── report_generator.py       # Generate standalone HTML reports (3-basket restructuring)
│   └── static/                       # React build output (served by FastAPI in production)
├── frontend/                         # Frontend (React SPA)
│   ├── src/
│   │   ├── services/api.ts           # Axios client + TypeScript interfaces (auto-attaches JWT)
│   │   ├── store/                    # Zustand stores
│   │   │   ├── authStore.ts          # Auth state (user, token, login/logout/register)
│   │   │   ├── portfolioStore.ts     # Portfolio list, current selection
│   │   │   ├── basketStore.ts        # Basket list, CRUD, target vs actual allocations
│   │   │   ├── positionStore.ts     # Positions, live price updates
│   │   │   └── tradeStore.ts         # Trade history, filters
│   │   ├── hooks/                    # Custom React hooks
│   │   │   ├── useWebSocket.ts       # WS connection + reconnect with backoff
│   │   │   ├── useAuth.ts            # Auth guard hook (redirect to login if not authenticated)
│   │   │   └── usePortfolio.ts       # Data fetching helpers
│   │   ├── pages/                    # Route pages
│   │   │   ├── LoginPage.tsx        # Login form (email/password + Google OAuth button)
│   │   │   ├── RegisterPage.tsx     # Registration form
│   │   │   ├── DashboardPage.tsx     # Portfolio overview, KPI cards, basket allocation
│   │   │   ├── PositionsPage.tsx     # Position table with live prices, P&L, sell modal
│   │   │   ├── AnalyticsPage.tsx     # Risk metrics, charts, benchmark comparison
│   │   │   ├── TradesPage.tsx        # Trade audit trail, filters, CSV export
│   │   │   ├── BasketsPage.tsx       # Multi-basket view, allocation targets, rebalancing, CRUD baskets
│   │   │   └── SettingsPage.tsx      # Theme, data source, refresh interval
│   │   ├── components/               # Reusable components
│   │   │   ├── PortfolioCard.tsx
│   │   │   ├── PositionTable.tsx
│   │   │   ├── SellModal.tsx
│   │   │   ├── BuyModal.tsx
│   │   │   ├── BasketAllocation.tsx   # Multi-basket progress bars + CRUD (create/edit/delete baskets)
│   │   │   ├── RiskGauge.tsx
│   │   │   ├── NavChart.tsx           # TradingView Lightweight Charts
│   │   │   ├── AllocationPie.tsx     # Recharts donut
│   │   │   ├── DrawdownChart.tsx
│   │   │   └── Layout.tsx             # Nav bar, portfolio selector, WS status, user menu/logout
│   │   ├── App.tsx                   # Root with HashRouter + auth guard
│   │   └── index.css                 # Tailwind + custom animations
│   ├── vite.config.ts                # Vite + proxy to FastAPI
│   ├── tailwind.config.js            # Dark theme config
│   ├── tsconfig.json
│   └── package.json
├── tests/                            # Backend tests
│   ├── conftest.py                   # Shared fixtures (async Postgres test DB, test client, auth)
│   ├── test_auth.py                  # Registration, login, JWT, protected routes
│   ├── test_baskets.py               # Basket CRUD, target validation, analytics
│   ├── test_portfolios.py            # Portfolio CRUD
│   ├── test_positions.py             # Position management + price refresh
│   ├── test_transactions.py          # Trade execution + FIFO P&L
│   ├── test_risk_metrics.py          # Sharpe, Sortino, VaR, Max DD
│   ├── test_portfolio_calc.py        # NAV, returns, allocation
│   ├── test_benchmark.py             # Excess returns, tracking error
│   ├── test_ws.py                    # WebSocket connect/subscribe/broadcast
│   └── test_statement_import.py     # Schwab PDF parsing
├── settings.yaml                     # Dynaconf config: [default], [development], [production] sections
├── .env                              # Dev overrides (secrets, local Postgres) — gitignored
├── .env.production                   # Prod overrides (secrets, Supabase) — gitignored
├── migrations/                       # Alembic migrations (Postgres-native)
├── pyproject.toml                    # Python deps (uv + hatchling)
├── uv.lock                           # Python lockfile
├── Dockerfile                        # Multi-stage: Node build frontend + Python runtime
├── docker-compose.yaml               # Dev: local Postgres + backend
├── docker-compose.prod.yaml          # Prod: backend only (connects to Supabase)
├── .dockerignore
├── PLAN.md                           # This file
└── README.md
```

---

## 4. Look & Feel

### Visual Theme

Dark, professional, Bloomberg-terminal-inspired. Based on the HTML report design from the July 17 session.

| Element | Color | Usage |
|---|---|---|
| **Background** | `#0d1117` | Page background |
| **Surface** | `#161b22` | Cards, tables, modals |
| **Border** | `#30363d` | Table rows, dividers, card edges |
| **Text** | `#e6edf3` | Primary text |
| **Text Dim** | `#8b949e` | Secondary text, labels |
| **Accent** | `#10b981` (emerald) | Primary actions, positive highlights |
| **Positive P&L** | `#3fb950` (green) | Gains |
| **Negative P&L** | `#f85149` (red) | Losses |
| **Basket colors** | User-defined (hex) | Dynamic — each basket has its own color used across UI. Defaults: `#58a6ff` (blue), `#bc8cff` (purple), `#f0883e` (orange) |
| **Warning** | `#d29922` (gold) | Notes, tax warnings |

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Portfolio Manager        [Wacky ▾] [Stable ▾]    ● Live  ⚙  ☰  │  ← Nav bar
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Total    │  │ Day Change│  │ P&L      │  │ Positions│         │  ← KPI cards
│  │ $673K    │  │ +$1,234  │  │ +$112K   │  │ 47       │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Basket Allocation                                          ││
│  │  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░  40% Super Stable││  ← Dynamic progress bars
│  │  ████████████████░░░░░░░░░░░░░░░░░░░░░░░  39% Stable Alpha ││     (N baskets, user colors)
│  │  ██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  21% High Beta    ││
│  │  [+ New Basket]  [Edit]  [Delete]                           ││  ← Basket CRUD
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Positions                              [Refresh] [Buy]     ││
│  │  ┌────────┬────────┬────────┬────────┬────────┬────────┐    ││
│  │  │ Symbol │ Qty    │ Price  │ Value  │ P&L    │ Action │    ││  ← Position table
│  │  ├────────┼────────┼────────┼────────┼────────┼────────┤    ││     with live prices
│  │  │ AAPL   │ 100    │ $198.5 │ $19,850│ +$1,230│ [Sell] │    ││
│  │  │ INTC   │ 160    │ $95.04 │ $15,207│ +$10.1K│ [Sell] │    ││
│  │  │ ...    │ ...    │ ...    │ ...    │ ...    │ ...    │    ││
│  │  └────────┴────────┴────────┴────────┴────────┴────────┘    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐              │
│  │  NAV Growth Chart    │  │  Allocation Donut    │              │  ← Charts
│  │  ╱╲    ╱╲    ╱       │  │     ◔                │              │
│  │ ╱  ╲  ╱  ╲  ╱        │  │   ◑   ◒              │              │
│  │╱    ╲╱    ╲╱         │  │ ◕                    │              │
│  └──────────────────────┘  └──────────────────────┘              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Risk Metrics (vs SPY, 1Y)                                 ││
│  │  Sharpe: 1.42  Sortino: 2.18  Max DD: -8.3%  VaR: -$4,231  ││  ← Risk gauges
│  │  Beta: 0.95   Alpha: +3.2%  Treynor: 12.4  Calmar: 4.2     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Dark by default** — `#0d1117` background, no light mode initially
2. **Sharp edges** — minimal border-radius (4px max), clean professional look
3. **Color-coded baskets** — each basket has a user-pickable color (hex) that propagates to charts, progress bars, and table accents. The 3-basket preset seeds blue/purple/orange but users can add/recolor freely
4. **Dynamic basket count** — the UI renders N basket cards/progress bars, not a hardcoded 3. Users can create, edit, or delete baskets at any time
4. **Live indicator** — green pulsing dot when WebSocket is connected, gray when offline
5. **Flash on price change** — row briefly flashes green (price up) or red (price down) on WebSocket update
6. **Responsive** — works on desktop (primary), tablet, and mobile
7. **Monospace for numbers** — financial figures use `SF Mono` / `Fira Code` for alignment

---

## 5. Database Schema

### Core Models

> **PostgreSQL — local dev, Supabase prod.** All tables use `UUID` primary keys (Postgres native `uuid` type), `TIMESTAMPTZ` for timestamps, `NUMERIC` for financial values. For local dev, Docker Compose runs a `postgres:16-alpine` container. For production, set `ENV_FOR_DYNACONF=production` and Dynaconf loads the Supabase connection string from `.env.production`. Same `asyncpg` driver, same Alembic migrations — zero code changes between dev and prod.

> **SQLModel** — each class below is a single SQLModel class that serves as both the SQLAlchemy ORM model AND the Pydantic request/response schema. No separate `models/` and `schemas/` directories. For complex responses (e.g., aggregation queries), plain Pydantic models are used.

> **Multi-tenant via `user_id`** — every user-scoped table has a `user_id` FK to the `users` table. All queries filter by `user_id` so users only see their own data. fastapi-users provides the current user via dependency injection.

```sql
-- User (provided by fastapi-users)
users
  id              UUID PK
  email           VARCHAR(255) UNIQUE
  hashed_password VARCHAR(255)
  display_name    VARCHAR(100)     -- extended field
  is_active       BOOLEAN DEFAULT TRUE
  is_superuser    BOOLEAN DEFAULT FALSE
  is_verified     BOOLEAN DEFAULT FALSE
  created_at      TIMESTAMPTZ

-- Asset master (symbol → metadata) — NOT user-scoped (shared lookup table)
assets
  id              UUID PK
  symbol          VARCHAR(10) UNIQUE
  name            VARCHAR(255)
  asset_class     VARCHAR(20)  -- equity, etf, mutual_fund, option, future, bond, adr, cfd, crypto, cash
  exchange        VARCHAR(50)
  cusip           VARCHAR(20)  -- internal, hidden from UI
  sector          VARCHAR(100)
  industry        VARCHAR(100)
  region          VARCHAR(50)
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

-- Account (brokerage account) — user-scoped
accounts
  id              UUID PK
  user_id         UUID FK → users
  name            VARCHAR(100)  -- "Wacky", "Long-term Stable"
  institution     VARCHAR(100)  -- "Schwab"
  account_number  VARCHAR(50)   -- last 4 only
  created_at      TIMESTAMPTZ

-- Basket (user-defined, first-class entity) — user-scoped
-- Users create any number of baskets with custom names, colors, and targets.
-- Example: 3 baskets (Super Stable / Stable Alpha / High Beta) at 40/40/20
-- Example: 4 baskets (Core / Growth / Speculative / Cash) at 30/30/20/20
baskets
  id                  UUID PK
  user_id             UUID FK → users
  name                VARCHAR(100)     -- "Super Stable", "Stable Alpha", "High Beta"
  description         TEXT             -- "Core compounders + broad market index — sleep well at night"
  color               VARCHAR(7)       -- "#58a6ff" (hex, user-pickable)
  target_allocation   NUMERIC(5,2)     -- 40.00 (percent of total portfolio)
  sort_order          INTEGER          -- display ordering (1, 2, 3, ...)
  is_preset           BOOLEAN DEFAULT FALSE  -- true for the default 3-basket preset
  created_at          TIMESTAMPTZ
  updated_at          TIMESTAMPTZ

-- Portfolio (a portfolio belongs to a user, an account, and is assigned to a basket) — user-scoped
portfolios
  id              UUID PK
  user_id         UUID FK → users
  name            VARCHAR(100)
  account_id      UUID FK → accounts
  basket_id       UUID FK → baskets NULL  -- nullable: unassigned positions live outside baskets
  currency        VARCHAR(3) DEFAULT 'USD'
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

-- Position (current holding — a position belongs to a portfolio, which determines its basket) — user-scoped via portfolio
positions
  id              UUID PK
  portfolio_id    UUID FK → portfolios
  asset_id        UUID FK → assets
  quantity        NUMERIC(18,6)
  avg_cost_basis  NUMERIC(18,6)
  current_price   NUMERIC(18,6)
  market_value    NUMERIC(18,6)  -- computed: quantity * current_price
  unrealized_gain NUMERIC(18,6)
  unrealized_gain_pct NUMERIC(10,4)
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ
  UNIQUE(portfolio_id, asset_id)

-- Transaction (buy/sell/dividend/split/etc.) — user-scoped via portfolio
transactions
  id              UUID PK
  portfolio_id    UUID FK → portfolios
  asset_id        UUID FK → assets
  type            VARCHAR(20)  -- buy, sell, dividend, split, interest, fee, deposit, withdrawal
  quantity        NUMERIC(18,6)
  price           NUMERIC(18,6)
  fees            NUMERIC(18,6) DEFAULT 0
  trade_date      TIMESTAMPTZ
  notes           TEXT
  realized_gain   NUMERIC(18,6)  -- computed via FIFO for sells
  created_at      TIMESTAMPTZ

-- Benchmark (comparison index) — NOT user-scoped (shared)
benchmarks
  id              UUID PK
  symbol          VARCHAR(10)  -- "SPY", "QQQ"
  name            VARCHAR(255)
  created_at      TIMESTAMPTZ

-- Benchmark historical data — shared
benchmark_data
  id              UUID PK
  benchmark_id    UUID FK → benchmarks
  date            DATE
  close           NUMERIC(18,6)
  UNIQUE(benchmark_id, date)

-- Portfolio ↔ Benchmark association (many-to-many) — user-scoped via portfolio
portfolio_benchmarks
  portfolio_id    UUID FK → portfolios
  benchmark_id    UUID FK → benchmarks
  PRIMARY KEY(portfolio_id, benchmark_id)
```

### Database Design Notes

- **Postgres-native types** — `UUID` (not `CHAR(36)`), `TIMESTAMPTZ` (not `DATETIME`), `NUMERIC` (not `FLOAT`). These are the correct types for financial data in Postgres and avoid precision issues.
- **No SQLite-specific features** — no `AUTOINCREMENT`, no `INTEGER PRIMARY KEY` rowid tricks, no `PRAGMA` statements. The schema works identically on Postgres 14+.
- **SQLModel** — each model is a single class (e.g., `class Basket(SQLModel, table=True)`). For create/update operations, a separate `BasketCreate` / `BasketUpdate` class is defined (non-table) that inherits from `Basket` with omitted fields. This eliminates the separate `schemas/` directory entirely.
- **Multi-tenant via `user_id`** — every user-scoped table (`accounts`, `baskets`, `portfolios`) has a `user_id` FK. The `assets`, `benchmarks`, and `benchmark_data` tables are shared (not user-scoped) since ticker metadata and benchmark prices are universal.
- **Connection string via Dynaconf** — YAML config with env-specific sections + `.env` overrides:
  - `settings.yaml` — committed to git, contains all defaults:
    ```yaml
    default:
      database_url: "postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio_manager"
      jwt_secret: "change-me-in-production"
      jwt_algorithm: "HS256"
      jwt_lifetime_seconds: 3600
      cors_origins: ["http://localhost:5173"]
      yfinance_enabled: true
      price_cache_ttl_seconds: 30
      ws_poll_interval_seconds: 5
    development:
      database_url: "postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio_manager"
      cors_origins: ["http://localhost:5173", "http://localhost:8000"]
    production:
      database_url: "postgresql+asyncpg://postgres.ref:CHANGE_ME@host:6543/postgres"
      cors_origins: []
    ```
  - `.env` — gitignored, overrides YAML for dev (secrets like real JWT_SECRET, OAuth client IDs):
    ```env
    PORTFOLIO_MANAGER_JWT_SECRET=<random-64-char-string>
    PORTFOLIO_MANAGER_GOOGLE_OAUTH_CLIENT_ID=xxx
    PORTFOLIO_MANAGER_GOOGLE_OAUTH_CLIENT_SECRET=yyy
    ```
  - `.env.production` — gitignored, overrides YAML for prod:
    ```env
    PORTFOLIO_MANAGER_DATABASE_URL=postgresql+asyncpg://postgres.ref:real_password@db.host.supabase.co:6543/postgres
    PORTFOLIO_MANAGER_JWT_SECRET=<different-random-64-char-string>
    ```
  - **Priority (highest wins):** env vars (`PORTFOLIO_MANAGER_*`) → `.env` file → YAML `[production]` → YAML `[default]`
  - **Switch env:** `export ENV_FOR_DYNACONF=production` (or set in docker-compose). Dynaconf loads `settings.yaml` `[production]` section + `.env.production`.
  - **config.py** (~15 lines):
    ```python
    from dynaconf import Dynaconf
    settings = Dynaconf(
        envvar_prefix="PORTFOLIO_MANAGER",
        settings_files=["settings.yaml"],
        environments=True,
        load_dotenv=True,
        env_switcher="ENV_FOR_DYNACONF",
    )
    ```
- **Docker Compose includes Postgres for dev** — a `postgres:16-alpine` container runs alongside the backend with a named volume for data persistence. For production, use `docker-compose.prod.yaml` (backend only, `ENV_FOR_DYNACONF=production` set in container env).
- **Same schema, same migrations** — Alembic migrations run identically against local Postgres and Supabase. No environment-specific migration logic needed.
- **Supabase Dashboard** — for prod, use the Supabase SQL editor to inspect tables, run ad-hoc queries, and monitor performance.

---

## 6. API Endpoints

### REST API

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/jwt/register` | Register new user (fastapi-users) |
| `POST` | `/auth/jwt/login` | Login with email + password → JWT token |
| `POST` | `/auth/jwt/logout` | Logout (invalidate JWT) |
| `GET` | `/users/me` | Get current authenticated user |
| `PATCH` | `/users/me` | Update current user (display name, etc.) |
| `POST` | `/auth/jwt/forgot-password` | Request password reset email |
| `POST` | `/auth/jwt/reset-password` | Reset password with token |
| `GET` | `/auth/google/login` | OAuth2 login via Google |
| `GET` | `/auth/github/login` | OAuth2 login via GitHub |
| `GET` | `/api/v1/baskets/` | List all baskets (with target vs actual allocation) |
| `POST` | `/api/v1/baskets/` | Create a new basket (name, color, target_allocation, description) |
| `PUT` | `/api/v1/baskets/{id}` | Update basket (rename, recolor, change target) |
| `DELETE` | `/api/v1/baskets/{id}` | Delete basket (positions become unassigned) |
| `GET` | `/api/v1/baskets/{id}/analytics` | Basket-level P&L, allocation, risk metrics |
| `GET` | `/api/v1/portfolios/` | List all portfolios (with account + basket assignment) |
| `POST` | `/api/v1/portfolios/` | Create portfolio |
| `GET` | `/api/v1/portfolios/{id}` | Get portfolio detail with positions |
| `PUT` | `/api/v1/portfolios/{id}` | Update portfolio (name, basket, target allocation) |
| `DELETE` | `/api/v1/portfolios/{id}` | Delete portfolio |
| `GET` | `/api/v1/portfolios/{id}/positions` | List positions for a portfolio |
| `POST` | `/api/v1/portfolios/{id}/positions` | Add/update position |
| `POST` | `/api/v1/portfolios/{id}/positions/refresh` | Refresh all position prices via yfinance |
| `POST` | `/api/v1/portfolios/{id}/transactions` | Record a transaction (buy/sell/dividend/etc.) |
| `GET` | `/api/v1/portfolios/{id}/transactions` | Get transaction history (with filters) |
| `GET` | `/api/v1/portfolios/{id}/analytics/risk` | Risk metrics (Sharpe, Sortino, VaR, etc.) |
| `GET` | `/api/v1/portfolios/{id}/analytics/allocations` | Allocation by sector, region, asset class, basket |
| `GET` | `/api/v1/portfolios/{id}/charts/nav` | NAV history chart data |
| `GET` | `/api/v1/portfolios/{id}/charts/drawdown` | Drawdown chart data |
| `GET` | `/api/v1/portfolios/{id}/charts/allocation` | Allocation pie chart data |
| `GET` | `/api/v1/portfolios/{id}/charts/monthly-returns` | Monthly returns heatmap data |
| `GET` | `/api/v1/portfolios/{id}/charts/benchmark-comparison` | Portfolio vs benchmark overlay |
| `GET` | `/api/v1/portfolios/{id}/baskets` | Basket summary for a portfolio (target vs actual) |
| `POST` | `/api/v1/portfolios/{id}/positions/{pid}/move` | Move a position to a different basket (reassign portfolio) |
| `POST` | `/api/v1/portfolios/import/statement` | Import Schwab PDF statement |
| `GET` | `/api/v1/portfolios/{id}/export/csv` | Export positions as CSV |
| `GET` | `/api/v1/portfolios/{id}/export/trades/csv` | Export trade history as CSV |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/docs` | Swagger UI |

### WebSocket

| Path | Description |
|---|---|
| `ws://host/ws/quotes` | Live price streaming — client subscribes with symbols, receives batch price updates |

**WebSocket message protocol:**

```
Client → Server:  { "type": "subscribe", "symbols": ["AAPL", "TSLA", "GOOG"] }
Server → Client:  { "type": "connected", "client_id": "abc123" }
Server → Client:  { "type": "subscribed", "symbols": ["AAPL", "TSLA", "GOOG"] }
Server → Client:  { "type": "batch", "updates": [
  { "symbol": "AAPL", "price": 198.50, "prev": 197.80 },
  { "symbol": "TSLA", "price": 245.30, "prev": 243.10 }
]}
```

---

## 7. Phased Implementation (Segmented for 128k Context)

> **Each segment is designed to fit within a single coding session using Qwen 3.6 27B (128k context window).**
>
> A segment touches 3-8 files, produces a self-contained deliverable, and has independent verification. At the start of each segment, provide the agent with: (1) this PLAN.md path, (2) the segment number, (3) the list of files to read for context, and (4) the expected deliverable.
>
> **Estimated session budget:** ~20-30k tokens of new code + ~10-15k tokens of existing file context + tool outputs. This leaves headroom in 128k for reasoning and iteration.

---

### Phase 1: Project Scaffolding & Backend Foundation

#### Segment 1.1 — Project Init & Dependencies
**Goal:** Initialize the project, install all deps, create Dynaconf config (YAML + .env) + database connection + Docker Compose with local Postgres.
**Files to read at start:** None (fresh project)
**Files created:** `pyproject.toml`, `settings.yaml` (with `default`, `development`, `production` sections), `.env`, `.gitignore`, `docker-compose.yaml`, `src/portfolio_manager/__init__.py`, `src/portfolio_manager/config.py`, `src/portfolio_manager/database.py`
**Deliverable:** `uv sync` succeeds, `docker compose up -d postgres` starts local Postgres, `config.py` creates a Dynaconf instance loading `settings.yaml` + `.env` with `PORTFOLIO_MANAGER_` prefix, `database.py` connects to local Postgres.
**Verify:**
```bash
uv sync
docker compose up -d postgres
sleep 3
uv run python -c "from portfolio_manager.config import settings; print(settings.DATABASE_URL)"
# → postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio_manager
uv run python -c "from portfolio_manager.database import engine; print('engine created')"
# Test env switching:
ENV_FOR_DYNACONF=production uv run python -c "from portfolio_manager.config import settings; print(settings.DATABASE_URL)"
# → postgresql+asyncpg://postgres.ref:CHANGE_ME@host:6543/postgres (from settings.yaml [production])
```

#### Segment 1.2 — SQLModel Models (Part 1: Core)
**Goal:** Create the core models: User, Asset, Account, Basket, Portfolio.
**Files to read at start:** `src/portfolio_manager/config.py`, `src/portfolio_manager/database.py`
**Files created:** `src/portfolio_manager/models/__init__.py`, `models/user.py`, `models/asset.py`, `models/account.py`, `models/basket.py`, `models/portfolio.py`
**Deliverable:** All models importable, SQLModel table definitions with correct relationships and `user_id` scoping.
**Verify:**
```bash
uv run python -c "from portfolio_manager.models import User, Asset, Account, Basket, Portfolio; print('all models import')"
uv run python -c "from portfolio_manager.models import Basket; print(Basket.__tablename__, [c.name for c in Basket.__table__.columns])"
```

#### Segment 1.3 — SQLModel Models (Part 2: Holdings + Benchmarks)
**Goal:** Create Position, Transaction, Benchmark, BenchmarkData models + portfolio_benchmarks association.
**Files to read at start:** `models/__init__.py`, `models/portfolio.py`, `models/asset.py`
**Files created:** `models/position.py`, `models/transaction.py`, `models/benchmark.py`
**Deliverable:** All 9 models defined and importable. Relationships: Portfolio→Positions, Portfolio→Transactions, Portfolio↔Benchmarks.
**Verify:**
```bash
uv run python -c "from portfolio_manager.models import Position, Transaction, Benchmark, BenchmarkData; print('all models OK')"
uv run python -c "from portfolio_manager.models import Portfolio; print([r.key for r in Portfolio.__mapper__.relationships])"
```

#### Segment 1.4 — Auth Setup (fastapi-users)
**Goal:** Set up fastapi-users with JWT strategy, user model integration, OAuth2 backends.
**Files to read at start:** `config.py`, `database.py`, `models/user.py`
**Files created:** `src/portfolio_manager/auth.py`
**Deliverable:** `auth.py` exports `fastapi_users`, `current_active_user`, `jwt_authentication`, `get_jwt_strategy`. Registration, login, logout routes ready to mount.
**Verify:**
```bash
uv run python -c "from portfolio_manager.auth import fastapi_users, current_active_user; print('auth OK')"
```

#### Segment 1.5 — Main App + Health Check + Route Registration
**Goal:** Create the FastAPI app factory with lifespan, CORS, auth routers, health check.
**Files to read at start:** `config.py`, `database.py`, `auth.py`, `models/__init__.py`
**Files created:** `src/portfolio_manager/main.py`
**Deliverable:** App starts, health check works, auth routes are mounted (`/auth/jwt/register`, `/auth/jwt/login`, `/users/me`).
**Verify:**
```bash
uv run uvicorn portfolio_manager.main:app --reload &
sleep 3
curl -s localhost:8000/health  # → {"status": "healthy"}
curl -s localhost:8000/openapi.json | python3 -m json.tool | grep "/auth/jwt/register"
kill %1
```

#### Segment 1.6 — Alembic Migration + Apply to Local Postgres
**Goal:** Initialize Alembic, generate initial migration, apply to local Postgres.
**Files to read at start:** `main.py`, `models/__init__.py`, `database.py`, `config.py`
**Files created:** `alembic.ini`, `migrations/env.py`, `migrations/versions/001_initial_schema.py`
**Deliverable:** `alembic upgrade head` creates all tables in local Postgres. Verify with `psql` or DBeaver.
**Verify:**
```bash
uv run alembic upgrade head
# Verify tables exist:
docker compose exec postgres psql -U portfolio -d portfolio_manager -c "\dt"
# → users, assets, accounts, baskets, portfolios, positions, transactions, benchmarks, benchmark_data, portfolio_benchmarks
```

#### Segment 1.7 — Test Fixtures + Model + Auth Tests
**Goal:** Create conftest.py with authenticated test client, write basic model and auth tests.
**Files to read at start:** `main.py`, `auth.py`, `models/__init__.py`, `database.py`
**Files created:** `tests/__init__.py`, `tests/conftest.py`, `tests/test_auth.py`, `tests/test_models.py`
**Deliverable:** `pytest` passes. Tests cover: user registration, login, JWT token retrieval, protected route access, model field validation.
**Verify:**
```bash
uv run pytest tests/test_auth.py tests/test_models.py -v
# → all tests pass
```

---

### Phase 2: Core Services & API

#### Segment 2.1 — Data Feed + Price Cache Services
**Goal:** yfinance wrapper + in-memory TTL price cache.
**Files to read at start:** `config.py`, `models/asset.py`, `models/position.py`
**Files created:** `src/portfolio_manager/services/__init__.py`, `services/data_feed.py`, `services/price_cache.py`
**Deliverable:** `data_feed.py` provides `get_price(symbol)`, `get_historical(symbol, period)`, `search_ticker(query)`. `price_cache.py` provides TTL cache with `get`/`set`/`invalidate`.
**Verify:**
```bash
uv run pytest tests/test_data_feed.py tests/test_price_cache.py -v
# Tests: get_price returns float for known ticker, cache hit/miss, TTL expiry
```

#### Segment 2.2 — Portfolio Calc + Risk Services
**Goal:** NAV calculation, returns, allocation, P&L + 9 risk metrics.
**Files to read at start:** `models/position.py`, `models/transaction.py`, `models/portfolio.py`
**Files created:** `services/portfolio_calc.py`, `services/risk.py`, `tests/test_portfolio_calc.py`, `tests/test_risk_metrics.py`
**Deliverable:** `portfolio_calc.py` computes NAV, daily returns, allocation %, P&L. `risk.py` computes Sharpe, Sortino, Max DD, VaR, Beta, Alpha, Treynor, Calmar, Ulcer Index.
**Verify:**
```bash
uv run pytest tests/test_portfolio_calc.py tests/test_risk_metrics.py -v
# Tests: NAV from transactions, Sharpe on known returns, VaR parametric vs historical, Max DD calculation
```

#### Segment 2.3 — Trades + Nav History + Benchmark + Classification Services
**Goal:** FIFO P&L trade execution, NAV history from transactions, benchmark comparison, sector classification.
**Files to read at start:** `models/transaction.py`, `models/position.py`, `models/benchmark.py`, `services/portfolio_calc.py`
**Files created:** `services/trades.py`, `services/nav_history.py`, `services/benchmark.py`, `services/classification.py`, `tests/test_trades.py`, `tests/test_benchmark.py`
**Deliverable:** `trades.py` executes buy/sell with FIFO realized P&L. `nav_history.py` builds historical NAV series. `benchmark.py` computes excess returns, tracking error, information ratio. `classification.py` maps tickers to sector/region.
**Verify:**
```bash
uv run pytest tests/test_trades.py tests/test_benchmark.py -v
# Tests: FIFO P&L (buy 10@100, buy 10@110, sell 5@120 → realized = $100), tracking error, info ratio
```

#### Segment 2.4 — Basket + Portfolio Routes
**Goal:** CRUD API for baskets and portfolios with user_id scoping.
**Files to read at start:** `main.py`, `auth.py`, `models/basket.py`, `models/portfolio.py`, `models/account.py`
**Files created:** `src/portfolio_manager/routes/__init__.py`, `routes/baskets.py`, `routes/portfolios.py`, `tests/test_baskets.py`, `tests/test_portfolios.py`
**Deliverable:** `GET/POST/PUT/DELETE /api/v1/baskets/`, `GET/POST/DELETE /api/v1/portfolios/`. All routes require auth, filter by `current_user.id`. Basket CRUD creates/edits/deletes with color picker and target validation.
**Verify:**
```bash
uv run pytest tests/test_baskets.py tests/test_portfolios.py -v
# Tests: create basket, list baskets (only own), update color, delete (positions unassigned), create portfolio with basket_id
```

#### Segment 2.5 — Position + Transaction Routes
**Goal:** Position management + trade execution API with price refresh.
**Files to read at start:** `routes/portfolios.py`, `models/position.py`, `models/transaction.py`, `services/data_feed.py`, `services/trades.py`, `services/portfolio_calc.py`
**Files created:** `routes/positions.py`, `routes/transactions.py`, `tests/test_positions.py`, `tests/test_transactions.py`
**Deliverable:** `GET /portfolios/{id}/positions`, `POST /portfolios/{id}/positions`, `POST /portfolios/{id}/positions/refresh`, `POST /portfolios/{id}/transactions`, `GET /portfolios/{id}/transactions`, `POST /portfolios/{id}/positions/{pid}/move`.
**Verify:**
```bash
uv run pytest tests/test_positions.py tests/test_transactions.py -v
# Tests: add position, refresh prices, record buy, record sell with FIFO P&L, move position between baskets
```

#### Segment 2.6 — Analytics Routes + Chart Data Endpoints
**Goal:** Risk metrics, allocation breakdown, chart data endpoints.
**Files to read at start:** `routes/portfolios.py`, `services/risk.py`, `services/portfolio_calc.py`, `services/nav_history.py`, `services/benchmark.py`, `services/classification.py`
**Files created:** `routes/analytics.py`, `tests/test_analytics.py`
**Deliverable:** `GET /portfolios/{id}/analytics/risk`, `/analytics/allocations`, `/charts/nav`, `/charts/drawdown`, `/charts/allocation`, `/charts/monthly-returns`, `/charts/benchmark-comparison`, `/baskets/{id}/analytics`.
**Verify:**
```bash
uv run pytest tests/test_analytics.py -v
# Tests: risk endpoint returns 9 metrics, allocation endpoint returns sector breakdown, chart endpoints return arrays
```

---

### Phase 3: React Frontend Foundation

#### Segment 3.1 — Vite Scaffold + Tailwind + API Client
**Goal:** Scaffold React app, configure Tailwind dark theme, create Axios client with JWT interceptor.
**Files to read at start:** `PLAN.md` (for color palette), `routes/baskets.py` (for response shapes)
**Files created:** `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`, `frontend/tsconfig.json`, `frontend/src/services/api.ts`, `frontend/src/index.css`
**Deliverable:** `npm run dev` starts Vite on :5173. `api.ts` has Axios instance with JWT auto-attach + 401 redirect. TypeScript interfaces for Basket, Portfolio, Position, Transaction.
**Verify:**
```bash
cd frontend && npm run build  # TypeScript compiles
npm run dev &  # dev server starts
curl localhost:5173  # returns HTML
```

#### Segment 3.2 — Auth Store + Login/Register Pages + Auth Guard
**Goal:** Zustand auth store, login/register pages, useAuth hook, route protection.
**Files to read at start:** `frontend/src/services/api.ts`
**Files created:** `frontend/src/store/authStore.ts`, `frontend/src/hooks/useAuth.ts`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/RegisterPage.tsx`, `frontend/src/App.tsx`
**Deliverable:** App redirects to `/login` when unauthenticated. Register → login → dashboard flow works. JWT stored in localStorage.
**Verify:**
```bash
cd frontend && npm run build  # compiles
# Manual: open localhost:5173 → redirects to /login → register → redirected to dashboard → logout → back to login
```

#### Segment 3.3 — Layout + DashboardPage + SettingsPage
**Goal:** Main layout (nav bar, portfolio selector, user menu), dashboard with KPI cards, settings page.
**Files to read at start:** `frontend/src/App.tsx`, `frontend/src/store/authStore.ts`, `frontend/src/services/api.ts`
**Files created:** `frontend/src/components/Layout.tsx`, `frontend/src/store/portfolioStore.ts`, `frontend/src/store/basketStore.ts`, `frontend/src/pages/DashboardPage.tsx`, `frontend/src/pages/SettingsPage.tsx`, `frontend/src/pages/PositionsPage.tsx` (basic table only)
**Deliverable:** Dashboard shows KPI cards (total value, day change, P&L, positions), basket allocation progress bars, position table with empty state. Portfolio selector dropdown populates from API.
**Verify:**
```bash
cd frontend && npm run build  # compiles
# Manual: login → dashboard renders with empty state → portfolio selector shows "No portfolios" → settings page renders
```

---

### Phase 4: Real-Time Prices (WebSocket)

#### Segment 4.1 — Backend WebSocket Service + Route
**Goal:** WebSocket manager with background polling, batch push, TTL cache integration.
**Files to read at start:** `main.py`, `services/price_cache.py`, `services/data_feed.py`, `auth.py`
**Files created:** `services/ws_service.py`, `routes/ws.py`, `tests/test_ws.py`
**Deliverable:** `ws://host/ws/quotes?token=...` accepts connections, subscribes to symbols, polls yfinance every 2-30s, batch-pushes price changes. WS manager starts/stops in lifespan.
**Verify:**
```bash
uv run pytest tests/test_ws.py -v
# Tests: connect → receive "connected", subscribe → receive "subscribed", price change → receive "batch"
```

#### Segment 4.2 — Frontend WebSocket Hook + Live Price Updates
**Goal:** useWebSocket hook, positionStore live updates, flash animation.
**Files to read at start:** `frontend/src/pages/PositionsPage.tsx`, `frontend/src/store/positionStore.ts`, `frontend/src/services/api.ts`
**Files created:** `frontend/src/hooks/useWebSocket.ts`, `frontend/src/store/positionStore.ts` (update), `frontend/src/pages/PositionsPage.tsx` (update), `frontend/src/index.css` (add flash animations), `frontend/src/components/Layout.tsx` (add WS status indicator)
**Deliverable:** Positions table shows live prices with green/red flash on change. Connection indicator (green dot = live, gray = offline). Reconnect with exponential backoff.
**Verify:**
```bash
cd frontend && npm run build
# Manual: open positions page → green "Live" indicator → prices update with flash → kill backend → indicator turns gray → restart backend → reconnects
```

---

### Phase 5: Trade Operations & Audit Trail

#### Segment 5.1 — Buy/Sell Modals + Trade Execution UI
**Goal:** Buy modal (symbol search, qty, price, fee), sell modal (qty, price, P&L preview).
**Files to read at start:** `frontend/src/pages/PositionsPage.tsx`, `frontend/src/services/api.ts`, `frontend/src/store/positionStore.ts`
**Files created:** `frontend/src/components/BuyModal.tsx`, `frontend/src/components/SellModal.tsx`, `frontend/src/store/tradeStore.ts`
**Deliverable:** Buy modal creates position via API. Sell modal shows FIFO P&L preview before execution. Position table updates after trade.
**Verify:**
```bash
cd frontend && npm run build
# Manual: buy AAPL 100@$150 → appears in table → sell 50@$160 → P&L preview shows +$500 → position qty reduces to 50
```

#### Segment 5.2 — Trade Audit Page + CSV Export
**Goal:** Trade history page with filters, CSV export.
**Files to read at start:** `frontend/src/store/tradeStore.ts`, `frontend/src/services/api.ts`
**Files created:** `frontend/src/pages/TradesPage.tsx`, `frontend/src/App.tsx` (add route)
**Deliverable:** Trades page shows paginated history (date, symbol, type, qty, price, fees, P&L). Filters: date range, type, symbol. CSV export buttons for positions and trades.
**Verify:**
```bash
cd frontend && npm run build
# Manual: execute a few trades → trades page shows them → filter by type=BUY → CSV export downloads
```

---

### Phase 6: Analytics & Charts

#### Segment 6.1 — Analytics Page + Risk Metrics Table
**Goal:** Analytics page with risk metrics, benchmark selector, time range selector.
**Files to read at start:** `frontend/src/services/api.ts`, `frontend/src/store/portfolioStore.ts`
**Files created:** `frontend/src/pages/AnalyticsPage.tsx`, `frontend/src/components/RiskGauge.tsx`, `frontend/src/App.tsx` (add route)
**Deliverable:** Analytics page renders risk metrics table (9 metrics, color-coded). Benchmark dropdown (SPY, QQQ). Time range buttons (1M, 3M, 6M, 1Y, All).
**Verify:**
```bash
cd frontend && npm run build
# Manual: navigate to analytics → risk metrics table renders → switch benchmark → switch time range
```

#### Segment 6.2 — NAV Chart + Allocation Pie + Drawdown Chart
**Goal:** Three interactive charts using TradingView Lightweight Charts + Recharts.
**Files to read at start:** `frontend/src/pages/AnalyticsPage.tsx`, `frontend/src/services/api.ts`
**Files created:** `frontend/src/components/NavChart.tsx`, `frontend/src/components/AllocationPie.tsx`, `frontend/src/components/DrawdownChart.tsx`, `frontend/src/pages/AnalyticsPage.tsx` (update to embed charts)
**Deliverable:** NAV growth chart (line chart, benchmark overlay). Allocation donut (by sector/region/asset class). Drawdown waterfall.
**Verify:**
```bash
cd frontend && npm run build
# Manual: analytics page → NAV chart renders → allocation pie shows sectors → drawdown chart shows underwater periods
```

#### Segment 6.3 — Monthly Returns Heatmap + Benchmark Comparison
**Goal:** Monthly returns heatmap + portfolio vs benchmark overlay chart.
**Files to read at start:** `frontend/src/pages/AnalyticsPage.tsx`, `frontend/src/components/NavChart.tsx`
**Files created:** `frontend/src/components/MonthlyReturnsHeatmap.tsx`, `frontend/src/components/BenchmarkComparison.tsx`, `frontend/src/pages/AnalyticsPage.tsx` (update)
**Deliverable:** Monthly returns heatmap (green/red grid by month/year). Benchmark comparison overlay (portfolio NAV vs SPY/QQQ normalized to 100).
**Verify:**
```bash
cd frontend && npm run build
# Manual: analytics page → heatmap shows monthly returns → benchmark comparison shows portfolio vs SPY
```

---

### Phase 7: Custom Basket Framework

#### Segment 7.1 — Basket Seed Data + Backend CRUD Tests
**Goal:** Seed 3-basket preset on startup, write comprehensive basket CRUD tests.
**Files to read at start:** `routes/baskets.py`, `models/basket.py`, `main.py`
**Files created:** `src/portfolio_manager/services/basket_seed.py`, `tests/test_baskets.py` (update with seed tests)
**Deliverable:** On first run, 3 baskets are seeded (Super Stable 40% blue, Stable Alpha 40% purple, High Beta 20% orange). Tests verify seed + CRUD + target validation.
**Verify:**
```bash
uv run pytest tests/test_baskets.py -v
# Tests: seed creates 3 baskets, create 4th basket, delete basket → positions unassigned, targets don't sum to 100% → warning
```

#### Segment 7.2 — BasketsPage + Basket CRUD UI
**Goal:** Full baskets page with dynamic cards, create/edit/delete modals, allocation bars.
**Files to read at start:** `frontend/src/store/basketStore.ts`, `frontend/src/services/api.ts`, `frontend/src/components/BasketAllocation.tsx`
**Files created:** `frontend/src/pages/BasketsPage.tsx`, `frontend/src/components/BasketAllocation.tsx` (update with CRUD), `frontend/src/App.tsx` (add route)
**Deliverable:** Baskets page renders N cards (not hardcoded 3). Each card: name, color, progress bar (target vs actual), total value, P&L. "+ New Basket" button. Edit/delete with confirmation.
**Verify:**
```bash
cd frontend && npm run build
# Manual: baskets page shows 3 preset baskets → create 4th "Cash Reserve" green 10% → edit color → delete → positions go to Unassigned
```

#### Segment 7.3 — Move Position Between Baskets + Rebalancing
**Goal:** "Move to basket" dropdown in position table, rebalancing suggestions.
**Files to read at start:** `frontend/src/components/PositionTable.tsx`, `frontend/src/store/positionStore.ts`, `frontend/src/services/api.ts`
**Files created:** `frontend/src/components/PositionTable.tsx` (update with move dropdown), `frontend/src/store/positionStore.ts` (add movePosition action)
**Deliverable:** Each position row has a "Move to basket" dropdown. Moving a position calls `POST /portfolios/{id}/positions/{pid}/move` and updates allocation bars.
**Verify:**
```bash
cd frontend && npm run build
# Manual: select position → move from Super Stable to High Beta → allocation bars update → position disappears from one basket, appears in another
```

---

### Phase 8: Statement Import & Report Generation

#### Segment 8.1 — Backend Statement Import Service + Route
**Goal:** Parse Schwab PDF → create/update positions.
**Files to read at start:** `routes/portfolios.py`, `models/position.py`, `models/asset.py`, `services/data_feed.py`
**Files created:** `services/statement_import.py`, `routes/import.py`, `tests/test_statement_import.py`
**Deliverable:** `POST /api/v1/portfolios/import/statement` accepts PDF upload, parses holdings, creates/updates positions and assets. Uses the existing `portfolio-statement-analyzer` skill patterns.
**Verify:**
```bash
uv run pytest tests/test_statement_import.py -v
# Tests: upload sample PDF → positions created with correct quantities and cost basis
```

#### Segment 8.2 — Frontend Import UI + Report Generator
**Goal:** File upload modal for statements, HTML report generation endpoint.
**Files to read at start:** `frontend/src/pages/DashboardPage.tsx`, `frontend/src/services/api.ts`
**Files created:** `frontend/src/components/ImportModal.tsx`, `services/report_generator.py`, `routes/reports.py`, `frontend/src/pages/DashboardPage.tsx` (add import + report buttons)
**Deliverable:** Upload modal lets user select a portfolio and upload a Schwab PDF. "Generate Report" button downloads a standalone HTML file (like the July 17 3-basket report).
**Verify:**
```bash
cd frontend && npm run build
# Manual: upload Schwab PDF → positions appear → click "Generate Report" → HTML downloads → open in browser → renders correctly
```

---

### Phase 9: Docker & Production Readiness

#### Segment 9.1 — Dockerfile + docker-compose (dev + prod)
**Goal:** Multi-stage Docker build (Node frontend + Python backend), docker-compose for dev (local Postgres) and prod (Supabase).
**Files to read at start:** `pyproject.toml`, `frontend/package.json`
**Files created:** `Dockerfile`, `docker-compose.yaml` (dev: postgres + backend), `docker-compose.prod.yaml` (prod: backend only), `.dockerignore`
**Deliverable:** `docker compose up -d` builds and runs local Postgres + backend serving the React SPA. `docker compose -f docker-compose.prod.yaml up -d --build` runs backend only connecting to Supabase.
**Verify:**
```bash
# Dev
docker compose up -d --build
sleep 10
curl -s localhost:8000/health  # → {"status": "healthy"}
curl -s localhost:8000/  # → returns React SPA HTML
docker compose down

# Prod (after setting .env.production with Supabase URL)
docker compose -f docker-compose.prod.yaml up -d --build
sleep 10
curl -s localhost:8000/health  # → {"status": "healthy"}
docker compose -f docker-compose.prod.yaml down
```

#### Segment 9.2 — Exception Handlers + Structured Logging + Graceful Shutdown
**Goal:** Global exception handlers, structlog JSON logging, graceful shutdown.
**Files to read at start:** `main.py`, `services/ws_service.py`, `database.py`
**Files created:** `src/portfolio_manager/exceptions.py`, `main.py` (update with exception handlers + structlog), `tests/test_exceptions.py`
**Deliverable:** All API errors return consistent JSON `{detail, error_code}`. Logs are structured JSON. Graceful shutdown closes DB + stops WS manager.
**Verify:**
```bash
uv run pytest tests/test_exceptions.py -v
# Tests: 404 returns consistent JSON, 422 validation error formatted, 500 returns generic error with log
```

#### Segment 9.3 — README + Final Integration Test
**Goal:** Write README, run full end-to-end test.
**Files to read at start:** `PLAN.md`, all phase summaries
**Files created:** `README.md`
**Deliverable:** README with setup, dev, build, test, and deploy instructions. Full E2E test: register → login → create baskets → create portfolio → add positions → buy → sell → view analytics → generate report → export CSV.
**Verify:**
```bash
docker compose up -d --build
sleep 10
# Full E2E via curl or browser:
# 1. Register + login → JWT
# 2. Create 3 baskets (or use presets)
# 3. Create portfolio "Wacky" in High Beta basket
# 4. Add position AAPL 100@$150
# 5. Refresh prices
# 6. Record buy TSLA 50@$250
# 7. Record sell 30 AAPL @$160 (FIFO P&L)
# 8. View analytics (risk metrics + charts)
# 9. Generate report → download HTML
# 10. Export positions CSV
docker compose down
```

---

### Segment Summary

| # | Segment | Phase | Files | Est. Session |
|---|---|---|---|---|
| 1.1 | Project Init & Dependencies | 1 | 6 | Short |
| 1.2 | SQLModel Models (Core) | 1 | 6 | Short |
| 1.3 | SQLModel Models (Holdings) | 1 | 4 | Short |
| 1.4 | Auth Setup (fastapi-users) | 1 | 1 | Medium |
| 1.5 | Main App + Health + Routes | 1 | 1 | Short |
| 1.6 | Alembic Migration + Apply | 1 | 3 | Short |
| 1.7 | Test Fixtures + Auth Tests | 1 | 4 | Medium |
| 2.1 | Data Feed + Price Cache | 2 | 4 | Medium |
| 2.2 | Portfolio Calc + Risk | 2 | 4 | Medium |
| 2.3 | Trades + Nav + Benchmark + Classification | 2 | 7 | Long |
| 2.4 | Basket + Portfolio Routes | 2 | 5 | Medium |
| 2.5 | Position + Transaction Routes | 2 | 5 | Medium |
| 2.6 | Analytics Routes + Chart Data | 2 | 2 | Medium |
| 3.1 | Vite Scaffold + Tailwind + API Client | 3 | 6 | Medium |
| 3.2 | Auth Store + Login/Register + Guard | 3 | 5 | Medium |
| 3.3 | Layout + Dashboard + Settings | 3 | 6 | Medium |
| 4.1 | Backend WebSocket Service | 4 | 3 | Medium |
| 4.2 | Frontend WebSocket + Live Prices | 4 | 5 | Medium |
| 5.1 | Buy/Sell Modals | 5 | 3 | Medium |
| 5.2 | Trade Audit Page + CSV Export | 5 | 2 | Short |
| 6.1 | Analytics Page + Risk Table | 6 | 3 | Medium |
| 6.2 | NAV + Allocation + Drawdown Charts | 6 | 4 | Medium |
| 6.3 | Monthly Heatmap + Benchmark Chart | 6 | 3 | Medium |
| 7.1 | Basket Seed + CRUD Tests | 7 | 2 | Short |
| 7.2 | BasketsPage + Basket CRUD UI | 7 | 3 | Medium |
| 7.3 | Move Position + Rebalancing | 7 | 2 | Short |
| 8.1 | Backend Statement Import | 8 | 3 | Medium |
| 8.2 | Frontend Import UI + Report Gen | 8 | 4 | Medium |
| 9.1 | Dockerfile + docker-compose | 9 | 3 | Short |
| 9.2 | Exception Handlers + Logging | 9 | 3 | Short |
| 9.3 | README + Final E2E Test | 9 | 1 | Medium |

**30 segments total.** Each fits within a 128k context window. Start each session by telling the agent: *"Read ~/Work/portfolio-manager/PLAN.md, then implement Segment X.Y"*.

---

## 8. Build & Test Tools

### Backend

```bash
# Install dependencies
uv sync

# Run dev server
uv run uvicorn portfolio_manager.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest -q

# Run tests with coverage
uv run pytest --cov=src/portfolio_manager --cov-report=term-missing

# Lint
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Database migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Dev server (with HMR + proxy to backend)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Type check
npx tsc --noEmit

# Lint
npx eslint src/

# Run tests (when added)
npx vitest
```

### Docker

```bash
# Dev: start local Postgres + backend (Dynaconf loads .env automatically)
docker compose up -d

# Dev: start just Postgres (for running backend locally without Docker)
docker compose up -d postgres

# Prod: build and run backend only (Dynaconf loads .env.production via ENV_FOR_DYNACONF)
docker compose -f docker-compose.prod.yaml up -d --build
# (docker-compose.prod.yaml sets ENV_FOR_DYNACONF=production in container env)

# Rebuild from scratch (dev)
docker compose down && docker compose up -d --build

# View logs
docker compose logs -f backend

# Run tests in container
docker compose exec backend uv run pytest -q

# Connect to local Postgres (dev)
docker compose exec postgres psql -U portfolio -d portfolio_manager

# Inspect prod DB via Supabase Dashboard
# → Supabase Dashboard → Table Editor
```

### Test Strategy

| Layer | Tool | What's Tested |
|---|---|---|
| **Unit** | pytest | Service functions (risk calculations, portfolio calc, FIFO P&L) |
| **Integration** | pytest + httpx (AsyncClient) | API endpoints (CRUD, price refresh, transactions) |
| **WebSocket** | pytest + Starlette TestClient | WS connect, subscribe, batch broadcast |
| **Frontend** | vitest (future) | Component rendering, store actions, API mocking |
| **E2E** | Manual browser test | Full user workflows (create portfolio → buy → view analytics → sell → export) |

**Test fixtures:**
- `conftest.py` provides async DB session (in-memory SQLite), test client, and sample data
- Each test starts with a clean database
- Tests use `pytest.mark.asyncio` for async test functions

---

## 9. Expected Outcome

A fully functional, web-based portfolio management application that:

1. **Tracks multiple portfolios** across accounts with a user-defined, multi-basket framework (create any number of baskets with custom names, colors, and target allocations)
2. **Shows real-time prices** via WebSocket with live flash animations
3. **Calculates professional risk metrics** (9 metrics, benchmarked against SPY/QQQ)
4. **Renders interactive charts** (NAV, drawdown, allocation, monthly returns, benchmark comparison)
5. **Records trades** with FIFO P&L tracking and full audit trail
6. **Imports Schwab statements** from PDF and auto-creates positions
7. **Generates standalone HTML reports** (like the July 17 3-basket restructuring report)
8. **Runs in Docker** with a single `docker compose up` command
9. **Has comprehensive tests** covering services, API, and WebSocket
10. **Looks professional** — dark Bloomberg-terminal-inspired theme with basket color coding

---

## 10. Key Lessons Applied from Prior Sessions

| Lesson | How It's Applied |
|---|---|
| TypeScript interfaces must match backend response exactly | All Pydantic schemas → TypeScript interfaces, verified via `npm run build` |
| API routes before SPA catch-all | Route registration order documented in `main.py` |
| HashRouter not BrowserRouter | `HashRouter` used in `App.tsx` to avoid 404s on refresh |
| WebSocket needs `ws: true` in Vite proxy | Documented in `vite.config.ts` |
| Price cache with TTL prevents API hammering | 30s TTL cache in `price_cache.py`, shared between WS and REST |
| CUSIP is internal — hide from UI | `cusip` field in Asset model but never exposed in frontend |
| Auto-price refresh, not manual button | WebSocket background polling + `applyLivePrices` in store |
| Portfolio dropdown must handle all page contexts | `Layout.tsx` uses `location.pathname` to navigate with portfolio ID |
| Trade audit must accept portfolioId from URL params | `TradesPage.tsx` uses `useParams` to extract `portfolioId` |
| Services are framework-agnostic | All business logic in `services/` with no HTTP/UI imports |
| Verify before declaring complete | Each phase has explicit verification steps (curl, browser, tests) |
| Local Postgres dev → Supabase prod via Dynaconf | Same `asyncpg` driver, same Alembic migrations. `settings.yaml` `[development]` → local Postgres. `settings.yaml` `[production]` + `.env.production` → Supabase. Switch: `ENV_FOR_DYNACONF=production`. Zero code changes. |
| Polars replaces pandas + numpy | Rust-based DataFrame — 10-100x faster for NAV resampling, rolling returns, risk metrics. Lazy evaluation, type safety. No pandas/numpy dependency needed. |
| Dynaconf (YAML + .env) for multi-env config | `settings.yaml` with `default`/`development`/`production` sections (committed to git, no secrets). `.env` / `.env.production` override with secrets (gitignored). Env vars `PORTFOLIO_MANAGER_*` override everything. Priority: env vars > .env > YAML [env] > YAML [default]. Switch: `ENV_FOR_DYNACONF=production`. |
| SQLModel eliminates schema boilerplate | One class = ORM model + Pydantic schema. `BasketCreate` / `BasketUpdate` inherit from `Basket` with omitted fields. No separate `schemas/` directory. |
| fastapi-users handles auth entirely | Registration, login, JWT, password reset, OAuth2 (Google) — all provided. Write ~20 lines of config, not 500 lines of auth code. |
| All user-scoped queries filter by `user_id` | fastapi-users provides the current user via dependency injection. Every basket/portfolio/account query includes `.where(Model.user_id == current_user.id)` to enforce multi-tenant isolation. |
| structlog for structured logging | JSON log output for all services and routes |
| yfinance can fail silently | All `get_price` calls wrapped in `try/except` with logging |

---

## 11. Initialization Steps (To Execute)

```bash
# 1. Create project directory (already exists)
mkdir -p ~/Work/portfolio-manager
cd ~/Work/portfolio-manager

# 2. Initialize Python project
uv init --name portfolio-manager --python 3.12

# 3. Add backend dependencies
uv add fastapi uvicorn[standard] sqlmodel asyncpg alembic \
       dynaconf polars yfinance structlog \
       fastapi-users[sqlalchemy] httpx-oauth

# 4. Add dev dependencies
uv add --group dev pytest pytest-asyncio httpx ruff

# 4. Create Supabase project (free tier) — for later production use
#    → Dashboard → Settings → Database → Connection string (pooler, port 6543)
#    → Save for later, not needed for dev

# 5. Create config files (Dynaconf — YAML + .env layering)
#
# settings.yaml — committed to git, env-specific defaults:
#   default:
#     database_url: "postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio_manager"
#     jwt_secret: "change-me-in-production"
#     jwt_algorithm: "HS256"
#     jwt_lifetime_seconds: 3600
#     cors_origins: ["http://localhost:5173"]
#     yfinance_enabled: true
#     price_cache_ttl_seconds: 30
#     ws_poll_interval_seconds: 5
#   development:
#     database_url: "postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio_manager"
#     cors_origins: ["http://localhost:5173", "http://localhost:8000"]
#   production:
#     database_url: "postgresql+asyncpg://postgres.ref:CHANGE_ME@host:6543/postgres"
#     cors_origins: []
#
# .env — gitignored, dev secrets (overrides YAML):
#   PORTFOLIO_MANAGER_JWT_SECRET=<random-64-char-string>
#   PORTFOLIO_MANAGER_GOOGLE_OAUTH_CLIENT_ID=xxx
#   PORTFOLIO_MANAGER_GOOGLE_OAUTH_CLIENT_SECRET=yyy
#
# .env.production — gitignored, prod secrets (overrides YAML when ENV_FOR_DYNACONF=production):
#   PORTFOLIO_MANAGER_DATABASE_URL=postgresql+asyncpg://postgres.ref:real_password@db.host.supabase.co:6543/postgres
#   PORTFOLIO_MANAGER_JWT_SECRET=<different-random-64-char-string>
#
# Priority: env vars (PORTFOLIO_MANAGER_*) > .env file > YAML [env] > YAML [default]
# Switch to prod: export ENV_FOR_DYNACONF=production

# 6. Create docker-compose.yaml (dev: postgres:16-alpine + backend)
#    Create docker-compose.prod.yaml (prod: backend only)

# 7. Create source directory structure
mkdir -p src/portfolio_manager/{models,routes,services}
mkdir -p tests migrations frontend

# 8. Start local Postgres
docker compose up -d postgres

# 9. Initialize Alembic (configure for async + asyncpg)
uv run alembic init migrations

# 10. Scaffold React frontend
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router axios zustand
npm install -D tailwindcss @tailwindcss/vite
cd ..

# 10. Initialize git
git init
echo "node_modules/\n.venv/\n__pycache__/\n*.pyc\n.env\n.env.production\ndist/" > .gitignore

# 10. Create initial files (config.py, database.py, auth.py, models, main.py)

# 11. Run first migration against local Postgres
uv run alembic revision --autogenerate -m "initial schema with auth, baskets, portfolios, positions, transactions"
uv run alembic upgrade head

# 12. Verify
uv run uvicorn portfolio_manager.main:app --reload
# → Open localhost:8000/health → {"status": "healthy"}
# → Open localhost:8000/auth/jwt/register → can register a user
# → Open localhost:8000/auth/jwt/login → can login and get JWT
# → Check local Postgres: docker compose exec postgres psql -U portfolio -d portfolio_manager -c "\dt"
#
# To deploy to prod later:
# 1. Create Supabase project → get connection string from Dashboard
# 2. Add to .env.production: PORTFOLIO_MANAGER_DATABASE_URL=postgresql+asyncpg://postgres.ref:password@host:6543/postgres
# 3. Run: ENV_FOR_DYNACONF=production alembic upgrade head (applies migrations to Supabase)
# 4. Run: docker compose -f docker-compose.prod.yaml up -d --build (sets ENV_FOR_DYNACONF=production in container)
```

---

*This plan is a living document. Update it as phases complete and requirements evolve.*