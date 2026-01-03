# =============================================================================
# IPA Platform - Hybrid Context API Schemas
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Pydantic schemas for hybrid context API request/response validation.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums (matching domain models)
# =============================================================================


class SyncStatusSchema(str):
    """Sync status values."""
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    SYNCING = "syncing"
    FAILED = "failed"


class SyncDirectionSchema(str):
    """Sync direction values."""
    MAF_TO_CLAUDE = "maf_to_claude"
    CLAUDE_TO_MAF = "claude_to_maf"
    BIDIRECTIONAL = "bidirectional"


class SyncStrategySchema(str):
    """Sync strategy values."""
    MERGE = "merge"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    MANUAL = "manual"
    MAF_PRIMARY = "maf_primary"
    CLAUDE_PRIMARY = "claude_primary"


# =============================================================================
# Supporting Schemas
# =============================================================================


class AgentStateResponse(BaseModel):
    """Agent state response schema."""
    agent_id: str
    agent_name: str
    status: str
    current_task: Optional[str] = None
    last_output: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class MessageResponse(BaseModel):
    """Message response schema."""
    message_id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    """Tool call response schema."""
    call_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    status: str
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0


class ApprovalRequestResponse(BaseModel):
    """Approval request response schema."""
    request_id: str
    checkpoint_id: str
    action: str
    description: str
    status: str
    requested_by: Optional[str] = None
    requested_at: datetime
    responded_at: Optional[datetime] = None
    timeout_seconds: int = 3600


class ExecutionRecordResponse(BaseModel):
    """Execution record response schema."""
    record_id: str
    step_index: int
    step_name: str
    agent_id: str
    status: str
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0


# =============================================================================
# Context Schemas
# =============================================================================


class MAFContextResponse(BaseModel):
    """MAF context response schema."""
    workflow_id: str
    workflow_name: str
    current_step: int = 0
    total_steps: int = 0
    agent_states: Dict[str, AgentStateResponse] = Field(default_factory=dict)
    checkpoint_data: Dict[str, Any] = Field(default_factory=dict)
    pending_approvals: List[ApprovalRequestResponse] = Field(default_factory=list)
    execution_history: List[ExecutionRecordResponse] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_updated: datetime


class ClaudeContextResponse(BaseModel):
    """Claude context response schema."""
    session_id: str
    message_count: int = 0
    tool_call_count: int = 0
    current_system_prompt: str = ""
    context_variables: Dict[str, Any] = Field(default_factory=dict)
    active_hooks: List[str] = Field(default_factory=list)
    mcp_server_states: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_updated: datetime


class HybridContextResponse(BaseModel):
    """Hybrid context response schema."""
    context_id: str
    maf: Optional[MAFContextResponse] = None
    claude: Optional[ClaudeContextResponse] = None
    primary_framework: str = "maf"
    sync_status: str = "pending"
    version: int = 1
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None


class ConflictResponse(BaseModel):
    """Conflict response schema."""
    conflict_id: str
    field_path: str
    local_value: Any = None
    remote_value: Any = None
    local_timestamp: Optional[datetime] = None
    remote_timestamp: Optional[datetime] = None
    resolution: Optional[str] = None
    resolved: bool = False


class SyncResultResponse(BaseModel):
    """Sync result response schema."""
    success: bool
    direction: str
    strategy: str
    source_version: int
    target_version: int
    changes_applied: int = 0
    conflicts_resolved: int = 0
    conflicts: List[ConflictResponse] = Field(default_factory=list)
    hybrid_context: Optional[HybridContextResponse] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0


# =============================================================================
# Request Schemas
# =============================================================================


class SyncRequest(BaseModel):
    """Request to trigger sync operation."""
    session_id: str = Field(..., description="Session or workflow ID")
    strategy: str = Field(
        default="merge",
        description="Sync strategy: merge, source_wins, target_wins, maf_primary, claude_primary, manual"
    )
    direction: str = Field(
        default="bidirectional",
        description="Sync direction: maf_to_claude, claude_to_maf, bidirectional"
    )
    force: bool = Field(
        default=False,
        description="Force sync even if no changes detected"
    )


class MergeContextRequest(BaseModel):
    """Request to merge MAF and Claude contexts."""
    maf_workflow_id: Optional[str] = Field(
        default=None,
        description="MAF workflow ID"
    )
    claude_session_id: Optional[str] = Field(
        default=None,
        description="Claude session ID"
    )
    primary_framework: str = Field(
        default="maf",
        description="Primary framework: maf or claude"
    )


# =============================================================================
# List Response Schemas
# =============================================================================


class HybridContextListResponse(BaseModel):
    """List of hybrid contexts response."""
    data: List[HybridContextResponse]
    total: int
    page: int = 1
    page_size: int = 20


class SyncHistoryResponse(BaseModel):
    """Sync history response."""
    session_id: str
    syncs: List[SyncResultResponse]
    total: int
