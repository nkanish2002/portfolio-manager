"""Tests for the DataFeed — async yfinance wrapper with cache integration.

Network calls are isolated behind a ``FakeFetcher`` so the suite is fully
deterministic and CI-safe. A separate live smoke test (marked ``live``) is
skipped by default and exercises the real ``YFinanceFetcher`` on demand.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from portfolio_manager.services.data_feed import (
    DataFeed,
    PriceBar,
    PriceQuote,
    TickerSearchResult,
)
from portfolio_manager.services.price_cache import PriceCache

# ── Fakes ────────────────────────────────────────────────────────────────


class FakeFetcher:
    """In-memory QuoteFetcher stub."""

    def __init__(self) -> None:
        self.quotes: dict[str, PriceQuote] = {}
        self.history_: dict[str, list[PriceBar]] = {}
        self.search_results: dict[str, list[TickerSearchResult]] = {}
        self.quote_calls = 0
        self.history_calls = 0
        self.search_calls = 0

    def add_quote(self, symbol: str, price: float, prev_close: float | None = None) -> None:
        self.quotes[symbol.upper()] = PriceQuote(
            symbol=symbol.upper(), price=price, prev_close=prev_close, currency="USD",
        )

    def quote(self, symbol: str) -> PriceQuote | None:
        self.quote_calls += 1
        return self.quotes.get(symbol.upper())

    def history(self, symbol: str, period: str) -> list[PriceBar]:
        self.history_calls += 1
        return self.history_.get(symbol.upper(), [])

    def search(self, query: str, max_results: int = 10) -> list[TickerSearchResult]:
        self.search_calls += 1
        return self.search_results.get(query.lower(), [])[:max_results]


def make_feed(ttl: float = 30) -> tuple[DataFeed, PriceCache[PriceQuote], FakeFetcher]:
    cache: PriceCache[PriceQuote] = PriceCache(default_ttl=ttl)
    fetcher = FakeFetcher()
    return DataFeed(cache, fetcher, enabled=True), cache, fetcher


# ── get_price ────────────────────────────────────────────────────────────


class TestGetPrice:
    async def test_fetches_from_fetcher_on_miss(self):
        feed, cache, fetcher = make_feed()
        fetcher.add_quote("AAPL", 198.5, prev_close=197.0)
        q = await feed.get_price("aapl")
        assert q is not None
        assert q.symbol == "AAPL"
        assert q.price == 198.5
        assert q.prev_close == 197.0
        assert q.change == pytest.approx(1.5)
        assert fetcher.quote_calls == 1

    async def test_cache_hit_avoids_refetch(self):
        feed, cache, fetcher = make_feed()
        fetcher.add_quote("AAPL", 198.5)
        await feed.get_price("AAPL")  # miss → fetch
        await feed.get_price("AAPL")  # hit → no fetch
        assert fetcher.quote_calls == 1

    async def test_unknown_symbol_returns_none(self):
        feed, cache, fetcher = make_feed()
        assert await feed.get_price("ZZZZ") is None
        assert fetcher.quote_calls == 1

    async def test_disabled_returns_none_without_fetch(self):
        cache: PriceCache[PriceQuote] = PriceCache(default_ttl=30)
        fetcher = FakeFetcher()
        feed = DataFeed(cache, fetcher, enabled=False)
        assert await feed.get_price("AAPL") is None
        assert fetcher.quote_calls == 0

    async def test_normalizes_symbol_case_and_whitespace(self):
        feed, cache, fetcher = make_feed()
        fetcher.add_quote("AAPL", 198.5)
        await feed.get_price("  aapl ")
        # cached under uppercased key
        assert cache.get("AAPL") is not None

    async def test_fetch_failure_not_cached(self):
        feed, cache, fetcher = make_feed()
        # symbol not in fetcher → None, must not pollute cache
        await feed.get_price("MISS")
        assert "MISS" not in cache


# ── get_historical ───────────────────────────────────────────────────────


class TestGetHistorical:
    async def test_returns_bars_from_fetcher(self):
        feed, cache, fetcher = make_feed()
        fetcher.history_["AAPL"] = [
            PriceBar(date=datetime(2026, 7, 1).date(), open=1, high=2, low=0.5, close=1.5, volume=100),
            PriceBar(date=datetime(2026, 7, 2).date(), open=1.5, high=2.5, low=1, close=2, volume=200),
        ]
        bars = await feed.get_historical("AAPL", "1mo")
        assert len(bars) == 2
        assert bars[0].close == 1.5
        assert bars[1].volume == 200
        assert fetcher.history_calls == 1

    async def test_disabled_returns_empty(self):
        cache: PriceCache[PriceQuote] = PriceCache()
        feed = DataFeed(cache, FakeFetcher(), enabled=False)
        assert await feed.get_historical("AAPL") == []


# ── search_ticker ────────────────────────────────────────────────────────


class TestSearchTicker:
    async def test_returns_results_from_fetcher(self):
        feed, cache, fetcher = make_feed()
        fetcher.search_results["apple"] = [
            TickerSearchResult(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", quote_type="EQUITY"),
            TickerSearchResult(symbol="AAPL.SW", name="Apple SW", exchange="Swiss"),
        ]
        results = await feed.search_ticker("Apple", max_results=1)
        assert len(results) == 1
        assert results[0].symbol == "AAPL"

    async def test_disabled_returns_empty(self):
        cache: PriceCache[PriceQuote] = PriceCache()
        feed = DataFeed(cache, FakeFetcher(), enabled=False)
        assert await feed.search_ticker("anything") == []


# ── cache integration ────────────────────────────────────────────────────


class TestCacheIntegration:
    async def test_invalidate_forces_refetch(self):
        feed, cache, fetcher = make_feed()
        fetcher.add_quote("AAPL", 198.5)
        await feed.get_price("AAPL")
        assert fetcher.quote_calls == 1
        feed.invalidate("aapl")  # case-insensitive
        await feed.get_price("AAPL")
        assert fetcher.quote_calls == 2

    async def test_short_ttl_expires_to_refetch(self):
        feed, cache, fetcher = make_feed(ttl=0.05)
        fetcher.add_quote("AAPL", 198.5)
        await feed.get_price("AAPL")
        assert fetcher.quote_calls == 1
        await asyncio.sleep(0.06)
        await feed.get_price("AAPL")
        assert fetcher.quote_calls == 2


# ── DTO behaviour ────────────────────────────────────────────────────────


class TestPriceQuote:
    def test_change_derived_from_prev_close(self):
        q = PriceQuote(symbol="AAPL", price=110.0, prev_close=100.0)
        assert q.change == pytest.approx(10.0)
        assert q.change_pct == pytest.approx(10.0)

    def test_no_prev_close_leaves_change_none(self):
        q = PriceQuote(symbol="X", price=50.0)
        assert q.prev_close is None
        assert q.change is None
        assert q.change_pct is None

    def test_zero_prev_close_does_not_divide_by_zero(self):
        q = PriceQuote(symbol="X", price=50.0, prev_close=0.0)
        assert q.change == pytest.approx(50.0)
        assert q.change_pct is None  # guarded

    def test_to_dict_round_trip(self):
        q = PriceQuote(symbol="AAPL", price=1.0, prev_close=1.0, currency="USD")
        d = q.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["price"] == 1.0
        assert "timestamp" in d and d["source"] == "yfinance"


# ── Live smoke test (opt-in, network) ────────────────────────────────────


@pytest.mark.live
class TestLiveYFinance:
    """Exercises the real yfinance fetcher. Skipped unless ``-m live`` is passed.

    Run: ``uv run pytest tests/test_data_feed.py -m live -v``
    """

    async def test_live_get_price_returns_float(self):
        from portfolio_manager.services.data_feed import YFinanceFetcher

        q = YFinanceFetcher().quote("AAPL")
        if q is None:  # network blocked in CI
            pytest.skip("yfinance unreachable")
        assert isinstance(q.price, float)
        assert q.price > 0
        assert q.symbol == "AAPL"
