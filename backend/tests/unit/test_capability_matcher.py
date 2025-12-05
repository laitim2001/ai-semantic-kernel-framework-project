# =============================================================================
# IPA Platform - Capability Matcher Unit Tests
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Tests for:
#   - AgentCapability
#   - CapabilityRegistry
#   - CapabilityMatcher
#   - Match scoring and strategy selection
# =============================================================================

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.orchestration.handoff.capabilities import (
    AgentCapability,
    CapabilityCategory,
    CapabilityRegistry,
    CapabilityRequirement,
    ProficiencyLevel,
)
from src.domain.orchestration.handoff.capability_matcher import (
    AgentAvailability,
    AgentStatus,
    CapabilityMatcher,
    MatchResult,
    MatchStrategy,
)


# =============================================================================
# ProficiencyLevel Tests
# =============================================================================

class TestProficiencyLevel:
    """Tests for ProficiencyLevel enum."""

    def test_from_score_novice(self):
        """Test novice level from score."""
        assert ProficiencyLevel.from_score(0.0) == ProficiencyLevel.NOVICE
        assert ProficiencyLevel.from_score(0.1) == ProficiencyLevel.NOVICE
        assert ProficiencyLevel.from_score(0.19) == ProficiencyLevel.NOVICE

    def test_from_score_beginner(self):
        """Test beginner level from score."""
        assert ProficiencyLevel.from_score(0.2) == ProficiencyLevel.BEGINNER
        assert ProficiencyLevel.from_score(0.3) == ProficiencyLevel.BEGINNER

    def test_from_score_intermediate(self):
        """Test intermediate level from score."""
        assert ProficiencyLevel.from_score(0.4) == ProficiencyLevel.INTERMEDIATE
        assert ProficiencyLevel.from_score(0.5) == ProficiencyLevel.INTERMEDIATE

    def test_from_score_advanced(self):
        """Test advanced level from score."""
        assert ProficiencyLevel.from_score(0.6) == ProficiencyLevel.ADVANCED
        assert ProficiencyLevel.from_score(0.7) == ProficiencyLevel.ADVANCED

    def test_from_score_expert(self):
        """Test expert level from score."""
        assert ProficiencyLevel.from_score(0.8) == ProficiencyLevel.EXPERT
        assert ProficiencyLevel.from_score(0.9) == ProficiencyLevel.EXPERT
        assert ProficiencyLevel.from_score(1.0) == ProficiencyLevel.EXPERT

    def test_to_score_range(self):
        """Test score range for each level."""
        assert ProficiencyLevel.NOVICE.to_score_range() == (0.0, 0.2)
        assert ProficiencyLevel.EXPERT.to_score_range() == (0.8, 1.0)


# =============================================================================
# AgentCapability Tests
# =============================================================================

class TestAgentCapability:
    """Tests for AgentCapability dataclass."""

    def test_basic_initialization(self):
        """Test basic capability creation."""
        cap = AgentCapability(
            name="data_analysis",
            description="Analyze data",
            proficiency_level=0.7,
        )
        assert cap.name == "data_analysis"
        assert cap.proficiency_level == 0.7

    def test_proficiency_clamping(self):
        """Test proficiency is clamped to 0-1 range."""
        cap_low = AgentCapability(proficiency_level=-0.5)
        assert cap_low.proficiency_level == 0.0

        cap_high = AgentCapability(proficiency_level=1.5)
        assert cap_high.proficiency_level == 1.0

    def test_proficiency_property(self):
        """Test proficiency level enum property."""
        cap = AgentCapability(proficiency_level=0.75)
        assert cap.proficiency == ProficiencyLevel.ADVANCED

    def test_matches_same_name(self):
        """Test capability matching with same name."""
        cap1 = AgentCapability(name="test", proficiency_level=0.8)
        cap2 = AgentCapability(name="test", proficiency_level=0.5)
        assert cap1.matches(cap2)

    def test_matches_threshold(self):
        """Test capability matching with threshold."""
        cap1 = AgentCapability(name="test", proficiency_level=0.5)
        cap2 = AgentCapability(name="test", proficiency_level=0.3)
        assert cap1.matches(cap2, threshold=0.4)
        assert not cap1.matches(cap2, threshold=0.6)

    def test_matches_different_name(self):
        """Test capability not matching with different name."""
        cap1 = AgentCapability(name="test1", proficiency_level=0.8)
        cap2 = AgentCapability(name="test2", proficiency_level=0.5)
        assert not cap1.matches(cap2)

    def test_similarity_same_name(self):
        """Test similarity calculation for same name."""
        cap1 = AgentCapability(name="test", proficiency_level=0.8)
        cap2 = AgentCapability(name="test", proficiency_level=0.8)
        assert cap1.similarity(cap2) == 1.0

    def test_similarity_same_category(self):
        """Test similarity for same category."""
        cap1 = AgentCapability(
            name="test1",
            category=CapabilityCategory.REASONING,
        )
        cap2 = AgentCapability(
            name="test2",
            category=CapabilityCategory.REASONING,
        )
        assert cap1.similarity(cap2) == 0.3

    def test_similarity_different(self):
        """Test similarity for completely different capabilities."""
        cap1 = AgentCapability(
            name="test1",
            category=CapabilityCategory.REASONING,
        )
        cap2 = AgentCapability(
            name="test2",
            category=CapabilityCategory.ACTION,
        )
        assert cap1.similarity(cap2) == 0.0


