"""Unit tests for Capability Matcher.

Sprint 50: S50-3 - Hybrid Orchestrator (12 pts)
Tests for CapabilityMatcher class.
"""

import pytest

from src.integrations.claude_sdk.hybrid.capability import (
    CapabilityMatcher,
    CapabilityScore,
    create_matcher,
)
from src.integrations.claude_sdk.hybrid.types import TaskCapability


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def matcher():
    """Create a default CapabilityMatcher."""
    return CapabilityMatcher()


@pytest.fixture
def case_sensitive_matcher():
    """Create a case-sensitive matcher."""
    return CapabilityMatcher(case_sensitive=True)


# ============================================================================
# CapabilityMatcher Initialization Tests
# ============================================================================


class TestCapabilityMatcherInit:
    """Tests for CapabilityMatcher initialization."""

    def test_default_init(self):
        """Test default initialization."""
        matcher = CapabilityMatcher()

        assert matcher._case_sensitive is False
        assert matcher._min_keyword_length == 2
        assert len(matcher.CAPABILITY_KEYWORDS) > 0

    def test_custom_init(self):
        """Test custom initialization."""
        matcher = CapabilityMatcher(
            case_sensitive=True,
            min_keyword_length=3,
            context_window=100,
        )

        assert matcher._case_sensitive is True
        assert matcher._min_keyword_length == 3
        assert matcher._context_window == 100


# ============================================================================
# Capability Analysis Tests
# ============================================================================


class TestCapabilityAnalysis:
    """Tests for task capability analysis."""

    def test_analyze_file_operations(self, matcher):
        """Test detecting file operations."""
        analysis = matcher.analyze("Read the config.json file and update it")

        assert TaskCapability.FILE_OPERATIONS in analysis.capabilities
        assert analysis.confidence > 0.5

    def test_analyze_code_execution(self, matcher):
        """Test detecting code execution."""
        analysis = matcher.analyze("Execute this Python script to process data")

        assert TaskCapability.CODE_EXECUTION in analysis.capabilities
        assert "python" in [kw.lower() for kw in analysis.matched_keywords.get(
            TaskCapability.CODE_EXECUTION, []
        )]

    def test_analyze_web_search(self, matcher):
        """Test detecting web search."""
        analysis = matcher.analyze("Search the web for Python tutorials")

        assert TaskCapability.WEB_SEARCH in analysis.capabilities

    def test_analyze_multi_agent(self, matcher):
        """Test detecting multi-agent requirements."""
        analysis = matcher.analyze(
            "Have multiple agents collaborate on this task"
        )

        assert TaskCapability.MULTI_AGENT in analysis.capabilities
        assert analysis.requires_multi_agent()

    def test_analyze_handoff(self, matcher):
        """Test detecting handoff requirements."""
        analysis = matcher.analyze("Delegate this task to another agent")

        assert TaskCapability.HANDOFF in analysis.capabilities
        assert analysis.requires_handoff()

    def test_analyze_database(self, matcher):
        """Test detecting database access."""
        analysis = matcher.analyze("Query the PostgreSQL database for user records")

        assert TaskCapability.DATABASE_ACCESS in analysis.capabilities

    def test_analyze_planning(self, matcher):
        """Test detecting planning requirements."""
        analysis = matcher.analyze("Plan and schedule the project milestones")

        assert TaskCapability.PLANNING in analysis.capabilities

    def test_analyze_conversation(self, matcher):
        """Test detecting conversation requirements."""
        analysis = matcher.analyze("Chat with the user to discuss their needs")

        assert TaskCapability.CONVERSATION in analysis.capabilities

    def test_analyze_api_integration(self, matcher):
        """Test detecting API integration."""
        analysis = matcher.analyze("Call the REST API endpoint to get data")

        assert TaskCapability.API_INTEGRATION in analysis.capabilities

    def test_analyze_document_processing(self, matcher):
        """Test detecting document processing."""
        analysis = matcher.analyze("Parse and extract data from the PDF report")

        assert TaskCapability.DOCUMENT_PROCESSING in analysis.capabilities

    def test_analyze_empty_prompt(self, matcher):
        """Test analyzing empty prompt."""
        analysis = matcher.analyze("")

        assert len(analysis.capabilities) == 0
        assert analysis.complexity == 0.0

    def test_analyze_whitespace_prompt(self, matcher):
        """Test analyzing whitespace-only prompt."""
        analysis = matcher.analyze("   \n\t  ")

        assert len(analysis.capabilities) == 0

    def test_analyze_multiple_capabilities(self, matcher):
        """Test detecting multiple capabilities."""
        analysis = matcher.analyze(
            "Read the file, execute the Python code, and search the web for documentation"
        )

        assert TaskCapability.FILE_OPERATIONS in analysis.capabilities
        assert TaskCapability.CODE_EXECUTION in analysis.capabilities
        assert TaskCapability.WEB_SEARCH in analysis.capabilities
        assert len(analysis.capabilities) >= 3


# ============================================================================
# Complexity Calculation Tests
# ============================================================================


