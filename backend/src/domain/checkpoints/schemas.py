"""
Checkpoint Schemas

Sprint 2 - Story S2-4: Teams Approval Flow

Pydantic models for checkpoint operations.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CheckpointCreate(BaseModel):
    """Schema for creating a checkpoint."""
    execution_id: UUID = Field(..., description="Execution ID")
    step_index: int = Field(..., ge=0, description="Step index in workflow")
    step_name: Optional[str] = Field(None, description="Step name")
    proposed_action: Optional[str] = Field(None, description="Proposed action description")
    context: Optional[dict[str, Any]] = Field(None, description="Additional context")
    expires_in_minutes: Optional[int] = Field(
        default=60,
        ge=1,
        le=10080,  # Max 1 week
        description="Minutes until approval expires"
    )


class CheckpointResponse(BaseModel):
    """Schema for checkpoint response."""
    id: UUID
    execution_id: UUID
    step_index: int
    step_name: Optional[str]
    status: str
    proposed_action: Optional[str]
    context: Optional[dict[str, Any]]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    feedback: Optional[str]
    expires_at: Optional[datetime]
    notification_sent: bool
    notification_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CheckpointApprovalRequest(BaseModel):
    """Schema for approving a checkpoint."""
    feedback: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional approval feedback"
    )


class CheckpointRejectionRequest(BaseModel):
    """Schema for rejecting a checkpoint."""
    reason: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Rejection reason (required)"
    )


class CheckpointListResponse(BaseModel):
    """Schema for checkpoint list response."""
    total: int
    checkpoints: list[CheckpointResponse]
    page: int
    page_size: int


class CheckpointSummary(BaseModel):
    """Schema for checkpoint summary in notifications."""
    checkpoint_id: str
    execution_id: str
    workflow_name: str
    step_number: int
    step_name: Optional[str]
    proposed_action: Optional[str]
    approve_url: str
    reject_url: str
    expires_at: Optional[datetime]
