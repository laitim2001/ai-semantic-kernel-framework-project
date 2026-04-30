"""
File: backend/src/infrastructure/db/session.py
Purpose: FastAPI async DB session dependency + per-request transaction wrapper.
Category: Infrastructure / ORM core
Scope: Sprint 49.2 (initial async session dependency)
Owner: infrastructure/db owner

Description:
    Provides:
        get_db_session()  ->  AsyncIterator[AsyncSession]

    Used by FastAPI route handlers via Depends(get_db_session). Each request
    gets a fresh AsyncSession from the singleton factory; the session
    auto-commits on success or rolls back on exception.

    Sprint 49.3 will add per-request `SET LOCAL app.tenant_id = :tid`
    inside this dependency (for PostgreSQL RLS). For 49.2 we just yield
    a clean session.

Created: 2026-04-29 (Sprint 49.2 Day 1.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 1.4)

Related:
    - backend/src/infrastructure/db/engine.py (singleton factory)
    - backend/src/middleware/tenant.py (Sprint 49.3 will set tenant context)
    - 09-db-schema-design.md §RLS Policy
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.engine import get_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency: yield an AsyncSession with auto commit / rollback.

    Usage:
        @router.get("/")
        async def list_things(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = ["get_db_session"]
