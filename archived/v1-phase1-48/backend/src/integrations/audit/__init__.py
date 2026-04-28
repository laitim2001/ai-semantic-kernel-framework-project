# =============================================================================
# IPA Platform - Decision Audit System
# =============================================================================
# Sprint 80: S80-2 - 自主決策審計追蹤 (8 pts)
#
# This module provides comprehensive audit tracking for AI decisions.
#
# Architecture:
#   ┌─────────────────────────────────────────────────────────────┐
#   │                    決策審計系統                              │
#   ├─────────────────────────────────────────────────────────────┤
#   │  1. DecisionTracker - 追蹤和記錄 AI 決策                     │
#   │  2. AuditReportGenerator - 生成可解釋性報告                  │
#   └─────────────────────────────────────────────────────────────┘
#
# Usage:
#   from src.integrations.audit import DecisionTracker
#
#   tracker = DecisionTracker()
#   await tracker.initialize()
#
#   # Record a decision
#   audit = await tracker.record_decision(
#       decision_type=DecisionType.PLAN_GENERATION,
#       selected_action="Execute remediation plan",
#       action_details={"plan_id": "plan-123"},
#       confidence_score=0.85,
#       context=DecisionContext(event_id="event-456"),
#       thinking_process=ThinkingProcess(raw_thinking="..."),
#   )
#
#   # Update outcome
#   await tracker.update_outcome(
#       decision_id=audit.decision_id,
#       outcome=DecisionOutcome.SUCCESS,
#   )
#
#   # Generate report
#   generator = AuditReportGenerator()
#   report = generator.generate_report(audit)
# =============================================================================

from .types import (
    # Enums
    DecisionType,
    DecisionOutcome,
    QualityRating,
    # Data classes
    DecisionContext,
    ThinkingProcess,
    AlternativeConsidered,
    DecisionAudit,
    AuditReport,
    AuditQuery,
    AuditConfig,
    # Constants
    DEFAULT_AUDIT_CONFIG,
)

from .decision_tracker import DecisionTracker
from .report_generator import AuditReportGenerator


__all__ = [
    # Enums
    "DecisionType",
    "DecisionOutcome",
    "QualityRating",
    # Data classes
    "DecisionContext",
    "ThinkingProcess",
    "AlternativeConsidered",
    "DecisionAudit",
    "AuditReport",
    "AuditQuery",
    "AuditConfig",
    # Constants
    "DEFAULT_AUDIT_CONFIG",
    # Core components
    "DecisionTracker",
    "AuditReportGenerator",
]
