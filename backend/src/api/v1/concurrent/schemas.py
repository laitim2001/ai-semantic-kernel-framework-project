# =============================================================================
# IPA Platform - Concurrent Execution API Schemas
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Pydantic schemas for Concurrent Execution API endpoints.
# Provides request/response validation for:
#   - Concurrent execution requests
#   - Branch status monitoring
#   - Statistics reporting
#   - WebSocket message formats
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class ConcurrentModeEnum(str, Enum):
    """Concurrent execution mode options for API requests."""

    ALL = "all"
    ANY = "any"
    MAJORITY = "majority"
    FIRST_SUCCESS = "first_success"


class BranchStatusEnum(str, Enum):
    """Branch execution status for API responses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ExecutionStatusEnum(str, Enum):
    """Overall concurrent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


# =============================================================================
# Request Schemas
# =============================================================================


class ConcurrentExecuteRequest(BaseModel):
    """
    Request schema for concurrent task execution.

    Supports multiple execution modes:
    - all: Wait for all branches to complete
    - any: Return when any branch completes
    - majority: Wait for majority of branches
    - first_success: Return on first successful branch
    """

    workflow_id: UUID = Field(..., description="ID of the workflow to execute")
    inputs: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Input data for the execution"
    )
    mode: ConcurrentModeEnum = Field(
        ConcurrentModeEnum.ALL, description="Execution mode"
    )
    timeout_seconds: Optional[int] = Field(
        300, ge=1, le=3600, description="Global timeout in seconds (1-3600)"
    )
    max_concurrency: Optional[int] = Field(
        10, ge=1, le=100, description="Maximum concurrent branches (1-100)"
    )
    branch_timeout_seconds: Optional[int] = Field(
        None, ge=1, le=3600, description="Per-branch timeout in seconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "inputs": {"query": "process this data"},
                "mode": "all",
                "timeout_seconds": 300,
                "max_concurrency": 5,
            }
        }


class BranchCancelRequest(BaseModel):
    """Request schema for cancelling a specific branch."""

    reason: Optional[str] = Field(None, description="Reason for cancellation")


class ExecutionCancelRequest(BaseModel):
    """Request schema for cancelling an entire execution."""

    reason: Optional[str] = Field(None, description="Reason for cancellation")
    force: bool = Field(False, description="Force cancel even if branches are running")


# =============================================================================
# Response Schemas
# =============================================================================


class BranchInfo(BaseModel):
    """Information about a single execution branch."""

    branch_id: str = Field(..., description="Unique branch identifier")
    status: BranchStatusEnum = Field(..., description="Branch status")
    started_at: Optional[datetime] = Field(None, description="Branch start time")
    completed_at: Optional[datetime] = Field(None, description="Branch completion time")
    duration_ms: Optional[float] = Field(None, description="Execution duration in ms")
    result: Optional[Dict[str, Any]] = Field(None, description="Branch result data")
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        from_attributes = True


class ConcurrentExecuteResponse(BaseModel):
    """
    Response schema for concurrent execution request.

    Returns execution ID and initial branch information.
    """

    execution_id: UUID = Field(..., description="Unique execution identifier")
    status: ExecutionStatusEnum = Field(..., description="Execution status")
    mode: ConcurrentModeEnum = Field(..., description="Execution mode")
    branches: List[BranchInfo] = Field(
        default_factory=list, description="List of execution branches"
    )
    created_at: datetime = Field(..., description="Execution creation time")
    timeout_seconds: int = Field(..., description="Configured timeout")
    message: str = Field(..., description="Status message")

    class Config:
        from_attributes = True


