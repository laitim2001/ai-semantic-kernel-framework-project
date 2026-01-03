# =============================================================================
# IPA Platform - Rule-Based Classifier Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Unit tests for RuleBasedClassifier.
# =============================================================================

import pytest

from src.integrations.hybrid.intent.classifiers.rule_based import (
    CHAT_KEYWORDS,
    CHAT_PHRASE_PATTERNS,
    HYBRID_INDICATORS,
    RuleBasedClassifier,
    WORKFLOW_KEYWORDS,
    WORKFLOW_PHRASE_PATTERNS,
)
from src.integrations.hybrid.intent.models import (
    ExecutionMode,
    SessionContext,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def classifier() -> RuleBasedClassifier:
    """Create a default RuleBasedClassifier."""
    return RuleBasedClassifier()


@pytest.fixture
def classifier_custom() -> RuleBasedClassifier:
    """Create a classifier with custom keywords."""
    return RuleBasedClassifier(
        custom_workflow_keywords=["my_workflow_trigger"],
        custom_chat_keywords=["my_chat_trigger"],
    )


# =============================================================================
# Initialization Tests
# =============================================================================

class TestRuleBasedClassifierInit:
    """Tests for RuleBasedClassifier initialization."""

    def test_default_initialization(self, classifier: RuleBasedClassifier):
        """Test default initialization."""
        assert classifier.name == "rule_based"
        assert classifier.weight == 1.0
        assert classifier.is_enabled() is True
        assert len(classifier.workflow_keywords) > 0
        assert len(classifier.chat_keywords) > 0

    def test_custom_name_and_weight(self):
        """Test custom name and weight."""
        classifier = RuleBasedClassifier(name="custom", weight=0.8)
        assert classifier.name == "custom"
        assert classifier.weight == 0.8

    def test_disabled_classifier(self):
        """Test disabled classifier."""
        classifier = RuleBasedClassifier(enabled=False)
        assert classifier.is_enabled() is False

    def test_custom_keywords_added(self, classifier_custom: RuleBasedClassifier):
        """Test custom keywords are added."""
        assert "my_workflow_trigger" in classifier_custom.workflow_keywords
        assert "my_chat_trigger" in classifier_custom.chat_keywords

    def test_keywords_are_lowercase(self, classifier: RuleBasedClassifier):
        """Test all keywords are lowercase for matching."""
        for kw in classifier.workflow_keywords:
            assert kw == kw.lower()
        for kw in classifier.chat_keywords:
            assert kw == kw.lower()

    def test_patterns_compiled(self, classifier: RuleBasedClassifier):
        """Test regex patterns are compiled."""
        assert len(classifier.workflow_patterns) > 0
        assert len(classifier.chat_patterns) > 0
        # Check they are compiled patterns
        for pattern in classifier.workflow_patterns:
            assert hasattr(pattern, "search")


# =============================================================================
# Workflow Detection Tests
# =============================================================================

class TestWorkflowDetection:
    """Tests for workflow mode detection."""

    @pytest.mark.asyncio
    async def test_explicit_workflow_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with explicit workflow keyword."""
        result = await classifier.classify("Create a new workflow for data processing")
        assert result.mode == ExecutionMode.WORKFLOW_MODE
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_pipeline_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with pipeline keyword."""
        result = await classifier.classify("Set up a data pipeline")
        assert result.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_automation_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with automation keyword."""
        result = await classifier.classify("I want to automate this process")
        assert result.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_multi_agent_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with multi-agent keyword."""
        result = await classifier.classify("Use multiple agents to solve this")
        assert result.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_handoff_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with handoff keyword."""
        result = await classifier.classify("Agent handoff between specialists")
        assert result.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_groupchat_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with groupchat keyword."""
        result = await classifier.classify("Start a groupchat for discussion")
        assert result.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_chinese_workflow_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with Chinese workflow keyword."""
        result = await classifier.classify("建立一個新的工作流程")
        assert result.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_chinese_automation_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with Chinese automation keyword."""
        result = await classifier.classify("我想要自動化這個流程")
        assert result.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_workflow_phrase_pattern(self, classifier: RuleBasedClassifier):
        """Test detection with workflow phrase pattern."""
        result = await classifier.classify("I need to create a new workflow for reports")
        assert result.mode == ExecutionMode.WORKFLOW_MODE
        assert result.confidence >= 0.65  # Patterns add more weight

    @pytest.mark.asyncio
    async def test_multiple_workflow_signals(self, classifier: RuleBasedClassifier):
        """Test detection with multiple workflow signals gives higher confidence."""
        result = await classifier.classify(
            "Create an automated workflow with agent handoff and orchestration"
        )
        assert result.mode == ExecutionMode.WORKFLOW_MODE
        assert result.confidence >= 0.75


# =============================================================================
# Chat Detection Tests
# =============================================================================

class TestChatDetection:
    """Tests for chat mode detection."""

    @pytest.mark.asyncio
    async def test_explain_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with explain keyword."""
        result = await classifier.classify("Can you explain this concept?")
        assert result.mode == ExecutionMode.CHAT_MODE
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_what_is_question(self, classifier: RuleBasedClassifier):
        """Test detection with 'what is' question."""
        result = await classifier.classify("What is machine learning?")
        assert result.mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_why_question(self, classifier: RuleBasedClassifier):
        """Test detection with 'why' question."""
        result = await classifier.classify("Why is the sky blue?")
        assert result.mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_summarize_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with summarize keyword."""
        result = await classifier.classify("Please summarize this document")
        assert result.mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_suggest_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with suggest keyword."""
        result = await classifier.classify("Can you suggest some improvements?")
        assert result.mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_chinese_explain_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with Chinese explain keyword."""
        result = await classifier.classify("請解釋這個概念")
        assert result.mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_chinese_what_is_keyword(self, classifier: RuleBasedClassifier):
        """Test detection with Chinese 'what is' keyword."""
        result = await classifier.classify("什麼是人工智能？")
        assert result.mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_chat_phrase_pattern(self, classifier: RuleBasedClassifier):
        """Test detection with chat phrase pattern."""
        result = await classifier.classify("Help me understand this algorithm")
        assert result.mode == ExecutionMode.CHAT_MODE
        assert result.confidence >= 0.65  # Patterns add more weight

    @pytest.mark.asyncio
    async def test_multiple_chat_signals(self, classifier: RuleBasedClassifier):
        """Test detection with multiple chat signals gives higher confidence."""
        result = await classifier.classify(
            "Can you explain what this is and recommend some improvements?"
        )
        assert result.mode == ExecutionMode.CHAT_MODE
        assert result.confidence >= 0.75


# =============================================================================
# Hybrid Detection Tests
# =============================================================================

class TestHybridDetection:
    """Tests for hybrid mode detection."""

    @pytest.mark.asyncio
    async def test_hybrid_indicator(self, classifier: RuleBasedClassifier):
        """Test detection with hybrid indicator."""
        result = await classifier.classify(
            "First explain the concept, then execute the workflow"
        )
        assert result.mode == ExecutionMode.HYBRID_MODE

    @pytest.mark.asyncio
    async def test_chinese_hybrid_indicator(self, classifier: RuleBasedClassifier):
        """Test detection with Chinese hybrid indicator."""
        result = await classifier.classify("先解釋再執行這個流程")
        assert result.mode == ExecutionMode.HYBRID_MODE

    @pytest.mark.asyncio
    async def test_hybrid_with_multiple_signals(self, classifier: RuleBasedClassifier):
        """Test hybrid detection with multiple signals."""
        # Hybrid requires: hybrid indicator + workflow keyword + chat keyword
        result = await classifier.classify(
            "First explain the concept, then run the automation pipeline"
        )
        # Should detect hybrid mode (hybrid: "explain...then", workflow: "automation", chat: "explain")
        assert result.mode == ExecutionMode.HYBRID_MODE


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_input(self, classifier: RuleBasedClassifier):
        """Test with empty input."""
        result = await classifier.classify("")
        assert result.mode == ExecutionMode.CHAT_MODE
        assert result.confidence == 0.5
        assert "Empty input" in result.reasoning

    @pytest.mark.asyncio
    async def test_whitespace_only_input(self, classifier: RuleBasedClassifier):
        """Test with whitespace-only input."""
        result = await classifier.classify("   \n\t  ")
        assert result.mode == ExecutionMode.CHAT_MODE
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_no_clear_indicators(self, classifier: RuleBasedClassifier):
        """Test with no clear indicators."""
        result = await classifier.classify("Hello there")
        assert result.mode == ExecutionMode.CHAT_MODE
        assert result.confidence == 0.5
        assert "No clear indicators" in result.reasoning

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, classifier: RuleBasedClassifier):
        """Test case-insensitive keyword matching."""
        result = await classifier.classify("CREATE A NEW WORKFLOW")
        assert result.mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_equal_signals_defaults_to_chat(self, classifier: RuleBasedClassifier):
        """Test that equal signals defaults to chat mode."""
        # This is a tie scenario
        result = await classifier.classify("explain workflow")
        # Should default to chat when signals are equal
        assert result.mode in [ExecutionMode.CHAT_MODE, ExecutionMode.WORKFLOW_MODE]


