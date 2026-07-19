"""NAV history builder tests — replay transactions, mark to market."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_manager.services.nav_history import build_nav_history


def _txn(t, asset, qty, price, when, fees=0):
    return {
        "asset_id": asset,
        "type": t,
        "quantity": Decimal(str(qty)),
        "price": Decimal(str(price)),
        "fees": Decimal(str(fees)),
        "trade_date": when,
    }


class TestBuildNavHistory:
    async def test_empty_returns_empty(self):
        assert build_nav_history([], price_provider=lambda *a: Decimal("1")) == []

    async def test_buy_then_hold(self):
        day1 = datetime(2026, 1, 2, tzinfo=UTC)
        day2 = datetime(2026, 1, 3, tzinfo=UTC)
        txns = [_txn("buy", "AAPL", 10, 100, day1)]
        prices = {("AAPL", day1.date()): Decimal("100"), ("AAPL", day2.date()): Decimal("110")}
        points = build_nav_history(txns, price_provider=lambda a, d: prices.get((a, d)))
        assert len(points) == 1
        assert points[0].nav == pytest.approx(0.0)  # buy: cash -1000 + holdings 1000 = net 0
        # cash went -1000, holdings +1000 → nav 0 at buy; then no further points (no day2 txn)

    async def test_nav_grows_with_price(self):
        d1 = datetime(2026, 1, 2, tzinfo=UTC)
        d2 = datetime(2026, 1, 3, tzinfo=UTC)
        txns = [_txn("buy", "AAPL", 10, 100, d1), _txn("buy", "AAPL", 0, 0, d2)]
        prices = {("AAPL", d1.date()): Decimal("100"), ("AAPL", d2.date()): Decimal("120")}
        points = build_nav_history(txns, price_provider=lambda a, d: prices.get((a, d)))
        # point at d1: cash -1000 + 10*100 = 0 ; point at d2: cash -1000 + 10*120 = 200
        assert len(points) == 2
        assert points[0].nav == pytest.approx(0.0)
        assert points[1].nav == pytest.approx(200.0)
        assert points[1].holdings_value == pytest.approx(1200.0)

    async def test_missing_price_skips_point(self):
        d1 = datetime(2026, 1, 2, tzinfo=UTC)
        d2 = datetime(2026, 1, 3, tzinfo=UTC)
        txns = [_txn("buy", "AAPL", 5, 100, d1), _txn("buy", "AAPL", 0, 0, d2)]
        # price only on d2 → d1 skipped, d2 included
        prices = {("AAPL", d2.date()): Decimal("100")}
        points = build_nav_history(txns, price_provider=lambda a, d: prices.get((a, d)))
        assert len(points) == 1
        assert points[0].date == d2.date()

    async def test_sell_reduces_holdings(self):
        d1 = datetime(2026, 1, 2, tzinfo=UTC)
        d2 = datetime(2026, 1, 3, tzinfo=UTC)
        txns = [_txn("buy", "X", 10, 100, d1), _txn("sell", "X", 4, 110, d2)]
        prices = {("X", d1.date()): Decimal("100"), ("X", d2.date()): Decimal("110")}
        points = build_nav_history(txns, price_provider=lambda a, d: prices.get((a, d)))
        # d1: cash -1000 + 1000 = 0 ; d2: cash -1000+440 = -560, holdings 6*110=660 → nav 100
        assert points[1].nav == pytest.approx(100.0)
        assert points[1].cash == pytest.approx(-560.0)
