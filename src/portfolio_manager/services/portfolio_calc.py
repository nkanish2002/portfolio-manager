"""Portfolio calculations — NAV, returns, P&L, allocation."""

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd


def calculate_portfolio_value(positions: pd.DataFrame) -> dict:
    """Calculate total portfolio value and breakdown.

    Args:
        positions: DataFrame with columns [symbol, quantity, price, asset_class, cost_basis]

    Returns:
        dict with total_value, by_class, top_holdings, allocation_pct
    """
    positions = positions.copy()
    positions["market_value"] = positions["quantity"] * positions["price"]
    positions["cost_basis_total"] = positions["quantity"] * positions["cost_basis"]
    positions["gain"] = positions["market_value"] - positions["cost_basis_total"]

    total_value = positions["market_value"].sum()
    total_cost = positions["cost_basis_total"].sum()

    by_class = positions.groupby("asset_class").agg(
        market_value=("market_value", "sum"),
        cost_basis=("cost_basis_total", "sum"),
        count=("symbol", "count"),
    ).to_dict("index")

    allocation = positions.copy()
    allocation["allocation_pct"] = (allocation["market_value"] / total_value * 100).round(2) if total_value > 0 else 0
    top_holdings = (
        allocation.nlargest(10, "market_value")[["symbol", "market_value", "allocation_pct"]]
        .round(2)
        .to_dict("records")
    )

    return {
        "total_value": round(float(total_value), 2),
        "total_cost_basis": round(float(total_cost), 2),
        "total_gain": round(float(total_value - total_cost), 2),
        "total_gain_pct": round(float((total_value - total_cost) / total_cost * 100), 2) if total_cost > 0 else 0,
        "position_count": len(positions),
        "by_class": {k: {kk: round(float(vv), 2) for kk, vv in v.items()} for k, v in by_class.items()},
        "allocation_pct": allocation[["symbol", "asset_class", "allocation_pct"]].to_dict("records"),
        "top_holdings": top_holdings,
    }


def calculate_returns(prices: list[float], interval: str = "daily") -> dict:
    """Calculate returns over multiple periods.

    Args:
        prices: list of price values (oldest first)
        interval: 'daily', 'weekly', 'monthly'

    Returns:
        dict with returns for various periods
    """
    series = pd.Series(prices)
    total_return = (series.iloc[-1] / series.iloc[0] - 1) * 100

    if len(series) < 2:
        return {"total_return_pct": round(total_return, 2), "annualized_return_pct": None}

    # Calculate daily returns
    daily_returns = series.pct_change().dropna()

    # Annualized return
    n_years = len(daily_returns) / 252
    annualized = (1 + daily_returns.mean()) ** 252 - 1 if n_years > 0 else 0

    # Period returns
    periods = {
        "1w": 5,
        "1m": 22,
        "3m": 66,
        "6m": 131,
        "1y": 252,
        "ytd": _ytd_days(series),
    }

    returns = {}
    for label, days in periods.items():
        if len(series) > days:
            ret = (series.iloc[-1] / series.iloc[-days - 1] - 1) * 100
            returns[f"{label}_return_pct"] = round(float(ret), 2)

    returns["total_return_pct"] = round(float(total_return), 2)
    returns["annualized_return_pct"] = round(float(annualized * 100), 2)
    returns["volatility"] = round(float(daily_returns.std() * np.sqrt(252) * 100), 2)

    return returns


def _ytd_days(series: pd.Series) -> int:
    """Get days from start of year to last data point."""
    if hasattr(series.index, "date"):
        dates = [d for d in series.index if hasattr(d, "month")]
        if dates:
            first_jan = date(dates[-1].year, 1, 1)
            return (dates[-1] - first_jan).days
    return 0


def build_price_series(transactions: list[dict], benchmark: str = "SPY") -> dict:
    """Build portfolio price series from transactions and fetch benchmark.

    Args:
        transactions: list of {date, amount} dicts (positive = deposit/negative = withdrawal)
        benchmark: benchmark ticker symbol

    Returns:
        dict with portfolio_series, benchmark_series
    """
    # Simplified: in production this would use a proper time-weighted return engine
    df = pd.DataFrame(transactions).sort_values("date")
    df["cumulative"] = df["amount"].cumsum()
    return {
        "portfolio": df[["date", "cumulative"]].to_dict("records"),
        "benchmark": benchmark,
    }
