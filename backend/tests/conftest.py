"""
File: backend/tests/conftest.py
Purpose: Shared pytest fixtures + seed helpers for V2 backend tests.
Category: Tests / Infrastructure
Scope: Sprint 49.2 Day 2.3 (initial conftest + db_session + seed helpers)

Description:
    Provides:
        db_session: per-test AsyncSession with rollback at end (real docker
                    compose PostgreSQL — AP-10 對策, no SQLite).
        seed_tenant: helper to create + flush a Tenant.
        seed_user: helper to create + flush a User under a tenant.

    Pre-requisite for tests using db_session:
        docker compose -f docker-compose.dev.yml up -d postgres
        cd backend && alembic upgrade head

Created: 2026-04-29 (Sprint 49.2 Day 2.3)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 2.3)

Related:
    - .claude/rules/testing.md (testing rules + AP-10 對策)
    - infrastructure/db/engine.py (singleton factory)
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import dispose_engine, get_session_factory
from infrastructure.db.models import Tenant, User


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncIterator[AsyncSession]:
    """Per-test AsyncSession with rollback + engine disposal at end.

    Why dispose_engine() per-test:
        pytest-asyncio defaults to per-test event loops. The singleton
        AsyncEngine in infrastructure.db.engine is bound to whichever
        loop first created it; subsequent tests run in new loops and
        hit RuntimeError('Event loop is closed') on pooled connections.
        Disposing the engine after each test forces a fresh engine on
        the next test's loop. Slight perf cost (~10 ms / test) is the
        right trade for correctness + isolation.

    Caller may flush + use ORM normally; pending changes are rolled
    back at fixture teardown so each test sees a clean DB state.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
    await dispose_engine()


async def seed_tenant(
    session: AsyncSession, *, code: str = "TEST_TENANT", display_name: str | None = None
) -> Tenant:
    """Create + flush a Tenant. Caller must NOT commit — fixture rollback handles cleanup."""
    t = Tenant(code=code, display_name=display_name or f"Tenant {code}")
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t


async def seed_user(
    session: AsyncSession,
    tenant: Tenant,
    *,
    email: str = "user@test.com",
    display_name: str | None = None,
) -> User:
    """Create + flush a User scoped to the given tenant."""
    u = User(
        tenant_id=tenant.id,
        email=email,
        display_name=display_name or email.split("@")[0],
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u
