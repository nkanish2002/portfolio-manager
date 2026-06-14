"""SQLAlchemy async engine, session, and base model."""

import sqlite3
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from portfolio_manager.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _adapt_uuid(u: UUID) -> str:
    """Convert UUID to string for SQLite storage."""
    return str(u)


def _convert_uuid(s: bytes) -> UUID:
    """Convert SQLite bytes back to UUID."""
    return UUID(s.decode())


# Register SQLite adapters for UUIDs
if "sqlite" in settings.database_url:
    sqlite3.register_adapter(UUID, _adapt_uuid)
    sqlite3.register_converter("UUID", _convert_uuid)


async def get_db() -> AsyncSession:
    """FastAPI dependency for a DB session."""
    async with async_session() as session:
        yield session


async def init_db():
    """Create all tables. Imports models so they're registered with Base.metadata."""
    import portfolio_manager.models  # noqa: F401 -- register models with SQLAlchemy

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
