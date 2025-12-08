# =============================================================================
# IPA Platform - EnhancedExecutionStateMachine Unit Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 27, Story S27-3: ExecutionStateMachine Refactoring Tests
#
# Comprehensive tests for the EnhancedExecutionStateMachine including:
#   - Event-driven state transitions
#   - Backward compatibility
#   - State change callbacks
#   - Manager functionality
# =============================================================================

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.integrations.agent_framework.core.state_machine import (
    EnhancedExecutionStateMachine,
    StateMachineManager,
    create_enhanced_state_machine,
    wrap_state_machine,
    EVENT_TO_DOMAIN_STATUS,
    DOMAIN_TO_EVENT_STATUS,
)
from src.integrations.agent_framework.core.events import (
    WorkflowStatusEventAdapter,
    ExecutionStatus,
    InternalExecutionEvent,
)
from src.domain.executions.state_machine import (
    ExecutionStatus as DomainExecutionStatus,
    ExecutionStateMachine as DomainStateMachine,
    InvalidStateTransitionError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def execution_id():
    """Create a test execution ID."""
    return uuid4()


@pytest.fixture
def event_adapter():
    """Create a WorkflowStatusEventAdapter."""
    return WorkflowStatusEventAdapter()


@pytest.fixture
def enhanced_machine(execution_id, event_adapter):
    """Create an EnhancedExecutionStateMachine."""
    return EnhancedExecutionStateMachine(
        execution_id=execution_id,
        initial_status=DomainExecutionStatus.PENDING,
        event_adapter=event_adapter,
    )


@pytest.fixture
def running_machine(execution_id, event_adapter):
    """Create a running state machine."""
    machine = EnhancedExecutionStateMachine(
        execution_id=execution_id,
        event_adapter=event_adapter,
    )
    machine.start()
    return machine


@pytest.fixture
def sample_event(execution_id):
    """Create a sample internal event."""
    return InternalExecutionEvent(
        execution_id=execution_id,
        event_type="executor_completed",
        status=ExecutionStatus.RUNNING,
        node_id="node-1",
    )


# =============================================================================
# Test: Status Mappings
# =============================================================================

class TestStatusMappings:
    """Tests for status mapping dictionaries."""

    def test_event_to_domain_mapping(self):
        """Test event to domain status mapping."""
        assert EVENT_TO_DOMAIN_STATUS[ExecutionStatus.PENDING] == DomainExecutionStatus.PENDING
        assert EVENT_TO_DOMAIN_STATUS[ExecutionStatus.RUNNING] == DomainExecutionStatus.RUNNING
        assert EVENT_TO_DOMAIN_STATUS[ExecutionStatus.COMPLETED] == DomainExecutionStatus.COMPLETED
        assert EVENT_TO_DOMAIN_STATUS[ExecutionStatus.FAILED] == DomainExecutionStatus.FAILED

    def test_domain_to_event_mapping(self):
        """Test domain to event status mapping."""
        assert DOMAIN_TO_EVENT_STATUS[DomainExecutionStatus.PENDING] == ExecutionStatus.PENDING
        assert DOMAIN_TO_EVENT_STATUS[DomainExecutionStatus.RUNNING] == ExecutionStatus.RUNNING
        assert DOMAIN_TO_EVENT_STATUS[DomainExecutionStatus.COMPLETED] == ExecutionStatus.COMPLETED

    def test_waiting_approval_maps_to_paused(self):
        """Test waiting_approval maps to paused."""
        assert EVENT_TO_DOMAIN_STATUS[ExecutionStatus.WAITING_APPROVAL] == DomainExecutionStatus.PAUSED


# =============================================================================
# Test: EnhancedExecutionStateMachine - Creation
# =============================================================================

class TestEnhancedStateMachineCreation:
    """Tests for enhanced state machine creation."""

    def test_create_machine(self, execution_id):
        """Test creating an enhanced state machine."""
        machine = EnhancedExecutionStateMachine(execution_id=execution_id)

        assert machine.execution_id == execution_id
        assert machine.status == DomainExecutionStatus.PENDING

    def test_create_with_initial_status(self, execution_id):
        """Test creating with initial status."""
        machine = EnhancedExecutionStateMachine(
            execution_id=execution_id,
            initial_status=DomainExecutionStatus.RUNNING,
        )

        assert machine.status == DomainExecutionStatus.RUNNING

    def test_create_with_event_adapter(self, execution_id, event_adapter):
        """Test creating with event adapter."""
        machine = EnhancedExecutionStateMachine(
            execution_id=execution_id,
            event_adapter=event_adapter,
        )

        assert machine.event_adapter is event_adapter

    def test_default_event_adapter(self, execution_id):
        """Test default event adapter is created."""
        machine = EnhancedExecutionStateMachine(execution_id=execution_id)

        assert machine.event_adapter is not None
        assert isinstance(machine.event_adapter, WorkflowStatusEventAdapter)


# =============================================================================
# Test: EnhancedExecutionStateMachine - Properties
# =============================================================================

class TestEnhancedStateMachineProperties:
    """Tests for enhanced state machine properties."""

    def test_event_status(self, enhanced_machine):
        """Test event_status property."""
        assert enhanced_machine.event_status == ExecutionStatus.PENDING

    def test_current_node_id(self, enhanced_machine):
        """Test current_node_id property."""
        assert enhanced_machine.current_node_id is None

    def test_node_execution_count(self, enhanced_machine):
        """Test node_execution_count property."""
        assert enhanced_machine.node_execution_count == 0

    def test_last_event(self, enhanced_machine):
        """Test last_event property."""
        assert enhanced_machine.last_event is None


# =============================================================================
# Test: EnhancedExecutionStateMachine - Manual Transitions
# =============================================================================

class TestEnhancedStateMachineManualTransitions:
    """Tests for manual state transitions (backward compatibility)."""

    def test_start(self, enhanced_machine):
        """Test start transition."""
        enhanced_machine.start()

        assert enhanced_machine.status == DomainExecutionStatus.RUNNING
        assert enhanced_machine.started_at is not None

    def test_pause(self, running_machine):
        """Test pause transition."""
        running_machine.pause()

        assert running_machine.status == DomainExecutionStatus.PAUSED

    def test_resume(self, running_machine):
        """Test resume transition."""
        running_machine.pause()
        running_machine.resume()

        assert running_machine.status == DomainExecutionStatus.RUNNING

    def test_complete(self, running_machine):
        """Test complete transition."""
        running_machine.complete(llm_calls=10, llm_tokens=1000, llm_cost=0.05)

        assert running_machine.status == DomainExecutionStatus.COMPLETED
        assert running_machine.completed_at is not None
        assert running_machine.llm_calls == 10

    def test_fail(self, running_machine):
        """Test fail transition."""
        running_machine.fail()

        assert running_machine.status == DomainExecutionStatus.FAILED

    def test_cancel(self, enhanced_machine):
        """Test cancel transition."""
        enhanced_machine.cancel()

        assert enhanced_machine.status == DomainExecutionStatus.CANCELLED

    def test_invalid_transition_raises(self, enhanced_machine):
        """Test invalid transition raises error."""
        with pytest.raises(InvalidStateTransitionError):
            enhanced_machine.complete()  # Can't complete from PENDING


# =============================================================================
# Test: EnhancedExecutionStateMachine - Event Handling
# =============================================================================

class TestEnhancedStateMachineEventHandling:
    """Tests for event-driven state transitions."""

    @pytest.mark.asyncio
    async def test_handle_started_event(self, enhanced_machine, execution_id):
        """Test handling started event."""
        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="started",
            status=ExecutionStatus.RUNNING,
        )

        await enhanced_machine.handle_event(event)

        assert enhanced_machine.status == DomainExecutionStatus.RUNNING

    @pytest.mark.asyncio
    async def test_handle_completed_event(self, running_machine, execution_id):
        """Test handling completed event."""
        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="completed",
            status=ExecutionStatus.COMPLETED,
        )

        await running_machine.handle_event(event)

        assert running_machine.status == DomainExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_handle_failed_event(self, running_machine, execution_id):
        """Test handling failed event."""
        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="failed",
            status=ExecutionStatus.FAILED,
        )

        await running_machine.handle_event(event)

        assert running_machine.status == DomainExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_tracks_node_id(self, running_machine, execution_id):
        """Test that node_id is tracked."""
        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="executor_started",
            status=ExecutionStatus.RUNNING,
            node_id="test-node",
        )

        await running_machine.handle_event(event)

        assert running_machine.current_node_id == "test-node"

    @pytest.mark.asyncio
    async def test_tracks_node_count(self, running_machine, execution_id):
        """Test that node execution count is tracked."""
        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="executor_completed",
            status=ExecutionStatus.RUNNING,
            node_id="node-1",
        )

        await running_machine.handle_event(event)
        await running_machine.handle_event(event)

        assert running_machine.node_execution_count == 2

    @pytest.mark.asyncio
    async def test_last_event_updated(self, running_machine, execution_id):
        """Test that last_event is updated."""
        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="progress",
            status=ExecutionStatus.RUNNING,
        )

        await running_machine.handle_event(event)

        assert running_machine.last_event is event


