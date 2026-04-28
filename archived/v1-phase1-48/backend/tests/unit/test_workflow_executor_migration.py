# =============================================================================
# IPA Platform - WorkflowExecutor Migration Tests
# =============================================================================
# Sprint 18: S18-2 NestedWorkflowManager 遷移測試
#
# This module contains unit tests for WorkflowExecutor migration layer
# ensuring backward compatibility with Phase 2 NestedWorkflowManager.
#
# Test Coverage:
#   - Legacy enum conversions
#   - Legacy data class conversions
#   - Status conversions (bidirectional)
#   - Context conversions (bidirectional)
#   - Config conversions (bidirectional)
#   - Result conversions (bidirectional)
#   - NestedWorkflowManagerAdapter functionality
#   - Factory functions
#
# Author: IPA Platform Team
# Sprint: 18 - WorkflowExecutor 和整合
# Created: 2025-12-05
# =============================================================================

import pytest
import asyncio
from uuid import uuid4, UUID
from datetime import datetime
from typing import Dict, Any

from src.integrations.agent_framework.builders.workflow_executor import (
    WorkflowExecutorAdapter,
    WorkflowExecutorStatus,
    WorkflowRunState,
    ExecutionContext,
    WorkflowOutput,
    WorkflowRunResult,
    WorkflowExecutorResult,
    SimpleWorkflow,
)

from src.integrations.agent_framework.builders.workflow_executor_migration import (
    # Legacy Enums
    NestedWorkflowTypeLegacy,
    WorkflowScopeLegacy,
    NestedExecutionStatusLegacy,
    # Legacy Data Classes
    NestedWorkflowConfigLegacy,
    SubWorkflowReferenceLegacy,
    NestedExecutionContextLegacy,
    NestedWorkflowResultLegacy,
    # Conversion Functions
    convert_legacy_status_to_executor,
    convert_executor_status_to_legacy,
    convert_legacy_context_to_execution,
    convert_execution_to_legacy_context,
    convert_legacy_config_to_executor_config,
    convert_executor_config_to_legacy,
    convert_executor_result_to_legacy,
    convert_legacy_result_to_executor,
    convert_sub_workflow_reference_to_executor,
    # Adapter
    NestedWorkflowManagerAdapter,
    # Factory Functions
    migrate_nested_workflow_manager,
    create_nested_executor_from_legacy,
    create_migration_context,
)


# =============================================================================
# Tests - Legacy Enums
# =============================================================================


class TestLegacyEnums:
    """Test legacy enum definitions."""

    def test_nested_workflow_type_legacy_values(self):
        """Test NestedWorkflowTypeLegacy enum values."""
        assert NestedWorkflowTypeLegacy.INLINE.value == "inline"
        assert NestedWorkflowTypeLegacy.REFERENCE.value == "reference"
        assert NestedWorkflowTypeLegacy.DYNAMIC.value == "dynamic"
        assert NestedWorkflowTypeLegacy.RECURSIVE.value == "recursive"

    def test_workflow_scope_legacy_values(self):
        """Test WorkflowScopeLegacy enum values."""
        assert WorkflowScopeLegacy.ISOLATED.value == "isolated"
        assert WorkflowScopeLegacy.INHERITED.value == "inherited"
        assert WorkflowScopeLegacy.SHARED.value == "shared"

    def test_nested_execution_status_legacy_values(self):
        """Test NestedExecutionStatusLegacy enum values."""
        assert NestedExecutionStatusLegacy.PENDING.value == "pending"
        assert NestedExecutionStatusLegacy.RUNNING.value == "running"
        assert NestedExecutionStatusLegacy.COMPLETED.value == "completed"
        assert NestedExecutionStatusLegacy.FAILED.value == "failed"
        assert NestedExecutionStatusLegacy.TIMEOUT.value == "timeout"
        assert NestedExecutionStatusLegacy.CANCELLED.value == "cancelled"


# =============================================================================
# Tests - Legacy Data Classes
# =============================================================================


