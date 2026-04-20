"""Unit tests for counter key cleanup (Sprint 171 AC-6).

Validates:
  - Phase 3 Promote path calls _cleanup_counter → Redis delete
  - Phase 4 Prune path calls _cleanup_counter → Redis delete
  - Phase 5 Summarize does NOT call _cleanup_counter (30-day grace)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.memory.consolidation import MemoryConsolidationService
from src.integrations.memory.types import (
    MemoryConfig,
    MemoryLayer,
    MemoryMetadata,
    MemoryRecord,
    MemoryType,
)


def _make_mgr_with_redis() -> MagicMock:
    config = MemoryConfig()
    mgr = MagicMock()
    mgr.config = config
    mgr._embedding_service = MagicMock()
    mgr._redis = AsyncMock()
    mgr._redis.delete = AsyncMock(return_value=1)
    mgr.promote = AsyncMock(return_value=None)
    mgr.delete = AsyncMock(return_value=True)
    mgr._mem0_client = MagicMock()
    mgr._mem0_client.update_importance_metadata = AsyncMock(return_value=True)
    mgr.add = AsyncMock()
    return mgr


@pytest.mark.asyncio
async def test_promote_triggers_counter_cleanup():
    """Phase 3 Promote: counter + accessed_at keys deleted via Redis."""
    mgr = _make_mgr_with_redis()
    session_mem = MemoryRecord(
        id="promo_mem",
        user_id="user_pro",
        content="x",
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.SESSION,
        metadata=MemoryMetadata(),
        access_count=10,
    )
    mgr.get_user_memories = AsyncMock(return_value=[session_mem])
    svc = MemoryConsolidationService(memory_manager=mgr)

    promoted = await svc._promote_frequent("user_pro")

    assert promoted == 1
    mgr.promote.assert_awaited_once()
    mgr._redis.delete.assert_awaited_once()
    args = mgr._redis.delete.await_args.args
    assert "memory:counter:session:user_pro:promo_mem" in args
    assert "memory:accessed_at:session:user_pro:promo_mem" in args


@pytest.mark.asyncio
async def test_prune_triggers_counter_cleanup():
    """Phase 4 Prune: counter + accessed_at keys deleted BEFORE delete()."""
    mgr = _make_mgr_with_redis()
    stale_mem = MemoryRecord(
        id="stale_mem",
        user_id="user_pru",
        content="x",
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.LONG_TERM,
        metadata=MemoryMetadata(importance=0.05),
        created_at=datetime.now(timezone.utc) - timedelta(days=120),
    )
    mgr.get_user_memories = AsyncMock(return_value=[stale_mem])
    svc = MemoryConsolidationService(memory_manager=mgr)

    pruned = await svc._prune_stale("user_pru")

    assert pruned == 1
    mgr._redis.delete.assert_awaited_once()
    args = mgr._redis.delete.await_args.args
    assert "memory:counter:long_term:user_pru:stale_mem" in args
    mgr.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_summarize_does_not_cleanup_counters():
    """Phase 5: supersede markers set, but counters retained for 30-day grace."""
    mgr = _make_mgr_with_redis()
    records = [
        MemoryRecord(
            id=f"sm_{i}",
            user_id="user_sum",
            content=f"similar content {i}",
            memory_type=MemoryType.SYSTEM_KNOWLEDGE,
            layer=MemoryLayer.LONG_TERM,
            metadata=MemoryMetadata(importance=0.2),
        )
        for i in range(5)
    ]
    mgr.get_user_memories = AsyncMock(return_value=records)
    mgr._embedding_service.embed_text = AsyncMock(return_value=[1.0, 0.05, 0.02])

    def _summary_factory(*args, **kwargs):
        return MemoryRecord(
            id="summary_s1",
            user_id="user_sum",
            content=kwargs.get("content", "sum"),
            memory_type=MemoryType.SYSTEM_KNOWLEDGE,
            layer=MemoryLayer.LONG_TERM,
            metadata=kwargs.get("metadata", MemoryMetadata()),
        )

    mgr.add = AsyncMock(side_effect=_summary_factory)
    svc = MemoryConsolidationService(memory_manager=mgr)

    with patch.object(svc, "_call_summarize_llm", AsyncMock(return_value="unified summary text")):
        count = await svc._summarize_clusters("user_sum")

    assert count == 1
    # CRITICAL: Phase 5 must NOT call Redis delete on counter keys.
    mgr._redis.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_counter_helper_tolerates_no_redis():
    """_cleanup_counter is a no-op when Redis is absent (fall back disabled)."""
    mgr = _make_mgr_with_redis()
    mgr._redis = None  # simulate Redis unavailable
    svc = MemoryConsolidationService(memory_manager=mgr)

    # Should not raise
    await svc._cleanup_counter("any_mem", "any_user", MemoryLayer.WORKING)


@pytest.mark.asyncio
async def test_cleanup_counter_helper_key_format():
    """Verify exact key format matches Sprint 170 producer contract."""
    mgr = _make_mgr_with_redis()
    svc = MemoryConsolidationService(memory_manager=mgr)

    await svc._cleanup_counter("mem123", "alice", MemoryLayer.WORKING)

    mgr._redis.delete.assert_awaited_once_with(
        "memory:counter:working:alice:mem123",
        "memory:accessed_at:working:alice:mem123",
    )
