"""
File: backend/tests/unit/api/v1/chat/test_sse.py
Purpose: Unit tests for SSE serializer (LoopEvent → wire format).
Category: tests
Scope: Phase 50 / Sprint 50.2 (Day 1.3)

Created: 2026-04-30
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from agent_harness._contracts import (
    LoopCompleted,
    LoopStarted,
    Thinking,
    ToolCallExecuted,
    ToolCallRequested,
    VerificationPassed,
)
from api.v1.chat.sse import format_sse_message, serialize_loop_event


class TestSerializeLoopEvent:
    def test_loop_started(self) -> None:
        sid = uuid4()
        ev = LoopStarted(session_id=sid)
        out = serialize_loop_event(ev)
        assert out["type"] == "loop_start"
        assert out["data"]["session_id"] == str(sid)
        assert "request_id" in out["data"]

    def test_loop_started_no_session(self) -> None:
        ev = LoopStarted()
        out = serialize_loop_event(ev)
        assert out["data"]["session_id"] is None

    def test_thinking_maps_to_llm_response(self) -> None:
        ev = Thinking(text="hello world")
        out = serialize_loop_event(ev)
        assert out["type"] == "llm_response"
        assert out["data"]["content"] == "hello world"

    def test_tool_call_requested(self) -> None:
        ev = ToolCallRequested(
            tool_call_id="call_123",
            tool_name="echo_tool",
            arguments={"text": "X"},
        )
        out = serialize_loop_event(ev)
        assert out["type"] == "tool_call_request"
        assert out["data"]["tool_call_id"] == "call_123"
        assert out["data"]["tool_name"] == "echo_tool"
        assert out["data"]["args"] == {"text": "X"}

    def test_tool_call_executed(self) -> None:
        ev = ToolCallExecuted(
            tool_call_id="call_123",
            tool_name="echo_tool",
            duration_ms=1.25,
        )
        out = serialize_loop_event(ev)
        assert out["type"] == "tool_call_result"
        assert out["data"]["duration_ms"] == 1.25
        assert out["data"]["is_error"] is False

    def test_loop_completed(self) -> None:
        ev = LoopCompleted(stop_reason="end_turn", total_turns=2)
        out = serialize_loop_event(ev)
        assert out["type"] == "loop_end"
        assert out["data"]["stop_reason"] == "end_turn"
        assert out["data"]["total_turns"] == 2

    def test_unsupported_event_raises_with_sprint_pointer(self) -> None:
        ev = VerificationPassed(verifier="some_verifier")
        with pytest.raises(NotImplementedError, match="Sprint 50.2"):
            serialize_loop_event(ev)


class TestFormatSseMessage:
    def test_basic_frame(self) -> None:
        frame = format_sse_message("loop_start", {"a": 1})
        assert frame.startswith(b"event: loop_start\n")
        assert b'data: {"a":1}\n\n' in frame

    def test_unicode_preserved(self) -> None:
        frame = format_sse_message("llm_response", {"content": "你好"})
        assert "你好".encode("utf-8") in frame

    def test_uuid_serializable(self) -> None:
        sid = uuid4()
        frame = format_sse_message("loop_start", {"session_id": sid})
        # UUID coerced to string by _jsonable
        body = frame.decode("utf-8")
        assert str(sid) in body
        # Verify it parses as JSON
        data_line = [line for line in body.split("\n") if line.startswith("data: ")][0]
        parsed = json.loads(data_line[len("data: "):])
        assert parsed["session_id"] == str(sid)
