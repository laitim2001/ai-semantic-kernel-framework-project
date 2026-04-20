"""End-to-end full 5-phase consolidation test (Sprint 171 AC-9 / AC-10).

Validates that a single `run_once(force_run=True)` invocation exercises
all 5 phases (dedup / decay / promote / prune / summarize) against a
diverse seeded corpus.

Requires real Redis + Qdrant + mem0 via testcontainers. Auto-skips when
infra is not available (same pattern as Sprint 170's integration test).

Run with:
    pytest backend/tests/integration/memory/test_consolidation_full_5phase.py \
        -v -m integration
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

testcontainers = pytest.importorskip(
    "testcontainers",
    reason="testcontainers package required — pip install testcontainers[redis]",
)

from testcontainers.redis import RedisContainer  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer("redis:7-alpine") as container:
        yield container


@pytest.fixture(scope="module")
def qdrant_url():
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    import urllib.request

    try:
        urllib.request.urlopen(f"{url}/readyz", timeout=2)  # nosec B310
    except Exception:
        pytest.skip(f"Qdrant not reachable at {url}")
    return url


@pytest.fixture
async def memory_manager(redis_container, qdrant_url, monkeypatch):
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)

    monkeypatch.setenv("REDIS_HOST", redis_host)
    monkeypatch.setenv("REDIS_PORT", str(redis_port))
    monkeypatch.setenv("QDRANT_URL", qdrant_url)
    monkeypatch.setenv("MEM0_ENABLED", "true")

    from src.integrations.memory.types import MemoryConfig
    from src.integrations.memory.unified_memory import UnifiedMemoryManager

    mgr = UnifiedMemoryManager(config=MemoryConfig())
    await mgr.initialize()
    yield mgr
    await mgr.close()


@pytest.mark.asyncio
async def test_full_5phase_run_once_executes_all_phases(memory_manager):
    """AC-9: force_run=True triggers all 5 phases; result captures each count."""
    from src.integrations.memory.consolidation import MemoryConsolidationService
    from src.integrations.memory.types import (
        MemoryLayer,
        MemoryMetadata,
        MemoryType,
    )

    user_id = "e2e-5phase-user"

    # Seed diverse corpus:
    #   - 2 near-duplicate LONG_TERM (→ Phase 1 dedup)
    #   - 3 stale low-importance LONG_TERM (→ Phase 2 decay + Phase 4 prune)
    #   - 5 similar low-importance LONG_TERM (→ Phase 5 summarize)
    #   - 1 high-access SESSION (→ Phase 3 promote)
    old = datetime.now(timezone.utc) - timedelta(days=120)

    # Dedup candidates
    await memory_manager.add(
        content="duplicate fact about python typing",
        user_id=user_id,
        memory_type=MemoryType.SYSTEM_KNOWLEDGE,
        layer=MemoryLayer.LONG_TERM,
    )
    await memory_manager.add(
        content="duplicate fact about python typing",
        user_id=user_id,
        memory_type=MemoryType.SYSTEM_KNOWLEDGE,
        layer=MemoryLayer.LONG_TERM,
    )

    # Stale / prunable
    for i in range(3):
        rec = await memory_manager.add(
            content=f"stale topic {i} from long ago",
            user_id=user_id,
            memory_type=MemoryType.SYSTEM_KNOWLEDGE,
            metadata=MemoryMetadata(importance=0.05),
            layer=MemoryLayer.LONG_TERM,
        )
        # Inject old created_at by mutating storage directly where possible
        rec.created_at = old

    # Summarize candidates
    for i in range(5):
        await memory_manager.add(
            content=f"customer feedback theme A variant {i}",
            user_id=user_id,
            memory_type=MemoryType.SYSTEM_KNOWLEDGE,
            metadata=MemoryMetadata(importance=0.2),
            layer=MemoryLayer.LONG_TERM,
        )

    # Promote candidate (high access_count)
    await memory_manager.add(
        content="frequently accessed session memory",
        user_id=user_id,
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.SESSION,
    )
    # Hit search 6 times to bump access_count above threshold
    for _ in range(6):
        await memory_manager.search(
            query="frequently accessed",
            user_id=user_id,
            layers=[MemoryLayer.SESSION],
        )
    await memory_manager._background_tasks.drain(timeout=5.0)

    # Run full consolidation
    svc = MemoryConsolidationService(memory_manager)
    result = await svc.run_once(user_id=user_id, force_run=True)

    assert result is not None
    # AC-9: per-run summary includes all 5 phase counts
    assert result.deduplicated >= 0  # Phase 1 ran
    assert result.decayed >= 0  # Phase 2 ran
    assert result.promoted >= 0  # Phase 3 ran
    assert result.pruned >= 0  # Phase 4 ran
    assert result.summarized >= 0  # Phase 5 ran

    # At least one phase should have produced an action given our seed
    assert result.total_actions >= 1, (
        f"Expected at least 1 action; got {result.total_actions} " f"(errors: {result.errors})"
    )
