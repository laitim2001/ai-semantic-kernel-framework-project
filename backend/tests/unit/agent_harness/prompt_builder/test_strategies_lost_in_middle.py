"""Unit tests for LostInMiddleStrategy. Sprint 52.2 Day 1.8 — 5 tests."""

from __future__ import annotations

from agent_harness.prompt_builder.strategies import (
    LostInMiddleStrategy,
    PromptSections,
)
from tests.unit.agent_harness.prompt_builder.conftest import msg


def _conversation_with_assistants(n_assistants: int = 5) -> list:
    """Build conversation with N assistant messages interleaved with users."""
    out = []
    for i in range(n_assistants):
        out.append(msg("user", f"u{i}"))
        out.append(msg("assistant", f"a{i}"))
    return out


def test_system_at_idx_0() -> None:
    sections = PromptSections(
        system=msg("system", "system role"),
        user_message=msg("user", "current query"),
    )
    result = LostInMiddleStrategy().arrange(sections)
    assert result[0].role == "system"
    assert result[0].content == "system role"


def test_user_echo_at_idx_1() -> None:
    sections = PromptSections(
        system=msg("system", "sys"),
        user_message=msg("user", "important query content"),
    )
    result = LostInMiddleStrategy().arrange(sections)
    # idx 0 = system, idx 1 = user echo (system role with metadata['echo']=True)
    assert result[1].role == "system"
    assert result[1].metadata.get("echo") is True
    assert "important query content" in str(result[1].content)


def test_user_actual_at_last() -> None:
    sections = PromptSections(
        system=msg("system", "sys"),
        conversation=_conversation_with_assistants(3),
        user_message=msg("user", "final actual query"),
    )
    result = LostInMiddleStrategy().arrange(sections)
    assert result[-1].role == "user"
    assert result[-1].content == "final actual query"
    # Ensure actual user message is NOT the echoed one (echo has metadata flag)
    assert result[-1].metadata.get("echo") is None


def test_memory_after_user_echo() -> None:
    from tests.unit.agent_harness.prompt_builder.conftest import make_memory_hint

    sections = PromptSections(
        system=msg("system", "sys"),
        memory_layers={"tenant": [make_memory_hint(summary="company policy")]},
        user_message=msg("user", "ask me"),
    )
    result = LostInMiddleStrategy().arrange(sections)
    # Order: [system(0), user_echo(1), memory_msg(2), user_actual(-1)]
    assert result[0].role == "system" and result[0].metadata.get("echo") is None
    assert result[1].metadata.get("echo") is True
    assert result[2].metadata.get("memory_layer") == "tenant"
    assert "company policy" in str(result[2].content)


def test_recent_assistant_count_3() -> None:
    sections = PromptSections(
        system=msg("system", "sys"),
        conversation=_conversation_with_assistants(5),  # 5 user + 5 assistant
        user_message=msg("user", "query"),
    )
    result = LostInMiddleStrategy(recent_assistant_count=3).arrange(sections)
    # The last 3 assistants should be just before the final user_actual
    # result[-1] = user_actual; result[-2..-4] = last 3 assistants
    last_three = result[-4:-1]
    assert all(m.role == "assistant" for m in last_three)
    assert [m.content for m in last_three] == ["a2", "a3", "a4"]
