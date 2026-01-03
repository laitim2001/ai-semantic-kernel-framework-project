# =============================================================================
# IPA Platform - Hybrid Mode Switch API Schemas
# =============================================================================
# Sprint 56: Mode Switcher & HITL
#
# Pydantic schemas for hybrid mode switch API request/response validation.
#
# Endpoints:
#   - POST /api/v1/hybrid/switch - Manual trigger mode switch
#   - GET /api/v1/hybrid/switch/status - Query switch status
#   - POST /api/v1/hybrid/switch/rollback - Rollback switch
#
# Dependencies:
#   - SwitchStatus, SwitchTriggerType (src.integrations.hybrid.switching)
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums (matching domain models)
# =============================================================================


class SwitchTriggerTypeSchema(str):
    """Switch trigger type values."""
    MANUAL = "manual"
    COMPLEXITY = "complexity"
    USER_REQUEST = "user_request"
    ERROR_RECOVERY = "error_recovery"
    CAPABILITY_MISMATCH = "capability_mismatch"
    TIMEOUT = "timeout"
    CONFIDENCE = "confidence"
    HYBRID_ESCALATION = "hybrid_escalation"


class SwitchStatusSchema(str):
    """Switch status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ExecutionModeSchema(str):
    """Execution mode values."""
    WORKFLOW_MODE = "workflow"
    CHAT_MODE = "chat"
    HYBRID_MODE = "hybrid"


class MigrationStatusSchema(str):
    """Migration status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# =============================================================================
# Supporting Schemas
# =============================================================================


class SwitchTriggerResponse(BaseModel):
    """Switch trigger response schema."""
    trigger_type: str = Field(..., description="Type of trigger that initiated the switch")
    reason: str = Field(..., description="Human-readable reason for the switch")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the trigger (0.0-1.0)"
    )
    source_mode: str = Field(..., description="Source execution mode")
    target_mode: str = Field(..., description="Target execution mode")
    detected_at: datetime = Field(..., description="When the trigger was detected")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional trigger metadata")


class MigratedStateResponse(BaseModel):
    """Migrated state response schema."""
    source_mode: str = Field(..., description="Original execution mode")
    target_mode: str = Field(..., description="Target execution mode")
    status: str = Field(..., description="Migration status")
    migrated_at: datetime = Field(..., description="When migration occurred")
    conversation_history_count: int = Field(0, description="Number of conversation messages migrated")
    tool_call_count: int = Field(0, description="Number of tool calls migrated")
    context_summary: str = Field("", description="Summary of migrated context")
    warnings: List[str] = Field(default_factory=list, description="Migration warnings")


class SwitchCheckpointResponse(BaseModel):
    """Switch checkpoint response schema."""
    checkpoint_id: str = Field(..., description="Unique checkpoint identifier")
    session_id: str = Field(..., description="Session identifier")
    source_mode: str = Field(..., description="Mode before switch")
    target_mode: str = Field(..., description="Mode after switch")
    created_at: datetime = Field(..., description="When checkpoint was created")
    execution_state: Dict[str, Any] = Field(default_factory=dict, description="Captured execution state")


class ModeTransitionResponse(BaseModel):
    """Mode transition response schema."""
    transition_id: str = Field(..., description="Unique transition identifier")
    session_id: str = Field(..., description="Session identifier")
    source_mode: str = Field(..., description="Source execution mode")
    target_mode: str = Field(..., description="Target execution mode")
    status: str = Field(..., description="Transition status")
    trigger: SwitchTriggerResponse = Field(..., description="Trigger that initiated the transition")
    checkpoint_id: Optional[str] = Field(None, description="Associated checkpoint ID")
    started_at: datetime = Field(..., description="When transition started")
    completed_at: Optional[datetime] = Field(None, description="When transition completed")
    duration_ms: int = Field(0, description="Transition duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")


# =============================================================================
# Switch Result Schemas
# =============================================================================


