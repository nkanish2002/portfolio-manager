"""Authentication module — fastapi-users with JWT strategy.

Sets up user manager, JWT auth backend, and exports dependency callables
for route-level authentication (current_active_user, current_user).
"""

import os
from uuid import UUID

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate

from portfolio_manager.config import settings
from portfolio_manager.database import async_session_factory
from portfolio_manager.models.user import User

# ── User schemas (extend fastapi-users base) ──────────────────────────────

class UserRead(BaseUser):
    """Public user schema returned in API responses."""

    display_name: str | None = None


class UserCreate(BaseUserCreate):
    """Schema for user registration."""

    display_name: str | None = None


class UserUpdate(BaseUserUpdate):
    """Schema for user profile updates."""

    display_name: str | None = None


# ── User manager ──────────────────────────────────────────────────────────

class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    """Custom user manager with JWT tokens for password reset / verification."""

    reset_password_token_secret = settings.JWT_SECRET
    reset_password_token_lifetime_seconds = settings.JWT_LIFETIME_SECONDS

    verification_token_secret = settings.JWT_SECRET
    verification_token_lifetime_seconds = 3600 * 24  # 24h for email verification

    async def on_after_register(self, user: User, request=None) -> None:
        """Hook after successful registration."""
        # No email sending in dev — verified by default
        if os.environ.get("ENV_FOR_DYNACONF", "development") == "development":
            await self._update(user, {"is_verified": True})

    async def on_after_forgot_password(self, user: User, token: str, request=None) -> None:
        """Hook after password reset request (would send email in prod)."""
        pass  # TODO: send reset email with token


# ── Database adapter factory ──────────────────────────────────────────────

async def get_user_db():
    """Yield a SQLAlchemy user database adapter with a scoped session."""
    async with async_session_factory() as session:
        yield SQLAlchemyUserDatabase(session, User)


# ── User manager factory ──────────────────────────────────────────────────

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):  # noqa: B008
    """Yield the user manager bound to a request-scoped DB adapter."""
    yield UserManager(user_db)


# ── JWT strategy ──────────────────────────────────────────────────────────

def get_jwt_strategy() -> JWTStrategy:
    """Return the JWT authentication strategy."""
    return JWTStrategy(
        secret=settings.JWT_SECRET,
        lifetime_seconds=settings.JWT_LIFETIME_SECONDS,
        algorithm=settings.JWT_ALGORITHM,
    )


# ── Authentication backend ────────────────────────────────────────────────

bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# ── FastAPIUsers instance ─────────────────────────────────────────────────

fastapi_users = FastAPIUsers(
    get_user_manager,
    [auth_backend],
)


# ── Dependency callables ──────────────────────────────────────────────────

current_active_user = fastapi_users.authenticator.current_user(active=True)
"""Dependency: current active authenticated user. 401 if missing/inactive."""

current_user = fastapi_users.authenticator.current_user()
"""Dependency: current authenticated user (active or inactive)."""
