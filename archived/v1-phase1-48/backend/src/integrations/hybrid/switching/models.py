# =============================================================================
# IPA Platform - Mode Switching Models
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL
#
# Data models for dynamic mode switching between Workflow and Chat modes.
#
# Key Models:
#   - SwitchTrigger: Trigger information for mode switching
#   - SwitchResult: Result of mode switch operation
#   - ModeTransition: Transition record between modes
#   - MigratedState: State after migration between modes
#   - SwitchConfig: Configuration for mode switching
#
# Dependencies:
#   - ExecutionMode (src.integrations.hybrid.intent.models)
#   - HybridContext (src.integrations.hybrid.context.models)
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


# =============================================================================
# Enums
# =============================================================================


class SwitchTriggerType(str, Enum):
    """
    Type of trigger that initiates mode switching.

    Types:
        COMPLEXITY: Task complexity change detected
        USER_REQUEST: User explicitly requests mode switch
        FAILURE: Failure recovery needed
        RESOURCE: Resource constraints require mode change
        TIMEOUT: Timeout in current mode
        MANUAL: Manual API trigger
    """

    COMPLEXITY = "complexity"
    USER_REQUEST = "user_request"
    FAILURE = "failure"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    MANUAL = "manual"


class SwitchStatus(str, Enum):
    """
    Status of a mode switch operation.

    Statuses:
        PENDING: Switch requested but not started
        IN_PROGRESS: Switch is being executed
        COMPLETED: Switch completed successfully
        FAILED: Switch failed
        ROLLED_BACK: Switch was rolled back
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationDirection(str, Enum):
    """
    Direction of state migration.

    Directions:
        WORKFLOW_TO_CHAT: MAF Workflow to Claude Chat
        CHAT_TO_WORKFLOW: Claude Chat to MAF Workflow
        WORKFLOW_TO_HYBRID: Workflow to Hybrid mode
        CHAT_TO_HYBRID: Chat to Hybrid mode
        HYBRID_TO_WORKFLOW: Hybrid to Workflow mode
        HYBRID_TO_CHAT: Hybrid to Chat mode
    """

    WORKFLOW_TO_CHAT = "workflow_to_chat"
    CHAT_TO_WORKFLOW = "chat_to_workflow"
    WORKFLOW_TO_HYBRID = "workflow_to_hybrid"
    CHAT_TO_HYBRID = "chat_to_hybrid"
    HYBRID_TO_WORKFLOW = "hybrid_to_workflow"
    HYBRID_TO_CHAT = "hybrid_to_chat"


class ValidationStatus(str, Enum):
    """
    Status of switch validation.

    Statuses:
        VALID: Validation passed
        INVALID: Validation failed
        WARNING: Validation passed with warnings
    """

    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class SwitchConfig:
    """
    Configuration for mode switching.

    Attributes:
        enable_auto_switch: Allow automatic mode switching
        complexity_threshold: Threshold for complexity-based switching
        failure_threshold: Number of failures before switching
        timeout_seconds: Timeout for switch operation
        enable_rollback: Enable automatic rollback on failure
        max_rollback_attempts: Maximum rollback attempts
        require_approval_for_switch: Require human approval for switching
        preserve_history: Preserve conversation/execution history
        preserve_tool_results: Preserve tool call results
    """

    enable_auto_switch: bool = True
    complexity_threshold: float = 0.7
    failure_threshold: int = 3
    timeout_seconds: int = 300
    enable_rollback: bool = True
    max_rollback_attempts: int = 3
    require_approval_for_switch: bool = False
    preserve_history: bool = True
    preserve_tool_results: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enable_auto_switch": self.enable_auto_switch,
            "complexity_threshold": self.complexity_threshold,
            "failure_threshold": self.failure_threshold,
            "timeout_seconds": self.timeout_seconds,
            "enable_rollback": self.enable_rollback,
            "max_rollback_attempts": self.max_rollback_attempts,
            "require_approval_for_switch": self.require_approval_for_switch,
            "preserve_history": self.preserve_history,
            "preserve_tool_results": self.preserve_tool_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SwitchConfig":
        """Create from dictionary."""
        return cls(
            enable_auto_switch=data.get("enable_auto_switch", True),
            complexity_threshold=data.get("complexity_threshold", 0.7),
            failure_threshold=data.get("failure_threshold", 3),
            timeout_seconds=data.get("timeout_seconds", 300),
            enable_rollback=data.get("enable_rollback", True),
            max_rollback_attempts=data.get("max_rollback_attempts", 3),
            require_approval_for_switch=data.get("require_approval_for_switch", False),
            preserve_history=data.get("preserve_history", True),
            preserve_tool_results=data.get("preserve_tool_results", True),
        )


# =============================================================================
# Core Models
# =============================================================================


@dataclass
class SwitchTrigger:
    """
    Trigger information for mode switching.

    Contains details about what triggered the mode switch,
    including source mode, target mode, and confidence level.

    Attributes:
        trigger_id: Unique trigger identifier
        trigger_type: Type of trigger (complexity, user_request, etc.)
        source_mode: Current execution mode
        target_mode: Desired execution mode
        reason: Human-readable reason for the switch
        confidence: Confidence level (0.0 to 1.0)
        metadata: Additional trigger metadata
        detected_at: When the trigger was detected

    Example:
        >>> trigger = SwitchTrigger(
        ...     trigger_type=SwitchTriggerType.COMPLEXITY,
        ...     source_mode="chat",
        ...     target_mode="workflow",
        ...     reason="Multi-step task detected",
        ...     confidence=0.85
        ... )
    """

    trigger_type: SwitchTriggerType
    source_mode: str  # ExecutionMode value
    target_mode: str  # ExecutionMode value
    reason: str
    confidence: float = 0.5
    trigger_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trigger_id": self.trigger_id,
            "trigger_type": self.trigger_type.value,
            "source_mode": self.source_mode,
            "target_mode": self.target_mode,
            "reason": self.reason,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "detected_at": self.detected_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SwitchTrigger":
        """Create from dictionary."""
        return cls(
            trigger_id=data.get("trigger_id", str(uuid4())),
            trigger_type=SwitchTriggerType(data["trigger_type"]),
            source_mode=data["source_mode"],
            target_mode=data["target_mode"],
            reason=data["reason"],
            confidence=data.get("confidence", 0.5),
            metadata=data.get("metadata", {}),
            detected_at=(
                datetime.fromisoformat(data["detected_at"])
                if "detected_at" in data
                else datetime.utcnow()
            ),
        )

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if trigger has high confidence."""
        return self.confidence >= threshold


