# Portfolio Manager — Textual TUI Migration Plan

||> **Status:** Backend services complete. Textual TUI migration in progress. 🔄
||> **Last Updated:** June 18, 2026
||> **Tech Stack:** Python 3.11+, SQLAlchemy (Async), SQLite, yfinance, Plotly, Textual.
||> **UI:** Textual TUI (in progress) — replacing Solara/FastAPI/React layers removed June 17, 2026.
|> **Tests:** 39/43 passing (4 db-dependent tests failing in isolation).
|> **Docker:** Dockerfile + docker-compose.yaml updated for Textual TUI.

---

## 1. Vision & Scope

Build a professional, terminal-based portfolio management tool with a Textual TUI that mirrors the capabilities of Schwab's brokerage interface — accessible from any terminal, fast, keyboard-driven, and visually rich.

**Key Capabilities:**
- Multi-asset-class support (Equities, Options, Futures, Bonds, ETFs, MFs, ADRs, CFDs, Crypto, Cash).
- Real-time price fetching via `yfinance` (extensible to paid APIs).
- Advanced risk analytics (Sharpe, Sortino, VaR, Beta, Alpha, etc.).
- Benchmark comparison (Portfolio vs. S&P 500, Custom indices).
- Interactive visualizations (Plotly charts rendered externally + Textual-native charts for terminal).
- Clean, dark-themed TUI with keyboard navigation and responsive layout.

---

## 2. System Architecture

```text
portfolio-manager/
├── src/portfolio_manager/
│   ├── config.py            # [CORE] Pydantic settings (.env, DB URL, toggles)
│   ├── database.py          # [CORE] Async SQLAlchemy engine, session, Base
│   ├── models/              # [DATA] ORM definitions (6 models)
│   │   ├── asset.py
│   │   ├── benchmark.py
│   │   ├── portfolio.py
│   │   ├── position.py
│   │   └── transaction.py
│   ├── services/            # [LOGIC] Business rules (framework-agnostic, async SQLAlchemy)
│   │   ├── portfolios.py    # Portfolio CRUD, position management
│   │   ├── trades.py        # Buy/sell, FIFO P&L, trade audit
│   │   ├── charts.py        # Allocation, drawdown, monthly returns
│   │   ├── risk.py          # 9 risk metrics (Sharpe, Sortino, VaR, etc.)
│   │   ├── portfolio_calc.py# NAV, returns, allocation, P&L
│   │   ├── data_feed.py     # yfinance wrapper
│   │   ├── nav_history.py   # Historical NAV from transactions
│   │   ├── benchmark.py     # Benchmark comparison calculations
│   │   ├── classification.py# Sector/industry/region mapping
│   │   ├── price_cache.py   # In-memory TTL cache
│   │   └── chart_data.py    # Chart data generation utilities
│   ├── ui/                  # [TEXTUAL TUI] — NEW
│   │   ├── app.py           # Textual application entry point
│   │   ├── screens/         # TUI screens (Dashboard, Portfolio, Analytics, Trades, Settings)
│   │   ├── widgets/         # Custom Textual widgets (PositionTable, PortfolioCard, etc.)
│   │   └── styles.tcss      # Textual CSS for dark theme
│   └── __init__.py
├── tests/                   # [QA] Pytest suite (43 tests, 39 passing)
├── migrations/              # [DB] Alembic migrations
├── pyproject.toml           # [DEPS] Hatch configuration
├── Dockerfile               # Multi-stage build, Python 3.11, uv
├── docker-compose.yaml      # Service definition
├── PLAN.md                  # [DOC] This file
└── README.md
```

**Architecture Principle:** The services layer is framework-agnostic. Textual TUI is a thin presentation layer that calls services via async. No framework coupling in services.

---

## 3. Textual TUI Design

### Design Philosophy
- **Keyboard-first:** Every action accessible via keyboard shortcuts.
- **Dark theme:** Pure black (`#000`), off-white text (`#E2E8F0`), emerald accents.
- **Sharp edges:** No rounded corners — clean, professional look.
- **Responsive:** Adapts to terminal size (min 80x24, optimal 120x40+).
- **Real-time:** Background task for price refresh with live updates.

