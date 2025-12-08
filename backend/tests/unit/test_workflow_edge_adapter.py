# =============================================================================
# IPA Platform - WorkflowEdgeAdapter Unit Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26, Story S26-2: WorkflowEdgeAdapter Tests
#
# Comprehensive tests for the WorkflowEdgeAdapter including:
#   - Simple edge creation
#   - Conditional edge evaluation
#   - ConditionEvaluator parsing and evaluation
#   - Factory functions
#   - Edge conversion
# =============================================================================

import pytest
from unittest.mock import MagicMock

from src.integrations.agent_framework.core.edge import (
    ConditionEvaluator,
    WorkflowEdgeAdapter,
    create_edge,
    create_edge_from_start,
    create_edge_to_end,
    convert_edges,
)
from src.domain.workflows.models import WorkflowEdge


# =============================================================================
# Test: ConditionEvaluator - Parsing
# =============================================================================

class TestConditionEvaluatorParsing:
    """Tests for ConditionEvaluator expression parsing."""

    def test_parse_equality_string(self):
        """Test parsing equality with string value."""
        evaluator = ConditionEvaluator("status == 'approved'")
        assert evaluator.expression == "status == 'approved'"

    def test_parse_equality_number(self):
        """Test parsing equality with numeric value."""
        evaluator = ConditionEvaluator("count == 5")
        assert evaluator.expression == "count == 5"

    def test_parse_inequality(self):
        """Test parsing inequality operator."""
        evaluator = ConditionEvaluator("status != 'rejected'")
        assert evaluator.expression == "status != 'rejected'"

    def test_parse_greater_than(self):
        """Test parsing greater than operator."""
        evaluator = ConditionEvaluator("value > 10")
        assert evaluator.expression == "value > 10"

    def test_parse_less_than(self):
        """Test parsing less than operator."""
        evaluator = ConditionEvaluator("priority < 5")
        assert evaluator.expression == "priority < 5"

    def test_parse_greater_equal(self):
        """Test parsing greater or equal operator."""
        evaluator = ConditionEvaluator("score >= 80")
        assert evaluator.expression == "score >= 80"

    def test_parse_less_equal(self):
        """Test parsing less or equal operator."""
        evaluator = ConditionEvaluator("age <= 65")
        assert evaluator.expression == "age <= 65"

    def test_parse_in_list(self):
        """Test parsing 'in' operator with list."""
        evaluator = ConditionEvaluator("status in ['approved', 'completed']")
        assert evaluator.expression == "status in ['approved', 'completed']"

    def test_parse_not_in_list(self):
        """Test parsing 'not in' operator with list."""
        evaluator = ConditionEvaluator("status not in ['rejected', 'cancelled']")
        assert evaluator.expression == "status not in ['rejected', 'cancelled']"

    def test_parse_jsonpath_prefix(self):
        """Test parsing with JSONPath prefix."""
        evaluator = ConditionEvaluator("$.result == 'success'")
        # Should strip the $. prefix internally
        assert evaluator.expression == "$.result == 'success'"

    def test_parse_boolean_check(self):
        """Test parsing simple boolean check (no operator)."""
        evaluator = ConditionEvaluator("is_valid")
        assert evaluator.expression == "is_valid"

    def test_parse_double_quoted_string(self):
        """Test parsing with double-quoted string."""
        evaluator = ConditionEvaluator('intent == "support"')
        assert evaluator.expression == 'intent == "support"'


# =============================================================================
# Test: ConditionEvaluator - Value Parsing
# =============================================================================

