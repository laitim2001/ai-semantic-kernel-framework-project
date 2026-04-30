# =============================================================================
# IPA Platform - Hybrid Hooks System
# =============================================================================
# Sprint 55: S55-4 - API & ApprovalHook Integration
#
# Risk-driven hooks for hybrid MAF + Claude SDK architecture.
#
# Hooks:
# - RiskDrivenApprovalHook: Uses RiskAssessmentEngine to drive approval decisions
# =============================================================================

from .approval_hook import (
    RiskDrivenApprovalHook,
    ApprovalDecision,
    ApprovalMode,
)

__all__ = [
    "RiskDrivenApprovalHook",
    "ApprovalDecision",
    "ApprovalMode",
]