@dataclass
class MigratedState:
    """
    State after migration between modes.

    Contains the migrated context and any transformation details.

    Attributes:
        migration_id: Unique migration identifier
        direction: Direction of migration
        preserved_history: Preserved conversation/execution history
        preserved_tool_results: Preserved tool call results
        context_summary: Summary of migrated context
        transformed_variables: Variables transformed during migration
        warnings: Any warnings during migration
        migration_time_ms: Time taken for migration

    Example:
        >>> state = MigratedState(
        ...     direction=MigrationDirection.CHAT_TO_WORKFLOW,
        ...     preserved_history=True,
        ...     context_summary="5 messages, 3 tool calls preserved"
        ... )
    """

    direction: MigrationDirection
    preserved_history: bool = True
    preserved_tool_results: bool = True
    migration_id: str = field(default_factory=lambda: str(uuid4()))
    context_summary: str = ""
    transformed_variables: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_call_results: List[Dict[str, Any]] = field(default_factory=list)
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    migration_time_ms: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "migration_id": self.migration_id,
            "direction": self.direction.value,
            "preserved_history": self.preserved_history,
            "preserved_tool_results": self.preserved_tool_results,
            "context_summary": self.context_summary,
            "transformed_variables": self.transformed_variables,
            "conversation_history": self.conversation_history,
            "tool_call_results": self.tool_call_results,
            "workflow_state": self.workflow_state,
            "warnings": self.warnings,
            "migration_time_ms": self.migration_time_ms,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigratedState":
        """Create from dictionary."""
        return cls(
            migration_id=data.get("migration_id", str(uuid4())),
            direction=MigrationDirection(data["direction"]),
            preserved_history=data.get("preserved_history", True),
            preserved_tool_results=data.get("preserved_tool_results", True),
            context_summary=data.get("context_summary", ""),
            transformed_variables=data.get("transformed_variables", {}),
            conversation_history=data.get("conversation_history", []),
            tool_call_results=data.get("tool_call_results", []),
            workflow_state=data.get("workflow_state", {}),
            warnings=data.get("warnings", []),
            migration_time_ms=data.get("migration_time_ms", 0),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
        )

    def has_warnings(self) -> bool:
        """Check if migration has warnings."""
        return len(self.warnings) > 0


