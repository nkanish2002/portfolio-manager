"""Benchmark comparison — excess returns, tracking error, information ratio.

Also exposes helpers to turn ``BenchmarkData`` rows (date + close) into a
return series aligned with the portfolio's return series.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

import numpy as np

from portfolio_manager.services.portfolio_calc import simple_returns


def returns_from_close_series(closes: Sequence[float | Decimal]) -> list[float]:
    """Daily simple returns from an ordered benchmark close-price series."""
    return simple_returns([float(c) for c in closes])


def align_series(
    portfolio_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> tuple[list[float], list[float]]:
    """Truncate both series to the shorter length (index-aligned)."""
    n = min(len(portfolio_returns), len(benchmark_returns))
    return list(portfolio_returns[:n]), list(benchmark_returns[:n])


def excess_returns(
    portfolio_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> list[float]:
    """Per-period ``portfolio - benchmark`` returns."""
    p, b = align_series(portfolio_returns, benchmark_returns)
    return [float(p[i] - b[i]) for i in range(len(p))]


def tracking_error(
    portfolio_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    periods: int = 252,
) -> float:
    """Annualized standard deviation of excess returns."""
    ex = np.asarray(excess_returns(portfolio_returns, benchmark_returns), dtype=float)
    if ex.size < 2:
        return 0.0
    return float(ex.std(ddof=1) * np.sqrt(periods))


def information_ratio(
    portfolio_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    periods: int = 252,
) -> float:
    """Annualized mean excess return / tracking error."""
    ex = np.asarray(excess_returns(portfolio_returns, benchmark_returns), dtype=float)
    if ex.size < 2:
        return 0.0
    te = float(ex.std(ddof=1))
    if te == 0:
        return 0.0
    mean_excess = float(ex.mean())
    return mean_excess / te * np.sqrt(periods)


def compare_to_benchmark(
    portfolio_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> dict[str, float]:
    """Bundle of benchmark-comparison metrics."""
    p, b = align_series(portfolio_returns, benchmark_returns)
    ex = excess_returns(p, b)
    ex_arr = np.asarray(ex, dtype=float)
    cumulative_excess = float(np.prod(1.0 + ex_arr) - 1.0) if ex_arr.size else 0.0
    return {
        "tracking_error": tracking_error(p, b),
        "information_ratio": information_ratio(p, b),
        "excess_return_annualized": float(np.mean(ex_arr) * 252) if ex_arr.size else 0.0,
        "cumulative_excess_return": cumulative_excess,
    }
