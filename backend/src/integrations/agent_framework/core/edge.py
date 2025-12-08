# =============================================================================
# IPA Platform - WorkflowEdge Adapter
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26, Story S26-2: WorkflowEdgeAdapter (8 pts)
#
# This module adapts the existing WorkflowEdge to the official
# Microsoft Agent Framework Edge interface.
#
# Official API Pattern (from workflows-api.md):
#   Edge(source="node_a", target="node_b", condition=lambda output: ...)
#
# Key Features:
#   - Converts WorkflowEdge to official Edge
#   - Safe condition evaluation (no eval)
#   - Supports JSONPath-like expressions
#   - Factory methods for start/end edges
#
# IMPORTANT: Uses official Agent Framework API
#   from agent_framework.workflows import Edge
# =============================================================================

from typing import Any, Callable, Dict, List, Optional, Union
import re
import logging

# Official Agent Framework Import - MUST use this
from agent_framework.workflows import Edge

# Import existing domain models
from src.domain.workflows.models import WorkflowEdge


logger = logging.getLogger(__name__)


# =============================================================================
# ConditionEvaluator - Safe Expression Evaluation
# =============================================================================

class ConditionEvaluator:
    """
    Safe condition evaluator for workflow edge conditions.

    Evaluates condition expressions without using eval() for security.
    Supports common comparison operators and JSONPath-like expressions.

    Supported Patterns:
        - "result == 'success'"
        - "$.value > 10"
        - "status in ['approved', 'completed']"
        - "intent == 'support'"
        - "count >= 5"

    Example:
        >>> evaluator = ConditionEvaluator("status == 'approved'")
        >>> evaluator.evaluate({"status": "approved"})
        True
        >>> evaluator.evaluate({"status": "pending"})
        False

    IMPORTANT: Never uses eval() - all parsing is done safely
    """

    # Supported operators and their implementations
    OPERATORS = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">=": lambda a, b: a >= b if a is not None and b is not None else False,
        "<=": lambda a, b: a <= b if a is not None and b is not None else False,
        ">": lambda a, b: a > b if a is not None and b is not None else False,
        "<": lambda a, b: a < b if a is not None and b is not None else False,
        " in ": lambda a, b: a in b if b is not None else False,
        " not in ": lambda a, b: a not in b if b is not None else False,
    }

    def __init__(self, expression: str):
        """
        Initialize the condition evaluator.

        Args:
            expression: Condition expression string to evaluate
        """
        self._expression = expression.strip()
        self._parsed = self._parse(self._expression)

    @property
    def expression(self) -> str:
        """Get the original expression."""
        return self._expression

    def _parse(self, expression: str) -> Optional[Dict[str, Any]]:
        """
        Parse the expression into components.

        Args:
            expression: The expression to parse

        Returns:
            Parsed expression dict with key, operator, value
        """
        # Handle JSONPath prefix
        if expression.startswith("$."):
            expression = expression[2:]

        # Try each operator (order matters - longer operators first)
        for op in [" not in ", " in ", ">=", "<=", "!=", "==", ">", "<"]:
            if op in expression:
                parts = expression.split(op, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value_str = parts[1].strip()

                    return {
                        "key": key,
                        "operator": op,
                        "value": self._parse_value(value_str),
                    }

        # No operator found - treat as boolean check
        return {
            "key": expression,
            "operator": "bool",
            "value": None,
        }

    def _parse_value(self, value_str: str) -> Any:
        """
        Parse a value string into the appropriate Python type.

        Args:
            value_str: String representation of the value

        Returns:
            Parsed value (str, int, float, bool, list, or None)
        """
        value_str = value_str.strip()

        # Handle quoted strings
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]

        # Handle list values like ['a', 'b', 'c']
        if value_str.startswith("[") and value_str.endswith("]"):
            return self._parse_list(value_str)

        # Handle boolean literals
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # Handle None/null
        if value_str.lower() in ("none", "null"):
            return None

        # Handle numeric values
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # Return as string
        return value_str

    def _parse_list(self, list_str: str) -> List[Any]:
        """
        Parse a list string like ['a', 'b', 'c'].

        Args:
            list_str: String representation of a list

        Returns:
            Parsed list
        """
        # Remove brackets
        content = list_str[1:-1].strip()
        if not content:
            return []

        result = []
        # Simple parsing - split by comma and parse each item
        items = content.split(",")
        for item in items:
            result.append(self._parse_value(item.strip()))

        return result

    def evaluate(self, output: Any) -> bool:
        """
        Evaluate the condition against an output value.

        Args:
            output: The output to evaluate (dict, NodeOutput, or any value)

        Returns:
            True if condition is met, False otherwise
        """
        if self._parsed is None:
            logger.warning(f"Failed to parse expression: {self._expression}")
            return True  # Default to true on parse failure

        try:
            # Extract value from output based on type
            actual_value = self._get_value(output, self._parsed["key"])
            operator = self._parsed["operator"]
            expected_value = self._parsed["value"]

            # Boolean check (no operator)
            if operator == "bool":
                return bool(actual_value)

            # Apply operator
            if operator in self.OPERATORS:
                return self.OPERATORS[operator](actual_value, expected_value)

            logger.warning(f"Unknown operator: {operator}")
            return True

        except Exception as e:
            logger.error(f"Error evaluating condition '{self._expression}': {e}")
            return True  # Default to true on evaluation error

    def _get_value(self, output: Any, key: str) -> Any:
        """
        Extract a value from the output using the key path.

        Args:
            output: The output object to extract from
            key: The key or path to extract

        Returns:
            The extracted value or None if not found
        """
        # Handle None output
        if output is None:
            return None

        # Handle dict output
        if isinstance(output, dict):
            # Support nested keys with dot notation
            if "." in key:
                parts = key.split(".")
                current = output
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None
                return current
            return output.get(key)

        # Handle object with result attribute (NodeOutput)
        if hasattr(output, "result"):
            result = output.result
            if isinstance(result, dict):
                return result.get(key)
            # Check direct attribute
            if hasattr(result, key):
                return getattr(result, key)
            return result if key == "result" else None

        # Handle object with direct attribute
        if hasattr(output, key):
            return getattr(output, key)

        return None

    def __repr__(self) -> str:
        """String representation."""
        return f"ConditionEvaluator('{self._expression}')"


