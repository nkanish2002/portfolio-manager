"""Professional chart data API endpoints for financial visualizations.

Provides endpoints for:
- NAV growth with benchmark overlay
- Drawdown chart
- Asset allocation pie chart
- Monthly returns heatmap
- Returns distribution
- Benchmark comparison panel
- Risk metrics report
"""

import math
from datetime import date
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from portfolio_manager.database import get_db
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.transaction import Transaction, TransactionType
from portfolio_manager.services.benchmark import (
    calculate_information_ratio,
    calculate_tracking_error,
)
from portfolio_manager.services.chart_data import (
    generate_monthly_returns_heatmap,
    generate_nav_chart,
    generate_returns_distribution,
)
from portfolio_manager.services.nav_history import (
    build_nav_from_transactions,
    build_nav_with_benchmark,
)
from portfolio_manager.services.data_feed import YFinanceSource, get_historical

router = APIRouter(tags=["charts"])


async def get_transactions_for_portfolio(portfolio_id: str, db: AsyncSession) -> list[Transaction]:
    """Fetch all transactions for a portfolio."""
    result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.asset))
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.asc())
    )
    return list(result.scalars().all())


def _build_nav_df(transactions: list[Transaction]) -> pd.DataFrame:
    """Build a DataFrame with date index and NAV column from transactions."""
    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty:
        return pd.DataFrame(columns=["date", "nav"])
    return pd.DataFrame({"date": nav_series.index, "nav": nav_series.values})


@router.get("/charts/nav-history")
async def get_nav_history(portfolio_id: str,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          benchmark: str = "SPY") -> dict:
    """Get NAV history with benchmark overlay for TradingView Lightweight Charts.

    Returns data formatted for lightweight-charts line series:
    {
        "portfolio": [{"time": "2024-01-01", "value": 100.0}, ...],
        "benchmark": [{"time": "2024-01-01", "value": 98.0}, ...] | null,
        "benchmark_symbol": "SPY"
    }
    """
    # Verify portfolio exists
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await get_transactions_for_portfolio(portfolio_id, db)
    if not transactions:
        return {
            "portfolio": [],
            "benchmark": [],
            "benchmark_symbol": benchmark,
        }

    nav_data = build_nav_with_benchmark(transactions, benchmark)

    # Format for TradingView Lightweight Charts
    portfolio_series = [
        {"time": str(d), "value": round(float(v), 2)}
        for d, v in zip(nav_data["portfolio_dates"], nav_data["portfolio_nav"])
    ]
    benchmark_series = None
    if nav_data.get("benchmark_dates") and nav_data.get("benchmark_nav"):
        benchmark_series = [
            {"time": d, "value": round(float(v), 2)}
            for d, v in zip(nav_data["benchmark_dates"], nav_data["benchmark_nav"])
        ]

    return {
        "portfolio": portfolio_series,
        "benchmark": benchmark_series,
        "benchmark_symbol": nav_data.get("benchmark_symbol", benchmark),
    }


@router.get("/charts/nav")
async def get_nav_chart(portfolio_id: str,
                        db: Annotated[AsyncSession, Depends(get_db)],
                        benchmark: str = "SPY") -> dict:
    """Get NAV (Net Asset Value) chart data.

    Returns data formatted for both Plotly (legacy) and Lightweight Charts.
    """
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await get_transactions_for_portfolio(portfolio_id, db)
    if not transactions:
        return {
            "portfolio_dates": [],
            "portfolio_nav": [],
            "benchmark_dates": [],
            "benchmark_nav": [],
            "benchmark_symbol": benchmark,
        }

    nav_data = build_nav_with_benchmark(transactions, benchmark)
    return nav_data


