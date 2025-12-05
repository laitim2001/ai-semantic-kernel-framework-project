# =============================================================================
# IPA Platform - Speaker Selector Tests
# =============================================================================
# Sprint 9: S9-2 SpeakerSelector (5 points)
#
# Unit tests for SpeakerSelector and related strategies.
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.domain.orchestration.groupchat.manager import (
    AgentInfo,
    GroupChatConfig,
    GroupChatState,
    GroupChatStatus,
    GroupMessage,
    MessageType,
    SpeakerSelectionMethod,
)
from src.domain.orchestration.groupchat.speaker_selector import (
    AutoStrategy,
    BaseSpeakerStrategy,
    ExpertiseMatcher,
    ExpertiseMatchResult,
    ExpertiseStrategy,
    ManualStrategy,
    PriorityStrategy,
    RandomStrategy,
    RoundRobinStrategy,
    SelectionContext,
    SelectionResult,
    SelectionStrategy,
    SpeakerSelector,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_agents():
    """Create sample agents for testing."""
    return [
        AgentInfo(
            agent_id="agent-1",
            name="Planning Agent",
            description="Handles project planning tasks",
            capabilities=["planning", "scheduling", "coordination"],
            priority=1,
        ),
        AgentInfo(
            agent_id="agent-2",
            name="Technical Agent",
            description="Handles technical implementation",
            capabilities=["coding", "debugging", "testing"],
            priority=2,
        ),
        AgentInfo(
            agent_id="agent-3",
            name="Review Agent",
            description="Reviews and provides feedback",
            capabilities=["review", "feedback", "quality"],
            priority=3,
        ),
        AgentInfo(
            agent_id="agent-4",
            name="Security Agent",
            description="Handles security concerns",
            capabilities=["security", "authentication", "authorization"],
            priority=4,
        ),
    ]


@pytest.fixture
def sample_state(sample_agents):
    """Create a sample group chat state."""
    state = GroupChatState(
        group_id="group-1",
        name="Test Group",
        agents=sample_agents,
        status=GroupChatStatus.ACTIVE,
        current_round=1,
        config=GroupChatConfig(
            speaker_selection_method=SpeakerSelectionMethod.AUTO,
            allow_repeat_speaker=False,
        ),
    )
    return state


@pytest.fixture
def sample_message():
    """Create a sample message."""
    return GroupMessage(
        id="msg-1",
        group_id="group-1",
        sender_id="user",
        sender_name="User",
        content="We need to debug the authentication issue in the system",
        message_type=MessageType.USER,
    )


@pytest.fixture
def selector():
    """Create a SpeakerSelector instance."""
    return SpeakerSelector()


# =============================================================================
# SelectionContext Tests
# =============================================================================

class TestSelectionContext:
    """Tests for SelectionContext dataclass."""

    def test_create_context(self, sample_state, sample_agents, sample_message):
        """Test creating a selection context."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_speaker_id="agent-1",
            last_message=sample_message,
            allow_repeat=False,
            manual_selection=None,
        )

        assert context.state == sample_state
        assert len(context.candidates) == 4
        assert context.last_speaker_id == "agent-1"
        assert context.last_message == sample_message
        assert context.allow_repeat is False
        assert context.manual_selection is None

    def test_context_with_manual_selection(self, sample_state, sample_agents):
        """Test context with manual selection."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            manual_selection="agent-2",
        )

        assert context.manual_selection == "agent-2"


# =============================================================================
# SelectionResult Tests
# =============================================================================

