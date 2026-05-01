"""Unit tests for NaiveStrategy. Sprint 52.2 Day 1.8 — 3 tests."""

from __future__ import annotations

from agent_harness.prompt_builder.strategies import (
    NaiveStrategy,
    PromptSections,
)
from tests.unit.agent_harness.prompt_builder.conftest import (
    make_memory_hint,
    msg,
)


def test_order_system_first() -> None:
    sections = PromptSections(
        system=msg("system", "sys content"),
        conversation=[msg("user", "old user"), msg("assistant", "old reply")],
        user_message=msg("user", "current"),
    )
    result = NaiveStrategy().arrange(sections)
    assert result[0].role == "system"
    assert result[0].content == "sys content"


def test_memory_between_system_and_conversation() -> None:
    sections = PromptSections(
        system=msg("system", "sys"),
        memory_layers={"user": [make_memory_hint(summary="remember X")]},
        conversation=[msg("assistant", "previous reply")],
        user_message=msg("user", "current"),
    )
    result = NaiveStrategy().arrange(sections)
    # Order: [system, memory_msg, conversation_msg, user_message]
    assert result[0].role == "system"
    assert "remember X" in str(result[1].content)
    assert result[1].metadata.get("memory_layer") == "user"
    assert result[2].role == "assistant"
    assert result[3].content == "current"


def test_user_at_end() -> None:
    sections = PromptSections(
        system=msg("system", "sys"),
        conversation=[msg("user", "u1"), msg("assistant", "a1")],
        user_message=msg("user", "final user query"),
    )
    result = NaiveStrategy().arrange(sections)
    assert result[-1].content == "final user query"
