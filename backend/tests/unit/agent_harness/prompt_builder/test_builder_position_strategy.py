"""Position strategy override tests. Sprint 52.2 Day 2.5 — 3 tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent_harness.prompt_builder.builder import DefaultPromptBuilder
from agent_harness.prompt_builder.strategies import (
    NaiveStrategy,
    ToolsAtEndStrategy,
)
from tests.unit.agent_harness.prompt_builder.conftest import make_state, msg


@pytest.mark.asyncio
async def test_default_strategy_lost_in_middle(
    builder: DefaultPromptBuilder,
) -> None:
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    artifact = await builder.build(state=state, tenant_id=tenant_id)
    assert artifact.layer_metadata["position_strategy"] == "LostInMiddleStrategy"


@pytest.mark.asyncio
async def test_override_to_naive(builder: DefaultPromptBuilder) -> None:
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    artifact = await builder.build(
        state=state, tenant_id=tenant_id, position_strategy=NaiveStrategy()
    )
    assert artifact.layer_metadata["position_strategy"] == "NaiveStrategy"


@pytest.mark.asyncio
async def test_override_to_tools_at_end(builder: DefaultPromptBuilder) -> None:
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id)
    artifact = await builder.build(
        state=state, tenant_id=tenant_id, position_strategy=ToolsAtEndStrategy()
    )
    assert artifact.layer_metadata["position_strategy"] == "ToolsAtEndStrategy"
