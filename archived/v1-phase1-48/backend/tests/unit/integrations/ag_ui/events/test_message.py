# =============================================================================
# IPA Platform - AG-UI Message Events Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Unit tests for AG-UI text message events.
# =============================================================================

import json

import pytest

from src.integrations.ag_ui.events.base import AGUIEventType
from src.integrations.ag_ui.events.message import (
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)


class TestTextMessageStartEvent:
    """Tests for TextMessageStartEvent class."""

    def test_create_message_start_event(self):
        """Test creating a message start event."""
        event = TextMessageStartEvent(
            message_id="msg-123",
            role="assistant"
        )
        assert event.type == AGUIEventType.TEXT_MESSAGE_START
        assert event.message_id == "msg-123"
        assert event.role == "assistant"

    def test_default_role_is_assistant(self):
        """Test default role is assistant."""
        event = TextMessageStartEvent(message_id="msg-123")
        assert event.role == "assistant"

    def test_different_roles(self):
        """Test different message roles."""
        for role in ["user", "assistant", "system"]:
            event = TextMessageStartEvent(message_id="msg-123", role=role)
            assert event.role == role

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = TextMessageStartEvent(
            message_id="msg-123",
            role="assistant"
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "TEXT_MESSAGE_START"
        assert data["message_id"] == "msg-123"
        assert data["role"] == "assistant"

    def test_required_message_id(self):
        """Test message_id is required."""
        with pytest.raises(ValueError):
            TextMessageStartEvent()


class TestTextMessageContentEvent:
    """Tests for TextMessageContentEvent class."""

    def test_create_message_content_event(self):
        """Test creating a message content event."""
        event = TextMessageContentEvent(
            message_id="msg-123",
            delta="Hello, "
        )
        assert event.type == AGUIEventType.TEXT_MESSAGE_CONTENT
        assert event.message_id == "msg-123"
        assert event.delta == "Hello, "

    def test_streaming_multiple_deltas(self):
        """Test streaming multiple content deltas."""
        deltas = ["Hello, ", "how ", "can ", "I ", "help ", "you?"]
        events = [
            TextMessageContentEvent(message_id="msg-123", delta=d)
            for d in deltas
        ]

        # Reconstruct full message
        full_message = "".join(e.delta for e in events)
        assert full_message == "Hello, how can I help you?"

    def test_empty_delta(self):
        """Test empty delta string is valid."""
        event = TextMessageContentEvent(
            message_id="msg-123",
            delta=""
        )
        assert event.delta == ""

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = TextMessageContentEvent(
            message_id="msg-123",
            delta="test content"
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "TEXT_MESSAGE_CONTENT"
        assert data["message_id"] == "msg-123"
        assert data["delta"] == "test content"

    def test_unicode_content(self):
        """Test Unicode content in delta."""
        event = TextMessageContentEvent(
            message_id="msg-123",
            delta="你好！這是繁體中文 🎉"
        )
        assert event.delta == "你好！這是繁體中文 🎉"
        # Verify JSON serialization handles Unicode
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        assert data["delta"] == "你好！這是繁體中文 🎉"


class TestTextMessageEndEvent:
    """Tests for TextMessageEndEvent class."""

    def test_create_message_end_event(self):
        """Test creating a message end event."""
        event = TextMessageEndEvent(message_id="msg-123")
        assert event.type == AGUIEventType.TEXT_MESSAGE_END
        assert event.message_id == "msg-123"

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = TextMessageEndEvent(message_id="msg-123")
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "TEXT_MESSAGE_END"
        assert data["message_id"] == "msg-123"

    def test_required_message_id(self):
        """Test message_id is required."""
        with pytest.raises(ValueError):
            TextMessageEndEvent()


class TestTextMessageEventFlow:
    """Tests for complete text message event flow."""

    def test_complete_message_flow(self):
        """Test complete message flow: start -> content* -> end."""
        message_id = "msg-flow-test"

        # Start event
        start = TextMessageStartEvent(
            message_id=message_id,
            role="assistant"
        )

        # Content events
        contents = [
            TextMessageContentEvent(message_id=message_id, delta="I "),
            TextMessageContentEvent(message_id=message_id, delta="am "),
            TextMessageContentEvent(message_id=message_id, delta="an "),
            TextMessageContentEvent(message_id=message_id, delta="AI "),
            TextMessageContentEvent(message_id=message_id, delta="assistant."),
        ]

        # End event
        end = TextMessageEndEvent(message_id=message_id)

        # Verify all events share same message_id
        assert start.message_id == message_id
        assert all(c.message_id == message_id for c in contents)
        assert end.message_id == message_id

        # Verify event types
        assert start.type == AGUIEventType.TEXT_MESSAGE_START
        assert all(c.type == AGUIEventType.TEXT_MESSAGE_CONTENT for c in contents)
        assert end.type == AGUIEventType.TEXT_MESSAGE_END

        # Reconstruct full message
        full_message = "".join(c.delta for c in contents)
        assert full_message == "I am an AI assistant."
