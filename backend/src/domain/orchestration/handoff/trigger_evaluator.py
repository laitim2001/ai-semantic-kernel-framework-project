# =============================================================================
# IPA Platform - Handoff Trigger Evaluator
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Evaluates handoff trigger conditions to determine when handoff should occur.
# Supports evaluation of:
#   - Condition expressions (simple comparisons)
#   - Event-based triggers
#   - Timeout conditions
#   - Error conditions
#   - Capability requirements
#
# References:
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

from src.domain.orchestration.handoff.triggers import (
    HandoffTrigger,
    TriggerCondition,
    TriggerEvaluationResult,
    TriggerRegistry,
    TriggerType,
)

logger = logging.getLogger(__name__)


class ConditionParser:
    """
    Parses and evaluates condition expressions.

    Supports simple comparison expressions like:
        - "confidence < 0.5"
        - "error_count > 3"
        - "status == 'failed'"
        - "retry_count >= 5"
    """

    # Supported operators
    OPERATORS = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "<": lambda a, b: a < b,
        ">": lambda a, b: a > b,
        "<=": lambda a, b: a <= b,
        ">=": lambda a, b: a >= b,
        "in": lambda a, b: a in b,
        "not in": lambda a, b: a not in b,
    }

    # Pattern for parsing expressions
    EXPRESSION_PATTERN = re.compile(
        r"^\s*(\w+)\s*(==|!=|<=|>=|<|>|in|not in)\s*(.+)\s*$"
    )

    @classmethod
    def parse(cls, expression: str, context: Dict[str, Any]) -> bool:
        """
        Parse and evaluate a condition expression.

        Args:
            expression: Condition expression string
            context: Context dictionary with variable values

        Returns:
            True if condition is met, False otherwise

        Raises:
            ValueError: If expression format is invalid
        """
        if not expression:
            return False

        match = cls.EXPRESSION_PATTERN.match(expression.strip())
        if not match:
            raise ValueError(f"Invalid expression format: {expression}")

        field_name, operator, raw_value = match.groups()

        # Get field value from context
        field_value = context.get(field_name)
        if field_value is None:
            logger.debug(f"Field '{field_name}' not found in context")
            return False

        # Parse the comparison value
        comparison_value = cls._parse_value(raw_value.strip())

        # Get operator function
        op_func = cls.OPERATORS.get(operator)
        if not op_func:
            raise ValueError(f"Unknown operator: {operator}")

        try:
            result = op_func(field_value, comparison_value)
            logger.debug(
                f"Condition '{expression}': {field_value} {operator} "
                f"{comparison_value} = {result}"
            )
            return result
        except TypeError as e:
            logger.warning(f"Type error in condition evaluation: {e}")
            return False

    @classmethod
    def _parse_value(cls, value_str: str) -> Any:
        """
        Parse a string value into its appropriate type.

        Args:
            value_str: String representation of value

        Returns:
            Parsed value (int, float, bool, str, or list)
        """
        value_str = value_str.strip()

        # Handle quoted strings
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]

        # Handle booleans
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # Handle None
        if value_str.lower() in ("none", "null"):
            return None

        # Handle lists (simple format: [a, b, c])
        if value_str.startswith("[") and value_str.endswith("]"):
            items = value_str[1:-1].split(",")
            return [cls._parse_value(item.strip()) for item in items if item.strip()]

        # Handle numbers
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # Default to string
        return value_str


