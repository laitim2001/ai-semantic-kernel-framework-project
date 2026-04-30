# =============================================================================
# IPA Platform - WorkflowExecutor Adapter Tests
# =============================================================================
# Sprint 18: S18-1 WorkflowExecutor 適配器測試
#
# This module contains comprehensive unit tests for WorkflowExecutorAdapter
# and related components.
#
# Test Coverage:
#   - WorkflowExecutorAdapter lifecycle (build, run, cleanup)
#   - Request/Response message handling
#   - Concurrent execution isolation
#   - Checkpoint save/restore
#   - Factory functions
#
# Author: IPA Platform Team
# Sprint: 18 - WorkflowExecutor 和整合
# Created: 2025-12-05
# =============================================================================

import pytest
import asyncio
from typing import Any, Dict, List, Type
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.agent_framework.builders.workflow_executor import (
    WorkflowExecutorAdapter,
    WorkflowExecutorStatus,
    WorkflowRunState,
    MessageRole,
    RequestInfoEvent,
    SubWorkflowRequestMessage,
    SubWorkflowResponseMessage,
    ExecutionContext,
    WorkflowOutput,
    WorkflowRunResult,
    WorkflowExecutorResult,
    WorkflowProtocol,
    SimpleWorkflow,
    create_workflow_executor,
    create_simple_workflow,
    create_nested_workflow_executor,
)


# =============================================================================
# Mock Implementations
# =============================================================================


class MockWorkflow:
    """Mock workflow for testing."""

    def __init__(self, workflow_id: str = "mock-workflow"):
        self._id = workflow_id
        self._input_types: List[Type[Any]] = [str, dict]
        self._output_types: List[Type[Any]] = [str]
        self._run_result: WorkflowRunResult = WorkflowRunResult(
            outputs=[WorkflowOutput(data="mock output")],
            final_state=WorkflowRunState.COMPLETED,
        )
        self._send_responses_result: WorkflowRunResult = WorkflowRunResult(
            outputs=[WorkflowOutput(data="resumed output")],
            final_state=WorkflowRunState.COMPLETED,
        )

    @property
    def id(self) -> str:
        return self._id

    @property
    def input_types(self) -> List[Type[Any]]:
        return self._input_types

    @property
    def output_types(self) -> List[Type[Any]]:
        return self._output_types

    def set_run_result(self, result: WorkflowRunResult) -> None:
        self._run_result = result

    def set_send_responses_result(self, result: WorkflowRunResult) -> None:
        self._send_responses_result = result

    async def run(self, input_data: Any) -> WorkflowRunResult:
        return self._run_result

    async def send_responses(self, responses: Dict[str, Any]) -> WorkflowRunResult:
        return self._send_responses_result


class RequestingWorkflow(MockWorkflow):
    """Workflow that generates request events."""

    def __init__(self, workflow_id: str = "requesting-workflow"):
        super().__init__(workflow_id)
        self._request_events: List[RequestInfoEvent] = []

    def add_request_event(self, event: RequestInfoEvent) -> None:
        self._request_events.append(event)

    async def run(self, input_data: Any) -> WorkflowRunResult:
        if self._request_events:
            return WorkflowRunResult(
                outputs=[],
                request_info_events=list(self._request_events),
                final_state=WorkflowRunState.IN_PROGRESS_PENDING_REQUESTS,
            )
        return await super().run(input_data)


# =============================================================================
# Tests - Enums
# =============================================================================


