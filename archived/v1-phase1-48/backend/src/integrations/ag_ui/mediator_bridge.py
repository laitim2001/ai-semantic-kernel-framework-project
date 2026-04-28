"""MediatorEventBridge — adapts OrchestratorMediator events to AG-UI SSE format.

Replaces the old HybridEventBridge (which connects to HybridOrchestratorV2)
with a new bridge that connects to the OrchestratorMediator pipeline.

Sprint 135 — Phase 39 E2E Assembly D.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)


# AG-UI event type constants
AGUI_RUN_STARTED = "RUN_STARTED"
AGUI_RUN_FINISHED = "RUN_FINISHED"
AGUI_RUN_ERROR = "RUN_ERROR"
AGUI_TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
AGUI_TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
AGUI_TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
AGUI_TOOL_CALL_START = "TOOL_CALL_START"
AGUI_TOOL_CALL_END = "TOOL_CALL_END"
AGUI_STEP_STARTED = "STEP_STARTED"
AGUI_STEP_FINISHED = "STEP_FINISHED"
AGUI_STATE_SNAPSHOT = "STATE_SNAPSHOT"

# Mediator event type mappings
EVENT_MAP = {
    "pipeline.started": AGUI_RUN_STARTED,
    "pipeline.completed": AGUI_RUN_FINISHED,
    "pipeline.error": AGUI_RUN_ERROR,
    "routing.started": AGUI_STEP_STARTED,
    "routing.completed": AGUI_STEP_FINISHED,
    "execution.started": AGUI_STEP_STARTED,
    "execution.completed": AGUI_STEP_FINISHED,
    "execution.failed": AGUI_RUN_ERROR,
    "approval.pending": AGUI_STATE_SNAPSHOT,
    "approval.completed": AGUI_STEP_FINISHED,
    "approval.rejected": AGUI_RUN_ERROR,
    # New intermediate events (Sprint 135)
    "thinking.token": AGUI_TEXT_MESSAGE_CONTENT,
    "tool_call.progress": AGUI_TOOL_CALL_START,
    "step.progress": AGUI_STATE_SNAPSHOT,
}


class MediatorEventBridge:
    """Bridges OrchestratorMediator to AG-UI SSE protocol.

    Converts internal mediator events into AG-UI standard SSE events
    for real-time frontend streaming.

    Args:
        sse_buffer: Optional SSEEventBuffer for reconnection support.
    """

    def __init__(self, sse_buffer: Any = None) -> None:
        self._buffer = sse_buffer
        self._event_counter = 0

    async def stream_events(
        self,
        mediator: Any,
        request: Any,
        thread_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute the mediator pipeline and stream AG-UI events.

        Args:
            mediator: OrchestratorMediator instance.
            request: OrchestratorRequest to execute.
            thread_id: AG-UI thread ID for state tracking.

        Yields:
            SSE-formatted event strings.
        """
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()

        # --- RUN_STARTED ---
        yield self._format_sse(AGUI_RUN_STARTED, {
            "run_id": run_id,
            "thread_id": thread_id,
            "timestamp": time.time(),
        })

        # --- Execute pipeline ---
        try:
            from src.integrations.hybrid.orchestrator.contracts import OrchestratorRequest

            if not isinstance(request, OrchestratorRequest):
                request = OrchestratorRequest(
                    content=str(request),
                    session_id=thread_id,
                )

            # STEP: Routing
            yield self._format_sse(AGUI_STEP_STARTED, {
                "step_name": "intent_routing",
                "run_id": run_id,
            })

            response = await mediator.execute(request)

            yield self._format_sse(AGUI_STEP_FINISHED, {
                "step_name": "intent_routing",
                "run_id": run_id,
            })

            # --- TEXT_MESSAGE streaming ---
            content = response.content or "" if response else ""
            message_id = f"msg-{uuid.uuid4().hex[:8]}"

            yield self._format_sse(AGUI_TEXT_MESSAGE_START, {
                "message_id": message_id,
                "role": "assistant",
                "run_id": run_id,
            })

            # Stream content in chunks for real-time feel
            chunk_size = 50
            for i in range(0, len(content), chunk_size):
                chunk = content[i: i + chunk_size]
                yield self._format_sse(AGUI_TEXT_MESSAGE_CONTENT, {
                    "message_id": message_id,
                    "delta": chunk,
                })
                await asyncio.sleep(0.01)  # Small delay for streaming effect

            yield self._format_sse(AGUI_TEXT_MESSAGE_END, {
                "message_id": message_id,
            })

            # --- RUN_FINISHED ---
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            yield self._format_sse(AGUI_RUN_FINISHED, {
                "run_id": run_id,
                "thread_id": thread_id,
                "processing_time_ms": round(elapsed_ms, 2),
                "framework_used": getattr(response, "framework_used", "unknown"),
            })

        except Exception as e:
            logger.error("MediatorEventBridge: pipeline error: %s", e, exc_info=True)
            yield self._format_sse(AGUI_RUN_ERROR, {
                "run_id": run_id,
                "error": str(e),
                "error_type": type(e).__name__,
            })

    def convert_event(self, mediator_event_type: str, data: Dict[str, Any]) -> Optional[str]:
        """Convert a single mediator event to AG-UI SSE format.

        Args:
            mediator_event_type: Event type string from EventType enum.
            data: Event payload.

        Returns:
            SSE-formatted string, or None if unmapped.
        """
        agui_type = EVENT_MAP.get(mediator_event_type)
        if agui_type is None:
            return None
        return self._format_sse(agui_type, data)

    def _format_sse(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format an event as SSE string with optional buffering."""
        self._event_counter += 1
        event_id = self._event_counter

        sse_data = json.dumps({"type": event_type, **data}, default=str)
        sse_line = f"id: {event_id}\nevent: {event_type}\ndata: {sse_data}\n\n"

        # Buffer for reconnection support
        if self._buffer:
            try:
                asyncio.get_event_loop().create_task(
                    self._buffer.buffer_event(
                        data.get("thread_id", "default"),
                        {"id": event_id, "type": event_type, "data": data},
                    )
                )
            except Exception:
                pass  # Non-critical

        return sse_line
