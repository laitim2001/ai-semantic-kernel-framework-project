"""Unit tests for ToolsAtEndStrategy. Sprint 52.2 Day 1.8 — 3 tests."""

from __future__ import annotations

from agent_harness.prompt_builder.strategies import (
    PromptSections,
    ToolsAtEndStrategy,
)
from tests.unit.agent_harness.prompt_builder.conftest import (
    make_tool_spec,
    msg,
)


def test_system_first() -> None:
    sections = PromptSections(
        system=msg("system", "sys"),
        user_message=msg("user", "ask"),
    )
    result = ToolsAtEndStrategy().arrange(sections)
    assert result[0].role == "system"
    assert result[0].content == "sys"


def test_tools_hint_at_last_when_tools_present() -> None:
    sections = PromptSections(
        system=msg("system", "sys"),
        tools=[make_tool_spec("search"), make_tool_spec("fetch")],
        user_message=msg("user", "ask"),
    )
    result = ToolsAtEndStrategy().arrange(sections)
    assert result[-1].role == "system"
    assert result[-1].metadata.get("tools_position_hint") is True
    assert result[-1].metadata.get("tool_count") == 2


def test_user_before_tools_hint() -> None:
    sections = PromptSections(
        system=msg("system", "sys"),
        tools=[make_tool_spec()],
        user_message=msg("user", "actual query"),
    )
    result = ToolsAtEndStrategy().arrange(sections)
    # result[-2] = user, result[-1] = tools hint
    assert result[-2].role == "user"
    assert result[-2].content == "actual query"
    assert result[-1].metadata.get("tools_position_hint") is True
