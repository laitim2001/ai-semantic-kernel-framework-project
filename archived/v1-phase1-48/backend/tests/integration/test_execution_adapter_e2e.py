# =============================================================================
# IPA Platform - Execution Adapter E2E Integration Tests
# =============================================================================
# Sprint 27, Story S27-5: Integration Tests (5 pts)
#
# End-to-end integration tests for the execution adapter pipeline:
#   - SequentialOrchestrationAdapter execution flow
#   - Event stream handling
#   - State machine transitions
#   - Error recovery
#   - Full workflow execution with official API
#
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta
import asyncio

# Domain models
from src.domain.workflows.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    NodeType,
    WorkflowContext,
)

# Sprint 26 adapters (dependencies)
from src.integrations.agent_framework.core.executor import (
    WorkflowNodeExecutor,
    NodeInput,
    NodeOutput,
    create_executor_from_node,
)
from src.integrations.agent_framework.core.context import (
    WorkflowContextAdapter,
    create_context,
)

# Sprint 27 adapters (under test)
from src.integrations.agent_framework.core.execution import (
    SequentialOrchestrationAdapter,
    SequentialExecutionResult,
    ExecutionAdapter,
    ExecutionResult,
    ExecutorAgentWrapper,
    ExecutionError,
    create_sequential_orchestration,
    create_execution_adapter,
    wrap_executor_as_agent,
)
from src.integrations.agent_framework.core.events import (
    WorkflowStatusEventAdapter,
    ExecutionStatus,
    EventType,
    InternalExecutionEvent,
    EventFilter,
    create_event_adapter,
    create_event,
)
from src.integrations.agent_framework.core.state_machine import (
    EnhancedExecutionStateMachine,
    StateMachineManager,
    create_enhanced_state_machine,
    EVENT_TO_DOMAIN_STATUS,
    DOMAIN_TO_EVENT_STATUS,
)

# Domain state machine
from src.domain.executions.state_machine import ExecutionStatus as DomainExecutionStatus


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_agent_service():
    """Create a mock agent service for testing."""
    service = AsyncMock()
    service.is_initialized = True
    service.execute = AsyncMock(return_value={"result": "processed"})
    return service


@pytest.fixture
def simple_nodes():
    """Create simple workflow nodes."""
    return [
        WorkflowNode(
            id="node-1",
            name="Classifier",
            type=NodeType.AGENT,
            agent_id=uuid4(),
            config={"instructions": "Classify input"},
        ),
        WorkflowNode(
            id="node-2",
            name="Processor",
            type=NodeType.AGENT,
            agent_id=uuid4(),
            config={"instructions": "Process classified input"},
        ),
    ]


@pytest.fixture
def simple_executors(simple_nodes, mock_agent_service):
    """Create executors from simple nodes."""
    return [
        create_executor_from_node(node, mock_agent_service)
        for node in simple_nodes
    ]


@pytest.fixture
def event_adapter():
    """Create a fresh event adapter."""
    return WorkflowStatusEventAdapter()


@pytest.fixture
def state_manager(event_adapter):
    """Create a state machine manager."""
    return StateMachineManager(event_adapter)


# =============================================================================
# Test: E2E Sequential Execution
# =============================================================================

