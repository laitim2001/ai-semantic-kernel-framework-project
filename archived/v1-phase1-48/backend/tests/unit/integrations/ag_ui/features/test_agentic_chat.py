# =============================================================================
# IPA Platform - Agentic Chat Handler Tests
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-1: Agentic Chat Tests
#
# Unit tests for AgenticChatHandler, ChatMessage, ChatSession, and related
# components.
# =============================================================================

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from src.integrations.ag_ui.features.agentic_chat import (
    AgenticChatHandler,
    ChatConfig,
    ChatMessage,
    ChatRole,
    ChatSession,
    create_chat_handler,
)
from src.integrations.ag_ui.events import (
    AGUIEventType,
    TextMessageContentEvent,
    ToolCallEndEvent,
    RunStartedEvent,
    RunFinishedEvent,
)


# =============================================================================
# ChatRole Tests
# =============================================================================


class TestChatRole:
    """Tests for ChatRole enum."""

    def test_user_role_value(self):
        """Test USER role has correct value."""
        assert ChatRole.USER.value == "user"

    def test_assistant_role_value(self):
        """Test ASSISTANT role has correct value."""
        assert ChatRole.ASSISTANT.value == "assistant"

    def test_system_role_value(self):
        """Test SYSTEM role has correct value."""
        assert ChatRole.SYSTEM.value == "system"

    def test_tool_role_value(self):
        """Test TOOL role has correct value."""
        assert ChatRole.TOOL.value == "tool"

    def test_role_is_string_enum(self):
        """Test ChatRole is a string enum."""
        assert isinstance(ChatRole.USER, str)
        assert ChatRole.USER == "user"


# =============================================================================
# ChatMessage Tests
# =============================================================================


class TestChatMessage:
    """Tests for ChatMessage dataclass."""

    def test_create_message_with_required_fields(self):
        """Test creating message with only required fields."""
        msg = ChatMessage(role=ChatRole.USER, content="Hello")

        assert msg.role == ChatRole.USER
        assert msg.content == "Hello"
        assert msg.id.startswith("msg-")
        assert msg.timestamp > 0
        assert msg.tool_calls is None
        assert msg.tool_call_id is None
        assert msg.metadata == {}

    def test_create_message_with_all_fields(self):
        """Test creating message with all fields."""
        tool_calls = [{"id": "tc1", "name": "test_tool"}]
        metadata = {"source": "test"}

        msg = ChatMessage(
            role=ChatRole.ASSISTANT,
            content="Response",
            id="custom-id",
            timestamp=1234567890.0,
            tool_calls=tool_calls,
            tool_call_id="tc-ref",
            metadata=metadata,
        )

        assert msg.role == ChatRole.ASSISTANT
        assert msg.content == "Response"
        assert msg.id == "custom-id"
        assert msg.timestamp == 1234567890.0
        assert msg.tool_calls == tool_calls
        assert msg.tool_call_id == "tc-ref"
        assert msg.metadata == metadata

    def test_to_dict_basic(self):
        """Test to_dict with basic message."""
        msg = ChatMessage(
            role=ChatRole.USER,
            content="Test",
            id="msg-123",
            timestamp=1000.0,
        )

        result = msg.to_dict()

        assert result["role"] == "user"
        assert result["content"] == "Test"
        assert result["id"] == "msg-123"
        assert result["timestamp"] == 1000.0
        assert "tool_calls" not in result
        assert "tool_call_id" not in result
        assert "metadata" not in result

    def test_to_dict_with_tool_calls(self):
        """Test to_dict includes tool_calls when present."""
        tool_calls = [{"id": "tc1", "name": "tool"}]
        msg = ChatMessage(
            role=ChatRole.ASSISTANT,
            content="",
            tool_calls=tool_calls,
        )

        result = msg.to_dict()

        assert result["tool_calls"] == tool_calls

    def test_to_dict_with_metadata(self):
        """Test to_dict includes metadata when present."""
        metadata = {"key": "value"}
        msg = ChatMessage(
            role=ChatRole.USER,
            content="Test",
            metadata=metadata,
        )

        result = msg.to_dict()

        assert result["metadata"] == metadata

    def test_from_dict_basic(self):
        """Test from_dict creates message from dict."""
        data = {
            "role": "assistant",
            "content": "Hello",
            "id": "msg-456",
            "timestamp": 2000.0,
        }

        msg = ChatMessage.from_dict(data)

        assert msg.role == ChatRole.ASSISTANT
        assert msg.content == "Hello"
        assert msg.id == "msg-456"
        assert msg.timestamp == 2000.0

    def test_from_dict_with_tool_calls(self):
        """Test from_dict preserves tool_calls."""
        data = {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "tc1"}],
        }

        msg = ChatMessage.from_dict(data)

        assert msg.tool_calls == [{"id": "tc1"}]

    def test_from_dict_defaults(self):
        """Test from_dict uses defaults for missing fields."""
        data = {}

        msg = ChatMessage.from_dict(data)

        assert msg.role == ChatRole.USER
        assert msg.content == ""
        assert msg.id.startswith("msg-")


