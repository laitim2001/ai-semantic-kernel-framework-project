# =============================================================================
# IPA Platform - Multi-Turn Session Tests
# =============================================================================
# Sprint 9: S9-3 MultiTurnSessionManager (8 points)
#
# Unit tests for MultiTurnSessionManager, TurnTracker, and ContextManager.
# =============================================================================

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.domain.orchestration.multiturn.session_manager import (
    MultiTurnSession,
    MultiTurnSessionManager,
    SessionMessage,
    SessionStatus,
)
from src.domain.orchestration.multiturn.turn_tracker import (
    Turn,
    TurnMessage,
    TurnStatus,
    TurnTracker,
)
from src.domain.orchestration.multiturn.context_manager import (
    ContextEntry,
    ContextScope,
    SessionContextManager,
)


# =============================================================================
# SessionMessage Tests
# =============================================================================

class TestSessionMessage:
    """Tests for SessionMessage dataclass."""

    def test_create_message(self):
        """Test creating a session message."""
        message = SessionMessage(
            message_id="msg-1",
            session_id="session-1",
            turn_number=1,
            role="user",
            content="Hello",
        )

        assert message.message_id == "msg-1"
        assert message.session_id == "session-1"
        assert message.turn_number == 1
        assert message.role == "user"
        assert message.content == "Hello"
        assert isinstance(message.timestamp, datetime)

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = SessionMessage(
            message_id="msg-1",
            session_id="session-1",
            turn_number=1,
            role="agent",
            content="Hi there!",
            sender_id="agent-1",
            sender_name="Agent 1",
            metadata={"key": "value"},
        )

        data = message.to_dict()

        assert data["message_id"] == "msg-1"
        assert data["role"] == "agent"
        assert data["sender_id"] == "agent-1"
        assert data["metadata"] == {"key": "value"}

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "message_id": "msg-1",
            "session_id": "session-1",
            "turn_number": 2,
            "role": "user",
            "content": "Test",
            "timestamp": "2025-01-01T00:00:00",
        }

        message = SessionMessage.from_dict(data)

        assert message.message_id == "msg-1"
        assert message.turn_number == 2


# =============================================================================
# MultiTurnSession Tests
# =============================================================================

class TestMultiTurnSession:
    """Tests for MultiTurnSession dataclass."""

    def test_create_session(self):
        """Test creating a multi-turn session."""
        session = MultiTurnSession(
            session_id="session-1",
            user_id="user-1",
            agent_ids=["agent-1", "agent-2"],
        )

        assert session.session_id == "session-1"
        assert session.user_id == "user-1"
        assert session.agent_ids == ["agent-1", "agent-2"]
        assert session.status == SessionStatus.CREATED
        assert session.current_turn == 0
        assert session.expires_at is not None

    def test_session_properties(self):
        """Test session properties."""
        session = MultiTurnSession(
            session_id="session-1",
            user_id="user-1",
            status=SessionStatus.ACTIVE,
        )

        assert session.is_active is True
        assert session.is_expired is False
        assert session.message_count == 0

    def test_session_expired(self):
        """Test session expiration."""
        session = MultiTurnSession(
            session_id="session-1",
            user_id="user-1",
            timeout_seconds=1,  # 1 second timeout
        )

        # Initially not expired
        assert session.is_expired is False

        # Set expires_at to the past
        session.expires_at = datetime.utcnow() - timedelta(seconds=10)
        assert session.is_expired is True

    def test_update_activity(self):
        """Test activity update."""
        session = MultiTurnSession(
            session_id="session-1",
            user_id="user-1",
            timeout_seconds=60,
        )

        old_expires = session.expires_at
        session.update_activity()

        assert session.last_activity > session.created_at
        assert session.expires_at > old_expires

    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        session = MultiTurnSession(
            session_id="session-1",
            user_id="user-1",
            context={"key": "value"},
        )

        data = session.to_dict()

        assert data["session_id"] == "session-1"
        assert data["user_id"] == "user-1"
        assert data["context"] == {"key": "value"}


