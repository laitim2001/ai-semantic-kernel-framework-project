# =============================================================================
# IPA Platform - Intent Analysis Module
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# This module provides intelligent intent analysis and execution mode detection
# for the hybrid MAF + Claude SDK architecture.
#
# Key Components:
#   - ExecutionMode: Enum for execution modes (WORKFLOW, CHAT, HYBRID)
#   - IntentAnalysis: Analysis result with mode, confidence, reasoning
#   - IntentRouter: Main router class for intent analysis
#   - SessionContext: Session context for analysis
#
# Usage:
#   from src.integrations.hybrid.intent import IntentRouter, ExecutionMode
#
#   router = IntentRouter()
#   analysis = await router.analyze_intent("Help me process this workflow")
#   print(analysis.mode)  # ExecutionMode.WORKFLOW_MODE
# =============================================================================

from src.integrations.hybrid.intent.models import (
    ClassificationResult,
    ExecutionMode,
    IntentAnalysis,
    SessionContext,
    SuggestedFramework,
)
from src.integrations.hybrid.intent.router import IntentRouter

__all__ = [
    "ClassificationResult",
    "ExecutionMode",
    "IntentAnalysis",
    "IntentRouter",
    "SessionContext",
    "SuggestedFramework",
]
