"""Analytics service — risk metrics, chart data, and benchmark comparison.

Provides all data needed for the analytics screen:
- Risk report with 9 metrics (Sharpe, Sortino, Max DD, VaR, Beta, Alpha,
  Treynor, Calmar, Ulcer Index)
- NAV history for line chart
- Drawdown waterfall data
- Asset allocation (bar chart)
- Monthly returns heatmap
- Returns distribution histogram
- Benchmark comparison overlay

All methods use direct async SQLAlchemy — no framework dependency.
"""

from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from portfolio_manager.database import async_session as _default_session
from portfolio_manager.models.portfolio import Portfolio
from portfolio_manager.models.transaction import Transaction
from portfolio_manager.services.data_feed import YFinanceSource
from portfolio_manager.services.nav_history import build_nav_from_transactions
from portfolio_manager.services.risk import (
    calculate_alpha,
    calculate_beta,
    calculate_calmar,
    calculate_max_drawdown,
    calculate_sharpe,
    calculate_sortino,
    calculate_treynor,
    calculate_ulcer_index,
    calculate_var,
)


def _get_transactions(db: AsyncSession, portfolio_id: str):
    """Fetch all transactions for a portfolio, sorted chronologically."""
    result = db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.asc())
    )
    return list(result.scalars().all())


def _get_current_portfolio(db: AsyncSession, portfolio_id: str):
    """Get the current portfolio by ID."""
    result = db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    return result.scalar_one_or_none()


