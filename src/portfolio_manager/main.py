"""Portfolio Manager Solara application entry point.

This file initializes the database and exposes the Solara app component.
Run with: solara run portfolio_manager.solara_app
"""

import structlog

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


async def lifespan():
    """Initialize DB on startup."""
    logger.info("Starting Portfolio Manager")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down Portfolio Manager")
