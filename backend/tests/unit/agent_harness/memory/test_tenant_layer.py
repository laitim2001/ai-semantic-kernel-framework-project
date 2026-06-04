"""
File: backend/tests/unit/agent_harness/memory/test_tenant_layer.py
Purpose: Unit tests for TenantLayer (Layer 2; PG-backed tenant-wide memory).
Category: Tests / 範疇 3
Scope: Phase 51 / Sprint 51.2 Day 2.8

Created: 2026-04-30
Modified: 2026-06-04 (Sprint 57.76 — update write assertion for memory_ops emit)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agent_harness.memory.layers.tenant_layer import TenantLayer
from infrastructure.db.models.memory import MemoryTenant


def _build_factory(rows: list[MemoryTenant], scalar_value: str | None = None) -> AsyncMock:
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
    factory._mock_session = session
    return factory


def _make_row(*, tenant_id: object | None = None, content: str = "tenant playbook") -> MemoryTenant:
    row = MemoryTenant(
        id=uuid4(),
        tenant_id=tenant_id or uuid4(),
        key="hint-1",
        category="domain_knowledge",
        content=content,
        metadata_={"time_scale": "long_term", "confidence": 0.65},
    )
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


@pytest.mark.asyncio
async def test_read_empty_without_tenant() -> None:
    layer = TenantLayer(_build_factory([]))
    assert await layer.read(query="x", tenant_id=None) == []


@pytest.mark.asyncio
async def test_read_returns_hints() -> None:
    tenant = uuid4()
    row = _make_row(tenant_id=tenant, content="our refund policy is generous")
    layer = TenantLayer(_build_factory([row]))
    hints = await layer.read(query="refund", tenant_id=tenant)
    assert len(hints) == 1
    h = hints[0]
    assert h.layer == "tenant"
    assert h.time_scale == "long_term"
    assert h.confidence == 0.65
    assert h.tenant_id == tenant
    assert h.relevance_score == 0.7


@pytest.mark.asyncio
async def test_read_semantic_only_returns_empty() -> None:
    layer = TenantLayer(_build_factory([_make_row()]))
    hints = await layer.read(query="x", tenant_id=uuid4(), time_scales=("semantic",))
    assert hints == []


@pytest.mark.asyncio
async def test_write_long_term() -> None:
    layer = TenantLayer(_build_factory([]))
    tenant = uuid4()
    eid = await layer.write(content="new SOP", tenant_id=tenant, time_scale="long_term")
    assert eid is not None
    session = layer._session_factory._mock_session  # type: ignore[attr-defined]
    # Sprint 57.76: write now adds BOTH the MemoryTenant row + a MemoryOp row;
    # find the MemoryTenant among the add() targets (order: tenant row first).
    targets = [c.args[0] for c in session.add.call_args_list]
    added: MemoryTenant = next(t for t in targets if isinstance(t, MemoryTenant))
    assert added.tenant_id == tenant
    meta = added.metadata_ or {}
    assert meta.get("time_scale") == "long_term"


@pytest.mark.asyncio
async def test_write_rejects_short_term() -> None:
    layer = TenantLayer(_build_factory([]))
    with pytest.raises(ValueError, match="short_term"):
        await layer.write(content="x", tenant_id=uuid4(), time_scale="short_term")


@pytest.mark.asyncio
async def test_write_requires_tenant() -> None:
    layer = TenantLayer(_build_factory([]))
    with pytest.raises(ValueError, match="tenant_id"):
        await layer.write(content="x", tenant_id=None)
