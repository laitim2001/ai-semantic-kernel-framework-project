"""
Orchestration Integration Module

This module provides intelligent routing and dialog management:
- Layer 1: Pattern Matcher (rule-based, high-confidence)
- Layer 2: Semantic Router (vector similarity)
- Layer 3: LLM Classifier (semantic understanding)
- Guided Dialog Engine (multi-turn information gathering)

Sprint 91: Pattern Matcher + Rule Definition (Phase 28)
Sprint 92: Semantic Router + LLM Classifier (Phase 28)
Sprint 93: BusinessIntentRouter + CompletenessChecker (Phase 28)
Sprint 94: GuidedDialogEngine + Incremental Update (Phase 28)
"""

from .intent_router.models import (
    ITIntentCategory,
    CompletenessInfo,
    RoutingDecision,
    PatternMatchResult,
    RiskLevel,
    WorkflowType,
)
from .intent_router.pattern_matcher import PatternMatcher
from .intent_router.router import (
    BusinessIntentRouter,
    MockBusinessIntentRouter,
    RouterConfig,
    create_router,
    create_mock_router,
)
from .guided_dialog import (
    GuidedDialogEngine,
    MockGuidedDialogEngine,
    ConversationContextManager,
    QuestionGenerator,
    RefinementRules,
    create_guided_dialog_engine,
    create_mock_dialog_engine,
)

__all__ = [
    # Core Models
    "ITIntentCategory",
    "CompletenessInfo",
    "RoutingDecision",
    "PatternMatchResult",
    "RiskLevel",
    "WorkflowType",
    # Pattern Matcher
    "PatternMatcher",
    # Business Intent Router
    "BusinessIntentRouter",
    "MockBusinessIntentRouter",
    "RouterConfig",
    "create_router",
    "create_mock_router",
    # Guided Dialog
    "GuidedDialogEngine",
    "MockGuidedDialogEngine",
    "ConversationContextManager",
    "QuestionGenerator",
    "RefinementRules",
    "create_guided_dialog_engine",
    "create_mock_dialog_engine",
]
