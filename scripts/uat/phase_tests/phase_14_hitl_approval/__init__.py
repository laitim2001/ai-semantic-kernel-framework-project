# =============================================================================
# IPA Platform - Phase 14 UAT 測試
# =============================================================================
# Phase 14：人工審核與核准機制 (HITL & Approval)
#
# Sprint 55：風險評估引擎 (35 pts)
# Sprint 56：模式切換器 (30 pts)
# Sprint 57：統一 Checkpoint (30 pts)
#
# 總計：95 故事點數
# =============================================================================
"""
Phase 14 UAT 測試套件 - 人工審核與核准機制

本模組包含進階混合架構的真實場景測試：
- 風險評估驅動的人工審核決策
- 動態工作流程與對話模式切換
- 跨框架統一狀態持久化與恢復
"""

from .phase_14_hitl_approval_test import Phase14HITLApprovalTest
from .scenario_risk_assessment import (
    test_high_risk_transaction_detection,
    test_risk_based_approval_routing,
    test_dynamic_risk_threshold_adjustment,
    test_risk_audit_trail,
)
from .scenario_mode_switcher import (
    test_workflow_to_chat_transition,
    test_chat_to_workflow_escalation,
    test_graceful_mode_transition,
    test_context_preservation_on_switch,
)
from .scenario_unified_checkpoint import (
    test_checkpoint_creation_and_restore,
    test_cross_framework_state_recovery,
    test_checkpoint_versioning,
    test_partial_state_recovery,
)

__all__ = [
    "Phase14HITLApprovalTest",
    # 風險評估場景
    "test_high_risk_transaction_detection",
    "test_risk_based_approval_routing",
    "test_dynamic_risk_threshold_adjustment",
    "test_risk_audit_trail",
    # 模式切換場景
    "test_workflow_to_chat_transition",
    "test_chat_to_workflow_escalation",
    "test_graceful_mode_transition",
    "test_context_preservation_on_switch",
    # 統一 Checkpoint 場景
    "test_checkpoint_creation_and_restore",
    "test_cross_framework_state_recovery",
    "test_checkpoint_versioning",
    "test_partial_state_recovery",
]
