"""
Pattern Matcher Module

Provides rule-based pattern matching for the first layer of the
three-layer routing architecture.

Features:
- YAML-based rule configuration
- Pre-compiled regex patterns for performance
- Confidence scoring based on match quality
- Support for Chinese and English patterns

Sprint 91: Pattern Matcher + Rule Definition (Phase 28)
"""

from .matcher import PatternMatcher

__all__ = ["PatternMatcher"]