class TestConditionEvaluatorValueParsing:
    """Tests for ConditionEvaluator value parsing."""

    def test_parse_string_value_single_quotes(self):
        """Test parsing single-quoted string value."""
        evaluator = ConditionEvaluator("x == 'hello'")
        result = evaluator.evaluate({"x": "hello"})
        assert result is True

    def test_parse_string_value_double_quotes(self):
        """Test parsing double-quoted string value."""
        evaluator = ConditionEvaluator('x == "world"')
        result = evaluator.evaluate({"x": "world"})
        assert result is True

    def test_parse_integer_value(self):
        """Test parsing integer value."""
        evaluator = ConditionEvaluator("count == 42")
        result = evaluator.evaluate({"count": 42})
        assert result is True

    def test_parse_float_value(self):
        """Test parsing float value."""
        evaluator = ConditionEvaluator("score == 3.14")
        result = evaluator.evaluate({"score": 3.14})
        assert result is True

    def test_parse_boolean_true(self):
        """Test parsing boolean True value."""
        evaluator = ConditionEvaluator("active == true")
        result = evaluator.evaluate({"active": True})
        assert result is True

    def test_parse_boolean_false(self):
        """Test parsing boolean False value."""
        evaluator = ConditionEvaluator("disabled == false")
        result = evaluator.evaluate({"disabled": False})
        assert result is True

    def test_parse_none_value(self):
        """Test parsing None/null value."""
        evaluator = ConditionEvaluator("data == none")
        result = evaluator.evaluate({"data": None})
        assert result is True

    def test_parse_list_value(self):
        """Test parsing list value."""
        evaluator = ConditionEvaluator("status in ['a', 'b', 'c']")
        result = evaluator.evaluate({"status": "b"})
        assert result is True


# =============================================================================
# Test: ConditionEvaluator - Evaluation
# =============================================================================

class TestConditionEvaluatorEvaluation:
    """Tests for ConditionEvaluator condition evaluation."""

    def test_evaluate_equality_match(self):
        """Test equality evaluation matching."""
        evaluator = ConditionEvaluator("intent == 'support'")
        result = evaluator.evaluate({"intent": "support"})
        assert result is True

    def test_evaluate_equality_no_match(self):
        """Test equality evaluation not matching."""
        evaluator = ConditionEvaluator("intent == 'support'")
        result = evaluator.evaluate({"intent": "sales"})
        assert result is False

    def test_evaluate_inequality_match(self):
        """Test inequality evaluation matching."""
        evaluator = ConditionEvaluator("status != 'error'")
        result = evaluator.evaluate({"status": "success"})
        assert result is True

    def test_evaluate_greater_than(self):
        """Test greater than evaluation."""
        evaluator = ConditionEvaluator("score > 50")
        assert evaluator.evaluate({"score": 75}) is True
        assert evaluator.evaluate({"score": 50}) is False
        assert evaluator.evaluate({"score": 25}) is False

    def test_evaluate_less_than(self):
        """Test less than evaluation."""
        evaluator = ConditionEvaluator("age < 18")
        assert evaluator.evaluate({"age": 15}) is True
        assert evaluator.evaluate({"age": 18}) is False
        assert evaluator.evaluate({"age": 25}) is False

    def test_evaluate_greater_equal(self):
        """Test greater or equal evaluation."""
        evaluator = ConditionEvaluator("level >= 5")
        assert evaluator.evaluate({"level": 10}) is True
        assert evaluator.evaluate({"level": 5}) is True
        assert evaluator.evaluate({"level": 3}) is False

    def test_evaluate_less_equal(self):
        """Test less or equal evaluation."""
        evaluator = ConditionEvaluator("priority <= 3")
        assert evaluator.evaluate({"priority": 1}) is True
        assert evaluator.evaluate({"priority": 3}) is True
        assert evaluator.evaluate({"priority": 5}) is False

    def test_evaluate_in_list(self):
        """Test 'in' list evaluation."""
        evaluator = ConditionEvaluator("status in ['approved', 'completed']")
        assert evaluator.evaluate({"status": "approved"}) is True
        assert evaluator.evaluate({"status": "completed"}) is True
        assert evaluator.evaluate({"status": "pending"}) is False

    def test_evaluate_not_in_list(self):
        """Test 'not in' list evaluation."""
        evaluator = ConditionEvaluator("type not in ['error', 'warning']")
        assert evaluator.evaluate({"type": "info"}) is True
        assert evaluator.evaluate({"type": "error"}) is False

    def test_evaluate_boolean_check_true(self):
        """Test boolean check with truthy value."""
        evaluator = ConditionEvaluator("is_valid")
        assert evaluator.evaluate({"is_valid": True}) is True
        assert evaluator.evaluate({"is_valid": 1}) is True
        assert evaluator.evaluate({"is_valid": "yes"}) is True

    def test_evaluate_boolean_check_false(self):
        """Test boolean check with falsy value."""
        evaluator = ConditionEvaluator("is_valid")
        assert evaluator.evaluate({"is_valid": False}) is False
        assert evaluator.evaluate({"is_valid": 0}) is False
        assert evaluator.evaluate({"is_valid": ""}) is False
        assert evaluator.evaluate({"is_valid": None}) is False

    def test_evaluate_missing_key(self):
        """Test evaluation with missing key."""
        evaluator = ConditionEvaluator("missing_key == 'value'")
        result = evaluator.evaluate({"other_key": "data"})
        assert result is False  # None != 'value'

    def test_evaluate_nested_key(self):
        """Test evaluation with nested key path."""
        evaluator = ConditionEvaluator("result.status == 'success'")
        data = {"result": {"status": "success"}}
        result = evaluator.evaluate(data)
        assert result is True

    def test_evaluate_none_output(self):
        """Test evaluation with None output."""
        evaluator = ConditionEvaluator("status == 'ok'")
        result = evaluator.evaluate(None)
        assert result is False

    def test_evaluate_with_jsonpath_prefix(self):
        """Test evaluation with JSONPath prefix."""
        evaluator = ConditionEvaluator("$.result == 'done'")
        result = evaluator.evaluate({"result": "done"})
        assert result is True


