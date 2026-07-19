"""Benchmark-comparison + classification tests."""

from __future__ import annotations

import pytest

from portfolio_manager.services.benchmark import (
    compare_to_benchmark,
    excess_returns,
    information_ratio,
    tracking_error,
)
from portfolio_manager.services.classification import (
    bucketize,
    classify_asset,
    infer_region,
)


class TestExcessReturns:
    def test_per_period_difference(self):
        ex = excess_returns([0.01, 0.02, -0.01], [0.005, 0.01, 0.0])
        assert ex == pytest.approx([0.005, 0.01, -0.01])

    def test_aligns_to_shorter(self):
        ex = excess_returns([0.01, 0.02, 0.03], [0.01, 0.02])
        assert len(ex) == 2


class TestTrackingError:
    def test_zero_when_identical(self):
        assert tracking_error([0.01, 0.02, -0.01], [0.01, 0.02, -0.01]) == 0.0

    def test_positive_when_different(self):
        te = tracking_error([0.01, -0.02, 0.03, 0.0, 0.01], [0.0, 0.0, 0.0, 0.0, 0.0])
        assert te > 0.0

    def test_short_series_zero(self):
        assert tracking_error([0.01], [0.01]) == 0.0


class TestInformationRatio:
    def test_zero_for_identical(self):
        assert information_ratio([0.01, 0.02, -0.01], [0.01, 0.02, -0.01]) == 0.0

    def test_positive_when_portfolio_beats_benchmark(self):
        ir = information_ratio(
            [0.02, 0.03, 0.01, 0.02, 0.015], [0.01, 0.01, 0.0, 0.005, 0.005]
        )
        assert ir > 0.0

    def test_sign_tracks_excess(self):
        ir = information_ratio(
            [0.0, 0.0, 0.0, 0.0, 0.0], [0.01, 0.02, 0.01, 0.015, 0.005]
        )
        assert ir < 0.0


class TestCompareBundle:
    def test_keys(self):
        m = compare_to_benchmark([0.01, 0.02, -0.01, 0.0, 0.02], [0.005, 0.01, 0.0, 0.005, 0.01])
        assert set(m) == {
            "tracking_error", "information_ratio",
            "excess_return_annualized", "cumulative_excess_return",
        }
        # all plain floats
        for v in m.values():
            assert isinstance(v, float)


class TestClassification:
    def test_explicit_sector_region(self):
        c = classify_asset(sector="Technology", region="United States", symbol="AAPL")
        assert c == {"sector": "Technology", "region": "United States"}

    def test_infer_region_us(self):
        assert infer_region("AAPL") == "United States"
        assert infer_region("MSFT") == "United States"

    def test_infer_region_international(self):
        assert infer_region("NESN.SW") == "Europe"
        assert infer_region("0700.HK") == "Asia"

    def test_defaults_to_unknown_sector(self):
        c = classify_asset(symbol="XYZ")
        assert c["sector"] == "Unknown"
        assert c["region"] == "United States"

    def test_bucketize(self):
        assert bucketize(["Tech", "Tech", "Energy", "Tech"]) == {"Tech": 3, "Energy": 1}
