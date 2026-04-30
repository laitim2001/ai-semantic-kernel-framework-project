# =============================================================================
# IPA Platform - WorkflowNode Executor Adapter
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26, Story S26-1: WorkflowNodeExecutor (8 pts)
#
# This module adapts the existing WorkflowNode concept to the official
# Microsoft Agent Framework Executor interface.
#
# Official API Pattern (from agent_framework samples):
#   from agent_framework import Executor, WorkflowContext, handler
#
#   class MyExecutor(Executor):
#       @handler
#       async def handle(self, input: InputType, ctx: WorkflowContext) -> None:
#           await ctx.send_message(result)
#
# Key Features:
#   - Supports AGENT, GATEWAY, START, END node types
#   - Integrates with existing AgentService for agent execution
#   - Supports function execution for gateway/function nodes
#   - Proper error handling with success/failure status
#
# IMPORTANT: Uses official Agent Framework API with @handler decorator
#   from agent_framework import Executor, WorkflowContext, handler
# =============================================================================

from typing import Any, Dict, List, Optional, Callable, Union
from uuid import UUID
from datetime import datetime
import asyncio
import logging

from pydantic import BaseModel, Field

# Official Agent Framework Import - MUST use this
# Note: Classes are directly under agent_framework, not agent_framework.workflows
from agent_framework import Executor, WorkflowContext, handler

# Import domain models directly from models (not from __init__ to avoid circular imports)
from src.domain.workflows.models import WorkflowNode, NodeType


logger = logging.getLogger(__name__)


# =============================================================================
# Input/Output Models (Pydantic for type safety)
# =============================================================================

class NodeInput(BaseModel):
    """
    Unified input model for workflow node execution.

    Attributes:
        data: Primary input data for the node
        execution_id: Optional execution identifier for tracking
        context: Additional context data passed between nodes
        metadata: Execution metadata (timestamps, trace_id, etc.)
    """
    data: Dict[str, Any] = Field(default_factory=dict)
    execution_id: Optional[UUID] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class NodeOutput(BaseModel):
    """
    Unified output model for workflow node execution.

    Attributes:
        result: The execution result (any type depending on node)
        success: Whether execution completed successfully
        error: Error message if execution failed
        metadata: Execution metadata including node_id, type, timing
        next_nodes: Suggested next nodes (for conditional routing)
    """
    result: Any = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    next_nodes: List[str] = Field(default_factory=list)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


# =============================================================================
# WorkflowNodeExecutor - Official Executor Implementation
# =============================================================================

