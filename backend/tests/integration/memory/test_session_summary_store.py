"""
File: backend/tests/integration/memory/test_session_summary_store.py
Purpose: Real-DB tests for DBSessionSummaryStore (Sprint 57.151 session recall).
Category: Tests / Integration / 範疇 3
Scope: Phase 57 / Sprint 57.151 (US-1, US-3)

Description:
    Requires a live PostgreSQL with `alembic upgrade head` (per conftest db_session)
    so memory_session_summary.updated_at (0033) + the session_id UNIQUE exist.
    Verifies the upsert keeps one row per session, and that recent_for_user JOINs
    sessions to scope by tenant + user, excludes the current session, and orders by
    updated_at DESC.

    Uses the commit→flush shared-session trick (mirrors test_user_layer_dedup.py) so
    writes live in the test transaction and roll back at teardown; ON CONFLICT still
    sees the flushed first row within the same transaction.

    Note on updated_at: PostgreSQL func.now() is the TRANSACTION start time (stable
    within a txn), so two upserts in one test txn share an updated_at. The ordering
    test therefore seeds rows directly with EXPLICIT distinct updated_at; the
    "updated_at bumps across turns" behavior is a cross-transaction property verified
    in the drive-through, not assertable in a single-txn test.

Created: 2026-06-30 (Sprint 57.151)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness.memory.session_summary_store import DBSessionSummaryStore
from infrastructure.db.models.memory import MemorySessionSummary
from infrastructure.db.models.sessions import Session as SessionRow
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


def _shared_factory(db_session: AsyncSession) -> Callable[[], object]:
    """Yield the test session; treat commit as flush so the test txn rolls back."""

    @asynccontextmanager
    async def _factory() -> AsyncIterator[AsyncSession]:
        orig_commit = db_session.commit
        db_session.commit = db_session.flush  # type: ignore[method-assign]
        try:
            yield db_session
        finally:
            db_session.commit = orig_commit  # type: ignore[method-assign]

    return _factory


async def _seed_session(db_session: AsyncSession, tenant_id: UUID, user_id: UUID) -> UUID:
    """Create + flush a sessions row (the recall JOIN target); return its id."""
    s = SessionRow(tenant_id=tenant_id, user_id=user_id)
    db_session.add(s)
    await db_session.flush()
    await db_session.refresh(s)
    return s.id


async def _seed_summary(
    db_session: AsyncSession,
    *,
    session_id: UUID,
    summary: str,
    updated_at: datetime,
    unresolved: list[str] | None = None,
) -> None:
    """Insert a memory_session_summary row directly with an EXPLICIT updated_at."""
    db_session.add(
        MemorySessionSummary(
            id=uuid4(),
            session_id=session_id,
            summary=summary,
            key_decisions=[],
            unresolved_issues=unresolved or [],
            updated_at=updated_at,
        )
    )
    await db_session.flush()


async def _summary_count(db_session: AsyncSession, session_id: UUID) -> int:
    return (
        await db_session.execute(
            select(func.count())
            .select_from(MemorySessionSummary)
            .where(MemorySessionSummary.session_id == session_id)
        )
    ).scalar_one()


async def test_upsert_same_session_one_row(db_session: AsyncSession) -> None:
    """A second upsert for the same session UPDATEs the one row (the session_id
    UNIQUE), refreshing summary / key_decisions / unresolved_issues — not a 2nd row."""
    t = await seed_tenant(db_session, code="SUMM_UP")
    u = await seed_user(db_session, t, email="up@summ.test")
    sid = await _seed_session(db_session, t.id, u.id)

    store = DBSessionSummaryStore(_shared_factory(db_session))  # type: ignore[arg-type]
    id1 = await store.upsert_summary(
        session_id=sid, summary="first pass", key_decisions=["a"], unresolved_issues=["x"]
    )
    id2 = await store.upsert_summary(
        session_id=sid, summary="refined pass", key_decisions=["a", "b"], unresolved_issues=[]
    )

    assert id1 == id2  # upsert returned the existing row id
    assert await _summary_count(db_session, sid) == 1

    row = (
        await db_session.execute(
            select(MemorySessionSummary).where(MemorySessionSummary.session_id == sid)
        )
    ).scalar_one()
    assert row.summary == "refined pass"
    assert row.key_decisions == ["a", "b"]
    assert row.unresolved_issues == []


async def test_recent_for_user_orders_and_excludes(db_session: AsyncSession) -> None:
    """recent_for_user returns the user's summaries updated_at DESC and excludes the
    passed current session."""
    t = await seed_tenant(db_session, code="SUMM_ORD")
    u = await seed_user(db_session, t, email="ord@summ.test")
    s_old = await _seed_session(db_session, t.id, u.id)
    s_mid = await _seed_session(db_session, t.id, u.id)
    s_cur = await _seed_session(db_session, t.id, u.id)

    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    await _seed_summary(db_session, session_id=s_old, summary="oldest", updated_at=base)
    await _seed_summary(
        db_session,
        session_id=s_mid,
        summary="middle",
        updated_at=base + timedelta(hours=1),
        unresolved=["open Q"],
    )
    await _seed_summary(
        db_session, session_id=s_cur, summary="current", updated_at=base + timedelta(hours=2)
    )

    store = DBSessionSummaryStore(_shared_factory(db_session))  # type: ignore[arg-type]
    rows = await store.recent_for_user(
        tenant_id=t.id, user_id=u.id, exclude_session_id=s_cur, limit=10
    )

    # s_cur excluded; the rest newest-first.
    assert [r.session_id for r in rows] == [s_mid, s_old]
    assert rows[0].summary == "middle"
    assert rows[0].unresolved_issues == ["open Q"]


async def test_recent_for_user_per_tenant_isolation(db_session: AsyncSession) -> None:
    """A user's recall never crosses tenants (the JOIN filters sessions.tenant_id)."""
    t_a = await seed_tenant(db_session, code="SUMM_T_A")
    t_b = await seed_tenant(db_session, code="SUMM_T_B")
    u_a = await seed_user(db_session, t_a, email="a@summ.test")
    u_b = await seed_user(db_session, t_b, email="b@summ.test")
    s_a = await _seed_session(db_session, t_a.id, u_a.id)
    s_b = await _seed_session(db_session, t_b.id, u_b.id)

    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    await _seed_summary(db_session, session_id=s_a, summary="tenant A secret", updated_at=base)
    await _seed_summary(db_session, session_id=s_b, summary="tenant B secret", updated_at=base)

    store = DBSessionSummaryStore(_shared_factory(db_session))  # type: ignore[arg-type]
    rows_a = await store.recent_for_user(
        tenant_id=t_a.id, user_id=u_a.id, exclude_session_id=None, limit=10
    )
    assert [r.summary for r in rows_a] == ["tenant A secret"]  # 0 B leak


