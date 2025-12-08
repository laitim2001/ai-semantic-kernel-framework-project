# =============================================================================
# IPA Platform - SequentialOrchestrationAdapter Unit Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 27, Story S27-1: SequentialOrchestrationAdapter Tests
#
# Comprehensive tests for the SequentialOrchestrationAdapter including:
#   - Adapter creation and initialization
#   - Sequential execution
#   - Streaming execution
#   - Error handling
#   - Factory functions
# =============================================================================

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.integrations.agent_framework.core.execution import (
    SequentialOrchestrationAdapter,
    SequentialExecutionResult,
    ExecutorAgentWrapper,
    ExecutionAdapter,
    ExecutionResult,
    ExecutionError,
    create_sequential_orchestration,
    create_execution_adapter,
    wrap_executor_as_agent,
)
from src.integrations.agent_framework.core.executor import (
    WorkflowNodeExecutor,
    NodeInput,
    NodeOutput,
)
from src.domain.workflows.models import WorkflowNode, NodeType


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_agent_service():
    """Create a mock agent service."""
    service = AsyncMock()
    service.execute = AsyncMock(return_value={"response": "Agent executed"})
    return service


@pytest.fixture
def sample_node():
    """Create a sample workflow node."""
    return WorkflowNode(
        id="test-node-1",
        name="Test Node",
        type=NodeType.AGENT,
        agent_id=uuid4(),
        config={},
    )


@pytest.fixture
def start_node():
    """Create a START node."""
    return WorkflowNode(
        id="start",
        name="Start Node",
        type=NodeType.START,
        config={"initial_variables": {"initialized": True}},
    )


@pytest.fixture
def end_node():
    """Create an END node."""
    return WorkflowNode(
        id="end",
        name="End Node",
        type=NodeType.END,
        config={},
    )


@pytest.fixture
def agent_node(mock_agent_service):
    """Create an AGENT node."""
    return WorkflowNode(
        id="agent-1",
        name="Agent Node",
        type=NodeType.AGENT,
        agent_id=uuid4(),
        config={},
    )


@pytest.fixture
def executor(sample_node, mock_agent_service):
    """Create a WorkflowNodeExecutor."""
    return WorkflowNodeExecutor(
        node=sample_node,
        agent_service=mock_agent_service,
    )


@pytest.fixture
def start_executor(start_node):
    """Create a START node executor."""
    return WorkflowNodeExecutor(node=start_node)


@pytest.fixture
def end_executor(end_node):
    """Create an END node executor."""
    return WorkflowNodeExecutor(node=end_node)


@pytest.fixture
def agent_executor(agent_node, mock_agent_service):
    """Create an AGENT node executor."""
    return WorkflowNodeExecutor(
        node=agent_node,
        agent_service=mock_agent_service,
    )


@pytest.fixture
def three_executors(start_executor, agent_executor, end_executor):
    """Create a list of three executors."""
    return [start_executor, agent_executor, end_executor]


# =============================================================================
# Test: ExecutorAgentWrapper - Creation
# =============================================================================

class TestExecutorAgentWrapperCreation:
    """Tests for ExecutorAgentWrapper creation."""

    def test_create_wrapper(self, executor):
        """Test creating an executor agent wrapper."""
        wrapper = ExecutorAgentWrapper(executor=executor)

        assert wrapper.name == executor.id
        assert wrapper.executor is executor

    def test_create_with_custom_name(self, executor):
        """Test creating with custom name."""
        wrapper = ExecutorAgentWrapper(
            executor=executor,
            name="custom-name",
        )

        assert wrapper.name == "custom-name"

    def test_create_with_instructions(self, executor):
        """Test creating with custom instructions."""
        wrapper = ExecutorAgentWrapper(
            executor=executor,
            instructions="Custom instructions",
        )

        assert wrapper.instructions == "Custom instructions"

    def test_default_instructions(self, executor, sample_node):
        """Test default instructions."""
        wrapper = ExecutorAgentWrapper(executor=executor)

        assert sample_node.name in wrapper.instructions


# =============================================================================
# Test: ExecutorAgentWrapper - Execution
# =============================================================================

