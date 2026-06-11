"""
File: backend/tests/unit/agent_harness/subagent/test_teammate_inbox.py
Purpose: Unit tests — the teammate child loop receives the B1 MessageInbox via the
    executor's inbox_factory + drains a queued message at its turn boundary (B1 seam).
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 57.102 (B2a)

Description:
    B2a wires the teammate child loop with a MessageInbox (reusing B1's
    QueueMessageInbox over the InjectionRegistry keyed by subagent_id). The live UI
    producer is B2b; here we prove the wiring end-to-end by pre-seeding the registry
    queue (simulating a future inject-to-teammate POST) and asserting the child loop
    consumes it via the B1 drain seam (loop.py is unchanged — the child reuses it).

Created: 2026-06-11 (Sprint 57.102 B2a)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import (
    ChatResponse,
    Message,
    MessageInbox,
    StopReason,
    SubagentBudget,
    TokenUsage,
)
from agent_harness.subagent import MailboxStore, TeammateExecutor
from api.v1.chat.injection_registry import InjectionRegistry, QueueMessageInbox

from ._child_loop_helpers import make_teammate_child_loop_factory


def _mock_response(text: str) -> ChatResponse:
    return ChatResponse(
        model="mock-gpt",
        content=text,
        stop_reason=StopReason.END_TURN,
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


class _NullInbox(MessageInbox):
    """A MessageInbox that always drains empty (for the factory-call spy test)."""

    async def drain(self) -> list[Message]:
        return []


@pytest.mark.asyncio
async def test_executor_calls_inbox_factory_with_subagent_id() -> None:
    """The TeammateExecutor builds the child's inbox via inbox_factory(subagent_id)."""
    captured: list[UUID] = []

    def inbox_factory(sid: UUID) -> MessageInbox:
        captured.append(sid)
        return _NullInbox()

    teammate = TeammateExecutor(
        teammate_child_loop_factory=make_teammate_child_loop_factory(
            MockChatClient(responses=[_mock_response("done")])
        ),
        mailbox=MailboxStore(),
        inbox_factory=inbox_factory,
    )
    sid = uuid4()
    result = await teammate.execute(
        subagent_id=sid,
        parent_session_id=uuid4(),
        role="teammate",
        task="go",
        budget=SubagentBudget(),
    )
    assert result.success is True
    assert captured == [sid]  # the factory was called with the child's subagent_id


@pytest.mark.asyncio
async def test_teammate_child_loop_drains_queued_inbox_message() -> None:
    """A message queued for the child's subagent_id is drained by the child loop (B1 seam)."""
    registry = InjectionRegistry()
    tenant_id = uuid4()

    def inbox_factory(sid: UUID) -> MessageInbox:
        return QueueMessageInbox(registry, tenant_id, sid)

    teammate = TeammateExecutor(
        teammate_child_loop_factory=make_teammate_child_loop_factory(
            MockChatClient(responses=[_mock_response("done")])
        ),
        mailbox=MailboxStore(),
        inbox_factory=inbox_factory,
    )
    sid = uuid4()
    # Pre-seed the child's inbox queue (simulates a future B2b inject-to-teammate POST).
    await registry.register(tenant_id, sid)
    await registry.put(tenant_id, sid, Message(role="user", content="also check the db pool"))

    result = await teammate.execute(
        subagent_id=sid,
        parent_session_id=uuid4(),
        role="teammate",
        task="investigate",
        budget=SubagentBudget(),
    )
    assert result.success is True
    # The child loop drained the inbox at its turn boundary (the B1 seam consumed it).
    assert await registry.drain(tenant_id, sid) == []


@pytest.mark.asyncio
async def test_teammate_no_inbox_factory_runs_without_inbox() -> None:
    """Without an inbox_factory the teammate child runs fine (inbox=None → no drain)."""
    teammate = TeammateExecutor(
        teammate_child_loop_factory=make_teammate_child_loop_factory(
            MockChatClient(responses=[_mock_response("done")])
        ),
        mailbox=MailboxStore(),
    )
    result = await teammate.execute(
        subagent_id=uuid4(),
        parent_session_id=uuid4(),
        role="teammate",
        task="go",
        budget=SubagentBudget(),
    )
    assert result.success is True
