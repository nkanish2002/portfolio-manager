"""Chart data generation services for Plotly visualizations.

Provides data functions for:
- NAV (Net Asset Value) growth chart
- Portfolio allocation pie chart
- Drawdown waterfall chart
- Benchmark comparison overlay
- Returns distribution histogram
"""


import numpy as np
import pandas as pd


def generate_nav_chart(
    position_history: pd.DataFrame, benchmark_history: pd.DataFrame = None
) -> dict:
    """Generate NAV (Net Asset Value) growth chart data.

    Args:
        position_history: DataFrame with date index and 'nav' column
        benchmark_history: Optional DataFrame with date index and 'nav' column

    Returns:
        dict with dates, portfolio_nav, benchmark_nav (if provided)
    """
    if position_history.empty:
        return {"dates": [], "portfolio_nav": [], "benchmark_nav": None}

    # Normalize NAV to start at 100
    start_nav = float(position_history["nav"].iloc[0])
    portfolio_norm = (position_history["nav"] / start_nav * 100).round(2)

    dates = [str(d.date()) if hasattr(d, "date") else str(d) for d in position_history.index]

    result = {
        "dates": dates,
        "portfolio_nav": list(portfolio_norm),
        "benchmark_nav": None,
    }

    if benchmark_history is not None and not benchmark_history.empty:
        bm_start = float(benchmark_history["nav"].iloc[0])
        bm_norm = (benchmark_history["nav"] / bm_start * 100).round(2)
        # Align on common dates
        bm_aligned = bm_norm.loc[portfolio_norm.index].dropna()
        result["benchmark_nav"] = list(bm_aligned)

    return result


def generate_returns_distribution(position_history: pd.DataFrame) -> dict:
    """Generate returns distribution histogram data."""
    if "nav" not in position_history.columns or len(position_history) < 2:
        return {"bins": [], "counts": [], "mean_return": 0.0, "std_return": 0.0}

    returns = position_history["nav"].pct_change().dropna()
    if returns.empty:
        return {"bins": [], "counts": [], "mean_return": 0.0, "std_return": 0.0}

    # Calculate histogram bins
    hist, bin_edges = np.histogram(returns, bins=30)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    return {
        "bins": [round(float(b), 6) for b in bin_centers],
        "counts": [int(c) for c in hist],
        "mean_return": round(float(returns.mean() * 100), 4),  # Percentage
        "std_return": round(float(returns.std() * 100), 4),  # Percentage
    }


def generate_monthly_returns_heatmap(position_history: pd.DataFrame) -> dict:
    """Generate monthly returns heatmap data."""
    if "nav" not in position_history.columns or len(position_history) < 60:
        return {"years": [], "months": [], "values": [], "labels": []}

    nav = position_history["nav"]
    nav.index = pd.to_datetime(nav.index)

    # Group by year and month
    nav["year"] = nav.index.year
    nav["month"] = nav.index.month
    nav["month_name"] = nav.index.strftime("%b")

    monthly_returns = nav["nav"].pct_change().groupby([nav["year"], nav["month"]]).last()
    monthly_returns = monthly_returns.unstack("month")

    # Filter to last 36 months
    if len(monthly_returns) > 36:
        monthly_returns = monthly_returns.tail(36)

    years = [int(y) for y in monthly_returns.index]
    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    # Select relevant months
    present_months = [m for m in monthly_returns.columns if m <= 12]
    present_month_names = [month_names[m - 1] for m in present_months]

    values = monthly_returns[present_months].fillna(0).values.tolist()
    values_pct = [[round(float(v) * 100, 2) for v in row] for row in values]

    return {
        "years": years,
        "months": present_month_names,
        "values": values_pct,
        "labels": [f"{year} {month}" for year in years for month in present_month_names],
    }


def generate_benchmark_comparison(portfolio_nav: pd.Series, benchmark_nav: pd.Series) -> dict:
    """Generate benchmark comparison data with overlay chart."""
    if portfolio_nav.empty or benchmark_nav.empty:
        return {"dates": [], "portfolio": [], "benchmark": [], "excess": []}

    # Normalize to 100
    port_norm = (portfolio_nav / float(portfolio_nav.iloc[0]) * 100).round(2)
    bm_norm = (benchmark_nav / float(benchmark_nav.iloc[0]) * 100).round(2)

    # Align on common dates
    common_idx = port_norm.index.intersection(bm_norm.index)
    port_aligned = port_norm.loc[common_idx]
    bm_aligned = bm_norm.loc[common_idx]

    excess = (port_aligned - bm_aligned).round(2)

    dates = [str(d.date()) if hasattr(d, "date") else str(d) for d in common_idx]

    return {
        "dates": dates,
        "portfolio": list(port_aligned),
        "benchmark": list(bm_aligned),
        "excess": list(excess),
    }
