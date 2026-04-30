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

    Day 2 wiring (after Sprint 50.2 Day 2.4 Loop event additions):
        loop_start          ← LoopStarted        (Cat 1)
        turn_start          ← TurnStarted        (Cat 1, NEW Day 2)
        llm_request         ← LLMRequested       (Cat 1, NEW Day 2)
        llm_response        ← LLMResponded       (Cat 1, NEW Day 2; canonical)
        tool_call_request   ← ToolCallRequested  (Cat 6)
        tool_call_result    ← ToolCallExecuted   (Cat 2; success path)
        tool_call_result    ← ToolCallFailed     (Cat 2; error path)
        loop_end            ← LoopCompleted      (Cat 1)

    `Thinking` (Cat 1) → returns None → router skips: LLMResponded carries
    the same content via the canonical llm_response schema so emitting both
    would duplicate the frame. Thinking event itself stays in 50.1
    test_loop assertions; only the SSE projection drops it.

    All other LoopEvent subclasses (HITL / Guardrails / Verification / etc.)
    are deferred to their owner sprints (53-54) and currently raise
    NotImplementedError with a clear "not in 50.2 scope" message.

Key Components:
    - serialize_loop_event(event) -> dict[str, Any] | None
    - format_sse_message(event_type, data) -> bytes

Created: 2026-04-30 (Sprint 50.2 Day 1.3)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Wire 3 new Day 2 events + skip-Thinking + ToolCallFailed
        (Sprint 50.2 Day 2.5) — TurnStarted / LLMRequested / LLMResponded;
        Thinking returns None (LLMResponded canonical); ToolCallExecuted
        carries result_content; ToolCallFailed → tool_call_result is_error=True.
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
    LLMRequested,
    LLMResponded,
    LoopCompleted,
    LoopEvent,
    LoopStarted,
    Thinking,
    ToolCallExecuted,
    ToolCallFailed,
    ToolCallRequested,
    TurnStarted,
)


def serialize_loop_event(event: LoopEvent) -> dict[str, Any] | None:
    """Map a LoopEvent instance to the SSE event_dict shape per 02.md §SSE.

    Returns a dict with keys ``type`` (SSE event type string) and ``data``
    (dict serializable as JSON), or None to signal "skip this event"
    (used for Thinking, replaced by LLMResponded in Day 2). Raises
    NotImplementedError for events not yet wired in 50.2 scope.
    """
    if isinstance(event, LoopStarted):
        return {
            "type": "loop_start",
            "data": {
                "session_id": str(event.session_id) if event.session_id else None,
                "request_id": str(event.event_id),
            },
        }

    if isinstance(event, TurnStarted):
        return {
            "type": "turn_start",
            "data": {"turn_num": event.turn_num},
        }

    if isinstance(event, LLMRequested):
        return {
            "type": "llm_request",
            "data": {"model": event.model, "tokens_in": event.tokens_in},
        }

    if isinstance(event, LLMResponded):
        # Day 2: canonical llm_response carrier per 02.md §SSE.
        return {
            "type": "llm_response",
            "data": {
                "content": event.content,
                "tool_calls": [
                    {
                        "id": getattr(tc, "id", ""),
                        "name": getattr(tc, "name", ""),
                        "arguments": getattr(tc, "arguments", {}),
                    }
                    for tc in event.tool_calls
                ],
                "thinking": event.thinking,
            },
        }

    if isinstance(event, Thinking):
        # Day 2: skip — LLMResponded carries the same content via canonical
        # llm_response. Returning None signals the router to drop the frame.
        return None

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
        return {
            "type": "tool_call_result",
            "data": {
                "tool_call_id": event.tool_call_id,
                "tool_name": event.tool_name,
                "duration_ms": event.duration_ms,
                "result": event.result_content,
                "is_error": False,
            },
        }

    if isinstance(event, ToolCallFailed):
        return {
            "type": "tool_call_result",
            "data": {
                "tool_call_id": event.tool_call_id,
                "tool_name": event.tool_name,
                "duration_ms": 0.0,
                "result": event.error,
                "is_error": True,
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