# =============================================================================
# ChatConfig Tests
# =============================================================================


class TestChatConfig:
    """Tests for ChatConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ChatConfig()

        assert config.max_history_length == 50
        assert config.enable_intent_analysis is True
        assert config.enable_tool_calls is True
        assert config.default_timeout == 300.0
        assert config.stream_chunk_size == 100

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ChatConfig(
            max_history_length=100,
            enable_intent_analysis=False,
            enable_tool_calls=False,
            default_timeout=60.0,
            stream_chunk_size=50,
        )

        assert config.max_history_length == 100
        assert config.enable_intent_analysis is False
        assert config.enable_tool_calls is False
        assert config.default_timeout == 60.0
        assert config.stream_chunk_size == 50


# =============================================================================
# ChatSession Tests
# =============================================================================


class TestChatSession:
    """Tests for ChatSession dataclass."""

    def test_create_session(self):
        """Test creating a chat session."""
        session = ChatSession(
            session_id="sess-123",
            thread_id="thread-456",
        )

        assert session.session_id == "sess-123"
        assert session.thread_id == "thread-456"
        assert session.messages == []
        assert session.metadata == {}
        assert session.created_at > 0
        assert session.last_activity > 0

    def test_session_with_messages(self):
        """Test session with pre-populated messages."""
        messages = [
            ChatMessage(role=ChatRole.USER, content="Hi"),
            ChatMessage(role=ChatRole.ASSISTANT, content="Hello"),
        ]

        session = ChatSession(
            session_id="sess-123",
            thread_id="thread-456",
            messages=messages,
        )

        assert len(session.messages) == 2
        assert session.messages[0].content == "Hi"


# =============================================================================
# AgenticChatHandler Tests
# =============================================================================


class TestAgenticChatHandler:
    """Tests for AgenticChatHandler class."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock HybridOrchestratorV2."""
        return MagicMock()

    @pytest.fixture
    def mock_event_bridge(self):
        """Create mock HybridEventBridge."""
        bridge = MagicMock()
        bridge.stream_events_raw = AsyncMock()
        return bridge

    @pytest.fixture
    def handler(self, mock_orchestrator, mock_event_bridge):
        """Create AgenticChatHandler instance."""
        return AgenticChatHandler(
            orchestrator=mock_orchestrator,
            event_bridge=mock_event_bridge,
        )

    def test_init_with_defaults(self, mock_orchestrator, mock_event_bridge):
        """Test handler initialization with defaults."""
        handler = AgenticChatHandler(
            orchestrator=mock_orchestrator,
            event_bridge=mock_event_bridge,
        )

        assert handler.orchestrator is mock_orchestrator
        assert handler.event_bridge is mock_event_bridge
        assert handler.config.max_history_length == 50

    def test_init_with_custom_config(self, mock_orchestrator, mock_event_bridge):
        """Test handler initialization with custom config."""
        config = ChatConfig(max_history_length=100)

        handler = AgenticChatHandler(
            orchestrator=mock_orchestrator,
            event_bridge=mock_event_bridge,
            config=config,
        )

        assert handler.config.max_history_length == 100

    def test_create_session(self, handler):
        """Test creating a new session."""
        session = handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
            metadata={"key": "value"},
        )

        assert session.session_id == "sess-456"
        assert session.thread_id == "thread-123"
        assert session.metadata == {"key": "value"}

    def test_create_session_auto_id(self, handler):
        """Test creating session with auto-generated ID."""
        session = handler.create_session(thread_id="thread-123")

        assert session.session_id is not None
        assert len(session.session_id) > 0

    def test_get_session(self, handler):
        """Test getting an existing session."""
        handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        session = handler.get_session("sess-456")

        assert session is not None
        assert session.session_id == "sess-456"

    def test_get_session_not_found(self, handler):
        """Test getting a non-existent session."""
        session = handler.get_session("nonexistent")

        assert session is None

    def test_get_or_create_session_existing(self, handler):
        """Test get_or_create returns existing session."""
        original = handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        session = handler.get_or_create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        assert session is original

    def test_get_or_create_session_new(self, handler):
        """Test get_or_create creates new session if not found."""
        session = handler.get_or_create_session(
            thread_id="thread-123",
            session_id="sess-new",
        )

        assert session.session_id == "sess-new"
        assert session.thread_id == "thread-123"

    def test_close_session(self, handler):
        """Test closing a session."""
        handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        result = handler.close_session("sess-456")

        assert result is True
        assert handler.get_session("sess-456") is None

    def test_close_session_not_found(self, handler):
        """Test closing non-existent session."""
        result = handler.close_session("nonexistent")

        assert result is False

    def test_add_message(self, handler):
        """Test adding message to session."""
        handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        msg = ChatMessage(role=ChatRole.USER, content="Hello")
        result = handler.add_message("sess-456", msg)

        assert result is True
        session = handler.get_session("sess-456")
        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello"

    def test_add_message_session_not_found(self, handler):
        """Test adding message to non-existent session."""
        msg = ChatMessage(role=ChatRole.USER, content="Hello")
        result = handler.add_message("nonexistent", msg)

        assert result is False

    def test_add_message_trims_history(self, handler):
        """Test that history is trimmed when exceeding max length."""
        config = ChatConfig(max_history_length=3)
        handler = AgenticChatHandler(
            orchestrator=handler.orchestrator,
            event_bridge=handler.event_bridge,
            config=config,
        )
        handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        # Add 5 messages
        for i in range(5):
            msg = ChatMessage(role=ChatRole.USER, content=f"Message {i}")
            handler.add_message("sess-456", msg)

        session = handler.get_session("sess-456")
        assert len(session.messages) == 3
        assert session.messages[0].content == "Message 2"
        assert session.messages[2].content == "Message 4"

    @pytest.mark.asyncio
    async def test_handle_chat_basic(self, handler, mock_event_bridge):
        """Test basic chat handling."""
        # Setup mock events
        async def mock_stream(*args, **kwargs):
            yield RunStartedEvent(
                type=AGUIEventType.RUN_STARTED,
                thread_id="thread-123",
                run_id="run-456",
            )
            yield TextMessageContentEvent(
                type=AGUIEventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-001",
                delta="Hello ",
            )
            yield TextMessageContentEvent(
                type=AGUIEventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-002",
                delta="world!",
            )
            yield RunFinishedEvent(
                type=AGUIEventType.RUN_FINISHED,
                thread_id="thread-123",
                run_id="run-456",
            )

        mock_event_bridge.stream_events_raw = mock_stream

        events = []
        async for event in handler.handle_chat(
            thread_id="thread-123",
            message="Hello",
        ):
            events.append(event)

        assert len(events) == 4
        assert events[0].type == AGUIEventType.RUN_STARTED
        assert events[1].delta == "Hello "
        assert events[2].delta == "world!"
        assert events[3].type == AGUIEventType.RUN_FINISHED

    @pytest.mark.asyncio
    async def test_handle_chat_stores_assistant_response(self, handler, mock_event_bridge):
        """Test that assistant response is stored in session."""
        async def mock_stream(*args, **kwargs):
            yield TextMessageContentEvent(
                type=AGUIEventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-resp",
                delta="Response text",
            )

        mock_event_bridge.stream_events_raw = mock_stream

        async for _ in handler.handle_chat(
            thread_id="thread-123",
            message="Hello",
            session_id="sess-456",
        ):
            pass

        session = handler.get_session("sess-456")
        assert len(session.messages) == 2  # User + Assistant
        assert session.messages[0].role == ChatRole.USER
        assert session.messages[1].role == ChatRole.ASSISTANT
        assert session.messages[1].content == "Response text"

    @pytest.mark.asyncio
    async def test_handle_chat_sse(self, handler, mock_event_bridge):
        """Test SSE-formatted chat handling."""
        async def mock_stream(*args, **kwargs):
            event = RunStartedEvent(
                type=AGUIEventType.RUN_STARTED,
                thread_id="thread-123",
                run_id="run-456",
            )
            yield event

        mock_event_bridge.stream_events_raw = mock_stream

        sse_events = []
        async for sse in handler.handle_chat_sse(
            thread_id="thread-123",
            message="Hello",
        ):
            sse_events.append(sse)

        assert len(sse_events) == 1
        assert sse_events[0].startswith("data: ")
        assert sse_events[0].endswith("\n\n")

    def test_get_conversation_history(self, handler):
        """Test getting conversation history."""
        handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        # Add messages
        handler.add_message("sess-456", ChatMessage(role=ChatRole.USER, content="Hi"))
        handler.add_message("sess-456", ChatMessage(role=ChatRole.ASSISTANT, content="Hello"))
        handler.add_message("sess-456", ChatMessage(role=ChatRole.USER, content="How are you?"))

        history = handler.get_conversation_history("sess-456")

        assert len(history) == 3
        assert history[0]["content"] == "Hi"
        assert history[1]["content"] == "Hello"
        assert history[2]["content"] == "How are you?"

    def test_get_conversation_history_with_limit(self, handler):
        """Test getting limited conversation history."""
        handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        # Add 5 messages
        for i in range(5):
            handler.add_message(
                "sess-456",
                ChatMessage(role=ChatRole.USER, content=f"Message {i}"),
            )

        history = handler.get_conversation_history("sess-456", limit=2)

        assert len(history) == 2
        assert history[0]["content"] == "Message 3"
        assert history[1]["content"] == "Message 4"

    def test_get_conversation_history_excludes_system(self, handler):
        """Test that system messages are excluded by default."""
        handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        handler.add_message("sess-456", ChatMessage(role=ChatRole.SYSTEM, content="System"))
        handler.add_message("sess-456", ChatMessage(role=ChatRole.USER, content="User"))

        history = handler.get_conversation_history("sess-456")

        assert len(history) == 1
        assert history[0]["content"] == "User"

    def test_get_conversation_history_includes_system(self, handler):
        """Test including system messages when requested."""
        handler.create_session(
            thread_id="thread-123",
            session_id="sess-456",
        )

        handler.add_message("sess-456", ChatMessage(role=ChatRole.SYSTEM, content="System"))
        handler.add_message("sess-456", ChatMessage(role=ChatRole.USER, content="User"))

        history = handler.get_conversation_history("sess-456", include_system=True)

        assert len(history) == 2
        assert history[0]["content"] == "System"

    def test_get_conversation_history_session_not_found(self, handler):
        """Test getting history for non-existent session."""
        history = handler.get_conversation_history("nonexistent")

        assert history == []

    @pytest.mark.asyncio
    async def test_emit_typing_indicator(self, handler):
        """Test emitting typing indicator event."""
        event = await handler.emit_typing_indicator(
            thread_id="thread-123",
            run_id="run-456",
            is_typing=True,
        )

        assert event.type == AGUIEventType.CUSTOM
        assert event.event_name == "typing_indicator"
        assert event.payload["thread_id"] == "thread-123"
        assert event.payload["run_id"] == "run-456"
        assert event.payload["is_typing"] is True


