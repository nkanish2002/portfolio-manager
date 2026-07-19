"""Risk metric calculations — the 9 metrics shown on the analytics dashboard.

All functions accept plain lists/arrays of **periodic returns** (e.g. daily
simple returns) or **NAV/price series** where noted. Inputs are floats; model
``Decimal`` values should be cast to ``float`` at the call site. Annualization
assumes 252 trading days. Every function is pure (no I/O) so it is trivially
unit-testable.

Metrics: Sharpe, Sortino, Max Drawdown, VaR (parametric + historical),
Beta, Alpha (CAPM), Treynor, Calmar, Ulcer Index.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

TRADING_DAYS = 252


# ── helpers ──────────────────────────────────────────────────────────────


def _to_array(x: Sequence[float]) -> np.ndarray:
    arr = np.asarray([float(v) for v in x], dtype=float)
    return arr


def _mean(arr: np.ndarray) -> float:
    return float(arr.mean()) if arr.size else 0.0


def _std(arr: np.ndarray, ddof: int = 1) -> float:
    if arr.size < ddof + 1:
        return 0.0
    return float(arr.std(ddof=ddof))


# ── ratio metrics ────────────────────────────────────────────────────────


def sharpe_ratio(
    returns: Sequence[float], risk_free: float = 0.0, periods: int = TRADING_DAYS
) -> float:
    """Annualized Sharpe ratio (excess return over risk-free per unit vol)."""
    arr = _to_array(returns)
    if arr.size < 2:
        return 0.0
    excess = arr - risk_free / periods
    std = _std(excess)
    if std == 0:
        return 0.0
    return (excess.mean() / std) * np.sqrt(periods)


def sortino_ratio(
    returns: Sequence[float],
    risk_free: float = 0.0,
    target: float = 0.0,
    periods: int = TRADING_DAYS,
) -> float:
    """Annualized Sortino ratio — uses downside deviation only."""
    arr = _to_array(returns)
    if arr.size < 2:
        return 0.0
    excess = arr - (risk_free + target) / periods
    downside = np.minimum(excess, 0.0)
    # downside std (population) over negative returns only
    downside_dev = np.sqrt((downside**2).mean()) if arr.size else 0.0
    if downside_dev == 0:
        return 0.0
    return (excess.mean() / downside_dev) * np.sqrt(periods)


def treynor_ratio(
    portfolio_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    risk_free: float = 0.0,
    periods: int = TRADING_DAYS,
) -> float:
    """Annualized excess return per unit of systematic risk (beta)."""
    beta, _ = beta_alpha(portfolio_returns, benchmark_returns)
    if beta == 0:
        return 0.0
    arr = _to_array(portfolio_returns)
    if arr.size == 0:
        return 0.0
    excess = arr.mean() - risk_free / periods
    return float(excess / beta * np.sqrt(periods))


def calmar_ratio(
    annualized_return: float, max_drawdown: float, periods: int = TRADING_DAYS
) -> float:
    """Annualized return divided by absolute max drawdown."""
    if max_drawdown >= 0:
        # no (positive) drawdown → Calmar is undefined; report 0.0
        return 0.0
    return float(annualized_return / abs(max_drawdown))


# ── drawdown metrics ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class MaxDrawdown:
    """Result of a max-drawdown computation over a NAV/price series."""

    value: float  # the drawdown as a fraction (<= 0), e.g. -0.083 == -8.3%
    peak_index: int
    trough_index: int
    peak_value: float
    trough_value: float


def max_drawdown(nav: Sequence[float]) -> MaxDrawdown:
    """Largest peak-to-trough decline as a fraction (negative or 0)."""
    arr = _to_array(nav)
    if arr.size == 0:
        return MaxDrawdown(0.0, 0, 0, 0.0, 0.0)
    if arr.size == 1:
        return MaxDrawdown(0.0, 0, 0, float(arr[0]), float(arr[0]))

    running_max = np.maximum.accumulate(arr)
    drawdown = (arr - running_max) / running_max  # <= 0
    trough_idx = int(np.argmin(drawdown))
    peak_idx = int(np.argmax(arr[: trough_idx + 1])) if trough_idx > 0 else 0
    value = float(drawdown[trough_idx])
    if value == 0.0:
        # no drawdown → trough/peak collapse to the final (highest) point
        last = arr.size - 1
        return MaxDrawdown(0.0, last, last, float(arr[last]), float(arr[last]))
    return MaxDrawdown(
        value=value,
        peak_index=peak_idx,
        trough_index=trough_idx,
        peak_value=float(arr[peak_idx]),
        trough_value=float(arr[trough_idx]),
    )


def ulcer_index(nav: Sequence[float]) -> float:
    """Ulcer Index — sqrt(mean(drawdown_percent²)). Lower is better."""
    arr = _to_array(nav)
    if arr.size < 2:
        return 0.0
    running_max = np.maximum.accumulate(arr)
    drawdown_pct = (arr - running_max) / running_max * 100.0  # in percent
    return float(np.sqrt((drawdown_pct**2).mean()))


# ── value at risk ─────────────────────────────────────────────────────────


def value_at_risk_parametric(
    returns: Sequence[float],
    portfolio_value: float,
    confidence: float = 0.95,
) -> float:
    """Parametric (Gaussian) VaR in currency units (a positive loss amount)."""
    arr = _to_array(returns)
    if arr.size < 2:
        return 0.0
    # z-score for the confidence level (one-tailed)
    z = _z_score(confidence)
    mean = arr.mean()
    std = _std(arr)
    if std == 0:
        return 0.0
    # worst-case return at this confidence; VaR as a positive loss
    var_return = -(mean - z * std)
    return float(max(0.0, var_return) * portfolio_value)


def value_at_risk_historical(
    returns: Sequence[float],
    portfolio_value: float,
    confidence: float = 0.95,
) -> float:
    """Historical (empirical percentile) VaR in currency units."""
    arr = _to_array(returns)
    if arr.size < 2:
        return 0.0
    percentile = (1.0 - confidence) * 100.0  # left tail
    worst = float(np.percentile(arr, percentile))
    return float(max(0.0, -worst) * portfolio_value)


def _z_score(confidence: float) -> float:
    """Inverse-normal z for a one-tailed confidence level (no scipy dep)."""
    # Abramowitz & Stegun approximation for the inverse CDF of N(0,1).
    if confidence <= 0.0:
        return 0.0
    if confidence >= 1.0:
        return 4.0
    p = confidence
    # one-tailed upper critical value: P(Z <= z) = confidence (z > 0 for c > 0.5)
    if p <= 0.5:
        q = p
        sign = -1.0  # lower tail → negative z
    else:
        q = 1.0 - p
        sign = 1.0  # upper tail → positive z
    t = np.sqrt(-2.0 * np.log(q))
    cc = [2.515517, 0.802853, 0.010328]
    dd = [1.432788, 0.189269, 0.001308]
    z = t - (cc[0] + cc[1] * t + cc[2] * t * t) / (1.0 + dd[0] * t + dd[1] * t * t + dd[2] * t**3)
    return sign * float(z)


# ── CAPM beta / alpha ────────────────────────────────────────────────────


def beta_alpha(
    portfolio_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> tuple[float, float]:
    """CAPM beta and (periodic) alpha vs a benchmark.

    Returns ``(beta, alpha)`` where alpha is the periodic intercept
    (annualize by multiplying by ``periods`` at the call site).
    """
    rp = _to_array(portfolio_returns)
    rb = _to_array(benchmark_returns)
    n = min(rp.size, rb.size)
    if n < 2:
        return 0.0, 0.0
    rp = rp[:n]
    rb = rb[:n]
    var_b = float(np.var(rb, ddof=1))
    if var_b == 0:
        return 0.0, float(rp.mean())
    cov = float(np.cov(rp, rb, ddof=1)[0, 1])
    beta = cov / var_b
    alpha = float(rp.mean() - beta * rb.mean())
    return beta, alpha


# ── aggregate ────────────────────────────────────────────────────────────


def annualized_return(returns: Sequence[float], periods: int = TRADING_DAYS) -> float:
    """Geometric annualized return from a periodic return series."""
    arr = _to_array(returns)
    if arr.size == 0:
        return 0.0
    growth = float(np.prod(1.0 + arr))
    if growth <= 0:
        return -1.0  # total loss
    years = arr.size / periods
    if years == 0:
        return 0.0
    return float(growth ** (1.0 / years) - 1.0)


def compute_risk_metrics(
    portfolio_returns: Sequence[float],
    benchmark_returns: Sequence[float] | None = None,
    *,
    portfolio_value: float = 1.0,
    nav_series: Sequence[float] | None = None,
    risk_free: float = 0.0,
    periods: int = TRADING_DAYS,
) -> dict[str, float]:
    """Compute the full dashboard risk-metric bundle.

    ``nav_series`` (optional) is used for drawdown-based metrics (Max DD,
    Calmar, Ulcer). If omitted, the NAV is reconstructed from cumulative
    compounding of ``portfolio_returns``.
    """
    arr = _to_array(portfolio_returns)
    if nav_series is None:
        nav = np.cumprod(1.0 + arr) if arr.size else np.array([1.0])
        nav = np.insert(nav, 0, 1.0) if arr.size else nav
    else:
        nav = _to_array(nav_series)

    mdd = max_drawdown(nav)
    ann_ret = annualized_return(arr, periods)

    metrics: dict[str, float] = {
        "sharpe": float(sharpe_ratio(arr, risk_free=risk_free, periods=periods)),
        "sortino": float(sortino_ratio(arr, risk_free=risk_free, periods=periods)),
        "max_drawdown": float(mdd.value),
        "var_95_parametric": float(value_at_risk_parametric(arr, portfolio_value, 0.95)),
        "var_95_historical": float(value_at_risk_historical(arr, portfolio_value, 0.95)),
        "calmar": float(calmar_ratio(ann_ret, mdd.value, periods)),
        "ulcer_index": float(ulcer_index(nav)),
        "annualized_return": float(ann_ret),
    }

    if benchmark_returns is not None:
        beta, alpha = beta_alpha(arr, benchmark_returns)
        metrics["beta"] = float(beta)
        metrics["alpha"] = float(alpha * periods)  # annualized
        metrics["treynor"] = float(treynor_ratio(arr, benchmark_returns, risk_free, periods))

    return metrics