class TestEnums:
    """Test enum definitions."""

    def test_workflow_executor_status_values(self):
        """Test WorkflowExecutorStatus enum values."""
        assert WorkflowExecutorStatus.IDLE.value == "idle"
        assert WorkflowExecutorStatus.RUNNING.value == "running"
        assert WorkflowExecutorStatus.WAITING_RESPONSE.value == "waiting_response"
        assert WorkflowExecutorStatus.COMPLETED.value == "completed"
        assert WorkflowExecutorStatus.FAILED.value == "failed"
        assert WorkflowExecutorStatus.CANCELLED.value == "cancelled"

    def test_workflow_run_state_values(self):
        """Test WorkflowRunState enum values."""
        assert WorkflowRunState.IDLE.value == "idle"
        assert WorkflowRunState.IN_PROGRESS.value == "in_progress"
        assert WorkflowRunState.IN_PROGRESS_PENDING_REQUESTS.value == "in_progress_pending_requests"
        assert WorkflowRunState.IDLE_WITH_PENDING_REQUESTS.value == "idle_with_pending_requests"
        assert WorkflowRunState.COMPLETED.value == "completed"
        assert WorkflowRunState.FAILED.value == "failed"
        assert WorkflowRunState.CANCELLED.value == "cancelled"

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.EXECUTOR.value == "executor"


# =============================================================================
# Tests - Data Classes
# =============================================================================


class TestRequestInfoEvent:
    """Test RequestInfoEvent data class."""

    def test_creation(self):
        """Test RequestInfoEvent creation."""
        event = RequestInfoEvent(
            request_id="req-1",
            data={"key": "value"},
            response_type=dict,
            executor_id="exec-1",
        )
        assert event.request_id == "req-1"
        assert event.data == {"key": "value"}
        assert event.response_type == dict
        assert event.executor_id == "exec-1"
        assert event.timestamp > 0

    def test_to_dict(self):
        """Test RequestInfoEvent to_dict conversion."""
        event = RequestInfoEvent(
            request_id="req-1",
            data="test data",
            response_type=str,
        )
        result = event.to_dict()
        assert result["request_id"] == "req-1"
        assert result["data"] == "test data"
        assert "response_type" in result


class TestSubWorkflowRequestMessage:
    """Test SubWorkflowRequestMessage data class."""

    def test_creation(self):
        """Test SubWorkflowRequestMessage creation."""
        event = RequestInfoEvent(
            request_id="req-1",
            data="request data",
            response_type=str,
        )
        message = SubWorkflowRequestMessage(
            source_event=event,
            executor_id="exec-1",
        )
        assert message.source_event == event
        assert message.executor_id == "exec-1"

    def test_create_response(self):
        """Test create_response method."""
        event = RequestInfoEvent(
            request_id="req-1",
            data="request",
            response_type=str,
        )
        request = SubWorkflowRequestMessage(source_event=event, executor_id="exec-1")

        response = request.create_response("response data")
        assert isinstance(response, SubWorkflowResponseMessage)
        assert response.data == "response data"
        assert response.source_event == event

    def test_to_dict(self):
        """Test to_dict conversion."""
        event = RequestInfoEvent(
            request_id="req-1",
            data="data",
            response_type=str,
        )
        message = SubWorkflowRequestMessage(source_event=event, executor_id="exec-1")
        result = message.to_dict()
        assert "source_event" in result
        assert result["executor_id"] == "exec-1"


class TestSubWorkflowResponseMessage:
    """Test SubWorkflowResponseMessage data class."""

    def test_creation(self):
        """Test SubWorkflowResponseMessage creation."""
        event = RequestInfoEvent(
            request_id="req-1",
            data="request",
            response_type=str,
        )
        response = SubWorkflowResponseMessage(
            data="response data",
            source_event=event,
        )
        assert response.data == "response data"
        assert response.source_event == event

    def test_to_dict(self):
        """Test to_dict conversion."""
        event = RequestInfoEvent(
            request_id="req-1",
            data="data",
            response_type=str,
        )
        response = SubWorkflowResponseMessage(data="response", source_event=event)
        result = response.to_dict()
        assert result["data"] == "response"
        assert "source_event" in result


