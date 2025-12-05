# =============================================================================
# IPA Platform - Sub-Workflow Executor Tests
# =============================================================================
# Sprint 11: S11-2 SubWorkflowExecutor Tests
#
# Unit tests for sub-workflow execution including:
# - Sync, async, fire-and-forget, callback modes
# - Parallel and sequential batch execution
# - Status tracking and cancellation
# - Statistics and cleanup
# =============================================================================

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from src.domain.orchestration.nested import (
    SubWorkflowExecutor,
    SubWorkflowExecutionMode,
    SubExecutionState,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def executor():
    """Create a fresh SubWorkflowExecutor instance."""
    return SubWorkflowExecutor(max_concurrent=5, default_timeout=30.0)


@pytest.fixture
def sample_workflow_id():
    """Generate a sample workflow ID."""
    return uuid4()


# =============================================================================
# Execution State Tests
# =============================================================================


class TestSubExecutionState:
    """Tests for SubExecutionState."""

    def test_state_creation(self, sample_workflow_id):
        """Test execution state creation with defaults."""
        state = SubExecutionState(
            execution_id=uuid4(),
            sub_workflow_id=sample_workflow_id,
            mode=SubWorkflowExecutionMode.SYNC,
        )
        assert state.sub_workflow_id == sample_workflow_id
        assert state.mode == SubWorkflowExecutionMode.SYNC
        assert state.status == "pending"
        assert state.result is None

    def test_state_to_dict(self, sample_workflow_id):
        """Test state serialization."""
        state = SubExecutionState(
            execution_id=uuid4(),
            sub_workflow_id=sample_workflow_id,
            mode=SubWorkflowExecutionMode.ASYNC,
            status="running",
        )

        result = state.to_dict()
        assert "execution_id" in result
        assert "sub_workflow_id" in result
        assert result["mode"] == "async"
        assert result["status"] == "running"


# =============================================================================
# Sync Execution Tests
# =============================================================================


class TestSyncExecution:
    """Tests for synchronous sub-workflow execution."""

    @pytest.mark.asyncio
    async def test_sync_execute_success(self, executor, sample_workflow_id):
        """Test successful sync execution."""
        result = await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.SYNC,
        )

        assert result["status"] == "completed"
        assert result["mock"] is True  # Without engine, uses mock

    @pytest.mark.asyncio
    async def test_sync_execute_with_timeout(self, executor, sample_workflow_id):
        """Test sync execution with custom timeout."""
        result = await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.SYNC,
            timeout=5.0,
        )

        assert result["status"] == "completed"


# =============================================================================
# Async Execution Tests
# =============================================================================


class TestAsyncExecution:
    """Tests for asynchronous sub-workflow execution."""

    @pytest.mark.asyncio
    async def test_async_execute(self, executor, sample_workflow_id):
        """Test async execution returns immediately."""
        result = await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.ASYNC,
        )

        assert result["status"] == "started"
        assert "execution_id" in result

    @pytest.mark.asyncio
    async def test_async_wait_for_completion(self, executor, sample_workflow_id):
        """Test waiting for async execution completion."""
        result = await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.ASYNC,
        )

        execution_id = result["execution_id"]

        # Wait for completion
        await asyncio.sleep(0.2)

        status = await executor.get_execution_status(
            execution_id=executor._executions[list(executor._executions.keys())[0]].execution_id
        )
        assert status["status"] in ["completed", "running"]


# =============================================================================
# Fire and Forget Tests
# =============================================================================


class TestFireAndForget:
    """Tests for fire-and-forget execution."""

    @pytest.mark.asyncio
    async def test_fire_and_forget_execute(self, executor, sample_workflow_id):
        """Test fire-and-forget execution."""
        result = await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.FIRE_AND_FORGET,
        )

        assert result["status"] == "dispatched"
        assert result["mode"] == "fire_and_forget"


# =============================================================================
# Callback Execution Tests
# =============================================================================


class TestCallbackExecution:
    """Tests for callback-based execution."""

    @pytest.mark.asyncio
    async def test_callback_execute(self, executor, sample_workflow_id):
        """Test callback execution."""
        callback_result = {}

        async def callback(result):
            callback_result.update(result)

        result = await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.CALLBACK,
            callback=callback,
        )

        assert result["status"] == "started"

        # Wait for callback
        await asyncio.sleep(0.3)

        assert callback_result.get("status") == "completed"

    @pytest.mark.asyncio
    async def test_callback_required(self, executor, sample_workflow_id):
        """Test that callback is required for CALLBACK mode."""
        with pytest.raises(ValueError) as exc_info:
            await executor.execute(
                sub_workflow_id=sample_workflow_id,
                inputs={"test": "data"},
                mode=SubWorkflowExecutionMode.CALLBACK,
            )

        assert "requires a callback function" in str(exc_info.value)