@router.get("/charts/drawdown")
async def get_drawdown_chart(portfolio_id: str,
                             db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    """Get drawdown chart data from transaction history."""
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await get_transactions_for_portfolio(portfolio_id, db)
    if not transactions:
        return {"dates": [], "drawdown": [], "nav": []}

    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 2:
        return {"dates": [], "drawdown": [], "nav": []}

    # Calculate drawdown: ((current / max) - 1) * 100
    cumulative_max = nav_series.cummax()
    drawdown = ((nav_series / cumulative_max) - 1) * 100

    dates = [str(d) for d in nav_series.index]
    return {
        "dates": dates,
        "drawdown": [round(float(v), 2) for v in drawdown],
        "nav": [round(float(v), 2) for v in nav_series],
    }


@router.get("/charts/allocation")
async def get_allocation_chart(portfolio_id: str,
                               db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    """Get asset allocation pie chart data."""
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    # Get current positions
    from portfolio_manager.models.position import Position

    pos_result = await db.execute(
        select(Position)
        .options(selectinload(Position.asset))
        .where(Position.portfolio_id == portfolio_id)
    )
    positions = pos_result.scalars().all()

    if not positions:
        return {"labels": [], "values": [], "colors": [], "total_value": 0}

    rows = []
    for pos in positions:
        rows.append({
            "symbol": pos.asset.symbol if pos.asset else "?",
            "market_value": float(pos.quantity) * float(pos.current_price or 0),
            "asset_class": pos.asset.asset_class if pos.asset else "equity",
        })

    df = pd.DataFrame(rows)
    from portfolio_manager.services.benchmark import generate_allocation_pie
    result = generate_allocation_pie(df)

    # Map asset class colors for consistent palette
    color_map = {
        "equity": "#36A2EB",
        "crypto": "#FF6384",
        "bond": "#4BC0C0",
        "etf": "#FFCE56",
        "mutual_fund": "#9966FF",
        "commodity": "#FF9F40",
    }
    result["colors"] = [color_map.get(cls, "#C9CBCF") for cls in result["labels"]]

    return result


@router.get("/charts/monthly-returns")
async def get_monthly_returns(portfolio_id: str,
                              db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    """Get monthly returns heatmap data from transaction history."""
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await get_transactions_for_portfolio(portfolio_id, db)
    if not transactions:
        return {"years": [], "months": [], "values": [], "labels": []}

    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 60:
        # Return what we have (may be sparse)
        return _generate_monthly_from_nav(nav_series)

    return _generate_monthly_from_nav(nav_series)


def _generate_monthly_from_nav(nav_series: pd.Series) -> dict:
    """Generate monthly returns heatmap from a NAV series."""
    if nav_series.empty or len(nav_series) < 60:
        return {"years": [], "months": [], "values": [], "labels": []}

    nav = nav_series.copy()
    nav.index = pd.to_datetime(nav.index)

    monthly_returns = nav.pct_change().groupby([nav.index.year, nav.index.month]).last()
    monthly_returns = monthly_returns.unstack("month")

    # Keep last 36 months max
    if len(monthly_returns) > 36:
        monthly_returns = monthly_returns.tail(36)

    years = [int(y) for y in monthly_returns.index]
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
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


@router.get("/charts/returns-distribution")
async def get_returns_distribution(portfolio_id: str,
                                   db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    """Get returns distribution histogram data."""
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await get_transactions_for_portfolio(portfolio_id, db)
    if not transactions:
        return {"bins": [], "counts": [], "mean_return": 0.0, "std_return": 0.0}

    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 2:
        return {"bins": [], "counts": [], "mean_return": 0.0, "std_return": 0.0}

    return generate_returns_distribution(pd.DataFrame({"nav": nav_series}))


@router.get("/charts/benchmark-comparison")
async def get_benchmark_comparison(portfolio_id: str,
                                   db: Annotated[AsyncSession, Depends(get_db)],
                                   benchmark: str = "SPY") -> dict:
    """Get benchmark comparison statistics for the portfolio.

    Returns tracking error, information ratio, correlation, excess returns,
    and aligned price series for overlay charts.
    """
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await get_transactions_for_portfolio(portfolio_id, db)
    if not transactions:
        return {
            "dates": [], "portfolio": [], "benchmark": [],
            "excess_return": 0, "tracking_error": 0,
            "information_ratio": 0, "correlation": 0,
        }

    # Build portfolio NAV series
    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 60:
        return {
            "dates": [], "portfolio": [], "benchmark": [],
            "excess_return": 0, "tracking_error": 0,
            "information_ratio": 0, "correlation": 0,
        }

    # Calculate portfolio returns
    portfolio_returns = nav_series.pct_change().dropna()

    # Fetch benchmark data
    try:
        source = YFinanceSource()
        end = date.today()
        start = end - pd.Timedelta(days=730)
        bm_data = source.get_historical(benchmark, start, end)

        if bm_data.empty or "Close" not in bm_data.columns:
            return {
                "dates": [str(d) for d in portfolio_returns.index],
                "portfolio": [round(float(v), 2) for v in portfolio_returns],
                "benchmark": [],
                "excess_return": 0, "tracking_error": 0,
                "information_ratio": 0, "correlation": 0,
            }

        # Normalize both to 100
        bm_close = bm_data["Close"]
        port_norm = (nav_series / float(nav_series.iloc[0]) * 100)
        bm_norm = (bm_close / float(bm_close.iloc[0]) * 100)

        # Align on common dates
        common_idx = port_norm.index.intersection(bm_norm.index)
        port_aligned = port_norm.loc[common_idx]
        bm_aligned = bm_norm.loc[common_idx]

        # Calculate returns for aligned series
        port_rets = port_aligned.pct_change().dropna()
        bm_rets = bm_aligned.pct_change().dropna()

        # Alignment
        aligned = pd.concat([port_rets, bm_rets], axis=1).dropna()
        if len(aligned) < 2:
            return {
                "dates": [str(d) for d in common_idx],
                "portfolio": [round(float(v), 2) for v in port_aligned],
                "benchmark": [round(float(v), 2) for v in bm_aligned],
                "excess_return": 0, "tracking_error": 0,
                "information_ratio": 0, "correlation": 0,
            }

        excess = aligned[0] - aligned[1]
        te = calculate_tracking_error(excess)
        ir = calculate_information_ratio(excess, te) if te > 0 else 0
        corr = aligned[0].corr(aligned[1])
        corr = round(float(corr), 4) if not pd.isna(corr) else 0

        return {
            "dates": [str(d) for d in common_idx],
            "portfolio": [round(float(v), 2) for v in port_aligned],
            "benchmark": [round(float(v), 2) for v in bm_aligned],
            "excess_return": round(float(excess.sum() * 100), 2),
            "tracking_error": round(te, 2),
            "information_ratio": round(ir, 2),
            "correlation": corr,
            "benchmark_symbol": benchmark,
        }

    except Exception:
        return {
            "dates": [str(d) for d in port_norm.index],
            "portfolio": [round(float(v), 2) for v in port_norm],
            "benchmark": [],
            "excess_return": 0, "tracking_error": 0,
            "information_ratio": 0, "correlation": 0,
        }


@router.get("/risk-report")
async def get_risk_report(portfolio_id: str,
                          db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    """Get comprehensive risk report for a portfolio."""
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await get_transactions_for_portfolio(portfolio_id, db)
    if not transactions:
        return {"error": "No positions found"}

    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 60:
        return {"error": "Insufficient data for risk report"}

    returns = nav_series.pct_change().dropna()
    from portfolio_manager.services.benchmark import calculate_risk_report
    report = calculate_risk_report(returns)
    report["portfolio_id"] = portfolio_id
    return report
