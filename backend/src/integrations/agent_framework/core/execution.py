# =============================================================================
# IPA Platform - Sequential Orchestration Adapter
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 27, Story S27-1: SequentialOrchestrationAdapter (10 pts)
#
# This module provides adapters for sequential workflow execution using
# the official Microsoft Agent Framework SequentialOrchestration API.
#
# Official API Pattern (from workflows-api.md):
#   from agent_framework.workflows.orchestrations import SequentialOrchestration
#   orchestration = SequentialOrchestration(agents=[...], name="...")
#   result = await orchestration.run(input_data)
#
# Key Features:
#   - SequentialOrchestrationAdapter: Wraps WorkflowNodeExecutors for sequential execution
#   - ExecutorAgentWrapper: Adapts Executor to ChatAgent interface
#   - ExecutionAdapter: High-level execution interface with event handling
#
# IMPORTANT: Uses official Agent Framework API
#   from agent_framework.workflows.orchestrations import SequentialOrchestration
# =============================================================================

from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
import asyncio
import logging

# Official Agent Framework Imports - MUST use these
# Note: Classes are directly under agent_framework, not agent_framework.workflows
# SequentialOrchestration was renamed to SequentialBuilder in the official API
from agent_framework import ChatAgent, SequentialBuilder, Workflow

# Alias for backward compatibility
SequentialOrchestration = SequentialBuilder

# Import Sprint 26 adapters
from .executor import WorkflowNodeExecutor, NodeInput, NodeOutput
from .workflow import WorkflowDefinitionAdapter, WorkflowRunResult
from .context import WorkflowContextAdapter, create_context


logger = logging.getLogger(__name__)


# =============================================================================
# ExecutorAgentWrapper - Adapt Executor to ChatAgent
# =============================================================================

