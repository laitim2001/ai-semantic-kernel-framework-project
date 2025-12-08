# =============================================================================
# IPA Platform - Enhanced Execution State Machine
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 27, Story S27-3: ExecutionStateMachine Refactoring (8 pts)
#
# This module provides an enhanced ExecutionStateMachine that integrates
# with the official Microsoft Agent Framework event system.
#
# Key Features:
#   - Integrates with WorkflowStatusEventAdapter
#   - Handles InternalExecutionEvent automatically
#   - Maintains backward compatibility with existing API
#   - Supports event-driven state transitions
#
# IMPORTANT: Integrates with official Agent Framework events
# =============================================================================

from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import logging

# Import existing state machine components
from src.domain.executions.state_machine import (
    ExecutionStatus as DomainExecutionStatus,
    ExecutionStateMachine as DomainStateMachine,
    InvalidStateTransitionError,
    TRANSITIONS,
    TERMINAL_STATES,
)

# Import Sprint 27 event adapters
from .events import (
    WorkflowStatusEventAdapter,
    ExecutionStatus,
    EventType,
    InternalExecutionEvent,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Status Mapping between Domain and Events
# =============================================================================

# Map from events.ExecutionStatus to domain ExecutionStatus
EVENT_TO_DOMAIN_STATUS: Dict[ExecutionStatus, DomainExecutionStatus] = {
    ExecutionStatus.PENDING: DomainExecutionStatus.PENDING,
    ExecutionStatus.RUNNING: DomainExecutionStatus.RUNNING,
    ExecutionStatus.WAITING_APPROVAL: DomainExecutionStatus.PAUSED,
    ExecutionStatus.COMPLETED: DomainExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED: DomainExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED: DomainExecutionStatus.CANCELLED,
    ExecutionStatus.PAUSED: DomainExecutionStatus.PAUSED,
    ExecutionStatus.TIMEOUT: DomainExecutionStatus.FAILED,
}

# Map from domain ExecutionStatus to events.ExecutionStatus
DOMAIN_TO_EVENT_STATUS: Dict[DomainExecutionStatus, ExecutionStatus] = {
    DomainExecutionStatus.PENDING: ExecutionStatus.PENDING,
    DomainExecutionStatus.RUNNING: ExecutionStatus.RUNNING,
    DomainExecutionStatus.PAUSED: ExecutionStatus.WAITING_APPROVAL,
    DomainExecutionStatus.COMPLETED: ExecutionStatus.COMPLETED,
    DomainExecutionStatus.FAILED: ExecutionStatus.FAILED,
    DomainExecutionStatus.CANCELLED: ExecutionStatus.CANCELLED,
}


# =============================================================================
# EnhancedExecutionStateMachine
# =============================================================================

class EnhancedExecutionStateMachine:
    """
    Enhanced execution state machine with event system integration.

    Extends the functionality of the domain ExecutionStateMachine by:
    - Integrating with WorkflowStatusEventAdapter
    - Handling InternalExecutionEvent for automatic state transitions
    - Supporting event-driven state management
    - Providing backward compatibility with existing API

    Example:
        >>> machine = EnhancedExecutionStateMachine(execution_id)
        >>> machine.start()  # Manual transition
        >>> await machine.handle_event(event)  # Event-driven transition
        >>> print(machine.status)  # Current status

    IMPORTANT: Integrates with official Agent Framework event system
    """

    def __init__(
        self,
        execution_id: UUID,
        initial_status: DomainExecutionStatus = DomainExecutionStatus.PENDING,
        event_adapter: Optional[WorkflowStatusEventAdapter] = None,
    ):
        """
        Initialize the enhanced state machine.

        Args:
            execution_id: UUID of the execution
            initial_status: Initial status (default: PENDING)
            event_adapter: Optional event adapter for event handling
        """
        # Create the underlying domain state machine
        self._machine = DomainStateMachine(execution_id, initial_status)

        # Event system integration
        self._event_adapter = event_adapter or WorkflowStatusEventAdapter()
        self._event_adapter.add_handler(self._on_event)

        # Additional tracking
        self._current_node_id: Optional[str] = None
        self._node_execution_count: int = 0
        self._last_event: Optional[InternalExecutionEvent] = None
        self._state_change_callbacks: List[Callable] = []

    @property
    def execution_id(self) -> UUID:
        """Get execution ID."""
        return self._machine.execution_id

    @property
    def status(self) -> DomainExecutionStatus:
        """Get current execution status."""
        return self._machine.status

    @property
    def event_status(self) -> ExecutionStatus:
        """Get current status as events.ExecutionStatus."""
        return DOMAIN_TO_EVENT_STATUS.get(
            self._machine.status,
            ExecutionStatus.RUNNING
        )

    @property
    def started_at(self) -> Optional[datetime]:
        """Get execution start time."""
        return self._machine.started_at

    @property
    def completed_at(self) -> Optional[datetime]:
        """Get execution completion time."""
        return self._machine.completed_at

    @property
    def llm_calls(self) -> int:
        """Get total LLM calls."""
        return self._machine.llm_calls

    @property
    def llm_tokens(self) -> int:
        """Get total LLM tokens."""
        return self._machine.llm_tokens

    @property
    def llm_cost(self) -> Decimal:
        """Get total LLM cost."""
        return self._machine.llm_cost

    @property
    def current_node_id(self) -> Optional[str]:
        """Get current executing node ID."""
        return self._current_node_id

    @property
    def node_execution_count(self) -> int:
        """Get count of executed nodes."""
        return self._node_execution_count

    @property
    def last_event(self) -> Optional[InternalExecutionEvent]:
        """Get last processed event."""
        return self._last_event

    @property
    def event_adapter(self) -> WorkflowStatusEventAdapter:
        """Get the event adapter."""
        return self._event_adapter

    # =========================================================================
    # Event Handling
    # =========================================================================

    async def handle_event(self, event: InternalExecutionEvent) -> None:
        """
        Handle an internal execution event.

        Automatically transitions state based on event status.

        Args:
            event: The event to handle
        """
        self._last_event = event

        # Update node tracking
        if event.node_id:
            self._current_node_id = event.node_id
            if event.event_type == "executor_completed":
                self._node_execution_count += 1

        # Map event status to domain status
        target_status = EVENT_TO_DOMAIN_STATUS.get(event.status)
        if target_status and target_status != self._machine.status:
            # Attempt transition if valid
            if self._machine.can_transition(self._machine.status, target_status):
                self._transition_from_event(target_status, event)

        logger.debug(
            f"Handled event: type={event.event_type}, "
            f"status={event.status.value}, node={event.node_id}"
        )

    def _transition_from_event(
        self,
        target_status: DomainExecutionStatus,
        event: InternalExecutionEvent,
    ) -> None:
        """
        Transition state based on event.

        Args:
            target_status: Target domain status
            event: The triggering event
        """
        old_status = self._machine.status

        try:
            # Use appropriate transition method
            if target_status == DomainExecutionStatus.RUNNING:
                if old_status == DomainExecutionStatus.PENDING:
                    self._machine.start()
                elif old_status == DomainExecutionStatus.PAUSED:
                    self._machine.resume()
            elif target_status == DomainExecutionStatus.PAUSED:
                self._machine.pause()
            elif target_status == DomainExecutionStatus.COMPLETED:
                self._machine.complete()
            elif target_status == DomainExecutionStatus.FAILED:
                self._machine.fail()
            elif target_status == DomainExecutionStatus.CANCELLED:
                self._machine.cancel()
            else:
                self._machine.transition(target_status)

            # Notify callbacks
            self._notify_state_change(old_status, target_status, event)

        except InvalidStateTransitionError as e:
            logger.warning(
                f"Event-driven transition failed: {e.message}",
                extra={"event": event.to_dict()},
            )

    async def _on_event(self, event: InternalExecutionEvent) -> None:
        """
        Internal event handler callback.

        Called by the event adapter when events are processed.

        Args:
            event: The internal event
        """
        # Only handle events for this execution
        if event.execution_id == self.execution_id:
            await self.handle_event(event)

    # =========================================================================
    # State Change Callbacks
    # =========================================================================

    def add_state_change_callback(self, callback: Callable) -> None:
        """
        Add a callback for state changes.

        Callbacks receive (old_status, new_status, event).

        Args:
            callback: Callable to invoke on state changes
        """
        self._state_change_callbacks.append(callback)

    def remove_state_change_callback(self, callback: Callable) -> None:
        """
        Remove a state change callback.

        Args:
            callback: The callback to remove
        """
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)

    def _notify_state_change(
        self,
        old_status: DomainExecutionStatus,
        new_status: DomainExecutionStatus,
        event: Optional[InternalExecutionEvent] = None,
    ) -> None:
        """
        Notify callbacks of state change.

        Args:
            old_status: Previous status
            new_status: New status
            event: Triggering event (optional)
        """
        for callback in self._state_change_callbacks:
            try:
                callback(old_status, new_status, event)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

    # =========================================================================
    # Manual State Transitions (Backward Compatibility)
    # =========================================================================

    def start(self) -> None:
        """Start the execution (PENDING -> RUNNING)."""
        old_status = self._machine.status
        self._machine.start()
        self._notify_state_change(old_status, self._machine.status)

    def pause(self) -> None:
        """Pause the execution (RUNNING -> PAUSED)."""
        old_status = self._machine.status
        self._machine.pause()
        self._notify_state_change(old_status, self._machine.status)

    def resume(self) -> None:
        """Resume the execution (PAUSED -> RUNNING)."""
        old_status = self._machine.status
        self._machine.resume()
        self._notify_state_change(old_status, self._machine.status)

    def complete(
        self,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ) -> None:
        """Complete the execution (RUNNING -> COMPLETED)."""
        old_status = self._machine.status
        self._machine.complete(llm_calls, llm_tokens, llm_cost)
        self._notify_state_change(old_status, self._machine.status)

    def fail(
        self,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ) -> None:
        """Fail the execution (RUNNING -> FAILED)."""
        old_status = self._machine.status
        self._machine.fail(llm_calls, llm_tokens, llm_cost)
        self._notify_state_change(old_status, self._machine.status)

    def cancel(self) -> None:
        """Cancel the execution."""
        old_status = self._machine.status
        self._machine.cancel()
        self._notify_state_change(old_status, self._machine.status)

    def transition(self, to_status: DomainExecutionStatus) -> None:
        """
        Manual state transition.

        Args:
            to_status: Target status
        """
        old_status = self._machine.status
        self._machine.transition(to_status)
        self._notify_state_change(old_status, self._machine.status)

    # =========================================================================
    # Statistics and State
    # =========================================================================

    def update_stats(
        self,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ) -> None:
        """Update LLM usage statistics."""
        self._machine.update_stats(llm_calls, llm_tokens, llm_cost)

    def get_duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        return self._machine.get_duration_seconds()

    def get_history(self) -> List[Dict[str, Any]]:
        """Get state transition history."""
        return self._machine.get_history()

    def get_event_history(self) -> List[InternalExecutionEvent]:
        """Get event history from adapter."""
        return self._event_adapter.get_history(self.execution_id)

    @classmethod
    def can_transition(
        cls,
        from_status: DomainExecutionStatus,
        to_status: DomainExecutionStatus,
    ) -> bool:
        """Check if a transition is valid."""
        return DomainStateMachine.can_transition(from_status, to_status)

    @classmethod
    def is_terminal(cls, status: DomainExecutionStatus) -> bool:
        """Check if a status is terminal."""
        return DomainStateMachine.is_terminal(status)

    @classmethod
    def get_valid_transitions(
        cls,
        status: DomainExecutionStatus,
    ) -> Set[DomainExecutionStatus]:
        """Get valid transitions from a status."""
        return DomainStateMachine.get_valid_transitions(status)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base_dict = self._machine.to_dict()
        base_dict.update({
            "current_node_id": self._current_node_id,
            "node_execution_count": self._node_execution_count,
            "event_count": self._event_adapter.event_count,
            "event_status": self.event_status.value,
        })
        return base_dict

    def __repr__(self) -> str:
        return (
            f"EnhancedExecutionStateMachine("
            f"id={self.execution_id}, "
            f"status={self.status.value}, "
            f"nodes={self._node_execution_count})"
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_enhanced_state_machine(
    execution_id: UUID,
    status: str = "pending",
    event_adapter: Optional[WorkflowStatusEventAdapter] = None,
) -> EnhancedExecutionStateMachine:
    """
    Factory function to create EnhancedExecutionStateMachine.

    Args:
        execution_id: Execution UUID
        status: Initial status string
        event_adapter: Optional event adapter

    Returns:
        EnhancedExecutionStateMachine instance
    """
    try:
        initial_status = DomainExecutionStatus(status)
    except ValueError:
        initial_status = DomainExecutionStatus.PENDING

    return EnhancedExecutionStateMachine(
        execution_id=execution_id,
        initial_status=initial_status,
        event_adapter=event_adapter,
    )


def wrap_state_machine(
    machine: DomainStateMachine,
    event_adapter: Optional[WorkflowStatusEventAdapter] = None,
) -> EnhancedExecutionStateMachine:
    """
    Wrap an existing domain state machine.

    Args:
        machine: The domain state machine to wrap
        event_adapter: Optional event adapter

    Returns:
        EnhancedExecutionStateMachine wrapping the domain machine
    """
    enhanced = EnhancedExecutionStateMachine(
        execution_id=machine.execution_id,
        initial_status=machine.status,
        event_adapter=event_adapter,
    )

    # Copy state from original machine
    enhanced._machine.started_at = machine.started_at
    enhanced._machine.completed_at = machine.completed_at
    enhanced._machine.llm_calls = machine.llm_calls
    enhanced._machine.llm_tokens = machine.llm_tokens
    enhanced._machine.llm_cost = machine.llm_cost
    enhanced._machine._history = list(machine._history)

    return enhanced


# =============================================================================
# Event-Driven State Machine Manager
# =============================================================================

class StateMachineManager:
    """
    Manager for multiple state machines.

    Provides centralized management of execution state machines
    with shared event adapter.

    Example:
        >>> manager = StateMachineManager()
        >>> machine = manager.create(execution_id)
        >>> await manager.process_event(event)  # Dispatches to correct machine
    """

    def __init__(self, event_adapter: Optional[WorkflowStatusEventAdapter] = None):
        """
        Initialize the manager.

        Args:
            event_adapter: Shared event adapter (optional)
        """
        self._machines: Dict[UUID, EnhancedExecutionStateMachine] = {}
        self._event_adapter = event_adapter or WorkflowStatusEventAdapter()

    def create(
        self,
        execution_id: UUID,
        initial_status: str = "pending",
    ) -> EnhancedExecutionStateMachine:
        """
        Create and register a new state machine.

        Args:
            execution_id: Execution UUID
            initial_status: Initial status

        Returns:
            New EnhancedExecutionStateMachine
        """
        machine = create_enhanced_state_machine(
            execution_id=execution_id,
            status=initial_status,
            event_adapter=self._event_adapter,
        )
        self._machines[execution_id] = machine
        return machine

    def get(self, execution_id: UUID) -> Optional[EnhancedExecutionStateMachine]:
        """Get a state machine by execution ID."""
        return self._machines.get(execution_id)

    def remove(self, execution_id: UUID) -> bool:
        """Remove a state machine."""
        if execution_id in self._machines:
            del self._machines[execution_id]
            return True
        return False

    async def process_event(self, event: InternalExecutionEvent) -> bool:
        """
        Process an event and route to correct machine.

        Args:
            event: The event to process

        Returns:
            True if machine found and event processed
        """
        machine = self._machines.get(event.execution_id)
        if machine:
            await machine.handle_event(event)
            return True
        return False

    @property
    def machine_count(self) -> int:
        """Get count of managed machines."""
        return len(self._machines)

    def get_all_statuses(self) -> Dict[UUID, DomainExecutionStatus]:
        """Get all machine statuses."""
        return {
            exec_id: machine.status
            for exec_id, machine in self._machines.items()
        }

    def __repr__(self) -> str:
        return f"StateMachineManager(machines={len(self._machines)})"
