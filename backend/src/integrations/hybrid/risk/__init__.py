# =============================================================================
# IPA Platform - Risk Assessment Module
# =============================================================================
# Sprint 55: Risk Assessment Engine Core
# Sprint 55: S55-2 - Operation Analyzer
# Sprint 55: S55-3 - Context Evaluator & Pattern Detector
#
# Multi-dimensional risk assessment for hybrid orchestration.
# Supports tool operation analysis, context evaluation, and pattern detection.
#
# Dependencies:
#   - HybridOrchestrator V2 (src.integrations.hybrid.orchestrator_v2)
#   - ContextBridge (src.integrations.hybrid.context)
# =============================================================================

from .models import (
    OperationContext,
    RiskLevel,
    RiskFactor,
    RiskFactorType,
    RiskAssessment,
    RiskConfig,
)
from .engine import RiskAssessmentEngine
from .scoring.scorer import RiskScorer
from .analyzers import (
    OperationAnalyzer,
    ContextEvaluator,
    ContextEvaluatorConfig,
    UserTrustLevel,
    PatternDetector,
    PatternDetectorConfig,
    PatternType,
)

__all__ = [
    # Enums
    "RiskLevel",
    "RiskFactorType",
    "UserTrustLevel",
    "PatternType",
    # Models
    "RiskFactor",
    "RiskAssessment",
    "RiskConfig",
    "OperationContext",
    # Core
    "RiskAssessmentEngine",
    "RiskScorer",
    # Analyzers
    "OperationAnalyzer",
    "ContextEvaluator",
    "ContextEvaluatorConfig",
    "PatternDetector",
    "PatternDetectorConfig",
]