class TestExecutorAgentWrapperExecution:
    """Tests for ExecutorAgentWrapper execution."""

    @pytest.mark.asyncio
    async def test_run_with_dict(self, start_executor):
        """Test running with dict input."""
        wrapper = ExecutorAgentWrapper(executor=start_executor)

        result = await wrapper.run({"key": "value"})

        assert result is not None

    @pytest.mark.asyncio
    async def test_run_with_string(self, start_executor):
        """Test running with string input."""
        wrapper = ExecutorAgentWrapper(executor=start_executor)

        result = await wrapper.run("test input")

        assert result is not None

    @pytest.mark.asyncio
    async def test_run_with_node_input(self, start_executor):
        """Test running with NodeInput."""
        wrapper = ExecutorAgentWrapper(executor=start_executor)
        node_input = NodeInput(data={"test": "data"})

        result = await wrapper.run(node_input)

        assert result is not None

    @pytest.mark.asyncio
    async def test_run_streaming(self, start_executor):
        """Test streaming execution."""
        wrapper = ExecutorAgentWrapper(executor=start_executor)

        events = []
        async for event in wrapper.run_streaming({"input": "test"}):
            events.append(event)

        assert len(events) == 2  # started + completed
        assert events[0]["type"] == "started"
        assert events[1]["type"] == "completed"


# =============================================================================
# Test: SequentialOrchestrationAdapter - Creation
# =============================================================================

class TestSequentialOrchestrationAdapterCreation:
    """Tests for SequentialOrchestrationAdapter creation."""

    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    def test_create_adapter(self, mock_orch, three_executors):
        """Test creating a sequential orchestration adapter."""
        adapter = SequentialOrchestrationAdapter(
            executors=three_executors,
            name="test-workflow",
        )

        assert adapter.name == "test-workflow"
        assert adapter.executor_count == 3

    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    def test_default_name(self, mock_orch, three_executors):
        """Test default orchestration name."""
        adapter = SequentialOrchestrationAdapter(executors=three_executors)

        assert adapter.name == "sequential-workflow"

    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    def test_executor_ids(self, mock_orch, three_executors):
        """Test getting executor IDs."""
        adapter = SequentialOrchestrationAdapter(executors=three_executors)

        ids = adapter.executor_ids
        assert len(ids) == 3
        assert "start" in ids
        assert "end" in ids

    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    def test_get_executor(self, mock_orch, three_executors):
        """Test getting executor by ID."""
        adapter = SequentialOrchestrationAdapter(executors=three_executors)

        executor = adapter.get_executor("start")
        assert executor is not None
        assert executor.id == "start"

    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    def test_get_nonexistent_executor(self, mock_orch, three_executors):
        """Test getting nonexistent executor."""
        adapter = SequentialOrchestrationAdapter(executors=three_executors)

        executor = adapter.get_executor("nonexistent")
        assert executor is None


# =============================================================================
# Test: SequentialOrchestrationAdapter - Execution
# =============================================================================

class TestSequentialOrchestrationAdapterExecution:
    """Tests for SequentialOrchestrationAdapter execution."""

    @pytest.mark.asyncio
    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    async def test_run_success(self, mock_orch_class, three_executors):
        """Test successful execution."""
        # Setup mock
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value={"final": "result"})
        mock_orch_class.return_value = mock_orch

        adapter = SequentialOrchestrationAdapter(
            executors=three_executors,
            name="test-workflow",
        )

        result = await adapter.run({"input": "test"})

        assert isinstance(result, SequentialExecutionResult)
        assert result.success is True
        assert result.executed_count == 3

    @pytest.mark.asyncio
    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    async def test_run_failure(self, mock_orch_class, three_executors):
        """Test execution failure."""
        # Setup mock to raise exception
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(side_effect=Exception("Execution failed"))
        mock_orch_class.return_value = mock_orch

        adapter = SequentialOrchestrationAdapter(executors=three_executors)

        result = await adapter.run({"input": "test"})

        assert result.success is False
        assert "Execution failed" in result.error

    @pytest.mark.asyncio
    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    async def test_execution_count_increments(self, mock_orch_class, three_executors):
        """Test execution count increments."""
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value={"result": "ok"})
        mock_orch_class.return_value = mock_orch

        adapter = SequentialOrchestrationAdapter(executors=three_executors)

        assert adapter.execution_count == 0

        await adapter.run({})
        assert adapter.execution_count == 1

        await adapter.run({})
        assert adapter.execution_count == 2


# =============================================================================
# Test: SequentialOrchestrationAdapter - Streaming
# =============================================================================

class TestSequentialOrchestrationAdapterStreaming:
    """Tests for SequentialOrchestrationAdapter streaming."""

    @pytest.mark.asyncio
    async def test_run_stream_events(self, start_executor, end_executor):
        """Test streaming execution events."""
        executors = [start_executor, end_executor]

        with patch('src.integrations.agent_framework.core.execution.SequentialOrchestration'):
            adapter = SequentialOrchestrationAdapter(executors=executors)

            events = []
            async for event in adapter.run_stream({"input": "test"}):
                events.append(event)

            # Should have started, executor_started, executor_completed for each, and completed
            assert len(events) >= 3
            assert events[0]["event_type"] == "started"

    @pytest.mark.asyncio
    async def test_run_stream_callback(self, start_executor, end_executor):
        """Test step completion callback."""
        executors = [start_executor, end_executor]
        callback_calls = []

        async def on_step_complete(executor_id, result):
            callback_calls.append((executor_id, result))

        with patch('src.integrations.agent_framework.core.execution.SequentialOrchestration'):
            adapter = SequentialOrchestrationAdapter(
                executors=executors,
                on_step_complete=on_step_complete,
            )

            events = []
            async for event in adapter.run_stream({"input": "test"}):
                events.append(event)

            assert len(callback_calls) == 2  # One per executor


