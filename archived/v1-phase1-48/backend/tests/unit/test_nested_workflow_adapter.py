# =============================================================================
# IPA Platform - NestedWorkflowAdapter Tests
# =============================================================================
# Sprint 23: S23-5 測試和文檔
#
# 測試 NestedWorkflowAdapter 的完整功能:
# - 基本嵌套執行
# - 多層嵌套 (深度 = 3)
# - 上下文傳播策略 (INHERITED, ISOLATED, MERGED, FILTERED)
# - 遞歸深度限制
# - 子工作流類型 (GroupChat, Handoff, Concurrent)
# - 執行模式 (sequential, conditional, parallel)
# - 錯誤處理
# - 邊界情況
# =============================================================================

import asyncio
import pytest
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.integrations.agent_framework.builders.nested_workflow import (
    NestedWorkflowAdapter,
    ContextPropagationStrategy,
    ExecutionMode,
    RecursionStatus,
    ContextConfig,
    RecursionConfig,
    RecursionState,
    SubWorkflowInfo,
    NestedExecutionResult,
    ContextPropagator,
    RecursiveDepthController,
    create_nested_workflow_adapter,
    create_sequential_nested_workflow,
    create_parallel_nested_workflow,
    create_conditional_nested_workflow,
)
from src.integrations.agent_framework.exceptions import RecursionError


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_workflow():
    """Create a mock workflow for testing."""
    workflow = MagicMock()
    workflow.run = AsyncMock(return_value={"result": "success"})
    return workflow


@pytest.fixture
def mock_adapter():
    """Create a mock adapter for testing."""
    adapter = MagicMock()
    adapter.build = MagicMock(return_value=MagicMock())
    adapter.run = AsyncMock(return_value={"result": "adapter_success"})
    return adapter


@pytest.fixture
def nested_adapter():
    """Create a basic NestedWorkflowAdapter for testing."""
    return create_nested_workflow_adapter(
        id="test-nested",
        max_depth=5,
        context_strategy=ContextPropagationStrategy.INHERITED,
    )


# =============================================================================
# ContextPropagationStrategy Tests
# =============================================================================


class TestContextPropagationStrategy:
    """Test ContextPropagationStrategy enum."""

    def test_strategy_values(self):
        """Test all strategy values exist."""
        assert ContextPropagationStrategy.INHERITED.value == "inherited"
        assert ContextPropagationStrategy.ISOLATED.value == "isolated"
        assert ContextPropagationStrategy.MERGED.value == "merged"
        assert ContextPropagationStrategy.FILTERED.value == "filtered"

    def test_strategy_string_conversion(self):
        """Test strategy string conversion."""
        assert str(ContextPropagationStrategy.INHERITED) == "ContextPropagationStrategy.INHERITED"


class TestExecutionMode:
    """Test ExecutionMode enum."""

    def test_mode_values(self):
        """Test all mode values exist."""
        assert ExecutionMode.SEQUENTIAL.value == "sequential"
        assert ExecutionMode.PARALLEL.value == "parallel"
        assert ExecutionMode.CONDITIONAL.value == "conditional"


class TestRecursionStatus:
    """Test RecursionStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert RecursionStatus.PENDING.value == "pending"
        assert RecursionStatus.RUNNING.value == "running"
        assert RecursionStatus.COMPLETED.value == "completed"
        assert RecursionStatus.FAILED.value == "failed"
        assert RecursionStatus.DEPTH_EXCEEDED.value == "depth_exceeded"
        assert RecursionStatus.TIMEOUT.value == "timeout"


# =============================================================================
# ContextConfig Tests
# =============================================================================


class TestContextConfig:
    """Test ContextConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ContextConfig()
        assert config.strategy == ContextPropagationStrategy.INHERITED
        assert config.allowed_keys is None
        assert config.additional_context == {}
        assert config.transform_fn is None

    def test_custom_values(self):
        """Test custom configuration values."""
        allowed = {"key1", "key2"}
        additional = {"extra": "value"}
        transform = lambda x: x

        config = ContextConfig(
            strategy=ContextPropagationStrategy.FILTERED,
            allowed_keys=allowed,
            additional_context=additional,
            transform_fn=transform,
        )

        assert config.strategy == ContextPropagationStrategy.FILTERED
        assert config.allowed_keys == allowed
        assert config.additional_context == additional
        assert config.transform_fn == transform

    def test_to_dict(self):
        """Test to_dict conversion."""
        config = ContextConfig(
            strategy=ContextPropagationStrategy.MERGED,
            allowed_keys={"a", "b"},
            additional_context={"x": 1},
        )
        result = config.to_dict()

        assert result["strategy"] == "merged"
        assert set(result["allowed_keys"]) == {"a", "b"}
        assert result["additional_context_keys"] == ["x"]
        assert result["has_transform"] is False


