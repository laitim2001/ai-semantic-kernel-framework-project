"""
File: backend/src/api/v1/chat/sse.py
Purpose: LoopEvent → SSE wire-format serializer (per 02-architecture-design §SSE).
Category: api/v1/chat
Scope: Phase 50 / Sprint 50.2 (Day 1.3)

Description:
    Pure transformation: turns a `LoopEvent` instance into the
    `{event, data}` shape specified in 02-architecture-design.md §SSE.
    `format_sse_message()` then encodes that shape into the SSE wire
    format (`event: ...\\ndata: <json>\\n\\n`).

    Day 1 implements the LoopEvent subclasses already emitted by 50.1
    AgentLoopImpl: LoopStarted / Thinking / ToolCallRequested / LoopCompleted.
    Forward-compatible: ToolCallExecuted (Cat 2 owner; Day 2 Loop emit) +
    TurnStarted / LLMRequested / LLMResponded (Day 2 new types) raise
    NotImplementedError until Day 2 fills them in — explicit failure beats
    silent drop.

    All other LoopEvent subclasses (HITL / Guardrails / Verification / etc.)
    are deferred to their owner sprints (53-54) and currently raise
    NotImplementedError with a clear "not in 50.2 scope" message.

Key Components:
    - serialize_loop_event(event) -> dict[str, Any]
    - format_sse_message(event_type, data) -> bytes

Created: 2026-04-30 (Sprint 50.2 Day 1.3)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 50.2 Day 1.3) — 4 50.1-emit events
        serialize; rest raise NotImplementedError with sprint pointer.

Related:
    - 02-architecture-design.md §SSE 事件規範
    - agent_harness/_contracts/events.py (single-source LoopEvent tree)
    - .router (consumes serialize + format)
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from agent_harness._contracts import (
    LoopCompleted,
    LoopEvent,
    LoopStarted,
    Thinking,
    ToolCallExecuted,
    ToolCallRequested,
)


def serialize_loop_event(event: LoopEvent) -> dict[str, Any]:
    """Map a LoopEvent instance to the SSE event_dict shape per 02.md §SSE.

    Returns a dict with keys ``type`` (SSE event type string) and ``data``
    (dict serializable as JSON). Raises NotImplementedError for events not
    yet wired in 50.2 scope.
    """
    if isinstance(event, LoopStarted):
        return {
            "type": "loop_start",
            "data": {
                "session_id": str(event.session_id) if event.session_id else None,
                "request_id": str(event.event_id),
            },
        }

    if isinstance(event, Thinking):
        # 50.1 Loop emits Thinking AFTER parser.parse(); represents LLM response
        # text. Per 02.md §SSE this maps to llm_response (with no tool_calls
        # split out — Day 2 LLMResponded carries that explicitly).
        return {
            "type": "llm_response",
            "data": {
                "content": event.text,
            },
        }

    if isinstance(event, ToolCallRequested):
        return {
            "type": "tool_call_request",
            "data": {
                "tool_call_id": event.tool_call_id,
                "tool_name": event.tool_name,
                "args": event.arguments,
            },
        }

    if isinstance(event, ToolCallExecuted):
        # Cat 2 owns; 50.1 Loop does NOT yield this today. Day 2 patches Loop
        # to yield after tool_executor.execute() success.
        return {
            "type": "tool_call_result",
            "data": {
                "tool_call_id": event.tool_call_id,
                "tool_name": event.tool_name,
                "duration_ms": event.duration_ms,
                "is_error": False,
            },
        }

    if isinstance(event, LoopCompleted):
        return {
            "type": "loop_end",
            "data": {
                "stop_reason": event.stop_reason,
                "total_turns": event.total_turns,
            },
        }

    raise NotImplementedError(
        f"SSE serialization for {type(event).__name__} is not in Sprint 50.2 scope."
        " See sprint-50-2-plan.md §3.2 deferred / 02-architecture-design.md §SSE for owner sprint."
    )


def format_sse_message(event_type: str, data: dict[str, Any]) -> bytes:
    """Encode an SSE message frame: ``event: <type>\\ndata: <json>\\n\\n``."""
    payload = json.dumps(_jsonable(data), ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")


def _jsonable(value: Any) -> Any:
    """Recursively coerce dataclasses + UUIDs to JSON-friendly forms."""
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    # uuid.UUID, datetime, etc. — fall back to str repr
    if hasattr(value, "isoformat"):  # datetime
        return value.isoformat()
    if hasattr(value, "hex") and not isinstance(value, (bytes, bytearray, str, int)):
        return str(value)  # UUID
    return value
