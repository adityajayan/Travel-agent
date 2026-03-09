from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from db.models import Base

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _is_sqlite() -> bool:
    return settings.database_url.startswith("sqlite")


async def init_db() -> None:
    """Auto-create tables for SQLite (dev/test). For PostgreSQL, use Alembic migrations."""
    if not _is_sqlite():
        return  # PostgreSQL uses Alembic
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
