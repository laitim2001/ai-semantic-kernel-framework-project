"""
File: backend/tests/unit/agent_harness/memory/test_role_layer.py
Purpose: Unit tests for RoleLayer (Layer 3; simplified read-only in 51.2).
Category: Tests / 範疇 3
Scope: Phase 51 / Sprint 51.2 Day 2.8

Created: 2026-04-30
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agent_harness.memory.layers.role_layer import RoleLayer
from infrastructure.db.models.memory import MemoryRole


def _build_factory(rows: list[MemoryRole]) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


@pytest.mark.asyncio
async def test_write_raises_not_implemented() -> None:
    layer = RoleLayer(_build_factory([]))
    with pytest.raises(NotImplementedError, match="admin-managed"):
        await layer.write(content="x")


@pytest.mark.asyncio
async def test_evict_raises_not_implemented() -> None:
    layer = RoleLayer(_build_factory([]))
    with pytest.raises(NotImplementedError):
        await layer.evict(entry_id=uuid4())


@pytest.mark.asyncio
async def test_read_returns_hints() -> None:
    sample = MemoryRole(
        id=uuid4(),
        role_id=uuid4(),
        key="auditor-policy",
        category="approval_rule",
        content="auditor must approve over 10000",
        created_at=datetime.now(timezone.utc),
    )
    layer = RoleLayer(_build_factory([sample]))
    hints = await layer.read(query="approve")
    assert len(hints) == 1
    assert hints[0].layer == "role"
    assert hints[0].time_scale == "long_term"
    assert hints[0].confidence == 0.7
