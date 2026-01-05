# =============================================================================
# IPA Platform - Phase 13 UAT Tests
# =============================================================================
# Phase 13: Hybrid MAF + Claude SDK Integration (Core Architecture)
#
# Sprint 52: Intent Router & Mode Detection (35 pts)
# Sprint 53: Context Bridge & Sync (35 pts)
# Sprint 54: HybridOrchestrator Refactor (35 pts)
#
# Total: 105 Story Points
# =============================================================================
"""
Phase 13 UAT Test Suite - Hybrid MAF + Claude SDK Integration

This module contains real-world scenario tests for the hybrid architecture:
- Intent routing between Workflow Mode and Chat Mode
- Context synchronization between MAF and Claude SDK
- Unified orchestration with mode-aware execution
"""

from .phase_13_hybrid_core_test import Phase13HybridCoreTest
from .scenario_intent_routing import (
    test_invoice_processing_workflow_detection,
    test_customer_inquiry_chat_detection,
    test_ambiguous_input_hybrid_routing,
    test_forced_mode_override,
)
from .scenario_context_bridge import (
    test_maf_to_claude_state_sync,
    test_claude_to_maf_state_sync,
    test_bidirectional_context_sync,
    test_state_conflict_resolution,
)
from .scenario_hybrid_orchestrator import (
    test_workflow_mode_execution,
    test_chat_mode_execution,
    test_hybrid_mode_with_auto_routing,
    test_mode_switching_mid_execution,
)

__all__ = [
    "Phase13HybridCoreTest",
    # Intent Routing Scenarios
    "test_invoice_processing_workflow_detection",
    "test_customer_inquiry_chat_detection",
    "test_ambiguous_input_hybrid_routing",
    "test_forced_mode_override",
    # Context Bridge Scenarios
    "test_maf_to_claude_state_sync",
    "test_claude_to_maf_state_sync",
    "test_bidirectional_context_sync",
    "test_state_conflict_resolution",
    # Hybrid Orchestrator Scenarios
    "test_workflow_mode_execution",
    "test_chat_mode_execution",
    "test_hybrid_mode_with_auto_routing",
    "test_mode_switching_mid_execution",
]