class SwitchResultResponse(BaseModel):
    """Switch result response schema."""
    success: bool = Field(..., description="Whether the switch was successful")
    session_id: str = Field(..., description="Session identifier")
    source_mode: str = Field(..., description="Source execution mode")
    target_mode: str = Field(..., description="Target execution mode")
    status: str = Field(..., description="Switch status")
    trigger: SwitchTriggerResponse = Field(..., description="Trigger that initiated the switch")
    migrated_state: Optional[MigratedStateResponse] = Field(
        None,
        description="Migrated state details"
    )
    checkpoint: Optional[SwitchCheckpointResponse] = Field(
        None,
        description="Checkpoint for potential rollback"
    )
    started_at: datetime = Field(..., description="When switch started")
    completed_at: Optional[datetime] = Field(None, description="When switch completed")
    duration_ms: int = Field(0, description="Switch duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")
    can_rollback: bool = Field(True, description="Whether rollback is available")


class SwitchStatusResponse(BaseModel):
    """Switch status response schema."""
    session_id: str = Field(..., description="Session identifier")
    current_mode: str = Field(..., description="Current execution mode")
    last_switch: Optional[ModeTransitionResponse] = Field(
        None,
        description="Last mode switch details"
    )
    pending_switch: Optional[Dict[str, Any]] = Field(
        None,
        description="Pending switch if in progress"
    )
    switch_history: List[ModeTransitionResponse] = Field(
        default_factory=list,
        description="Recent switch history"
    )
    can_switch: bool = Field(True, description="Whether switch is currently allowed")
    available_checkpoints: int = Field(0, description="Number of available rollback checkpoints")


class RollbackResultResponse(BaseModel):
    """Rollback result response schema."""
    success: bool = Field(..., description="Whether rollback was successful")
    session_id: str = Field(..., description="Session identifier")
    rolled_back_from: str = Field(..., description="Mode rolled back from")
    rolled_back_to: str = Field(..., description="Mode rolled back to")
    checkpoint_id: str = Field(..., description="Checkpoint used for rollback")
    restored_state: Optional[Dict[str, Any]] = Field(
        None,
        description="Restored state details"
    )
    completed_at: datetime = Field(..., description="When rollback completed")
    error: Optional[str] = Field(None, description="Error message if failed")


# =============================================================================
# Request Schemas
# =============================================================================


class SwitchRequest(BaseModel):
    """Request to trigger manual mode switch."""
    session_id: str = Field(..., description="Session identifier to switch")
    target_mode: Literal["workflow", "chat", "hybrid"] = Field(
        ...,
        description="Target execution mode: workflow, chat, or hybrid"
    )
    reason: str = Field(
        default="Manual switch request",
        max_length=500,
        description="Reason for the switch"
    )
    preserve_state: bool = Field(
        default=True,
        description="Whether to preserve and migrate state"
    )
    create_checkpoint: bool = Field(
        default=True,
        description="Whether to create a checkpoint for rollback"
    )
    force: bool = Field(
        default=False,
        description="Force switch even if conditions not ideal"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the switch"
    )


class RollbackRequest(BaseModel):
    """Request to rollback a mode switch."""
    session_id: str = Field(..., description="Session identifier to rollback")
    checkpoint_id: Optional[str] = Field(
        None,
        description="Specific checkpoint ID to rollback to. If not provided, uses latest."
    )
    reason: str = Field(
        default="Manual rollback request",
        max_length=500,
        description="Reason for the rollback"
    )


class SwitchStatusRequest(BaseModel):
    """Request to query switch status."""
    session_id: str = Field(..., description="Session identifier")
    include_history: bool = Field(
        default=True,
        description="Whether to include switch history"
    )
    history_limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of history items to return"
    )


# =============================================================================
# List Response Schemas
# =============================================================================


class SwitchHistoryResponse(BaseModel):
    """Switch history response."""
    session_id: str = Field(..., description="Session identifier")
    transitions: List[ModeTransitionResponse] = Field(
        default_factory=list,
        description="List of mode transitions"
    )
    total: int = Field(0, description="Total number of transitions")
    page: int = Field(1, description="Current page")
    page_size: int = Field(20, description="Page size")
