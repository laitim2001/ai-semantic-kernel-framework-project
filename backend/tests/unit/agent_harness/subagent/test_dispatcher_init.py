"""
File: backend/tests/unit/agent_harness/subagent/test_dispatcher_init.py
Purpose: Unit tests for DefaultSubagentDispatcher (Cat 11 ABC compliance + spawn rejection paths).
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1 (skeleton); US-2 wires FORK + AsTool

Description:
    These tests verify the dispatcher ABC compliance and "out-of-band" rejection
    behavior for AS_TOOL / HANDOFF modes in spawn(). FORK behavior tests live in
    test_fork.py; AsTool behavior tests in test_as_tool.py.

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Update for US-2 (DefaultSubagentDispatcher now requires
      chat_client; HANDOFF still NotImplementedError until US-4)
    - 2026-05-04: Initial creation (Sprint 54.2 US-1)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import SubagentMode
from agent_harness.subagent import (
    DefaultSubagentDispatcher,
    SubagentDispatcher,
    SubagentLaunchError,
)


@pytest.fixture
def dispatcher() -> DefaultSubagentDispatcher:
    return DefaultSubagentDispatcher(chat_client=MockChatClient())


def test_dispatcher_inherits_subagent_dispatcher_abc(
    dispatcher: DefaultSubagentDispatcher,
) -> None:
    """DefaultSubagentDispatcher is a SubagentDispatcher (single-source ABC)."""
    assert isinstance(dispatcher, SubagentDispatcher)


@pytest.mark.asyncio
async def test_spawn_as_tool_mode_raises_launch_error(
    dispatcher: DefaultSubagentDispatcher,
) -> None:
    """AS_TOOL mode does NOT route through spawn(); use as_tool_factory() instead.

    Per Day 0 D1-followup Option A: AS_TOOL returns ToolSpec, not SubagentResult,
    so it cannot share the spawn() / wait_for() retrieval pattern. spawn() must
    raise SubagentLaunchError to surface the misuse.
    """
    with pytest.raises(SubagentLaunchError, match="AS_TOOL mode does not use spawn"):
        await dispatcher.spawn(
            mode=SubagentMode.AS_TOOL,
            task="dummy",
            parent_session_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_spawn_handoff_mode_raises_launch_error(
    dispatcher: DefaultSubagentDispatcher,
) -> None:
    """HANDOFF mode does NOT route through spawn(); use handoff() method instead.

    The ABC has a dedicated handoff() method (returns new session_id directly).
    spawn() raises to prevent silent fallthrough.
    """
    with pytest.raises(SubagentLaunchError, match="HANDOFF mode does not use spawn"):
        await dispatcher.spawn(
            mode=SubagentMode.HANDOFF,
            task="dummy",
            parent_session_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_spawn_teammate_skeleton_raises_not_implemented(
    dispatcher: DefaultSubagentDispatcher,
) -> None:
    """US-2 wires FORK; TEAMMATE still skeleton — raises NotImplementedError until US-3."""
    with pytest.raises(NotImplementedError, match="US-3"):
        await dispatcher.spawn(
            mode=SubagentMode.TEAMMATE,
            task="dummy",
            parent_session_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_handoff_method_skeleton_raises_not_implemented(
    dispatcher: DefaultSubagentDispatcher,
) -> None:
    """US-4 will fill handoff(); for now skeleton raises."""
    with pytest.raises(NotImplementedError, match="US-4"):
        await dispatcher.handoff(target_agent="other", context={})
