# =============================================================================
# IPA Platform - AG-UI API Schemas
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
# Sprint 59: AG-UI Basic Features
# S59-3: Human-in-the-Loop Approval Schemas
# Sprint 60: AG-UI Advanced Features
# S60-2: Shared State Management Schemas
#
# Request/Response schemas for AG-UI protocol API.
# Follows CopilotKit AG-UI protocol specification.
#
# Dependencies:
#   - Pydantic (pydantic)
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AGUIExecutionMode(str, Enum):
    """AG-UI execution mode."""
    WORKFLOW = "workflow"
    CHAT = "chat"
    HYBRID = "hybrid"
    AUTO = "auto"


class AGUIToolDefinition(BaseModel):
    """Tool definition for AG-UI request."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "search",
                "description": "Search for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            }
        }


class AGUIMessage(BaseModel):
    """Message in AG-UI format."""
    id: Optional[str] = Field(None, description="Message ID")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls in message")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg-123",
                "role": "user",
                "content": "Hello, how can you help me?",
            }
        }


class AGUIAttachment(BaseModel):
    """
    Attachment in AG-UI format.

    Sprint 75: S75-5 - File Attachment Support
    """
    file_id: str = Field(..., description="File ID from upload")
    type: str = Field("file", description="Attachment type")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file-abc123",
                "type": "file",
            }
        }


class RunAgentRequest(BaseModel):
    """
    AG-UI Run Agent Request.

    Follows the CopilotKit AG-UI protocol specification for running
    an agent with streaming response.
    """
    thread_id: str = Field(..., description="Thread ID for conversation context")
    run_id: Optional[str] = Field(None, description="Optional run ID (generated if not provided)")
    messages: List[AGUIMessage] = Field(default_factory=list, description="Conversation messages")
    tools: Optional[List[AGUIToolDefinition]] = Field(None, description="Available tools")

    # S75-5: File attachments
    attachments: Optional[List[AGUIAttachment]] = Field(None, description="File attachments")

    # Execution options
    mode: AGUIExecutionMode = Field(
        AGUIExecutionMode.AUTO,
        description="Execution mode (auto detects best mode)"
    )
    max_tokens: Optional[int] = Field(None, ge=1, le=100000, description="Maximum tokens for response")
    timeout: Optional[float] = Field(None, ge=1, le=600, description="Execution timeout in seconds")

    # Session context
    session_id: Optional[str] = Field(None, description="Optional session ID for persistence")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread-abc123",
                "messages": [
                    {"role": "user", "content": "Help me analyze this data"},
                ],
                "mode": "auto",
                "max_tokens": 2000,
            }
        }


class RunAgentResponse(BaseModel):
    """
    AG-UI Run Agent Response (for non-streaming mode).

    Only used when streaming is not supported or disabled.
    Normally the response is streamed via SSE.
    """
    thread_id: str
    run_id: str
    status: str = Field(..., description="Execution status (success, error)")
    content: str = Field("", description="Generated content")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread-abc123",
                "run_id": "run-xyz789",
                "status": "success",
                "content": "Here is my analysis...",
                "tool_calls": [],
                "created_at": "2026-01-05T10:00:00Z",
            }
        }


class HealthResponse(BaseModel):
    """Health check response for AG-UI endpoint."""
    status: str = Field("healthy", description="Service status")
    version: str = Field("1.0.0", description="AG-UI protocol version")
    protocol: str = Field("ag-ui", description="Protocol name")
    features: List[str] = Field(
        default_factory=lambda: ["streaming", "tool_calls", "hybrid_mode"],
        description="Supported features"
    )


class ErrorResponse(BaseModel):
    """Error response for AG-UI endpoint."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "INVALID_REQUEST",
                "message": "thread_id is required",
                "details": {"field": "thread_id"},
            }
        }


# =============================================================================
# S59-3: Human-in-the-Loop Approval Schemas
# =============================================================================

class ApprovalStatusEnum(str, Enum):
    """Approval status for pending tool calls."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RiskLevelEnum(str, Enum):
    """Risk level for tool operations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalActionRequest(BaseModel):
    """Request to approve or reject a tool call."""
    comment: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional comment from the approver",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "comment": "Approved after reviewing the command",
            }
        }
    )


