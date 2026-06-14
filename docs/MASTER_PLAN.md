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
| Phase 5 | React Frontend SPA | ✅ Complete (deprecated) |
| Phase 5.1 | Mobile-First Responsive Design | ✅ Complete (deprecated) |
| Phase 6 | Real-Time Market Data Streaming | ✅ Complete (deprecated) |
| Phase 7 | Sell Operations & Trade Audit Trail | ✅ Complete (deprecated) |
| Phase 7.1 | Sharp Edges UI (No Rounded Corners) | ✅ Complete (deprecated) |
| Phase 8 | Professional Charting & Benchmark Visualization | ✅ Complete (deprecated) |
| Phase 10 | Robustness, Testing & Polish | ✅ Complete |

**Backend Status:**
- FastAPI app, lifespan management, config loading ✅
- Async SQLAlchemy setup, SQLite file, 6 ORM models ✅
- 8+ functional REST endpoints ✅
- 9 professional-grade risk metrics ✅
- NAV, returns, allocation, P&L calculations ✅
- yfinance data feed wrapper ✅

**Frontend Status:**
- React SPA (Vite + TypeScript + Tailwind) — ✅ Complete (deprecated, to be removed)
- Sharp square corners, pure black theme — ✅ Complete (deprecated, to be removed)
- Real-time WebSocket price streaming — ✅ Complete (deprecated, to be removed)
- Sell operations with FIFO P&L — ✅ Complete (deprecated, to be removed)
- Professional charts (TradingView Lightweight Charts) — ✅ Complete (deprecated, to be removed)

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

## 3. Phase 11: Solara Frontend Migration (3-4 weeks)

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

### Phase 11.3: State Management (2-3 days)

| Task | Description |
|------|-------------|
| 11.3.1 | Global portfolio state (list of portfolios) |
| 11.3.2 | Current portfolio state (auto-updates UI on switch) |
| 11.3.3 | Auto-refresh on portfolio change |
| 11.3.4 | Clean shutdown handling |

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

## 4. Phase 12: Enhanced Features (Post-Solara Migration)

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

## 5. Phase 13: Multi-User Support (Post-Solara Migration)

| Task | Description |
|------|-------------|
| 13.1 | JWT authentication |
| 13.2 | User registration |
| 13.3 | Portfolio sharing |
| 13.4 | Role-based access control |

---

## 6. Migration Strategy

### React Frontend Removal

1. **Phase 11**: Build Solara frontend as the **primary** frontend
   - Solara serves on `/*` (root routes)
   - React frontend routes are **not implemented** in Phase 11
2. **Phase 11.5**: Test Solara frontend thoroughly
   - Manual testing of all pages
   - Edge cases, performance tuning
3. **Post-Phase 11**: Remove React frontend completely
   - Remove React routes from FastAPI
   - Delete `frontend/` directory (~385MB)
   - Commit to Solara-only

### Rollback Plan

- Solara is the **only** frontend in Phase 11
- No React fallback — if Solara has issues, fix them in Phase 11
- React frontend is **deprecated** and will be removed

---

## 7. Estimated Timeline

| Phase | Duration |
|-------|----------|
| Phase 11.1 | 3-5 days |
| Phase 11.2 | 5-7 days |
| Phase 11.3 | 2-3 days |
| Phase 11.4 | 3-5 days |
| Phase 11.5 | 3-5 days |
| **Phase 11 Total** | **16-25 days (3-4 weeks)** |
| Phase 12 | 1-2 weeks |
| Phase 13 | 2-3 weeks |

---

## 8. Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Keep yfinance** | Already working, robust, no API key required |
| **Build Solara frontend** | Eliminates hash router bugs, pure Python, no build step |
| **Remove React frontend** | React has hash router bugs, JavaScript complexity, build steps |
| **No Phase 9/10** | Already completed in Phase 1-10 |

---

## 9. Next Steps

1. ✅ **Compile both PLAN.md files** — This document
2. 🔄 **Open PR** — `feature/compile-plan-merge`
3. 📝 **Create Phase 11 tasks** — Break down Phase 11.1-11.5 into tasks
4. 🚀 **Start Phase 11.1** — Setup Solara project structure

---

## 10. Files to Reference

| File | Purpose |
|------|---------|
| `src/portfolio_manager/main.py` | FastAPI backend (UNCHANGED) |
| `src/portfolio_manager/routes/` | API endpoints (UNCHANGED) |
| `docs/solara/DESIGN.md` | Solara frontend design docs |
| `docs/solara/PLAN.md` | Solara migration plan |
| `docs/MASTER_PLAN.md` | This unified master plan |

---

*Last Updated: June 13, 2026*

*Branch: `feature/compile-plan-merge`*

*PR: To be created*
