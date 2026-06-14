1|# Portfolio Manager — Master Plan (Unified)

## Overview

This is the **unified master plan** that combines:

1. **Original PLAN.md** — FastAPI backend + phases 1-10
2. **docs/solara/PLAN.md** — Solara frontend migration plan

This unified plan ensures we build the **correct thing** and avoids building the wrong thing.

---

## 1. Current State (✅ Completed)

| Phase | Component | Status |
|-------|-----------|--------|
| Phase 1 | Foundation & Core Infrastructure | ✅ Complete |
| Phase 2 | Core Business Logic & Data Integration | ✅ Complete |
| Phase 3 | Advanced Analytics & Visualization | ✅ Complete |
| Phase 5 | React Frontend SPA | ✅ Complete (removed) |
| Phase 5.1 | Mobile-First Responsive Design | ✅ Complete (removed) |
| Phase 6 | Real-Time Market Data Streaming | ✅ Complete (removed) |
| Phase 7 | Sell Operations & Trade Audit Trail | ✅ Complete (removed) |
| Phase 7.1 | Sharp Edges UI (No Rounded Corners) | ✅ Complete (removed) |
| Phase 8 | Professional Charting & Benchmark Visualization | ✅ Complete (removed) |
| Phase 10 | Robustness, Testing & Polish | ✅ Complete |

**Backend Status:**
- FastAPI app, lifespan management, config loading ✅
- Async SQLAlchemy setup, SQLite file, 6 ORM models ✅
- 19 REST endpoints across 3 routers (`portfolios`, `charts`, `trades`) ✅
- 9 professional-grade risk metrics (Sharpe, Sortino, Max Drawdown, VaR, Beta, Alpha, Treynor, Calmar, Ulcer Index) ✅
- NAV history, benchmark overlay, allocation, P&L, FIFO trade audit ✅
- yfinance data feed wrapper with price caching ✅
- Benchmark comparison: tracking error, information ratio, correlation ✅
- Structlog structured logging, global exception handlers ✅
- Alembic migrations, 9 test files ✅

**Known Backend Bugs (to fix in Phase 10.5):**
- `total_value` hardcoded to `0.0` in all portfolio endpoints — dashboard will always show $0
- FIFO P&L calculation is wrong across multiple sells — each sell rescans all buys from scratch without tracking consumed lots
- 60-data-point minimum on analytics endpoints (`monthly-returns`, `benchmark-comparison`, `risk-report`) — any portfolio under 3 months of data sees blank pages

**Known DESIGN.md Technical Errors (to fix in Phase 10.5):**
- `asyncio.run()` used inside all Solara `@effect` callbacks — crashes at runtime because Solara runs inside Tornado's event loop (nested `asyncio.run()` raises `RuntimeError`)
- `use_state(list[Portfolio], [])` signature doesn't exist in Solara — correct API is `solara.use_state([])` or `solara.reactive([])`

**Frontend Status — ⚠️ No Working UI:**
- React frontend (`frontend/`) — **already deleted** from the repo
- Jinja2 templates exist in `src/portfolio_manager/templates/` — **dead code, no route serves them**
- Solara frontend — **not yet started**
- Running the app today returns 404 on `/`

---

## 2. Next Major Milestone: Solara Frontend Migration

### Why Solara?

| React Issue | Solara Solution |
|-------------|-----------------|
| Hash router bugs (`#/analytics/:id`) | Direct component composition, no routing |
| JavaScript complexity (TypeScript, React, Vite) | Pure Python throughout |
| Build process (npm, webpack, build steps) | `uv run solara` — no build step |
| Browser compatibility (cross-browser testing) | One codebase, native browser support |
| Performance (React re-renders) | Automatic reactive updates (like spreadsheets) |
| Debugging (browser devtools) | Terminal logs, print statements |

### Architecture

```
portfolio-manager/
├── src/portfolio_manager/           # FastAPI backend (UNCHANGED)
│   ├── main.py
│   └── routes/
├── solara-ui/                        # NEW: Solara frontend
│   ├── __init__.py
│   ├── app.py                        # Main SolaraApp
│   ├── components/
│   │   ├── dashboard.py
│   │   ├── positions.py
│   │   ├── trades.py
│   │   ├── analytics.py
│   │   ├── portfolio_selector.py
│   │   └── nav_header.py
│   ├── services/
│   │   └── api.py                    # Async HTTP client
│   └── models/
│       └── schemas.py                # Pydantic models (shared)
└── pyproject.toml                    # Solara dependencies
```

