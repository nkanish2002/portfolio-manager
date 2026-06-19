"""Chart service — business logic for chart data generation.

This service is called directly by Solara components. No FastAPI routes.
"""

import structlog
from datetime import date
from typing import Annotated

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.database import async_session
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.transaction import Transaction, TransactionType
from portfolio_manager.services.nav_history import build_nav_from_transactions
from portfolio_manager.services.chart_data import (
    generate_monthly_returns_heatmap,
    generate_returns_distribution,
)
from portfolio_manager.services.benchmark import (
    calculate_information_ratio,
    calculate_tracking_error,
    generate_allocation_pie,
)
from portfolio_manager.services.data_feed import YFinanceSource, get_historical

logger = structlog.getLogger(__name__)


class ChartService:
    """Chart business logic service."""

    async def get_nav_history(self, portfolio_id: str, benchmark: str = "SPY") -> dict:
        """Get NAV history with benchmark overlay."""
        async with async_session() as session:
            return await _get_nav_history(session, portfolio_id, benchmark)

    async def get_drawdown(self, portfolio_id: str) -> dict:
        """Get drawdown chart data."""
        async with async_session() as session:
            return await _get_drawdown(session, portfolio_id)

    async def get_allocation(self, portfolio_id: str) -> dict:
        """Get asset allocation pie chart data."""
        async with async_session() as session:
            return await _get_allocation(session, portfolio_id)

    async def get_monthly_returns(self, portfolio_id: str) -> dict:
        """Get monthly returns heatmap data."""
        async with async_session() as session:
            return await _get_monthly_returns(session, portfolio_id)

    async def get_returns_distribution(self, portfolio_id: str) -> dict:
        """Get returns distribution histogram data."""
        async with async_session() as session:
            return await _get_returns_distribution(session, portfolio_id)

    async def get_benchmark_comparison(
        self, portfolio_id: str, benchmark: str = "SPY"
    ) -> dict:
        """Get benchmark comparison statistics."""
        async with async_session() as session:
            return await _get_benchmark_comparison(session, portfolio_id, benchmark)

    async def get_risk_report(self, portfolio_id: str) -> dict:
        """Get comprehensive risk report."""
        async with async_session() as session:
            return await _get_risk_report(session, portfolio_id)


async def _get_nav_history(
    db, portfolio_id: str, benchmark: str = "SPY"
) -> dict:
    """Get NAV history with benchmark overlay."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await _get_transactions(db, portfolio_id)
    if not transactions:
        return {
            "portfolio_dates": [],
            "portfolio_nav": [],
            "benchmark_dates": [],
            "benchmark_nav": [],
            "benchmark_symbol": benchmark,
        }

    from portfolio_manager.services.nav_history import build_nav_with_benchmark
    nav_data = build_nav_with_benchmark(transactions, benchmark)
    return nav_data


async def _get_drawdown(db, portfolio_id: str) -> dict:
    """Get drawdown chart data."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await _get_transactions(db, portfolio_id)
    if not transactions:
        return {"dates": [], "drawdown": [], "nav": []}

    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 2:
        return {"dates": [], "drawdown": [], "nav": []}

    cumulative_max = nav_series.cummax()
    drawdown = ((nav_series / cumulative_max) - 1) * 100

    dates = [str(d) for d in nav_series.index]
    return {
        "dates": dates,
        "drawdown": [round(float(v), 2) for v in drawdown],
        "nav": [round(float(v), 2) for v in nav_series],
    }


async def _get_allocation(db, portfolio_id: str) -> dict:
    """Get asset allocation pie chart data."""
    from portfolio_manager.models.position import Position
    from portfolio_manager.models.asset import Asset

    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    pos_result = await db.execute(
        select(Position)
        .where(Position.portfolio_id == portfolio_id)
        .join(Position.asset)
    )
    positions = pos_result.scalars().all()

    if not positions:
        return {"labels": [], "values": [], "colors": [], "total_value": 0}

    rows = []
    for pos in positions:
        rows.append(
            {
                "symbol": pos.asset.symbol if pos.asset else "?",
                "market_value": float(pos.quantity) * float(pos.current_price or 0),
                "asset_class": pos.asset.asset_class if pos.asset else "equity",
            }
        )

    df = pd.DataFrame(rows)
    result = generate_allocation_pie(df)

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