class ApprovalResponse(BaseModel):
    """Response for a single approval request."""
    approval_id: str = Field(..., description="Unique approval request ID")
    tool_call_id: str = Field(..., description="Associated tool call ID")
    tool_name: str = Field(..., description="Name of the tool being called")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    risk_level: RiskLevelEnum = Field(..., description="Assessed risk level")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score (0.0-1.0)")
    reasoning: str = Field(..., description="Reason for requiring approval")
    run_id: str = Field(..., description="Associated run ID")
    session_id: Optional[str] = Field(None, description="Optional session ID")
    status: ApprovalStatusEnum = Field(..., description="Current approval status")
    created_at: datetime = Field(..., description="Request creation time")
    expires_at: datetime = Field(..., description="Request expiration time")
    resolved_at: Optional[datetime] = Field(None, description="When the request was resolved")
    user_comment: Optional[str] = Field(None, description="Comment from the approver")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "approval_id": "approval-abc123def456",
                "tool_call_id": "tc-789xyz",
                "tool_name": "Bash",
                "arguments": {"command": "rm -rf /tmp/test"},
                "risk_level": "high",
                "risk_score": 0.75,
                "reasoning": "High-risk shell command with destructive potential",
                "run_id": "run-abc123",
                "session_id": "session-xyz789",
                "status": "pending",
                "created_at": "2026-01-05T10:00:00Z",
                "expires_at": "2026-01-05T10:05:00Z",
                "resolved_at": None,
                "user_comment": None,
            }
        }
    )


class ApprovalActionResponse(BaseModel):
    """Response after approval action (approve/reject)."""
    success: bool = Field(..., description="Whether the action was successful")
    approval_id: str = Field(..., description="Approval request ID")
    status: ApprovalStatusEnum = Field(..., description="New approval status")
    message: str = Field(..., description="Action result message")
    resolved_at: Optional[datetime] = Field(None, description="When the request was resolved")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "approval_id": "approval-abc123def456",
                "status": "approved",
                "message": "Tool call approved successfully",
                "resolved_at": "2026-01-05T10:02:30Z",
            }
        }
    )


class PendingApprovalsResponse(BaseModel):
    """Response listing pending approvals."""
    pending: List[ApprovalResponse] = Field(
        default_factory=list,
        description="List of pending approval requests",
    )
    total: int = Field(0, description="Total count of pending approvals")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pending": [],
                "total": 0,
            }
        }
    )


class ApprovalStorageStats(BaseModel):
    """Statistics for approval storage."""
    total: int = Field(0, description="Total requests in storage")
    pending: int = Field(0, description="Pending requests")
    approved: int = Field(0, description="Approved requests")
    rejected: int = Field(0, description="Rejected requests")
    timeout: int = Field(0, description="Timed out requests")
    cancelled: int = Field(0, description="Cancelled requests")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 10,
                "pending": 2,
                "approved": 5,
                "rejected": 2,
                "timeout": 1,
                "cancelled": 0,
            }
        }
    )


# =============================================================================
# S60-2: Shared State Management Schemas
# =============================================================================

class DiffOperationEnum(str, Enum):
    """Type of diff operation."""
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"


class ConflictResolutionStrategyEnum(str, Enum):
    """Strategy for resolving state conflicts."""
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"
    MANUAL = "manual"


class StateDiffSchema(BaseModel):
    """Schema for a single state diff operation."""
    path: str = Field(..., description="JSON path to the changed value")
    op: DiffOperationEnum = Field(..., description="Type of diff operation")
    old_value: Optional[Any] = Field(None, alias="oldValue", description="Previous value")
    new_value: Optional[Any] = Field(None, alias="newValue", description="New value")
    timestamp: Optional[float] = Field(None, description="When the diff was created")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "path": "user.profile.name",
                "op": "replace",
                "oldValue": "John",
                "newValue": "Jane",
                "timestamp": 1704456000.0,
            }
        }
    )


class ThreadStateResponse(BaseModel):
    """Response for thread state retrieval."""
    thread_id: str = Field(..., description="Thread ID")
    state: Dict[str, Any] = Field(default_factory=dict, description="Current state data")
    version: int = Field(..., description="State version number")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "thread_id": "thread-abc123",
                "state": {
                    "user": {"name": "John", "role": "admin"},
                    "context": {"step": 3, "total": 10},
                },
                "version": 5,
                "last_modified": "2026-01-05T10:00:00Z",
                "metadata": {"source": "backend"},
            }
        }
    )


class ThreadStateUpdateRequest(BaseModel):
    """Request to update thread state."""
    state: Optional[Dict[str, Any]] = Field(
        None,
        description="Full state to replace (for snapshot update)"
    )
    diffs: Optional[List[StateDiffSchema]] = Field(
        None,
        description="List of state diffs to apply (for delta update)"
    )
    expected_version: Optional[int] = Field(
        None,
        description="Expected current version for optimistic locking"
    )
    conflict_resolution: ConflictResolutionStrategyEnum = Field(
        ConflictResolutionStrategyEnum.SERVER_WINS,
        description="How to resolve conflicts"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "diffs": [
                    {"path": "user.name", "op": "replace", "newValue": "Jane"},
                    {"path": "context.step", "op": "replace", "newValue": 4},
                ],
                "expected_version": 5,
                "conflict_resolution": "server_wins",
            }
        }
    )


