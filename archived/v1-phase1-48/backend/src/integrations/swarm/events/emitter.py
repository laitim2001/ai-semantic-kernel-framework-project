# =============================================================================
# IPA Platform - Swarm Event Emitter
# =============================================================================
# Sprint 101: Swarm Event System + SSE Integration
# S101-2: SwarmEventEmitter Implementation
#
# Event emitter that converts Swarm state changes into AG-UI CustomEvents.
# Supports event throttling and batch sending for performance optimization.
#
# Features:
#   - Converts Swarm/Worker state changes to CustomEvent
#   - Event throttling (configurable interval)
#   - Batch event sending
#   - Priority event handling (immediate send)
#
# Dependencies:
#   - asyncio
#   - AG-UI CustomEvent
#   - Swarm models
# =============================================================================

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, TYPE_CHECKING

from src.integrations.ag_ui.events import CustomEvent

from .types import (
    SwarmEventNames,
    SwarmCreatedPayload,
    SwarmStatusUpdatePayload,
    SwarmCompletedPayload,
    WorkerStartedPayload,
    WorkerProgressPayload,
    WorkerThinkingPayload,
    WorkerToolCallPayload,
    WorkerMessagePayload,
    WorkerCompletedPayload,
)

if TYPE_CHECKING:
    from src.integrations.swarm.models import (
        AgentSwarmStatus,
        WorkerExecution,
        ToolCallInfo,
    )

logger = logging.getLogger(__name__)

# Type alias for event callback
EventCallback = Callable[[CustomEvent], Awaitable[None]]