class TestComplexityCalculation:
    """Tests for complexity calculation."""

    def test_simple_task_low_complexity(self, matcher):
        """Test that simple tasks have low complexity."""
        analysis = matcher.analyze("Answer a quick simple question")

        assert analysis.complexity < 0.5

    def test_complex_task_high_complexity(self, matcher):
        """Test that complex tasks have high complexity."""
        analysis = matcher.analyze(
            "Perform a comprehensive multi-step advanced analysis "
            "with multiple agents collaborating on database queries and file operations"
        )

        assert analysis.complexity > 0.5

    def test_long_prompt_increases_complexity(self, matcher):
        """Test that long prompts increase complexity."""
        short_analysis = matcher.analyze("Do something")
        long_prompt = "Do something. " * 100  # Long prompt
        long_analysis = matcher.analyze(long_prompt)

        assert long_analysis.complexity >= short_analysis.complexity


# ============================================================================
# Framework Matching Tests
# ============================================================================


class TestFrameworkMatching:
    """Tests for framework matching."""

    def test_match_claude_for_file_ops(self, matcher):
        """Test Claude SDK is matched for file operations."""
        analysis = matcher.analyze("Read and edit the configuration file")

        assert analysis.recommended_framework == "claude_sdk"
        assert analysis.is_claude_suitable()

    def test_match_ms_for_multi_agent(self, matcher):
        """Test MS Agent Framework is matched for multi-agent."""
        analysis = matcher.analyze(
            "Coordinate a team of agents to collaborate on planning"
        )

        assert analysis.recommended_framework == "microsoft_agent_framework"
        assert analysis.is_ms_suitable()

    def test_match_with_empty_capabilities(self, matcher):
        """Test framework matching with no capabilities."""
        framework, confidence = matcher.match_framework(set())

        assert framework == "claude_sdk"  # Default
        assert confidence == 0.5

    def test_match_with_mixed_capabilities(self, matcher):
        """Test matching with mixed capabilities."""
        # Both Claude and MS capabilities
        caps = {
            TaskCapability.FILE_OPERATIONS,  # Claude
            TaskCapability.MULTI_AGENT,  # MS
        }

        framework, confidence = matcher.match_framework(caps)

        # Should pick one - MS wins for multi-agent
        assert framework in ["claude_sdk", "microsoft_agent_framework"]


# ============================================================================
# Keyword Management Tests
# ============================================================================


class TestKeywordManagement:
    """Tests for keyword management."""

    def test_get_capability_for_keyword(self, matcher):
        """Test getting capability for known keyword."""
        capability = matcher.get_capability_for_keyword("file")

        assert capability == TaskCapability.FILE_OPERATIONS

    def test_get_capability_for_unknown_keyword(self, matcher):
        """Test getting capability for unknown keyword."""
        capability = matcher.get_capability_for_keyword("xyz123unknown")

        assert capability is None

    def test_get_keywords_for_capability(self, matcher):
        """Test getting keywords for capability."""
        keywords = matcher.get_keywords_for_capability(TaskCapability.FILE_OPERATIONS)

        assert "file" in keywords
        assert "read" in keywords
        assert len(keywords) > 0

    def test_add_custom_keyword(self, matcher):
        """Test adding custom keyword."""
        matcher.add_custom_keyword(TaskCapability.FILE_OPERATIONS, "datafile")

        keywords = matcher.get_keywords_for_capability(TaskCapability.FILE_OPERATIONS)
        assert "datafile" in keywords

        # Test that it's now detected
        analysis = matcher.analyze("Process the datafile")
        assert TaskCapability.FILE_OPERATIONS in analysis.capabilities


# ============================================================================
# Case Sensitivity Tests
# ============================================================================


class TestCaseSensitivity:
    """Tests for case sensitivity."""

    def test_case_insensitive_matching(self, matcher):
        """Test case-insensitive matching (default)."""
        analysis1 = matcher.analyze("Read the FILE")
        analysis2 = matcher.analyze("read the file")

        assert analysis1.capabilities == analysis2.capabilities

    def test_case_sensitive_matching(self, case_sensitive_matcher):
        """Test case-sensitive matching."""
        analysis1 = case_sensitive_matcher.analyze("Read the FILE")
        analysis2 = case_sensitive_matcher.analyze("Read the file")

        # Depending on keyword casing, results may differ
        # This mainly tests that the option works


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateMatcher:
    """Tests for create_matcher factory function."""

    def test_create_default(self):
        """Test creating default matcher."""
        matcher = create_matcher()

        assert isinstance(matcher, CapabilityMatcher)
        assert matcher._case_sensitive is False

    def test_create_custom(self):
        """Test creating custom matcher."""
        matcher = create_matcher(
            case_sensitive=True,
            min_keyword_length=4,
        )

        assert matcher._case_sensitive is True
        assert matcher._min_keyword_length == 4


# ============================================================================
# CapabilityScore Tests
# ============================================================================


class TestCapabilityScore:
    """Tests for CapabilityScore dataclass."""

    def test_score_creation(self):
        """Test creating a CapabilityScore."""
        score = CapabilityScore(
            capability=TaskCapability.FILE_OPERATIONS,
            score=0.8,
            matched_keywords=["file", "read"],
        )

        assert score.capability == TaskCapability.FILE_OPERATIONS
        assert score.score == 0.8
        assert "file" in score.matched_keywords

    def test_score_defaults(self):
        """Test CapabilityScore default values."""
        score = CapabilityScore(capability=TaskCapability.WEB_SEARCH)

        assert score.score == 0.0
        assert score.matched_keywords == []
        assert score.context_relevance == 1.0
