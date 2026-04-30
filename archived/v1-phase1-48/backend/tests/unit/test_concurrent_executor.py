# =============================================================================
# IPA Platform - Concurrent Executor Unit Tests
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Tests for the concurrent executor including:
#   - ConcurrentMode enumeration
#   - ConcurrentTask data structure
#   - ConcurrentResult data structure
#   - ConcurrentExecutor execution modes (ALL, ANY, MAJORITY, FIRST_SUCCESS)
#   - Concurrency control and timeout handling
# =============================================================================

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.domain.workflows.executors.concurrent import (
    ConcurrentExecutor,
    ConcurrentMode,
    ConcurrentTask,
    ConcurrentResult,
    create_all_executor,
    create_any_executor,
    create_majority_executor,
    create_first_success_executor,
)


# =============================================================================
# ConcurrentMode Tests
# =============================================================================


class TestConcurrentMode:
    """Tests for ConcurrentMode enum."""

    def test_mode_values(self):
        """Test all mode enum values."""
        assert ConcurrentMode.ALL.value == "all"
        assert ConcurrentMode.ANY.value == "any"
        assert ConcurrentMode.MAJORITY.value == "majority"
        assert ConcurrentMode.FIRST_SUCCESS.value == "first_success"

    def test_mode_from_string(self):
        """Test creating mode from string."""
        assert ConcurrentMode("all") == ConcurrentMode.ALL
        assert ConcurrentMode("any") == ConcurrentMode.ANY
        assert ConcurrentMode("majority") == ConcurrentMode.MAJORITY
        assert ConcurrentMode("first_success") == ConcurrentMode.FIRST_SUCCESS


# =============================================================================
# ConcurrentTask Tests
# =============================================================================