### Screen Layout

#### Dashboard Screen
```
┌──────────────────────────────────────────────────────────────┐
│ PORTFOLIO MANAGER              [1] Wacky  [2] Stable  [ESC] │
├──────────────────────────────────────────────────────────────┤
│ Portfolio: Wacky (1/2)                              Jun 18  │
├──────────────────────────────────────────────────────────────┤
│  Total Value: $542,318.42    Day Change: +$1,234.56 (+0.23%) │
│  Positions: 15             Unrealized P&L: +$12,345.67       │
├──────────────────────────────────────────────────────────────┤
│  ┌────────┬────────┬────────┬────────┬────────┬────────┐    │
│  │ Symbol │ Qty    │ Price  │ Value  │ P&L    │ Action │    │
│  ├────────┼────────┼────────┼────────┼────────┼────────┤    │
│  │ AAPL   │ 100    │ $198.5 │ $19,850│ +$1,230│ [S]ell │    │
│  │ MSFT   │ 50     │ $420.1 │ $21,005│ +$2,100│ [S]ell │    │
│  │ SPY    │ 200    │ $540.2 │ $108,040│+$5,400│ [S]ell │    │
│  │ ...    │ ...    │ ...    │ ...    │ ...    │ ...    │    │
│  └────────┴────────┴────────┴────────┴────────┴────────┘    │
├──────────────────────────────────────────────────────────────┤
│ [R]efresh  [A]nalytics  [T]rades  [C]reate  [S]ettings [Q]uit│
└──────────────────────────────────────────────────────────────┘
```

#### Analytics Screen
```
┌──────────────────────────────────────────────────────────────┐
│ PORTFOLIO MANAGER  > Analytics              [ESC] Back       │
├──────────────────────────────────────────────────────────────┤
│  Risk Metrics (Portfolio vs SPY, 1Y)                         │
├──────────────────────────────────────────────────────────────┤
│  Sharpe Ratio: 1.42 [████████░░]  Sortino: 2.18 [███████░░░] │
│  Max Drawdown: -8.3% [███░░░░░░░]  VaR(95): -$4,231 [███░░░░]│
│  Beta: 0.95 [█████░░░░░]  Alpha: +3.2% [████████░░]         │
│  Treynor: 12.4 [██████░░░░]  Calmar: 4.2 [██████████]       │
│  Ulcer Index: 2.1 [██░░░░░░░░]                                │
├──────────────────────────────────────────────────────────────┤
│  [O]pen Charts in Browser  [B]enchmark: [SPY] [QQQ] [Custom] │
│  [1]M  [3]M  [6]M  [1]Y  [A]ll   [R]eturn                    │
└──────────────────────────────────────────────────────────────┘
```

### Chart Strategy
Textual has limited native charting. Two approaches:
1. **Textual-native:** Use `textual-chart` or ASCII-based charts for simple visualizations (allocation pie as bar chart, drawdown as text area chart).
2. **External browser:** Generate Plotly HTML and open in browser with `[O]pen Charts` keybinding. This is the pragmatic choice for complex financial charts.

**Decision:** Use Textual-native for simple data displays (allocation bars, risk metric gauges). Use Plotly-in-browser for complex charts (NAV history, drawdown, monthly returns, benchmark comparison).

---

## 4. Phased Implementation

### Phase 1: Textual Foundation
**Goal:** Set up Textual project structure, app shell, and basic navigation.
- [ ] Add `textual` to pyproject.toml dependencies
- [ ] Create `src/portfolio_manager/ui/` directory structure
- [ ] Build `app.py` — Textual app with async database lifecycle
- [ ] Implement screen routing (Dashboard, Analytics, Trades, Settings)
- [ ] Create base `Screen` class with common functionality (status bar, keybindings)
- [ ] Build `styles.tcss` — dark theme with sharp edges
- [ ] Create CLI entry point (`portfolio-manager` command)
**Status:** ⬜ Not Started