class HandoffTriggerEvaluator:
    """
    Evaluates handoff triggers based on current context.

    Provides functionality for:
        - Evaluating single triggers
        - Evaluating all triggers for an agent
        - Finding matching triggers
        - Custom evaluator registration

    Usage:
        evaluator = HandoffTriggerEvaluator(registry)

        # Evaluate a specific trigger
        result = await evaluator.evaluate(trigger, context)

        # Find all matching triggers for an agent
        matches = await evaluator.get_matching_triggers(agent_id, context)
    """

    def __init__(self, trigger_registry: TriggerRegistry = None):
        """
        Initialize HandoffTriggerEvaluator.

        Args:
            trigger_registry: Registry of triggers to evaluate
        """
        self._registry = trigger_registry or TriggerRegistry()

        # Custom evaluators by trigger type
        self._evaluators: Dict[TriggerType, Callable] = {
            TriggerType.CONDITION: self._evaluate_condition,
            TriggerType.EVENT: self._evaluate_event,
            TriggerType.TIMEOUT: self._evaluate_timeout,
            TriggerType.ERROR: self._evaluate_error,
            TriggerType.CAPABILITY: self._evaluate_capability,
            TriggerType.EXPLICIT: self._evaluate_explicit,
        }

        logger.info("HandoffTriggerEvaluator initialized")

    @property
    def registry(self) -> TriggerRegistry:
        """Get the trigger registry."""
        return self._registry

    def register_evaluator(
        self,
        trigger_type: TriggerType,
        evaluator: Callable,
    ) -> None:
        """
        Register a custom evaluator for a trigger type.

        Args:
            trigger_type: Type to register evaluator for
            evaluator: Async function (trigger, context) -> bool
        """
        self._evaluators[trigger_type] = evaluator
        logger.debug(f"Registered custom evaluator for {trigger_type.value}")

    async def evaluate(
        self,
        trigger: HandoffTrigger,
        context: Dict[str, Any],
    ) -> TriggerEvaluationResult:
        """
        Evaluate a single trigger against context.

        Args:
            trigger: Trigger to evaluate
            context: Current execution context

        Returns:
            TriggerEvaluationResult with evaluation outcome
        """
        if not trigger.enabled:
            return TriggerEvaluationResult(
                trigger_id=trigger.id,
                triggered=False,
                trigger_type=trigger.trigger_type,
                reason="Trigger is disabled",
            )

        evaluator = self._evaluators.get(trigger.trigger_type)
        if not evaluator:
            logger.warning(f"No evaluator for trigger type: {trigger.trigger_type}")
            return TriggerEvaluationResult(
                trigger_id=trigger.id,
                triggered=False,
                trigger_type=trigger.trigger_type,
                reason=f"No evaluator for type {trigger.trigger_type.value}",
            )

        try:
            triggered, reason = await evaluator(trigger, context)

            return TriggerEvaluationResult(
                trigger_id=trigger.id,
                triggered=triggered,
                trigger_type=trigger.trigger_type,
                reason=reason,
                suggested_target=trigger.target_agent_id if triggered else None,
                context=context,
            )

        except Exception as e:
            logger.error(f"Error evaluating trigger {trigger.id}: {e}")
            return TriggerEvaluationResult(
                trigger_id=trigger.id,
                triggered=False,
                trigger_type=trigger.trigger_type,
                reason=f"Evaluation error: {e}",
            )

    async def evaluate_all(
        self,
        agent_id: UUID,
        context: Dict[str, Any],
    ) -> List[TriggerEvaluationResult]:
        """
        Evaluate all triggers for an agent.

        Args:
            agent_id: Agent to evaluate triggers for
            context: Current execution context

        Returns:
            List of evaluation results for all triggers
        """
        triggers = self._registry.get_triggers_for_agent(agent_id, enabled_only=True)
        results = []

        for trigger in triggers:
            result = await self.evaluate(trigger, context)
            results.append(result)

        return results

    async def get_matching_triggers(
        self,
        agent_id: UUID,
        context: Dict[str, Any],
    ) -> List[TriggerEvaluationResult]:
        """
        Get all matching (triggered) triggers for an agent.

        Args:
            agent_id: Agent to check triggers for
            context: Current execution context

        Returns:
            List of triggered evaluation results, sorted by priority
        """
        all_results = await self.evaluate_all(agent_id, context)
        triggered = [r for r in all_results if r.triggered]

        # Sort by trigger priority (from trigger registry)
        return sorted(
            triggered,
            key=lambda r: self._registry.get_trigger(r.trigger_id).priority
            if self._registry.get_trigger(r.trigger_id) else 0,
            reverse=True,
        )

    async def should_trigger_handoff(
        self,
        agent_id: UUID,
        context: Dict[str, Any],
    ) -> Optional[TriggerEvaluationResult]:
        """
        Check if any trigger should fire and return the highest priority one.

        Args:
            agent_id: Agent to check triggers for
            context: Current execution context

        Returns:
            Highest priority triggered result, or None if no triggers matched
        """
        matches = await self.get_matching_triggers(agent_id, context)
        return matches[0] if matches else None

    # =========================================================================
    # Built-in Evaluators
    # =========================================================================

    async def _evaluate_condition(
        self,
        trigger: HandoffTrigger,
        context: Dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Evaluate condition-based trigger.

        Args:
            trigger: Trigger with condition expression
            context: Execution context

        Returns:
            Tuple of (triggered, reason)
        """
        expression = trigger.condition.expression
        if not expression:
            return False, "No condition expression defined"

        try:
            result = ConditionParser.parse(expression, context)
            return result, f"Condition '{expression}' = {result}"
        except ValueError as e:
            return False, f"Invalid condition: {e}"

    async def _evaluate_event(
        self,
        trigger: HandoffTrigger,
        context: Dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Evaluate event-based trigger.

        Args:
            trigger: Trigger with event names
            context: Execution context with triggered_events

        Returns:
            Tuple of (triggered, reason)
        """
        event_names = trigger.condition.event_names
        if not event_names:
            return False, "No event names defined"

        triggered_events = set(context.get("triggered_events", []))

        for event_name in event_names:
            if event_name in triggered_events:
                return True, f"Event '{event_name}' occurred"

        return False, f"No matching events (watching: {event_names})"

    async def _evaluate_timeout(
        self,
        trigger: HandoffTrigger,
        context: Dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Evaluate timeout-based trigger.

        Args:
            trigger: Trigger with timeout threshold
            context: Execution context with elapsed time

        Returns:
            Tuple of (triggered, reason)
        """
        timeout_seconds = trigger.condition.timeout_seconds
        if not timeout_seconds:
            return False, "No timeout threshold defined"

        elapsed = context.get("elapsed_seconds", 0)

        if elapsed >= timeout_seconds:
            return True, f"Timeout exceeded ({elapsed}s >= {timeout_seconds}s)"

        return False, f"Within timeout ({elapsed}s < {timeout_seconds}s)"

    async def _evaluate_error(
        self,
        trigger: HandoffTrigger,
        context: Dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Evaluate error-based trigger.

        Args:
            trigger: Trigger with error types
            context: Execution context with error info

        Returns:
            Tuple of (triggered, reason)
        """
        error_type = context.get("error_type")
        if not error_type:
            return False, "No error in context"

        error_types = trigger.condition.error_types
        if not error_types:
            # Any error triggers
            return True, f"Error occurred: {error_type}"

        if error_type in error_types:
            return True, f"Error '{error_type}' matches trigger"

        return False, f"Error '{error_type}' not in watched types {error_types}"

    async def _evaluate_capability(
        self,
        trigger: HandoffTrigger,
        context: Dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Evaluate capability-based trigger.

        Args:
            trigger: Trigger with capability requirements
            context: Execution context with agent capabilities

        Returns:
            Tuple of (triggered, reason)
        """
        required = set(trigger.condition.capability_requirements)
        if not required:
            return False, "No capability requirements defined"

        agent_capabilities = set(context.get("agent_capabilities", []))

        missing = required - agent_capabilities
        if missing:
            return True, f"Missing capabilities: {missing}"

        return False, "All required capabilities present"

    async def _evaluate_explicit(
        self,
        trigger: HandoffTrigger,
        context: Dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Evaluate explicit trigger.

        Args:
            trigger: Trigger for explicit handoff
            context: Execution context

        Returns:
            Tuple of (triggered, reason)
        """
        explicit_handoff = context.get("explicit_handoff_requested", False)
        trigger_id = context.get("explicit_trigger_id")

        if explicit_handoff:
            if trigger_id and str(trigger.id) == str(trigger_id):
                return True, "Explicit handoff requested for this trigger"
            elif not trigger_id:
                return True, "Explicit handoff requested"

        return False, "No explicit handoff requested"
