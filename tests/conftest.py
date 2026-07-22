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


async def _dispose_module_engines() -> None:
    """Dispose module-level engines bound to the test DB so DROP DATABASE works."""
    import contextlib

    import portfolio_manager.database as db
    import portfolio_manager.main as main_mod

    for engine in (getattr(db, "engine", None), getattr(main_mod, "engine", None)):
        if engine is None:
            continue
        with contextlib.suppress(Exception):
            await engine.dispose()


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

    # free any module-level connections to the test DB before dropping it
    asyncio.run(_dispose_module_engines())
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
        original_db_factory = database.async_session_factory
        original_db_engine = database.engine
        original_main_engine = main_mod.engine

        auth_mod.async_session_factory = test_session_factory
        database.async_session_factory = test_session_factory
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
            database.async_session_factory = original_db_factory
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


# ── Domain helpers for route tests ───────────────────────────────────────
# These create entities via the API (accounts, baskets) or directly via the
# DB session (assets — there's no asset CRUD endpoint), returning the row.


@pytest_asyncio.fixture
async def make_account(client):
    """POST an account via the API; returns the created AccountRead dict."""

    async def _make(name: str = "Wacky", institution: str = "Schwab"):
        r = await client.post(
            "/api/v1/accounts/",
            json={"name": name, "institution": institution, "account_number": "1234"},
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _make


@pytest_asyncio.fixture
async def make_basket(client):
    """POST a basket via the API; returns the created BasketRead dict."""

    async def _make(name: str = "High Beta", color: str = "#ff7b00", target_allocation: float = 40.0):
        r = await client.post(
            "/api/v1/baskets/",
            json={
                "name": name,
                "color": color,
                "target_allocation": target_allocation,
                "description": f"{name} basket",
                "sort_order": 0,
            },
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _make


@pytest_asyncio.fixture
async def make_portfolio(client, make_account):
    """POST a portfolio via the API; returns the created PortfolioRead dict."""

    async def _make(account: dict | None = None, basket_id: str | None = None, name: str = "Main"):
        account = account or await make_account()
        payload = {"name": name, "account_id": account["id"], "currency": "USD"}
        if basket_id is not None:
            payload["basket_id"] = basket_id
        r = await client.post("/api/v1/portfolios/", json=payload)
        assert r.status_code == 201, r.text
        return r.json()

    return _make


@pytest_asyncio.fixture
async def make_asset(db_session):
    """Insert an Asset row directly (no asset CRUD endpoint); returns the Asset."""

    async def _make(symbol: str = "AAPL", name: str = "Apple Inc", asset_class: str = "equity",
                    sector: str = "Technology", region: str = "United States"):
        from portfolio_manager.models import Asset

        asset = Asset(symbol=symbol, name=name, asset_class=asset_class, sector=sector, region=region)
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        return asset

    return _make


# ── Fake data feed for route tests (positions refresh / analytics) ──────
# Patches the module-level data_feed used by routes so tests are network-free.


@pytest_asyncio.fixture
async def fake_data_feed(monkeypatch):
    """Install a deterministic in-memory DataFeed for routes that use it.

    Returns a small helper to register price/quote/history data per symbol.
    """
    import sys
    from datetime import date
    df_mod = sys.modules["portfolio_manager.services.data_feed"]  # real submodule (not the shadowed singleton)
    from portfolio_manager.services.data_feed import DataFeed, PriceBar, PriceQuote
    from portfolio_manager.services.price_cache import PriceCache

    cache: PriceCache[PriceQuote] = PriceCache(default_ttl=60)
    feed = DataFeed(cache, enabled=True)

    class _FakeFetcher:
        def __init__(self):
            self._quotes: dict[str, PriceQuote] = {}
            self._history: dict[str, list[PriceBar]] = {}

        def quote(self, symbol):
            return self._quotes.get(symbol.upper())

        def history(self, symbol, period):
            return self._history.get(symbol.upper(), [])

        def search(self, query, max_results=10):
            return []

    fetcher = _FakeFetcher()
    feed._fetcher = fetcher  # type: ignore[attr-defined]
    # point the module singleton (used by routes) at our feed
    monkeypatch.setattr(df_mod, "data_feed", feed)
    # also patch the import inside the routes modules
    from portfolio_manager.routes import analytics, positions, reports

    monkeypatch.setattr(positions, "data_feed", feed)
    monkeypatch.setattr(analytics, "data_feed", feed)
    monkeypatch.setattr(reports, "data_feed", feed)

    feed.fetcher = fetcher  # expose for tests

    def add_quote(symbol, price, prev_close=None):
        fetcher._quotes[symbol.upper()] = PriceQuote(
            symbol=symbol.upper(), price=price, prev_close=prev_close, currency="USD"
        )

    def add_history(symbol, prices):
        from datetime import timedelta

        start = date(2026, 1, 1)
        bars = [
            PriceBar(date=start + timedelta(days=i), open=p, high=p, low=p, close=p, volume=0)
            for i, p in enumerate(prices)
        ]
        fetcher._history[symbol.upper()] = bars

    feed.add_quote = add_quote  # type: ignore[attr-defined]
    feed.add_history = add_history  # type: ignore[attr-defined]
    return feed
