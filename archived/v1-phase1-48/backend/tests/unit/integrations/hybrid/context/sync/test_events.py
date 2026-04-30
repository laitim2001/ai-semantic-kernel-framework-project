# =============================================================================
# IPA Platform - Sync Event Publisher Tests
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Unit tests for SyncEventPublisher class.
# =============================================================================

import pytest
import asyncio
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock

from src.integrations.hybrid.context.sync.events import (
    SyncEvent,
    SyncEventHandler,
    SyncEventPublisher,
    SyncEventType,
)
from src.integrations.hybrid.context.models import (
    Conflict,
    SyncDirection,
    SyncResult,
    SyncStrategy,
)


class TestSyncEventPublisherInit:
    """Test SyncEventPublisher initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        publisher = SyncEventPublisher()
        assert publisher.handler_count == 0
        assert publisher.event_count == 0

    def test_custom_max_history(self):
        """Test custom max history setting."""
        publisher = SyncEventPublisher(max_history=50)
        assert publisher._max_history == 50

    def test_disable_logging(self):
        """Test logging can be disabled."""
        publisher = SyncEventPublisher(enable_logging=False)
        assert publisher._enable_logging is False


class TestSubscription:
    """Test subscription management."""

    def test_subscribe_handler(self):
        """Test subscribing a handler."""
        publisher = SyncEventPublisher()
        handler = AsyncMock()

        sub_id = publisher.subscribe(handler)

        assert sub_id == "sub-1"
        assert publisher.handler_count == 1

    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers."""
        publisher = SyncEventPublisher()
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        sub_id1 = publisher.subscribe(handler1)
        sub_id2 = publisher.subscribe(handler2)

        assert sub_id1 == "sub-1"
        assert sub_id2 == "sub-2"
        assert publisher.handler_count == 2

    def test_subscribe_with_event_filter(self):
        """Test subscribing with event type filter."""
        publisher = SyncEventPublisher()
        handler = AsyncMock()

        sub_id = publisher.subscribe(
            handler, event_types=[SyncEventType.SYNC_STARTED, SyncEventType.SYNC_COMPLETED]
        )

        assert sub_id in publisher._filters
        assert SyncEventType.SYNC_STARTED in publisher._filters[sub_id]
        assert SyncEventType.SYNC_COMPLETED in publisher._filters[sub_id]

    def test_unsubscribe_handler(self):
        """Test unsubscribing a handler."""
        publisher = SyncEventPublisher()
        handler = AsyncMock()

        publisher.subscribe(handler)
        result = publisher.unsubscribe(handler)

        assert result is True
        assert publisher.handler_count == 0

    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing non-existent handler."""
        publisher = SyncEventPublisher()
        handler = AsyncMock()

        result = publisher.unsubscribe(handler)

        assert result is False


class TestPublishing:
    """Test event publishing."""

    @pytest.mark.asyncio
    async def test_publish_event(self):
        """Test publishing an event."""
        publisher = SyncEventPublisher(enable_logging=False)
        handler = AsyncMock()
        publisher.subscribe(handler)

        event = SyncEvent(
            event_type=SyncEventType.SYNC_STARTED,
            session_id="sess-123",
        )
        await publisher.publish(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_to_multiple_handlers(self):
        """Test publishing to multiple handlers."""
        publisher = SyncEventPublisher(enable_logging=False)
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        publisher.subscribe(handler1)
        publisher.subscribe(handler2)

        event = SyncEvent(
            event_type=SyncEventType.SYNC_STARTED,
            session_id="sess-123",
        )
        await publisher.publish(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_respects_filter(self):
        """Test publishing respects event filter."""
        publisher = SyncEventPublisher(enable_logging=False)
        handler = AsyncMock()
        publisher.subscribe(handler, event_types=[SyncEventType.SYNC_COMPLETED])

        # Publish filtered-out event
        event = SyncEvent(
            event_type=SyncEventType.SYNC_STARTED,
            session_id="sess-123",
        )
        await publisher.publish(event)

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_filtered_event_received(self):
        """Test filtered event is received."""
        publisher = SyncEventPublisher(enable_logging=False)
        handler = AsyncMock()
        publisher.subscribe(handler, event_types=[SyncEventType.SYNC_COMPLETED])

        # Publish matching event
        event = SyncEvent(
            event_type=SyncEventType.SYNC_COMPLETED,
            session_id="sess-123",
        )
        await publisher.publish(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_adds_to_history(self):
        """Test publishing adds event to history."""
        publisher = SyncEventPublisher(enable_logging=False)

        event = SyncEvent(
            event_type=SyncEventType.SYNC_STARTED,
            session_id="sess-123",
        )
        await publisher.publish(event)

        assert publisher.event_count == 1

    @pytest.mark.asyncio
    async def test_history_limit_enforced(self):
        """Test history limit is enforced."""
        publisher = SyncEventPublisher(max_history=5, enable_logging=False)

        for i in range(10):
            event = SyncEvent(
                event_type=SyncEventType.SYNC_STARTED,
                session_id=f"sess-{i}",
            )
            await publisher.publish(event)

        assert publisher.event_count == 5

    @pytest.mark.asyncio
    async def test_handler_error_does_not_propagate(self):
        """Test handler error does not propagate."""
        publisher = SyncEventPublisher(enable_logging=False)

        async def failing_handler(event):
            raise ValueError("Handler error")

        publisher.subscribe(failing_handler)

        event = SyncEvent(
            event_type=SyncEventType.SYNC_STARTED,
            session_id="sess-123",
        )

        # Should not raise
        await publisher.publish(event)


class TestConvenienceMethods:
    """Test convenience publishing methods."""

    @pytest.mark.asyncio
    async def test_publish_sync_started(self):
        """Test publish_sync_started method."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        await publisher.publish_sync_started(
            session_id="sess-123",
            strategy=SyncStrategy.MERGE,
            correlation_id="corr-456",
        )

        assert len(events) == 1
        assert events[0].event_type == SyncEventType.SYNC_STARTED
        assert events[0].session_id == "sess-123"
        assert events[0].data["strategy"] == "merge"
        assert events[0].correlation_id == "corr-456"

    @pytest.mark.asyncio
    async def test_publish_sync_completed(self):
        """Test publish_sync_completed method."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        result = SyncResult(
            success=True,
            direction=SyncDirection.BIDIRECTIONAL,
            strategy=SyncStrategy.MERGE,
            source_version=1,
            target_version=2,
            changes_applied=5,
            duration_ms=100,
        )

        await publisher.publish_sync_completed(
            session_id="sess-123",
            result=result,
        )

        assert len(events) == 1
        assert events[0].event_type == SyncEventType.SYNC_COMPLETED
        assert events[0].data["status"] == "success"
        assert events[0].data["items_synced"] == 5

    @pytest.mark.asyncio
    async def test_publish_sync_failed(self):
        """Test publish_sync_failed method."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        await publisher.publish_sync_failed(
            session_id="sess-123",
            error="Connection timeout",
        )

        assert len(events) == 1
        assert events[0].event_type == SyncEventType.SYNC_FAILED
        assert events[0].data["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_publish_conflict_detected(self):
        """Test publish_conflict_detected method."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        conflict = Conflict(
            conflict_id="conflict-123",
            field_path="workflow_status",
            local_value=1,
            remote_value=2,
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
            resolution=SyncStrategy.MERGE.value,
        )

        await publisher.publish_conflict_detected(
            session_id="sess-123",
            conflict=conflict,
        )

        assert len(events) == 1
        assert events[0].event_type == SyncEventType.CONFLICT_DETECTED
        assert events[0].data["conflict_id"] == "conflict-123"
        assert "workflow_status" in events[0].data["conflicting_fields"]

    @pytest.mark.asyncio
    async def test_publish_conflict_resolved(self):
        """Test publish_conflict_resolved method."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        conflict = Conflict(
            conflict_id="conflict-123",
            field_path="workflow_status",
            local_value=1,
            remote_value=2,
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
            resolution=SyncStrategy.MERGE.value,
        )

        await publisher.publish_conflict_resolved(
            session_id="sess-123",
            conflict=conflict,
            strategy_used=SyncStrategy.MAF_PRIMARY,
        )

        assert len(events) == 1
        assert events[0].event_type == SyncEventType.CONFLICT_RESOLVED
        assert events[0].data["strategy_used"] == "maf_primary"

    @pytest.mark.asyncio
    async def test_publish_rollback_events(self):
        """Test rollback event publishing."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        await publisher.publish_rollback_started(
            session_id="sess-123",
            from_version=5,
            to_version=3,
        )

        await publisher.publish_rollback_completed(
            session_id="sess-123",
            version=3,
        )

        assert len(events) == 2
        assert events[0].event_type == SyncEventType.ROLLBACK_STARTED
        assert events[0].data["from_version"] == 5
        assert events[0].data["to_version"] == 3
        assert events[1].event_type == SyncEventType.ROLLBACK_COMPLETED
        assert events[1].data["version"] == 3


class TestEventHistory:
    """Test event history management."""

    @pytest.mark.asyncio
    async def test_get_event_history(self):
        """Test getting event history."""
        publisher = SyncEventPublisher(enable_logging=False)

        for i in range(5):
            await publisher.publish(
                SyncEvent(
                    event_type=SyncEventType.SYNC_STARTED,
                    session_id=f"sess-{i}",
                )
            )

        history = publisher.get_event_history()
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_get_event_history_by_session(self):
        """Test filtering history by session."""
        publisher = SyncEventPublisher(enable_logging=False)

        await publisher.publish(
            SyncEvent(event_type=SyncEventType.SYNC_STARTED, session_id="sess-1")
        )
        await publisher.publish(
            SyncEvent(event_type=SyncEventType.SYNC_STARTED, session_id="sess-2")
        )
        await publisher.publish(
            SyncEvent(event_type=SyncEventType.SYNC_COMPLETED, session_id="sess-1")
        )

        history = publisher.get_event_history(session_id="sess-1")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_event_history_by_type(self):
        """Test filtering history by event type."""
        publisher = SyncEventPublisher(enable_logging=False)

        await publisher.publish(
            SyncEvent(event_type=SyncEventType.SYNC_STARTED, session_id="sess-1")
        )
        await publisher.publish(
            SyncEvent(event_type=SyncEventType.SYNC_COMPLETED, session_id="sess-1")
        )
        await publisher.publish(
            SyncEvent(event_type=SyncEventType.SYNC_STARTED, session_id="sess-2")
        )

        history = publisher.get_event_history(event_type=SyncEventType.SYNC_STARTED)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_event_history_with_limit(self):
        """Test history limit."""
        publisher = SyncEventPublisher(enable_logging=False)

        for i in range(10):
            await publisher.publish(
                SyncEvent(event_type=SyncEventType.SYNC_STARTED, session_id=f"sess-{i}")
            )

        history = publisher.get_event_history(limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_get_last_event(self):
        """Test getting last event for session."""
        publisher = SyncEventPublisher(enable_logging=False)

        await publisher.publish(
            SyncEvent(event_type=SyncEventType.SYNC_STARTED, session_id="sess-1")
        )
        await publisher.publish(
            SyncEvent(event_type=SyncEventType.SYNC_COMPLETED, session_id="sess-1")
        )

        last = publisher.get_last_event("sess-1")
        assert last is not None
        assert last.event_type == SyncEventType.SYNC_COMPLETED

    @pytest.mark.asyncio
    async def test_get_last_event_not_found(self):
        """Test getting last event for non-existent session."""
        publisher = SyncEventPublisher(enable_logging=False)

        last = publisher.get_last_event("sess-nonexistent")
        assert last is None

    @pytest.mark.asyncio
    async def test_clear_history(self):
        """Test clearing history."""
        publisher = SyncEventPublisher(enable_logging=False)

        for i in range(5):
            await publisher.publish(
                SyncEvent(event_type=SyncEventType.SYNC_STARTED, session_id=f"sess-{i}")
            )

        publisher.clear_history()
        assert publisher.event_count == 0


class TestSyncEvent:
    """Test SyncEvent dataclass."""

    def test_event_creation(self):
        """Test creating an event."""
        event = SyncEvent(
            event_type=SyncEventType.SYNC_STARTED,
            session_id="sess-123",
            data={"key": "value"},
        )

        assert event.event_type == SyncEventType.SYNC_STARTED
        assert event.session_id == "sess-123"
        assert event.data == {"key": "value"}
        assert event.source == "sync_service"

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = SyncEvent(
            event_type=SyncEventType.SYNC_STARTED,
            session_id="sess-123",
            correlation_id="corr-456",
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "sync_started"
        assert event_dict["session_id"] == "sess-123"
        assert event_dict["correlation_id"] == "corr-456"
        assert "timestamp" in event_dict

    def test_event_default_timestamp(self):
        """Test event has default timestamp."""
        event = SyncEvent(
            event_type=SyncEventType.SYNC_STARTED,
            session_id="sess-123",
        )

        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)