# =============================================================================
# Test: EnhancedExecutionStateMachine - State Change Callbacks
# =============================================================================

class TestEnhancedStateMachineCallbacks:
    """Tests for state change callbacks."""

    def test_add_callback(self, enhanced_machine):
        """Test adding a callback."""
        callback = MagicMock()
        enhanced_machine.add_state_change_callback(callback)

        enhanced_machine.start()

        callback.assert_called_once()

    def test_remove_callback(self, enhanced_machine):
        """Test removing a callback."""
        callback = MagicMock()
        enhanced_machine.add_state_change_callback(callback)
        enhanced_machine.remove_state_change_callback(callback)

        enhanced_machine.start()

        callback.assert_not_called()

    def test_callback_receives_correct_args(self, enhanced_machine):
        """Test callback receives correct arguments."""
        received_args = []

        def callback(old_status, new_status, event):
            received_args.append((old_status, new_status, event))

        enhanced_machine.add_state_change_callback(callback)
        enhanced_machine.start()

        assert len(received_args) == 1
        assert received_args[0][0] == DomainExecutionStatus.PENDING
        assert received_args[0][1] == DomainExecutionStatus.RUNNING

    def test_callback_error_doesnt_stop_transition(self, enhanced_machine):
        """Test callback error doesn't prevent transition."""
        def bad_callback(old, new, event):
            raise Exception("Callback error")

        enhanced_machine.add_state_change_callback(bad_callback)
        enhanced_machine.start()

        assert enhanced_machine.status == DomainExecutionStatus.RUNNING


