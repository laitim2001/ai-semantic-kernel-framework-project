# =============================================================================
# IPA Platform - Intent Router Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Unit tests for IntentRouter class.
# =============================================================================

from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.hybrid.intent.classifiers.base import BaseClassifier
from src.integrations.hybrid.intent.models import (
    ClassificationResult,
    ExecutionMode,
    IntentAnalysis,
    Message,
    SessionContext,
    SuggestedFramework,
)
from src.integrations.hybrid.intent.router import IntentRouter


class MockClassifier(BaseClassifier):
    """Mock classifier for testing."""

    def __init__(
        self,
        name: str = "mock",
        mode: ExecutionMode = ExecutionMode.CHAT_MODE,
        confidence: float = 0.8,
        weight: float = 1.0,
        enabled: bool = True,
        raise_error: bool = False,
    ):
        super().__init__(name=name, weight=weight, enabled=enabled)
        self._mode = mode
        self._confidence = confidence
        self._raise_error = raise_error

    async def classify(
        self,
        input_text: str,
        context: Optional[SessionContext] = None,
        history: Optional[List[Message]] = None,
    ) -> ClassificationResult:
        if self._raise_error:
            raise Exception("Mock classifier error")
        return ClassificationResult(
            mode=self._mode,
            confidence=self._confidence,
            reasoning=f"Mock classification for: {input_text[:20]}...",
            classifier_name=self.name,
        )


class TestIntentRouterInit:
    """Tests for IntentRouter initialization."""

    def test_init_default(self):
        """Test default initialization."""
        router = IntentRouter()
        assert router.classifiers == []
        assert router.default_mode == ExecutionMode.CHAT_MODE
        assert router.confidence_threshold == 0.7
        assert router.enable_logging is True

    def test_init_with_classifiers(self):
        """Test initialization with classifiers."""
        classifiers = [
            MockClassifier(name="mock1"),
            MockClassifier(name="mock2"),
        ]
        router = IntentRouter(classifiers=classifiers)
        assert len(router.classifiers) == 2

    def test_init_with_default_mode(self):
        """Test initialization with custom default mode."""
        router = IntentRouter(default_mode=ExecutionMode.WORKFLOW_MODE)
        assert router.default_mode == ExecutionMode.WORKFLOW_MODE

    def test_init_with_threshold(self):
        """Test initialization with custom threshold."""
        router = IntentRouter(confidence_threshold=0.9)
        assert router.confidence_threshold == 0.9


class TestIntentRouterClassifierManagement:
    """Tests for classifier management methods."""

    def test_add_classifier(self):
        """Test adding a classifier."""
        router = IntentRouter()
        classifier = MockClassifier(name="test")
        router.add_classifier(classifier)
        assert len(router.classifiers) == 1
        assert router.classifiers[0].name == "test"

    def test_remove_classifier(self):
        """Test removing a classifier."""
        classifier = MockClassifier(name="test")
        router = IntentRouter(classifiers=[classifier])
        result = router.remove_classifier("test")
        assert result is True
        assert len(router.classifiers) == 0

    def test_remove_nonexistent_classifier(self):
        """Test removing a non-existent classifier."""
        router = IntentRouter()
        result = router.remove_classifier("nonexistent")
        assert result is False

    def test_get_classifiers(self):
        """Test getting all classifiers."""
        classifiers = [MockClassifier(name="c1"), MockClassifier(name="c2")]
        router = IntentRouter(classifiers=classifiers)
        result = router.get_classifiers()
        assert len(result) == 2
        # Should return a copy
        result.append(MockClassifier(name="c3"))
        assert len(router.classifiers) == 2

    def test_get_enabled_classifiers(self):
        """Test getting only enabled classifiers."""
        classifiers = [
            MockClassifier(name="c1", enabled=True),
            MockClassifier(name="c2", enabled=False),
            MockClassifier(name="c3", enabled=True),
        ]
        router = IntentRouter(classifiers=classifiers)
        result = router.get_enabled_classifiers()
        assert len(result) == 2


class TestIntentRouterSettings:
    """Tests for router settings methods."""

    def test_set_confidence_threshold(self):
        """Test setting confidence threshold."""
        router = IntentRouter()
        router.set_confidence_threshold(0.8)
        assert router.confidence_threshold == 0.8

    def test_set_confidence_threshold_invalid_low(self):
        """Test setting invalid low threshold."""
        router = IntentRouter()
        with pytest.raises(ValueError):
            router.set_confidence_threshold(-0.1)

    def test_set_confidence_threshold_invalid_high(self):
        """Test setting invalid high threshold."""
        router = IntentRouter()
        with pytest.raises(ValueError):
            router.set_confidence_threshold(1.1)

    def test_set_default_mode(self):
        """Test setting default mode."""
        router = IntentRouter()
        router.set_default_mode(ExecutionMode.WORKFLOW_MODE)
        assert router.default_mode == ExecutionMode.WORKFLOW_MODE


