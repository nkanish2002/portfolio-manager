# Portfolio Manager

A web-based portfolio management application for tracking and analyzing investment portfolios across multiple accounts, with support for custom basket strategies, real-time pricing, risk analytics, and interactive charts.

## Features

- **Multi-account, multi-portfolio** — track holdings across brokerage accounts
- **Custom basket framework** — create any number of baskets with custom names, colors, and target allocations
- **Real-time pricing** via yfinance with WebSocket push updates
- **9 risk metrics** — Sharpe, Sortino, Max Drawdown, VaR, Beta, Alpha, Treynor, Calmar, Ulcer Index
- **Interactive charts** — NAV growth, drawdown, allocation pie, monthly returns heatmap, benchmark comparison
- **Trade tracking** — buy/sell with FIFO P&L, full audit trail, CSV export
- **Statement import** — parse Schwab PDF statements into positions
- **HTML report generation** — standalone downloadable reports
- **Dark theme** — Bloomberg-terminal-inspired design

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (async), Python 3.14+ |
| ORM | SQLModel (model + schema in one class) |
| Database | PostgreSQL 16 (local dev), Supabase (production) |
| Driver | asyncpg |
| Auth | fastapi-users (JWT + OAuth2) |
| Config | Dynaconf (YAML + `.env`, prefix `PORTFOLIO_MANAGER_`) |
| Data | yfinance (dev), Polars for analytics |
| Frontend | React 19 + TypeScript + Vite + Tailwind v4 |
| State | Zustand |
| Charts | TradingView Lightweight Charts + Recharts |
| Real-time | FastAPI WebSockets + TTL price cache |
| Migrations | Alembic |
| Logging | structlog (structured JSON) |
| Container | podman / Docker Compose |

## Quick Start

### Prerequisites