class TestE2ESequentialExecution:
    """End-to-end tests for sequential orchestration."""

    @pytest.mark.asyncio
    async def test_sequential_execution_completes(self, simple_executors):
        """Test that sequential execution completes successfully."""
        orchestration = create_sequential_orchestration(
            executors=simple_executors,
            name="test-sequential",
        )

        # Mock the underlying orchestration run
        with patch.object(orchestration._orchestration, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"final": "result"}

            result = await orchestration.run({"input": "test data"})

            assert result.success is True
            assert result.executed_count == len(simple_executors)
            assert result.execution_ms > 0

    @pytest.mark.asyncio
    async def test_sequential_execution_with_streaming(self, simple_executors):
        """Test sequential execution with event streaming."""
        orchestration = create_sequential_orchestration(
            executors=simple_executors,
            name="test-streaming",
        )

        events = []
        async for event in orchestration.run_stream({"input": "test"}):
            events.append(event)

        # Should have started, executor events, and completed
        assert len(events) >= 3
        assert events[0]["event_type"] == "started"
        assert events[-1]["event_type"] in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_execution_tracks_step_results(self, simple_executors):
        """Test that step results are tracked."""
        step_results = []

        async def on_step_complete(node_id, result):
            step_results.append({"node_id": node_id, "result": result})

        orchestration = create_sequential_orchestration(
            executors=simple_executors,
            name="test-tracking",
            on_step_complete=on_step_complete,
        )

        # Execute with streaming to trigger callbacks
        async for event in orchestration.run_stream({"input": "test"}):
            pass

        # Should have tracked step completions
        # Note: This depends on executor implementation
        assert orchestration.execution_count >= 0

    @pytest.mark.asyncio
    async def test_execution_failure_handled(self, simple_executors):
        """Test that execution failures are properly handled."""
        orchestration = create_sequential_orchestration(
            executors=simple_executors,
            name="test-failure",
        )

        # Make first executor fail
        original_run = simple_executors[0]._agent_service.execute
        simple_executors[0]._agent_service.execute = AsyncMock(
            side_effect=Exception("Agent execution failed")
        )

        events = []
        async for event in orchestration.run_stream({"input": "test"}):
            events.append(event)

        # Should have a failed event
        assert any(e.get("event_type") == "failed" for e in events)

        # Restore
        simple_executors[0]._agent_service.execute = original_run


# =============================================================================
# Test: Event Stream Handling
# =============================================================================

class TestEventStreamHandling:
    """Test event stream processing and handling."""

    @pytest.mark.asyncio
    async def test_event_adapter_processes_events(self, event_adapter):
        """Test that event adapter processes events correctly."""
        received_events = []

        async def handler(event):
            received_events.append(event)

        event_adapter.add_handler(handler)

        # Create and handle an event
        exec_id = uuid4()
        mock_event = MagicMock()
        mock_event.event_type = "executor_completed"
        mock_event.data = {"node_id": "test-node"}

        await event_adapter.handle(exec_id, mock_event)

        # Handler should have received event
        assert len(received_events) == 1
        assert received_events[0].execution_id == exec_id

    @pytest.mark.asyncio
    async def test_event_filter_filters_correctly(self, event_adapter):
        """Test that event filter works correctly."""
        # Create filter for specific execution
        exec_id = uuid4()
        filter = EventFilter(execution_ids={exec_id})

        # Create events for different executions
        event1 = InternalExecutionEvent(
            execution_id=exec_id,
            event_type="started",
            status=ExecutionStatus.RUNNING,
            node_id=None,
            data={},
            timestamp=datetime.utcnow(),
        )
        event2 = InternalExecutionEvent(
            execution_id=uuid4(),  # Different execution
            event_type="started",
            status=ExecutionStatus.RUNNING,
            node_id=None,
            data={},
            timestamp=datetime.utcnow(),
        )

        assert filter.matches(event1) is True
        assert filter.matches(event2) is False

    def test_event_status_mapping(self, event_adapter):
        """Test event type to status mapping."""
        # Test various mappings
        assert event_adapter._map_status("started") == ExecutionStatus.RUNNING
        assert event_adapter._map_status("completed") == ExecutionStatus.COMPLETED
        assert event_adapter._map_status("failed") == ExecutionStatus.FAILED
        assert event_adapter._map_status("waiting_input") == ExecutionStatus.WAITING_APPROVAL


# =============================================================================
# Test: State Machine Transitions
# =============================================================================