class ExecutorAgentWrapper(ChatAgent):
    """
    Wrapper that adapts a WorkflowNodeExecutor to the ChatAgent interface.

    This allows Executors to be used with SequentialOrchestration which
    expects ChatAgent instances.

    Example:
        >>> executor = WorkflowNodeExecutor(node=my_node, agent_service=svc)
        >>> agent = ExecutorAgentWrapper(executor=executor)
        >>> result = await agent.run("process this")

    IMPORTANT: Implements ChatAgent interface for official API compatibility
    """

    def __init__(
        self,
        executor: WorkflowNodeExecutor,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
    ):
        """
        Initialize the executor agent wrapper.

        Args:
            executor: The WorkflowNodeExecutor to wrap
            name: Optional name override (defaults to executor.id)
            instructions: Optional instructions for the agent
        """
        self._executor = executor
        self._name = name or executor.id
        self._instructions = instructions or f"Execute node: {executor.node.name}"
        self._context = create_context()

    @property
    def name(self) -> str:
        """Get the agent name."""
        return self._name

    @property
    def instructions(self) -> str:
        """Get the agent instructions."""
        return self._instructions

    @property
    def executor(self) -> WorkflowNodeExecutor:
        """Get the wrapped executor."""
        return self._executor

    async def run(self, input_data: Any) -> Any:
        """
        Execute the wrapped executor.

        Args:
            input_data: Input data (string or dict)

        Returns:
            Execution result
        """
        # Convert input to NodeInput format
        if isinstance(input_data, dict):
            node_input = NodeInput(data=input_data)
        elif isinstance(input_data, str):
            node_input = NodeInput(data={"input": input_data, "message": input_data})
        elif isinstance(input_data, NodeInput):
            node_input = input_data
        else:
            node_input = NodeInput(data={"input": str(input_data)})

        # Execute through the wrapped executor
        result = await self._executor.execute(node_input, self._context)

        # Return result based on success
        if result.success:
            return result.result
        else:
            raise ExecutionError(
                f"Executor '{self._name}' failed: {result.error}",
                node_id=self._executor.id,
                error_details=result.metadata,
            )

    async def run_streaming(self, input_data: Any) -> AsyncIterator[Any]:
        """
        Execute with streaming output.

        For non-streaming executors, yields the final result once.

        Args:
            input_data: Input data

        Yields:
            Execution events/results
        """
        # Most executors don't support true streaming
        # Yield progress event then final result
        yield {
            "type": "started",
            "node_id": self._executor.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = await self.run(input_data)

        yield {
            "type": "completed",
            "node_id": self._executor.id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }


# =============================================================================
# ExecutionError - Custom Exception
# =============================================================================

class ExecutionError(Exception):
    """
    Custom exception for execution failures.

    Attributes:
        message: Error message
        node_id: ID of the node that failed
        error_details: Additional error details
    """

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.node_id = node_id
        self.error_details = error_details or {}


# =============================================================================
# SequentialOrchestrationAdapter - Main Adapter
# =============================================================================

class SequentialOrchestrationAdapter:
    """
    Sequential orchestration adapter using official SequentialOrchestration.

    Wraps multiple WorkflowNodeExecutors for sequential execution using
    the official Agent Framework SequentialOrchestration API.

    Example:
        >>> executors = [executor1, executor2, executor3]
        >>> adapter = SequentialOrchestrationAdapter(
        ...     executors=executors,
        ...     name="my-workflow"
        ... )
        >>> result = await adapter.run({"query": "process this"})

    IMPORTANT: Uses official SequentialOrchestration from
        agent_framework.workflows.orchestrations
    """

    def __init__(
        self,
        executors: List[WorkflowNodeExecutor],
        name: str = "sequential-workflow",
        on_step_complete: Optional[Callable] = None,
    ):
        """
        Initialize the sequential orchestration adapter.

        Args:
            executors: List of WorkflowNodeExecutors (in execution order)
            name: Name for the orchestration
            on_step_complete: Optional callback for step completion
        """
        self._executors = executors
        self._name = name
        self._on_step_complete = on_step_complete

        # Create agent wrappers for each executor
        self._agents = [
            ExecutorAgentWrapper(executor=exe, name=exe.id)
            for exe in executors
        ]

        # Build the official SequentialOrchestration
        self._orchestration = self._build_orchestration()

        # Execution tracking
        self._execution_count = 0
        self._last_execution_time: Optional[datetime] = None

    def _build_orchestration(self) -> SequentialOrchestration:
        """
        Build the official SequentialOrchestration.

        Returns:
            SequentialOrchestration instance
        """
        return SequentialOrchestration(
            agents=self._agents,
            name=self._name,
        )

    @property
    def name(self) -> str:
        """Get the orchestration name."""
        return self._name

    @property
    def executor_count(self) -> int:
        """Get the number of executors."""
        return len(self._executors)

    @property
    def executor_ids(self) -> List[str]:
        """Get the list of executor IDs in order."""
        return [exe.id for exe in self._executors]

    @property
    def execution_count(self) -> int:
        """Get total execution count."""
        return self._execution_count

    async def run(self, input_data: Any) -> "SequentialExecutionResult":
        """
        Execute the sequential orchestration.

        Runs all executors in sequence, passing output from one to the next.

        Args:
            input_data: Initial input data

        Returns:
            SequentialExecutionResult with outcome
        """
        start_time = datetime.utcnow()
        execution_id = uuid4()
        step_results: List[Dict[str, Any]] = []

        try:
            # Execute through official orchestration
            result = await self._orchestration.run(input_data)

            # Track execution
            self._execution_count += 1
            self._last_execution_time = datetime.utcnow()

            end_time = datetime.utcnow()
            execution_ms = (end_time - start_time).total_seconds() * 1000

            return SequentialExecutionResult(
                execution_id=execution_id,
                success=True,
                result=result,
                executed_count=len(self._executors),
                step_results=step_results,
                execution_ms=execution_ms,
            )

        except Exception as e:
            logger.error(f"Sequential execution failed: {e}", exc_info=True)

            end_time = datetime.utcnow()
            execution_ms = (end_time - start_time).total_seconds() * 1000

            return SequentialExecutionResult(
                execution_id=execution_id,
                success=False,
                result=None,
                executed_count=len(step_results),
                step_results=step_results,
                error=str(e),
                error_node_id=getattr(e, 'node_id', None),
                execution_ms=execution_ms,
            )

    async def run_stream(self, input_data: Any) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute with streaming events.

        Yields events as each executor completes.

        Args:
            input_data: Initial input data

        Yields:
            Execution events (started, step_completed, completed, failed)
        """
        execution_id = uuid4()
        start_time = datetime.utcnow()

        yield {
            "event_type": "started",
            "execution_id": str(execution_id),
            "orchestration_name": self._name,
            "executor_count": len(self._executors),
            "timestamp": start_time.isoformat(),
        }

        try:
            # Execute each step manually for streaming
            current_input = input_data
            step_index = 0

            for agent in self._agents:
                step_start = datetime.utcnow()

                yield {
                    "event_type": "executor_started",
                    "execution_id": str(execution_id),
                    "executor_id": agent.name,
                    "step_index": step_index,
                    "timestamp": step_start.isoformat(),
                }

                # Execute this step
                step_result = await agent.run(current_input)

                step_end = datetime.utcnow()
                step_ms = (step_end - step_start).total_seconds() * 1000

                yield {
                    "event_type": "executor_completed",
                    "execution_id": str(execution_id),
                    "executor_id": agent.name,
                    "step_index": step_index,
                    "execution_ms": step_ms,
                    "timestamp": step_end.isoformat(),
                }

                # Notify callback if registered
                if self._on_step_complete:
                    await self._on_step_complete(agent.name, step_result)

                # Pass result to next step
                current_input = step_result
                step_index += 1

            # All steps completed
            end_time = datetime.utcnow()
            total_ms = (end_time - start_time).total_seconds() * 1000

            self._execution_count += 1
            self._last_execution_time = end_time

            yield {
                "event_type": "completed",
                "execution_id": str(execution_id),
                "success": True,
                "result": current_input,
                "executed_count": len(self._executors),
                "execution_ms": total_ms,
                "timestamp": end_time.isoformat(),
            }

        except Exception as e:
            logger.error(f"Streaming execution failed: {e}", exc_info=True)

            end_time = datetime.utcnow()
            total_ms = (end_time - start_time).total_seconds() * 1000

            yield {
                "event_type": "failed",
                "execution_id": str(execution_id),
                "success": False,
                "error": str(e),
                "error_node_id": getattr(e, 'node_id', None),
                "execution_ms": total_ms,
                "timestamp": end_time.isoformat(),
            }

    def get_executor(self, executor_id: str) -> Optional[WorkflowNodeExecutor]:
        """
        Get an executor by ID.

        Args:
            executor_id: The executor ID to find

        Returns:
            WorkflowNodeExecutor or None
        """
        for executor in self._executors:
            if executor.id == executor_id:
                return executor
        return None

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SequentialOrchestrationAdapter("
            f"name={self._name!r}, "
            f"executors={len(self._executors)}, "
            f"executions={self._execution_count})"
        )


# =============================================================================
# SequentialExecutionResult - Execution Result
# =============================================================================

@dataclass
class SequentialExecutionResult:
    """
    Result of a sequential orchestration execution.

    Attributes:
        execution_id: Unique execution identifier
        success: Whether execution completed successfully
        result: Final result (output of last executor)
        executed_count: Number of executors that ran
        step_results: Results from each step
        error: Error message if failed
        error_node_id: ID of node that failed
        execution_ms: Total execution time in milliseconds
    """
    execution_id: UUID
    success: bool
    result: Any
    executed_count: int
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    error_node_id: Optional[str] = None
    execution_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "success": self.success,
            "result": self.result,
            "executed_count": self.executed_count,
            "step_results": self.step_results,
            "error": self.error,
            "error_node_id": self.error_node_id,
            "execution_ms": self.execution_ms,
        }


# =============================================================================
# ExecutionAdapter - High-Level Execution Interface
# =============================================================================

class ExecutionAdapter:
    """
    High-level workflow execution adapter.

    Provides a unified interface for executing workflows with event handling
    and checkpoint support. Replaces the internal WorkflowExecutionService
    with official API-based execution.

    Example:
        >>> workflow_adapter = WorkflowDefinitionAdapter(definition, agent_service)
        >>> execution = ExecutionAdapter(workflow_adapter, checkpoint_store)
        >>> execution.add_event_handler(my_handler)
        >>> result = await execution.execute(execution_id, input_data)

    IMPORTANT: Uses official API for workflow execution
    """

    def __init__(
        self,
        workflow_adapter: WorkflowDefinitionAdapter,
        checkpoint_store: Optional[Any] = None,
    ):
        """
        Initialize the execution adapter.

        Args:
            workflow_adapter: The WorkflowDefinitionAdapter for the workflow
            checkpoint_store: Optional checkpoint storage for persistence
        """
        self._workflow_adapter = workflow_adapter
        self._checkpoint_store = checkpoint_store
        self._event_handlers: List[Callable] = []

        # Execution tracking
        self._active_executions: Dict[UUID, Dict[str, Any]] = {}

    def add_event_handler(self, handler: Callable) -> None:
        """
        Add an event handler.

        Handlers receive (execution_id, event) for each workflow event.

        Args:
            handler: Async callable that receives execution events
        """
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: Callable) -> None:
        """
        Remove an event handler.

        Args:
            handler: The handler to remove
        """
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    async def execute(
        self,
        execution_id: UUID,
        input_data: Dict[str, Any],
        checkpoint_id: Optional[str] = None,
    ) -> "ExecutionResult":
        """
        Execute the workflow.

        Args:
            execution_id: Unique execution identifier
            input_data: Input data for the workflow
            checkpoint_id: Optional checkpoint ID for resume

        Returns:
            ExecutionResult with execution outcome
        """
        start_time = datetime.utcnow()

        # Track active execution
        self._active_executions[execution_id] = {
            "status": "running",
            "start_time": start_time,
            "checkpoint_id": checkpoint_id,
        }

        try:
            # Build workflow if needed
            workflow = self._workflow_adapter.build()

            # Configure checkpoint store if provided
            if self._checkpoint_store and hasattr(workflow, 'with_checkpointing'):
                workflow = workflow.with_checkpointing(self._checkpoint_store)

            # Emit started event
            await self._emit_event(execution_id, {
                "event_type": "started",
                "timestamp": start_time.isoformat(),
            })

            # Execute with streaming for event handling
            final_result = None

            async for event in self._workflow_adapter.run_stream(
                input_data=input_data,
                execution_id=execution_id,
            ):
                # Emit each event to handlers
                await self._emit_event(execution_id, event)

                # Capture final result
                if event.get("type") == "final_result":
                    final_result = event.get("data")

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_ms = (end_time - start_time).total_seconds() * 1000

            # Update tracking
            self._active_executions[execution_id]["status"] = "completed"
            self._active_executions[execution_id]["end_time"] = end_time

            # Emit completed event
            await self._emit_event(execution_id, {
                "event_type": "completed",
                "success": True,
                "execution_ms": execution_ms,
                "timestamp": end_time.isoformat(),
            })

            return ExecutionResult(
                execution_id=execution_id,
                success=True,
                result=final_result,
                execution_ms=execution_ms,
            )

        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}", exc_info=True)

            end_time = datetime.utcnow()
            execution_ms = (end_time - start_time).total_seconds() * 1000

            # Update tracking
            self._active_executions[execution_id]["status"] = "failed"
            self._active_executions[execution_id]["error"] = str(e)

            # Emit failed event
            await self._emit_event(execution_id, {
                "event_type": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_ms": execution_ms,
                "timestamp": end_time.isoformat(),
            })

            return ExecutionResult(
                execution_id=execution_id,
                success=False,
                result=None,
                error=str(e),
                execution_ms=execution_ms,
            )

    async def _emit_event(self, execution_id: UUID, event: Dict[str, Any]) -> None:
        """
        Emit an event to all registered handlers.

        Args:
            execution_id: The execution ID
            event: The event to emit
        """
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(execution_id, event)
                else:
                    handler(execution_id, event)
            except Exception as e:
                logger.error(f"Event handler error: {e}", exc_info=True)

    def get_active_execution(self, execution_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get active execution status.

        Args:
            execution_id: The execution ID

        Returns:
            Execution status dict or None
        """
        return self._active_executions.get(execution_id)

    def get_all_active_executions(self) -> Dict[UUID, Dict[str, Any]]:
        """Get all active executions."""
        return dict(self._active_executions)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ExecutionAdapter("
            f"workflow={self._workflow_adapter!r}, "
            f"handlers={len(self._event_handlers)}, "
            f"active={len(self._active_executions)})"
        )


# =============================================================================
# ExecutionResult - Execution Outcome
# =============================================================================

@dataclass
class ExecutionResult:
    """
    Result of a workflow execution.

    Attributes:
        execution_id: Unique execution identifier
        success: Whether execution completed successfully
        result: Execution result data
        error: Error message if failed
        execution_ms: Execution time in milliseconds
    """
    execution_id: UUID
    success: bool
    result: Any
    error: Optional[str] = None
    execution_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_ms": self.execution_ms,
        }