# =============================================================================
# RecursionConfig Tests
# =============================================================================


class TestRecursionConfig:
    """Test RecursionConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RecursionConfig()
        assert config.max_depth == 5
        assert config.max_iterations == 100
        assert config.timeout_seconds == 300.0
        assert config.track_history is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RecursionConfig(
            max_depth=10,
            max_iterations=50,
            timeout_seconds=600.0,
            track_history=False,
        )

        assert config.max_depth == 10
        assert config.max_iterations == 50
        assert config.timeout_seconds == 600.0
        assert config.track_history is False

    def test_to_dict(self):
        """Test to_dict conversion."""
        config = RecursionConfig(max_depth=3)
        result = config.to_dict()

        assert result["max_depth"] == 3
        assert result["max_iterations"] == 100
        assert "timeout_seconds" in result


# =============================================================================
# RecursionState Tests
# =============================================================================


class TestRecursionState:
    """Test RecursionState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = RecursionState()
        assert state.current_depth == 0
        assert state.iteration_count == 0
        assert state.status == RecursionStatus.PENDING
        assert state.started_at is None
        assert state.completed_at is None
        assert state.history == []

    def test_to_dict(self):
        """Test to_dict conversion."""
        state = RecursionState(
            current_depth=2,
            iteration_count=5,
            status=RecursionStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        result = state.to_dict()

        assert result["current_depth"] == 2
        assert result["iteration_count"] == 5
        assert result["status"] == "running"
        assert result["started_at"] is not None
        assert result["history_length"] == 0


# =============================================================================
# ContextPropagator Tests
# =============================================================================


class TestContextPropagator:
    """Test ContextPropagator class."""

    def test_inherited_strategy(self):
        """Test INHERITED strategy copies parent context."""
        config = ContextConfig(strategy=ContextPropagationStrategy.INHERITED)
        propagator = ContextPropagator(config)

        parent = {"key1": "value1", "key2": "value2"}
        result = propagator.prepare_child_context(parent, "child")

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert result["_nested_parent"] is True
        assert result["_nested_child_name"] == "child"

    def test_isolated_strategy(self):
        """Test ISOLATED strategy doesn't inherit parent context."""
        config = ContextConfig(
            strategy=ContextPropagationStrategy.ISOLATED,
            additional_context={"added": "context"},
        )
        propagator = ContextPropagator(config)

        parent = {"key1": "value1", "key2": "value2"}
        result = propagator.prepare_child_context(parent, "child")

        assert "key1" not in result
        assert "key2" not in result
        assert result["added"] == "context"
        assert result["_nested_parent"] is True

    def test_merged_strategy(self):
        """Test MERGED strategy merges parent with additional context."""
        config = ContextConfig(
            strategy=ContextPropagationStrategy.MERGED,
            additional_context={"added": "value", "key1": "override"},
        )
        propagator = ContextPropagator(config)

        parent = {"key1": "original", "key2": "value2"}
        result = propagator.prepare_child_context(parent, "child")

        assert result["key1"] == "override"  # Additional context overrides
        assert result["key2"] == "value2"
        assert result["added"] == "value"

    def test_filtered_strategy(self):
        """Test FILTERED strategy only passes allowed keys."""
        config = ContextConfig(
            strategy=ContextPropagationStrategy.FILTERED,
            allowed_keys={"key1"},
        )
        propagator = ContextPropagator(config)

        parent = {"key1": "value1", "key2": "value2", "key3": "value3"}
        result = propagator.prepare_child_context(parent, "child")

        assert result["key1"] == "value1"
        assert "key2" not in result
        assert "key3" not in result

    def test_transform_function(self):
        """Test context transformation function."""
        def transform(ctx):
            ctx["transformed"] = True
            return ctx

        config = ContextConfig(
            strategy=ContextPropagationStrategy.INHERITED,
            transform_fn=transform,
        )
        propagator = ContextPropagator(config)

        parent = {"key1": "value1"}
        result = propagator.prepare_child_context(parent, "child")

        assert result["transformed"] is True

    def test_finalize_result_isolated(self):
        """Test finalize_result with ISOLATED strategy."""
        config = ContextConfig(strategy=ContextPropagationStrategy.ISOLATED)
        propagator = ContextPropagator(config)

        child_result = {"output": "result"}
        parent_context = {"input": "data"}
        result = propagator.finalize_result(child_result, parent_context)

        assert result == child_result

    def test_finalize_result_merged(self):
        """Test finalize_result with MERGED strategy."""
        config = ContextConfig(strategy=ContextPropagationStrategy.MERGED)
        propagator = ContextPropagator(config)

        child_result = {"output": "result"}
        parent_context = {"input": "data"}
        result = propagator.finalize_result(child_result, parent_context)

        assert result["input"] == "data"
        assert result["output"] == "result"


# =============================================================================
# RecursiveDepthController Tests
# =============================================================================


class TestRecursiveDepthController:
    """Test RecursiveDepthController class."""

    def test_initial_state(self):
        """Test initial controller state."""
        controller = RecursiveDepthController()
        assert controller.current_depth == 0
        assert controller.max_depth == 5
        assert controller.can_enter() is True

    def test_enter_increments_depth(self):
        """Test entering increases depth."""
        controller = RecursiveDepthController()
        controller.enter()
        assert controller.current_depth == 1
        controller.enter()
        assert controller.current_depth == 2

    def test_exit_decrements_depth(self):
        """Test exiting decreases depth."""
        controller = RecursiveDepthController()
        controller.enter()
        controller.enter()
        assert controller.current_depth == 2
        controller.exit()
        assert controller.current_depth == 1
        controller.exit()
        assert controller.current_depth == 0

    def test_max_depth_enforcement(self):
        """Test maximum depth is enforced."""
        config = RecursionConfig(max_depth=3)
        controller = RecursiveDepthController(config)

        controller.enter()  # depth 1
        controller.enter()  # depth 2
        controller.enter()  # depth 3
        assert controller.can_enter() is False

        with pytest.raises(RecursionError):
            controller.enter()

    def test_state_tracking(self):
        """Test state tracking."""
        controller = RecursiveDepthController()
        controller.enter()

        state = controller.state
        assert state.status == RecursionStatus.RUNNING
        assert state.started_at is not None

        controller.exit()
        assert state.status == RecursionStatus.COMPLETED

    def test_history_recording(self):
        """Test history recording."""
        config = RecursionConfig(track_history=True)
        controller = RecursiveDepthController(config)
        controller.enter()
        controller.record_history({"action": "test"})

        assert len(controller.state.history) == 1
        assert controller.state.history[0]["action"] == "test"

    def test_reset(self):
        """Test controller reset."""
        controller = RecursiveDepthController()
        controller.enter()
        controller.enter()
        controller.reset()

        assert controller.current_depth == 0
        assert controller.state.status == RecursionStatus.PENDING


# =============================================================================
# NestedWorkflowAdapter Tests
# =============================================================================


class TestNestedWorkflowAdapter:
    """Test NestedWorkflowAdapter class."""

    def test_initialization(self):
        """Test adapter initialization."""
        adapter = NestedWorkflowAdapter(
            id="test",
            max_depth=10,
            context_strategy=ContextPropagationStrategy.MERGED,
            timeout_seconds=600.0,
        )

        assert adapter.id == "test"
        assert adapter.max_depth == 10
        assert adapter.context_strategy == ContextPropagationStrategy.MERGED
        assert adapter.execution_mode == ExecutionMode.SEQUENTIAL

    def test_add_sub_workflow_with_workflow(self, mock_workflow):
        """Test adding a workflow instance."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub1", mock_workflow)

        assert "sub1" in adapter.sub_workflow_names
        assert len(adapter.sub_workflow_names) == 1

    def test_add_sub_workflow_with_adapter(self, mock_adapter):
        """Test adding an adapter."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub1", mock_adapter)

        assert "sub1" in adapter.sub_workflow_names

    def test_add_duplicate_sub_workflow_raises(self, mock_workflow):
        """Test adding duplicate sub-workflow raises error."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub1", mock_workflow)

        with pytest.raises(ValueError, match="already exists"):
            adapter.add_sub_workflow("sub1", mock_workflow)

    def test_remove_sub_workflow(self, mock_workflow):
        """Test removing sub-workflow."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub1", mock_workflow)
        adapter.add_sub_workflow("sub2", mock_workflow)

        adapter.remove_sub_workflow("sub1")
        assert "sub1" not in adapter.sub_workflow_names
        assert "sub2" in adapter.sub_workflow_names

    def test_with_context_strategy(self):
        """Test context strategy configuration."""
        adapter = create_nested_workflow_adapter("test")
        adapter.with_context_strategy(
            strategy=ContextPropagationStrategy.FILTERED,
            allowed_keys={"key1", "key2"},
            additional_context={"extra": "value"},
        )

        assert adapter.context_strategy == ContextPropagationStrategy.FILTERED

    def test_with_sequential_execution(self, mock_workflow):
        """Test sequential execution configuration."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("a", mock_workflow)
        adapter.add_sub_workflow("b", mock_workflow)
        adapter.add_sub_workflow("c", mock_workflow)

        adapter.with_sequential_execution(["c", "a", "b"])
        assert adapter.execution_mode == ExecutionMode.SEQUENTIAL

    def test_with_parallel_execution(self, mock_workflow):
        """Test parallel execution configuration."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("a", mock_workflow)
        adapter.add_sub_workflow("b", mock_workflow)

        adapter.with_parallel_execution()
        assert adapter.execution_mode == ExecutionMode.PARALLEL

    def test_with_conditional_execution(self, mock_workflow):
        """Test conditional execution configuration."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("a", mock_workflow)
        adapter.add_sub_workflow("b", mock_workflow)

        conditions = {
            "a": lambda ctx: ctx.get("run_a", True),
            "b": lambda ctx: ctx.get("run_b", False),
        }
        adapter.with_conditional_execution(conditions)
        assert adapter.execution_mode == ExecutionMode.CONDITIONAL

    def test_get_status(self, mock_workflow):
        """Test getting adapter status."""
        adapter = create_nested_workflow_adapter("test", max_depth=7)
        adapter.add_sub_workflow("sub1", mock_workflow)

        status = adapter.get_status()
        assert status["id"] == "test"
        assert status["max_depth"] == 7
        assert "sub1" in status["sub_workflows"]

    def test_validate_empty_adapter(self):
        """Test validation with no sub-workflows."""
        adapter = create_nested_workflow_adapter("test")
        errors = adapter.validate()
        assert "No sub-workflows configured" in errors

    def test_validate_conditional_missing_condition(self, mock_workflow):
        """Test validation for conditional mode without conditions."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("a", mock_workflow)
        adapter._execution_mode = ExecutionMode.CONDITIONAL
        adapter._conditions = {}

        errors = adapter.validate()
        assert any("No condition" in e for e in errors)


