"""
File: backend/tests/unit/infrastructure/db/test_rls_enforcement.py
Purpose: Verify RLS policies (migration 0009) actually filter cross-tenant data.
Category: Tests / Infrastructure / DB / RLS enforcement
Scope: Sprint 49.3 Day 4.6

Why a separate role:
    The dev DB role `ipa_v2` is `SUPERUSER + BYPASSRLS`, which bypasses
    even FORCE ROW LEVEL SECURITY policies. To verify RLS actually
    filters, we SET LOCAL ROLE to a non-superuser, non-BYPASSRLS role
    (`rls_app_role`) within the test transaction. The role is created
    once per test module (idempotent) and granted CRUD on the 13 RLS
    tables. SET LOCAL ROLE applies only to the current transaction;
    rollback at end of test restores the connection state.

Test pattern:
    1. (as superuser) seed tenants A + B + their users / sessions
    2. Insert tenant-scoped rows for both A and B
    3. SET LOCAL ROLE rls_app_role  ← loses superuser bypass
    4. SET LOCAL app.tenant_id = A
    5. Verify only A's rows are visible / mutable / insertable
    6. (transaction rolls back at fixture end)

Tests:
    1. test_rls_select_blocked_without_set_local
    2. test_rls_select_scoped_to_tenant_a (memory_user)
    3. test_rls_insert_with_check_blocks_wrong_tenant
    4. test_rls_update_blocked_cross_tenant
    5. test_rls_delete_blocked_cross_tenant
    6. test_rls_audit_log_isolation

Created: 2026-04-29 (Sprint 49.3 Day 4.6)
"""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.audit_helper import append_audit
from infrastructure.db.models import AuditLog, MemoryUser
from tests.conftest import seed_tenant, seed_user

# Tables we test RLS on; rls_app_role needs CRUD on these.
_RLS_TABLES = (
    "users",
    "roles",
    "sessions",
    "messages",
    "message_events",
    "tool_calls",
    "state_snapshots",
    "loop_states",
    "api_keys",
    "rate_limits",
    "audit_log",
    "memory_tenant",
    "memory_user",
    # Junction tables that the queries touch transitively
    "tenants",
    "tool_results",
    "user_roles",
    "role_permissions",
)


async def _ensure_rls_app_role(session: AsyncSession) -> None:
    """Create rls_app_role NOLOGIN (no superuser, no BYPASSRLS) if absent.

    Idempotent: PG raises duplicate_object on re-run; we swallow it.
    Grants CRUD on all RLS-relevant tables so SET ROLE rls_app_role
    can still issue ordinary SELECT/INSERT/UPDATE/DELETE.
    """
    await session.execute(text("""
            DO $$
            BEGIN
                CREATE ROLE rls_app_role NOLOGIN;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END
            $$;
            """))
    # Grants are idempotent
    grants = ", ".join(_RLS_TABLES)
    await session.execute(
        text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {grants} TO rls_app_role")
    )
    # SEQUENCE on bigserial / uuid_generate_v4 default still needs USAGE
    await session.execute(
        text("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rls_app_role")
    )


async def _set_app_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    """SET LOCAL app.tenant_id (scoped to current tx)."""
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


@pytest.mark.asyncio
async def test_rls_select_blocked_without_set_local(
    db_session: AsyncSession,
) -> None:
    """As rls_app_role with no app.tenant_id setting, SELECT returns 0 rows."""
    await _ensure_rls_app_role(db_session)

    # Seed data as superuser
    t = await seed_tenant(db_session, code="RLS_NS")
    u = await seed_user(db_session, t, email="ns@rls.test")
    db_session.add(
        MemoryUser(tenant_id=t.id, user_id=u.id, category="fact", content="X")
    )
    await db_session.flush()

    # Switch to non-bypass role. Do NOT call set_config — app.tenant_id is
    # transaction-scoped via SET LOCAL, and the db_session fixture starts a
    # fresh transaction per test, so current_setting('app.tenant_id', true)
    # returns NULL and the policy filters everything out.
    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))

    result = await db_session.execute(select(MemoryUser))
    rows = list(result.scalars().all())
    assert rows == []  # RLS hides everything when current_setting empty/null


