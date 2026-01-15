"""
Intent Router Module

Provides intelligent routing for IT service management intents.
Implements a three-layer routing architecture:
1. Pattern Matcher - Rule-based high-confidence matching
2. LLM Classifier - Semantic intent classification (Sprint 92)
3. Human Handoff - Ambiguous case handling (Sprint 93)
"""

from .models import (
    ITIntentCategory,
    CompletenessInfo,
    RoutingDecision,
    PatternMatchResult,
    RiskLevel,
    WorkflowType,
)
from .pattern_matcher import PatternMatcher

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
]