class TestExecutionContext:
    """Test ExecutionContext data class."""

    def test_creation(self):
        """Test ExecutionContext creation."""
        ctx = ExecutionContext(execution_id="exec-1")
        assert ctx.execution_id == "exec-1"
        assert ctx.collected_responses == {}
        assert ctx.expected_response_count == 0
        assert ctx.pending_requests == {}
        assert ctx.started_at > 0

    def test_to_dict(self):
        """Test to_dict conversion."""
        ctx = ExecutionContext(
            execution_id="exec-1",
            expected_response_count=2,
            metadata={"key": "value"},
        )
        result = ctx.to_dict()
        assert result["execution_id"] == "exec-1"
        assert result["expected_response_count"] == 2
        assert result["metadata"] == {"key": "value"}

    def test_from_dict(self):
        """Test from_dict restoration."""
        data = {
            "execution_id": "exec-1",
            "collected_responses": {"req-1": "response"},
            "expected_response_count": 1,
            "pending_requests": {},
            "started_at": 1234567890.0,
            "metadata": {"test": True},
        }
        ctx = ExecutionContext.from_dict(data)
        assert ctx.execution_id == "exec-1"
        assert ctx.collected_responses == {"req-1": "response"}
        assert ctx.expected_response_count == 1
        assert ctx.metadata == {"test": True}


class TestWorkflowRunResult:
    """Test WorkflowRunResult data class."""

    def test_creation(self):
        """Test WorkflowRunResult creation."""
        result = WorkflowRunResult(
            outputs=[WorkflowOutput(data="output1")],
            final_state=WorkflowRunState.COMPLETED,
        )
        assert len(result.outputs) == 1
        assert result.final_state == WorkflowRunState.COMPLETED

    def test_get_outputs(self):
        """Test get_outputs method."""
        result = WorkflowRunResult(
            outputs=[
                WorkflowOutput(data="out1"),
                WorkflowOutput(data="out2"),
            ]
        )
        outputs = result.get_outputs()
        assert outputs == ["out1", "out2"]

    def test_get_request_info_events(self):
        """Test get_request_info_events method."""
        event = RequestInfoEvent(request_id="req-1", data="data", response_type=str)
        result = WorkflowRunResult(request_info_events=[event])
        events = result.get_request_info_events()
        assert len(events) == 1
        assert events[0] == event

    def test_to_dict(self):
        """Test to_dict conversion."""
        result = WorkflowRunResult(
            outputs=[WorkflowOutput(data="output")],
            final_state=WorkflowRunState.COMPLETED,
        )
        data = result.to_dict()
        assert data["final_state"] == "completed"
        assert len(data["outputs"]) == 1


class TestWorkflowExecutorResult:
    """Test WorkflowExecutorResult data class."""

    def test_creation(self):
        """Test WorkflowExecutorResult creation."""
        result = WorkflowExecutorResult(
            status=WorkflowExecutorStatus.COMPLETED,
            outputs=["output1", "output2"],
            execution_id="exec-1",
            workflow_id="wf-1",
        )
        assert result.status == WorkflowExecutorStatus.COMPLETED
        assert result.outputs == ["output1", "output2"]
        assert result.execution_id == "exec-1"
        assert result.workflow_id == "wf-1"

    def test_to_dict(self):
        """Test to_dict conversion."""
        result = WorkflowExecutorResult(
            status=WorkflowExecutorStatus.RUNNING,
            outputs=["out"],
            execution_id="exec-1",
        )
        data = result.to_dict()
        assert data["status"] == "running"
        assert data["outputs"] == ["out"]


# =============================================================================
# Tests - WorkflowExecutorAdapter
# =============================================================================


