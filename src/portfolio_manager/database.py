"""SQLAlchemy async engine, session, and base model."""

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from portfolio_manager.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)

# Create a Jinja2 Environment with caching disabled (Python 3.14 compatibility fix)
# where Jinja2 uses unhashable dict keys in its internal cache.
jinja_env = Environment(
    loader=FileSystemLoader(settings.template_dir),
    autoescape=True,
    cache_size=0,
)
templates = Jinja2Templates(env=jinja_env)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency for a DB session."""
    async with async_session() as session:
        yield session


async def init_db():
    """Create all tables. Imports models so they're registered with Base.metadata."""
    import portfolio_manager.models  # noqa: F401 -- register models with SQLAlchemy

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
