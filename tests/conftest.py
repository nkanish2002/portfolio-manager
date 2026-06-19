"""Shared test fixtures.

Provides a fresh in-memory SQLite database for every test, with all tables
created and the global ``async_session`` factories in the service modules
swapped to point at it. This lets integration tests run against a real
SQLAlchemy session without touching the on-disk ``portfolio.db``.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portfolio_manager import database
from portfolio_manager.services import charts as charts_svc
from portfolio_manager.services import portfolios as portfolios_svc
from portfolio_manager.services import trades as trades_svc


@pytest_asyncio.fixture(autouse=True)
async def isolated_db(monkeypatch):
    """Replace the global async_session with a fresh in-memory SQLite per test."""
    import portfolio_manager.models  # noqa: F401 — register models with Base.metadata

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    monkeypatch.setattr(database, "async_session", session_factory)
    monkeypatch.setattr(portfolios_svc, "async_session", session_factory)
    monkeypatch.setattr(trades_svc, "async_session", session_factory)
    monkeypatch.setattr(charts_svc, "async_session", session_factory)

    try:
        yield session_factory
    finally:
        await engine.dispose()
