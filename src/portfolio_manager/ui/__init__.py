"""UI components package — Solara frontend components for Portfolio Manager.

This package contains Solara components that call services directly.
No FastAPI routes — all components use async Python functions.
"""

from portfolio_manager.ui.dashboard import Dashboard
from portfolio_manager.ui.charts import ChartsView
from portfolio_manager.ui.trades import TradesView

__all__ = ["Dashboard", "ChartsView", "TradesView"]