class TestNestedWorkflowConfigLegacy:
    """Test NestedWorkflowConfigLegacy data class."""

    def test_default_creation(self):
        """Test default config creation."""
        config = NestedWorkflowConfigLegacy()
        assert config.workflow_type == NestedWorkflowTypeLegacy.REFERENCE
        assert config.scope == WorkflowScopeLegacy.INHERITED
        assert config.max_depth == 5
        assert config.timeout_seconds == 600
        assert config.retry_on_failure is True
        assert config.max_retries == 2

    def test_custom_creation(self):
        """Test custom config creation."""
        config = NestedWorkflowConfigLegacy(
            workflow_type=NestedWorkflowTypeLegacy.INLINE,
            scope=WorkflowScopeLegacy.ISOLATED,
            max_depth=10,
            timeout_seconds=300,
        )
        assert config.workflow_type == NestedWorkflowTypeLegacy.INLINE
        assert config.scope == WorkflowScopeLegacy.ISOLATED
        assert config.max_depth == 10

    def test_to_dict(self):
        """Test to_dict conversion."""
        config = NestedWorkflowConfigLegacy()
        data = config.to_dict()
        assert data["workflow_type"] == "reference"
        assert data["scope"] == "inherited"
        assert data["max_depth"] == 5

    def test_from_dict(self):
        """Test from_dict creation."""
        data = {
            "workflow_type": "dynamic",
            "scope": "shared",
            "max_depth": 8,
        }
        config = NestedWorkflowConfigLegacy.from_dict(data)
        assert config.workflow_type == NestedWorkflowTypeLegacy.DYNAMIC
        assert config.scope == WorkflowScopeLegacy.SHARED
        assert config.max_depth == 8


class TestSubWorkflowReferenceLegacy:
    """Test SubWorkflowReferenceLegacy data class."""

    def test_creation(self):
        """Test reference creation."""
        ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=uuid4(),
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )
        assert ref.position == 0
        assert ref.status == "pending"
        assert ref.input_mapping == {}
        assert ref.output_mapping == {}

    def test_with_mappings(self):
        """Test reference with mappings."""
        ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=uuid4(),
            workflow_id=None,
            definition={"steps": []},
            config=NestedWorkflowConfigLegacy(
                workflow_type=NestedWorkflowTypeLegacy.INLINE
            ),
            input_mapping={"input1": "child_input"},
            output_mapping={"child_output": "result"},
        )
        assert ref.definition == {"steps": []}
        assert ref.input_mapping == {"input1": "child_input"}

    def test_to_dict(self):
        """Test to_dict conversion."""
        ref_id = uuid4()
        parent_id = uuid4()
        ref = SubWorkflowReferenceLegacy(
            id=ref_id,
            parent_workflow_id=parent_id,
            workflow_id=None,
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )
        data = ref.to_dict()
        assert data["id"] == str(ref_id)
        assert data["parent_workflow_id"] == str(parent_id)
        assert data["workflow_id"] is None


class TestNestedExecutionContextLegacy:
    """Test NestedExecutionContextLegacy data class."""

    def test_creation(self):
        """Test context creation."""
        exec_id = uuid4()
        wf_id = uuid4()
        ctx = NestedExecutionContextLegacy(
            execution_id=exec_id,
            parent_execution_id=None,
            workflow_id=wf_id,
            depth=0,
            path=[],
            variables={"key": "value"},
        )
        assert ctx.execution_id == exec_id
        assert ctx.status == "running"
        assert ctx.variables == {"key": "value"}

    def test_nested_context(self):
        """Test nested context creation."""
        parent_id = uuid4()
        exec_id = uuid4()
        wf_id = uuid4()
        ctx = NestedExecutionContextLegacy(
            execution_id=exec_id,
            parent_execution_id=parent_id,
            workflow_id=wf_id,
            depth=2,
            path=[uuid4(), parent_id],
            variables={},
        )
        assert ctx.parent_execution_id == parent_id
        assert ctx.depth == 2
        assert len(ctx.path) == 2

    def test_to_dict(self):
        """Test to_dict conversion."""
        ctx = NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=None,
            workflow_id=uuid4(),
            depth=1,
            path=[],
            variables={"test": True},
        )
        data = ctx.to_dict()
        assert "execution_id" in data
        assert data["depth"] == 1
        assert data["variables"] == {"test": True}


