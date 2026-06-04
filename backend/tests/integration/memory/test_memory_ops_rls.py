"""
File: backend/tests/integration/memory/test_memory_ops_rls.py
Purpose: RLS enforcement + Risk-C same-txn atomicity for the memory_ops table.
Category: Tests / Integration / 範疇 3 / RLS
Scope: Phase 57 / Sprint 57.76 (US-5 / US-6)

Description:
    Requires a live PostgreSQL with `alembic upgrade head` (per conftest
    db_session). Two test groups:

    1. RLS (mirrors test_rls_enforcement.py): SET LOCAL ROLE to a non-superuser,
       non-BYPASSRLS role; verify tenant A's memory_ops are invisible to tenant
       B and INSERT WITH CHECK blocks cross-tenant writes.

    2. Risk Class C (same-txn atomicity): the layer-emitted op row participates
       in the SAME transaction as the underlying memory_user write. Rolling back
       the transaction rolls back BOTH the memory_user row and its op row.

Created: 2026-06-04 (Sprint 57.76)
"""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.memory import MemoryOp, MemoryUser
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


async def _ensure_rls_app_role(session: AsyncSession) -> None:
    """Create rls_app_role NOLOGIN (no superuser, no BYPASSRLS) if absent."""
    await session.execute(text("""
            DO $$
            BEGIN
                CREATE ROLE rls_app_role NOLOGIN;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END
            $$;
            """))
    await session.execute(
        text(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON tenants, users, memory_ops " "TO rls_app_role"
        )
    )
    await session.execute(text("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rls_app_role"))


async def _set_app_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


async def _seed_op(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    content: str,
    operation: str = "WRITE",
) -> None:
    session.add(
        MemoryOp(
            tenant_id=tenant_id,
            user_id=user_id,
            scope="user",
            key="general",
            operation=operation,
            time_scale="long_term",
            value_snapshot=content,
            actor=str(user_id),
        )
    )
    await session.flush()


# ---------------------------------------------------------------------------
# RLS
# ---------------------------------------------------------------------------


async def test_memory_ops_select_scoped_to_tenant_a(db_session: AsyncSession) -> None:
    """tenant A's memory_ops invisible to a context set to... only sees A's rows."""
    await _ensure_rls_app_role(db_session)
    t_a = await seed_tenant(db_session, code="OPS_RLS_A")
    t_b = await seed_tenant(db_session, code="OPS_RLS_B")
    u_a = await seed_user(db_session, t_a, email="a@ops.test")
    u_b = await seed_user(db_session, t_b, email="b@ops.test")
    await _seed_op(db_session, tenant_id=t_a.id, user_id=u_a.id, content="A op")
    await _seed_op(db_session, tenant_id=t_b.id, user_id=u_b.id, content="B op")

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    rows = list((await db_session.execute(select(MemoryOp))).scalars().all())
    assert len(rows) == 1
    assert rows[0].value_snapshot == "A op"
    assert rows[0].tenant_id == t_a.id


async def test_memory_ops_insert_with_check_blocks_wrong_tenant(db_session: AsyncSession) -> None:
    await _ensure_rls_app_role(db_session)
    t_a = await seed_tenant(db_session, code="OPS_INS_A")
    t_b = await seed_tenant(db_session, code="OPS_INS_B")
    u_b = await seed_user(db_session, t_b, email="bins@ops.test")
    await db_session.flush()

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    # Insert an op for tenant B while context is tenant A → WITH CHECK rejects.
    db_session.add(
        MemoryOp(
            tenant_id=t_b.id,
            user_id=u_b.id,
            scope="user",
            key="general",
            operation="WRITE",
            value_snapshot="hijack",
            actor=str(u_b.id),
        )
    )
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.flush()
    assert "row-level security" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Risk Class C — same-txn atomicity (layer write + op row roll back together)
# ---------------------------------------------------------------------------


async def test_user_layer_write_op_same_txn_rollback(db_session: AsyncSession) -> None:
    """UserLayer.write inserts both rows in one txn; rollback drops both.

    Uses a factory that yields the test's db_session (no commit reaches disk),
    proving the op row lives in the same transaction as the memory_user row.
    """
    from contextlib import asynccontextmanager

    from agent_harness.memory.layers.user_layer import UserLayer

    t = await seed_tenant(db_session, code="OPS_TXN")
    u = await seed_user(db_session, t, email="txn@ops.test")
    await db_session.flush()

    @asynccontextmanager
    async def _shared_session():  # type: ignore[no-untyped-def]
        # Yield the test session; treat commit as flush so rollback still drops it.
        orig_commit = db_session.commit
        db_session.commit = db_session.flush  # type: ignore[method-assign]
        try:
            yield db_session
        finally:
            db_session.commit = orig_commit  # type: ignore[method-assign]

    layer = UserLayer(_shared_session)  # type: ignore[arg-type]
    await layer.write(content="atomic note", tenant_id=t.id, user_id=u.id, time_scale="long_term")

    # Both rows are present pre-rollback.
    op_count = (
        await db_session.execute(
            select(func.count()).select_from(MemoryOp).where(MemoryOp.tenant_id == t.id)
        )
    ).scalar_one()
    user_count = (
        await db_session.execute(
            select(func.count()).select_from(MemoryUser).where(MemoryUser.tenant_id == t.id)
        )
    ).scalar_one()
    assert op_count == 1
    assert user_count == 1

    # Rollback the shared transaction → both rows gone (atomic).
    await db_session.rollback()
    op_after = (
        await db_session.execute(
            select(func.count()).select_from(MemoryOp).where(MemoryOp.tenant_id == t.id)
        )
    ).scalar_one()
    assert op_after == 0
