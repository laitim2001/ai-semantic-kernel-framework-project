# =============================================================================
# IPA Platform - Learning API Schemas
# =============================================================================
# Sprint 4: Developer Experience - Few-shot Learning Mechanism
#
# Pydantic schemas for learning API request/response validation.
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Case Schemas
# =============================================================================


class RecordCorrectionRequest(BaseModel):
    """Request to record a human correction."""

    scenario: str = Field(..., min_length=1, max_length=100, description="Business scenario")
    original_input: str = Field(..., min_length=1, description="Original input text")
    original_output: str = Field(..., min_length=1, description="AI's original output")
    corrected_output: str = Field(..., min_length=1, description="Human-corrected output")
    feedback: str = Field(..., min_length=1, description="Explanation of correction")
    execution_id: Optional[UUID] = Field(None, description="Related execution ID")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CaseResponse(BaseModel):
    """Learning case response."""

    id: UUID
    execution_id: Optional[UUID]
    scenario: str
    original_input: str
    original_output: str
    corrected_output: str
    feedback: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    rejection_reason: Optional[str]
    usage_count: int
    effectiveness_score: float
    tags: List[str]
    metadata: Dict[str, Any]


class CaseListResponse(BaseModel):
    """Case list response."""

    cases: List[CaseResponse]
    total: int


# =============================================================================
# Approval Schemas
# =============================================================================


class ApproveRequest(BaseModel):
    """Approve case request."""

    approved_by: Optional[str] = Field(None, description="Approver identifier")


class RejectRequest(BaseModel):
    """Reject case request."""

    reason: str = Field(..., min_length=1, description="Rejection reason")


class BulkApproveRequest(BaseModel):
    """Bulk approve request."""

    case_ids: List[UUID] = Field(..., min_items=1, description="Case IDs to approve")
    approved_by: Optional[str] = Field(None, description="Approver identifier")


class BulkApproveResponse(BaseModel):
    """Bulk approve response."""

    approved_count: int
    total_requested: int


# =============================================================================
# Search Schemas
# =============================================================================


class SimilarCasesRequest(BaseModel):
    """Request for similar cases."""

    scenario: str = Field(..., description="Scenario to search")
    input_text: str = Field(..., description="Input to match")
    limit: int = Field(5, ge=1, le=20, description="Maximum results")
    approved_only: bool = Field(True, description="Only approved cases")


class SimilarCaseItem(BaseModel):
    """Similar case with score."""

    case: CaseResponse
    similarity: float


class SimilarCasesResponse(BaseModel):
    """Similar cases response."""

    results: List[SimilarCaseItem]
    query_input: str
    total: int


# =============================================================================
# Few-shot Prompt Schemas
# =============================================================================


class BuildPromptRequest(BaseModel):
    """Request to build few-shot prompt."""

    base_prompt: str = Field(..., description="Base system prompt")
    scenario: str = Field(..., description="Scenario for examples")
    input_text: str = Field(..., description="Current input")
    example_format: str = Field("standard", description="Format style")


class BuildPromptResponse(BaseModel):
    """Few-shot prompt response."""

    enhanced_prompt: str
    examples_used: int
    scenario: str


# =============================================================================
# Effectiveness Schemas
# =============================================================================


class RecordEffectivenessRequest(BaseModel):
    """Record case effectiveness."""

    was_helpful: bool = Field(..., description="Whether case was helpful")
    score: Optional[float] = Field(None, ge=0, le=1, description="Effectiveness score")


# =============================================================================
# Statistics Schemas
# =============================================================================


class LearningStatisticsResponse(BaseModel):
    """Learning service statistics."""

    total_cases: int
    approved_cases: int
    pending_cases: int
    rejected_cases: int
    total_usage: int
    by_scenario: Dict[str, int]
    avg_effectiveness: float


class ScenarioStatisticsResponse(BaseModel):
    """Scenario-specific statistics."""

    scenario: str
    total_cases: int
    approved_cases: int
    total_usage: int
    avg_effectiveness: float


# =============================================================================
# Health Check Schema
# =============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response."""

    service: str = "learning"
    status: str
    total_cases: int
    approved_cases: int
