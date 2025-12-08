# =============================================================================
# IPA Platform - Workflow Status Event Adapter
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 27, Story S27-2: WorkflowStatusEventAdapter (8 pts)
#
# This module provides adapters for handling workflow status events from
# the official Microsoft Agent Framework API.
#
# Official API Pattern (from workflows-api.md):
#   async for event in workflow.run_stream(input_data):
#       # Handle WorkflowStatusEvent
#
# Key Features:
#   - WorkflowStatusEventAdapter: Converts official events to internal format
#   - ExecutionStatus: Execution state enumeration
#   - InternalExecutionEvent: Internal event representation
#   - Event handler registration and management
#
# IMPORTANT: Uses official Agent Framework API
#   from agent_framework.workflows import WorkflowStatusEvent
# =============================================================================

from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
import asyncio
import logging

# Official Agent Framework Imports - MUST use these
from agent_framework.workflows import WorkflowStatusEvent


logger = logging.getLogger(__name__)


# =============================================================================
# ExecutionStatus - State Enumeration
# =============================================================================

class ExecutionStatus(str, Enum):
    """
    Execution status enumeration.

    Maps to workflow execution states for tracking and reporting.

    States:
        PENDING: Execution is queued but not started
        RUNNING: Execution is actively running
        WAITING_APPROVAL: Execution paused for human approval
        COMPLETED: Execution finished successfully
        FAILED: Execution encountered an error
        CANCELLED: Execution was cancelled
        PAUSED: Execution is paused (can be resumed)
        TIMEOUT: Execution exceeded time limit
    """
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    TIMEOUT = "timeout"

    @classmethod
    def from_string(cls, value: str) -> "ExecutionStatus":
        """
        Create status from string value.

        Args:
            value: Status string

        Returns:
            ExecutionStatus enum value
        """
        try:
            return cls(value.lower())
        except ValueError:
            # Default to RUNNING for unknown statuses
            return cls.RUNNING

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal (final) state."""
        return self in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT,
        )

    @property
    def is_active(self) -> bool:
        """Check if this is an active (running) state."""
        return self in (
            ExecutionStatus.RUNNING,
            ExecutionStatus.WAITING_APPROVAL,
            ExecutionStatus.PAUSED,
        )


# =============================================================================
# EventType - Event Type Enumeration
# =============================================================================

class EventType(str, Enum):
    """
    Workflow event types.

    These map to official WorkflowStatusEvent event types.
    """
    # Workflow-level events
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    # Executor-level events
    EXECUTOR_STARTED = "executor_started"
    EXECUTOR_COMPLETED = "executor_completed"
    EXECUTOR_FAILED = "executor_failed"

    # Human-in-the-loop events
    WAITING_INPUT = "waiting_input"
    INPUT_RECEIVED = "input_received"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RECEIVED = "approval_received"

    # Progress events
    PROGRESS = "progress"
    CHECKPOINT_SAVED = "checkpoint_saved"
    CHECKPOINT_LOADED = "checkpoint_loaded"

    @classmethod
    def from_string(cls, value: str) -> "EventType":
        """Create event type from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.PROGRESS


# =============================================================================
# InternalExecutionEvent - Internal Event Representation
# =============================================================================

