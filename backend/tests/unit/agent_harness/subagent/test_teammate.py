"""
File: backend/tests/unit/agent_harness/subagent/test_teammate.py
Purpose: Unit tests for TeammateExecutor + dispatcher.spawn(TEAMMATE) round-trip.
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-3

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
    MailboxStore,
    TeammateExecutor,
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
async def test_teammate_returns_subagent_result_and_delivers_to_mailbox() -> None:
    """TeammateExecutor: happy path → SubagentResult + parent receives summary in mailbox."""
    chat = MockChatClient(responses=[_mock_response("Researcher report: 3 facts found.")])
    mailbox = MailboxStore()
    teammate = TeammateExecutor(chat_client=chat, mailbox=mailbox)
    parent_sid = uuid4()
    sid = uuid4()
    result = await teammate.execute(
        subagent_id=sid,
        parent_session_id=parent_sid,
        role="researcher",
        task="Find 3 facts",
        budget=SubagentBudget(),
    )
    # Result correct
    assert result.success is True
    assert result.mode == SubagentMode.TEAMMATE
    assert result.subagent_id == sid
    assert "Researcher report: 3 facts found." in result.summary
    # Mailbox delivery
    msg = await mailbox.receive(parent_sid, recipient="parent", timeout_s=0.5)
    assert msg is not None
    assert "[from researcher]" in str(msg.content)
    assert "Researcher report: 3 facts found." in str(msg.content)


@pytest.mark.asyncio
async def test_teammate_timeout_returns_timeout_error_no_mailbox_delivery() -> None:
    """TeammateExecutor: budget timeout → fail-closed; mailbox should NOT receive partial."""

    class SlowChatClient(MockChatClient):
        async def chat(self, request, **kwargs):  # type: ignore[override]
            await asyncio.sleep(0.5)
            return _mock_response("never returned")

    mailbox = MailboxStore()
    teammate = TeammateExecutor(chat_client=SlowChatClient(), mailbox=mailbox)
    parent_sid = uuid4()
    result = await teammate.execute(
        subagent_id=uuid4(),
        parent_session_id=parent_sid,
        role="laggard",
        task="slow task",
        budget=SubagentBudget(max_duration_s=0),
    )
    assert result.success is False
    assert result.error is not None
    assert "timeout" in result.error
    # Mailbox should be empty since chat never completed
    msg = await mailbox.receive(parent_sid, recipient="parent", timeout_s=0.05)
    assert msg is None


@pytest.mark.asyncio
async def test_dispatcher_spawn_teammate_then_wait_for_round_trip() -> None:
    """End-to-end: dispatcher.spawn(TEAMMATE) → wait_for() → SubagentResult; parent has summary."""
    chat = MockChatClient(responses=[_mock_response("Teammate said hi")])
    mailbox = MailboxStore()
    dispatcher = DefaultSubagentDispatcher(chat_client=chat, mailbox=mailbox)
    parent_sid = uuid4()
    subagent_id = await dispatcher.spawn(
        mode=SubagentMode.TEAMMATE,
        task="Say hi",
        parent_session_id=parent_sid,
    )
    result = await dispatcher.wait_for(subagent_id)
    assert result.subagent_id == subagent_id
    assert result.mode == SubagentMode.TEAMMATE
    assert result.success is True
    # Parent's mailbox holds the message
    msg = await mailbox.receive(parent_sid, recipient="parent", timeout_s=0.5)
    assert msg is not None
    assert "[from teammate]" in str(msg.content)


@pytest.mark.asyncio
async def test_teammate_chat_exception_returns_fail_closed_no_mailbox_delivery() -> None:
    """TeammateExecutor: ChatClient raises → success=False; no mailbox spam."""

    class BrokenChatClient(MockChatClient):
        async def chat(self, request, **kwargs):  # type: ignore[override]
            raise RuntimeError("provider down")

    mailbox = MailboxStore()
    teammate = TeammateExecutor(chat_client=BrokenChatClient(), mailbox=mailbox)
    parent_sid = uuid4()
    result = await teammate.execute(
        subagent_id=uuid4(),
        parent_session_id=parent_sid,
        role="x",
        task="t",
        budget=SubagentBudget(),
    )
    assert result.success is False
    assert "RuntimeError" in str(result.error)
    msg = await mailbox.receive(parent_sid, recipient="parent", timeout_s=0.05)
    assert msg is None