### Phase 2: Dashboard & Portfolio Management
**Goal:** Build the core dashboard — portfolio list, position table, CRUD operations.
- [ ] `DashboardScreen` — portfolio overview with total value, day change, position count
- [ ] `PositionTable` widget — sortable table with gain/loss coloring
- [ ] Portfolio selection (switch between portfolios via number keys)
- [ ] Create portfolio dialog (modal)
- [ ] Delete portfolio dialog with confirmation
- [ ] Price refresh (background task, auto-refresh toggle)
- [ ] Keyboard shortcuts: `[R]`efresh, `[C]`reate, `[D]`elete, `[S]`ettings
**Status:** ⬜ Not Started

### Phase 3: Trade Operations
**Goal:** Buy, sell, and trade audit trail.
- [ ] Buy position dialog — symbol, quantity, price, fee
- [ ] Sell position dialog — quantity, price, fee, P&L preview
- [ ] `TradesScreen` — paginated trade history with filters
- [ ] Trade type indicators (BUY, SELL, DIVIDEND, FEE)
- [ ] FIFO P&L display for realized gains
- [ ] CSV export of trade history
- [ ] Keyboard shortcuts: `[B]`uy, `[S]`ell, `[T]`rades
**Status:** ⬜ Not Started

### Phase 4: Analytics & Risk Metrics
**Goal:** Risk metrics display and chart integration.
- [ ] `AnalyticsScreen` — risk metrics with visual gauges
- [ ] Risk metric coloring (green/yellow/red thresholds)
- [ ] Benchmark selection (SPY, QQQ, custom)
- [ ] Time range selector (1M, 3M, 6M, 1Y, All)
- [ ] Plotly chart generation — NAV history, drawdown, allocation, monthly returns
- [ ] `[O]pen Charts` keybinding to launch browser with Plotly charts
- [ ] Benchmark comparison stats (excess return, tracking error, information ratio)
- [ ] Keyboard shortcuts: `[A]`nalytics, `[O]`pen Charts, `[B]`enchmark
**Status:** ⬜ Not Started

### Phase 5: Data Feed & Real-Time Updates
**Goal:** Background price fetching with live updates.
- [ ] Background worker for periodic price refresh
- [ ] Price cache integration (use existing `price_cache.py`)
- [ ] Live price flash (green/red highlight on change)
- [ ] Connection status indicator (yfinance connectivity)
- [ ] Configurable refresh interval (settings)
- [ ] Manual refresh with `[R]` key
**Status:** ⬜ Not Started

### Phase 6: Settings & Configuration
**Goal:** Settings screen for user preferences.
- [ ] `SettingsScreen` — dark/light theme toggle
- [ ] Data source configuration (yfinance toggle, future API keys)
- [ ] Refresh interval setting
- [ ] Default portfolio selection
- [ ] Database path display
- [ ] Keyboard shortcuts: `[S]`ettings, `[ESC]` back
**Status:** ⬜ Not Started

### Phase 7: Polish & Production Readiness
**Goal:** Production polish, error handling, Docker integration.
- [ ] Error handling — database errors, network errors, yfinance failures
- [ ] Startup sequence — database init, migration check, price cache warmup
- [ ] Graceful shutdown — close DB connections, save state
- [ ] Terminal size handling — responsive layout for small terminals
- [ ] Help screen / keybinding reference (`[?]` or `[H]`elp)
- [ ] Update Dockerfile to run Textual app
- [ ] Update docker-compose.yaml
- [ ] Update pyproject.toml entry point
- [ ] Write Textual-specific tests
- [ ] Integration tests for TUI workflows
**Status:** ⬜ Not Started

---

## 5. Current State & Gap Analysis

