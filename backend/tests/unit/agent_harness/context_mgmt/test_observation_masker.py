"""
File: tests/unit/agent_harness/context_mgmt/test_observation_masker.py
Purpose: Unit tests for DefaultObservationMasker (impl: observation_masker.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 3.2

6 tests:
  - test_12turn_keep_recent_5_redacts_old_intact_recent
  - test_preserves_tool_calls_field
  - test_handles_empty_messages
  - test_handles_single_turn
  - test_honors_keep_recent_override
  - test_skips_non_tool_messages
"""

from __future__ import annotations

import pytest

from agent_harness._contracts import Message, ToolCall
from agent_harness.context_mgmt.observation_masker import DefaultObservationMasker


def _build_history(num_turns: int) -> list[Message]:
    """Build [system, (user, assistant w/ tool_calls, tool result) × num_turns]."""
    msgs: list[Message] = [Message(role="system", content="sys prompt")]
    for i in range(num_turns):
        msgs.append(Message(role="user", content=f"user q{i}"))
        msgs.append(
            Message(
                role="assistant",
                content="",
                tool_calls=[ToolCall(id=f"c{i}", name="db_query", arguments={"q": i})],
            )
        )
        msgs.append(
            Message(
                role="tool",
                content=f"large tool result body for turn {i}" * 5,
                tool_call_id=f"c{i}",
                name="db_query",
            )
        )
    return msgs


def test_12turn_keep_recent_5_redacts_old_intact_recent() -> None:
    """Core case: 12 turns + keep_recent=5 → turns 0-6 tool bodies redacted, 7-11 intact."""
    masker = DefaultObservationMasker()
    msgs = _build_history(12)

    out = masker.mask_old_results(msgs, keep_recent=5)

    assert len(out) == len(msgs)
    # Build per-turn map of tool message contents
    tool_msgs = [m for m in out if m.role == "tool"]
    assert len(tool_msgs) == 12
    # First 7 should be redacted
    for i in range(7):
        assert tool_msgs[i].content.startswith("[REDACTED: tool db_query result;")
    # Last 5 should be intact
    for i in range(7, 12):
        assert tool_msgs[i].content.startswith("large tool result body")


def test_preserves_tool_calls_field() -> None:
    """Assistant tool_calls must never be touched, even for old turns."""
    masker = DefaultObservationMasker()
    msgs = _build_history(10)

    out = masker.mask_old_results(msgs, keep_recent=2)

    assistant_msgs = [m for m in out if m.role == "assistant"]
    assert len(assistant_msgs) == 10
    for am in assistant_msgs:
        assert am.tool_calls is not None
        assert len(am.tool_calls) == 1
        assert am.tool_calls[0].name == "db_query"


def test_handles_empty_messages() -> None:
    """Empty input → empty output, no error."""
    masker = DefaultObservationMasker()
    out = masker.mask_old_results([], keep_recent=5)
    assert out == []


def test_handles_single_turn() -> None:
    """history with < keep_recent user messages → nothing is redacted."""
    masker = DefaultObservationMasker()
    msgs = _build_history(2)  # 2 user messages

    out = masker.mask_old_results(msgs, keep_recent=5)

    tool_contents = [m.content for m in out if m.role == "tool"]
    for c in tool_contents:
        assert "[REDACTED" not in c


def test_honors_keep_recent_override() -> None:
    """keep_recent=3 → only the last 3 user→assistant turns survive."""
    masker = DefaultObservationMasker()
    msgs = _build_history(8)

    out = masker.mask_old_results(msgs, keep_recent=3)

    tool_msgs = [m for m in out if m.role == "tool"]
    # First 8-3=5 should be redacted
    for i in range(5):
        assert tool_msgs[i].content.startswith("[REDACTED:")
    # Last 3 intact
    for i in range(5, 8):
        assert not tool_msgs[i].content.startswith("[REDACTED:")


def test_skips_non_tool_messages() -> None:
    """user / system / assistant content untouched."""
    masker = DefaultObservationMasker()
    msgs = _build_history(8)

    out = masker.mask_old_results(msgs, keep_recent=2)

    # System unchanged
    sys_msgs = [m for m in out if m.role == "system"]
    assert len(sys_msgs) == 1
    assert sys_msgs[0].content == "sys prompt"

    # User unchanged
    user_msgs = [m for m in out if m.role == "user"]
    assert [m.content for m in user_msgs] == [f"user q{i}" for i in range(8)]

    # Assistant content untouched (always "" in this fixture)
    asst_msgs = [m for m in out if m.role == "assistant"]
    for m in asst_msgs:
        assert m.content == ""