class TestNestedWorkflowResultLegacy:
    """Test NestedWorkflowResultLegacy data class."""

    def test_success_result(self):
        """Test successful result creation."""
        result = NestedWorkflowResultLegacy(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status=NestedExecutionStatusLegacy.COMPLETED,
            outputs={"result": "success"},
            duration_seconds=1.5,
        )
        assert result.status == NestedExecutionStatusLegacy.COMPLETED
        assert result.outputs == {"result": "success"}
        assert result.error is None

    def test_failed_result(self):
        """Test failed result creation."""
        result = NestedWorkflowResultLegacy(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status=NestedExecutionStatusLegacy.FAILED,
            error="Test error",
        )
        assert result.status == NestedExecutionStatusLegacy.FAILED
        assert result.error == "Test error"

    def test_to_dict(self):
        """Test to_dict conversion."""
        result = NestedWorkflowResultLegacy(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status=NestedExecutionStatusLegacy.COMPLETED,
        )
        data = result.to_dict()
        assert data["status"] == "completed"


# =============================================================================
# Tests - Status Conversions
# =============================================================================


class TestStatusConversions:
    """Test status conversion functions."""

    def test_legacy_to_executor_pending(self):
        """Test pending status conversion."""
        result = convert_legacy_status_to_executor("pending")
        assert result == WorkflowExecutorStatus.IDLE

    def test_legacy_to_executor_running(self):
        """Test running status conversion."""
        result = convert_legacy_status_to_executor("running")
        assert result == WorkflowExecutorStatus.RUNNING

    def test_legacy_to_executor_completed(self):
        """Test completed status conversion."""
        result = convert_legacy_status_to_executor("completed")
        assert result == WorkflowExecutorStatus.COMPLETED

    def test_legacy_to_executor_failed(self):
        """Test failed status conversion."""
        result = convert_legacy_status_to_executor("failed")
        assert result == WorkflowExecutorStatus.FAILED

    def test_legacy_to_executor_timeout(self):
        """Test timeout status conversion."""
        result = convert_legacy_status_to_executor("timeout")
        assert result == WorkflowExecutorStatus.FAILED

    def test_legacy_to_executor_cancelled(self):
        """Test cancelled status conversion."""
        result = convert_legacy_status_to_executor("cancelled")
        assert result == WorkflowExecutorStatus.CANCELLED

    def test_legacy_to_executor_with_enum(self):
        """Test conversion with enum input."""
        result = convert_legacy_status_to_executor(NestedExecutionStatusLegacy.RUNNING)
        assert result == WorkflowExecutorStatus.RUNNING

    def test_executor_to_legacy_idle(self):
        """Test IDLE to legacy conversion."""
        result = convert_executor_status_to_legacy(WorkflowExecutorStatus.IDLE)
        assert result == NestedExecutionStatusLegacy.PENDING

    def test_executor_to_legacy_running(self):
        """Test RUNNING to legacy conversion."""
        result = convert_executor_status_to_legacy(WorkflowExecutorStatus.RUNNING)
        assert result == NestedExecutionStatusLegacy.RUNNING

    def test_executor_to_legacy_waiting(self):
        """Test WAITING_RESPONSE to legacy conversion."""
        result = convert_executor_status_to_legacy(WorkflowExecutorStatus.WAITING_RESPONSE)
        assert result == NestedExecutionStatusLegacy.RUNNING

    def test_executor_to_legacy_completed(self):
        """Test COMPLETED to legacy conversion."""
        result = convert_executor_status_to_legacy(WorkflowExecutorStatus.COMPLETED)
        assert result == NestedExecutionStatusLegacy.COMPLETED


# =============================================================================
# Tests - Context Conversions
# =============================================================================


class TestContextConversions:
    """Test context conversion functions."""

    def test_legacy_to_execution_context(self):
        """Test legacy context to execution context conversion."""
        legacy_ctx = NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=uuid4(),
            workflow_id=uuid4(),
            depth=2,
            path=[uuid4()],
            variables={"key": "value"},
            status="running",
        )

        new_ctx = convert_legacy_context_to_execution(legacy_ctx)

        assert new_ctx.execution_id == str(legacy_ctx.execution_id)
        assert new_ctx.metadata["depth"] == 2
        assert new_ctx.metadata["variables"] == {"key": "value"}

    def test_execution_to_legacy_context(self):
        """Test execution context to legacy conversion."""
        exec_ctx = ExecutionContext(
            execution_id="exec-123",
            metadata={
                "depth": 1,
                "variables": {"x": 1},
            },
        )
        wf_id = uuid4()

        legacy_ctx = convert_execution_to_legacy_context(exec_ctx, wf_id)

        assert str(legacy_ctx.execution_id) == "exec-123"
        assert legacy_ctx.workflow_id == wf_id
        assert legacy_ctx.depth == 1


