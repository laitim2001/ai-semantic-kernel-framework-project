# =============================================================================
# IPA Platform - WorkflowNodeExecutor Unit Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26, Story S26-1: WorkflowNodeExecutor (8 pts)
#
# Tests for the WorkflowNodeExecutor adapter that connects WorkflowNode
# to the official Agent Framework Executor interface.
#
# Test Coverage:
#   - Executor creation and initialization
#   - START node execution
#   - END node execution
#   - AGENT node execution
#   - GATEWAY node execution (exclusive, parallel, inclusive)
#   - Error handling
#   - Condition evaluation
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from src.integrations.agent_framework.core.executor import (
    WorkflowNodeExecutor,
    NodeInput,
    NodeOutput,
    create_executor_from_node,
)
from src.domain.workflows.models import WorkflowNode, NodeType


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_agent_service():
    """Create a mock agent service."""
    service = MagicMock()
    service.execute = AsyncMock(return_value={"response": "Agent executed successfully"})
    return service


@pytest.fixture
def mock_context():
    """Create a mock workflow context."""
    context = MagicMock()
    context._state = {}

    def get_state(key, default=None):
        return context._state.get(key, default)

    def set_state(key, value):
        context._state[key] = value

    context.get = MagicMock(side_effect=get_state)
    context.set = MagicMock(side_effect=set_state)
    context.run_id = uuid4()
    return context


@pytest.fixture
def start_node():
    """Create a START node."""
    return WorkflowNode(
        id="start",
        type=NodeType.START,
        name="Workflow Start",
        config={"initial_variables": {"workflow_version": "1.0"}}
    )


@pytest.fixture
def end_node():
    """Create an END node."""
    return WorkflowNode(
        id="end",
        type=NodeType.END,
        name="Workflow End",
        config={}
    )


@pytest.fixture
def agent_node():
    """Create an AGENT node."""
    return WorkflowNode(
        id="classifier",
        type=NodeType.AGENT,
        name="Intent Classifier",
        agent_id=uuid4(),
        config={
            "agent_config": {"temperature": 0.7},
            "output_key": "classification_result"
        }
    )


@pytest.fixture
def gateway_node():
    """Create a GATEWAY node."""
    return WorkflowNode(
        id="router",
        type=NodeType.GATEWAY,
        name="Request Router",
        config={
            "gateway_type": "exclusive",
            "conditions": [
                {"expression": "intent == 'billing'", "target": "billing_agent"},
                {"expression": "intent == 'support'", "target": "support_agent"},
            ],
            "default_target": "general_agent"
        }
    )


@pytest.fixture
def function_registry():
    """Create a function registry for gateway conditions."""
    def check_priority(data, context):
        return data.get("priority", "low") == "high"

    async def async_check(data, context):
        return data.get("async_check", False)

    return {
        "check_priority": check_priority,
        "async_check": async_check,
    }


# =============================================================================
# Test: Executor Creation
# =============================================================================

class TestExecutorCreation:
    """Tests for executor creation and initialization."""

    def test_create_executor_with_start_node(self, start_node):
        """Test creating executor with START node."""
        executor = WorkflowNodeExecutor(node=start_node)

        assert executor.id == "start"
        assert executor.node == start_node
        assert executor.node_type == NodeType.START

    def test_create_executor_with_agent_node(self, agent_node, mock_agent_service):
        """Test creating executor with AGENT node."""
        executor = WorkflowNodeExecutor(
            node=agent_node,
            agent_service=mock_agent_service
        )

        assert executor.id == "classifier"
        assert executor.node_type == NodeType.AGENT
        assert executor._agent_service == mock_agent_service

    def test_create_agent_executor_without_service_logs_warning(self, agent_node, caplog):
        """Test that creating AGENT executor without service logs warning."""
        with caplog.at_level("WARNING"):
            executor = WorkflowNodeExecutor(node=agent_node)

        assert "without agent_service" in caplog.text

    def test_factory_function(self, agent_node, mock_agent_service):
        """Test create_executor_from_node factory function."""
        executor = create_executor_from_node(
            node=agent_node,
            agent_service=mock_agent_service
        )

        assert isinstance(executor, WorkflowNodeExecutor)
        assert executor.node == agent_node


