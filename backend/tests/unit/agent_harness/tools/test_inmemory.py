"""
File: backend/tests/unit/agent_harness/tools/test_inmemory.py
Purpose: Unit tests for InMemoryToolRegistry + InMemoryToolExecutor + echo_tool.
Category: Tests / 範疇 2 (stub)
Scope: Phase 50 / Sprint 50.1 (Day 3.3)
Created: 2026-04-30
"""

from __future__ import annotations

import pytest

from agent_harness._contracts import ToolCall
from agent_harness.tools import (
    ECHO_TOOL_SPEC,
    InMemoryToolExecutor,
    InMemoryToolRegistry,
    echo_handler,
    make_echo_executor,
)


def test_registry_register_and_get() -> None:
    reg = InMemoryToolRegistry()
    reg.register(ECHO_TOOL_SPEC)
    assert reg.get("echo_tool") is ECHO_TOOL_SPEC
    assert reg.get("nonexistent") is None
    assert [s.name for s in reg.list()] == ["echo_tool"]


def test_registry_duplicate_raises() -> None:
    reg = InMemoryToolRegistry()
    reg.register(ECHO_TOOL_SPEC)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(ECHO_TOOL_SPEC)


@pytest.mark.asyncio
async def test_executor_echo_tool_success() -> None:
    _, executor = make_echo_executor()
    tc = ToolCall(id="c1", name="echo_tool", arguments={"text": "hi there"})
    result = await executor.execute(tc)
    assert result.success is True
    assert result.content == "hi there"
    assert result.error is None
    assert result.tool_call_id == "c1"
    assert result.tool_name == "echo_tool"


@pytest.mark.asyncio
async def test_executor_unknown_tool_returns_failure_not_raise() -> None:
    _, executor = make_echo_executor()
    tc = ToolCall(id="c2", name="not_registered", arguments={})
    result = await executor.execute(tc)
    assert result.success is False
    assert result.error is not None
    assert "unknown tool" in result.error
    assert result.content == ""


@pytest.mark.asyncio
async def test_executor_handler_exception_caught_into_result() -> None:
    """Tool handler exception must NOT propagate; surfaces as ToolResult.error."""

    async def bad_handler(call: ToolCall) -> str:
        raise RuntimeError("boom")

    executor = InMemoryToolExecutor(handlers={"bad": bad_handler})
    result = await executor.execute(
        ToolCall(id="c3", name="bad", arguments={})
    )
    assert result.success is False
    assert result.error == "boom"


@pytest.mark.asyncio
async def test_executor_batch_executes_all_sequentially() -> None:
    _, executor = make_echo_executor()
    calls = [
        ToolCall(id=f"c{i}", name="echo_tool", arguments={"text": f"msg-{i}"})
        for i in range(3)
    ]
    results = await executor.execute_batch(calls)
    assert len(results) == 3
    assert [r.content for r in results] == ["msg-0", "msg-1", "msg-2"]
    assert all(r.success for r in results)


def test_echo_tool_spec_attributes() -> None:
    """ECHO_TOOL_SPEC has correct annotations + concurrency policy."""
    assert ECHO_TOOL_SPEC.name == "echo_tool"
    assert ECHO_TOOL_SPEC.annotations.read_only is True
    assert ECHO_TOOL_SPEC.annotations.idempotent is True
    assert ECHO_TOOL_SPEC.annotations.destructive is False
    # input_schema requires "text"
    assert "text" in ECHO_TOOL_SPEC.input_schema["properties"]
    assert ECHO_TOOL_SPEC.input_schema["required"] == ["text"]


@pytest.mark.asyncio
async def test_echo_handler_missing_text_returns_empty() -> None:
    """If 'text' arg is missing, handler returns empty string (not crash)."""
    result = await echo_handler(ToolCall(id="c", name="echo_tool", arguments={}))
    assert result == ""