@dataclass
class InternalExecutionEvent:
    """
    Internal representation of a workflow execution event.

    This provides a normalized format for events received from
    the official WorkflowStatusEvent, making them easier to handle
    in the IPA platform.

    Attributes:
        execution_id: Unique execution identifier
        event_type: Type of event (started, completed, etc.)
        status: Current execution status
        node_id: ID of the node that generated this event (optional)
        node_name: Name of the node (optional)
        data: Additional event data
        error: Error message if applicable
        timestamp: When the event occurred
        is_final: Whether this is a terminal event
        metadata: Additional metadata
    """
    execution_id: UUID
    event_type: str
    status: ExecutionStatus
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "event_type": self.event_type,
            "status": self.status.value,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "is_final": self.is_final,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InternalExecutionEvent":
        """Create event from dictionary."""
        return cls(
            execution_id=UUID(data["execution_id"]),
            event_type=data["event_type"],
            status=ExecutionStatus.from_string(data["status"]),
            node_id=data.get("node_id"),
            node_name=data.get("node_name"),
            data=data.get("data", {}),
            error=data.get("error"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            is_final=data.get("is_final", False),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"InternalExecutionEvent("
            f"type={self.event_type}, "
            f"status={self.status.value}, "
            f"node={self.node_id})"
        )


# =============================================================================
# WorkflowStatusEventAdapter - Main Event Adapter
# =============================================================================

class WorkflowStatusEventAdapter:
    """
    Adapter for handling official WorkflowStatusEvent instances.

    Converts official events to internal format and distributes them
    to registered handlers.

    Example:
        >>> adapter = WorkflowStatusEventAdapter()
        >>> adapter.add_handler(my_event_handler)
        >>> async for event in workflow.run_stream(input):
        ...     await adapter.handle(execution_id, event)

    IMPORTANT: Processes official WorkflowStatusEvent from agent_framework.workflows
    """

    # Mapping from official event types to internal status
    STATUS_MAPPING: Dict[str, ExecutionStatus] = {
        "started": ExecutionStatus.RUNNING,
        "executor_started": ExecutionStatus.RUNNING,
        "executor_completed": ExecutionStatus.RUNNING,
        "executor_failed": ExecutionStatus.FAILED,
        "completed": ExecutionStatus.COMPLETED,
        "failed": ExecutionStatus.FAILED,
        "cancelled": ExecutionStatus.CANCELLED,
        "waiting_input": ExecutionStatus.WAITING_APPROVAL,
        "input_received": ExecutionStatus.RUNNING,
        "approval_required": ExecutionStatus.WAITING_APPROVAL,
        "approval_received": ExecutionStatus.RUNNING,
        "progress": ExecutionStatus.RUNNING,
        "checkpoint_saved": ExecutionStatus.RUNNING,
        "checkpoint_loaded": ExecutionStatus.RUNNING,
    }

    # Terminal event types
    TERMINAL_EVENTS = {"completed", "failed", "cancelled", "timeout"}

    def __init__(self):
        """Initialize the event adapter."""
        self._handlers: List[Callable[[InternalExecutionEvent], None]] = []
        self._event_history: Dict[UUID, List[InternalExecutionEvent]] = {}
        self._event_count = 0

    def add_handler(
        self,
        handler: Callable[[InternalExecutionEvent], None],
    ) -> None:
        """
        Add an event handler.

        Handlers receive InternalExecutionEvent instances when events occur.
        Both sync and async handlers are supported.

        Args:
            handler: Callable that receives InternalExecutionEvent
        """
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable) -> None:
        """
        Remove an event handler.

        Args:
            handler: The handler to remove
        """
        if handler in self._handlers:
            self._handlers.remove(handler)

    def clear_handlers(self) -> None:
        """Remove all event handlers."""
        self._handlers.clear()

    async def handle(
        self,
        execution_id: UUID,
        event: Union[WorkflowStatusEvent, Dict[str, Any]],
    ) -> InternalExecutionEvent:
        """
        Handle a workflow status event.

        Converts the official event to internal format and dispatches
        to all registered handlers.

        Args:
            execution_id: The execution ID
            event: Official WorkflowStatusEvent or dict

        Returns:
            The converted InternalExecutionEvent
        """
        # Convert to internal event
        internal_event = self._convert_to_internal(execution_id, event)

        # Track in history
        if execution_id not in self._event_history:
            self._event_history[execution_id] = []
        self._event_history[execution_id].append(internal_event)
        self._event_count += 1

        # Dispatch to handlers
        await self._dispatch_event(internal_event)

        return internal_event

    def _convert_to_internal(
        self,
        execution_id: UUID,
        event: Union[WorkflowStatusEvent, Dict[str, Any]],
    ) -> InternalExecutionEvent:
        """
        Convert official event to internal format.

        Args:
            execution_id: The execution ID
            event: Official event or dict

        Returns:
            InternalExecutionEvent
        """
        # Handle dict events (for testing/mocking)
        if isinstance(event, dict):
            event_type = event.get("event_type", "progress")
            return InternalExecutionEvent(
                execution_id=execution_id,
                event_type=event_type,
                status=self._map_status(event_type),
                node_id=event.get("executor_id") or event.get("node_id"),
                node_name=event.get("executor_name") or event.get("node_name"),
                data=event.get("data", {}),
                error=event.get("error"),
                timestamp=datetime.utcnow(),
                is_final=event_type in self.TERMINAL_EVENTS,
                metadata=event.get("metadata", {}),
            )

        # Handle official WorkflowStatusEvent
        event_type = getattr(event, "event_type", "progress")

        return InternalExecutionEvent(
            execution_id=execution_id,
            event_type=event_type,
            status=self._map_status(event_type),
            node_id=getattr(event, "executor_id", None),
            node_name=getattr(event, "executor_name", None),
            data=getattr(event, "data", {}) if hasattr(event, "data") else {},
            error=getattr(event, "error", None),
            timestamp=datetime.utcnow(),
            is_final=event_type in self.TERMINAL_EVENTS,
            metadata={
                "workflow_id": getattr(event, "workflow_id", None),
                "original_type": type(event).__name__,
            },
        )

    def _map_status(self, event_type: str) -> ExecutionStatus:
        """
        Map event type to execution status.

        Args:
            event_type: The event type string

        Returns:
            ExecutionStatus enum value
        """
        return self.STATUS_MAPPING.get(
            event_type.lower(),
            ExecutionStatus.RUNNING
        )

    async def _dispatch_event(self, event: InternalExecutionEvent) -> None:
        """
        Dispatch event to all registered handlers.

        Args:
            event: The internal event to dispatch
        """
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    f"Event handler error: {e}",
                    exc_info=True,
                    extra={"event": event.to_dict()},
                )

    def get_history(self, execution_id: UUID) -> List[InternalExecutionEvent]:
        """
        Get event history for an execution.

        Args:
            execution_id: The execution ID

        Returns:
            List of events for this execution
        """
        return self._event_history.get(execution_id, [])

    def get_latest_status(self, execution_id: UUID) -> Optional[ExecutionStatus]:
        """
        Get the latest status for an execution.

        Args:
            execution_id: The execution ID

        Returns:
            Latest ExecutionStatus or None
        """
        history = self.get_history(execution_id)
        if history:
            return history[-1].status
        return None

    def clear_history(self, execution_id: Optional[UUID] = None) -> None:
        """
        Clear event history.

        Args:
            execution_id: Specific execution to clear, or None for all
        """
        if execution_id:
            self._event_history.pop(execution_id, None)
        else:
            self._event_history.clear()

    @property
    def handler_count(self) -> int:
        """Get the number of registered handlers."""
        return len(self._handlers)

    @property
    def event_count(self) -> int:
        """Get total number of events processed."""
        return self._event_count

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"WorkflowStatusEventAdapter("
            f"handlers={len(self._handlers)}, "
            f"events={self._event_count})"
        )


