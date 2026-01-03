# =============================================================================
# IPA Platform - Intent Models Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Unit tests for intent analysis models.
# =============================================================================

from datetime import datetime

import pytest

from src.integrations.hybrid.intent.models import (
    ClassificationResult,
    ComplexityScore,
    ExecutionMode,
    IntentAnalysis,
    Message,
    MultiAgentAnalysis,
    SessionContext,
    SuggestedFramework,
)


class TestExecutionMode:
    """Tests for ExecutionMode enum."""

    def test_workflow_mode_value(self):
        """Test WORKFLOW_MODE has correct value."""
        assert ExecutionMode.WORKFLOW_MODE.value == "workflow"

    def test_chat_mode_value(self):
        """Test CHAT_MODE has correct value."""
        assert ExecutionMode.CHAT_MODE.value == "chat"

    def test_hybrid_mode_value(self):
        """Test HYBRID_MODE has correct value."""
        assert ExecutionMode.HYBRID_MODE.value == "hybrid"

    def test_is_str_enum(self):
        """Test ExecutionMode is string enum."""
        assert isinstance(ExecutionMode.WORKFLOW_MODE, str)
        assert ExecutionMode.WORKFLOW_MODE == "workflow"

    def test_from_string(self):
        """Test creating ExecutionMode from string."""
        assert ExecutionMode("workflow") == ExecutionMode.WORKFLOW_MODE
        assert ExecutionMode("chat") == ExecutionMode.CHAT_MODE


class TestSuggestedFramework:
    """Tests for SuggestedFramework enum."""

    def test_maf_value(self):
        """Test MAF has correct value."""
        assert SuggestedFramework.MAF.value == "maf"

    def test_claude_value(self):
        """Test CLAUDE has correct value."""
        assert SuggestedFramework.CLAUDE.value == "claude"

    def test_hybrid_value(self):
        """Test HYBRID has correct value."""
        assert SuggestedFramework.HYBRID.value == "hybrid"


class TestClassificationResult:
    """Tests for ClassificationResult model."""

    def test_create_basic_result(self):
        """Test creating a basic classification result."""
        result = ClassificationResult(
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.85,
            reasoning="Multi-step task detected",
            classifier_name="rule_based",
        )
        assert result.mode == ExecutionMode.WORKFLOW_MODE
        assert result.confidence == 0.85
        assert result.reasoning == "Multi-step task detected"
        assert result.classifier_name == "rule_based"
        assert result.metadata == {}

    def test_create_result_with_metadata(self):
        """Test creating a result with metadata."""
        result = ClassificationResult(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.9,
            reasoning="Simple question",
            classifier_name="llm_based",
            metadata={"keywords": ["help", "explain"]},
        )
        assert result.metadata["keywords"] == ["help", "explain"]

    def test_confidence_validation_min(self):
        """Test confidence minimum validation."""
        with pytest.raises(ValueError):
            ClassificationResult(
                mode=ExecutionMode.CHAT_MODE,
                confidence=-0.1,
                reasoning="test",
                classifier_name="test",
            )

    def test_confidence_validation_max(self):
        """Test confidence maximum validation."""
        with pytest.raises(ValueError):
            ClassificationResult(
                mode=ExecutionMode.CHAT_MODE,
                confidence=1.1,
                reasoning="test",
                classifier_name="test",
            )


class TestIntentAnalysis:
    """Tests for IntentAnalysis model."""

    def test_create_basic_analysis(self):
        """Test creating a basic intent analysis."""
        analysis = IntentAnalysis(
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.85,
            reasoning="Workflow keywords detected",
        )
        assert analysis.mode == ExecutionMode.WORKFLOW_MODE
        assert analysis.confidence == 0.85
        assert analysis.suggested_framework == SuggestedFramework.CLAUDE
        assert analysis.classification_results == []

    def test_create_analysis_with_framework(self):
        """Test creating analysis with suggested framework."""
        analysis = IntentAnalysis(
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.9,
            reasoning="Complex workflow",
            suggested_framework=SuggestedFramework.MAF,
        )
        assert analysis.suggested_framework == SuggestedFramework.MAF

    def test_create_analysis_with_results(self):
        """Test creating analysis with classification results."""
        results = [
            ClassificationResult(
                mode=ExecutionMode.WORKFLOW_MODE,
                confidence=0.8,
                reasoning="Keywords",
                classifier_name="rule_based",
            ),
            ClassificationResult(
                mode=ExecutionMode.WORKFLOW_MODE,
                confidence=0.9,
                reasoning="Complexity",
                classifier_name="complexity",
            ),
        ]
        analysis = IntentAnalysis(
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.85,
            reasoning="Multiple classifiers agree",
            classification_results=results,
        )
        assert len(analysis.classification_results) == 2

    def test_created_at_default(self):
        """Test created_at has default value."""
        analysis = IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.5,
            reasoning="test",
        )
        assert analysis.created_at is not None
        assert isinstance(analysis.created_at, datetime)

    def test_analysis_time_ms(self):
        """Test analysis_time_ms is optional."""
        analysis = IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.5,
            reasoning="test",
            analysis_time_ms=15.5,
        )
        assert analysis.analysis_time_ms == 15.5


