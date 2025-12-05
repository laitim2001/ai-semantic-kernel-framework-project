# =============================================================================
# IPA Platform - Handoff Triggers Unit Tests
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Tests for handoff triggers including:
#   - TriggerType enumeration
#   - TriggerPriority enumeration
#   - TriggerCondition data structure
#   - HandoffTrigger data structure
#   - TriggerRegistry management
#   - ConditionParser parsing and evaluation
#   - HandoffTriggerEvaluator evaluation logic
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.domain.orchestration.handoff.triggers import (
    HandoffTrigger,
    TriggerCondition,
    TriggerEvaluationResult,
    TriggerPriority,
    TriggerRegistry,
    TriggerType,
)
from src.domain.orchestration.handoff.trigger_evaluator import (
    ConditionParser,
    HandoffTriggerEvaluator,
)


# =============================================================================
# TriggerType Tests
# =============================================================================


class TestTriggerType:
    """Tests for TriggerType enum."""

    def test_type_values(self):
        """Test all type enum values."""
        assert TriggerType.CONDITION.value == "condition"
        assert TriggerType.EVENT.value == "event"
        assert TriggerType.TIMEOUT.value == "timeout"
        assert TriggerType.ERROR.value == "error"
        assert TriggerType.CAPABILITY.value == "capability"
        assert TriggerType.EXPLICIT.value == "explicit"

    def test_type_from_string(self):
        """Test creating type from string."""
        assert TriggerType("condition") == TriggerType.CONDITION
        assert TriggerType("event") == TriggerType.EVENT
        assert TriggerType("timeout") == TriggerType.TIMEOUT


# =============================================================================
# TriggerPriority Tests
# =============================================================================


class TestTriggerPriority:
    """Tests for TriggerPriority enum."""

    def test_priority_values(self):
        """Test priority values ordering."""
        assert TriggerPriority.LOW.value == 0
        assert TriggerPriority.NORMAL.value == 50
        assert TriggerPriority.HIGH.value == 100
        assert TriggerPriority.CRITICAL.value == 200

    def test_priority_comparison(self):
        """Test priority value comparison."""
        assert TriggerPriority.LOW.value < TriggerPriority.NORMAL.value
        assert TriggerPriority.NORMAL.value < TriggerPriority.HIGH.value
        assert TriggerPriority.HIGH.value < TriggerPriority.CRITICAL.value


# =============================================================================
# TriggerCondition Tests
# =============================================================================


