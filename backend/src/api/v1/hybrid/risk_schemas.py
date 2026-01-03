# =============================================================================
# IPA Platform - Risk Assessment API Schemas
# =============================================================================
# Sprint 55: S55-4 - API & ApprovalHook Integration
#
# Pydantic schemas for risk assessment API request/response validation.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================


class RiskAssessRequest(BaseModel):
    """Request schema for single operation risk assessment.

    Attributes:
        tool_name: Name of the tool being used (e.g., Bash, Write, Edit)
        operation_type: Type of operation (read, write, execute)
        target_paths: File/resource paths being accessed
        command: Command string (for Bash operations)
        arguments: Tool arguments/parameters
        session_id: Current session identifier
        user_id: Optional user identifier
        user_trust_level: Optional user trust level override
        environment: Execution environment
    """
    tool_name: str = Field(
        ...,
        description="Name of the tool (e.g., Bash, Write, Edit, Read)",
        examples=["Bash", "Write", "Edit"],
    )
    operation_type: Optional[str] = Field(
        default="unknown",
        description="Type of operation (read, write, execute)",
    )
    target_paths: Optional[List[str]] = Field(
        default=None,
        description="File/resource paths being accessed",
    )
    command: Optional[str] = Field(
        default=None,
        description="Command string (for Bash operations)",
    )
    arguments: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Tool arguments/parameters",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Current session identifier",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier for trust level tracking",
    )
    user_trust_level: Optional[str] = Field(
        default=None,
        description="User trust level (new, low, medium, high, trusted)",
    )
    environment: Optional[str] = Field(
        default="development",
        description="Execution environment (development, staging, production, testing)",
    )


class RiskAssessBatchRequest(BaseModel):
    """Request schema for batch operation risk assessment.

    Attributes:
        operations: List of operations to assess
    """
    operations: List[RiskAssessRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of operations to assess",
    )


class RiskConfigUpdate(BaseModel):
    """Request schema for updating risk configuration.

    All fields are optional - only provided fields will be updated.
    """
    critical_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score threshold for CRITICAL level",
    )
    high_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score threshold for HIGH level",
    )
    medium_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score threshold for MEDIUM level",
    )
    operation_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Weight for operation-based risk factors",
    )
    context_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Weight for context-based risk factors",
    )
    pattern_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Weight for pattern-based risk factors",
    )
    auto_approve_low: Optional[bool] = Field(
        default=None,
        description="Auto-approve LOW risk operations",
    )
    auto_approve_medium: Optional[bool] = Field(
        default=None,
        description="Auto-approve MEDIUM risk operations",
    )
    max_auto_approve_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum score for auto-approval",
    )
    enable_pattern_detection: Optional[bool] = Field(
        default=None,
        description="Enable behavioral pattern detection",
    )
    pattern_window_seconds: Optional[int] = Field(
        default=None,
        ge=60,
        le=3600,
        description="Time window for pattern detection (60-3600 seconds)",
    )


# =============================================================================
# Response Schemas
# =============================================================================


class RiskFactorResponse(BaseModel):
    """Response schema for individual risk factor.

    Attributes:
        factor_type: Category of the risk factor
        score: Risk score (0.0 - 1.0)
        weight: Weight in overall calculation
        weighted_score: Calculated weighted contribution
        description: Human-readable description
        source: Source of the risk
        metadata: Additional context information
    """
    factor_type: str = Field(
        ...,
        description="Risk factor type (operation, path, command, pattern, user, environment)",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Risk score (0.0 - 1.0)",
    )
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weight in overall calculation",
    )
    weighted_score: float = Field(
        ...,
        description="Calculated weighted contribution (score * weight)",
    )
    description: str = Field(
        ...,
        description="Human-readable description of the risk",
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of the risk (tool name, path, command)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context information",
    )


class RiskAssessResponse(BaseModel):
    """Response schema for risk assessment result.

    Attributes:
        overall_level: Final risk level classification
        overall_score: Composite risk score (0.0 - 1.0)
        requires_approval: Whether human approval is required
        approval_reason: Reason for requiring approval
        factors: List of contributing risk factors
        assessment_time: When the assessment was performed
        session_id: Session identifier if provided
        metadata: Additional assessment context
    """
    overall_level: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Risk level: low, medium, high, critical",
    )
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite risk score (0.0 - 1.0)",
    )
    requires_approval: bool = Field(
        ...,
        description="Whether human approval is required",
    )
    approval_reason: Optional[str] = Field(
        default=None,
        description="Reason for requiring approval (if applicable)",
    )
    factors: List[RiskFactorResponse] = Field(
        default_factory=list,
        description="Contributing risk factors",
    )
    assessment_time: str = Field(
        ...,
        description="ISO timestamp of assessment",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional assessment context",
    )


class RiskAssessBatchResponse(BaseModel):
    """Response schema for batch risk assessment.

    Attributes:
        assessments: List of individual assessments
        total_operations: Number of operations assessed
        max_risk_level: Highest risk level in batch
        max_risk_score: Highest risk score in batch
        average_risk_score: Average risk score
        approvals_required: Number of operations requiring approval
    """
    assessments: List[RiskAssessResponse] = Field(
        ...,
        description="Individual assessment results",
    )
    total_operations: int = Field(
        ...,
        description="Number of operations assessed",
    )
    max_risk_level: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Highest risk level in batch",
    )
    max_risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Highest risk score in batch",
    )
    average_risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average risk score across all operations",
    )
    approvals_required: int = Field(
        ...,
        ge=0,
        description="Number of operations requiring approval",
    )


class SessionRiskResponse(BaseModel):
    """Response schema for session risk query.

    Attributes:
        session_id: Session identifier
        window_seconds: Time window analyzed
        overall_score: Aggregated session risk score
        overall_level: Aggregated session risk level
        operations_in_window: Number of operations in window
        strategy_used: Scoring strategy used
    """
    session_id: str = Field(
        ...,
        description="Session identifier",
    )
    window_seconds: int = Field(
        ...,
        description="Time window analyzed in seconds",
    )
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregated session risk score",
    )
    overall_level: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Aggregated session risk level",
    )
    operations_in_window: int = Field(
        ...,
        ge=0,
        description="Number of operations in the time window",
    )
    strategy_used: str = Field(
        ...,
        description="Scoring strategy used for aggregation",
    )


class EngineMetricsResponse(BaseModel):
    """Response schema for engine performance metrics.

    Attributes:
        total_assessments: Total assessments performed
        assessments_by_level: Count by risk level
        average_score: Average risk score
        approval_rate: Rate of operations requiring approval
        average_latency_ms: Average assessment latency
    """
    total_assessments: int = Field(
        ...,
        ge=0,
        description="Total number of assessments performed",
    )
    assessments_by_level: Dict[str, int] = Field(
        ...,
        description="Count of assessments by risk level",
    )
    average_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average risk score across all assessments",
    )
    approval_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Proportion of operations requiring approval",
    )
    average_latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Average assessment latency in milliseconds",
    )