class TestWorkflowExecutorAdapterInit:
    """Test WorkflowExecutorAdapter initialization."""

    def test_basic_init(self):
        """Test basic initialization."""
        adapter = WorkflowExecutorAdapter(id="test-adapter")
        assert adapter.id == "test-adapter"
        assert adapter.workflow is None
        assert adapter.status == WorkflowExecutorStatus.IDLE
        assert not adapter.is_built
        assert not adapter.is_initialized
        assert not adapter.allow_direct_output

    def test_init_with_workflow(self):
        """Test initialization with workflow."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(
            id="test-adapter",
            workflow=workflow,
        )
        assert adapter.workflow == workflow

    def test_init_with_config(self):
        """Test initialization with config."""
        adapter = WorkflowExecutorAdapter(
            id="test-adapter",
            allow_direct_output=True,
            config={"option": "value"},
        )
        assert adapter.allow_direct_output is True

    def test_init_empty_id_raises(self):
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="ID cannot be empty"):
            WorkflowExecutorAdapter(id="")


class TestWorkflowExecutorAdapterProperties:
    """Test WorkflowExecutorAdapter properties."""

    def test_input_types_without_workflow(self):
        """Test input_types without workflow."""
        adapter = WorkflowExecutorAdapter(id="test")
        input_types = adapter.input_types
        assert SubWorkflowResponseMessage in input_types

    def test_input_types_with_workflow(self):
        """Test input_types with workflow."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        input_types = adapter.input_types
        assert str in input_types
        assert dict in input_types
        assert SubWorkflowResponseMessage in input_types

    def test_output_types_with_workflow(self):
        """Test output_types with workflow."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        output_types = adapter.output_types
        assert str in output_types
        assert SubWorkflowRequestMessage in output_types

    def test_active_execution_count(self):
        """Test active_execution_count property."""
        adapter = WorkflowExecutorAdapter(id="test")
        assert adapter.active_execution_count == 0


class TestWorkflowExecutorAdapterFluentMethods:
    """Test WorkflowExecutorAdapter fluent configuration methods."""

    def test_with_workflow(self):
        """Test with_workflow method."""
        adapter = WorkflowExecutorAdapter(id="test")
        workflow = MockWorkflow()
        result = adapter.with_workflow(workflow)
        assert result is adapter
        assert adapter.workflow == workflow

    def test_with_direct_output(self):
        """Test with_direct_output method."""
        adapter = WorkflowExecutorAdapter(id="test")
        result = adapter.with_direct_output(True)
        assert result is adapter
        assert adapter.allow_direct_output is True

    def test_with_request_handler(self):
        """Test with_request_handler method."""
        adapter = WorkflowExecutorAdapter(id="test")
        handler = AsyncMock()
        result = adapter.with_request_handler(str, handler)
        assert result is adapter

    def test_with_output_handler(self):
        """Test with_output_handler method."""
        adapter = WorkflowExecutorAdapter(id="test")
        handler = AsyncMock()
        result = adapter.with_output_handler(handler)
        assert result is adapter


class TestWorkflowExecutorAdapterLifecycle:
    """Test WorkflowExecutorAdapter lifecycle methods."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialize method."""
        adapter = WorkflowExecutorAdapter(id="test")
        await adapter.initialize()
        assert adapter.is_initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize is idempotent."""
        adapter = WorkflowExecutorAdapter(id="test")
        await adapter.initialize()
        await adapter.initialize()  # Should not raise
        assert adapter.is_initialized is True

    def test_build(self):
        """Test build method."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        result = adapter.build()
        assert result is adapter
        assert adapter.is_built is True

    def test_build_without_workflow_raises(self):
        """Test that build without workflow raises ValueError."""
        adapter = WorkflowExecutorAdapter(id="test")
        with pytest.raises(ValueError, match="Workflow must be set"):
            adapter.build()

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup method."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()
        await adapter.initialize()
        await adapter.cleanup()
        assert adapter.is_built is False
        assert adapter.is_initialized is False

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test reset method."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()
        await adapter.reset()
        assert adapter.status == WorkflowExecutorStatus.IDLE