# =============================================================================
# Test: START Node Execution
# =============================================================================

class TestStartNodeExecution:
    """Tests for START node execution."""

    @pytest.mark.asyncio
    async def test_start_node_passes_through_input(self, start_node, mock_context):
        """Test START node passes through input data."""
        executor = WorkflowNodeExecutor(node=start_node)
        input_data = NodeInput(data={"query": "Hello", "user_id": "123"})

        result = await executor.execute(input_data, mock_context)

        assert result.success is True
        assert result.result == {"query": "Hello", "user_id": "123"}
        assert result.metadata["node_id"] == "start"
        assert result.metadata["node_type"] == "start"

    @pytest.mark.asyncio
    async def test_start_node_sets_initial_variables(self, start_node, mock_context):
        """Test START node sets initial variables in context."""
        executor = WorkflowNodeExecutor(node=start_node)
        input_data = NodeInput(data={"test": "data"})

        await executor.execute(input_data, mock_context)

        mock_context.set.assert_called_with("workflow_version", "1.0")


# =============================================================================
# Test: END Node Execution
# =============================================================================

class TestEndNodeExecution:
    """Tests for END node execution."""

    @pytest.mark.asyncio
    async def test_end_node_returns_input(self, end_node, mock_context):
        """Test END node returns input data."""
        executor = WorkflowNodeExecutor(node=end_node)
        input_data = NodeInput(data={"final_result": "completed"})

        result = await executor.execute(input_data, mock_context)

        assert result.success is True
        assert result.result == {"final_result": "completed"}
        assert result.metadata["node_type"] == "end"

    @pytest.mark.asyncio
    async def test_end_node_with_output_key(self, mock_context):
        """Test END node retrieves from context when output_key specified."""
        end_node = WorkflowNode(
            id="end",
            type=NodeType.END,
            config={"output_key": "aggregated_result"}
        )
        executor = WorkflowNodeExecutor(node=end_node)

        # Set value in context
        mock_context._state["aggregated_result"] = {"summary": "All tasks done"}

        input_data = NodeInput(data={"ignored": "data"})
        result = await executor.execute(input_data, mock_context)

        assert result.result == {"summary": "All tasks done"}


# =============================================================================
# Test: AGENT Node Execution
# =============================================================================

class TestAgentNodeExecution:
    """Tests for AGENT node execution."""

    @pytest.mark.asyncio
    async def test_agent_node_calls_agent_service(
        self,
        agent_node,
        mock_agent_service,
        mock_context
    ):
        """Test AGENT node calls agent service correctly."""
        executor = WorkflowNodeExecutor(
            node=agent_node,
            agent_service=mock_agent_service
        )
        input_data = NodeInput(data={"query": "What is my balance?"})

        result = await executor.execute(input_data, mock_context)

        assert result.success is True
        mock_agent_service.execute.assert_called_once()
        call_args = mock_agent_service.execute.call_args
        assert call_args.kwargs["agent_id"] == agent_node.agent_id

    @pytest.mark.asyncio
    async def test_agent_node_stores_result_in_context(
        self,
        agent_node,
        mock_agent_service,
        mock_context
    ):
        """Test AGENT node stores result in context when output_key set."""
        executor = WorkflowNodeExecutor(
            node=agent_node,
            agent_service=mock_agent_service
        )
        input_data = NodeInput(data={"query": "Test"})

        await executor.execute(input_data, mock_context)

        # Check context.set was called with output_key
        set_calls = [call for call in mock_context.set.call_args_list
                     if call[0][0] == "classification_result"]
        assert len(set_calls) == 1

    @pytest.mark.asyncio
    async def test_agent_node_without_agent_id_fails(self, mock_agent_service, mock_context):
        """Test AGENT node without agent_id raises error."""
        # Create agent node without agent_id (skip validation)
        node = WorkflowNode.__new__(WorkflowNode)
        node.id = "bad_agent"
        node.type = NodeType.AGENT
        node.agent_id = None
        node.config = {}
        node.name = None
        node.position = None

        executor = WorkflowNodeExecutor(node=node, agent_service=mock_agent_service)
        input_data = NodeInput(data={"query": "Test"})

        result = await executor.execute(input_data, mock_context)

        assert result.success is False
        assert "requires agent_id" in result.error

    @pytest.mark.asyncio
    async def test_agent_node_without_service_fails(self, agent_node, mock_context):
        """Test AGENT node without agent_service raises error."""
        executor = WorkflowNodeExecutor(node=agent_node, agent_service=None)
        input_data = NodeInput(data={"query": "Test"})

        result = await executor.execute(input_data, mock_context)

        assert result.success is False
        assert "requires agent_service" in result.error