async def _get_monthly_returns(db, portfolio_id: str) -> dict:
    """Get monthly returns heatmap data."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await _get_transactions(db, portfolio_id)
    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty:
        return {
            "years": [],
            "months": [],
            "values": [],
            "labels": [],
            "insufficient_data": True,
        }

    return _generate_monthly_from_nav(nav_series)


def _generate_monthly_from_nav(nav_series: pd.Series) -> dict:
    """Generate monthly returns heatmap from a NAV series."""
    if nav_series.empty or len(nav_series) < 5:
        return {
            "years": [],
            "months": [],
            "values": [],
            "labels": [],
            "insufficient_data": True,
        }

    nav = nav_series.copy()
    nav.index = pd.to_datetime(nav.index)

    monthly_returns = (
        nav.pct_change().groupby([nav.index.year, nav.index.month]).last()
    )
    monthly_returns.index.names = ["year", "month"]
    monthly_returns = monthly_returns.unstack("month")

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
    present_months = [m for m in monthly_returns.columns if m <= 12]
    present_month_names = [month_names[m - 1] for m in present_months]

    values = monthly_returns[present_months].fillna(0).values.tolist()
    values_pct = [[round(float(v) * 100, 2) for v in row] for row in values]

    return {
        "years": years,
        "months": present_month_names,
        "values": values_pct,
        "labels": [
            f"{year} {month}" for year in years for month in present_month_names
        ],
        "insufficient_data": False,
    }


async def _get_returns_distribution(db, portfolio_id: str) -> dict:
    """Get returns distribution histogram data."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await _get_transactions(db, portfolio_id)
    if not transactions:
        return {"bins": [], "counts": [], "mean_return": 0.0, "std_return": 0.0}

    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 2:
        return {"bins": [], "counts": [], "mean_return": 0.0, "std_return": 0.0}

    return generate_returns_distribution(pd.DataFrame({"nav": nav_series}))


async def _get_benchmark_comparison(
    db, portfolio_id: str, benchmark: str = "SPY"
) -> dict:
    """Get benchmark comparison statistics."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await _get_transactions(db, portfolio_id)
    if not transactions:
        return {
            "dates": [],
            "portfolio": [],
            "benchmark": [],
            "excess_return": 0,
            "tracking_error": 0,
            "information_ratio": 0,
            "correlation": 0,
        }

    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 30:
        return {
            "dates": [],
            "portfolio": [],
            "benchmark": [],
            "excess_return": 0,
            "tracking_error": 0,
            "information_ratio": 0,
            "correlation": 0,
            "insufficient_data": True,
        }

    portfolio_returns = nav_series.pct_change().dropna()

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
                "excess_return": 0,
                "tracking_error": 0,
                "information_ratio": 0,
                "correlation": 0,
            }

        bm_close = bm_data["Close"]
        port_norm = nav_series / float(nav_series.iloc[0]) * 100
        bm_norm = bm_close / float(bm_close.iloc[0]) * 100

        common_idx = port_norm.index.intersection(bm_norm.index)
        port_aligned = port_norm.loc[common_idx]
        bm_aligned = bm_norm.loc[common_idx]

        port_rets = port_aligned.pct_change().dropna()
        bm_rets = bm_aligned.pct_change().dropna()

        aligned = pd.concat([port_rets, bm_rets], axis=1).dropna()
        if len(aligned) < 2:
            return {
                "dates": [str(d) for d in common_idx],
                "portfolio": [round(float(v), 2) for v in port_aligned],
                "benchmark": [round(float(v), 2) for v in bm_aligned],
                "excess_return": 0,
                "tracking_error": 0,
                "information_ratio": 0,
                "correlation": 0,
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
            "excess_return": 0,
            "tracking_error": 0,
            "information_ratio": 0,
            "correlation": 0,
        }


async def _get_risk_report(db, portfolio_id: str) -> dict:
    """Get comprehensive risk report."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"error": "Portfolio not found"}

    transactions = await _get_transactions(db, portfolio_id)
    if not transactions:
        return {"error": "No positions found"}

    nav_series = build_nav_from_transactions(transactions)
    if nav_series.empty or len(nav_series) < 30:
        return {
            "error": "Insufficient data for risk report",
            "insufficient_data": True,
        }

    returns = nav_series.pct_change().dropna()
    from portfolio_manager.services.benchmark import calculate_risk_report
    report = calculate_risk_report(returns)
    report["portfolio_id"] = portfolio_id
    return report


async def _get_transactions(db, portfolio_id: str):
    """Fetch all transactions for a portfolio."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.asc())
    )
    return list(result.scalars().all())
