"""Tests for the risk metrics engine."""
import numpy as np
import pandas as pd
import pytest

from portfolio_manager.services.risk import (
    calculate_sharpe,
    calculate_sortino,
    calculate_max_drawdown,
    calculate_var,
    calculate_beta,
    calculate_alpha,
    calculate_treynor,
    calculate_calmar,
    calculate_ulcer_index,
    full_risk_report,
)


class TestSharpeRatio:
    def test_positive_returns(self):
        returns = pd.Series([0.01, 0.02, 0.01, 0.03, 0.02])
        result = calculate_sharpe(returns)
        assert result > 0

    def test_negative_returns(self):
        returns = pd.Series([-0.01, -0.02, -0.01, -0.03, -0.02])
        result = calculate_sharpe(returns)
        assert result < 0

    def test_zero_volatility(self):
        returns = pd.Series([0.01, 0.01, 0.01, 0.01, 0.01])
        result = calculate_sharpe(returns)
        assert result == 0.0

    def test_empty_series(self):
        returns = pd.Series([])
        result = calculate_sharpe(returns)
        assert result == 0.0


class TestSortinoRatio:
    def test_sortino_ratio(self):
        returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.02])
        result = calculate_sortino(returns)
        # Just verify it returns a float (can be positive or negative depending on data)
        assert isinstance(result, float)

    def test_no_downside_returns(self):
        returns = pd.Series([0.01, 0.02, 0.01, 0.03, 0.02])
        result = calculate_sortino(returns)
        assert result == 0.0

    def test_empty_series(self):
        returns = pd.Series([])
        result = calculate_sortino(returns)
        assert result == 0.0


class TestMaxDrawdown:
    def test_normal_drawdown(self):
        prices = pd.Series([100, 105, 102, 98, 100, 103])
        result = calculate_max_drawdown(prices)
        assert result["max_drawdown_pct"] < 0
        assert result["peak_date"] is not None
        assert result["trough_date"] is not None

    def test_no_drawdown(self):
        prices = pd.Series([100, 101, 102, 103, 104])
        result = calculate_max_drawdown(prices)
        assert result["max_drawdown_pct"] == 0.0

    def test_single_price(self):
        prices = pd.Series([100])
        result = calculate_max_drawdown(prices)
        assert result["max_drawdown_pct"] == 0.0

    def test_empty_series(self):
        prices = pd.Series([])
        result = calculate_max_drawdown(prices)
        assert result["max_drawdown_pct"] == 0.0


class TestValueAtRisk:
    def test_normal_var(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = calculate_var(returns, portfolio_value=100000)
        assert result["parametric_var_daily"] >= 0
        assert result["historical_var_daily"] >= 0

    def test_empty_returns(self):
        returns = pd.Series([])
        result = calculate_var(returns)
        assert result["parametric_var"] == 0.0

    def test_zero_volatility(self):
        returns = pd.Series([0.001] * 50)
        result = calculate_var(returns)
        assert result["parametric_var"] == 0.0


class TestBeta:
    def test_beta_returns_float(self):
        portfolio_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        benchmark_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = calculate_beta(portfolio_returns, benchmark_returns)
        assert isinstance(result, float)

    def test_zero_variance_benchmark(self):
        portfolio_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        benchmark_returns = pd.Series([0.001] * 100)
        result = calculate_beta(portfolio_returns, benchmark_returns)
        # Should return 1.0 (default market-like) when benchmark has no variance
        assert result == 1.0


class TestAlpha:
    def test_positive_alpha(self):
        portfolio_returns = pd.Series(np.random.normal(0.002, 0.02, 100))
        benchmark_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = calculate_alpha(portfolio_returns, benchmark_returns)
        assert isinstance(result, float)


class TestTreynorRatio:
    def test_normal_treynor(self):
        portfolio_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        benchmark_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        result = calculate_treynor(portfolio_returns, benchmark_returns)
        assert isinstance(result, float)


class TestCalmarRatio:
    def test_normal_calmar(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        prices = pd.Series([100 * (1 + r) for r in returns])
        result = calculate_calmar(returns, prices)
        assert isinstance(result, float)


class TestUlcerIndex:
    def test_normal_ulcer(self):
        prices = pd.Series([100, 102, 99, 101, 103, 98, 100])
        result = calculate_ulcer_index(prices)
        assert result >= 0

    def test_single_price(self):
        prices = pd.Series([100])
        result = calculate_ulcer_index(prices)
        assert result == 0.0

    def test_empty_series(self):
        prices = pd.Series([])
        result = calculate_ulcer_index(prices)
        assert result == 0.0


class TestFullRiskReport:
    def test_full_report_with_benchmark(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        prices = pd.Series([100 * (1 + r) for r in returns])
        benchmark_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        report = full_risk_report(returns, prices, benchmark_returns)
        assert "sharpe_ratio" in report
        assert "sortino_ratio" in report
        assert "max_drawdown" in report
        assert "var" in report
        assert "ulcer_index" in report
        assert "calmar_ratio" in report
        assert "beta" in report
        assert "alpha" in report
        assert "treynor_ratio" in report

    def test_full_report_without_benchmark(self):
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        prices = pd.Series([100 * (1 + r) for r in returns])
        report = full_risk_report(returns, prices)
        assert "sharpe_ratio" in report
        assert "beta" not in report
        assert "alpha" not in report
