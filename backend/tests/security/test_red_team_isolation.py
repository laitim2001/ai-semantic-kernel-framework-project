"""
File: backend/tests/security/test_red_team_isolation.py
Purpose: Red-team verification — 6 cross-tenant attack vectors all blocked.
Category: Tests / Security / Multi-tenant red-team
Scope: Sprint 49.3 Day 5.3

This is the AC-10 acceptance suite per sprint-49-3-plan.md:
    AV-1  Forged X-Tenant-Id (valid UUID belonging to tenant B; attacker is A)
          → RLS hides B's rows even if app sets B's id.
    AV-2  Missing SET LOCAL                  → RLS hides everything.
    AV-3  SQL injection of app.tenant_id     → ::uuid cast rejects.
    AV-4  UPDATE audit_log                   → ROW trigger raises.
    AV-5a TRUNCATE audit_log                 → STATEMENT trigger raises.
    AV-5b TRUNCATE state_snapshots CASCADE   → STATEMENT trigger raises.
    AV-6  Qdrant cross-namespace             → distinct collection names +
          payload filter still rejects mismatch.

Each vector verifies a different layer of defense; together they cover
the full multi-tenant boundary surface that Sprint 49.3 establishes.

Created: 2026-04-29 (Sprint 49.3 Day 5.3)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.audit_helper import append_audit
from infrastructure.db.models import AuditLog, MemoryUser, Session, append_snapshot
from infrastructure.vector import QdrantNamespaceStrategy
from tests.conftest import seed_tenant, seed_user


async def _ensure_rls_app_role(session: AsyncSession) -> None:
    """Create the non-bypassrls test role (idempotent)."""
    await session.execute(text("""
            DO $$
            BEGIN
                CREATE ROLE rls_app_role NOLOGIN;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END
            $$;
            """))
    grant_tables = (
        "users, roles, sessions, messages, message_events, "
        "tool_calls, state_snapshots, loop_states, api_keys, "
        "rate_limits, audit_log, memory_tenant, memory_user, tenants, "
        "tool_results, user_roles, role_permissions"
    )
    await session.execute(
        text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {grant_tables} TO rls_app_role")
    )
    await session.execute(text("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rls_app_role"))


@pytest.mark.asyncio
async def test_av1_forged_tenant_id_rls_filters(db_session: AsyncSession) -> None:
    """AV-1: Attacker (tenant A actor) sets X-Tenant-Id to tenant B's UUID;
    the middleware accepts the cast (valid UUID) but the row's tenant_id
    must equal app.tenant_id. So the attacker can only see B's data IF
    they set B's id — at which point they can't perform A's actions.

    Concretely: setting app.tenant_id to a tenant the actor doesn't
    legitimately own does not magically give them access to A's data,
    and any INSERT they attempt for A would fail WITH CHECK.
    """
    await _ensure_rls_app_role(db_session)

    t_a = await seed_tenant(db_session, code="AV1_A")
    t_b = await seed_tenant(db_session, code="AV1_B")
    u_a = await seed_user(db_session, t_a, email="a@av1.test")
    db_session.add(MemoryUser(tenant_id=t_a.id, user_id=u_a.id, category="fact", content="A only"))
    await db_session.flush()

    # Attacker pretends to be tenant B (sets B's UUID via SET LOCAL)
    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    await db_session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(t_b.id)},
    )

    # Cannot read A's row (RLS USING blocks it)
    result = await db_session.execute(select(MemoryUser))
    rows = list(result.scalars().all())
    assert all(r.tenant_id == t_b.id for r in rows)
    assert not any(r.content == "A only" for r in rows)


@pytest.mark.asyncio
async def test_av2_missing_set_local_returns_zero(db_session: AsyncSession) -> None:
    """AV-2: If middleware fails / dep skipped, app.tenant_id stays NULL.
    Result is empty (RLS USING evaluates NULL = NULL → NULL → no row)."""
    await _ensure_rls_app_role(db_session)

    t = await seed_tenant(db_session, code="AV2")
    u = await seed_user(db_session, t, email="av2@rls.test")
    db_session.add(MemoryUser(tenant_id=t.id, user_id=u.id, category="fact", content="hidden"))
    await db_session.flush()

    await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
    # Intentionally do NOT set app.tenant_id
    result = await db_session.execute(select(MemoryUser))
    assert list(result.scalars().all()) == []


@pytest.mark.asyncio
async def test_av3_sql_injection_rejected_by_uuid_cast(db_session: AsyncSession) -> None:
    """AV-3: Try to set app.tenant_id to a string that mimics SQL injection.
    The current_setting('app.tenant_id', true)::uuid cast rejects anything
    that isn't a valid UUID — so 'foo OR 1=1' or '<uuid>; DROP ...' fails.
    """
    await _ensure_rls_app_role(db_session)

    bogus_values = [
        "not-a-uuid",
        "1' OR '1'='1",
        f"{uuid4()}; DROP TABLE memory_user;",  # injection attempt
    ]
    for bogus in bogus_values:
        # Use SAVEPOINT so the cast error doesn't kill the outer tx (and
        # blow away rls_app_role we created in _ensure_rls_app_role).
        async with db_session.begin_nested() as sp:
            await db_session.execute(text("SET LOCAL ROLE rls_app_role"))
            await db_session.execute(
                text("SELECT set_config('app.tenant_id', :v, true)"), {"v": bogus}
            )
            # SELECT triggers the RLS USING clause — its ::uuid cast rejects bogus.
            with pytest.raises(DBAPIError):
                await db_session.execute(select(MemoryUser))
            # explicit rollback so SAVEPOINT releases cleanly + role/setting
            # are scoped inside the savepoint.
            await sp.rollback()


@pytest.mark.asyncio
async def test_av4_audit_update_blocked(db_session: AsyncSession) -> None:
    """AV-4: ROW UPDATE trigger on audit_log fires regardless of role."""
    t = await seed_tenant(db_session, code="AV4")
    row = await append_audit(
        db_session,
        tenant_id=t.id,
        operation="anchor",
        resource_type="security_test",
        operation_data={"test": "av4"},
    )
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(
            update(AuditLog).where(AuditLog.id == row.id).values(operation="tampered")
        )
        await db_session.flush()
    assert "audit_log is append-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_av5a_audit_truncate_blocked(db_session: AsyncSession) -> None:
    """AV-5a: STATEMENT TRUNCATE trigger on audit_log fires."""
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(text("TRUNCATE audit_log"))
        await db_session.flush()
    assert "audit_log is append-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_av5b_state_snapshots_truncate_blocked(db_session: AsyncSession) -> None:
    """AV-5b: STATEMENT TRUNCATE trigger on state_snapshots fires (49.2 carry).

    Use TRUNCATE ... CASCADE to bypass the FK rejection from sessions
    so the trigger has a chance to fire. Both layers (FK + trigger)
    form defense-in-depth.
    """
    t = await seed_tenant(db_session, code="AV5B")
    u = await seed_user(db_session, t, email="av5b@rls.test")
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


@pytest.mark.asyncio
async def test_av6_qdrant_namespace_isolation() -> None:
    """AV-6: Two tenants get distinct collection names; payload filters
    each include the OWN tenant_id, so cross-namespace is impossible."""
    a, b = uuid4(), uuid4()

    coll_a = QdrantNamespaceStrategy.collection_name(a, "user_memory")
    coll_b = QdrantNamespaceStrategy.collection_name(b, "user_memory")
    assert coll_a != coll_b
    # Even the per-tenant prefix must not overlap
    prefix_a = coll_a.split("_")[1]
    prefix_b = coll_b.split("_")[1]
    assert prefix_a != prefix_b

    # payload filters carry FULL tenant uuid (not just prefix)
    f_a = QdrantNamespaceStrategy.payload_filter(a)
    f_b = QdrantNamespaceStrategy.payload_filter(b)
    assert f_a["must"][0]["match"]["value"] == str(a)
    assert f_b["must"][0]["match"]["value"] == str(b)
    assert f_a != f_b