# =============================================================================
# create_chat_handler Tests
# =============================================================================


class TestCreateChatHandler:
    """Tests for create_chat_handler factory function."""

    def test_create_with_provided_bridge(self):
        """Test creating handler with provided event bridge."""
        orchestrator = MagicMock()
        bridge = MagicMock()

        handler = create_chat_handler(
            orchestrator=orchestrator,
            event_bridge=bridge,
        )

        assert handler.orchestrator is orchestrator
        assert handler.event_bridge is bridge

    def test_create_with_custom_config(self):
        """Test creating handler with custom config."""
        orchestrator = MagicMock()
        bridge = MagicMock()
        config = ChatConfig(max_history_length=100)

        handler = create_chat_handler(
            orchestrator=orchestrator,
            event_bridge=bridge,
            config=config,
        )

        assert handler.config.max_history_length == 100

    @patch("src.integrations.ag_ui.bridge.create_bridge")
    def test_create_without_bridge(self, mock_create_bridge):
        """Test creating handler creates bridge if not provided."""
        orchestrator = MagicMock()
        mock_bridge = MagicMock()
        mock_create_bridge.return_value = mock_bridge

        handler = create_chat_handler(orchestrator=orchestrator)

        mock_create_bridge.assert_called_once_with(orchestrator=orchestrator)
        assert handler.event_bridge is mock_bridge
