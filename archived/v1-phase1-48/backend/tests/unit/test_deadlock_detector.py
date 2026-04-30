# =============================================================================
# IPA Platform - Deadlock Detector Unit Tests
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Tests for deadlock detection and timeout handling including:
#   - WaitingTask data structure
#   - DeadlockDetector cycle detection
#   - TimeoutHandler operations
#   - Resolution strategies
# =============================================================================

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.workflows.deadlock_detector import (
    DeadlockDetector,
    DeadlockInfo,
    DeadlockResolutionStrategy,
    TimeoutHandler,
    WaitingTask,
    get_deadlock_detector,
    reset_deadlock_detector,
)


# =============================================================================
# WaitingTask Tests
# =============================================================================


class TestWaitingTask:
    """Tests for WaitingTask dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        task = WaitingTask(
            task_id="task-A",
            waiting_for={"task-B", "task-C"},
        )

        assert task.task_id == "task-A"
        assert "task-B" in task.waiting_for
        assert "task-C" in task.waiting_for
        assert task.timeout == 300  # Default

    def test_elapsed_seconds(self):
        """Test elapsed time calculation."""
        task = WaitingTask(
            task_id="test",
            waiting_for=set(),
            started_at=datetime.utcnow() - timedelta(seconds=10),
        )

        assert task.elapsed_seconds >= 10

    def test_is_timed_out(self):
        """Test timeout detection."""
        # Not timed out
        task1 = WaitingTask(
            task_id="recent",
            waiting_for=set(),
            timeout=60,
        )
        assert not task1.is_timed_out

        # Timed out
        task2 = WaitingTask(
            task_id="old",
            waiting_for=set(),
            started_at=datetime.utcnow() - timedelta(seconds=120),
            timeout=60,
        )
        assert task2.is_timed_out

    def test_remaining_seconds(self):
        """Test remaining time calculation."""
        task = WaitingTask(
            task_id="test",
            waiting_for=set(),
            started_at=datetime.utcnow() - timedelta(seconds=50),
            timeout=60,
        )

        assert 0 < task.remaining_seconds <= 10

    def test_to_dict(self):
        """Test serialization."""
        task = WaitingTask(
            task_id="task-A",
            waiting_for={"task-B"},
            timeout=120,
            priority=5,
        )

        data = task.to_dict()

        assert data["task_id"] == "task-A"
        assert "task-B" in data["waiting_for"]
        assert data["timeout"] == 120
        assert data["priority"] == 5


# =============================================================================
# DeadlockInfo Tests
# =============================================================================


class TestDeadlockInfo:
    """Tests for DeadlockInfo dataclass."""

    def test_initialization(self):
        """Test basic initialization."""
        info = DeadlockInfo(cycle=["A", "B", "C"])

        assert info.cycle == ["A", "B", "C"]
        assert not info.resolved
        assert info.detected_at is not None

    def test_to_dict(self):
        """Test serialization."""
        info = DeadlockInfo(
            cycle=["A", "B"],
            resolved=True,
            resolution_action="cancel_youngest",
            cancelled_task="B",
        )

        data = info.to_dict()

        assert data["cycle"] == ["A", "B"]
        assert data["resolved"] is True
        assert data["resolution_action"] == "cancel_youngest"


# =============================================================================
# DeadlockDetector Tests
# =============================================================================


class TestDeadlockDetector:
    """Tests for DeadlockDetector class."""

    @pytest.fixture
    def detector(self):
        """Create fresh detector for each test."""
        reset_deadlock_detector()
        return DeadlockDetector()

    def test_initialization(self):
        """Test detector initialization."""
        detector = DeadlockDetector(
            check_interval=10,
            resolution_strategy=DeadlockResolutionStrategy.CANCEL_ALL,
        )

        assert detector._check_interval == 10
        assert detector._resolution_strategy == DeadlockResolutionStrategy.CANCEL_ALL

    def test_register_waiting(self, detector):
        """Test registering waiting tasks."""
        detector.register_waiting("A", {"B", "C"}, timeout=60, priority=5)

        tasks = detector.get_all_waiting_tasks()
        assert "A" in tasks
        assert tasks["A"].waiting_for == {"B", "C"}
        assert tasks["A"].timeout == 60
        assert tasks["A"].priority == 5

    def test_unregister(self, detector):
        """Test unregistering tasks."""
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", set())

        assert detector.unregister("A") is True
        assert detector.unregister("A") is False  # Already removed

        tasks = detector.get_all_waiting_tasks()
        assert "A" not in tasks
        assert "B" in tasks

    def test_update_waiting_for(self, detector):
        """Test updating task dependencies."""
        detector.register_waiting("A", {"B", "C"})
        detector.update_waiting_for("A", {"D"})

        tasks = detector.get_all_waiting_tasks()
        assert tasks["A"].waiting_for == {"D"}

    def test_remove_dependency(self, detector):
        """Test removing a single dependency."""
        detector.register_waiting("A", {"B", "C"})

        detector.remove_dependency("A", "B")
        tasks = detector.get_all_waiting_tasks()
        assert tasks["A"].waiting_for == {"C"}

        # Removing last dependency unregisters task
        detector.remove_dependency("A", "C")
        assert "A" not in detector.get_all_waiting_tasks()

    def test_no_deadlock(self, detector):
        """Test detection when no deadlock exists."""
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", {"C"})
        detector.register_waiting("C", set())

        cycle = detector.detect_deadlock()
        assert cycle is None

    def test_simple_deadlock(self, detector):
        """Test detection of simple A->B->A deadlock."""
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", {"A"})

        cycle = detector.detect_deadlock()
        assert cycle is not None
        assert "A" in cycle
        assert "B" in cycle

    def test_three_way_deadlock(self, detector):
        """Test detection of A->B->C->A deadlock."""
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", {"C"})
        detector.register_waiting("C", {"A"})

        cycle = detector.detect_deadlock()
        assert cycle is not None
        assert len(cycle) == 3
        assert "A" in cycle
        assert "B" in cycle
        assert "C" in cycle

    def test_complex_graph_no_deadlock(self, detector):
        """Test complex graph without deadlock."""
        # Diamond pattern: A -> B,C -> D
        detector.register_waiting("A", {"B", "C"})
        detector.register_waiting("B", {"D"})
        detector.register_waiting("C", {"D"})
        detector.register_waiting("D", set())

        cycle = detector.detect_deadlock()
        assert cycle is None

    def test_deadlock_in_complex_graph(self, detector):
        """Test deadlock in complex graph."""
        # A -> B -> C, but also D -> E -> D (deadlock)
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", {"C"})
        detector.register_waiting("D", {"E"})
        detector.register_waiting("E", {"D"})

        cycle = detector.detect_deadlock()
        assert cycle is not None
        # Should find D-E cycle
        assert "D" in cycle or "E" in cycle

    def test_get_timed_out_tasks(self, detector):
        """Test getting timed out tasks."""
        detector.register_waiting("recent", set(), timeout=60)
        detector.register_waiting(
            "old",
            set(),
            timeout=1,
        )
        # Manually set old start time
        detector._waiting_tasks["old"].started_at = datetime.utcnow() - timedelta(seconds=10)

        timed_out = detector.get_timed_out_tasks()
        assert len(timed_out) == 1
        assert timed_out[0].task_id == "old"

    def test_get_tasks_near_timeout(self, detector):
        """Test getting tasks near timeout."""
        detector.register_waiting("far", set(), timeout=120)
        detector.register_waiting("near", set(), timeout=60)

        # Set near task to be 50 seconds in
        detector._waiting_tasks["near"].started_at = datetime.utcnow() - timedelta(seconds=50)

        near = detector.get_tasks_near_timeout(threshold_seconds=15)
        assert len(near) == 1
        assert near[0].task_id == "near"

    def test_get_statistics(self, detector):
        """Test statistics gathering."""
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", {"A"})

        stats = detector.get_statistics()
        assert stats["waiting_tasks"] == 2
        assert stats["is_monitoring"] is False

    def test_deadlock_history(self, detector):
        """Test deadlock history tracking."""
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", {"A"})

        # Detect deadlock
        cycle = detector.detect_deadlock()
        if cycle:
            detector._deadlock_history.append(DeadlockInfo(cycle=cycle))

        history = detector.get_deadlock_history()
        assert len(history) == 1

        detector.clear_history()
        assert len(detector.get_deadlock_history()) == 0


# =============================================================================
# DeadlockResolutionStrategy Tests
# =============================================================================


class TestDeadlockResolutionStrategy:
    """Tests for DeadlockResolutionStrategy enum."""

    def test_strategy_values(self):
        """Test all strategy values."""
        assert DeadlockResolutionStrategy.CANCEL_YOUNGEST.value == "cancel_youngest"
        assert DeadlockResolutionStrategy.CANCEL_OLDEST.value == "cancel_oldest"
        assert DeadlockResolutionStrategy.CANCEL_ALL.value == "cancel_all"
        assert DeadlockResolutionStrategy.CANCEL_LOWEST_PRIORITY.value == "cancel_lowest_priority"
        assert DeadlockResolutionStrategy.NOTIFY_ONLY.value == "notify_only"


# =============================================================================
# TimeoutHandler Tests
# =============================================================================


class TestTimeoutHandler:
    """Tests for TimeoutHandler class."""

    @pytest.mark.asyncio
    async def test_handle_task_timeout(self):
        """Test handling task timeout."""
        cleanup_called = {"value": False}

        async def cleanup(task_id: str):
            cleanup_called["value"] = True

        result = await TimeoutHandler.handle_task_timeout(
            execution_id=uuid4(),
            task_id="slow-task",
            cleanup_fn=cleanup,
        )

        assert result["task_id"] == "slow-task"
        assert result["status"] == "timeout"
        assert cleanup_called["value"] is True
        assert result["cleanup_status"] == "success"

    @pytest.mark.asyncio
    async def test_handle_task_timeout_with_notification(self):
        """Test handling with notification."""
        notified = {"value": False}

        async def notify(data: dict):
            notified["value"] = True

        result = await TimeoutHandler.handle_task_timeout(
            execution_id=uuid4(),
            task_id="task-1",
            notify_fn=notify,
        )

        assert result["notification_sent"] is True
        assert notified["value"] is True

    @pytest.mark.asyncio
    async def test_handle_task_timeout_cleanup_failure(self):
        """Test handling cleanup failure."""
        async def failing_cleanup(task_id: str):
            raise Exception("Cleanup failed")

        result = await TimeoutHandler.handle_task_timeout(
            execution_id=uuid4(),
            task_id="task-1",
            cleanup_fn=failing_cleanup,
        )

        assert result["cleanup_status"] == "failed"
        assert "cleanup_error" in result

    @pytest.mark.asyncio
    async def test_handle_execution_timeout(self):
        """Test handling execution timeout."""
        cancelled = {"value": False}
        cleaned = {"value": False}

        async def cancel():
            cancelled["value"] = True

        async def cleanup():
            cleaned["value"] = True

        result = await TimeoutHandler.handle_execution_timeout(
            execution_id=uuid4(),
            cancel_fn=cancel,
            cleanup_fn=cleanup,
        )

        assert result["status"] == "execution_timeout"
        assert cancelled["value"] is True
        assert cleaned["value"] is True

    @pytest.mark.asyncio
    async def test_handle_deadlock(self):
        """Test handling deadlock."""
        cancelled_tasks = []

        async def cancel(task_id: str):
            cancelled_tasks.append(task_id)

        result = await TimeoutHandler.handle_deadlock(
            execution_id=uuid4(),
            cycle=["A", "B", "C"],
            resolution_strategy=DeadlockResolutionStrategy.CANCEL_YOUNGEST,
            cancel_fn=cancel,
        )

        assert result["deadlock_detected"] is True
        assert result["cycle"] == ["A", "B", "C"]
        assert result["cancelled_task"] == "C"  # Youngest (last in cycle)
        assert "C" in cancelled_tasks

    @pytest.mark.asyncio
    async def test_handle_deadlock_cancel_all(self):
        """Test deadlock with cancel all strategy."""
        cancelled_tasks = []

        async def cancel(task_id: str):
            cancelled_tasks.append(task_id)

        result = await TimeoutHandler.handle_deadlock(
            execution_id=uuid4(),
            cycle=["A", "B"],
            resolution_strategy=DeadlockResolutionStrategy.CANCEL_ALL,
            cancel_fn=cancel,
        )

        assert "A" in cancelled_tasks
        assert "B" in cancelled_tasks


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_deadlock_detector_singleton(self):
        """Test singleton returns same instance."""
        reset_deadlock_detector()
        d1 = get_deadlock_detector()
        d2 = get_deadlock_detector()
        assert d1 is d2

    def test_reset_deadlock_detector(self):
        """Test reset creates new instance."""
        d1 = get_deadlock_detector()
        reset_deadlock_detector()
        d2 = get_deadlock_detector()
        assert d1 is not d2


# =============================================================================
# Integration Tests
# =============================================================================


class TestDeadlockDetectorIntegration:
    """Integration tests for deadlock detection."""

    @pytest.fixture
    def detector(self):
        reset_deadlock_detector()
        return DeadlockDetector(check_interval=1)

    @pytest.mark.asyncio
    async def test_monitoring_detects_deadlock(self, detector):
        """Test continuous monitoring detects deadlock."""
        deadlocks_found = []

        async def on_deadlock(cycle):
            deadlocks_found.append(cycle)

        # Start monitoring in background
        monitoring_task = asyncio.create_task(
            detector.start_monitoring(on_deadlock=on_deadlock)
        )

        # Create deadlock
        await asyncio.sleep(0.1)
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", {"A"})

        # Wait for detection
        await asyncio.sleep(1.5)

        # Stop monitoring
        detector.stop_monitoring()
        await asyncio.sleep(0.1)
        monitoring_task.cancel()

        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

        assert len(deadlocks_found) >= 1

    @pytest.mark.asyncio
    async def test_monitoring_handles_timeout(self, detector):
        """Test monitoring handles timeouts."""
        timed_out_tasks = []

        async def on_timeout(task):
            timed_out_tasks.append(task.task_id)

        # Register task with very short timeout
        detector.register_waiting("quick", set(), timeout=1)

        # Start monitoring
        monitoring_task = asyncio.create_task(
            detector.start_monitoring(on_timeout=on_timeout)
        )

        # Wait for timeout
        await asyncio.sleep(2.5)

        detector.stop_monitoring()
        await asyncio.sleep(0.1)
        monitoring_task.cancel()

        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

        assert "quick" in timed_out_tasks