### Tech Stack

| Component | Technology |
|-----------|------------|
| UI Framework | Solara (Python web framework) |
| Widget Components | ipyvuetify (Vuetify/Vue components) |
| HTTP Client | `httpx` (async) |
| Data Validation | Pydantic (shared with backend) |
| Charts | Plotly or Solara's built-in reactive charts |
| Build | uv + `solara-server` (Starlette-based) |
| Styling | ipyvuetify themes, CSS-in-Python |

---

## 3. Phase 10.5: Pre-Solara Cleanup (2-3 days)

This phase must complete before Phase 11 starts. It resolves all known blockers discovered during codebase audit: dead code, API spec mismatches, missing dependencies, backend bugs, and DESIGN.md technical errors that would cause Phase 11 to fail on day 1.

### 10.5.1: Remove Dead Jinja2 Templates

The React frontend was deleted but a set of Jinja2 HTML templates (`templates/dashboard.html`, `positions.html`, `analytics.html`, `settings.html`, `base.html`, `components/nav.html`) were left behind. No route in any router serves them — they are dead code.

| Task | Description |
|------|-------------|
| 10.5.1.1 | Delete `src/portfolio_manager/templates/` entirely |
| 10.5.1.2 | Remove `template_dir` config entry from `config.py` |
| 10.5.1.3 | Confirm `main.py` returns a clean 404 JSON on `/` (not a Jinja2 error) |

### 10.5.2: Fix API Spec Mismatches in DESIGN.md

`docs/solara/DESIGN.md` documents API URLs that don't match the actual routes. The Solara API client will be written from this doc, so discrepancies must be fixed before Phase 11.1.5.

| DESIGN.md (wrong) | Actual route | Fix |
|--------------------|--------------|-----|
| `GET /api/v1/charts/nav-history?portfolio_id=X` | `GET /api/v1/{portfolio_id}/charts/nav-history` | Update DESIGN.md |
| `GET /api/v1/risk-report?portfolio_id=X` | `GET /api/v1/{portfolio_id}/risk-report` | Update DESIGN.md |
| `GET /api/v1/portfolios/{id}/metrics` | **Does not exist** | Add the endpoint (see 10.5.4) |

| Task | Description |
|------|-------------|
| 10.5.2.1 | Update all API URLs in `DESIGN.md` service layer section to match actual path-param routes |

### 10.5.3: Add Missing Dependencies to pyproject.toml

Solara and httpx (as a main dep, not dev-only) must be listed before Phase 11 begins.

| Task | Description |
|------|-------------|
| 10.5.3.1 | Add `solara[assets]>=1.0` to `[project.dependencies]` in `pyproject.toml` |
| 10.5.3.2 | Move `httpx` from `[dev]` optional to `[project.dependencies]` |
| 10.5.3.3 | Run `uv sync` and confirm both packages install cleanly |

### 10.5.4: Fix Backend Bugs

These bugs will surface immediately once the Solara UI is built. Fix them before Phase 11 to avoid debugging backend issues through a new frontend.

**Bug 1 — `total_value` always returns `0.0`**

`list_portfolios`, `get_portfolio`, and `create_portfolio` all hardcode `"total_value": 0.0`. The `PortfolioResponse` schema has the field but nothing populates it. The Phase 11 dashboard "Total Value" card will permanently show $0 without this fix.

| Task | Description |
|------|-------------|
| 10.5.4.1 | Add `GET /portfolios/{id}/metrics` endpoint returning `total_value`, `unrealized_pnl`, `position_count`, `cost_basis` (aggregated from current positions) |
| 10.5.4.2 | Populate `total_value` in `list_portfolios` by summing `quantity × current_price` across positions (single subquery, not N+1) |

**Bug 2 — FIFO P&L wrong across multiple sells**

`_calc_pnl_from_history` in `routes/trades.py` rescans all buy lots from the beginning for every sell, without tracking which lots prior sells have already consumed. If you buy 10 shares then sell 5 twice, both sells calculate P&L against the same 10-share pool — the second sell overstates cost basis.

| Task | Description |
|------|-------------|
| 10.5.4.3 | Rewrite `_calc_pnl_from_history` to process sells in chronological order, tracking cumulative lot consumption across all sells for a given symbol |
| 10.5.4.4 | Add a test case: buy 10 @ $10, sell 5 @ $15, sell 5 @ $20 — verify each sell's P&L is calculated independently against the correct remaining lots |

