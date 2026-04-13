"""
PipelineEmitterBridge — Bridges PoC's PipelineEventEmitter to Production's asyncio.Queue.

The PoC's agent_work_loop.py calls `emitter.emit_event(event_name_str, data_dict)`.
Production uses `event_queue.put(PipelineEvent(PipelineEventType, data, step_name))`.

This bridge:
1. Accepts the PoC's emit_event(str, dict) calls
2. Maps PoC event names to Production PipelineEventType enum values
3. Puts PipelineEvent into the asyncio.Queue

Also provides the `.emit(sse_type, data)` method expected by _patch_emitter().

Phase 45: Sprint C — PoC Persistent Loop integration.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PipelineEmitterBridge:
    """Bridges PoC emitter interface to Production PipelineEvent + asyncio.Queue.

    Supports two call patterns:
    1. emitter.emit_event(event_name: str, data: dict) — used by agent_work_loop
    2. emitter.emit(sse_type, data: dict) — used by _patch_emitter/_safe_emit
    """

    def __init__(self, event_queue: asyncio.Queue, team_id: str):
        self._queue = event_queue
        self._team_id = team_id

    async def emit_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Handle PoC-style emit_event(name, data) calls."""
        from ...pipeline.service import PipelineEvent, PipelineEventType

        # Map PoC event names to Production PipelineEventType
        event_data = {"team_id": self._team_id, **data}

        try:
            if event_name == "SWARM_WORKER_START":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_STARTED,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("agent", data.get("worker", "")),
                        "agent_name": data.get("agent", data.get("display_name", "")),
                        "role": data.get("role", ""),
                    },
                    step_name="dispatch",
                ))
                # Backward compat
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_THINKING,
                    {"agent_name": data.get("agent", ""), "role": data.get("role", "")},
                    step_name="dispatch",
                ))

            elif event_name == "SWARM_WORKER_END":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_COMPLETED,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("agent", ""),
                        "agent_name": data.get("agent", ""),
                        "status": data.get("status", "completed"),
                        "output": data.get("output", ""),
                        "duration_ms": data.get("duration_ms", 0),
                    },
                    step_name="dispatch",
                ))
                # Backward compat
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_COMPLETE,
                    {
                        "agent_name": data.get("agent", ""),
                        "output_preview": data.get("output", "")[:200],
                        "duration_ms": data.get("duration_ms", 0),
                    },
                    step_name="dispatch",
                ))

            elif event_name == "AGENT_THINKING":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("agent", ""),
                        "thinking_content": data.get("thinking", data.get("preview", "thinking...")),
                        "step": data.get("step", ""),
                        "status": data.get("status", ""),
                    },
                    step_name="dispatch",
                ))

            elif event_name == "TEAM_MESSAGE":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("from", data.get("agent", "")),
                        "thinking_content": (
                            f"[→ {data.get('to', 'all')}] {data.get('content', data.get('message', ''))}"
                        ),
                        "message_type": "team_message",
                        "from_agent": data.get("from", ""),
                        "to_agent": data.get("to"),
                        "directed": data.get("directed", bool(data.get("to"))),
                    },
                    step_name="dispatch",
                ))

            elif event_name == "INBOX_RECEIVED":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("agent", ""),
                        "thinking_content": f"[inbox] received from {data.get('from', '?')}",
                        "message_type": "inbox_received",
                    },
                    step_name="dispatch",
                ))

            elif event_name == "TASK_COMPLETED":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("agent", ""),
                        "thinking_content": f"Task {data.get('task_id', '?')} completed",
                        "message_type": "task_completed",
                        "task_id": data.get("task_id", ""),
                        "status": data.get("status", "completed"),
                    },
                    step_name="dispatch",
                ))

            elif event_name == "ALL_TASKS_DONE":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": self._team_id,
                        "agent_id": "system",
                        "thinking_content": "All tasks completed — entering communication window",
                        "message_type": "all_tasks_done",
                    },
                    step_name="dispatch",
                ))

            elif event_name == "APPROVAL_REQUIRED":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("agent", ""),
                        "thinking_content": f"Approval required: {data.get('message', '')}",
                        "message_type": "approval_required",
                        "approval_id": data.get("approval_id", ""),
                        "risk_level": data.get("risk_level", ""),
                    },
                    step_name="dispatch",
                ))

            elif event_name in ("SWARM_PROGRESS", "TASK_DISPATCHED", "ROUTING_COMPLETE"):
                # Forward progress events to keep SSE alive
                subtype = data.get("event_type", event_name)
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("agent", "system"),
                        "thinking_content": data.get("preview", subtype),
                        "progress": data.get("progress", 0),
                        "message_type": subtype,
                    },
                    step_name="dispatch",
                ))

            elif event_name == "TEXT_DELTA":
                await self._queue.put(PipelineEvent(
                    PipelineEventType.TEXT_DELTA,
                    {"content": data.get("delta", ""), "source": data.get("source", "agent")},
                    step_name="dispatch",
                ))

            else:
                # Unknown event — log and forward as thinking
                logger.debug("PipelineEmitterBridge: unhandled event %s", event_name)
                await self._queue.put(PipelineEvent(
                    PipelineEventType.AGENT_MEMBER_THINKING,
                    {
                        "team_id": self._team_id,
                        "agent_id": data.get("agent", "system"),
                        "thinking_content": f"[{event_name}] {str(data)[:100]}",
                    },
                    step_name="dispatch",
                ))

        except Exception as e:
            logger.warning("PipelineEmitterBridge: failed to emit %s: %s", event_name, str(e)[:100])

    async def emit(self, sse_type: Any, data: Dict[str, Any]) -> None:
        """Handle _safe_emit / _patch_emitter style calls.

        _safe_emit calls: emitter.emit(SSEEventType.XXX, data)
        We extract the event name from the enum and delegate to emit_event().
        """
        event_name = sse_type.value if hasattr(sse_type, "value") else str(sse_type)
        await self.emit_event(event_name, data)
