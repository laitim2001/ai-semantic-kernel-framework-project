# =============================================================================
# IPA Platform - Handoff API Schemas
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Request and response schemas for Handoff API endpoints.
# Provides Pydantic models for:
#   - Handoff trigger requests
#   - Handoff status responses
#   - Capability matching
#
# References:
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class HandoffPolicyEnum(str, Enum):
    """Handoff policy types."""
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    CONDITIONAL = "conditional"


class HandoffStatusEnum(str, Enum):
    """Handoff status types."""
    INITIATED = "initiated"
    VALIDATING = "validating"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class TriggerTypeEnum(str, Enum):
    """Trigger types for handoff."""
    CONDITION = "condition"
    EVENT = "event"
    TIMEOUT = "timeout"
    ERROR = "error"
    CAPABILITY = "capability"
    EXPLICIT = "explicit"


class CapabilityCategoryEnum(str, Enum):
    """Capability categories."""
    LANGUAGE = "language"
    REASONING = "reasoning"
    KNOWLEDGE = "knowledge"
    ACTION = "action"
    INTEGRATION = "integration"
    COMMUNICATION = "communication"


class MatchStrategyEnum(str, Enum):
    """Match strategy types."""
    BEST_FIT = "best_fit"
    FIRST_FIT = "first_fit"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"


# =============================================================================
# Handoff Trigger Schemas
# =============================================================================

class TriggerCondition(BaseModel):
    """Condition for handoff trigger."""
    trigger_type: TriggerTypeEnum = Field(
        default=TriggerTypeEnum.EXPLICIT,
        description="Type of trigger",
    )
    expression: Optional[str] = Field(
        default=None,
        description="Condition expression (for CONDITION type)",
    )
    event_name: Optional[str] = Field(
        default=None,
        description="Event name (for EVENT type)",
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        description="Timeout in seconds (for TIMEOUT type)",
    )
    required_capability: Optional[str] = Field(
        default=None,
        description="Required capability (for CAPABILITY type)",
    )


class HandoffTriggerRequest(BaseModel):
    """Request to trigger a handoff."""
    source_agent_id: UUID = Field(
        ...,
        description="ID of source agent initiating handoff",
    )
    target_agent_id: Optional[UUID] = Field(
        default=None,
        description="ID of target agent (auto-match if not provided)",
    )
    policy: HandoffPolicyEnum = Field(
        default=HandoffPolicyEnum.GRACEFUL,
        description="Handoff policy to apply",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context to transfer to target agent",
    )
    trigger_conditions: List[TriggerCondition] = Field(
        default_factory=list,
        description="Conditions that triggered this handoff",
    )
    required_capabilities: List[str] = Field(
        default_factory=list,
        description="Required capabilities for target agent",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for handoff",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_agent_id": "123e4567-e89b-12d3-a456-426614174000",
                "target_agent_id": None,
                "policy": "graceful",
                "context": {
                    "task_id": "task-123",
                    "progress": 0.5,
                    "variables": {"key": "value"},
                },
                "required_capabilities": ["data_analysis", "code_generation"],
                "reason": "Task requires specialized data analysis",
            }
        }


class HandoffTriggerResponse(BaseModel):
    """Response after triggering a handoff."""
    handoff_id: UUID = Field(
        ...,
        description="Unique handoff identifier",
    )
    status: HandoffStatusEnum = Field(
        ...,
        description="Current handoff status",
    )
    source_agent_id: UUID = Field(
        ...,
        description="Source agent ID",
    )
    target_agent_id: Optional[UUID] = Field(
        default=None,
        description="Target agent ID (if determined)",
    )
    initiated_at: datetime = Field(
        ...,
        description="When handoff was initiated",
    )
    message: str = Field(
        default="Handoff initiated successfully",
        description="Status message",
    )


# =============================================================================
# Handoff Status Schemas
# =============================================================================

