"""Unit tests for risk metric calculations (pure functions, no I/O)."""

from __future__ import annotations

import math

import pytest

from portfolio_manager.services.risk import (
    annualized_return,
    beta_alpha,
    calmar_ratio,
    compute_risk_metrics,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    treynor_ratio,
    ulcer_index,
    value_at_risk_historical,
    value_at_risk_parametric,
)

# ── Sharpe / Sortino ──────────────────────────────────────────────────────


class TestSharpe:
    def test_zero_returns_zero(self):
        assert sharpe_ratio([]) == 0.0
        assert sharpe_ratio([0.01]) == 0.0  # need >= 2

    def test_constant_positive_returns_zero_vol(self):
        # identical returns → std 0 → defined as 0 (not inf)
        assert sharpe_ratio([0.01, 0.01, 0.01]) == 0.0

    def test_positive_vol_positive_sharpe(self):
        r = [0.01, -0.005, 0.02, -0.01, 0.015]
        assert sharpe_ratio(r) > 0

    def test_sign_tracks_mean(self):
        r = [-0.01, -0.02, -0.005, -0.03, -0.01]
        assert sharpe_ratio(r) < 0


class TestSortino:
    def test_all_positive_returns_zero_downside(self):
        # no downside deviation → 0 (not inf)
        assert sortino_ratio([0.01, 0.02, 0.015]) == 0.0

    def test_sortino_geq_sharpe_for_mixed_returns(self):
        r = [0.01, -0.02, 0.03, -0.01, 0.02]
        assert sortino_ratio(r) >= sharpe_ratio(r)


# ── Max drawdown ──────────────────────────────────────────────────────────


class TestMaxDrawdown:
    def test_monotonic_increase_no_drawdown(self):
        mdd = max_drawdown([100, 110, 120, 130])
        assert mdd.value == 0.0
        assert mdd.trough_value == 130

    def test_known_drawdown(self):
        # peak 120 → trough 90 → -25%
        mdd = max_drawdown([100, 120, 90, 110])
        assert mdd.value == pytest.approx(-0.25)
        assert mdd.peak_value == 120
        assert mdd.trough_value == 90
        assert mdd.peak_index == 1
        assert mdd.trough_index == 2

    def test_empty_series(self):
        mdd = max_drawdown([])
        assert mdd.value == 0.0


# ── VaR ──────────────────────────────────────────────────────────────────


class TestVaR:
    def test_parametric_positive_for_risky_returns(self):
        r = [0.01, -0.03, 0.02, -0.02, 0.0, 0.01, -0.01]
        var = value_at_risk_parametric(r, portfolio_value=10000, confidence=0.95)
        assert var > 0  # some positive loss amount

    def test_parametric_zero_vol(self):
        assert value_at_risk_parametric([0.01, 0.01], 10000) == 0.0

    def test_historical_uses_percentile(self):
        # 10 returns, the 5th-percentile is the worst single value
        r = [0.01, 0.02, -0.01, 0.0, 0.03, -0.02, 0.005, -0.015, 0.01, 0.0]
        var = value_at_risk_historical(r, portfolio_value=10000, confidence=0.95)
        # worst (most negative) return magnitude * value
        assert var > 0
        assert var <= 10000 * 0.02  # bounded by the worst single-day loss

    def test_var_scales_with_position_size(self):
        r = [0.01, -0.03, 0.02, -0.02, 0.0]
        small = value_at_risk_parametric(r, 1000)
        large = value_at_risk_parametric(r, 10000)
        assert large == pytest.approx(small * 10, rel=0.01)


# ── Beta / Alpha ──────────────────────────────────────────────────────────


class TestBetaAlpha:
    def test_beta_one_for_identical_series(self):
        r = [0.01, -0.02, 0.03, 0.0, -0.01]
        beta, alpha = beta_alpha(r, r)
        assert beta == pytest.approx(1.0, abs=1e-9)
        assert alpha == pytest.approx(0.0, abs=1e-9)

    def test_beta_zero_for_constant_benchmark(self):
        beta, alpha = beta_alpha([0.01, 0.02, -0.01], [0.0, 0.0, 0.0])
        assert beta == 0.0
        assert alpha == pytest.approx(0.02 / 3, abs=1e-9)


# ── Treynor / Calmar / Ulcer ──────────────────────────────────────────────


class TestOtherRatios:
    def test_calmar_positive_return_negative_dd(self):
        assert calmar_ratio(0.10, -0.05) == pytest.approx(2.0)

    def test_calmar_no_drawdown(self):
        assert calmar_ratio(0.10, 0.0) == 0.0  # 0.0 dd → guard returns 0

    def test_calmar_positive_dd_returns_zero(self):
        assert calmar_ratio(0.10, 0.05) == 0.0

    def test_treynor_zero_beta(self):
        assert treynor_ratio([0.01, 0.02], [0.0, 0.0]) == 0.0

    def test_ulcer_zero_for_monotonic(self):
        assert ulcer_index([100, 110, 120]) == 0.0

    def test_ulcer_positive_with_drawdown(self):
        assert ulcer_index([100, 120, 90, 110]) > 0.0


# ── aggregate ──────────────────────────────────────────────────────────────


class TestAggregate:
    def test_compute_metrics_keys_without_benchmark(self):
        r = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005]
        m = compute_risk_metrics(r, portfolio_value=10000)
        assert set(m) == {
            "sharpe", "sortino", "max_drawdown", "var_95_parametric",
            "var_95_historical", "calmar", "ulcer_index", "annualized_return",
        }

    def test_compute_metrics_keys_with_benchmark(self):
        m = compute_risk_metrics(
            [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005],
            benchmark_returns=[0.005, -0.01, 0.01, 0.0, 0.015, -0.005, 0.002],
        )
        assert {"beta", "alpha", "treynor"}.issubset(m)

    def test_all_values_are_plain_floats(self):
        m = compute_risk_metrics([0.01, -0.02, 0.015], portfolio_value=1000)
        for v in m.values():
            assert isinstance(v, float)
            assert not math.isnan(v)

    def test_empty_returns(self):
        m = compute_risk_metrics([], portfolio_value=1000)
        assert m["max_drawdown"] == 0.0
        assert m["sharpe"] == 0.0


class TestAnnualizedReturn:
    def test_zero_returns(self):
        assert annualized_return([]) == 0.0

    def test_positive_growth(self):
        r = [0.01] * 252  # 1% daily for a year → ~12.2x → annualized ~11.2
        ar = annualized_return(r)
        assert ar > 0
        # 1.01**252 ≈ 12.27 → annualized ≈ 11.27
        assert ar == pytest.approx(1.01**252 - 1, rel=1e-6)
