"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from portfolio_manager.config import settings

# Templates (now in database.py to avoid circular imports)
from portfolio_manager.database import templates

# Setup structlog for structured JSON logging
import structlog
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_class=structlog.BoundLogger,
)
logger = structlog.getLogger(__name__)

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and start WebSocket manager on startup."""
    from portfolio_manager.database import init_db
    from portfolio_manager.services.ws_service import ws_manager

    await init_db()

    # Start WebSocket polling loop
    await ws_manager.start()

    yield

    # Shutdown: stop WebSocket polling
    await ws_manager.stop()


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

# React SPA static files
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


# Import routes after app creation to avoid circular imports
from portfolio_manager.routes import portfolios  # noqa: E402
from portfolio_manager.routes import dashboard  # noqa: E402
from portfolio_manager.routes import charts  # noqa: E402
from portfolio_manager.routes import ui  # noqa: E402
from portfolio_manager.routes import ws  # noqa: E402
from portfolio_manager.routes import trades  # noqa: E402

app.include_router(portfolios.router, prefix="/api/v1")
app.include_router(dashboard.router)
app.include_router(charts.router, prefix="/api/v1")
app.include_router(ui.router)
app.include_router(trades.router, prefix="/api/v1")
# WebSocket endpoint (no HTTP prefix — FastAPI detects @app.websocket)
app.include_router(ws.router)


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """Serve React SPA for all non-API routes."""
    # Don't intercept API routes — let FastAPI's 404 handling take over
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"error": "Frontend not built"}