class TestWorkflowExecutorAdapterRun:
    """Test WorkflowExecutorAdapter run method."""

    @pytest.mark.asyncio
    async def test_run_basic(self):
        """Test basic run execution."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        result = await adapter.run("input data")
        assert result.status == WorkflowExecutorStatus.COMPLETED
        assert result.outputs == ["mock output"]
        assert result.workflow_id == "mock-workflow"

    @pytest.mark.asyncio
    async def test_run_without_build_raises(self):
        """Test that run without build raises ValueError."""
        adapter = WorkflowExecutorAdapter(id="test")
        with pytest.raises(ValueError, match="must be built"):
            await adapter.run("input")

    @pytest.mark.asyncio
    async def test_run_with_timeout(self):
        """Test run with timeout."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        result = await adapter.run("input", timeout_seconds=10.0)
        assert result.status == WorkflowExecutorStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_timeout_exceeded(self):
        """Test run with exceeded timeout."""

        class SlowWorkflow(MockWorkflow):
            async def run(self, input_data):
                await asyncio.sleep(2)
                return await super().run(input_data)

        workflow = SlowWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        result = await adapter.run("input", timeout_seconds=0.1)
        assert result.status == WorkflowExecutorStatus.FAILED
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_run_with_metadata(self):
        """Test run with metadata."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        result = await adapter.run("input", metadata={"key": "value"})
        assert result.status == WorkflowExecutorStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_error_handling(self):
        """Test run error handling."""

        class ErrorWorkflow(MockWorkflow):
            async def run(self, input_data):
                raise RuntimeError("Test error")

        workflow = ErrorWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        result = await adapter.run("input")
        assert result.status == WorkflowExecutorStatus.FAILED
        assert "Test error" in result.error


class TestWorkflowExecutorAdapterRequestResponse:
    """Test WorkflowExecutorAdapter request/response handling."""

    @pytest.mark.asyncio
    async def test_run_with_pending_requests(self):
        """Test run that generates pending requests."""
        workflow = RequestingWorkflow()
        event = RequestInfoEvent(
            request_id="req-1",
            data="need info",
            response_type=str,
            executor_id="exec-1",
        )
        workflow.add_request_event(event)

        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        result = await adapter.run("input")
        assert result.status == WorkflowExecutorStatus.WAITING_RESPONSE
        assert len(result.pending_requests) == 1
        assert result.pending_requests[0].source_event.request_id == "req-1"

    @pytest.mark.asyncio
    async def test_send_response(self):
        """Test send_response method."""
        workflow = RequestingWorkflow()
        event = RequestInfoEvent(
            request_id="req-1",
            data="need info",
            response_type=str,
            executor_id="exec-1",
        )
        workflow.add_request_event(event)

        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        # Run to generate request
        run_result = await adapter.run("input")
        assert len(run_result.pending_requests) == 1

        # Create and send response
        request = run_result.pending_requests[0]
        response = request.create_response("response data")

        # Clear request events to simulate completed workflow
        workflow._request_events.clear()

        response_result = await adapter.send_response(response)
        assert response_result is not None
        assert response_result.status == WorkflowExecutorStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_send_response_unknown_request(self):
        """Test send_response with unknown request_id."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        event = RequestInfoEvent(
            request_id="unknown-req",
            data="data",
            response_type=str,
        )
        response = SubWorkflowResponseMessage(data="response", source_event=event)

        result = await adapter.send_response(response)
        assert result is None

    @pytest.mark.asyncio
    async def test_send_responses_batch(self):
        """Test send_responses batch method."""
        workflow = RequestingWorkflow()
        event = RequestInfoEvent(
            request_id="req-1",
            data="need info",
            response_type=str,
        )
        workflow.add_request_event(event)

        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        run_result = await adapter.run("input")
        workflow._request_events.clear()

        result = await adapter.send_responses({"req-1": "response"})
        assert result is not None


class TestWorkflowExecutorAdapterCheckpoint:
    """Test WorkflowExecutorAdapter checkpoint methods."""

    @pytest.mark.asyncio
    async def test_checkpoint_save(self):
        """Test on_checkpoint_save method."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        state = await adapter.on_checkpoint_save()
        assert "execution_contexts" in state
        assert "request_to_execution" in state
        assert "status" in state

    @pytest.mark.asyncio
    async def test_checkpoint_restore(self):
        """Test on_checkpoint_restore method."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        state = {
            "execution_contexts": {
                "exec-1": {
                    "execution_id": "exec-1",
                    "collected_responses": {},
                    "expected_response_count": 0,
                    "pending_requests": {},
                    "started_at": 0,
                    "metadata": {},
                }
            },
            "request_to_execution": {},
            "status": "idle",
        }

        await adapter.on_checkpoint_restore(state)
        assert adapter.active_execution_count == 1

    @pytest.mark.asyncio
    async def test_checkpoint_restore_missing_key_raises(self):
        """Test that checkpoint restore with missing key raises."""
        adapter = WorkflowExecutorAdapter(id="test")
        with pytest.raises(KeyError):
            await adapter.on_checkpoint_restore({})


