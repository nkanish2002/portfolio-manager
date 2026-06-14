"""Benchmark comparison service — portfolio vs benchmark metrics.

Calculates:
- Excess returns (portfolio − benchmark)
- Tracking error (std of excess returns)
- Information ratio (excess return / tracking error)
- Benchmark overlay data for visualization
- Correlation between portfolio and benchmark returns
"""


import numpy as np
import pandas as pd


def calculate_excess_returns(
    portfolio_returns: pd.Series, benchmark_returns: pd.Series
) -> pd.Series:
    """Excess returns = portfolio − benchmark."""
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    return (aligned[0] - aligned[1]).dropna()


def calculate_tracking_error(excess_returns: pd.Series, annualization: int = 252) -> float:
    """Tracking error = annualized std of excess returns."""
    if len(excess_returns) < 2:
        return 0.0
    return float(np.std(excess_returns, ddof=1) * np.sqrt(annualization))


def calculate_information_ratio(excess_returns: pd.Series, tracking_error: float) -> float:
    """Information ratio = mean(excess) / tracking error."""
    if tracking_error == 0 or len(excess_returns) < 2:
        return 0.0
    return float((excess_returns.mean() * 252) / tracking_error)


def calculate_benchmark_correlation(
    portfolio_returns: pd.Series, benchmark_returns: pd.Series
) -> float:
    """Pearson correlation between portfolio and benchmark returns."""
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    corr = aligned[0].corr(aligned[1])
    return round(float(corr), 4) if not pd.isna(corr) else 0.0


def generate_benchmark_overlay(portfolio_prices: pd.Series, benchmark_prices: pd.Series) -> dict:
    """Generate aligned price series for overlay chart."""
    portfolio_prices = portfolio_prices.copy()
    benchmark_prices = benchmark_prices.copy()

    # Normalize both to same starting point (100)
    start_p = float(portfolio_prices.iloc[0])
    start_b = float(benchmark_prices.iloc[0])

    portfolio_norm = (portfolio_prices / start_p * 100).round(2)
    benchmark_norm = (benchmark_prices / start_b * 100).round(2)

    # Align on common index
    common_idx = portfolio_norm.index.intersection(benchmark_norm.index)
    aligned_portfolio = portfolio_norm.loc[common_idx].reset_index()
    aligned_benchmark = benchmark_norm.loc[common_idx].reset_index()

    return {
        "dates": list(aligned_portfolio.iloc[:, 0].astype(str)),
        "portfolio": list(aligned_portfolio.iloc[:, 1]),
        "benchmark": list(aligned_benchmark.iloc[:, 1]),
    }


def generate_allocation_pie(positions: pd.DataFrame) -> dict:
    """Generate asset allocation pie chart data."""
    if positions.empty:
        return {"labels": [], "values": [], "colors": [], "total_value": 0}

    df = positions.copy()
    if "market_value" not in df.columns:
        df["market_value"] = df["quantity"] * df["price"]

    by_class = df.groupby("asset_class")["market_value"].sum().reset_index()
    by_class.columns = ["asset_class", "total_value"]

    total = float(by_class["total_value"].sum())
    if total == 0:
        return {"labels": [], "values": [], "colors": [], "total_value": 0}

    # Color palette
    colors = [
        "#FF6384",
        "#36A2EB",
        "#FFCE56",
        "#4BC0C0",
        "#9966FF",
        "#FF9F40",
        "#FF6384",
        "#C9CBCF",
    ]
    labels = by_class["asset_class"].tolist()
    values = by_class["total_value"].round(2).tolist()
    pie_colors = colors[: len(labels)]

    return {
        "labels": labels,
        "values": values,
        "colors": pie_colors,
        "total_value": round(total, 2),
    }


def generate_drawdown_chart(nav_series: pd.Series) -> dict:
    """Generate drawdown waterfall data."""
    if len(nav_series) < 2:
        return {"dates": [], "drawdown": [], "nav": []}

    cumulative = nav_series / nav_series.cummax()
    drawdown = ((cumulative - 1) * 100).round(2)
    dates = [str(d.date()) if hasattr(d, "date") else str(d) for d in nav_series.index]

    return {
        "dates": dates,
        "drawdown": list(drawdown),
        "nav": [round(float(v), 2) for v in nav_series],
    }


def calculate_risk_report(
    portfolio_returns: pd.Series, benchmark_returns: pd.Series | None = None
) -> dict:
    """Full risk report combining portfolio metrics with benchmark comparison."""
    from portfolio_manager.services.risk import (
        calculate_alpha,
        calculate_beta,
        calculate_calmar_ratio,
        calculate_max_drawdown,
        calculate_sharpe,
        calculate_sortino,
        calculate_treynor_ratio,
        calculate_ulcer_index,
        calculate_value_at_risk,
    )

    report = {
        "portfolio_returns_count": len(portfolio_returns),
    }

    # Basic metrics
    report["sharpe_ratio"] = round(calculate_sharpe(portfolio_returns), 2)
    report["sortino_ratio"] = round(calculate_sortino(portfolio_returns), 2)

    # Max drawdown
    nav = (1 + portfolio_returns).cumsum()
    nav.index = portfolio_returns.index
    mdd = calculate_max_drawdown(nav)
    report["max_drawdown"] = mdd

    # VaR
    var = calculate_value_at_risk(portfolio_returns)
    report["var_95"] = var

    if benchmark_returns is not None:
        # Benchmark comparison
        benchmark_nav = (1 + benchmark_returns).cumsum()
        benchmark_nav.index = benchmark_returns.index
        bm_mdd = calculate_max_drawdown(benchmark_nav)

        excess = calculate_excess_returns(portfolio_returns, benchmark_returns)
        tracking_error = calculate_tracking_error(excess)
        info_ratio = calculate_information_ratio(excess, tracking_error)
        correlation = calculate_benchmark_correlation(portfolio_returns, benchmark_returns)
        beta = calculate_beta(portfolio_returns, benchmark_returns)
        alpha = calculate_alpha(portfolio_returns, benchmark_returns)
        treynor = calculate_treynor_ratio(portfolio_returns, benchmark_returns)
        calmar = calculate_calmar_ratio(portfolio_returns, mdd["max_drawdown_pct"])

        report.update(
            {
                "benchmark_sharpe": round(calculate_sharpe(benchmark_returns), 2),
                "benchmark_sortino": round(calculate_sortino(benchmark_returns), 2),
                "benchmark_max_drawdown": round(bm_mdd["max_drawdown_pct"], 2),
                "excess_return": round(float(excess.sum() * 100), 2),
                "tracking_error": round(tracking_error, 2),
                "information_ratio": round(info_ratio, 2),
                "correlation": correlation,
                "beta": round(beta, 2),
                "alpha": round(alpha, 2),
                "treynor_ratio": round(treynor, 2),
                "calmar_ratio": round(calmar, 2),
            }
        )

    report["ulcer_index"] = round(calculate_ulcer_index(nav), 2)

    return report
