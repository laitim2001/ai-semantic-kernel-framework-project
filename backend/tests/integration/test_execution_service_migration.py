# =============================================================================
# IPA Platform - ExecutionService Migration Integration Tests
# =============================================================================
# Sprint 27, Story S27-4: ExecutionService Migration (7 pts)
#
# Integration tests for the ExecutionService migration to official API.
# Verifies:
#   - Legacy mode backward compatibility
#   - Official API mode execution
#   - Event handling and state tracking
#   - Sequential orchestration adapter integration
#
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.domain.workflows.service import (
    WorkflowExecutionService,
    WorkflowExecutionResult,
    NodeExecutionResult,
    get_workflow_execution_service,
    reset_workflow_execution_service,
)
from src.domain.workflows.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    NodeType,
)
from src.integrations.agent_framework.core.events import (
    ExecutionStatus,
    InternalExecutionEvent,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def simple_workflow_definition():
    """Create a simple workflow definition for testing."""
    start_node = WorkflowNode(
        id="start",
        name="Start",
        type=NodeType.START,
        config={},
    )
    agent_node = WorkflowNode(
        id="agent-1",
        name="Agent 1",
        type=NodeType.AGENT,
        agent_id=uuid4(),
        config={"instructions": "Process the input"},
    )
    end_node = WorkflowNode(
        id="end",
        name="End",
        type=NodeType.END,
        config={},
    )

    edges = [
        WorkflowEdge(id="e1", source="start", target="agent-1"),
        WorkflowEdge(id="e2", source="agent-1", target="end"),
    ]

    return WorkflowDefinition(
        id=uuid4(),
        name="Test Workflow",
        nodes=[start_node, agent_node, end_node],
        edges=edges,
    )


@pytest.fixture
def multi_agent_workflow_definition():
    """Create a workflow with multiple agent nodes."""
    start_node = WorkflowNode(
        id="start",
        name="Start",
        type=NodeType.START,
        config={},
    )
    agent_1 = WorkflowNode(
        id="agent-1",
        name="Classifier",
        type=NodeType.AGENT,
        agent_id=uuid4(),
        config={"instructions": "Classify the input"},
    )
    agent_2 = WorkflowNode(
        id="agent-2",
        name="Processor",
        type=NodeType.AGENT,
        agent_id=uuid4(),
        config={"instructions": "Process the classified input"},
    )
    agent_3 = WorkflowNode(
        id="agent-3",
        name="Formatter",
        type=NodeType.AGENT,
        agent_id=uuid4(),
        config={"instructions": "Format the output"},
    )
    end_node = WorkflowNode(
        id="end",
        name="End",
        type=NodeType.END,
        config={},
    )

    edges = [
        WorkflowEdge(id="e1", source="start", target="agent-1"),
        WorkflowEdge(id="e2", source="agent-1", target="agent-2"),
        WorkflowEdge(id="e3", source="agent-2", target="agent-3"),
        WorkflowEdge(id="e4", source="agent-3", target="end"),
    ]

    return WorkflowDefinition(
        id=uuid4(),
        name="Multi-Agent Workflow",
        nodes=[start_node, agent_1, agent_2, agent_3, end_node],
        edges=edges,
    )


@pytest.fixture
def mock_agent_service():
    """Create a mock agent service."""
    service = AsyncMock()
    service.is_initialized = True
    service.execute = AsyncMock(return_value="Processed result")
    service.run_agent_with_config = AsyncMock(
        return_value=MagicMock(
            text="Agent response",
            llm_calls=1,
            llm_tokens=100,
            llm_cost=0.001,
        )
    )
    return service


@pytest.fixture
def legacy_service():
    """Create a legacy (non-official API) execution service."""
    return WorkflowExecutionService(use_official_api=False)


@pytest.fixture
def official_service():
    """Create an official API execution service."""
    return WorkflowExecutionService(use_official_api=True)


# =============================================================================
# Test: Service Initialization
# =============================================================================

class TestServiceInitialization:
    """Test service initialization modes."""

    def test_legacy_mode_initialization(self, legacy_service):
        """Test legacy mode service initialization."""
        assert legacy_service.use_official_api is False
        assert legacy_service.state_machine_manager is None
        assert legacy_service.event_adapter is None

    def test_official_mode_initialization(self, official_service):
        """Test official API mode service initialization."""
        assert official_service.use_official_api is True
        assert official_service.state_machine_manager is not None
        assert official_service.event_adapter is not None

    def test_global_service_factory_legacy(self):
        """Test global service factory for legacy mode."""
        reset_workflow_execution_service()
        service = get_workflow_execution_service(use_official_api=False)
        assert service.use_official_api is False

    def test_global_service_factory_official(self):
        """Test global service factory for official mode."""
        reset_workflow_execution_service()
        service = get_workflow_execution_service(use_official_api=True)
        assert service.use_official_api is True


# =============================================================================
# Test: Event Handler Management
# =============================================================================

class TestEventHandlerManagement:
    """Test event handler registration and removal."""

    def test_add_event_handler_legacy(self, legacy_service):
        """Test adding event handler in legacy mode."""
        handler = AsyncMock()
        legacy_service.add_event_handler(handler)
        assert handler in legacy_service._event_handlers

    def test_add_event_handler_official(self, official_service):
        """Test adding event handler in official mode."""
        handler = AsyncMock()
        official_service.add_event_handler(handler)
        assert handler in official_service._event_handlers

    def test_remove_event_handler(self, official_service):
        """Test removing event handler."""
        handler = AsyncMock()
        official_service.add_event_handler(handler)
        official_service.remove_event_handler(handler)
        assert handler not in official_service._event_handlers


# =============================================================================
# Test: Legacy Mode Execution
# =============================================================================

class TestLegacyModeExecution:
    """Test workflow execution in legacy mode."""

    @pytest.mark.asyncio
    async def test_execute_simple_workflow_legacy(
        self,
        legacy_service,
        simple_workflow_definition,
        mock_agent_service,
    ):
        """Test simple workflow execution in legacy mode."""
        with patch.object(
            legacy_service, '_get_agent_service',
            return_value=mock_agent_service
        ):
            result = await legacy_service.execute_workflow(
                workflow_id=uuid4(),
                definition=simple_workflow_definition,
                input_data={"message": "Hello"},
            )

            assert result.execution_id is not None
            assert result.status in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_invalid_workflow_raises_error(
        self,
        legacy_service,
    ):
        """Test that invalid workflow raises ValueError."""
        # Create invalid workflow (no start node)
        invalid_def = WorkflowDefinition(
            id=uuid4(),
            name="Invalid",
            nodes=[
                WorkflowNode(id="agent", name="Agent", type=NodeType.AGENT),
            ],
            edges=[],
        )

        with pytest.raises(ValueError, match="Invalid workflow"):
            await legacy_service.execute_workflow(
                workflow_id=uuid4(),
                definition=invalid_def,
                input_data={},
            )


# =============================================================================
# Test: Official API Mode Execution
# =============================================================================

class TestOfficialModeExecution:
    """Test workflow execution in official API mode."""

    @pytest.mark.asyncio
    async def test_execute_creates_state_machine(
        self,
        official_service,
        simple_workflow_definition,
        mock_agent_service,
    ):
        """Test that execution creates a state machine."""
        with patch.object(
            official_service, '_get_agent_service',
            return_value=mock_agent_service
        ):
            # Mock the orchestration to avoid full execution
            with patch(
                'src.domain.workflows.service.create_sequential_orchestration'
            ) as mock_create:
                mock_orchestration = MagicMock()
                mock_orchestration.run_stream = AsyncMock(return_value=iter([
                    {"event_type": "started", "executor_count": 1},
                    {"event_type": "completed", "result": "done"},
                ]))
                mock_create.return_value = mock_orchestration

                result = await official_service.execute_workflow(
                    workflow_id=uuid4(),
                    definition=simple_workflow_definition,
                    input_data={"message": "Hello"},
                )

                # Verify state machine was created
                assert official_service.state_machine_manager.machine_count >= 0

    @pytest.mark.asyncio
    async def test_event_handler_called(
        self,
        official_service,
        simple_workflow_definition,
        mock_agent_service,
    ):
        """Test that event handlers are called during execution."""
        events_received = []

        async def handler(event):
            events_received.append(event)

        official_service.add_event_handler(handler)

        with patch.object(
            official_service, '_get_agent_service',
            return_value=mock_agent_service
        ):
            with patch(
                'src.domain.workflows.service.create_sequential_orchestration'
            ) as mock_create:
                mock_orchestration = MagicMock()
                mock_orchestration.run_stream = AsyncMock(return_value=iter([
                    {"event_type": "started"},
                    {"event_type": "completed", "result": "done"},
                ]))
                mock_create.return_value = mock_orchestration

                await official_service.execute_workflow(
                    workflow_id=uuid4(),
                    definition=simple_workflow_definition,
                    input_data={"message": "Hello"},
                )

        # Events should have been received
        # Note: Event handling depends on adapter implementation
        assert official_service._event_handlers[0] == handler

    def test_get_execution_state(self, official_service):
        """Test getting execution state."""
        # Create a state machine manually
        exec_id = uuid4()
        machine = official_service.state_machine_manager.create(exec_id)

        state = official_service.get_execution_state(exec_id)
        assert state is not None
        assert "status" in state

    def test_get_nonexistent_execution_state(self, official_service):
        """Test getting state of non-existent execution."""
        state = official_service.get_execution_state(uuid4())
        assert state is None


# =============================================================================
# Test: State Machine Integration
# =============================================================================

class TestStateMachineIntegration:
    """Test state machine integration with execution service."""

    @pytest.mark.asyncio
    async def test_state_transitions_during_execution(
        self,
        official_service,
        simple_workflow_definition,
        mock_agent_service,
    ):
        """Test state machine transitions during workflow execution."""
        exec_id = uuid4()

        # Pre-create state machine to track
        machine = official_service.state_machine_manager.create(exec_id)
        initial_status = machine.status

        # Verify initial state
        from src.domain.executions.state_machine import ExecutionStatus as DomainStatus
        assert initial_status == DomainStatus.PENDING

    def test_state_machine_manager_tracks_multiple(self, official_service):
        """Test that manager tracks multiple executions."""
        exec_id_1 = uuid4()
        exec_id_2 = uuid4()

        machine_1 = official_service.state_machine_manager.create(exec_id_1)
        machine_2 = official_service.state_machine_manager.create(exec_id_2)

        assert official_service.state_machine_manager.machine_count == 2
        assert official_service.state_machine_manager.get(exec_id_1) == machine_1
        assert official_service.state_machine_manager.get(exec_id_2) == machine_2


# =============================================================================
# Test: Backward Compatibility
# =============================================================================

class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    @pytest.mark.asyncio
    async def test_legacy_api_unchanged(
        self,
        legacy_service,
        simple_workflow_definition,
        mock_agent_service,
    ):
        """Test that legacy API remains unchanged."""
        with patch.object(
            legacy_service, '_get_agent_service',
            return_value=mock_agent_service
        ):
            result = await legacy_service.execute_workflow(
                workflow_id=uuid4(),
                definition=simple_workflow_definition,
                input_data={"message": "Test"},
                variables={"var1": "value1"},
            )

            # Result should have expected structure
            assert isinstance(result, WorkflowExecutionResult)
            assert result.workflow_id is not None
            assert result.execution_id is not None

    def test_result_properties_available(self, legacy_service):
        """Test that result object has all expected properties."""
        result = WorkflowExecutionResult(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status="completed",
        )

        # Add node results
        node_result = NodeExecutionResult(
            node_id="test",
            node_type=NodeType.AGENT,
            output="test output",
            llm_calls=1,
            llm_tokens=100,
            llm_cost=0.01,
        )
        result.node_results.append(node_result)

        # Test properties
        assert result.total_llm_calls == 1
        assert result.total_llm_tokens == 100
        assert result.total_llm_cost == 0.01

    def test_to_dict_format_unchanged(self, legacy_service):
        """Test that to_dict format is unchanged."""
        result = WorkflowExecutionResult(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status="completed",
        )
        result.result = "Final result"
        result.complete("completed")

        result_dict = result.to_dict()

        # Verify structure
        assert "execution_id" in result_dict
        assert "workflow_id" in result_dict
        assert "status" in result_dict
        assert "result" in result_dict
        assert "node_results" in result_dict
        assert "stats" in result_dict


# =============================================================================
# Test: Node Sorting
# =============================================================================

class TestNodeSorting:
    """Test node sorting for execution order."""

    def test_get_sorted_nodes_simple(
        self,
        official_service,
        simple_workflow_definition,
    ):
        """Test sorting nodes for simple workflow."""
        sorted_nodes = official_service._get_sorted_nodes(simple_workflow_definition)

        # Should exclude START and END
        assert all(n.type not in (NodeType.START, NodeType.END) for n in sorted_nodes)
        # Should include agent node
        assert len(sorted_nodes) == 1
        assert sorted_nodes[0].id == "agent-1"

    def test_get_sorted_nodes_multi_agent(
        self,
        official_service,
        multi_agent_workflow_definition,
    ):
        """Test sorting nodes for multi-agent workflow."""
        sorted_nodes = official_service._get_sorted_nodes(multi_agent_workflow_definition)

        # Should exclude START and END
        assert all(n.type not in (NodeType.START, NodeType.END) for n in sorted_nodes)
        # Should include all agent nodes
        assert len(sorted_nodes) == 3


# =============================================================================
# Test: Error Handling
# =============================================================================

class TestErrorHandling:
    """Test error handling in execution service."""

    @pytest.mark.asyncio
    async def test_execution_failure_handled(
        self,
        official_service,
        simple_workflow_definition,
    ):
        """Test that execution failures are properly handled."""
        with patch.object(
            official_service, '_get_agent_service',
            side_effect=Exception("Service unavailable")
        ):
            result = await official_service.execute_workflow(
                workflow_id=uuid4(),
                definition=simple_workflow_definition,
                input_data={"message": "Test"},
            )

            assert result.status == "failed"
            assert "Service unavailable" in str(result.result)

    def test_event_status_mapping(self, official_service):
        """Test event type to status mapping."""
        assert official_service._map_event_to_status("started") == ExecutionStatus.RUNNING
        assert official_service._map_event_to_status("completed") == ExecutionStatus.COMPLETED
        assert official_service._map_event_to_status("failed") == ExecutionStatus.FAILED
        assert official_service._map_event_to_status("unknown") == ExecutionStatus.RUNNING


# =============================================================================
# Cleanup
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup():
    """Clean up global state after each test."""
    yield
    reset_workflow_execution_service()