# =============================================================================
# NestedWorkflowAdapter Execution Tests
# =============================================================================


class TestNestedWorkflowAdapterExecution:
    """Test NestedWorkflowAdapter execution methods."""

    @pytest.mark.asyncio
    async def test_run_sequential(self, mock_adapter):
        """Test sequential execution."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("step1", mock_adapter)
        adapter.add_sub_workflow("step2", mock_adapter)
        adapter.with_sequential_execution(["step1", "step2"])

        result = await adapter.run({"input": "data"})

        assert result.success is True
        assert "step1" in result.sub_results
        assert "step2" in result.sub_results

    @pytest.mark.asyncio
    async def test_run_parallel(self, mock_adapter):
        """Test parallel execution."""
        adapter = create_nested_workflow_adapter("test", timeout_seconds=10.0)
        adapter.add_sub_workflow("a", mock_adapter)
        adapter.add_sub_workflow("b", mock_adapter)
        adapter.with_parallel_execution()

        result = await adapter.run({"input": "data"})

        assert result.success is True
        assert "a" in result.sub_results
        assert "b" in result.sub_results

    @pytest.mark.asyncio
    async def test_run_conditional(self, mock_adapter):
        """Test conditional execution."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("run", mock_adapter)
        adapter.add_sub_workflow("skip", mock_adapter)

        conditions = {
            "run": lambda ctx: True,
            "skip": lambda ctx: False,
        }
        adapter.with_conditional_execution(conditions)

        result = await adapter.run({"input": "data"})

        assert result.success is True
        assert "run" in result.sub_results
        assert result.sub_results.get("skip", {}).get("skipped") is True

    @pytest.mark.asyncio
    async def test_run_respects_depth_limit(self, mock_adapter):
        """Test that depth limit is respected."""
        adapter = create_nested_workflow_adapter("test", max_depth=0)
        adapter.add_sub_workflow("sub", mock_adapter)

        result = await adapter.run({"input": "data"})

        assert result.success is False
        assert "depth exceeded" in result.error.lower() or "Maximum recursion" in result.error

    @pytest.mark.asyncio
    async def test_run_with_context_propagation(self, mock_adapter):
        """Test context propagation during execution."""
        adapter = create_nested_workflow_adapter("test")
        adapter.with_context_strategy(
            strategy=ContextPropagationStrategy.INHERITED,
            additional_context={"extra": "value"},
        )
        adapter.add_sub_workflow("sub", mock_adapter)

        await adapter.run({"input": "data"})

        # Verify adapter was called
        mock_adapter.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_records_elapsed_time(self, mock_adapter):
        """Test that elapsed time is recorded."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub", mock_adapter)

        result = await adapter.run({"input": "data"})

        assert result.elapsed_seconds >= 0

    @pytest.mark.asyncio
    async def test_run_records_recursion_state(self, mock_adapter):
        """Test that recursion state is recorded."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub", mock_adapter)

        result = await adapter.run({"input": "data"})

        assert result.recursion_state is not None
        assert result.recursion_state.current_depth == 0  # Should be back to 0 after exit


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_nested_workflow_adapter(self):
        """Test create_nested_workflow_adapter."""
        adapter = create_nested_workflow_adapter(
            id="test",
            max_depth=10,
            context_strategy=ContextPropagationStrategy.MERGED,
            timeout_seconds=600.0,
        )

        assert adapter.id == "test"
        assert adapter.max_depth == 10
        assert adapter.context_strategy == ContextPropagationStrategy.MERGED

    def test_create_sequential_nested_workflow(self, mock_adapter):
        """Test create_sequential_nested_workflow."""
        sub_workflows = [
            ("step1", mock_adapter),
            ("step2", mock_adapter),
        ]
        adapter = create_sequential_nested_workflow("test", sub_workflows)

        assert adapter.execution_mode == ExecutionMode.SEQUENTIAL
        assert "step1" in adapter.sub_workflow_names
        assert "step2" in adapter.sub_workflow_names

    def test_create_parallel_nested_workflow(self, mock_adapter):
        """Test create_parallel_nested_workflow."""
        sub_workflows = [
            ("a", mock_adapter),
            ("b", mock_adapter),
        ]
        adapter = create_parallel_nested_workflow("test", sub_workflows, timeout_seconds=60.0)

        assert adapter.execution_mode == ExecutionMode.PARALLEL
        assert "a" in adapter.sub_workflow_names
        assert "b" in adapter.sub_workflow_names

    def test_create_conditional_nested_workflow(self, mock_adapter):
        """Test create_conditional_nested_workflow."""
        condition = lambda ctx: True
        sub_workflows = [
            ("run", mock_adapter, condition),
            ("also_run", mock_adapter),
        ]
        adapter = create_conditional_nested_workflow("test", sub_workflows)

        assert adapter.execution_mode == ExecutionMode.CONDITIONAL


