"""
File: backend/tests/unit/agent_harness/subagent/test_fork.py
Purpose: Unit tests for ForkExecutor + dispatcher.spawn(FORK) round-trip.
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-2

Created: 2026-05-04 (Sprint 54.2)
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import (
    ChatResponse,
    StopReason,
    SubagentBudget,
    SubagentMode,
    TokenUsage,
)
from agent_harness.subagent import (
    DefaultSubagentDispatcher,
    ForkExecutor,
)


def _mock_response(text: str, prompt: int = 50, completion: int = 30) -> ChatResponse:
    return ChatResponse(
        model="mock-gpt",
        content=text,
        stop_reason=StopReason.END_TURN,
        usage=TokenUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
        ),
    )


@pytest.mark.asyncio
async def test_fork_returns_subagent_result_with_summary() -> None:
    """ForkExecutor: happy path — chat_client returns text → success=True + summary."""
    chat = MockChatClient(responses=[_mock_response("Subagent did X and Y.")])
    fork = ForkExecutor(chat_client=chat)
    sid = uuid4()
    result = await fork.execute(
        subagent_id=sid,
        task="Compute X and Y.",
        budget=SubagentBudget(),
    )
    assert result.success is True
    assert result.subagent_id == sid
    assert result.mode == SubagentMode.FORK
    assert "Subagent did X and Y." in result.summary
    assert result.tokens_used == 80  # 50 + 30
    assert result.error is None


@pytest.mark.asyncio
async def test_fork_summary_truncated_to_cap() -> None:
    """ForkExecutor: response > cap_words=500 → truncated marker appended."""
    long_text = " ".join(["word"] * 1000)  # 1000 words
    chat = MockChatClient(responses=[_mock_response(long_text)])
    fork = ForkExecutor(chat_client=chat)
    result = await fork.execute(
        subagent_id=uuid4(),
        task="Generate long output",
        budget=SubagentBudget(),
    )
    assert result.success is True
    assert result.summary.endswith("[...truncated]")
    # Truncated to 500 words + truncation marker (1 word) = 501 tokens total
    assert len(result.summary.split()) == 501


@pytest.mark.asyncio
async def test_fork_chat_exception_returns_fail_closed() -> None:
    """ForkExecutor: ChatClient.chat() raises → SubagentResult(success=False, error=...)."""

    class BrokenChatClient(MockChatClient):
        async def chat(self, request, **kwargs):  # type: ignore[override]
            raise RuntimeError("provider down")

    fork = ForkExecutor(chat_client=BrokenChatClient())
    result = await fork.execute(
        subagent_id=uuid4(),
        task="Will fail",
        budget=SubagentBudget(),
    )
    assert result.success is False
    assert result.summary == ""
    assert result.error is not None
    assert "RuntimeError" in result.error
    assert "provider down" in result.error


@pytest.mark.asyncio
async def test_fork_timeout_returns_timeout_error() -> None:
    """ForkExecutor: chat exceeds budget.max_duration_s → SubagentResult(error='timeout: ...')."""

    class SlowChatClient(MockChatClient):
        async def chat(self, request, **kwargs):  # type: ignore[override]
            await asyncio.sleep(0.5)  # Longer than budget below
            return _mock_response("never returned")

    fork = ForkExecutor(chat_client=SlowChatClient())
    result = await fork.execute(
        subagent_id=uuid4(),
        task="Slow task",
        budget=SubagentBudget(max_duration_s=0),  # Force immediate timeout
    )
    assert result.success is False
    assert result.error is not None
    assert "timeout" in result.error


@pytest.mark.asyncio
async def test_dispatcher_spawn_fork_then_wait_for_round_trip() -> None:
    """End-to-end: dispatcher.spawn(FORK) returns UUID → wait_for(uuid) → SubagentResult."""
    chat = MockChatClient(responses=[_mock_response("Round-trip OK")])
    dispatcher = DefaultSubagentDispatcher(chat_client=chat)
    subagent_id = await dispatcher.spawn(
        mode=SubagentMode.FORK,
        task="Test round trip",
        parent_session_id=uuid4(),
    )
    result = await dispatcher.wait_for(subagent_id)
    assert result.subagent_id == subagent_id
    assert result.success is True
    assert "Round-trip OK" in result.summary
