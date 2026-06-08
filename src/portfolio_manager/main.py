"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from portfolio_manager.config import settings

# Templates (now in database.py to avoid circular imports)
from portfolio_manager.database import templates

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


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

# React SPA static files
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """Serve React SPA for all non-API routes."""
    if full_path.startswith("api/"):
        return {"error": "Not found"}
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"error": "Frontend not built"}


# Import routes after app creation to avoid circular imports
from portfolio_manager.routes import portfolios  # noqa: E402
from portfolio_manager.routes import dashboard  # noqa: E402
from portfolio_manager.routes import charts  # noqa: E402
from portfolio_manager.routes import ui  # noqa: E402

app.include_router(portfolios.router, prefix="/api/v1")
app.include_router(dashboard.router)
app.include_router(charts.router, prefix="/api/v1")
app.include_router(ui.router)
