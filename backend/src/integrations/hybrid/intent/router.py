# =============================================================================
# IPA Platform - Framework Selector (formerly Intent Router)
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
# Sprint 98: Renamed IntentRouter → FrameworkSelector (Phase 28 Integration)
#
# Main framework selector class that analyzes user input and determines
# the optimal execution mode (Workflow, Chat, or Hybrid).
#
# Decision Logic:
#   1. Check for explicit workflow keywords
#   2. Analyze task complexity (step count, dependencies)
#   3. Check for multi-agent collaboration needs
#   4. Evaluate persistence/checkpoint requirements
#
# Dependencies:
#   - classifiers/base.py (BaseClassifier)
#   - models.py (ExecutionMode, FrameworkAnalysis, SessionContext)
#
# Note: IntentRouter and IntentAnalysis are kept as backward-compatible aliases.
# =============================================================================

import logging
import time
from typing import Dict, List, Optional

from src.integrations.hybrid.intent.classifiers.base import BaseClassifier
from src.integrations.hybrid.intent.models import (
    ClassificationResult,
    ExecutionMode,
    IntentAnalysis,
    Message,
    SessionContext,
    SuggestedFramework,
)

logger = logging.getLogger(__name__)


class FrameworkSelector:
    """
    Framework Selector for analyzing user input and determining execution mode.

    Sprint 98: Renamed from IntentRouter to FrameworkSelector to avoid confusion
    with Phase 28's BusinessIntentRouter which handles IT intent classification.

    The FrameworkSelector uses multiple classifiers to analyze user input and
    determine the optimal execution mode. It supports rule-based classification,
    complexity analysis, and LLM-based classification as a fallback.

    Attributes:
        classifiers: List of classifiers to use for analysis
        default_mode: Default mode when confidence is below threshold
        confidence_threshold: Minimum confidence to accept a classification
        enable_logging: Whether to log classification decisions

    Example:
        >>> from src.integrations.hybrid.intent.classifiers.rule_based import RuleBasedClassifier
        >>>
        >>> selector = FrameworkSelector(
        ...     classifiers=[RuleBasedClassifier()],
        ...     confidence_threshold=0.7
        ... )
        >>> analysis = await selector.select_framework("Help me create a workflow")
        >>> print(analysis.mode)  # ExecutionMode.WORKFLOW_MODE

    Decision Flow:
        1. Run all enabled classifiers on the input
        2. Aggregate results using weighted voting
        3. If confidence >= threshold, use the detected mode
        4. Otherwise, use the default mode
    """

    def __init__(
        self,
        classifiers: Optional[List[BaseClassifier]] = None,
        default_mode: ExecutionMode = ExecutionMode.CHAT_MODE,
        confidence_threshold: float = 0.7,
        enable_logging: bool = True,
    ):
        """
        Initialize the IntentRouter.

        Args:
            classifiers: List of classifiers to use. If None, uses defaults.
            default_mode: Default mode when confidence is below threshold.
            confidence_threshold: Minimum confidence to accept a classification.
            enable_logging: Whether to log classification decisions.
        """
        self.classifiers = classifiers or []
        self.default_mode = default_mode
        self.confidence_threshold = confidence_threshold
        self.enable_logging = enable_logging

        logger.info(
            f"FrameworkSelector initialized with {len(self.classifiers)} classifiers, "
            f"threshold={confidence_threshold}, default={default_mode.value}"
        )

    def add_classifier(self, classifier: BaseClassifier) -> None:
        """
        Add a classifier to the router.

        Args:
            classifier: The classifier to add
        """
        self.classifiers.append(classifier)
        logger.debug(f"Added classifier: {classifier.name}")

    def remove_classifier(self, name: str) -> bool:
        """
        Remove a classifier by name.

        Args:
            name: Name of the classifier to remove

        Returns:
            True if removed, False if not found
        """
        for i, c in enumerate(self.classifiers):
            if c.name == name:
                self.classifiers.pop(i)
                logger.debug(f"Removed classifier: {name}")
                return True
        return False

    async def select_framework(
        self,
        user_input: str,
        session_context: Optional[SessionContext] = None,
        history: Optional[List[Message]] = None,
        routing_decision: Optional["RoutingDecision"] = None,
    ) -> IntentAnalysis:
        """
        Select the appropriate framework based on user input.

        Sprint 98: Renamed from analyze_intent to select_framework.
        This is the main entry point for framework selection. It runs all enabled
        classifiers, aggregates their results, and returns a comprehensive
        analysis result.

        Args:
            user_input: The user's input text to analyze
            session_context: Optional session context for additional info
            history: Optional conversation history
            routing_decision: Optional routing decision from BusinessIntentRouter (Phase 28)

        Returns:
            IntentAnalysis (FrameworkAnalysis) with the detected mode, confidence, and reasoning

        Example:
            >>> analysis = await selector.select_framework(
            ...     "Create a multi-step workflow for data processing",
            ...     session_context=SessionContext(session_id="sess_123")
            ... )
            >>> print(f"Mode: {analysis.mode}, Confidence: {analysis.confidence}")
        """
        start_time = time.time()

        # Validate input
        if not user_input or not user_input.strip():
            return self._create_default_analysis(
                reasoning="Empty input, using default mode",
                analysis_time_ms=(time.time() - start_time) * 1000,
            )

        # Run all enabled classifiers
        classification_results = await self._run_classifiers(
            user_input, session_context, history
        )

        # If no classifiers or all failed, return default
        if not classification_results:
            return self._create_default_analysis(
                reasoning="No classifiers available or all failed",
                analysis_time_ms=(time.time() - start_time) * 1000,
            )

        # Aggregate results
        aggregated = self._aggregate_results(classification_results)
        analysis_time_ms = (time.time() - start_time) * 1000

        # Determine final mode
        if aggregated["confidence"] >= self.confidence_threshold:
            mode = aggregated["mode"]
            reasoning = aggregated["reasoning"]
        else:
            mode = self.default_mode
            reasoning = (
                f"Confidence {aggregated['confidence']:.2f} below threshold "
                f"{self.confidence_threshold}, using default mode"
            )

        # Determine suggested framework
        suggested_framework = self._determine_framework(mode, session_context)

        # Extract detected features
        detected_features = self._extract_features(classification_results)

        analysis = IntentAnalysis(
            mode=mode,
            confidence=aggregated["confidence"],
            reasoning=reasoning,
            suggested_framework=suggested_framework,
            classification_results=classification_results,
            detected_features=detected_features,
            analysis_time_ms=analysis_time_ms,
        )

        if self.enable_logging:
            logger.info(
                f"Intent analysis complete: mode={mode.value}, "
                f"confidence={analysis.confidence:.2f}, "
                f"time={analysis_time_ms:.1f}ms"
            )

        return analysis

    async def _run_classifiers(
        self,
        user_input: str,
        context: Optional[SessionContext],
        history: Optional[List[Message]],
    ) -> List[ClassificationResult]:
        """
        Run all enabled classifiers on the input.

        Args:
            user_input: The user's input text
            context: Optional session context
            history: Optional conversation history

        Returns:
            List of classification results from all classifiers
        """
        results = []

        for classifier in self.classifiers:
            if not classifier.is_enabled():
                continue

            try:
                result = await classifier.classify(user_input, context, history)
                results.append(result)
                logger.debug(
                    f"Classifier {classifier.name}: mode={result.mode.value}, "
                    f"confidence={result.confidence:.2f}"
                )
            except Exception as e:
                logger.warning(
                    f"Classifier {classifier.name} failed: {e}",
                    exc_info=True,
                )

        return results

    def _aggregate_results(
        self,
        results: List[ClassificationResult],
    ) -> Dict:
        """
        Aggregate classification results using weighted voting.

        Args:
            results: List of classification results

        Returns:
            Dict with aggregated mode, confidence, and reasoning
        """
        if not results:
            return {
                "mode": self.default_mode,
                "confidence": 0.0,
                "reasoning": "No classification results",
            }

        # Calculate weighted scores for each mode
        # Use raw weighted scores to determine winner (weight affects voting power)
        # Use weighted average of confidences for the final confidence value
        mode_scores: Dict[ExecutionMode, float] = {}  # Raw weighted scores
        mode_confidences: Dict[ExecutionMode, List[float]] = {}  # For averaging
        mode_weights: Dict[ExecutionMode, float] = {}  # For weighted avg
        reasonings = []

        for result in results:
            classifier = next(
                (c for c in self.classifiers if c.name == result.classifier_name),
                None,
            )
            weight = classifier.weight if classifier else 1.0

            # Initialize mode if not present
            if result.mode not in mode_scores:
                mode_scores[result.mode] = 0.0
                mode_confidences[result.mode] = []
                mode_weights[result.mode] = 0.0

            # Raw weighted score for determining winner
            mode_scores[result.mode] += result.confidence * weight
            # Track confidences and weights for final confidence calculation
            mode_confidences[result.mode].append(result.confidence)
            mode_weights[result.mode] += weight
            reasonings.append(f"[{result.classifier_name}] {result.reasoning}")

        # Find best mode by raw weighted score
        best_mode = max(mode_scores, key=mode_scores.get)  # type: ignore
        # Calculate final confidence as weighted average of winning mode's confidences
        # This preserves the original confidence values
        if mode_weights[best_mode] > 0:
            best_confidence = mode_scores[best_mode] / mode_weights[best_mode]
        else:
            best_confidence = sum(mode_confidences[best_mode]) / len(mode_confidences[best_mode])

        return {
            "mode": best_mode,
            "confidence": best_confidence,
            "reasoning": " | ".join(reasonings),
        }

    def _determine_framework(
        self,
        mode: ExecutionMode,
        context: Optional[SessionContext],
    ) -> SuggestedFramework:
        """
        Determine the suggested framework based on mode and context.

        Args:
            mode: The detected execution mode
            context: Optional session context

        Returns:
            Suggested framework for execution
        """
        if mode == ExecutionMode.WORKFLOW_MODE:
            return SuggestedFramework.MAF
        elif mode == ExecutionMode.CHAT_MODE:
            return SuggestedFramework.CLAUDE
        else:
            # HYBRID_MODE - check context for hints
            if context and context.workflow_active:
                return SuggestedFramework.MAF
            return SuggestedFramework.HYBRID

    def _extract_features(
        self,
        results: List[ClassificationResult],
    ) -> Dict:
        """
        Extract detected features from classification results.

        Args:
            results: List of classification results

        Returns:
            Dict of detected features
        """
        features = {
            "classifier_count": len(results),
            "high_confidence_count": sum(1 for r in results if r.confidence >= 0.8),
            "mode_distribution": {},
        }

        # Count mode distribution
        mode_counts: Dict[str, int] = {}
        for result in results:
            mode_val = result.mode.value
            mode_counts[mode_val] = mode_counts.get(mode_val, 0) + 1

        features["mode_distribution"] = mode_counts

        # Merge metadata from all results
        for result in results:
            if result.metadata:
                features[f"{result.classifier_name}_metadata"] = result.metadata

        return features

    def _create_default_analysis(
        self,
        reasoning: str,
        analysis_time_ms: float,
    ) -> IntentAnalysis:
        """
        Create a default analysis result.

        Args:
            reasoning: Reason for using default
            analysis_time_ms: Time taken for analysis

        Returns:
            Default IntentAnalysis
        """
        return IntentAnalysis(
            mode=self.default_mode,
            confidence=0.5,
            reasoning=reasoning,
            suggested_framework=(
                SuggestedFramework.MAF
                if self.default_mode == ExecutionMode.WORKFLOW_MODE
                else SuggestedFramework.CLAUDE
            ),
            classification_results=[],
            detected_features={},
            analysis_time_ms=analysis_time_ms,
        )

    def get_classifiers(self) -> List[BaseClassifier]:
        """Get all registered classifiers."""
        return self.classifiers.copy()

    def get_enabled_classifiers(self) -> List[BaseClassifier]:
        """Get all enabled classifiers."""
        return [c for c in self.classifiers if c.is_enabled()]

    def set_confidence_threshold(self, threshold: float) -> None:
        """
        Set the confidence threshold.

        Args:
            threshold: New threshold value (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        self.confidence_threshold = threshold
        logger.debug(f"Confidence threshold set to {threshold}")

    def set_default_mode(self, mode: ExecutionMode) -> None:
        """
        Set the default execution mode.

        Args:
            mode: New default mode
        """
        self.default_mode = mode
        logger.debug(f"Default mode set to {mode.value}")

    # =========================================================================
    # Backward Compatibility Methods (Sprint 98)
    # =========================================================================

    async def analyze_intent(
        self,
        user_input: str,
        session_context: Optional[SessionContext] = None,
        history: Optional[List[Message]] = None,
    ) -> IntentAnalysis:
        """
        Backward-compatible alias for select_framework().

        Deprecated: Use select_framework() instead.

        Args:
            user_input: The user's input text to analyze
            session_context: Optional session context for additional info
            history: Optional conversation history

        Returns:
            IntentAnalysis with the detected mode, confidence, and reasoning
        """
        return await self.select_framework(
            user_input=user_input,
            session_context=session_context,
            history=history,
        )


# =============================================================================
# Backward Compatibility Aliases (Sprint 98)
# =============================================================================

# IntentRouter is now FrameworkSelector
IntentRouter = FrameworkSelector

# IntentAnalysis is now FrameworkAnalysis (alias defined in models.py)
# Note: FrameworkAnalysis is the same as IntentAnalysis for backward compatibility
