# =============================================================================
# IPA Platform - Hybrid Architecture Integration
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# This module provides the hybrid MAF + Claude SDK integration layer,
# enabling intelligent routing between workflow and chat execution modes.
#
# Key Components:
#   - IntentRouter: Intelligent intent analysis and mode detection
#   - ContextBridge: Cross-framework context synchronization (Sprint 53)
#   - HybridOrchestratorV2: Unified tool execution (Sprint 54)
#
# Dependencies:
#   - Claude SDK (src.integrations.claude_sdk)
#   - Agent Framework (src.integrations.agent_framework)
# =============================================================================

from src.integrations.hybrid.intent import (
    ExecutionMode,
    IntentAnalysis,
    IntentRouter,
    SessionContext,
)

__all__ = [
    "ExecutionMode",
    "IntentAnalysis",
    "IntentRouter",
    "SessionContext",
]
