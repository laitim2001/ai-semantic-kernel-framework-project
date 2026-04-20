"""End-to-end promotion flow test (Sprint 170 AC-5 / AC-11).

Validates full path:
  1. Seed memory at SESSION tier with access_count=0
  2. Call search() 5 times (counter → 5)
  3. Drain background tasks
  4. Invoke consolidation with force_run=True
  5. Verify memory promoted to Qdrant LONG_TERM collection
  6. Verify source tier counter/accessed_at keys cleaned up

Requires real Redis + Qdrant via testcontainers. Test auto-skips when
testcontainers package is absent or Docker is not reachable.

Run with:
    pytest backend/tests/integration/memory/test_promotion_triggered.py -v -m integration
"""

from __future__ import annotations

import asyncio
import os

import pytest

# Skip entire module if testcontainers unavailable
testcontainers = pytest.importorskip(
    "testcontainers",
    reason="testcontainers package required — pip install testcontainers[redis]",
)

from testcontainers.redis import RedisContainer  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def redis_container():
    """Provide a fresh Redis container for the test module."""
    with RedisContainer("redis:7-alpine") as container:
        yield container


@pytest.fixture(scope="module")
def qdrant_url():
    """Qdrant instance URL. Expects docker-compose to provide it at :6333.

    If Qdrant is not reachable, the test is skipped. A full testcontainers
    Qdrant setup is possible but requires more boilerplate — for now we
    assume the local dev docker-compose is running.
    """
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    import urllib.request

    try:
        urllib.request.urlopen(f"{url}/readyz", timeout=2)  # nosec B310
    except Exception:
        pytest.skip(f"Qdrant not reachable at {url} — skipping integration test")
    return url


@pytest.fixture
async def memory_manager(redis_container, qdrant_url, monkeypatch):
    """Spin up UnifiedMemoryManager against testcontainer Redis + local Qdrant."""
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
@pytest.mark.integration
async def test_promotion_triggered_by_5_search_hits(memory_manager):
    """Full E2E: 5 search hits + force consolidation → memory in LONG_TERM."""
    from src.integrations.memory.consolidation import MemoryConsolidationService
    from src.integrations.memory.types import MemoryLayer, MemoryType

    user_id = "e2e-promotion-user"
    test_query = "promotion fixture memory about project standards"

    # Step 1: Seed SESSION tier memory
    record = await memory_manager.add(
        content=test_query,
        user_id=user_id,
        memory_type=MemoryType.SYSTEM_KNOWLEDGE,
        layer=MemoryLayer.SESSION,
    )
    assert record is not None
    mem_id = record.id

    # Step 2: 5 search calls to trigger promotion threshold
    for _ in range(5):
        results = await memory_manager.search(
            query=test_query,
            user_id=user_id,
            layers=[MemoryLayer.SESSION],
        )
        assert any(
            r.memory.id == mem_id for r in results
        ), "Seeded memory must appear in search results"

    # Step 3: Drain background tasks so counter reaches 5 before consolidation
    drained = await memory_manager._background_tasks.drain(timeout=5.0)
    assert drained

    # Verify counter key == 5
    counter_key = f"memory:counter:session:{user_id}:{mem_id}"
    counter_value = await memory_manager._redis.get(counter_key)
    assert counter_value is not None
    assert int(counter_value) == 5, f"Counter should equal 5 after 5 drains, got {counter_value}"

    # Step 4: Force-run consolidation (bypasses 20-count throttle)
    svc = MemoryConsolidationService(memory_manager)
    result = await svc.run_once(user_id=user_id, force_run=True)
    assert result is not None
    assert result.promoted >= 1, (
        f"Expected at least 1 promotion, got {result.promoted}. " f"Errors: {result.errors}"
    )

    # Step 5: Verify memory now in LONG_TERM (via mem0 query)
    long_term_records = await memory_manager.get_user_memories(
        user_id=user_id,
        layers=[MemoryLayer.LONG_TERM],
    )
    promoted_ids = {m.id for m in long_term_records}
    # Note: mem0 may assign new id on promote; check by content match instead
    promoted_content = [m.content for m in long_term_records]
    assert any(
        test_query in c for c in promoted_content
    ), f"Promoted content should be in LONG_TERM. Got: {promoted_content}"

    # Step 6: Verify source tier counter cleanup (AC / Implementation Note 3)
    counter_after = await memory_manager._redis.get(counter_key)
    assert counter_after is None, "Counter key should be cleaned up after promotion"
