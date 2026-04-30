# =============================================================================
# IPA Platform - Agent Discovery Service
# =============================================================================
# Sprint 81: S81-2 - A2A 通信協議完善 (8 pts)
#
# This module provides agent discovery and registration services.
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .protocol import (
    A2AAgentStatus,
    AgentCapability,
    DiscoveryQuery,
    DiscoveryResult,
)


logger = logging.getLogger(__name__)


class AgentDiscoveryService:
    """
    Service for agent registration and discovery.

    Manages:
    - Agent registration and unregistration
    - Agent capability querying
    - Agent discovery based on requirements
    - Heartbeat tracking and cleanup
    """

    def __init__(
        self,
        heartbeat_timeout_seconds: int = 60,
        cleanup_interval_seconds: int = 30,
    ):
        """
        Initialize discovery service.

        Args:
            heartbeat_timeout_seconds: Time after which agent is considered offline.
            cleanup_interval_seconds: Interval for cleanup of stale agents.
        """
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds

        # Agent registry
        self._agents: Dict[str, AgentCapability] = {}

        # Callbacks
        self._on_register_callbacks: List[Callable[[AgentCapability], None]] = []
        self._on_unregister_callbacks: List[Callable[[str], None]] = []

    def register_agent(self, agent: AgentCapability) -> bool:
        """
        Register an agent.

        Args:
            agent: Agent capability information.

        Returns:
            True if successfully registered.
        """
        # Update registration time
        agent.registered_at = datetime.utcnow()
        agent.last_heartbeat = datetime.utcnow()

        # Store agent
        self._agents[agent.agent_id] = agent

        # Notify callbacks
        for callback in self._on_register_callbacks:
            try:
                callback(agent)
            except Exception as e:
                logger.warning(f"Register callback failed: {e}")

        logger.info(
            f"Registered agent: {agent.name} ({agent.agent_id}) "
            f"with capabilities: {agent.capabilities}"
        )

        return True

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: ID of agent to unregister.

        Returns:
            True if agent was found and removed.
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent not found for unregister: {agent_id}")
            return False

        del self._agents[agent_id]

        # Notify callbacks
        for callback in self._on_unregister_callbacks:
            try:
                callback(agent_id)
            except Exception as e:
                logger.warning(f"Unregister callback failed: {e}")

        logger.info(f"Unregistered agent: {agent_id}")

        return True

    def update_heartbeat(self, agent_id: str) -> bool:
        """
        Update agent heartbeat timestamp.

        Args:
            agent_id: ID of agent.

        Returns:
            True if agent found and updated.
        """
        if agent_id not in self._agents:
            return False

        self._agents[agent_id].last_heartbeat = datetime.utcnow()
        return True

    def update_status(
        self,
        agent_id: str,
        status: A2AAgentStatus,
        current_load: Optional[int] = None,
    ) -> bool:
        """
        Update agent status.

        Args:
            agent_id: ID of agent.
            status: New status.
            current_load: Optional current load update.

        Returns:
            True if agent found and updated.
        """
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]
        agent.status = status
        agent.last_heartbeat = datetime.utcnow()

        if current_load is not None:
            agent.current_load = current_load

        return True

    def get_agent(self, agent_id: str) -> Optional[AgentCapability]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def get_all_agents(self) -> List[AgentCapability]:
        """Get all registered agents."""
        return list(self._agents.values())

    def query_capability(
        self,
        agent_id: str,
        capability: str,
    ) -> Optional[float]:
        """
        Query agent's proficiency for a capability.

        Args:
            agent_id: ID of agent.
            capability: Capability to query.

        Returns:
            Proficiency score (0-1) or None if not found.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return None

        if capability not in agent.capabilities:
            return None

        return agent.skills.get(capability, 0.5)

    def discover_agents(self, query: DiscoveryQuery) -> DiscoveryResult:
        """
        Discover agents matching query criteria.

        Args:
            query: Discovery query parameters.

        Returns:
            DiscoveryResult with matching agents.
        """
        candidates = []

        for agent in self._agents.values():
            # Check status
            if not query.include_busy and agent.status == A2AAgentStatus.BUSY:
                continue

            if agent.status == A2AAgentStatus.OFFLINE:
                continue

            # Check availability
            if agent.availability_score < query.min_availability:
                continue

            # Check capabilities
            if query.required_capabilities:
                if not agent.can_handle(query.required_capabilities):
                    continue

            # Check tags
            if query.required_tags:
                if not agent.matches_tags(query.required_tags):
                    continue

            # Check metadata filters
            if query.metadata_filters:
                if not self._matches_metadata(agent, query.metadata_filters):
                    continue

            # Calculate match score
            score = self._calculate_match_score(agent, query)
            candidates.append((agent, score))

        # Sort by score
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        results = [c[0] for c in candidates[: query.max_results]]

        return DiscoveryResult(
            query=query,
            agents=results,
            total_found=len(candidates),
        )

    def _matches_metadata(
        self,
        agent: AgentCapability,
        filters: Dict[str, Any],
    ) -> bool:
        """Check if agent metadata matches filters."""
        for key, value in filters.items():
            if key not in agent.metadata:
                return False
            if agent.metadata[key] != value:
                return False
        return True

    def _calculate_match_score(
        self,
        agent: AgentCapability,
        query: DiscoveryQuery,
    ) -> float:
        """Calculate match score for ranking."""
        score = 0.0

        # Capability match score
        if query.required_capabilities:
            matched = sum(
                1 for cap in query.required_capabilities
                if cap in agent.capabilities
            )
            score += (matched / len(query.required_capabilities)) * 0.4

        # Tag match score
        if query.required_tags:
            matched_tags = len(set(agent.tags) & set(query.required_tags))
            score += (matched_tags / len(query.required_tags)) * 0.2

        # Availability score
        score += agent.availability_score * 0.3

        # Skill proficiency
        if query.required_capabilities:
            avg_skill = sum(
                agent.skills.get(cap, 0.5)
                for cap in query.required_capabilities
            ) / len(query.required_capabilities)
            score += avg_skill * 0.1

        return score

    def cleanup_stale_agents(self) -> int:
        """
        Remove agents that haven't sent heartbeat within timeout.

        Returns:
            Number of agents removed.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout_seconds)
        stale_ids = [
            agent_id
            for agent_id, agent in self._agents.items()
            if agent.last_heartbeat < cutoff
        ]

        for agent_id in stale_ids:
            self.unregister_agent(agent_id)
            logger.info(f"Cleaned up stale agent: {agent_id}")

        return len(stale_ids)

    def on_register(self, callback: Callable[[AgentCapability], None]) -> None:
        """Register callback for agent registration events."""
        self._on_register_callbacks.append(callback)

    def on_unregister(self, callback: Callable[[str], None]) -> None:
        """Register callback for agent unregistration events."""
        self._on_unregister_callbacks.append(callback)

    def get_statistics(self) -> Dict[str, Any]:
        """Get discovery service statistics."""
        total = len(self._agents)
        online = sum(
            1 for a in self._agents.values()
            if a.status == A2AAgentStatus.ONLINE
        )
        busy = sum(
            1 for a in self._agents.values()
            if a.status == A2AAgentStatus.BUSY
        )
        offline = sum(
            1 for a in self._agents.values()
            if a.status == A2AAgentStatus.OFFLINE
        )

        return {
            "total_agents": total,
            "online": online,
            "busy": busy,
            "offline": offline,
            "capabilities": self._get_all_capabilities(),
        }

    def _get_all_capabilities(self) -> List[str]:
        """Get list of all unique capabilities."""
        caps = set()
        for agent in self._agents.values():
            caps.update(agent.capabilities)
        return sorted(caps)
