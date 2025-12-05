# =============================================================================
# IPA Platform - Handoff Triggers
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Defines handoff trigger types and conditions for automatic handoff.
# Supports multiple trigger types:
#   - CONDITION: Expression-based conditional triggers
#   - EVENT: Event-driven triggers
#   - TIMEOUT: Time-based triggers
#   - ERROR: Error-based triggers
#   - CAPABILITY: Capability mismatch triggers
#
# References:
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """
    Types of handoff triggers.

    Types:
        CONDITION: Triggered when a condition expression evaluates to True
        EVENT: Triggered by specific events
        TIMEOUT: Triggered after a time threshold
        ERROR: Triggered by error occurrences
        CAPABILITY: Triggered when agent lacks required capability
        EXPLICIT: Explicitly triggered by user or system
    """
    CONDITION = "condition"
    EVENT = "event"
    TIMEOUT = "timeout"
    ERROR = "error"
    CAPABILITY = "capability"
    EXPLICIT = "explicit"


class TriggerPriority(int, Enum):
    """
    Priority levels for trigger evaluation.

    Higher priority triggers are evaluated first.
    """
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


@dataclass
class TriggerCondition:
    """
    Defines conditions for a specific trigger type.

    Attributes:
        expression: Condition expression (for CONDITION type)
        event_names: List of event names to watch (for EVENT type)
        timeout_seconds: Timeout threshold in seconds (for TIMEOUT type)
        error_types: List of error types to match (for ERROR type)
        capability_requirements: Required capabilities (for CAPABILITY type)
        metadata: Additional condition metadata
    """
    expression: Optional[str] = None
    event_names: List[str] = field(default_factory=list)
    timeout_seconds: Optional[int] = None
    error_types: List[str] = field(default_factory=list)
    capability_requirements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffTrigger:
    """
    Handoff trigger definition.

    Attributes:
        id: Unique trigger identifier
        trigger_type: Type of trigger
        condition: Trigger condition details
        priority: Evaluation priority
        target_agent_id: Preferred target agent (optional)
        target_capabilities: Required capabilities for target
        enabled: Whether trigger is active
        description: Human-readable description
        created_at: When trigger was created
    """
    id: UUID = field(default_factory=uuid4)
    trigger_type: TriggerType = TriggerType.CONDITION
    condition: TriggerCondition = field(default_factory=TriggerCondition)
    priority: int = TriggerPriority.NORMAL.value
    target_agent_id: Optional[UUID] = None
    target_capabilities: List[str] = field(default_factory=list)
    enabled: bool = True
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TriggerEvaluationResult:
    """
    Result of trigger evaluation.

    Attributes:
        trigger_id: ID of the evaluated trigger
        triggered: Whether the trigger condition was met
        trigger_type: Type of the trigger
        reason: Reason for the result
        suggested_target: Suggested target agent ID
        context: Additional context from evaluation
        evaluated_at: When evaluation was performed
    """
    trigger_id: UUID
    triggered: bool
    trigger_type: TriggerType
    reason: str = ""
    suggested_target: Optional[UUID] = None
    context: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)


class TriggerRegistry:
    """
    Registry for managing handoff triggers.

    Provides functionality for:
        - Registering triggers for agents
        - Retrieving triggers by agent or type
        - Enabling/disabling triggers
        - Removing triggers
    """

    def __init__(self):
        """Initialize TriggerRegistry."""
        # Triggers indexed by agent ID
        self._agent_triggers: Dict[UUID, List[HandoffTrigger]] = {}

        # All triggers indexed by trigger ID
        self._triggers: Dict[UUID, HandoffTrigger] = {}

        logger.info("TriggerRegistry initialized")

    def register_trigger(
        self,
        agent_id: UUID,
        trigger: HandoffTrigger,
    ) -> HandoffTrigger:
        """
        Register a trigger for an agent.

        Args:
            agent_id: Agent to register trigger for
            trigger: Trigger definition

        Returns:
            Registered trigger
        """
        if agent_id not in self._agent_triggers:
            self._agent_triggers[agent_id] = []

        self._agent_triggers[agent_id].append(trigger)
        self._triggers[trigger.id] = trigger

        logger.debug(
            f"Registered trigger {trigger.id} for agent {agent_id}: "
            f"type={trigger.trigger_type.value}"
        )

        return trigger

    def get_triggers_for_agent(
        self,
        agent_id: UUID,
        enabled_only: bool = True,
    ) -> List[HandoffTrigger]:
        """
        Get all triggers for an agent.

        Args:
            agent_id: Agent to get triggers for
            enabled_only: Only return enabled triggers

        Returns:
            List of triggers sorted by priority (highest first)
        """
        triggers = self._agent_triggers.get(agent_id, [])

        if enabled_only:
            triggers = [t for t in triggers if t.enabled]

        # Sort by priority (highest first)
        return sorted(triggers, key=lambda t: t.priority, reverse=True)

    def get_trigger(self, trigger_id: UUID) -> Optional[HandoffTrigger]:
        """
        Get a specific trigger by ID.

        Args:
            trigger_id: Trigger ID to look up

        Returns:
            Trigger if found, None otherwise
        """
        return self._triggers.get(trigger_id)

    def get_triggers_by_type(
        self,
        trigger_type: TriggerType,
    ) -> List[HandoffTrigger]:
        """
        Get all triggers of a specific type.

        Args:
            trigger_type: Type to filter by

        Returns:
            List of matching triggers
        """
        return [
            t for t in self._triggers.values()
            if t.trigger_type == trigger_type
        ]

    def enable_trigger(self, trigger_id: UUID) -> bool:
        """
        Enable a trigger.

        Args:
            trigger_id: Trigger to enable

        Returns:
            True if trigger was found and enabled
        """
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.enabled = True
            logger.debug(f"Enabled trigger {trigger_id}")
            return True
        return False

    def disable_trigger(self, trigger_id: UUID) -> bool:
        """
        Disable a trigger.

        Args:
            trigger_id: Trigger to disable

        Returns:
            True if trigger was found and disabled
        """
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.enabled = False
            logger.debug(f"Disabled trigger {trigger_id}")
            return True
        return False

    def remove_trigger(self, trigger_id: UUID) -> bool:
        """
        Remove a trigger.

        Args:
            trigger_id: Trigger to remove

        Returns:
            True if trigger was found and removed
        """
        trigger = self._triggers.pop(trigger_id, None)
        if trigger:
            # Remove from agent triggers
            for agent_triggers in self._agent_triggers.values():
                if trigger in agent_triggers:
                    agent_triggers.remove(trigger)
            logger.debug(f"Removed trigger {trigger_id}")
            return True
        return False

    def remove_triggers_for_agent(self, agent_id: UUID) -> int:
        """
        Remove all triggers for an agent.

        Args:
            agent_id: Agent to remove triggers for

        Returns:
            Number of triggers removed
        """
        triggers = self._agent_triggers.pop(agent_id, [])
        for trigger in triggers:
            self._triggers.pop(trigger.id, None)

        logger.debug(f"Removed {len(triggers)} triggers for agent {agent_id}")
        return len(triggers)

    def clear_all(self) -> None:
        """Clear all registered triggers."""
        self._agent_triggers.clear()
        self._triggers.clear()
        logger.debug("Cleared all triggers")

    @property
    def trigger_count(self) -> int:
        """Get total number of registered triggers."""
        return len(self._triggers)

    @property
    def agent_count(self) -> int:
        """Get number of agents with triggers."""
        return len(self._agent_triggers)
