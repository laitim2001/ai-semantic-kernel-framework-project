"""Unit tests for DefaultPromptBuilder basics. Sprint 52.2 Day 1.8 — 4 tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent_harness._contracts import CachePolicy, PromptArtifact
from agent_harness.prompt_builder.builder import DefaultPromptBuilder
from agent_harness.prompt_builder.strategies import LostInMiddleStrategy
from tests.unit.agent_harness.prompt_builder.conftest import make_state, msg


@pytest.mark.asyncio
async def test_build_returns_prompt_artifact(
    builder: DefaultPromptBuilder,
) -> None:
    tenant_id = uuid4()
    state = make_state(
        messages=[msg("user", "hello")],
        tenant_id=tenant_id,
    )
    artifact = await builder.build(state=state, tenant_id=tenant_id)
    assert isinstance(artifact, PromptArtifact)
    # System + user_echo + user_actual = at least 3 messages with default LostInMiddle
    assert len(artifact.messages) >= 2


def test_default_strategy_lost_in_middle(builder: DefaultPromptBuilder) -> None:
    assert isinstance(builder._default_strategy, LostInMiddleStrategy)


def test_default_cache_policy(builder: DefaultPromptBuilder) -> None:
    assert isinstance(builder._default_cache_policy, CachePolicy)
    # 52.1 default policy: enabled + cache_system + cache_tools + cache_memory; recent_turns=False
    assert builder._default_cache_policy.enabled is True
    assert builder._default_cache_policy.cache_recent_turns is False


@pytest.mark.asyncio
async def test_layer_metadata_keys(builder: DefaultPromptBuilder) -> None:
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    artifact = await builder.build(state=state, tenant_id=tenant_id)
    # 4 keys per plan §2.4 + W3-2 carryover
    md = artifact.layer_metadata
    assert "memory_layers_used" in md
    assert "position_strategy" in md
    assert md["position_strategy"] == "LostInMiddleStrategy"
    assert "cache_sections" in md
    assert "trace_id" in md
    assert isinstance(md["trace_id"], str) and md["trace_id"]
