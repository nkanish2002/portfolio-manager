"""FastAPI application factory.

Wires lifespan (DB connectivity check), CORS middleware, auth routers,
user management routes, and health-check endpoints.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from portfolio_manager.auth import (
    UserCreate,
    UserRead,
    UserUpdate,
    auth_backend,
    fastapi_users,
)
from portfolio_manager.config import settings
from portfolio_manager.database import engine
from portfolio_manager.services.ws_service import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: verify DB connectivity, start WS poller. Shutdown: dispose engine pool."""
    # Import all models so they register with the shared metadata
    import portfolio_manager.models  # noqa: F401

    # Verify DB connectivity on startup
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:  # noqa: BLE001
        import structlog

        log = structlog.get_logger()
        log.warning("DB connectivity check failed on startup", error=str(e))

    # Start WebSocket price poller
    await ws_manager.start()

    yield

    # Shutdown: stop WS poller and dispose engine connections
    await ws_manager.stop()
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

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

    return app


# Module-level instance for `uvicorn portfolio_manager.main:app`
app = create_app()
