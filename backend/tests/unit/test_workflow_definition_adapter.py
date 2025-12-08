# =============================================================================
# IPA Platform - WorkflowDefinitionAdapter Unit Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26, Story S26-3: WorkflowDefinitionAdapter Tests
#
# Comprehensive tests for the WorkflowDefinitionAdapter including:
#   - Adapter creation and initialization
#   - Workflow building from definition
#   - Workflow execution
#   - Factory functions
#   - Integration scenarios
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.integrations.agent_framework.core.workflow import (
    WorkflowDefinitionAdapter,
    WorkflowRunResult,
    create_workflow_adapter,
    build_simple_workflow,
    build_branching_workflow,
)
from src.integrations.agent_framework.core.executor import (
    WorkflowNodeExecutor,
    NodeInput,
    NodeOutput,
)
from src.domain.workflows.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    NodeType,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_agent_service():
    """Create a mock agent service."""
    service = MagicMock()
    service.execute = AsyncMock(return_value={"output": "agent_result"})
    return service


@pytest.fixture
def simple_definition():
    """Create a simple workflow definition (start -> agent -> end)."""
    return WorkflowDefinition(
        nodes=[
            WorkflowNode(id="start", type=NodeType.START, name="Start"),
            WorkflowNode(
                id="agent1",
                type=NodeType.AGENT,
                name="Agent 1",
                agent_id=uuid4(),
            ),
            WorkflowNode(id="end", type=NodeType.END, name="End"),
        ],
        edges=[
            WorkflowEdge(source="start", target="agent1"),
            WorkflowEdge(source="agent1", target="end"),
        ],
    )


@pytest.fixture
def branching_definition():
    """Create a branching workflow definition with gateway."""
    return WorkflowDefinition(
        nodes=[
            WorkflowNode(id="start", type=NodeType.START),
            WorkflowNode(
                id="gateway",
                type=NodeType.GATEWAY,
                config={"gateway_type": "exclusive"},
            ),
            WorkflowNode(id="branch_a", type=NodeType.AGENT, agent_id=uuid4()),
            WorkflowNode(id="branch_b", type=NodeType.AGENT, agent_id=uuid4()),
            WorkflowNode(id="end", type=NodeType.END),
        ],
        edges=[
            WorkflowEdge(source="start", target="gateway"),
            WorkflowEdge(source="gateway", target="branch_a", condition="path == 'a'"),
            WorkflowEdge(source="gateway", target="branch_b", condition="path == 'b'"),
            WorkflowEdge(source="branch_a", target="end"),
            WorkflowEdge(source="branch_b", target="end"),
        ],
    )


@pytest.fixture
def parallel_definition():
    """Create a parallel workflow definition."""
    return WorkflowDefinition(
        nodes=[
            WorkflowNode(id="start", type=NodeType.START),
            WorkflowNode(
                id="parallel_gateway",
                type=NodeType.GATEWAY,
                config={"gateway_type": "parallel"},
            ),
            WorkflowNode(id="task_1", type=NodeType.AGENT, agent_id=uuid4()),
            WorkflowNode(id="task_2", type=NodeType.AGENT, agent_id=uuid4()),
            WorkflowNode(id="task_3", type=NodeType.AGENT, agent_id=uuid4()),
            WorkflowNode(id="end", type=NodeType.END),
        ],
        edges=[
            WorkflowEdge(source="start", target="parallel_gateway"),
            WorkflowEdge(source="parallel_gateway", target="task_1"),
            WorkflowEdge(source="parallel_gateway", target="task_2"),
            WorkflowEdge(source="parallel_gateway", target="task_3"),
            WorkflowEdge(source="task_1", target="end"),
            WorkflowEdge(source="task_2", target="end"),
            WorkflowEdge(source="task_3", target="end"),
        ],
    )


# =============================================================================
# Test: WorkflowRunResult
# =============================================================================