# =============================================================================
# CapabilityRequirement Tests
# =============================================================================

class TestCapabilityRequirement:
    """Tests for CapabilityRequirement dataclass."""

    def test_basic_initialization(self):
        """Test basic requirement creation."""
        req = CapabilityRequirement(
            capability_name="data_analysis",
            min_proficiency=0.7,
        )
        assert req.capability_name == "data_analysis"
        assert req.min_proficiency == 0.7
        assert req.required == True

    def test_value_clamping(self):
        """Test values are clamped to valid range."""
        req = CapabilityRequirement(
            min_proficiency=1.5,
            weight=2.0,
        )
        assert req.min_proficiency == 1.0
        assert req.weight == 1.0


# =============================================================================
# CapabilityRegistry Tests
# =============================================================================

class TestCapabilityRegistry:
    """Tests for CapabilityRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry."""
        return CapabilityRegistry()

    @pytest.fixture
    def sample_capability(self):
        """Create a sample capability."""
        return AgentCapability(
            name="test_capability",
            description="Test",
            proficiency_level=0.7,
        )

    def test_register_capability(self, registry, sample_capability):
        """Test registering a capability."""
        agent_id = uuid4()
        registry.register(agent_id, sample_capability)

        caps = registry.get_capabilities(agent_id)
        assert len(caps) == 1
        assert caps[0].name == "test_capability"

    def test_register_multiple(self, registry):
        """Test registering multiple capabilities."""
        agent_id = uuid4()
        caps = [
            AgentCapability(name="cap1", proficiency_level=0.5),
            AgentCapability(name="cap2", proficiency_level=0.7),
            AgentCapability(name="cap3", proficiency_level=0.9),
        ]
        registry.register_multiple(agent_id, caps)

        result = registry.get_capabilities(agent_id)
        assert len(result) == 3

    def test_register_update_existing(self, registry):
        """Test updating an existing capability."""
        agent_id = uuid4()
        cap1 = AgentCapability(name="test", proficiency_level=0.5)
        cap2 = AgentCapability(name="test", proficiency_level=0.8)

        registry.register(agent_id, cap1)
        registry.register(agent_id, cap2)

        caps = registry.get_capabilities(agent_id)
        assert len(caps) == 1
        assert caps[0].proficiency_level == 0.8

    def test_unregister_capability(self, registry, sample_capability):
        """Test unregistering a capability."""
        agent_id = uuid4()
        registry.register(agent_id, sample_capability)

        result = registry.unregister(agent_id, "test_capability")
        assert result == True
        assert len(registry.get_capabilities(agent_id)) == 0

    def test_unregister_nonexistent(self, registry):
        """Test unregistering non-existent capability."""
        result = registry.unregister(uuid4(), "nonexistent")
        assert result == False

    def test_unregister_agent(self, registry):
        """Test unregistering all capabilities for an agent."""
        agent_id = uuid4()
        caps = [
            AgentCapability(name="cap1"),
            AgentCapability(name="cap2"),
        ]
        registry.register_multiple(agent_id, caps)

        count = registry.unregister_agent(agent_id)
        assert count == 2
        assert len(registry.get_capabilities(agent_id)) == 0

    def test_get_capability(self, registry, sample_capability):
        """Test getting a specific capability."""
        agent_id = uuid4()
        registry.register(agent_id, sample_capability)

        cap = registry.get_capability(agent_id, "test_capability")
        assert cap is not None
        assert cap.name == "test_capability"

    def test_get_capability_not_found(self, registry):
        """Test getting non-existent capability."""
        cap = registry.get_capability(uuid4(), "nonexistent")
        assert cap is None

    def test_has_capability(self, registry, sample_capability):
        """Test checking capability existence."""
        agent_id = uuid4()
        registry.register(agent_id, sample_capability)

        assert registry.has_capability(agent_id, "test_capability")
        assert registry.has_capability(agent_id, "test_capability", 0.5)
        assert not registry.has_capability(agent_id, "test_capability", 0.9)

    def test_find_agents_with_capability(self, registry):
        """Test finding agents with specific capability."""
        agent1 = uuid4()
        agent2 = uuid4()
        agent3 = uuid4()

        registry.register(agent1, AgentCapability(name="test", proficiency_level=0.5))
        registry.register(agent2, AgentCapability(name="test", proficiency_level=0.8))
        registry.register(agent3, AgentCapability(name="other", proficiency_level=0.9))

        agents = registry.find_agents_with_capability("test")
        assert len(agents) == 2
        assert agent1 in agents
        assert agent2 in agents

    def test_find_agents_with_min_proficiency(self, registry):
        """Test finding agents with minimum proficiency."""
        agent1 = uuid4()
        agent2 = uuid4()

        registry.register(agent1, AgentCapability(name="test", proficiency_level=0.5))
        registry.register(agent2, AgentCapability(name="test", proficiency_level=0.8))

        agents = registry.find_agents_with_capability("test", min_proficiency=0.7)
        assert len(agents) == 1
        assert agent2 in agents

    def test_find_agents_by_category(self, registry):
        """Test finding agents by capability category."""
        agent1 = uuid4()
        agent2 = uuid4()

        registry.register(agent1, AgentCapability(
            name="cap1",
            category=CapabilityCategory.REASONING,
        ))
        registry.register(agent2, AgentCapability(
            name="cap2",
            category=CapabilityCategory.ACTION,
        ))

        agents = registry.find_agents_by_category(CapabilityCategory.REASONING)
        assert len(agents) == 1
        assert agent1 in agents

    def test_builtin_capabilities(self, registry):
        """Test built-in capability definitions."""
        builtins = registry.list_builtins()
        assert len(builtins) > 0
        assert "text_generation" in builtins
        assert "data_analysis" in builtins

    def test_get_builtin(self, registry):
        """Test getting a built-in capability."""
        cap = registry.get_builtin("text_generation")
        assert cap is not None
        assert cap.name == "text_generation"

    def test_create_from_builtin(self, registry):
        """Test creating capability from built-in."""
        cap = registry.create_from_builtin("text_generation", proficiency_level=0.9)
        assert cap is not None
        assert cap.proficiency_level == 0.9

    def test_agent_count(self, registry):
        """Test agent count property."""
        agent1, agent2 = uuid4(), uuid4()
        registry.register(agent1, AgentCapability(name="cap1"))
        registry.register(agent2, AgentCapability(name="cap2"))

        assert registry.agent_count == 2

    def test_capability_count(self, registry):
        """Test capability count property."""
        agent1 = uuid4()
        caps = [
            AgentCapability(name="cap1"),
            AgentCapability(name="cap2"),
        ]
        registry.register_multiple(agent1, caps)

        assert registry.capability_count == 2


