"""Unit tests for DefaultPromptBuilder cross-session recall (Sprint 57.151).

Mirrors the 57.148 profile() injection tests: recent_sessions() is mocked and we
assert it is dispatched with the CURRENT session as exclude, its hints reach the
prompt, no user_id → no dispatch, and a failure degrades gracefully.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from agent_harness.context_mgmt.cache_manager import InMemoryCacheManager
from agent_harness.context_mgmt.token_counter.generic_approx import GenericApproxCounter
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.prompt_builder.builder import DefaultPromptBuilder
from tests.unit.agent_harness.prompt_builder.conftest import (
    make_memory_hint,
    make_state,
    msg,
)


@pytest.fixture
def builder_with_recent() -> tuple[DefaultPromptBuilder, AsyncMock, AsyncMock, AsyncMock]:
    """Builder whose search() / profile() / recent_sessions() are mocked independently."""
    retrieval = MemoryRetrieval(layers={})
    mock_search = AsyncMock(return_value=[])
    mock_profile = AsyncMock(return_value=[])
    mock_recent = AsyncMock(return_value=[])
    retrieval.search = mock_search  # type: ignore[method-assign]
    retrieval.profile = mock_profile  # type: ignore[method-assign]
    retrieval.recent_sessions = mock_recent  # type: ignore[method-assign]
    builder = DefaultPromptBuilder(
        memory_retrieval=retrieval,
        cache_manager=InMemoryCacheManager(),
        token_counter=GenericApproxCounter(),
    )
    return builder, mock_search, mock_profile, mock_recent


@pytest.mark.asyncio
async def test_recent_sessions_injected_excluding_current(
    builder_with_recent: tuple[DefaultPromptBuilder, AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """The headline fix: a prior session's summary surfaces in a NEW session, and
    recent_sessions() is dispatched with the CURRENT session excluded."""
    builder, _search, _profile, mock_recent = builder_with_recent
    mock_recent.return_value = [
        make_memory_hint(layer="session", summary="last time we pinned the redirect URI"),
    ]
    tenant_id = uuid4()
    user_id = uuid4()
    state = make_state(
        messages=[msg("user", "what were we working on last time?")],
        tenant_id=tenant_id,
        user_id=user_id,
    )

    artifact = await builder.build(state=state, tenant_id=tenant_id, user_id=user_id)

    content = " ".join(str(m.content) for m in artifact.messages)
    assert "pinned the redirect URI" in content
    mock_recent.assert_awaited_once()
    kwargs = mock_recent.await_args.kwargs
    assert kwargs["tenant_id"] == tenant_id
    assert kwargs["user_id"] == user_id
    assert kwargs["exclude_session_id"] == state.durable.session_id


@pytest.mark.asyncio
async def test_recent_sessions_not_pulled_without_user_id(
    builder_with_recent: tuple[DefaultPromptBuilder, AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """No user_id (anon / legacy caller) → recent_sessions() never dispatched."""
    builder, _search, _profile, mock_recent = builder_with_recent
    tenant_id = uuid4()
    state = make_state(messages=[msg("user", "hi")], tenant_id=tenant_id)  # user_id None

    await builder.build(state=state, tenant_id=tenant_id)

    mock_recent.assert_not_awaited()


@pytest.mark.asyncio
async def test_recent_sessions_empty_renders_no_recall(
    builder_with_recent: tuple[DefaultPromptBuilder, AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """No store / no prior sessions → [] → build still succeeds (byte-identical path)."""
    builder, _search, _profile, mock_recent = builder_with_recent
    mock_recent.return_value = []
    tenant_id = uuid4()
    user_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id, user_id=user_id)

    artifact = await builder.build(state=state, tenant_id=tenant_id, user_id=user_id)

    assert any(m.role == "system" for m in artifact.messages)
    assert "session" not in artifact.layer_metadata["memory_layers_used"]


@pytest.mark.asyncio
async def test_recent_sessions_failure_degrades_gracefully(
    builder_with_recent: tuple[DefaultPromptBuilder, AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """recent_sessions() raising must not crash build() (W3-2 degrade theme)."""
    builder, _search, _profile, mock_recent = builder_with_recent
    mock_recent.side_effect = RuntimeError("DB down")
    tenant_id = uuid4()
    user_id = uuid4()
    state = make_state(messages=[msg("user", "q")], tenant_id=tenant_id, user_id=user_id)

    artifact = await builder.build(state=state, tenant_id=tenant_id, user_id=user_id)

    assert any(m.role == "system" for m in artifact.messages)
