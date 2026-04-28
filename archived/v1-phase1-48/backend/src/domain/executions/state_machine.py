# =============================================================================
# IPA Platform - Execution State Machine
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# State machine for managing execution lifecycle.
# Provides:
#   - ExecutionStatus: Status enumeration
#   - ExecutionStateMachine: State transition management
#   - Transition validation and enforcement
#
# Status Flow:
#   PENDING -> RUNNING -> COMPLETED
#                     -> FAILED
#                     -> CANCELLED
#   RUNNING -> PAUSED -> RUNNING
#                     -> CANCELLED
# =============================================================================

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """
    Execution status enumeration.

    Represents all possible states of a workflow execution.

    States:
        PENDING: Execution is queued but not yet started
        RUNNING: Execution is currently in progress
        PAUSED: Execution is waiting for human input or external event
        COMPLETED: Execution finished successfully
        FAILED: Execution encountered an error
        CANCELLED: Execution was cancelled by user

    Terminal States: COMPLETED, FAILED, CANCELLED (no transitions out)
    """

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Define valid state transitions
TRANSITIONS: Dict[ExecutionStatus, Set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.RUNNING: {
        ExecutionStatus.PAUSED,
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.PAUSED: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
    },
    # Terminal states - no transitions allowed
    ExecutionStatus.COMPLETED: set(),
    ExecutionStatus.FAILED: set(),
    ExecutionStatus.CANCELLED: set(),
}

# Terminal states (execution finished, no further transitions)
TERMINAL_STATES: Set[ExecutionStatus] = {
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
}


class InvalidStateTransitionError(Exception):
    """
    Exception raised for invalid state transitions.

    Attributes:
        from_status: Current state
        to_status: Attempted target state
        message: Human-readable error message
    """

    def __init__(
        self,
        from_status: ExecutionStatus,
        to_status: ExecutionStatus,
        message: Optional[str] = None,
    ):
        self.from_status = from_status
        self.to_status = to_status
        self.message = message or f"Cannot transition from {from_status.value} to {to_status.value}"
        super().__init__(self.message)