# =============================================================================
# Batch Execution Tests
# =============================================================================


class TestBatchExecution:
    """Tests for batch sub-workflow execution."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self, executor):
        """Test parallel batch execution."""
        sub_workflows = [
            {"id": uuid4(), "inputs": {"step": i}}
            for i in range(3)
        ]

        results = await executor.execute_parallel(
            sub_workflows=sub_workflows,
            timeout=30.0,
        )

        assert len(results) == 3
        for result in results:
            assert result.get("status") == "completed"

    @pytest.mark.asyncio
    async def test_sequential_execution(self, executor):
        """Test sequential batch execution."""
        sub_workflows = [
            {"id": uuid4(), "inputs": {"step": i}}
            for i in range(3)
        ]

        results = await executor.execute_sequential(
            sub_workflows=sub_workflows,
            pass_outputs=True,
            stop_on_error=True,
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_sequential_with_output_passing(self, executor):
        """Test sequential execution with output passing."""
        sub_workflows = [
            {"id": uuid4(), "inputs": {"value": 1}},
            {"id": uuid4(), "inputs": {"multiplier": 2}},
        ]

        results = await executor.execute_sequential(
            sub_workflows=sub_workflows,
            pass_outputs=True,
        )

        assert len(results) == 2


# =============================================================================
# Status and Management Tests
# =============================================================================


class TestStatusManagement:
    """Tests for status tracking and management."""

    @pytest.mark.asyncio
    async def test_get_execution_status(self, executor, sample_workflow_id):
        """Test getting execution status."""
        await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.SYNC,
        )

        # Get first execution
        execution_id = list(executor._executions.keys())[0]
        status = await executor.get_execution_status(execution_id)

        assert status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_nonexistent_status(self, executor):
        """Test getting status for nonexistent execution."""
        status = await executor.get_execution_status(uuid4())
        assert "error" in status

    @pytest.mark.asyncio
    async def test_cancel_execution(self, executor, sample_workflow_id):
        """Test cancelling an async execution."""
        result = await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.ASYNC,
        )

        # Get execution ID from internal storage
        execution_id = list(executor._async_tasks.keys())[0] if executor._async_tasks else None

        if execution_id:
            success = await executor.cancel_execution(execution_id)
            # May already be completed
            assert isinstance(success, bool)

    def test_get_active_executions(self, executor):
        """Test getting active executions."""
        active = executor.get_active_executions()
        assert isinstance(active, list)

    def test_get_all_executions(self, executor):
        """Test getting all executions."""
        all_execs = executor.get_all_executions()
        assert isinstance(all_execs, list)

    def test_get_all_executions_with_filter(self, executor):
        """Test getting executions with status filter."""
        completed = executor.get_all_executions(status_filter="completed")
        assert isinstance(completed, list)


# =============================================================================
# Cleanup Tests
# =============================================================================


class TestCleanup:
    """Tests for execution cleanup."""

    @pytest.mark.asyncio
    async def test_clear_completed(self, executor, sample_workflow_id):
        """Test clearing completed executions."""
        # Create and complete some executions
        for _ in range(5):
            await executor.execute(
                sub_workflow_id=sample_workflow_id,
                inputs={"test": "data"},
                mode=SubWorkflowExecutionMode.SYNC,
            )

        initial_count = len(executor._executions)
        assert initial_count >= 5

        # Clear with 0 seconds threshold (immediate)
        cleared = executor.clear_completed(older_than_seconds=0)

        # All completed should be cleared
        assert cleared == initial_count


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for executor statistics."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, executor, sample_workflow_id):
        """Test getting executor statistics."""
        # Create some executions
        await executor.execute(
            sub_workflow_id=sample_workflow_id,
            inputs={"test": "data"},
            mode=SubWorkflowExecutionMode.SYNC,
        )

        stats = executor.get_statistics()

        assert "total_executions" in stats
        assert "active_tasks" in stats
        assert "by_status" in stats
        assert "by_mode" in stats
        assert "average_duration_seconds" in stats
        assert "max_concurrent" in stats