# =============================================================================
# Test: ConditionEvaluator - Object Output
# =============================================================================

class TestConditionEvaluatorObjectOutput:
    """Tests for ConditionEvaluator with object outputs."""

    def test_evaluate_object_with_result_attribute(self):
        """Test evaluation with object having result attribute."""
        evaluator = ConditionEvaluator("status == 'complete'")

        class Output:
            result = {"status": "complete"}

        assert evaluator.evaluate(Output()) is True

    def test_evaluate_object_with_direct_attribute(self):
        """Test evaluation with object having direct attribute."""
        evaluator = ConditionEvaluator("value == 100")

        class Output:
            value = 100

        assert evaluator.evaluate(Output()) is True


# =============================================================================
# Test: WorkflowEdgeAdapter - Creation
# =============================================================================

class TestWorkflowEdgeAdapterCreation:
    """Tests for WorkflowEdgeAdapter creation."""

    def test_create_simple_edge(self):
        """Test creating adapter for simple edge."""
        edge = WorkflowEdge(source="node_a", target="node_b")
        adapter = WorkflowEdgeAdapter(edge)

        assert adapter.source == "node_a"
        assert adapter.target == "node_b"
        assert adapter.condition is None
        assert adapter.has_condition is False

    def test_create_conditional_edge(self):
        """Test creating adapter for conditional edge."""
        edge = WorkflowEdge(
            source="gateway",
            target="handler",
            condition="intent == 'support'",
        )
        adapter = WorkflowEdgeAdapter(edge)

        assert adapter.source == "gateway"
        assert adapter.target == "handler"
        assert adapter.condition == "intent == 'support'"
        assert adapter.has_condition is True

    def test_create_edge_with_label(self):
        """Test creating adapter for edge with label."""
        edge = WorkflowEdge(
            source="a",
            target="b",
            label="Success Path",
        )
        adapter = WorkflowEdgeAdapter(edge)

        assert adapter.label == "Success Path"


# =============================================================================
# Test: WorkflowEdgeAdapter - Conversion
# =============================================================================

