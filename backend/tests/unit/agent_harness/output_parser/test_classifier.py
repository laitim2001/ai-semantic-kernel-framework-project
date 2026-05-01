"""
File: backend/tests/unit/agent_harness/output_parser/test_classifier.py
Purpose: Unit tests for classify_output() — Cat 6 dispatch classifier.
Category: Tests / 範疇 6
Scope: Phase 50 / Sprint 50.1 (Day 1.4)
Created: 2026-04-29
"""

from __future__ import annotations

from agent_harness._contracts import ChatResponse, StopReason, ToolCall
from agent_harness.output_parser import (
    HANDOFF_TOOL_NAME,
    OutputType,
    classify_output,
)


def _resp(
    *,
    tool_calls: list[ToolCall] | None = None,
    stop: StopReason = StopReason.END_TURN,
) -> ChatResponse:
    return ChatResponse(model="m", content="", tool_calls=tool_calls, stop_reason=stop)


def test_classify_final_no_tool_calls() -> None:
    """No tool_calls → FINAL (assistant final answer)."""
    assert classify_output(_resp()) == OutputType.FINAL
    assert classify_output(_resp(tool_calls=[])) == OutputType.FINAL


def test_classify_tool_use() -> None:
    """Non-empty tool_calls without 'handoff' → TOOL_USE."""
    tcs = [ToolCall(id="1", name="echo", arguments={})]
    assert classify_output(_resp(tool_calls=tcs)) == OutputType.TOOL_USE


def test_classify_handoff_priority_over_tool_use() -> None:
    """Mixed tool_calls including 'handoff' → HANDOFF (priority)."""
    tcs = [
        ToolCall(id="1", name="echo", arguments={}),
        ToolCall(id="2", name=HANDOFF_TOOL_NAME, arguments={"target_agent": "x"}),
    ]
    assert classify_output(_resp(tool_calls=tcs)) == OutputType.HANDOFF
