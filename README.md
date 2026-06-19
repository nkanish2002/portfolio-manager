# Portfolio Manager

A keyboard-driven, terminal-native portfolio management tool with Schwab asset-class support. Built on Textual for a fast, no-browser experience.

## Description

Portfolio Manager is a lightweight, terminal-first application for tracking investment portfolios. It replaces the previous Solara web frontend with a native Textual TUI, eliminating 200MB+ of CDN and React dependencies. The application runs from any terminal with ncurses support -- no browser, no web server, no port exposure required.

**Key capabilities:**
- Multi-asset-class support (equities, options, futures, bonds, ETFs, mutual funds, ADRs, CFDs, crypto, cash)
- Real-time price tracking via yfinance with configurable background refresh
- Professional risk metrics (Sharpe, Sortino, Max Drawdown, VaR, Beta, Alpha, Volatility)
- Six terminal-native charts rendered via textual-plotext (pie, heatmap, line, area, histogram)
- Buy/Sell trade execution with average-cost P&L tracking
- Persistent settings (theme, refresh interval, yfinance toggle, default portfolio)
- Docker-ready with interactive TUI entrypoint

## Architecture

```
src/portfolio_manager/
├── config.py            # Pydantic settings (env + defaults)
├── database.py          # Async SQLAlchemy engine + session (aiosqlite)
├── models/              # 6 ORM models (asset, benchmark, portfolio, position, transaction)
├── services/            # Framework-agnostic async business logic
│   ├── portfolios.py    # CRUD, position management
│   ├── trades.py        # Buy/sell, average-cost P&L
│   ├── analytics.py     # Portfolio allocation, monthly returns, risk metrics
│   ├── risk_gauges.py   # Sharpe, Sortino, max drawdown, volatility
│   ├── data_feed.py     # yfinance wrapper with connection checking
│   ├── chart_data.py    # Chart data preparation
│   ├── charts.py        # Chart rendering utilities
│   ├── benchmark.py     # Benchmark comparison (SPY, QQQ, custom)
│   ├── nav_history.py   # Historical NAV tracking
│   ├── classification.py# Sector/industry/region mapping
│   └── settings.py      # JSON-backed persistent settings
└── ui/                  # Textual TUI
    ├── app.py           # Main Textual app: navigation, keybindings, DB init
    ├── styles.tcss      # Dark + light theme CSS
    ├── screens/
    │   ├── base.py      # Shared base screen with DB session
    │   ├── dashboard.py # Portfolio overview, positions, real-time prices
    │   ├── analytics.py # Risk gauges + 6 textual-plotext charts
    │   ├── trades.py    # Trade history, buy/sell modals, CSV export
    │   ├── settings.py  # Theme, refresh, yfinance, default portfolio
    │   └── help.py      # Auto-generated keybinding reference
    └── widgets/
        ├── position_table.py    # Sortable positions with gain/loss coloring
        ├── trade_modal.py       # Buy/Sell modals with validation + P&L preview
        ├── portfolio_modal.py   # Create/Delete portfolio modals
        └── risk_gauge.py        # ASCII risk gauge widget
```

## Features

| Feature | Details |
|---|---|
| **Dashboard** | Live positions, NAV, P&L, portfolio switcher (keys 1-9) |
| **Trades** | Buy/Sell with validation, P&L preview, paginated history, CSV export |
| **Analytics** | 6 charts (allocation pie, monthly heatmap, sector bar, cumulative returns line, price history, drawdown area), 6 risk gauges, benchmark selector |
| **Real-time** | Background price refresh (configurable 30s default), row-flash on change, online/offline indicator |
| **Settings** | Theme toggle (light/dark), refresh interval, yfinance enable/disable, default portfolio |
| **Multi-asset** | Schwab asset classes: equities, options (:OPT), futures (:FUT), mutual funds (:MF), CFDs (:CFD), crypto (:CRYPTO), cash (:CASH) |
| **Persistence** | SQLite + aiosqlite (async), Alembic migrations, JSON settings file |

## Quick Start

### Prerequisites

- Python 3.11+
- uv (package manager): https://github.com/astral-sh/uv
- A terminal with ncurses support (xterm-256color recommended)

### Local Installation

```bash
# Clone and enter the project
cd portfolio-manager

# Install dependencies
uv sync

# Run the TUI
uv run portfolio-manager
```

Open http://localhost -- wait, there is no HTTP. This is a terminal app! Just run the command above.

### Docker

```bash
# Build and run interactively
docker compose run --rm portfolio-manager

# Or build manually
docker build -t portfolio-manager .
docker run --rm -it -e TERM=xterm-256color portfolio-manager
```

The container launches the Textual TUI directly. No port mapping needed. Data persists in the `portfolio-data` volume.