class TestWorkflowEdgeAdapterConversion:
    """Tests for WorkflowEdgeAdapter to official Edge conversion."""

    def test_convert_simple_edge(self):
        """Test converting simple edge to official Edge."""
        edge = WorkflowEdge(source="start", target="process")
        adapter = WorkflowEdgeAdapter(edge)

        official_edge = adapter.to_official_edge()

        assert official_edge.source == "start"
        assert official_edge.target == "process"

    def test_convert_conditional_edge(self):
        """Test converting conditional edge to official Edge."""
        edge = WorkflowEdge(
            source="classifier",
            target="support_handler",
            condition="intent == 'support'",
        )
        adapter = WorkflowEdgeAdapter(edge)

        official_edge = adapter.to_official_edge()

        assert official_edge.source == "classifier"
        assert official_edge.target == "support_handler"
        # Condition should be a callable
        assert callable(official_edge.condition)

    def test_converted_edge_condition_works(self):
        """Test that converted edge condition function works correctly."""
        edge = WorkflowEdge(
            source="a",
            target="b",
            condition="result == 'success'",
        )
        adapter = WorkflowEdgeAdapter(edge)
        official_edge = adapter.to_official_edge()

        # Test the condition function
        assert official_edge.condition({"result": "success"}) is True
        assert official_edge.condition({"result": "failure"}) is False


# =============================================================================
# Test: WorkflowEdgeAdapter - Condition Evaluation
# =============================================================================

class TestWorkflowEdgeAdapterConditionEvaluation:
    """Tests for WorkflowEdgeAdapter condition evaluation."""

    def test_evaluate_condition_match(self):
        """Test condition evaluation matching."""
        edge = WorkflowEdge(
            source="a",
            target="b",
            condition="status == 'ready'",
        )
        adapter = WorkflowEdgeAdapter(edge)

        assert adapter.evaluate_condition({"status": "ready"}) is True
        assert adapter.evaluate_condition({"status": "pending"}) is False

    def test_evaluate_no_condition(self):
        """Test evaluation when no condition exists."""
        edge = WorkflowEdge(source="a", target="b")
        adapter = WorkflowEdgeAdapter(edge)

        # Should always return True when no condition
        assert adapter.evaluate_condition({"anything": "value"}) is True
        assert adapter.evaluate_condition(None) is True

    def test_evaluate_complex_condition(self):
        """Test evaluation with complex condition."""
        edge = WorkflowEdge(
            source="validator",
            target="approver",
            condition="score >= 80",
        )
        adapter = WorkflowEdgeAdapter(edge)

        assert adapter.evaluate_condition({"score": 95}) is True
        assert adapter.evaluate_condition({"score": 80}) is True
        assert adapter.evaluate_condition({"score": 79}) is False


# =============================================================================
# Test: WorkflowEdgeAdapter - Repr
# =============================================================================

class TestWorkflowEdgeAdapterRepr:
    """Tests for WorkflowEdgeAdapter string representation."""

    def test_repr_simple(self):
        """Test repr for simple edge."""
        edge = WorkflowEdge(source="a", target="b")
        adapter = WorkflowEdgeAdapter(edge)

        assert "a -> b" in repr(adapter)
        assert "condition" not in repr(adapter)

    def test_repr_conditional(self):
        """Test repr for conditional edge."""
        edge = WorkflowEdge(
            source="a",
            target="b",
            condition="x == 1",
        )
        adapter = WorkflowEdgeAdapter(edge)

        assert "a -> b" in repr(adapter)
        assert "condition='x == 1'" in repr(adapter)


# =============================================================================
# Test: Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for edge factory functions."""

    def test_create_edge_simple(self):
        """Test create_edge factory for simple edge."""
        edge = create_edge("node_1", "node_2")

        assert edge.source == "node_1"
        assert edge.target == "node_2"

    def test_create_edge_with_condition(self):
        """Test create_edge factory with condition."""
        edge = create_edge(
            source="check",
            target="process",
            condition="valid == true",
        )

        assert edge.source == "check"
        assert edge.target == "process"
        assert callable(edge.condition)

    def test_create_edge_from_start(self):
        """Test create_edge_from_start factory."""
        edge = create_edge_from_start("first_node")

        assert edge.source == "start"
        assert edge.target == "first_node"

    def test_create_edge_to_end(self):
        """Test create_edge_to_end factory."""
        edge = create_edge_to_end("last_node")

        assert edge.source == "last_node"
        assert edge.target == "end"


