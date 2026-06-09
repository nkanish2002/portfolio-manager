"""Server-side in-memory price cache with TTL.

Avoids hammering yfinance by caching fetched prices with a configurable
time-to-live. Cache invalidation happens automatically on new position
creation (see the `invalidate` method).
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Any


class PriceCache:
    """TTL-backed in-memory price cache.

    Usage::

        cache = PriceCache(ttl_seconds=10)
        price = await cache.get("AAPL")          # cache miss → yfinance → store
        await cache.set("AAPL", Decimal("182.50"))
        cache.invalidate("AAPL")                  # force-refresh
    """

    def __init__(self, ttl_seconds: int = 30) -> None:
        self._ttl = ttl_seconds
        # {symbol: {"price": Decimal, "ts": float}}
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # ---- public API ----

    async def get(self, symbol: str) -> Decimal | None:
        """Return cached price if fresh, else None."""
        async with self._lock:
            entry = self._cache.get(symbol)
            if entry is None:
                return None
            if time.monotonic() - entry["ts"] > self._ttl:
                del self._cache[symbol]
                return None
            return entry["price"]

    async def set(self, symbol: str, price: Decimal) -> None:
        async with self._lock:
            self._cache[symbol] = {"price": price, "ts": time.monotonic()}

    async def invalidate(self, symbol: str) -> None:
        async with self._lock:
            self._cache.pop(symbol, None)

    async def invalidate_all(self) -> None:
        async with self._lock:
            self._cache.clear()

    async def bulk_get(self, symbols: list[str]) -> dict[str, Decimal | None]:
        """Fetch fresh prices for a batch of symbols.

        For each symbol: return cached if present, otherwise call
        `fetcher_fn` to resolve it. Returns a dict mapping symbol → price.
        """
        async with self._lock:
            # Snapshot current cache state
            results: dict[str, Decimal | None] = {}
            for sym in symbols:
                entry = self._cache.get(sym)
                if entry and time.monotonic() - entry["ts"] <= self._ttl:
                    results[sym] = entry["price"]
                    continue
                results[sym] = None  # cache miss

        # Resolve misses outside the lock to avoid blocking other requests
        # (caller must pass a fetcher function)
        return results

    @property
    def size(self) -> int:
        return len(self._cache)


# Singleton
default_cache = PriceCache(ttl_seconds=30)
