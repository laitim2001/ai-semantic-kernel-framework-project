# =============================================================================
# IPA Platform - Conversation Memory Store Tests
# =============================================================================
# Sprint 9: S9-4 ConversationMemoryStore (8 points)
#
# Comprehensive tests for conversation memory storage implementations.
# =============================================================================

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.orchestration.memory.models import (
    ConversationSession,
    ConversationTurn,
    MessageRecord,
    SessionStatus,
)
from src.domain.orchestration.memory.in_memory import InMemoryConversationMemoryStore


# =============================================================================
# MessageRecord Tests
# =============================================================================


class TestMessageRecord:
    """Tests for MessageRecord dataclass."""

    def test_create_message(self):
        """Test creating a message record."""
        message = MessageRecord(
            sender_id="user-1",
            sender_name="Alice",
            content="Hello",
            message_type="text",
        )

        assert message.sender_id == "user-1"
        assert message.sender_name == "Alice"
        assert message.content == "Hello"
        assert message.message_type == "text"
        assert message.message_id is not None

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = MessageRecord(
            sender_id="user-1",
            content="Test message",
        )

        data = message.to_dict()

        assert data["sender_id"] == "user-1"
        assert data["content"] == "Test message"
        assert "message_id" in data
        assert "timestamp" in data

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "message_id": str(uuid4()),
            "sender_id": "user-1",
            "sender_name": "Alice",
            "content": "Hello",
            "message_type": "text",
            "timestamp": datetime.utcnow().isoformat(),
        }

        message = MessageRecord.from_dict(data)

        assert message.sender_id == "user-1"
        assert message.content == "Hello"

    def test_message_with_reply(self):
        """Test message with reply_to reference."""
        parent_id = uuid4()
        message = MessageRecord(
            sender_id="user-1",
            content="Reply",
            reply_to=parent_id,
        )

        assert message.reply_to == parent_id


# =============================================================================
# ConversationTurn Tests
# =============================================================================


class TestConversationTurn:
    """Tests for ConversationTurn dataclass."""

    def test_create_turn(self):
        """Test creating a conversation turn."""
        turn = ConversationTurn(
            turn_number=1,
            user_input="What is the weather?",
            agent_response="It's sunny today.",
            agent_id="weather-agent",
        )

        assert turn.turn_number == 1
        assert turn.user_input == "What is the weather?"
        assert turn.agent_response == "It's sunny today."
        assert turn.agent_id == "weather-agent"

    def test_turn_to_dict(self):
        """Test converting turn to dictionary."""
        turn = ConversationTurn(
            turn_number=1,
            user_input="Hello",
            agent_response="Hi!",
            processing_time_ms=100,
        )

        data = turn.to_dict()

        assert data["turn_number"] == 1
        assert data["user_input"] == "Hello"
        assert data["agent_response"] == "Hi!"
        assert data["processing_time_ms"] == 100

    def test_turn_from_dict(self):
        """Test creating turn from dictionary."""
        data = {
            "turn_id": str(uuid4()),
            "turn_number": 2,
            "user_input": "How are you?",
            "agent_response": "I'm doing well!",
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": 150,
            "tokens_used": 50,
        }

        turn = ConversationTurn.from_dict(data)

        assert turn.turn_number == 2
        assert turn.user_input == "How are you?"
        assert turn.processing_time_ms == 150

    def test_turn_with_metadata(self):
        """Test turn with metadata."""
        turn = ConversationTurn(
            user_input="Test",
            agent_response="Response",
            metadata={"confidence": 0.95, "model": "gpt-4"},
        )

        assert turn.metadata["confidence"] == 0.95
        assert turn.metadata["model"] == "gpt-4"


# =============================================================================
# ConversationSession Tests
# =============================================================================


