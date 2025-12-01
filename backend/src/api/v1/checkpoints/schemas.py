# =============================================================================
# IPA Platform - Checkpoint API Schemas
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Pydantic schemas for Checkpoint API endpoints.
# Provides request/response validation for checkpoint operations including:
#   - CheckpointResponse: Checkpoint data response
#   - CheckpointListResponse: Paginated list of checkpoints
#   - ApprovalRequest: Request to approve a checkpoint
#   - RejectionRequest: Request to reject a checkpoint
#   - CheckpointStatsResponse: Checkpoint statistics
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CheckpointResponse(BaseModel):
    """
    Checkpoint response schema.

    Full checkpoint information including status and response data.
    """

    id: UUID = Field(..., description="Checkpoint UUID")
    execution_id: UUID = Field(..., description="Parent execution UUID")
    node_id: str = Field(..., description="Workflow node ID")
    status: str = Field(..., description="Checkpoint status (pending, approved, rejected, expired)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Data to review")
    response: Optional[Dict[str, Any]] = Field(None, description="Human response data")
    responded_by: Optional[UUID] = Field(None, description="User who responded")
    responded_at: Optional[datetime] = Field(None, description="When response was received")
    expires_at: Optional[datetime] = Field(None, description="When checkpoint expires")
    created_at: Optional[datetime] = Field(None, description="When checkpoint was created")
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        from_attributes = True


class CheckpointSummaryResponse(BaseModel):
    """
    Summary checkpoint response for list endpoints.

    Lighter weight than full checkpoint response.
    """

    id: UUID = Field(..., description="Checkpoint UUID")
    execution_id: UUID = Field(..., description="Parent execution UUID")
    node_id: str = Field(..., description="Workflow node ID")
    status: str = Field(..., description="Checkpoint status")
    created_at: Optional[datetime] = Field(None, description="When checkpoint was created")
    expires_at: Optional[datetime] = Field(None, description="When checkpoint expires")

    class Config:
        from_attributes = True


class CheckpointListResponse(BaseModel):
    """
    Paginated list of checkpoints response.
    """

    items: List[CheckpointResponse] = Field(..., description="List of checkpoints")
    total: int = Field(..., description="Total number of records")


class PendingCheckpointsResponse(BaseModel):
    """
    List of pending checkpoints awaiting approval.
    """

    items: List[CheckpointResponse] = Field(..., description="List of pending checkpoints")
    count: int = Field(..., description="Number of pending checkpoints")


class ApprovalRequest(BaseModel):
    """
    Request schema for approving a checkpoint.
    """

    user_id: UUID = Field(..., description="ID of user approving the checkpoint")
    response: Optional[Dict[str, Any]] = Field(
        None, description="Optional response data (e.g., modifications)"
    )
    feedback: Optional[str] = Field(
        None, description="Optional feedback text"
    )


class RejectionRequest(BaseModel):
    """
    Request schema for rejecting a checkpoint.
    """

    user_id: UUID = Field(..., description="ID of user rejecting the checkpoint")
    reason: Optional[str] = Field(
        None, description="Reason for rejection"
    )
    response: Optional[Dict[str, Any]] = Field(
        None, description="Optional additional response data"
    )


class CheckpointCreateRequest(BaseModel):
    """
    Request schema for creating a checkpoint.
    """

    execution_id: UUID = Field(..., description="Parent execution UUID")
    node_id: str = Field(..., description="Workflow node ID")
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Data to be reviewed"
    )
    timeout_hours: Optional[int] = Field(
        None, description="Hours until checkpoint expires"
    )
    notes: Optional[str] = Field(
        None, description="Optional notes or context"
    )


class CheckpointActionResponse(BaseModel):
    """
    Response for checkpoint approval/rejection actions.
    """

    id: UUID = Field(..., description="Checkpoint UUID")
    status: str = Field(..., description="New checkpoint status")
    message: str = Field(..., description="Action result message")
    responded_at: datetime = Field(..., description="When action was taken")


class CheckpointStatsResponse(BaseModel):
    """
    Checkpoint statistics response.
    """

    pending: int = Field(0, description="Number of pending checkpoints")
    approved: int = Field(0, description="Number of approved checkpoints")
    rejected: int = Field(0, description="Number of rejected checkpoints")
    expired: int = Field(0, description="Number of expired checkpoints")
    total: int = Field(0, description="Total checkpoints")
    avg_response_seconds: float = Field(
        0.0, description="Average response time in seconds"
    )