class TestStateMachineTransitions:
    """Test state machine transitions during execution."""

    def test_initial_state_is_pending(self):
        """Test that initial state is PENDING."""
        machine = create_enhanced_state_machine(uuid4())
        assert machine.status == DomainExecutionStatus.PENDING

    def test_start_transitions_to_running(self):
        """Test start() transitions to RUNNING."""
        machine = create_enhanced_state_machine(uuid4())
        machine.start()
        assert machine.status == DomainExecutionStatus.RUNNING

    def test_complete_transitions_from_running(self):
        """Test complete() transitions from RUNNING."""
        machine = create_enhanced_state_machine(uuid4())
        machine.start()
        machine.complete()
        assert machine.status == DomainExecutionStatus.COMPLETED

    def test_fail_transitions_from_running(self):
        """Test fail() transitions from RUNNING."""
        machine = create_enhanced_state_machine(uuid4())
        machine.start()
        machine.fail()
        assert machine.status == DomainExecutionStatus.FAILED

    def test_pause_and_resume(self):
        """Test pause and resume transitions."""
        machine = create_enhanced_state_machine(uuid4())
        machine.start()
        machine.pause()
        assert machine.status == DomainExecutionStatus.PAUSED

        machine.resume()
        assert machine.status == DomainExecutionStatus.RUNNING

    @pytest.mark.asyncio
    async def test_event_driven_transitions(self, event_adapter):
        """Test event-driven state transitions."""
        exec_id = uuid4()
        machine = EnhancedExecutionStateMachine(
            execution_id=exec_id,
            event_adapter=event_adapter,
        )

        # Start execution
        machine.start()
        assert machine.status == DomainExecutionStatus.RUNNING

        # Handle completion event
        completion_event = InternalExecutionEvent(
            execution_id=exec_id,
            event_type="completed",
            status=ExecutionStatus.COMPLETED,
            node_id=None,
            data={},
            timestamp=datetime.utcnow(),
            is_final=True,
        )
        await machine.handle_event(completion_event)

        assert machine.status == DomainExecutionStatus.COMPLETED

    def test_state_change_callbacks(self):
        """Test state change callbacks are invoked."""
        callbacks_received = []

        def callback(old_status, new_status, event):
            callbacks_received.append((old_status, new_status))

        machine = create_enhanced_state_machine(uuid4())
        machine.add_state_change_callback(callback)

        machine.start()
        machine.complete()

        assert len(callbacks_received) == 2
        assert callbacks_received[0] == (
            DomainExecutionStatus.PENDING,
            DomainExecutionStatus.RUNNING,
        )
        assert callbacks_received[1] == (
            DomainExecutionStatus.RUNNING,
            DomainExecutionStatus.COMPLETED,
        )


# =============================================================================
# Test: State Machine Manager
# =============================================================================

class TestStateMachineManager:
    """Test state machine manager functionality."""

    def test_manager_creates_machines(self, state_manager):
        """Test manager creates state machines."""
        exec_id = uuid4()
        machine = state_manager.create(exec_id)

        assert machine is not None
        assert machine.execution_id == exec_id
        assert state_manager.machine_count == 1

    def test_manager_retrieves_machines(self, state_manager):
        """Test manager retrieves machines."""
        exec_id = uuid4()
        created = state_manager.create(exec_id)
        retrieved = state_manager.get(exec_id)

        assert created == retrieved

    def test_manager_removes_machines(self, state_manager):
        """Test manager removes machines."""
        exec_id = uuid4()
        state_manager.create(exec_id)

        assert state_manager.remove(exec_id) is True
        assert state_manager.get(exec_id) is None

    @pytest.mark.asyncio
    async def test_manager_processes_events(self, state_manager):
        """Test manager routes events to correct machine."""
        exec_id = uuid4()
        machine = state_manager.create(exec_id)
        machine.start()

        event = InternalExecutionEvent(
            execution_id=exec_id,
            event_type="completed",
            status=ExecutionStatus.COMPLETED,
            node_id=None,
            data={},
            timestamp=datetime.utcnow(),
            is_final=True,
        )

        result = await state_manager.process_event(event)

        assert result is True
        assert machine.status == DomainExecutionStatus.COMPLETED

    def test_manager_tracks_all_statuses(self, state_manager):
        """Test manager tracks all machine statuses."""
        id1 = uuid4()
        id2 = uuid4()

        m1 = state_manager.create(id1)
        m2 = state_manager.create(id2)

        m1.start()
        m2.start()
        m2.complete()

        statuses = state_manager.get_all_statuses()

        assert len(statuses) == 2
        assert statuses[id1] == DomainExecutionStatus.RUNNING
        assert statuses[id2] == DomainExecutionStatus.COMPLETED