# =============================================================================
# AgentAvailability Tests
# =============================================================================

class TestAgentAvailability:
    """Tests for AgentAvailability dataclass."""

    def test_is_available_true(self):
        """Test agent is available."""
        avail = AgentAvailability(
            agent_id=uuid4(),
            status=AgentStatus.AVAILABLE,
            active_tasks=2,
            max_concurrent=5,
        )
        assert avail.is_available == True

    def test_is_available_busy_ok(self):
        """Test busy agent with capacity is available."""
        avail = AgentAvailability(
            agent_id=uuid4(),
            status=AgentStatus.BUSY,
            active_tasks=3,
            max_concurrent=5,
        )
        assert avail.is_available == True

    def test_is_available_at_capacity(self):
        """Test agent at capacity is not available."""
        avail = AgentAvailability(
            agent_id=uuid4(),
            status=AgentStatus.AVAILABLE,
            active_tasks=5,
            max_concurrent=5,
        )
        assert avail.is_available == False

    def test_is_available_offline(self):
        """Test offline agent is not available."""
        avail = AgentAvailability(
            agent_id=uuid4(),
            status=AgentStatus.OFFLINE,
        )
        assert avail.is_available == False

    def test_remaining_capacity(self):
        """Test remaining capacity calculation."""
        avail = AgentAvailability(
            agent_id=uuid4(),
            active_tasks=2,
            max_concurrent=5,
        )
        assert avail.remaining_capacity == 3


