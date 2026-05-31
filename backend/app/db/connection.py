from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return the shared async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        current_settings = settings or get_settings()
        _engine = create_async_engine(current_settings.database_url, pool_pre_ping=True)
    return _engine


def get_session_maker(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Return the shared async session maker."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            bind=get_engine(settings),
            expire_on_commit=False,
        )
    return _session_maker


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependencies."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


async def check_database_connection() -> bool:
    """Return whether the configured database accepts a trivial query."""
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


async def close_database_connections() -> None:
    """Dispose the shared async SQLAlchemy engine."""
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_maker = None