@dataclass
class SwitchValidation:
    """
    Validation result for mode switch.

    Attributes:
        status: Validation status
        success: Whether validation passed
        checks_passed: List of passed checks
        checks_failed: List of failed checks
        warnings: Validation warnings
        error: Error message if validation failed
    """

    status: ValidationStatus = ValidationStatus.VALID
    success: bool = True
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "success": self.success,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "warnings": self.warnings,
            "error": self.error,
        }


@dataclass
class SwitchCheckpoint:
    """
    Checkpoint created before mode switch for rollback support.

    Attributes:
        checkpoint_id: Unique checkpoint identifier
        switch_id: Associated switch operation ID
        context_snapshot: Snapshot of HybridContext before switch
        mode_before: Mode before switch
        created_at: When checkpoint was created
    """

    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    switch_id: str = ""
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    mode_before: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "switch_id": self.switch_id,
            "context_snapshot": self.context_snapshot,
            "mode_before": self.mode_before,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SwitchCheckpoint":
        """Create from dictionary."""
        return cls(
            checkpoint_id=data.get("checkpoint_id", str(uuid4())),
            switch_id=data.get("switch_id", ""),
            context_snapshot=data.get("context_snapshot", {}),
            mode_before=data.get("mode_before", ""),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
        )


@dataclass
class SwitchResult:
    """
    Result of a mode switch operation.

    Contains the outcome of the switch, including success status,
    new mode, and any error information.

    Attributes:
        switch_id: Unique switch operation identifier
        success: Whether switch succeeded
        status: Current status of the switch
        trigger: Trigger that initiated the switch
        new_mode: New execution mode after switch
        migrated_state: State after migration
        checkpoint_id: ID of rollback checkpoint
        validation: Validation result
        error: Error message if switch failed
        switch_time_ms: Time taken for switch operation
        started_at: When switch started
        completed_at: When switch completed

    Example:
        >>> result = SwitchResult(
        ...     success=True,
        ...     new_mode="workflow",
        ...     migrated_state=migrated_state
        ... )
    """

    success: bool
    switch_id: str = field(default_factory=lambda: str(uuid4()))
    status: SwitchStatus = SwitchStatus.COMPLETED
    trigger: Optional[SwitchTrigger] = None
    new_mode: Optional[str] = None
    migrated_state: Optional[MigratedState] = None
    checkpoint_id: Optional[str] = None
    validation: Optional[SwitchValidation] = None
    error: Optional[str] = None
    switch_time_ms: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "switch_id": self.switch_id,
            "success": self.success,
            "status": self.status.value,
            "trigger": self.trigger.to_dict() if self.trigger else None,
            "new_mode": self.new_mode,
            "migrated_state": self.migrated_state.to_dict() if self.migrated_state else None,
            "checkpoint_id": self.checkpoint_id,
            "validation": self.validation.to_dict() if self.validation else None,
            "error": self.error,
            "switch_time_ms": self.switch_time_ms,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SwitchResult":
        """Create from dictionary."""
        return cls(
            switch_id=data.get("switch_id", str(uuid4())),
            success=data["success"],
            status=SwitchStatus(data.get("status", "completed")),
            trigger=SwitchTrigger.from_dict(data["trigger"]) if data.get("trigger") else None,
            new_mode=data.get("new_mode"),
            migrated_state=(
                MigratedState.from_dict(data["migrated_state"])
                if data.get("migrated_state")
                else None
            ),
            checkpoint_id=data.get("checkpoint_id"),
            validation=(
                SwitchValidation(**data["validation"]) if data.get("validation") else None
            ),
            error=data.get("error"),
            switch_time_ms=data.get("switch_time_ms", 0),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if "started_at" in data
                else datetime.utcnow()
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            metadata=data.get("metadata", {}),
        )

    def is_rollbackable(self) -> bool:
        """Check if switch can be rolled back."""
        return self.checkpoint_id is not None and self.status != SwitchStatus.ROLLED_BACK


