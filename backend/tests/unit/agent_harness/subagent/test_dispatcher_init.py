"""
File: backend/tests/unit/agent_harness/subagent/test_dispatcher_init.py
Purpose: Unit tests for DefaultSubagentDispatcher skeleton (Cat 11 ABC compliance).
Category: Tests / 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1 (skeleton); US-2/3/4 fill in mode executors

Description:
    These tests verify the dispatcher skeleton ABC compliance and "out-of-band"
    behavior for AS_TOOL / HANDOFF in spawn(). US-2/3/4 will replace
    NotImplementedError tests with real mode-executor behavior tests.

Created: 2026-05-04 (Sprint 54.2)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent_harness._contracts import SubagentMode
from agent_harness.subagent import (
    DefaultSubagentDispatcher,
    SubagentDispatcher,
    SubagentLaunchError,
)


def test_dispatcher_inherits_subagent_dispatcher_abc() -> None:
    """DefaultSubagentDispatcher is a SubagentDispatcher (single-source ABC)."""
    d = DefaultSubagentDispatcher()
    assert isinstance(d, SubagentDispatcher)


@pytest.mark.asyncio
async def test_spawn_as_tool_mode_raises_launch_error() -> None:
    """AS_TOOL mode does NOT route through spawn(); use as_tool_factory() instead.

    Per Day 0 D1-followup Option A: AS_TOOL returns ToolSpec, not SubagentResult,
    so it cannot share the spawn() / wait_for() retrieval pattern. spawn() must
    raise SubagentLaunchError to surface the misuse.
    """
    d = DefaultSubagentDispatcher()
    with pytest.raises(SubagentLaunchError, match="AS_TOOL mode does not use spawn"):
        await d.spawn(
            mode=SubagentMode.AS_TOOL,
            task="dummy",
            parent_session_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_spawn_handoff_mode_raises_launch_error() -> None:
    """HANDOFF mode does NOT route through spawn(); use handoff() method instead.

    The ABC has a dedicated handoff() method (returns new session_id directly).
    spawn() raises to prevent silent fallthrough.
    """
    d = DefaultSubagentDispatcher()
    with pytest.raises(SubagentLaunchError, match="HANDOFF mode does not use spawn"):
        await d.spawn(
            mode=SubagentMode.HANDOFF,
            task="dummy",
            parent_session_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_spawn_fork_mode_skeleton_raises_not_implemented() -> None:
    """US-1 skeleton: FORK / TEAMMATE raise NotImplementedError; US-2/3 fill."""
    d = DefaultSubagentDispatcher()
    with pytest.raises(NotImplementedError, match="US-2.*FORK"):
        await d.spawn(
            mode=SubagentMode.FORK,
            task="dummy",
            parent_session_id=uuid4(),
        )
