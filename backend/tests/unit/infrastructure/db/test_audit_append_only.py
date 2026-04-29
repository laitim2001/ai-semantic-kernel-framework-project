"""
File: backend/tests/unit/infrastructure/db/test_audit_append_only.py
Purpose: AC-2/AC-3 verification — audit_log append-only triggers + hash chain integrity.
Category: Tests / Infrastructure / DB / Append-only enforcement
Scope: Sprint 49.3 Day 1.5

Description:
    Migration 0005 installs:
        - prevent_audit_modification() plpgsql function
        - audit_log_no_update_delete (ROW BEFORE UPDATE OR DELETE)
        - audit_log_no_truncate (STATEMENT BEFORE TRUNCATE)
        - state_snapshots_no_truncate (STATEMENT BEFORE TRUNCATE; 49.2 deferred)

    Tests verify:
        1. INSERT works normally (baseline + first-row sentinel hash)
        2. UPDATE raises DBAPIError 'audit_log is append-only'
        3. DELETE raises DBAPIError 'audit_log is append-only'
        4. TRUNCATE on audit_log raises DBAPIError 'audit_log is append-only'
        5. TRUNCATE on state_snapshots raises DBAPIError (49.2 carryover fix)
        6. Hash chain integrity: 3 successive rows form valid SHA-256 chain
           starting from SENTINEL_HASH; each row's previous_log_hash matches
           the prior row's current_log_hash; current_log_hash matches
           independent compute_audit_hash() recomputation.

Created: 2026-04-29 (Sprint 49.3 Day 1.5)
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.audit_helper import (SENTINEL_HASH, append_audit,
                                            compute_audit_hash)
from infrastructure.db.models import AuditLog, Session, append_snapshot
from tests.conftest import seed_tenant, seed_user


@pytest.mark.asyncio
async def test_audit_can_insert(db_session: AsyncSession) -> None:
    """Baseline append works; first row uses SENTINEL_HASH."""
    t = await seed_tenant(db_session, code="AUDIT_INS")
    u = await seed_user(db_session, t, email="ins@audit.test")

    row = await append_audit(
        db_session,
        tenant_id=t.id,
        user_id=u.id,
        operation="tool_executed",
        resource_type="tool",
        resource_id="echo_tool",
        operation_data={"args": {"x": 1}},
        operation_result="success",
    )
    assert row.id is not None
    assert row.previous_log_hash == SENTINEL_HASH
    # current_log_hash must equal independent recomputation
    expected = compute_audit_hash(
        previous_log_hash=SENTINEL_HASH,
        operation_data={"args": {"x": 1}},
        tenant_id=t.id,
        timestamp_ms=row.timestamp_ms,
    )
    assert row.current_log_hash == expected


@pytest.mark.asyncio
async def test_audit_cannot_update(db_session: AsyncSession) -> None:
    """UPDATE on audit_log raises trigger exception."""
    t = await seed_tenant(db_session, code="AUDIT_UPD")
    u = await seed_user(db_session, t, email="upd@audit.test")

    row = await append_audit(
        db_session,
        tenant_id=t.id,
        user_id=u.id,
        operation="approval_granted",
        resource_type="approval",
        operation_data={"approver": str(u.id)},
    )
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(
            update(AuditLog).where(AuditLog.id == row.id).values(operation="tampered")
        )
        await db_session.flush()
    assert "audit_log is append-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_audit_cannot_delete(db_session: AsyncSession) -> None:
    """DELETE on audit_log raises trigger exception."""
    t = await seed_tenant(db_session, code="AUDIT_DEL")
    u = await seed_user(db_session, t, email="del@audit.test")

    row = await append_audit(
        db_session,
        tenant_id=t.id,
        user_id=u.id,
        operation="state_committed",
        resource_type="state",
        operation_data={"version": 1},
    )
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(delete(AuditLog).where(AuditLog.id == row.id))
        await db_session.flush()
    assert "audit_log is append-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_audit_cannot_truncate(db_session: AsyncSession) -> None:
    """STATEMENT-level TRUNCATE on audit_log raises trigger exception."""
    t = await seed_tenant(db_session, code="AUDIT_TRC")
    await append_audit(
        db_session,
        tenant_id=t.id,
        operation="anchor",
        resource_type="bootstrap",
        operation_data={"phase": "test"},
    )
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(text("TRUNCATE audit_log"))
        await db_session.flush()
    assert "audit_log is append-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_state_snapshots_cannot_truncate(db_session: AsyncSession) -> None:
    """49.2 carryover fix: STATEMENT-level TRUNCATE on state_snapshots raises.

    Sprint 49.2 only had ROW UPDATE/DELETE trigger; TRUNCATE bypassed ROW
    triggers. Migration 0005 installs the STATEMENT-level trigger.
    """
    t = await seed_tenant(db_session, code="STATE_TRC")
    u = await seed_user(db_session, t, email="trc@state.test")
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
    # Use CASCADE so that the trigger can fire BEFORE FK-check fails:
    # plain TRUNCATE state_snapshots is rejected by FK reference from
    # sessions.current_state_snapshot_id; CASCADE bypasses the FK check
    # and exercises the BEFORE STATEMENT trigger we installed in 0005.
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(text("TRUNCATE state_snapshots CASCADE"))
        await db_session.flush()
    assert "state_snapshots is append-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_audit_hash_chain_integrity(db_session: AsyncSession) -> None:
    """Append 3 rows; verify SENTINEL bootstrap + chain linkage + recomputation.

    Row 1: previous_log_hash == SENTINEL_HASH
    Row 2: previous_log_hash == row1.current_log_hash
    Row 3: previous_log_hash == row2.current_log_hash
    For each row: current_log_hash == compute_audit_hash(prev, payload, tenant, ts)
    """
    t = await seed_tenant(db_session, code="AUDIT_CHAIN")
    u = await seed_user(db_session, t, email="chain@audit.test")

    payloads = [
        {"step": 1, "kind": "boot"},
        {"step": 2, "kind": "tool"},
        {"step": 3, "kind": "approval"},
    ]
    rows: list[AuditLog] = []
    for p in payloads:
        rows.append(
            await append_audit(
                db_session,
                tenant_id=t.id,
                user_id=u.id,
                operation=f"op_{p['step']}",
                resource_type="chain_test",
                operation_data=p,
            )
        )

    # Chain linkage
    assert rows[0].previous_log_hash == SENTINEL_HASH
    assert rows[1].previous_log_hash == rows[0].current_log_hash
    assert rows[2].previous_log_hash == rows[1].current_log_hash

    # Independent recomputation matches stored hash
    for row, payload in zip(rows, payloads, strict=True):
        expected = compute_audit_hash(
            previous_log_hash=row.previous_log_hash,
            operation_data=payload,
            tenant_id=t.id,
            timestamp_ms=row.timestamp_ms,
        )
        assert row.current_log_hash == expected