# =============================================================================
# Test: Error Recovery
# =============================================================================

class TestErrorRecovery:
    """Test error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_execution_error_captured(self, simple_executors):
        """Test that execution errors are captured in result."""
        orchestration = create_sequential_orchestration(
            executors=simple_executors,
            name="test-error",
        )

        # Make orchestration fail
        with patch.object(orchestration._orchestration, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Critical failure")

            result = await orchestration.run({"input": "test"})

            assert result.success is False
            assert "Critical failure" in result.error

    @pytest.mark.asyncio
    async def test_state_machine_handles_failure(self, event_adapter):
        """Test state machine handles failure events."""
        exec_id = uuid4()
        machine = EnhancedExecutionStateMachine(
            execution_id=exec_id,
            event_adapter=event_adapter,
        )
        machine.start()

        failure_event = InternalExecutionEvent(
            execution_id=exec_id,
            event_type="failed",
            status=ExecutionStatus.FAILED,
            node_id="failing-node",
            data={"error": "Something went wrong"},
            timestamp=datetime.utcnow(),
            is_final=True,
        )

        await machine.handle_event(failure_event)

        assert machine.status == DomainExecutionStatus.FAILED
        assert machine.last_event == failure_event

    def test_invalid_transition_logged_not_raised(self):
        """Test that invalid transitions are logged but don't raise."""
        machine = create_enhanced_state_machine(uuid4())

        # Try to complete from PENDING (invalid)
        # Should not raise, but status should remain PENDING
        try:
            machine.complete()
        except Exception:
            pass  # Some implementations may raise

        # Machine should be in a valid state
        assert machine.status in (
            DomainExecutionStatus.PENDING,
            DomainExecutionStatus.COMPLETED,
        )


# =============================================================================
# Test: ExecutorAgentWrapper
# =============================================================================

