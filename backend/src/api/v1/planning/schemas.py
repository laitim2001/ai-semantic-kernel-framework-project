# =============================================================================
# IPA Platform - Planning API Schemas
# =============================================================================
# Sprint 10: S10-5 Planning API (5 points)
#
# Pydantic schemas for Planning API endpoints including task decomposition,
# dynamic planning, decision-making, and trial-and-error execution.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Task Decomposition Schemas
# =============================================================================


class DecomposeTaskRequest(BaseModel):
    """Request to decompose a task into subtasks."""
    task_description: str = Field(..., description="Task description to decompose")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    strategy: str = Field(
        default="hybrid",
        description="Decomposition strategy: hierarchical, sequential, parallel, hybrid"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_description": "Implement user authentication system",
                "context": {"framework": "FastAPI", "database": "PostgreSQL"},
                "strategy": "hybrid"
            }
        }
    }


class SubTaskResponse(BaseModel):
    """Response for a single subtask."""
    id: str
    name: str
    description: str
    priority: str
    status: str
    dependencies: List[str]
    estimated_duration_minutes: int
    assigned_agent_id: Optional[str] = None


class DecompositionResponse(BaseModel):
    """Response for task decomposition."""
    task_id: str
    original_task: str
    subtasks: List[SubTaskResponse]
    execution_order: List[List[str]]
    estimated_total_duration: int
    confidence_score: float
    strategy: str


class RefineDecompositionRequest(BaseModel):
    """Request to refine a decomposition based on feedback."""
    feedback: str = Field(..., description="Improvement feedback")


# =============================================================================
# Dynamic Planning Schemas
# =============================================================================


class CreatePlanRequest(BaseModel):
    """Request to create an execution plan."""
    goal: str = Field(..., description="Goal description")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    deadline: Optional[datetime] = Field(None, description="Optional deadline")
    strategy: str = Field(default="hybrid", description="Decomposition strategy")

    model_config = {
        "json_schema_extra": {
            "example": {
                "goal": "Build REST API service with authentication",
                "context": {"team_size": 3},
                "deadline": "2025-12-31T23:59:59Z"
            }
        }
    }


class PlanResponse(BaseModel):
    """Response for plan operations."""
    id: str
    name: str
    goal: str
    status: str
    progress: float
    current_phase: int
    total_phases: int
    subtasks_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None


class PlanStatusResponse(BaseModel):
    """Detailed plan status response."""
    id: str
    name: str
    status: str
    progress: float
    current_phase: int
    total_phases: int
    adjustments: int
    subtasks: List[Dict[str, Any]]


class ApprovePlanRequest(BaseModel):
    """Request to approve a plan."""
    approver: str = Field(..., description="Approver name/ID")


class ApproveAdjustmentRequest(BaseModel):
    """Request to approve a plan adjustment."""
    adjustment_id: str = Field(..., description="Adjustment ID to approve")
    approver: str = Field(..., description="Approver name/ID")


# =============================================================================
# Decision Schemas
# =============================================================================


class DecisionRequest(BaseModel):
    """Request for a decision."""
    situation: str = Field(..., description="Situation description")
    options: List[str] = Field(..., description="Available options")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    decision_type: str = Field(
        default="routing",
        description="Decision type: routing, resource, error_handling, priority, escalation, optimization"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "situation": "Multiple agents available for task",
                "options": ["agent_a", "agent_b", "agent_c"],
                "context": {"priority": "high"},
                "decision_type": "routing"
            }
        }
    }


class DecisionOptionResponse(BaseModel):
    """Response for a decision option."""
    id: str
    name: str
    score: float


class DecisionResponse(BaseModel):
    """Response for a decision."""
    decision_id: str
    action: str
    confidence: str
    reasoning: str
    risk_level: float
    requires_approval: bool
    options: List[DecisionOptionResponse]


class ApproveDecisionRequest(BaseModel):
    """Request to approve a decision."""
    approver: str = Field(..., description="Approver name/ID")


class RejectDecisionRequest(BaseModel):
    """Request to reject a decision."""
    approver: str = Field(..., description="Approver name/ID")
    reason: str = Field(..., description="Rejection reason")


class DecisionExplanationResponse(BaseModel):
    """Response for decision explanation."""
    decision_id: str
    explanation: str


# =============================================================================
# Trial and Error Schemas
# =============================================================================


class TrialRequest(BaseModel):
    """Request to execute a task with trial and error."""
    task_id: str = Field(..., description="Task ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")
    strategy: str = Field(default="default", description="Execution strategy")

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "params": {"timeout": 30, "retry_delay": 5},
                "strategy": "default"
            }
        }
    }


class TrialResultResponse(BaseModel):
    """Response for a single trial."""
    id: str
    task_id: str
    attempt_number: int
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int


class TrialResponse(BaseModel):
    """Response for trial execution."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int
    final_params: Dict[str, Any]
    final_strategy: str
    trials: Optional[List[Dict[str, Any]]] = None


class InsightResponse(BaseModel):
    """Response for a learning insight."""
    id: str
    type: str
    pattern: str
    confidence: float
    recommendation: str
    created_at: str


class InsightsListResponse(BaseModel):
    """Response for list of insights."""
    insights: List[InsightResponse]


class RecommendationResponse(BaseModel):
    """Response for a recommendation."""
    id: str
    type: str
    pattern: str
    recommendation: str
    confidence: float
    created_at: str


class RecommendationsListResponse(BaseModel):
    """Response for list of recommendations."""
    recommendations: List[RecommendationResponse]


class TrialStatisticsResponse(BaseModel):
    """Response for trial statistics."""
    total_trials: int
    success_count: int
    failure_count: int
    success_rate: float
    average_duration_ms: float
    unique_tasks: int
    insights_count: int
    known_patterns: int


# =============================================================================
# Common Schemas
# =============================================================================


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
