# =============================================================================
# IPA Platform - Execution API Schemas
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Pydantic schemas for Execution API endpoints.
# Provides request/response validation for execution operations.
# =============================================================================

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExecutionBase(BaseModel):
    """Base schema for execution data."""

    workflow_id: UUID = Field(..., description="ID of the workflow being executed")


class ExecutionDetailResponse(BaseModel):
    """
    Detailed execution response schema.

    Includes full execution information with LLM statistics.
    """

    id: UUID = Field(..., description="Execution UUID")
    workflow_id: UUID = Field(..., description="Workflow UUID")
    status: str = Field(..., description="Execution status")
    started_at: Optional[datetime] = Field(None, description="When execution started")
    completed_at: Optional[datetime] = Field(None, description="When execution completed")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    llm_calls: int = Field(0, description="Total LLM API calls")
    llm_tokens: int = Field(0, description="Total tokens used")
    llm_cost: float = Field(0.0, description="Estimated cost in USD")
    triggered_by: Optional[UUID] = Field(None, description="User who triggered")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Input data")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    created_at: datetime = Field(..., description="Record creation time")
    updated_at: datetime = Field(..., description="Record update time")

    class Config:
        from_attributes = True


class ExecutionSummaryResponse(BaseModel):
    """
    Summary execution response for list endpoints.

    Lighter weight than detail response.
    """

    id: UUID = Field(..., description="Execution UUID")
    workflow_id: UUID = Field(..., description="Workflow UUID")
    status: str = Field(..., description="Execution status")
    started_at: Optional[datetime] = Field(None, description="When execution started")
    completed_at: Optional[datetime] = Field(None, description="When execution completed")
    llm_calls: int = Field(0, description="Total LLM API calls")
    llm_tokens: int = Field(0, description="Total tokens used")
    llm_cost: float = Field(0.0, description="Estimated cost in USD")
    created_at: datetime = Field(..., description="Record creation time")

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """
    Paginated list of executions response.
    """

    items: List[ExecutionSummaryResponse] = Field(
        ..., description="List of executions"
    )
    total: int = Field(..., description="Total number of records")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Records per page")
    pages: int = Field(..., description="Total number of pages")


class ExecutionStatsResponse(BaseModel):
    """
    Execution statistics response.
    """

    total_executions: int = Field(0, description="Total number of executions")
    total_llm_calls: int = Field(0, description="Total LLM API calls")
    total_llm_tokens: int = Field(0, description="Total tokens used")
    total_llm_cost: float = Field(0.0, description="Total estimated cost in USD")
    avg_duration_seconds: float = Field(0.0, description="Average execution duration")


class ExecutionCancelResponse(BaseModel):
    """
    Response for execution cancellation.
    """

    id: UUID = Field(..., description="Execution UUID")
    status: str = Field(..., description="New execution status")
    message: str = Field(..., description="Cancellation message")


class ValidTransitionsResponse(BaseModel):
    """
    Response showing valid state transitions.
    """

    current_status: str = Field(..., description="Current execution status")
    valid_transitions: List[str] = Field(
        ..., description="List of valid target statuses"
    )
    is_terminal: bool = Field(..., description="Whether status is terminal")


# =============================================================================
# Sprint 2: Resume Schemas
# =============================================================================


class ResumeRequest(BaseModel):
    """
    Request for resuming a paused execution.
    """

    user_id: UUID = Field(..., description="User approving the resume")
    checkpoint_id: Optional[UUID] = Field(
        None, description="Specific checkpoint to resume from"
    )
    response: Optional[Dict[str, Any]] = Field(
        None, description="Optional response data for approval"
    )


class ResumeResponse(BaseModel):
    """
    Response for execution resume.
    """

    status: str = Field(..., description="Resume operation status")
    execution_id: UUID = Field(..., description="Execution UUID")
    checkpoint_id: Optional[UUID] = Field(None, description="Checkpoint UUID")
    message: str = Field(..., description="Result message")
    resumed_at: Optional[datetime] = Field(None, description="When resumed")
    next_node_id: Optional[str] = Field(None, description="Next node to execute")


class ResumeStatusResponse(BaseModel):
    """
    Response showing resume status for an execution.
    """

    can_resume: bool = Field(..., description="Whether execution can be resumed")
    reason: str = Field(..., description="Reason for resume status")
    current_status: Optional[str] = Field(None, description="Current execution status")
    pending_count: int = Field(0, description="Number of pending checkpoints")
    approved_count: int = Field(0, description="Number of approved checkpoints")
    pending_checkpoints: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of pending checkpoints"
    )
