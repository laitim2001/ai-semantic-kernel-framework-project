"""
Unit tests for SwarmTracker.

Tests all tracker methods including state management and thread safety.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.integrations.swarm import (
    SwarmTracker,
    SwarmNotFoundError,
    WorkerNotFoundError,
    ToolCallNotFoundError,
    SwarmMode,
    SwarmStatus,
    WorkerType,
    WorkerStatus,
)


class TestSwarmTrackerBasics:
    """Test basic SwarmTracker operations."""

    def test_create_tracker(self):
        """Test creating a SwarmTracker."""
        tracker = SwarmTracker()
        assert tracker is not None

    def test_create_swarm(self):
        """Test creating a swarm."""
        tracker = SwarmTracker()
        swarm = tracker.create_swarm(
            swarm_id="swarm-1",
            mode=SwarmMode.PARALLEL,
            metadata={"test": True},
        )
        assert swarm.swarm_id == "swarm-1"
        assert swarm.mode == SwarmMode.PARALLEL
        assert swarm.status == SwarmStatus.INITIALIZING
        assert swarm.overall_progress == 0
        assert swarm.metadata == {"test": True}

    def test_get_swarm(self):
        """Test getting a swarm by ID."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.SEQUENTIAL)

        swarm = tracker.get_swarm("swarm-1")
        assert swarm is not None
        assert swarm.swarm_id == "swarm-1"

        missing = tracker.get_swarm("nonexistent")
        assert missing is None

    def test_complete_swarm(self):
        """Test completing a swarm."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)

        swarm = tracker.complete_swarm("swarm-1")
        assert swarm.status == SwarmStatus.COMPLETED
        assert swarm.overall_progress == 100
        assert swarm.completed_at is not None

    def test_complete_swarm_failed(self):
        """Test marking a swarm as failed."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)

        swarm = tracker.complete_swarm("swarm-1", status=SwarmStatus.FAILED)
        assert swarm.status == SwarmStatus.FAILED

    def test_complete_nonexistent_swarm_raises(self):
        """Test completing a nonexistent swarm raises error."""
        tracker = SwarmTracker()
        with pytest.raises(SwarmNotFoundError):
            tracker.complete_swarm("nonexistent")


class TestWorkerOperations:
    """Test worker-related operations."""

    def test_start_worker(self):
        """Test starting a worker."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)

        worker = tracker.start_worker(
            swarm_id="swarm-1",
            worker_id="worker-1",
            worker_name="Research Agent",
            worker_type=WorkerType.RESEARCH,
            role="Data Gatherer",
            current_task="Searching for data",
        )

        assert worker.worker_id == "worker-1"
        assert worker.worker_name == "Research Agent"
        assert worker.worker_type == WorkerType.RESEARCH
        assert worker.status == WorkerStatus.RUNNING
        assert worker.progress == 0
        assert worker.current_task == "Searching for data"
        assert worker.started_at is not None

    def test_start_worker_updates_swarm_status(self):
        """Test that starting a worker updates swarm status to running."""
        tracker = SwarmTracker()
        swarm = tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        assert swarm.status == SwarmStatus.INITIALIZING

        tracker.start_worker(
            swarm_id="swarm-1",
            worker_id="w-1",
            worker_name="Agent",
            worker_type=WorkerType.CUSTOM,
            role="Worker",
        )

        swarm = tracker.get_swarm("swarm-1")
        assert swarm.status == SwarmStatus.RUNNING

    def test_update_worker_progress(self):
        """Test updating worker progress."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        worker = tracker.update_worker_progress("swarm-1", "w-1", 50, "Processing")
        assert worker.progress == 50
        assert worker.current_task == "Processing"

    def test_update_worker_progress_clamps_values(self):
        """Test that progress values are clamped to 0-100."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        worker = tracker.update_worker_progress("swarm-1", "w-1", 150)
        assert worker.progress == 100

        worker = tracker.update_worker_progress("swarm-1", "w-1", -10)
        assert worker.progress == 0

    def test_complete_worker(self):
        """Test completing a worker."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        worker = tracker.complete_worker("swarm-1", "w-1")
        assert worker.status == WorkerStatus.COMPLETED
        assert worker.progress == 100
        assert worker.completed_at is not None

    def test_complete_worker_failed(self):
        """Test marking a worker as failed."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        worker = tracker.complete_worker(
            "swarm-1", "w-1",
            status=WorkerStatus.FAILED,
            error="Something went wrong"
        )
        assert worker.status == WorkerStatus.FAILED
        assert worker.error == "Something went wrong"

    def test_get_worker(self):
        """Test getting a worker by ID."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        worker = tracker.get_worker("swarm-1", "w-1")
        assert worker is not None
        assert worker.worker_id == "w-1"

        missing = tracker.get_worker("swarm-1", "nonexistent")
        assert missing is None


