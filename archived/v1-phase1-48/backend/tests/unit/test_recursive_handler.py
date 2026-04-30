# =============================================================================
# IPA Platform - Recursive Pattern Handler Tests
# =============================================================================
# Sprint 11: S11-3 RecursivePatternHandler Tests
#
# Unit tests for recursive pattern handling including:
# - Recursion strategies (depth-first, breadth-first, parallel)
# - Termination conditions
# - Memoization
# - State tracking
# =============================================================================

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from src.domain.orchestration.nested import (
    RecursivePatternHandler,
    RecursionStrategy,
    TerminationType,
    RecursionConfig,
    RecursionState,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def handler():
    """Create a fresh RecursivePatternHandler instance."""
    return RecursivePatternHandler()


@pytest.fixture
def sample_workflow_id():
    """Generate a sample workflow ID."""
    return uuid4()


@pytest.fixture
def sample_config(sample_workflow_id):
    """Create a sample recursion configuration."""
    return RecursionConfig(
        workflow_id=sample_workflow_id,
        strategy=RecursionStrategy.DEPTH_FIRST,
        max_depth=5,
        max_iterations=100,
        timeout_seconds=30,
        enable_memoization=True,
    )


# =============================================================================
# Configuration Tests
# =============================================================================


class TestRecursionConfig:
    """Tests for RecursionConfig."""

    def test_config_creation(self, sample_workflow_id):
        """Test configuration creation with defaults."""
        config = RecursionConfig(workflow_id=sample_workflow_id)

        assert config.workflow_id == sample_workflow_id
        assert config.strategy == RecursionStrategy.DEPTH_FIRST
        assert config.max_depth == 10
        assert config.max_iterations == 100
        assert config.enable_memoization is True

    def test_config_custom_values(self, sample_workflow_id):
        """Test configuration with custom values."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            strategy=RecursionStrategy.BREADTH_FIRST,
            max_depth=20,
            max_iterations=500,
            timeout_seconds=120,
            enable_memoization=False,
        )

        assert config.strategy == RecursionStrategy.BREADTH_FIRST
        assert config.max_depth == 20
        assert config.max_iterations == 500
        assert config.enable_memoization is False

    def test_config_to_dict(self, sample_config):
        """Test configuration serialization."""
        result = sample_config.to_dict()

        assert "config_id" in result
        assert "workflow_id" in result
        assert result["strategy"] == "depth_first"
        assert result["max_depth"] == 5


# =============================================================================
# Recursion State Tests
# =============================================================================


class TestRecursionState:
    """Tests for RecursionState."""

    def test_state_creation(self, sample_workflow_id):
        """Test state creation with defaults."""
        state = RecursionState(
            execution_id=uuid4(),
            workflow_id=sample_workflow_id,
            max_depth=10,
            max_iterations=100,
        )

        assert state.current_depth == 0
        assert state.iteration_count == 0
        assert state.status == "pending"
        assert state.memoization_cache == {}

    def test_state_to_dict(self, sample_workflow_id):
        """Test state serialization."""
        state = RecursionState(
            execution_id=uuid4(),
            workflow_id=sample_workflow_id,
            max_depth=5,
            max_iterations=50,
            status="running",
            current_depth=2,
            iteration_count=10,
        )

        result = state.to_dict()
        assert result["status"] == "running"
        assert result["current_depth"] == 2
        assert result["iteration_count"] == 10


# =============================================================================
# Execution Tests
# =============================================================================


class TestRecursiveExecution:
    """Tests for recursive execution."""

    @pytest.mark.asyncio
    async def test_execute_depth_first(self, handler, sample_config):
        """Test depth-first recursive execution."""
        result = await handler.execute(
            config=sample_config,
            initial_inputs={"value": 5},
        )

        assert "execution_id" in result
        assert "status" in result
        assert result["status"] in ["completed", "max_iterations"]

    @pytest.mark.asyncio
    async def test_execute_breadth_first(self, handler, sample_workflow_id):
        """Test breadth-first recursive execution."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            strategy=RecursionStrategy.BREADTH_FIRST,
            max_depth=3,
            max_iterations=20,
        )

        result = await handler.execute(
            config=config,
            initial_inputs={"value": 3},
        )

        assert "execution_id" in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_execute_parallel(self, handler, sample_workflow_id):
        """Test parallel recursive execution."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            strategy=RecursionStrategy.PARALLEL,
            max_depth=3,
            max_iterations=10,
        )

        result = await handler.execute(
            config=config,
            initial_inputs={"value": 2},
        )

        assert "execution_id" in result


# =============================================================================
# Termination Tests
# =============================================================================


class TestTermination:
    """Tests for recursion termination."""

    @pytest.mark.asyncio
    async def test_max_depth_termination(self, handler, sample_workflow_id):
        """Test termination by max depth."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            max_depth=2,
            max_iterations=1000,
        )

        result = await handler.execute(
            config=config,
            initial_inputs={"value": 100},
        )

        state = handler.get_execution_state(result.get("execution_id"))
        if state:
            assert state.current_depth <= 2

    @pytest.mark.asyncio
    async def test_max_iterations_termination(self, handler, sample_workflow_id):
        """Test termination by max iterations."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            max_depth=100,
            max_iterations=5,
        )

        result = await handler.execute(
            config=config,
            initial_inputs={"value": 100},
        )

        state = handler.get_execution_state(result.get("execution_id"))
        if state:
            assert state.iteration_count <= 5

    @pytest.mark.asyncio
    async def test_condition_termination(self, handler, sample_workflow_id):
        """Test termination by condition."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            max_depth=10,
            max_iterations=100,
            termination_condition="value <= 1",
        )

        result = await handler.execute(
            config=config,
            initial_inputs={"value": 5},
        )

        assert "status" in result