# =============================================================================
# Tests - Config Conversions
# =============================================================================


class TestConfigConversions:
    """Test config conversion functions."""

    def test_legacy_to_executor_config(self):
        """Test legacy config to executor config conversion."""
        legacy_config = NestedWorkflowConfigLegacy(
            max_depth=8,
            timeout_seconds=120,
            retry_on_failure=False,
        )

        new_config = convert_legacy_config_to_executor_config(legacy_config)

        assert new_config["max_depth"] == 8
        assert new_config["timeout_seconds"] == 120
        assert new_config["retry_on_failure"] is False

    def test_executor_to_legacy_config(self):
        """Test executor config to legacy conversion."""
        config = {
            "max_depth": 10,
            "timeout_seconds": 300,
            "legacy_type": "dynamic",
            "legacy_scope": "isolated",
        }

        legacy_config = convert_executor_config_to_legacy(config)

        assert legacy_config.max_depth == 10
        assert legacy_config.timeout_seconds == 300
        assert legacy_config.workflow_type == NestedWorkflowTypeLegacy.DYNAMIC
        assert legacy_config.scope == WorkflowScopeLegacy.ISOLATED


# =============================================================================
# Tests - Result Conversions
# =============================================================================


class TestResultConversions:
    """Test result conversion functions."""

    def test_executor_to_legacy_result(self):
        """Test executor result to legacy conversion."""
        exec_result = WorkflowExecutorResult(
            status=WorkflowExecutorStatus.COMPLETED,
            outputs=["output1", "output2"],
            execution_id="exec-123",
            duration_seconds=2.5,
        )
        wf_id = uuid4()

        legacy_result = convert_executor_result_to_legacy(exec_result, wf_id)

        assert legacy_result.status == NestedExecutionStatusLegacy.COMPLETED
        assert legacy_result.workflow_id == wf_id
        assert legacy_result.duration_seconds == 2.5
        assert "output_0" in legacy_result.outputs

    def test_legacy_to_executor_result(self):
        """Test legacy result to executor conversion."""
        legacy_result = NestedWorkflowResultLegacy(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status=NestedExecutionStatusLegacy.FAILED,
            outputs={"error_output": "error"},
            error="Test error",
        )

        exec_result = convert_legacy_result_to_executor(legacy_result)

        assert exec_result.status == WorkflowExecutorStatus.FAILED
        assert exec_result.error == "Test error"
        assert "error" in exec_result.outputs


# =============================================================================
# Tests - Reference Conversion
# =============================================================================


class TestReferenceConversion:
    """Test SubWorkflowReference to Executor conversion."""

    def test_basic_conversion(self):
        """Test basic reference conversion."""
        ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=uuid4(),
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        adapter = convert_sub_workflow_reference_to_executor(ref)

        assert adapter.id == str(ref.id)
        assert adapter.workflow is None  # No executor_fn provided

    def test_conversion_with_executor_fn(self):
        """Test conversion with executor function."""

        async def my_executor(data, responses):
            return f"processed: {data}"

        ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=uuid4(),
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        adapter = convert_sub_workflow_reference_to_executor(ref, my_executor)

        assert adapter.workflow is not None
        assert isinstance(adapter.workflow, SimpleWorkflow)


# =============================================================================
# Tests - NestedWorkflowManagerAdapter
# =============================================================================


