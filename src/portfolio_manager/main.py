"""FastAPI application factory.

Wires lifespan (DB connectivity check), CORS middleware, auth routers,
user management routes, health-check endpoints, SPA static file serving,
global exception handlers, and structured logging.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from portfolio_manager.auth import (
    UserCreate,
    UserRead,
    UserUpdate,
    auth_backend,
    fastapi_users,
)
from portfolio_manager.config import settings
from portfolio_manager.database import async_session_factory, engine
from portfolio_manager.exceptions import register_exception_handlers
from portfolio_manager.services.ws_service import ws_manager

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: verify DB connectivity, start WS poller.
    Shutdown: stop WS poller, close DB sessions, dispose engine pool.
    """
    # Import all models so they register with the shared metadata
    import portfolio_manager.models  # noqa: F401

    # Verify DB connectivity on startup
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        log.info("Database connectivity verified")
    except Exception as exc:  # noqa: BLE001
        log.warning("DB connectivity check failed on startup", error=str(exc))

    # Start WebSocket price poller
    await ws_manager.start()
    log.info("Application started")

    yield

    # ── Graceful shutdown ──────────────────────────────────────────────
    log.info("Shutting down application")

    # Stop WS poller (cancel background task, disconnect clients)
    try:
        await ws_manager.stop()
        log.info("WebSocket manager stopped")
    except Exception:  # noqa: BLE001
        log.error("Error stopping WebSocket manager", exc_info=True)

    # Close any lingering DB sessions and dispose the connection pool
    try:
        await async_session_factory.close()
        log.info("DB session factory closed")
    except Exception:  # noqa: BLE001
        log.error("Error closing DB session factory", exc_info=True)

    try:
        await engine.dispose()
        log.info("DB engine pool disposed")
    except Exception:  # noqa: BLE001
        log.error("Error disposing DB engine", exc_info=True)

    log.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # ── Global exception handlers + structured logging ─────────────────
    # Must be registered before routers so they catch everything.
    register_exception_handlers(app)

    # ── CORS ──────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health check ──────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness probe — does not hit the DB."""
        return {"status": "healthy"}

    @app.get("/health/db", tags=["health"])
    async def health_db() -> dict[str, str]:
        """Readiness probe — verifies DB connectivity."""
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}

    # ── Auth routers (fastapi-users) ──────────────────────────────────
    # All auth routes under /auth/jwt to match the API spec.
    app.include_router(
        fastapi_users.get_auth_router(auth_backend),
        prefix="/auth/jwt",
        tags=["auth"],
    )
    app.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix="/auth/jwt",
        tags=["auth"],
    )
    app.include_router(
        fastapi_users.get_reset_password_router(),
        prefix="/auth/jwt",
        tags=["auth"],
    )
    app.include_router(
        fastapi_users.get_users_router(UserRead, UserUpdate),
        prefix="/users",
        tags=["users"],
    )

    # ── API v1 routes (auth-gated) ─────────────────────────────────────
    from portfolio_manager.routes import api_router
    from portfolio_manager.routes import ws as ws_routes

    app.include_router(api_router)

    # ── WebSocket routes ────────────────────────────────────────────────
    app.include_router(ws_routes.router)

    # ── SPA static files + catch-all (production) ─────────────────────
    # When the React build output exists (Docker/prod), serve the SPA
    # so that FastAPI is the single entry point for both API + frontend.
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            """Catch-all: serve index.html for any non-API, non-static path."""
            return FileResponse(str(static_dir / "index.html"))

    return app


# Module-level instance for `uvicorn portfolio_manager.main:app`
app = create_app()
