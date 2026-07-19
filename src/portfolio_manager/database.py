from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from portfolio_manager.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Shared declarative base — ties SQLAlchemy models (e.g., User from fastapi-users)
# into the same registry as SQLModel so they share MetaData and Alembic sees them all.
Base = SQLModel._sa_registry.generate_base()


async def get_session() -> AsyncSession:
    """Get an async database session."""
    async with async_session_factory() as session:
        yield session
