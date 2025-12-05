# =============================================================================
# IPA Platform - Orchestration Module
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Advanced orchestration capabilities including:
#   - Agent handoff and task transfer
#   - Collaboration protocols
#   - Capability matching
#
# This module builds upon the base workflow execution from Sprint 1-7.
# =============================================================================

from src.domain.orchestration.handoff import (
    HandoffController,
    HandoffPolicy,
    HandoffState,
    HandoffStatus,
    ContextTransferManager,
    HandoffTrigger,
    TriggerType,
    HandoffTriggerEvaluator,
    # Capabilities
    AgentCapability,
    CapabilityCategory,
    CapabilityRegistry,
    CapabilityRequirement,
    ProficiencyLevel,
    # Capability Matcher
    AgentAvailability,
    AgentStatus,
    CapabilityMatcher,
    MatchResult,
    MatchStrategy,
)
from src.domain.orchestration.collaboration import (
    CollaborationProtocol,
    CollaborationMessage,
    MessageType,
    CollaborationSession,
    SessionManager,
    SessionPhase,
)

__all__ = [
    # Handoff
    "HandoffController",
    "HandoffPolicy",
    "HandoffState",
    "HandoffStatus",
    "ContextTransferManager",
    "HandoffTrigger",
    "TriggerType",
    "HandoffTriggerEvaluator",
    # Capabilities
    "AgentCapability",
    "CapabilityCategory",
    "CapabilityRegistry",
    "CapabilityRequirement",
    "ProficiencyLevel",
    # Capability Matcher
    "AgentAvailability",
    "AgentStatus",
    "CapabilityMatcher",
    "MatchResult",
    "MatchStrategy",
    # Collaboration
    "CollaborationProtocol",
    "CollaborationMessage",
    "MessageType",
    "CollaborationSession",
    "SessionManager",
    "SessionPhase",
]
