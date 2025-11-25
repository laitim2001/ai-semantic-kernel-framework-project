"""
Database session management

Provides async database session for SQLAlchemy operations.
"""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# Get database configuration from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ipa_user:ipa_password@localhost:5432/ipa_platform")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

# Convert PostgreSQL URL to async format
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=DB_ECHO,
    poolclass=NullPool,  # Use NullPool for better async support
    pool_pre_ping=DB_POOL_PRE_PING,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for get_session
get_db = get_session
