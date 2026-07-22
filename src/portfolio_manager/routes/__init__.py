"""API route layer — all routers mounted under ``/api/v1`` and auth-gated."""

from fastapi import APIRouter

from portfolio_manager.routes import (
    accounts,
    analytics,
    baskets,
    portfolios,
    positions,
    reports,
    statement_import,
    transactions,
    ws,
)

api_router = APIRouter()
api_router.include_router(accounts.router)
api_router.include_router(baskets.router)
api_router.include_router(portfolios.router)
api_router.include_router(positions.router)
api_router.include_router(transactions.router)
api_router.include_router(analytics.router)
api_router.include_router(statement_import.router)
api_router.include_router(reports.router)

# WebSocket router is separate (not under /api/v1)
__all__ = ["api_router", "ws"]
