"""
LLM Classifier Module

Provides LLM-based intent classification for IT service management.
Uses Claude Haiku for efficient classification with multi-task output.

Sprint 92: Layer 3 of the three-layer routing architecture.
Sprint 93: Added MockLLMClassifier for testing.
"""

from .classifier import LLMClassifier, MockLLMClassifier
from .prompts import CLASSIFICATION_PROMPT, get_classification_prompt

__all__ = [
    "LLMClassifier",
    "MockLLMClassifier",
    "CLASSIFICATION_PROMPT",
    "get_classification_prompt",
]