## Usage

### Navigation

Press the key shown in brackets to navigate between screens:

| Key | Action | Screen |
|---|---|---|
| `[D]` | Dashboard (default on launch) | Portfolio positions, NAV, P&L |
| `[T]` | Trades | Trade history, buy/sell execution |
| `[A]` | Analytics | Risk metrics, charts, benchmark comparison |
| `[S]` | Settings | Theme, refresh interval, yfinance, default portfolio |
| `[?]` | Help | All keybindings reference |

### Dashboard Keys

| Key | Action |
|---|---|
| `[R]` | Refresh prices (yfinance) |
| `[1]` - `[9]` | Switch portfolio |
| `[C]` | Create new portfolio |
| `[Esc]` | Back / close modal |

### Analytics Keys

| Key | Action |
|---|---|
| `[B]` | Cycle benchmark (SPY -> QQQ -> Custom -> SPY) |
| `[1]` | 1-month range |
| `[3]` | 3-month range |
| `[6]` | 6-month range |
| `[y]` | 1-year range |
| `[a]` | All time |
| `[R]` | Refresh all data |

### Trades Keys

| Key | Action |
|---|---|
| `[B]` | Buy modal |
| `[S]` | Sell modal (when a position row is focused) |
| `[E]` | Export trade history to CSV |
| `ALL` / `BUY` / `SELL` / `DIVIDEND` / `FEE` | Filter buttons |

### Global Keys

| Key | Action |
|---|---|
| `[Q]` | Quit application |
| `[?]` | Help screen |
| `[Esc]` | Back / close modal / exit full-screen chart |

### Screens Overview

**Dashboard** -- Shows your portfolio overview: total value, day change, and a sortable position table with gain/loss coloring. Green rows indicate profit, red rows indicate loss. Rows flash blue when prices update during background refresh.

**Analytics** -- Displays six risk gauges (Sharpe, Sortino, Max Drawdown, Volatility, Beta, Alpha) in a header row, followed by six textual-plotext charts: asset allocation pie chart, monthly returns heatmap, sector allocation bar chart, cumulative returns line chart, individual price history, and drawdown area chart. Use range keys (1, 3, 6, y, a) to adjust the time window.

**Trades** -- Paginated trade history with filter buttons (ALL / BUY / SELL / DIVIDEND / FEE). Click Buy to open the trade modal: enter ticker, quantity, and price; preview P&L before executing. Click Sell (on a focused row) to sell that position. Export full trade history to CSV.

**Settings** -- Configure the application: toggle between light and dark themes, set the price refresh interval (in seconds), enable/disable automatic yfinance price fetching, and select the default portfolio to load on startup. All settings persist across restarts in `.settings.json`.

**Help** -- Auto-generated reference screen listing all keybindings organized by screen. Press [?] from any screen to open it.

### Asset Classes (Schwab)

| Class | Symbol Suffix |
|---|---|
| Equities | None |
| Options | `:OPT` |
| Futures | `:FUT` |
| Bonds | None (CUSIP-based) |
| ETFs | None |
| Mutual Funds | `:MF` |
| ADRs | None |
| CFDs | `:CFD` |
| Crypto | `:CRYPTO` |
| Cash | `:CASH` |

## Developer Guide

### Project Structure

```
pyproject.toml          # uv project config: textual, pydantic-settings, SQLAlchemy, yfinance
Dockerfile              # Multi-stage build: uv builder + runtime
docker-compose.yaml     # Docker Compose with tty/stdin_open
migrations/             # Alembic database migrations
src/portfolio_manager/  # Application source
├── ui/                 # Textual TUI (screens, widgets, styles)
├── services/           # Business logic (framework-agnostic)
├── models/             # SQLAlchemy ORM models
├── config.py           # Pydantic settings
└── database.py         # Async SQLAlchemy engine
tests/                  # pytest test suite (191 tests passing)
```

### Development Workflow

```bash
# Install dependencies
uv sync

# Run the TUI
uv run portfolio-manager

# Run tests
uv run pytest -q

# Run tests with verbose output
uv run pytest -v

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Run Alembic migrations
uv run alembic upgrade head

# Apply a single migration
uv run alembic upgrade <revision>
```

### Adding a New Screen

1. Create `src/portfolio_manager/ui/screens/<name>.py` inheriting from `BaseScreen`.
2. Define `BINDINGS` with `(key, action, description)` tuples.
3. Register the screen in `app.py`'s navigation bindings.
4. Add the screen to `HelpScreen._registry` in `help.py` via `HelpScreen.register_screen()`.

### Adding a New Widget