# =============================================================================
# EventFilter - Event Filtering
# =============================================================================

class EventFilter:
    """
    Filter for workflow events.

    Allows filtering events by type, status, node, etc.

    Example:
        >>> filter = EventFilter(event_types=["completed", "failed"])
        >>> if filter.matches(event):
        ...     process_event(event)
    """

    def __init__(
        self,
        event_types: Optional[List[str]] = None,
        statuses: Optional[List[ExecutionStatus]] = None,
        node_ids: Optional[List[str]] = None,
        include_terminal_only: bool = False,
        exclude_progress: bool = False,
    ):
        """
        Initialize the event filter.

        Args:
            event_types: Only match these event types
            statuses: Only match these statuses
            node_ids: Only match events from these nodes
            include_terminal_only: Only match terminal events
            exclude_progress: Exclude progress events
        """
        self.event_types = set(event_types) if event_types else None
        self.statuses = set(statuses) if statuses else None
        self.node_ids = set(node_ids) if node_ids else None
        self.include_terminal_only = include_terminal_only
        self.exclude_progress = exclude_progress

    def matches(self, event: InternalExecutionEvent) -> bool:
        """
        Check if an event matches the filter.

        Args:
            event: The event to check

        Returns:
            True if event matches filter criteria
        """
        # Check terminal only
        if self.include_terminal_only and not event.is_final:
            return False

        # Check exclude progress
        if self.exclude_progress and event.event_type == "progress":
            return False

        # Check event types
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Check statuses
        if self.statuses and event.status not in self.statuses:
            return False

        # Check node IDs
        if self.node_ids and event.node_id not in self.node_ids:
            return False

        return True


# =============================================================================
# Factory Functions
# =============================================================================

def create_event_adapter() -> WorkflowStatusEventAdapter:
    """
    Factory function to create a WorkflowStatusEventAdapter.

    Returns:
        WorkflowStatusEventAdapter instance
    """
    return WorkflowStatusEventAdapter()


def create_event(
    execution_id: UUID,
    event_type: str,
    status: Optional[ExecutionStatus] = None,
    node_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> InternalExecutionEvent:
    """
    Factory function to create an InternalExecutionEvent.

    Args:
        execution_id: Execution identifier
        event_type: Type of event
        status: Execution status (auto-mapped if not provided)
        node_id: Node identifier
        data: Event data
        error: Error message

    Returns:
        InternalExecutionEvent instance
    """
    adapter = WorkflowStatusEventAdapter()

    return InternalExecutionEvent(
        execution_id=execution_id,
        event_type=event_type,
        status=status or adapter._map_status(event_type),
        node_id=node_id,
        data=data or {},
        error=error,
        is_final=event_type in adapter.TERMINAL_EVENTS,
    )


def create_event_filter(
    event_types: Optional[List[str]] = None,
    terminal_only: bool = False,
) -> EventFilter:
    """
    Factory function to create an EventFilter.

    Args:
        event_types: Event types to match
        terminal_only: Only match terminal events

    Returns:
        EventFilter instance
    """
    return EventFilter(
        event_types=event_types,
        include_terminal_only=terminal_only,
    )