# =============================================================================
# Test: GATEWAY Node Execution
# =============================================================================

class TestGatewayNodeExecution:
    """Tests for GATEWAY node execution."""

    @pytest.mark.asyncio
    async def test_exclusive_gateway_routes_correctly(
        self,
        gateway_node,
        mock_context
    ):
        """Test exclusive gateway routes to matching condition."""
        executor = WorkflowNodeExecutor(node=gateway_node)
        input_data = NodeInput(data={"intent": "billing"})

        result = await executor.execute(input_data, mock_context)

        assert result.success is True
        assert result.result["gateway_type"] == "exclusive"
        assert result.result["target"] == "billing_agent"

    @pytest.mark.asyncio
    async def test_exclusive_gateway_uses_default(
        self,
        gateway_node,
        mock_context
    ):
        """Test exclusive gateway uses default when no condition matches."""
        executor = WorkflowNodeExecutor(node=gateway_node)
        input_data = NodeInput(data={"intent": "unknown"})

        result = await executor.execute(input_data, mock_context)

        assert result.success is True
        assert result.result["target"] == "general_agent"

    @pytest.mark.asyncio
    async def test_parallel_gateway_returns_all_targets(self, mock_context):
        """Test parallel gateway returns all targets."""
        parallel_node = WorkflowNode(
            id="parallel",
            type=NodeType.GATEWAY,
            config={"gateway_type": "parallel"}
        )
        executor = WorkflowNodeExecutor(node=parallel_node)
        input_data = NodeInput(data={"task": "process"})

        result = await executor.execute(input_data, mock_context)

        assert result.result["gateway_type"] == "parallel"
        assert result.result["all_targets"] is True

    @pytest.mark.asyncio
    async def test_inclusive_gateway_returns_multiple_targets(self, mock_context):
        """Test inclusive gateway returns multiple matching targets."""
        inclusive_node = WorkflowNode(
            id="inclusive",
            type=NodeType.GATEWAY,
            config={
                "gateway_type": "inclusive",
                "conditions": [
                    {"expression": "notify_email == True", "target": "email_sender"},
                    {"expression": "notify_sms == True", "target": "sms_sender"},
                ]
            }
        )
        executor = WorkflowNodeExecutor(node=inclusive_node)
        input_data = NodeInput(data={"notify_email": True, "notify_sms": True})

        result = await executor.execute(input_data, mock_context)

        assert result.result["gateway_type"] == "inclusive"
        assert "email_sender" in result.result["targets"]
        assert "sms_sender" in result.result["targets"]


# =============================================================================
# Test: Condition Evaluation
# =============================================================================

