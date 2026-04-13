"""
EventQueueAdapter — Bridges SwarmWorkerExecutor events to PipelineEvent + asyncio.Queue.

Maps SWARM_WORKER_* events (from SwarmWorkerExecutor._emit) to AGENT_MEMBER_*
PipelineEventType events for the production SSE pipeline.

Phase 45: Agent Team Visualization — PoC integration.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EventQueueAdapter:
    """Adapts SwarmWorkerExecutor event emissions to PipelineEvent + asyncio.Queue.

    SwarmWorkerExecutor calls `self._emitter.emit(sse_type, data)` where:
    - sse_type: an SSEEventType enum value (not used in our mapping)
    - data: dict with "event_subtype" key indicating the actual event type

    This adapter intercepts those calls, maps them to AGENT_MEMBER_*
    PipelineEventType events, and puts them into the asyncio.Queue that
    feeds the SSE StreamingResponse.
    """

    def __init__(
        self,
        event_queue: asyncio.Queue,
        team_id: str,
    ) -> None:
        self._queue = event_queue
        self._team_id = team_id

    async def emit(self, _sse_type: Any, data: Dict[str, Any]) -> None:
        """Handle an event from SwarmWorkerExecutor._emit().

        Args:
            _sse_type: SSEEventType enum (ignored — we map via event_subtype).
            data: Event data with "event_subtype" key.
        """
        from ...pipeline.service import PipelineEvent, PipelineEventType

        subtype = data.get("event_subtype", "")
        worker_id = data.get("worker_id", "")

        try:
            if subtype == "SWARM_WORKER_START":
                # Agent started executing
                await self._queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_MEMBER_STARTED,
                        {
                            "team_id": self._team_id,
                            "agent_id": worker_id,
                            "agent_name": data.get("agent_name") or data.get("display_name") or worker_id,
                            "role": data.get("role", ""),
                            "started_at": data.get("started_at", ""),
                        },
                        step_name="dispatch",
                    )
                )
                # Backward compat
                await self._queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_THINKING,
                        {"agent_name": data.get("agent_name", worker_id), "role": data.get("role", "")},
                        step_name="dispatch",
                    )
                )

            elif subtype == "SWARM_WORKER_THINKING":
                # Agent thinking content (real LLM response text)
                await self._queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_MEMBER_THINKING,
                        {
                            "team_id": self._team_id,
                            "agent_id": worker_id,
                            "thinking_content": data.get("content", ""),
                            "timestamp": data.get("timestamp", ""),
                        },
                        step_name="dispatch",
                    )
                )

            elif subtype == "SWARM_WORKER_TOOL_CALL":
                # Real tool execution
                status = data.get("status", "running")
                event_data: Dict[str, Any] = {
                    "team_id": self._team_id,
                    "agent_id": worker_id,
                    "tool_call_id": data.get("tool_call_id", f"tc-{worker_id}"),
                    "tool_name": data.get("tool_name", ""),
                    "status": status,
                    "timestamp": data.get("timestamp", ""),
                }
                if status == "running":
                    event_data["input_args"] = data.get("arguments", {})
                else:
                    event_data["output_result"] = data.get("result", {})
                    event_data["duration_ms"] = data.get("duration_ms")

                await self._queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_MEMBER_TOOL_CALL,
                        event_data,
                        step_name="dispatch",
                    )
                )

            elif subtype == "SWARM_WORKER_PROGRESS":
                # Forward progress events to keep SSE alive during long dispatch
                await self._queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_MEMBER_THINKING,
                        {
                            "team_id": self._team_id,
                            "agent_id": worker_id,
                            "thinking_content": data.get("current_action", "processing..."),
                            "progress": data.get("progress", 0),
                            "timestamp": data.get("timestamp", ""),
                        },
                        step_name="dispatch",
                    )
                )

            elif subtype == "SWARM_WORKER_COMPLETED":
                # Agent completed
                await self._queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_MEMBER_COMPLETED,
                        {
                            "team_id": self._team_id,
                            "agent_id": worker_id,
                            "agent_name": data.get("agent_name", worker_id),
                            "status": data.get("status", "completed"),
                            "output": data.get("content_preview", ""),
                            "duration_ms": data.get("duration_ms", 0),
                            "completed_at": data.get("completed_at", ""),
                        },
                        step_name="dispatch",
                    )
                )
                # Backward compat
                await self._queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_COMPLETE,
                        {
                            "agent_name": data.get("agent_name", worker_id),
                            "output_preview": data.get("content_preview", ""),
                            "duration_ms": round(data.get("duration_ms", 0)),
                        },
                        step_name="dispatch",
                    )
                )

            elif subtype == "SWARM_WORKER_FAILED":
                await self._queue.put(
                    PipelineEvent(
                        PipelineEventType.AGENT_MEMBER_COMPLETED,
                        {
                            "team_id": self._team_id,
                            "agent_id": worker_id,
                            "agent_name": worker_id,
                            "status": "failed",
                            "output": data.get("error", "Unknown error"),
                            "duration_ms": data.get("duration_ms", 0),
                        },
                        step_name="dispatch",
                    )
                )

            else:
                logger.debug("EventQueueAdapter: unhandled subtype %s", subtype)

        except Exception as e:
            logger.warning("EventQueueAdapter: failed to emit %s: %s", subtype, str(e)[:100])