class BranchStatusResponse(BaseModel):
    """Response schema for branch status query."""

    execution_id: UUID = Field(..., description="Parent execution ID")
    branch_id: str = Field(..., description="Branch identifier")
    status: BranchStatusEnum = Field(..., description="Branch status")
    progress: Optional[float] = Field(
        None, ge=0, le=100, description="Progress percentage (0-100)"
    )
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    result: Optional[Dict[str, Any]] = Field(None, description="Branch result")
    error: Optional[str] = Field(None, description="Error if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ExecutionStatusResponse(BaseModel):
    """Response schema for execution status query."""

    execution_id: UUID = Field(..., description="Execution identifier")
    workflow_id: UUID = Field(..., description="Workflow identifier")
    status: ExecutionStatusEnum = Field(..., description="Overall status")
    mode: ConcurrentModeEnum = Field(..., description="Execution mode")
    progress: float = Field(0.0, ge=0, le=100, description="Overall progress")
    total_branches: int = Field(0, description="Total number of branches")
    completed_branches: int = Field(0, description="Completed branches count")
    failed_branches: int = Field(0, description="Failed branches count")
    running_branches: int = Field(0, description="Running branches count")
    branches: List[BranchInfo] = Field(
        default_factory=list, description="Branch details"
    )
    started_at: Optional[datetime] = Field(None, description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration_seconds: Optional[float] = Field(None, description="Total duration")
    result: Optional[Dict[str, Any]] = Field(None, description="Merged result")
    error: Optional[str] = Field(None, description="Error message if failed")


class BranchListResponse(BaseModel):
    """Response schema for listing all branches of an execution."""

    execution_id: UUID = Field(..., description="Execution identifier")
    branches: List[BranchInfo] = Field(..., description="List of all branches")
    total: int = Field(..., description="Total branch count")
    completed: int = Field(..., description="Completed branch count")
    running: int = Field(..., description="Running branch count")
    failed: int = Field(..., description="Failed branch count")


class ExecutionCancelResponse(BaseModel):
    """Response schema for execution cancellation."""

    execution_id: UUID = Field(..., description="Execution identifier")
    status: ExecutionStatusEnum = Field(..., description="New status")
    cancelled_branches: List[str] = Field(
        default_factory=list, description="IDs of cancelled branches"
    )
    message: str = Field(..., description="Cancellation result message")


class BranchCancelResponse(BaseModel):
    """Response schema for branch cancellation."""

    execution_id: UUID = Field(..., description="Execution identifier")
    branch_id: str = Field(..., description="Branch identifier")
    status: BranchStatusEnum = Field(..., description="New branch status")
    message: str = Field(..., description="Cancellation result message")


class ConcurrentStatsResponse(BaseModel):
    """Response schema for concurrent execution statistics."""

    total_executions: int = Field(0, description="Total concurrent executions")
    active_executions: int = Field(0, description="Currently active executions")
    completed_executions: int = Field(0, description="Completed executions")
    failed_executions: int = Field(0, description="Failed executions")
    cancelled_executions: int = Field(0, description="Cancelled executions")
    total_branches: int = Field(0, description="Total branches executed")
    avg_branches_per_execution: float = Field(
        0.0, description="Average branches per execution"
    )
    avg_duration_seconds: float = Field(
        0.0, description="Average execution duration"
    )
    total_duration_seconds: float = Field(
        0.0, description="Total execution time"
    )
    mode_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Executions by mode"
    )
    success_rate: float = Field(0.0, ge=0, le=100, description="Success rate %")
    deadlocks_detected: int = Field(0, description="Total deadlocks detected")
    deadlocks_resolved: int = Field(0, description="Deadlocks successfully resolved")


# =============================================================================
# WebSocket Message Schemas
# =============================================================================


class WebSocketMessageType(str, Enum):
    """WebSocket message types for real-time updates."""

    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    BRANCH_STARTED = "branch_started"
    BRANCH_COMPLETED = "branch_completed"
    BRANCH_FAILED = "branch_failed"
    BRANCH_PROGRESS = "branch_progress"
    DEADLOCK_DETECTED = "deadlock_detected"
    DEADLOCK_RESOLVED = "deadlock_resolved"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """WebSocket message format for real-time updates."""

    type: WebSocketMessageType = Field(..., description="Message type")
    execution_id: UUID = Field(..., description="Execution identifier")
    branch_id: Optional[str] = Field(None, description="Branch identifier if applicable")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    data: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    message: Optional[str] = Field(None, description="Human-readable message")
