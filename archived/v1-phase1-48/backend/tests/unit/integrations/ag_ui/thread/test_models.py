# =============================================================================
# IPA Platform - AG-UI Thread Models Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-3: Thread Manager
#
# Unit tests for AG-UI Thread data models.
# =============================================================================

from datetime import datetime, timedelta

import pytest

from src.integrations.ag_ui.thread.models import (
    AGUIMessage,
    AGUIMessageSchema,
    AGUIThread,
    AGUIThreadSchema,
    MessageRole,
    ThreadStatus,
)


class TestThreadStatus:
    """Tests for ThreadStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ThreadStatus.ACTIVE == "active"
        assert ThreadStatus.IDLE == "idle"
        assert ThreadStatus.ARCHIVED == "archived"
        assert ThreadStatus.DELETED == "deleted"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert ThreadStatus("active") == ThreadStatus.ACTIVE
        assert ThreadStatus("archived") == ThreadStatus.ARCHIVED


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_role_values(self):
        """Test role enum values."""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.TOOL == "tool"

    def test_role_from_string(self):
        """Test creating role from string."""
        assert MessageRole("user") == MessageRole.USER
        assert MessageRole("assistant") == MessageRole.ASSISTANT


class TestAGUIMessage:
    """Tests for AGUIMessage dataclass."""

    def test_create_message(self):
        """Test creating a message."""
        message = AGUIMessage(
            message_id="msg-123",
            role=MessageRole.USER,
            content="Hello, world!",
        )
        assert message.message_id == "msg-123"
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert isinstance(message.created_at, datetime)
        assert message.metadata == {}
        assert message.tool_calls == []
        assert message.tool_call_id is None

    def test_create_message_with_metadata(self):
        """Test creating a message with metadata."""
        message = AGUIMessage(
            message_id="msg-123",
            role=MessageRole.ASSISTANT,
            content="Response",
            metadata={"tokens": 50, "model": "gpt-4"},
        )
        assert message.metadata["tokens"] == 50
        assert message.metadata["model"] == "gpt-4"

    def test_create_tool_message(self):
        """Test creating a tool response message."""
        message = AGUIMessage(
            message_id="msg-456",
            role=MessageRole.TOOL,
            content='{"result": "success"}',
            tool_call_id="call-789",
        )
        assert message.role == MessageRole.TOOL
        assert message.tool_call_id == "call-789"

    def test_create_message_with_tool_calls(self):
        """Test creating a message with tool calls."""
        tool_calls = [
            {"id": "call-1", "name": "search", "args": '{"query": "test"}'},
            {"id": "call-2", "name": "calculate", "args": '{"expr": "2+2"}'},
        ]
        message = AGUIMessage(
            message_id="msg-789",
            role=MessageRole.ASSISTANT,
            content="Let me help with that.",
            tool_calls=tool_calls,
        )
        assert len(message.tool_calls) == 2
        assert message.tool_calls[0]["name"] == "search"

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = AGUIMessage(
            message_id="msg-123",
            role=MessageRole.USER,
            content="Test content",
            metadata={"key": "value"},
        )
        d = message.to_dict()

        assert d["message_id"] == "msg-123"
        assert d["role"] == "user"
        assert d["content"] == "Test content"
        assert d["metadata"] == {"key": "value"}
        assert "created_at" in d

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "message_id": "msg-123",
            "role": "assistant",
            "content": "Hello!",
            "created_at": "2026-01-05T10:00:00",
            "metadata": {"source": "test"},
        }
        message = AGUIMessage.from_dict(data)

        assert message.message_id == "msg-123"
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Hello!"
        assert message.metadata["source"] == "test"

    def test_message_from_dict_minimal(self):
        """Test creating message from minimal dictionary."""
        data = {
            "message_id": "msg-min",
            "role": "user",
        }
        message = AGUIMessage.from_dict(data)

        assert message.message_id == "msg-min"
        assert message.content == ""
        assert message.metadata == {}


class TestAGUIThread:
    """Tests for AGUIThread dataclass."""

    def test_create_thread(self):
        """Test creating a thread."""
        thread = AGUIThread(thread_id="thread-123")

        assert thread.thread_id == "thread-123"
        assert isinstance(thread.created_at, datetime)
        assert isinstance(thread.updated_at, datetime)
        assert thread.messages == []
        assert thread.state == {}
        assert thread.metadata == {}
        assert thread.status == ThreadStatus.ACTIVE
        assert thread.run_count == 0

    def test_create_thread_with_messages(self):
        """Test creating a thread with messages."""
        messages = [
            AGUIMessage(message_id="msg-1", role=MessageRole.USER, content="Hi"),
            AGUIMessage(message_id="msg-2", role=MessageRole.ASSISTANT, content="Hello!"),
        ]
        thread = AGUIThread(thread_id="thread-123", messages=messages)

        assert len(thread.messages) == 2
        assert thread.message_count == 2

    def test_create_thread_with_state(self):
        """Test creating a thread with initial state."""
        thread = AGUIThread(
            thread_id="thread-123",
            state={"user_id": "user-456", "preferences": {"theme": "dark"}},
        )
        assert thread.state["user_id"] == "user-456"
        assert thread.state["preferences"]["theme"] == "dark"

    def test_add_message(self):
        """Test adding a message to thread."""
        thread = AGUIThread(thread_id="thread-123")
        original_updated = thread.updated_at

        message = AGUIMessage(message_id="msg-1", role=MessageRole.USER, content="Test")
        thread.add_message(message)

        assert len(thread.messages) == 1
        assert thread.messages[0].content == "Test"
        assert thread.updated_at >= original_updated

    def test_update_state(self):
        """Test updating thread state."""
        thread = AGUIThread(thread_id="thread-123", state={"key1": "value1"})
        original_updated = thread.updated_at

        thread.update_state({"key2": "value2", "key1": "updated"})

        assert thread.state["key1"] == "updated"
        assert thread.state["key2"] == "value2"
        assert thread.updated_at >= original_updated

    def test_increment_run_count(self):
        """Test incrementing run count."""
        thread = AGUIThread(thread_id="thread-123")
        assert thread.run_count == 0

        count = thread.increment_run_count()
        assert count == 1
        assert thread.run_count == 1

        count = thread.increment_run_count()
        assert count == 2

    def test_archive(self):
        """Test archiving a thread."""
        thread = AGUIThread(thread_id="thread-123")
        assert thread.status == ThreadStatus.ACTIVE
        assert thread.is_active

        thread.archive()

        assert thread.status == ThreadStatus.ARCHIVED
        assert not thread.is_active

    def test_thread_to_dict(self):
        """Test converting thread to dictionary."""
        messages = [
            AGUIMessage(message_id="msg-1", role=MessageRole.USER, content="Hi"),
        ]
        thread = AGUIThread(
            thread_id="thread-123",
            messages=messages,
            state={"key": "value"},
            metadata={"source": "test"},
            run_count=5,
        )
        d = thread.to_dict()

        assert d["thread_id"] == "thread-123"
        assert len(d["messages"]) == 1
        assert d["state"]["key"] == "value"
        assert d["metadata"]["source"] == "test"
        assert d["status"] == "active"
        assert d["run_count"] == 5

    def test_thread_from_dict(self):
        """Test creating thread from dictionary."""
        data = {
            "thread_id": "thread-123",
            "created_at": "2026-01-05T10:00:00",
            "updated_at": "2026-01-05T11:00:00",
            "messages": [
                {"message_id": "msg-1", "role": "user", "content": "Hello"},
            ],
            "state": {"counter": 5},
            "metadata": {},
            "status": "active",
            "run_count": 3,
        }
        thread = AGUIThread.from_dict(data)

        assert thread.thread_id == "thread-123"
        assert len(thread.messages) == 1
        assert thread.messages[0].role == MessageRole.USER
        assert thread.state["counter"] == 5
        assert thread.status == ThreadStatus.ACTIVE
        assert thread.run_count == 3

    def test_thread_from_dict_minimal(self):
        """Test creating thread from minimal dictionary."""
        data = {"thread_id": "thread-min"}
        thread = AGUIThread.from_dict(data)

        assert thread.thread_id == "thread-min"
        assert thread.messages == []
        assert thread.state == {}
        assert thread.status == ThreadStatus.ACTIVE


class TestAGUIMessageSchema:
    """Tests for AGUIMessageSchema Pydantic model."""

    def test_create_schema(self):
        """Test creating message schema."""
        schema = AGUIMessageSchema(
            message_id="msg-123",
            role="user",
            content="Test",
            created_at=datetime.utcnow(),
        )
        assert schema.message_id == "msg-123"
        assert schema.role == "user"

    def test_from_dataclass(self):
        """Test creating schema from dataclass."""
        message = AGUIMessage(
            message_id="msg-123",
            role=MessageRole.ASSISTANT,
            content="Response",
            metadata={"tokens": 100},
        )
        schema = AGUIMessageSchema.from_dataclass(message)

        assert schema.message_id == "msg-123"
        assert schema.role == "assistant"
        assert schema.content == "Response"
        assert schema.metadata["tokens"] == 100


class TestAGUIThreadSchema:
    """Tests for AGUIThreadSchema Pydantic model."""

    def test_create_schema(self):
        """Test creating thread schema."""
        schema = AGUIThreadSchema(
            thread_id="thread-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="active",
        )
        assert schema.thread_id == "thread-123"
        assert schema.status == "active"

    def test_from_dataclass(self):
        """Test creating schema from dataclass."""
        messages = [
            AGUIMessage(message_id="msg-1", role=MessageRole.USER, content="Hi"),
        ]
        thread = AGUIThread(
            thread_id="thread-123",
            messages=messages,
            state={"key": "value"},
            run_count=2,
        )
        schema = AGUIThreadSchema.from_dataclass(thread)

        assert schema.thread_id == "thread-123"
        assert len(schema.messages) == 1
        assert schema.messages[0].content == "Hi"
        assert schema.state["key"] == "value"
        assert schema.run_count == 2

    def test_schema_json_serialization(self):
        """Test JSON serialization of schema."""
        schema = AGUIThreadSchema(
            thread_id="thread-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="active",
            state={"nested": {"key": "value"}},
        )
        json_str = schema.model_dump_json()
        assert "thread-123" in json_str
        assert "active" in json_str
