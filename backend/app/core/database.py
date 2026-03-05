"""
core/database.py

Async SQLAlchemy engine and session factory for PostgreSQL (via asyncpg).
Provides the `get_db` dependency for FastAPI route injection,
`get_standalone_session` for background jobs, and lifecycle functions
for startup/shutdown.

Pool settings are tuned for a mid-traffic API server:
- pool_size=10: baseline connections kept open
- max_overflow=20: burst capacity above pool_size
- pool_recycle=1800: recycle connections every 30 min to avoid stale connections
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings

# Lazy initialisation — engine and session factory are created in init_db()
_engine = None
_async_session_factory = None


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def _create_engine(settings: Settings):
    """Build the async engine with production-safe pool settings."""
    return create_async_engine(
        settings.database_url,
        echo=settings.app_debug,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


async def init_db(settings: Settings) -> None:
    """
    Initialise the database engine and session factory.
    Called once during application startup via the lifespan context manager.
    """
    global _engine, _async_session_factory

    _engine = _create_engine(settings)
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db() -> None:
    """
    Dispose the engine connection pool.
    Called once during application shutdown via the lifespan context manager.
    """
    global _engine, _async_session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.
    Commits on success, rolls back on exception, always closes.

    Usage:
        @router.get("/funds")
        async def list_funds(db: AsyncSession = Depends(get_db)):
            ...
    """
    if _async_session_factory is None:
        raise RuntimeError(
            "Database not initialised. Ensure init_db() is called during app startup."
        )

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_standalone_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager that provides an async DB session OUTSIDE of FastAPI
    request context. Used by background jobs and scheduled tasks.

    Commits on success, rolls back on exception, always closes.

    Usage:
        async with get_standalone_session() as session:
            service = IngestionService(session)
            await service.ingest_all_funds(mstar_ids)
    """
    if _async_session_factory is None:
        raise RuntimeError(
            "Database not initialised. Ensure init_db() is called during app startup."
        )

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