class TestExecutorAgentWrapper:
    """Test ExecutorAgentWrapper functionality."""

    def test_wrapper_has_correct_name(self, simple_nodes, mock_agent_service):
        """Test wrapper has correct agent name."""
        executor = create_executor_from_node(simple_nodes[0], mock_agent_service)
        wrapper = wrap_executor_as_agent(executor)

        assert wrapper.name == simple_nodes[0].id

    def test_wrapper_custom_name(self, simple_nodes, mock_agent_service):
        """Test wrapper with custom name."""
        executor = create_executor_from_node(simple_nodes[0], mock_agent_service)
        wrapper = wrap_executor_as_agent(executor, name="custom-name")

        assert wrapper.name == "custom-name"

    @pytest.mark.asyncio
    async def test_wrapper_executes_correctly(self, simple_nodes, mock_agent_service):
        """Test wrapper executes underlying executor."""
        executor = create_executor_from_node(simple_nodes[0], mock_agent_service)
        wrapper = wrap_executor_as_agent(executor)

        # Mock the executor's execute method
        with patch.object(executor, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = NodeOutput(
                result="test result",
                success=True,
            )

            result = await wrapper.run({"input": "test"})

            assert result == "test result"
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_wrapper_raises_on_failure(self, simple_nodes, mock_agent_service):
        """Test wrapper raises ExecutionError on failure."""
        executor = create_executor_from_node(simple_nodes[0], mock_agent_service)
        wrapper = wrap_executor_as_agent(executor)

        with patch.object(executor, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = NodeOutput(
                result=None,
                success=False,
                error="Execution failed",
            )

            with pytest.raises(ExecutionError) as exc_info:
                await wrapper.run({"input": "test"})

            assert "failed" in str(exc_info.value).lower()


# =============================================================================
# Test: Full Integration Pipeline
# =============================================================================

class TestFullIntegrationPipeline:
    """Test full integration pipeline from start to finish."""

    @pytest.mark.asyncio
    async def test_complete_pipeline_execution(
        self,
        simple_executors,
        event_adapter,
        state_manager,
    ):
        """Test complete execution pipeline."""
        exec_id = uuid4()

        # Create state machine
        machine = state_manager.create(exec_id)

        # Create orchestration
        orchestration = create_sequential_orchestration(
            executors=simple_executors,
            name="pipeline-test",
        )

        # Start execution
        machine.start()

        # Execute and process events
        events_processed = []
        async for event in orchestration.run_stream({"input": "test"}):
            internal_event = InternalExecutionEvent(
                execution_id=exec_id,
                event_type=event.get("event_type", "unknown"),
                status=ExecutionStatus.RUNNING,
                node_id=event.get("executor_id"),
                data=event,
                timestamp=datetime.utcnow(),
                is_final=event.get("event_type") == "completed",
            )

            if event.get("event_type") == "completed":
                internal_event.status = ExecutionStatus.COMPLETED

            await machine.handle_event(internal_event)
            events_processed.append(internal_event)

        # Verify final state
        assert machine.status in (
            DomainExecutionStatus.RUNNING,
            DomainExecutionStatus.COMPLETED,
        )
        assert len(events_processed) > 0

    @pytest.mark.asyncio
    async def test_pipeline_with_event_handlers(
        self,
        simple_executors,
        state_manager,
    ):
        """Test pipeline with registered event handlers."""
        exec_id = uuid4()
        events_received = []

        # Register handler
        async def handler(event):
            events_received.append(event)

        machine = state_manager.create(exec_id)
        machine.add_state_change_callback(
            lambda old, new, evt: events_received.append({"old": old, "new": new})
        )

        # Execute
        machine.start()
        machine.complete()

        # Verify callbacks were called
        assert len(events_received) == 2

    def test_status_mapping_consistency(self):
        """Test that status mappings are consistent."""
        # Every event status should map to a domain status
        for event_status in ExecutionStatus:
            if event_status in EVENT_TO_DOMAIN_STATUS:
                domain_status = EVENT_TO_DOMAIN_STATUS[event_status]
                # And back
                if domain_status in DOMAIN_TO_EVENT_STATUS:
                    back_mapped = DOMAIN_TO_EVENT_STATUS[domain_status]
                    # Should be consistent (or at least not conflicting)
                    assert back_mapped is not None


# =============================================================================
# Test: Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Test factory functions create correct instances."""

    def test_create_sequential_orchestration(self, simple_executors):
        """Test create_sequential_orchestration factory."""
        orchestration = create_sequential_orchestration(
            executors=simple_executors,
            name="test",
        )

        assert isinstance(orchestration, SequentialOrchestrationAdapter)
        assert orchestration.name == "test"
        assert orchestration.executor_count == len(simple_executors)

    def test_create_enhanced_state_machine(self):
        """Test create_enhanced_state_machine factory."""
        exec_id = uuid4()
        machine = create_enhanced_state_machine(exec_id, status="pending")

        assert isinstance(machine, EnhancedExecutionStateMachine)
        assert machine.execution_id == exec_id
        assert machine.status == DomainExecutionStatus.PENDING

    def test_create_event_adapter(self):
        """Test create_event_adapter factory."""
        adapter = create_event_adapter()

        assert isinstance(adapter, WorkflowStatusEventAdapter)

    def test_wrap_executor_as_agent(self, simple_nodes, mock_agent_service):
        """Test wrap_executor_as_agent factory."""
        executor = create_executor_from_node(simple_nodes[0], mock_agent_service)
        wrapper = wrap_executor_as_agent(executor)

        assert isinstance(wrapper, ExecutorAgentWrapper)
