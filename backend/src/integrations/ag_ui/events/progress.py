# =============================================================================
# IPA Platform - AG-UI Step Progress Events
# =============================================================================
# Sprint 69: S69-1 - step_progress Backend Event
#
# Step progress events for AG-UI protocol, providing hierarchical step
# information including sub-steps, progress percentage, and status.
#
# Used for Claude Code-style visual feedback during workflow execution.
#
# Dependencies:
#   - CustomEvent (src.integrations.ag_ui.events.state)
# =============================================================================

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .state import CustomEvent


class SubStepStatus(str, Enum):
    """
    Sub-step status enumeration.

    Attributes:
        PENDING: Not yet started
        RUNNING: Currently executing
        COMPLETED: Successfully completed
        FAILED: Execution failed
        SKIPPED: Skipped (e.g., conditional skip)
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubStep:
    """
    Sub-step within a main step.

    Represents a sub-task within a workflow step for granular progress tracking.

    Attributes:
        id: Unique identifier for the sub-step
        name: Display name of the sub-step
        status: Current status
        progress: Progress percentage (0-100), optional
        message: Optional status message
        started_at: ISO timestamp when started
        completed_at: ISO timestamp when completed
        duration_ms: Duration in milliseconds (calculated)
    """

    id: str
    name: str
    status: SubStepStatus = SubStepStatus.PENDING
    progress: Optional[int] = None
    message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
        }
        if self.progress is not None:
            result["progress"] = self.progress
        if self.message:
            result["message"] = self.message
        if self.started_at:
            result["started_at"] = self.started_at
        if self.completed_at:
            result["completed_at"] = self.completed_at
        return result

    def mark_running(self, message: Optional[str] = None) -> "SubStep":
        """Mark sub-step as running."""
        from datetime import datetime

        self.status = SubStepStatus.RUNNING
        self.started_at = datetime.utcnow().isoformat() + "Z"
        if message:
            self.message = message
        return self

    def mark_completed(self, message: Optional[str] = None) -> "SubStep":
        """Mark sub-step as completed."""
        from datetime import datetime

        self.status = SubStepStatus.COMPLETED
        self.progress = 100
        self.completed_at = datetime.utcnow().isoformat() + "Z"
        if message:
            self.message = message
        return self

    def mark_failed(self, message: Optional[str] = None) -> "SubStep":
        """Mark sub-step as failed."""
        from datetime import datetime

        self.status = SubStepStatus.FAILED
        self.completed_at = datetime.utcnow().isoformat() + "Z"
        if message:
            self.message = message
        return self


@dataclass
class StepProgressPayload:
    """
    Payload for step_progress custom event.

    Provides hierarchical step information for Claude Code-style progress display.

    Attributes:
        step_id: Unique identifier for the step
        step_name: Display name of the step
        current: Current step number (1-based)
        total: Total number of steps
        progress: Overall progress percentage (0-100)
        status: Current step status
        substeps: List of sub-steps
        metadata: Additional metadata
    """

    step_id: str
    step_name: str
    current: int
    total: int
    progress: int
    status: SubStepStatus = SubStepStatus.PENDING
    substeps: List[SubStep] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "current": self.current,
            "total": self.total,
            "progress": self.progress,
            "status": self.status.value,
            "substeps": [ss.to_dict() for ss in self.substeps],
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @staticmethod
    def calculate_progress(substeps: List[SubStep]) -> int:
        """
        Calculate overall progress from substeps.

        Args:
            substeps: List of sub-steps

        Returns:
            Progress percentage (0-100)
        """
        if not substeps:
            return 0

        completed = sum(1 for s in substeps if s.status == SubStepStatus.COMPLETED)
        running_progress = sum(
            (s.progress or 0) / 100
            for s in substeps
            if s.status == SubStepStatus.RUNNING
        )

        total_progress = completed + running_progress
        return int((total_progress / len(substeps)) * 100)


class StepProgressTracker:
    """
    Tracker for step progress during workflow execution.

    Manages step state and generates progress events.

    Example:
        >>> tracker = StepProgressTracker(total_steps=5)
        >>> tracker.start_step("load", "Load data", ["parse", "validate"])
        >>> tracker.update_substep("parse", SubStepStatus.COMPLETED)
        >>> event = tracker.get_progress_event()
    """

    def __init__(
        self,
        total_steps: int,
        emit_callback: Optional[callable] = None,
    ):
        """
        Initialize tracker.

        Args:
            total_steps: Total number of steps in the workflow
            emit_callback: Optional callback to emit events
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.emit_callback = emit_callback
        self._current_payload: Optional[StepProgressPayload] = None
        self._last_emit_time = 0.0
        self._min_emit_interval = 0.5  # Max 2 events per second

    def start_step(
        self,
        step_id: str,
        step_name: str,
        substep_names: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StepProgressPayload:
        """
        Start a new step.

        Args:
            step_id: Unique step identifier
            step_name: Display name
            substep_names: Optional list of substep names
            metadata: Optional metadata

        Returns:
            StepProgressPayload for the started step
        """
        self.current_step += 1

        substeps = []
        if substep_names:
            substeps = [
                SubStep(id=f"{step_id}-{i}", name=name)
                for i, name in enumerate(substep_names)
            ]

        self._current_payload = StepProgressPayload(
            step_id=step_id,
            step_name=step_name,
            current=self.current_step,
            total=self.total_steps,
            progress=0,
            status=SubStepStatus.RUNNING,
            substeps=substeps,
            metadata=metadata,
        )

        self._emit_event()
        return self._current_payload

    def update_substep(
        self,
        substep_id: str,
        status: SubStepStatus,
        progress: Optional[int] = None,
        message: Optional[str] = None,
    ) -> Optional[StepProgressPayload]:
        """
        Update a substep's status.

        Args:
            substep_id: Substep identifier
            status: New status
            progress: Optional progress percentage
            message: Optional status message

        Returns:
            Updated StepProgressPayload or None if not found
        """
        if not self._current_payload:
            return None

        for substep in self._current_payload.substeps:
            if substep.id == substep_id or substep.id.endswith(f"-{substep_id}"):
                substep.status = status
                if progress is not None:
                    substep.progress = progress
                if message:
                    substep.message = message

                # Update timestamps
                from datetime import datetime

                now = datetime.utcnow().isoformat() + "Z"
                if status == SubStepStatus.RUNNING and not substep.started_at:
                    substep.started_at = now
                elif status in (
                    SubStepStatus.COMPLETED,
                    SubStepStatus.FAILED,
                    SubStepStatus.SKIPPED,
                ):
                    substep.completed_at = now

                break

        # Recalculate overall progress
        self._current_payload.progress = StepProgressPayload.calculate_progress(
            self._current_payload.substeps
        )

        self._emit_event()
        return self._current_payload

    def complete_step(
        self,
        success: bool = True,
        message: Optional[str] = None,
    ) -> Optional[StepProgressPayload]:
        """
        Mark current step as complete.

        Args:
            success: Whether step completed successfully
            message: Optional completion message

        Returns:
            Updated StepProgressPayload or None
        """
        if not self._current_payload:
            return None

        self._current_payload.status = (
            SubStepStatus.COMPLETED if success else SubStepStatus.FAILED
        )
        self._current_payload.progress = 100 if success else self._current_payload.progress

        if message and self._current_payload.metadata is None:
            self._current_payload.metadata = {}
        if message:
            self._current_payload.metadata["completion_message"] = message

        self._emit_event(force=True)
        return self._current_payload

    def get_progress_event(self) -> Optional[CustomEvent]:
        """
        Get current progress as CustomEvent.

        Returns:
            CustomEvent with step_progress payload or None
        """
        if not self._current_payload:
            return None

        return create_step_progress_event(self._current_payload)

    def _emit_event(self, force: bool = False) -> None:
        """Emit progress event via callback if configured."""
        if not self.emit_callback:
            return

        # Throttle events (max 2 per second)
        now = time.time()
        if not force and (now - self._last_emit_time) < self._min_emit_interval:
            return

        event = self.get_progress_event()
        if event:
            self.emit_callback(event)
            self._last_emit_time = now


def create_step_progress_event(payload: StepProgressPayload) -> CustomEvent:
    """
    Create a step_progress CustomEvent.

    Args:
        payload: StepProgressPayload with step information

    Returns:
        CustomEvent with event_name="step_progress"
    """
    return CustomEvent(
        event_name="step_progress",
        payload=payload.to_dict(),
    )


def emit_step_progress(
    bridge: Any,  # HybridEventBridge
    payload: StepProgressPayload,
) -> None:
    """
    Emit step_progress event via bridge.

    Convenience function for emitting progress during workflow execution.

    Args:
        bridge: HybridEventBridge instance
        payload: StepProgressPayload with step information

    Example:
        >>> emit_step_progress(bridge, StepProgressPayload(
        ...     step_id="step-001",
        ...     step_name="Process documents",
        ...     current=2,
        ...     total=5,
        ...     progress=45,
        ...     status=SubStepStatus.RUNNING,
        ...     substeps=[
        ...         SubStep(id="load", name="Load files", status=SubStepStatus.COMPLETED),
        ...         SubStep(id="parse", name="Parse content", status=SubStepStatus.RUNNING, progress=67),
        ...     ],
        ... ))
    """
    event = create_step_progress_event(payload)

    # If bridge has format_event method, use it
    if hasattr(bridge, "format_event"):
        sse_string = bridge.format_event(event)
        # Log for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"Emitting step_progress: step={payload.step_id}, progress={payload.progress}%")
