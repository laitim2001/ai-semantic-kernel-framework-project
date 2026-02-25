"""
LLM Classifier Module

Provides LLM-based intent classification for IT service management.
Uses LLMServiceProtocol for flexible LLM backend integration.

Sprint 92: Layer 3 of the three-layer routing architecture.
Sprint 128: Migration from anthropic SDK to LLMServiceProtocol + cache + evaluation.
"""

from .classifier import LLMClassifier
from .prompts import (
    CLASSIFICATION_PROMPT,
    get_classification_prompt,
    get_required_fields,
    get_sub_intent_examples,
)
from .cache import ClassificationCache
from .evaluation import (
    EVALUATION_CASES,
    EvaluationCase,
    EvaluationResult,
    evaluate_classifier,
)

__all__ = [
    # Classifier
    "LLMClassifier",
    # Prompts
    "CLASSIFICATION_PROMPT",
    "get_classification_prompt",
    "get_required_fields",
    "get_sub_intent_examples",
    # Cache (Sprint 128)
    "ClassificationCache",
    # Evaluation (Sprint 128)
    "EVALUATION_CASES",
    "EvaluationCase",
    "EvaluationResult",
    "evaluate_classifier",
]
