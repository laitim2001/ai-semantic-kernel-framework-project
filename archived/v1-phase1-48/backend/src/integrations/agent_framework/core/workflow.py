# =============================================================================
# IPA Platform - WorkflowDefinition Adapter
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26, Story S26-3: WorkflowDefinitionAdapter (10 pts)
#
# This module adapts the existing WorkflowDefinition to the official
# Microsoft Agent Framework Workflow interface.
#
# Official API Pattern (from WorkflowBuilder):
#   workflow = (
#       WorkflowBuilder()
#       .register_executor(factory, name="name")
#       .add_edge("source", "target")
#       .set_start_executor("name")
#       .build()
#   )
#   result = await workflow.run(message)
#
# Key Features:
#   - Converts WorkflowDefinition to official Workflow via WorkflowBuilder
#   - Integrates WorkflowNodeExecutor for node execution
#   - Supports checkpoint storage for persistence
#   - Provides run() and run_stream() methods
#
# IMPORTANT: Uses official Agent Framework API
#   from agent_framework import WorkflowBuilder
# =============================================================================

from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from uuid import UUID
from datetime import datetime
import logging

# Official Agent Framework Imports - MUST use these
# Note: Classes are directly under agent_framework
from agent_framework import Workflow, WorkflowBuilder, Edge, Executor

# Import our adapters
from .executor import WorkflowNodeExecutor, NodeInput, NodeOutput
from .edge import WorkflowEdgeAdapter

# Import existing domain models
from src.domain.workflows.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    NodeType,
)


logger = logging.getLogger(__name__)


# =============================================================================
# WorkflowRunResult - Execution Result Model
# =============================================================================