@dataclass
class ModeTransition:
    """
    Record of a mode transition.

    Tracks the complete lifecycle of a mode switch for audit and analysis.

    Attributes:
        transition_id: Unique transition identifier
        session_id: Session where transition occurred
        source_mode: Mode before transition
        target_mode: Mode after transition
        trigger: Trigger that initiated transition
        result: Result of the transition
        rollback_of: If this is a rollback, ID of original transition
        created_at: When transition was created

    Example:
        >>> transition = ModeTransition(
        ...     session_id="sess_123",
        ...     source_mode="chat",
        ...     target_mode="workflow",
        ...     trigger=trigger,
        ...     result=result
        ... )
    """

    session_id: str
    source_mode: str
    target_mode: str
    transition_id: str = field(default_factory=lambda: str(uuid4()))
    trigger: Optional[SwitchTrigger] = None
    result: Optional[SwitchResult] = None
    rollback_of: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transition_id": self.transition_id,
            "session_id": self.session_id,
            "source_mode": self.source_mode,
            "target_mode": self.target_mode,
            "trigger": self.trigger.to_dict() if self.trigger else None,
            "result": self.result.to_dict() if self.result else None,
            "rollback_of": self.rollback_of,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModeTransition":
        """Create from dictionary."""
        return cls(
            transition_id=data.get("transition_id", str(uuid4())),
            session_id=data["session_id"],
            source_mode=data["source_mode"],
            target_mode=data["target_mode"],
            trigger=SwitchTrigger.from_dict(data["trigger"]) if data.get("trigger") else None,
            result=SwitchResult.from_dict(data["result"]) if data.get("result") else None,
            rollback_of=data.get("rollback_of"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
            metadata=data.get("metadata", {}),
        )

    def is_rollback(self) -> bool:
        """Check if this transition is a rollback."""
        return self.rollback_of is not None

    def was_successful(self) -> bool:
        """Check if transition was successful."""
        return self.result is not None and self.result.success


# =============================================================================
# Execution State for Trigger Detection
# =============================================================================


@dataclass
class ExecutionState:
    """
    Current execution state for trigger detection.

    Used by trigger detectors to evaluate if mode switch is needed.

    Attributes:
        session_id: Session identifier
        current_mode: Current execution mode
        consecutive_failures: Number of consecutive failures
        has_pending_steps: Whether workflow has pending steps
        step_count: Number of steps executed
        message_count: Number of messages in conversation
        tool_call_count: Number of tool calls made
        resource_usage: Resource usage metrics
        last_activity: Last activity timestamp
    """

    session_id: str
    current_mode: str
    consecutive_failures: int = 0
    has_pending_steps: bool = False
    step_count: int = 0
    message_count: int = 0
    tool_call_count: int = 0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "current_mode": self.current_mode,
            "consecutive_failures": self.consecutive_failures,
            "has_pending_steps": self.has_pending_steps,
            "step_count": self.step_count,
            "message_count": self.message_count,
            "tool_call_count": self.tool_call_count,
            "resource_usage": self.resource_usage,
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionState":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            current_mode=data["current_mode"],
            consecutive_failures=data.get("consecutive_failures", 0),
            has_pending_steps=data.get("has_pending_steps", False),
            step_count=data.get("step_count", 0),
            message_count=data.get("message_count", 0),
            tool_call_count=data.get("tool_call_count", 0),
            resource_usage=data.get("resource_usage", {}),
            last_activity=(
                datetime.fromisoformat(data["last_activity"])
                if "last_activity" in data
                else datetime.utcnow()
            ),
            metadata=data.get("metadata", {}),
        )
