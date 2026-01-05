# =============================================================================
# IPA Platform - AG-UI Base Events Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Unit tests for AG-UI base event classes and enums.
# =============================================================================

import json
from datetime import datetime

import pytest

from src.integrations.ag_ui.events.base import (
    AGUIEventType,
    BaseAGUIEvent,
    RunFinishReason,
)


class TestAGUIEventType:
    """Tests for AGUIEventType enum."""

    def test_lifecycle_events_exist(self):
        """Test lifecycle event types exist."""
        assert AGUIEventType.RUN_STARTED == "RUN_STARTED"
        assert AGUIEventType.RUN_FINISHED == "RUN_FINISHED"

    def test_text_message_events_exist(self):
        """Test text message event types exist."""
        assert AGUIEventType.TEXT_MESSAGE_START == "TEXT_MESSAGE_START"
        assert AGUIEventType.TEXT_MESSAGE_CONTENT == "TEXT_MESSAGE_CONTENT"
        assert AGUIEventType.TEXT_MESSAGE_END == "TEXT_MESSAGE_END"

    def test_tool_call_events_exist(self):
        """Test tool call event types exist."""
        assert AGUIEventType.TOOL_CALL_START == "TOOL_CALL_START"
        assert AGUIEventType.TOOL_CALL_ARGS == "TOOL_CALL_ARGS"
        assert AGUIEventType.TOOL_CALL_END == "TOOL_CALL_END"

    def test_state_events_exist(self):
        """Test state event types exist."""
        assert AGUIEventType.STATE_SNAPSHOT == "STATE_SNAPSHOT"
        assert AGUIEventType.STATE_DELTA == "STATE_DELTA"
        assert AGUIEventType.CUSTOM == "CUSTOM"

    def test_event_type_count(self):
        """Test total number of event types (11 types)."""
        assert len(AGUIEventType) == 11


class TestRunFinishReason:
    """Tests for RunFinishReason enum."""

    def test_finish_reasons_exist(self):
        """Test all finish reasons exist."""
        assert RunFinishReason.COMPLETE == "complete"
        assert RunFinishReason.ERROR == "error"
        assert RunFinishReason.CANCELLED == "cancelled"
        assert RunFinishReason.TIMEOUT == "timeout"

    def test_finish_reason_count(self):
        """Test total number of finish reasons."""
        assert len(RunFinishReason) == 4


class TestBaseAGUIEvent:
    """Tests for BaseAGUIEvent class."""

    def test_create_event_with_type(self):
        """Test creating base event with type."""
        event = BaseAGUIEvent(type=AGUIEventType.RUN_STARTED)
        assert event.type == AGUIEventType.RUN_STARTED

    def test_timestamp_auto_generated(self):
        """Test timestamp is auto-generated."""
        event = BaseAGUIEvent(type=AGUIEventType.RUN_STARTED)
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

    def test_custom_timestamp(self):
        """Test custom timestamp can be provided."""
        custom_time = datetime(2026, 1, 5, 10, 0, 0)
        event = BaseAGUIEvent(type=AGUIEventType.RUN_STARTED, timestamp=custom_time)
        assert event.timestamp == custom_time

    def test_model_dump_json(self):
        """Test JSON serialization."""
        event = BaseAGUIEvent(type=AGUIEventType.RUN_STARTED)
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        assert data["type"] == "RUN_STARTED"
        assert "timestamp" in data

    def test_to_sse_format(self):
        """Test SSE format output."""
        event = BaseAGUIEvent(type=AGUIEventType.RUN_STARTED)
        sse_str = event.to_sse()
        assert sse_str.startswith("data: ")
        assert sse_str.endswith("\n\n")
        # Verify JSON is valid
        json_part = sse_str[6:-2]  # Remove "data: " and "\n\n"
        data = json.loads(json_part)
        assert data["type"] == "RUN_STARTED"

    def test_use_enum_values_config(self):
        """Test enum values are used in serialization."""
        event = BaseAGUIEvent(type=AGUIEventType.RUN_FINISHED)
        data = event.model_dump()
        # Should be string value, not enum object
        assert data["type"] == "RUN_FINISHED"
        assert isinstance(data["type"], str)