# =============================================================================
# Test: SequentialExecutionResult
# =============================================================================

class TestSequentialExecutionResult:
    """Tests for SequentialExecutionResult."""

    def test_create_success_result(self):
        """Test creating a success result."""
        result = SequentialExecutionResult(
            execution_id=uuid4(),
            success=True,
            result={"output": "value"},
            executed_count=3,
        )

        assert result.success is True
        assert result.executed_count == 3
        assert result.error is None

    def test_create_failure_result(self):
        """Test creating a failure result."""
        result = SequentialExecutionResult(
            execution_id=uuid4(),
            success=False,
            result=None,
            executed_count=1,
            error="Node failed",
            error_node_id="node-1",
        )

        assert result.success is False
        assert result.error == "Node failed"
        assert result.error_node_id == "node-1"

    def test_to_dict(self):
        """Test converting result to dict."""
        exec_id = uuid4()
        result = SequentialExecutionResult(
            execution_id=exec_id,
            success=True,
            result={"data": "value"},
            executed_count=2,
            execution_ms=150.5,
        )

        data = result.to_dict()

        assert data["execution_id"] == str(exec_id)
        assert data["success"] is True
        assert data["executed_count"] == 2
        assert data["execution_ms"] == 150.5


# =============================================================================
# Test: ExecutionAdapter - Creation
# =============================================================================

class TestExecutionAdapterCreation:
    """Tests for ExecutionAdapter creation."""

    def test_create_adapter(self):
        """Test creating an execution adapter."""
        mock_workflow_adapter = MagicMock()

        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        assert adapter._workflow_adapter is mock_workflow_adapter

    def test_create_with_checkpoint_store(self):
        """Test creating with checkpoint store."""
        mock_workflow_adapter = MagicMock()
        mock_checkpoint_store = MagicMock()

        adapter = ExecutionAdapter(
            workflow_adapter=mock_workflow_adapter,
            checkpoint_store=mock_checkpoint_store,
        )

        assert adapter._checkpoint_store is mock_checkpoint_store


# =============================================================================
# Test: ExecutionAdapter - Event Handlers
# =============================================================================

class TestExecutionAdapterEventHandlers:
    """Tests for ExecutionAdapter event handlers."""

    def test_add_event_handler(self):
        """Test adding an event handler."""
        mock_workflow_adapter = MagicMock()
        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        handler = AsyncMock()
        adapter.add_event_handler(handler)

        assert handler in adapter._event_handlers

    def test_remove_event_handler(self):
        """Test removing an event handler."""
        mock_workflow_adapter = MagicMock()
        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        handler = AsyncMock()
        adapter.add_event_handler(handler)
        adapter.remove_event_handler(handler)

        assert handler not in adapter._event_handlers

    def test_remove_nonexistent_handler(self):
        """Test removing nonexistent handler doesn't error."""
        mock_workflow_adapter = MagicMock()
        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        handler = AsyncMock()
        # Should not raise
        try:
            adapter.remove_event_handler(handler)
        except ValueError:
            pass  # Expected


# =============================================================================
# Test: ExecutionAdapter - Execution
# =============================================================================