class SwarmEventEmitter:
    """
    Swarm 事件發送器.

    將 Swarm 狀態變化轉換為 AG-UI CustomEvent 並發送。

    Features:
        1. 將 Swarm 狀態變化轉換為 AG-UI CustomEvent
        2. 事件節流（限制頻率）
        3. 批量發送優化
        4. 優先級事件處理

    Example:
        >>> async def callback(event: CustomEvent):
        ...     print(f"Event: {event.event_name}")
        >>> emitter = SwarmEventEmitter(event_callback=callback)
        >>> await emitter.start()
        >>> await emitter.emit_swarm_created(swarm)
        >>> await emitter.stop()
    """

    def __init__(
        self,
        event_callback: EventCallback,
        throttle_interval_ms: int = 200,
        batch_size: int = 5,
    ):
        """
        Initialize SwarmEventEmitter.

        Args:
            event_callback: Async function to call with each CustomEvent
            throttle_interval_ms: Minimum interval between throttled events (ms)
            batch_size: Number of events to batch before sending
        """
        self._callback = event_callback
        self._throttle_interval = throttle_interval_ms / 1000  # Convert to seconds
        self._batch_size = batch_size

        # Event throttling state
        self._last_emit_time: Dict[str, float] = {}
        self._pending_events: Dict[str, CustomEvent] = {}

        # Batch sending state
        self._event_queue: asyncio.Queue[CustomEvent] = asyncio.Queue()
        self._batch_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            f"SwarmEventEmitter initialized: "
            f"throttle_interval={throttle_interval_ms}ms, "
            f"batch_size={batch_size}"
        )

    @property
    def is_running(self) -> bool:
        """Check if emitter is running."""
        return self._running

    async def start(self) -> None:
        """Start the batch sender task."""
        if self._running:
            logger.warning("SwarmEventEmitter already running")
            return

        self._running = True
        self._batch_task = asyncio.create_task(self._batch_sender())
        logger.info("SwarmEventEmitter started")

    async def stop(self) -> None:
        """Stop the batch sender task and flush pending events."""
        if not self._running:
            return

        self._running = False

        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
            self._batch_task = None

        # Flush remaining events
        await self._flush_pending_events()
        logger.info("SwarmEventEmitter stopped")

    # =========================================================================
    # Swarm Events
    # =========================================================================

    async def emit_swarm_created(
        self,
        swarm: "AgentSwarmStatus",
        session_id: str = "",
    ) -> None:
        """
        Emit swarm_created event.

        Args:
            swarm: AgentSwarmStatus instance
            session_id: Session ID (optional)
        """
        workers = [
            {
                "worker_id": w.worker_id,
                "worker_name": w.worker_name,
                "worker_type": w.worker_type.value,
                "role": w.role,
            }
            for w in swarm.workers
        ]

        payload = SwarmCreatedPayload(
            swarm_id=swarm.swarm_id,
            session_id=session_id or getattr(swarm, "session_id", ""),
            mode=swarm.mode.value,
            workers=workers,
            created_at=swarm.started_at.isoformat() if swarm.started_at else datetime.utcnow().isoformat(),
        )

        event = CustomEvent(
            event_name=SwarmEventNames.SWARM_CREATED,
            payload=payload.to_dict(),
        )

        await self._emit(event, priority=True)
        logger.debug(f"Emitted swarm_created: swarm_id={swarm.swarm_id}")

    async def emit_swarm_status_update(
        self,
        swarm: "AgentSwarmStatus",
        session_id: str = "",
    ) -> None:
        """
        Emit swarm_status_update event (full status snapshot).

        This event is throttled to avoid overwhelming the client.

        Args:
            swarm: AgentSwarmStatus instance
            session_id: Session ID (optional)
        """
        workers = [self._worker_to_summary(w) for w in swarm.workers]

        payload = SwarmStatusUpdatePayload(
            swarm_id=swarm.swarm_id,
            session_id=session_id or getattr(swarm, "session_id", ""),
            mode=swarm.mode.value,
            status=swarm.status.value,
            total_workers=len(swarm.workers),
            overall_progress=swarm.overall_progress,
            workers=workers,
            metadata=swarm.metadata or {},
        )

        event = CustomEvent(
            event_name=SwarmEventNames.SWARM_STATUS_UPDATE,
            payload=payload.to_dict(),
        )

        await self._emit_throttled(event, f"swarm_status_{swarm.swarm_id}")

    async def emit_swarm_completed(
        self,
        swarm: "AgentSwarmStatus",
    ) -> None:
        """
        Emit swarm_completed event.

        Args:
            swarm: AgentSwarmStatus instance
        """
        duration_ms = 0
        if swarm.started_at and swarm.completed_at:
            duration_ms = int(
                (swarm.completed_at - swarm.started_at).total_seconds() * 1000
            )

        payload = SwarmCompletedPayload(
            swarm_id=swarm.swarm_id,
            status=swarm.status.value,
            summary=swarm.metadata.get("summary") if swarm.metadata else None,
            total_duration_ms=duration_ms,
            completed_at=swarm.completed_at.isoformat() if swarm.completed_at else datetime.utcnow().isoformat(),
        )

        event = CustomEvent(
            event_name=SwarmEventNames.SWARM_COMPLETED,
            payload=payload.to_dict(),
        )

        await self._emit(event, priority=True)
        logger.debug(f"Emitted swarm_completed: swarm_id={swarm.swarm_id}")

    # =========================================================================
    # Worker Events
    # =========================================================================

    async def emit_worker_started(
        self,
        swarm_id: str,
        worker: "WorkerExecution",
    ) -> None:
        """
        Emit worker_started event.

        Args:
            swarm_id: Parent swarm ID
            worker: WorkerExecution instance
        """
        payload = WorkerStartedPayload(
            swarm_id=swarm_id,
            worker_id=worker.worker_id,
            worker_name=worker.worker_name,
            worker_type=worker.worker_type.value,
            role=worker.role,
            task_description=worker.current_task or "",
            started_at=worker.started_at.isoformat() if worker.started_at else datetime.utcnow().isoformat(),
        )

        event = CustomEvent(
            event_name=SwarmEventNames.WORKER_STARTED,
            payload=payload.to_dict(),
        )

        await self._emit(event, priority=True)
        logger.debug(f"Emitted worker_started: worker_id={worker.worker_id}")

    async def emit_worker_progress(
        self,
        swarm_id: str,
        worker: "WorkerExecution",
    ) -> None:
        """
        Emit worker_progress event.

        This event is throttled to avoid overwhelming the client.

        Args:
            swarm_id: Parent swarm ID
            worker: WorkerExecution instance
        """
        payload = WorkerProgressPayload(
            swarm_id=swarm_id,
            worker_id=worker.worker_id,
            progress=worker.progress,
            current_action=worker.current_task,
            status=worker.status.value,
            updated_at=datetime.utcnow().isoformat(),
        )

        event = CustomEvent(
            event_name=SwarmEventNames.WORKER_PROGRESS,
            payload=payload.to_dict(),
        )

        await self._emit_throttled(
            event, f"worker_progress_{swarm_id}_{worker.worker_id}"
        )

    async def emit_worker_thinking(
        self,
        swarm_id: str,
        worker: "WorkerExecution",
        thinking_content: str,
        token_count: Optional[int] = None,
    ) -> None:
        """
        Emit worker_thinking event.

        This event is throttled to avoid overwhelming the client.

        Args:
            swarm_id: Parent swarm ID
            worker: WorkerExecution instance
            thinking_content: Thinking content text
            token_count: Token count (optional)
        """
        payload = WorkerThinkingPayload(
            swarm_id=swarm_id,
            worker_id=worker.worker_id,
            thinking_content=thinking_content,
            token_count=token_count,
            timestamp=datetime.utcnow().isoformat(),
        )

        event = CustomEvent(
            event_name=SwarmEventNames.WORKER_THINKING,
            payload=payload.to_dict(),
        )

        await self._emit_throttled(
            event, f"worker_thinking_{swarm_id}_{worker.worker_id}"
        )

    async def emit_worker_tool_call(
        self,
        swarm_id: str,
        worker: "WorkerExecution",
        tool_call: "ToolCallInfo",
    ) -> None:
        """
        Emit worker_tool_call event.

        Args:
            swarm_id: Parent swarm ID
            worker: WorkerExecution instance
            tool_call: ToolCallInfo instance
        """
        duration_ms = None
        if tool_call.started_at and tool_call.completed_at:
            duration_ms = int(
                (tool_call.completed_at - tool_call.started_at).total_seconds() * 1000
            )

        payload = WorkerToolCallPayload(
            swarm_id=swarm_id,
            worker_id=worker.worker_id,
            tool_call_id=tool_call.tool_id,
            tool_name=tool_call.tool_name,
            status=tool_call.status,
            input_args=tool_call.input_params or {},
            output_result=tool_call.result,
            error=tool_call.error,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat(),
        )

        event = CustomEvent(
            event_name=SwarmEventNames.WORKER_TOOL_CALL,
            payload=payload.to_dict(),
        )

        await self._emit(event, priority=True)
        logger.debug(
            f"Emitted worker_tool_call: worker_id={worker.worker_id}, "
            f"tool={tool_call.tool_name}"
        )

    async def emit_worker_message(
        self,
        swarm_id: str,
        worker: "WorkerExecution",
        role: str,
        content: str,
        tool_call_id: Optional[str] = None,
    ) -> None:
        """
        Emit worker_message event.

        Args:
            swarm_id: Parent swarm ID
            worker: WorkerExecution instance
            role: Message role (system, user, assistant, tool)
            content: Message content
            tool_call_id: Related tool call ID (optional)
        """
        payload = WorkerMessagePayload(
            swarm_id=swarm_id,
            worker_id=worker.worker_id,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            timestamp=datetime.utcnow().isoformat(),
        )

        event = CustomEvent(
            event_name=SwarmEventNames.WORKER_MESSAGE,
            payload=payload.to_dict(),
        )

        await self._emit(event, priority=False)

    async def emit_worker_completed(
        self,
        swarm_id: str,
        worker: "WorkerExecution",
    ) -> None:
        """
        Emit worker_completed event.

        Args:
            swarm_id: Parent swarm ID
            worker: WorkerExecution instance
        """
        duration_ms = 0
        if worker.started_at and worker.completed_at:
            duration_ms = int(
                (worker.completed_at - worker.started_at).total_seconds() * 1000
            )

        payload = WorkerCompletedPayload(
            swarm_id=swarm_id,
            worker_id=worker.worker_id,
            status=worker.status.value,
            result=None,  # Result can be added if needed
            error=worker.error,
            duration_ms=duration_ms,
            completed_at=worker.completed_at.isoformat() if worker.completed_at else datetime.utcnow().isoformat(),
        )

        event = CustomEvent(
            event_name=SwarmEventNames.WORKER_COMPLETED,
            payload=payload.to_dict(),
        )

        await self._emit(event, priority=True)
        logger.debug(f"Emitted worker_completed: worker_id={worker.worker_id}")

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _emit(self, event: CustomEvent, priority: bool = False) -> None:
        """
        Emit an event.

        Priority events are sent immediately.
        Non-priority events are queued for batch sending.

        Args:
            event: CustomEvent to emit
            priority: If True, send immediately
        """
        if priority:
            # Priority events are sent immediately
            try:
                await self._callback(event)
            except Exception as e:
                logger.error(f"Error sending priority event: {e}", exc_info=True)
        else:
            # Non-priority events go to the queue
            await self._event_queue.put(event)

    async def _emit_throttled(self, event: CustomEvent, key: str) -> None:
        """
        Emit an event with throttling.

        If the event is sent too frequently, it will be stored
        and sent later.

        Args:
            event: CustomEvent to emit
            key: Unique key for throttling (e.g., "worker_progress_swarm1_worker1")
        """
        now = time.time()
        last_time = self._last_emit_time.get(key, 0)

        if now - last_time >= self._throttle_interval:
            # Enough time has passed, send immediately
            await self._emit(event, priority=False)
            self._last_emit_time[key] = now
            # Clear any pending event for this key
            self._pending_events.pop(key, None)
        else:
            # Too soon, store for later
            self._pending_events[key] = event

    async def _batch_sender(self) -> None:
        """
        Batch sender coroutine.

        Collects events from the queue and sends them in batches.
        Also sends pending throttled events periodically.
        """
        while self._running:
            try:
                events: List[CustomEvent] = []

                # Collect events from queue
                while len(events) < self._batch_size:
                    try:
                        event = await asyncio.wait_for(
                            self._event_queue.get(), timeout=0.1
                        )
                        events.append(event)
                    except asyncio.TimeoutError:
                        break

                # Send collected events
                for event in events:
                    try:
                        await self._callback(event)
                    except Exception as e:
                        logger.error(f"Error sending batch event: {e}", exc_info=True)

                # Send pending throttled events
                await self._flush_pending_events()

            except asyncio.CancelledError:
                # Send remaining events before exit
                await self._flush_remaining()
                raise
            except Exception as e:
                logger.error(f"Error in batch sender: {e}", exc_info=True)

    async def _flush_pending_events(self) -> None:
        """Flush all pending throttled events."""
        now = time.time()
        keys_to_remove = []

        for key, event in self._pending_events.items():
            last_time = self._last_emit_time.get(key, 0)
            if now - last_time >= self._throttle_interval:
                try:
                    await self._callback(event)
                    self._last_emit_time[key] = now
                    keys_to_remove.append(key)
                except Exception as e:
                    logger.error(f"Error flushing pending event: {e}", exc_info=True)

        for key in keys_to_remove:
            del self._pending_events[key]

    async def _flush_remaining(self) -> None:
        """Flush all remaining events in the queue."""
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                await self._callback(event)
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Error flushing remaining event: {e}", exc_info=True)

        # Also flush pending events
        for event in self._pending_events.values():
            try:
                await self._callback(event)
            except Exception as e:
                logger.error(f"Error flushing pending event: {e}", exc_info=True)
        self._pending_events.clear()

    def _worker_to_summary(self, worker: "WorkerExecution") -> Dict[str, Any]:
        """
        Convert WorkerExecution to summary dictionary.

        Args:
            worker: WorkerExecution instance

        Returns:
            Summary dictionary for the worker
        """
        return {
            "worker_id": worker.worker_id,
            "worker_name": worker.worker_name,
            "worker_type": worker.worker_type.value,
            "role": worker.role,
            "status": worker.status.value,
            "progress": worker.progress,
            "current_action": worker.current_task,
            "tool_calls_count": len(worker.tool_calls) if worker.tool_calls else 0,
        }


def create_swarm_emitter(
    event_callback: EventCallback,
    *,
    throttle_interval_ms: int = 200,
    batch_size: int = 5,
) -> SwarmEventEmitter:
    """
    Factory function to create SwarmEventEmitter.

    Args:
        event_callback: Async function to call with each CustomEvent
        throttle_interval_ms: Minimum interval between throttled events (ms)
        batch_size: Number of events to batch before sending

    Returns:
        Configured SwarmEventEmitter instance
    """
    return SwarmEventEmitter(
        event_callback=event_callback,
        throttle_interval_ms=throttle_interval_ms,
        batch_size=batch_size,
    )
