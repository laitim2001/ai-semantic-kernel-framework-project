"""Token estimation tests. Sprint 52.2 Day 2.5 — 3 tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from agent_harness.context_mgmt.cache_manager import InMemoryCacheManager
from agent_harness.context_mgmt.token_counter._abc import TokenCounter
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.prompt_builder.builder import DefaultPromptBuilder
from tests.unit.agent_harness.prompt_builder.conftest import (
    make_state,
    make_tool_spec,
    msg,
)


@pytest.mark.asyncio
async def test_token_count_called_with_messages_and_tools() -> None:
    fake: TokenCounter = MagicMock(spec=TokenCounter)
    fake.count = MagicMock(return_value=42)  # type: ignore[method-assign]
    builder = DefaultPromptBuilder(
        memory_retrieval=MemoryRetrieval(layers={}),
        cache_manager=InMemoryCacheManager(),
        token_counter=fake,
    )
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    tools = [make_tool_spec("search")]

    await builder.build(state=state, tenant_id=tenant_id, tools=tools)

    fake.count.assert_called_once()  # type: ignore[attr-defined]
    call_kwargs = fake.count.call_args.kwargs  # type: ignore[attr-defined]
    assert "messages" in call_kwargs
    assert call_kwargs["tools"] == tools


@pytest.mark.asyncio
async def test_estimated_tokens_in_artifact() -> None:
    fake: TokenCounter = MagicMock(spec=TokenCounter)
    fake.count = MagicMock(return_value=137)  # type: ignore[method-assign]
    builder = DefaultPromptBuilder(
        memory_retrieval=MemoryRetrieval(layers={}),
        cache_manager=InMemoryCacheManager(),
        token_counter=fake,
    )
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)

    artifact = await builder.build(state=state, tenant_id=tenant_id)

    assert artifact.estimated_input_tokens == 137


@pytest.mark.asyncio
async def test_token_counter_failure_zero() -> None:
    failing: TokenCounter = MagicMock(spec=TokenCounter)
    failing.count = MagicMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("tokenizer crashed")
    )
    builder = DefaultPromptBuilder(
        memory_retrieval=MemoryRetrieval(layers={}),
        cache_manager=InMemoryCacheManager(),
        token_counter=failing,
    )
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)

    artifact = await builder.build(state=state, tenant_id=tenant_id)

    assert artifact.estimated_input_tokens == 0
    assert any(m.role == "system" for m in artifact.messages)
