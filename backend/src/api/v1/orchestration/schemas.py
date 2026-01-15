"""
Orchestration API Schemas

Pydantic models for orchestration API request/response handling.

Sprint 96: Story 96-5 - API Route Implementation (Phase 28)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class IntentCategoryEnum(str, Enum):
    """IT Intent categories."""

    INCIDENT = "incident"
    REQUEST = "request"
    CHANGE = "change"
    QUERY = "query"
    UNKNOWN = "unknown"


class RiskLevelEnum(str, Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowTypeEnum(str, Enum):
    """Workflow types for handling intents."""

    MAGENTIC = "magentic"
    HANDOFF = "handoff"
    CONCURRENT = "concurrent"
    SEQUENTIAL = "sequential"
    SIMPLE = "simple"


# =============================================================================
# Request Schemas
# =============================================================================


class IntentClassifyRequest(BaseModel):
    """Request model for intent classification."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User input text to classify",
    )
    source: str = Field(
        default="user",
        description="Source of the input (user, servicenow, prometheus, etc.)",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for classification",
    )
    include_risk_assessment: bool = Field(
        default=True,
        description="Whether to include risk assessment in response",
    )


class IntentTestRequest(BaseModel):
    """Request model for testing intent classification (debug mode)."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Test input text",
    )
    verbose: bool = Field(
        default=True,
        description="Include detailed layer results",
    )


class RiskAssessmentRequest(BaseModel):
    """Request model for standalone risk assessment."""

    intent_category: IntentCategoryEnum = Field(
        ...,
        description="IT intent category",
    )
    sub_intent: Optional[str] = Field(
        default=None,
        description="Sub-intent classification",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Assessment context (is_production, is_weekend, etc.)",
    )


# =============================================================================
# Response Schemas
# =============================================================================


class CompletenessInfoResponse(BaseModel):
    """Response model for completeness information."""

    is_complete: bool = Field(
        ...,
        description="Whether all required information is present",
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="List of missing required fields",
    )
    optional_missing: List[str] = Field(
        default_factory=list,
        description="List of missing optional fields",
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completeness score (0.0 - 1.0)",
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for gathering missing information",
    )


class RiskFactorResponse(BaseModel):
    """Response model for a risk factor."""

    name: str = Field(..., description="Factor identifier")
    description: str = Field(..., description="Human-readable description")
    weight: float = Field(..., ge=0.0, le=1.0, description="Factor weight")
    value: Any = Field(default=None, description="Current value")
    impact: str = Field(..., description="Impact direction (increase/decrease/neutral)")


class RiskAssessmentResponse(BaseModel):
    """Response model for risk assessment."""

    level: RiskLevelEnum = Field(..., description="Risk level")
    score: float = Field(..., ge=0.0, le=1.0, description="Risk score")
    requires_approval: bool = Field(..., description="Whether approval is required")
    approval_type: str = Field(..., description="Approval type (none/single/multi)")
    factors: List[RiskFactorResponse] = Field(
        default_factory=list,
        description="Contributing risk factors",
    )
    reasoning: str = Field(default="", description="Assessment reasoning")
    policy_id: Optional[str] = Field(default=None, description="Policy used")
    adjustments_applied: List[str] = Field(
        default_factory=list,
        description="Context adjustments applied",
    )


class RoutingDecisionResponse(BaseModel):
    """Response model for routing decision."""

    intent_category: IntentCategoryEnum = Field(
        ...,
        description="Primary intent classification",
    )
    sub_intent: Optional[str] = Field(
        default=None,
        description="Sub-intent classification",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classification confidence",
    )
    workflow_type: WorkflowTypeEnum = Field(
        ...,
        description="Recommended workflow type",
    )
    risk_level: RiskLevelEnum = Field(
        ...,
        description="Assessed risk level",
    )
    completeness: CompletenessInfoResponse = Field(
        ...,
        description="Information completeness",
    )
    routing_layer: str = Field(
        ...,
        description="Layer that made the decision (pattern/semantic/llm)",
    )
    rule_id: Optional[str] = Field(
        default=None,
        description="Rule ID if pattern matched",
    )
    reasoning: str = Field(
        default="",
        description="Explanation for routing decision",
    )
    processing_time_ms: float = Field(
        ...,
        description="Processing time in milliseconds",
    )
    timestamp: datetime = Field(
        ...,
        description="Decision timestamp",
    )


class IntentClassifyResponse(BaseModel):
    """Response model for intent classification endpoint."""

    routing_decision: RoutingDecisionResponse = Field(
        ...,
        description="Routing decision details",
    )
    risk_assessment: Optional[RiskAssessmentResponse] = Field(
        default=None,
        description="Risk assessment (if requested)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class LayerResultResponse(BaseModel):
    """Response model for layer test result."""

    layer: str = Field(..., description="Layer name")
    matched: bool = Field(..., description="Whether layer matched")
    confidence: float = Field(default=0.0, description="Match confidence/similarity")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Layer result details")
    latency_ms: float = Field(default=0.0, description="Layer processing time")


class IntentTestResponse(BaseModel):
    """Response model for intent test endpoint (debug mode)."""

    input: str = Field(..., description="Test input")
    final_decision: RoutingDecisionResponse = Field(
        ...,
        description="Final routing decision",
    )
    layer_results: List[LayerResultResponse] = Field(
        default_factory=list,
        description="Results from each layer",
    )
    total_latency_ms: float = Field(
        ...,
        description="Total processing time",
    )


# =============================================================================
# Utility Models
# =============================================================================


class PolicyResponse(BaseModel):
    """Response model for risk policy."""

    id: str = Field(..., description="Policy identifier")
    intent_category: IntentCategoryEnum = Field(..., description="Intent category")
    sub_intent: str = Field(..., description="Sub-intent pattern")
    default_risk_level: RiskLevelEnum = Field(..., description="Default risk level")
    requires_approval: bool = Field(..., description="Approval required")
    approval_type: str = Field(..., description="Approval type")
    factors: List[str] = Field(default_factory=list, description="Risk factors")
    description: str = Field(default="", description="Policy description")


class PolicyListResponse(BaseModel):
    """Response model for policy list."""

    policies: List[PolicyResponse] = Field(..., description="List of policies")
    count: int = Field(..., description="Total policy count")


class MetricsResponse(BaseModel):
    """Response model for routing metrics."""

    total_requests: int = Field(..., description="Total requests processed")
    pattern_matches: int = Field(..., description="Pattern layer matches")
    semantic_matches: int = Field(..., description="Semantic layer matches")
    llm_fallbacks: int = Field(..., description="LLM fallback invocations")
    avg_latency_ms: float = Field(..., description="Average latency")
    p95_latency_ms: float = Field(..., description="95th percentile latency")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
