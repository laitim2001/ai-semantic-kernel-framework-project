# =============================================================================
# IPA Platform - Learning System
# =============================================================================
# Sprint 80: S80-1 - Few-shot 學習系統 (8 pts)
#
# This module provides Few-shot learning capabilities for AI decision-making.
#
# Architecture:
#   ┌─────────────────────────────────────────────────────────────┐
#   │                    Few-shot 學習系統                         │
#   ├─────────────────────────────────────────────────────────────┤
#   │  1. CaseExtractor - 從 mem0 提取歷史案例                     │
#   │  2. SimilarityCalculator - 計算案例相似度                    │
#   │  3. FewShotLearner - 動態增強 prompt                        │
#   └─────────────────────────────────────────────────────────────┘
#
# Usage:
#   from src.integrations.learning import FewShotLearner
#
#   learner = FewShotLearner()
#   await learner.initialize(embedding_service, memory_manager)
#
#   # Enhance prompt with similar cases
#   result = await learner.enhance_prompt(
#       base_prompt="Analyze and fix this issue...",
#       event_description="Database connection timeout",
#       affected_systems=["postgresql", "api-gateway"],
#   )
#
#   # Track effectiveness
#   await learner.track_effectiveness(
#       enhancement_id=result.enhancement_id,
#       decision_id="decision-123",
#       was_successful=True,
#   )
# =============================================================================

from .types import (
    # Enums
    CaseOutcome,
    CaseCategory,
    # Data classes
    CaseMetadata,
    Case,
    SimilarityResult,
    LearningResult,
    LearningEffectiveness,
    LearningConfig,
    # Constants
    DEFAULT_LEARNING_CONFIG,
)

from .similarity import SimilarityCalculator
from .case_extractor import CaseExtractor
from .few_shot import FewShotLearner


__all__ = [
    # Enums
    "CaseOutcome",
    "CaseCategory",
    # Data classes
    "CaseMetadata",
    "Case",
    "SimilarityResult",
    "LearningResult",
    "LearningEffectiveness",
    "LearningConfig",
    # Constants
    "DEFAULT_LEARNING_CONFIG",
    # Core components
    "SimilarityCalculator",
    "CaseExtractor",
    "FewShotLearner",
]
