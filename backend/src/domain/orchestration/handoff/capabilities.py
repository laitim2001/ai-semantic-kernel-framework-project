# =============================================================================
# IPA Platform - Agent Capabilities
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Defines agent capabilities for intelligent task routing and handoff.
# Includes:
#   - AgentCapability: Capability definition with proficiency
#   - CapabilityRegistry: Central registry for agent capabilities
#   - Built-in capability definitions
#
# References:
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class CapabilityCategory(str, Enum):
    """
    Categories of agent capabilities.

    Categories:
        LANGUAGE: Natural language processing capabilities
        REASONING: Logical reasoning and analysis
        KNOWLEDGE: Domain knowledge and expertise
        ACTION: Ability to perform actions/tasks
        INTEGRATION: External system integration
        COMMUNICATION: Inter-agent communication
    """
    LANGUAGE = "language"
    REASONING = "reasoning"
    KNOWLEDGE = "knowledge"
    ACTION = "action"
    INTEGRATION = "integration"
    COMMUNICATION = "communication"


class ProficiencyLevel(str, Enum):
    """
    Proficiency levels for capabilities.

    Levels:
        NOVICE: Basic understanding (0.0-0.2)
        BEGINNER: Limited proficiency (0.2-0.4)
        INTERMEDIATE: Moderate proficiency (0.4-0.6)
        ADVANCED: High proficiency (0.6-0.8)
        EXPERT: Full mastery (0.8-1.0)
    """
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

    @classmethod
    def from_score(cls, score: float) -> "ProficiencyLevel":
        """Convert a numeric score (0-1) to proficiency level."""
        if score < 0.2:
            return cls.NOVICE
        elif score < 0.4:
            return cls.BEGINNER
        elif score < 0.6:
            return cls.INTERMEDIATE
        elif score < 0.8:
            return cls.ADVANCED
        else:
            return cls.EXPERT

    def to_score_range(self) -> tuple[float, float]:
        """Get the score range for this proficiency level."""
        ranges = {
            ProficiencyLevel.NOVICE: (0.0, 0.2),
            ProficiencyLevel.BEGINNER: (0.2, 0.4),
            ProficiencyLevel.INTERMEDIATE: (0.4, 0.6),
            ProficiencyLevel.ADVANCED: (0.6, 0.8),
            ProficiencyLevel.EXPERT: (0.8, 1.0),
        }
        return ranges[self]


@dataclass
class AgentCapability:
    """
    Defines a capability that an agent possesses.

    Attributes:
        id: Unique capability identifier
        name: Human-readable capability name
        description: Detailed capability description
        category: Capability category
        proficiency_level: Numeric proficiency (0.0 to 1.0)
        metadata: Additional capability metadata
        created_at: When capability was registered
        updated_at: When capability was last updated
    """
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    category: CapabilityCategory = CapabilityCategory.ACTION
    proficiency_level: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate proficiency level is in range."""
        self.proficiency_level = max(0.0, min(1.0, self.proficiency_level))

    @property
    def proficiency(self) -> ProficiencyLevel:
        """Get the proficiency level enum."""
        return ProficiencyLevel.from_score(self.proficiency_level)

    def matches(self, required: "AgentCapability", threshold: float = 0.0) -> bool:
        """
        Check if this capability matches a required capability.

        Args:
            required: Required capability to match against
            threshold: Minimum proficiency threshold (default 0)

        Returns:
            True if capability matches and meets threshold
        """
        if self.name.lower() != required.name.lower():
            return False
        return self.proficiency_level >= max(threshold, required.proficiency_level)

    def similarity(self, other: "AgentCapability") -> float:
        """
        Calculate similarity score with another capability.

        Args:
            other: Capability to compare with

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Same name = high base similarity
        if self.name.lower() == other.name.lower():
            # Proficiency difference reduces similarity
            return 1.0 - abs(self.proficiency_level - other.proficiency_level) * 0.5

        # Same category = some similarity
        if self.category == other.category:
            return 0.3

        return 0.0


@dataclass
class CapabilityRequirement:
    """
    Defines a required capability for a task.

    Attributes:
        capability_name: Name of required capability
        min_proficiency: Minimum proficiency required (0.0 to 1.0)
        category: Optional category constraint
        required: Whether this is mandatory (vs preferred)
        weight: Importance weight for matching (0.0 to 1.0)
    """
    capability_name: str = ""
    min_proficiency: float = 0.0
    category: Optional[CapabilityCategory] = None
    required: bool = True
    weight: float = 1.0

    def __post_init__(self):
        """Validate values are in range."""
        self.min_proficiency = max(0.0, min(1.0, self.min_proficiency))
        self.weight = max(0.0, min(1.0, self.weight))