class TestConcurrentTask:
    """Tests for ConcurrentTask dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        task = ConcurrentTask(
            id="task-1",
            executor_id="agent-001",
        )

        assert task.id == "task-1"
        assert task.executor_id == "agent-001"
        assert task.input_data == {}
        assert task.timeout is None
        assert task.priority == 0

    def test_initialization_with_data(self):
        """Test initialization with input data."""
        task = ConcurrentTask(
            id="analyze-task",
            executor_id="analysis-agent",
            input_data={"document": "report.pdf", "type": "financial"},
            timeout=60,
            priority=5,
            metadata={"source": "api"},
        )

        assert task.id == "analyze-task"
        assert task.executor_id == "analysis-agent"
        assert task.input_data["document"] == "report.pdf"
        assert task.timeout == 60
        assert task.priority == 5
        assert task.metadata["source"] == "api"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        task = ConcurrentTask(
            id="task-1",
            executor_id="agent-1",
            input_data={"key": "value"},
            timeout=30,
        )

        result = task.to_dict()

        assert result["id"] == "task-1"
        assert result["executor_id"] == "agent-1"
        assert result["input_data"]["key"] == "value"
        assert result["timeout"] == 30


# =============================================================================
# ConcurrentResult Tests
# =============================================================================


class TestConcurrentResult:
    """Tests for ConcurrentResult dataclass."""

    def test_successful_result(self):
        """Test successful result."""
        result = ConcurrentResult(
            task_id="task-1",
            success=True,
            result={"output": "processed data"},
            duration_ms=1500,
        )

        assert result.task_id == "task-1"
        assert result.success is True
        assert result.result["output"] == "processed data"
        assert result.error is None
        assert result.duration_ms == 1500

    def test_failed_result(self):
        """Test failed result."""
        result = ConcurrentResult(
            task_id="task-2",
            success=False,
            error="Connection timeout",
            duration_ms=30000,
        )

        assert result.task_id == "task-2"
        assert result.success is False
        assert result.result is None
        assert result.error == "Connection timeout"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        now = datetime.utcnow()
        result = ConcurrentResult(
            task_id="task-1",
            success=True,
            result="data",
            started_at=now,
            completed_at=now,
            duration_ms=100,
        )

        data = result.to_dict()

        assert data["task_id"] == "task-1"
        assert data["success"] is True
        assert data["result"] == "data"
        assert data["duration_ms"] == 100


# =============================================================================
# ConcurrentExecutor Tests
# =============================================================================


class TestConcurrentExecutor:
    """Tests for ConcurrentExecutor class."""

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            ConcurrentTask(id="task1", executor_id="agent1"),
            ConcurrentTask(id="task2", executor_id="agent2"),
            ConcurrentTask(id="task3", executor_id="agent3"),
        ]

    @pytest.fixture
    def successful_executor_fn(self):
        """Create executor function that always succeeds."""
        async def executor(task: ConcurrentTask):
            await asyncio.sleep(0.01)  # Small delay
            return {"task_id": task.id, "status": "completed"}
        return executor

    @pytest.fixture
    def mixed_executor_fn(self):
        """Create executor function with mixed results."""
        results = {"task1": True, "task2": False, "task3": True}

        async def executor(task: ConcurrentTask):
            await asyncio.sleep(0.01)
            if not results.get(task.id, True):
                raise Exception(f"Task {task.id} failed")
            return {"task_id": task.id, "status": "completed"}
        return executor

    def test_initialization(self, sample_tasks):
        """Test executor initialization."""
        executor = ConcurrentExecutor(
            id="test-executor",
            tasks=sample_tasks,
            mode=ConcurrentMode.ALL,
            max_concurrency=5,
            timeout=60,
        )

        assert executor.id == "test-executor"
        assert executor.mode == ConcurrentMode.ALL
        assert len(executor.tasks) == 3

    def test_initialization_with_limits(self, sample_tasks):
        """Test initialization enforces limits."""
        # Max concurrency capped at 100
        executor = ConcurrentExecutor(
            id="test",
            tasks=sample_tasks,
            max_concurrency=200,
        )
        assert executor._max_concurrency == 100

        # Timeout capped at 3600
        executor2 = ConcurrentExecutor(
            id="test2",
            tasks=sample_tasks,
            timeout=5000,
        )
        assert executor2._timeout == 3600

    @pytest.mark.asyncio
    async def test_execute_all_mode(self, sample_tasks, successful_executor_fn):
        """Test ALL mode - wait for all tasks."""
        executor = ConcurrentExecutor(
            id="all-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.ALL,
        )

        result = await executor.execute(successful_executor_fn)

        assert result["mode"] == "all"
        assert result["total_tasks"] == 3
        assert result["completed_tasks"] == 3
        assert result["failed_tasks"] == 0
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_execute_all_mode_with_failures(self, sample_tasks, mixed_executor_fn):
        """Test ALL mode with some failures."""
        executor = ConcurrentExecutor(
            id="all-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.ALL,
        )

        result = await executor.execute(mixed_executor_fn)

        assert result["total_tasks"] == 3
        assert result["completed_tasks"] == 2
        assert result["failed_tasks"] == 1
        assert "task2" in result["errors"]

    @pytest.mark.asyncio
    async def test_execute_any_mode(self, sample_tasks, successful_executor_fn):
        """Test ANY mode - return on first completion."""
        executor = ConcurrentExecutor(
            id="any-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.ANY,
        )

        result = await executor.execute(successful_executor_fn)

        assert result["mode"] == "any"
        # At least one task should complete
        assert result["completed_tasks"] >= 1

    @pytest.mark.asyncio
    async def test_execute_first_success_mode(self, sample_tasks):
        """Test FIRST_SUCCESS mode."""
        # First two tasks fail, third succeeds
        call_count = {"count": 0}

        async def executor(task: ConcurrentTask):
            call_count["count"] += 1
            await asyncio.sleep(0.01 * call_count["count"])
            if task.id in ["task1", "task2"]:
                raise Exception("Planned failure")
            return {"status": "success"}

        executor_obj = ConcurrentExecutor(
            id="first-success-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.FIRST_SUCCESS,
        )

        result = await executor_obj.execute(executor)

        # Should have at least one success
        assert result["completed_tasks"] >= 1 or result["failed_tasks"] == 3

    @pytest.mark.asyncio
    async def test_execute_majority_mode(self, sample_tasks, successful_executor_fn):
        """Test MAJORITY mode - return when majority completes."""
        executor = ConcurrentExecutor(
            id="majority-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.MAJORITY,
        )

        result = await executor.execute(successful_executor_fn)

        assert result["mode"] == "majority"
        # Majority of 3 is 2
        assert result["completed_tasks"] + result["failed_tasks"] >= 2

    @pytest.mark.asyncio
    async def test_task_timeout(self):
        """Test task-level timeout handling."""
        async def slow_executor(task: ConcurrentTask):
            await asyncio.sleep(5)  # Will timeout
            return {"status": "completed"}

        tasks = [
            ConcurrentTask(id="slow-task", executor_id="slow-agent", timeout=0.1)
        ]

        executor = ConcurrentExecutor(
            id="timeout-test",
            tasks=tasks,
            mode=ConcurrentMode.ALL,
            timeout=1,  # Global timeout
        )

        result = await executor.execute(slow_executor)

        assert result["failed_tasks"] == 1
        assert "slow-task" in result["errors"]
        assert "timeout" in result["errors"]["slow-task"].lower()

    @pytest.mark.asyncio
    async def test_get_results(self, sample_tasks, successful_executor_fn):
        """Test getting results after execution."""
        executor = ConcurrentExecutor(
            id="results-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.ALL,
        )

        await executor.execute(successful_executor_fn)

        results = executor.get_results()
        assert len(results) == 3
        assert all(r.success for r in results.values())

    @pytest.mark.asyncio
    async def test_get_successful_results(self, sample_tasks, mixed_executor_fn):
        """Test getting only successful results."""
        executor = ConcurrentExecutor(
            id="success-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.ALL,
        )

        await executor.execute(mixed_executor_fn)

        successful = executor.get_successful_results()
        assert len(successful) == 2  # task1 and task3 succeed

    @pytest.mark.asyncio
    async def test_get_failed_results(self, sample_tasks, mixed_executor_fn):
        """Test getting only failed results."""
        executor = ConcurrentExecutor(
            id="failed-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.ALL,
        )

        await executor.execute(mixed_executor_fn)

        failed = executor.get_failed_results()
        assert len(failed) == 1
        assert "task2" in failed

    def test_to_dict(self, sample_tasks):
        """Test serialization to dictionary."""
        executor = ConcurrentExecutor(
            id="dict-test",
            tasks=sample_tasks,
            mode=ConcurrentMode.ALL,
            max_concurrency=5,
        )

        data = executor.to_dict()

        assert data["id"] == "dict-test"
        assert data["mode"] == "all"
        assert len(data["tasks"]) == 3
        assert data["max_concurrency"] == 5


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for executor factory functions."""

    @pytest.fixture
    def sample_tasks(self):
        return [
            ConcurrentTask(id="t1", executor_id="a1"),
            ConcurrentTask(id="t2", executor_id="a2"),
        ]

    def test_create_all_executor(self, sample_tasks):
        """Test create_all_executor factory."""
        executor = create_all_executor("test", sample_tasks)
        assert executor.mode == ConcurrentMode.ALL

    def test_create_any_executor(self, sample_tasks):
        """Test create_any_executor factory."""
        executor = create_any_executor("test", sample_tasks)
        assert executor.mode == ConcurrentMode.ANY

    def test_create_majority_executor(self, sample_tasks):
        """Test create_majority_executor factory."""
        executor = create_majority_executor("test", sample_tasks)
        assert executor.mode == ConcurrentMode.MAJORITY

    def test_create_first_success_executor(self, sample_tasks):
        """Test create_first_success_executor factory."""
        executor = create_first_success_executor("test", sample_tasks)
        assert executor.mode == ConcurrentMode.FIRST_SUCCESS


# =============================================================================
# Concurrency Control Tests
# =============================================================================


class TestConcurrencyControl:
    """Tests for concurrency control."""

    @pytest.mark.asyncio
    async def test_max_concurrency_limit(self):
        """Test that max_concurrency limits parallel execution."""
        concurrent_count = {"max": 0, "current": 0}

        async def counting_executor(task: ConcurrentTask):
            concurrent_count["current"] += 1
            if concurrent_count["current"] > concurrent_count["max"]:
                concurrent_count["max"] = concurrent_count["current"]
            await asyncio.sleep(0.05)
            concurrent_count["current"] -= 1
            return {"status": "ok"}

        tasks = [ConcurrentTask(id=f"t{i}", executor_id=f"a{i}") for i in range(10)]

        executor = ConcurrentExecutor(
            id="concurrency-test",
            tasks=tasks,
            mode=ConcurrentMode.ALL,
            max_concurrency=3,
        )

        await executor.execute(counting_executor)

        # Max concurrent should not exceed limit
        assert concurrent_count["max"] <= 3
