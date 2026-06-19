"""Market data feed abstraction.

Currently backed by yfinance; swap to paid APIs (Schwab, Polygon, etc.) later.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol

import pandas as pd

# Lazy import so yfinance is optional
import yfinance as yf  # type: ignore[import-untyped]


class PriceSource(Protocol):
    """Protocol for pluggable price sources."""

    def get_price(self, symbol: str, as_of: date | None = None) -> Decimal | None: ...
    def get_historical(self, symbol: str, start: date, end: date) -> pd.DataFrame: ...


class YFinanceSource:
    """yfinance-backed price source."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def check_connection(self) -> bool:
        """Check if yfinance can reach Yahoo Finance.

        Returns:
            True if a lightweight price fetch succeeds, False otherwise.
        """
        try:
            # Probe with a well-known, liquid symbol
            result = self.get_price("SPY")
            return result is not None
        except Exception:
            return False

    def get_price(self, symbol: str, as_of: date | None = None) -> Decimal | None:
        """Get latest (or historical) price for a symbol."""
        ticker = yf.Ticker(symbol)
        if as_of:
            hist = ticker.history(start=str(as_of), end=str(as_of + timedelta(days=1)))
        else:
            hist = ticker.history(period="1d")
        if hist.empty:
            return None
        return Decimal(str(round(hist["Close"].iloc[-1], 2)))

    def get_historical(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Get historical OHLCV data as a DataFrame indexed by Date."""
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=str(start), end=str(end + timedelta(days=1)))
        if df.empty:
            return pd.DataFrame(columns=["Date", "Close", "Volume"])
        df.index = df.index.date
        df = df.rename(columns={"Close": "Close", "Volume": "Volume"})
        df.index.name = "Date"
        return df.reset_index()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search for ticker symbols."""
        results = yf.Tickers(query)
        tickers = results.tickers if hasattr(results, "tickers") else []
        return [
            {"symbol": t.symbol, "name": t.info.get("shortName", t.symbol)} for t in tickers[:limit]
        ]


# Singleton default instance
default_source: PriceSource = YFinanceSource()


def get_price(symbol: str, as_of: date | None = None) -> Decimal | None:
    return default_source.get_price(symbol, as_of)


def get_historical(symbol: str, start: date, end: date) -> pd.DataFrame:
    return default_source.get_historical(symbol, start, end)