class TestWorkflowRunResult:
    """Tests for WorkflowRunResult."""

    def test_create_success_result(self):
        """Test creating a successful result."""
        result = WorkflowRunResult(
            success=True,
            result={"data": "output"},
            execution_path=["start", "agent", "end"],
        )

        assert result.success is True
        assert result.result == {"data": "output"}
        assert result.execution_path == ["start", "agent", "end"]
        assert result.error is None

    def test_create_failure_result(self):
        """Test creating a failed result."""
        result = WorkflowRunResult(
            success=False,
            error="Execution failed",
        )

        assert result.success is False
        assert result.result is None
        assert result.error == "Execution failed"

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = WorkflowRunResult(
            success=True,
            result={"output": "value"},
            execution_path=["a", "b"],
            metadata={"key": "value"},
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["result"] == {"output": "value"}
        assert data["execution_path"] == ["a", "b"]
        assert "timestamp" in data

    def test_repr_success(self):
        """Test repr for successful result."""
        result = WorkflowRunResult(success=True, execution_path=["a", "b"])
        repr_str = repr(result)

        assert "✅" in repr_str
        assert "['a', 'b']" in repr_str

    def test_repr_failure(self):
        """Test repr for failed result."""
        result = WorkflowRunResult(success=False, execution_path=[])
        repr_str = repr(result)

        assert "❌" in repr_str


# =============================================================================
# Test: WorkflowDefinitionAdapter - Creation
# =============================================================================

class TestWorkflowDefinitionAdapterCreation:
    """Tests for WorkflowDefinitionAdapter creation."""

    def test_create_adapter(self, simple_definition, mock_agent_service):
        """Test creating an adapter."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        assert adapter.definition == simple_definition
        assert adapter.is_built is False

    def test_create_adapter_with_checkpoint_store(self, simple_definition):
        """Test creating adapter with checkpoint store."""
        checkpoint_store = MagicMock()

        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            checkpoint_store=checkpoint_store,
        )

        assert adapter._checkpoint_store == checkpoint_store

    def test_create_adapter_with_function_registry(self, simple_definition):
        """Test creating adapter with function registry."""
        func_registry = {"my_func": lambda x: x}

        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            function_registry=func_registry,
        )

        assert adapter._function_registry == func_registry

    def test_definition_property(self, simple_definition):
        """Test definition property access."""
        adapter = WorkflowDefinitionAdapter(definition=simple_definition)

        assert adapter.definition is simple_definition
        assert len(adapter.definition.nodes) == 3
        assert len(adapter.definition.edges) == 2


# =============================================================================
# Test: WorkflowDefinitionAdapter - Building
# =============================================================================

class TestWorkflowDefinitionAdapterBuilding:
    """Tests for WorkflowDefinitionAdapter building."""

    def test_build_simple_workflow(self, simple_definition, mock_agent_service):
        """Test building a simple workflow."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        workflow = adapter.build()

        assert workflow is not None
        assert adapter.is_built is True
        assert len(adapter.executors) == 3
        assert len(adapter.edges) == 2

    def test_build_creates_executors(self, simple_definition, mock_agent_service):
        """Test that building creates executors for all nodes."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        adapter.build()

        # Check executors were created
        assert len(adapter.executors) == 3

        # Check executor types
        executor_ids = [e.id for e in adapter.executors]
        assert "start" in executor_ids
        assert "agent1" in executor_ids
        assert "end" in executor_ids

    def test_build_creates_edges(self, simple_definition, mock_agent_service):
        """Test that building creates edges."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        adapter.build()

        assert len(adapter.edges) == 2

    def test_build_idempotent(self, simple_definition, mock_agent_service):
        """Test that building is idempotent."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        workflow1 = adapter.build()
        workflow2 = adapter.build()

        assert workflow1 is workflow2

    def test_build_branching_workflow(self, branching_definition, mock_agent_service):
        """Test building a branching workflow."""
        adapter = WorkflowDefinitionAdapter(
            definition=branching_definition,
            agent_service=mock_agent_service,
        )

        workflow = adapter.build()

        assert workflow is not None
        assert len(adapter.executors) == 5
        assert len(adapter.edges) == 5

    def test_build_parallel_workflow(self, parallel_definition, mock_agent_service):
        """Test building a parallel workflow."""
        adapter = WorkflowDefinitionAdapter(
            definition=parallel_definition,
            agent_service=mock_agent_service,
        )

        workflow = adapter.build()

        assert workflow is not None
        assert len(adapter.executors) == 6
        assert len(adapter.edges) == 7


# =============================================================================
# Test: WorkflowDefinitionAdapter - Execution
# =============================================================================

class TestWorkflowDefinitionAdapterExecution:
    """Tests for WorkflowDefinitionAdapter execution."""

    @pytest.mark.asyncio
    async def test_run_simple_workflow(self, simple_definition, mock_agent_service):
        """Test running a simple workflow."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        # Mock the workflow run
        with patch.object(adapter, "_workflow") as mock_workflow:
            mock_workflow.run = AsyncMock(return_value={"output": "success"})
            adapter._workflow = mock_workflow

            result = await adapter.run({"query": "test"})

            assert result.success is True
            assert result.error is None

    @pytest.mark.asyncio
    async def test_run_builds_if_needed(self, simple_definition, mock_agent_service):
        """Test that run builds the workflow if not already built."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        assert adapter.is_built is False

        # Mock the workflow run
        with patch.object(adapter, "build") as mock_build:
            mock_workflow = MagicMock()
            mock_workflow.run = AsyncMock(return_value={})
            mock_build.return_value = mock_workflow
            adapter._workflow = mock_workflow

            await adapter.run({"query": "test"})

    @pytest.mark.asyncio
    async def test_run_with_execution_id(self, simple_definition, mock_agent_service):
        """Test running with execution ID."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        execution_id = uuid4()

        with patch.object(adapter, "_workflow") as mock_workflow:
            mock_workflow.run = AsyncMock(return_value={})
            adapter._workflow = mock_workflow

            result = await adapter.run(
                {"query": "test"},
                execution_id=execution_id,
            )

            assert result.metadata.get("execution_id") == str(execution_id)

    @pytest.mark.asyncio
    async def test_run_captures_error(self, simple_definition, mock_agent_service):
        """Test that run captures errors."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        with patch.object(adapter, "_workflow") as mock_workflow:
            mock_workflow.run = AsyncMock(side_effect=Exception("Execution error"))
            adapter._workflow = mock_workflow

            result = await adapter.run({"query": "test"})

            assert result.success is False
            assert "Execution error" in result.error
            assert result.metadata.get("error_type") == "Exception"


# =============================================================================
# Test: WorkflowDefinitionAdapter - Streaming
# =============================================================================

class TestWorkflowDefinitionAdapterStreaming:
    """Tests for WorkflowDefinitionAdapter streaming."""

    @pytest.mark.asyncio
    async def test_run_stream_yields_events(self, simple_definition, mock_agent_service):
        """Test that run_stream yields events."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        async def mock_stream(input_data):
            yield {"node": "start", "status": "completed"}
            yield {"node": "agent1", "status": "completed"}
            yield {"node": "end", "status": "completed"}

        with patch.object(adapter, "_workflow") as mock_workflow:
            mock_workflow.run_stream = mock_stream
            adapter._workflow = mock_workflow

            events = []
            async for event in adapter.run_stream({"query": "test"}):
                events.append(event)

            assert len(events) == 3

    @pytest.mark.asyncio
    async def test_run_stream_fallback(self, simple_definition, mock_agent_service):
        """Test run_stream fallback when streaming not available."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        with patch.object(adapter, "_workflow") as mock_workflow:
            # No run_stream method
            del mock_workflow.run_stream
            mock_workflow.run = AsyncMock(return_value={"result": "done"})
            adapter._workflow = mock_workflow

            events = []
            async for event in adapter.run_stream({"query": "test"}):
                events.append(event)

            assert len(events) == 1
            assert events[0]["type"] == "final_result"

    @pytest.mark.asyncio
    async def test_run_stream_error(self, simple_definition, mock_agent_service):
        """Test run_stream error handling."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        with patch.object(adapter, "_workflow") as mock_workflow:
            mock_workflow.run = AsyncMock(side_effect=Exception("Stream error"))
            adapter._workflow = mock_workflow

            events = []
            async for event in adapter.run_stream({"query": "test"}):
                events.append(event)

            assert len(events) == 1
            assert events[0]["type"] == "error"
            assert "Stream error" in events[0]["error"]


# =============================================================================
# Test: WorkflowDefinitionAdapter - Helper Methods
# =============================================================================

class TestWorkflowDefinitionAdapterHelpers:
    """Tests for WorkflowDefinitionAdapter helper methods."""

    def test_get_executor(self, simple_definition, mock_agent_service):
        """Test getting executor by node ID."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        adapter.build()
        executor = adapter.get_executor("agent1")

        assert executor is not None
        assert executor.id == "agent1"

    def test_get_executor_not_found(self, simple_definition, mock_agent_service):
        """Test getting non-existent executor."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        adapter.build()
        executor = adapter.get_executor("nonexistent")

        assert executor is None

    def test_get_node_ids(self, simple_definition, mock_agent_service):
        """Test getting all node IDs."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        node_ids = adapter.get_node_ids()

        assert "start" in node_ids
        assert "agent1" in node_ids
        assert "end" in node_ids

    def test_get_start_node_id(self, simple_definition, mock_agent_service):
        """Test getting start node ID."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        start_id = adapter.get_start_node_id()

        assert start_id == "start"

    def test_get_end_node_ids(self, simple_definition, mock_agent_service):
        """Test getting end node IDs."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        end_ids = adapter.get_end_node_ids()

        assert "end" in end_ids

    def test_repr(self, simple_definition, mock_agent_service):
        """Test string representation."""
        adapter = WorkflowDefinitionAdapter(
            definition=simple_definition,
            agent_service=mock_agent_service,
        )

        repr_str = repr(adapter)

        assert "nodes=3" in repr_str
        assert "edges=2" in repr_str
        assert "not built" in repr_str

        adapter.build()
        repr_str = repr(adapter)
        assert "built" in repr_str


# =============================================================================
# Test: Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for workflow factory functions."""

    def test_create_workflow_adapter(self, mock_agent_service):
        """Test create_workflow_adapter factory."""
        nodes = [
            {"id": "start", "type": "start"},
            {"id": "end", "type": "end"},
        ]
        edges = [
            {"source": "start", "target": "end"},
        ]

        adapter = create_workflow_adapter(
            nodes=nodes,
            edges=edges,
            agent_service=mock_agent_service,
        )

        assert adapter is not None
        assert len(adapter.definition.nodes) == 2
        assert len(adapter.definition.edges) == 1

    def test_create_workflow_adapter_with_variables(self, mock_agent_service):
        """Test create_workflow_adapter with variables."""
        nodes = [
            {"id": "start", "type": "start"},
            {"id": "end", "type": "end"},
        ]
        edges = [
            {"source": "start", "target": "end"},
        ]
        variables = {"key": "value"}

        adapter = create_workflow_adapter(
            nodes=nodes,
            edges=edges,
            variables=variables,
            agent_service=mock_agent_service,
        )

        assert adapter.definition.variables == variables


class TestBuildSimpleWorkflow:
    """Tests for build_simple_workflow factory."""

    def test_build_start_to_end(self):
        """Test building workflow with just start and end."""
        start_node = WorkflowNode(id="start", type=NodeType.START)
        end_node = WorkflowNode(id="end", type=NodeType.END)

        start_executor = WorkflowNodeExecutor(node=start_node)
        end_executor = WorkflowNodeExecutor(node=end_node)

        workflow = build_simple_workflow(
            start_executor=start_executor,
            end_executor=end_executor,
        )

        assert workflow is not None

    def test_build_with_middle_nodes(self, mock_agent_service):
        """Test building workflow with middle nodes."""
        start_node = WorkflowNode(id="start", type=NodeType.START)
        middle_node = WorkflowNode(id="middle", type=NodeType.AGENT, agent_id=uuid4())
        end_node = WorkflowNode(id="end", type=NodeType.END)

        start_exec = WorkflowNodeExecutor(node=start_node)
        middle_exec = WorkflowNodeExecutor(
            node=middle_node,
            agent_service=mock_agent_service,
        )
        end_exec = WorkflowNodeExecutor(node=end_node)

        workflow = build_simple_workflow(
            start_executor=start_exec,
            end_executor=end_exec,
            middle_executors=[middle_exec],
        )

        assert workflow is not None


class TestBuildBranchingWorkflow:
    """Tests for build_branching_workflow factory."""

    def test_build_branching(self, mock_agent_service):
        """Test building branching workflow."""
        gateway_node = WorkflowNode(
            id="gateway",
            type=NodeType.GATEWAY,
            config={"gateway_type": "exclusive"},
        )
        branch_a_node = WorkflowNode(id="branch_a", type=NodeType.AGENT, agent_id=uuid4())
        branch_b_node = WorkflowNode(id="branch_b", type=NodeType.AGENT, agent_id=uuid4())
        merge_node = WorkflowNode(id="merge", type=NodeType.END)

        gateway_exec = WorkflowNodeExecutor(node=gateway_node)
        branch_a_exec = WorkflowNodeExecutor(
            node=branch_a_node,
            agent_service=mock_agent_service,
        )
        branch_b_exec = WorkflowNodeExecutor(
            node=branch_b_node,
            agent_service=mock_agent_service,
        )
        merge_exec = WorkflowNodeExecutor(node=merge_node)

        workflow = build_branching_workflow(
            gateway_executor=gateway_exec,
            branch_executors=[branch_a_exec, branch_b_exec],
            branch_conditions=["path == 'a'", "path == 'b'"],
            merge_executor=merge_exec,
        )

        assert workflow is not None

    def test_build_branching_mismatched_lengths(self, mock_agent_service):
        """Test that mismatched lengths raise error."""
        gateway_node = WorkflowNode(
            id="gateway",
            type=NodeType.GATEWAY,
        )
        branch_node = WorkflowNode(id="branch", type=NodeType.AGENT, agent_id=uuid4())
        merge_node = WorkflowNode(id="merge", type=NodeType.END)

        gateway_exec = WorkflowNodeExecutor(node=gateway_node)
        branch_exec = WorkflowNodeExecutor(
            node=branch_node,
            agent_service=mock_agent_service,
        )
        merge_exec = WorkflowNodeExecutor(node=merge_node)

        with pytest.raises(ValueError, match="same length"):
            build_branching_workflow(
                gateway_executor=gateway_exec,
                branch_executors=[branch_exec],
                branch_conditions=["a", "b"],  # Mismatched length
                merge_executor=merge_exec,
            )


# =============================================================================
# Test: Integration Scenarios
# =============================================================================

class TestIntegrationScenarios:
    """Integration tests for realistic workflow scenarios."""

    def test_customer_service_workflow(self, mock_agent_service):
        """Test a customer service routing workflow."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode(id="start", type=NodeType.START, name="Receive Request"),
                WorkflowNode(
                    id="classifier",
                    type=NodeType.AGENT,
                    name="Intent Classifier",
                    agent_id=uuid4(),
                ),
                WorkflowNode(
                    id="router",
                    type=NodeType.GATEWAY,
                    name="Intent Router",
                    config={"gateway_type": "exclusive"},
                ),
                WorkflowNode(
                    id="support",
                    type=NodeType.AGENT,
                    name="Support Agent",
                    agent_id=uuid4(),
                ),
                WorkflowNode(
                    id="sales",
                    type=NodeType.AGENT,
                    name="Sales Agent",
                    agent_id=uuid4(),
                ),
                WorkflowNode(
                    id="general",
                    type=NodeType.AGENT,
                    name="General Agent",
                    agent_id=uuid4(),
                ),
                WorkflowNode(id="end", type=NodeType.END, name="Send Response"),
            ],
            edges=[
                WorkflowEdge(source="start", target="classifier"),
                WorkflowEdge(source="classifier", target="router"),
                WorkflowEdge(
                    source="router",
                    target="support",
                    condition="intent == 'support'",
                ),
                WorkflowEdge(
                    source="router",
                    target="sales",
                    condition="intent == 'sales'",
                ),
                WorkflowEdge(
                    source="router",
                    target="general",
                    condition="intent not in ['support', 'sales']",
                ),
                WorkflowEdge(source="support", target="end"),
                WorkflowEdge(source="sales", target="end"),
                WorkflowEdge(source="general", target="end"),
            ],
            variables={"max_retries": 3, "timeout_seconds": 30},
        )

        adapter = WorkflowDefinitionAdapter(
            definition=definition,
            agent_service=mock_agent_service,
        )

        # Build should succeed
        workflow = adapter.build()

        assert workflow is not None
        assert len(adapter.executors) == 7
        assert len(adapter.edges) == 8

        # Check helper methods
        assert adapter.get_start_node_id() == "start"
        assert "end" in adapter.get_end_node_ids()
        assert adapter.get_executor("classifier") is not None

    def test_approval_workflow(self, mock_agent_service):
        """Test an approval workflow with parallel review."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode(id="start", type=NodeType.START),
                WorkflowNode(
                    id="parallel_review",
                    type=NodeType.GATEWAY,
                    config={"gateway_type": "parallel"},
                ),
                WorkflowNode(id="legal", type=NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode(id="finance", type=NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode(id="compliance", type=NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode(
                    id="merge",
                    type=NodeType.GATEWAY,
                    config={"gateway_type": "parallel"},
                ),
                WorkflowNode(id="final_decision", type=NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode(id="end", type=NodeType.END),
            ],
            edges=[
                WorkflowEdge(source="start", target="parallel_review"),
                WorkflowEdge(source="parallel_review", target="legal"),
                WorkflowEdge(source="parallel_review", target="finance"),
                WorkflowEdge(source="parallel_review", target="compliance"),
                WorkflowEdge(source="legal", target="merge"),
                WorkflowEdge(source="finance", target="merge"),
                WorkflowEdge(source="compliance", target="merge"),
                WorkflowEdge(source="merge", target="final_decision"),
                WorkflowEdge(source="final_decision", target="end"),
            ],
        )

        adapter = WorkflowDefinitionAdapter(
            definition=definition,
            agent_service=mock_agent_service,
        )

        workflow = adapter.build()

        assert workflow is not None
        assert len(adapter.executors) == 8
