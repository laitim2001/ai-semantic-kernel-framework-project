# =============================================================================
# IPA Platform - AG-UI HybridEventBridge Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-2: HybridEventBridge
#
# Unit tests for AG-UI HybridEventBridge.
# =============================================================================

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.ag_ui.bridge import (
    BridgeConfig,
    HybridEventBridge,
    RunAgentInput,
    create_bridge,
)
from src.integrations.ag_ui.converters import EventConverters
from src.integrations.ag_ui.events import (
    AGUIEventType,
    BaseAGUIEvent,
    RunFinishedEvent,
    RunFinishReason,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)


# =============================================================================
# Mock Classes for Testing
# =============================================================================


class MockExecutionMode:
    """Mock execution mode."""

    def __init__(self, value: str = "chat"):
        self.value = value


@dataclass
class MockToolResult:
    """Mock tool execution result."""

    tool_name: str
    tool_call_id: str
    success: bool = True
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)


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
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockOrchestrator:
    """Mock HybridOrchestratorV2 for testing."""

    def __init__(self, result: Optional[MockHybridResult] = None):
        self._result = result or MockHybridResult(success=True, content="Hello!")
        self.execute_called = False
        self.execute_kwargs: Dict[str, Any] = {}

    async def execute(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        force_mode: Optional[Any] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MockHybridResult:
        """Mock execute method."""
        self.execute_called = True
        self.execute_kwargs = {
            "prompt": prompt,
            "session_id": session_id,
            "force_mode": force_mode,
            "tools": tools,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "metadata": metadata,
        }
        return self._result


# =============================================================================
# RunAgentInput Tests
# =============================================================================


class TestRunAgentInput:
    """Tests for RunAgentInput dataclass."""

    def test_basic_creation(self):
        """Test basic RunAgentInput creation."""
        input = RunAgentInput(
            prompt="Hello",
            thread_id="thread-123",
        )

        assert input.prompt == "Hello"
        assert input.thread_id == "thread-123"
        assert input.run_id is not None  # Auto-generated
        assert input.run_id.startswith("run-")

    def test_with_custom_run_id(self):
        """Test RunAgentInput with custom run_id."""
        input = RunAgentInput(
            prompt="Hello",
            thread_id="thread-123",
            run_id="custom-run-456",
        )

        assert input.run_id == "custom-run-456"

    def test_with_all_fields(self):
        """Test RunAgentInput with all fields."""
        input = RunAgentInput(
            prompt="Hello",
            thread_id="thread-123",
            run_id="run-456",
            session_id="session-789",
            force_mode=MockExecutionMode("workflow"),
            tools=[{"name": "search"}],
            max_tokens=1000,
            timeout=30.0,
            metadata={"key": "value"},
        )

        assert input.session_id == "session-789"
        assert input.force_mode.value == "workflow"
        assert input.tools == [{"name": "search"}]
        assert input.max_tokens == 1000
        assert input.timeout == 30.0
        assert input.metadata == {"key": "value"}

    def test_auto_generated_run_id_format(self):
        """Test auto-generated run_id format."""
        input1 = RunAgentInput(prompt="Test", thread_id="t1")
        input2 = RunAgentInput(prompt="Test", thread_id="t1")

        # Should be unique
        assert input1.run_id != input2.run_id
        # Should have correct format
        assert input1.run_id.startswith("run-")
        assert len(input1.run_id) == 16  # "run-" + 12 hex chars


class TestBridgeConfig:
    """Tests for BridgeConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BridgeConfig()

        assert config.chunk_size == 100
        assert config.include_metadata is True
        assert config.emit_state_events is True
        assert config.emit_custom_events is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = BridgeConfig(
            chunk_size=50,
            include_metadata=False,
            emit_state_events=False,
            emit_custom_events=False,
        )

        assert config.chunk_size == 50
        assert config.include_metadata is False
        assert config.emit_state_events is False
        assert config.emit_custom_events is False


# =============================================================================
# HybridEventBridge Tests
# =============================================================================


class TestHybridEventBridgeInit:
    """Tests for HybridEventBridge initialization."""

    def test_default_initialization(self):
        """Test default initialization without orchestrator."""
        bridge = HybridEventBridge()

        assert bridge.orchestrator is None
        assert bridge.converters is not None
        assert bridge.config is not None

    def test_with_orchestrator(self):
        """Test initialization with orchestrator."""
        orchestrator = MockOrchestrator()
        bridge = HybridEventBridge(orchestrator=orchestrator)

        assert bridge.orchestrator is orchestrator

    def test_with_custom_config(self):
        """Test initialization with custom config."""
        config = BridgeConfig(chunk_size=200)
        bridge = HybridEventBridge(config=config)

        assert bridge.config.chunk_size == 200

    def test_with_custom_converters(self):
        """Test initialization with custom converters."""
        converters = EventConverters(chunk_size=50)
        bridge = HybridEventBridge(converters=converters)

        assert bridge.converters is converters

    def test_set_orchestrator(self):
        """Test setting orchestrator after initialization."""
        bridge = HybridEventBridge()
        orchestrator = MockOrchestrator()

        bridge.set_orchestrator(orchestrator)

        assert bridge.orchestrator is orchestrator


class TestStreamEvents:
    """Tests for stream_events method."""

    @pytest.fixture
    def orchestrator(self):
        """Create mock orchestrator."""
        return MockOrchestrator(
            result=MockHybridResult(
                success=True,
                content="Hello, how can I help you?",
                execution_mode=MockExecutionMode("chat"),
            )
        )

    @pytest.fixture
    def bridge(self, orchestrator):
        """Create bridge with mock orchestrator."""
        return HybridEventBridge(orchestrator=orchestrator)

    @pytest.mark.asyncio
    async def test_stream_events_basic(self, bridge, orchestrator):
        """Test basic event streaming."""
        input = RunAgentInput(
            prompt="Hello",
            thread_id="thread-123",
        )

        events = []
        async for event_sse in bridge.stream_events(input):
            events.append(event_sse)

        # Should have multiple events
        assert len(events) >= 3

        # First event should be RUN_STARTED
        first = json.loads(events[0].replace("data: ", "").strip())
        assert first["type"] == "RUN_STARTED"

        # Last event should be RUN_FINISHED
        last = json.loads(events[-1].replace("data: ", "").strip())
        assert last["type"] == "RUN_FINISHED"

    @pytest.mark.asyncio
    async def test_stream_events_sse_format(self, bridge):
        """Test SSE format of events."""
        input = RunAgentInput(prompt="Test", thread_id="t1")

        async for event_sse in bridge.stream_events(input):
            # Should be SSE format: "data: {...}\n\n"
            assert event_sse.startswith("data: ")
            assert event_sse.endswith("\n\n")

            # Should be valid JSON after "data: "
            json_str = event_sse[6:-2]  # Remove "data: " prefix and "\n\n" suffix
            data = json.loads(json_str)
            assert "type" in data

    @pytest.mark.asyncio
    async def test_stream_events_calls_orchestrator(self, bridge, orchestrator):
        """Test that stream_events calls orchestrator.execute."""
        input = RunAgentInput(
            prompt="Test prompt",
            thread_id="thread-1",
            session_id="session-1",
            max_tokens=500,
        )

        events = []
        async for event in bridge.stream_events(input):
            events.append(event)

        assert orchestrator.execute_called
        assert orchestrator.execute_kwargs["prompt"] == "Test prompt"
        assert orchestrator.execute_kwargs["session_id"] == "session-1"
        assert orchestrator.execute_kwargs["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_stream_events_no_orchestrator_raises(self):
        """Test that stream_events raises without orchestrator."""
        bridge = HybridEventBridge()
        input = RunAgentInput(prompt="Test", thread_id="t1")

        with pytest.raises(ValueError, match="Orchestrator not configured"):
            async for _ in bridge.stream_events(input):
                pass

    @pytest.mark.asyncio
    async def test_stream_events_handles_error(self):
        """Test error handling in stream_events."""
        orchestrator = MockOrchestrator()
        orchestrator.execute = AsyncMock(side_effect=Exception("Test error"))

        bridge = HybridEventBridge(orchestrator=orchestrator)
        input = RunAgentInput(prompt="Test", thread_id="t1")

        events = []
        async for event in bridge.stream_events(input):
            events.append(event)

        # Should still have events including error RUN_FINISHED
        assert len(events) >= 2

        # Last should be error RUN_FINISHED
        last = json.loads(events[-1].replace("data: ", "").strip())
        assert last["type"] == "RUN_FINISHED"
        assert last.get("finish_reason") == "error"


class TestStreamEventsRaw:
    """Tests for stream_events_raw method."""

    @pytest.fixture
    def bridge(self):
        """Create bridge with mock orchestrator."""
        orchestrator = MockOrchestrator(
            result=MockHybridResult(success=True, content="Test")
        )
        return HybridEventBridge(orchestrator=orchestrator)

    @pytest.mark.asyncio
    async def test_stream_events_raw_returns_objects(self, bridge):
        """Test that stream_events_raw returns event objects."""
        input = RunAgentInput(prompt="Test", thread_id="t1")

        events = []
        async for event in bridge.stream_events_raw(input):
            events.append(event)

        # All events should be BaseAGUIEvent instances
        for event in events:
            assert isinstance(event, BaseAGUIEvent)

        # First should be RUN_STARTED
        assert isinstance(events[0], RunStartedEvent)
        # Last should be RUN_FINISHED
        assert isinstance(events[-1], RunFinishedEvent)

    @pytest.mark.asyncio
    async def test_stream_events_raw_no_orchestrator_raises(self):
        """Test that stream_events_raw raises without orchestrator."""
        bridge = HybridEventBridge()
        input = RunAgentInput(prompt="Test", thread_id="t1")

        with pytest.raises(ValueError, match="Orchestrator not configured"):
            async for _ in bridge.stream_events_raw(input):
                pass


class TestExecuteAndCollect:
    """Tests for execute_and_collect method."""

    @pytest.fixture
    def bridge(self):
        """Create bridge with mock orchestrator."""
        orchestrator = MockOrchestrator(
            result=MockHybridResult(success=True, content="Response")
        )
        return HybridEventBridge(orchestrator=orchestrator)

    @pytest.mark.asyncio
    async def test_execute_and_collect_returns_list(self, bridge):
        """Test that execute_and_collect returns list of events."""
        input = RunAgentInput(prompt="Test", thread_id="t1")

        events = await bridge.execute_and_collect(input)

        assert isinstance(events, list)
        assert len(events) >= 3

    @pytest.mark.asyncio
    async def test_execute_and_collect_same_as_stream(self, bridge):
        """Test that execute_and_collect matches stream_events_raw."""
        input = RunAgentInput(prompt="Test", thread_id="t1", run_id="fixed-run")

        # Collect via streaming
        streamed = []
        async for event in bridge.stream_events_raw(input):
            streamed.append(event)

        # Create new bridge with same orchestrator for fair comparison
        orchestrator = MockOrchestrator(
            result=MockHybridResult(success=True, content="Response")
        )
        bridge2 = HybridEventBridge(orchestrator=orchestrator)

        # Collect via method (need same run_id)
        input2 = RunAgentInput(prompt="Test", thread_id="t1", run_id="fixed-run-2")
        collected = await bridge2.execute_and_collect(input2)

        # Should have same number and types of events
        assert len(streamed) == len(collected)
        for s, c in zip(streamed, collected):
            assert type(s) == type(c)


class TestToolCallEvents:
    """Tests for tool call event generation."""

    @pytest.mark.asyncio
    async def test_stream_events_with_tools(self):
        """Test streaming events with tool calls."""
        tool = MockToolResult(
            tool_name="search",
            tool_call_id="call-123",
            success=True,
            result={"documents": ["doc1"]},
            arguments={"query": "test"},
        )
        orchestrator = MockOrchestrator(
            result=MockHybridResult(
                success=True,
                content="Found documents.",
                tool_results=[tool],
            )
        )
        bridge = HybridEventBridge(orchestrator=orchestrator)

        input = RunAgentInput(prompt="Search", thread_id="t1")
        events = await bridge.execute_and_collect(input)

        # Find tool events
        tool_starts = [e for e in events if isinstance(e, ToolCallStartEvent)]
        tool_ends = [e for e in events if isinstance(e, ToolCallEndEvent)]

        assert len(tool_starts) == 1
        assert len(tool_ends) == 1
        assert tool_starts[0].tool_name == "search"
        # tool_call_id is auto-generated by converters, just verify it exists
        assert tool_starts[0].tool_call_id is not None
        assert tool_starts[0].tool_call_id.startswith("call-")


class TestDirectEventMethods:
    """Tests for direct event creation methods."""

    @pytest.fixture
    def bridge(self):
        """Create bridge instance."""
        return HybridEventBridge()

    def test_create_run_started(self, bridge):
        """Test create_run_started method."""
        event = bridge.create_run_started("thread-1", "run-1")

        assert isinstance(event, RunStartedEvent)
        assert event.thread_id == "thread-1"
        assert event.run_id == "run-1"

    def test_create_run_finished_success(self, bridge):
        """Test create_run_finished for success."""
        event = bridge.create_run_finished("thread-1", "run-1", success=True)

        assert isinstance(event, RunFinishedEvent)
        # RunFinishReason is str-based enum, compare directly or via string value
        assert str(event.finish_reason) == "complete" or event.finish_reason == RunFinishReason.COMPLETE

    def test_create_run_finished_error(self, bridge):
        """Test create_run_finished for error."""
        event = bridge.create_run_finished(
            "thread-1", "run-1",
            success=False,
            error="Something failed",
        )

        # RunFinishReason is str-based enum, compare directly or via string value
        assert str(event.finish_reason) == "error" or event.finish_reason == RunFinishReason.ERROR
        assert event.error == "Something failed"

    def test_format_event(self, bridge):
        """Test format_event method."""
        event = RunStartedEvent(thread_id="t1", run_id="r1")
        sse = bridge.format_event(event)

        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")
        assert "RUN_STARTED" in sse


class TestCreateBridgeFactory:
    """Tests for create_bridge factory function."""

    def test_create_bridge_default(self):
        """Test factory with default settings."""
        bridge = create_bridge()

        assert isinstance(bridge, HybridEventBridge)
        assert bridge.orchestrator is None
        assert bridge.config.chunk_size == 100

    def test_create_bridge_with_orchestrator(self):
        """Test factory with orchestrator."""
        orchestrator = MockOrchestrator()
        bridge = create_bridge(orchestrator=orchestrator)

        assert bridge.orchestrator is orchestrator

    def test_create_bridge_custom_settings(self):
        """Test factory with custom settings."""
        bridge = create_bridge(
            chunk_size=50,
            include_metadata=False,
        )

        assert bridge.config.chunk_size == 50
        assert bridge.config.include_metadata is False


class TestMetadataInclusion:
    """Tests for metadata inclusion in events."""

    @pytest.mark.asyncio
    async def test_metadata_included_by_default(self):
        """Test that metadata is included by default."""
        orchestrator = MockOrchestrator(
            result=MockHybridResult(
                success=True,
                content="Test",
                execution_mode=MockExecutionMode("chat"),
                tokens_used=150,
                duration=0.5,
                framework_used="claude",
            )
        )
        bridge = HybridEventBridge(
            orchestrator=orchestrator,
            config=BridgeConfig(include_metadata=True),
        )

        input = RunAgentInput(prompt="Test", thread_id="t1")
        events = await bridge.execute_and_collect(input)

        # Find RUN_FINISHED event
        finished = [e for e in events if isinstance(e, RunFinishedEvent)]
        assert len(finished) == 1
        assert finished[0].usage is not None
        assert finished[0].usage["tokens_used"] == 150

    @pytest.mark.asyncio
    async def test_metadata_excluded_when_disabled(self):
        """Test that metadata is excluded when disabled."""
        orchestrator = MockOrchestrator(
            result=MockHybridResult(success=True, content="Test")
        )
        bridge = HybridEventBridge(
            orchestrator=orchestrator,
            config=BridgeConfig(include_metadata=False),
        )

        input = RunAgentInput(prompt="Test", thread_id="t1")
        events = await bridge.execute_and_collect(input)

        # Find RUN_FINISHED event
        finished = [e for e in events if isinstance(e, RunFinishedEvent)]
        assert len(finished) == 1
        assert finished[0].usage is None
