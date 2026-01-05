# =============================================================================
# IPA Platform - AG-UI Tool Events Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Unit tests for AG-UI tool call events.
# =============================================================================

import json

import pytest

from src.integrations.ag_ui.events.base import AGUIEventType
from src.integrations.ag_ui.events.tool import (
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolCallStatus,
)


class TestToolCallStatus:
    """Tests for ToolCallStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ToolCallStatus.PENDING == "pending"
        assert ToolCallStatus.RUNNING == "running"
        assert ToolCallStatus.SUCCESS == "success"
        assert ToolCallStatus.ERROR == "error"


class TestToolCallStartEvent:
    """Tests for ToolCallStartEvent class."""

    def test_create_tool_call_start_event(self):
        """Test creating a tool call start event."""
        event = ToolCallStartEvent(
            tool_call_id="call-123",
            tool_name="search_documents"
        )
        assert event.type == AGUIEventType.TOOL_CALL_START
        assert event.tool_call_id == "call-123"
        assert event.tool_name == "search_documents"
        assert event.parent_message_id is None

    def test_with_parent_message_id(self):
        """Test tool call start with parent message."""
        event = ToolCallStartEvent(
            tool_call_id="call-123",
            tool_name="search_documents",
            parent_message_id="msg-456"
        )
        assert event.parent_message_id == "msg-456"

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = ToolCallStartEvent(
            tool_call_id="call-123",
            tool_name="calculate",
            parent_message_id="msg-456"
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "TOOL_CALL_START"
        assert data["tool_call_id"] == "call-123"
        assert data["tool_name"] == "calculate"
        assert data["parent_message_id"] == "msg-456"

    def test_required_fields(self):
        """Test required fields."""
        with pytest.raises(ValueError):
            ToolCallStartEvent(tool_call_id="call-123")  # Missing tool_name

        with pytest.raises(ValueError):
            ToolCallStartEvent(tool_name="search")  # Missing tool_call_id


class TestToolCallArgsEvent:
    """Tests for ToolCallArgsEvent class."""

    def test_create_tool_call_args_event(self):
        """Test creating a tool call args event."""
        event = ToolCallArgsEvent(
            tool_call_id="call-123",
            delta='{"query": "test"}'
        )
        assert event.type == AGUIEventType.TOOL_CALL_ARGS
        assert event.tool_call_id == "call-123"
        assert event.delta == '{"query": "test"}'

    def test_streaming_args(self):
        """Test streaming args in chunks."""
        deltas = [
            '{"query": "IPA ',
            'Platform",',
            ' "limit": 10}'
        ]
        events = [
            ToolCallArgsEvent(tool_call_id="call-123", delta=d)
            for d in deltas
        ]

        # Reconstruct full args
        full_args = "".join(e.delta for e in events)
        assert full_args == '{"query": "IPA Platform", "limit": 10}'

        # Verify it's valid JSON
        args = json.loads(full_args)
        assert args["query"] == "IPA Platform"
        assert args["limit"] == 10

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = ToolCallArgsEvent(
            tool_call_id="call-123",
            delta='{"key": "value"}'
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "TOOL_CALL_ARGS"
        assert data["tool_call_id"] == "call-123"
        assert data["delta"] == '{"key": "value"}'


class TestToolCallEndEvent:
    """Tests for ToolCallEndEvent class."""

    def test_create_tool_call_end_success(self):
        """Test creating a successful tool call end event."""
        event = ToolCallEndEvent(
            tool_call_id="call-123",
            status=ToolCallStatus.SUCCESS,
            result={"documents": [{"id": "doc-1", "title": "Test"}]}
        )
        assert event.type == AGUIEventType.TOOL_CALL_END
        assert event.tool_call_id == "call-123"
        assert event.status == ToolCallStatus.SUCCESS
        assert event.result is not None
        assert event.error is None

    def test_create_tool_call_end_error(self):
        """Test creating an error tool call end event."""
        event = ToolCallEndEvent(
            tool_call_id="call-123",
            status=ToolCallStatus.ERROR,
            error="Connection timeout"
        )
        assert event.status == ToolCallStatus.ERROR
        assert event.error == "Connection timeout"
        assert event.result is None

    def test_default_status_is_success(self):
        """Test default status is SUCCESS."""
        event = ToolCallEndEvent(tool_call_id="call-123")
        assert event.status == ToolCallStatus.SUCCESS

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = ToolCallEndEvent(
            tool_call_id="call-123",
            status=ToolCallStatus.SUCCESS,
            result={"value": 42}
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "TOOL_CALL_END"
        assert data["tool_call_id"] == "call-123"
        assert data["status"] == "success"
        assert data["result"]["value"] == 42


class TestToolCallEventFlow:
    """Tests for complete tool call event flow."""

    def test_complete_tool_call_flow_success(self):
        """Test complete successful tool call flow."""
        tool_call_id = "call-flow-test"

        # Start event
        start = ToolCallStartEvent(
            tool_call_id=tool_call_id,
            tool_name="calculate",
            parent_message_id="msg-parent"
        )

        # Args events (streaming)
        args_events = [
            ToolCallArgsEvent(tool_call_id=tool_call_id, delta='{"expression":'),
            ToolCallArgsEvent(tool_call_id=tool_call_id, delta=' "2 + 2"}'),
        ]

        # End event with result
        end = ToolCallEndEvent(
            tool_call_id=tool_call_id,
            status=ToolCallStatus.SUCCESS,
            result={"answer": 4}
        )

        # Verify flow
        assert start.type == AGUIEventType.TOOL_CALL_START
        assert all(e.type == AGUIEventType.TOOL_CALL_ARGS for e in args_events)
        assert end.type == AGUIEventType.TOOL_CALL_END

        # Reconstruct args
        full_args = "".join(e.delta for e in args_events)
        args = json.loads(full_args)
        assert args["expression"] == "2 + 2"

        # Verify result
        assert end.result["answer"] == 4

    def test_complete_tool_call_flow_error(self):
        """Test complete failed tool call flow."""
        tool_call_id = "call-error-test"

        # Start event
        start = ToolCallStartEvent(
            tool_call_id=tool_call_id,
            tool_name="fetch_data"
        )

        # Args event
        args = ToolCallArgsEvent(
            tool_call_id=tool_call_id,
            delta='{"url": "https://invalid.example.com"}'
        )

        # End event with error
        end = ToolCallEndEvent(
            tool_call_id=tool_call_id,
            status=ToolCallStatus.ERROR,
            error="DNS resolution failed"
        )

        # Verify error flow
        assert end.status == ToolCallStatus.ERROR
        assert end.error == "DNS resolution failed"
        assert end.result is None
