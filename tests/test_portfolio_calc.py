"""Tests for portfolio calculations."""
import numpy as np
import pandas as pd
import pytest

from portfolio_manager.services.portfolio_calc import (
    calculate_portfolio_value,
    calculate_returns,
    build_price_series,
)


class TestPortfolioValue:
    def test_single_position(self):
        positions = pd.DataFrame({
            "symbol": ["AAPL"],
            "quantity": [100],
            "price": [150.0],
            "asset_class": ["equity"],
            "cost_basis": [140.0],
        })
        result = calculate_portfolio_value(positions)
        assert result["total_value"] == 15000.0
        assert result["total_gain"] == 1000.0
        assert result["total_gain_pct"] == pytest.approx(7.14, abs=0.01)
        assert result["position_count"] == 1

    def test_multiple_positions(self):
        positions = pd.DataFrame({
            "symbol": ["AAPL", "GOOGL"],
            "quantity": [100, 50],
            "price": [150.0, 2800.0],
            "asset_class": ["equity", "etf"],
            "cost_basis": [140.0, 2700.0],
        })
        result = calculate_portfolio_value(positions)
        assert result["total_value"] == 155000.0  # 100*150 + 50*2800 = 15000 + 140000
        assert result["position_count"] == 2
        assert "equity" in result["by_class"]
        assert "etf" in result["by_class"]

    def test_empty_positions(self):
        positions = pd.DataFrame(columns=["symbol", "quantity", "price", "asset_class", "cost_basis"])
        result = calculate_portfolio_value(positions)
        assert result["total_value"] == 0.0
        assert result["position_count"] == 0

    def test_allocation_percentages(self):
        positions = pd.DataFrame({
            "symbol": ["AAPL", "MSFT"],
            "quantity": [100, 100],
            "price": [100.0, 200.0],
            "asset_class": ["equity", "equity"],
            "cost_basis": [90.0, 180.0],
        })
        result = calculate_portfolio_value(positions)
        alloc = {row["symbol"]: row["allocation_pct"] for row in result["allocation_pct"]}
        assert alloc["AAPL"] == pytest.approx(33.33, abs=0.01)
        assert alloc["MSFT"] == pytest.approx(66.67, abs=0.01)


class TestReturns:
    def test_simple_returns(self):
        prices = [100, 105, 110, 108, 115]
        result = calculate_returns(prices)
        assert result["total_return_pct"] == pytest.approx(15.0, abs=0.1)
        assert "annualized_return_pct" in result
        assert "volatility" in result

    def test_short_series(self):
        prices = [100]
        result = calculate_returns(prices)
        assert result["total_return_pct"] == 0.0
        assert result["annualized_return_pct"] is None

    def test_period_returns(self):
        # Generate 1 year of daily data
        np.random.seed(42)
        daily_returns = np.random.normal(0.0005, 0.01, 252)
        prices = [100]
        for r in daily_returns:
            prices.append(prices[-1] * (1 + r))
        result = calculate_returns(prices)
        assert "1w_return_pct" in result
        assert "1m_return_pct" in result
        assert "1y_return_pct" in result


class TestPriceSeries:
    def test_build_series(self):
        transactions = [
            {"date": "2024-01-01", "amount": 10000},
            {"date": "2024-02-01", "amount": -2000},
            {"date": "2024-03-01", "amount": 5000},
        ]
        result = build_price_series(transactions, benchmark="SPY")
        assert "portfolio" in result
        assert "benchmark" in result
        assert result["benchmark"] == "SPY"
        assert len(result["portfolio"]) == 3
