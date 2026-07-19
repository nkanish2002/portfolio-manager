# AGENTS.md — Coding Agent Reference

> **Project:** Portfolio Manager
> **Status:** Phase 1 — Backend Foundation
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
| **2.1** | 🔄 Next | Data feed + price cache services |
| 2.2-2.6 | ⏳ Pending | Services & API routes |
| 3.1-3.3 | ⏳ Pending | React frontend foundation |
| 4.1-4.2 | ⏳ Pending | WebSocket real-time prices |
| 5.1-5.2 | ⏳ Pending | Trade operations UI |

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
    └── test_models.py                # Model registry, types, relationships, DB round-trip
```