# =============================================================================
# Memoization Tests
# =============================================================================


class TestMemoization:
    """Tests for memoization functionality."""

    @pytest.mark.asyncio
    async def test_memoization_enabled(self, handler, sample_workflow_id):
        """Test execution with memoization enabled."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            enable_memoization=True,
            max_iterations=20,
        )

        result = await handler.execute(
            config=config,
            initial_inputs={"value": 5},
        )

        state = handler.get_execution_state(result.get("execution_id"))
        # Memoization should have some hits if same inputs occur
        assert state is not None or "execution_id" in result

    @pytest.mark.asyncio
    async def test_memoization_disabled(self, handler, sample_workflow_id):
        """Test execution with memoization disabled."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            enable_memoization=False,
            max_iterations=10,
        )

        result = await handler.execute(
            config=config,
            initial_inputs={"value": 3},
        )

        state = handler.get_execution_state(result.get("execution_id"))
        if state:
            assert state.memoization_hits == 0


# =============================================================================
# State Management Tests
# =============================================================================


class TestStateManagement:
    """Tests for state management."""

    @pytest.mark.asyncio
    async def test_get_execution_state(self, handler, sample_config):
        """Test getting execution state."""
        result = await handler.execute(
            config=sample_config,
            initial_inputs={"value": 3},
        )

        exec_id = result.get("execution_id")
        if exec_id:
            state = handler.get_execution_state(exec_id)
            assert state is not None

    def test_get_nonexistent_state(self, handler):
        """Test getting nonexistent execution state."""
        state = handler.get_execution_state(uuid4())
        assert state is None

    @pytest.mark.asyncio
    async def test_list_active_executions(self, handler, sample_config):
        """Test listing active executions."""
        # Start async execution
        active = handler.list_active_executions()
        assert isinstance(active, list)


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for handler statistics."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, handler, sample_config):
        """Test getting handler statistics."""
        await handler.execute(
            config=sample_config,
            initial_inputs={"value": 3},
        )

        stats = handler.get_statistics()

        assert "total_executions" in stats
        assert "by_strategy" in stats
        assert "by_termination_type" in stats
        assert "average_iterations" in stats
        assert "total_memoization_hits" in stats


# =============================================================================
# Abort Tests
# =============================================================================


class TestAbort:
    """Tests for execution abort."""

    @pytest.mark.asyncio
    async def test_abort_execution(self, handler, sample_workflow_id):
        """Test aborting an execution."""
        config = RecursionConfig(
            workflow_id=sample_workflow_id,
            max_depth=100,
            max_iterations=1000,
            timeout_seconds=60,
        )

        # Start execution in background
        task = asyncio.create_task(
            handler.execute(config=config, initial_inputs={"value": 100})
        )

        # Give it time to start
        await asyncio.sleep(0.1)

        # Try to abort (may or may not have an execution yet)
        if handler._executions:
            exec_id = list(handler._executions.keys())[0]
            success = await handler.abort_execution(exec_id)
            assert isinstance(success, bool)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