class TestThinkingAndToolCalls:
    """Test thinking and tool call operations."""

    def test_add_worker_thinking(self):
        """Test adding thinking content."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        thinking = tracker.add_worker_thinking(
            "swarm-1", "w-1",
            content="Analyzing the problem...",
            token_count=50,
        )

        assert thinking.content == "Analyzing the problem..."
        assert thinking.token_count == 50
        assert thinking.timestamp is not None

        worker = tracker.get_worker("swarm-1", "w-1")
        assert worker.status == WorkerStatus.THINKING
        assert len(worker.thinking_contents) == 1

    def test_add_worker_tool_call(self):
        """Test adding a tool call."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        tool_call = tracker.add_worker_tool_call(
            "swarm-1", "w-1",
            tool_id="tc-1",
            tool_name="web_search",
            is_mcp=True,
            input_params={"query": "test"},
        )

        assert tool_call.tool_id == "tc-1"
        assert tool_call.tool_name == "web_search"
        assert tool_call.is_mcp is True
        assert tool_call.status == "running"

        worker = tracker.get_worker("swarm-1", "w-1")
        assert worker.status == WorkerStatus.TOOL_CALLING
        assert len(worker.tool_calls) == 1

        swarm = tracker.get_swarm("swarm-1")
        assert swarm.total_tool_calls == 1

    def test_update_tool_call_result(self):
        """Test updating tool call with result."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")
        tracker.add_worker_tool_call(
            "swarm-1", "w-1", "tc-1", "search", False, {}
        )

        tool_call = tracker.update_tool_call_result(
            "swarm-1", "w-1", "tc-1",
            result={"data": "results"},
        )

        assert tool_call.status == "completed"
        assert tool_call.result == {"data": "results"}
        assert tool_call.completed_at is not None
        assert tool_call.duration_ms is not None

        swarm = tracker.get_swarm("swarm-1")
        assert swarm.completed_tool_calls == 1

    def test_update_tool_call_error(self):
        """Test updating tool call with error."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")
        tracker.add_worker_tool_call(
            "swarm-1", "w-1", "tc-1", "search", False, {}
        )

        tool_call = tracker.update_tool_call_result(
            "swarm-1", "w-1", "tc-1",
            error="Tool failed",
        )

        assert tool_call.status == "failed"
        assert tool_call.error == "Tool failed"

        # Failed tool calls should not increment completed count
        swarm = tracker.get_swarm("swarm-1")
        assert swarm.completed_tool_calls == 0

    def test_update_nonexistent_tool_call_raises(self):
        """Test updating a nonexistent tool call raises error."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        with pytest.raises(ToolCallNotFoundError):
            tracker.update_tool_call_result(
                "swarm-1", "w-1", "nonexistent",
                result={}
            )


class TestMessages:
    """Test message operations."""

    def test_add_worker_message(self):
        """Test adding a message."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")

        message = tracker.add_worker_message(
            "swarm-1", "w-1",
            role="assistant",
            content="Hello!",
        )

        assert message.role == "assistant"
        assert message.content == "Hello!"
        assert message.timestamp is not None

        worker = tracker.get_worker("swarm-1", "w-1")
        assert len(worker.messages) == 1


class TestProgressCalculation:
    """Test progress calculation."""

    def test_calculate_overall_progress_empty(self):
        """Test progress calculation with no workers."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)

        progress = tracker.calculate_overall_progress("swarm-1")
        assert progress == 0

    def test_calculate_overall_progress(self):
        """Test progress calculation with multiple workers."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent 1", WorkerType.CUSTOM, "R1")
        tracker.start_worker("swarm-1", "w-2", "Agent 2", WorkerType.CUSTOM, "R2")

        tracker.update_worker_progress("swarm-1", "w-1", 100)
        tracker.update_worker_progress("swarm-1", "w-2", 50)

        progress = tracker.calculate_overall_progress("swarm-1")
        assert progress == 75  # (100 + 50) / 2


