"""
File: backend/tests/unit/agent_harness/orchestrator_loop/test_termination.py
Purpose: Unit tests for 4 terminators + TerminationReason enum.
Category: Tests / 範疇 1
Scope: Phase 50 / Sprint 50.1 (Day 2.1)
Created: 2026-04-30
"""

from __future__ import annotations

import asyncio

import pytest

from agent_harness._contracts import ChatResponse, StopReason
from agent_harness.orchestrator_loop.termination import (
    TerminationReason,
    TripwireTerminator,
    should_terminate_by_cancellation,
    should_terminate_by_stop_reason,
    should_terminate_by_tokens,
    should_terminate_by_turns,
)


def _resp(stop: StopReason) -> ChatResponse:
    return ChatResponse(model="m", content="", stop_reason=stop)


def test_stop_reason_end_turn_terminates() -> None:
    assert should_terminate_by_stop_reason(_resp(StopReason.END_TURN)) is True


def test_stop_reason_tool_use_does_not_terminate() -> None:
    assert should_terminate_by_stop_reason(_resp(StopReason.TOOL_USE)) is False


def test_turns_at_or_above_max_terminates() -> None:
    assert should_terminate_by_turns(turn_count=5, max_turns=5) is True
    assert should_terminate_by_turns(turn_count=6, max_turns=5) is True


def test_turns_below_max_does_not_terminate() -> None:
    assert should_terminate_by_turns(turn_count=4, max_turns=5) is False


def test_tokens_at_or_above_budget_terminates() -> None:
    assert should_terminate_by_tokens(tokens_used=100, token_budget=100) is True
    assert should_terminate_by_tokens(tokens_used=101, token_budget=100) is True


def test_tokens_below_budget_does_not_terminate() -> None:
    assert should_terminate_by_tokens(tokens_used=99, token_budget=100) is False


@pytest.mark.asyncio
async def test_cancellation_false_when_task_not_cancelled() -> None:
    """Inside a normal task, cancelling() returns 0 → False."""
    assert should_terminate_by_cancellation() is False


@pytest.mark.asyncio
async def test_cancellation_true_when_task_cancelled() -> None:
    """Once a task receives .cancel(), cancelling() > 0 → True before the
    CancelledError actually propagates."""
    detected = False

    async def child() -> None:
        nonlocal detected
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            # Inside the cancel-handling region: cancelling() > 0 here.
            detected = should_terminate_by_cancellation()
            raise

    task = asyncio.create_task(child())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert detected is True


def test_termination_reason_values() -> None:
    """All 7 reasons present + values stable for use as LoopCompleted.stop_reason."""
    assert TerminationReason.END_TURN.value == "end_turn"
    assert TerminationReason.MAX_TURNS.value == "max_turns"
    assert TerminationReason.TOKEN_BUDGET.value == "token_budget"
    assert TerminationReason.CANCELLED.value == "cancelled"
    assert TerminationReason.TRIPWIRE.value == "tripwire"
    assert TerminationReason.ERROR.value == "error"
    assert TerminationReason.HANDOFF_NOT_IMPLEMENTED.value == "handoff_not_implemented"


def test_tripwire_terminator_abc_unimplementable() -> None:
    """ABC stub can't be instantiated; concrete impl required (Phase 53.3)."""
    with pytest.raises(TypeError):
        TripwireTerminator()  # type: ignore[abstract]
