"""
Intent Router Module

Provides intelligent routing for IT service management intents.
Implements a three-layer routing architecture:
1. Pattern Matcher - Rule-based high-confidence matching (Sprint 91)
2. Semantic Router - Vector-based semantic matching (Sprint 92)
3. LLM Classifier - LLM-based intent classification (Sprint 92)
4. BusinessIntentRouter - Unified coordinator (Sprint 93)
5. CompletenessChecker - Information completeness (Sprint 93)
"""

from .models import (
    ITIntentCategory,
    CompletenessInfo,
    RoutingDecision,
    PatternMatchResult,
    PatternRule,
    RiskLevel,
    WorkflowType,
    # Sprint 92: Semantic Router + LLM Classifier
    SemanticRouteResult,
    SemanticRoute,
    LLMClassificationResult,
)
from .pattern_matcher import PatternMatcher
from .semantic_router import SemanticRouter, MockSemanticRouter, get_default_routes, IT_SEMANTIC_ROUTES
from .llm_classifier import LLMClassifier, MockLLMClassifier, CLASSIFICATION_PROMPT

# Sprint 93: BusinessIntentRouter + CompletenessChecker
from .router import (
    RouterConfig,
    RoutingMetrics,
    BusinessIntentRouter,
    MockBusinessIntentRouter,
    create_router,
    create_mock_router,
)
from .completeness import (
    CompletenessChecker,
    MockCompletenessChecker,
    CompletenessRules,
    CompletenessRule,
    FieldDefinition,
    get_default_rules,
    get_required_fields,
    INCIDENT_RULE,
    REQUEST_RULE,
    CHANGE_RULE,
    QUERY_RULE,
)

__all__ = [
    # Core Models
    "ITIntentCategory",
    "CompletenessInfo",
    "RoutingDecision",
    "PatternMatchResult",
    "PatternRule",
    "RiskLevel",
    "WorkflowType",
    # Sprint 92: Semantic Router + LLM Classifier Models
    "SemanticRouteResult",
    "SemanticRoute",
    "LLMClassificationResult",
    # Pattern Matcher (Layer 1)
    "PatternMatcher",
    # Semantic Router (Layer 2)
    "SemanticRouter",
    "MockSemanticRouter",
    "get_default_routes",
    "IT_SEMANTIC_ROUTES",
    # LLM Classifier (Layer 3)
    "LLMClassifier",
    "MockLLMClassifier",
    "CLASSIFICATION_PROMPT",
    # Sprint 93: BusinessIntentRouter (Coordinator)
    "RouterConfig",
    "RoutingMetrics",
    "BusinessIntentRouter",
    "MockBusinessIntentRouter",
    "create_router",
    "create_mock_router",
    # Sprint 93: CompletenessChecker
    "CompletenessChecker",
    "MockCompletenessChecker",
    "CompletenessRules",
    "CompletenessRule",
    "FieldDefinition",
    "get_default_rules",
    "get_required_fields",
    "INCIDENT_RULE",
    "REQUEST_RULE",
    "CHANGE_RULE",
    "QUERY_RULE",
]