class TestThreadSafety:
    """Test thread safety of SwarmTracker."""

    def test_concurrent_worker_updates(self):
        """Test concurrent updates to workers."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)

        # Create 10 workers
        for i in range(10):
            tracker.start_worker(
                "swarm-1", f"w-{i}", f"Agent {i}",
                WorkerType.CUSTOM, f"Role {i}"
            )

        def update_progress(worker_id: str):
            for progress in range(0, 101, 10):
                tracker.update_worker_progress("swarm-1", worker_id, progress)
                time.sleep(0.001)

        # Run concurrent updates
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(update_progress, f"w-{i}")
                for i in range(10)
            ]
            for f in futures:
                f.result()

        # All workers should be at 100%
        for i in range(10):
            worker = tracker.get_worker("swarm-1", f"w-{i}")
            assert worker.progress == 100

    def test_concurrent_swarm_creation(self):
        """Test creating multiple swarms concurrently."""
        tracker = SwarmTracker()

        def create_swarm(swarm_id: str):
            tracker.create_swarm(swarm_id, SwarmMode.PARALLEL)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(create_swarm, f"swarm-{i}")
                for i in range(20)
            ]
            for f in futures:
                f.result()

        # All swarms should exist
        swarms = tracker.list_swarms()
        assert len(swarms) == 20


class TestListOperations:
    """Test list operations."""

    def test_list_swarms(self):
        """Test listing all swarms."""
        tracker = SwarmTracker()
        tracker.create_swarm("s-1", SwarmMode.PARALLEL)
        tracker.create_swarm("s-2", SwarmMode.SEQUENTIAL)

        swarms = tracker.list_swarms()
        assert len(swarms) == 2

    def test_list_active_swarms(self):
        """Test listing active swarms."""
        tracker = SwarmTracker()
        tracker.create_swarm("s-1", SwarmMode.PARALLEL)
        tracker.create_swarm("s-2", SwarmMode.SEQUENTIAL)
        tracker.complete_swarm("s-2")

        active = tracker.list_active_swarms()
        assert len(active) == 1
        assert active[0].swarm_id == "s-1"

    def test_get_all_workers(self):
        """Test getting all workers in a swarm."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker("swarm-1", "w-1", "Agent 1", WorkerType.CUSTOM, "R1")
        tracker.start_worker("swarm-1", "w-2", "Agent 2", WorkerType.CUSTOM, "R2")

        workers = tracker.get_all_workers("swarm-1")
        assert len(workers) == 2

    def test_delete_swarm(self):
        """Test deleting a swarm."""
        tracker = SwarmTracker()
        tracker.create_swarm("s-1", SwarmMode.PARALLEL)

        result = tracker.delete_swarm("s-1")
        assert result is True

        swarm = tracker.get_swarm("s-1")
        assert swarm is None

        # Deleting nonexistent swarm returns False
        result = tracker.delete_swarm("nonexistent")
        assert result is False


class TestCallbacks:
    """Test callback functionality."""

    def test_swarm_update_callback(self):
        """Test that swarm update callback is called."""
        updates = []

        def on_swarm_update(swarm):
            updates.append(swarm.swarm_id)

        tracker = SwarmTracker(on_swarm_update=on_swarm_update)
        tracker.create_swarm("s-1", SwarmMode.PARALLEL)
        tracker.complete_swarm("s-1")

        assert "s-1" in updates
        assert len(updates) >= 2  # At least create and complete

    def test_worker_update_callback(self):
        """Test that worker update callback is called."""
        updates = []

        def on_worker_update(swarm_id, worker):
            updates.append((swarm_id, worker.worker_id))

        tracker = SwarmTracker(on_worker_update=on_worker_update)
        tracker.create_swarm("s-1", SwarmMode.PARALLEL)
        tracker.start_worker("s-1", "w-1", "Agent", WorkerType.CUSTOM, "Worker")
        tracker.update_worker_progress("s-1", "w-1", 50)

        assert ("s-1", "w-1") in updates