### What's Already Done ✅
| Component | Details |
|---|---|
| **Database** | Async SQLAlchemy setup, SQLite, 6 ORM models with relationships. |
| **Services** | 11 service files — framework-agnostic, direct async SQLAlchemy. |
| **Risk Engine** | 9 professional-grade metrics (`risk.py`). |
| **Calc Engine** | NAV, returns, allocation, P&L (`portfolio_calc.py`). |
| **Data Feed** | `yfinance` wrapper (`data_feed.py`). |
| **Price Cache** | TTL cache for market data (`price_cache.py`). |
| **Chart Data** | Allocation, NAV history, drawdown, monthly returns, benchmark comparison. |
| **NAV History** | Historical NAV from transactions (`nav_history.py`). |
| **Classification** | Sector/industry/region for 150+ tickers (`classification.py`). |
| **Benchmark** | Benchmark comparison calculations (`benchmark.py`). |
| **Sell Operations** | Partial/full sell with FIFO P&L in TradeService. |
| **Tests** | 43 tests: 39 passing, 4 db-dependent failures. |
| **Docker** | Dockerfile + docker-compose.yaml (needs Textual update). |

### What Was Removed 🔧 (June 17, 2026)
| Component | Reason |
|---|---|
| Solara UI (`solara_app.py`, `ui/`) | Solara routing broken, no working UI. |
| FastAPI routes (`routes/`) | Orphaned — not used by Solara. |
| FastAPI exception handlers (`exceptions.py`) | FastAPI-specific, not needed for Textual. |
| Solara test files (8 files) | Tested deleted routes/UI components. |
| `test_server.py` | Ran Solara server, no longer applicable. |
| `solara[assets]` dep | No longer in pyproject.toml. |
| `httpx` dep | Not needed for Textual UI. |

### What Needs to Be Built ❌
| Priority | Component | Description |
|---|---|---|
| **P0** | Textual app shell | App entry point, screen routing, base styles. |
| **P0** | Dashboard screen | Portfolio overview, position table, price refresh. |
| **P0** | Trade operations | Buy, sell, trade audit trail. |
| **P1** | Analytics screen | Risk metrics, chart integration. |
| **P1** | Real-time updates | Background worker, price cache, live flash. |
| **P2** | Settings screen | Theme, data source, refresh interval. |
| **P2** | CSV export | Positions, trade history. |
| **P3** | Portfolio classification | Live sector/industry lookups. |

---

## 6. Dependencies to Add

```toml
[project]
dependencies = [
    "textual>=0.68.0",          # TUI framework
    # ... existing deps remain
]

[project.scripts]
portfolio-manager = "portfolio_manager.ui.app:run"
```

---

## 7. Next Steps

1. **Phase 1 (Foundation)** — Set up Textual project structure, app shell, and navigation.
2. **Phase 2 (Dashboard)** — Build the core dashboard with position table.
3. **Phase 3 (Trades)** — Add buy/sell operations and trade audit.
4. **Phase 4 (Analytics)** — Risk metrics and chart integration.
5. **Phase 5 (Real-time)** — Background price fetching.
6. **Phase 6 (Settings)** — User preferences.
7. **Phase 7 (Polish)** — Production readiness, Docker, tests.

> **Legacy plan archived:** The previous PLAN.md (covering FastAPI/React/Solara phases) has been moved to `docs/PLAN_LEGACY.md` for historical reference.

---

## Appendix A: Keybindings Reference

| Key | Action |
|---|---|
| `1-9` | Switch to portfolio N |
| `R` | Refresh prices |
| `A` | Analytics screen |
| `T` | Trades screen |
| `C` | Create portfolio |
| `B` | Buy position |
| `S` | Sell position (from position row) |
| `O` | Open charts in browser |
| `S` | Settings screen |
| `?` / `H` | Help / keybinding reference |
| `Q` | Quit |
| `ESC` | Go back / close dialog |
| `↑↓←→` | Navigate tables |
| `Enter` | Confirm / select |

## Appendix B: Color Palette

| Element | Color |
|---|---|
| Background | `#000` (pure black) |
| Text | `#E2E8F0` (off-white) |
| Accent | `#10B981` (emerald) |
| Positive P&L | `#22C55E` (green) |
| Negative P&L | `#EF4444` (red) |
| Warning | `#F59E0B` (amber) |
| Border | `#334155` (slate) |
| Highlight | `#1E293B` (dark slate) |

</content>