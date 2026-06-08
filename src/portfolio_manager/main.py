"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from portfolio_manager.config import settings

# Templates (now in database.py to avoid circular imports)
from portfolio_manager.database import templates


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

# Static files (for JS/CSS assets)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    from portfolio_manager.database import async_session

    db = async_session()
    try:
        # Quick check: do we have any portfolios?
        from sqlalchemy import text
        result = await db.execute(text("SELECT COUNT(*) FROM portfolios"))
        portfolio_count = result.scalar()
    except Exception:
        portfolio_count = 0
    finally:
        await db.close()

    return templates.TemplateResponse(request, "index.html", {"portfolio_count": portfolio_count})


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


# Import routes after app creation to avoid circular imports
from portfolio_manager.routes import portfolios  # noqa: E402
from portfolio_manager.routes import dashboard  # noqa: E402

app.include_router(portfolios.router, prefix="/api/v1")
app.include_router(dashboard.router)
