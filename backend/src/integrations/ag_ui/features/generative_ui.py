# =============================================================================
# IPA Platform - AG-UI Agentic Generative UI Feature
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-4: Agentic Generative UI (6 pts)
#
# Generative UI handler for AG-UI protocol.
# Provides real-time progress updates for long-running operations and
# mode switch notifications for workflow/chat transitions.
#
# Features:
#   - Workflow progress event streaming
#   - Mode switch notification events
#   - Integration with ModeSwitcher for dynamic mode switching
#   - Multi-step workflow progress tracking
#
# Dependencies:
#   - ModeSwitcher (src.integrations.hybrid.switching)
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

from src.integrations.ag_ui.events import (
    AGUIEventType,
    CustomEvent,
)
from src.integrations.hybrid.switching.models import (
    SwitchResult,
    SwitchTrigger,
    SwitchTriggerType,
    SwitchStatus,
)

if TYPE_CHECKING:
    from src.integrations.hybrid.switching.switcher import ModeSwitcher

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class ProgressStatus(str, Enum):
    """
    Status of workflow progress.

    Attributes:
        PENDING: Step not yet started
        IN_PROGRESS: Step is currently executing
        COMPLETED: Step completed successfully
        FAILED: Step failed
        SKIPPED: Step was skipped
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ModeSwitchReason(str, Enum):
    """
    Reason for mode switch.

    Attributes:
        COMPLEXITY: Task complexity requires mode change
        USER_REQUEST: User explicitly requested mode switch
        FAILURE_RECOVERY: Recovery from failure
        RESOURCE_OPTIMIZATION: Resource optimization
        TIMEOUT: Timeout in current mode
        AUTOMATIC: Automatic detection
    """

    COMPLEXITY = "complexity"
    USER_REQUEST = "user_request"
    FAILURE_RECOVERY = "failure_recovery"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    TIMEOUT = "timeout"
    AUTOMATIC = "automatic"


# Default event names for AG-UI custom events
EVENT_WORKFLOW_PROGRESS = "workflow_progress"
EVENT_MODE_SWITCH = "mode_switch"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WorkflowStep:
    """
    A single step in a workflow.

    Attributes:
        step_id: Unique step identifier
        name: Human-readable step name
        description: Step description
        status: Current step status
        order: Step order in workflow
        started_at: When step started
        completed_at: When step completed
        result: Step result data
        error: Error message if failed
        metadata: Additional metadata
    """

    step_id: str
    name: str
    description: str = ""
    status: ProgressStatus = ProgressStatus.PENDING
    order: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "order": self.order,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowProgress:
    """
    Progress information for a multi-step workflow.

    Attributes:
        workflow_id: Unique workflow identifier
        workflow_name: Human-readable workflow name
        total_steps: Total number of steps
        completed_steps: Number of completed steps
        current_step: Currently executing step
        steps: List of all workflow steps
        overall_progress: Overall progress percentage (0.0-1.0)
        started_at: When workflow started
        estimated_completion: Estimated completion time
        metadata: Additional metadata
    """

    workflow_id: str
    workflow_name: str
    total_steps: int
    completed_steps: int = 0
    current_step: Optional[WorkflowStep] = None
    steps: List[WorkflowStep] = field(default_factory=list)
    overall_progress: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "current_step": self.current_step.to_dict() if self.current_step else None,
            "steps": [step.to_dict() for step in self.steps],
            "overall_progress": self.overall_progress,
            "started_at": self.started_at.isoformat(),
            "estimated_completion": (
                self.estimated_completion.isoformat()
                if self.estimated_completion
                else None
            ),
            "metadata": self.metadata,
        }

    def calculate_progress(self) -> float:
        """Calculate and update overall progress."""
        if self.total_steps == 0:
            return 0.0
        self.overall_progress = self.completed_steps / self.total_steps
        return self.overall_progress


@dataclass
class ModeSwitchInfo:
    """
    Information about a mode switch event.

    Attributes:
        switch_id: Unique switch identifier
        source_mode: Mode before switch
        target_mode: Mode after switch
        reason: Reason for the switch
        trigger_type: Type of trigger that initiated switch
        confidence: Confidence level (0.0-1.0)
        message: Human-readable message about the switch
        success: Whether switch was successful
        rollback_available: Whether rollback is available
        metadata: Additional metadata
    """

    switch_id: str
    source_mode: str
    target_mode: str
    reason: str
    trigger_type: str = SwitchTriggerType.MANUAL.value
    confidence: float = 1.0
    message: str = ""
    success: bool = True
    rollback_available: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "switch_id": self.switch_id,
            "source_mode": self.source_mode,
            "target_mode": self.target_mode,
            "reason": self.reason,
            "trigger_type": self.trigger_type,
            "confidence": self.confidence,
            "message": self.message,
            "success": self.success,
            "rollback_available": self.rollback_available,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


# =============================================================================
# Generative UI Handler
# =============================================================================


class GenerativeUIHandler:
    """
    Handler for Agentic Generative UI events.

    Manages the emission of progress events and mode switch notifications
    following the AG-UI protocol specification.

    Attributes:
        mode_switcher: Optional ModeSwitcher instance for mode switching integration
        _active_workflows: Dictionary of active workflow progress trackers
        _event_history: History of emitted events for debugging

    Example:
        >>> handler = GenerativeUIHandler()
        >>> progress = WorkflowProgress(
        ...     workflow_id="wf-123",
        ...     workflow_name="Data Analysis",
        ...     total_steps=3
        ... )
        >>> event = await handler.emit_progress_event(
        ...     run_id="run-456",
        ...     progress=progress
        ... )
    """

    def __init__(
        self,
        mode_switcher: Optional["ModeSwitcher"] = None,
        max_event_history: int = 100,
    ):
        """
        Initialize the GenerativeUIHandler.

        Args:
            mode_switcher: Optional ModeSwitcher for mode switching integration
            max_event_history: Maximum number of events to keep in history
        """
        self.mode_switcher = mode_switcher
        self._active_workflows: Dict[str, WorkflowProgress] = {}
        self._event_history: List[CustomEvent] = []
        self._max_event_history = max_event_history

        logger.info("GenerativeUIHandler initialized")

    # =========================================================================
    # Progress Event Methods
    # =========================================================================

    async def emit_progress_event(
        self,
        run_id: str,
        progress: WorkflowProgress,
        *,
        include_steps: bool = True,
    ) -> CustomEvent:
        """
        Emit a workflow progress event.

        Creates and returns a CustomEvent containing workflow progress information
        that can be streamed to the client via AG-UI SSE.

        Args:
            run_id: Run identifier for the event
            progress: WorkflowProgress containing current progress state
            include_steps: Whether to include individual step details

        Returns:
            CustomEvent with workflow_progress event type

        Example:
            >>> progress = WorkflowProgress(
            ...     workflow_id="wf-123",
            ...     workflow_name="Data Processing",
            ...     total_steps=5,
            ...     completed_steps=2
            ... )
            >>> event = await handler.emit_progress_event("run-456", progress)
            >>> print(event.event_name)  # "workflow_progress"
        """
        # Calculate progress if not already done
        progress.calculate_progress()

        # Build payload
        payload: Dict[str, Any] = {
            "workflow_id": progress.workflow_id,
            "workflow_name": progress.workflow_name,
            "total_steps": progress.total_steps,
            "completed_steps": progress.completed_steps,
            "overall_progress": progress.overall_progress,
            "started_at": progress.started_at.isoformat(),
        }

        if progress.current_step:
            payload["current_step"] = progress.current_step.to_dict()

        if include_steps:
            payload["steps"] = [step.to_dict() for step in progress.steps]

        if progress.estimated_completion:
            payload["estimated_completion"] = progress.estimated_completion.isoformat()

        if progress.metadata:
            payload["metadata"] = progress.metadata

        # Add run_id to payload
        payload["run_id"] = run_id

        # Create event
        event = CustomEvent(
            event_name=EVENT_WORKFLOW_PROGRESS,
            payload=payload,
        )

        # Track active workflow
        self._active_workflows[progress.workflow_id] = progress

        # Add to history
        self._add_to_history(event)

        logger.debug(
            f"Emitted workflow_progress event: workflow_id={progress.workflow_id}, "
            f"progress={progress.overall_progress:.1%}"
        )

        return event

    async def emit_step_started(
        self,
        run_id: str,
        workflow_id: str,
        step: WorkflowStep,
    ) -> CustomEvent:
        """
        Emit an event when a workflow step starts.

        Args:
            run_id: Run identifier
            workflow_id: Workflow identifier
            step: The step that started

        Returns:
            CustomEvent for step started
        """
        step.status = ProgressStatus.IN_PROGRESS
        step.started_at = datetime.utcnow()

        # Update active workflow if exists
        if workflow_id in self._active_workflows:
            progress = self._active_workflows[workflow_id]
            progress.current_step = step
            return await self.emit_progress_event(run_id, progress)

        # Create standalone event
        payload = {
            "workflow_id": workflow_id,
            "step": step.to_dict(),
            "event_type": "step_started",
            "run_id": run_id,
        }

        event = CustomEvent(
            event_name=EVENT_WORKFLOW_PROGRESS,
            payload=payload,
        )
        self._add_to_history(event)

        return event

    async def emit_step_completed(
        self,
        run_id: str,
        workflow_id: str,
        step: WorkflowStep,
        result: Optional[Dict[str, Any]] = None,
    ) -> CustomEvent:
        """
        Emit an event when a workflow step completes.

        Args:
            run_id: Run identifier
            workflow_id: Workflow identifier
            step: The step that completed
            result: Optional result data from the step

        Returns:
            CustomEvent for step completed
        """
        step.status = ProgressStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.result = result

        # Update active workflow if exists
        if workflow_id in self._active_workflows:
            progress = self._active_workflows[workflow_id]
            progress.completed_steps += 1
            progress.current_step = None
            return await self.emit_progress_event(run_id, progress)

        # Create standalone event
        payload = {
            "workflow_id": workflow_id,
            "step": step.to_dict(),
            "event_type": "step_completed",
            "run_id": run_id,
        }

        event = CustomEvent(
            event_name=EVENT_WORKFLOW_PROGRESS,
            payload=payload,
        )
        self._add_to_history(event)

        return event

    async def emit_step_failed(
        self,
        run_id: str,
        workflow_id: str,
        step: WorkflowStep,
        error: str,
    ) -> CustomEvent:
        """
        Emit an event when a workflow step fails.

        Args:
            run_id: Run identifier
            workflow_id: Workflow identifier
            step: The step that failed
            error: Error message

        Returns:
            CustomEvent for step failed
        """
        step.status = ProgressStatus.FAILED
        step.completed_at = datetime.utcnow()
        step.error = error

        # Update active workflow if exists
        if workflow_id in self._active_workflows:
            progress = self._active_workflows[workflow_id]
            progress.current_step = step
            return await self.emit_progress_event(run_id, progress)

        # Create standalone event
        payload = {
            "workflow_id": workflow_id,
            "step": step.to_dict(),
            "event_type": "step_failed",
            "error": error,
            "run_id": run_id,
        }

        event = CustomEvent(
            event_name=EVENT_WORKFLOW_PROGRESS,
            payload=payload,
        )
        self._add_to_history(event)

        return event

    # =========================================================================
    # Mode Switch Event Methods
    # =========================================================================

    async def emit_mode_switch_event(
        self,
        run_id: str,
        switch_info: ModeSwitchInfo,
    ) -> CustomEvent:
        """
        Emit a mode switch notification event.

        Creates and returns a CustomEvent containing mode switch information
        that notifies the client of a mode transition.

        Args:
            run_id: Run identifier for the event
            switch_info: ModeSwitchInfo containing switch details

        Returns:
            CustomEvent with mode_switch event type

        Example:
            >>> switch_info = ModeSwitchInfo(
            ...     switch_id="sw-123",
            ...     source_mode="chat",
            ...     target_mode="workflow",
            ...     reason="Multi-step task detected"
            ... )
            >>> event = await handler.emit_mode_switch_event("run-456", switch_info)
        """
        # Include run_id in payload for mode switch events
        payload = switch_info.to_dict()
        payload["run_id"] = run_id

        event = CustomEvent(
            event_name=EVENT_MODE_SWITCH,
            payload=payload,
        )
        self._add_to_history(event)

        logger.info(
            f"Emitted mode_switch event: {switch_info.source_mode} -> "
            f"{switch_info.target_mode}, reason={switch_info.reason}"
        )

        return event

    async def emit_mode_switch_from_result(
        self,
        run_id: str,
        result: SwitchResult,
        *,
        message: Optional[str] = None,
    ) -> CustomEvent:
        """
        Emit a mode switch event from a SwitchResult.

        Convenience method to create and emit a mode switch event
        directly from a ModeSwitcher SwitchResult.

        Args:
            run_id: Run identifier for the event
            result: SwitchResult from ModeSwitcher
            message: Optional custom message

        Returns:
            CustomEvent with mode_switch event type
        """
        trigger = result.trigger
        source_mode = trigger.source_mode if trigger else "unknown"
        target_mode = result.new_mode or (trigger.target_mode if trigger else "unknown")
        trigger_type = trigger.trigger_type.value if trigger else SwitchTriggerType.MANUAL.value
        confidence = trigger.confidence if trigger else 1.0
        reason = trigger.reason if trigger else "Mode switch executed"

        switch_info = ModeSwitchInfo(
            switch_id=result.switch_id,
            source_mode=source_mode,
            target_mode=target_mode,
            reason=reason,
            trigger_type=trigger_type,
            confidence=confidence,
            message=message or self._generate_switch_message(result),
            success=result.success,
            rollback_available=result.is_rollbackable(),
            metadata=result.metadata,
        )

        return await self.emit_mode_switch_event(run_id, switch_info)

    async def emit_mode_switch_started(
        self,
        run_id: str,
        trigger: SwitchTrigger,
    ) -> CustomEvent:
        """
        Emit a mode switch started notification.

        Called when a mode switch is about to begin.

        Args:
            run_id: Run identifier
            trigger: The trigger initiating the switch

        Returns:
            CustomEvent for switch started
        """
        switch_info = ModeSwitchInfo(
            switch_id=trigger.trigger_id,
            source_mode=trigger.source_mode,
            target_mode=trigger.target_mode,
            reason=trigger.reason,
            trigger_type=trigger.trigger_type.value,
            confidence=trigger.confidence,
            message=f"Switching from {trigger.source_mode} to {trigger.target_mode}...",
            success=True,  # In progress
            rollback_available=False,  # Not yet available
            metadata={
                "status": "started",
                **trigger.metadata,
            },
        )

        return await self.emit_mode_switch_event(run_id, switch_info)

    async def emit_mode_switch_completed(
        self,
        run_id: str,
        result: SwitchResult,
    ) -> CustomEvent:
        """
        Emit a mode switch completed notification.

        Called when a mode switch has completed (successfully or failed).

        Args:
            run_id: Run identifier
            result: The result of the switch operation

        Returns:
            CustomEvent for switch completed
        """
        return await self.emit_mode_switch_from_result(
            run_id,
            result,
            message=self._generate_switch_message(result),
        )

    # =========================================================================
    # Integration with ModeSwitcher
    # =========================================================================

    async def handle_switch_trigger(
        self,
        run_id: str,
        trigger: SwitchTrigger,
        context: Any,
        session_id: str,
    ) -> AsyncGenerator[CustomEvent, None]:
        """
        Handle a mode switch trigger with progress events.

        Orchestrates the mode switch process, emitting progress events
        at each stage.

        Args:
            run_id: Run identifier
            trigger: The switch trigger
            context: Hybrid context for migration
            session_id: Session identifier

        Yields:
            CustomEvent objects at each stage of the switch

        Raises:
            ValueError: If mode_switcher is not configured
        """
        if not self.mode_switcher:
            raise ValueError("ModeSwitcher not configured")

        # Emit started event
        yield await self.emit_mode_switch_started(run_id, trigger)

        try:
            # Execute the switch
            result = await self.mode_switcher.execute_switch(
                trigger=trigger,
                context=context,
                session_id=session_id,
            )

            # Emit completed event
            yield await self.emit_mode_switch_completed(run_id, result)

        except Exception as e:
            # Emit failed event
            error_info = ModeSwitchInfo(
                switch_id=trigger.trigger_id,
                source_mode=trigger.source_mode,
                target_mode=trigger.target_mode,
                reason=f"Switch failed: {str(e)}",
                trigger_type=trigger.trigger_type.value,
                confidence=trigger.confidence,
                message=f"Mode switch failed: {str(e)}",
                success=False,
                rollback_available=False,
                metadata={"error": str(e)},
            )
            yield await self.emit_mode_switch_event(run_id, error_info)
            raise

    # =========================================================================
    # Workflow Management
    # =========================================================================

    def start_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        steps: List[WorkflowStep],
    ) -> WorkflowProgress:
        """
        Start tracking a new workflow.

        Args:
            workflow_id: Unique workflow identifier
            workflow_name: Human-readable name
            steps: List of workflow steps

        Returns:
            WorkflowProgress instance for tracking
        """
        progress = WorkflowProgress(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            total_steps=len(steps),
            steps=steps,
            started_at=datetime.utcnow(),
        )

        self._active_workflows[workflow_id] = progress

        logger.debug(f"Started tracking workflow: {workflow_id} with {len(steps)} steps")

        return progress

    def get_workflow_progress(self, workflow_id: str) -> Optional[WorkflowProgress]:
        """
        Get progress for an active workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            WorkflowProgress if found, None otherwise
        """
        return self._active_workflows.get(workflow_id)

    def complete_workflow(self, workflow_id: str) -> Optional[WorkflowProgress]:
        """
        Mark a workflow as complete and stop tracking.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Final WorkflowProgress if found, None otherwise
        """
        progress = self._active_workflows.pop(workflow_id, None)
        if progress:
            progress.completed_steps = progress.total_steps
            progress.overall_progress = 1.0
            logger.debug(f"Completed workflow: {workflow_id}")
        return progress

    def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel an active workflow and stop tracking.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if workflow was found and cancelled
        """
        if workflow_id in self._active_workflows:
            del self._active_workflows[workflow_id]
            logger.debug(f"Cancelled workflow: {workflow_id}")
            return True
        return False

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _generate_switch_message(self, result: SwitchResult) -> str:
        """Generate a human-readable message for a switch result."""
        if result.success:
            new_mode = result.new_mode or "new mode"
            return f"Successfully switched to {new_mode}"
        else:
            return f"Mode switch failed: {result.error or 'Unknown error'}"

    def _add_to_history(self, event: CustomEvent) -> None:
        """Add event to history with size limit."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_event_history:
            self._event_history.pop(0)

    def get_event_history(
        self,
        limit: Optional[int] = None,
        event_name: Optional[str] = None,
    ) -> List[CustomEvent]:
        """
        Get event history with optional filtering.

        Args:
            limit: Maximum number of events to return
            event_name: Filter by event name

        Returns:
            List of CustomEvent objects
        """
        events = self._event_history

        if event_name:
            events = [e for e in events if e.event_name == event_name]

        if limit:
            events = events[-limit:]

        return events

    def get_active_workflow_count(self) -> int:
        """Get count of active workflows being tracked."""
        return len(self._active_workflows)

    def get_active_workflow_ids(self) -> List[str]:
        """Get list of active workflow IDs."""
        return list(self._active_workflows.keys())

    def clear_event_history(self) -> None:
        """Clear all event history."""
        self._event_history.clear()
        logger.debug("Cleared event history")


# =============================================================================
# Factory Function
# =============================================================================


def create_generative_ui_handler(
    mode_switcher: Optional["ModeSwitcher"] = None,
    max_event_history: int = 100,
) -> GenerativeUIHandler:
    """
    Create a GenerativeUIHandler instance.

    Factory function for creating handler instances with dependency injection.

    Args:
        mode_switcher: Optional ModeSwitcher for mode switching integration
        max_event_history: Maximum events to keep in history

    Returns:
        Configured GenerativeUIHandler instance

    Example:
        >>> from src.integrations.hybrid.switching import ModeSwitcher
        >>> switcher = ModeSwitcher()
        >>> handler = create_generative_ui_handler(mode_switcher=switcher)
    """
    return GenerativeUIHandler(
        mode_switcher=mode_switcher,
        max_event_history=max_event_history,
    )
