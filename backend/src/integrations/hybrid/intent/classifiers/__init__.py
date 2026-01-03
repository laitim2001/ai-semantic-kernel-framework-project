# =============================================================================
# IPA Platform - Intent Classifiers Module
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# This module provides classifiers for intent analysis and mode detection.
#
# Key Components:
#   - BaseClassifier: Abstract base class for all classifiers
#   - RuleBasedClassifier: Keyword-based rule classifier
#   - LLMBasedClassifier: LLM-powered classifier (fallback)
# =============================================================================

from src.integrations.hybrid.intent.classifiers.base import BaseClassifier

__all__ = [
    "BaseClassifier",
]