class HandoffStatusResponse(BaseModel):
    """Response with handoff status details."""
    handoff_id: UUID = Field(
        ...,
        description="Handoff identifier",
    )
    status: HandoffStatusEnum = Field(
        ...,
        description="Current status",
    )
    source_agent_id: UUID = Field(
        ...,
        description="Source agent ID",
    )
    target_agent_id: Optional[UUID] = Field(
        default=None,
        description="Target agent ID",
    )
    policy: HandoffPolicyEnum = Field(
        ...,
        description="Applied policy",
    )
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Handoff progress (0-1)",
    )
    context_transferred: bool = Field(
        default=False,
        description="Whether context has been transferred",
    )
    initiated_at: datetime = Field(
        ...,
        description="When handoff was initiated",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When handoff completed",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class HandoffCancelRequest(BaseModel):
    """Request to cancel a handoff."""
    reason: Optional[str] = Field(
        default=None,
        description="Reason for cancellation",
    )


class HandoffCancelResponse(BaseModel):
    """Response after cancelling a handoff."""
    handoff_id: UUID = Field(
        ...,
        description="Handoff identifier",
    )
    status: HandoffStatusEnum = Field(
        ...,
        description="Status after cancellation",
    )
    cancelled_at: datetime = Field(
        ...,
        description="When handoff was cancelled",
    )
    rollback_performed: bool = Field(
        default=False,
        description="Whether rollback was performed",
    )
    message: str = Field(
        default="Handoff cancelled successfully",
        description="Status message",
    )


# =============================================================================
# Handoff History Schemas
# =============================================================================

class HandoffHistoryItem(BaseModel):
    """Single handoff history entry."""
    handoff_id: UUID = Field(
        ...,
        description="Handoff identifier",
    )
    status: HandoffStatusEnum = Field(
        ...,
        description="Final status",
    )
    source_agent_id: UUID = Field(
        ...,
        description="Source agent ID",
    )
    target_agent_id: Optional[UUID] = Field(
        default=None,
        description="Target agent ID",
    )
    policy: HandoffPolicyEnum = Field(
        ...,
        description="Applied policy",
    )
    initiated_at: datetime = Field(
        ...,
        description="When initiated",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When completed",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Total duration in seconds",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Handoff reason",
    )


class HandoffHistoryResponse(BaseModel):
    """Response with handoff history."""
    items: List[HandoffHistoryItem] = Field(
        default_factory=list,
        description="History items",
    )
    total: int = Field(
        default=0,
        description="Total number of items",
    )
    page: int = Field(
        default=1,
        description="Current page",
    )
    page_size: int = Field(
        default=20,
        description="Items per page",
    )
    has_more: bool = Field(
        default=False,
        description="Whether more items exist",
    )


# =============================================================================
# Capability Matching Schemas
# =============================================================================

class CapabilityRequirementSchema(BaseModel):
    """Capability requirement for matching."""
    capability_name: str = Field(
        ...,
        description="Name of required capability",
    )
    min_proficiency: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum proficiency level (0-1)",
    )
    category: Optional[CapabilityCategoryEnum] = Field(
        default=None,
        description="Category constraint",
    )
    required: bool = Field(
        default=True,
        description="Whether mandatory",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Importance weight (0-1)",
    )


class CapabilityMatchRequest(BaseModel):
    """Request to find matching agents."""
    requirements: List[CapabilityRequirementSchema] = Field(
        ...,
        min_length=1,
        description="Required capabilities",
    )
    strategy: MatchStrategyEnum = Field(
        default=MatchStrategyEnum.BEST_FIT,
        description="Matching strategy",
    )
    check_availability: bool = Field(
        default=True,
        description="Whether to check agent availability",
    )
    exclude_agents: List[UUID] = Field(
        default_factory=list,
        description="Agent IDs to exclude",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "requirements": [
                    {
                        "capability_name": "data_analysis",
                        "min_proficiency": 0.7,
                        "required": True,
                    },
                    {
                        "capability_name": "code_generation",
                        "min_proficiency": 0.5,
                        "required": False,
                        "weight": 0.5,
                    },
                ],
                "strategy": "best_fit",
                "check_availability": True,
            }
        }


class CapabilityMatchResult(BaseModel):
    """Single capability match result."""
    agent_id: UUID = Field(
        ...,
        description="Matched agent ID",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Match score (0-1)",
    )
    capability_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Individual capability scores",
    )
    missing_capabilities: List[str] = Field(
        default_factory=list,
        description="Missing required capabilities",
    )
    is_available: bool = Field(
        default=True,
        description="Whether agent is available",
    )
    current_load: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Current agent load",
    )


class CapabilityMatchResponse(BaseModel):
    """Response with capability match results."""
    matches: List[CapabilityMatchResult] = Field(
        default_factory=list,
        description="Matching agents",
    )
    total_candidates: int = Field(
        default=0,
        description="Total candidates evaluated",
    )
    strategy_used: MatchStrategyEnum = Field(
        ...,
        description="Strategy that was applied",
    )
    best_match: Optional[CapabilityMatchResult] = Field(
        default=None,
        description="Best matching agent",
    )


# =============================================================================
# Agent Capability Schemas
# =============================================================================

class AgentCapabilitySchema(BaseModel):
    """Agent capability information."""
    id: UUID = Field(
        ...,
        description="Capability ID",
    )
    name: str = Field(
        ...,
        description="Capability name",
    )
    description: str = Field(
        default="",
        description="Capability description",
    )
    category: CapabilityCategoryEnum = Field(
        ...,
        description="Capability category",
    )
    proficiency_level: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Proficiency level (0-1)",
    )
    created_at: datetime = Field(
        ...,
        description="When registered",
    )