class TestIntentRouterAnalyzeIntent:
    """Tests for analyze_intent method."""

    @pytest.mark.asyncio
    async def test_analyze_empty_input(self):
        """Test analyzing empty input."""
        router = IntentRouter()
        analysis = await router.analyze_intent("")
        assert analysis.mode == ExecutionMode.CHAT_MODE
        assert "Empty input" in analysis.reasoning

    @pytest.mark.asyncio
    async def test_analyze_whitespace_input(self):
        """Test analyzing whitespace-only input."""
        router = IntentRouter()
        analysis = await router.analyze_intent("   ")
        assert analysis.mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_analyze_no_classifiers(self):
        """Test analyzing with no classifiers."""
        router = IntentRouter()
        analysis = await router.analyze_intent("Hello world")
        assert analysis.mode == ExecutionMode.CHAT_MODE
        assert "No classifiers" in analysis.reasoning

    @pytest.mark.asyncio
    async def test_analyze_with_single_classifier(self):
        """Test analyzing with a single classifier."""
        classifier = MockClassifier(
            name="mock",
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.9,
        )
        router = IntentRouter(classifiers=[classifier])
        analysis = await router.analyze_intent("Create a workflow")
        assert analysis.mode == ExecutionMode.WORKFLOW_MODE
        assert analysis.confidence == 0.9

    @pytest.mark.asyncio
    async def test_analyze_with_multiple_classifiers(self):
        """Test analyzing with multiple classifiers."""
        classifiers = [
            MockClassifier(name="c1", mode=ExecutionMode.WORKFLOW_MODE, confidence=0.8),
            MockClassifier(name="c2", mode=ExecutionMode.WORKFLOW_MODE, confidence=0.9),
        ]
        router = IntentRouter(classifiers=classifiers)
        analysis = await router.analyze_intent("Create a workflow")
        assert analysis.mode == ExecutionMode.WORKFLOW_MODE
        assert len(analysis.classification_results) == 2

    @pytest.mark.asyncio
    async def test_analyze_below_threshold(self):
        """Test analyzing with confidence below threshold."""
        classifier = MockClassifier(
            name="mock",
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.5,
        )
        router = IntentRouter(classifiers=[classifier], confidence_threshold=0.7)
        analysis = await router.analyze_intent("Maybe workflow?")
        assert analysis.mode == ExecutionMode.CHAT_MODE  # Falls back to default
        assert "below threshold" in analysis.reasoning

    @pytest.mark.asyncio
    async def test_analyze_with_session_context(self):
        """Test analyzing with session context."""
        classifier = MockClassifier(name="mock", mode=ExecutionMode.CHAT_MODE)
        router = IntentRouter(classifiers=[classifier])
        context = SessionContext(
            session_id="sess_123",
            current_mode=ExecutionMode.WORKFLOW_MODE,
            workflow_active=True,
        )
        analysis = await router.analyze_intent("What's next?", session_context=context)
        assert analysis is not None
        assert analysis.mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_analyze_with_history(self):
        """Test analyzing with conversation history."""
        classifier = MockClassifier(name="mock")
        router = IntentRouter(classifiers=[classifier])
        history = [
            Message(role="user", content="Start workflow"),
            Message(role="assistant", content="Starting..."),
        ]
        analysis = await router.analyze_intent("Continue", history=history)
        assert analysis is not None

    @pytest.mark.asyncio
    async def test_analyze_includes_analysis_time(self):
        """Test that analysis includes timing information."""
        classifier = MockClassifier(name="mock")
        router = IntentRouter(classifiers=[classifier])
        analysis = await router.analyze_intent("Test input")
        assert analysis.analysis_time_ms is not None
        assert analysis.analysis_time_ms >= 0

    @pytest.mark.asyncio
    async def test_analyze_classifier_error_handled(self):
        """Test that classifier errors are handled gracefully."""
        classifiers = [
            MockClassifier(name="error", raise_error=True),
            MockClassifier(name="good", mode=ExecutionMode.CHAT_MODE, confidence=0.8),
        ]
        router = IntentRouter(classifiers=classifiers)
        analysis = await router.analyze_intent("Test input")
        # Should still work with the good classifier
        assert analysis is not None
        assert len(analysis.classification_results) == 1

    @pytest.mark.asyncio
    async def test_analyze_disabled_classifier_skipped(self):
        """Test that disabled classifiers are skipped."""
        classifiers = [
            MockClassifier(name="disabled", enabled=False),
            MockClassifier(name="enabled", mode=ExecutionMode.WORKFLOW_MODE),
        ]
        router = IntentRouter(classifiers=classifiers)
        analysis = await router.analyze_intent("Test input")
        assert len(analysis.classification_results) == 1
        assert analysis.classification_results[0].classifier_name == "enabled"


