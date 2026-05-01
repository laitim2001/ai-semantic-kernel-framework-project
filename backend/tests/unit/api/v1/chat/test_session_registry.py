"""
File: backend/tests/unit/api/v1/chat/test_session_registry.py
Purpose: Unit tests for tenant-scoped in-memory SessionRegistry.
Category: tests
Scope: Phase 50 / Sprint 50.2 (Day 1.2) — Sprint 52.5 Day 2.1 tenant isolation

Modification History (newest-first):
    - 2026-05-01: Sprint 52.5 Day 2.1 (P0 #11) — every test now passes
        tenant_id; new tests cover cross-tenant isolation (read / cancel /
        mark_completed / cleanup) — never leak state across tenants.
    - 2026-04-30: Initial creation (Sprint 50.2 Day 1.2)
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from api.v1.chat.session_registry import SessionRegistry

# ============================================================
# Existing single-tenant tests (refactored to pass tenant_id)
# ============================================================


@pytest.mark.asyncio
async def test_register_creates_running_entry() -> None:
    reg = SessionRegistry()
    tid, sid = uuid4(), uuid4()
    entry = await reg.register(tid, sid)
    assert entry.status == "running"
    assert entry.cancel_event.is_set() is False
    assert (await reg.get(tid, sid)) is entry


@pytest.mark.asyncio
async def test_register_idempotent_on_same_session_id() -> None:
    reg = SessionRegistry()
    tid, sid = uuid4(), uuid4()
    e1 = await reg.register(tid, sid)
    e2 = await reg.register(tid, sid)
    assert e1 is e2


@pytest.mark.asyncio
async def test_cancel_sets_status_and_event() -> None:
    reg = SessionRegistry()
    tid, sid = uuid4(), uuid4()
    await reg.register(tid, sid)
    found = await reg.cancel(tid, sid)
    assert found is True
    entry = await reg.get(tid, sid)
    assert entry is not None
    assert entry.status == "cancelled"
    assert entry.cancel_event.is_set() is True


@pytest.mark.asyncio
async def test_cancel_returns_false_for_missing() -> None:
    reg = SessionRegistry()
    assert (await reg.cancel(uuid4(), uuid4())) is False


@pytest.mark.asyncio
async def test_mark_completed_does_not_override_cancelled() -> None:
    reg = SessionRegistry()
    tid, sid = uuid4(), uuid4()
    await reg.register(tid, sid)
    await reg.cancel(tid, sid)
    await reg.mark_completed(tid, sid)  # no-op since status=cancelled
    entry = await reg.get(tid, sid)
    assert entry is not None
    assert entry.status == "cancelled"


@pytest.mark.asyncio
async def test_cleanup_removes_entry() -> None:
    reg = SessionRegistry()
    tid, sid = uuid4(), uuid4()
    await reg.register(tid, sid)
    await reg.cleanup(tid, sid)
    assert (await reg.get(tid, sid)) is None
    # idempotent on missing
    await reg.cleanup(tid, sid)


@pytest.mark.asyncio
async def test_concurrent_register_no_race() -> None:
    """Lock prevents two co-routines creating duplicate entries (same tenant)."""
    reg = SessionRegistry()
    tid, sid = uuid4(), uuid4()
    e1, e2 = await asyncio.gather(reg.register(tid, sid), reg.register(tid, sid))
    assert e1 is e2


# ============================================================
# Cross-tenant isolation tests (NEW — P0 #11 Sprint 52.5)
# ============================================================


@pytest.mark.asyncio
async def test_get_returns_none_when_session_belongs_to_different_tenant() -> None:
    """tenant_a registers; tenant_b reads same session_id → None.

    Why this matters: V1 W3-2 audit confirmed pre-refactor registry was a
    flat dict shared across tenants — exactly this kind of cross-tenant
    read would have leaked another tenant's session metadata.
    """
    reg = SessionRegistry()
    tenant_a, tenant_b = uuid4(), uuid4()
    sid = uuid4()
    await reg.register(tenant_a, sid)
    assert (await reg.get(tenant_b, sid)) is None


@pytest.mark.asyncio
async def test_cancel_cannot_affect_other_tenants_session() -> None:
    """tenant_a cancel of tenant_b's session must not flip the latter's state."""
    reg = SessionRegistry()
    tenant_a, tenant_b = uuid4(), uuid4()
    sid = uuid4()
    entry_b = await reg.register(tenant_b, sid)
    found = await reg.cancel(tenant_a, sid)
    assert found is False
    # tenant_b's entry stays running, cancel_event NOT signalled
    assert entry_b.status == "running"
    assert entry_b.cancel_event.is_set() is False


@pytest.mark.asyncio
async def test_mark_completed_cannot_affect_other_tenants_session() -> None:
    reg = SessionRegistry()
    tenant_a, tenant_b = uuid4(), uuid4()
    sid = uuid4()
    entry_b = await reg.register(tenant_b, sid)
    await reg.mark_completed(tenant_a, sid)  # cross-tenant — no-op
    assert entry_b.status == "running"


@pytest.mark.asyncio
async def test_cleanup_cannot_affect_other_tenants_session() -> None:
    reg = SessionRegistry()
    tenant_a, tenant_b = uuid4(), uuid4()
    sid = uuid4()
    entry_b = await reg.register(tenant_b, sid)
    await reg.cleanup(tenant_a, sid)  # cross-tenant — no-op
    # tenant_b's entry still retrievable
    assert (await reg.get(tenant_b, sid)) is entry_b


@pytest.mark.asyncio
async def test_two_tenants_can_register_same_session_id_independently() -> None:
    """Different tenants may share a session_id; registry stores them separately."""
    reg = SessionRegistry()
    tenant_a, tenant_b = uuid4(), uuid4()
    sid = uuid4()  # SAME id used by both tenants
    e_a = await reg.register(tenant_a, sid)
    e_b = await reg.register(tenant_b, sid)
    # Independent entries
    assert e_a is not e_b
    # Cancel one doesn't affect the other
    await reg.cancel(tenant_a, sid)
    assert e_a.status == "cancelled"
    assert e_b.status == "running"


@pytest.mark.asyncio
async def test_cleanup_drops_empty_tenant_bucket() -> None:
    """After cleanup of last session for a tenant, tenant entry itself is removed.

    Internal detail (avoids unbounded dict growth from short-lived tenants).
    """
    reg = SessionRegistry()
    tid, sid = uuid4(), uuid4()
    await reg.register(tid, sid)
    await reg.cleanup(tid, sid)
    # Internal storage check via attribute (private — acceptable in unit test).
    assert tid not in reg._tenants  # noqa: SLF001