- **Python 3.14+** (managed by [uv](https://github.com/astral-sh/uv))
- **Node.js 22+** (for frontend)
- **podman** or **Docker** (for local PostgreSQL)
- **uv** for Python dependency management: `pip install uv`

### Local Development

```bash
# 1. Clone and enter the project
cd ~/Work/portfolio-manager

# 2. Install Python dependencies
uv sync

# 3. Install frontend dependencies
cd frontend && npm install && cd ..

# 4. Start PostgreSQL (use podman-compose on machines without Docker)
podman-compose up -d postgres

# 5. Run database migrations
uv run alembic upgrade head

# 6. Start the backend
uv run uvicorn portfolio_manager.main:app --reload --host 0.0.0.0 --port 8000

# 7. In another terminal, start the frontend dev server
cd frontend && npm run dev
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Swagger docs: `http://localhost:8000/docs`

### Configuration

The application uses **Dynaconf** with layered configuration:

| File | Purpose | Git-tracked? |
|---|---|---|
| `settings.yaml` | Defaults for `default`, `development`, `production` | Yes |
| `.env` | Dev overrides (secrets) | No |
| `.env.production` | Production overrides (secrets) | No |

Priority (highest wins): `PORTFOLIO_MANAGER_*` env vars → `.env` file → YAML `[env]` → YAML `[default]`

Switch environment: `export ENV_FOR_DYNACONF=production`

Minimal `.env` for local development:
```env
PORTFOLIO_MANAGER_JWT_SECRET=<random-64-char-string>
```

Generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

## Docker Deployment

### Development (PostgreSQL + Backend)

```bash
# Build and start everything
podman-compose up -d --build

# View logs
podman-compose logs -f backend

# Connect to database
podman-compose exec postgres psql -U portfolio -d portfolio_manager

# Tear down
podman-compose down
```

### Production (Backend only, connects to Supabase)

1. Create a Supabase project and get the connection string
2. Create `.env.production`:
```env
PORTFOLIO_MANAGER_DATABASE_URL=postgresql+asyncpg://postgres.ref:password@db.host.supabase.co:6543/postgres
PORTFOLIO_MANAGER_JWT_SECRET=<random-64-char-string>
```

3. Deploy:
```bash
podman-compose -f docker-compose.prod.yaml up -d --build
```

The production Docker image is multi-stage: it builds the React frontend in a Node stage, then copies the static output into a Python runtime stage. The result serves both the API and the SPA from a single container.

## Project Structure

```
portfolio-manager/
├── pyproject.toml                    # Python deps (uv)
├── settings.yaml                     # Dynaconf config (default/dev/prod)
├── .env                              # Dev overrides (gitignored)
├── Dockerfile                        # Multi-stage: Node frontend + Python runtime
├── docker-compose.yaml               # Dev: Postgres 16 + backend
├── docker-compose.prod.yaml          # Prod: backend only (Supabase)
├── alembic.ini                       # Alembic config
├── migrations/                       # Alembic migrations
├── src/portfolio_manager/
│   ├── main.py                       # FastAPI app factory + lifespan
│   ├── config.py                     # Dynaconf instance
│   ├── database.py                   # Async engine + session factory
│   ├── auth.py                       # fastapi-users setup
│   ├── exceptions.py                 # Global exception handlers + structlog
│   ├── models/                       # SQLModel definitions (9 models + 1 association)
│   ├── routes/                       # API v1 routers (all auth-gated)
│   └── services/                     # Business logic (framework-agnostic, async)
├── frontend/                         # React 19 + TS + Vite + Tailwind v4
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── store/                    # Zustand stores
│       ├── hooks/                    # Custom React hooks
│       ├── pages/                    # Route pages
│       ├── components/               # Reusable components
│       └── services/                 # API client (Axios)
├── tests/                            # Backend tests (pytest + httpx)
└── README.md
```

## Testing

```bash
# Run all tests
uv run pytest -q

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/portfolio_manager --cov-report=term-missing

# Run only service unit tests (no DB)
uv run pytest tests/test_risk_metrics.py tests/test_portfolio_calc.py tests/test_trades.py -v

# Run live yfinance tests (opt-in)
uv run pytest -m live -v
```

## Code Quality

```bash
# Python linting (Ruff)
uv run ruff check src/ tests/

# Python formatting (Ruff)
uv run ruff format src/ tests/

# TypeScript check
cd frontend && npx tsc --noEmit

# Frontend lint (Biome)
cd frontend && npm run lint
```

## API Overview

All API routes require authentication via JWT (auto-attached by the frontend Axios interceptor). Open API docs are available at `/docs` (Swagger UI) and `/redoc`.

### Auth
| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/jwt/register` | Register new user |
| `POST` | `/auth/jwt/login` | Login → JWT token |
| `GET` | `/users/me` | Current user profile |
| `PATCH` | `/users/me` | Update profile |

### Baskets
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/baskets/` | List baskets |
| `POST` | `/api/v1/baskets/` | Create basket |
| `PUT` | `/api/v1/baskets/{id}` | Update basket |
| `DELETE` | `/api/v1/baskets/{id}` | Delete basket |
| `GET` | `/api/v1/baskets/{id}/analytics` | Basket analytics |

### Portfolios, Positions & Transactions
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/portfolios/` | List portfolios |
| `POST` | `/api/v1/portfolios/` | Create portfolio |
| `GET` | `/api/v1/portfolios/{id}/positions` | List positions |
| `POST` | `/api/v1/portfolios/{id}/positions` | Add position |
| `POST` | `/api/v1/portfolios/{id}/positions/refresh` | Refresh prices |
| `POST` | `/api/v1/portfolios/{id}/positions/{pid}/move` | Move between baskets |
| `POST` | `/api/v1/portfolios/{id}/transactions` | Record buy/sell |
| `GET` | `/api/v1/portfolios/{id}/transactions` | Transaction history |

### Analytics & Charts
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/portfolios/{id}/analytics/risk` | 9 risk metrics |
| `GET` | `/api/v1/portfolios/{id}/analytics/allocations` | Sector/region breakdown |
| `GET` | `/api/v1/portfolios/{id}/charts/nav` | NAV history |
| `GET` | `/api/v1/portfolios/{id}/charts/drawdown` | Drawdown chart |
| `GET` | `/api/v1/portfolios/{id}/charts/allocation` | Allocation pie |
| `GET` | `/api/v1/portfolios/{id}/charts/monthly-returns` | Monthly heatmap |
| `GET` | `/api/v1/portfolios/{id}/charts/benchmark-comparison` | Portfolio vs benchmark |

### Imports & Reports
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/import/statement` | Upload Schwab PDF statement |
| `GET` | `/api/v1/reports/portfolio/{id}` | Download HTML report |

### WebSocket
| Path | Description |
|---|---|
| `ws://host/ws/quotes?token=...` | Live price streaming (JWT auth via query param) |

## Health Checks

| Endpoint | Description |
|---|---|
| `GET /health` | Liveness probe (no DB hit) |
| `GET /health/db` | Readiness probe (verifies DB connectivity) |

## Database

The application uses PostgreSQL with asyncpg driver. Migrations are managed by Alembic.

```bash
# Apply pending migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Check migration status
uv run alembic current
uv run alembic history
```

The same migrations work against both local PostgreSQL and Supabase — only the connection string changes.

## Architecture

### Multi-tenancy
Every user-scoped table has a `user_id` FK to the `users` table. All queries filter by the authenticated user's ID via fastapi-users dependency injection.

### Pricing Pipeline
1. WebSocket manager polls yfinance every N seconds (configurable via `ws_poll_interval_seconds`)
2. Prices are cached with TTL (`price_cache_ttl_seconds`, default 30s)
3. Connected clients subscribe to symbols and receive batch updates
4. Frontend flash-animates rows on price change (green = up, red = down)

### Risk Calculations
All financial computations use Polars (Rust-based DataFrame library) for 10-100x speed improvement over pandas. The service layer is framework-agnostic — no HTTP or UI dependencies.

## License

Private — all rights reserved.