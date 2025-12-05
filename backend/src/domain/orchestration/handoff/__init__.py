# =============================================================================
# IPA Platform - Handoff Module
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Agent handoff capabilities including:
#   - HandoffController: Core handoff execution
#   - ContextTransferManager: Context serialization and transfer
#   - HandoffTrigger: Trigger conditions and evaluation
#   - CapabilityMatcher: Agent capability matching
# =============================================================================

from src.domain.orchestration.handoff.controller import (
    HandoffController,
    HandoffContext,
    HandoffPolicy,
    HandoffRequest,
    HandoffResult,
    HandoffState,
    HandoffStatus,
)
from src.domain.orchestration.handoff.context_transfer import (
    ContextTransferManager,
    TransferContext,
    TransferValidationError,
)
from src.domain.orchestration.handoff.triggers import (
    HandoffTrigger,
    TriggerCondition,
    TriggerEvaluationResult,
    TriggerPriority,
    TriggerRegistry,
    TriggerType,
)
from src.domain.orchestration.handoff.trigger_evaluator import (
    ConditionParser,
    HandoffTriggerEvaluator,
)
from src.domain.orchestration.handoff.capabilities import (
    AgentCapability,
    CapabilityCategory,
    CapabilityRegistry,
    CapabilityRequirement,
    ProficiencyLevel,
)
from src.domain.orchestration.handoff.capability_matcher import (
    AgentAvailability,
    AgentStatus,
    CapabilityMatcher,
    MatchResult,
    MatchStrategy,
)

__all__ = [
    # Controller
    "HandoffController",
    "HandoffContext",
    "HandoffPolicy",
    "HandoffRequest",
    "HandoffResult",
    "HandoffState",
    "HandoffStatus",
    # Context Transfer
    "ContextTransferManager",
    "TransferContext",
    "TransferValidationError",
    # Triggers
    "HandoffTrigger",
    "TriggerCondition",
    "TriggerEvaluationResult",
    "TriggerPriority",
    "TriggerRegistry",
    "TriggerType",
    # Trigger Evaluator
    "ConditionParser",
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
]