class TestNestedWorkflowManagerAdapterInit:
    """Test NestedWorkflowManagerAdapter initialization."""

    def test_basic_init(self):
        """Test basic initialization."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test-manager")
        assert adapter.id == "test-manager"
        assert adapter.max_global_depth == 10
        assert adapter.executor_count == 0

    def test_custom_init(self):
        """Test custom initialization."""
        adapter = NestedWorkflowManagerAdapter(
            manager_id="custom-manager",
            max_global_depth=5,
            config={"option": "value"},
        )
        assert adapter.max_global_depth == 5


class TestNestedWorkflowManagerAdapterRegistration:
    """Test NestedWorkflowManagerAdapter registration methods."""

    @pytest.mark.asyncio
    async def test_register_sub_workflow(self):
        """Test sub-workflow registration."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")
        parent_id = uuid4()
        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=parent_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        result = await adapter.register_sub_workflow(parent_id, sub_ref)

        assert result.id == sub_ref.id
        assert adapter.executor_count == 1

    @pytest.mark.asyncio
    async def test_register_multiple_sub_workflows(self):
        """Test registering multiple sub-workflows."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")
        parent_id = uuid4()

        for i in range(3):
            sub_ref = SubWorkflowReferenceLegacy(
                id=uuid4(),
                parent_workflow_id=parent_id,
                workflow_id=uuid4(),
                definition=None,
                config=NestedWorkflowConfigLegacy(),
                position=i,
            )
            await adapter.register_sub_workflow(parent_id, sub_ref)

        subs = adapter.get_sub_workflows(parent_id)
        assert len(subs) == 3
        assert adapter.executor_count == 3

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")

        wf_a = uuid4()
        wf_b = uuid4()

        # A -> B
        ref1 = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=wf_a,
            workflow_id=wf_b,
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )
        await adapter.register_sub_workflow(wf_a, ref1)

        # B -> A (circular)
        ref2 = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=wf_b,
            workflow_id=wf_a,
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        with pytest.raises(ValueError, match="Circular dependency"):
            await adapter.register_sub_workflow(wf_b, ref2)

    def test_unregister_sub_workflow(self):
        """Test sub-workflow unregistration."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")
        parent_id = uuid4()
        sub_id = uuid4()

        # Manually add to simulate registration
        sub_ref = SubWorkflowReferenceLegacy(
            id=sub_id,
            parent_workflow_id=parent_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )
        adapter._sub_workflows[parent_id] = [sub_ref]
        adapter._executors[str(sub_id)] = WorkflowExecutorAdapter(id=str(sub_id))

        result = adapter.unregister_sub_workflow(parent_id, sub_id)

        assert result is True
        assert len(adapter.get_sub_workflows(parent_id)) == 0