**Bug 3 — 60-point minimum blocks analytics for new portfolios**

`monthly-returns`, `benchmark-comparison`, and `risk-report` return empty responses when `len(nav_series) < 60` (~3 months of daily data). New portfolios see blank analytics pages with no explanation.

| Task | Description |
|------|-------------|
| 10.5.4.5 | Lower minimums: `monthly-returns` → 2 data points, `risk-report` → 30 points, `benchmark-comparison` → 30 points |
| 10.5.4.6 | Return explicit `"insufficient_data": true` flag alongside partial results so the UI can show a contextual message instead of a blank page |

### 10.5.5: Fix DESIGN.md Technical Errors

These errors are in `docs/solara/DESIGN.md` and will cause Phase 11 to crash on day 1 if not corrected before writing any Solara code.

**Error 1 — `asyncio.run()` inside Solara effects**

All component examples in DESIGN.md use this pattern:
```python
@effect
def load_portfolios():
    async def _load():
        portfolios.value = await PortfolioAPI().list_portfolios()
    asyncio.run(_load())  # ← RuntimeError: event loop already running
```
Solara runs inside Tornado's event loop. Calling `asyncio.run()` from within it raises `RuntimeError: This event loop is already running`. The correct pattern is `solara.lab.use_task`.

**Error 2 — `use_state` type-as-first-argument signature does not exist**

DESIGN.md uses `use_state(list[Portfolio], [])` and `use_state(Portfolio | None, None)` throughout. Solara's actual API is:
```python
portfolios, set_portfolios = solara.use_state([])   # mutable state
# or
portfolios = solara.reactive([])                     # reactive variable
```

| Task | Description |
|------|-------------|
| 10.5.5.1 | Replace all `asyncio.run(_load())` patterns in DESIGN.md with the correct `solara.lab.use_task` pattern |
| 10.5.5.2 | Replace all `use_state(Type, default)` signatures with `solara.use_state(default)` or `solara.reactive(default)` |
| 10.5.5.3 | Add a canonical "Solara async data-fetch pattern" section to DESIGN.md for reference during Phase 11 |

---

## 4. Phase 11: Solara Frontend Migration (3-4 weeks)

### Phase 11.1: Core Infrastructure (3-5 days)

| Task | Description |
|------|-------------|
| 11.1.1 | Setup Solara project structure (`solara-ui/` directory) |
| 11.1.2 | Set up `pyproject.toml` with Solara dependencies |
| 11.1.3 | Configure `uv` for dependency management |
| 11.1.4 | Install `solara[assets]` for air-gapped environments |
| 11.1.5 | Create `PortfolioAPI` client (`httpx.AsyncClient`) |
| 11.1.6 | Implement async methods for all backend endpoints |
| 11.1.7 | Move Pydantic schemas to shared location |

### Phase 11.2: Core Components (5-7 days)

| Task | Description |
|------|-------------|
| 11.2.1 | **Dashboard Component** — Portfolio overview cards, Total Value, P&L, position count |
| 11.2.2 | **Positions Component** — Position table, Edit/Sell functionality, Refresh prices |
| 11.2.3 | **Trades Component** — Trade history table, filtering, summary statistics |
| 11.2.4 | **Analytics Component** — Reactive charts (Plotly/Solara), risk metrics |
| 11.2.5 | **PortfolioSelector Component** — Dropdown widget for portfolio switching |
| 11.2.6 | **NavHeader Component** — Navigation bar with portfolio context |
| 11.2.7 | **Settings Component** — API URL, theme settings |

### Phase 11.3: State Management & Live Prices (2-3 days)

| Task | Description |
|------|-------------|
| 11.3.1 | Global portfolio state (list of portfolios) |
| 11.3.2 | Current portfolio state (auto-updates UI on switch) |
| 11.3.3 | Auto-refresh on portfolio change |
| 11.3.4 | Clean shutdown handling |
| 11.3.5 | **Live price refresh strategy** — implement polling via `solara.lab.use_task` with configurable interval (default 60s); use a manual "Refresh Prices" button that calls `POST /portfolios/{id}/positions/refresh` as the primary trigger, with background polling as secondary. No WebSocket needed — Solara's reactivity handles UI updates once state changes. |

### Phase 11.4: Deployment (3-5 days)