1. Create `src/portfolio_manager/ui/widgets/<name>.py`.
2. Inherit from `Widget` or `Static` or `DataTable` as appropriate.
3. Define CSS in the widget's `CSS` class attribute.
4. Import and compose in the target screen.

### Testing

The test suite uses pytest with pytest-asyncio. Tests use an autouse `isolated_db` fixture that builds a fresh in-memory SQLite per test -- no `portfolio.db` writes from the test suite.

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_analytics_screen.py -v

# Run with coverage
uv run pytest --cov=src/portfolio_manager --cov-report=term-missing

# Run Pilot/screen tests (textual snapshot tests)
uv run pytest tests/test_pilot_screens.py -v
```

### Docker Development

```bash
# Build the image
docker compose build

# Run interactively
docker compose run --rm portfolio-manager

# Run with a specific command
docker compose run --rm portfolio-manager uv run pytest
```

The Docker image uses a multi-stage build: the `builder` stage installs dependencies, and the `runtime` stage copies only thevenv and source code. The container includes `ncurses-term` and sets `TERM=xterm-256color` for proper terminal rendering.

## Debugging

### Application Logging

The app uses Python's `logging` module with `structlog`-style formatting. Logs are written to `stdout` with level prefix:

```
2026-06-19 11:30:00,123 [ERROR] [Database] Database initialization failed: ...
2026-06-19 11:30:01,456 [INFO] Loaded 2 portfolio(s).
```

Set the log level via the `LOG_LEVEL` environment variable:

```bash
LOG_LEVEL=DEBUG uv run portfolio-manager
```

### Textual DevTools

Textual ships with built-in development tools:

```bash
# Start the app with devtools (live reload + browser console)
uv run textual run --dev portfolio_manager.ui.app:run

# Open Textual's console in a second terminal
uv run textual console
```

Devtools opens a browser window showing the app layout, widget tree, and live console for inspecting bindings, events, and state.

### Common Issues

**Terminal is garbled / characters overlap** -- Your terminal doesn't support 256 colors. Set `TERM=xterm-256color` or switch to a terminal emulator that supports it (tmux, Kitty, Alacritty, Wezterm).

**Prices not updating** -- Check the connection indicator at the top. If it shows red/offline, yfinance is unreachable. Toggle `yfinance_enabled` to `false` in Settings. Check your internet connection.

**Database errors on startup** -- The database file is at `portfolio.db` (or the path in `DATABASE_URL`). If corrupted, back it up and delete it -- the app will recreate tables on next launch. You'll lose existing data.

**Screen is blank / crashes on launch** -- Run with `LOG_LEVEL=DEBUG` to see error traces. Check that `uv sync` completed successfully and all dependencies are installed.

**Chart rendering issues** -- textual-plotext requires `plt` backend support. Ensure your terminal supports the required character set. Some terminals (like VS Code's built-in terminal) may need configuration adjustments.

### Inspecting the Database

The database is a standard SQLite file. You can inspect it directly:

```bash
sqlite3 portfolio.db ".tables"
sqlite3 portfolio.db "SELECT * FROM portfolios;"
```

Or use the Python REPL:

```python
from portfolio_manager.database import async_session
async with async_session() as s:
    from portfolio_manager.models import Portfolio
    result = await s.execute(select(Portfolio))
    print(result.all())
```

## Configuration

Settings are managed through both environment variables and the in-app Settings screen:

| Environment Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./portfolio.db` | Database connection string |
| `DEBUG` | `True` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `TERM` | `xterm-256color` | Terminal type (for Docker) |

In-app settings (persisted in `.settings.json`):

| Setting | Default | Description |
|---|---|---|
| `theme` | `dark` | UI theme (dark or light) |
| `price_refresh_interval` | `30` | Seconds between background price refreshes |
| `yfinance_enabled` | `true` | Whether to fetch live prices |
| `default_portfolio_id` | (empty) | Portfolio ID to load on startup |

## Built With

| Layer | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **TUI Framework** | Textual >= 0.86.0 |
| **Charting** | textual-plotext >= 1.0.1 |
| **Database** | SQLAlchemy 2.x (async) + aiosqlite |
| **Migrations** | Alembic >= 1.14 |
| **Data Fetching** | yfinance >= 0.2 |
| **Settings** | pydantic-settings >= 2.0 |
| **Data Processing** | pandas >= 2.2, numpy >= 2.0 |
| **Testing** | pytest >= 8.0, pytest-asyncio >= 0.24 |
| **Linting** | Ruff >= 0.8 |
| **Packaging** | uv + hatchling |

This project was built using **Hermes Agent** with the **Qwen3.6-35B-A3B-MTP-GGUF** model, guided by the Textual TUI migration plan (Phases 1-7). 191 tests passing at time of release.

## License

MIT
