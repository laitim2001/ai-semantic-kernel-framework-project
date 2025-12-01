# =============================================================================
# IPA Platform - Workflow Execution Service
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Service for executing workflows with Agent Framework integration.
# Handles sequential agent orchestration and state management.
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.domain.agents.service import AgentConfig, AgentService, get_agent_service
from src.domain.workflows.models import (
    NodeType,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowNode,
)

logger = logging.getLogger(__name__)


class NodeExecutionResult:
    """Result of executing a single node."""

    def __init__(
        self,
        node_id: str,
        node_type: NodeType,
        output: Optional[str] = None,
        error: Optional[str] = None,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.output = output
        self.error = error
        self.llm_calls = llm_calls
        self.llm_tokens = llm_tokens
        self.llm_cost = llm_cost
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

    def complete(self):
        """Mark node execution as complete."""
        self.completed_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "type": self.node_type.value,
            "output": self.output,
            "error": self.error,
            "llm_calls": self.llm_calls,
            "llm_tokens": self.llm_tokens,
            "llm_cost": self.llm_cost,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class WorkflowExecutionResult:
    """Result of executing a complete workflow."""

    def __init__(
        self,
        execution_id: UUID,
        workflow_id: UUID,
        status: str = "pending",
    ):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.status = status
        self.result: Optional[str] = None
        self.node_results: List[NodeExecutionResult] = []
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

    @property
    def total_llm_calls(self) -> int:
        """Total LLM calls across all nodes."""
        return sum(nr.llm_calls for nr in self.node_results)

    @property
    def total_llm_tokens(self) -> int:
        """Total LLM tokens across all nodes."""
        return sum(nr.llm_tokens for nr in self.node_results)

    @property
    def total_llm_cost(self) -> float:
        """Total LLM cost across all nodes."""
        return sum(nr.llm_cost for nr in self.node_results)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Execution duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def complete(self, status: str = "completed"):
        """Mark workflow execution as complete."""
        self.status = status
        self.completed_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "workflow_id": str(self.workflow_id),
            "status": self.status,
            "result": self.result,
            "node_results": [nr.to_dict() for nr in self.node_results],
            "stats": {
                "total_llm_calls": self.total_llm_calls,
                "total_llm_tokens": self.total_llm_tokens,
                "total_llm_cost": self.total_llm_cost,
                "duration_seconds": self.duration_seconds,
            },
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class WorkflowExecutionService:
    """
    Service for executing workflows.

    Orchestrates sequential agent execution following workflow graph.
    Tracks execution state, LLM usage, and handles errors.

    Usage:
        service = WorkflowExecutionService()
        result = await service.execute_workflow(
            workflow_id=uuid4(),
            definition=workflow_def,
            input_data={"message": "Hello"},
        )
    """

    def __init__(self):
        """Initialize WorkflowExecutionService."""
        self._agent_service: Optional[AgentService] = None

    async def _get_agent_service(self) -> AgentService:
        """Get or initialize agent service."""
        if self._agent_service is None:
            self._agent_service = get_agent_service()
            if not self._agent_service.is_initialized:
                await self._agent_service.initialize()
        return self._agent_service

    async def execute_workflow(
        self,
        workflow_id: UUID,
        definition: WorkflowDefinition,
        input_data: Dict[str, Any],
        variables: Optional[Dict[str, Any]] = None,
        agent_configs: Optional[Dict[UUID, AgentConfig]] = None,
    ) -> WorkflowExecutionResult:
        """
        Execute a workflow.

        Args:
            workflow_id: Workflow identifier
            definition: Workflow definition with nodes and edges
            input_data: Initial input data
            variables: Optional runtime variables
            agent_configs: Map of agent_id to AgentConfig for execution

        Returns:
            WorkflowExecutionResult with status and outputs
        """
        # Validate workflow
        errors = definition.validate()
        if errors:
            raise ValueError(f"Invalid workflow: {errors}")

        # Initialize execution
        execution_id = uuid4()
        result = WorkflowExecutionResult(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status="running",
        )

        # Create execution context
        context = WorkflowContext(
            execution_id=execution_id,
            workflow_id=workflow_id,
            variables=variables or {},
            input_data=input_data,
        )

        logger.info(f"Starting workflow execution: {execution_id}")

        try:
            # Get start node
            start_node = definition.get_start_node()
            if not start_node:
                raise ValueError("No start node found")

            # Execute workflow sequentially
            current_output = input_data.get("message", "")
            await self._execute_sequential(
                definition=definition,
                context=context,
                result=result,
                start_node=start_node,
                current_output=current_output,
                agent_configs=agent_configs or {},
            )

            # Mark complete
            result.complete("completed")
            logger.info(
                f"Workflow execution completed: {execution_id}, "
                f"tokens={result.total_llm_tokens}, cost=${result.total_llm_cost:.6f}"
            )

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            result.status = "failed"
            result.result = str(e)
            result.complete("failed")

        return result

    async def _execute_sequential(
        self,
        definition: WorkflowDefinition,
        context: WorkflowContext,
        result: WorkflowExecutionResult,
        start_node: WorkflowNode,
        current_output: str,
        agent_configs: Dict[UUID, AgentConfig],
    ) -> None:
        """
        Execute workflow nodes sequentially.

        Follows edges from start to end, executing each agent node.
        """
        current_node = start_node
        agent_service = await self._get_agent_service()

        while current_node:
            context.current_node = current_node.id

            # Execute node based on type
            if current_node.type == NodeType.START:
                # Start node - just pass through
                node_result = NodeExecutionResult(
                    node_id=current_node.id,
                    node_type=current_node.type,
                    output=current_output,
                )
                node_result.complete()
                result.node_results.append(node_result)
                context.add_history(current_node.id, "start", "Workflow started")

            elif current_node.type == NodeType.END:
                # End node - finalize
                node_result = NodeExecutionResult(
                    node_id=current_node.id,
                    node_type=current_node.type,
                    output=current_output,
                )
                node_result.complete()
                result.node_results.append(node_result)
                result.result = current_output
                context.add_history(current_node.id, "end", "Workflow completed")
                break  # Exit loop

            elif current_node.type == NodeType.AGENT:
                # Execute agent node
                node_result = await self._execute_agent_node(
                    node=current_node,
                    context=context,
                    input_message=current_output,
                    agent_configs=agent_configs,
                    agent_service=agent_service,
                )
                result.node_results.append(node_result)

                if node_result.error:
                    raise RuntimeError(
                        f"Agent node '{current_node.id}' failed: {node_result.error}"
                    )

                current_output = node_result.output or ""

            elif current_node.type == NodeType.GATEWAY:
                # Gateway node - evaluate conditions
                node_result = await self._execute_gateway_node(
                    node=current_node,
                    context=context,
                    definition=definition,
                )
                result.node_results.append(node_result)

            # Get next node
            outgoing_edges = definition.get_outgoing_edges(current_node.id)
            if outgoing_edges:
                # For sequential execution, take the first edge
                next_node_id = outgoing_edges[0].target
                current_node = definition.get_node(next_node_id)
            else:
                current_node = None

    async def _execute_agent_node(
        self,
        node: WorkflowNode,
        context: WorkflowContext,
        input_message: str,
        agent_configs: Dict[UUID, AgentConfig],
        agent_service: AgentService,
    ) -> NodeExecutionResult:
        """
        Execute an agent node.

        Args:
            node: The agent node to execute
            context: Execution context
            input_message: Input message for the agent
            agent_configs: Map of agent configurations
            agent_service: Agent service instance

        Returns:
            NodeExecutionResult with agent output
        """
        node_result = NodeExecutionResult(
            node_id=node.id,
            node_type=node.type,
        )

        try:
            # Get agent config
            if node.agent_id and node.agent_id in agent_configs:
                config = agent_configs[node.agent_id]
            else:
                # Create default config from node
                config = AgentConfig(
                    name=node.name or node.id,
                    instructions=node.config.get(
                        "instructions", "You are a helpful assistant."
                    ),
                    tools=[],
                    model_config=node.config.get("model_config", {}),
                )

            # Execute agent
            logger.debug(f"Executing agent node: {node.id}")
            agent_result = await agent_service.run_agent_with_config(
                config=config,
                message=input_message,
                context={"workflow_id": str(context.workflow_id)},
            )

            # Update node result
            node_result.output = agent_result.text
            node_result.llm_calls = agent_result.llm_calls
            node_result.llm_tokens = agent_result.llm_tokens
            node_result.llm_cost = agent_result.llm_cost

            context.add_history(
                node.id,
                "agent_executed",
                result=agent_result.text[:100] if agent_result.text else None,
            )

        except Exception as e:
            logger.error(f"Agent node {node.id} execution failed: {e}")
            node_result.error = str(e)
            context.add_history(node.id, "agent_failed", error=str(e))

        node_result.complete()
        return node_result

    async def _execute_gateway_node(
        self,
        node: WorkflowNode,
        context: WorkflowContext,
        definition: WorkflowDefinition,
    ) -> NodeExecutionResult:
        """
        Execute a gateway node.

        Evaluates conditions on outgoing edges to determine path.

        Args:
            node: The gateway node
            context: Execution context
            definition: Workflow definition

        Returns:
            NodeExecutionResult (gateways don't produce output)
        """
        node_result = NodeExecutionResult(
            node_id=node.id,
            node_type=node.type,
            output=f"Gateway evaluated: {node.config.get('gateway_type', 'exclusive')}",
        )
        node_result.complete()

        context.add_history(node.id, "gateway_evaluated")
        return node_result

    async def validate_workflow(
        self,
        definition: WorkflowDefinition,
    ) -> Dict[str, Any]:
        """
        Validate a workflow definition.

        Args:
            definition: Workflow definition to validate

        Returns:
            Validation result with errors and warnings
        """
        errors = definition.validate()
        warnings = []

        # Additional validation warnings
        agent_nodes = [n for n in definition.nodes if n.type == NodeType.AGENT]
        for node in agent_nodes:
            if not node.agent_id:
                warnings.append(
                    f"Agent node '{node.id}' has no agent_id - will use default config"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# Global service instance
_workflow_execution_service: Optional[WorkflowExecutionService] = None


def get_workflow_execution_service() -> WorkflowExecutionService:
    """Get or create the global WorkflowExecutionService instance."""
    global _workflow_execution_service
    if _workflow_execution_service is None:
        _workflow_execution_service = WorkflowExecutionService()
    return _workflow_execution_service