# =============================================================================
# Factory Functions
# =============================================================================

def create_sequential_orchestration(
    executors: List[WorkflowNodeExecutor],
    name: str = "sequential-workflow",
    on_step_complete: Optional[Callable] = None,
) -> SequentialOrchestrationAdapter:
    """
    Factory function to create a SequentialOrchestrationAdapter.

    Args:
        executors: List of WorkflowNodeExecutors
        name: Orchestration name
        on_step_complete: Optional step completion callback

    Returns:
        SequentialOrchestrationAdapter instance
    """
    return SequentialOrchestrationAdapter(
        executors=executors,
        name=name,
        on_step_complete=on_step_complete,
    )


def create_execution_adapter(
    workflow_adapter: WorkflowDefinitionAdapter,
    checkpoint_store: Optional[Any] = None,
) -> ExecutionAdapter:
    """
    Factory function to create an ExecutionAdapter.

    Args:
        workflow_adapter: The WorkflowDefinitionAdapter
        checkpoint_store: Optional checkpoint storage

    Returns:
        ExecutionAdapter instance
    """
    return ExecutionAdapter(
        workflow_adapter=workflow_adapter,
        checkpoint_store=checkpoint_store,
    )


def wrap_executor_as_agent(
    executor: WorkflowNodeExecutor,
    name: Optional[str] = None,
) -> ExecutorAgentWrapper:
    """
    Factory function to wrap an executor as a ChatAgent.

    Args:
        executor: The WorkflowNodeExecutor to wrap
        name: Optional name override

    Returns:
        ExecutorAgentWrapper instance
    """
    return ExecutorAgentWrapper(
        executor=executor,
        name=name,
    )
