"""NAV history generation from transaction history.

Provides proper historical NAV time series built from transaction records,
replacing the synthetic single-point NAV used in the old chart endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd

from portfolio_manager.models.transaction import Transaction, TransactionType


def build_nav_from_transactions(transactions: list[Transaction]) -> pd.Series:
    """Build a chronological NAV time series from transaction history.

    Processes transactions in chronological order, computing cumulative
    portfolio value after each event. Supports:
    - BUY: adds quantity * price to portfolio value
    - SELL: subtracts quantity * price from portfolio value
    - DIVIDEND/INTEREST: adds to portfolio value
    - FEE: subtracts from portfolio value
    - DEPOSIT: adds to portfolio value
    - WITHDRAWAL: subtracts from portfolio value

    Args:
        transactions: List of Transaction objects sorted by date.

    Returns:
        pd.Series with date index and float NAV values.
    """
    if not transactions:
        return pd.Series(dtype=float)

    # Sort chronologically
    sorted_txns = sorted(transactions, key=lambda t: (t.transaction_date, t.created_at or datetime.min))

    nav_series = []
    cumulative_nav = 0.0

    for txn in sorted_txns:
        if txn.transaction_date is None:
            continue

        amount = 0.0
        match txn.transaction_type:
            case TransactionType.BUY:
                amount = float(txn.quantity) * float(txn.price) + float(txn.fees)
                cumulative_nav -= amount  # Cash outflow reduces net value
            case TransactionType.SELL:
                amount = float(txn.quantity) * float(txn.price) - float(txn.fees)
                cumulative_nav += amount  # Cash inflow increases net value
            case TransactionType.DIVIDEND | TransactionType.INTEREST | TransactionType.DEPOSIT:
                amount = float(txn.quantity) * float(txn.price)
                cumulative_nav += amount
            case TransactionType.FEE:
                amount = float(txn.quantity) * float(txn.price)
                cumulative_nav -= amount
            case TransactionType.WITHDRAWAL:
                amount = float(txn.quantity) * float(txn.price)
                cumulative_nav -= amount
            case _:
                # For splits and reinvestments, no direct NAV change
                amount = 0.0

        nav_series.append((txn.transaction_date, cumulative_nav))

    if not nav_series:
        return pd.Series(dtype=float)

    series = pd.Series(
        [v for _, v in nav_series],
        index=pd.to_datetime([d for d, _ in nav_series]),
        dtype=float,
    )

    # Forward-fill to handle gaps and normalize to start at 100
    series = series.ffill().bfill()
    if len(series) > 0 and series.iloc[0] != 0:
        series = series / series.iloc[0] * 100

    return series


def build_nav_with_benchmark(
    transactions: list[Transaction],
    benchmark_symbol: str = "SPY",
) -> dict:
    """Build NAV history with optional benchmark overlay.

    Args:
        transactions: Transaction history.
        benchmark_symbol: Ticker for benchmark (default SPY).

    Returns:
        dict with 'portfolio_dates', 'portfolio_nav', 'benchmark_dates',
        'benchmark_nav', and 'benchmark_symbol'.
    """
    portfolio_nav = build_nav_from_transactions(transactions)

    result: dict = {
        "portfolio_dates": [str(d) for d in portfolio_nav.index],
        "portfolio_nav": [round(float(v), 2) for v in portfolio_nav],
        "benchmark_dates": [],
        "benchmark_nav": [],
        "benchmark_symbol": benchmark_symbol,
    }

    if portfolio_nav.empty or len(portfolio_nav) < 2:
        return result

    # Fetch benchmark data
    try:
        from portfolio_manager.services.data_feed import YFinanceSource

        source = YFinanceSource()
        end = date.today()
        # Fetch 2 years of benchmark data for overlay
        start = end - pd.Timedelta(days=730)
        benchmark_data = source.get_historical(benchmark_symbol, start, end)

        if benchmark_data is not None and not benchmark_data.empty:
            # Require 'Date' column for benchmark data
            date_col = "Date"
            if date_col not in benchmark_data.columns:
                # Benchmark data missing required Date column
                return result
            
            close_col = "Close" if "Close" in benchmark_data.columns else None
            if close_col is not None and len(benchmark_data) > 0:
                # Normalize benchmark to same starting point (100)
                bm_start = float(benchmark_data[close_col].iloc[0])
                if bm_start > 0:
                    benchmark_nav = (benchmark_data[close_col] / bm_start * 100).round(2)
                    # Get dates as strings
                    dates = [str(d) for d in benchmark_data[date_col]]
                    result["benchmark_dates"] = dates
                    result["benchmark_nav"] = list(benchmark_nav)
    except Exception:
        # Gracefully degrade — return portfolio-only chart
        pass

    return result