async def test_recent_for_user_per_user_isolation(db_session: AsyncSession) -> None:
    """Two users in the SAME tenant only see their own sessions (filters user_id)."""
    t = await seed_tenant(db_session, code="SUMM_USR")
    u1 = await seed_user(db_session, t, email="u1@summ.test")
    u2 = await seed_user(db_session, t, email="u2@summ.test")
    s1 = await _seed_session(db_session, t.id, u1.id)
    s2 = await _seed_session(db_session, t.id, u2.id)

    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    await _seed_summary(db_session, session_id=s1, summary="u1 work", updated_at=base)
    await _seed_summary(db_session, session_id=s2, summary="u2 work", updated_at=base)

    store = DBSessionSummaryStore(_shared_factory(db_session))  # type: ignore[arg-type]
    rows_1 = await store.recent_for_user(
        tenant_id=t.id, user_id=u1.id, exclude_session_id=None, limit=10
    )
    assert [r.summary for r in rows_1] == ["u1 work"]  # 0 u2 leak


async def test_recent_for_user_empty_when_none(db_session: AsyncSession) -> None:
    """A user with no session summaries recalls nothing (not an error)."""
    t = await seed_tenant(db_session, code="SUMM_EMP")
    u = await seed_user(db_session, t, email="emp@summ.test")
    await db_session.flush()

    store = DBSessionSummaryStore(_shared_factory(db_session))  # type: ignore[arg-type]
    rows = await store.recent_for_user(
        tenant_id=t.id, user_id=u.id, exclude_session_id=None, limit=10
    )
    assert rows == []