class TestSessionContext:
    """Tests for SessionContext model."""

    def test_create_empty_context(self):
        """Test creating an empty session context."""
        context = SessionContext()
        assert context.session_id is None
        assert context.current_mode is None
        assert context.message_count == 0
        assert context.tool_call_count == 0
        assert context.workflow_active is False
        assert context.pending_steps == 0

    def test_create_context_with_session_id(self):
        """Test creating context with session ID."""
        context = SessionContext(session_id="sess_123")
        assert context.session_id == "sess_123"

    def test_create_context_with_mode(self):
        """Test creating context with current mode."""
        context = SessionContext(
            session_id="sess_123",
            current_mode=ExecutionMode.WORKFLOW_MODE,
            workflow_active=True,
            pending_steps=3,
        )
        assert context.current_mode == ExecutionMode.WORKFLOW_MODE
        assert context.workflow_active is True
        assert context.pending_steps == 3

    def test_context_variables(self):
        """Test context variables."""
        context = SessionContext(
            context_variables={"user_id": "user_123", "language": "zh-TW"}
        )
        assert context.context_variables["user_id"] == "user_123"
        assert context.context_variables["language"] == "zh-TW"


class TestMessage:
    """Tests for Message model."""

    def test_create_basic_message(self):
        """Test creating a basic message."""
        message = Message(role="user", content="Hello, world!")
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.tool_calls == []

    def test_create_message_with_timestamp(self):
        """Test creating message with timestamp."""
        ts = datetime.utcnow()
        message = Message(role="assistant", content="Hi!", timestamp=ts)
        assert message.timestamp == ts

    def test_create_message_with_tool_calls(self):
        """Test creating message with tool calls."""
        message = Message(
            role="assistant",
            content="Let me check that.",
            tool_calls=[{"name": "search", "arguments": {"query": "test"}}],
        )
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0]["name"] == "search"


class TestComplexityScore:
    """Tests for ComplexityScore model."""

    def test_create_basic_score(self):
        """Test creating a basic complexity score."""
        score = ComplexityScore(total_score=0.5)
        assert score.total_score == 0.5
        assert score.step_count_estimate == 0
        assert score.requires_multi_agent is False

    def test_create_detailed_score(self):
        """Test creating a detailed complexity score."""
        score = ComplexityScore(
            total_score=0.8,
            step_count_estimate=5,
            resource_dependency_count=3,
            estimated_duration_minutes=10.0,
            requires_persistence=True,
            requires_multi_agent=True,
            reasoning="Complex workflow with multiple dependencies",
        )
        assert score.total_score == 0.8
        assert score.step_count_estimate == 5
        assert score.requires_persistence is True

    def test_score_validation_min(self):
        """Test score minimum validation."""
        with pytest.raises(ValueError):
            ComplexityScore(total_score=-0.1)

    def test_score_validation_max(self):
        """Test score maximum validation."""
        with pytest.raises(ValueError):
            ComplexityScore(total_score=1.1)


class TestMultiAgentAnalysis:
    """Tests for MultiAgentAnalysis model."""

    def test_create_basic_analysis(self):
        """Test creating a basic multi-agent analysis."""
        analysis = MultiAgentAnalysis()
        assert analysis.requires_multi_agent is False
        assert analysis.detected_agent_types == []
        assert analysis.confidence == 0.5

    def test_create_multi_agent_required(self):
        """Test creating analysis with multi-agent required."""
        analysis = MultiAgentAnalysis(
            requires_multi_agent=True,
            detected_agent_types=["coordinator", "executor", "reviewer"],
            collaboration_pattern="pipeline",
            confidence=0.85,
            reasoning="Multiple distinct roles detected",
        )
        assert analysis.requires_multi_agent is True
        assert len(analysis.detected_agent_types) == 3
        assert analysis.collaboration_pattern == "pipeline"
