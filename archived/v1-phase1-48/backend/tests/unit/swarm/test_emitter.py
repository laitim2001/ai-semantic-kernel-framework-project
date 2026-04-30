"""
Unit tests for SwarmEventEmitter.

Tests event emission, throttling, and batch sending.
Sprint 101: Swarm Event System + SSE Integration
"""

import asyncio
import pytest
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock

from src.integrations.ag_ui.events import CustomEvent
from src.integrations.swarm.events import (
    SwarmEventEmitter,
    create_swarm_emitter,
    SwarmEventNames,
)
from src.integrations.swarm.models import (
    AgentSwarmStatus,
    WorkerExecution,
    ToolCallInfo,
    SwarmMode,
    SwarmStatus,
    WorkerType,
    WorkerStatus,
)


@pytest.fixture
def mock_callback():
    """Create a mock callback that collects events."""
    events: List[CustomEvent] = []

    async def callback(event: CustomEvent):
        events.append(event)

    callback.events = events  # type: ignore
    return callback


@pytest.fixture
def sample_swarm():
    """Create a sample swarm for testing."""
    return AgentSwarmStatus(
        swarm_id="test-swarm-1",
        mode=SwarmMode.PARALLEL,
        status=SwarmStatus.RUNNING,
        overall_progress=50,
        workers=[
            WorkerExecution(
                worker_id="worker-1",
                worker_name="Research Agent",
                worker_type=WorkerType.RESEARCH,
                role="Data Gatherer",
                status=WorkerStatus.RUNNING,
                progress=75,
                current_task="Searching for data",
            ),
        ],
        total_tool_calls=2,
        completed_tool_calls=1,
        started_at=datetime.utcnow(),
        metadata={"test": True},
    )


@pytest.fixture
def sample_worker():
    """Create a sample worker for testing."""
    return WorkerExecution(
        worker_id="worker-1",
        worker_name="Research Agent",
        worker_type=WorkerType.RESEARCH,
        role="Data Gatherer",
        status=WorkerStatus.RUNNING,
        progress=50,
        current_task="Processing",
        started_at=datetime.utcnow(),
    )


class TestSwarmEventEmitterCreation:
    """Test SwarmEventEmitter creation."""

    def test_create_emitter(self, mock_callback):
        """Test creating an emitter with defaults."""
        emitter = SwarmEventEmitter(event_callback=mock_callback)
        assert emitter is not None
        assert not emitter.is_running

    def test_create_emitter_with_options(self, mock_callback):
        """Test creating an emitter with custom options."""
        emitter = SwarmEventEmitter(
            event_callback=mock_callback,
            throttle_interval_ms=500,
            batch_size=10,
        )
        assert emitter is not None

    def test_factory_function(self, mock_callback):
        """Test the factory function."""
        emitter = create_swarm_emitter(
            event_callback=mock_callback,
            throttle_interval_ms=300,
            batch_size=3,
        )
        assert emitter is not None


class TestSwarmEventEmitterLifecycle:
    """Test emitter lifecycle methods."""

    @pytest.mark.asyncio
    async def test_start_stop(self, mock_callback):
        """Test starting and stopping the emitter."""
        emitter = SwarmEventEmitter(event_callback=mock_callback)

        assert not emitter.is_running

        await emitter.start()
        assert emitter.is_running

        await emitter.stop()
        assert not emitter.is_running

    @pytest.mark.asyncio
    async def test_start_twice(self, mock_callback):
        """Test that starting twice doesn't cause issues."""
        emitter = SwarmEventEmitter(event_callback=mock_callback)

        await emitter.start()
        await emitter.start()  # Should not raise

        assert emitter.is_running

        await emitter.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start(self, mock_callback):
        """Test that stopping without starting doesn't cause issues."""
        emitter = SwarmEventEmitter(event_callback=mock_callback)

        await emitter.stop()  # Should not raise
        assert not emitter.is_running


class TestSwarmEvents:
    """Test swarm-level event emission."""

    @pytest.mark.asyncio
    async def test_emit_swarm_created(self, mock_callback, sample_swarm):
        """Test emitting swarm_created event."""
        emitter = SwarmEventEmitter(event_callback=mock_callback)
        await emitter.start()

        await emitter.emit_swarm_created(sample_swarm, session_id="session-123")

        await emitter.stop()

        assert len(mock_callback.events) == 1
        event = mock_callback.events[0]
        assert event.event_name == SwarmEventNames.SWARM_CREATED
        assert event.payload["swarm_id"] == "test-swarm-1"
        assert event.payload["mode"] == "parallel"

    @pytest.mark.asyncio
    async def test_emit_swarm_completed(self, mock_callback, sample_swarm):
        """Test emitting swarm_completed event."""
        sample_swarm.status = SwarmStatus.COMPLETED
        sample_swarm.completed_at = datetime.utcnow()

        emitter = SwarmEventEmitter(event_callback=mock_callback)
        await emitter.start()

        await emitter.emit_swarm_completed(sample_swarm)

        await emitter.stop()

        assert len(mock_callback.events) == 1
        event = mock_callback.events[0]
        assert event.event_name == SwarmEventNames.SWARM_COMPLETED
        assert event.payload["status"] == "completed"


