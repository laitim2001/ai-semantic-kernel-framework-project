# =============================================================================
# IPA Platform - Framework Selection Module (formerly Intent Analysis Module)
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
# Sprint 98: Renamed IntentRouter → FrameworkSelector (Phase 28 Integration)
#
# This module provides intelligent framework selection and execution mode detection
# for the hybrid MAF + Claude SDK architecture.
#
# Key Components:
#   - ExecutionMode: Enum for execution modes (WORKFLOW, CHAT, HYBRID)
#   - FrameworkAnalysis (IntentAnalysis): Analysis result with mode, confidence, reasoning
#   - FrameworkSelector (IntentRouter): Main selector class for framework selection
#   - SessionContext: Session context for analysis
#
# Usage (new naming):
#   from src.integrations.hybrid.intent import FrameworkSelector, ExecutionMode
#
#   selector = FrameworkSelector()
#   analysis = await selector.select_framework("Help me process this workflow")
#   print(analysis.mode)  # ExecutionMode.WORKFLOW_MODE
#
# Usage (backward compatible):
#   from src.integrations.hybrid.intent import IntentRouter, ExecutionMode
#
#   router = IntentRouter()  # Same as FrameworkSelector
#   analysis = await router.analyze_intent("Help me process this workflow")
#   print(analysis.mode)  # ExecutionMode.WORKFLOW_MODE
# =============================================================================

from src.integrations.hybrid.intent.models import (
    ClassificationResult,
    ExecutionMode,
    FrameworkAnalysis,
    IntentAnalysis,
    SessionContext,
    SuggestedFramework,
)
from src.integrations.hybrid.intent.router import (
    FrameworkSelector,
    IntentRouter,
)

__all__ = [
    # New names (Sprint 98)
    "FrameworkSelector",
    "FrameworkAnalysis",
    # Backward compatible names
    "ClassificationResult",
    "ExecutionMode",
    "IntentAnalysis",
    "IntentRouter",
    "SessionContext",
    "SuggestedFramework",
]
