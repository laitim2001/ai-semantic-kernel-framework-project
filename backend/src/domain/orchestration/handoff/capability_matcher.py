# =============================================================================
# IPA Platform - Capability Matcher
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Intelligent capability matching for agent selection and handoff routing.
# Includes:
#   - CapabilityMatcher: Find best agent for task requirements
#   - Match scoring algorithm
#   - Availability checking
#
# References:
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

from src.domain.orchestration.handoff.capabilities import (
    AgentCapability,
    CapabilityCategory,
    CapabilityRegistry,
    CapabilityRequirement,
)

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """
    Agent availability status.

    States:
        AVAILABLE: Agent is ready to accept tasks
        BUSY: Agent is processing tasks but can queue more
        OVERLOADED: Agent is at capacity
        OFFLINE: Agent is not available
        MAINTENANCE: Agent is under maintenance
    """
    AVAILABLE = "available"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class MatchStrategy(str, Enum):
    """
    Strategy for selecting the best match.

    Strategies:
        BEST_FIT: Select agent with highest match score
        FIRST_FIT: Select first agent meeting requirements
        ROUND_ROBIN: Distribute evenly among capable agents
        LEAST_LOADED: Select agent with lowest current load
    """
    BEST_FIT = "best_fit"
    FIRST_FIT = "first_fit"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"


@dataclass
class AgentAvailability:
    """
    Agent availability information.

    Attributes:
        agent_id: Agent identifier
        status: Current status
        current_load: Current workload (0.0 to 1.0)
        max_concurrent: Maximum concurrent tasks
        active_tasks: Number of active tasks
        last_updated: When availability was last updated
    """
    agent_id: UUID
    status: AgentStatus = AgentStatus.AVAILABLE
    current_load: float = 0.0
    max_concurrent: int = 5
    active_tasks: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_available(self) -> bool:
        """Check if agent can accept new tasks."""
        return (
            self.status in (AgentStatus.AVAILABLE, AgentStatus.BUSY)
            and self.active_tasks < self.max_concurrent
        )

    @property
    def remaining_capacity(self) -> int:
        """Get remaining task capacity."""
        return max(0, self.max_concurrent - self.active_tasks)


@dataclass
class MatchResult:
    """
    Result of capability matching.

    Attributes:
        agent_id: Matched agent ID
        score: Overall match score (0.0 to 1.0)
        capability_scores: Individual capability match scores
        missing_capabilities: List of missing required capabilities
        availability: Agent availability info
        metadata: Additional match metadata
    """
    agent_id: UUID
    score: float = 0.0
    capability_scores: Dict[str, float] = field(default_factory=dict)
    missing_capabilities: List[str] = field(default_factory=list)
    availability: Optional[AgentAvailability] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete_match(self) -> bool:
        """Check if all required capabilities are met."""
        return len(self.missing_capabilities) == 0

    @property
    def is_available(self) -> bool:
        """Check if agent is available."""
        return self.availability is not None and self.availability.is_available