# =============================================================================
# Test: EnhancedExecutionStateMachine - Utility Methods
# =============================================================================

class TestEnhancedStateMachineUtilityMethods:
    """Tests for utility methods."""

    def test_update_stats(self, running_machine):
        """Test updating stats."""
        running_machine.update_stats(llm_calls=5, llm_tokens=500)

        assert running_machine.llm_calls == 5
        assert running_machine.llm_tokens == 500

    def test_get_duration_seconds(self, running_machine):
        """Test getting duration."""
        running_machine.complete()

        duration = running_machine.get_duration_seconds()
        assert duration is not None
        assert duration >= 0

    def test_get_history(self, enhanced_machine):
        """Test getting state history."""
        enhanced_machine.start()
        enhanced_machine.complete()

        history = enhanced_machine.get_history()
        assert len(history) >= 3  # Initial + start + complete

    def test_get_event_history(self, enhanced_machine, execution_id):
        """Test getting event history."""
        history = enhanced_machine.get_event_history()
        assert isinstance(history, list)

    def test_can_transition(self):
        """Test can_transition class method."""
        assert EnhancedExecutionStateMachine.can_transition(
            DomainExecutionStatus.PENDING,
            DomainExecutionStatus.RUNNING,
        ) is True

        assert EnhancedExecutionStateMachine.can_transition(
            DomainExecutionStatus.PENDING,
            DomainExecutionStatus.COMPLETED,
        ) is False

    def test_is_terminal(self):
        """Test is_terminal class method."""
        assert EnhancedExecutionStateMachine.is_terminal(
            DomainExecutionStatus.COMPLETED
        ) is True
        assert EnhancedExecutionStateMachine.is_terminal(
            DomainExecutionStatus.RUNNING
        ) is False

    def test_to_dict(self, enhanced_machine):
        """Test to_dict method."""
        data = enhanced_machine.to_dict()

        assert "execution_id" in data
        assert "status" in data
        assert "current_node_id" in data
        assert "node_execution_count" in data
        assert "event_status" in data

    def test_repr(self, enhanced_machine):
        """Test string representation."""
        repr_str = repr(enhanced_machine)

        assert "EnhancedExecutionStateMachine" in repr_str
        assert "pending" in repr_str