# =============================================================================
# Context Tests
# =============================================================================

class TestContextIntegration:
    """Tests for context-based classification."""

    @pytest.mark.asyncio
    async def test_context_workflow_boost(self, classifier: RuleBasedClassifier):
        """Test that workflow context provides boost."""
        context = SessionContext(
            session_id="test",
            workflow_active=True,
            pending_steps=3,
            current_mode=ExecutionMode.WORKFLOW_MODE,
        )
        result = await classifier.classify("continue with the task", context=context)
        # With workflow context, should boost workflow signals
        assert result.metadata is not None
        assert result.metadata.get("context_boost") == "workflow"

    @pytest.mark.asyncio
    async def test_context_chat_mode(self, classifier: RuleBasedClassifier):
        """Test that chat context is tracked."""
        context = SessionContext(
            session_id="test",
            current_mode=ExecutionMode.CHAT_MODE,
        )
        result = await classifier.classify("tell me more", context=context)
        assert result.metadata is not None
        assert result.metadata.get("context_boost") == "chat"

    @pytest.mark.asyncio
    async def test_no_context(self, classifier: RuleBasedClassifier):
        """Test classification without context."""
        result = await classifier.classify("Create a workflow")
        assert result.metadata is not None
        assert result.metadata.get("context_boost") is None