class TestSelectionResult:
    """Tests for SelectionResult dataclass."""

    def test_successful_result(self, sample_agents):
        """Test creating a successful selection result."""
        result = SelectionResult(
            selected_agent=sample_agents[0],
            strategy_used=SelectionStrategy.ROUND_ROBIN,
            confidence=1.0,
            reason="Next in rotation",
        )

        assert result.success is True
        assert result.selected_agent == sample_agents[0]
        assert result.strategy_used == SelectionStrategy.ROUND_ROBIN
        assert result.confidence == 1.0

    def test_failed_result(self):
        """Test creating a failed selection result."""
        result = SelectionResult(
            selected_agent=None,
            strategy_used=SelectionStrategy.MANUAL,
            reason="No agent specified",
        )

        assert result.success is False
        assert result.selected_agent is None

    def test_result_with_alternatives(self, sample_agents):
        """Test result with alternative agents."""
        result = SelectionResult(
            selected_agent=sample_agents[0],
            strategy_used=SelectionStrategy.EXPERTISE,
            alternatives=sample_agents[1:3],
        )

        assert len(result.alternatives) == 2


# =============================================================================
# RoundRobinStrategy Tests
# =============================================================================

class TestRoundRobinStrategy:
    """Tests for RoundRobinStrategy."""

    @pytest.fixture
    def strategy(self):
        return RoundRobinStrategy()

    @pytest.mark.asyncio
    async def test_first_selection(self, strategy, sample_state, sample_agents):
        """Test first speaker selection."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_speaker_id=None,
        )

        result = await strategy.select(context)

        assert result.success is True
        assert result.selected_agent == sample_agents[0]
        assert result.strategy_used == SelectionStrategy.ROUND_ROBIN

    @pytest.mark.asyncio
    async def test_sequential_selection(self, strategy, sample_state, sample_agents):
        """Test sequential round-robin selection."""
        # First selection
        context1 = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_speaker_id=None,
        )
        result1 = await strategy.select(context1)
        assert result1.selected_agent.agent_id == "agent-1"

        # Update state with current speaker
        sample_state.current_speaker_id = "agent-1"

        # Second selection
        context2 = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_speaker_id="agent-1",
        )
        result2 = await strategy.select(context2)
        assert result2.selected_agent.agent_id == "agent-2"

        # Third selection
        sample_state.current_speaker_id = "agent-2"
        context3 = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_speaker_id="agent-2",
        )
        result3 = await strategy.select(context3)
        assert result3.selected_agent.agent_id == "agent-3"

    @pytest.mark.asyncio
    async def test_wrap_around(self, strategy, sample_state, sample_agents):
        """Test wrap-around to first agent after last."""
        sample_state.current_speaker_id = "agent-4"

        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_speaker_id="agent-4",
        )
        result = await strategy.select(context)

        assert result.selected_agent.agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_with_filtered_candidates(self, strategy, sample_state, sample_agents):
        """Test round-robin with some candidates filtered."""
        # Filter out agent-2
        filtered = [a for a in sample_agents if a.agent_id != "agent-2"]
        sample_state.current_speaker_id = "agent-1"

        context = SelectionContext(
            state=sample_state,
            candidates=filtered,
            last_speaker_id="agent-1",
        )
        result = await strategy.select(context)

        # Should skip agent-2 and go to agent-3
        assert result.selected_agent.agent_id == "agent-3"

    @pytest.mark.asyncio
    async def test_empty_candidates(self, strategy, sample_state):
        """Test with no candidates."""
        context = SelectionContext(
            state=sample_state,
            candidates=[],
        )
        result = await strategy.select(context)

        assert result.success is False
        assert result.selected_agent is None


# =============================================================================
# RandomStrategy Tests
# =============================================================================

class TestRandomStrategy:
    """Tests for RandomStrategy."""

    @pytest.fixture
    def strategy(self):
        return RandomStrategy()

    @pytest.mark.asyncio
    async def test_random_selection(self, strategy, sample_state, sample_agents):
        """Test random speaker selection."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
        )

        result = await strategy.select(context)

        assert result.success is True
        assert result.selected_agent in sample_agents
        assert result.strategy_used == SelectionStrategy.RANDOM

    @pytest.mark.asyncio
    async def test_random_distribution(self, strategy, sample_state, sample_agents):
        """Test that random selection distributes across agents."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
        )

        # Run multiple selections
        selections = {}
        for _ in range(100):
            result = await strategy.select(context)
            agent_id = result.selected_agent.agent_id
            selections[agent_id] = selections.get(agent_id, 0) + 1

        # Each agent should be selected at least once
        assert len(selections) == len(sample_agents)
        for agent in sample_agents:
            assert agent.agent_id in selections

    @pytest.mark.asyncio
    async def test_random_with_alternatives(self, strategy, sample_state, sample_agents):
        """Test that alternatives are provided."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
        )

        result = await strategy.select(context)

        assert len(result.alternatives) == len(sample_agents) - 1

    @pytest.mark.asyncio
    async def test_single_candidate(self, strategy, sample_state, sample_agents):
        """Test with single candidate."""
        context = SelectionContext(
            state=sample_state,
            candidates=[sample_agents[0]],
        )

        result = await strategy.select(context)

        assert result.success is True
        assert result.selected_agent == sample_agents[0]