class TestTriggerCondition:
    """Tests for TriggerCondition dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        condition = TriggerCondition()

        assert condition.expression is None
        assert condition.event_names == []
        assert condition.timeout_seconds is None
        assert condition.error_types == []
        assert condition.capability_requirements == []
        assert condition.metadata == {}

    def test_condition_expression(self):
        """Test condition with expression."""
        condition = TriggerCondition(
            expression="confidence < 0.5",
        )

        assert condition.expression == "confidence < 0.5"

    def test_event_condition(self):
        """Test condition with events."""
        condition = TriggerCondition(
            event_names=["task_failed", "timeout"],
        )

        assert len(condition.event_names) == 2
        assert "task_failed" in condition.event_names

    def test_timeout_condition(self):
        """Test condition with timeout."""
        condition = TriggerCondition(
            timeout_seconds=300,
        )

        assert condition.timeout_seconds == 300


# =============================================================================
# HandoffTrigger Tests
# =============================================================================


class TestHandoffTrigger:
    """Tests for HandoffTrigger dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        trigger = HandoffTrigger()

        assert trigger.id is not None
        assert trigger.trigger_type == TriggerType.CONDITION
        assert trigger.priority == TriggerPriority.NORMAL.value
        assert trigger.enabled is True
        assert isinstance(trigger.created_at, datetime)

    def test_initialization_with_type(self):
        """Test initialization with specific type."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.TIMEOUT,
            priority=TriggerPriority.HIGH.value,
            description="Timeout trigger",
        )

        assert trigger.trigger_type == TriggerType.TIMEOUT
        assert trigger.priority == 100
        assert trigger.description == "Timeout trigger"

    def test_trigger_with_condition(self):
        """Test trigger with condition."""
        condition = TriggerCondition(expression="status == 'failed'")
        trigger = HandoffTrigger(
            trigger_type=TriggerType.CONDITION,
            condition=condition,
        )

        assert trigger.condition.expression == "status == 'failed'"

    def test_trigger_with_target(self):
        """Test trigger with target agent."""
        target_id = uuid4()
        trigger = HandoffTrigger(
            target_agent_id=target_id,
            target_capabilities=["analysis", "reporting"],
        )

        assert trigger.target_agent_id == target_id
        assert "analysis" in trigger.target_capabilities


# =============================================================================
# TriggerEvaluationResult Tests
# =============================================================================


class TestTriggerEvaluationResult:
    """Tests for TriggerEvaluationResult dataclass."""

    def test_basic_result(self):
        """Test basic result creation."""
        trigger_id = uuid4()
        result = TriggerEvaluationResult(
            trigger_id=trigger_id,
            triggered=True,
            trigger_type=TriggerType.CONDITION,
            reason="Condition met",
        )

        assert result.trigger_id == trigger_id
        assert result.triggered is True
        assert result.trigger_type == TriggerType.CONDITION
        assert result.reason == "Condition met"

    def test_result_with_target(self):
        """Test result with suggested target."""
        target_id = uuid4()
        result = TriggerEvaluationResult(
            trigger_id=uuid4(),
            triggered=True,
            trigger_type=TriggerType.CAPABILITY,
            suggested_target=target_id,
        )

        assert result.suggested_target == target_id


# =============================================================================
# TriggerRegistry Tests
# =============================================================================


class TestTriggerRegistry:
    """Tests for TriggerRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create registry instance."""
        return TriggerRegistry()

    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert registry.trigger_count == 0
        assert registry.agent_count == 0

    def test_register_trigger(self, registry):
        """Test trigger registration."""
        agent_id = uuid4()
        trigger = HandoffTrigger(
            trigger_type=TriggerType.TIMEOUT,
            condition=TriggerCondition(timeout_seconds=60),
        )

        result = registry.register_trigger(agent_id, trigger)

        assert result == trigger
        assert registry.trigger_count == 1
        assert registry.agent_count == 1

    def test_get_triggers_for_agent(self, registry):
        """Test getting triggers for an agent."""
        agent_id = uuid4()

        for i in range(3):
            registry.register_trigger(
                agent_id,
                HandoffTrigger(priority=i * 50),
            )

        triggers = registry.get_triggers_for_agent(agent_id)

        assert len(triggers) == 3
        # Should be sorted by priority (highest first)
        assert triggers[0].priority >= triggers[1].priority

    def test_get_triggers_enabled_only(self, registry):
        """Test filtering by enabled status."""
        agent_id = uuid4()

        trigger1 = HandoffTrigger(enabled=True)
        trigger2 = HandoffTrigger(enabled=False)

        registry.register_trigger(agent_id, trigger1)
        registry.register_trigger(agent_id, trigger2)

        enabled = registry.get_triggers_for_agent(agent_id, enabled_only=True)
        all_triggers = registry.get_triggers_for_agent(agent_id, enabled_only=False)

        assert len(enabled) == 1
        assert len(all_triggers) == 2

    def test_get_trigger_by_id(self, registry):
        """Test getting trigger by ID."""
        agent_id = uuid4()
        trigger = HandoffTrigger()
        registry.register_trigger(agent_id, trigger)

        result = registry.get_trigger(trigger.id)

        assert result == trigger

    def test_get_trigger_not_found(self, registry):
        """Test getting non-existent trigger."""
        result = registry.get_trigger(uuid4())

        assert result is None

    def test_get_triggers_by_type(self, registry):
        """Test filtering by trigger type."""
        agent_id = uuid4()

        registry.register_trigger(
            agent_id, HandoffTrigger(trigger_type=TriggerType.TIMEOUT)
        )
        registry.register_trigger(
            agent_id, HandoffTrigger(trigger_type=TriggerType.ERROR)
        )
        registry.register_trigger(
            agent_id, HandoffTrigger(trigger_type=TriggerType.TIMEOUT)
        )

        timeouts = registry.get_triggers_by_type(TriggerType.TIMEOUT)

        assert len(timeouts) == 2

    def test_enable_trigger(self, registry):
        """Test enabling a trigger."""
        trigger = HandoffTrigger(enabled=False)
        registry.register_trigger(uuid4(), trigger)

        result = registry.enable_trigger(trigger.id)

        assert result is True
        assert trigger.enabled is True

    def test_disable_trigger(self, registry):
        """Test disabling a trigger."""
        trigger = HandoffTrigger(enabled=True)
        registry.register_trigger(uuid4(), trigger)

        result = registry.disable_trigger(trigger.id)

        assert result is True
        assert trigger.enabled is False

    def test_remove_trigger(self, registry):
        """Test removing a trigger."""
        agent_id = uuid4()
        trigger = HandoffTrigger()
        registry.register_trigger(agent_id, trigger)

        result = registry.remove_trigger(trigger.id)

        assert result is True
        assert registry.trigger_count == 0

    def test_remove_triggers_for_agent(self, registry):
        """Test removing all triggers for an agent."""
        agent_id = uuid4()

        for _ in range(3):
            registry.register_trigger(agent_id, HandoffTrigger())

        count = registry.remove_triggers_for_agent(agent_id)

        assert count == 3
        assert registry.trigger_count == 0

    def test_clear_all(self, registry):
        """Test clearing all triggers."""
        for _ in range(5):
            registry.register_trigger(uuid4(), HandoffTrigger())

        registry.clear_all()

        assert registry.trigger_count == 0
        assert registry.agent_count == 0


# =============================================================================
# ConditionParser Tests
# =============================================================================


class TestConditionParser:
    """Tests for ConditionParser class."""

    def test_parse_equality(self):
        """Test equality comparison."""
        context = {"status": "active"}
        result = ConditionParser.parse("status == 'active'", context)
        assert result is True

    def test_parse_inequality(self):
        """Test inequality comparison."""
        context = {"status": "active"}
        result = ConditionParser.parse("status != 'failed'", context)
        assert result is True

    def test_parse_less_than(self):
        """Test less than comparison."""
        context = {"confidence": 0.3}
        result = ConditionParser.parse("confidence < 0.5", context)
        assert result is True

    def test_parse_greater_than(self):
        """Test greater than comparison."""
        context = {"error_count": 5}
        result = ConditionParser.parse("error_count > 3", context)
        assert result is True

    def test_parse_less_than_or_equal(self):
        """Test less than or equal comparison."""
        context = {"retries": 3}
        result = ConditionParser.parse("retries <= 3", context)
        assert result is True

    def test_parse_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        context = {"score": 80}
        result = ConditionParser.parse("score >= 80", context)
        assert result is True

    def test_parse_boolean_true(self):
        """Test parsing boolean true."""
        context = {"is_valid": True}
        result = ConditionParser.parse("is_valid == true", context)
        assert result is True

    def test_parse_boolean_false(self):
        """Test parsing boolean false."""
        context = {"is_active": False}
        result = ConditionParser.parse("is_active == false", context)
        assert result is True

    def test_parse_integer(self):
        """Test parsing integer values."""
        context = {"count": 10}
        result = ConditionParser.parse("count == 10", context)
        assert result is True

    def test_parse_float(self):
        """Test parsing float values."""
        context = {"ratio": 0.75}
        result = ConditionParser.parse("ratio > 0.5", context)
        assert result is True

    def test_parse_missing_field(self):
        """Test handling missing field."""
        context = {}
        result = ConditionParser.parse("missing_field == 'value'", context)
        assert result is False

    def test_parse_invalid_expression(self):
        """Test invalid expression format."""
        with pytest.raises(ValueError):
            ConditionParser.parse("invalid expression", {})

    def test_parse_quoted_string(self):
        """Test parsing quoted string values."""
        context = {"name": "test"}
        result = ConditionParser.parse('name == "test"', context)
        assert result is True

    def test_parse_value_types(self):
        """Test _parse_value for various types."""
        assert ConditionParser._parse_value("true") is True
        assert ConditionParser._parse_value("false") is False
        assert ConditionParser._parse_value("none") is None
        assert ConditionParser._parse_value("123") == 123
        assert ConditionParser._parse_value("12.5") == 12.5
        assert ConditionParser._parse_value("'hello'") == "hello"


# =============================================================================
# HandoffTriggerEvaluator Tests
# =============================================================================


class TestHandoffTriggerEvaluator:
    """Tests for HandoffTriggerEvaluator class."""

    @pytest.fixture
    def registry(self):
        """Create registry instance."""
        return TriggerRegistry()

    @pytest.fixture
    def evaluator(self, registry):
        """Create evaluator instance."""
        return HandoffTriggerEvaluator(registry)

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_evaluator_initialization(self, evaluator):
        """Test evaluator initialization."""
        assert evaluator.registry is not None

    def test_evaluator_with_default_registry(self):
        """Test evaluator creates default registry."""
        evaluator = HandoffTriggerEvaluator()
        assert evaluator.registry is not None

    # -------------------------------------------------------------------------
    # Condition Evaluation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_condition_trigger_true(self, evaluator):
        """Test condition trigger evaluates to true."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.CONDITION,
            condition=TriggerCondition(expression="confidence < 0.5"),
        )

        context = {"confidence": 0.3}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is True
        assert result.trigger_type == TriggerType.CONDITION

    @pytest.mark.asyncio
    async def test_evaluate_condition_trigger_false(self, evaluator):
        """Test condition trigger evaluates to false."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.CONDITION,
            condition=TriggerCondition(expression="confidence < 0.5"),
        )

        context = {"confidence": 0.8}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_evaluate_disabled_trigger(self, evaluator):
        """Test disabled trigger is not evaluated."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.CONDITION,
            enabled=False,
        )

        result = await evaluator.evaluate(trigger, {})

        assert result.triggered is False
        assert "disabled" in result.reason.lower()

    # -------------------------------------------------------------------------
    # Event Evaluation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_event_trigger_match(self, evaluator):
        """Test event trigger matches."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.EVENT,
            condition=TriggerCondition(event_names=["task_failed"]),
        )

        context = {"triggered_events": ["task_started", "task_failed"]}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_evaluate_event_trigger_no_match(self, evaluator):
        """Test event trigger no match."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.EVENT,
            condition=TriggerCondition(event_names=["task_failed"]),
        )

        context = {"triggered_events": ["task_started", "task_completed"]}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is False

    # -------------------------------------------------------------------------
    # Timeout Evaluation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_timeout_trigger_exceeded(self, evaluator):
        """Test timeout trigger when exceeded."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.TIMEOUT,
            condition=TriggerCondition(timeout_seconds=60),
        )

        context = {"elapsed_seconds": 90}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_evaluate_timeout_trigger_within(self, evaluator):
        """Test timeout trigger within threshold."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.TIMEOUT,
            condition=TriggerCondition(timeout_seconds=60),
        )

        context = {"elapsed_seconds": 30}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is False

    # -------------------------------------------------------------------------
    # Error Evaluation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_error_trigger_any(self, evaluator):
        """Test error trigger catches any error."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.ERROR,
            condition=TriggerCondition(),  # No specific error types
        )

        context = {"error_type": "ValidationError"}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_evaluate_error_trigger_specific(self, evaluator):
        """Test error trigger matches specific type."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.ERROR,
            condition=TriggerCondition(error_types=["TimeoutError", "NetworkError"]),
        )

        context = {"error_type": "TimeoutError"}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_evaluate_error_trigger_no_error(self, evaluator):
        """Test error trigger with no error in context."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.ERROR,
            condition=TriggerCondition(),
        )

        context = {}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is False

    # -------------------------------------------------------------------------
    # Capability Evaluation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_capability_trigger_missing(self, evaluator):
        """Test capability trigger with missing capabilities."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.CAPABILITY,
            condition=TriggerCondition(
                capability_requirements=["analysis", "reporting", "visualization"]
            ),
        )

        context = {"agent_capabilities": ["analysis"]}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_evaluate_capability_trigger_satisfied(self, evaluator):
        """Test capability trigger with all capabilities."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.CAPABILITY,
            condition=TriggerCondition(
                capability_requirements=["analysis", "reporting"]
            ),
        )

        context = {"agent_capabilities": ["analysis", "reporting", "visualization"]}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is False

    # -------------------------------------------------------------------------
    # Explicit Evaluation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_explicit_trigger(self, evaluator):
        """Test explicit trigger."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.EXPLICIT,
        )

        context = {"explicit_handoff_requested": True}
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_evaluate_explicit_trigger_specific(self, evaluator):
        """Test explicit trigger for specific ID."""
        trigger = HandoffTrigger(
            trigger_type=TriggerType.EXPLICIT,
        )

        context = {
            "explicit_handoff_requested": True,
            "explicit_trigger_id": str(trigger.id),
        }
        result = await evaluator.evaluate(trigger, context)

        assert result.triggered is True

    # -------------------------------------------------------------------------
    # Aggregate Evaluation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_all_triggers(self, evaluator, registry):
        """Test evaluating all triggers for an agent."""
        agent_id = uuid4()

        # Register multiple triggers
        registry.register_trigger(
            agent_id,
            HandoffTrigger(
                trigger_type=TriggerType.CONDITION,
                condition=TriggerCondition(expression="score < 50"),
            ),
        )
        registry.register_trigger(
            agent_id,
            HandoffTrigger(
                trigger_type=TriggerType.TIMEOUT,
                condition=TriggerCondition(timeout_seconds=60),
            ),
        )

        context = {"score": 30, "elapsed_seconds": 30}
        results = await evaluator.evaluate_all(agent_id, context)

        assert len(results) == 2
        # One should be triggered (condition), one not (timeout)
        triggered = [r for r in results if r.triggered]
        assert len(triggered) == 1

    @pytest.mark.asyncio
    async def test_get_matching_triggers(self, evaluator, registry):
        """Test getting only matching triggers."""
        agent_id = uuid4()

        registry.register_trigger(
            agent_id,
            HandoffTrigger(
                trigger_type=TriggerType.CONDITION,
                condition=TriggerCondition(expression="score < 50"),
                priority=TriggerPriority.HIGH.value,
            ),
        )
        registry.register_trigger(
            agent_id,
            HandoffTrigger(
                trigger_type=TriggerType.TIMEOUT,
                condition=TriggerCondition(timeout_seconds=60),
                priority=TriggerPriority.LOW.value,
            ),
        )

        context = {"score": 30, "elapsed_seconds": 90}
        matches = await evaluator.get_matching_triggers(agent_id, context)

        assert len(matches) == 2
        # Sorted by priority, high first
        assert matches[0].trigger_type == TriggerType.CONDITION

    @pytest.mark.asyncio
    async def test_should_trigger_handoff(self, evaluator, registry):
        """Test checking if any handoff should trigger."""
        agent_id = uuid4()

        registry.register_trigger(
            agent_id,
            HandoffTrigger(
                trigger_type=TriggerType.CONDITION,
                condition=TriggerCondition(expression="confidence < 0.5"),
                priority=TriggerPriority.HIGH.value,
            ),
        )

        context = {"confidence": 0.3}
        result = await evaluator.should_trigger_handoff(agent_id, context)

        assert result is not None
        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_should_trigger_handoff_none(self, evaluator, registry):
        """Test no handoff triggers."""
        agent_id = uuid4()

        registry.register_trigger(
            agent_id,
            HandoffTrigger(
                trigger_type=TriggerType.CONDITION,
                condition=TriggerCondition(expression="confidence < 0.5"),
            ),
        )

        context = {"confidence": 0.8}
        result = await evaluator.should_trigger_handoff(agent_id, context)

        assert result is None

    # -------------------------------------------------------------------------
    # Custom Evaluator Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_custom_evaluator_registration(self, evaluator):
        """Test registering custom evaluator."""
        async def custom_eval(trigger, context):
            return True, "Custom evaluation"

        evaluator.register_evaluator(TriggerType.CONDITION, custom_eval)

        trigger = HandoffTrigger(
            trigger_type=TriggerType.CONDITION,
        )

        result = await evaluator.evaluate(trigger, {})

        assert result.triggered is True
        assert "Custom" in result.reason
