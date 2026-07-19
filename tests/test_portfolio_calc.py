"""Unit tests for portfolio calculation helpers (pure functions)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_manager.services.portfolio_calc import (
    PortfolioSummary,
    compute_allocation,
    compute_nav,
    compute_pnl,
    compute_position_fields,
    cumulative_nav,
    position_value,
    simple_returns,
    summarize_portfolio,
)


def pos(qty: float, cost: float, price: float, asset_id="A") -> object:
    return position_value(
        quantity=Decimal(str(qty)),
        avg_cost_basis=Decimal(str(cost)),
        current_price=Decimal(str(price)),
        asset_id=asset_id,
    )


class TestPositionValue:
    def test_market_value_and_gain(self):
        pv = pos(10, 100, 150)
        assert pv.market_value == Decimal("1500")
        assert pv.unrealized_gain == Decimal("500")
        assert pv.unrealized_gain_pct == pytest.approx(0.5)

    def test_loss(self):
        pv = pos(10, 100, 80)
        assert pv.unrealized_gain == Decimal("-200")
        assert pv.unrealized_gain_pct == pytest.approx(-0.2)

    def test_zero_cost_basis(self):
        pv = pos(5, 0, 10)
        assert pv.unrealized_gain_pct == 0.0  # guarded
        assert pv.market_value == Decimal("50")

    def test_compute_position_fields_for_db(self):
        mv, gain, pct = compute_position_fields(
            quantity=Decimal("10"), avg_cost_basis=Decimal("100"), current_price=Decimal("150")
        )
        assert mv == Decimal("1500")
        assert gain == Decimal("500")
        assert isinstance(pct, Decimal)
        assert pct == Decimal("0.5000")


class TestNavAndPnl:
    def test_nav_sums_market_values(self):
        assert compute_nav([pos(10, 100, 150), pos(5, 50, 60)]) == Decimal("1800")

    def test_nav_empty(self):
        assert compute_nav([]) == Decimal("0")

    def test_pnl_aggregates(self):
        gain, pct = compute_pnl([pos(10, 100, 150), pos(5, 50, 60)])
        assert gain == Decimal("550")  # 500 + 50
        assert pct == pytest.approx(550 / 1250)

    def test_pnl_empty(self):
        gain, pct = compute_pnl([])
        assert gain == Decimal("0")
        assert pct == 0.0


class TestSummary:
    def test_summary_fields(self):
        s = summarize_portfolio([pos(10, 100, 150), pos(5, 50, 60)])
        assert isinstance(s, PortfolioSummary)
        assert s.nav == Decimal("1800")
        assert s.cost_basis == Decimal("1250")  # 1000 + 250
        assert s.unrealized_gain == Decimal("550")
        assert s.unrealized_gain_pct == pytest.approx(550 / 1250)
        assert s.position_count == 2

    def test_summary_empty(self):
        s = summarize_portfolio([])
        assert s.nav == Decimal("0")
        assert s.position_count == 0
        assert s.unrealized_gain_pct == 0.0


class TestAllocation:
    def test_allocation_by_sector(self):
        positions = [pos(10, 100, 200), pos(5, 100, 100), pos(2, 100, 300)]
        sectors = ["Tech", "Tech", "Energy"]
        alloc = compute_allocation(positions, keys=sectors)
        # nav = 2000 + 500 + 600 = 3100
        assert alloc["Tech"] == pytest.approx(2500 / 3100)
        assert alloc["Energy"] == pytest.approx(600 / 3100)

    def test_allocation_zero_nav(self):
        alloc = compute_allocation([pos(0, 100, 200)], keys=["Tech"])
        assert alloc == {"Tech": 0.0}

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            compute_allocation([pos(1, 1, 1)], keys=["A", "B"])


class TestReturns:
    def test_simple_returns(self):
        nav = [100.0, 110.0, 99.0]
        r = simple_returns(nav)
        assert r == pytest.approx([0.10, -0.10])

    def test_simple_returns_short_series(self):
        assert simple_returns([1.0]) == []
        assert simple_returns([]) == []

    def test_simple_returns_handles_zero_prev(self):
        # zero previous value → 0.0 (guarded, not inf)
        r = simple_returns([0.0, 10.0, 12.0])
        assert r == pytest.approx([0.0, 0.2])

    def test_cumulative_nav(self):
        rets = [0.10, 0.10]
        nav = cumulative_nav(rets, start_value=100.0)
        assert nav == pytest.approx([100.0, 110.0, 121.0])

    def test_cumulative_nav_empty(self):
        assert cumulative_nav([]) == [1.0]