class TestWorkerEvents:
    """Test worker-level event emission."""

    @pytest.mark.asyncio
    async def test_emit_worker_started(self, mock_callback, sample_worker):
        """Test emitting worker_started event."""
        emitter = SwarmEventEmitter(event_callback=mock_callback)
        await emitter.start()

        await emitter.emit_worker_started("swarm-1", sample_worker)

        await emitter.stop()

        assert len(mock_callback.events) == 1
        event = mock_callback.events[0]
        assert event.event_name == SwarmEventNames.WORKER_STARTED
        assert event.payload["worker_id"] == "worker-1"
        assert event.payload["worker_name"] == "Research Agent"

    @pytest.mark.asyncio
    async def test_emit_worker_completed(self, mock_callback, sample_worker):
        """Test emitting worker_completed event."""
        sample_worker.status = WorkerStatus.COMPLETED
        sample_worker.completed_at = datetime.utcnow()

        emitter = SwarmEventEmitter(event_callback=mock_callback)
        await emitter.start()

        await emitter.emit_worker_completed("swarm-1", sample_worker)

        await emitter.stop()

        assert len(mock_callback.events) == 1
        event = mock_callback.events[0]
        assert event.event_name == SwarmEventNames.WORKER_COMPLETED
        assert event.payload["status"] == "completed"

    @pytest.mark.asyncio
    async def test_emit_worker_tool_call(self, mock_callback, sample_worker):
        """Test emitting worker_tool_call event."""
        tool_call = ToolCallInfo(
            tool_id="tc-1",
            tool_name="web_search",
            is_mcp=True,
            input_params={"query": "test"},
            status="completed",
            result={"data": "results"},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        emitter = SwarmEventEmitter(event_callback=mock_callback)
        await emitter.start()

        await emitter.emit_worker_tool_call("swarm-1", sample_worker, tool_call)

        await emitter.stop()

        assert len(mock_callback.events) == 1
        event = mock_callback.events[0]
        assert event.event_name == SwarmEventNames.WORKER_TOOL_CALL
        assert event.payload["tool_name"] == "web_search"
        assert event.payload["status"] == "completed"


class TestThrottling:
    """Test event throttling."""

    @pytest.mark.asyncio
    async def test_throttled_events_are_delayed(self, mock_callback, sample_worker):
        """Test that throttled events are properly delayed."""
        emitter = SwarmEventEmitter(
            event_callback=mock_callback,
            throttle_interval_ms=500,  # 500ms throttle
        )
        await emitter.start()

        # Emit multiple progress events rapidly
        for i in range(5):
            sample_worker.progress = i * 20
            await emitter.emit_worker_progress("swarm-1", sample_worker)

        # Wait a bit for processing
        await asyncio.sleep(0.1)

        await emitter.stop()

        # Due to throttling, we should have fewer events than emitted
        # The first event should be sent immediately, others are throttled
        assert len(mock_callback.events) <= 2  # First + maybe last

    @pytest.mark.asyncio
    async def test_priority_events_not_throttled(self, mock_callback, sample_worker):
        """Test that priority events are not throttled."""
        emitter = SwarmEventEmitter(
            event_callback=mock_callback,
            throttle_interval_ms=500,
        )
        await emitter.start()

        # Emit multiple priority events
        for i in range(3):
            sample_worker.worker_id = f"worker-{i}"
            await emitter.emit_worker_started("swarm-1", sample_worker)

        await emitter.stop()

        # All priority events should be sent
        assert len(mock_callback.events) == 3


class TestBatchSending:
    """Test batch sending functionality."""

    @pytest.mark.asyncio
    async def test_events_are_batched(self, mock_callback, sample_worker):
        """Test that non-priority events are batched."""
        events_sent = []
        send_count = 0

        async def counting_callback(event):
            nonlocal send_count
            send_count += 1
            events_sent.append(event)

        emitter = SwarmEventEmitter(
            event_callback=counting_callback,
            throttle_interval_ms=50,  # Short throttle
            batch_size=5,
        )
        await emitter.start()

        # Emit multiple events
        for i in range(10):
            await emitter.emit_worker_message(
                "swarm-1",
                sample_worker,
                role="assistant",
                content=f"Message {i}",
            )

        # Wait for batch processing
        await asyncio.sleep(0.3)

        await emitter.stop()

        # Events should have been sent (either batched or flushed on stop)
        assert len(events_sent) > 0


class TestErrorHandling:
    """Test error handling in emitter."""

    @pytest.mark.asyncio
    async def test_callback_error_does_not_crash(self, sample_swarm):
        """Test that callback errors don't crash the emitter."""
        async def failing_callback(event):
            raise ValueError("Callback failed")

        emitter = SwarmEventEmitter(event_callback=failing_callback)
        await emitter.start()

        # Should not raise
        await emitter.emit_swarm_created(sample_swarm)

        await emitter.stop()

    @pytest.mark.asyncio
    async def test_emit_without_start(self, mock_callback, sample_swarm):
        """Test emitting without starting still works for priority events."""
        emitter = SwarmEventEmitter(event_callback=mock_callback)

        # Priority events should still be sent
        await emitter.emit_swarm_created(sample_swarm)

        assert len(mock_callback.events) == 1


class TestWorkerToSummary:
    """Test worker to summary conversion."""

    def test_worker_to_summary(self, mock_callback, sample_worker):
        """Test the _worker_to_summary internal method."""
        emitter = SwarmEventEmitter(event_callback=mock_callback)

        summary = emitter._worker_to_summary(sample_worker)

        assert summary["worker_id"] == "worker-1"
        assert summary["worker_name"] == "Research Agent"
        assert summary["worker_type"] == "research"
        assert summary["status"] == "running"
        assert summary["progress"] == 50