# =============================================================================
# MatchResult Tests
# =============================================================================

class TestMatchResult:
    """Tests for MatchResult dataclass."""

    def test_is_complete_match(self):
        """Test complete match detection."""
        result = MatchResult(
            agent_id=uuid4(),
            score=0.9,
            missing_capabilities=[],
        )
        assert result.is_complete_match == True

    def test_is_incomplete_match(self):
        """Test incomplete match detection."""
        result = MatchResult(
            agent_id=uuid4(),
            score=0.5,
            missing_capabilities=["missing_cap"],
        )
        assert result.is_complete_match == False

    def test_is_available(self):
        """Test availability through match result."""
        result = MatchResult(
            agent_id=uuid4(),
            availability=AgentAvailability(
                agent_id=uuid4(),
                status=AgentStatus.AVAILABLE,
            ),
        )
        assert result.is_available == True


# =============================================================================
# CapabilityMatcher Tests
# =============================================================================

class TestCapabilityMatcher:
    """Tests for CapabilityMatcher class."""

    @pytest.fixture
    def registry(self):
        """Create a capability registry."""
        return CapabilityRegistry()

    @pytest.fixture
    def matcher(self, registry):
        """Create a capability matcher."""
        return CapabilityMatcher(registry)

    @pytest.fixture
    def setup_agents(self, registry, matcher):
        """Set up test agents with capabilities."""
        agent1 = uuid4()
        agent2 = uuid4()
        agent3 = uuid4()

        # Agent 1: Strong in data analysis
        matcher.register_agent_capabilities(agent1, [
            AgentCapability(name="data_analysis", proficiency_level=0.9),
            AgentCapability(name="code_generation", proficiency_level=0.6),
        ])

        # Agent 2: Strong in code generation
        matcher.register_agent_capabilities(agent2, [
            AgentCapability(name="data_analysis", proficiency_level=0.5),
            AgentCapability(name="code_generation", proficiency_level=0.9),
        ])

        # Agent 3: Balanced
        matcher.register_agent_capabilities(agent3, [
            AgentCapability(name="data_analysis", proficiency_level=0.7),
            AgentCapability(name="code_generation", proficiency_level=0.7),
            AgentCapability(name="text_generation", proficiency_level=0.8),
        ])

        # Set availability
        matcher.update_availability(agent1, AgentAvailability(
            agent_id=agent1,
            status=AgentStatus.AVAILABLE,
            current_load=0.2,
            active_tasks=1,
            max_concurrent=5,
        ))
        matcher.update_availability(agent2, AgentAvailability(
            agent_id=agent2,
            status=AgentStatus.AVAILABLE,
            current_load=0.0,
            active_tasks=0,
            max_concurrent=5,
        ))
        matcher.update_availability(agent3, AgentAvailability(
            agent_id=agent3,
            status=AgentStatus.BUSY,
            current_load=0.8,
            active_tasks=4,
            max_concurrent=5,
        ))

        return agent1, agent2, agent3

    def test_find_capable_agents_single_requirement(self, matcher, setup_agents):
        """Test finding agents with single requirement."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.8),
        ]

        matches = matcher.find_capable_agents(requirements)
        assert len(matches) == 1
        assert matches[0].agent_id == agent1

    def test_find_capable_agents_multiple_requirements(self, matcher, setup_agents):
        """Test finding agents with multiple requirements."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.5),
            CapabilityRequirement("code_generation", min_proficiency=0.5),
        ]

        matches = matcher.find_capable_agents(requirements)
        # All 3 agents have both capabilities at 0.5+
        assert len(matches) == 3

    def test_find_capable_agents_no_match(self, matcher, setup_agents):
        """Test no agents match requirements."""
        requirements = [
            CapabilityRequirement("nonexistent_capability", min_proficiency=0.5),
        ]

        matches = matcher.find_capable_agents(requirements)
        assert len(matches) == 0

    def test_find_capable_agents_check_availability(self, matcher, setup_agents):
        """Test availability filtering."""
        agent1, agent2, agent3 = setup_agents

        # Make agent2 offline
        matcher.update_availability(agent2, AgentAvailability(
            agent_id=agent2,
            status=AgentStatus.OFFLINE,
        ))

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.4),
        ]

        matches = matcher.find_capable_agents(requirements, check_availability=True)
        # Agent2 should be excluded due to offline status
        agent_ids = [m.agent_id for m in matches]
        assert agent2 not in agent_ids

    def test_find_capable_agents_include_partial(self, matcher, setup_agents):
        """Test including partial matches."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.5),
            CapabilityRequirement("text_generation", min_proficiency=0.5),
        ]

        # Without partial, only agent3 has both
        matches = matcher.find_capable_agents(requirements, include_partial=False)
        assert len(matches) == 1

        # With partial, more agents included
        matches_partial = matcher.find_capable_agents(
            requirements,
            include_partial=True,
            check_availability=False,
        )
        assert len(matches_partial) >= 1

    def test_get_best_match_best_fit(self, matcher, setup_agents):
        """Test best fit strategy."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.5, weight=1.0),
        ]

        best = matcher.get_best_match(requirements, strategy=MatchStrategy.BEST_FIT)
        assert best is not None
        # Agent1 has highest data_analysis proficiency
        assert best.agent_id == agent1

    def test_get_best_match_least_loaded(self, matcher, setup_agents):
        """Test least loaded strategy."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.4),
        ]

        best = matcher.get_best_match(requirements, strategy=MatchStrategy.LEAST_LOADED)
        assert best is not None
        # Agent2 has 0 active tasks, should be selected
        assert best.agent_id == agent2

    def test_get_best_match_exclude_agents(self, matcher, setup_agents):
        """Test excluding specific agents."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.4),
        ]

        best = matcher.get_best_match(
            requirements,
            exclude_agents={agent1, agent2},
        )
        assert best is not None
        assert best.agent_id == agent3

    def test_get_best_match_no_match(self, matcher, setup_agents):
        """Test no best match available."""
        requirements = [
            CapabilityRequirement("nonexistent", min_proficiency=0.5),
        ]

        best = matcher.get_best_match(requirements)
        assert best is None

    def test_match_score_calculation(self, matcher, setup_agents):
        """Test match score is calculated correctly."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.5, weight=1.0),
            CapabilityRequirement("code_generation", min_proficiency=0.5, weight=1.0),
        ]

        matches = matcher.find_capable_agents(requirements, check_availability=False)

        # Find agent3's match
        agent3_match = next((m for m in matches if m.agent_id == agent3), None)
        assert agent3_match is not None
        # Agent3 has balanced capabilities (0.7, 0.7)
        assert agent3_match.score > 0

    def test_is_agent_available(self, matcher, setup_agents):
        """Test checking agent availability."""
        agent1, agent2, agent3 = setup_agents

        assert matcher.is_agent_available(agent1)
        assert matcher.is_agent_available(agent2)
        # Agent3 has 4/5 tasks, still has capacity
        assert matcher.is_agent_available(agent3)

        # Check with higher capacity requirement
        assert not matcher.is_agent_available(agent3, min_capacity=2)

    def test_get_agent_capabilities(self, matcher, setup_agents):
        """Test getting agent capabilities."""
        agent1, agent2, agent3 = setup_agents

        caps = matcher.get_agent_capabilities(agent1)
        assert len(caps) == 2
        cap_names = [c.name for c in caps]
        assert "data_analysis" in cap_names

    def test_get_agents_by_category(self, matcher, registry):
        """Test getting agents by capability category."""
        agent1 = uuid4()
        agent2 = uuid4()

        matcher.register_agent_capabilities(agent1, [
            AgentCapability(
                name="reasoning_cap",
                category=CapabilityCategory.REASONING,
            ),
        ])
        matcher.register_agent_capabilities(agent2, [
            AgentCapability(
                name="action_cap",
                category=CapabilityCategory.ACTION,
            ),
        ])

        matcher.update_availability(agent1, AgentAvailability(
            agent_id=agent1,
            status=AgentStatus.AVAILABLE,
        ))
        matcher.update_availability(agent2, AgentAvailability(
            agent_id=agent2,
            status=AgentStatus.AVAILABLE,
        ))

        reasoning_agents = matcher.get_agents_by_category(CapabilityCategory.REASONING)
        assert len(reasoning_agents) == 1
        assert agent1 in reasoning_agents

    def test_calculate_handoff_score(self, matcher, setup_agents):
        """Test handoff score calculation."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.7),
        ]

        # Handoff from agent2 (low data_analysis) to agent1 (high data_analysis)
        score = matcher.calculate_handoff_score(agent2, agent1, requirements)
        assert score > 0.5  # Should be good handoff

        # Handoff from agent1 to agent2 (worse for data_analysis)
        reverse_score = matcher.calculate_handoff_score(agent1, agent2, requirements)
        assert reverse_score < score  # Should be worse

    def test_round_robin_selection(self, matcher, setup_agents):
        """Test round robin strategy distributes evenly."""
        agent1, agent2, agent3 = setup_agents

        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.4),
        ]

        selected = []
        for _ in range(6):
            match = matcher.get_best_match(requirements, strategy=MatchStrategy.ROUND_ROBIN)
            if match:
                selected.append(match.agent_id)

        # Should see distribution across agents
        assert len(set(selected)) > 1  # At least 2 different agents