class WorkflowRunResult:
    """
    Result of a workflow execution.

    Attributes:
        success: Whether the workflow completed successfully
        result: The final output of the workflow
        execution_path: List of node IDs that were executed
        node_results: Results from each node execution
        error: Error message if workflow failed
        metadata: Additional execution metadata
    """

    def __init__(
        self,
        success: bool = True,
        result: Any = None,
        execution_path: Optional[List[str]] = None,
        node_results: Optional[Dict[str, NodeOutput]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.result = result
        self.execution_path = execution_path or []
        self.node_results = node_results or {}
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "result": self.result,
            "execution_path": self.execution_path,
            "node_results": {
                k: v.dict() if hasattr(v, "dict") else v
                for k, v in self.node_results.items()
            },
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self) -> str:
        status = "✅" if self.success else "❌"
        return f"WorkflowRunResult({status}, path={self.execution_path})"


# =============================================================================
# WorkflowDefinitionAdapter - Main Adapter
# =============================================================================

class WorkflowDefinitionAdapter:
    """
    Adapter to convert WorkflowDefinition to official Agent Framework Workflow.

    This class bridges the existing IPA WorkflowDefinition model to the official
    Workflow interface from Microsoft Agent Framework.

    Example:
        >>> from src.domain.workflows.models import WorkflowDefinition
        >>> definition = WorkflowDefinition(nodes=[...], edges=[...])
        >>> adapter = WorkflowDefinitionAdapter(
        ...     definition=definition,
        ...     agent_service=agent_svc,
        ... )
        >>> workflow = adapter.build()
        >>> result = await adapter.run({"query": "Help me"})

    IMPORTANT: Uses official Workflow from agent_framework.workflows
    """

    def __init__(
        self,
        definition: WorkflowDefinition,
        agent_service: Optional[Any] = None,
        checkpoint_store: Optional[Any] = None,
        function_registry: Optional[Dict[str, Callable]] = None,
    ):
        """
        Initialize the workflow definition adapter.

        Args:
            definition: The WorkflowDefinition to adapt
            agent_service: Service for executing AI agents (required for AGENT nodes)
            checkpoint_store: Optional checkpoint storage for persistence
            function_registry: Registry of functions for gateway/function nodes
        """
        self._definition = definition
        self._agent_service = agent_service
        self._checkpoint_store = checkpoint_store
        self._function_registry = function_registry or {}

        # Built components
        self._executors: List[WorkflowNodeExecutor] = []
        self._edges: List[Edge] = []
        self._executor_map: Dict[str, WorkflowNodeExecutor] = {}
        self._workflow: Optional[Workflow] = None

        # Validate definition
        errors = definition.validate()
        if errors:
            logger.warning(f"Workflow definition has validation errors: {errors}")

    @property
    def definition(self) -> WorkflowDefinition:
        """Get the underlying WorkflowDefinition."""
        return self._definition

    @property
    def is_built(self) -> bool:
        """Check if workflow has been built."""
        return self._workflow is not None

    @property
    def executors(self) -> List[WorkflowNodeExecutor]:
        """Get the list of executors."""
        return self._executors

    @property
    def edges(self) -> List[Edge]:
        """Get the list of edges."""
        return self._edges

    def build(self) -> Workflow:
        """
        Build the official Workflow from the definition using WorkflowBuilder.

        Converts all nodes to executors, registers them with WorkflowBuilder,
        and adds edges between them.

        Returns:
            Official Workflow instance

        Raises:
            ValueError: If definition is invalid or missing required components
        """
        if self._workflow is not None:
            return self._workflow

        logger.debug(f"Building workflow with {len(self._definition.nodes)} nodes")

        # 1. Create WorkflowBuilder
        builder = WorkflowBuilder()

        # 2. Create executors for all nodes
        self._executors = []
        self._executor_map = {}

        for node in self._definition.nodes:
            executor = WorkflowNodeExecutor(
                node=node,
                agent_service=self._agent_service,
                function_registry=self._function_registry,
            )
            self._executors.append(executor)
            self._executor_map[node.id] = executor

        # 3. Add edges between executors using executor objects directly
        # Note: The installed agent_framework version uses add_edge with
        # Executor objects, not registered names
        for edge in self._definition.edges:
            source_executor = self._executor_map.get(edge.source)
            target_executor = self._executor_map.get(edge.target)

            if source_executor is None:
                raise ValueError(f"Source node '{edge.source}' not found")
            if target_executor is None:
                raise ValueError(f"Target node '{edge.target}' not found")

            if edge.condition:
                # Create condition evaluator for conditional edges
                evaluator = WorkflowEdgeAdapter(edge)
                builder.add_edge(
                    source_executor,
                    target_executor,
                    condition=evaluator.evaluate_condition,
                )
            else:
                builder.add_edge(source_executor, target_executor)

        # 4. Set start executor
        start_node = self._definition.get_start_node()
        if start_node:
            start_executor = self._executor_map.get(start_node.id)
            if start_executor:
                builder.set_start_executor(start_executor)
            else:
                raise ValueError(f"Start node '{start_node.id}' not found in executor map")
        elif self._definition.nodes:
            # Fallback to first node if no explicit start
            first_executor = self._executors[0]
            builder.set_start_executor(first_executor)
        else:
            raise ValueError("Workflow must have at least one node")

        # 5. Configure checkpointing if storage provided
        if self._checkpoint_store:
            builder.with_checkpointing(self._checkpoint_store)

        # 6. Build the official Workflow
        self._workflow = builder.build()

        logger.info(
            f"Built workflow with {len(self._executors)} executors, "
            f"{len(self._definition.edges)} edges"
        )

        return self._workflow

    async def run(
        self,
        input_data: Dict[str, Any],
        execution_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRunResult:
        """
        Execute the workflow.

        Args:
            input_data: Input data for the workflow
            execution_id: Optional execution identifier for tracking
            context: Optional additional context

        Returns:
            WorkflowRunResult with execution outcome
        """
        # Ensure workflow is built
        if self._workflow is None:
            self.build()

        start_time = datetime.utcnow()
        execution_path: List[str] = []
        node_results: Dict[str, NodeOutput] = {}

        try:
            # Prepare input
            node_input = NodeInput(
                data=input_data,
                execution_id=execution_id,
                context=context or {},
                metadata={
                    "workflow_nodes": len(self._definition.nodes),
                    "start_time": start_time.isoformat(),
                },
            )

            # Execute the workflow through official API
            result = await self._workflow.run(node_input)

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_ms = (end_time - start_time).total_seconds() * 1000

            return WorkflowRunResult(
                success=True,
                result=result,
                execution_path=execution_path,
                node_results=node_results,
                metadata={
                    "execution_id": str(execution_id) if execution_id else None,
                    "execution_ms": execution_ms,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)

            end_time = datetime.utcnow()
            execution_ms = (end_time - start_time).total_seconds() * 1000

            return WorkflowRunResult(
                success=False,
                result=None,
                execution_path=execution_path,
                node_results=node_results,
                error=str(e),
                metadata={
                    "execution_id": str(execution_id) if execution_id else None,
                    "execution_ms": execution_ms,
                    "error_type": type(e).__name__,
                },
            )

    async def run_stream(
        self,
        input_data: Dict[str, Any],
        execution_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute the workflow with streaming results.

        Yields node execution results as they complete.

        Args:
            input_data: Input data for the workflow
            execution_id: Optional execution identifier
            context: Optional additional context

        Yields:
            Dict with node_id, result, and status for each node execution
        """
        # Ensure workflow is built
        if self._workflow is None:
            self.build()

        try:
            # Prepare input
            node_input = NodeInput(
                data=input_data,
                execution_id=execution_id,
                context=context or {},
            )

            # Execute with streaming if available
            if hasattr(self._workflow, "run_stream"):
                async for event in self._workflow.run_stream(node_input):
                    yield {
                        "type": "node_event",
                        "data": event,
                    }
            else:
                # Fallback to regular run
                result = await self._workflow.run(node_input)
                yield {
                    "type": "final_result",
                    "data": result,
                }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def get_executor(self, node_id: str) -> Optional[WorkflowNodeExecutor]:
        """
        Get an executor by node ID.

        Args:
            node_id: The node ID to look up

        Returns:
            WorkflowNodeExecutor or None if not found
        """
        if not self._executor_map:
            self.build()
        return self._executor_map.get(node_id)

    def get_node_ids(self) -> List[str]:
        """Get all node IDs in the workflow."""
        return [node.id for node in self._definition.nodes]

    def get_start_node_id(self) -> Optional[str]:
        """Get the start node ID."""
        start_node = self._definition.get_start_node()
        return start_node.id if start_node else None

    def get_end_node_ids(self) -> List[str]:
        """Get all end node IDs."""
        return [node.id for node in self._definition.get_end_nodes()]

    def __repr__(self) -> str:
        """String representation."""
        built = "built" if self.is_built else "not built"
        return (
            f"WorkflowDefinitionAdapter("
            f"nodes={len(self._definition.nodes)}, "
            f"edges={len(self._definition.edges)}, "
            f"{built})"
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_workflow_adapter(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    variables: Optional[Dict[str, Any]] = None,
    agent_service: Optional[Any] = None,
    checkpoint_store: Optional[Any] = None,
) -> WorkflowDefinitionAdapter:
    """
    Factory function to create a WorkflowDefinitionAdapter from raw data.

    Args:
        nodes: List of node dictionaries
        edges: List of edge dictionaries
        variables: Optional workflow variables
        agent_service: Service for executing agents
        checkpoint_store: Optional checkpoint storage

    Returns:
        WorkflowDefinitionAdapter instance
    """
    definition = WorkflowDefinition(
        nodes=nodes,
        edges=edges,
        variables=variables or {},
    )

    return WorkflowDefinitionAdapter(
        definition=definition,
        agent_service=agent_service,
        checkpoint_store=checkpoint_store,
    )


def build_simple_workflow(
    start_executor: WorkflowNodeExecutor,
    end_executor: WorkflowNodeExecutor,
    middle_executors: Optional[List[WorkflowNodeExecutor]] = None,
    checkpoint_store: Optional[Any] = None,
) -> Workflow:
    """
    Build a simple linear workflow.

    Creates a workflow: start -> [middle1 -> middle2 -> ...] -> end

    Args:
        start_executor: The start node executor
        end_executor: The end node executor
        middle_executors: Optional list of executors between start and end
        checkpoint_store: Optional checkpoint storage

    Returns:
        Official Workflow instance
    """
    builder = WorkflowBuilder()

    # Build the chain of executors
    all_executors = [start_executor]
    if middle_executors:
        all_executors.extend(middle_executors)
    all_executors.append(end_executor)

    # Use add_chain for linear workflows (requires 2+ executors)
    if len(all_executors) >= 2:
        builder.add_chain(all_executors)

    # Set start executor
    builder.set_start_executor(start_executor)

    # Configure checkpointing if storage provided
    if checkpoint_store:
        builder.with_checkpointing(checkpoint_store)

    return builder.build()


def build_branching_workflow(
    gateway_executor: WorkflowNodeExecutor,
    branch_executors: List[WorkflowNodeExecutor],
    branch_conditions: List[str],
    merge_executor: WorkflowNodeExecutor,
    checkpoint_store: Optional[Any] = None,
) -> Workflow:
    """
    Build a branching workflow with gateway.

    Creates a workflow: gateway -> [branch1 | branch2 | ...] -> merge

    Args:
        gateway_executor: The gateway node that determines routing
        branch_executors: List of branch executors
        branch_conditions: Conditions for each branch (same length as branch_executors)
        merge_executor: The merge/end node
        checkpoint_store: Optional checkpoint storage

    Returns:
        Official Workflow instance
    """
    if len(branch_executors) != len(branch_conditions):
        raise ValueError("branch_executors and branch_conditions must have same length")

    builder = WorkflowBuilder()

    # Connect gateway to each branch with conditions
    for executor, condition in zip(branch_executors, branch_conditions):
        workflow_edge = WorkflowEdge(
            source=gateway_executor.id,
            target=executor.id,
            condition=condition,
        )
        adapter = WorkflowEdgeAdapter(workflow_edge)
        builder.add_edge(
            gateway_executor,
            executor,
            condition=adapter.evaluate_condition,
        )

    # Connect each branch to merge
    for executor in branch_executors:
        builder.add_edge(executor, merge_executor)

    # Set start executor (gateway)
    builder.set_start_executor(gateway_executor)

    # Configure checkpointing if storage provided
    if checkpoint_store:
        builder.with_checkpointing(checkpoint_store)

    return builder.build()
