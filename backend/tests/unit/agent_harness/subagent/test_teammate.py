"""
File: backend/tests/unit/agent_harness/subagent/test_teammate.py
Purpose: Unit tests for TeammateExecutor (real child loop) + dispatcher.spawn(TEAMMATE)
    round-trip + send_to_parent report fold.
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-3 → Sprint 57.102 (B2a: real child loop)

Description:
    Sprint 57.102 (B2a): TEAMMATE now drives a REAL child AgentLoop via an injected
    TeammateChildLoopFactory (no single-shot fallback) — mirroring the FORK conversion
    (Sprint 57.94). These tests inject a mock-LLM child loop
    (make_teammate_child_loop_factory) and assert the same outward behavior (summary /
    fail-closed / timeout) now produced by a real loop, plus the send_to_parent report
    fold into the summary.

Created: 2026-05-04 (Sprint 54.2)
Last Modified: 2026-06-11

Modification History:
    - 2026-06-11: Convert to real child loop via TeammateChildLoopFactory + send_to_parent
      fold (Sprint 57.102 B2a)
    - 2026-05-04: Initial creation (Sprint 54.2 US-3)
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

from ._child_loop_helpers import make_teammate_child_loop_factory


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
async def test_teammate_returns_subagent_result_from_child_loop() -> None:
    """TeammateExecutor: child loop returns a final answer → success=True + summary + tokens."""
    chat = MockChatClient(responses=[_mock_response("Researcher report: 3 facts found.")])
    mailbox = MailboxStore()
    teammate = TeammateExecutor(
        teammate_child_loop_factory=make_teammate_child_loop_factory(chat),
        mailbox=mailbox,
    )
    parent_sid = uuid4()
    sid = uuid4()
    result = await teammate.execute(
        subagent_id=sid,
        parent_session_id=parent_sid,
        role="researcher",
        task="Find 3 facts",
        budget=SubagentBudget(),
    )
    assert result.success is True
    assert result.mode == SubagentMode.TEAMMATE
    assert result.subagent_id == sid
    assert "Researcher report: 3 facts found." in result.summary
    assert result.tokens_used == 80  # 50 + 30 (child loop LoopCompleted.total_tokens)
    assert result.error is None


@pytest.mark.asyncio
async def test_teammate_folds_send_to_parent_reports_into_summary() -> None:
    """A send_to_parent report (in the parent mailbox) is drained + folded into the summary."""
    chat = MockChatClient(responses=[_mock_response("Final teammate answer.")])
    mailbox = MailboxStore()
    teammate = TeammateExecutor(
        teammate_child_loop_factory=make_teammate_child_loop_factory(chat),
        mailbox=mailbox,
    )
    parent_sid = uuid4()
    # Simulate a send_to_parent mid-loop report (the tool delivers to THIS queue; the
    # tool->mailbox path itself is covered by test_send_to_parent_tool.py).
    await mailbox.send(
        session_id=parent_sid,
        sender="teammate",
        recipient="parent",
        content="interim finding A",
    )
    result = await teammate.execute(
        subagent_id=uuid4(),
        parent_session_id=parent_sid,
        role="teammate",
        task="investigate",
        budget=SubagentBudget(),
    )
    assert result.success is True
    # Both the report + the final answer reach the parent via the summary.
    assert "interim finding A" in result.summary
    assert "Final teammate answer." in result.summary
    # The mailbox is drained (no leftover).
    assert await mailbox.drain(parent_sid, "parent") == []


@pytest.mark.asyncio
async def test_teammate_no_factory_fails_closed() -> None:
    """TeammateExecutor without a factory fails closed (mirror FORK US-5; no single-shot)."""
    mailbox = MailboxStore()
    teammate = TeammateExecutor(mailbox=mailbox)
    result = await teammate.execute(
        subagent_id=uuid4(),
        parent_session_id=uuid4(),
        role="x",
        task="cannot run",
        budget=SubagentBudget(),
    )
    assert result.success is False
    assert result.error == "teammate_child_loop_factory_unavailable"


@pytest.mark.asyncio
async def test_teammate_timeout_returns_timeout_error() -> None:
    """TeammateExecutor: child loop exceeds budget.max_duration_s → error='timeout: ...'."""

    class SlowChatClient(MockChatClient):
        async def chat(self, request, **kwargs):  # type: ignore[override]
            await asyncio.sleep(0.5)
            return _mock_response("never returned")

    mailbox = MailboxStore()
    teammate = TeammateExecutor(
        teammate_child_loop_factory=make_teammate_child_loop_factory(SlowChatClient()),
        mailbox=mailbox,
    )
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
    # Mailbox empty (child never reported).
    assert await mailbox.drain(parent_sid, "parent") == []


@pytest.mark.asyncio
async def test_teammate_child_exception_returns_fail_closed() -> None:
    """TeammateExecutor: child loop raises → success=False; no mailbox spam."""

    class BrokenChatClient(MockChatClient):
        async def chat(self, request, **kwargs):  # type: ignore[override]
            raise RuntimeError("provider down")

    mailbox = MailboxStore()
    teammate = TeammateExecutor(
        teammate_child_loop_factory=make_teammate_child_loop_factory(BrokenChatClient()),
        mailbox=mailbox,
    )
    parent_sid = uuid4()
    result = await teammate.execute(
        subagent_id=uuid4(),
        parent_session_id=parent_sid,
        role="x",
        task="t",
        budget=SubagentBudget(),
    )
    assert result.success is False
    assert "child_loop_error" in str(result.error)
    assert "RuntimeError" in str(result.error)
    assert await mailbox.drain(parent_sid, "parent") == []


@pytest.mark.asyncio
async def test_dispatcher_spawn_teammate_then_wait_for_round_trip() -> None:
    """End-to-end: dispatcher.spawn(TEAMMATE) → wait_for() → SubagentResult from a child loop."""
    chat = MockChatClient(responses=[_mock_response("Teammate said hi")])
    mailbox = MailboxStore()
    dispatcher = DefaultSubagentDispatcher(
        chat_client=chat,
        mailbox=mailbox,
        teammate_child_loop_factory=make_teammate_child_loop_factory(chat),
    )
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
    assert "Teammate said hi" in result.summary


@pytest.mark.asyncio
async def test_dispatcher_spawn_teammate_no_factory_fails_closed() -> None:
    """dispatcher.spawn(TEAMMATE) without a teammate factory → fail-closed result."""
    chat = MockChatClient(responses=[_mock_response("unused")])
    dispatcher = DefaultSubagentDispatcher(chat_client=chat)
    subagent_id = await dispatcher.spawn(
        mode=SubagentMode.TEAMMATE,
        task="x",
        parent_session_id=uuid4(),
    )
    result = await dispatcher.wait_for(subagent_id)
    assert result.success is False
    assert result.error == "teammate_child_loop_factory_unavailable"