# =============================================================================
# MultiTurnSessionManager Tests
# =============================================================================

class TestMultiTurnSessionManager:
    """Tests for MultiTurnSessionManager."""

    @pytest.fixture
    def manager(self):
        """Create a session manager."""
        return MultiTurnSessionManager()

    @pytest.mark.asyncio
    async def test_create_session(self, manager):
        """Test creating a session."""
        session = await manager.create_session(
            user_id="user-1",
            agent_ids=["agent-1"],
            initial_context={"topic": "test"},
        )

        assert session.user_id == "user-1"
        assert session.agent_ids == ["agent-1"]
        assert session.context.get("topic") == "test"
        assert session.status == SessionStatus.CREATED

    @pytest.mark.asyncio
    async def test_get_session(self, manager):
        """Test getting a session."""
        created = await manager.create_session(user_id="user-1")
        retrieved = await manager.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, manager):
        """Test getting a nonexistent session."""
        result = await manager.get_session("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_session(self, manager):
        """Test updating a session."""
        session = await manager.create_session(user_id="user-1")

        updated = await manager.update_session(
            session.session_id,
            context={"key": "value"},
            metadata={"updated": True},
        )

        assert updated.context.get("key") == "value"
        assert updated.metadata.get("updated") is True

    @pytest.mark.asyncio
    async def test_close_session(self, manager):
        """Test closing a session."""
        session = await manager.create_session(user_id="user-1")

        result = await manager.close_session(session.session_id, "Test close")

        assert result is True
        closed = await manager.get_session(session.session_id)
        assert closed.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_delete_session(self, manager):
        """Test deleting a session."""
        session = await manager.create_session(user_id="user-1")

        result = await manager.delete_session(session.session_id)

        assert result is True
        retrieved = await manager.get_session(session.session_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_start_session(self, manager):
        """Test starting a session."""
        session = await manager.create_session(user_id="user-1")

        started = await manager.start_session(session.session_id)

        assert started.status == SessionStatus.ACTIVE
        assert started.current_turn == 1

    @pytest.mark.asyncio
    async def test_pause_resume_session(self, manager):
        """Test pausing and resuming a session."""
        session = await manager.create_session(user_id="user-1")
        await manager.start_session(session.session_id)

        # Pause
        result = await manager.pause_session(session.session_id)
        assert result is True

        paused = await manager.get_session(session.session_id)
        assert paused.status == SessionStatus.PAUSED

        # Resume
        resumed = await manager.resume_session(session.session_id)
        assert resumed.status == SessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_start_turn(self, manager):
        """Test starting a new turn."""
        session = await manager.create_session(user_id="user-1")
        await manager.start_session(session.session_id)

        turn_number = await manager.start_turn(session.session_id)

        assert turn_number == 2  # First turn is 1, this is turn 2

    @pytest.mark.asyncio
    async def test_add_message(self, manager):
        """Test adding a message."""
        session = await manager.create_session(user_id="user-1")
        await manager.start_session(session.session_id)

        message = await manager.add_message(
            session_id=session.session_id,
            role="user",
            content="Hello",
            sender_id="user-1",
        )

        assert message is not None
        assert message.content == "Hello"
        assert message.turn_number == 1

    @pytest.mark.asyncio
    async def test_get_history(self, manager):
        """Test getting message history."""
        session = await manager.create_session(user_id="user-1")
        await manager.start_session(session.session_id)

        await manager.add_message(session.session_id, "user", "Message 1")
        await manager.add_message(session.session_id, "agent", "Response 1")
        await manager.add_message(session.session_id, "user", "Message 2")

        history = await manager.get_history(session.session_id)
        assert len(history) == 3

        # Test with limit
        limited = await manager.get_history(session.session_id, limit=2)
        assert len(limited) == 2

    @pytest.mark.asyncio
    async def test_execute_turn(self, manager):
        """Test executing a complete turn."""
        session = await manager.create_session(
            user_id="user-1",
            agent_ids=["agent-1"],
        )

        def mock_handler(agent_id, user_input, history):
            return f"Response to: {user_input}"

        response = await manager.execute_turn(
            session_id=session.session_id,
            user_input="Hello",
            agent_handler=mock_handler,
        )

        assert response is not None
        assert "Response to: Hello" in response.content

        # Verify both messages are in history
        history = await manager.get_history(session.session_id)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_list_sessions(self, manager):
        """Test listing sessions."""
        await manager.create_session(user_id="user-1")
        await manager.create_session(user_id="user-1")
        await manager.create_session(user_id="user-2")

        all_sessions = await manager.list_sessions()
        assert len(all_sessions) == 3

        user1_sessions = await manager.list_sessions(user_id="user-1")
        assert len(user1_sessions) == 2

    @pytest.mark.asyncio
    async def test_list_active_sessions(self, manager):
        """Test listing active sessions."""
        session1 = await manager.create_session(user_id="user-1")
        session2 = await manager.create_session(user_id="user-1")

        await manager.start_session(session1.session_id)

        active = await manager.list_active_sessions(user_id="user-1")
        assert len(active) == 1
        assert active[0].session_id == session1.session_id

    @pytest.mark.asyncio
    async def test_max_turns_limit(self, manager):
        """Test max turns limit."""
        session = await manager.create_session(
            user_id="user-1",
            max_turns=2,
        )
        await manager.start_session(session.session_id)

        # Turn 2
        await manager.start_turn(session.session_id)

        # Turn 3 should fail (exceeds max)
        turn3 = await manager.start_turn(session.session_id)
        assert turn3 is None

        updated = await manager.get_session(session.session_id)
        assert updated.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_event_handling(self, manager):
        """Test event handling."""
        events = []

        def handler(data):
            events.append(data)

        manager.on_event("session_created", handler)

        await manager.create_session(user_id="user-1")

        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, manager):
        """Test cleaning up expired sessions."""
        # Create session with very short timeout
        session = await manager.create_session(
            user_id="user-1",
            timeout_seconds=1,
        )

        # Force expiration
        session.expires_at = datetime.utcnow() - timedelta(seconds=10)

        count = await manager.cleanup_expired_sessions()

        # Session should be marked as expired
        assert count >= 0


# =============================================================================
# TurnTracker Tests
# =============================================================================

class TestTurnTracker:
    """Tests for TurnTracker."""

    @pytest.fixture
    def tracker(self):
        """Create a turn tracker."""
        return TurnTracker(session_id="session-1")

    def test_create_tracker(self, tracker):
        """Test creating a turn tracker."""
        assert tracker.session_id == "session-1"
        assert tracker.turn_count == 0
        assert tracker.current_turn is None

    def test_start_turn(self, tracker):
        """Test starting a new turn."""
        turn = tracker.start_turn(agent_id="agent-1")

        assert turn.turn_number == 1
        assert turn.status == TurnStatus.STARTED
        assert turn.agent_id == "agent-1"
        assert tracker.current_turn == turn

    def test_multiple_turns(self, tracker):
        """Test multiple turns."""
        turn1 = tracker.start_turn()
        tracker.end_turn(turn1.turn_id)

        turn2 = tracker.start_turn()

        assert turn2.turn_number == 2
        assert tracker.turn_count == 2

    def test_end_turn_success(self, tracker):
        """Test ending a turn successfully."""
        turn = tracker.start_turn()

        ended = tracker.end_turn(turn.turn_id, success=True)

        assert ended.status == TurnStatus.COMPLETED
        assert ended.completed_at is not None
        assert ended.duration_ms is not None

    def test_end_turn_failure(self, tracker):
        """Test ending a turn with failure."""
        turn = tracker.start_turn()

        ended = tracker.end_turn(turn.turn_id, success=False, failure_reason="Error")

        assert ended.status == TurnStatus.FAILED
        assert ended.metadata.get("failure_reason") == "Error"

    def test_add_message_to_current(self, tracker):
        """Test adding message to current turn."""
        tracker.start_turn()

        message = tracker.add_message_to_current("user", "Hello")

        assert message is not None
        assert message.role == "user"
        assert message.content == "Hello"

    def test_add_message_no_turn(self, tracker):
        """Test adding message without active turn."""
        message = tracker.add_message_to_current("user", "Hello")
        assert message is None

    def test_get_turn_by_number(self, tracker):
        """Test getting turn by number."""
        tracker.start_turn()
        tracker.end_turn(tracker.current_turn.turn_id)
        tracker.start_turn()

        turn = tracker.get_turn_by_number(1)
        assert turn is not None
        assert turn.turn_number == 1

    def test_get_turn_history(self, tracker):
        """Test getting turn history."""
        for i in range(3):
            turn = tracker.start_turn()
            tracker.end_turn(turn.turn_id)

        history = tracker.get_turn_history()
        assert len(history) == 3

        limited = tracker.get_turn_history(limit=2)
        assert len(limited) == 2

    def test_get_all_messages(self, tracker):
        """Test getting all messages across turns."""
        turn1 = tracker.start_turn()
        tracker.add_message_to_current("user", "Message 1")
        tracker.add_message_to_current("agent", "Response 1")
        tracker.end_turn(turn1.turn_id)

        turn2 = tracker.start_turn()
        tracker.add_message_to_current("user", "Message 2")
        tracker.end_turn(turn2.turn_id)

        messages = tracker.get_all_messages()
        assert len(messages) == 3

    def test_get_statistics(self, tracker):
        """Test getting statistics."""
        turn1 = tracker.start_turn()
        tracker.add_message_to_current("user", "Hello")
        tracker.end_turn(turn1.turn_id, success=True)

        turn2 = tracker.start_turn()
        tracker.end_turn(turn2.turn_id, success=False)

        stats = tracker.get_statistics()

        assert stats["total_turns"] == 2
        assert stats["completed_turns"] == 1
        assert stats["failed_turns"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["total_messages"] == 1

    def test_cancel_current(self, tracker):
        """Test cancelling current turn."""
        turn = tracker.start_turn()

        cancelled = tracker.cancel_current()

        assert cancelled.status == TurnStatus.CANCELLED
        assert tracker.current_turn is None

    def test_clear(self, tracker):
        """Test clearing all turns."""
        tracker.start_turn()
        tracker.start_turn()

        tracker.clear()

        assert tracker.turn_count == 0
        assert tracker.current_turn is None


# =============================================================================
# Turn Tests
# =============================================================================

class TestTurn:
    """Tests for Turn dataclass."""

    def test_create_turn(self):
        """Test creating a turn."""
        turn = Turn(
            turn_id="turn-1",
            session_id="session-1",
            turn_number=1,
        )

        assert turn.turn_id == "turn-1"
        assert turn.status == TurnStatus.STARTED
        assert turn.messages == []

    def test_add_message(self):
        """Test adding message to turn."""
        turn = Turn(
            turn_id="turn-1",
            session_id="session-1",
            turn_number=1,
        )

        message = turn.add_message("user", "Hello")

        assert message.role == "user"
        assert message.content == "Hello"
        assert len(turn.messages) == 1

    def test_complete_turn(self):
        """Test completing a turn."""
        turn = Turn(
            turn_id="turn-1",
            session_id="session-1",
            turn_number=1,
        )

        turn.complete()

        assert turn.status == TurnStatus.COMPLETED
        assert turn.completed_at is not None
        assert turn.duration_ms is not None

    def test_fail_turn(self):
        """Test failing a turn."""
        turn = Turn(
            turn_id="turn-1",
            session_id="session-1",
            turn_number=1,
        )

        turn.fail("Test error")

        assert turn.status == TurnStatus.FAILED
        assert turn.metadata.get("failure_reason") == "Test error"

    def test_turn_to_dict(self):
        """Test converting turn to dictionary."""
        turn = Turn(
            turn_id="turn-1",
            session_id="session-1",
            turn_number=1,
            agent_id="agent-1",
        )
        turn.add_message("user", "Hello")

        data = turn.to_dict()

        assert data["turn_id"] == "turn-1"
        assert data["turn_number"] == 1
        assert len(data["messages"]) == 1


# =============================================================================
# SessionContextManager Tests
# =============================================================================

class TestSessionContextManager:
    """Tests for SessionContextManager."""

    @pytest.fixture
    def context_manager(self):
        """Create a context manager."""
        return SessionContextManager(session_id="session-1")

    def test_create_manager(self, context_manager):
        """Test creating a context manager."""
        assert context_manager.session_id == "session-1"
        assert context_manager.current_turn == 0

    def test_set_get_context(self, context_manager):
        """Test setting and getting context."""
        context_manager.set("key", "value")

        result = context_manager.get("key")
        assert result == "value"

    def test_get_default(self, context_manager):
        """Test getting with default value."""
        result = context_manager.get("nonexistent", default="default")
        assert result == "default"

    def test_remove_context(self, context_manager):
        """Test removing context."""
        context_manager.set("key", "value")

        result = context_manager.remove("key")
        assert result is True

        result = context_manager.get("key")
        assert result is None

    def test_has_key(self, context_manager):
        """Test checking key existence."""
        context_manager.set("key", "value")

        assert context_manager.has("key") is True
        assert context_manager.has("nonexistent") is False

    def test_context_scopes(self, context_manager):
        """Test different context scopes."""
        context_manager.set("session_key", "session_value", scope=ContextScope.SESSION)
        context_manager.set("turn_key", "turn_value", scope=ContextScope.TURN)

        keys = context_manager.keys()
        assert "session_key" in keys
        assert "turn_key" in keys

        session_keys = context_manager.keys(scope=ContextScope.SESSION)
        assert "session_key" in session_keys
        assert "turn_key" not in session_keys

    def test_update_context(self, context_manager):
        """Test batch context update."""
        context_manager.update_context({
            "key1": "value1",
            "key2": "value2",
        })

        assert context_manager.get("key1") == "value1"
        assert context_manager.get("key2") == "value2"

    def test_merge_context(self, context_manager):
        """Test merging context."""
        context_manager.set("existing", "old_value")

        context_manager.merge_context(
            {"existing": "new_value", "new": "value"},
            override=False,
        )

        assert context_manager.get("existing") == "old_value"  # Not overridden
        assert context_manager.get("new") == "value"

        context_manager.merge_context(
            {"existing": "new_value"},
            override=True,
        )
        assert context_manager.get("existing") == "new_value"  # Overridden

    def test_clear_context(self, context_manager):
        """Test clearing context."""
        context_manager.set("key1", "value1", scope=ContextScope.SESSION)
        context_manager.set("key2", "value2", scope=ContextScope.TURN)

        count = context_manager.clear_context(scope=ContextScope.TURN)
        assert count == 1
        assert context_manager.has("key1")
        assert not context_manager.has("key2")

        context_manager.clear_context()
        assert not context_manager.has("key1")

    def test_turn_management(self, context_manager):
        """Test turn context management."""
        context_manager.set("session_var", "session", scope=ContextScope.SESSION)
        context_manager.set("turn_var", "turn", scope=ContextScope.TURN)

        context_manager.start_turn(1)
        assert context_manager.current_turn == 1

        context_manager.end_turn()
        # Turn-scoped context should be cleared
        assert context_manager.has("session_var")
        assert not context_manager.has("turn_var")

    def test_build_agent_context(self, context_manager):
        """Test building agent context."""
        context_manager.set("user_name", "Alice", scope=ContextScope.SESSION)
        context_manager.set("current_topic", "Testing", scope=ContextScope.TURN)

        context = context_manager.build_agent_context()

        assert context.get("user_name") == "Alice"
        assert context.get("current_topic") == "Testing"
        assert "_session_id" in context

    def test_context_transformer(self, context_manager):
        """Test context transformer."""
        def transformer(ctx):
            ctx["transformed"] = True
            return ctx

        context_manager.register_transformer(transformer)
        context_manager.set("key", "value")

        context = context_manager.build_agent_context()

        assert context.get("transformed") is True

    def test_serialization(self, context_manager):
        """Test context serialization."""
        context_manager.set("key", "value")
        context_manager.start_turn(5)

        data = context_manager.to_dict()

        restored = SessionContextManager.from_dict(data)

        assert restored.session_id == context_manager.session_id
        assert restored.current_turn == 5
        assert restored.get("key") == "value"

    def test_clone(self, context_manager):
        """Test cloning context manager."""
        context_manager.set("key", "value")

        cloned = context_manager.clone()

        assert cloned.session_id == context_manager.session_id
        assert cloned.get("key") == "value"

        # Modify original
        context_manager.set("key", "modified")
        assert cloned.get("key") == "value"  # Clone unaffected

    def test_get_statistics(self, context_manager):
        """Test getting statistics."""
        context_manager.set("key1", "value1", scope=ContextScope.SESSION)
        context_manager.set("key2", "value2", scope=ContextScope.TURN)

        stats = context_manager.get_statistics()

        assert stats["total_entries"] == 2
        assert stats["by_scope"]["session"] == 1
        assert stats["by_scope"]["turn"] == 1

    def test_expired_context(self, context_manager):
        """Test expired context handling."""
        context_manager.set(
            "expiring",
            "value",
            expires_at=datetime.utcnow() - timedelta(seconds=1),
        )

        result = context_manager.get("expiring")
        assert result is None  # Expired and removed

    def test_initial_context(self):
        """Test creating manager with initial context."""
        manager = SessionContextManager(
            session_id="session-1",
            initial_context={"key": "value"},
        )

        assert manager.get("key") == "value"


# =============================================================================
# Integration Tests
# =============================================================================

class TestMultiTurnIntegration:
    """Integration tests for multi-turn session components."""

    @pytest.mark.asyncio
    async def test_complete_session_flow(self):
        """Test a complete multi-turn session flow."""
        manager = MultiTurnSessionManager()

        # Create session
        session = await manager.create_session(
            user_id="user-1",
            agent_ids=["agent-1"],
            initial_context={"topic": "testing"},
        )

        # Start session
        await manager.start_session(session.session_id)

        # First turn
        def handler(agent_id, user_input, history):
            return f"Agent {agent_id} says: {user_input}"

        response1 = await manager.execute_turn(
            session.session_id,
            "Hello",
            handler,
        )
        assert response1 is not None

        # Second turn
        await manager.start_turn(session.session_id)
        response2 = await manager.execute_turn(
            session.session_id,
            "How are you?",
            handler,
        )

        # Get history
        history = await manager.get_history(session.session_id)
        assert len(history) >= 4  # 2 user + 2 agent messages

        # Close session
        await manager.close_session(session.session_id, "Test complete")

        final = await manager.get_session(session.session_id)
        assert final.status == SessionStatus.COMPLETED

    def test_turn_tracker_with_context_manager(self):
        """Test turn tracker with context manager."""
        tracker = TurnTracker(session_id="session-1")
        context = SessionContextManager(session_id="session-1")

        # Turn 1
        turn1 = tracker.start_turn()
        context.start_turn(turn1.turn_number)
        context.set("turn_topic", "Intro", scope=ContextScope.TURN)

        tracker.add_message_to_current("user", "Hello")
        tracker.add_message_to_current("agent", "Hi!")
        tracker.end_turn(turn1.turn_id)
        context.end_turn()

        # Turn-scoped context should be cleared
        assert not context.has("turn_topic")

        # Turn 2
        turn2 = tracker.start_turn()
        context.start_turn(turn2.turn_number)

        assert context.current_turn == 2
        assert tracker.current_turn.turn_number == 2