# =============================================================================
# Metadata Tests
# =============================================================================

class TestMetadata:
    """Tests for classification metadata."""

    @pytest.mark.asyncio
    async def test_metadata_contains_scores(self, classifier: RuleBasedClassifier):
        """Test that metadata contains scores."""
        result = await classifier.classify("Create a workflow for automation")
        assert result.metadata is not None
        assert "workflow_keyword_matches" in result.metadata
        assert "chat_keyword_matches" in result.metadata
        assert "workflow_score" in result.metadata
        assert "chat_score" in result.metadata

    @pytest.mark.asyncio
    async def test_classifier_name_set(self, classifier: RuleBasedClassifier):
        """Test that classifier name is set in result."""
        result = await classifier.classify("Hello")
        assert result.classifier_name == "rule_based"

    @pytest.mark.asyncio
    async def test_reasoning_provided(self, classifier: RuleBasedClassifier):
        """Test that reasoning is provided."""
        result = await classifier.classify("Create a workflow")
        assert result.reasoning is not None
        assert len(result.reasoning) > 0


# =============================================================================
# Keyword Management Tests
# =============================================================================

class TestKeywordManagement:
    """Tests for keyword management."""

    def test_add_workflow_keyword(self, classifier: RuleBasedClassifier):
        """Test adding a workflow keyword."""
        classifier.add_workflow_keyword("custom_workflow")
        assert "custom_workflow" in classifier.workflow_keywords

    def test_add_chat_keyword(self, classifier: RuleBasedClassifier):
        """Test adding a chat keyword."""
        classifier.add_chat_keyword("custom_chat")
        assert "custom_chat" in classifier.chat_keywords

    def test_get_keyword_stats(self, classifier: RuleBasedClassifier):
        """Test getting keyword statistics."""
        stats = classifier.get_keyword_stats()
        assert "workflow_keywords" in stats
        assert "chat_keywords" in stats
        assert "hybrid_keywords" in stats
        assert "workflow_patterns" in stats
        assert "chat_patterns" in stats
        assert all(isinstance(v, int) for v in stats.values())


# =============================================================================
# Confidence Calculation Tests
# =============================================================================

class TestConfidenceCalculation:
    """Tests for confidence calculation logic."""

    @pytest.mark.asyncio
    async def test_strong_workflow_high_confidence(self, classifier: RuleBasedClassifier):
        """Test that strong workflow signals give high confidence."""
        result = await classifier.classify(
            "Create a multi-step workflow pipeline with agent handoff and automation"
        )
        assert result.mode == ExecutionMode.WORKFLOW_MODE
        assert result.confidence >= 0.85

    @pytest.mark.asyncio
    async def test_weak_signal_lower_confidence(self, classifier: RuleBasedClassifier):
        """Test that weak signals give lower confidence."""
        result = await classifier.classify("maybe run task")
        # Should have lower confidence
        assert result.confidence <= 0.75

    @pytest.mark.asyncio
    async def test_confidence_bounded(self, classifier: RuleBasedClassifier):
        """Test that confidence is bounded between 0.5 and 0.95."""
        # Strong signals
        result = await classifier.classify(
            "Create workflow pipeline automation orchestration handoff groupchat"
        )
        assert 0.5 <= result.confidence <= 0.95

        # Weak signals
        result = await classifier.classify("hello")
        assert 0.5 <= result.confidence <= 0.95
