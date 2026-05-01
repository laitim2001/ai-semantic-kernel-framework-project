"""Cache breakpoint integration tests. Sprint 52.2 Day 2.4 — 6 tests.

- default_policy_3_breakpoints
- cache_recent_turns_disabled_default
- content_hash_deterministic
- layer_metadata_cache_sections
- cache_manager_failure_degrades
- disabled_policy_returns_no_breakpoints
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from agent_harness._contracts import CachePolicy
from agent_harness.context_mgmt.cache_manager import (
    InMemoryCacheManager,
    PromptCacheManager,
)
from agent_harness.context_mgmt.token_counter.generic_approx import (
    GenericApproxCounter,
)
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.prompt_builder.builder import DefaultPromptBuilder
from tests.unit.agent_harness.prompt_builder.conftest import make_state, msg


def _builder_with_real_cache() -> DefaultPromptBuilder:
    return DefaultPromptBuilder(
        memory_retrieval=MemoryRetrieval(layers={}),
        cache_manager=InMemoryCacheManager(),
        token_counter=GenericApproxCounter(),
    )


@pytest.mark.asyncio
async def test_default_policy_3_breakpoints() -> None:
    builder = _builder_with_real_cache()
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    artifact = await builder.build(state=state, tenant_id=tenant_id)
    section_ids = [bp.section_id for bp in artifact.cache_breakpoints]
    assert "system_prompt" in section_ids
    assert "tool_definitions" in section_ids
    assert "memory_layers" in section_ids
    assert len(artifact.cache_breakpoints) == 3


@pytest.mark.asyncio
async def test_cache_recent_turns_disabled_default() -> None:
    builder = _builder_with_real_cache()
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    artifact = await builder.build(state=state, tenant_id=tenant_id)
    section_ids = [bp.section_id for bp in artifact.cache_breakpoints]
    assert "recent_turns" not in section_ids
    assert "conversation" not in section_ids


@pytest.mark.asyncio
async def test_content_hash_deterministic() -> None:
    builder = _builder_with_real_cache()
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "same query")], tenant_id=tenant_id)
    artifact1 = await builder.build(state=state, tenant_id=tenant_id)
    artifact2 = await builder.build(state=state, tenant_id=tenant_id)
    hashes1 = {bp.section_id: bp.content_hash for bp in artifact1.cache_breakpoints}
    hashes2 = {bp.section_id: bp.content_hash for bp in artifact2.cache_breakpoints}
    assert hashes1 == hashes2
    assert all(h is not None for h in hashes1.values())


@pytest.mark.asyncio
async def test_layer_metadata_cache_sections() -> None:
    builder = _builder_with_real_cache()
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    artifact = await builder.build(state=state, tenant_id=tenant_id)
    cache_sections = artifact.layer_metadata["cache_sections"]
    assert isinstance(cache_sections, list)
    assert set(cache_sections) == {"system_prompt", "tool_definitions", "memory_layers"}


@pytest.mark.asyncio
async def test_cache_manager_failure_degrades() -> None:
    failing: PromptCacheManager = InMemoryCacheManager()
    failing.get_cache_breakpoints = AsyncMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("cache backend down")
    )
    builder = DefaultPromptBuilder(
        memory_retrieval=MemoryRetrieval(layers={}),
        cache_manager=failing,
        token_counter=GenericApproxCounter(),
    )
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    artifact = await builder.build(state=state, tenant_id=tenant_id)
    assert artifact.cache_breakpoints == []
    assert artifact.layer_metadata["cache_sections"] == []
    assert any(m.role == "system" for m in artifact.messages)


@pytest.mark.asyncio
async def test_disabled_policy_returns_no_breakpoints() -> None:
    builder = _builder_with_real_cache()
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    disabled = CachePolicy(enabled=False)
    artifact = await builder.build(
        state=state, tenant_id=tenant_id, cache_policy=disabled
    )
    assert artifact.cache_breakpoints == []