# =============================================================================
# Test: Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_enhanced_state_machine(self, execution_id):
        """Test create_enhanced_state_machine factory."""
        machine = create_enhanced_state_machine(
            execution_id=execution_id,
            status="running",
        )

        assert isinstance(machine, EnhancedExecutionStateMachine)
        assert machine.status == DomainExecutionStatus.RUNNING

    def test_create_with_invalid_status(self, execution_id):
        """Test create with invalid status defaults to PENDING."""
        machine = create_enhanced_state_machine(
            execution_id=execution_id,
            status="invalid_status",
        )

        assert machine.status == DomainExecutionStatus.PENDING

    def test_wrap_state_machine(self, execution_id):
        """Test wrap_state_machine factory."""
        domain_machine = DomainStateMachine(execution_id)
        domain_machine.start()

        enhanced = wrap_state_machine(domain_machine)

        assert isinstance(enhanced, EnhancedExecutionStateMachine)
        assert enhanced.execution_id == execution_id


# =============================================================================
# Test: StateMachineManager
# =============================================================================

class TestStateMachineManager:
    """Tests for StateMachineManager."""

    def test_create_manager(self):
        """Test creating a manager."""
        manager = StateMachineManager()

        assert manager.machine_count == 0

    def test_create_machine(self, execution_id):
        """Test creating a machine through manager."""
        manager = StateMachineManager()
        machine = manager.create(execution_id)

        assert isinstance(machine, EnhancedExecutionStateMachine)
        assert manager.machine_count == 1

    def test_get_machine(self, execution_id):
        """Test getting a machine."""
        manager = StateMachineManager()
        created = manager.create(execution_id)
        retrieved = manager.get(execution_id)

        assert retrieved is created

    def test_get_nonexistent(self, execution_id):
        """Test getting nonexistent machine."""
        manager = StateMachineManager()
        result = manager.get(execution_id)

        assert result is None

    def test_remove_machine(self, execution_id):
        """Test removing a machine."""
        manager = StateMachineManager()
        manager.create(execution_id)
        result = manager.remove(execution_id)

        assert result is True
        assert manager.machine_count == 0

    def test_remove_nonexistent(self, execution_id):
        """Test removing nonexistent machine."""
        manager = StateMachineManager()
        result = manager.remove(execution_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_event(self, execution_id):
        """Test processing an event."""
        manager = StateMachineManager()
        machine = manager.create(execution_id)
        machine.start()

        event = InternalExecutionEvent(
            execution_id=execution_id,
            event_type="completed",
            status=ExecutionStatus.COMPLETED,
        )

        result = await manager.process_event(event)

        assert result is True
        assert machine.status == DomainExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_event_unknown_execution(self):
        """Test processing event for unknown execution."""
        manager = StateMachineManager()

        event = InternalExecutionEvent(
            execution_id=uuid4(),
            event_type="completed",
            status=ExecutionStatus.COMPLETED,
        )

        result = await manager.process_event(event)

        assert result is False

    def test_get_all_statuses(self):
        """Test getting all statuses."""
        manager = StateMachineManager()
        exec_id_1 = uuid4()
        exec_id_2 = uuid4()

        machine1 = manager.create(exec_id_1)
        machine2 = manager.create(exec_id_2)
        machine1.start()

        statuses = manager.get_all_statuses()

        assert statuses[exec_id_1] == DomainExecutionStatus.RUNNING
        assert statuses[exec_id_2] == DomainExecutionStatus.PENDING

    def test_repr(self):
        """Test string representation."""
        manager = StateMachineManager()
        repr_str = repr(manager)

        assert "StateMachineManager" in repr_str
