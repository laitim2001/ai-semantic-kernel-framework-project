"""
File: backend/tests/unit/agent_harness/memory/test_session_layer.py
Purpose: Unit tests for SessionLayer (Layer 5; in-memory dict backend in 51.2).
Category: Tests / 範疇 3
Scope: Phase 51 / Sprint 51.2 Day 2.7

Description:
    SessionLayer is in-memory dict-backed (51.2 design; CARRY-029 promotes to
    Redis later). All 6 tests exercise the real implementation directly — no
    mocking required. Covers tenant isolation, TTL expiry, write/read/evict
    roundtrip, write rejection for non-short_term.

Created: 2026-04-30
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from agent_harness.memory.layers.session_layer import SessionLayer, _SessionEntry


@pytest.mark.asyncio
async def test_write_then_read_roundtrip() -> None:
    layer = SessionLayer()
    tenant = uuid4()
    session_id = uuid4()

    entry_id = await layer.write(
        content="user said hello",
        tenant_id=tenant,
        user_id=session_id,
        time_scale="short_term",
        confidence=0.7,
    )
    assert entry_id is not None

    hints = await layer.read(
        query="hello",
        tenant_id=tenant,
        user_id=session_id,
    )
    assert len(hints) == 1
    assert hints[0].hint_id == entry_id
    assert hints[0].layer == "session"
    assert hints[0].time_scale == "short_term"
    assert hints[0].confidence == 0.7
    assert hints[0].tenant_id == tenant


@pytest.mark.asyncio
async def test_tenant_isolation() -> None:
    layer = SessionLayer()
    tenant_a = uuid4()
    tenant_b = uuid4()
    session_a = uuid4()
    session_b = uuid4()

    await layer.write(
        content="tenant A secret",
        tenant_id=tenant_a,
        user_id=session_a,
    )

    # Tenant B reads (different tenant + session) → 0 leak
    hints_b = await layer.read(
        query="secret",
        tenant_id=tenant_b,
        user_id=session_b,
    )
    assert hints_b == []


@pytest.mark.asyncio
async def test_write_rejects_non_short_term() -> None:
    layer = SessionLayer()
    tenant = uuid4()
    session_id = uuid4()

    with pytest.raises(ValueError, match="short_term"):
        await layer.write(
            content="durable",
            tenant_id=tenant,
            user_id=session_id,
            time_scale="long_term",
        )


@pytest.mark.asyncio
async def test_read_filters_only_short_term_axis() -> None:
    layer = SessionLayer()
    tenant = uuid4()
    session_id = uuid4()
    await layer.write(content="hi", tenant_id=tenant, user_id=session_id, time_scale="short_term")

    # long_term-only request → empty (session layer is short_term only)
    hints = await layer.read(
        query="hi", tenant_id=tenant, user_id=session_id, time_scales=("long_term",)
    )
    assert hints == []


@pytest.mark.asyncio
async def test_evict_removes_entry() -> None:
    layer = SessionLayer()
    tenant = uuid4()
    session_id = uuid4()
    eid = await layer.write(content="abc", tenant_id=tenant, user_id=session_id)

    await layer.evict(entry_id=eid, tenant_id=tenant)

    hints = await layer.read(query="abc", tenant_id=tenant, user_id=session_id)
    assert hints == []


@pytest.mark.asyncio
async def test_lazy_expiry_drops_expired_entries() -> None:
    layer = SessionLayer()
    tenant = uuid4()
    session_id = uuid4()

    # Inject an already-expired entry directly (bypassing write)
    now = datetime.now(timezone.utc)
    expired = _SessionEntry(
        entry_id=uuid4(),
        tenant_id=tenant,
        session_id=session_id,
        content="ancient note",
        confidence=0.5,
        created_at=now - timedelta(days=2),
        expires_at=now - timedelta(hours=1),  # already expired
    )
    layer._store[(tenant, session_id)] = [expired]

    hints = await layer.read(query="ancient", tenant_id=tenant, user_id=session_id)
    assert hints == []
    # store should now have no entries for the key (lazy expiry sweep)
    assert layer._store[(tenant, session_id)] == []


@pytest.mark.asyncio
async def test_read_returns_empty_without_tenant_or_session() -> None:
    layer = SessionLayer()
    # tenant_id None
    assert await layer.read(query="x", tenant_id=None, user_id=uuid4()) == []
    # user_id (session_id slot) None
    assert await layer.read(query="x", tenant_id=uuid4(), user_id=None) == []
