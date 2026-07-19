"""Unit tests for the in-memory TTL price cache (no network)."""

from __future__ import annotations

import time

from portfolio_manager.services.price_cache import PriceCache


class TestBasicGetSet:
    def test_set_then_get_returns_value(self):
        c: PriceCache[float] = PriceCache(default_ttl=30)
        c.set("AAPL", 198.5)
        assert c.get("AAPL") == 198.5

    def test_get_missing_returns_none(self):
        c: PriceCache[float] = PriceCache()
        assert c.get("NOPE") is None

    def test_keys_and_len(self):
        c: PriceCache[int] = PriceCache(default_ttl=30)
        c.set("a", 1)
        c.set("b", 2)
        assert set(c.keys()) == {"a", "b"}
        assert len(c) == 2


class TestTtlExpiry:
    def test_expired_entry_is_evicted_on_get(self):
        c: PriceCache[str] = PriceCache(default_ttl=30)
        c.set("X", "v", ttl=0.05)
        assert c.get("X") == "v"  # still fresh
        time.sleep(0.06)
        assert c.get("X") is None  # expired → miss
        assert "X" not in c

    def test_default_ttl_used_when_omitted(self):
        c: PriceCache[int] = PriceCache(default_ttl=0.05)
        c.set("K", 1)
        assert c.get("K") == 1
        time.sleep(0.06)
        assert c.get("K") is None

    def test_zero_or_negative_ttl_does_not_cache(self):
        c: PriceCache[int] = PriceCache(default_ttl=30)
        c.set("A", 1, ttl=0)
        c.set("B", 2, ttl=-5)
        assert c.get("A") is None
        assert c.get("B") is None

    def test_get_does_not_mutate_other_entries(self):
        c: PriceCache[int] = PriceCache(default_ttl=30)
        c.set("a", 1)
        c.set("b", 2, ttl=0.05)
        time.sleep(0.06)
        assert c.get("b") is None
        assert c.get("a") == 1


class TestInvalidate:
    def test_invalidate_single_key(self):
        c: PriceCache[float] = PriceCache(default_ttl=30)
        c.set("AAPL", 1.0)
        c.set("MSFT", 2.0)
        c.invalidate("AAPL")
        assert c.get("AAPL") is None
        assert c.get("MSFT") == 2.0

    def test_invalidate_missing_key_is_noop(self):
        c: PriceCache[float] = PriceCache()
        c.invalidate("ghost")  # must not raise

    def test_invalidate_all_clears_everything(self):
        c: PriceCache[float] = PriceCache(default_ttl=30)
        c.set("a", 1.0)
        c.set("b", 2.0)
        c.invalidate_all()
        assert len(c) == 0
        assert c.get("a") is None


class TestBatch:
    def test_set_many_get_many(self):
        c: PriceCache[int] = PriceCache(default_ttl=30)
        c.set_many({"a": 1, "b": 2, "c": 3})
        got = c.get_many(["a", "c", "missing"])
        assert got == {"a": 1, "c": 3}

    def test_get_many_skips_expired(self):
        c: PriceCache[int] = PriceCache(default_ttl=30)
        c.set("fresh", 1)
        c.set("stale", 2, ttl=0.05)
        time.sleep(0.06)
        got = c.get_many(["fresh", "stale"])
        assert got == {"fresh": 1}
        assert "stale" not in c

    def test_set_many_zero_ttl_skips_cache(self):
        c: PriceCache[int] = PriceCache(default_ttl=30)
        c.set_many({"a": 1}, ttl=0)
        assert c.get("a") is None


class TestReusedKey:
    def test_overwrite_with_new_ttl(self):
        c: PriceCache[int] = PriceCache(default_ttl=30)
        c.set("k", 1, ttl=0.05)
        time.sleep(0.03)
        c.set("k", 2, ttl=30)  # refresh
        time.sleep(0.04)
        # original short ttl would have expired; refreshed value survives
        assert c.get("k") == 2