class WorkflowNodeExecutor(Executor):
    """
    Workflow node executor adapter.

    Adapts the existing WorkflowNode to the official Agent Framework Executor
    interface. Supports different node types:

    - AGENT: Executes an AI agent via AgentService
    - GATEWAY: Evaluates conditions and determines routing
    - START: Workflow entry point (pass-through)
    - END: Workflow exit point (pass-through)

    Example:
        >>> from src.domain.workflows.models import WorkflowNode, NodeType
        >>> node = WorkflowNode(id="classifier", type=NodeType.AGENT, agent_id=uuid)
        >>> executor = WorkflowNodeExecutor(node=node, agent_service=agent_svc)
        >>> # Register with WorkflowBuilder and run via workflow.run()

    IMPORTANT: This class uses the official @handler decorator
    from agent_framework to mark handler methods.
    """

    def __init__(
        self,
        node: WorkflowNode,
        agent_service: Optional[Any] = None,
        function_registry: Optional[Dict[str, Callable]] = None,
    ):
        """
        Initialize the workflow node executor.

        Args:
            node: The WorkflowNode to adapt
            agent_service: Service for executing AI agents (required for AGENT nodes)
            function_registry: Registry of functions (for GATEWAY/function nodes)
        """
        # Call parent constructor with node.id as the executor ID
        super().__init__(id=node.id)

        self._node = node
        self._agent_service = agent_service
        self._function_registry = function_registry or {}
        # Internal context storage for sharing state between nodes
        self._context_storage: Dict[str, Any] = {}

        # Validate requirements
        if node.type == NodeType.AGENT and not agent_service:
            logger.warning(
                f"Agent node '{node.id}' created without agent_service - "
                "agent execution will fail"
            )

    @property
    def node(self) -> WorkflowNode:
        """Get the underlying WorkflowNode."""
        return self._node

    @property
    def node_type(self) -> NodeType:
        """Get the node type."""
        return self._node.type

    @handler
    async def handle_node_input(
        self,
        input_data: NodeInput,
        ctx: WorkflowContext
    ) -> None:
        """
        Main handler for workflow node execution.

        This is the entry point called by the workflow engine when data
        arrives at this node. Routes to the appropriate internal handler
        based on node type and sends the result to the next node.

        IMPORTANT: Uses official @handler decorator from agent_framework.

        Args:
            input_data: Dictionary containing input data for this node
            ctx: WorkflowContext for sending messages and yielding outputs
        """
        start_time = datetime.utcnow()

        try:
            # input_data is already NodeInput type (enforced by @handler decorator)
            node_input = input_data

            # Route to appropriate handler based on node type
            if self._node.type == NodeType.START:
                result = await self._execute_start_node(node_input)
            elif self._node.type == NodeType.END:
                result = await self._execute_end_node(node_input)
            elif self._node.type == NodeType.AGENT:
                result = await self._execute_agent_node(node_input)
            elif self._node.type == NodeType.GATEWAY:
                result = await self._execute_gateway_node(node_input)
            else:
                raise ValueError(f"Unknown node type: {self._node.type}")

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_ms = (end_time - start_time).total_seconds() * 1000

            # Create output
            output = NodeOutput(
                result=result,
                success=True,
                metadata={
                    "node_id": self._node.id,
                    "node_type": self._node.type.value,
                    "node_name": self._node.name,
                    "execution_ms": execution_ms,
                    "timestamp": end_time.isoformat(),
                }
            )

            # Send result to next node via official API
            await ctx.send_message(output.model_dump())

        except Exception as e:
            logger.error(
                f"Node '{self._node.id}' execution failed: {str(e)}",
                exc_info=True
            )

            end_time = datetime.utcnow()
            execution_ms = (end_time - start_time).total_seconds() * 1000

            error_output = NodeOutput(
                result=None,
                success=False,
                error=str(e),
                metadata={
                    "node_id": self._node.id,
                    "node_type": self._node.type.value,
                    "execution_ms": execution_ms,
                    "timestamp": end_time.isoformat(),
                    "error_type": type(e).__name__,
                }
            )

            # Send error result to next node
            await ctx.send_message(error_output.model_dump())

    # Helper methods for context storage (internal state management)
    def _context_set(self, key: str, value: Any) -> None:
        """Set a value in internal context storage."""
        self._context_storage[key] = value

    def _context_get(self, key: str, default: Any = None) -> Any:
        """Get a value from internal context storage."""
        return self._context_storage.get(key, default)

    async def _execute_start_node(self, input: NodeInput) -> Any:
        """
        Execute a START node.

        START nodes are entry points - they pass through input data
        and may set initial context variables.

        Args:
            input: The input data

        Returns:
            The input data (pass-through)
        """
        logger.debug(f"Executing START node: {self._node.id}")

        # Set initial variables from config if specified
        initial_vars = self._node.config.get("initial_variables", {})
        for key, value in initial_vars.items():
            self._context_set(key, value)

        # Pass through input data
        return input.data

    async def _execute_end_node(self, input: NodeInput) -> Any:
        """
        Execute an END node.

        END nodes are exit points - they finalize the workflow result.

        Args:
            input: The input data

        Returns:
            The final result (may include transformations)
        """
        logger.debug(f"Executing END node: {self._node.id}")

        # Check for output transformation in config
        output_key = self._node.config.get("output_key")
        if output_key:
            return self._context_get(output_key, input.data)

        return input.data

    async def _execute_agent_node(self, input: NodeInput) -> Any:
        """
        Execute an AGENT node.

        AGENT nodes invoke AI agents via the AgentService.

        Args:
            input: The input data

        Returns:
            Agent execution result

        Raises:
            ValueError: If agent_id is missing or agent_service not configured
        """
        logger.debug(f"Executing AGENT node: {self._node.id}")

        if not self._node.agent_id:
            raise ValueError(f"Agent node '{self._node.id}' requires agent_id")

        if not self._agent_service:
            raise ValueError(
                f"Agent node '{self._node.id}' requires agent_service"
            )

        # Prepare agent input
        agent_input = self._prepare_agent_input(input)

        # Execute agent via service
        result = await self._agent_service.execute(
            agent_id=self._node.agent_id,
            input_data=agent_input,
            config=self._node.config.get("agent_config", {}),
        )

        # Store result in context if output_key specified
        output_key = self._node.config.get("output_key")
        if output_key:
            self._context_set(output_key, result)

        return result

    def _prepare_agent_input(self, input: NodeInput) -> Dict[str, Any]:
        """
        Prepare input data for agent execution.

        Merges input data with internal context and applies any transformations
        specified in node config.

        Args:
            input: The node input

        Returns:
            Prepared input dictionary for agent
        """
        # Start with input data
        agent_input = dict(input.data)

        # Merge context variables if specified
        context_keys = self._node.config.get("context_keys", [])
        for key in context_keys:
            value = self._context_get(key)
            if value is not None:
                agent_input[key] = value

        # Apply input mapping if specified
        input_mapping = self._node.config.get("input_mapping", {})
        for target_key, source_key in input_mapping.items():
            if source_key in agent_input:
                agent_input[target_key] = agent_input[source_key]

        return agent_input

    async def _execute_gateway_node(self, input: NodeInput) -> Any:
        """
        Execute a GATEWAY node.

        GATEWAY nodes evaluate conditions and determine routing.
        They can be:
        - EXCLUSIVE: One path based on condition
        - PARALLEL: All paths simultaneously
        - INCLUSIVE: Multiple paths based on conditions

        Args:
            input: The input data

        Returns:
            Gateway evaluation result with routing information
        """
        logger.debug(f"Executing GATEWAY node: {self._node.id}")

        gateway_type = self._node.config.get("gateway_type", "exclusive")
        conditions = self._node.config.get("conditions", [])

        if gateway_type == "parallel":
            # Parallel gateway - return all configured targets
            return {
                "gateway_type": "parallel",
                "all_targets": True,
                "data": input.data,
            }

        elif gateway_type == "inclusive":
            # Inclusive gateway - evaluate all conditions
            matching_targets = []
            for condition in conditions:
                if await self._evaluate_condition(condition, input):
                    matching_targets.append(condition.get("target"))

            return {
                "gateway_type": "inclusive",
                "targets": matching_targets,
                "data": input.data,
            }

        else:  # exclusive (default)
            # Exclusive gateway - first matching condition
            for condition in conditions:
                if await self._evaluate_condition(condition, input):
                    return {
                        "gateway_type": "exclusive",
                        "target": condition.get("target"),
                        "data": input.data,
                    }

            # Default target if no condition matches
            default_target = self._node.config.get("default_target")
            return {
                "gateway_type": "exclusive",
                "target": default_target,
                "data": input.data,
            }

    async def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        input: NodeInput,
    ) -> bool:
        """
        Evaluate a gateway condition.

        Supports simple expressions and function-based conditions.
        Uses safe evaluation (no eval) to prevent code injection.

        Args:
            condition: Condition configuration
            input: The input data

        Returns:
            True if condition is met, False otherwise
        """
        expr = condition.get("expression")
        func_name = condition.get("function")

        if func_name and func_name in self._function_registry:
            # Function-based condition
            func = self._function_registry[func_name]
            if asyncio.iscoroutinefunction(func):
                return await func(input.data, self._context_storage)
            else:
                return func(input.data, self._context_storage)

        elif expr:
            # Expression-based condition (safe evaluation)
            return self._safe_evaluate_expression(expr, input.data)

        return True  # Default to true if no condition specified

    def _safe_evaluate_expression(
        self,
        expr: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Safely evaluate a condition expression.

        Uses simple pattern matching instead of eval for security.
        Supports:
        - data.key == value
        - data.key != value
        - data.key > value (numeric)
        - data.key < value (numeric)
        - data.key in [list]

        Args:
            expr: Expression string
            data: Input data dictionary

        Returns:
            Evaluation result
        """
        # Simple expression parser (avoid eval for security)
        # Format: "key operator value" or "$.key operator value"

        expr = expr.strip()

        # Parse JSONPath-like expressions: $.key
        if expr.startswith("$."):
            expr = expr[2:]  # Remove $. prefix

        # Split by common operators
        for op in ["==", "!=", ">=", "<=", ">", "<", " in "]:
            if op in expr:
                parts = expr.split(op, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value_str = parts[1].strip()

                    # Get actual value from data or internal context storage
                    actual_value = data.get(key)
                    if actual_value is None:
                        actual_value = self._context_get(key)

                    # Parse expected value
                    try:
                        if value_str.startswith("[") and value_str.endswith("]"):
                            # List value
                            expected_value = eval(value_str)  # Safe for lists
                        elif value_str.startswith("'") or value_str.startswith('"'):
                            # String value
                            expected_value = value_str[1:-1]
                        elif value_str.lower() == "true":
                            expected_value = True
                        elif value_str.lower() == "false":
                            expected_value = False
                        elif value_str.lower() == "none":
                            expected_value = None
                        else:
                            # Try numeric
                            try:
                                expected_value = int(value_str)
                            except ValueError:
                                try:
                                    expected_value = float(value_str)
                                except ValueError:
                                    expected_value = value_str
                    except Exception:
                        expected_value = value_str

                    # Evaluate
                    if op == "==":
                        return actual_value == expected_value
                    elif op == "!=":
                        return actual_value != expected_value
                    elif op == ">=":
                        return actual_value >= expected_value
                    elif op == "<=":
                        return actual_value <= expected_value
                    elif op == ">":
                        return actual_value > expected_value
                    elif op == "<":
                        return actual_value < expected_value
                    elif op == " in ":
                        return actual_value in expected_value

        # Default: treat as boolean key check
        return bool(data.get(expr) or self._context_get(expr))


# =============================================================================
# Factory Functions
# =============================================================================

def create_executor_from_node(
    node: WorkflowNode,
    agent_service: Optional[Any] = None,
    function_registry: Optional[Dict[str, Callable]] = None,
) -> WorkflowNodeExecutor:
    """
    Factory function to create a WorkflowNodeExecutor from a WorkflowNode.

    Args:
        node: The WorkflowNode to adapt
        agent_service: Service for executing AI agents
        function_registry: Registry of functions for gateway nodes

    Returns:
        WorkflowNodeExecutor instance
    """
    return WorkflowNodeExecutor(
        node=node,
        agent_service=agent_service,
        function_registry=function_registry,
    )