class AnalyticsService:
    """Analytics data service for the Textual TUI analytics screen."""

    def __init__(
        self,
        session_factory: async_sessionmaker | None = None,
    ) -> None:
        """Initialize with optional session factory."""
        self._session_factory = session_factory

    def _get_session_factory(self) -> async_sessionmaker:
        """Return the DB session factory, falling back to the global."""
        if self._session_factory is not None:
            return self._session_factory
        return _default_session

    async def get_current_portfolio_id(self) -> Optional[str]:
        """Get the current portfolio ID."""
        try:
            async with self._get_session_factory()() as session:
                result = await session.execute(
                    select(Portfolio).order_by(Portfolio.created_at).limit(1)
                )
                portfolio = result.scalar_one_or_none()
                return str(portfolio.id) if portfolio else None
        except Exception:
            return None

    async def get_risk_report(self, portfolio_id: str) -> dict:
        """Calculate all 9 risk metrics for a portfolio.

        Returns dict with:
            sharpe_ratio, sortino_ratio, max_drawdown, var,
            beta, alpha, treynor_ratio, calmar_ratio, ulcer_index,
            benchmark_sharpe, benchmark_sortino, benchmark_max_drawdown
        """
        try:
            async with self._get_session_factory()() as session:
                nav_series = await self._get_nav_series(session, portfolio_id)

                if nav_series.empty or len(nav_series) < 30:
                    return {"insufficient_data": True}

                returns = nav_series.pct_change().dropna()
                prices = (1 + returns).cumsum() * nav_series.iloc[0]
                prices.index = returns.index

                # Core portfolio metrics
                report = {
                    "sharpe_ratio": round(calculate_sharpe(returns), 2),
                    "sortino_ratio": round(calculate_sortino(returns), 2),
                    "max_drawdown": calculate_max_drawdown(prices),
                    "ulcer_index": round(calculate_ulcer_index(prices), 2),
                    "var": calculate_var(
                        returns, portfolio_value=float(prices.iloc[-1])
                    ),
                    "calmar_ratio": round(calculate_calmar(returns, prices), 2),
                    "benchmark_sharpe": None,
                    "benchmark_sortino": None,
                    "benchmark_max_drawdown": None,
                }

                # Benchmark comparison
                benchmark_returns = await self._fetch_benchmark_returns(
                    session, portfolio_id
                )
                if benchmark_returns is not None and not benchmark_returns.empty:
                    report["beta"] = round(
                        calculate_beta(returns, benchmark_returns), 2
                    )
                    report["alpha"] = round(
                        calculate_alpha(returns, benchmark_returns), 2
                    )
                    report["treynor_ratio"] = round(
                        calculate_treynor(returns, benchmark_returns), 2
                    )

                    # Benchmark own metrics
                    bm_prices = (
                        1 + benchmark_returns
                    ).cumsum() * benchmark_returns.iloc[0]
                    bm_prices.index = benchmark_returns.index
                    report["benchmark_sharpe"] = round(
                        calculate_sharpe(benchmark_returns), 2
                    )
                    report["benchmark_sortino"] = round(
                        calculate_sortino(benchmark_returns), 2
                    )
                    bm_mdd = calculate_max_drawdown(bm_prices)
                    report["benchmark_max_drawdown"] = round(
                        bm_mdd["max_drawdown_pct"], 2
                    )

                return report
        except Exception:
            return {"insufficient_data": True}

    async def _fetch_benchmark_returns(
        self, session: AsyncSession, portfolio_id: str, benchmark: str = "SPY"
    ):
        """Fetch benchmark daily returns for the same period as portfolio data."""
        nav_series = await self._get_nav_series(session, portfolio_id)
        if nav_series.empty or len(nav_series) < 2:
            return None

        try:
            source = YFinanceSource()
            end = date.today()
            start = end - timedelta(days=365)
            bm_data = source.get_historical(benchmark, start, end)

            if bm_data is None or bm_data.empty or "Close" not in bm_data.columns:
                return None

            bm_close = bm_data["Close"]
            common_start = max(
                nav_series.index[0],
                bm_close.index[0] if hasattr(bm_close.index[0], "year") else bm_close.index[0],
            )
            bm_filtered = bm_close[bm_close.index >= common_start]
            if len(bm_filtered) < 30:
                return None

            bm_returns = bm_filtered.pct_change().dropna()
            common_idx = nav_series.index.intersection(bm_returns.index)
            if len(common_idx) < 30:
                return None

            return bm_returns.loc[common_idx]
        except Exception:
            return None

    async def _get_nav_series(self, session: AsyncSession, portfolio_id: str):
        """Get NAV series for a portfolio."""
        transactions = await session.execute(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.transaction_date.asc())
        )
        txns = list(transactions.scalars().all())
        if not txns:
            return pd.Series(dtype=float)
        return build_nav_from_transactions(txns)

    async def get_nav_history(
        self, portfolio_id: str, benchmark: str = "SPY", range_str: str = "1Y"
    ) -> dict:
        """Get NAV history with optional benchmark overlay.

        Returns dict with 'dates', 'portfolio_nav', 'benchmark_nav', 'benchmark_symbol'.
        """
        try:
            async with self._get_session_factory()() as session:
                nav_series = await self._get_nav_series(session, portfolio_id)

            if nav_series.empty or len(nav_series) < 2:
                return {
                    "dates": [],
                    "portfolio_nav": [],
                    "benchmark_nav": None,
                    "benchmark_symbol": benchmark,
                }

            nav_series = self._apply_range(nav_series, range_str)

            result = {
                "dates": [
                    str(d.date()) if hasattr(d, "date") else str(d)
                    for d in nav_series.index
                ],
                "portfolio_nav": [round(float(v), 2) for v in nav_series],
                "benchmark_nav": None,
                "benchmark_symbol": benchmark,
            }

            if len(nav_series) >= 2:
                try:
                    end = date.today()
                    start = end - timedelta(days=730)
                    source = YFinanceSource()
                    bm_data = source.get_historical(benchmark, start, end)

                    if bm_data is not None and not bm_data.empty and "Close" in bm_data.columns:
                        bm_close = bm_data["Close"]
                        common_idx = nav_series.index.intersection(bm_close.index)
                        if len(common_idx) >= 2:
                            nav_common = nav_series.loc[common_idx]
                            bm_common = bm_close.loc[common_idx]
                            nav_norm = (nav_common / nav_common.iloc[0] * 100).round(2)
                            bm_norm = (bm_common / bm_common.iloc[0] * 100).round(2)
                            result["benchmark_nav"] = list(bm_norm)
                except Exception:
                    pass

            return result
        except Exception:
            return {
                "dates": [],
                "portfolio_nav": [],
                "benchmark_nav": None,
                "benchmark_symbol": benchmark,
            }

    async def get_drawdown(self, portfolio_id: str, range_str: str = "1Y") -> dict:
        """Get drawdown chart data.

        Returns dict with 'dates', 'drawdown', 'nav'.
        """
        try:
            async with self._get_session_factory()() as session:
                nav_series = await self._get_nav_series(session, portfolio_id)

            if nav_series.empty or len(nav_series) < 2:
                return {"dates": [], "drawdown": [], "nav": []}

            nav_series = self._apply_range(nav_series, range_str)

            cumulative_max = nav_series.cummax()
            drawdown = ((nav_series / cumulative_max) - 1) * 100

            return {
                "dates": [
                    str(d.date()) if hasattr(d, "date") else str(d)
                    for d in nav_series.index
                ],
                "drawdown": [round(float(v), 2) for v in drawdown],
                "nav": [round(float(v), 2) for v in nav_series],
            }
        except Exception:
            return {"dates": [], "drawdown": [], "nav": []}

    async def get_allocation(self, portfolio_id: str) -> dict:
        """Get asset allocation data.

        Returns dict with 'labels', 'values', 'colors', 'total_value'.
        """
        try:
            async with self._get_session_factory()() as session:
                from portfolio_manager.models.position import Position
                from portfolio_manager.models.asset import Asset

                result = await session.execute(
                    select(Position, Asset.symbol, Asset.asset_class)
                    .outerjoin(Asset, Position.asset_id == Asset.id)
                    .where(Position.portfolio_id == portfolio_id)
                )
                rows = result.all()

            if not rows:
                return {
                    "labels": [],
                    "values": [],
                    "colors": [],
                    "total_value": 0,
                }

            rows_list = [
                {
                    "symbol": r[1] if r[1] else "Unknown",
                    "asset_class": r[2] if r[2] else "Unknown",
                }
                for r in rows
            ]

            # Aggregate by asset class
            by_class = {}
            total_value = 0
            for row in rows_list:
                cls = row["asset_class"]
                by_class[cls] = by_class.get(cls, 0) + 1
                total_value += 1

            labels = sorted(by_class.keys())
            values = [by_class[cls] for cls in labels]

            color_map = {
                "equity": "#36A2EB",
                "crypto": "#FF6384",
                "bond": "#4BC0C0",
                "etf": "#FFCE56",
                "mutual_fund": "#9966FF",
                "commodity": "#FF9F40",
            }
            colors = [color_map.get(cls, "#C9CBCF") for cls in labels]

            return {
                "labels": labels,
                "values": values,
                "colors": colors,
                "total_value": total_value,
            }
        except Exception:
            return {
                "labels": [],
                "values": [],
                "colors": [],
                "total_value": 0,
            }

    async def get_monthly_returns(self, portfolio_id: str) -> dict:
        """Get monthly returns heatmap data.

        Returns dict with 'years', 'months', 'values'.
        """
        try:
            async with self._get_session_factory()() as session:
                nav_series = await self._get_nav_series(session, portfolio_id)

            if nav_series.empty or len(nav_series) < 5:
                return {
                    "years": [],
                    "months": [],
                    "values": [],
                    "insufficient_data": True,
                }

            nav = nav_series.copy()
            nav.index = pd.to_datetime(nav.index)

            monthly_returns = (
                nav.pct_change()
                .groupby([nav.index.year, nav.index.month])
                .last()
            )
            monthly_returns.index.names = ["year", "month"]
            monthly_returns = monthly_returns.unstack("month")

            if len(monthly_returns) > 36:
                monthly_returns = monthly_returns.tail(36)

            years = [int(y) for y in monthly_returns.index]
            month_names = [
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
            ]
            present_months = [m for m in monthly_returns.columns if m <= 12]
            present_month_names = [month_names[m - 1] for m in present_months]

            values_raw = monthly_returns[present_months].fillna(0).values.tolist()
            values_pct = [
                [round(float(v) * 100, 2) for v in row]
                for row in values_raw
            ]

            return {
                "years": years,
                "months": present_month_names,
                "values": values_pct,
                "insufficient_data": False,
            }
        except Exception:
            return {
                "years": [],
                "months": [],
                "values": [],
                "insufficient_data": True,
            }

    async def get_returns_distribution(self, portfolio_id: str) -> dict:
        """Get returns distribution histogram data.

        Returns dict with 'bins', 'counts', 'mean_return', 'std_return'.
        """
        try:
            async with self._get_session_factory()() as session:
                nav_series = await self._get_nav_series(session, portfolio_id)

            if nav_series.empty or len(nav_series) < 2:
                return {
                    "bins": [],
                    "counts": [],
                    "mean_return": 0.0,
                    "std_return": 0.0,
                }

            returns = nav_series.pct_change().dropna()
            if returns.empty:
                return {
                    "bins": [],
                    "counts": [],
                    "mean_return": 0.0,
                    "std_return": 0.0,
                }

            hist, bin_edges = np.histogram(returns, bins=30)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

            return {
                "bins": [round(float(b), 6) for b in bin_centers],
                "counts": [int(c) for c in hist],
                "mean_return": round(float(returns.mean() * 100), 4),
                "std_return": round(float(returns.std() * 100), 4),
            }
        except Exception:
            return {
                "bins": [],
                "counts": [],
                "mean_return": 0.0,
                "std_return": 0.0,
            }

    async def get_benchmark_comparison(
        self, portfolio_id: str, benchmark: str = "SPY", range_str: str = "1Y"
    ) -> dict:
        """Get benchmark comparison overlay data.

        Returns dict with 'dates', 'portfolio', 'benchmark', 'excess'.
        """
        try:
            async with self._get_session_factory()() as session:
                nav_series = await self._get_nav_series(session, portfolio_id)
                benchmark_returns = await self._fetch_benchmark_returns(
                    session, portfolio_id, benchmark
                )

            if nav_series.empty or len(nav_series) < 30:
                return {
                    "dates": [],
                    "portfolio": [],
                    "benchmark": [],
                    "excess": [],
                }

            nav_series = self._apply_range(nav_series, range_str)

            if nav_series.empty or len(nav_series) < 30:
                return {
                    "dates": [
                        str(d.date()) if hasattr(d, "date") else str(d)
                        for d in nav_series.index
                    ],
                    "portfolio": [round(float(v), 2) for v in nav_series],
                    "benchmark": [],
                    "excess": [],
                }

            if benchmark_returns is not None and not benchmark_returns.empty:
                common_idx = nav_series.index.intersection(benchmark_returns.index)
                if len(common_idx) >= 30:
                    nav_common = nav_series.loc[common_idx]
                    bm_common = benchmark_returns.loc[common_idx].cumsum() + 1

                    nav_norm = (nav_common / nav_common.iloc[0] * 100).round(2)
                    bm_norm = (bm_common / bm_common.iloc[0] * 100).round(2)

                    excess = (nav_norm - bm_norm).round(2)

                    return {
                        "dates": [
                            str(d.date()) if hasattr(d, "date") else str(d)
                            for d in common_idx
                        ],
                        "portfolio": list(nav_norm),
                        "benchmark": list(bm_norm),
                        "excess": list(excess),
                    }

            # Fallback: portfolio-only
            nav_norm = (nav_series / nav_series.iloc[0] * 100).round(2)
            return {
                "dates": [
                    str(d.date()) if hasattr(d, "date") else str(d)
                    for d in nav_norm.index
                ],
                "portfolio": list(nav_norm),
                "benchmark": [],
                "excess": [],
            }
        except Exception:
            return {
                "dates": [],
                "portfolio": [],
                "benchmark": [],
                "excess": [],
            }

    def _apply_range(self, series: pd.Series, range_str: str) -> pd.Series:
        """Apply a date range filter to a datetime-indexed series."""
        if range_str.upper() == "ALL":
            return series

        range_map = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}
        days = range_map.get(range_str.upper(), 365)

        if len(series) > days:
            return series.iloc[-days:]
        return series
