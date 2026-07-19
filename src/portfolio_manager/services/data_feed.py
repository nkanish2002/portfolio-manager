"""Market data feed — async yfinance wrapper with TTL cache integration.

yfinance is synchronous (requests-based), so every call is offloaded to a
worker thread via ``asyncio.to_thread`` to avoid blocking the event loop.
The concrete network access lives behind a ``QuoteFetcher`` protocol so the
async ``DataFeed`` can be unit-tested with an in-memory fake — no network.

Public surface (per PLAN Segment 2.1):
  * ``get_price(symbol) -> PriceQuote | None``   (cache-aware)
  * ``get_historical(symbol, period) -> list[PriceBar]``
  * ``search_ticker(query) -> list[TickerSearchResult]``
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from portfolio_manager.config import settings
from portfolio_manager.services.price_cache import PriceCache

# ── DTOs (pure transport objects, no DB) ──────────────────────────────────


class PriceQuote:
    """A single live/most-recent quote for a symbol."""

    __slots__ = (
        "symbol", "price", "prev_close", "change", "change_pct",
        "currency", "exchange", "timestamp", "source",
    )

    def __init__(
        self,
        *,
        symbol: str,
        price: float,
        prev_close: float | None = None,
        change: float | None = None,
        change_pct: float | None = None,
        currency: str | None = None,
        exchange: str | None = None,
        timestamp: datetime | None = None,
        source: str = "yfinance",
    ) -> None:
        self.symbol = symbol
        self.price = float(price)
        self.prev_close = float(prev_close) if prev_close is not None else None
        # derive change from prev_close when not supplied (safe for prev_close == 0)
        if change is None and prev_close is not None:
            change = self.price - prev_close
        # change_pct needs a non-zero prev_close to avoid division by zero
        if change_pct is None and prev_close and prev_close != 0:
            change_pct = (self.price - prev_close) / prev_close * 100.0
        self.change = change
        self.change_pct = change_pct
        self.currency = currency
        self.exchange = exchange
        self.timestamp = timestamp or datetime.now(UTC)
        self.source = source

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "prev_close": self.prev_close,
            "change": self.change,
            "change_pct": self.change_pct,
            "currency": self.currency,
            "exchange": self.exchange,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PriceQuote):
            return NotImplemented
        return self.symbol == other.symbol and self.price == other.price

    def __repr__(self) -> str:
        return f"PriceQuote(symbol={self.symbol!r}, price={self.price}, source={self.source!r})"


class PriceBar:
    """A single OHLCV bar from a historical series."""

    __slots__ = ("date", "open", "high", "low", "close", "volume")

    def __init__(
        self,
        *,
        date,  # datetime.date
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int | None = None,
    ) -> None:
        self.date = date
        self.open = float(open)
        self.high = float(high)
        self.low = float(low)
        self.close = float(close)
        self.volume = int(volume) if volume is not None else None

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class TickerSearchResult:
    """A ticker-search hit."""

    __slots__ = ("symbol", "name", "exchange", "quote_type", "sector")

    def __init__(
        self,
        *,
        symbol: str,
        name: str,
        exchange: str | None = None,
        quote_type: str | None = None,
        sector: str | None = None,
    ) -> None:
        self.symbol = symbol
        self.name = name
        self.exchange = exchange
        self.quote_type = quote_type
        self.sector = sector

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "quote_type": self.quote_type,
            "sector": self.sector,
        }


# ── Fetcher protocol (pluggable for tests) ─────────────────────────────────


@runtime_checkable
class QuoteFetcher(Protocol):
    """Synchronous data source — wrapped in a thread by ``DataFeed``."""

    def quote(self, symbol: str) -> PriceQuote | None: ...

    def history(self, symbol: str, period: str) -> list[PriceBar]: ...

    def search(self, query: str, max_results: int = 10) -> list[TickerSearchResult]: ...


# ── yfinance implementation ────────────────────────────────────────────────


class YFinanceFetcher:
    """Real yfinance-backed fetcher (synchronous)."""

    def quote(self, symbol: str) -> PriceQuote | None:
        import yfinance as yf

        try:
            info = yf.Ticker(symbol).fast_info
            price = getattr(info, "last_price", None)
            if price is None:
                return None
            prev_close = getattr(info, "previous_close", None)
            return PriceQuote(
                symbol=symbol.upper(),
                price=price,
                prev_close=prev_close,
                currency=getattr(info, "currency", None),
                exchange=getattr(info, "exchange", None),
            )
        except Exception:  # noqa: BLE001 — network/parse failures → no quote
            return None

    def history(self, symbol: str, period: str) -> list[PriceBar]:
        import yfinance as yf

        df = yf.Ticker(symbol).history(period=period)
        if df is None or df.empty:
            return []
        bars: list[PriceBar] = []
        for idx, row in df.iterrows():
            # idx is a tz-aware pandas Timestamp; normalize to a date
            bar_date = getattr(idx, "date", None) or idx
            volume = row.get("Volume")
            bars.append(
                PriceBar(
                    date=bar_date,
                    open=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    volume=volume if volume == volume else None,  # NaN guard
                )
            )
        return bars

    def search(self, query: str, max_results: int = 10) -> list[TickerSearchResult]:
        import yfinance as yf

        try:
            results = yf.Search(query, max_results=max_results).quotes
        except Exception:  # noqa: BLE001
            return []
        out: list[TickerSearchResult] = []
        for r in results:
            symbol = r.get("symbol")
            name = r.get("shortname") or r.get("longname") or symbol or ""
            if not symbol:
                continue
            out.append(
                TickerSearchResult(
                    symbol=symbol,
                    name=name,
                    exchange=r.get("exchDisp") or r.get("exchange"),
                    quote_type=r.get("quoteType"),
                    sector=r.get("sector"),
                )
            )
        return out[:max_results]


# ── Async wrapper with cache integration ──────────────────────────────────


class DataFeed:
    """Async market-data facade: cache-first quote lookups + threaded I/O."""

    def __init__(
        self,
        cache: PriceCache[PriceQuote],
        fetcher: QuoteFetcher | None = None,
        *,
        enabled: bool | None = None,
    ) -> None:
        self._cache = cache
        self._fetcher = fetcher or YFinanceFetcher()
        self._enabled = settings.YFINANCE_ENABLED if enabled is None else enabled

    @staticmethod
    def _norm(symbol: str) -> str:
        return symbol.strip().upper()

    async def get_price(self, symbol: str) -> PriceQuote | None:
        """Return a quote for ``symbol`` — cache first, then yfinance.

        A cache miss fetches from the feed and caches the result for the
        cache's default TTL. Returns ``None`` if the feed is disabled or the
        symbol is unknown.
        """
        key = self._norm(symbol)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        if not self._enabled:
            return None
        quote = await asyncio.to_thread(self._fetcher.quote, key)
        if quote is not None:
            self._cache.set(key, quote)
        return quote

    async def get_historical(self, symbol: str, period: str = "1mo") -> list[PriceBar]:
        """Return OHLCV bars for ``symbol`` over ``period`` (e.g. ``1mo``, ``1y``)."""
        if not self._enabled:
            return []
        return await asyncio.to_thread(self._fetcher.history, self._norm(symbol), period)

    async def search_ticker(self, query: str, max_results: int = 10) -> list[TickerSearchResult]:
        """Search tickers by free-text query."""
        if not self._enabled:
            return []
        return await asyncio.to_thread(self._fetcher.search, query, max_results)

    # ── cache control ───────────────────────────────────────────────

    def invalidate(self, symbol: str) -> None:
        """Drop a cached quote so the next lookup refetches."""
        self._cache.invalidate(self._norm(symbol))


# ── Module-level singletons (used by routes/services) ────────────────────

price_cache: PriceCache[PriceQuote] = PriceCache(default_ttl=settings.PRICE_CACHE_TTL_SECONDS)
data_feed: DataFeed = DataFeed(price_cache, enabled=settings.YFINANCE_ENABLED)
