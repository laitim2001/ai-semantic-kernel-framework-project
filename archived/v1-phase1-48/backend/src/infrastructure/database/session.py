# =============================================================================
# IPA Platform - Database Session Management
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Async SQLAlchemy session management with connection pooling.
# Provides FastAPI dependency injection for database sessions.
# =============================================================================

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.config import get_settings


# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """
    Get or create the SQLAlchemy async engine.

    Uses connection pooling with configurable pool size.
    For testing, uses NullPool to avoid connection issues.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance
    """
    global _engine

    if _engine is None:
        settings = get_settings()

        # Build engine arguments
        engine_kwargs = {
            "echo": settings.app_env == "development",  # SQL logging in dev
            "pool_pre_ping": True,  # Connection health check
        }

        # For testing, use NullPool to avoid connection issues
        if settings.app_env == "testing":
            engine_kwargs["poolclass"] = NullPool
        else:
            # Connection pool settings for production
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10

        _engine = create_async_engine(settings.database_url, **engine_kwargs)

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the session factory.

    Returns:
        async_sessionmaker: Session factory for creating new sessions
    """
    global _session_factory

    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Yields a new session for each request and ensures proper cleanup.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def DatabaseSession() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside of FastAPI.

    Usage:
        async with DatabaseSession() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database connection.

    Should be called during application startup.
    Creates the engine and verifies connectivity.
    """
    engine = get_engine()
    # Verify connection
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)


async def close_db() -> None:
    """
    Close database connections.

    Should be called during application shutdown.
    Disposes of the engine and closes all connections.
    """
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def reset_db() -> None:
    """
    Reset database connections (for testing).

    Closes and recreates the engine and session factory.
    """
    await close_db()
    get_engine()
    get_session_factory()
