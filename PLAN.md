# Portfolio Manager — Textual TUI Migration Plan

> **Status:** Backend services complete. Phase 1 (Textual foundation) merged. 🔄
> **Last Updated:** June 18, 2026
> **Stack:** Python 3.11+, SQLAlchemy 2.x (async), SQLite + aiosqlite, yfinance, Textual ≥0.86, textual-plotext ≥1.0.1.
> **Tests:** 43/43 passing.

---

## 1. Vision

A keyboard-driven, dark-themed Textual TUI for portfolio management. Multi-asset support, live yfinance prices, professional risk metrics, and in-terminal charts via `textual-plotext`. No browser, no web stack — runs from any terminal.

**Out of scope:** order routing, auth, web/mobile, tax lots beyond FIFO.

---

## 2. Architecture

```text
src/portfolio_manager/
├── config.py            # Pydantic settings
├── database.py          # Async SQLAlchemy engine + session
├── models/              # 6 ORM models (asset, benchmark, portfolio, position, transaction)
├── services/            # Framework-agnostic async business logic
│   ├── portfolios.py    # CRUD, position management
│   ├── trades.py        # Buy/sell, FIFO P&L
│   ├── charts.py        # Allocation, drawdown, monthly returns
│   ├── chart_data.py    # Chart data generation
│   ├── risk.py          # 9 risk metrics
│   ├── portfolio_calc.py# NAV, returns, allocation
│   ├── data_feed.py     # yfinance wrapper
│   ├── price_cache.py   # In-memory TTL cache
│   ├── nav_history.py   # Historical NAV
│   ├── benchmark.py     # Benchmark comparison
│   └── classification.py# Sector/industry/region
└── ui/                  # Textual TUI
    ├── app.py           # App entry point
    ├── styles.tcss      # Dark theme
    ├── screens/         # base, dashboard, analytics, trades, settings
    └── widgets/         # (empty — to be built)
```

**Principle:** Services are framework-agnostic. The TUI calls them and binds the results to widgets.

---

## 3. Design

- **Keyboard-first**, dark theme (`#000` bg, `#E2E8F0` text, `#10B981` accent).
- **Sharp edges, no rounded corners.**
- Min terminal 80×24, optimal 120×40+.
- Background price refresh; flash rows on change.
- Charts rendered via `textual-plotext` — line, bar, candlestick, pie, heatmap, histogram.

**Charts by screen:**

| Chart | Screen | Source |
|---|---|---|
| NAV History (line) | Analytics | `nav_history.py` + `benchmark.py` |
| Drawdown (area) | Analytics | `chart_data.py` |
| Allocation (bar) | Dashboard | `chart_data.py` |
| Monthly Returns (heatmap) | Analytics | `charts.py` |
| Returns Distribution (histogram) | Analytics | `portfolio_calc.py` |
| Benchmark Comparison (line) | Analytics | `benchmark.py` |
| Risk Gauges (ASCII bars) | Analytics | `risk.py` |

---

## 4. Phases

### Phase 1: Foundation — ✅ Done (commit `bee8a73`)
App shell, screen routing (Dashboard / Analytics / Trades / Settings), base screen class, dark `styles.tcss`, CLI entry point `portfolio-manager`. Screens currently render placeholder content.

### Phase 2: Dashboard & Portfolios — ⬜

**Prerequisites** (must land first):
- Wire `app.py::_initialize_database` to `database.async_session` and pass the session factory to screens (currently a TODO stub).
- Replace hardcoded fixture rows in `dashboard.py:41–55` with real service calls.
- Drop orphaned deps `plotly>=5.24` and `python-multipart>=0.0.18` from `pyproject.toml`.

**Tasks:**
- Wire `DashboardScreen` to `portfolios` + `portfolio_calc` services.
- `PositionTable` widget — sortable, gain/loss coloring, live flash.
- Create / delete portfolio modals.
- Portfolio switching via `1`–`9`.
- `[R]` refresh wired to yfinance.

**Done when:** creating a portfolio persists to SQLite, dashboard shows real positions and NAV, `[R]` triggers a real yfinance fetch and updates the table.

### Phase 3: Trades — ⬜
- Buy / Sell modals with validation + P&L preview.
- `TradesScreen` paginated history with `ALL` / `BUY` / `SELL` / `DIV` / `FEE` filters.
- CSV export.

