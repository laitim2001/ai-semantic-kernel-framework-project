# =============================================================================
# IPA Platform - Handoff API Module
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# API endpoints for Agent handoff operations.
# =============================================================================

from src.api.v1.handoff.routes import router
from src.api.v1.handoff.schemas import (
    AgentCapabilitiesResponse,
    AgentCapabilitySchema,
    CapabilityCategoryEnum,
    CapabilityMatchRequest,
    CapabilityMatchResponse,
    CapabilityMatchResult,
    CapabilityRequirementSchema,
    HandoffCancelRequest,
    HandoffCancelResponse,
    HandoffErrorResponse,
    HandoffHistoryItem,
    HandoffHistoryResponse,
    HandoffPolicyEnum,
    HandoffStatusEnum,
    HandoffStatusResponse,
    HandoffTriggerRequest,
    HandoffTriggerResponse,
    MatchStrategyEnum,
    RegisterCapabilityRequest,
    RegisterCapabilityResponse,
    TriggerCondition,
    TriggerTypeEnum,
)

__all__ = [
    "router",
    # Enums
    "CapabilityCategoryEnum",
    "HandoffPolicyEnum",
    "HandoffStatusEnum",
    "MatchStrategyEnum",
    "TriggerTypeEnum",
    # Trigger Schemas
    "HandoffTriggerRequest",
    "HandoffTriggerResponse",
    "TriggerCondition",
    # Status Schemas
    "HandoffStatusResponse",
    "HandoffCancelRequest",
    "HandoffCancelResponse",
    # History Schemas
    "HandoffHistoryItem",
    "HandoffHistoryResponse",
    # Capability Schemas
    "CapabilityRequirementSchema",
    "CapabilityMatchRequest",
    "CapabilityMatchResponse",
    "CapabilityMatchResult",
    "AgentCapabilitySchema",
    "AgentCapabilitiesResponse",
    "RegisterCapabilityRequest",
    "RegisterCapabilityResponse",
    # Error
    "HandoffErrorResponse",
]
