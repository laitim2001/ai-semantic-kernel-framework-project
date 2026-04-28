"""
Unit tests for Session Recovery Manager (S47-2)

Tests:
- CheckpointType enumeration
- SessionCheckpoint data class
- SessionRecoveryManager checkpoint operations
- Event buffering for reconnection
- WebSocket reconnection handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import asyncio

from src.domain.sessions.recovery import (
    CheckpointType,
    SessionCheckpoint,
    SessionRecoveryManager,
    create_recovery_manager,
)
from src.domain.sessions.events import ExecutionEvent, ExecutionEventType


# =============================================================================
# CheckpointType Tests
# =============================================================================

class TestCheckpointType:
    """Test CheckpointType enumeration"""

    def test_checkpoint_types_exist(self):
        """Test all checkpoint types exist"""
        assert CheckpointType.EXECUTION_START.value == "execution_start"
        assert CheckpointType.TOOL_CALL.value == "tool_call"
        assert CheckpointType.APPROVAL_PENDING.value == "approval_pending"
        assert CheckpointType.CONTENT_PARTIAL.value == "content_partial"
        assert CheckpointType.EXECUTION_COMPLETE.value == "execution_complete"

    def test_checkpoint_type_count(self):
        """Test checkpoint type count"""
        assert len(CheckpointType) == 5


# =============================================================================
# SessionCheckpoint Tests
# =============================================================================

class TestSessionCheckpoint:
    """Test SessionCheckpoint data class"""

    def test_create_checkpoint(self):
        """Test creating checkpoint"""
        checkpoint = SessionCheckpoint(
            session_id="session-123",
            checkpoint_type=CheckpointType.EXECUTION_START,
            execution_id="exec-456",
            state={"current_step": 1},
            metadata={"agent_id": "agent-789"},
        )

        assert checkpoint.session_id == "session-123"
        assert checkpoint.checkpoint_type == CheckpointType.EXECUTION_START
        assert checkpoint.execution_id == "exec-456"
        assert checkpoint.state == {"current_step": 1}
        assert checkpoint.metadata == {"agent_id": "agent-789"}
        assert checkpoint.created_at is not None

    def test_checkpoint_to_dict(self):
        """Test converting checkpoint to dictionary"""
        now = datetime.utcnow()
        expires = now + timedelta(hours=1)

        checkpoint = SessionCheckpoint(
            session_id="session-123",
            checkpoint_type=CheckpointType.TOOL_CALL,
            execution_id="exec-456",
            state={"tool_name": "calculator"},
            created_at=now,
            expires_at=expires,
            metadata={"retry_count": 0},
        )

        data = checkpoint.to_dict()

        assert data["session_id"] == "session-123"
        assert data["checkpoint_type"] == "tool_call"
        assert data["execution_id"] == "exec-456"
        assert data["state"] == {"tool_name": "calculator"}
        assert data["created_at"] == now.isoformat()
        assert data["expires_at"] == expires.isoformat()
        assert data["metadata"] == {"retry_count": 0}

    def test_checkpoint_from_dict(self):
        """Test creating checkpoint from dictionary"""
        now = datetime.utcnow()
        expires = now + timedelta(hours=1)

        data = {
            "session_id": "session-123",
            "checkpoint_type": "approval_pending",
            "execution_id": "exec-456",
            "state": {"approval_id": "approval-789"},
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "metadata": {"tool_name": "file_write"},
        }

        checkpoint = SessionCheckpoint.from_dict(data)

        assert checkpoint.session_id == "session-123"
        assert checkpoint.checkpoint_type == CheckpointType.APPROVAL_PENDING
        assert checkpoint.execution_id == "exec-456"
        assert checkpoint.state == {"approval_id": "approval-789"}
        assert checkpoint.metadata == {"tool_name": "file_write"}

    def test_checkpoint_is_expired_false(self):
        """Test checkpoint not expired"""
        checkpoint = SessionCheckpoint(
            session_id="session-123",
            checkpoint_type=CheckpointType.EXECUTION_START,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

        assert checkpoint.is_expired is False

    def test_checkpoint_is_expired_true(self):
        """Test checkpoint expired"""
        checkpoint = SessionCheckpoint(
            session_id="session-123",
            checkpoint_type=CheckpointType.EXECUTION_START,
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )

        assert checkpoint.is_expired is True

    def test_checkpoint_no_expiry(self):
        """Test checkpoint without expiry"""
        checkpoint = SessionCheckpoint(
            session_id="session-123",
            checkpoint_type=CheckpointType.EXECUTION_START,
        )

        assert checkpoint.is_expired is False


# =============================================================================
# SessionRecoveryManager Tests - Checkpoint Operations
# =============================================================================

class TestSessionRecoveryManagerCheckpoint:
    """Test SessionRecoveryManager checkpoint operations"""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        cache.exists = AsyncMock(return_value=False)
        return cache

    @pytest.fixture
    def manager(self, mock_cache):
        """Create recovery manager"""
        return SessionRecoveryManager(
            cache=mock_cache,
            checkpoint_ttl=3600,
            event_buffer_ttl=300,
            max_buffered_events=100,
        )

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, manager, mock_cache):
        """Test saving checkpoint"""
        checkpoint = await manager.save_checkpoint(
            session_id="session-123",
            checkpoint_type=CheckpointType.EXECUTION_START,
            state={"step": 1},
            execution_id="exec-456",
            metadata={"agent_id": "agent-789"},
        )

        assert checkpoint.session_id == "session-123"
        assert checkpoint.checkpoint_type == CheckpointType.EXECUTION_START
        assert checkpoint.state == {"step": 1}
        assert checkpoint.execution_id == "exec-456"
        assert checkpoint.metadata == {"agent_id": "agent-789"}
        assert checkpoint.expires_at is not None

        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_checkpoint_custom_ttl(self, manager, mock_cache):
        """Test saving checkpoint with custom TTL"""
        await manager.save_checkpoint(
            session_id="session-123",
            checkpoint_type=CheckpointType.TOOL_CALL,
            state={},
            ttl=7200,  # 2 hours
        )

        # Verify set was called with custom TTL
        call_args = mock_cache.set.call_args
        assert call_args.kwargs.get("ttl") == 7200

    @pytest.mark.asyncio
    async def test_get_checkpoint_exists(self, manager, mock_cache):
        """Test getting existing checkpoint"""
        now = datetime.utcnow()
        expires = now + timedelta(hours=1)

        mock_cache.get.return_value = {
            "session_id": "session-123",
            "checkpoint_type": "execution_start",
            "execution_id": "exec-456",
            "state": {"step": 1},
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "metadata": {},
        }

        checkpoint = await manager.get_checkpoint("session-123")

        assert checkpoint is not None
        assert checkpoint.session_id == "session-123"
        assert checkpoint.checkpoint_type == CheckpointType.EXECUTION_START

    @pytest.mark.asyncio
    async def test_get_checkpoint_not_exists(self, manager, mock_cache):
        """Test getting non-existent checkpoint"""
        mock_cache.get.return_value = None

        checkpoint = await manager.get_checkpoint("session-123")

        assert checkpoint is None

    @pytest.mark.asyncio
    async def test_get_checkpoint_expired(self, manager, mock_cache):
        """Test getting expired checkpoint deletes it"""
        now = datetime.utcnow()
        expired = now - timedelta(hours=1)

        mock_cache.get.return_value = {
            "session_id": "session-123",
            "checkpoint_type": "execution_start",
            "state": {},
            "created_at": now.isoformat(),
            "expires_at": expired.isoformat(),
            "metadata": {},
        }

        checkpoint = await manager.get_checkpoint("session-123")

        assert checkpoint is None
        mock_cache.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, manager, mock_cache):
        """Test deleting checkpoint"""
        await manager.delete_checkpoint("session-123")

        mock_cache.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_from_checkpoint(self, manager, mock_cache):
        """Test restoring from checkpoint"""
        now = datetime.utcnow()
        expires = now + timedelta(hours=1)

        mock_cache.get.return_value = {
            "session_id": "session-123",
            "checkpoint_type": "tool_call",
            "execution_id": "exec-456",
            "state": {"tool_name": "calculator", "args": {"a": 1, "b": 2}},
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "metadata": {},
        }

        state = await manager.restore_from_checkpoint("session-123")

        assert state is not None
        assert state["tool_name"] == "calculator"
        assert state["args"] == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_restore_from_checkpoint_not_exists(self, manager, mock_cache):
        """Test restoring from non-existent checkpoint"""
        mock_cache.get.return_value = None

        state = await manager.restore_from_checkpoint("session-123")

        assert state is None


# =============================================================================
# SessionRecoveryManager Tests - Event Buffer Operations
# =============================================================================

class TestSessionRecoveryManagerEventBuffer:
    """Test SessionRecoveryManager event buffer operations"""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def manager(self, mock_cache):
        """Create recovery manager"""
        return SessionRecoveryManager(
            cache=mock_cache,
            max_buffered_events=5,
        )

    def create_event(self, event_id: str) -> ExecutionEvent:
        """Create test event"""
        return ExecutionEvent(
            id=event_id,
            event_type=ExecutionEventType.CONTENT,
            session_id="session-123",
            execution_id="exec-456",
            content=f"Event {event_id}",
        )

    @pytest.mark.asyncio
    async def test_buffer_event(self, manager, mock_cache):
        """Test buffering event"""
        event = self.create_event("event-1")

        await manager.buffer_event("session-123", event)

        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_buffer_event_limits_size(self, manager, mock_cache):
        """Test buffer limits size"""
        # Simulate existing buffer with 5 events
        existing_buffer = [
            self.create_event(f"event-{i}").to_dict()
            for i in range(5)
        ]
        mock_cache.get.return_value = existing_buffer

        # Add one more event
        new_event = self.create_event("event-5")
        await manager.buffer_event("session-123", new_event)

        # Check that buffer was trimmed
        call_args = mock_cache.set.call_args
        saved_buffer = call_args[0][1]
        assert len(saved_buffer) == 5

    @pytest.mark.asyncio
    async def test_get_buffered_events(self, manager, mock_cache):
        """Test getting buffered events"""
        mock_cache.get.return_value = [
            self.create_event("event-1").to_dict(),
            self.create_event("event-2").to_dict(),
            self.create_event("event-3").to_dict(),
        ]

        events = await manager.get_buffered_events("session-123")

        assert len(events) == 3
        assert events[0].id == "event-1"
        assert events[1].id == "event-2"
        assert events[2].id == "event-3"

    @pytest.mark.asyncio
    async def test_get_buffered_events_since(self, manager, mock_cache):
        """Test getting buffered events since specific event"""
        mock_cache.get.return_value = [
            self.create_event("event-1").to_dict(),
            self.create_event("event-2").to_dict(),
            self.create_event("event-3").to_dict(),
        ]

        events = await manager.get_buffered_events("session-123", since_event_id="event-1")

        assert len(events) == 2
        assert events[0].id == "event-2"
        assert events[1].id == "event-3"

    @pytest.mark.asyncio
    async def test_get_buffered_events_empty(self, manager, mock_cache):
        """Test getting empty buffer"""
        mock_cache.get.return_value = None

        events = await manager.get_buffered_events("session-123")

        assert events == []

    @pytest.mark.asyncio
    async def test_clear_event_buffer(self, manager, mock_cache):
        """Test clearing event buffer"""
        await manager.clear_event_buffer("session-123")

        mock_cache.delete.assert_called_once()


# =============================================================================
# SessionRecoveryManager Tests - WebSocket Reconnection
# =============================================================================

class TestSessionRecoveryManagerReconnection:
    """Test SessionRecoveryManager WebSocket reconnection"""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def manager(self, mock_cache):
        """Create recovery manager"""
        return SessionRecoveryManager(cache=mock_cache)

    def create_event(self, event_id: str) -> ExecutionEvent:
        """Create test event"""
        return ExecutionEvent(
            id=event_id,
            event_type=ExecutionEventType.CONTENT,
            session_id="session-123",
            execution_id="exec-456",
            content=f"Event {event_id}",
        )

    @pytest.mark.asyncio
    async def test_handle_websocket_reconnect_no_data(self, manager, mock_cache):
        """Test reconnect with no checkpoint or events"""
        result = await manager.handle_websocket_reconnect("session-123")

        assert result["status"] == "reconnected"
        assert result["session_id"] == "session-123"
        assert result["checkpoint"] is None
        assert result["missed_events"] == []
        assert result["pending_state"] is None

    @pytest.mark.asyncio
    async def test_handle_websocket_reconnect_with_checkpoint(self, manager, mock_cache):
        """Test reconnect with pending checkpoint"""
        now = datetime.utcnow()
        expires = now + timedelta(hours=1)

        # First call returns checkpoint, second returns empty events
        mock_cache.get.side_effect = [
            {
                "session_id": "session-123",
                "checkpoint_type": "approval_pending",
                "execution_id": "exec-456",
                "state": {"approval_id": "approval-789"},
                "created_at": now.isoformat(),
                "expires_at": expires.isoformat(),
                "metadata": {},
            },
            [],  # Empty event buffer
        ]

        result = await manager.handle_websocket_reconnect("session-123")

        assert result["checkpoint"] is not None
        assert result["pending_state"] == {"approval_id": "approval-789"}

    @pytest.mark.asyncio
    async def test_handle_websocket_reconnect_with_missed_events(self, manager, mock_cache):
        """Test reconnect with missed events"""
        # First call returns no checkpoint, second returns events
        mock_cache.get.side_effect = [
            None,  # No checkpoint
            [
                self.create_event("event-1").to_dict(),
                self.create_event("event-2").to_dict(),
            ],
        ]

        result = await manager.handle_websocket_reconnect("session-123", last_event_id=None)

        assert len(result["missed_events"]) == 2

    @pytest.mark.asyncio
    async def test_save_reconnect_info(self, manager, mock_cache):
        """Test saving reconnect info"""
        await manager.save_reconnect_info(
            session_id="session-123",
            connection_id="conn-456",
            client_info={"user_agent": "test"},
        )

        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        saved_data = call_args[0][1]
        assert saved_data["connection_id"] == "conn-456"
        assert saved_data["client_info"] == {"user_agent": "test"}

    @pytest.mark.asyncio
    async def test_get_reconnect_info(self, manager, mock_cache):
        """Test getting reconnect info"""
        mock_cache.get.return_value = {
            "connection_id": "conn-456",
            "connected_at": datetime.utcnow().isoformat(),
            "client_info": {},
        }

        info = await manager.get_reconnect_info("session-123")

        assert info is not None
        assert info["connection_id"] == "conn-456"

    @pytest.mark.asyncio
    async def test_clear_reconnect_info(self, manager, mock_cache):
        """Test clearing reconnect info"""
        await manager.clear_reconnect_info("session-123")

        mock_cache.delete.assert_called_once()


# =============================================================================
# Recovery Event Creation Tests
# =============================================================================

class TestRecoveryEventCreation:
    """Test recovery event creation methods"""

    @pytest.fixture
    def manager(self):
        """Create recovery manager with mock cache"""
        mock_cache = AsyncMock()
        return SessionRecoveryManager(cache=mock_cache)

    def test_create_reconnect_event(self, manager):
        """Test creating reconnect event"""
        event = manager.create_reconnect_event(
            session_id="session-123",
            execution_id="exec-456",
            pending_state={"approval_id": "approval-789"},
            missed_event_count=5,
        )

        assert event.session_id == "session-123"
        assert event.execution_id == "exec-456"
        assert event.event_type == ExecutionEventType.CONTENT
        assert event.content == "reconnected"
        assert event.metadata["type"] == "reconnected"
        assert event.metadata["pending_state"] == {"approval_id": "approval-789"}
        assert event.metadata["missed_event_count"] == 5

    def test_create_recovery_event(self, manager):
        """Test creating recovery event"""
        event = manager.create_recovery_event(
            session_id="session-123",
            execution_id="exec-456",
            checkpoint_type=CheckpointType.APPROVAL_PENDING,
            message="Waiting for tool approval",
        )

        assert event.session_id == "session-123"
        assert event.execution_id == "exec-456"
        assert event.event_type == ExecutionEventType.CONTENT
        assert event.content == "Waiting for tool approval"
        assert event.metadata["type"] == "recovery"
        assert event.metadata["checkpoint_type"] == "approval_pending"
        assert event.metadata["message"] == "Waiting for tool approval"


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Test factory function"""

    def test_create_recovery_manager_default(self):
        """Test creating manager with defaults"""
        mock_cache = AsyncMock()
        manager = create_recovery_manager(cache=mock_cache)

        assert manager._checkpoint_ttl == 3600
        assert manager._event_buffer_ttl == 300
        assert manager._max_buffered_events == 100

    def test_create_recovery_manager_custom(self):
        """Test creating manager with custom values"""
        mock_cache = AsyncMock()
        manager = create_recovery_manager(
            cache=mock_cache,
            checkpoint_ttl=7200,
            event_buffer_ttl=600,
            max_buffered_events=50,
        )

        assert manager._checkpoint_ttl == 7200
        assert manager._event_buffer_ttl == 600
        assert manager._max_buffered_events == 50