# =============================================================================
# PriorityStrategy Tests
# =============================================================================

class TestPriorityStrategy:
    """Tests for PriorityStrategy."""

    @pytest.fixture
    def strategy(self):
        return PriorityStrategy()

    @pytest.mark.asyncio
    async def test_highest_priority(self, strategy, sample_state, sample_agents):
        """Test selection of highest priority agent."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
        )

        result = await strategy.select(context)

        # agent-1 has priority 1 (highest)
        assert result.success is True
        assert result.selected_agent.agent_id == "agent-1"
        assert result.strategy_used == SelectionStrategy.PRIORITY

    @pytest.mark.asyncio
    async def test_priority_with_filtered(self, strategy, sample_state, sample_agents):
        """Test priority selection with filtered candidates."""
        # Remove agent-1 (highest priority)
        filtered = sample_agents[1:]

        context = SelectionContext(
            state=sample_state,
            candidates=filtered,
        )

        result = await strategy.select(context)

        # agent-2 should be selected (next highest priority)
        assert result.selected_agent.agent_id == "agent-2"

    @pytest.mark.asyncio
    async def test_priority_alternatives(self, strategy, sample_state, sample_agents):
        """Test that alternatives are sorted by priority."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
        )

        result = await strategy.select(context)

        # Should have top alternatives
        assert len(result.alternatives) <= 3

    @pytest.mark.asyncio
    async def test_same_priority(self, strategy, sample_state):
        """Test agents with same priority."""
        agents = [
            AgentInfo(agent_id="a1", name="Agent 1", priority=1),
            AgentInfo(agent_id="a2", name="Agent 2", priority=1),
            AgentInfo(agent_id="a3", name="Agent 3", priority=2),
        ]
        sample_state.agents = agents

        context = SelectionContext(
            state=sample_state,
            candidates=agents,
        )

        result = await strategy.select(context)

        # Should select one of the priority-1 agents
        assert result.selected_agent.priority == 1


# =============================================================================
# ManualStrategy Tests
# =============================================================================

