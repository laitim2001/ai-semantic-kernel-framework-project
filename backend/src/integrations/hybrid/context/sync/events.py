# =============================================================================
# IPA Platform - Sync Event Publisher
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Publishes sync lifecycle events for monitoring and reactive updates.
#
# Event Types:
#   - SYNC_STARTED: Sync operation initiated
#   - SYNC_COMPLETED: Sync operation completed successfully
#   - SYNC_FAILED: Sync operation failed
#   - CONFLICT_DETECTED: Conflict detected during sync
#   - CONFLICT_RESOLVED: Conflict resolved
# =============================================================================

import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..models import Conflict, HybridContext, SyncResult, SyncStrategy

logger = logging.getLogger(__name__)


class SyncEventType(str, Enum):
    """Types of sync events."""

    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    SYNC_PROGRESS = "sync_progress"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    CONFLICT_MANUAL = "conflict_manual"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"
    VERSION_UPDATED = "version_updated"


@dataclass
class SyncEvent:
    """Represents a sync event."""

    event_type: SyncEventType
    session_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "sync_service"
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


# Type alias for event handlers
SyncEventHandler = Callable[[SyncEvent], Awaitable[None]]


class SyncEventPublisher:
    """
    同步事件發布器

    發布同步生命週期事件，支持訂閱和通知機制。

    Features:
    - 異步事件發布
    - 多訂閱者支持
    - 事件過濾
    - 事件歷史記錄

    Example:
        publisher = SyncEventPublisher()

        async def handler(event: SyncEvent):
            print(f"Received: {event.event_type}")

        publisher.subscribe(handler)
        await publisher.publish_sync_started(session_id, strategy)
    """

    def __init__(
        self,
        max_history: int = 100,
        enable_logging: bool = True,
    ):
        """
        Initialize SyncEventPublisher.

        Args:
            max_history: Maximum number of events to keep in history
            enable_logging: Whether to log events
        """
        self._handlers: List[SyncEventHandler] = []
        self._event_history: List[SyncEvent] = []
        self._max_history = max_history
        self._enable_logging = enable_logging
        self._filters: Dict[str, List[SyncEventType]] = {}

    def subscribe(
        self,
        handler: SyncEventHandler,
        event_types: Optional[List[SyncEventType]] = None,
    ) -> str:
        """
        Subscribe to sync events.

        Args:
            handler: Async function to call when events occur
            event_types: Optional list of event types to filter (None = all)

        Returns:
            Subscription ID for unsubscribing
        """
        self._handlers.append(handler)
        sub_id = f"sub-{len(self._handlers)}"

        if event_types:
            self._filters[sub_id] = event_types

        logger.debug(f"Subscribed handler {sub_id}, filtering: {event_types}")
        return sub_id

    def unsubscribe(self, handler: SyncEventHandler) -> bool:
        """
        Unsubscribe from sync events.

        Args:
            handler: Handler to remove

        Returns:
            True if handler was removed
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            return True
        return False

    async def publish(self, event: SyncEvent) -> None:
        """
        Publish a sync event to all subscribers.

        Args:
            event: The event to publish
        """
        # Log event if enabled
        if self._enable_logging:
            logger.info(
                f"Sync event: {event.event_type.value} for session {event.session_id}"
            )

        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        # Notify handlers
        tasks = []
        for i, handler in enumerate(self._handlers):
            # Check filter
            sub_id = f"sub-{i + 1}"
            if sub_id in self._filters:
                if event.event_type not in self._filters[sub_id]:
                    continue

            tasks.append(self._safe_call_handler(handler, event))

        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_call_handler(
        self,
        handler: SyncEventHandler,
        event: SyncEvent,
    ) -> None:
        """Safely call a handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in sync event handler: {e}", exc_info=True)

    # =========================================================================
    # Convenience Methods for Publishing Specific Events
    # =========================================================================

    async def publish_sync_started(
        self,
        session_id: str,
        strategy: SyncStrategy,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish sync started event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.SYNC_STARTED,
                session_id=session_id,
                data={
                    "strategy": strategy.value,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_sync_completed(
        self,
        session_id: str,
        result: SyncResult,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish sync completed event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.SYNC_COMPLETED,
                session_id=session_id,
                data={
                    "status": "success" if result.success else "failed",
                    "items_synced": result.changes_applied,
                    "duration_ms": result.duration_ms,
                    "version": result.target_version,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_sync_failed(
        self,
        session_id: str,
        error: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish sync failed event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.SYNC_FAILED,
                session_id=session_id,
                data={
                    "error": error,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_sync_progress(
        self,
        session_id: str,
        progress: float,
        message: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish sync progress event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.SYNC_PROGRESS,
                session_id=session_id,
                data={
                    "progress": progress,
                    "message": message,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_conflict_detected(
        self,
        session_id: str,
        conflict: Conflict,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish conflict detected event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.CONFLICT_DETECTED,
                session_id=session_id,
                data={
                    "conflict_id": conflict.conflict_id,
                    "conflicting_fields": [conflict.field_path] if conflict.field_path else [],
                    "suggested_strategy": conflict.resolution or "merge",
                    "field_path": conflict.field_path,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_conflict_resolved(
        self,
        session_id: str,
        conflict: Conflict,
        strategy_used: SyncStrategy,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish conflict resolved event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.CONFLICT_RESOLVED,
                session_id=session_id,
                data={
                    "conflict_id": conflict.conflict_id,
                    "strategy_used": strategy_used.value,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_conflict_manual(
        self,
        session_id: str,
        conflict: Conflict,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish conflict requiring manual resolution event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.CONFLICT_MANUAL,
                session_id=session_id,
                data={
                    "conflict_id": conflict.conflict_id,
                    "conflicting_fields": [conflict.field_path] if conflict.field_path else [],
                    "field_path": conflict.field_path,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_rollback_started(
        self,
        session_id: str,
        from_version: int,
        to_version: int,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish rollback started event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.ROLLBACK_STARTED,
                session_id=session_id,
                data={
                    "from_version": from_version,
                    "to_version": to_version,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_rollback_completed(
        self,
        session_id: str,
        version: int,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish rollback completed event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.ROLLBACK_COMPLETED,
                session_id=session_id,
                data={
                    "version": version,
                },
                correlation_id=correlation_id,
            )
        )

    async def publish_version_updated(
        self,
        session_id: str,
        old_version: int,
        new_version: int,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish version updated event."""
        await self.publish(
            SyncEvent(
                event_type=SyncEventType.VERSION_UPDATED,
                session_id=session_id,
                data={
                    "old_version": old_version,
                    "new_version": new_version,
                },
                correlation_id=correlation_id,
            )
        )

    # =========================================================================
    # History and Query Methods
    # =========================================================================

    def get_event_history(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[SyncEventType] = None,
        limit: int = 50,
    ) -> List[SyncEvent]:
        """
        Get event history with optional filtering.

        Args:
            session_id: Filter by session ID
            event_type: Filter by event type
            limit: Maximum number of events to return

        Returns:
            List of matching events
        """
        events = self._event_history.copy()

        if session_id:
            events = [e for e in events if e.session_id == session_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def get_last_event(self, session_id: str) -> Optional[SyncEvent]:
        """Get the last event for a session."""
        for event in reversed(self._event_history):
            if event.session_id == session_id:
                return event
        return None

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()

    @property
    def handler_count(self) -> int:
        """Get number of subscribed handlers."""
        return len(self._handlers)

    @property
    def event_count(self) -> int:
        """Get number of events in history."""
        return len(self._event_history)