class StateUpdateResponse(BaseModel):
    """Response after state update."""
    success: bool = Field(..., description="Whether the update was successful")
    thread_id: str = Field(..., description="Thread ID")
    version: int = Field(..., description="New state version after update")
    conflicts_resolved: int = Field(0, description="Number of conflicts resolved")
    diffs_applied: int = Field(0, description="Number of diffs applied")
    message: str = Field("", description="Status message")
    updated_at: datetime = Field(..., description="Update timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "thread_id": "thread-abc123",
                "version": 6,
                "conflicts_resolved": 0,
                "diffs_applied": 2,
                "message": "State updated successfully",
                "updated_at": "2026-01-05T10:05:00Z",
            }
        }
    )


class StateConflictResponse(BaseModel):
    """Response when state conflict is detected."""
    has_conflict: bool = Field(..., description="Whether a conflict exists")
    conflict_paths: List[str] = Field(
        default_factory=list,
        description="Paths where conflicts were detected"
    )
    server_version: int = Field(..., description="Current server version")
    client_version: int = Field(..., description="Client's expected version")
    resolution_required: bool = Field(
        False,
        description="Whether manual resolution is required"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "has_conflict": True,
                "conflict_paths": ["user.name", "context.step"],
                "server_version": 7,
                "client_version": 5,
                "resolution_required": True,
            }
        }
    )


# =============================================================================
# S61-6: Test Endpoints for Feature 4 & 5
# =============================================================================

class WorkflowStepStatusEnum(str, Enum):
    """Status for workflow step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TestWorkflowProgressRequest(BaseModel):
    """Request to generate test workflow progress event."""
    thread_id: str = Field(..., description="Thread ID")
    workflow_name: str = Field("Test Workflow", description="Workflow name")
    total_steps: int = Field(3, ge=1, le=20, description="Total number of steps")
    current_step: int = Field(1, ge=1, description="Current step number")
    step_status: WorkflowStepStatusEnum = Field(
        WorkflowStepStatusEnum.IN_PROGRESS,
        description="Status of current step"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "thread_id": "test-123",
                "workflow_name": "Data Processing",
                "total_steps": 5,
                "current_step": 2,
                "step_status": "in_progress",
            }
        }
    )


class TestModeSwitchRequest(BaseModel):
    """Request to generate test mode switch event."""
    thread_id: str = Field(..., description="Thread ID")
    source_mode: str = Field("chat", description="Source execution mode")
    target_mode: str = Field("workflow", description="Target execution mode")
    reason: str = Field("complexity", description="Reason for mode switch")
    confidence: float = Field(0.9, ge=0.0, le=1.0, description="Confidence score")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "thread_id": "test-123",
                "source_mode": "chat",
                "target_mode": "workflow",
                "reason": "Multi-step task detected",
                "confidence": 0.95,
            }
        }
    )


class UIComponentTypeEnum(str, Enum):
    """Type of UI component."""
    FORM = "form"
    CHART = "chart"
    CARD = "card"
    TABLE = "table"
    CUSTOM = "custom"


class TestUIComponentRequest(BaseModel):
    """Request to generate test UI component event."""
    thread_id: str = Field(..., description="Thread ID")
    component_type: UIComponentTypeEnum = Field(..., description="Type of UI component")
    props: Dict[str, Any] = Field(..., description="Component properties")
    title: Optional[str] = Field(None, description="Component title")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "thread_id": "test-123",
                "component_type": "form",
                "props": {
                    "fields": [
                        {"name": "email", "label": "Email", "type": "email", "required": True}
                    ],
                    "submitLabel": "Submit",
                },
                "title": "Contact Form",
            }
        }
    )


class WorkflowProgressEventResponse(BaseModel):
    """Response containing workflow progress event data."""
    event_name: str = Field("workflow_progress", description="Event name")
    payload: Dict[str, Any] = Field(..., description="Event payload")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_name": "workflow_progress",
                "payload": {
                    "workflow_id": "wf-abc123",
                    "workflow_name": "Data Processing",
                    "total_steps": 5,
                    "completed_steps": 1,
                    "current_step": {"step_id": "step-2", "name": "Process Data", "status": "in_progress"},
                    "overall_progress": 0.3,
                },
            }
        }
    )


class ModeSwitchEventResponse(BaseModel):
    """Response containing mode switch event data."""
    event_name: str = Field("mode_switch", description="Event name")
    payload: Dict[str, Any] = Field(..., description="Event payload")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_name": "mode_switch",
                "payload": {
                    "switch_id": "sw-abc123",
                    "source_mode": "chat",
                    "target_mode": "workflow",
                    "reason": "Multi-step task detected",
                    "confidence": 0.95,
                    "success": True,
                },
            }
        }
    )


class UIComponentEventResponse(BaseModel):
    """Response containing UI component event data."""
    event_name: str = Field("ui_component", description="Event name")
    component: Dict[str, Any] = Field(..., description="Component definition")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_name": "ui_component",
                "component": {
                    "componentId": "ui-abc123",
                    "componentType": "form",
                    "props": {"fields": [{"name": "email", "label": "Email"}]},
                    "title": "Contact Form",
                },
            }
        }
    )