class TestConversationSession:
    """Tests for ConversationSession dataclass."""

    def test_create_session(self):
        """Test creating a conversation session."""
        session = ConversationSession(
            user_id="user-123",
            status=SessionStatus.ACTIVE,
        )

        assert session.user_id == "user-123"
        assert session.status == SessionStatus.ACTIVE
        assert session.turn_count == 0

    def test_session_properties(self):
        """Test session properties."""
        session = ConversationSession(user_id="user-1")

        assert session.is_expired is False
        assert session.duration_seconds >= 0

    def test_session_with_expiration(self):
        """Test session expiration."""
        # Not expired
        session = ConversationSession(
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        assert session.is_expired is False

        # Expired
        expired_session = ConversationSession(
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert expired_session.is_expired is True

    def test_add_turn(self):
        """Test adding turn to session."""
        session = ConversationSession(user_id="user-1")

        turn = ConversationTurn(
            user_input="Hello",
            agent_response="Hi!",
        )
        session.add_turn(turn)

        assert session.turn_count == 1
        assert turn.turn_number == 1

    def test_get_last_turn(self):
        """Test getting last turn."""
        session = ConversationSession()

        # No turns
        assert session.get_last_turn() is None

        # Add turn
        turn = ConversationTurn(user_input="Test", agent_response="Response")
        session.add_turn(turn)

        last = session.get_last_turn()
        assert last == turn

    def test_get_turn_by_number(self):
        """Test getting turn by number."""
        session = ConversationSession()

        turn1 = ConversationTurn(user_input="First", agent_response="R1")
        turn2 = ConversationTurn(user_input="Second", agent_response="R2")
        session.add_turn(turn1)
        session.add_turn(turn2)

        found = session.get_turn_by_number(1)
        assert found.user_input == "First"

        not_found = session.get_turn_by_number(99)
        assert not_found is None

    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        session = ConversationSession(
            user_id="user-1",
            context={"key": "value"},
        )

        data = session.to_dict()

        assert data["user_id"] == "user-1"
        assert data["context"]["key"] == "value"
        assert data["turn_count"] == 0

    def test_session_from_dict(self):
        """Test creating session from dictionary."""
        data = {
            "session_id": str(uuid4()),
            "user_id": "user-1",
            "status": "active",
            "turns": [
                {
                    "turn_id": str(uuid4()),
                    "turn_number": 1,
                    "user_input": "Hello",
                    "agent_response": "Hi",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
            "context": {"topic": "greetings"},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        session = ConversationSession.from_dict(data)

        assert session.user_id == "user-1"
        assert session.status == SessionStatus.ACTIVE
        assert session.turn_count == 1

    def test_session_summary(self):
        """Test getting session summary."""
        session = ConversationSession(user_id="user-1")

        turn = ConversationTurn(
            user_input="Hello world",
            agent_response="Hi there, how can I help?",
            processing_time_ms=100,
            tokens_used=25,
        )
        session.add_turn(turn)

        summary = session.get_summary()

        assert summary["user_id"] == "user-1"
        assert summary["turn_count"] == 1
        assert summary["total_user_words"] == 2  # "Hello" "world"
        assert summary["avg_response_time_ms"] == 100


# =============================================================================
# InMemoryConversationMemoryStore Tests
# =============================================================================


class TestInMemoryConversationMemoryStore:
    """Tests for InMemoryConversationMemoryStore."""

    @pytest.fixture
    def store(self):
        """Create a new store for each test."""
        return InMemoryConversationMemoryStore()

    # -------------------------------------------------------------------------
    # Message Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_add_message(self, store):
        """Test adding a message."""
        group_id = uuid4()
        message = MessageRecord(
            group_id=group_id,
            sender_id="user-1",
            content="Test message",
        )

        await store.add_message(message)

        count = await store.get_message_count(group_id)
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_messages(self, store):
        """Test getting messages."""
        group_id = uuid4()

        for i in range(5):
            message = MessageRecord(
                group_id=group_id,
                sender_id=f"user-{i}",
                content=f"Message {i}",
            )
            await store.add_message(message)

        messages = await store.get_messages(group_id, limit=3)
        assert len(messages) == 3

        all_messages = await store.get_messages(group_id)
        assert len(all_messages) == 5

    @pytest.mark.asyncio
    async def test_get_messages_with_offset(self, store):
        """Test getting messages with offset."""
        group_id = uuid4()

        for i in range(10):
            await store.add_message(MessageRecord(
                group_id=group_id,
                content=f"Message {i}",
            ))

        messages = await store.get_messages(group_id, limit=3, offset=5)
        assert len(messages) == 3

    @pytest.mark.asyncio
    async def test_delete_messages(self, store):
        """Test deleting messages."""
        group_id = uuid4()

        for i in range(3):
            await store.add_message(MessageRecord(
                group_id=group_id,
                content=f"Message {i}",
            ))

        count = await store.delete_messages(group_id)
        assert count == 3

        remaining = await store.get_message_count(group_id)
        assert remaining == 0

    # -------------------------------------------------------------------------
    # Session Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_save_session(self, store):
        """Test saving a session."""
        session = ConversationSession(
            user_id="user-1",
            status=SessionStatus.ACTIVE,
        )

        await store.save_session(session)

        loaded = await store.load_session(session.session_id)
        assert loaded is not None
        assert loaded.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, store):
        """Test loading non-existent session."""
        session = await store.load_session(uuid4())
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_session(self, store):
        """Test deleting a session."""
        session = ConversationSession(user_id="user-1")
        await store.save_session(session)

        result = await store.delete_session(session.session_id)
        assert result is True

        loaded = await store.load_session(session.session_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, store):
        """Test deleting non-existent session."""
        result = await store.delete_session(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_list_sessions(self, store):
        """Test listing sessions."""
        for i in range(5):
            await store.save_session(ConversationSession(
                user_id=f"user-{i % 2}",  # Alternate between user-0 and user-1
            ))

        all_sessions = await store.list_sessions()
        assert len(all_sessions) == 5

        user_sessions = await store.list_sessions(user_id="user-0")
        assert len(user_sessions) == 3  # 0, 2, 4

    @pytest.mark.asyncio
    async def test_list_sessions_by_status(self, store):
        """Test listing sessions by status."""
        session1 = ConversationSession(status=SessionStatus.ACTIVE)
        session2 = ConversationSession(status=SessionStatus.COMPLETED)
        session3 = ConversationSession(status=SessionStatus.ACTIVE)

        await store.save_session(session1)
        await store.save_session(session2)
        await store.save_session(session3)

        active = await store.list_sessions(status=SessionStatus.ACTIVE)
        assert len(active) == 2

        completed = await store.list_sessions(status=SessionStatus.COMPLETED)
        assert len(completed) == 1

    @pytest.mark.asyncio
    async def test_list_sessions_pagination(self, store):
        """Test listing sessions with pagination."""
        for i in range(10):
            await store.save_session(ConversationSession(user_id=f"user-{i}"))

        page1 = await store.list_sessions(limit=3, offset=0)
        page2 = await store.list_sessions(limit=3, offset=3)

        assert len(page1) == 3
        assert len(page2) == 3

    @pytest.mark.asyncio
    async def test_update_session_status(self, store):
        """Test updating session status."""
        session = ConversationSession(status=SessionStatus.ACTIVE)
        await store.save_session(session)

        result = await store.update_session_status(
            session.session_id,
            SessionStatus.COMPLETED,
        )
        assert result is True

        loaded = await store.load_session(session.session_id)
        assert loaded.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_nonexistent_session_status(self, store):
        """Test updating non-existent session status."""
        result = await store.update_session_status(
            uuid4(),
            SessionStatus.COMPLETED,
        )
        assert result is False

    # -------------------------------------------------------------------------
    # Turn Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_save_turn(self, store):
        """Test saving a turn."""
        session = ConversationSession(user_id="user-1")
        await store.save_session(session)

        turn = ConversationTurn(
            user_input="Hello",
            agent_response="Hi there!",
        )
        await store.save_turn(session.session_id, turn)

        turns = await store.get_turns(session.session_id)
        assert len(turns) == 1
        assert turns[0].turn_number == 1

    @pytest.mark.asyncio
    async def test_save_multiple_turns(self, store):
        """Test saving multiple turns."""
        session = ConversationSession()
        await store.save_session(session)

        for i in range(3):
            await store.save_turn(session.session_id, ConversationTurn(
                user_input=f"Question {i}",
                agent_response=f"Answer {i}",
            ))

        turns = await store.get_turns(session.session_id)
        assert len(turns) == 3
        assert [t.turn_number for t in turns] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_get_turns_with_limit(self, store):
        """Test getting turns with limit."""
        session = ConversationSession()
        await store.save_session(session)

        for i in range(10):
            await store.save_turn(session.session_id, ConversationTurn(
                user_input=f"Q{i}",
                agent_response=f"A{i}",
            ))

        recent = await store.get_turns(session.session_id, limit=3)
        assert len(recent) == 3
        # Should be the last 3 turns
        assert recent[0].turn_number == 8
        assert recent[-1].turn_number == 10

    @pytest.mark.asyncio
    async def test_get_specific_turn(self, store):
        """Test getting a specific turn."""
        session = ConversationSession()
        await store.save_session(session)

        for i in range(3):
            await store.save_turn(session.session_id, ConversationTurn(
                user_input=f"Q{i}",
                agent_response=f"A{i}",
            ))

        turn = await store.get_turn(session.session_id, 2)
        assert turn is not None
        assert turn.user_input == "Q1"

        not_found = await store.get_turn(session.session_id, 99)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_load_session_with_turns(self, store):
        """Test loading session includes turns."""
        session = ConversationSession(user_id="user-1")
        await store.save_session(session)

        await store.save_turn(session.session_id, ConversationTurn(
            user_input="Hello",
            agent_response="Hi!",
        ))

        loaded = await store.load_session(session.session_id)
        assert loaded.turn_count == 1

    # -------------------------------------------------------------------------
    # Search Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_search_by_content(self, store):
        """Test searching by content."""
        session = ConversationSession()
        await store.save_session(session)

        await store.save_turn(session.session_id, ConversationTurn(
            user_input="What is Python?",
            agent_response="Python is a programming language.",
        ))
        await store.save_turn(session.session_id, ConversationTurn(
            user_input="What about Java?",
            agent_response="Java is another programming language.",
        ))

        results = await store.search_by_content("Python")
        assert len(results) == 1
        assert "Python" in results[0]["user_input"]

        results = await store.search_by_content("programming")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_limit(self, store):
        """Test search with limit."""
        session = ConversationSession()
        await store.save_session(session)

        for i in range(20):
            await store.save_turn(session.session_id, ConversationTurn(
                user_input=f"Question about test {i}",
                agent_response=f"Answer about test {i}",
            ))

        results = await store.search_by_content("test", limit=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, store):
        """Test case-insensitive search."""
        session = ConversationSession()
        await store.save_session(session)

        await store.save_turn(session.session_id, ConversationTurn(
            user_input="HELLO World",
            agent_response="Hi!",
        ))

        results = await store.search_by_content("hello")
        assert len(results) == 1

        results = await store.search_by_content("WORLD")
        assert len(results) == 1

    # -------------------------------------------------------------------------
    # Statistics Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_session_summary(self, store):
        """Test getting session summary."""
        session = ConversationSession(user_id="user-1")
        await store.save_session(session)

        await store.save_turn(session.session_id, ConversationTurn(
            user_input="Hello there",
            agent_response="Hi how are you",
            processing_time_ms=100,
        ))

        summary = await store.get_session_summary(session.session_id)

        assert summary["user_id"] == "user-1"
        assert summary["turn_count"] == 1

    @pytest.mark.asyncio
    async def test_get_statistics(self, store):
        """Test getting overall statistics."""
        # Create sessions
        s1 = ConversationSession(status=SessionStatus.ACTIVE)
        s2 = ConversationSession(status=SessionStatus.COMPLETED)
        await store.save_session(s1)
        await store.save_session(s2)

        # Add turns
        await store.save_turn(s1.session_id, ConversationTurn(
            user_input="Q1",
            agent_response="A1",
        ))

        stats = await store.get_statistics()

        assert stats["total_sessions"] == 2
        assert stats["total_turns"] == 1
        assert "sessions_by_status" in stats

    # -------------------------------------------------------------------------
    # Cleanup Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, store):
        """Test cleaning up expired sessions."""
        # Active session
        active = ConversationSession(
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        await store.save_session(active)

        # Expired session
        expired = ConversationSession(
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        await store.save_session(expired)

        count = await store.cleanup_expired_sessions()
        assert count == 1

        sessions = await store.list_sessions()
        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_archive_session(self, store):
        """Test archiving a session."""
        session = ConversationSession(status=SessionStatus.ACTIVE)
        await store.save_session(session)

        result = await store.archive_session(session.session_id)
        assert result is True

        loaded = await store.load_session(session.session_id)
        assert loaded.status == SessionStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_archive_nonexistent_session(self, store):
        """Test archiving non-existent session."""
        result = await store.archive_session(uuid4())
        assert result is False

    # -------------------------------------------------------------------------
    # Context Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_update_session_context(self, store):
        """Test updating session context."""
        session = ConversationSession(context={"key1": "value1"})
        await store.save_session(session)

        result = await store.update_session_context(
            session.session_id,
            {"key2": "value2"},
        )
        assert result is True

        context = await store.get_session_context(session.session_id)
        assert context["key1"] == "value1"
        assert context["key2"] == "value2"

    @pytest.mark.asyncio
    async def test_get_nonexistent_context(self, store):
        """Test getting context for non-existent session."""
        context = await store.get_session_context(uuid4())
        assert context is None

    # -------------------------------------------------------------------------
    # Utility Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_session_exists(self, store):
        """Test checking if session exists."""
        session = ConversationSession()
        await store.save_session(session)

        exists = await store.session_exists(session.session_id)
        assert exists is True

        not_exists = await store.session_exists(uuid4())
        assert not_exists is False

    @pytest.mark.asyncio
    async def test_get_latest_sessions(self, store):
        """Test getting latest sessions."""
        for i in range(5):
            session = ConversationSession(user_id=f"user-{i}")
            await store.save_session(session)

        latest = await store.get_latest_sessions(limit=3)
        assert len(latest) == 3

    @pytest.mark.asyncio
    async def test_clear_store(self, store):
        """Test clearing the store."""
        await store.save_session(ConversationSession())
        await store.save_session(ConversationSession())

        store.clear()

        assert store.get_session_count() == 0
        assert store.get_total_turn_count() == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestConversationMemoryIntegration:
    """Integration tests for conversation memory."""

    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self):
        """Test a complete conversation flow."""
        store = InMemoryConversationMemoryStore()

        # Create session
        session = ConversationSession(
            user_id="user-123",
            context={"topic": "support"},
        )
        await store.save_session(session)

        # Simulate conversation
        turns_data = [
            ("Hello, I need help", "Hi! How can I assist you today?"),
            ("I have a billing question", "Sure, I can help with billing. What's your question?"),
            ("Why was I charged twice?", "Let me look into that for you..."),
        ]

        for user_input, agent_response in turns_data:
            turn = ConversationTurn(
                user_input=user_input,
                agent_response=agent_response,
                processing_time_ms=150,
            )
            await store.save_turn(session.session_id, turn)

        # Verify conversation
        loaded = await store.load_session(session.session_id)
        assert loaded.turn_count == 3
        assert loaded.context["topic"] == "support"

        # Search conversation
        results = await store.search_by_content("billing")
        assert len(results) >= 1

        # Get summary
        summary = await store.get_session_summary(session.session_id)
        assert summary["turn_count"] == 3

        # Complete session
        await store.update_session_status(session.session_id, SessionStatus.COMPLETED)

        final = await store.load_session(session.session_id)
        assert final.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_multiple_users_multiple_sessions(self):
        """Test multiple users with multiple sessions."""
        store = InMemoryConversationMemoryStore()

        users = ["alice", "bob", "charlie"]

        # Create sessions for each user
        for user in users:
            for i in range(2):
                session = ConversationSession(
                    user_id=user,
                    context={"session_num": i},
                )
                await store.save_session(session)

                # Add a turn
                await store.save_turn(session.session_id, ConversationTurn(
                    user_input=f"Hello from {user}",
                    agent_response="Hello!",
                ))

        # Verify
        stats = await store.get_statistics()
        assert stats["total_sessions"] == 6
        assert stats["total_turns"] == 6

        # Check user filtering
        alice_sessions = await store.list_sessions(user_id="alice")
        assert len(alice_sessions) == 2

    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        store = InMemoryConversationMemoryStore()

        # Create
        session = ConversationSession(
            user_id="user-1",
            status=SessionStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        await store.save_session(session)
        assert session.status == SessionStatus.ACTIVE

        # Pause
        await store.update_session_status(session.session_id, SessionStatus.PAUSED)
        loaded = await store.load_session(session.session_id)
        assert loaded.status == SessionStatus.PAUSED

        # Resume
        await store.update_session_status(session.session_id, SessionStatus.ACTIVE)
        loaded = await store.load_session(session.session_id)
        assert loaded.status == SessionStatus.ACTIVE

        # Complete
        await store.update_session_status(session.session_id, SessionStatus.COMPLETED)
        loaded = await store.load_session(session.session_id)
        assert loaded.status == SessionStatus.COMPLETED

        # Archive
        await store.archive_session(session.session_id)
        loaded = await store.load_session(session.session_id)
        assert loaded.status == SessionStatus.ARCHIVED
