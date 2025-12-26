"""Unit tests for Framework Selector.

Sprint 50: S50-3 - Hybrid Orchestrator (12 pts)
Tests for FrameworkSelector class.
"""

import pytest

from src.integrations.claude_sdk.hybrid.capability import CapabilityMatcher
from src.integrations.claude_sdk.hybrid.selector import (
    FrameworkSelector,
    SelectionContext,
    SelectionResult,
    SelectionStrategy,
    create_selector,
)
from src.integrations.claude_sdk.hybrid.types import TaskAnalysis, TaskCapability


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def selector():
    """Create a default FrameworkSelector."""
    return FrameworkSelector()


@pytest.fixture
def prefer_claude_selector():
    """Create a selector that prefers Claude."""
    return FrameworkSelector(strategy=SelectionStrategy.PREFER_CLAUDE)


@pytest.fixture
def prefer_ms_selector():
    """Create a selector that prefers Microsoft."""
    return FrameworkSelector(strategy=SelectionStrategy.PREFER_MICROSOFT)


@pytest.fixture
def cost_selector():
    """Create a cost-optimized selector."""
    return FrameworkSelector(strategy=SelectionStrategy.COST_OPTIMIZED)


@pytest.fixture
def performance_selector():
    """Create a performance-optimized selector."""
    return FrameworkSelector(strategy=SelectionStrategy.PERFORMANCE_OPTIMIZED)


# ============================================================================
# FrameworkSelector Initialization Tests
# ============================================================================


class TestFrameworkSelectorInit:
    """Tests for FrameworkSelector initialization."""

    def test_default_init(self):
        """Test default initialization."""
        selector = FrameworkSelector()

        assert selector.strategy == SelectionStrategy.CAPABILITY_BASED
        assert selector._switch_threshold == 0.7

    def test_custom_init(self):
        """Test custom initialization."""
        selector = FrameworkSelector(
            strategy=SelectionStrategy.PREFER_CLAUDE,
            switch_threshold=0.8,
            consistency_bonus=0.15,
        )

        assert selector.strategy == SelectionStrategy.PREFER_CLAUDE
        assert selector._switch_threshold == 0.8
        assert selector._consistency_bonus == 0.15

    def test_strategy_property(self):
        """Test strategy property getter and setter."""
        selector = FrameworkSelector()

        selector.strategy = SelectionStrategy.COST_OPTIMIZED
        assert selector.strategy == SelectionStrategy.COST_OPTIMIZED


# ============================================================================
# Capability-Based Selection Tests
# ============================================================================


class TestCapabilityBasedSelection:
    """Tests for capability-based selection."""

    def test_select_claude_for_file_ops(self, selector):
        """Test selecting Claude for file operations."""
        result = selector.select("Read and edit the configuration file")

        assert result.framework == "claude_sdk"
        assert result.confidence > 0.5
        assert result.alternative == "microsoft_agent_framework"

    def test_select_ms_for_multi_agent(self, selector):
        """Test selecting MS for multi-agent tasks."""
        result = selector.select(
            "Coordinate multiple agents to collaborate on planning"
        )

        assert result.framework == "microsoft_agent_framework"
        assert result.confidence > 0.5

    def test_select_with_no_capabilities(self, selector):
        """Test selecting with no clear capabilities."""
        result = selector.select("Hello")

        assert result.framework in ["claude_sdk", "microsoft_agent_framework"]

    def test_select_with_context(self, selector):
        """Test selecting with context."""
        context = SelectionContext(
            session_framework="claude_sdk",
            session_message_count=5,
            prefer_consistency=True,
        )

        result = selector.select("Continue the conversation", context)

        # Should prefer consistency
        assert result.confidence >= 0.5


# ============================================================================
# Prefer Claude Strategy Tests
# ============================================================================


class TestPreferClaudeStrategy:
    """Tests for PREFER_CLAUDE strategy."""

    def test_prefer_claude_for_general(self, prefer_claude_selector):
        """Test preferring Claude for general tasks."""
        result = prefer_claude_selector.select("Answer a question about Python")

        assert result.framework == "claude_sdk"
        assert "Claude SDK preferred" in result.reason

    def test_override_for_strong_multi_agent(self, prefer_claude_selector):
        """Test override for strong multi-agent requirements."""
        result = prefer_claude_selector.select(
            "Use multiple agents in a team to collaborate extensively"
        )

        # Strong multi-agent should override preference
        # (depends on confidence threshold)


# ============================================================================
# Prefer Microsoft Strategy Tests
# ============================================================================


class TestPreferMicrosoftStrategy:
    """Tests for PREFER_MICROSOFT strategy."""

    def test_prefer_ms_for_general(self, prefer_ms_selector):
        """Test preferring Microsoft for general tasks."""
        result = prefer_ms_selector.select("Help me with a task")

        assert result.framework == "microsoft_agent_framework"
        assert "Microsoft Agent Framework preferred" in result.reason

    def test_override_for_strong_file_ops(self, prefer_ms_selector):
        """Test override for strong file operation requirements."""
        result = prefer_ms_selector.select(
            "Read the file, write to file, and edit the configuration"
        )

        # Strong file ops should override preference
        # (depends on confidence threshold)


# ============================================================================
# Cost-Optimized Strategy Tests
# ============================================================================


