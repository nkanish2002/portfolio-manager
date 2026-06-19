"""Tests for the chart_data module (presentation-layer chart helpers)."""

import pandas as pd

from portfolio_manager.services.chart_data import generate_monthly_returns_heatmap


class TestMonthlyReturnsHeatmap:
    """generate_monthly_returns_heatmap should mirror charts._generate_monthly_from_nav."""

    def test_insufficient_data_under_5_points(self):
        df = pd.DataFrame(
            {"nav": [100, 101, 102]},
            index=pd.date_range("2024-01-01", periods=3, freq="D"),
        )

        result = generate_monthly_returns_heatmap(df)

        assert result["insufficient_data"] is True
        assert result["years"] == []
        assert result["months"] == []

    def test_missing_nav_column_is_insufficient(self):
        df = pd.DataFrame(
            {"price": [100, 101, 102, 103, 104, 105]},
            index=pd.date_range("2024-01-01", periods=6, freq="D"),
        )

        result = generate_monthly_returns_heatmap(df)

        assert result["insufficient_data"] is True

    def test_sufficient_data_returns_values(self):
        df = pd.DataFrame(
            {"nav": list(range(100, 200))},
            index=pd.date_range("2024-01-01", periods=100, freq="D"),
        )

        result = generate_monthly_returns_heatmap(df)

        assert result["insufficient_data"] is False
        assert len(result["years"]) > 0
        assert len(result["months"]) > 0
        assert len(result["values"]) > 0
