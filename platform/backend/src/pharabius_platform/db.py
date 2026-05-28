"""Database session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    """Initialize database engine and session factory."""
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        yield session


async def close_db() -> None:
    """Dispose of the database engine."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