class TestNestedWorkflowManagerAdapterExecution:
    """Test NestedWorkflowManagerAdapter execution methods."""

    @pytest.mark.asyncio
    async def test_execute_sub_workflow_basic(self):
        """Test basic sub-workflow execution."""

        async def executor_fn(data, responses):
            return {"output": f"processed: {data}"}

        adapter = NestedWorkflowManagerAdapter(manager_id="test")
        parent_id = uuid4()
        wf_id = uuid4()

        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=parent_id,
            workflow_id=wf_id,
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        await adapter.register_sub_workflow(parent_id, sub_ref, executor_fn)

        parent_ctx = NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=None,
            workflow_id=parent_id,
            depth=0,
            path=[],
            variables={"input": "test"},
        )

        result = await adapter.execute_sub_workflow(parent_ctx, sub_ref)

        assert result.status == NestedExecutionStatusLegacy.COMPLETED
        assert result.workflow_id == wf_id

    @pytest.mark.asyncio
    async def test_execute_depth_limit_exceeded(self):
        """Test depth limit exceeded error."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test", max_global_depth=2)

        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=uuid4(),
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(max_depth=3),
        )

        parent_ctx = NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=None,
            workflow_id=uuid4(),
            depth=2,  # Already at global max
            path=[],
            variables={},
        )

        with pytest.raises(ValueError, match="depth"):
            await adapter.execute_sub_workflow(parent_ctx, sub_ref)

    @pytest.mark.asyncio
    async def test_execute_with_input_mapping(self):
        """Test execution with input mapping."""
        output_data = {}

        async def executor_fn(data, responses):
            output_data.update(data)
            return {"result": "success"}

        adapter = NestedWorkflowManagerAdapter(manager_id="test")

        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=uuid4(),
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
            input_mapping={"parent_var": "child_var"},
        )

        await adapter.register_sub_workflow(sub_ref.parent_workflow_id, sub_ref, executor_fn)

        parent_ctx = NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=None,
            workflow_id=sub_ref.parent_workflow_id,
            depth=0,
            path=[],
            variables={"parent_var": "test_value"},
        )

        await adapter.execute_sub_workflow(parent_ctx, sub_ref)

        assert output_data.get("child_var") == "test_value"


class TestNestedWorkflowManagerAdapterTree:
    """Test NestedWorkflowManagerAdapter execution tree methods."""

    def test_get_execution_tree(self):
        """Test execution tree retrieval."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")

        root_id = uuid4()
        child_id = uuid4()

        # Add root context
        adapter._active_executions[root_id] = NestedExecutionContextLegacy(
            execution_id=root_id,
            parent_execution_id=None,
            workflow_id=uuid4(),
            depth=0,
            path=[],
            variables={},
            status="completed",
        )

        # Add child context
        adapter._active_executions[child_id] = NestedExecutionContextLegacy(
            execution_id=child_id,
            parent_execution_id=root_id,
            workflow_id=uuid4(),
            depth=1,
            path=[root_id],
            variables={},
            status="completed",
        )

        tree = adapter.get_execution_tree(root_id)

        assert tree["id"] == str(root_id)
        assert len(tree["children"]) == 1
        assert tree["children"][0]["id"] == str(child_id)

    def test_get_active_executions(self):
        """Test active executions retrieval."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")
        wf_id = uuid4()

        for i in range(3):
            adapter._active_executions[uuid4()] = NestedExecutionContextLegacy(
                execution_id=uuid4(),
                parent_execution_id=None,
                workflow_id=wf_id if i == 0 else uuid4(),
                depth=0,
                path=[],
                variables={},
            )

        all_executions = adapter.get_active_executions()
        assert len(all_executions) == 3

        filtered = adapter.get_active_executions(wf_id)
        assert len(filtered) == 1


class TestNestedWorkflowManagerAdapterCancellation:
    """Test NestedWorkflowManagerAdapter cancellation methods."""

    @pytest.mark.asyncio
    async def test_cancel_nested_execution(self):
        """Test nested execution cancellation."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")
        exec_id = uuid4()

        adapter._active_executions[exec_id] = NestedExecutionContextLegacy(
            execution_id=exec_id,
            parent_execution_id=None,
            workflow_id=uuid4(),
            depth=0,
            path=[],
            variables={},
        )

        result = await adapter.cancel_nested_execution(exec_id)

        assert result is True
        assert adapter._active_executions[exec_id].status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_with_cascade(self):
        """Test cancellation with cascade."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")

        parent_id = uuid4()
        child_id = uuid4()

        adapter._active_executions[parent_id] = NestedExecutionContextLegacy(
            execution_id=parent_id,
            parent_execution_id=None,
            workflow_id=uuid4(),
            depth=0,
            path=[],
            variables={},
        )

        adapter._active_executions[child_id] = NestedExecutionContextLegacy(
            execution_id=child_id,
            parent_execution_id=parent_id,
            workflow_id=uuid4(),
            depth=1,
            path=[parent_id],
            variables={},
        )

        await adapter.cancel_nested_execution(parent_id, cascade=True)

        assert adapter._active_executions[parent_id].status == "cancelled"
        assert adapter._active_executions[child_id].status == "cancelled"

    def test_clear_completed_executions(self):
        """Test clearing completed executions."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")

        # Add completed execution
        old_exec = NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=None,
            workflow_id=uuid4(),
            depth=0,
            path=[],
            variables={},
            status="completed",
            completed_at=datetime(2020, 1, 1),  # Old
        )
        adapter._active_executions[old_exec.execution_id] = old_exec

        # Add running execution
        new_exec = NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=None,
            workflow_id=uuid4(),
            depth=0,
            path=[],
            variables={},
            status="running",
        )
        adapter._active_executions[new_exec.execution_id] = new_exec

        cleared = adapter.clear_completed_executions(older_than_seconds=1)

        assert cleared == 1
        assert len(adapter._active_executions) == 1