class TestIntentRouterFrameworkSuggestion:
    """Tests for framework suggestion logic."""

    @pytest.mark.asyncio
    async def test_workflow_mode_suggests_maf(self):
        """Test that WORKFLOW_MODE suggests MAF."""
        classifier = MockClassifier(mode=ExecutionMode.WORKFLOW_MODE, confidence=0.9)
        router = IntentRouter(classifiers=[classifier])
        analysis = await router.analyze_intent("Create workflow")
        assert analysis.suggested_framework == SuggestedFramework.MAF

    @pytest.mark.asyncio
    async def test_chat_mode_suggests_claude(self):
        """Test that CHAT_MODE suggests Claude."""
        classifier = MockClassifier(mode=ExecutionMode.CHAT_MODE, confidence=0.9)
        router = IntentRouter(classifiers=[classifier])
        analysis = await router.analyze_intent("What is AI?")
        assert analysis.suggested_framework == SuggestedFramework.CLAUDE

    @pytest.mark.asyncio
    async def test_hybrid_mode_with_active_workflow(self):
        """Test that HYBRID_MODE with active workflow suggests MAF."""
        classifier = MockClassifier(mode=ExecutionMode.HYBRID_MODE, confidence=0.9)
        router = IntentRouter(classifiers=[classifier])
        context = SessionContext(workflow_active=True)
        analysis = await router.analyze_intent("Continue", session_context=context)
        assert analysis.suggested_framework == SuggestedFramework.MAF

    @pytest.mark.asyncio
    async def test_hybrid_mode_without_workflow(self):
        """Test that HYBRID_MODE without workflow suggests HYBRID."""
        classifier = MockClassifier(mode=ExecutionMode.HYBRID_MODE, confidence=0.9)
        router = IntentRouter(classifiers=[classifier])
        analysis = await router.analyze_intent("Something complex")
        assert analysis.suggested_framework == SuggestedFramework.HYBRID


class TestIntentRouterWeightedVoting:
    """Tests for weighted voting in result aggregation."""

    @pytest.mark.asyncio
    async def test_weighted_voting(self):
        """Test that classifier weights affect results."""
        classifiers = [
            MockClassifier(
                name="low_weight",
                mode=ExecutionMode.CHAT_MODE,
                confidence=0.9,
                weight=0.3,
            ),
            MockClassifier(
                name="high_weight",
                mode=ExecutionMode.WORKFLOW_MODE,
                confidence=0.8,
                weight=0.7,
            ),
        ]
        router = IntentRouter(classifiers=classifiers, confidence_threshold=0.5)
        analysis = await router.analyze_intent("Test input")
        # High weight classifier should win
        assert analysis.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_equal_weights_highest_confidence_wins(self):
        """Test that with equal weights, highest confidence wins."""
        classifiers = [
            MockClassifier(
                name="c1",
                mode=ExecutionMode.CHAT_MODE,
                confidence=0.6,
                weight=1.0,
            ),
            MockClassifier(
                name="c2",
                mode=ExecutionMode.WORKFLOW_MODE,
                confidence=0.9,
                weight=1.0,
            ),
        ]
        router = IntentRouter(classifiers=classifiers, confidence_threshold=0.5)
        analysis = await router.analyze_intent("Test input")
        assert analysis.mode == ExecutionMode.WORKFLOW_MODE


class TestIntentRouterFeatureExtraction:
    """Tests for feature extraction from results."""

    @pytest.mark.asyncio
    async def test_feature_extraction(self):
        """Test that features are extracted from results."""
        classifiers = [
            MockClassifier(name="c1", mode=ExecutionMode.WORKFLOW_MODE, confidence=0.9),
            MockClassifier(name="c2", mode=ExecutionMode.WORKFLOW_MODE, confidence=0.8),
        ]
        router = IntentRouter(classifiers=classifiers)
        analysis = await router.analyze_intent("Test input")
        assert "classifier_count" in analysis.detected_features
        assert analysis.detected_features["classifier_count"] == 2
        assert "high_confidence_count" in analysis.detected_features
        assert "mode_distribution" in analysis.detected_features