class TestManualStrategy:
    """Tests for ManualStrategy."""

    @pytest.fixture
    def strategy(self):
        return ManualStrategy()

    @pytest.mark.asyncio
    async def test_manual_selection(self, strategy, sample_state, sample_agents):
        """Test manual speaker selection."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            manual_selection="agent-2",
        )

        result = await strategy.select(context)

        assert result.success is True
        assert result.selected_agent.agent_id == "agent-2"
        assert result.strategy_used == SelectionStrategy.MANUAL

    @pytest.mark.asyncio
    async def test_no_manual_selection(self, strategy, sample_state, sample_agents):
        """Test when no manual selection is provided."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            manual_selection=None,
        )

        result = await strategy.select(context)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_invalid_manual_selection(self, strategy, sample_state, sample_agents):
        """Test with invalid agent ID."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            manual_selection="nonexistent-agent",
        )

        result = await strategy.select(context)

        assert result.success is False
        assert "not available" in result.reason

    @pytest.mark.asyncio
    async def test_manual_selection_not_in_candidates(self, strategy, sample_state, sample_agents):
        """Test selecting an agent not in candidates."""
        # Filter to only agent-1 and agent-2
        filtered = sample_agents[:2]

        context = SelectionContext(
            state=sample_state,
            candidates=filtered,
            manual_selection="agent-3",  # Not in filtered list
        )

        result = await strategy.select(context)

        assert result.success is False


# =============================================================================
# ExpertiseMatcher Tests
# =============================================================================

class TestExpertiseMatcher:
    """Tests for ExpertiseMatcher."""

    @pytest.fixture
    def matcher(self):
        return ExpertiseMatcher()

    @pytest.mark.asyncio
    async def test_direct_capability_match(self, matcher, sample_agents):
        """Test direct capability matching."""
        result = await matcher.match_expertise(
            message_content="We need to debug this issue",
            candidates=sample_agents,
        )

        assert result is not None
        # Agent-2 has "debugging" capability
        assert result.best_agent.agent_id == "agent-2"
        assert "debugging" in result.matched_capabilities

    @pytest.mark.asyncio
    async def test_synonym_matching(self, matcher, sample_agents):
        """Test synonym-based matching."""
        result = await matcher.match_expertise(
            message_content="We need to fix this problem",  # "fix" is synonym for "debugging"
            candidates=sample_agents,
        )

        assert result is not None
        assert result.best_agent.agent_id == "agent-2"

    @pytest.mark.asyncio
    async def test_multiple_capabilities_match(self, matcher, sample_agents):
        """Test matching multiple capabilities."""
        result = await matcher.match_expertise(
            message_content="We need to test and debug the code",
            candidates=sample_agents,
        )

        assert result is not None
        assert result.best_agent.agent_id == "agent-2"
        # Should match multiple capabilities
        assert len(result.matched_capabilities) >= 1

    @pytest.mark.asyncio
    async def test_security_capability_match(self, matcher, sample_agents):
        """Test security-related capability matching."""
        result = await matcher.match_expertise(
            message_content="Check the authentication and authorization setup",
            candidates=sample_agents,
        )

        assert result is not None
        assert result.best_agent.agent_id == "agent-4"  # Security Agent

    @pytest.mark.asyncio
    async def test_planning_capability_match(self, matcher, sample_agents):
        """Test planning-related capability matching."""
        result = await matcher.match_expertise(
            message_content="Let's plan the project schedule",
            candidates=sample_agents,
        )

        assert result is not None
        assert result.best_agent.agent_id == "agent-1"  # Planning Agent

    @pytest.mark.asyncio
    async def test_no_match(self, matcher):
        """Test when no capabilities match."""
        agents = [
            AgentInfo(
                agent_id="a1",
                name="Generic Agent",
                capabilities=["general"],
            ),
        ]

        result = await matcher.match_expertise(
            message_content="Some unrelated content xyz abc",
            candidates=agents,
        )

        # Score too low, returns None
        assert result is None

    @pytest.mark.asyncio
    async def test_alternatives_provided(self, matcher, sample_agents):
        """Test that alternatives are provided."""
        result = await matcher.match_expertise(
            message_content="debug the code",
            candidates=sample_agents,
        )

        assert result is not None
        # Should have alternatives for agents with lower scores
        assert isinstance(result.alternatives, list)

    @pytest.mark.asyncio
    async def test_empty_candidates(self, matcher):
        """Test with empty candidate list."""
        result = await matcher.match_expertise(
            message_content="test message",
            candidates=[],
        )

        assert result is None

    def test_calculate_relevance(self, matcher):
        """Test relevance calculation."""
        score, matched = matcher._calculate_relevance(
            capabilities=["coding", "debugging"],
            content_lower="we need to debug the code",
            content_words={"we", "need", "to", "debug", "the", "code"},
        )

        assert score > 0
        assert len(matched) > 0

    def test_custom_synonyms(self):
        """Test with custom synonym map."""
        custom_synonyms = {
            "custom": ["special", "unique"],
        }
        matcher = ExpertiseMatcher(synonym_map=custom_synonyms)

        assert "custom" in matcher._synonyms
        assert "special" in matcher._synonyms["custom"]


# =============================================================================
# ExpertiseStrategy Tests
# =============================================================================

class TestExpertiseStrategy:
    """Tests for ExpertiseStrategy."""

    @pytest.fixture
    def strategy(self):
        return ExpertiseStrategy()

    @pytest.mark.asyncio
    async def test_expertise_selection(self, strategy, sample_state, sample_agents, sample_message):
        """Test expertise-based selection."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_message=sample_message,  # Contains "debug" and "authentication"
        )

        result = await strategy.select(context)

        assert result.success is True
        assert result.strategy_used == SelectionStrategy.EXPERTISE
        # Should match security or technical agent
        assert result.selected_agent.agent_id in ["agent-2", "agent-4"]

    @pytest.mark.asyncio
    async def test_no_message_fallback(self, strategy, sample_state, sample_agents):
        """Test fallback when no message context."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_message=None,
        )

        result = await strategy.select(context)

        # Falls back to first candidate
        assert result.success is True
        assert result.selected_agent == sample_agents[0]


# =============================================================================
# AutoStrategy Tests
# =============================================================================

class TestAutoStrategy:
    """Tests for AutoStrategy."""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.complete = AsyncMock(return_value="agent-2")
        return llm

    @pytest.fixture
    def strategy_with_llm(self, mock_llm):
        return AutoStrategy(llm_client=mock_llm)

    @pytest.fixture
    def strategy_without_llm(self):
        return AutoStrategy(llm_client=None)

    @pytest.mark.asyncio
    async def test_llm_selection(self, strategy_with_llm, sample_state, sample_agents, sample_message):
        """Test LLM-based selection."""
        sample_state.messages.append(sample_message)

        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
            last_message=sample_message,
        )

        result = await strategy_with_llm.select(context)

        assert result.success is True
        assert result.selected_agent.agent_id == "agent-2"
        assert result.strategy_used == SelectionStrategy.AUTO

    @pytest.mark.asyncio
    async def test_fallback_without_llm(self, strategy_without_llm, sample_state, sample_agents):
        """Test fallback to round-robin when no LLM."""
        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
        )

        result = await strategy_without_llm.select(context)

        assert result.success is True
        assert "fallback" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_llm_error_fallback(self, mock_llm, sample_state, sample_agents):
        """Test fallback on LLM error."""
        mock_llm.complete = AsyncMock(side_effect=Exception("LLM error"))
        strategy = AutoStrategy(llm_client=mock_llm)

        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
        )

        result = await strategy.select(context)

        assert result.success is True
        assert "error" in result.reason.lower() or "fallback" in result.reason.lower()

    def test_build_selection_prompt(self, strategy_with_llm, sample_state, sample_agents, sample_message):
        """Test prompt building."""
        sample_state.messages.append(sample_message)

        context = SelectionContext(
            state=sample_state,
            candidates=sample_agents,
        )

        prompt = strategy_with_llm._build_selection_prompt(context)

        assert "Available agents:" in prompt
        assert "agent-1" in prompt
        assert "Planning Agent" in prompt
        assert "respond with" in prompt.lower()

    def test_parse_selection_response(self, strategy_with_llm, sample_agents):
        """Test response parsing."""
        # Direct ID match
        result = strategy_with_llm._parse_selection_response("agent-2", sample_agents)
        assert result == "agent-2"

        # Name match
        result = strategy_with_llm._parse_selection_response("Technical Agent", sample_agents)
        assert result == "agent-2"

        # Fallback
        result = strategy_with_llm._parse_selection_response("unknown", sample_agents)
        assert result == sample_agents[0].agent_id


# =============================================================================
# SpeakerSelector Tests
# =============================================================================

class TestSpeakerSelector:
    """Tests for the main SpeakerSelector class."""

    @pytest.mark.asyncio
    async def test_select_round_robin(self, selector, sample_state):
        """Test round-robin selection via main selector."""
        sample_state.config.speaker_selection_method = SpeakerSelectionMethod.ROUND_ROBIN

        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.ROUND_ROBIN,
        )

        assert result.success is True
        assert result.strategy_used == SelectionStrategy.ROUND_ROBIN

    @pytest.mark.asyncio
    async def test_select_random(self, selector, sample_state):
        """Test random selection via main selector."""
        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.RANDOM,
        )

        assert result.success is True
        assert result.strategy_used == SelectionStrategy.RANDOM

    @pytest.mark.asyncio
    async def test_select_priority(self, selector, sample_state):
        """Test priority selection via main selector."""
        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.PRIORITY,
        )

        assert result.success is True
        assert result.strategy_used == SelectionStrategy.PRIORITY
        assert result.selected_agent.agent_id == "agent-1"  # Highest priority

    @pytest.mark.asyncio
    async def test_select_manual(self, selector, sample_state):
        """Test manual selection via main selector."""
        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.MANUAL,
            manual_selection="agent-3",
        )

        assert result.success is True
        assert result.selected_agent.agent_id == "agent-3"

    @pytest.mark.asyncio
    async def test_select_expertise(self, selector, sample_state, sample_message):
        """Test expertise selection via main selector."""
        sample_state.messages.append(sample_message)

        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.EXPERTISE,
        )

        assert result.success is True
        assert result.strategy_used == SelectionStrategy.EXPERTISE

    @pytest.mark.asyncio
    async def test_default_strategy_from_config(self, selector, sample_state):
        """Test using default strategy from config."""
        sample_state.config.speaker_selection_method = SpeakerSelectionMethod.PRIORITY

        result = await selector.select_next(state=sample_state)

        # Should use PRIORITY from config
        assert result.strategy_used == SelectionStrategy.PRIORITY

    @pytest.mark.asyncio
    async def test_exclude_agents(self, selector, sample_state):
        """Test excluding specific agents."""
        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.ROUND_ROBIN,
            exclude_agents={"agent-1", "agent-2"},
        )

        assert result.success is True
        assert result.selected_agent.agent_id not in ["agent-1", "agent-2"]

    @pytest.mark.asyncio
    async def test_no_repeat_speaker(self, selector, sample_state):
        """Test no-repeat speaker constraint."""
        sample_state.config.allow_repeat_speaker = False
        sample_state.current_speaker_id = "agent-1"

        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.ROUND_ROBIN,
        )

        assert result.selected_agent.agent_id != "agent-1"

    @pytest.mark.asyncio
    async def test_allow_repeat_speaker(self, selector, sample_state):
        """Test allow-repeat speaker setting."""
        sample_state.config.allow_repeat_speaker = True
        sample_state.current_speaker_id = "agent-1"

        # With priority, should select agent-1 again
        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.PRIORITY,
        )

        assert result.selected_agent.agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_inactive_agents_filtered(self, selector, sample_state):
        """Test that inactive agents are filtered."""
        sample_state.agents[0].is_active = False
        sample_state.agents[1].is_active = False

        result = await selector.select_next(
            state=sample_state,
            strategy=SelectionStrategy.ROUND_ROBIN,
        )

        # Should only select from active agents
        assert result.selected_agent.agent_id in ["agent-3", "agent-4"]

    def test_register_custom_strategy(self, selector):
        """Test registering a custom strategy."""
        class CustomStrategy(BaseSpeakerStrategy):
            @property
            def strategy_type(self):
                return SelectionStrategy.AUTO

            async def select(self, context):
                return SelectionResult(
                    selected_agent=context.candidates[-1] if context.candidates else None,
                    strategy_used=SelectionStrategy.AUTO,
                    reason="Custom strategy: always last",
                )

        selector.register_strategy(SelectionStrategy.AUTO, CustomStrategy())

        strategies = selector.get_available_strategies()
        assert SelectionStrategy.AUTO in strategies

    def test_get_available_strategies(self, selector):
        """Test getting available strategies."""
        strategies = selector.get_available_strategies()

        assert SelectionStrategy.ROUND_ROBIN in strategies
        assert SelectionStrategy.RANDOM in strategies
        assert SelectionStrategy.PRIORITY in strategies
        assert SelectionStrategy.MANUAL in strategies
        assert SelectionStrategy.EXPERTISE in strategies
        assert SelectionStrategy.AUTO in strategies


# =============================================================================
# Integration Tests
# =============================================================================

class TestSpeakerSelectorIntegration:
    """Integration tests for SpeakerSelector."""

    @pytest.mark.asyncio
    async def test_complete_selection_flow(self, sample_agents):
        """Test a complete selection flow with multiple strategies."""
        selector = SpeakerSelector()

        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
            config=GroupChatConfig(
                speaker_selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
                allow_repeat_speaker=False,
            ),
        )

        # First selection
        result1 = await selector.select_next(state)
        assert result1.selected_agent.agent_id == "agent-1"

        # Update state
        state.current_speaker_id = "agent-1"

        # Second selection
        result2 = await selector.select_next(state)
        assert result2.selected_agent.agent_id == "agent-2"

        # Third selection with different strategy
        state.current_speaker_id = "agent-2"
        result3 = await selector.select_next(
            state,
            strategy=SelectionStrategy.PRIORITY,
        )
        # Highest priority available (not agent-2)
        assert result3.selected_agent.agent_id in ["agent-1", "agent-3", "agent-4"]

    @pytest.mark.asyncio
    async def test_expertise_based_conversation(self, sample_agents):
        """Test expertise-based selection in conversation."""
        selector = SpeakerSelector()

        state = GroupChatState(
            group_id="group-1",
            name="Technical Discussion",
            agents=sample_agents,
            config=GroupChatConfig(
                speaker_selection_method=SpeakerSelectionMethod.EXPERTISE,
            ),
        )

        # Add a technical question
        state.messages.append(GroupMessage(
            id="msg-1",
            group_id="group-1",
            sender_id="user",
            sender_name="User",
            content="Can you help debug this authentication issue?",
            message_type=MessageType.USER,
        ))

        result = await selector.select_next(state)

        # Should select security or technical agent
        assert result.selected_agent.agent_id in ["agent-2", "agent-4"]

    @pytest.mark.asyncio
    async def test_all_strategies_return_valid_results(self, sample_agents):
        """Test that all strategies return valid results."""
        selector = SpeakerSelector()

        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
        )
        state.messages.append(GroupMessage(
            id="msg-1",
            group_id="group-1",
            sender_id="user",
            sender_name="User",
            content="Test message",
            message_type=MessageType.USER,
        ))

        strategies = [
            SelectionStrategy.ROUND_ROBIN,
            SelectionStrategy.RANDOM,
            SelectionStrategy.PRIORITY,
            SelectionStrategy.EXPERTISE,
            SelectionStrategy.AUTO,
        ]

        for strategy in strategies:
            result = await selector.select_next(state, strategy=strategy)
            assert result.success is True, f"Strategy {strategy} failed"
            assert result.selected_agent is not None
            # AUTO falls back to ROUND_ROBIN when no LLM is available
            if strategy == SelectionStrategy.AUTO:
                assert result.strategy_used in [SelectionStrategy.AUTO, SelectionStrategy.ROUND_ROBIN]
            else:
                assert result.strategy_used == strategy
