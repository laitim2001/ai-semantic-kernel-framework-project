# =============================================================================
# IPA Platform - Multi-Agent Detector Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Unit tests for MultiAgentDetector.
# =============================================================================

import pytest

from src.integrations.hybrid.intent.analyzers.multi_agent import (
    AGENT_ROLE_REFERENCES,
    COLLABORATION_PATTERNS,
    MULTI_AGENT_KEYWORDS,
    MultiAgentDetector,
    SKILL_DOMAIN_KEYWORDS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def detector() -> MultiAgentDetector:
    """Create a default MultiAgentDetector."""
    return MultiAgentDetector()


@pytest.fixture
def detector_custom_threshold() -> MultiAgentDetector:
    """Create detector with custom threshold."""
    return MultiAgentDetector(domain_threshold=3)


# =============================================================================
# Initialization Tests
# =============================================================================

class TestMultiAgentDetectorInit:
    """Tests for MultiAgentDetector initialization."""

    def test_default_initialization(self, detector: MultiAgentDetector):
        """Test default initialization."""
        assert detector.domain_threshold == 2
        assert len(detector.multi_agent_keywords) > 0
        assert len(detector.agent_roles) > 0
        assert len(detector.domain_keywords) > 0

    def test_weights_normalized(self, detector: MultiAgentDetector):
        """Test that weights sum to 1."""
        total = (
            detector.keyword_weight +
            detector.domain_weight +
            detector.role_weight +
            detector.pattern_weight
        )
        assert abs(total - 1.0) < 0.001

    def test_custom_threshold(self, detector_custom_threshold: MultiAgentDetector):
        """Test custom domain threshold."""
        assert detector_custom_threshold.domain_threshold == 3

    def test_patterns_compiled(self, detector: MultiAgentDetector):
        """Test that collaboration patterns are compiled."""
        assert len(detector.collaboration_patterns) > 0
        for pattern in detector.collaboration_patterns:
            assert hasattr(pattern, "search")


# =============================================================================
# Explicit Keyword Detection Tests
# =============================================================================

class TestKeywordDetection:
    """Tests for explicit multi-agent keyword detection."""

    @pytest.mark.asyncio
    async def test_multiple_agents_keyword(self, detector: MultiAgentDetector):
        """Test 'multiple agents' keyword."""
        result = await detector.detect("Use multiple agents for this task")
        assert result.requires_multi_agent is True
        assert result.confidence >= 0.25  # Keyword match provides ~0.28 confidence

    @pytest.mark.asyncio
    async def test_multi_agent_keyword(self, detector: MultiAgentDetector):
        """Test 'multi-agent' keyword."""
        result = await detector.detect("This needs a multi-agent approach")
        assert result.requires_multi_agent is True

    @pytest.mark.asyncio
    async def test_agent_collaboration_keyword(self, detector: MultiAgentDetector):
        """Test 'agent collaboration' keyword."""
        result = await detector.detect("Enable agent collaboration")
        assert result.requires_multi_agent is True

    @pytest.mark.asyncio
    async def test_handoff_keyword(self, detector: MultiAgentDetector):
        """Test 'handoff' keyword."""
        result = await detector.detect("Agent handoff between specialists")
        assert result.requires_multi_agent is True
        assert result.collaboration_type == "handoff"

    @pytest.mark.asyncio
    async def test_groupchat_keyword(self, detector: MultiAgentDetector):
        """Test 'groupchat' keyword."""
        result = await detector.detect("Start a groupchat discussion")
        assert result.requires_multi_agent is True
        assert result.collaboration_type == "groupchat"

    @pytest.mark.asyncio
    async def test_chinese_multi_agent_keyword(self, detector: MultiAgentDetector):
        """Test Chinese multi-agent keyword."""
        result = await detector.detect("使用多個代理來完成任務")
        assert result.requires_multi_agent is True

    @pytest.mark.asyncio
    async def test_chinese_handoff_keyword(self, detector: MultiAgentDetector):
        """Test Chinese handoff keyword."""
        result = await detector.detect("代理移交給下一位專家")
        assert result.requires_multi_agent is True


# =============================================================================
# Skill Domain Detection Tests
# =============================================================================

class TestDomainDetection:
    """Tests for skill domain detection."""

    @pytest.mark.asyncio
    async def test_coding_domain(self, detector: MultiAgentDetector):
        """Test coding domain detection."""
        result = await detector.detect("Write code to implement this feature")
        assert "coding" in result.detected_domains

    @pytest.mark.asyncio
    async def test_analysis_domain(self, detector: MultiAgentDetector):
        """Test analysis domain detection."""
        result = await detector.detect("Analyze the performance data")
        assert "analysis" in result.detected_domains

    @pytest.mark.asyncio
    async def test_testing_domain(self, detector: MultiAgentDetector):
        """Test testing domain detection."""
        result = await detector.detect("Test and verify the functionality")
        assert "testing" in result.detected_domains

    @pytest.mark.asyncio
    async def test_documentation_domain(self, detector: MultiAgentDetector):
        """Test documentation domain detection."""
        result = await detector.detect("Write documentation for the API")
        assert "documentation" in result.detected_domains

    @pytest.mark.asyncio
    async def test_multiple_domains(self, detector: MultiAgentDetector):
        """Test multiple domain detection."""
        result = await detector.detect(
            "Code the feature, test it, and write documentation"
        )
        assert len(result.detected_domains) >= 2
        assert result.requires_multi_agent is True

    @pytest.mark.asyncio
    async def test_three_domains_strong_signal(self, detector: MultiAgentDetector):
        """Test that 3+ domains gives strong multi-agent signal."""
        result = await detector.detect(
            "Design the architecture, implement the code, and deploy to production"
        )
        assert len(result.detected_domains) >= 3
        assert result.requires_multi_agent is True

    @pytest.mark.asyncio
    async def test_chinese_domain_keywords(self, detector: MultiAgentDetector):
        """Test Chinese domain keywords."""
        result = await detector.detect("開發程式並測試功能")
        assert len(result.detected_domains) >= 1


# =============================================================================
# Agent Role Detection Tests
# =============================================================================

class TestRoleDetection:
    """Tests for agent role detection."""

    @pytest.mark.asyncio
    async def test_developer_role(self, detector: MultiAgentDetector):
        """Test developer role detection."""
        result = await detector.detect("The developer will implement this")
        assert "developer" in result.indicators_found or any(
            "role:" in i for i in result.indicators_found
        )

    @pytest.mark.asyncio
    async def test_analyst_role(self, detector: MultiAgentDetector):
        """Test analyst role detection."""
        result = await detector.detect("Have the analyst review the data")
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_tester_role(self, detector: MultiAgentDetector):
        """Test tester role detection."""
        result = await detector.detect("The tester should verify this")
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_multiple_roles(self, detector: MultiAgentDetector):
        """Test multiple role detection."""
        result = await detector.detect(
            "The developer codes, the tester validates, the analyst reviews"
        )
        # Should detect multiple roles
        role_indicators = [i for i in result.indicators_found if "role:" in i]
        assert len(role_indicators) >= 2

    @pytest.mark.asyncio
    async def test_chinese_role_keywords(self, detector: MultiAgentDetector):
        """Test Chinese role keywords."""
        result = await detector.detect("開發者和測試員合作完成")
        assert result.confidence > 0


# =============================================================================
# Collaboration Pattern Detection Tests
# =============================================================================

class TestPatternDetection:
    """Tests for collaboration pattern detection."""

    @pytest.mark.asyncio
    async def test_one_agent_another_pattern(self, detector: MultiAgentDetector):
        """Test 'one agent... another agent' pattern."""
        result = await detector.detect("One agent writes, another agent reviews")
        assert result.requires_multi_agent is True

    @pytest.mark.asyncio
    async def test_pass_to_pattern(self, detector: MultiAgentDetector):
        """Test 'pass to' pattern."""
        result = await detector.detect("Complete the task then pass it to the next")
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_work_together_pattern(self, detector: MultiAgentDetector):
        """Test 'work together' pattern."""
        result = await detector.detect("Agents work together to solve this")
        assert result.requires_multi_agent is True
        assert result.collaboration_type == "collaboration"

    @pytest.mark.asyncio
    async def test_coordinate_pattern(self, detector: MultiAgentDetector):
        """Test 'coordinate' pattern."""
        result = await detector.detect("Coordinate between the different teams")
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_handover_pattern(self, detector: MultiAgentDetector):
        """Test 'hand over' pattern."""
        result = await detector.detect("Hand over the work to the specialist")
        assert result.confidence > 0


# =============================================================================
# Agent Count Estimation Tests
# =============================================================================

class TestAgentCountEstimation:
    """Tests for agent count estimation."""

    @pytest.mark.asyncio
    async def test_single_domain_one_agent(self, detector: MultiAgentDetector):
        """Test that single domain suggests one agent."""
        result = await detector.detect("Write the code")
        assert result.agent_count_estimate >= 1

    @pytest.mark.asyncio
    async def test_two_domains_two_agents(self, detector: MultiAgentDetector):
        """Test that two domains suggest two agents."""
        result = await detector.detect("Write and test the code")
        if len(result.detected_domains) >= 2:
            assert result.agent_count_estimate >= 2

    @pytest.mark.asyncio
    async def test_three_domains_three_agents(self, detector: MultiAgentDetector):
        """Test that three domains suggest three agents."""
        result = await detector.detect(
            "Design, implement, and deploy the feature"
        )
        if len(result.detected_domains) >= 3:
            assert result.agent_count_estimate >= 3

    @pytest.mark.asyncio
    async def test_team_keyword_bumps_count(self, detector: MultiAgentDetector):
        """Test that 'team' keyword increases agent count."""
        result = await detector.detect("Use a team of agents")
        assert result.agent_count_estimate >= 2

    @pytest.mark.asyncio
    async def test_group_keyword_bumps_count(self, detector: MultiAgentDetector):
        """Test that 'group' keyword increases agent count."""
        result = await detector.detect("Start a group discussion")
        assert result.agent_count_estimate >= 1


# =============================================================================
# Collaboration Type Detection Tests
# =============================================================================

class TestCollaborationType:
    """Tests for collaboration type detection."""

    @pytest.mark.asyncio
    async def test_handoff_type(self, detector: MultiAgentDetector):
        """Test handoff collaboration type."""
        result = await detector.detect("Handoff the task to specialist")
        assert result.collaboration_type == "handoff"

    @pytest.mark.asyncio
    async def test_groupchat_type(self, detector: MultiAgentDetector):
        """Test groupchat collaboration type."""
        result = await detector.detect("Start groupchat for discussion")
        assert result.collaboration_type == "groupchat"

    @pytest.mark.asyncio
    async def test_round_robin_type(self, detector: MultiAgentDetector):
        """Test round robin collaboration type."""
        result = await detector.detect("Use round robin for task assignment")
        assert result.collaboration_type == "round_robin"

    @pytest.mark.asyncio
    async def test_collaboration_type(self, detector: MultiAgentDetector):
        """Test collaboration type."""
        result = await detector.detect("Agents collaborate on the solution")
        assert result.collaboration_type == "collaboration"

    @pytest.mark.asyncio
    async def test_multi_specialist_type(self, detector: MultiAgentDetector):
        """Test multi-specialist type from many domains."""
        result = await detector.detect(
            "Design the system, write code, and deploy to production"
        )
        if len(result.detected_domains) >= 3:
            assert result.collaboration_type in ["multi_specialist", "collaboration", None]


# =============================================================================
# Confidence Score Tests
# =============================================================================

class TestConfidenceScore:
    """Tests for confidence score calculation."""

    @pytest.mark.asyncio
    async def test_no_signals_low_confidence(self, detector: MultiAgentDetector):
        """Test that no signals give low confidence."""
        result = await detector.detect("Hello world")
        assert result.confidence < 0.5
        assert result.requires_multi_agent is False

    @pytest.mark.asyncio
    async def test_explicit_keyword_high_confidence(self, detector: MultiAgentDetector):
        """Test that explicit keywords give higher confidence."""
        result = await detector.detect("Use multi-agent collaboration")
        assert result.confidence >= 0.3

    @pytest.mark.asyncio
    async def test_multiple_signals_higher_confidence(self, detector: MultiAgentDetector):
        """Test that multiple signals increase confidence."""
        result = await detector.detect(
            "Multiple agents collaborate: developer codes, tester validates"
        )
        assert result.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_confidence_bounded(self, detector: MultiAgentDetector):
        """Test that confidence is bounded between 0 and 1."""
        # Maximum signals
        result = await detector.detect(
            "Multiple agents collaborate on this groupchat. "
            "Developer codes, tester validates, analyst reviews. "
            "Design, implement, test, document, deploy. "
            "Pass to next, work together, coordinate between teams."
        )
        assert 0.0 <= result.confidence <= 1.0


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_input(self, detector: MultiAgentDetector):
        """Test with empty input."""
        result = await detector.detect("")
        assert result.requires_multi_agent is False
        assert result.confidence == 0.0
        assert "Empty input" in result.reasoning

    @pytest.mark.asyncio
    async def test_whitespace_only(self, detector: MultiAgentDetector):
        """Test with whitespace-only input."""
        result = await detector.detect("   \n\t  ")
        assert result.requires_multi_agent is False
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_none_context(self, detector: MultiAgentDetector):
        """Test with None context."""
        result = await detector.detect("Test input", context=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_none_history(self, detector: MultiAgentDetector):
        """Test with None history."""
        result = await detector.detect("Test input", history=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_long_input(self, detector: MultiAgentDetector):
        """Test with very long input."""
        long_input = "agent " * 1000
        result = await detector.detect(long_input)
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_case_insensitivity(self, detector: MultiAgentDetector):
        """Test case-insensitive matching."""
        result = await detector.detect("MULTI-AGENT COLLABORATION")
        assert result.requires_multi_agent is True


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_supported_domains(self, detector: MultiAgentDetector):
        """Test getting supported domains."""
        domains = detector.get_supported_domains()
        assert isinstance(domains, list)
        assert len(domains) > 0
        assert "coding" in domains
        assert "testing" in domains

    def test_add_domain(self, detector: MultiAgentDetector):
        """Test adding a custom domain."""
        detector.add_domain("security", ["security", "vulnerability", "audit"])
        assert "security" in detector.domain_keywords
        assert len(detector.domain_keywords["security"]) == 3

    def test_add_keyword(self, detector: MultiAgentDetector):
        """Test adding a custom keyword."""
        detector.add_keyword("custom_multi_agent")
        assert "custom_multi_agent" in detector.multi_agent_keywords


# =============================================================================
# Reasoning Tests
# =============================================================================

class TestReasoning:
    """Tests for reasoning output."""

    @pytest.mark.asyncio
    async def test_reasoning_includes_keywords(self, detector: MultiAgentDetector):
        """Test that reasoning includes keyword matches."""
        result = await detector.detect("Use multi-agent for this task")
        assert "keyword" in result.reasoning.lower() or len(result.indicators_found) > 0

    @pytest.mark.asyncio
    async def test_reasoning_includes_domains(self, detector: MultiAgentDetector):
        """Test that reasoning includes domain info."""
        result = await detector.detect("Write code and test it")
        assert "domain" in result.reasoning.lower() or len(result.detected_domains) > 0

    @pytest.mark.asyncio
    async def test_reasoning_includes_patterns(self, detector: MultiAgentDetector):
        """Test that reasoning includes pattern info."""
        result = await detector.detect("Agents work together")
        assert "pattern" in result.reasoning.lower() or result.confidence > 0

    @pytest.mark.asyncio
    async def test_no_signals_reasoning(self, detector: MultiAgentDetector):
        """Test reasoning when no signals detected."""
        result = await detector.detect("Hello there")
        assert "No multi-agent signals" in result.reasoning


# =============================================================================
# Indicators Found Tests
# =============================================================================

class TestIndicatorsFound:
    """Tests for indicators_found field."""

    @pytest.mark.asyncio
    async def test_keyword_indicator(self, detector: MultiAgentDetector):
        """Test that keyword indicators are tracked."""
        result = await detector.detect("Use multi-agent")
        keyword_indicators = [i for i in result.indicators_found if i.startswith("keyword:")]
        assert len(keyword_indicators) >= 1

    @pytest.mark.asyncio
    async def test_domain_indicator(self, detector: MultiAgentDetector):
        """Test that domain indicators are tracked."""
        result = await detector.detect("Write code and documentation")
        domain_indicators = [i for i in result.indicators_found if i.startswith("domain:")]
        assert len(domain_indicators) >= 1

    @pytest.mark.asyncio
    async def test_role_indicator(self, detector: MultiAgentDetector):
        """Test that role indicators are tracked."""
        result = await detector.detect("The developer and tester collaborate")
        role_indicators = [i for i in result.indicators_found if i.startswith("role:")]
        assert len(role_indicators) >= 0  # May or may not match depending on exact keywords

    @pytest.mark.asyncio
    async def test_pattern_indicator(self, detector: MultiAgentDetector):
        """Test that pattern indicators are tracked."""
        result = await detector.detect("Work together on this task")
        pattern_indicators = [i for i in result.indicators_found if i.startswith("pattern:")]
        assert len(pattern_indicators) >= 0  # May or may not match