class TestWorkflowExecutorAdapterState:
    """Test WorkflowExecutorAdapter state methods."""

    def test_get_state(self):
        """Test get_state method."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        state = adapter.get_state()
        assert state["id"] == "test"
        assert state["is_built"] is True
        assert state["workflow_id"] == "mock-workflow"

    def test_get_events(self):
        """Test get_events method."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        events = adapter.get_events()
        assert len(events) == 1
        assert events[0]["type"] == "built"

    def test_clear_events(self):
        """Test clear_events method."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()
        adapter.clear_events()

        events = adapter.get_events()
        assert len(events) == 0


class TestWorkflowExecutorAdapterContextManager:
    """Test WorkflowExecutorAdapter context manager support."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager usage."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        async with adapter as ctx:
            assert ctx is adapter
            assert adapter.is_initialized is True

        assert adapter.is_initialized is False


# =============================================================================
# Tests - SimpleWorkflow
# =============================================================================


class TestSimpleWorkflow:
    """Test SimpleWorkflow class."""

    def test_creation(self):
        """Test SimpleWorkflow creation."""

        async def executor_fn(input_data, responses):
            return f"processed: {input_data}"

        workflow = SimpleWorkflow(
            id="simple-wf",
            executor_fn=executor_fn,
        )
        assert workflow.id == "simple-wf"

    @pytest.mark.asyncio
    async def test_run(self):
        """Test SimpleWorkflow run."""

        async def executor_fn(input_data, responses):
            return f"result: {input_data}"

        workflow = SimpleWorkflow(id="simple-wf", executor_fn=executor_fn)
        result = await workflow.run("test input")
        assert result.final_state == WorkflowRunState.COMPLETED
        assert len(result.outputs) == 1
        assert "test input" in result.outputs[0].data

    @pytest.mark.asyncio
    async def test_run_with_workflow_run_result(self):
        """Test SimpleWorkflow run returning WorkflowRunResult."""

        async def executor_fn(input_data, responses):
            return WorkflowRunResult(
                outputs=[WorkflowOutput(data="custom output")],
                final_state=WorkflowRunState.COMPLETED,
            )

        workflow = SimpleWorkflow(id="simple-wf", executor_fn=executor_fn)
        result = await workflow.run("test")
        assert result.outputs[0].data == "custom output"

    @pytest.mark.asyncio
    async def test_run_error(self):
        """Test SimpleWorkflow run with error."""

        async def executor_fn(input_data, responses):
            raise ValueError("Test error")

        workflow = SimpleWorkflow(id="simple-wf", executor_fn=executor_fn)
        result = await workflow.run("test")
        assert result.final_state == WorkflowRunState.FAILED
        assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_send_responses(self):
        """Test SimpleWorkflow send_responses."""

        async def executor_fn(input_data, responses):
            if responses:
                return f"got response: {responses}"
            return "no response"

        workflow = SimpleWorkflow(id="simple-wf", executor_fn=executor_fn)
        result = await workflow.send_responses({"key": "value"})
        assert result.final_state == WorkflowRunState.COMPLETED