class CapabilityMatcher:
    """
    Intelligent capability matcher for agent selection.

    Provides functionality for:
        - Finding agents matching capability requirements
        - Calculating match scores
        - Checking agent availability
        - Selecting best match based on strategy

    Usage:
        matcher = CapabilityMatcher(registry)

        # Define requirements
        requirements = [
            CapabilityRequirement("data_analysis", min_proficiency=0.7),
            CapabilityRequirement("code_generation", min_proficiency=0.5),
        ]

        # Find matching agents
        matches = matcher.find_capable_agents(requirements)

        # Get best match
        best = matcher.get_best_match(requirements)
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        availability_checker: Optional[Callable[[UUID], AgentAvailability]] = None,
    ):
        """
        Initialize CapabilityMatcher.

        Args:
            registry: Capability registry for agent capabilities
            availability_checker: Optional callback to get agent availability
        """
        self._registry = registry
        self._availability_checker = availability_checker

        # Agent availability cache
        self._availability_cache: Dict[UUID, AgentAvailability] = {}

        # Round-robin state
        self._round_robin_index: Dict[str, int] = {}

        logger.info("CapabilityMatcher initialized")

    # =========================================================================
    # Agent Registration
    # =========================================================================

    def register_agent_capabilities(
        self,
        agent_id: UUID,
        capabilities: List[AgentCapability],
    ) -> None:
        """
        Register capabilities for an agent.

        Args:
            agent_id: Agent to register
            capabilities: List of capabilities
        """
        self._registry.register_multiple(agent_id, capabilities)
        logger.debug(f"Registered {len(capabilities)} capabilities for agent {agent_id}")

    def update_availability(
        self,
        agent_id: UUID,
        availability: AgentAvailability,
    ) -> None:
        """
        Update agent availability information.

        Args:
            agent_id: Agent to update
            availability: New availability info
        """
        self._availability_cache[agent_id] = availability
        logger.debug(f"Updated availability for agent {agent_id}: {availability.status}")

    # =========================================================================
    # Capability Matching
    # =========================================================================

    def find_capable_agents(
        self,
        requirements: List[CapabilityRequirement],
        check_availability: bool = True,
        include_partial: bool = False,
    ) -> List[MatchResult]:
        """
        Find agents matching capability requirements.

        Args:
            requirements: List of required capabilities
            check_availability: Whether to check agent availability
            include_partial: Include agents with partial matches

        Returns:
            List of match results sorted by score
        """
        if not requirements:
            return []

        # Get all potentially matching agents
        candidate_agents = self._get_candidate_agents(requirements)

        if not candidate_agents:
            logger.debug("No candidate agents found for requirements")
            return []

        # Calculate match scores for each candidate
        results = []
        for agent_id in candidate_agents:
            result = self._calculate_match(agent_id, requirements)

            # Check if meets requirements
            if not include_partial and not result.is_complete_match:
                continue

            # Check availability if requested
            if check_availability:
                result.availability = self._check_availability(agent_id)
                if not result.is_available:
                    continue

            results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        logger.debug(f"Found {len(results)} matching agents for requirements")
        return results

    def get_best_match(
        self,
        requirements: List[CapabilityRequirement],
        strategy: MatchStrategy = MatchStrategy.BEST_FIT,
        exclude_agents: Optional[Set[UUID]] = None,
    ) -> Optional[MatchResult]:
        """
        Get the best matching agent for requirements.

        Args:
            requirements: List of required capabilities
            strategy: Selection strategy
            exclude_agents: Agent IDs to exclude

        Returns:
            Best match result or None if no match found
        """
        matches = self.find_capable_agents(
            requirements,
            check_availability=True,
            include_partial=False,
        )

        if not matches:
            return None

        # Filter excluded agents
        if exclude_agents:
            matches = [m for m in matches if m.agent_id not in exclude_agents]

        if not matches:
            return None

        # Apply selection strategy
        if strategy == MatchStrategy.BEST_FIT:
            return matches[0]  # Already sorted by score

        elif strategy == MatchStrategy.FIRST_FIT:
            # Return first meeting minimum threshold
            for match in matches:
                if match.score >= 0.5:
                    return match
            return matches[0]

        elif strategy == MatchStrategy.ROUND_ROBIN:
            return self._select_round_robin(matches, requirements)

        elif strategy == MatchStrategy.LEAST_LOADED:
            return self._select_least_loaded(matches)

        return matches[0]

    def _get_candidate_agents(
        self,
        requirements: List[CapabilityRequirement],
    ) -> Set[UUID]:
        """
        Get set of candidate agents for requirements.

        Args:
            requirements: Capability requirements

        Returns:
            Set of potential agent IDs
        """
        candidates: Optional[Set[UUID]] = None

        for req in requirements:
            if not req.required:
                continue

            agents = set(
                self._registry.find_agents_with_capability(
                    req.capability_name,
                    min_proficiency=0,  # We'll check proficiency in scoring
                )
            )

            if candidates is None:
                candidates = agents
            else:
                candidates &= agents  # Intersection

        return candidates or set()

    def _calculate_match(
        self,
        agent_id: UUID,
        requirements: List[CapabilityRequirement],
    ) -> MatchResult:
        """
        Calculate match score for an agent.

        Args:
            agent_id: Agent to evaluate
            requirements: Capability requirements

        Returns:
            Match result with scores
        """
        result = MatchResult(agent_id=agent_id)
        total_weight = 0.0
        weighted_score = 0.0

        for req in requirements:
            cap = self._registry.get_capability(agent_id, req.capability_name)

            if cap is None:
                if req.required:
                    result.missing_capabilities.append(req.capability_name)
                    result.capability_scores[req.capability_name] = 0.0
                continue

            # Calculate capability score
            score = self._calculate_capability_score(cap, req)
            result.capability_scores[req.capability_name] = score

            # Check minimum proficiency
            if cap.proficiency_level < req.min_proficiency:
                if req.required:
                    result.missing_capabilities.append(req.capability_name)

            # Accumulate weighted score
            weighted_score += score * req.weight
            total_weight += req.weight

        # Calculate overall score
        if total_weight > 0:
            result.score = weighted_score / total_weight

        return result

    def _calculate_capability_score(
        self,
        capability: AgentCapability,
        requirement: CapabilityRequirement,
    ) -> float:
        """
        Calculate match score for a single capability.

        Args:
            capability: Agent's capability
            requirement: Capability requirement

        Returns:
            Match score (0.0 to 1.0)
        """
        # Base score from proficiency level
        proficiency = capability.proficiency_level

        # Bonus for exceeding minimum requirement
        if proficiency >= requirement.min_proficiency:
            excess = proficiency - requirement.min_proficiency
            bonus = min(0.2, excess * 0.5)  # Up to 0.2 bonus
            score = min(1.0, proficiency + bonus)
        else:
            # Penalty for not meeting minimum
            deficit = requirement.min_proficiency - proficiency
            score = max(0.0, proficiency - deficit * 0.5)

        # Category match bonus
        if requirement.category and capability.category == requirement.category:
            score = min(1.0, score + 0.1)

        return score

    # =========================================================================
    # Availability Checking
    # =========================================================================

    def _check_availability(self, agent_id: UUID) -> AgentAvailability:
        """
        Check agent availability.

        Args:
            agent_id: Agent to check

        Returns:
            Agent availability info
        """
        # Try external checker first
        if self._availability_checker:
            try:
                return self._availability_checker(agent_id)
            except Exception as e:
                logger.warning(f"Availability check failed for {agent_id}: {e}")

        # Fall back to cache
        if agent_id in self._availability_cache:
            return self._availability_cache[agent_id]

        # Default to available
        return AgentAvailability(agent_id=agent_id)

    def is_agent_available(
        self,
        agent_id: UUID,
        min_capacity: int = 1,
    ) -> bool:
        """
        Check if agent is available with minimum capacity.

        Args:
            agent_id: Agent to check
            min_capacity: Minimum required capacity

        Returns:
            True if agent has required capacity
        """
        availability = self._check_availability(agent_id)
        return (
            availability.is_available
            and availability.remaining_capacity >= min_capacity
        )

    # =========================================================================
    # Selection Strategies
    # =========================================================================

    def _select_round_robin(
        self,
        matches: List[MatchResult],
        requirements: List[CapabilityRequirement],
    ) -> MatchResult:
        """
        Select agent using round-robin strategy.

        Args:
            matches: List of matching agents
            requirements: Requirements (for grouping)

        Returns:
            Selected match result
        """
        # Create key from requirements
        key = "_".join(sorted(r.capability_name for r in requirements))

        # Get current index
        index = self._round_robin_index.get(key, 0)

        # Select and update index
        result = matches[index % len(matches)]
        self._round_robin_index[key] = (index + 1) % len(matches)

        return result

    def _select_least_loaded(
        self,
        matches: List[MatchResult],
    ) -> MatchResult:
        """
        Select agent with lowest load.

        Args:
            matches: List of matching agents

        Returns:
            Least loaded match result
        """
        return min(
            matches,
            key=lambda m: (
                m.availability.current_load if m.availability else 0.0,
                -m.score,  # Secondary sort by score
            ),
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_agent_capabilities(self, agent_id: UUID) -> List[AgentCapability]:
        """
        Get all capabilities for an agent.

        Args:
            agent_id: Agent to query

        Returns:
            List of capabilities
        """
        return self._registry.get_capabilities(agent_id)

    def get_agents_by_category(
        self,
        category: CapabilityCategory,
        check_availability: bool = True,
    ) -> List[UUID]:
        """
        Get agents with capabilities in a category.

        Args:
            category: Capability category
            check_availability: Whether to filter by availability

        Returns:
            List of agent IDs
        """
        agents = self._registry.find_agents_by_category(category)

        if check_availability:
            agents = [
                a for a in agents
                if self._check_availability(a).is_available
            ]

        return agents

    def calculate_handoff_score(
        self,
        source_agent_id: UUID,
        target_agent_id: UUID,
        task_requirements: List[CapabilityRequirement],
    ) -> float:
        """
        Calculate handoff suitability score.

        Considers both target capability match and improvement over source.

        Args:
            source_agent_id: Current agent
            target_agent_id: Potential handoff target
            task_requirements: Task requirements

        Returns:
            Handoff score (0.0 to 1.0)
        """
        # Get match scores
        source_match = self._calculate_match(source_agent_id, task_requirements)
        target_match = self._calculate_match(target_agent_id, task_requirements)

        # Base score is target's match score
        score = target_match.score

        # Bonus if target is better than source
        improvement = target_match.score - source_match.score
        if improvement > 0:
            score = min(1.0, score + improvement * 0.2)

        # Penalty if source is actually better
        if improvement < 0:
            score = max(0.0, score + improvement * 0.5)

        # Check availability
        target_avail = self._check_availability(target_agent_id)
        if not target_avail.is_available:
            score *= 0.5

        return score