class CapabilityRegistry:
    """
    Central registry for agent capabilities.

    Provides functionality for:
        - Registering agent capabilities
        - Querying capabilities by agent or capability name
        - Finding agents with specific capabilities
        - Managing capability lifecycle

    Usage:
        registry = CapabilityRegistry()

        # Register capability for an agent
        registry.register(agent_id, capability)

        # Find agents with capability
        agents = registry.find_agents_with_capability("data_analysis")

        # Get agent's capabilities
        caps = registry.get_capabilities(agent_id)
    """

    def __init__(self):
        """Initialize CapabilityRegistry."""
        # Agent ID -> List of capabilities
        self._agent_capabilities: Dict[UUID, List[AgentCapability]] = {}

        # Capability name -> Set of agent IDs
        self._capability_agents: Dict[str, Set[UUID]] = {}

        # Built-in capabilities
        self._builtin_capabilities: Dict[str, AgentCapability] = {}

        # Initialize built-in capabilities
        self._init_builtin_capabilities()

        logger.info("CapabilityRegistry initialized")

    def _init_builtin_capabilities(self) -> None:
        """Initialize built-in capability definitions."""
        builtins = [
            AgentCapability(
                name="text_generation",
                description="Generate natural language text responses",
                category=CapabilityCategory.LANGUAGE,
                proficiency_level=0.8,
            ),
            AgentCapability(
                name="text_summarization",
                description="Summarize long text into concise form",
                category=CapabilityCategory.LANGUAGE,
                proficiency_level=0.7,
            ),
            AgentCapability(
                name="translation",
                description="Translate text between languages",
                category=CapabilityCategory.LANGUAGE,
                proficiency_level=0.7,
            ),
            AgentCapability(
                name="sentiment_analysis",
                description="Analyze emotional tone of text",
                category=CapabilityCategory.LANGUAGE,
                proficiency_level=0.6,
            ),
            AgentCapability(
                name="logical_reasoning",
                description="Perform logical deduction and analysis",
                category=CapabilityCategory.REASONING,
                proficiency_level=0.7,
            ),
            AgentCapability(
                name="data_analysis",
                description="Analyze and interpret data",
                category=CapabilityCategory.REASONING,
                proficiency_level=0.7,
            ),
            AgentCapability(
                name="problem_solving",
                description="Break down and solve complex problems",
                category=CapabilityCategory.REASONING,
                proficiency_level=0.6,
            ),
            AgentCapability(
                name="code_generation",
                description="Generate programming code",
                category=CapabilityCategory.ACTION,
                proficiency_level=0.7,
            ),
            AgentCapability(
                name="code_review",
                description="Review and analyze code quality",
                category=CapabilityCategory.ACTION,
                proficiency_level=0.6,
            ),
            AgentCapability(
                name="api_integration",
                description="Integrate with external APIs",
                category=CapabilityCategory.INTEGRATION,
                proficiency_level=0.8,
            ),
            AgentCapability(
                name="database_operations",
                description="Perform database queries and operations",
                category=CapabilityCategory.INTEGRATION,
                proficiency_level=0.7,
            ),
            AgentCapability(
                name="file_operations",
                description="Read, write, and manipulate files",
                category=CapabilityCategory.INTEGRATION,
                proficiency_level=0.8,
            ),
            AgentCapability(
                name="domain_knowledge_general",
                description="General domain knowledge",
                category=CapabilityCategory.KNOWLEDGE,
                proficiency_level=0.6,
            ),
            AgentCapability(
                name="domain_knowledge_technical",
                description="Technical domain expertise",
                category=CapabilityCategory.KNOWLEDGE,
                proficiency_level=0.7,
            ),
            AgentCapability(
                name="multi_agent_coordination",
                description="Coordinate with other agents",
                category=CapabilityCategory.COMMUNICATION,
                proficiency_level=0.6,
            ),
        ]

        for cap in builtins:
            self._builtin_capabilities[cap.name] = cap

        logger.debug(f"Initialized {len(builtins)} built-in capabilities")

    # =========================================================================
    # Registration
    # =========================================================================

    def register(
        self,
        agent_id: UUID,
        capability: AgentCapability,
    ) -> None:
        """
        Register a capability for an agent.

        Args:
            agent_id: Agent to register capability for
            capability: Capability to register
        """
        # Initialize agent's capability list if needed
        if agent_id not in self._agent_capabilities:
            self._agent_capabilities[agent_id] = []

        # Check for duplicate
        existing = self.get_capability(agent_id, capability.name)
        if existing:
            # Update existing capability
            self._agent_capabilities[agent_id].remove(existing)

        # Add capability
        self._agent_capabilities[agent_id].append(capability)

        # Update reverse index
        cap_name = capability.name.lower()
        if cap_name not in self._capability_agents:
            self._capability_agents[cap_name] = set()
        self._capability_agents[cap_name].add(agent_id)

        logger.debug(f"Registered capability '{capability.name}' for agent {agent_id}")

    def register_multiple(
        self,
        agent_id: UUID,
        capabilities: List[AgentCapability],
    ) -> None:
        """
        Register multiple capabilities for an agent.

        Args:
            agent_id: Agent to register capabilities for
            capabilities: List of capabilities to register
        """
        for cap in capabilities:
            self.register(agent_id, cap)

    def unregister(
        self,
        agent_id: UUID,
        capability_name: str,
    ) -> bool:
        """
        Unregister a capability from an agent.

        Args:
            agent_id: Agent to unregister from
            capability_name: Name of capability to remove

        Returns:
            True if capability was removed
        """
        if agent_id not in self._agent_capabilities:
            return False

        cap = self.get_capability(agent_id, capability_name)
        if not cap:
            return False

        self._agent_capabilities[agent_id].remove(cap)

        # Update reverse index
        cap_name = capability_name.lower()
        if cap_name in self._capability_agents:
            self._capability_agents[cap_name].discard(agent_id)

        logger.debug(f"Unregistered capability '{capability_name}' from agent {agent_id}")
        return True

    def unregister_agent(self, agent_id: UUID) -> int:
        """
        Unregister all capabilities for an agent.

        Args:
            agent_id: Agent to unregister

        Returns:
            Number of capabilities removed
        """
        if agent_id not in self._agent_capabilities:
            return 0

        caps = self._agent_capabilities.pop(agent_id, [])

        # Update reverse indices
        for cap in caps:
            cap_name = cap.name.lower()
            if cap_name in self._capability_agents:
                self._capability_agents[cap_name].discard(agent_id)

        logger.debug(f"Unregistered {len(caps)} capabilities for agent {agent_id}")
        return len(caps)

    # =========================================================================
    # Queries
    # =========================================================================

    def get_capabilities(self, agent_id: UUID) -> List[AgentCapability]:
        """
        Get all capabilities for an agent.

        Args:
            agent_id: Agent to get capabilities for

        Returns:
            List of agent capabilities
        """
        return self._agent_capabilities.get(agent_id, []).copy()

    def get_capability(
        self,
        agent_id: UUID,
        capability_name: str,
    ) -> Optional[AgentCapability]:
        """
        Get a specific capability for an agent.

        Args:
            agent_id: Agent to query
            capability_name: Name of capability

        Returns:
            Capability if found, None otherwise
        """
        caps = self._agent_capabilities.get(agent_id, [])
        for cap in caps:
            if cap.name.lower() == capability_name.lower():
                return cap
        return None

    def has_capability(
        self,
        agent_id: UUID,
        capability_name: str,
        min_proficiency: float = 0.0,
    ) -> bool:
        """
        Check if agent has a capability with minimum proficiency.

        Args:
            agent_id: Agent to check
            capability_name: Name of capability
            min_proficiency: Minimum proficiency level

        Returns:
            True if agent has capability meeting threshold
        """
        cap = self.get_capability(agent_id, capability_name)
        if not cap:
            return False
        return cap.proficiency_level >= min_proficiency

    def find_agents_with_capability(
        self,
        capability_name: str,
        min_proficiency: float = 0.0,
    ) -> List[UUID]:
        """
        Find agents with a specific capability.

        Args:
            capability_name: Name of capability
            min_proficiency: Minimum proficiency level

        Returns:
            List of agent IDs with capability
        """
        cap_name = capability_name.lower()
        if cap_name not in self._capability_agents:
            return []

        agents = []
        for agent_id in self._capability_agents[cap_name]:
            cap = self.get_capability(agent_id, capability_name)
            if cap and cap.proficiency_level >= min_proficiency:
                agents.append(agent_id)

        return agents

    def find_agents_by_category(
        self,
        category: CapabilityCategory,
    ) -> List[UUID]:
        """
        Find agents with capabilities in a category.

        Args:
            category: Capability category

        Returns:
            List of agent IDs
        """
        agents = set()
        for agent_id, caps in self._agent_capabilities.items():
            for cap in caps:
                if cap.category == category:
                    agents.add(agent_id)
                    break
        return list(agents)

    # =========================================================================
    # Built-in Capabilities
    # =========================================================================

    def get_builtin(self, name: str) -> Optional[AgentCapability]:
        """
        Get a built-in capability definition.

        Args:
            name: Capability name

        Returns:
            Built-in capability if exists
        """
        return self._builtin_capabilities.get(name)

    def list_builtins(self) -> List[str]:
        """
        List all built-in capability names.

        Returns:
            List of capability names
        """
        return list(self._builtin_capabilities.keys())

    def create_from_builtin(
        self,
        name: str,
        proficiency_level: Optional[float] = None,
    ) -> Optional[AgentCapability]:
        """
        Create a capability instance from a built-in definition.

        Args:
            name: Built-in capability name
            proficiency_level: Override proficiency level

        Returns:
            New capability instance or None if not found
        """
        builtin = self.get_builtin(name)
        if not builtin:
            return None

        return AgentCapability(
            name=builtin.name,
            description=builtin.description,
            category=builtin.category,
            proficiency_level=(
                proficiency_level if proficiency_level is not None
                else builtin.proficiency_level
            ),
        )

    # =========================================================================
    # Statistics
    # =========================================================================

    @property
    def agent_count(self) -> int:
        """Get number of registered agents."""
        return len(self._agent_capabilities)

    @property
    def capability_count(self) -> int:
        """Get total number of registered capabilities."""
        return sum(len(caps) for caps in self._agent_capabilities.values())

    def get_capability_distribution(self) -> Dict[str, int]:
        """
        Get distribution of capabilities across agents.

        Returns:
            Dict mapping capability name to agent count
        """
        return {
            name: len(agents)
            for name, agents in self._capability_agents.items()
        }