# =============================================================================
# WorkflowEdgeAdapter - Official Edge Adapter
# =============================================================================

class WorkflowEdgeAdapter:
    """
    Adapter to convert WorkflowEdge to official Agent Framework Edge.

    This class bridges the existing IPA WorkflowEdge model to the official
    Edge interface from Microsoft Agent Framework.

    Example:
        >>> from src.domain.workflows.models import WorkflowEdge
        >>> edge = WorkflowEdge(source="node_a", target="node_b", condition="result == 'success'")
        >>> adapter = WorkflowEdgeAdapter(edge)
        >>> official_edge = adapter.to_official_edge()
        >>> print(official_edge.source)  # "node_a"

    IMPORTANT: Uses official Edge from agent_framework.workflows
    """

    def __init__(self, edge: WorkflowEdge):
        """
        Initialize the edge adapter.

        Args:
            edge: The WorkflowEdge to adapt
        """
        self._edge = edge
        self._evaluator: Optional[ConditionEvaluator] = None

        if edge.condition:
            self._evaluator = ConditionEvaluator(edge.condition)

    @property
    def source(self) -> str:
        """Get the source node ID."""
        return self._edge.source

    @property
    def target(self) -> str:
        """Get the target node ID."""
        return self._edge.target

    @property
    def condition(self) -> Optional[str]:
        """Get the condition expression."""
        return self._edge.condition

    @property
    def label(self) -> Optional[str]:
        """Get the edge label."""
        return self._edge.label

    @property
    def has_condition(self) -> bool:
        """Check if edge has a condition."""
        return self._evaluator is not None

    def to_official_edge(self) -> Edge:
        """
        Convert to official Agent Framework Edge.

        Returns:
            Official Edge instance
        """
        if self._evaluator:
            return Edge(
                source=self._edge.source,
                target=self._edge.target,
                condition=self._evaluator.evaluate,
            )
        else:
            return Edge(
                source=self._edge.source,
                target=self._edge.target,
            )

    def evaluate_condition(self, output: Any) -> bool:
        """
        Evaluate the edge condition against an output.

        Args:
            output: The output to evaluate against

        Returns:
            True if condition passes or no condition exists
        """
        if self._evaluator:
            return self._evaluator.evaluate(output)
        return True

    def __repr__(self) -> str:
        """String representation."""
        cond = f", condition='{self._edge.condition}'" if self._edge.condition else ""
        return f"WorkflowEdgeAdapter({self._edge.source} -> {self._edge.target}{cond})"


# =============================================================================
# Factory Functions
# =============================================================================

def create_edge(
    source: str,
    target: str,
    condition: Optional[str] = None,
    label: Optional[str] = None,
) -> Edge:
    """
    Create an official Edge from parameters.

    Args:
        source: Source node ID
        target: Target node ID
        condition: Optional condition expression
        label: Optional display label

    Returns:
        Official Edge instance
    """
    workflow_edge = WorkflowEdge(
        source=source,
        target=target,
        condition=condition,
        label=label,
    )
    adapter = WorkflowEdgeAdapter(workflow_edge)
    return adapter.to_official_edge()


def create_edge_from_start(target: str) -> Edge:
    """
    Create an Edge from the workflow start point.

    Args:
        target: Target node ID

    Returns:
        Edge from "start" to target
    """
    return Edge(source="start", target=target)


def create_edge_to_end(source: str) -> Edge:
    """
    Create an Edge to the workflow end point.

    Args:
        source: Source node ID

    Returns:
        Edge from source to "end"
    """
    return Edge(source=source, target="end")


def convert_edges(edges: List[WorkflowEdge]) -> List[Edge]:
    """
    Convert a list of WorkflowEdges to official Edges.

    Args:
        edges: List of WorkflowEdge instances

    Returns:
        List of official Edge instances
    """
    result = []
    for edge in edges:
        adapter = WorkflowEdgeAdapter(edge)
        result.append(adapter.to_official_edge())
    return result