class TestConditionEvaluation:
    """Tests for gateway condition evaluation."""

    @pytest.mark.asyncio
    async def test_function_based_condition(
        self,
        function_registry,
        mock_context
    ):
        """Test function-based condition evaluation."""
        node = WorkflowNode(
            id="function_gateway",
            type=NodeType.GATEWAY,
            config={
                "gateway_type": "exclusive",
                "conditions": [
                    {"function": "check_priority", "target": "priority_handler"},
                ],
                "default_target": "normal_handler"
            }
        )
        executor = WorkflowNodeExecutor(
            node=node,
            function_registry=function_registry
        )

        # High priority input
        input_data = NodeInput(data={"priority": "high"})
        result = await executor.execute(input_data, mock_context)
        assert result.result["target"] == "priority_handler"

        # Low priority input
        input_data = NodeInput(data={"priority": "low"})
        result = await executor.execute(input_data, mock_context)
        assert result.result["target"] == "normal_handler"

    @pytest.mark.asyncio
    async def test_expression_equality(self, mock_context):
        """Test expression-based equality condition."""
        node = WorkflowNode(
            id="expr_gateway",
            type=NodeType.GATEWAY,
            config={
                "gateway_type": "exclusive",
                "conditions": [
                    {"expression": "status == 'approved'", "target": "approve_handler"},
                ],
                "default_target": "review_handler"
            }
        )
        executor = WorkflowNodeExecutor(node=node)

        input_data = NodeInput(data={"status": "approved"})
        result = await executor.execute(input_data, mock_context)
        assert result.result["target"] == "approve_handler"

    @pytest.mark.asyncio
    async def test_expression_numeric_comparison(self, mock_context):
        """Test numeric comparison in expressions."""
        node = WorkflowNode(
            id="num_gateway",
            type=NodeType.GATEWAY,
            config={
                "gateway_type": "exclusive",
                "conditions": [
                    {"expression": "amount > 1000", "target": "high_value"},
                ],
                "default_target": "standard"
            }
        )
        executor = WorkflowNodeExecutor(node=node)

        input_data = NodeInput(data={"amount": 1500})
        result = await executor.execute(input_data, mock_context)
        assert result.result["target"] == "high_value"

        input_data = NodeInput(data={"amount": 500})
        result = await executor.execute(input_data, mock_context)
        assert result.result["target"] == "standard"


# =============================================================================
# Test: Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_agent_service_error_captured(
        self,
        agent_node,
        mock_agent_service,
        mock_context
    ):
        """Test that agent service errors are captured properly."""
        mock_agent_service.execute.side_effect = Exception("Agent execution failed")

        executor = WorkflowNodeExecutor(
            node=agent_node,
            agent_service=mock_agent_service
        )
        input_data = NodeInput(data={"query": "Test"})

        result = await executor.execute(input_data, mock_context)

        assert result.success is False
        assert "Agent execution failed" in result.error
        assert result.metadata["error_type"] == "Exception"

    @pytest.mark.asyncio
    async def test_execution_includes_timing_metadata(
        self,
        start_node,
        mock_context
    ):
        """Test that execution includes timing metadata."""
        executor = WorkflowNodeExecutor(node=start_node)
        input_data = NodeInput(data={"test": "data"})

        result = await executor.execute(input_data, mock_context)

        assert "execution_ms" in result.metadata
        assert "timestamp" in result.metadata
        assert result.metadata["execution_ms"] >= 0


# =============================================================================
# Test: Input/Output Models
# =============================================================================

class TestInputOutputModels:
    """Tests for NodeInput and NodeOutput models."""

    def test_node_input_default_values(self):
        """Test NodeInput has proper defaults."""
        input_data = NodeInput()

        assert input_data.data == {}
        assert input_data.execution_id is None
        assert input_data.context == {}
        assert input_data.metadata == {}

    def test_node_input_with_values(self):
        """Test NodeInput with provided values."""
        exec_id = uuid4()
        input_data = NodeInput(
            data={"query": "test"},
            execution_id=exec_id,
            context={"user": "admin"},
            metadata={"trace_id": "abc"}
        )

        assert input_data.data == {"query": "test"}
        assert input_data.execution_id == exec_id
        assert input_data.context == {"user": "admin"}
        assert input_data.metadata == {"trace_id": "abc"}

    def test_node_output_default_values(self):
        """Test NodeOutput has proper defaults."""
        output = NodeOutput()

        assert output.result is None
        assert output.success is True
        assert output.error is None
        assert output.metadata == {}
        assert output.next_nodes == []

    def test_node_output_with_error(self):
        """Test NodeOutput with error."""
        output = NodeOutput(
            result=None,
            success=False,
            error="Something went wrong",
            metadata={"node_id": "test"}
        )

        assert output.success is False
        assert output.error == "Something went wrong"
