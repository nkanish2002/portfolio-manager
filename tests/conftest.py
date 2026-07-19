"""Pytest configuration — async Postgres test DB, test client, auth fixtures.

Strategy:
  * A dedicated ``portfolio_manager_test`` database is created/destroyed per
    test session in the same local Postgres instance (sync fixture using
    ``asyncio.run`` so it owns a throwaway loop).
  * Alembic migrations are applied to it (no metadata.create_all) so the
    migration itself is exercised by the test suite.
  * The async engine is function-scoped so it lives on each test's event loop
    (avoids "Future attached to a different loop" errors).
  * All tables are TRUNCATEd between tests for isolation.
  * The FastAPI app's DB layer is repointed at the test engine via dependency
    overrides and module patching.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Point everything at the test database *before* the app is imported.
TEST_DB_NAME = "portfolio_manager_test"
TEST_DB_URL = f"postgresql+asyncpg://portfolio:portfolio@localhost:5432/{TEST_DB_NAME}"
PG_DSN = "postgresql://portfolio:portfolio@localhost:5432/postgres"

os.environ["PORTFOLIO_MANAGER_DATABASE_URL"] = TEST_DB_URL
os.environ["ENV_FOR_DYNACONF"] = "development"

# Import app + DB layer after env is configured.
from portfolio_manager import database  # noqa: E402
from portfolio_manager.auth import get_user_db  # noqa: E402
from portfolio_manager.main import app  # noqa: E402

# ── Session-scoped (SYNC): create test DB + apply migrations ──────────────


async def _create_test_db() -> None:
    admin_conn = await asyncpg.connect(PG_DSN)
    try:
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
        await admin_conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await admin_conn.close()


async def _drop_test_db() -> None:
    admin_conn = await asyncpg.connect(PG_DSN)
    try:
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
    finally:
        await admin_conn.close()


@pytest.fixture(scope="session")
def test_db() -> Iterator[None]:
    """Create the test database + apply migrations for the whole session."""
    asyncio.run(_create_test_db())

    env = {**os.environ, "PORTFOLIO_MANAGER_DATABASE_URL": TEST_DB_URL}
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        check=True,
        env=env,
        capture_output=True,
    )

    yield

    asyncio.run(_drop_test_db())


# ── Function-scoped async: engine + session factory ───────────────────────


@asynccontextmanager
async def _truncate_all(engine) -> AsyncIterator[None]:
    """TRUNCATE every table (except alembic_version) cascade, between tests."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE assets, accounts, baskets, portfolios, positions, "
                "transactions, benchmarks, benchmark_data, portfolio_benchmarks, users "
                "RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest_asyncio.fixture
async def test_engine(test_db) -> AsyncIterator[Any]:
    """Per-test async engine bound to the test database (lives on test loop)."""
    engine = create_async_engine(TEST_DB_URL, echo=False, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine) -> async_sessionmaker[AsyncSession]:
    """Session factory bound to the per-test engine."""
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(test_engine, test_session_factory) -> AsyncIterator[AsyncSession]:
    """Per-test clean DB session, with tables truncated first.

    Also repoints the FastAPI app's DB layer at the test engine so that
    HTTP-backed routes (auth, health/db) hit the test database.
    """
    async with _truncate_all(test_engine), test_session_factory() as session:
        from portfolio_manager import auth as auth_mod
        from portfolio_manager import main as main_mod

        original_auth_factory = auth_mod.async_session_factory
        original_db_engine = database.engine
        original_main_engine = main_mod.engine

        auth_mod.async_session_factory = test_session_factory
        database.engine = test_engine
        main_mod.engine = test_engine

        async def override_get_user_db():
            from fastapi_users.db import SQLAlchemyUserDatabase

            from portfolio_manager.models.user import User

            sess = test_session_factory()
            try:
                yield SQLAlchemyUserDatabase(sess, User)
            finally:
                await sess.close()

        app.dependency_overrides[get_user_db] = override_get_user_db

        try:
            yield session
        finally:
            app.dependency_overrides.pop(get_user_db, None)
            auth_mod.async_session_factory = original_auth_factory
            database.engine = original_db_engine
            main_mod.engine = original_main_engine


# ── HTTP client fixtures ─────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session) -> AsyncIterator[AsyncClient]:
    """Anonymous HTTP client backed by the ASGI app (clean DB)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client) -> AsyncIterator[AsyncClient]:
    """Authenticated client: registers a user, logs in, attaches Bearer token."""
    import secrets

    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    password = secrets.token_urlsafe(12)

    reg = await client.post(
        "/auth/jwt/register",
        json={"email": email, "password": password, "display_name": "Tester"},
    )
    assert reg.status_code == 201, reg.text

    login = await client.post(
        "/auth/jwt/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client


# ── Shared user factory ──────────────────────────────────────────────────


@pytest_asyncio.fixture
async def make_user(client):
    """Factory to register+login arbitrary users, returning email/password/token."""

    async def _make(display_name: str | None = None):
        import secrets

        email = f"u-{uuid.uuid4().hex[:8]}@example.com"
        password = secrets.token_urlsafe(12)
        payload = {"email": email, "password": password}
        if display_name is not None:
            payload["display_name"] = display_name
        r = await client.post("/auth/jwt/register", json=payload)
        assert r.status_code == 201, r.text
        login = await client.post(
            "/auth/jwt/login", data={"username": email, "password": password}
        )
        assert login.status_code == 200, login.text
        return {"email": email, "password": password, "token": login.json()["access_token"]}

    return _make
