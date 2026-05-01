"""
File: backend/tests/unit/infrastructure/db/test_state_append_only.py
Purpose: AC-4 verification — state_snapshots append-only trigger blocks UPDATE/DELETE.
Category: Tests / Infrastructure / DB / Append-only enforcement
Scope: Sprint 49.2 Day 4.4

Description:
    Migration 0004 installs PostgreSQL trigger
    `state_snapshots_no_update_delete` that raises
    'state_snapshots is append-only' on any UPDATE/DELETE attempt.

    These tests verify:
    1. INSERT works normally
    2. UPDATE raises with the expected message
    3. DELETE raises with the expected message

Created: 2026-04-29 (Sprint 49.2 Day 4.4)
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Session, StateSnapshot, append_snapshot, compute_state_hash
from tests.conftest import seed_tenant, seed_user


@pytest.mark.asyncio
async def test_state_snapshot_can_insert(db_session: AsyncSession) -> None:
    """Normal append works — establishes baseline."""
    t = await seed_tenant(db_session, code="APPONLY_INSERT")
    u = await seed_user(db_session, t, email="ins@test.com")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    snap = await append_snapshot(
        db_session,
        session_id=s.id,
        tenant_id=t.id,
        state_data={"step": 1},
        turn_num=1,
        parent_version=None,
        expected_parent_hash=None,
        reason="turn_end",
    )
    assert snap.version == 1
    assert snap.state_hash == compute_state_hash({"step": 1})
    assert snap.parent_version is None


@pytest.mark.asyncio
async def test_state_snapshot_cannot_update(db_session: AsyncSession) -> None:
    """Direct UPDATE on state_snapshots raises trigger exception."""
    t = await seed_tenant(db_session, code="APPONLY_UPD")
    u = await seed_user(db_session, t, email="upd@test.com")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    snap = await append_snapshot(
        db_session,
        session_id=s.id,
        tenant_id=t.id,
        state_data={"step": 1},
        turn_num=1,
        parent_version=None,
        expected_parent_hash=None,
        reason="turn_end",
    )
    # Need to commit so trigger sees a "real" row to update;
    # but db_session fixture rolls back at end. Workaround: try via raw SQL
    # in same transaction — PG trigger fires regardless of commit boundary.
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(
            update(StateSnapshot).where(StateSnapshot.id == snap.id).values(reason="tampered")
        )
        await db_session.flush()
    assert "append-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_state_snapshot_cannot_delete(db_session: AsyncSession) -> None:
    """Direct DELETE on state_snapshots raises trigger exception."""
    t = await seed_tenant(db_session, code="APPONLY_DEL")
    u = await seed_user(db_session, t, email="del@test.com")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()

    snap = await append_snapshot(
        db_session,
        session_id=s.id,
        tenant_id=t.id,
        state_data={"step": 1},
        turn_num=1,
        parent_version=None,
        expected_parent_hash=None,
        reason="turn_end",
    )
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(delete(StateSnapshot).where(StateSnapshot.id == snap.id))
        await db_session.flush()
    assert "append-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_state_snapshot_truncate_blocked(db_session: AsyncSession) -> None:
    """Per 09.md L702-705 best practice — STATEMENT-level TRUNCATE blocked.

    Sprint 49.3 migration 0005 installs `state_snapshots_no_truncate`
    (BEFORE TRUNCATE FOR EACH STATEMENT). TRUNCATE state_snapshots
    requires CASCADE because sessions.current_state_snapshot_id FKs into
    it; CASCADE lets the trigger fire BEFORE the FK check would
    otherwise reject. The trigger raises 'state_snapshots is append-only'.
    """
    from sqlalchemy import text

    t = await seed_tenant(db_session, code="STATE_TRC2")
    u = await seed_user(db_session, t, email="trc2@state.test")
    s = Session(tenant_id=t.id, user_id=u.id)
    db_session.add(s)
    await db_session.flush()
    await append_snapshot(
        db_session,
        session_id=s.id,
        tenant_id=t.id,
        state_data={"step": 1},
        turn_num=1,
        parent_version=None,
        expected_parent_hash=None,
        reason="bootstrap",
    )
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(text("TRUNCATE state_snapshots CASCADE"))
        await db_session.flush()
    assert "state_snapshots is append-only" in str(exc_info.value)