**Done when:** buy/sell modals round-trip through `TradeService`, trade history paginates and filters, CSV export round-trips through pandas without precision loss.

### Phase 4: Analytics & Charts — ⬜
- Risk metric gauges with green/amber/red thresholds.
- Six `textual-plotext` charts (table above).
- Benchmark selector (SPY / QQQ / custom) and range selector (1M / 3M / 6M / 1Y / All).

**Done when:** all six charts render with real data for a portfolio with ≥3 months of history; switching benchmark or range updates every chart and gauge in sync.

### Phase 5: Real-Time Prices — ⬜
- Background refresh task on a configurable interval.
- Row-flash on price change.
- Connection status indicator.
- Manual refresh bypasses cache.

**Done when:** background refresh runs on the configured interval; offline flips the status indicator red, reconnect restores it without restart; `[R]` forces an immediate refresh bypassing cache.

### Phase 6: Settings — ⬜
- `.env`-backed persistence via `pydantic-settings`.
- Theme toggle, yfinance toggle, refresh interval, default portfolio.

**Done when:** changing the refresh interval persists across restarts; theme toggle repaints without restart; invalid values surface inline and don't persist.

### Phase 7: Polish — ⬜
- Centralized error handling via `self.notify(..., severity="error")`.
- Startup + graceful shutdown (DB init, task cleanup).
- Help screen auto-generated from `BINDINGS`.
- Update `Dockerfile` + `docker-compose.yaml` for TUI (drop Solara entry point / port mapping).
- Add `Pilot` and snapshot tests for screens.

**Done when:** `docker compose run --rm portfolio-manager` launches the TUI interactively; Pilot test suite is green; 30-minute run with refresh enabled shows no task leaks.

---

## 5. Recommended Order

1. Phase 2 — ship a working dashboard against real data.
2. Phase 3 — buy/sell + trade history.
3. Phase 4 — analytics + charts.
4. Phase 5 — real-time refresh.
5. Phase 6 — settings persistence.
6. Phase 7 — polish, Docker, release.

---

## 6. Known Issues

**Docker config still targets Solara** — `Dockerfile` entry point and `docker-compose.yaml` port mapping are stale. Tracked under Phase 7.

(Phase 2 prerequisites — `_initialize_database` stub, hardcoded dashboard fixtures, orphaned deps — moved into Phase 2 itself.)

---

## 7. Running

```bash
uv sync                                              # install
uv run portfolio-manager                             # run TUI
uv run pytest -q                                     # tests
uv run ruff check src/ tests/                        # lint
uv run alembic upgrade head                          # migrations

# Textual devtools (live reload + console)
uv run textual run --dev portfolio_manager.ui.app:run
uv run textual console                               # in a second terminal
```

**Test fixtures:** new service tests reuse `tests/conftest.py::isolated_db` — an autouse fixture that builds a fresh in-memory SQLite per test, creates all tables, and swaps `async_session` in every service module. No `portfolio.db` writes from the test suite.

---

## Appendix: Keybindings

| Key | Action |
|---|---|
| `1`–`9` | Switch portfolio |
| `R` | Refresh prices |
| `A` | Analytics screen |
| `T` | Trades screen |
| `C` | Create portfolio |
| `B` | Buy |
| `S` | **Context-sensitive:** Sell modal when a `DataTable` row is focused on the Dashboard; otherwise Settings screen |
| `E` | Export CSV (Trades) |
| `?` / `H` | Help |
| `Q` | Quit |
| `ESC` | Back / close dialog |

**`S` implementation hint:** define the Sell binding on `DashboardScreen` with higher priority than the app-level Settings binding, and gate its action handler on `isinstance(self.focused, DataTable)`. Falls through to Settings when no row is focused.

## Appendix: Colors

| Element | Color |
|---|---|
| Background | `#000000` |
| Text | `#E2E8F0` |
| Accent | `#10B981` (emerald) |
| Positive | `#22C55E` |
| Negative | `#EF4444` |
| Warning | `#F59E0B` |
| Border | `#334155` |
| Highlight | `#1E293B` |

> Legacy FastAPI/React/Solara plan archived at `docs/PLAN_LEGACY.md`.
