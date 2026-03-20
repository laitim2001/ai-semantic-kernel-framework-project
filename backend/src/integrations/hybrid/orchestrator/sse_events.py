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
    SWARM_PROGRESS = "SWARM_PROGRESS"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    PIPELINE_COMPLETE = "PIPELINE_COMPLETE"
    PIPELINE_ERROR = "PIPELINE_ERROR"


@dataclass
class SSEEvent:
    """A single SSE event."""

    event_type: SSEEventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_sse_string(self) -> str:
        """Format as SSE wire protocol."""
        payload = {**self.data, "timestamp": self.timestamp.isoformat()}
        return (
            f"event: {self.event_type.value}\n"
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

    async def stream(self) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings until PIPELINE_COMPLETE or ERROR."""
        while True:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=120)
                yield event.to_sse_string()
                if event.event_type in (SSEEventType.PIPELINE_COMPLETE, SSEEventType.PIPELINE_ERROR):
                    break
            except asyncio.TimeoutError:
                # Send keepalive comment to prevent connection timeout
                yield ": keepalive\n\n"
