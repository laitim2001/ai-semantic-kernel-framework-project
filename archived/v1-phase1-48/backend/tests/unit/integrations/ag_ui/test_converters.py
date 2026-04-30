# =============================================================================
# IPA Platform - AG-UI EventConverters Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-2: HybridEventBridge
#
# Unit tests for AG-UI EventConverters.
# =============================================================================

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from src.integrations.ag_ui.converters import (
    EventConverters,
    HybridEvent,
    HybridEventType,
    create_converters,
)
from src.integrations.ag_ui.events import (
    AGUIEventType,
    RunFinishedEvent,
    RunFinishReason,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolCallStatus,
)


# =============================================================================
# Mock HybridResultV2 for testing
# =============================================================================


@dataclass
class MockToolResult:
    """Mock tool execution result."""

    tool_name: str
    tool_call_id: str
    success: bool = True
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)


class MockExecutionMode:
    """Mock execution mode."""

    def __init__(self, value: str):
        self.value = value


@dataclass
class MockHybridResult:
    """Mock HybridResultV2 for testing."""

    success: bool
    content: str = ""
    error: Optional[str] = None
    framework_used: str = "claude"
    execution_mode: Optional[MockExecutionMode] = None
    tool_results: List[MockToolResult] = field(default_factory=list)
    duration: float = 0.5
    tokens_used: int = 100


# =============================================================================
# EventConverters Tests
# =============================================================================


