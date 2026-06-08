# Portfolio Manager

Professional portfolio management tool with Schwab asset-class support.

## Features

- Multi-asset-class support (equities, options, futures, bonds, ETFs, mutual funds, ADRs, cash, crypto)
- Performance tracking with benchmark comparison
- Interactive charts (Plotly)
- Risk metrics (Sharpe, Sortino, Max Drawdown, VaR, Beta, Alpha, etc.)
- Beautiful web UI (FastAPI + HTMX + Tailwind CSS)
- Extensible data feed layer (yfinance dev → paid APIs prod)

## Quick Start

```bash
cd portfolio-manager
uv sync
uv run uvicorn src.portfolio_manager.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)

## Architecture

```
src/portfolio_manager/
├── main.py            # FastAPI app factory
├── config.py          # Settings
├── database.py        # SQLAlchemy engine
├── models/            # SQLAlchemy ORM models
├── routes/            # API + HTML route handlers
├── services/          # Business logic (calc, risk, data)
└── templates/         # Jinja2 HTML templates
```

## Asset Classes (Schwab)

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