# =============================================================================
# Tests - Factory Functions
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_workflow_executor(self):
        """Test create_workflow_executor factory."""
        adapter = create_workflow_executor(
            id="factory-adapter",
            allow_direct_output=True,
        )
        assert adapter.id == "factory-adapter"
        assert adapter.allow_direct_output is True

    def test_create_workflow_executor_with_workflow(self):
        """Test create_workflow_executor with workflow."""
        workflow = MockWorkflow()
        adapter = create_workflow_executor(
            id="factory-adapter",
            workflow=workflow,
        )
        assert adapter.workflow == workflow

    def test_create_simple_workflow(self):
        """Test create_simple_workflow factory."""

        async def executor(data, responses):
            return data

        workflow = create_simple_workflow(
            id="simple",
            executor_fn=executor,
            input_types=[str],
            output_types=[str],
        )
        assert workflow.id == "simple"
        assert workflow.input_types == [str]
        assert workflow.output_types == [str]

    def test_create_nested_workflow_executor(self):
        """Test create_nested_workflow_executor factory."""
        parent = MockWorkflow("parent")
        child1 = MockWorkflow("child-1")
        child2 = MockWorkflow("child-2")

        adapter = create_nested_workflow_executor(
            id="nested",
            parent_workflow=parent,
            child_workflows=[child1, child2],
        )
        assert adapter.id == "nested"
        assert adapter.workflow == parent
        assert "child_executors" in adapter._config


# =============================================================================
# Tests - Concurrent Execution
# =============================================================================


class TestConcurrentExecution:
    """Test concurrent execution support."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_runs(self):
        """Test multiple concurrent run calls."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        # Start multiple concurrent runs
        tasks = [
            adapter.run(f"input-{i}")
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks)

        # All should complete
        for result in results:
            assert result.status == WorkflowExecutorStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execution_isolation(self):
        """Test that executions are isolated."""
        workflow = MockWorkflow()
        adapter = WorkflowExecutorAdapter(id="test", workflow=workflow)
        adapter.build()

        result1 = await adapter.run("input-1", metadata={"test": 1})
        result2 = await adapter.run("input-2", metadata={"test": 2})

        # Each should have unique execution_id
        assert result1.execution_id != result2.execution_id


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for WorkflowExecutorAdapter."""

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self):
        """Test complete workflow lifecycle."""
        # Create workflow
        async def process(data, responses):
            return f"Processed: {data}"

        workflow = create_simple_workflow(
            id="integration-wf",
            executor_fn=process,
        )

        # Create adapter
        adapter = create_workflow_executor(
            id="integration-adapter",
            workflow=workflow,
        )

        # Build and initialize
        adapter.build()
        await adapter.initialize()

        # Run
        result = await adapter.run("test data")
        assert result.status == WorkflowExecutorStatus.COMPLETED
        assert "Processed: test data" in result.outputs[0]

        # Cleanup
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_request_response_cycle(self):
        """Test complete request/response cycle."""
        call_count = 0

        async def process(data, responses):
            nonlocal call_count
            call_count += 1

            if call_count == 1 and not responses:
                # First call - request info
                event = RequestInfoEvent(
                    request_id="req-1",
                    data="need approval",
                    response_type=bool,
                )
                return WorkflowRunResult(
                    request_info_events=[event],
                    final_state=WorkflowRunState.IN_PROGRESS_PENDING_REQUESTS,
                )
            else:
                # Second call - use response
                approved = responses.get("req-1", False)
                return WorkflowRunResult(
                    outputs=[WorkflowOutput(data=f"Approved: {approved}")],
                    final_state=WorkflowRunState.COMPLETED,
                )

        workflow = create_simple_workflow(id="req-wf", executor_fn=process)
        adapter = create_workflow_executor(id="req-adapter", workflow=workflow)
        adapter.build()

        # Initial run - should get request
        result = await adapter.run("start")
        assert result.status == WorkflowExecutorStatus.WAITING_RESPONSE
        assert len(result.pending_requests) == 1

        # Send response
        request = result.pending_requests[0]
        response = request.create_response(True)
        final_result = await adapter.send_response(response)

        assert final_result is not None
        assert final_result.status == WorkflowExecutorStatus.COMPLETED
        assert "Approved: True" in final_result.outputs[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
