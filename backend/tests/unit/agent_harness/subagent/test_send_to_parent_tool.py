"""
File: backend/tests/unit/agent_harness/subagent/test_send_to_parent_tool.py
Purpose: Unit tests for make_send_to_parent_tool (TEAMMATE child→parent report).
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 57.102 (B2a)

Created: 2026-06-11 (Sprint 57.102 B2a)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent_harness.subagent import MailboxStore, make_send_to_parent_tool


@pytest.mark.asyncio
async def test_send_to_parent_delivers_to_parent_mailbox() -> None:
    """The send_to_parent handler delivers the message to the parent's mailbox queue."""
    mailbox = MailboxStore()
    parent_sid = uuid4()
    spec, handler = make_send_to_parent_tool(
        mailbox=mailbox, parent_session_id=parent_sid, role="researcher"
    )
    assert spec.name == "send_to_parent"
    assert "message" in spec.input_schema["properties"]

    result = await handler({"message": "found 3 incidents"})
    assert result["delivered"] is True

    reports = await mailbox.drain(parent_sid, "parent")
    assert len(reports) == 1
    assert "[from researcher]" in str(reports[0].content)
    assert "found 3 incidents" in str(reports[0].content)


@pytest.mark.asyncio
async def test_send_to_parent_empty_message_not_delivered() -> None:
    """An empty / whitespace message is rejected (delivered=False); nothing queued."""
    mailbox = MailboxStore()
    parent_sid = uuid4()
    _, handler = make_send_to_parent_tool(mailbox=mailbox, parent_session_id=parent_sid)

    result = await handler({"message": "   "})
    assert result["delivered"] is False
    assert result["error"] == "empty_message"
    assert await mailbox.drain(parent_sid, "parent") == []


@pytest.mark.asyncio
async def test_send_to_parent_default_role_is_teammate() -> None:
    """Default role annotation is 'teammate' (the sender prefix)."""
    mailbox = MailboxStore()
    parent_sid = uuid4()
    _, handler = make_send_to_parent_tool(mailbox=mailbox, parent_session_id=parent_sid)
    await handler({"message": "hello parent"})
    reports = await mailbox.drain(parent_sid, "parent")
    assert "[from teammate]" in str(reports[0].content)
