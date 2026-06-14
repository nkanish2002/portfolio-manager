"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from portfolio_manager.config import settings

# Setup structlog for structured JSON logging
import structlog
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
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    from portfolio_manager.database import init_db

    await init_db()

    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handlers (Phase 9) ──────────────────────────────────────
from portfolio_manager.exceptions import register_exception_handlers  # noqa: E402

register_exception_handlers(app)


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


# Import routes after app creation to avoid circular imports
from portfolio_manager.routes import portfolios  # noqa: E402
from portfolio_manager.routes import charts  # noqa: E402
from portfolio_manager.routes import trades  # noqa: E402

app.include_router(portfolios.router, prefix="/api/v1")
app.include_router(charts.router, prefix="/api/v1")
app.include_router(trades.router, prefix="/api/v1")