# =============================================================================
# Test: Batch Conversion
# =============================================================================

class TestBatchConversion:
    """Tests for batch edge conversion."""

    def test_convert_edges_empty_list(self):
        """Test converting empty list."""
        result = convert_edges([])
        assert result == []

    def test_convert_edges_single(self):
        """Test converting single edge."""
        edges = [WorkflowEdge(source="a", target="b")]
        result = convert_edges(edges)

        assert len(result) == 1
        assert result[0].source == "a"
        assert result[0].target == "b"

    def test_convert_edges_multiple(self):
        """Test converting multiple edges."""
        edges = [
            WorkflowEdge(source="start", target="process"),
            WorkflowEdge(source="process", target="validate", condition="ok == true"),
            WorkflowEdge(source="validate", target="end"),
        ]
        result = convert_edges(edges)

        assert len(result) == 3
        assert result[0].source == "start"
        assert result[1].source == "process"
        assert callable(result[1].condition)
        assert result[2].target == "end"

    def test_convert_edges_preserves_order(self):
        """Test that conversion preserves edge order."""
        edges = [
            WorkflowEdge(source="1", target="2"),
            WorkflowEdge(source="2", target="3"),
            WorkflowEdge(source="3", target="4"),
        ]
        result = convert_edges(edges)

        sources = [e.source for e in result]
        assert sources == ["1", "2", "3"]


# =============================================================================
# Test: Integration Scenarios
# =============================================================================

class TestIntegrationScenarios:
    """Integration tests for realistic workflow scenarios."""

    def test_intent_routing_workflow(self):
        """Test intent-based routing scenario."""
        # Simulate classifier -> gateway -> multiple handlers
        edges = [
            WorkflowEdge(source="start", target="classifier"),
            WorkflowEdge(
                source="classifier",
                target="support_handler",
                condition="intent == 'support'",
            ),
            WorkflowEdge(
                source="classifier",
                target="sales_handler",
                condition="intent == 'sales'",
            ),
            WorkflowEdge(
                source="classifier",
                target="default_handler",
                condition="intent not in ['support', 'sales']",
            ),
        ]

        official_edges = convert_edges(edges)

        # Test routing based on intent
        support_edge = official_edges[1]
        sales_edge = official_edges[2]
        default_edge = official_edges[3]

        output_support = {"intent": "support"}
        output_sales = {"intent": "sales"}
        output_other = {"intent": "billing"}

        assert support_edge.condition(output_support) is True
        assert support_edge.condition(output_sales) is False

        assert sales_edge.condition(output_sales) is True
        assert sales_edge.condition(output_support) is False

        assert default_edge.condition(output_other) is True
        assert default_edge.condition(output_support) is False

    def test_approval_workflow(self):
        """Test approval workflow with score-based routing."""
        edges = [
            WorkflowEdge(
                source="validator",
                target="auto_approve",
                condition="score >= 90",
            ),
            WorkflowEdge(
                source="validator",
                target="manual_review",
                condition="score >= 60",
            ),
            WorkflowEdge(
                source="validator",
                target="auto_reject",
                condition="score < 60",
            ),
        ]

        official_edges = convert_edges(edges)

        auto_approve = official_edges[0]
        manual_review = official_edges[1]
        auto_reject = official_edges[2]

        # High score -> auto approve
        assert auto_approve.condition({"score": 95}) is True
        assert manual_review.condition({"score": 95}) is True  # Also matches >= 60
        assert auto_reject.condition({"score": 95}) is False

        # Medium score -> manual review
        assert auto_approve.condition({"score": 75}) is False
        assert manual_review.condition({"score": 75}) is True
        assert auto_reject.condition({"score": 75}) is False

        # Low score -> auto reject
        assert auto_approve.condition({"score": 40}) is False
        assert manual_review.condition({"score": 40}) is False
        assert auto_reject.condition({"score": 40}) is True
