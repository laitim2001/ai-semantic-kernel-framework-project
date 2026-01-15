"""
Intent Router Module

Provides intelligent routing for IT service management intents.
Implements a three-layer routing architecture:
1. Pattern Matcher - Rule-based high-confidence matching (Sprint 91)
2. Semantic Router - Vector-based semantic matching (Sprint 92)
3. LLM Classifier - LLM-based intent classification (Sprint 92)
4. Human Handoff - Ambiguous case handling (Sprint 93)
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
from .semantic_router import SemanticRouter, get_default_routes, IT_SEMANTIC_ROUTES
from .llm_classifier import LLMClassifier, CLASSIFICATION_PROMPT

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
    "get_default_routes",
    "IT_SEMANTIC_ROUTES",
    # LLM Classifier (Layer 3)
    "LLMClassifier",
    "CLASSIFICATION_PROMPT",
]