# =============================================================================
# Integration Tests
# =============================================================================

class TestCapabilityMatcherIntegration:
    """Integration tests for capability matching workflow."""

    def test_complete_matching_workflow(self):
        """Test complete capability matching workflow."""
        # Setup
        registry = CapabilityRegistry()
        matcher = CapabilityMatcher(registry)

        # Create agents
        analysis_agent = uuid4()
        coding_agent = uuid4()
        general_agent = uuid4()

        # Register capabilities
        matcher.register_agent_capabilities(analysis_agent, [
            AgentCapability(name="data_analysis", proficiency_level=0.95),
            AgentCapability(name="logical_reasoning", proficiency_level=0.8),
        ])

        matcher.register_agent_capabilities(coding_agent, [
            AgentCapability(name="code_generation", proficiency_level=0.9),
            AgentCapability(name="code_review", proficiency_level=0.85),
        ])

        matcher.register_agent_capabilities(general_agent, [
            AgentCapability(name="text_generation", proficiency_level=0.8),
            AgentCapability(name="data_analysis", proficiency_level=0.6),
            AgentCapability(name="code_generation", proficiency_level=0.5),
        ])

        # Set availability
        for agent in [analysis_agent, coding_agent, general_agent]:
            matcher.update_availability(agent, AgentAvailability(
                agent_id=agent,
                status=AgentStatus.AVAILABLE,
            ))

        # Task requiring data analysis
        analysis_task = [
            CapabilityRequirement("data_analysis", min_proficiency=0.8),
        ]

        best_for_analysis = matcher.get_best_match(analysis_task)
        assert best_for_analysis.agent_id == analysis_agent

        # Task requiring coding
        coding_task = [
            CapabilityRequirement("code_generation", min_proficiency=0.7),
        ]

        best_for_coding = matcher.get_best_match(coding_task)
        assert best_for_coding.agent_id == coding_agent

        # Task requiring both (general agent might be best balanced)
        mixed_task = [
            CapabilityRequirement("data_analysis", min_proficiency=0.5, weight=0.5),
            CapabilityRequirement("text_generation", min_proficiency=0.5, weight=0.5),
        ]

        best_for_mixed = matcher.get_best_match(mixed_task)
        assert best_for_mixed is not None  # general_agent has both
        assert best_for_mixed.agent_id == general_agent

    def test_handoff_decision_workflow(self):
        """Test using capability matcher for handoff decisions."""
        registry = CapabilityRegistry()
        matcher = CapabilityMatcher(registry)

        # Current agent struggling with data analysis
        current_agent = uuid4()
        specialist_agent = uuid4()

        matcher.register_agent_capabilities(current_agent, [
            AgentCapability(name="text_generation", proficiency_level=0.9),
            AgentCapability(name="data_analysis", proficiency_level=0.3),
        ])

        matcher.register_agent_capabilities(specialist_agent, [
            AgentCapability(name="data_analysis", proficiency_level=0.95),
        ])

        matcher.update_availability(specialist_agent, AgentAvailability(
            agent_id=specialist_agent,
            status=AgentStatus.AVAILABLE,
        ))

        # Task requires strong data analysis
        task_requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.7),
        ]

        # Calculate if handoff makes sense
        handoff_score = matcher.calculate_handoff_score(
            current_agent,
            specialist_agent,
            task_requirements,
        )

        # Should recommend handoff since specialist is much better
        assert handoff_score > 0.7