class ExecutionStateMachine:
    """
    State machine for managing execution lifecycle.

    Provides controlled state transitions with validation,
    ensuring execution states follow the defined flow.

    Attributes:
        execution_id: UUID of the execution being managed
        status: Current execution status
        started_at: When execution started running
        completed_at: When execution reached terminal state
        llm_calls: Total LLM API calls
        llm_tokens: Total tokens used (input + output)
        llm_cost: Estimated cost in USD

    Example:
        machine = ExecutionStateMachine(execution_id)
        machine.start()  # PENDING -> RUNNING
        machine.pause()  # RUNNING -> PAUSED
        machine.resume()  # PAUSED -> RUNNING
        machine.complete(result)  # RUNNING -> COMPLETED
    """

    def __init__(
        self,
        execution_id: UUID,
        initial_status: ExecutionStatus = ExecutionStatus.PENDING,
    ):
        """
        Initialize state machine.

        Args:
            execution_id: UUID of the execution
            initial_status: Initial status (default: PENDING)
        """
        self.execution_id = execution_id
        self._status = initial_status
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.llm_calls: int = 0
        self.llm_tokens: int = 0
        self.llm_cost: Decimal = Decimal("0.000000")
        self._history: List[Dict[str, Any]] = []

        # Record initial state
        self._record_transition(None, initial_status)
        logger.debug(f"Execution {execution_id} initialized with status {initial_status.value}")

    @property
    def status(self) -> ExecutionStatus:
        """Get current execution status."""
        return self._status

    @classmethod
    def can_transition(cls, from_status: ExecutionStatus, to_status: ExecutionStatus) -> bool:
        """
        Check if a transition is valid.

        Args:
            from_status: Current status
            to_status: Target status

        Returns:
            True if transition is allowed, False otherwise
        """
        if from_status not in TRANSITIONS:
            return False
        return to_status in TRANSITIONS[from_status]

    @classmethod
    def is_terminal(cls, status: ExecutionStatus) -> bool:
        """
        Check if a status is terminal (execution finished).

        Args:
            status: Status to check

        Returns:
            True if status is terminal, False otherwise
        """
        return status in TERMINAL_STATES

    @classmethod
    def get_valid_transitions(cls, status: ExecutionStatus) -> Set[ExecutionStatus]:
        """
        Get valid transitions from a status.

        Args:
            status: Current status

        Returns:
            Set of valid target statuses
        """
        return TRANSITIONS.get(status, set())

    def transition(self, to_status: ExecutionStatus) -> None:
        """
        Transition to a new status.

        Args:
            to_status: Target status

        Raises:
            InvalidStateTransitionError: If transition is invalid
        """
        if not self.can_transition(self._status, to_status):
            raise InvalidStateTransitionError(self._status, to_status)

        old_status = self._status
        self._status = to_status
        self._record_transition(old_status, to_status)

        logger.info(
            f"Execution {self.execution_id} transitioned: {old_status.value} -> {to_status.value}"
        )

    def _record_transition(
        self,
        from_status: Optional[ExecutionStatus],
        to_status: ExecutionStatus,
    ) -> None:
        """Record a state transition in history."""
        self._history.append(
            {
                "from": from_status.value if from_status else None,
                "to": to_status.value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    # Convenience methods for common transitions

    def start(self) -> None:
        """
        Start the execution (PENDING -> RUNNING).

        Raises:
            InvalidStateTransitionError: If not in PENDING state
        """
        self.transition(ExecutionStatus.RUNNING)
        self.started_at = datetime.utcnow()

    def pause(self) -> None:
        """
        Pause the execution (RUNNING -> PAUSED).

        Raises:
            InvalidStateTransitionError: If not in RUNNING state
        """
        self.transition(ExecutionStatus.PAUSED)

    def resume(self) -> None:
        """
        Resume the execution (PAUSED -> RUNNING).

        Raises:
            InvalidStateTransitionError: If not in PAUSED state
        """
        self.transition(ExecutionStatus.RUNNING)

    def complete(
        self,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ) -> None:
        """
        Complete the execution (RUNNING -> COMPLETED).

        Args:
            llm_calls: Total LLM API calls
            llm_tokens: Total tokens used
            llm_cost: Estimated cost in USD

        Raises:
            InvalidStateTransitionError: If not in RUNNING state
        """
        self.transition(ExecutionStatus.COMPLETED)
        self.completed_at = datetime.utcnow()
        self.llm_calls = llm_calls
        self.llm_tokens = llm_tokens
        self.llm_cost = Decimal(str(llm_cost))

    def fail(
        self,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ) -> None:
        """
        Fail the execution (RUNNING -> FAILED).

        Args:
            llm_calls: Total LLM API calls
            llm_tokens: Total tokens used
            llm_cost: Estimated cost in USD

        Raises:
            InvalidStateTransitionError: If not in RUNNING state
        """
        self.transition(ExecutionStatus.FAILED)
        self.completed_at = datetime.utcnow()
        self.llm_calls = llm_calls
        self.llm_tokens = llm_tokens
        self.llm_cost = Decimal(str(llm_cost))

    def cancel(self) -> None:
        """
        Cancel the execution (PENDING/RUNNING/PAUSED -> CANCELLED).

        Raises:
            InvalidStateTransitionError: If in terminal state
        """
        self.transition(ExecutionStatus.CANCELLED)
        self.completed_at = datetime.utcnow()

    def update_stats(
        self,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ) -> None:
        """
        Update LLM usage statistics (incremental).

        Args:
            llm_calls: Additional LLM calls
            llm_tokens: Additional tokens
            llm_cost: Additional cost in USD
        """
        self.llm_calls += llm_calls
        self.llm_tokens += llm_tokens
        self.llm_cost += Decimal(str(llm_cost))

    def get_duration_seconds(self) -> Optional[float]:
        """
        Get execution duration in seconds.

        Returns:
            Duration in seconds, or None if not started/completed
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get state transition history.

        Returns:
            List of transition records
        """
        return list(self._history)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state machine to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "execution_id": str(self.execution_id),
            "status": self._status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "llm_calls": self.llm_calls,
            "llm_tokens": self.llm_tokens,
            "llm_cost": float(self.llm_cost),
            "duration_seconds": self.get_duration_seconds(),
            "is_terminal": self.is_terminal(self._status),
            "valid_transitions": [s.value for s in self.get_valid_transitions(self._status)],
            "history": self._history,
        }

    def __repr__(self) -> str:
        return f"<ExecutionStateMachine(id={self.execution_id}, status={self._status.value})>"


# Utility functions


def create_execution_state_machine(
    execution_id: UUID,
    status: str = "pending",
) -> ExecutionStateMachine:
    """
    Factory function to create ExecutionStateMachine from string status.

    Args:
        execution_id: Execution UUID
        status: Status string

    Returns:
        ExecutionStateMachine instance
    """
    try:
        initial_status = ExecutionStatus(status)
    except ValueError:
        initial_status = ExecutionStatus.PENDING

    return ExecutionStateMachine(execution_id, initial_status)


def validate_transition(from_status: str, to_status: str) -> bool:
    """
    Validate a state transition using string statuses.

    Args:
        from_status: Current status string
        to_status: Target status string

    Returns:
        True if transition is valid, False otherwise
    """
    try:
        from_enum = ExecutionStatus(from_status)
        to_enum = ExecutionStatus(to_status)
        return ExecutionStateMachine.can_transition(from_enum, to_enum)
    except ValueError:
        return False