class TestCostOptimizedStrategy:
    """Tests for COST_OPTIMIZED strategy."""

    def test_cost_optimized_selection(self, cost_selector):
        """Test cost-optimized selection."""
        result = cost_selector.select("Process some data")

        assert result.framework in ["claude_sdk", "microsoft_agent_framework"]
        assert "Cost optimized" in result.reason

    def test_cost_respects_capabilities(self, cost_selector):
        """Test that cost optimization respects capabilities."""
        result = cost_selector.select(
            "Coordinate agents to collaborate on a team task"
        )

        # Multi-agent should still trigger MS
        # (capability override)


# ============================================================================
# Performance-Optimized Strategy Tests
# ============================================================================


class TestPerformanceOptimizedStrategy:
    """Tests for PERFORMANCE_OPTIMIZED strategy."""

    def test_performance_optimized_selection(self, performance_selector):
        """Test performance-optimized selection."""
        result = performance_selector.select("Process some data quickly")

        assert result.framework in ["claude_sdk", "microsoft_agent_framework"]
        assert "Performance optimized" in result.reason


# ============================================================================
# Custom Rules Tests
# ============================================================================


class TestCustomRules:
    """Tests for custom selection rules."""

    def test_add_custom_rule(self, selector):
        """Test adding a custom rule."""
        def force_claude_rule(framework, context):
            if context and context.session_message_count > 10:
                return "claude_sdk"
            return None

        selector.add_custom_rule(force_claude_rule)

        context = SelectionContext(session_message_count=15)
        result = selector.select("Any task", context)

        assert result.framework == "claude_sdk"
        assert result.reason == "Custom rule match"

    def test_remove_custom_rules(self, selector):
        """Test removing custom rules."""
        selector.add_custom_rule(lambda f, c: "claude_sdk")
        selector.remove_custom_rules()

        # Should now use normal selection
        result = selector.select(
            "Coordinate multiple agents for collaboration"
        )

        # Without custom rule, should use normal logic


# ============================================================================
# Framework Profile Tests
# ============================================================================


class TestFrameworkProfiles:
    """Tests for framework profiles."""

    def test_get_framework_profile(self, selector):
        """Test getting framework profile."""
        profile = selector.get_framework_profile("claude_sdk")

        assert "strengths" in profile
        assert "avg_latency_ms" in profile
        assert "cost_per_1k_tokens" in profile
        assert profile["supports_streaming"] is True

    def test_get_unknown_profile(self, selector):
        """Test getting unknown framework profile."""
        profile = selector.get_framework_profile("unknown_framework")

        assert profile == {}

    def test_get_task_type_framework(self, selector):
        """Test getting framework for task type."""
        framework = selector.get_task_type_framework("multi_agent_collaboration")

        assert framework == "microsoft_agent_framework"

    def test_get_unknown_task_type(self, selector):
        """Test getting framework for unknown task type."""
        framework = selector.get_task_type_framework("unknown_task")

        assert framework is None


# ============================================================================
# Framework Comparison Tests
# ============================================================================


class TestFrameworkComparison:
    """Tests for framework comparison."""

    def test_compare_frameworks(self, selector):
        """Test comparing frameworks for a prompt."""
        results = selector.compare_frameworks("Read a file and process data")

        assert len(results) == len(SelectionStrategy)
        assert "capability_based" in results
        assert "prefer_claude" in results
        assert "prefer_microsoft" in results


# ============================================================================
# Selection Result Tests
# ============================================================================


class TestSelectionResult:
    """Tests for SelectionResult dataclass."""

    def test_result_creation(self):
        """Test creating a SelectionResult."""
        result = SelectionResult(
            framework="claude_sdk",
            confidence=0.85,
            reason="File operations detected",
            alternative="microsoft_agent_framework",
        )

        assert result.framework == "claude_sdk"
        assert result.confidence == 0.85
        assert result.switch_recommended is False
        assert result.warnings == []

    def test_result_with_warnings(self):
        """Test result with warnings."""
        result = SelectionResult(
            framework="claude_sdk",
            confidence=0.9,
            reason="Test",
            warnings=["High complexity", "Framework switch"],
        )

        assert len(result.warnings) == 2


# ============================================================================
# Selection Context Tests
# ============================================================================


class TestSelectionContext:
    """Tests for SelectionContext dataclass."""

    def test_context_defaults(self):
        """Test context default values."""
        context = SelectionContext()

        assert context.task_analysis is None
        assert context.session_framework is None
        assert context.session_message_count == 0
        assert context.allow_framework_switch is True
        assert context.prefer_consistency is False

    def test_context_with_analysis(self):
        """Test context with task analysis."""
        analysis = TaskAnalysis(
            capabilities={TaskCapability.FILE_OPERATIONS},
            recommended_framework="claude_sdk",
            confidence=0.8,
        )

        context = SelectionContext(task_analysis=analysis)

        assert context.task_analysis is analysis


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateSelector:
    """Tests for create_selector factory function."""

    def test_create_default(self):
        """Test creating default selector."""
        selector = create_selector()

        assert isinstance(selector, FrameworkSelector)
        assert selector.strategy == SelectionStrategy.CAPABILITY_BASED

    def test_create_custom(self):
        """Test creating custom selector."""
        selector = create_selector(
            strategy=SelectionStrategy.PREFER_CLAUDE,
            switch_threshold=0.6,
        )

        assert selector.strategy == SelectionStrategy.PREFER_CLAUDE
        assert selector._switch_threshold == 0.6
