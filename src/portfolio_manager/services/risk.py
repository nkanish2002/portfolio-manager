"""Risk metrics engine.

Calculates: Sharpe, Sortino, Max Drawdown, VaR (parametric & historical),
Beta, Alpha (Jensen's), Treynor, Calmar, Ulcer Index.
"""

import math

import numpy as np
import pandas as pd


def calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.04) -> float:
    """Sharpe ratio = (R_p - R_f) / sigma_p, annualized.

    Args:
        returns: daily returns as percentage (e.g., 0.01 for 1%)
        risk_free_rate: annual risk-free rate (default 4%)
    """
    if returns.std() == 0 or returns.empty:
        return 0.0
    excess = returns - (risk_free_rate / 252)
    return float(excess.mean() / returns.std() * math.sqrt(252))


def calculate_sortino(returns: pd.Series, risk_free_rate: float = 0.04) -> float:
    """Sortino ratio = (R_p - R_f) / downside_deviation, annualized."""
    if returns.empty:
        return 0.0
    excess = returns - (risk_free_rate / 252)
    downside = returns[returns < 0]
    if downside.empty or downside.std() == 0:
        return 0.0
    downside_std = downside.std() * math.sqrt(252)
    result = (excess.mean() * 252) / downside_std
    return float(result) if not math.isnan(result) else 0.0


def calculate_max_drawdown(prices: pd.Series) -> dict:
    """Maximum drawdown from peak.

    Returns:
        dict with max_drawdown_pct, peak_date, trough_date, duration_days
    """
    if prices.empty or len(prices) < 2:
        return {"max_drawdown_pct": 0.0, "peak_date": None, "trough_date": None, "duration_days": 0}

    cumulative = prices / prices.cummax()
    drawdown = cumulative - 1
    max_dd = drawdown.min()

    # If no drawdown (max_dd >= 0), return early
    if max_dd >= -0.0001:  # Allow for floating point tolerance
        return {"max_drawdown_pct": 0.0, "peak_date": None, "trough_date": None, "duration_days": 0}

    # Find peak and trough dates
    trough_idx = drawdown.idxmin()
    peak_idx = prices[:trough_idx].idxmax()

    if hasattr(peak_idx, "date"):
        peak_date = peak_idx.date() if hasattr(peak_idx, "date") else str(peak_idx)
        trough_date = trough_idx.date() if hasattr(trough_idx, "date") else str(trough_idx)
        duration = (trough_idx - peak_idx).days if hasattr(trough_idx, "__sub__") else 0
    else:
        peak_date = str(peak_idx)
        trough_date = str(trough_idx)
        duration = 0

    return {
        "max_drawdown_pct": round(float(max_dd * 100), 2),
        "peak_date": peak_date,
        "trough_date": trough_date,
        "duration_days": duration,
    }


def calculate_var(
    returns: pd.Series, confidence: float = 0.95, portfolio_value: float = 1_000_000
) -> dict:
    """Value at Risk — both parametric and historical.

    Args:
        returns: daily returns (decimal, e.g., 0.01 for 1%)
        confidence: confidence level (default 95%)
        portfolio_value: current portfolio value

    Returns:
        dict with parametric and historical VaR
    """
    if returns.empty or returns.std() == 0:
        return {"parametric_var": 0.0, "historical_var": 0.0, "confidence_pct": confidence}

    # Parametric VaR (normal distribution assumption)
    z_score = abs(np.percentile(np.random.standard_normal(100000), (1 - confidence) * 100))
    daily_mean = returns.mean()
    daily_std = returns.std()
    parametric_daily_var = portfolio_value * (z_score * daily_std - daily_mean)

    # Historical VaR
    sorted_returns = returns.sort_values()
    historical_daily_var = abs(sorted_returns.iloc[int((1 - confidence) * len(sorted_returns))])

    # Annualized
    annualized_parametric = parametric_daily_var * math.sqrt(252)
    annualized_historical = portfolio_value * historical_daily_var * math.sqrt(252)

    return {
        "parametric_var_daily": round(float(max(0, parametric_daily_var)), 2),
        "parametric_var_annual": round(float(annualized_parametric), 2),
        "historical_var_daily": round(float(portfolio_value * historical_daily_var), 2),
        "historical_var_annual": round(float(annualized_historical), 2),
        "confidence_pct": confidence * 100,
    }


def calculate_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Beta = Cov(Rp, Rb) / Var(Rb)."""
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if aligned.empty:
        return 1.0  # Default to 1 (market-like)
    benchmark_variance = aligned[1].var()
    if benchmark_variance < 1e-10:  # Near-zero variance
        return 1.0
    covariance = aligned[0].cov(aligned[1])
    return round(float(covariance / benchmark_variance), 2)


def calculate_alpha(
    portfolio_returns: pd.Series, benchmark_returns: pd.Series, risk_free_rate: float = 0.04
) -> float:
    """Jensen's Alpha = Rp - [Rf + Beta * (Rb - Rf)]."""
    beta = calculate_beta(portfolio_returns, benchmark_returns)
    rp = portfolio_returns.mean() * 252
    rb = benchmark_returns.mean() * 252
    rf = risk_free_rate
    return round(float(rp - (rf + beta * (rb - rf))) * 100, 2)  # Percentage


def calculate_treynor(
    portfolio_returns: pd.Series, benchmark_returns: pd.Series, risk_free_rate: float = 0.04
) -> float:
    """Treynor ratio = (Rp - Rf) / Beta."""
    beta = calculate_beta(portfolio_returns, benchmark_returns)
    if beta == 0:
        return 0.0
    rp = portfolio_returns.mean() * 252
    rf = risk_free_rate
    return round(float((rp - rf) / beta), 2)


def calculate_calmar(returns: pd.Series, prices: pd.Series) -> float:
    """Calmar ratio = Annualized Return / Max Drawdown."""
    if returns.empty:
        return 0.0
    ann_return = (1 + returns.mean()) ** 252 - 1
    dd = calculate_max_drawdown(prices)
    if dd["max_drawdown_pct"] == 0:
        return 0.0
    return round(float(ann_return / abs(dd["max_drawdown_pct"] / 100)), 2)


def calculate_ulcer_index(prices: pd.Series) -> float:
    """Ulcer Index = sqrt(mean(drawdown^2))."""
    if prices.empty or len(prices) < 2:
        return 0.0
    max_price = prices.cummax()
    drawdown = ((prices - max_price) / max_price) * 100
    return round(float(np.sqrt((drawdown**2).mean())), 2)


def full_risk_report(
    returns: pd.Series, prices: pd.Series, benchmark_returns: pd.Series | None = None
) -> dict:
    """Calculate all risk metrics at once."""
    report = {
        "sharpe_ratio": round(calculate_sharpe(returns), 2),
        "sortino_ratio": round(calculate_sortino(returns), 2),
        "max_drawdown": calculate_max_drawdown(prices),
        "var": calculate_var(
            returns, portfolio_value=float(prices.iloc[-1]) if not prices.empty else 1_000_000
        ),
        "ulcer_index": calculate_ulcer_index(prices),
        "calmar_ratio": calculate_calmar(returns, prices),
    }

    if benchmark_returns is not None and not benchmark_returns.empty:
        report["beta"] = calculate_beta(returns, benchmark_returns)
        report["alpha"] = calculate_alpha(returns, benchmark_returns)
        report["treynor_ratio"] = calculate_treynor(returns, benchmark_returns)

    return report