class TestExecutionAdapterExecution:
    """Tests for ExecutionAdapter execution."""

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution."""
        mock_workflow_adapter = MagicMock()
        mock_workflow = MagicMock()
        mock_workflow_adapter.build.return_value = mock_workflow

        # Setup async generator for run_stream
        async def mock_run_stream(*args, **kwargs):
            yield {"type": "final_result", "data": {"output": "done"}}

        mock_workflow_adapter.run_stream = mock_run_stream

        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        result = await adapter.execute(
            execution_id=uuid4(),
            input_data={"input": "test"},
        )

        assert isinstance(result, ExecutionResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_event_handlers(self):
        """Test execution emits events to handlers."""
        mock_workflow_adapter = MagicMock()
        mock_workflow_adapter.build.return_value = MagicMock()

        events_received = []

        async def event_handler(exec_id, event):
            events_received.append(event)

        async def mock_run_stream(*args, **kwargs):
            yield {"type": "node_event", "data": "processing"}
            yield {"type": "final_result", "data": "done"}

        mock_workflow_adapter.run_stream = mock_run_stream

        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)
        adapter.add_event_handler(event_handler)

        await adapter.execute(
            execution_id=uuid4(),
            input_data={},
        )

        # Should have started, node events, and completed
        assert len(events_received) >= 3

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        """Test execution failure handling."""
        mock_workflow_adapter = MagicMock()
        mock_workflow_adapter.build.side_effect = Exception("Build failed")

        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        result = await adapter.execute(
            execution_id=uuid4(),
            input_data={},
        )

        assert result.success is False
        assert "Build failed" in result.error


# =============================================================================
# Test: ExecutionAdapter - Active Executions
# =============================================================================

class TestExecutionAdapterActiveExecutions:
    """Tests for ExecutionAdapter active execution tracking."""

    @pytest.mark.asyncio
    async def test_track_active_execution(self):
        """Test tracking active executions."""
        mock_workflow_adapter = MagicMock()
        mock_workflow_adapter.build.return_value = MagicMock()

        async def mock_run_stream(*args, **kwargs):
            yield {"type": "final_result", "data": "done"}

        mock_workflow_adapter.run_stream = mock_run_stream

        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        exec_id = uuid4()
        await adapter.execute(execution_id=exec_id, input_data={})

        status = adapter.get_active_execution(exec_id)
        assert status is not None
        assert status["status"] == "completed"

    def test_get_all_active_executions(self):
        """Test getting all active executions."""
        mock_workflow_adapter = MagicMock()
        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        all_executions = adapter.get_all_active_executions()
        assert isinstance(all_executions, dict)


# =============================================================================
# Test: ExecutionResult
# =============================================================================

class TestExecutionResult:
    """Tests for ExecutionResult."""

    def test_create_result(self):
        """Test creating an execution result."""
        exec_id = uuid4()
        result = ExecutionResult(
            execution_id=exec_id,
            success=True,
            result={"data": "value"},
            execution_ms=100.0,
        )

        assert result.execution_id == exec_id
        assert result.success is True
        assert result.execution_ms == 100.0

    def test_to_dict(self):
        """Test converting to dict."""
        exec_id = uuid4()
        result = ExecutionResult(
            execution_id=exec_id,
            success=False,
            result=None,
            error="Test error",
        )

        data = result.to_dict()

        assert data["execution_id"] == str(exec_id)
        assert data["success"] is False
        assert data["error"] == "Test error"


# =============================================================================
# Test: ExecutionError
# =============================================================================

class TestExecutionError:
    """Tests for ExecutionError."""

    def test_create_error(self):
        """Test creating an execution error."""
        error = ExecutionError(
            message="Node failed",
            node_id="node-1",
            error_details={"reason": "timeout"},
        )

        assert str(error) == "Node failed"
        assert error.node_id == "node-1"
        assert error.error_details["reason"] == "timeout"

    def test_error_without_details(self):
        """Test error without details."""
        error = ExecutionError(message="Simple error")

        assert error.node_id is None
        assert error.error_details == {}


# =============================================================================
# Test: Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    def test_create_sequential_orchestration(self, mock_orch, three_executors):
        """Test create_sequential_orchestration factory."""
        adapter = create_sequential_orchestration(
            executors=three_executors,
            name="factory-workflow",
        )

        assert isinstance(adapter, SequentialOrchestrationAdapter)
        assert adapter.name == "factory-workflow"

    def test_create_execution_adapter(self):
        """Test create_execution_adapter factory."""
        mock_workflow_adapter = MagicMock()

        adapter = create_execution_adapter(
            workflow_adapter=mock_workflow_adapter,
        )

        assert isinstance(adapter, ExecutionAdapter)

    def test_wrap_executor_as_agent(self, executor):
        """Test wrap_executor_as_agent factory."""
        agent = wrap_executor_as_agent(
            executor=executor,
            name="wrapped-agent",
        )

        assert isinstance(agent, ExecutorAgentWrapper)
        assert agent.name == "wrapped-agent"


# =============================================================================
# Test: Repr Methods
# =============================================================================

class TestReprMethods:
    """Tests for string representations."""

    @patch('src.integrations.agent_framework.core.execution.SequentialOrchestration')
    def test_sequential_adapter_repr(self, mock_orch, three_executors):
        """Test SequentialOrchestrationAdapter repr."""
        adapter = SequentialOrchestrationAdapter(
            executors=three_executors,
            name="test-repr",
        )

        repr_str = repr(adapter)

        assert "SequentialOrchestrationAdapter" in repr_str
        assert "test-repr" in repr_str

    def test_execution_adapter_repr(self):
        """Test ExecutionAdapter repr."""
        mock_workflow_adapter = MagicMock()
        adapter = ExecutionAdapter(workflow_adapter=mock_workflow_adapter)

        repr_str = repr(adapter)

        assert "ExecutionAdapter" in repr_str
