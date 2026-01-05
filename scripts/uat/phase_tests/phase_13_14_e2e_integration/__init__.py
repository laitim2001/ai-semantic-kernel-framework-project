# =============================================================================
# IPA Platform - Phase 13+14 E2E Integration Tests
# =============================================================================
# Phase 13: Hybrid MAF + Claude SDK Core (105 pts)
#   - Sprint 52: Intent Router & Context Bridge (35 pts)
#   - Sprint 53: Unified Tool Executor (35 pts)
#   - Sprint 54: HybridOrchestrator Refactor (35 pts)
#
# Phase 14: HITL & Approval (100 pts)
#   - Sprint 55: Risk Assessment Engine (35 pts)
#   - Sprint 56: Mode Switcher (35 pts)
#   - Sprint 57: Unified Checkpoint (30 pts)
#
# Total: 205 Story Points
# =============================================================================
"""
Phase 13+14 E2E Integration Test Suite

This module contains end-to-end integration tests that validate the complete
hybrid architecture flow across both phases:

1. Intent Routing -> Risk Assessment -> HITL Decision
2. Mode Switching with Context Preservation
3. Unified Checkpoint with Cross-Framework Recovery
4. Complete Workflow -> Chat -> Workflow Transition

Test Scenarios:
- scenario_intent_to_risk: Intent detection triggering risk-based HITL
- scenario_mode_switch_context: Mode transitions with context sync
- scenario_checkpoint_recovery: Cross-framework state persistence
- scenario_full_hybrid_flow: Complete end-to-end hybrid execution
"""

from .e2e_integration_test import Phase13_14E2EIntegrationTest
from .scenario_intent_to_risk import (
    test_intent_detection_triggers_risk_assessment,
    test_high_risk_intent_requires_approval,
    test_low_risk_intent_auto_proceeds,
    test_risk_escalation_to_human,
)
from .scenario_mode_switch_context import (
    test_workflow_to_chat_preserves_context,
    test_chat_to_workflow_maintains_state,
    test_context_bridge_bidirectional_sync,
    test_graceful_degradation_on_sync_failure,
)
from .scenario_checkpoint_recovery import (
    test_checkpoint_spans_both_frameworks,
    test_recovery_restores_correct_mode,
    test_partial_state_recovery,
    test_checkpoint_versioning_across_switches,
)
from .scenario_full_hybrid_flow import (
    test_complete_workflow_chat_workflow_cycle,
    test_multi_step_approval_chain,
    test_error_recovery_with_checkpoint,
)

__all__ = [
    "Phase13_14E2EIntegrationTest",
    # Scenario 1: Intent to Risk
    "test_intent_detection_triggers_risk_assessment",
    "test_high_risk_intent_requires_approval",
    "test_low_risk_intent_auto_proceeds",
    "test_risk_escalation_to_human",
    # Scenario 2: Mode Switch Context
    "test_workflow_to_chat_preserves_context",
    "test_chat_to_workflow_maintains_state",
    "test_context_bridge_bidirectional_sync",
    "test_graceful_degradation_on_sync_failure",
    # Scenario 3: Checkpoint Recovery
    "test_checkpoint_spans_both_frameworks",
    "test_recovery_restores_correct_mode",
    "test_partial_recovery_with_validation",
    "test_checkpoint_versioning_across_switches",
    # Scenario 4: Full Hybrid Flow
    "test_complete_workflow_chat_workflow_cycle",
    "test_multi_step_approval_chain",
    "test_error_recovery_with_checkpoint",
]
