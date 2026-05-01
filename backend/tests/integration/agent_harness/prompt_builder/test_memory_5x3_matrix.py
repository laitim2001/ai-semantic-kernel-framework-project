"""5 layer x 3 time_scale matrix integration test. Sprint 52.2 Day 2.6.

W3-2 deviation declaration (recorded in retrospective.md Audit Debt):
    Audit prompt mandated real PostgreSQL via docker fixture. However:
    - 51.2 Memory Cat 3 ship surface = MemoryRetrieval coordinator + ABCs +
      InMemoryStore (per 51.2 retrospective)
    - Postgres-backed MemoryStore deferred to Phase 53.x Storage layer

    Day 2.6 uses mocked MemoryRetrieval.search returning the full 5x3 matrix.
    Real-PG validation deferred to Phase 53.x 51.2 Storage W3-2 cleanup.

15 cells: 5 layers (system / tenant / role / user / session) x 3 time_scales
(short_term / long_term / semantic).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from agent_harness._contracts import (
    DurableState,
    LoopState,
    MemoryHint,
    Message,
    StateVersion,
    TransientState,
)
from agent_harness.context_mgmt.cache_manager import InMemoryCacheManager
from agent_harness.context_mgmt.token_counter.tiktoken_counter import (
    TiktokenCounter,
)
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.prompt_builder.builder import DefaultPromptBuilder

LAYERS = ("system", "tenant", "role", "user", "session")
TIME_SCALES = ("short_term", "long_term", "semantic")


def _matrix_hints() -> list[MemoryHint]:
    out: list[MemoryHint] = []
    for layer in LAYERS:
        for ts in TIME_SCALES:
            out.append(
                MemoryHint(
                    hint_id=uuid4(),
                    layer=layer,  # type: ignore[arg-type]
                    time_scale=ts,  # type: ignore[arg-type]
                    summary=f"{layer}-{ts}-content",
                    confidence=0.8,
                    relevance_score=0.7,
                    full_content_pointer=f"db://memory/{layer}/{ts}/{uuid4()}",
                    timestamp=datetime.now(timezone.utc),
                )
            )
    return out


def _state(tenant_id, messages):
    return LoopState(
        transient=TransientState(messages=messages),
        durable=DurableState(session_id=uuid4(), tenant_id=tenant_id),
        version=StateVersion(
            version=1,
            parent_version=None,
            created_at=datetime.now(timezone.utc),
            created_by_category="orchestrator_loop",
        ),
    )


@pytest.mark.asyncio
async def test_5x3_matrix_full_coverage() -> None:
    retrieval = MemoryRetrieval(layers={})
    retrieval.search = AsyncMock(return_value=_matrix_hints())  # type: ignore[method-assign]
    builder = DefaultPromptBuilder(
        memory_retrieval=retrieval,
        cache_manager=InMemoryCacheManager(),
        token_counter=TiktokenCounter(model="gpt-4o"),
    )
    tenant_id = uuid4()
    state = _state(tenant_id, [Message(role="user", content="query")])

    artifact = await builder.build(state=state, tenant_id=tenant_id)

    used = artifact.layer_metadata["memory_layers_used"]
    assert set(used) == set(LAYERS)

    for layer in LAYERS:
        layer_msg = next(
            m for m in artifact.messages if m.metadata.get("memory_layer") == layer
        )
        content = str(layer_msg.content)
        for ts in TIME_SCALES:
            assert f"{layer}-{ts}-content" in content
        long_idx = content.index(f"{layer}-long_term-content")
        sem_idx = content.index(f"{layer}-semantic-content")
        short_idx = content.index(f"{layer}-short_term-content")
        assert long_idx < sem_idx < short_idx

    assert len(artifact.cache_breakpoints) == 3
    assert all(bp.content_hash is not None for bp in artifact.cache_breakpoints)
    assert artifact.estimated_input_tokens > 0


@pytest.mark.asyncio
async def test_5x3_matrix_empty_query_skips_injection() -> None:
    retrieval = MemoryRetrieval(layers={})
    mock_search = AsyncMock(return_value=_matrix_hints())
    retrieval.search = mock_search  # type: ignore[method-assign]
    builder = DefaultPromptBuilder(
        memory_retrieval=retrieval,
        cache_manager=InMemoryCacheManager(),
        token_counter=TiktokenCounter(model="gpt-4o"),
    )
    tenant_id = uuid4()
    state = _state(tenant_id, [])

    artifact = await builder.build(state=state, tenant_id=tenant_id)

    mock_search.assert_not_called()
    assert artifact.layer_metadata["memory_layers_used"] == []