| Task | Description |
|------|-------------|
| 11.4.1 | Configure `solara-server[starlette,dev]` |
| 11.4.2 | Set up reverse proxy (nginx) if needed |
| 11.4.3 | Test browser compatibility (Chrome, Firefox, Safari) |
| 11.4.4 | Mobile-friendly layouts (320px–768px) |
| 11.4.5 | Touch support and adaptive navigation |

### Phase 11.5: Polish & Testing (3-5 days)

| Task | Description |
|------|-------------|
| 11.5.1 | Custom theme (dark mode, emerald accents) |
| 11.5.2 | Network error handling |
| 11.5.3 | Validation error handling |
| 11.5.4 | Manual testing of all pages |
| 11.5.5 | Performance tuning |

---

## 5. Phase 12: Enhanced Features (Post-Solara Migration)

### Phase 12.1: Benchmark Data Integration

| Task | Description |
|------|-------------|
| 12.1.1 | Wire up SPY/QQQ from yfinance |
| 12.1.2 | Overlay benchmark in NAV chart |
| 12.1.3 | Add benchmark stats (excess return, tracking error, info ratio) |

### Phase 12.2: Export/Import

| Task | Description |
|------|-------------|
| 12.2.1 | CSV export for positions |
| 12.2.2 | CSV export for transactions |
| 12.2.3 | CSV export for benchmarks |
| 12.2.4 | Excel export (optional) |
| 12.2.5 | Import from broker statements (CSV) |

### Phase 12.3: Portfolio Classification Enhancement

| Task | Description |
|------|-------------|
| 12.3.1 | Integrate with free ticker API (Wikipedia sector list) |
| 12.3.2 | Live sector/industry lookups |
| 12.3.3 | Auto-classify new tickers |

---

## 6. Phase 13: Multi-User Support (Post-Solara Migration)

| Task | Description |
|------|-------------|
| 13.1 | JWT authentication |
| 13.2 | User registration |
| 13.3 | Portfolio sharing |
| 13.4 | Role-based access control |

---

## 7. Migration Strategy

### React Frontend Removal

React frontend (`frontend/`) has already been deleted from the repo. There is no rollback to React — Solara is the only path forward.

The remaining cleanup is Phase 10.5 (dead Jinja2 templates, API spec fixes, dependencies).

### Rollback Plan

- No React fallback exists
- If Solara has issues during Phase 11, fix them in place
- Jinja2 templates are **not** a fallback — they are dead code scheduled for deletion in Phase 10.5

---

## 8. Estimated Timeline

| Phase | Duration |
|-------|----------|
| **Phase 10.5** | **2-3 days** |
| Phase 11.1 | 3-5 days |
| Phase 11.2 | 5-7 days |
| Phase 11.3 | 2-3 days |
| Phase 11.4 | 3-5 days |
| Phase 11.5 | 3-5 days |
| **Phase 11 Total** | **16-25 days (3-4 weeks)** |
| Phase 12 | 1-2 weeks |
| Phase 13 | 2-3 weeks |

---

## 9. Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Keep yfinance** | Already working, robust, no API key required |
| **Build Solara frontend** | Eliminates hash router bugs, pure Python, no build step |
| **Remove React frontend** | React has hash router bugs, JavaScript complexity, build steps |
| **No Phase 9/10** | Already completed in Phase 1-10 |

---

## 10. Next Steps

1. ✅ **Compile both PLAN.md files** — This document
2. ✅ **Audit codebase against plan** — Found 3 structural blockers + 3 backend bugs + 2 DESIGN.md errors
3. ✅ **Update plan** — Added Phase 10.5 with 5 sub-phases covering all known issues
4. 🔄 **Open PR** — `feature/compile-plan-merge`
5. 🚀 **Start Phase 10.5** — Dead templates → API spec → deps → backend bugs → DESIGN.md fixes
6. 📝 **Start Phase 11.1** — Setup Solara project structure

---

## 11. Files to Reference

| File | Purpose |
|------|---------|
| `src/portfolio_manager/main.py` | FastAPI backend (UNCHANGED) |
| `src/portfolio_manager/routes/` | API endpoints (UNCHANGED) |
| `docs/solara/DESIGN.md` | Solara frontend design docs |
| `docs/solara/PLAN.md` | Solara migration plan |
| `docs/MASTER_PLAN.md` | This unified master plan |

---

*Last Updated: June 14, 2026*

*Branch: `feature/compile-plan-merge`*

*PR: To be created*
