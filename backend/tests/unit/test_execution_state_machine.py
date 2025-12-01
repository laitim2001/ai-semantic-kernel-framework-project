# =============================================================================
# IPA Platform - Execution State Machine Unit Tests
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Tests for the ExecutionStateMachine including:
#   - ExecutionStatus enum
#   - State transitions (valid and invalid)
#   - Terminal state detection
#   - LLM statistics tracking
#   - History recording
# =============================================================================

import pytest
from decimal import Decimal
from uuid import uuid4

from src.domain.executions import (
    ExecutionStateMachine,
    ExecutionStatus,
    InvalidStateTransitionError,
    TERMINAL_STATES,
    TRANSITIONS,
    create_execution_state_machine,
    validate_transition,
)


# =============================================================================
# ExecutionStatus Tests
# =============================================================================


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_status_values(self):
        """Test all status enum values."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.PAUSED.value == "paused"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert ExecutionStatus("pending") == ExecutionStatus.PENDING
        assert ExecutionStatus("running") == ExecutionStatus.RUNNING
        assert ExecutionStatus("completed") == ExecutionStatus.COMPLETED

    def test_invalid_status_raises(self):
        """Test that invalid status string raises ValueError."""
        with pytest.raises(ValueError):
            ExecutionStatus("invalid")


# =============================================================================
# TRANSITIONS Tests
# =============================================================================


class TestTransitions:
    """Tests for state transition definitions."""

    def test_pending_transitions(self):
        """Test valid transitions from PENDING."""
        valid = TRANSITIONS[ExecutionStatus.PENDING]
        assert ExecutionStatus.RUNNING in valid
        assert ExecutionStatus.CANCELLED in valid
        assert ExecutionStatus.COMPLETED not in valid

    def test_running_transitions(self):
        """Test valid transitions from RUNNING."""
        valid = TRANSITIONS[ExecutionStatus.RUNNING]
        assert ExecutionStatus.PAUSED in valid
        assert ExecutionStatus.COMPLETED in valid
        assert ExecutionStatus.FAILED in valid
        assert ExecutionStatus.CANCELLED in valid
        assert ExecutionStatus.PENDING not in valid

    def test_paused_transitions(self):
        """Test valid transitions from PAUSED."""
        valid = TRANSITIONS[ExecutionStatus.PAUSED]
        assert ExecutionStatus.RUNNING in valid
        assert ExecutionStatus.CANCELLED in valid
        assert ExecutionStatus.COMPLETED not in valid

    def test_terminal_states_have_no_transitions(self):
        """Test that terminal states have no valid transitions."""
        assert len(TRANSITIONS[ExecutionStatus.COMPLETED]) == 0
        assert len(TRANSITIONS[ExecutionStatus.FAILED]) == 0
        assert len(TRANSITIONS[ExecutionStatus.CANCELLED]) == 0


# =============================================================================
# TERMINAL_STATES Tests
# =============================================================================


class TestTerminalStates:
    """Tests for terminal state definitions."""

    def test_terminal_states_content(self):
        """Test terminal states set contains correct statuses."""
        assert ExecutionStatus.COMPLETED in TERMINAL_STATES
        assert ExecutionStatus.FAILED in TERMINAL_STATES
        assert ExecutionStatus.CANCELLED in TERMINAL_STATES

    def test_non_terminal_states(self):
        """Test non-terminal states are not in set."""
        assert ExecutionStatus.PENDING not in TERMINAL_STATES
        assert ExecutionStatus.RUNNING not in TERMINAL_STATES
        assert ExecutionStatus.PAUSED not in TERMINAL_STATES


# =============================================================================
# ExecutionStateMachine Tests
# =============================================================================


class TestExecutionStateMachine:
    """Tests for ExecutionStateMachine class."""

    def test_initialization(self):
        """Test state machine initialization."""
        exec_id = uuid4()
        machine = ExecutionStateMachine(exec_id)

        assert machine.execution_id == exec_id
        assert machine.status == ExecutionStatus.PENDING
        assert machine.started_at is None
        assert machine.completed_at is None
        assert machine.llm_calls == 0
        assert machine.llm_tokens == 0
        assert machine.llm_cost == Decimal("0.000000")

    def test_initialization_with_status(self):
        """Test initialization with specific status."""
        machine = ExecutionStateMachine(
            uuid4(), initial_status=ExecutionStatus.RUNNING
        )
        assert machine.status == ExecutionStatus.RUNNING

    def test_can_transition_valid(self):
        """Test can_transition for valid transitions."""
        assert ExecutionStateMachine.can_transition(
            ExecutionStatus.PENDING, ExecutionStatus.RUNNING
        )
        assert ExecutionStateMachine.can_transition(
            ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED
        )
        assert ExecutionStateMachine.can_transition(
            ExecutionStatus.RUNNING, ExecutionStatus.FAILED
        )

    def test_can_transition_invalid(self):
        """Test can_transition for invalid transitions."""
        assert not ExecutionStateMachine.can_transition(
            ExecutionStatus.PENDING, ExecutionStatus.COMPLETED
        )
        assert not ExecutionStateMachine.can_transition(
            ExecutionStatus.COMPLETED, ExecutionStatus.RUNNING
        )
        assert not ExecutionStateMachine.can_transition(
            ExecutionStatus.FAILED, ExecutionStatus.RUNNING
        )

    def test_is_terminal(self):
        """Test is_terminal method."""
        assert ExecutionStateMachine.is_terminal(ExecutionStatus.COMPLETED)
        assert ExecutionStateMachine.is_terminal(ExecutionStatus.FAILED)
        assert ExecutionStateMachine.is_terminal(ExecutionStatus.CANCELLED)
        assert not ExecutionStateMachine.is_terminal(ExecutionStatus.PENDING)
        assert not ExecutionStateMachine.is_terminal(ExecutionStatus.RUNNING)

    def test_get_valid_transitions(self):
        """Test get_valid_transitions method."""
        valid = ExecutionStateMachine.get_valid_transitions(ExecutionStatus.RUNNING)
        assert ExecutionStatus.COMPLETED in valid
        assert ExecutionStatus.FAILED in valid
        assert ExecutionStatus.PAUSED in valid
        assert ExecutionStatus.CANCELLED in valid

    def test_transition_success(self):
        """Test successful state transition."""
        machine = ExecutionStateMachine(uuid4())

        machine.transition(ExecutionStatus.RUNNING)

        assert machine.status == ExecutionStatus.RUNNING

    def test_transition_invalid_raises(self):
        """Test that invalid transition raises error."""
        machine = ExecutionStateMachine(uuid4())

        with pytest.raises(InvalidStateTransitionError) as exc:
            machine.transition(ExecutionStatus.COMPLETED)

        assert exc.value.from_status == ExecutionStatus.PENDING
        assert exc.value.to_status == ExecutionStatus.COMPLETED

    def test_start(self):
        """Test start() convenience method."""
        machine = ExecutionStateMachine(uuid4())

        machine.start()

        assert machine.status == ExecutionStatus.RUNNING
        assert machine.started_at is not None

    def test_pause(self):
        """Test pause() convenience method."""
        machine = ExecutionStateMachine(uuid4())
        machine.start()

        machine.pause()

        assert machine.status == ExecutionStatus.PAUSED

    def test_resume(self):
        """Test resume() convenience method."""
        machine = ExecutionStateMachine(uuid4())
        machine.start()
        machine.pause()

        machine.resume()

        assert machine.status == ExecutionStatus.RUNNING

    def test_complete(self):
        """Test complete() convenience method."""
        machine = ExecutionStateMachine(uuid4())
        machine.start()

        machine.complete(llm_calls=5, llm_tokens=1000, llm_cost=0.015)

        assert machine.status == ExecutionStatus.COMPLETED
        assert machine.completed_at is not None
        assert machine.llm_calls == 5
        assert machine.llm_tokens == 1000
        assert machine.llm_cost == Decimal("0.015")

    def test_fail(self):
        """Test fail() convenience method."""
        machine = ExecutionStateMachine(uuid4())
        machine.start()

        machine.fail(llm_calls=2, llm_tokens=500, llm_cost=0.0075)

        assert machine.status == ExecutionStatus.FAILED
        assert machine.completed_at is not None
        assert machine.llm_calls == 2

    def test_cancel_from_pending(self):
        """Test cancel() from PENDING state."""
        machine = ExecutionStateMachine(uuid4())

        machine.cancel()

        assert machine.status == ExecutionStatus.CANCELLED
        assert machine.completed_at is not None

    def test_cancel_from_running(self):
        """Test cancel() from RUNNING state."""
        machine = ExecutionStateMachine(uuid4())
        machine.start()

        machine.cancel()

        assert machine.status == ExecutionStatus.CANCELLED

    def test_cancel_from_paused(self):
        """Test cancel() from PAUSED state."""
        machine = ExecutionStateMachine(uuid4())
        machine.start()
        machine.pause()

        machine.cancel()

        assert machine.status == ExecutionStatus.CANCELLED

    def test_cancel_from_terminal_raises(self):
        """Test cancel() from terminal state raises error."""
        machine = ExecutionStateMachine(uuid4())
        machine.start()
        machine.complete()

        with pytest.raises(InvalidStateTransitionError):
            machine.cancel()

    def test_update_stats(self):
        """Test update_stats() incremental statistics."""
        machine = ExecutionStateMachine(uuid4())

        machine.update_stats(llm_calls=3, llm_tokens=500, llm_cost=0.0075)
        assert machine.llm_calls == 3
        assert machine.llm_tokens == 500

        machine.update_stats(llm_calls=2, llm_tokens=300, llm_cost=0.0045)
        assert machine.llm_calls == 5
        assert machine.llm_tokens == 800
        assert machine.llm_cost == Decimal("0.012")

    def test_get_duration_seconds(self):
        """Test get_duration_seconds calculation."""
        machine = ExecutionStateMachine(uuid4())

        # Before start, should be None
        assert machine.get_duration_seconds() is None

        machine.start()
        # After start but before complete, should be None
        assert machine.get_duration_seconds() is None

        machine.complete()
        # After complete, should have duration
        duration = machine.get_duration_seconds()
        assert duration is not None
        assert duration >= 0

    def test_get_history(self):
        """Test get_history records transitions."""
        machine = ExecutionStateMachine(uuid4())
        machine.start()
        machine.pause()
        machine.resume()
        machine.complete()

        history = machine.get_history()

        assert len(history) == 5  # Initial + 4 transitions
        assert history[0]["to"] == "pending"  # Initial state
        assert history[1]["from"] == "pending"
        assert history[1]["to"] == "running"
        assert history[-1]["to"] == "completed"

    def test_to_dict(self):
        """Test to_dict serialization."""
        exec_id = uuid4()
        machine = ExecutionStateMachine(exec_id)
        machine.start()

        result = machine.to_dict()

        assert result["execution_id"] == str(exec_id)
        assert result["status"] == "running"
        assert result["started_at"] is not None
        assert result["llm_calls"] == 0
        assert result["is_terminal"] is False
        assert "completed" in result["valid_transitions"]

    def test_repr(self):
        """Test string representation."""
        exec_id = uuid4()
        machine = ExecutionStateMachine(exec_id)

        r = repr(machine)

        assert "ExecutionStateMachine" in r
        assert str(exec_id) in r
        assert "pending" in r


# =============================================================================
# InvalidStateTransitionError Tests
# =============================================================================


class TestInvalidStateTransitionError:
    """Tests for InvalidStateTransitionError exception."""

    def test_error_attributes(self):
        """Test error has correct attributes."""
        error = InvalidStateTransitionError(
            ExecutionStatus.COMPLETED,
            ExecutionStatus.RUNNING,
        )

        assert error.from_status == ExecutionStatus.COMPLETED
        assert error.to_status == ExecutionStatus.RUNNING
        assert "completed" in error.message.lower()
        assert "running" in error.message.lower()

    def test_error_with_custom_message(self):
        """Test error with custom message."""
        error = InvalidStateTransitionError(
            ExecutionStatus.FAILED,
            ExecutionStatus.PENDING,
            message="Custom error message",
        )

        assert str(error) == "Custom error message"

    def test_error_is_exception(self):
        """Test that error is catchable as Exception."""
        with pytest.raises(Exception):
            raise InvalidStateTransitionError(
                ExecutionStatus.COMPLETED,
                ExecutionStatus.RUNNING,
            )


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_create_execution_state_machine(self):
        """Test factory function."""
        exec_id = uuid4()
        machine = create_execution_state_machine(exec_id, "running")

        assert machine.execution_id == exec_id
        assert machine.status == ExecutionStatus.RUNNING

    def test_create_execution_state_machine_invalid_status(self):
        """Test factory with invalid status defaults to PENDING."""
        exec_id = uuid4()
        machine = create_execution_state_machine(exec_id, "invalid")

        assert machine.status == ExecutionStatus.PENDING

    def test_validate_transition_valid(self):
        """Test validate_transition with valid transition."""
        assert validate_transition("pending", "running") is True
        assert validate_transition("running", "completed") is True

    def test_validate_transition_invalid(self):
        """Test validate_transition with invalid transition."""
        assert validate_transition("pending", "completed") is False
        assert validate_transition("completed", "running") is False

    def test_validate_transition_invalid_status(self):
        """Test validate_transition with invalid status strings."""
        assert validate_transition("invalid", "running") is False
        assert validate_transition("pending", "invalid") is False


# =============================================================================
# Full Workflow Tests
# =============================================================================


class TestFullWorkflow:
    """Tests for complete execution workflows."""

    def test_successful_workflow(self):
        """Test successful execution from start to completion."""
        machine = ExecutionStateMachine(uuid4())

        # Initial state
        assert machine.status == ExecutionStatus.PENDING

        # Start execution
        machine.start()
        assert machine.status == ExecutionStatus.RUNNING
        assert machine.started_at is not None

        # Add some LLM usage
        machine.update_stats(llm_calls=3, llm_tokens=500, llm_cost=0.0075)

        # Complete execution
        machine.complete(llm_calls=2, llm_tokens=300, llm_cost=0.0045)
        assert machine.status == ExecutionStatus.COMPLETED
        assert machine.completed_at is not None
        assert machine.get_duration_seconds() is not None

        # Verify terminal state
        assert ExecutionStateMachine.is_terminal(machine.status)

    def test_failed_workflow(self):
        """Test execution that fails."""
        machine = ExecutionStateMachine(uuid4())

        machine.start()
        machine.fail(llm_calls=1, llm_tokens=100, llm_cost=0.0015)

        assert machine.status == ExecutionStatus.FAILED
        assert machine.completed_at is not None

    def test_paused_and_resumed_workflow(self):
        """Test execution with pause for human input."""
        machine = ExecutionStateMachine(uuid4())

        machine.start()
        machine.pause()  # Wait for human input
        assert machine.status == ExecutionStatus.PAUSED

        machine.resume()  # Human approved
        assert machine.status == ExecutionStatus.RUNNING

        machine.complete()
        assert machine.status == ExecutionStatus.COMPLETED

    def test_cancelled_workflow(self):
        """Test execution that gets cancelled."""
        machine = ExecutionStateMachine(uuid4())

        machine.start()
        machine.cancel()

        assert machine.status == ExecutionStatus.CANCELLED
        assert machine.completed_at is not None

    def test_cannot_restart_completed(self):
        """Test that completed execution cannot restart."""
        machine = ExecutionStateMachine(uuid4())

        machine.start()
        machine.complete()

        with pytest.raises(InvalidStateTransitionError):
            machine.start()

    def test_cannot_complete_pending(self):
        """Test that pending execution cannot complete directly."""
        machine = ExecutionStateMachine(uuid4())

        with pytest.raises(InvalidStateTransitionError):
            machine.complete()
