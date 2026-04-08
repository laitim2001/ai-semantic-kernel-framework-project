"""Pipeline SSE Event Models and Emitter.

Provides real-time event streaming for the orchestrator pipeline.
Each handler step emits events via PipelineEventEmitter, which are
consumed by the SSE endpoint and pushed to the frontend.

Sprint 145 — Phase 42 SSE Streaming.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)

# Sprint 145-3: Mapping from Pipeline SSE events to AG-UI protocol events.
# This bridge allows AG-UI components to consume Pipeline events.
PIPELINE_TO_AGUI_MAP = {
    "PIPELINE_START": "RUN_STARTED",
    "ROUTING_COMPLETE": "STEP_FINISHED",
    "AGENT_THINKING": "TEXT_MESSAGE_START",
    "TOOL_CALL_START": "TOOL_CALL_START",
    "TOOL_CALL_END": "TOOL_CALL_END",
    "TEXT_DELTA": "TEXT_MESSAGE_CONTENT",
    "TASK_DISPATCHED": "STEP_STARTED",
    "SWARM_WORKER_START": "STEP_STARTED",
    "SWARM_WORKER_END": "STEP_FINISHED",
    "SWARM_PROGRESS": "STATE_SNAPSHOT",
    "APPROVAL_REQUIRED": "STATE_SNAPSHOT",
    "CHECKPOINT_RESTORED": "STATE_SNAPSHOT",
    # V2 parallel team events
    "TEAM_MESSAGE": "STATE_SNAPSHOT",
    "INBOX_RECEIVED": "STATE_SNAPSHOT",
    "TASK_COMPLETED": "STEP_FINISHED",
    "ALL_TASKS_DONE": "STATE_SNAPSHOT",
    "PIPELINE_COMPLETE": "RUN_FINISHED",
    "PIPELINE_ERROR": "RUN_ERROR",
}


class SSEEventType(str, Enum):
    """Event types emitted during pipeline execution."""

    PIPELINE_START = "PIPELINE_START"
    ROUTING_COMPLETE = "ROUTING_COMPLETE"
    AGENT_THINKING = "AGENT_THINKING"
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_END = "TOOL_CALL_END"
    TEXT_DELTA = "TEXT_DELTA"
    TASK_DISPATCHED = "TASK_DISPATCHED"
    SWARM_WORKER_START = "SWARM_WORKER_START"
    SWARM_WORKER_END = "SWARM_WORKER_END"
    SWARM_PROGRESS = "SWARM_PROGRESS"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CHECKPOINT_RESTORED = "CHECKPOINT_RESTORED"
    # V2: Parallel team events
    TEAM_MESSAGE = "TEAM_MESSAGE"
    INBOX_RECEIVED = "INBOX_RECEIVED"
    TASK_COMPLETED = "TASK_COMPLETED"
    ALL_TASKS_DONE = "ALL_TASKS_DONE"
    PIPELINE_COMPLETE = "PIPELINE_COMPLETE"
    PIPELINE_ERROR = "PIPELINE_ERROR"


@dataclass
class SSEEvent:
    """A single SSE event."""

    event_type: SSEEventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_sse_string(self) -> str:
        """Format as SSE wire protocol (Pipeline event names)."""
        payload = {**self.data, "timestamp": self.timestamp.isoformat()}
        return (
            f"event: {self.event_type.value}\n"
            f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        )

    def to_agui_sse_string(self) -> str:
        """Format as AG-UI protocol SSE event.

        Sprint 145-3: Maps Pipeline event type to AG-UI event type,
        preserving the original pipeline_type in the data payload.
        """
        agui_type = PIPELINE_TO_AGUI_MAP.get(
            self.event_type.value, "STATE_SNAPSHOT"
        )
        payload = {
            **self.data,
            "pipeline_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
        }
        return (
            f"event: {agui_type}\n"
            f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        )


class PipelineEventEmitter:
    """Async event emitter for pipeline SSE streaming.

    Each pipeline execution creates one emitter.  Handlers call
    ``emit()`` to push events; the SSE endpoint consumes via
    ``stream()``.

    Usage::

        emitter = PipelineEventEmitter()

        # In the SSE endpoint — consume events
        async for chunk in emitter.stream():
            yield chunk

        # In the mediator — produce events
        await emitter.emit(SSEEventType.ROUTING_COMPLETE, {...})
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[SSEEvent] = asyncio.Queue()
        self._closed = False

    async def emit(self, event_type: SSEEventType, data: Optional[Dict[str, Any]] = None) -> None:
        """Push an event into the stream."""
        if self._closed:
            return
        event = SSEEvent(event_type=event_type, data=data or {})
        await self._queue.put(event)

    async def emit_text_delta(self, delta: str) -> None:
        """Convenience: emit a TEXT_DELTA event."""
        await self.emit(SSEEventType.TEXT_DELTA, {"delta": delta})

    async def emit_complete(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit PIPELINE_COMPLETE and close the stream."""
        await self.emit(SSEEventType.PIPELINE_COMPLETE, {
            "content": content,
            **(metadata or {}),
        })
        self._closed = True

    async def emit_error(self, error: str) -> None:
        """Emit PIPELINE_ERROR and close the stream."""
        await self.emit(SSEEventType.PIPELINE_ERROR, {"error": error})
        self._closed = True

    async def stream(self, agui_format: bool = False) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings until PIPELINE_COMPLETE or ERROR.

        Args:
            agui_format: If True, output AG-UI protocol event names
                instead of Pipeline event names (Sprint 145-3).
        """
        while True:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=120)
                if agui_format:
                    yield event.to_agui_sse_string()
                else:
                    yield event.to_sse_string()
                if event.event_type in (SSEEventType.PIPELINE_COMPLETE, SSEEventType.PIPELINE_ERROR):
                    break
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