class TestNestedWorkflowManagerAdapterStatistics:
    """Test NestedWorkflowManagerAdapter statistics methods."""

    def test_get_statistics(self):
        """Test statistics retrieval."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")

        # Add some executions
        for status in ["running", "running", "completed"]:
            adapter._active_executions[uuid4()] = NestedExecutionContextLegacy(
                execution_id=uuid4(),
                parent_execution_id=None,
                workflow_id=uuid4(),
                depth=0,
                path=[],
                variables={},
                status=status,
            )

        stats = adapter.get_statistics()

        assert stats["total_active_executions"] == 3
        assert stats["by_status"]["running"] == 2
        assert stats["by_status"]["completed"] == 1


class TestNestedWorkflowManagerAdapterCheckpoint:
    """Test NestedWorkflowManagerAdapter checkpoint methods."""

    @pytest.mark.asyncio
    async def test_checkpoint_save(self):
        """Test checkpoint save."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")

        state = await adapter.on_checkpoint_save()

        assert state["id"] == "test"
        assert "executor_states" in state
        assert "active_executions" in state

    @pytest.mark.asyncio
    async def test_checkpoint_restore(self):
        """Test checkpoint restore."""
        adapter = NestedWorkflowManagerAdapter(manager_id="test")

        state = {
            "executor_states": {},
            "active_executions": {},
        }

        await adapter.on_checkpoint_restore(state)
        # Should not raise


# =============================================================================
# Tests - Factory Functions
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""

    def test_migrate_nested_workflow_manager(self):
        """Test migrate_nested_workflow_manager factory."""
        adapter = migrate_nested_workflow_manager(
            manager_id="migrated",
            max_global_depth=15,
        )
        assert isinstance(adapter, NestedWorkflowManagerAdapter)
        assert adapter.id == "migrated"
        assert adapter.max_global_depth == 15

    def test_create_nested_executor_from_legacy(self):
        """Test create_nested_executor_from_legacy factory."""
        ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=uuid4(),
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        executor = create_nested_executor_from_legacy(ref)

        assert isinstance(executor, WorkflowExecutorAdapter)
        assert executor.id == str(ref.id)

    def test_create_migration_context(self):
        """Test create_migration_context factory."""
        ctx = create_migration_context(
            variables={"key": "value"},
            depth=2,
        )

        assert isinstance(ctx, NestedExecutionContextLegacy)
        assert ctx.depth == 2
        assert ctx.variables == {"key": "value"}

    def test_create_migration_context_with_ids(self):
        """Test create_migration_context with custom IDs."""
        exec_id = uuid4()
        wf_id = uuid4()

        ctx = create_migration_context(
            execution_id=exec_id,
            workflow_id=wf_id,
        )

        assert ctx.execution_id == exec_id
        assert ctx.workflow_id == wf_id


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for migration layer."""

    @pytest.mark.asyncio
    async def test_full_migration_workflow(self):
        """Test complete migration workflow."""
        # 1. Create adapter
        adapter = migrate_nested_workflow_manager("integration-test")

        # 2. Define executor function
        async def process(data, responses):
            input_val = data.get("input", "default")
            return {"result": f"processed: {input_val}"}

        # 3. Register sub-workflow
        parent_id = uuid4()
        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=parent_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(
                scope=WorkflowScopeLegacy.INHERITED,
            ),
            input_mapping={"parent_input": "input"},
            output_mapping={"result": "child_result"},
        )

        await adapter.register_sub_workflow(parent_id, sub_ref, process)

        # 4. Create parent context
        parent_ctx = create_migration_context(
            workflow_id=parent_id,
            variables={"parent_input": "test_value"},
        )

        # 5. Execute
        result = await adapter.execute_sub_workflow(parent_ctx, sub_ref)

        # 6. Verify
        assert result.status == NestedExecutionStatusLegacy.COMPLETED
        assert "child_result" in parent_ctx.variables

    @pytest.mark.asyncio
    async def test_bidirectional_conversion_consistency(self):
        """Test that bidirectional conversions are consistent."""
        # Original legacy context
        original = NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=uuid4(),
            workflow_id=uuid4(),
            depth=3,
            path=[uuid4(), uuid4()],
            variables={"a": 1, "b": 2},
            status="running",
        )

        # Convert to new format and back
        new_ctx = convert_legacy_context_to_execution(original)
        restored = convert_execution_to_legacy_context(
            new_ctx,
            original.workflow_id,
            original.depth,
            original.path,
        )

        # Verify key fields preserved
        assert restored.execution_id == original.execution_id
        assert restored.depth == original.depth


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
