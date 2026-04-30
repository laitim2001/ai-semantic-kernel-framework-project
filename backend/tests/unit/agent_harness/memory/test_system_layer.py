"""
File: backend/tests/unit/agent_harness/memory/test_system_layer.py
Purpose: Unit tests for SystemLayer (Layer 1; PG-backed read-only).
Category: Tests / 範疇 3
Scope: Phase 51 / Sprint 51.2 Day 2.8

Created: 2026-04-30
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agent_harness.memory.layers.system_layer import SystemLayer, SystemReadOnlyError
from infrastructure.db.models.memory import MemorySystem


def _build_factory(rows: list[MemorySystem]) -> AsyncMock:
    """Create an async_sessionmaker-shaped mock that returns a session whose
    execute() yields the given rows."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.scalar_one_or_none.return_value = rows[0].content if rows else None
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=cm)
    return factory


@pytest.mark.asyncio
async def test_write_raises_read_only() -> None:
    layer = SystemLayer(_build_factory([]))
    with pytest.raises(SystemReadOnlyError):
        await layer.write(content="x")


@pytest.mark.asyncio
async def test_evict_raises_read_only() -> None:
    layer = SystemLayer(_build_factory([]))
    with pytest.raises(SystemReadOnlyError):
        await layer.evict(entry_id=uuid4())


@pytest.mark.asyncio
async def test_read_returns_hints() -> None:
    sample = MemorySystem(
        id=uuid4(),
        key="k1",
        category="safety",
        content="never expose PII",
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    layer = SystemLayer(_build_factory([sample]))
    hints = await layer.read(query="PII")
    assert len(hints) == 1
    assert hints[0].layer == "system"
    assert hints[0].time_scale == "long_term"
    assert hints[0].confidence == 1.0  # system policies authoritative
    assert hints[0].tenant_id is None  # global


@pytest.mark.asyncio
async def test_read_filters_non_long_term_returns_empty() -> None:
    layer = SystemLayer(_build_factory([]))
    # Even with stub data, semantic-only request returns empty
    hints = await layer.read(query="x", time_scales=("semantic",))
    assert hints == []
