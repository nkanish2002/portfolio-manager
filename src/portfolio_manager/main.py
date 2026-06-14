"""Portfolio Manager Solara application entry point.

This file initializes the database and exposes a Solara component for the
Solara UI server. It no longer uses FastAPI routes — all business logic
moves to Python services called directly by Solara components.
"""

from contextlib import asynccontextmanager

import structlog

from portfolio_manager.config import settings
from portfolio_manager.database import init_db

# Setup structlog for structured JSON logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.getLogger(__name__)


@asynccontextmanager
async def lifespan():
    """Initialize DB on startup."""
    await init_db()
    yield


app = lifespan


def get_app():
    """Return the lifespan context manager for Solara server."""
    return app
