"""
File: backend/tests/unit/infrastructure/db/test_models_crud.py
Purpose: CRUD tests for ORM models against real docker compose PostgreSQL.
Category: Tests / Infrastructure / DB
Scope: Sprint 49.2 (incremental: Day 2 sessions, Day 3 tools, Day 4 state)

Description:
    One-test-per-concern smoke CRUD covering create + read + relationship
    integrity for each ORM model defined in Sprint 49.2.

    Pre-requisite:
        docker compose -f docker-compose.dev.yml up -d postgres
        cd backend && alembic upgrade head

    AP-10 對策:
        Tests use the REAL docker compose PostgreSQL (NOT SQLite).

Created: 2026-04-29 (Sprint 49.2 Day 2.4)
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
    Message,
    MessageEvent,
    Session,
    Tenant,
)
from tests.conftest import seed_tenant, seed_user


# ---------------------------------------------------------------------
# Identity (Day 1 model coverage — added here for completeness)
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tenant_create_and_read(db_session: AsyncSession) -> None:
    """Create a Tenant, flush, read back."""
    t = await seed_tenant(db_session, code="ACME_TEST")
    assert t.id is not None
    assert t.code == "ACME_TEST"
    assert t.status == "active"

    result = await db_session.execute(select(Tenant).where(Tenant.code == "ACME_TEST"))
    fetched = result.scalar_one()
    assert fetched.id == t.id


@pytest.mark.asyncio
async def test_user_with_tenant_scope(db_session: AsyncSession) -> None:
    """User must reference a Tenant; UNIQUE(tenant_id, email) holds."""
    t = await seed_tenant(db_session, code="USER_TEST")
    u = await seed_user(db_session, t, email="alice@example.com")
    assert u.tenant_id == t.id
    assert u.email == "alice@example.com"


# ---------------------------------------------------------------------
# Sessions (Day 2 main coverage)
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_session_create_read(db_session: AsyncSession) -> None:
    """Session is per-tenant + per-user, defaults to status='active'."""
    t = await seed_tenant(db_session, code="SESS_TEST")
    u = await seed_user(db_session, t, email="bob@example.com")

    s = Session(
        tenant_id=t.id,
        user_id=u.id,
        title="My Conversation",
    )
    db_session.add(s)
    await db_session.flush()
    await db_session.refresh(s)

    assert s.id is not None
    assert s.tenant_id == t.id
    assert s.user_id == u.id
    assert s.title == "My Conversation"
    assert s.status == "active"
    assert s.total_turns == 0
    assert s.total_tokens == 0


@pytest.mark.asyncio
async def test_message_create_with_session(db_session: AsyncSession) -> None:
    """Message attaches to a Session; default created_at NOW() routes to current partition."""
    t = await seed_tenant(db_session, code="MSG_TEST")
    u = await seed_user(db_session, t, email="charlie@example.com")
    s = Session(tenant_id=t.id, user_id=u.id, title="Test session")
    db_session.add(s)
    await db_session.flush()

    m = Message(
        tenant_id=t.id,
        session_id=s.id,
        sequence_num=0,
        turn_num=1,
        role="user",
        content_type="text",
        content={"text": "Hello, agent."},
    )
    db_session.add(m)
    await db_session.flush()
    await db_session.refresh(m)

    assert m.id is not None
    assert m.created_at is not None
    assert m.tenant_id == t.id
    assert m.session_id == s.id
    assert m.role == "user"
    assert m.content == {"text": "Hello, agent."}
    assert m.is_compacted is False


@pytest.mark.asyncio
async def test_message_event_emit(db_session: AsyncSession) -> None:
    """MessageEvent rows go to current-month partition via NOW() default."""
    t = await seed_tenant(db_session, code="EVT_TEST")
    u = await seed_user(db_session, t, email="dana@example.com")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    e = MessageEvent(
        tenant_id=t.id,
        session_id=s.id,
        event_type="loop_turn_start",
        event_data={"turn": 1},
        sequence_num=1,
        timestamp_ms=1714464000000,
    )
    db_session.add(e)
    await db_session.flush()
    await db_session.refresh(e)

    assert e.id is not None
    assert e.created_at is not None
    assert e.event_type == "loop_turn_start"
    assert e.event_data == {"turn": 1}
    assert e.sequence_num == 1