# =============================================================================
# Lifecycle Tests
# =============================================================================


class TestLifecycle:
    """Test adapter lifecycle methods."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test adapter initialization."""
        adapter = create_nested_workflow_adapter("test")
        await adapter.initialize()
        assert adapter.is_initialized is True

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_adapter):
        """Test adapter cleanup."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub", mock_adapter)

        await adapter.initialize()
        await adapter.run({"input": "data"})
        await adapter.cleanup()

        assert adapter.is_initialized is False
        assert adapter.current_depth == 0


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling."""

    def test_add_invalid_workflow_type(self):
        """Test adding invalid workflow type raises error."""
        adapter = create_nested_workflow_adapter("test")

        with pytest.raises(TypeError, match="Unsupported workflow type"):
            adapter.add_sub_workflow("invalid", "not a workflow")

    def test_sequential_with_unknown_name(self, mock_workflow):
        """Test sequential execution with unknown name raises error."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("known", mock_workflow)

        with pytest.raises(ValueError, match="Unknown sub-workflow"):
            adapter.with_sequential_execution(["known", "unknown"])

    def test_conditional_with_unknown_name(self, mock_workflow):
        """Test conditional execution with unknown name raises error."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("known", mock_workflow)

        with pytest.raises(ValueError, match="Unknown sub-workflow"):
            adapter.with_conditional_execution({"unknown": lambda x: True})

    @pytest.mark.asyncio
    async def test_run_handles_sub_workflow_error(self, mock_adapter):
        """Test run handles sub-workflow errors."""
        mock_adapter.run.side_effect = Exception("Sub-workflow failed")

        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("failing", mock_adapter)

        result = await adapter.run({"input": "data"})

        assert result.success is False
        assert "failing" in result.error or "Sub-workflow" in result.error


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_sub_workflows_list(self):
        """Test adapter with no sub-workflows."""
        adapter = create_nested_workflow_adapter("test")
        assert len(adapter.sub_workflow_names) == 0

    def test_remove_nonexistent_sub_workflow(self, mock_workflow):
        """Test removing non-existent sub-workflow doesn't raise."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("exists", mock_workflow)

        # Should not raise
        adapter.remove_sub_workflow("nonexistent")
        assert "exists" in adapter.sub_workflow_names

    def test_get_nonexistent_sub_workflow(self):
        """Test getting non-existent sub-workflow returns None."""
        adapter = create_nested_workflow_adapter("test")
        result = adapter.get_sub_workflow("nonexistent")
        assert result is None

    def test_multiple_context_strategy_changes(self, mock_workflow):
        """Test changing context strategy multiple times."""
        adapter = create_nested_workflow_adapter("test")

        adapter.with_context_strategy(ContextPropagationStrategy.ISOLATED)
        assert adapter.context_strategy == ContextPropagationStrategy.ISOLATED

        adapter.with_context_strategy(ContextPropagationStrategy.MERGED)
        assert adapter.context_strategy == ContextPropagationStrategy.MERGED

    @pytest.mark.asyncio
    async def test_run_with_dict_input(self, mock_adapter):
        """Test run with dictionary input."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub", mock_adapter)

        result = await adapter.run({"key": "value"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_with_non_dict_input(self, mock_adapter):
        """Test run with non-dictionary input."""
        adapter = create_nested_workflow_adapter("test")
        adapter.add_sub_workflow("sub", mock_adapter)

        result = await adapter.run("string input")
        assert result.success is True