@pytest.mark.asyncio
async def test_rls_select_scoped_to_tenant_a(db_session: AsyncSession) -> None:
    """As rls_app_role with SET LOCAL app.tenant_id=A, only tenant A rows visible."""
    await _ensure_rls_app_role(db_session)

    t_a = await seed_tenant(db_session, code="RLS_A")
    t_b = await seed_tenant(db_session, code="RLS_B")
    u_a = await seed_user(db_session, t_a, email="a@rls.test")
    u_b = await seed_user(db_session, t_b, email="b@rls.test")

    db_session.add_all(
        [
            MemoryUser(
                tenant_id=t_a.id, user_id=u_a.id, category="fact", content="A note"
            ),
            MemoryUser(
                tenant_id=t_b.id, user_id=u_b.id, category="fact", content="B note"
            ),
        ]
    )
    await db_session.flush()

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    result = await db_session.execute(select(MemoryUser))
    rows = list(result.scalars().all())
    assert len(rows) == 1
    assert rows[0].content == "A note"
    assert rows[0].tenant_id == t_a.id


@pytest.mark.asyncio
async def test_rls_insert_with_check_blocks_wrong_tenant(
    db_session: AsyncSession,
) -> None:
    """As rls_app_role, INSERT with tenant_id != app.tenant_id raises."""
    await _ensure_rls_app_role(db_session)

    t_a = await seed_tenant(db_session, code="RLS_INS_A")
    t_b = await seed_tenant(db_session, code="RLS_INS_B")
    u_b = await seed_user(db_session, t_b, email="b_ins@rls.test")
    await db_session.flush()

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    # Try to insert a memory_user for tenant B while context is tenant A
    db_session.add(
        MemoryUser(tenant_id=t_b.id, user_id=u_b.id, category="fact", content="hijack")
    )
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.flush()
    assert "row-level security" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_rls_update_blocked_cross_tenant(db_session: AsyncSession) -> None:
    """As rls_app_role with tenant_id=A, UPDATE on B's row affects 0 rows."""
    await _ensure_rls_app_role(db_session)

    t_a = await seed_tenant(db_session, code="RLS_UPD_A")
    t_b = await seed_tenant(db_session, code="RLS_UPD_B")
    u_b = await seed_user(db_session, t_b, email="b_upd@rls.test")
    b_row = MemoryUser(
        tenant_id=t_b.id, user_id=u_b.id, category="fact", content="B original"
    )
    db_session.add(b_row)
    await db_session.flush()
    b_row_id = b_row.id

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    result = await db_session.execute(
        text("UPDATE memory_user SET content = :new WHERE id = :id"),
        {"new": "tampered", "id": str(b_row_id)},
    )
    assert result.rowcount == 0  # USING policy hides B's row from A

    # Verify by switching back to superuser-bypass via RESET ROLE then re-read
    await db_session.execute(text("RESET ROLE"))
    re = await db_session.execute(select(MemoryUser).where(MemoryUser.id == b_row_id))
    assert re.scalar_one().content == "B original"


@pytest.mark.asyncio
async def test_rls_delete_blocked_cross_tenant(db_session: AsyncSession) -> None:
    """As rls_app_role with tenant_id=A, DELETE on B's row affects 0 rows."""
    await _ensure_rls_app_role(db_session)

    t_a = await seed_tenant(db_session, code="RLS_DEL_A")
    t_b = await seed_tenant(db_session, code="RLS_DEL_B")
    u_b = await seed_user(db_session, t_b, email="b_del@rls.test")
    b_row = MemoryUser(
        tenant_id=t_b.id, user_id=u_b.id, category="fact", content="survive"
    )
    db_session.add(b_row)
    await db_session.flush()
    b_row_id = b_row.id

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    result = await db_session.execute(
        text("DELETE FROM memory_user WHERE id = :id"), {"id": str(b_row_id)}
    )
    assert result.rowcount == 0  # USING blocks the DELETE on B's row

    await db_session.execute(text("RESET ROLE"))
    re = await db_session.execute(select(MemoryUser).where(MemoryUser.id == b_row_id))
    assert re.scalar_one_or_none() is not None  # B's row survives


@pytest.mark.asyncio
async def test_rls_audit_log_isolation(db_session: AsyncSession) -> None:
    """audit_log is also RLS-scoped: tenant A cannot see tenant B's audit rows."""
    await _ensure_rls_app_role(db_session)

    t_a = await seed_tenant(db_session, code="RLS_AUD_A")
    t_b = await seed_tenant(db_session, code="RLS_AUD_B")
    await append_audit(
        db_session,
        tenant_id=t_b.id,
        operation="b_only_action",
        resource_type="test",
        operation_data={"secret": "B"},
    )
    await db_session.flush()

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await _set_app_tenant(db_session, t_a.id)

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.operation == "b_only_action")
    )
    assert result.scalar_one_or_none() is None  # B's audit invisible to A
