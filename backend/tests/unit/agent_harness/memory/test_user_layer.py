"""
File: backend/tests/unit/agent_harness/memory/test_user_layer.py
Purpose: Unit tests for UserLayer (Layer 4; PG-backed durable per-user memory).
Category: Tests / 範疇 3
Scope: Phase 51 / Sprint 51.2 Day 2.7

Description:
    Mix of static-helper tests (_row_to_hint mapping logic) and AsyncMock-
    based DB interaction tests. Real DB integration tests live in
    tests/integration/memory/ (Day 4-5).

Created: 2026-04-30
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agent_harness.memory.layers.user_layer import UserLayer
from infrastructure.db.models.memory import MemoryUser


def _build_factory(rows: list[MemoryUser], scalar_value: str | None = None) -> AsyncMock:
    """async_sessionmaker shape: factory() returns async ctx mgr -> session."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.scalar_one_or_none.return_value = scalar_value
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session.add = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    factory._mock_session = session  # for test introspection
    return factory


def _make_row(
    *,
    tenant_id: object | None = None,
    user_id: object | None = None,
    content: str = "user prefers detailed reports",
    confidence: Decimal | None = Decimal("0.85"),
    metadata: dict[str, object] | None = None,
    expires_at: datetime | None = None,
) -> MemoryUser:
    row = MemoryUser(
        id=uuid4(),
        tenant_id=tenant_id or uuid4(),
        user_id=user_id or uuid4(),
        category="preference",
        content=content,
        confidence=confidence,
        expires_at=expires_at,
        metadata_=metadata or {"time_scale": "long_term"},
    )
    row.created_at = datetime.now(timezone.utc)
    return row


@pytest.mark.asyncio
async def test_read_returns_empty_without_tenant_or_user() -> None:
    layer = UserLayer(_build_factory([]))
    assert await layer.read(query="x", tenant_id=None, user_id=uuid4()) == []
    assert await layer.read(query="x", tenant_id=uuid4(), user_id=None) == []


@pytest.mark.asyncio
async def test_read_returns_hints() -> None:
    tenant = uuid4()
    user = uuid4()
    row = _make_row(tenant_id=tenant, user_id=user)
    layer = UserLayer(_build_factory([row]))

    hints = await layer.read(query="detailed", tenant_id=tenant, user_id=user)
    assert len(hints) == 1
    h = hints[0]
    assert h.layer == "user"
    assert h.time_scale == "long_term"
    assert h.confidence == 0.85
    assert h.tenant_id == tenant
    # relevance_score boosted because query matches content
    assert h.relevance_score == 0.8


@pytest.mark.asyncio
async def test_read_semantic_only_returns_empty() -> None:
    """Semantic axis is stub in 51.2 (CARRY-026 Qdrant)."""
    layer = UserLayer(_build_factory([_make_row()]))
    hints = await layer.read(
        query="x", tenant_id=uuid4(), user_id=uuid4(), time_scales=("semantic",)
    )
    assert hints == []


@pytest.mark.asyncio
async def test_write_long_term_no_expires() -> None:
    layer = UserLayer(_build_factory([]))
    tenant = uuid4()
    user = uuid4()
    eid = await layer.write(
        content="prefers brevity",
        tenant_id=tenant,
        user_id=user,
        time_scale="long_term",
        confidence=0.7,
    )
    assert eid is not None

    session = layer._session_factory._mock_session  # type: ignore[attr-defined]
    session.add.assert_called_once()
    added: MemoryUser = session.add.call_args[0][0]
    assert added.tenant_id == tenant
    assert added.user_id == user
    assert added.expires_at is None  # long_term
    meta = added.metadata_ or {}
    assert meta.get("time_scale") == "long_term"
    assert meta.get("verify_before_use") is False


@pytest.mark.asyncio
async def test_write_short_term_sets_24h_expiry() -> None:
    layer = UserLayer(_build_factory([]))
    before = datetime.now(timezone.utc)
    await layer.write(
        content="working note",
        tenant_id=uuid4(),
        user_id=uuid4(),
        time_scale="short_term",
    )
    session = layer._session_factory._mock_session  # type: ignore[attr-defined]
    added: MemoryUser = session.add.call_args[0][0]
    assert added.expires_at is not None
    delta = added.expires_at - before
    assert timedelta(hours=23, minutes=55) < delta < timedelta(hours=24, minutes=5)


@pytest.mark.asyncio
async def test_write_requires_tenant_and_user() -> None:
    layer = UserLayer(_build_factory([]))
    with pytest.raises(ValueError, match="tenant_id and user_id"):
        await layer.write(content="x", tenant_id=None, user_id=uuid4())
    with pytest.raises(ValueError):
        await layer.write(content="x", tenant_id=uuid4(), user_id=None)


@pytest.mark.asyncio
async def test_evict_no_op_without_tenant_id() -> None:
    layer = UserLayer(_build_factory([]))
    # Should not raise; just no-op
    await layer.evict(entry_id=uuid4(), tenant_id=None)
    session = layer._session_factory._mock_session  # type: ignore[attr-defined]
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_evict_executes_delete_when_tenant_present() -> None:
    layer = UserLayer(_build_factory([]))
    await layer.evict(entry_id=uuid4(), tenant_id=uuid4())
    session = layer._session_factory._mock_session  # type: ignore[attr-defined]
    assert session.execute.await_count == 1
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_returns_full_content() -> None:
    full = "user prefers extremely detailed financial breakdowns including line items"
    factory = _build_factory(rows=[], scalar_value=full)
    layer = UserLayer(factory)

    from agent_harness._contracts import MemoryHint

    hint = MemoryHint(
        hint_id=uuid4(),
        layer="user",
        time_scale="long_term",
        summary=full[:50],
        confidence=0.9,
        relevance_score=0.8,
        full_content_pointer="memory_user:abc",
        timestamp=datetime.now(timezone.utc),
        tenant_id=uuid4(),
    )
    content = await layer.resolve(hint)
    assert content == full


def test_row_to_hint_handles_missing_metadata() -> None:
    """Static helper: missing metadata → defaults applied (no exception)."""
    row = _make_row(metadata={})
    hint = UserLayer._row_to_hint(row, query="anything")
    assert hint.time_scale == "long_term"  # default
    assert hint.verify_before_use is False
    assert hint.last_verified_at is None
    assert hint.source_tool_call_id is None


def test_row_to_hint_parses_iso_last_verified() -> None:
    iso = "2026-04-15T10:30:00+00:00"
    row = _make_row(metadata={"time_scale": "long_term", "last_verified_at": iso})
    hint = UserLayer._row_to_hint(row, query="x")
    assert hint.last_verified_at is not None
    assert hint.last_verified_at.year == 2026
