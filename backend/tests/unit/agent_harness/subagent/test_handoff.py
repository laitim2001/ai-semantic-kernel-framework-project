"""
File: backend/tests/unit/agent_harness/subagent/test_handoff.py
Purpose: Unit tests for HandoffExecutor + dispatcher.handoff().
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-4

Created: 2026-05-04 (Sprint 54.2)
"""

from __future__ import annotations

from uuid import UUID

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness.subagent import (
    DefaultSubagentDispatcher,
    HandoffExecutor,
)


@pytest.mark.asyncio
async def test_handoff_executor_returns_uuid() -> None:
    """HandoffExecutor: happy path returns a fresh UUID."""
    he = HandoffExecutor()
    result = await he.execute(target_agent="researcher", context={"k": "v"})
    assert isinstance(result, UUID)


@pytest.mark.asyncio
async def test_handoff_executor_rejects_empty_target() -> None:
    """HandoffExecutor: empty / whitespace target_agent → ValueError."""
    he = HandoffExecutor()
    with pytest.raises(ValueError, match="target_agent must be non-empty"):
        await he.execute(target_agent="", context={})
    with pytest.raises(ValueError, match="target_agent must be non-empty"):
        await he.execute(target_agent="   ", context={})


@pytest.mark.asyncio
async def test_dispatcher_handoff_returns_uuid() -> None:
    """End-to-end: dispatcher.handoff() returns new session_id (UUID)."""
    dispatcher = DefaultSubagentDispatcher(chat_client=MockChatClient())
    new_session_id = await dispatcher.handoff(
        target_agent="critic",
        context={"reason": "domain expertise"},
    )
    assert isinstance(new_session_id, UUID)