class TestEventConvertersInit:
    """Tests for EventConverters initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        converters = EventConverters()
        assert converters._chunk_size == 100
        assert converters._include_metadata is True

    def test_custom_chunk_size(self):
        """Test custom chunk size."""
        converters = EventConverters(chunk_size=50)
        assert converters._chunk_size == 50

    def test_custom_include_metadata(self):
        """Test custom include_metadata setting."""
        converters = EventConverters(include_metadata=False)
        assert converters._include_metadata is False


class TestRunLifecycleEvents:
    """Tests for RUN_STARTED and RUN_FINISHED events."""

    @pytest.fixture
    def converters(self):
        """Create EventConverters instance."""
        return EventConverters()

    def test_to_run_started(self, converters):
        """Test creating RUN_STARTED event."""
        event = converters.to_run_started("thread-123", "run-456")

        assert isinstance(event, RunStartedEvent)
        assert event.type == AGUIEventType.RUN_STARTED
        assert event.thread_id == "thread-123"
        assert event.run_id == "run-456"

    def test_to_run_finished_success(self, converters):
        """Test creating successful RUN_FINISHED event."""
        event = converters.to_run_finished(
            "thread-123",
            "run-456",
            success=True,
        )

        assert isinstance(event, RunFinishedEvent)
        assert event.type == AGUIEventType.RUN_FINISHED
        assert event.thread_id == "thread-123"
        assert event.run_id == "run-456"
        assert event.finish_reason == RunFinishReason.COMPLETE

    def test_to_run_finished_with_error(self, converters):
        """Test creating RUN_FINISHED event with error."""
        event = converters.to_run_finished(
            "thread-123",
            "run-456",
            success=False,
            error="Something went wrong",
        )

        assert event.finish_reason == RunFinishReason.ERROR
        assert event.error == "Something went wrong"

    def test_to_run_finished_with_usage(self, converters):
        """Test creating RUN_FINISHED event with usage metadata."""
        usage = {"tokens_used": 150, "duration_ms": 500}
        event = converters.to_run_finished(
            "thread-123",
            "run-456",
            success=True,
            usage=usage,
        )

        assert event.usage == usage


class TestTextMessageEvents:
    """Tests for TEXT_MESSAGE_* events."""

    @pytest.fixture
    def converters(self):
        """Create EventConverters instance."""
        return EventConverters()

    def test_to_text_message_start(self, converters):
        """Test creating TEXT_MESSAGE_START event."""
        event = converters.to_text_message_start("msg-123", role="assistant")

        assert isinstance(event, TextMessageStartEvent)
        assert event.type == AGUIEventType.TEXT_MESSAGE_START
        assert event.message_id == "msg-123"
        assert event.role == "assistant"

    def test_to_text_message_start_default_role(self, converters):
        """Test TEXT_MESSAGE_START with default role."""
        event = converters.to_text_message_start("msg-123")
        assert event.role == "assistant"

    def test_to_text_message_content(self, converters):
        """Test creating TEXT_MESSAGE_CONTENT event."""
        event = converters.to_text_message_content("msg-123", "Hello, ")

        assert isinstance(event, TextMessageContentEvent)
        assert event.type == AGUIEventType.TEXT_MESSAGE_CONTENT
        assert event.message_id == "msg-123"
        assert event.delta == "Hello, "

    def test_to_text_message_end(self, converters):
        """Test creating TEXT_MESSAGE_END event."""
        event = converters.to_text_message_end("msg-123")

        assert isinstance(event, TextMessageEndEvent)
        assert event.type == AGUIEventType.TEXT_MESSAGE_END
        assert event.message_id == "msg-123"


class TestToolCallEvents:
    """Tests for TOOL_CALL_* events."""

    @pytest.fixture
    def converters(self):
        """Create EventConverters instance."""
        return EventConverters()

    def test_to_tool_call_start(self, converters):
        """Test creating TOOL_CALL_START event."""
        event = converters.to_tool_call_start(
            "call-123",
            "search_documents",
            parent_message_id="msg-456",
        )

        assert isinstance(event, ToolCallStartEvent)
        assert event.type == AGUIEventType.TOOL_CALL_START
        assert event.tool_call_id == "call-123"
        assert event.tool_name == "search_documents"
        assert event.parent_message_id == "msg-456"

    def test_to_tool_call_start_no_parent(self, converters):
        """Test TOOL_CALL_START without parent message."""
        event = converters.to_tool_call_start("call-123", "search")
        assert event.parent_message_id is None

    def test_to_tool_call_args(self, converters):
        """Test creating TOOL_CALL_ARGS event."""
        args = {"query": "test", "limit": 10}
        event = converters.to_tool_call_args("call-123", args)

        assert isinstance(event, ToolCallArgsEvent)
        assert event.type == AGUIEventType.TOOL_CALL_ARGS
        assert event.tool_call_id == "call-123"
        assert json.loads(event.delta) == args

    def test_to_tool_call_end_success(self, converters):
        """Test creating successful TOOL_CALL_END event."""
        result = {"documents": ["doc1", "doc2"]}
        event = converters.to_tool_call_end(
            "call-123",
            success=True,
            result=result,
        )

        assert isinstance(event, ToolCallEndEvent)
        assert event.type == AGUIEventType.TOOL_CALL_END
        assert event.tool_call_id == "call-123"
        assert event.status == ToolCallStatus.SUCCESS
        assert event.result == result

    def test_to_tool_call_end_error(self, converters):
        """Test creating error TOOL_CALL_END event."""
        event = converters.to_tool_call_end(
            "call-123",
            success=False,
            error="Tool execution failed",
        )

        assert event.status == ToolCallStatus.ERROR
        assert event.error == "Tool execution failed"


class TestContentChunking:
    """Tests for content chunking functionality."""

    @pytest.fixture
    def converters(self):
        """Create EventConverters with small chunk size."""
        return EventConverters(chunk_size=10)

    def test_content_to_chunks_short_content(self, converters):
        """Test chunking short content."""
        chunks = converters.content_to_chunks("Hello", "msg-1")

        assert len(chunks) == 1
        assert chunks[0].delta == "Hello"

    def test_content_to_chunks_long_content(self, converters):
        """Test chunking long content."""
        content = "This is a longer message that needs to be chunked."
        chunks = converters.content_to_chunks(content, "msg-1")

        # Should create multiple chunks
        assert len(chunks) > 1

        # Verify all chunks have correct message_id
        for chunk in chunks:
            assert chunk.message_id == "msg-1"
            assert isinstance(chunk, TextMessageContentEvent)

        # Verify combined content matches original
        combined = "".join(c.delta for c in chunks)
        assert combined == content

    def test_content_to_chunks_empty(self, converters):
        """Test chunking empty content."""
        chunks = converters.content_to_chunks("", "msg-1")
        assert len(chunks) == 0

    def test_content_to_chunks_exact_chunk_size(self):
        """Test content exactly matching chunk size."""
        converters = EventConverters(chunk_size=5)
        chunks = converters.content_to_chunks("Hello", "msg-1")

        assert len(chunks) == 1
        assert chunks[0].delta == "Hello"


class TestHybridEventConversion:
    """Tests for converting HybridEvent to AG-UI events."""

    @pytest.fixture
    def converters(self):
        """Create EventConverters instance."""
        return EventConverters()

    def test_convert_execution_started(self, converters):
        """Test converting EXECUTION_STARTED event."""
        hybrid = HybridEvent(
            type=HybridEventType.EXECUTION_STARTED,
            thread_id="thread-1",
            run_id="run-1",
            data={},
        )
        result = converters.convert(hybrid)

        assert isinstance(result, RunStartedEvent)

    def test_convert_execution_completed(self, converters):
        """Test converting EXECUTION_COMPLETED event."""
        hybrid = HybridEvent(
            type=HybridEventType.EXECUTION_COMPLETED,
            thread_id="thread-1",
            run_id="run-1",
            data={"success": True},
        )
        result = converters.convert(hybrid)

        assert isinstance(result, RunFinishedEvent)
        assert result.finish_reason == RunFinishReason.COMPLETE

    def test_convert_message_start(self, converters):
        """Test converting MESSAGE_START event."""
        hybrid = HybridEvent(
            type=HybridEventType.MESSAGE_START,
            message_id="msg-1",
            data={"role": "user"},
        )
        result = converters.convert(hybrid)

        assert isinstance(result, TextMessageStartEvent)
        assert result.role == "user"

    def test_convert_message_chunk(self, converters):
        """Test converting MESSAGE_CHUNK event."""
        hybrid = HybridEvent(
            type=HybridEventType.MESSAGE_CHUNK,
            message_id="msg-1",
            data={"delta": "Hello "},
        )
        result = converters.convert(hybrid)

        assert isinstance(result, TextMessageContentEvent)
        assert result.delta == "Hello "

    def test_convert_message_end(self, converters):
        """Test converting MESSAGE_END event."""
        hybrid = HybridEvent(
            type=HybridEventType.MESSAGE_END,
            message_id="msg-1",
            data={},
        )
        result = converters.convert(hybrid)

        assert isinstance(result, TextMessageEndEvent)

    def test_convert_tool_call_start(self, converters):
        """Test converting TOOL_CALL_START event."""
        hybrid = HybridEvent(
            type=HybridEventType.TOOL_CALL_START,
            tool_call_id="call-1",
            data={"tool_name": "search"},
        )
        result = converters.convert(hybrid)

        assert isinstance(result, ToolCallStartEvent)
        assert result.tool_name == "search"

    def test_convert_tool_call_args(self, converters):
        """Test converting TOOL_CALL_ARGS event."""
        hybrid = HybridEvent(
            type=HybridEventType.TOOL_CALL_ARGS,
            tool_call_id="call-1",
            data={"args": {"query": "test"}},
        )
        result = converters.convert(hybrid)

        assert isinstance(result, ToolCallArgsEvent)

    def test_convert_tool_call_end(self, converters):
        """Test converting TOOL_CALL_END event."""
        hybrid = HybridEvent(
            type=HybridEventType.TOOL_CALL_END,
            tool_call_id="call-1",
            data={"success": True, "result": {"data": "test"}},
        )
        result = converters.convert(hybrid)

        assert isinstance(result, ToolCallEndEvent)
        assert result.status == ToolCallStatus.SUCCESS


class TestFromResult:
    """Tests for converting HybridResultV2 to AG-UI events."""

    @pytest.fixture
    def converters(self):
        """Create EventConverters instance."""
        return EventConverters(chunk_size=50)

    def test_from_result_simple_response(self, converters):
        """Test converting simple result without tools."""
        result = MockHybridResult(
            success=True,
            content="Hello, how can I help you?",
        )

        events = converters.from_result(
            result,
            thread_id="thread-1",
            run_id="run-1",
        )

        # from_result skips RUN_STARTED (handled by bridge)
        # Should have: MSG_START, MSG_CONTENT, MSG_END, RUN_FINISHED
        assert len(events) >= 3

        # Verify event types in order (no RUN_STARTED - that's handled by bridge)
        assert isinstance(events[0], TextMessageStartEvent)
        # Content events in middle
        assert isinstance(events[-2], TextMessageEndEvent)
        assert isinstance(events[-1], RunFinishedEvent)

    def test_from_result_with_tool_calls(self, converters):
        """Test converting result with tool calls."""
        tool = MockToolResult(
            tool_name="search",
            tool_call_id="call-1",
            success=True,
            result={"documents": []},
            arguments={"query": "test"},
        )
        result = MockHybridResult(
            success=True,
            content="Found no results.",
            tool_results=[tool],
        )

        events = converters.from_result(
            result,
            thread_id="thread-1",
            run_id="run-1",
        )

        # Should include tool call events
        tool_start_events = [e for e in events if isinstance(e, ToolCallStartEvent)]
        tool_end_events = [e for e in events if isinstance(e, ToolCallEndEvent)]

        assert len(tool_start_events) == 1
        assert len(tool_end_events) == 1

    def test_from_result_error(self, converters):
        """Test converting error result."""
        result = MockHybridResult(
            success=False,
            error="Something went wrong",
        )

        events = converters.from_result(
            result,
            thread_id="thread-1",
            run_id="run-1",
        )

        # Check last event is RUN_FINISHED with error
        assert isinstance(events[-1], RunFinishedEvent)
        assert events[-1].finish_reason == RunFinishReason.ERROR

    def test_from_result_empty_content(self, converters):
        """Test converting result with empty content."""
        result = MockHybridResult(
            success=True,
            content="",
        )

        events = converters.from_result(
            result,
            thread_id="thread-1",
            run_id="run-1",
        )

        # from_result skips RUN_STARTED (handled by bridge)
        # Should still have RUN_FINISHED at end
        assert len(events) >= 1
        assert isinstance(events[-1], RunFinishedEvent)

    def test_from_result_custom_message_id(self, converters):
        """Test using custom message ID."""
        result = MockHybridResult(
            success=True,
            content="Test",
        )

        events = converters.from_result(
            result,
            thread_id="thread-1",
            run_id="run-1",
            message_id="custom-msg-id",
        )

        # Find message start event and check ID
        msg_start = [e for e in events if isinstance(e, TextMessageStartEvent)]
        assert len(msg_start) == 1
        assert msg_start[0].message_id == "custom-msg-id"


class TestFactoryFunction:
    """Tests for create_converters factory function."""

    def test_create_converters_default(self):
        """Test factory with default settings."""
        converters = create_converters()
        assert isinstance(converters, EventConverters)
        assert converters._chunk_size == 100
        assert converters._include_metadata is True

    def test_create_converters_custom(self):
        """Test factory with custom settings."""
        converters = create_converters(chunk_size=200, include_metadata=False)
        assert converters._chunk_size == 200
        assert converters._include_metadata is False


class TestHybridEventDataclass:
    """Tests for HybridEvent dataclass."""

    def test_hybrid_event_creation(self):
        """Test creating HybridEvent."""
        event = HybridEvent(
            type=HybridEventType.MESSAGE_CHUNK,
            message_id="msg-1",
            data={"delta": "Hello"},
        )

        assert event.type == HybridEventType.MESSAGE_CHUNK
        assert event.message_id == "msg-1"
        assert event.data["delta"] == "Hello"

    def test_hybrid_event_optional_fields(self):
        """Test HybridEvent optional fields."""
        event = HybridEvent(
            type=HybridEventType.EXECUTION_STARTED,
            data={},
        )

        assert event.thread_id is None
        assert event.run_id is None
        assert event.message_id is None
        assert event.tool_call_id is None
        assert event.data == {}


class TestHybridEventType:
    """Tests for HybridEventType enum."""

    def test_all_event_types_defined(self):
        """Verify all expected event types exist."""
        expected_types = [
            "EXECUTION_STARTED",
            "EXECUTION_COMPLETED",
            "MESSAGE_START",
            "MESSAGE_CHUNK",
            "MESSAGE_END",
            "TOOL_CALL_START",
            "TOOL_CALL_ARGS",
            "TOOL_CALL_END",
        ]

        for type_name in expected_types:
            assert hasattr(HybridEventType, type_name)