class AgentCapabilitiesResponse(BaseModel):
    """Response with agent capabilities."""
    agent_id: UUID = Field(
        ...,
        description="Agent ID",
    )
    capabilities: List[AgentCapabilitySchema] = Field(
        default_factory=list,
        description="Agent's capabilities",
    )
    total_capabilities: int = Field(
        default=0,
        description="Total number of capabilities",
    )


class RegisterCapabilityRequest(BaseModel):
    """Request to register a capability for an agent."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Capability name",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Capability description",
    )
    category: CapabilityCategoryEnum = Field(
        default=CapabilityCategoryEnum.ACTION,
        description="Capability category",
    )
    proficiency_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Proficiency level (0-1)",
    )


class RegisterCapabilityResponse(BaseModel):
    """Response after registering a capability."""
    capability_id: UUID = Field(
        ...,
        description="Created capability ID",
    )
    agent_id: UUID = Field(
        ...,
        description="Agent ID",
    )
    name: str = Field(
        ...,
        description="Capability name",
    )
    message: str = Field(
        default="Capability registered successfully",
        description="Status message",
    )


# =============================================================================
# HITL (Human-in-the-Loop) Schemas - Sprint 15
# =============================================================================

class HITLInputTypeEnum(str, Enum):
    """HITL input types."""
    TEXT = "text"
    CHOICE = "choice"
    CONFIRMATION = "confirmation"
    FILE = "file"
    FORM = "form"


class HITLSessionStatusEnum(str, Enum):
    """HITL session status."""
    ACTIVE = "active"
    INPUT_RECEIVED = "input_received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class HITLInputRequestSchema(BaseModel):
    """HITL input request."""
    request_id: UUID = Field(
        ...,
        description="Request ID",
    )
    session_id: UUID = Field(
        ...,
        description="Session ID",
    )
    prompt: str = Field(
        ...,
        description="Prompt message for user",
    )
    awaiting_agent_id: str = Field(
        default="",
        description="Agent waiting for input",
    )
    input_type: HITLInputTypeEnum = Field(
        default=HITLInputTypeEnum.TEXT,
        description="Expected input type",
    )
    choices: List[str] = Field(
        default_factory=list,
        description="Available choices (for CHOICE type)",
    )
    default_value: Optional[str] = Field(
        default=None,
        description="Default value",
    )
    timeout_seconds: int = Field(
        default=300,
        description="Timeout in seconds",
    )
    expires_at: datetime = Field(
        ...,
        description="When request expires",
    )
    conversation_summary: str = Field(
        default="",
        description="Summary of conversation so far",
    )


class HITLSubmitInputRequest(BaseModel):
    """Request to submit user input for HITL."""
    request_id: UUID = Field(
        ...,
        description="Request ID to respond to",
    )
    input_value: Any = Field(
        ...,
        description="User's input value",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID (if available)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "input_value": "Yes, please proceed with the refund",
                "user_id": "user-123",
            }
        }


class HITLSubmitInputResponse(BaseModel):
    """Response after submitting HITL input."""
    response_id: UUID = Field(
        ...,
        description="Response ID",
    )
    request_id: UUID = Field(
        ...,
        description="Request ID",
    )
    session_id: UUID = Field(
        ...,
        description="Session ID",
    )
    message: str = Field(
        default="Input submitted successfully",
        description="Status message",
    )


class HITLSessionSchema(BaseModel):
    """HITL session information."""
    session_id: UUID = Field(
        ...,
        description="Session ID",
    )
    handoff_execution_id: Optional[UUID] = Field(
        default=None,
        description="Related handoff execution ID",
    )
    status: HITLSessionStatusEnum = Field(
        ...,
        description="Session status",
    )
    created_at: datetime = Field(
        ...,
        description="When session was created",
    )
    updated_at: datetime = Field(
        ...,
        description="When session was last updated",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When session completed",
    )
    current_request: Optional[HITLInputRequestSchema] = Field(
        default=None,
        description="Current pending request",
    )
    history_count: int = Field(
        default=0,
        description="Number of request/response pairs",
    )


class HITLSessionListResponse(BaseModel):
    """Response with list of HITL sessions."""
    sessions: List[HITLSessionSchema] = Field(
        default_factory=list,
        description="HITL sessions",
    )
    total: int = Field(
        default=0,
        description="Total count",
    )


class HITLPendingRequestsResponse(BaseModel):
    """Response with pending HITL requests."""
    requests: List[HITLInputRequestSchema] = Field(
        default_factory=list,
        description="Pending requests",
    )
    total: int = Field(
        default=0,
        description="Total count",
    )


# =============================================================================
# Error Response
# =============================================================================

class HandoffErrorResponse(BaseModel):
    """Error response for handoff operations."""
    error: str = Field(
        ...,
        description="Error type",
    )
    message: str = Field(
        ...,
        description="Error message",
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details",
    )
    handoff_id: Optional[UUID] = Field(
        default=None,
        description="Related handoff ID if applicable",
    )
