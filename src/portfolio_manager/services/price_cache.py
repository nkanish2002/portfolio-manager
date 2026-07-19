"""In-memory TTL cache for market data.

A small, thread-safe, monotonic-clock-based cache used by the data feed
and the WebSocket price poller. ``time.monotonic`` is used for expiry so
wall-clock changes (NTP jumps, DST) never corrupt the TTL.
"""

from __future__ import annotations

import time
from threading import Lock


class PriceCache[V]:
    """A generic TTL cache.

    Each entry stores ``(value, expires_at_monotonic)``. A ``ttl`` of ``0``
    or negative means "do not cache" (the value is discarded on ``set``).
    """

    def __init__(self, default_ttl: float = 30.0) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, tuple[V, float]] = {}
        self._lock = Lock()

    # ── core API ──────────────────────────────────────────────────────

    def get(self, key: str) -> V | None:
        """Return the cached value if present and unexpired, else None."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at <= time.monotonic():
                # expired — evict and miss
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: V, ttl: float | None = None) -> None:
        """Store ``value`` under ``key`` with the given TTL (seconds).

        ``ttl=None`` uses the cache default. ``ttl<=0`` skips caching.
        """
        ttl = self._default_ttl if ttl is None else ttl
        if ttl <= 0:
            # explicit "don't cache" — evict any stale entry
            with self._lock:
                self._store.pop(key, None)
            return
        expires_at = time.monotonic() + ttl
        with self._lock:
            self._store[key] = (value, expires_at)

    def invalidate(self, key: str) -> None:
        """Drop a single key (no-op if absent)."""
        with self._lock:
            self._store.pop(key, None)

    def invalidate_all(self) -> None:
        """Drop every key."""
        with self._lock:
            self._store.clear()

    # ── batch helpers (used by the WS poller) ─────────────────────────

    def get_many(self, keys: list[str]) -> dict[str, V]:
        """Return a mapping of present, unexpired keys → values."""
        out: dict[str, V] = {}
        with self._lock:
            for key in keys:
                entry = self._store.get(key)
                if entry is None:
                    continue
                value, expires_at = entry
                if expires_at <= time.monotonic():
                    self._store.pop(key, None)
                    continue
                out[key] = value
        return out

    def set_many(self, items: dict[str, V], ttl: float | None = None) -> None:
        """Store many entries with a shared TTL."""
        ttl = self._default_ttl if ttl is None else ttl
        if ttl <= 0:
            with self._lock:
                for key in items:
                    self._store.pop(key, None)
            return
        expires_at = time.monotonic() + ttl
        with self._lock:
            for key, value in items.items():
                self._store[key] = (value, expires_at)

    # ── introspection (handy for tests / health) ─────────────────────

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __contains__(self, key: str) -> bool:
        """True if ``key`` is present and unexpired (does not evict)."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            _, expires_at = entry
            return expires_at > time.monotonic()

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())
