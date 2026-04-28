# =============================================================================
# IPA Platform - WorkflowExecutor Migration Layer
# =============================================================================
# Sprint 18: S18-2 NestedWorkflowManager 遷移 (8 points)
#
# This module provides migration layer for transitioning from Phase 2
# NestedWorkflowManager to Agent Framework WorkflowExecutor.
#
# Migration Strategy:
#   - Parallel Architecture: Keep existing NestedWorkflowManager + add adapter
#   - Provides conversion functions between legacy and new formats
#   - Preserves backward compatibility for existing workflows
#
# Key Components:
#   - Legacy data class replicas for type conversion
#   - Conversion functions for bidirectional mapping
#   - NestedWorkflowManagerAdapter bridging the two systems
#   - Factory functions for easy migration
#
# Agent Framework Reference:
#   - WorkflowExecutor wraps workflows as executors
#   - SubWorkflowRequestMessage/SubWorkflowResponseMessage for communication
#   - ExecutionContext for per-execution state isolation
#
# Author: IPA Platform Team
# Sprint: 18 - WorkflowExecutor 和整合
# Created: 2025-12-05
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
from uuid import UUID, uuid4
import asyncio
import logging

from .workflow_executor import (
    WorkflowExecutorAdapter,
    WorkflowExecutorStatus,
    WorkflowRunState,
    RequestInfoEvent,
    SubWorkflowRequestMessage,
    SubWorkflowResponseMessage,
    ExecutionContext,
    WorkflowOutput,
    WorkflowRunResult,
    WorkflowExecutorResult,
    WorkflowProtocol,
    SimpleWorkflow,
    create_workflow_executor,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Legacy Enums (Phase 2 Compatibility)
# =============================================================================


class NestedWorkflowTypeLegacy(str, Enum):
    """
    Legacy nested workflow type enum.

    Phase 2 types mapped to new WorkflowExecutor patterns.
    """
    INLINE = "inline"
    REFERENCE = "reference"
    DYNAMIC = "dynamic"
    RECURSIVE = "recursive"


class WorkflowScopeLegacy(str, Enum):
    """
    Legacy workflow scope enum.

    Phase 2 scopes for context sharing behavior.
    """
    ISOLATED = "isolated"
    INHERITED = "inherited"
    SHARED = "shared"


class NestedExecutionStatusLegacy(str, Enum):
    """
    Legacy nested execution status enum.

    Phase 2 statuses mapped to new WorkflowExecutorStatus.
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


# =============================================================================
# Legacy Data Classes (Phase 2 Compatibility)
# =============================================================================


@dataclass
class NestedWorkflowConfigLegacy:
    """
    Legacy nested workflow configuration.

    Phase 2 configuration structure for nested workflow behavior.
    """
    workflow_type: NestedWorkflowTypeLegacy = NestedWorkflowTypeLegacy.REFERENCE
    scope: WorkflowScopeLegacy = WorkflowScopeLegacy.INHERITED
    max_depth: int = 5
    timeout_seconds: int = 600
    retry_on_failure: bool = True
    max_retries: int = 2
    pass_context: bool = True
    return_outputs: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_type": self.workflow_type.value,
            "scope": self.scope.value,
            "max_depth": self.max_depth,
            "timeout_seconds": self.timeout_seconds,
            "retry_on_failure": self.retry_on_failure,
            "max_retries": self.max_retries,
            "pass_context": self.pass_context,
            "return_outputs": self.return_outputs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NestedWorkflowConfigLegacy":
        """Create from dictionary."""
        return cls(
            workflow_type=NestedWorkflowTypeLegacy(data.get("workflow_type", "reference")),
            scope=WorkflowScopeLegacy(data.get("scope", "inherited")),
            max_depth=data.get("max_depth", 5),
            timeout_seconds=data.get("timeout_seconds", 600),
            retry_on_failure=data.get("retry_on_failure", True),
            max_retries=data.get("max_retries", 2),
            pass_context=data.get("pass_context", True),
            return_outputs=data.get("return_outputs", True),
        )


@dataclass
class SubWorkflowReferenceLegacy:
    """
    Legacy sub-workflow reference.

    Phase 2 structure for referencing sub-workflows.
    """
    id: UUID
    parent_workflow_id: UUID
    workflow_id: Optional[UUID]  # For REFERENCE type
    definition: Optional[Dict[str, Any]]  # For INLINE/DYNAMIC type
    config: NestedWorkflowConfigLegacy
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    position: int = 0
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "parent_workflow_id": str(self.parent_workflow_id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "definition": self.definition,
            "config": self.config.to_dict(),
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "position": self.position,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class NestedExecutionContextLegacy:
    """
    Legacy nested execution context.

    Phase 2 structure for execution context.
    """
    execution_id: UUID
    parent_execution_id: Optional[UUID]
    workflow_id: UUID
    depth: int
    path: List[UUID]
    variables: Dict[str, Any]
    parent_variables: Optional[Dict[str, Any]] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "parent_execution_id": str(self.parent_execution_id) if self.parent_execution_id else None,
            "workflow_id": str(self.workflow_id),
            "depth": self.depth,
            "path": [str(p) for p in self.path],
            "variables": self.variables,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class NestedWorkflowResultLegacy:
    """
    Legacy nested workflow execution result.

    Phase 2 structure for execution results.
    """
    execution_id: UUID
    workflow_id: UUID
    status: NestedExecutionStatusLegacy
    outputs: Dict[str, Any] = field(default_factory=dict)
    execution_tree: Optional[Dict[str, Any]] = None
    depth: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "workflow_id": str(self.workflow_id),
            "status": self.status.value,
            "outputs": self.outputs,
            "execution_tree": self.execution_tree,
            "depth": self.depth,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "metadata": self.metadata,
        }


# =============================================================================
# Status Conversion Functions
# =============================================================================


def convert_legacy_status_to_executor(
    status: Union[str, NestedExecutionStatusLegacy]
) -> WorkflowExecutorStatus:
    """
    Convert legacy nested execution status to WorkflowExecutorStatus.

    Args:
        status: Legacy status string or enum

    Returns:
        Corresponding WorkflowExecutorStatus

    Mapping:
        pending -> IDLE
        running -> RUNNING
        completed -> COMPLETED
        failed -> FAILED
        timeout -> FAILED
        cancelled -> CANCELLED
    """
    if isinstance(status, NestedExecutionStatusLegacy):
        status = status.value

    mapping = {
        "pending": WorkflowExecutorStatus.IDLE,
        "running": WorkflowExecutorStatus.RUNNING,
        "completed": WorkflowExecutorStatus.COMPLETED,
        "failed": WorkflowExecutorStatus.FAILED,
        "timeout": WorkflowExecutorStatus.FAILED,
        "cancelled": WorkflowExecutorStatus.CANCELLED,
    }

    return mapping.get(status, WorkflowExecutorStatus.IDLE)


def convert_executor_status_to_legacy(
    status: WorkflowExecutorStatus
) -> NestedExecutionStatusLegacy:
    """
    Convert WorkflowExecutorStatus to legacy nested execution status.

    Args:
        status: WorkflowExecutorStatus

    Returns:
        Corresponding NestedExecutionStatusLegacy

    Mapping:
        IDLE -> pending
        RUNNING -> running
        WAITING_RESPONSE -> running
        COMPLETED -> completed
        FAILED -> failed
        CANCELLED -> cancelled
    """
    mapping = {
        WorkflowExecutorStatus.IDLE: NestedExecutionStatusLegacy.PENDING,
        WorkflowExecutorStatus.RUNNING: NestedExecutionStatusLegacy.RUNNING,
        WorkflowExecutorStatus.WAITING_RESPONSE: NestedExecutionStatusLegacy.RUNNING,
        WorkflowExecutorStatus.COMPLETED: NestedExecutionStatusLegacy.COMPLETED,
        WorkflowExecutorStatus.FAILED: NestedExecutionStatusLegacy.FAILED,
        WorkflowExecutorStatus.CANCELLED: NestedExecutionStatusLegacy.CANCELLED,
    }

    return mapping.get(status, NestedExecutionStatusLegacy.PENDING)


# =============================================================================
# Context Conversion Functions
# =============================================================================


def convert_legacy_context_to_execution(
    legacy_context: NestedExecutionContextLegacy
) -> ExecutionContext:
    """
    Convert legacy NestedExecutionContext to new ExecutionContext.

    Args:
        legacy_context: Phase 2 nested execution context

    Returns:
        Agent Framework compatible ExecutionContext
    """
    return ExecutionContext(
        execution_id=str(legacy_context.execution_id),
        collected_responses=legacy_context.result or {},
        expected_response_count=0,
        pending_requests={},
        started_at=legacy_context.started_at.timestamp(),
        metadata={
            "parent_execution_id": str(legacy_context.parent_execution_id) if legacy_context.parent_execution_id else None,
            "workflow_id": str(legacy_context.workflow_id),
            "depth": legacy_context.depth,
            "path": [str(p) for p in legacy_context.path],
            "variables": legacy_context.variables,
            "legacy_status": legacy_context.status,
        },
    )


def convert_execution_to_legacy_context(
    execution_context: ExecutionContext,
    workflow_id: UUID,
    depth: int = 0,
    path: Optional[List[UUID]] = None,
) -> NestedExecutionContextLegacy:
    """
    Convert ExecutionContext to legacy NestedExecutionContext.

    Args:
        execution_context: Agent Framework execution context
        workflow_id: Workflow ID
        depth: Nesting depth
        path: Execution path

    Returns:
        Legacy NestedExecutionContext
    """
    metadata = execution_context.metadata
    parent_id_str = metadata.get("parent_execution_id")

    return NestedExecutionContextLegacy(
        execution_id=UUID(execution_context.execution_id),
        parent_execution_id=UUID(parent_id_str) if parent_id_str else None,
        workflow_id=workflow_id,
        depth=metadata.get("depth", depth),
        path=path or [UUID(p) for p in metadata.get("path", [])],
        variables=metadata.get("variables", {}),
        started_at=datetime.fromtimestamp(execution_context.started_at),
        status=metadata.get("legacy_status", "running"),
        result=execution_context.collected_responses or None,
    )


# =============================================================================
# Config Conversion Functions
# =============================================================================


def convert_legacy_config_to_executor_config(
    legacy_config: NestedWorkflowConfigLegacy
) -> Dict[str, Any]:
    """
    Convert legacy config to WorkflowExecutorAdapter config.

    Args:
        legacy_config: Phase 2 nested workflow config

    Returns:
        Config dictionary for WorkflowExecutorAdapter
    """
    return {
        "max_depth": legacy_config.max_depth,
        "timeout_seconds": legacy_config.timeout_seconds,
        "retry_on_failure": legacy_config.retry_on_failure,
        "max_retries": legacy_config.max_retries,
        "pass_context": legacy_config.pass_context,
        "return_outputs": legacy_config.return_outputs,
        "legacy_type": legacy_config.workflow_type.value,
        "legacy_scope": legacy_config.scope.value,
    }


def convert_executor_config_to_legacy(
    config: Dict[str, Any]
) -> NestedWorkflowConfigLegacy:
    """
    Convert WorkflowExecutorAdapter config to legacy config.

    Args:
        config: WorkflowExecutorAdapter config dictionary

    Returns:
        Legacy NestedWorkflowConfigLegacy
    """
    return NestedWorkflowConfigLegacy(
        workflow_type=NestedWorkflowTypeLegacy(config.get("legacy_type", "reference")),
        scope=WorkflowScopeLegacy(config.get("legacy_scope", "inherited")),
        max_depth=config.get("max_depth", 5),
        timeout_seconds=config.get("timeout_seconds", 600),
        retry_on_failure=config.get("retry_on_failure", True),
        max_retries=config.get("max_retries", 2),
        pass_context=config.get("pass_context", True),
        return_outputs=config.get("return_outputs", True),
    )


# =============================================================================
# Result Conversion Functions
# =============================================================================


def convert_executor_result_to_legacy(
    result: WorkflowExecutorResult,
    workflow_id: UUID,
    depth: int = 0,
) -> NestedWorkflowResultLegacy:
    """
    Convert WorkflowExecutorResult to legacy result format.

    Args:
        result: Agent Framework executor result
        workflow_id: Workflow ID
        depth: Nesting depth

    Returns:
        Legacy NestedWorkflowResultLegacy
    """
    legacy_status = convert_executor_status_to_legacy(result.status)

    outputs = {}
    for i, output in enumerate(result.outputs):
        outputs[f"output_{i}"] = output

    return NestedWorkflowResultLegacy(
        execution_id=UUID(result.execution_id) if result.execution_id else uuid4(),
        workflow_id=workflow_id,
        status=legacy_status,
        outputs=outputs,
        depth=depth,
        duration_seconds=result.duration_seconds,
        error=result.error,
        metadata=result.metadata,
    )


def convert_legacy_result_to_executor(
    legacy_result: NestedWorkflowResultLegacy
) -> WorkflowExecutorResult:
    """
    Convert legacy result to WorkflowExecutorResult.

    Args:
        legacy_result: Phase 2 nested workflow result

    Returns:
        Agent Framework WorkflowExecutorResult
    """
    status = convert_legacy_status_to_executor(legacy_result.status)

    outputs = list(legacy_result.outputs.values())

    return WorkflowExecutorResult(
        status=status,
        outputs=outputs,
        pending_requests=[],
        execution_id=str(legacy_result.execution_id),
        workflow_id=str(legacy_result.workflow_id),
        duration_seconds=legacy_result.duration_seconds,
        error=legacy_result.error,
        metadata=legacy_result.metadata,
    )


# =============================================================================
# Reference Conversion Functions
# =============================================================================


def convert_sub_workflow_reference_to_executor(
    reference: SubWorkflowReferenceLegacy,
    executor_fn: Optional[Callable] = None,
) -> WorkflowExecutorAdapter:
    """
    Convert legacy SubWorkflowReference to WorkflowExecutorAdapter.

    Args:
        reference: Phase 2 sub-workflow reference
        executor_fn: Optional async function for workflow logic

    Returns:
        Configured WorkflowExecutorAdapter
    """
    # Create executor config
    config = convert_legacy_config_to_executor_config(reference.config)
    config["input_mapping"] = reference.input_mapping
    config["output_mapping"] = reference.output_mapping
    config["position"] = reference.position

    # Create workflow if executor_fn provided
    workflow = None
    if executor_fn:
        workflow = SimpleWorkflow(
            id=str(reference.workflow_id or reference.id),
            executor_fn=executor_fn,
        )

    # Create adapter
    adapter = WorkflowExecutorAdapter(
        id=str(reference.id),
        workflow=workflow,
        config=config,
    )

    return adapter


# =============================================================================
# NestedWorkflowManagerAdapter
# =============================================================================


class NestedWorkflowManagerAdapter:
    """
    Adapter bridging Phase 2 NestedWorkflowManager to WorkflowExecutor.

    Provides backward-compatible API while using new Agent Framework
    WorkflowExecutor internally.

    Usage Example:
        ```python
        # Create adapter
        adapter = NestedWorkflowManagerAdapter(
            manager_id="nested-manager",
            max_global_depth=10,
        )

        # Register sub-workflow (legacy API)
        sub_ref = SubWorkflowReferenceLegacy(...)
        await adapter.register_sub_workflow(parent_id, sub_ref)

        # Execute (uses new executor internally)
        result = await adapter.execute_sub_workflow(parent_context, sub_ref)
        ```
    """

    def __init__(
        self,
        manager_id: str,
        max_global_depth: int = 10,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize NestedWorkflowManagerAdapter.

        Args:
            manager_id: Unique identifier for this manager
            max_global_depth: Maximum global nesting depth
            config: Additional configuration
        """
        self._id = manager_id
        self._max_global_depth = max_global_depth
        self._config = config or {}

        # Sub-workflow executors
        self._executors: Dict[str, WorkflowExecutorAdapter] = {}

        # Sub-workflow references by parent
        self._sub_workflows: Dict[UUID, List[SubWorkflowReferenceLegacy]] = {}

        # Active executions
        self._active_executions: Dict[UUID, NestedExecutionContextLegacy] = {}

        # Dependency graph for cycle detection
        self._dependency_graph: Dict[UUID, Set[UUID]] = {}

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

        logger.info(f"NestedWorkflowManagerAdapter created: {manager_id}")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Get manager ID."""
        return self._id

    @property
    def max_global_depth(self) -> int:
        """Get maximum global depth."""
        return self._max_global_depth

    @property
    def executor_count(self) -> int:
        """Get number of registered executors."""
        return len(self._executors)

    # -------------------------------------------------------------------------
    # Sub-Workflow Registration (Legacy API)
    # -------------------------------------------------------------------------

    async def register_sub_workflow(
        self,
        parent_workflow_id: UUID,
        sub_workflow: SubWorkflowReferenceLegacy,
        executor_fn: Optional[Callable] = None,
    ) -> SubWorkflowReferenceLegacy:
        """
        Register a sub-workflow (legacy API).

        Args:
            parent_workflow_id: Parent workflow ID
            sub_workflow: Sub-workflow reference
            executor_fn: Optional async function for workflow logic

        Returns:
            Registered sub-workflow reference

        Raises:
            ValueError: If circular dependency detected
        """
        # Update dependency graph
        if parent_workflow_id not in self._dependency_graph:
            self._dependency_graph[parent_workflow_id] = set()

        if sub_workflow.workflow_id:
            self._dependency_graph[parent_workflow_id].add(sub_workflow.workflow_id)

            # Check for circular dependencies
            if self._has_cycle(parent_workflow_id):
                self._dependency_graph[parent_workflow_id].discard(sub_workflow.workflow_id)
                raise ValueError(
                    f"Circular dependency detected when adding sub-workflow "
                    f"'{sub_workflow.workflow_id}' to parent '{parent_workflow_id}'"
                )

        # Create and register executor
        executor = convert_sub_workflow_reference_to_executor(sub_workflow, executor_fn)
        self._executors[str(sub_workflow.id)] = executor

        # Add to sub-workflows list
        if parent_workflow_id not in self._sub_workflows:
            self._sub_workflows[parent_workflow_id] = []

        self._sub_workflows[parent_workflow_id].append(sub_workflow)
        self._sub_workflows[parent_workflow_id].sort(key=lambda x: x.position)

        logger.info(f"Registered sub-workflow {sub_workflow.id} for parent {parent_workflow_id}")

        return sub_workflow

    def unregister_sub_workflow(
        self,
        parent_workflow_id: UUID,
        sub_workflow_id: UUID,
    ) -> bool:
        """
        Unregister a sub-workflow.

        Args:
            parent_workflow_id: Parent workflow ID
            sub_workflow_id: Sub-workflow ID to remove

        Returns:
            True if removed, False if not found
        """
        if parent_workflow_id not in self._sub_workflows:
            return False

        original_count = len(self._sub_workflows[parent_workflow_id])
        removed_ref = None

        for ref in self._sub_workflows[parent_workflow_id]:
            if ref.id == sub_workflow_id:
                removed_ref = ref
                break

        if removed_ref:
            self._sub_workflows[parent_workflow_id].remove(removed_ref)

            # Clean up executor
            executor_id = str(sub_workflow_id)
            if executor_id in self._executors:
                del self._executors[executor_id]

            # Clean up dependency graph
            if removed_ref.workflow_id:
                self._dependency_graph.get(parent_workflow_id, set()).discard(removed_ref.workflow_id)

        return len(self._sub_workflows[parent_workflow_id]) < original_count

    def get_sub_workflows(
        self,
        parent_workflow_id: UUID,
    ) -> List[SubWorkflowReferenceLegacy]:
        """Get all sub-workflows for a parent workflow."""
        return self._sub_workflows.get(parent_workflow_id, [])

    # -------------------------------------------------------------------------
    # Cycle Detection
    # -------------------------------------------------------------------------

    def _has_cycle(self, start_id: UUID) -> bool:
        """Detect circular dependencies using DFS."""
        visited: Set[UUID] = set()
        rec_stack: Set[UUID] = set()

        def dfs(node_id: UUID) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in self._dependency_graph.get(node_id, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        return dfs(start_id)

    # -------------------------------------------------------------------------
    # Sub-Workflow Execution
    # -------------------------------------------------------------------------

    async def execute_sub_workflow(
        self,
        parent_context: NestedExecutionContextLegacy,
        sub_workflow: SubWorkflowReferenceLegacy,
    ) -> NestedWorkflowResultLegacy:
        """
        Execute a sub-workflow (legacy API using new executor).

        Args:
            parent_context: Parent execution context (legacy format)
            sub_workflow: Sub-workflow reference

        Returns:
            Execution result in legacy format

        Raises:
            ValueError: If depth limit exceeded
        """
        # Check depth limits
        new_depth = parent_context.depth + 1
        if new_depth > sub_workflow.config.max_depth:
            raise ValueError(
                f"Maximum nesting depth ({sub_workflow.config.max_depth}) exceeded "
                f"at depth {new_depth}"
            )

        if new_depth > self._max_global_depth:
            raise ValueError(
                f"Global maximum nesting depth ({self._max_global_depth}) exceeded "
                f"at depth {new_depth}"
            )

        # Get or create executor
        executor_id = str(sub_workflow.id)
        executor = self._executors.get(executor_id)

        if not executor:
            # Create executor on-the-fly
            executor = convert_sub_workflow_reference_to_executor(sub_workflow)
            self._executors[executor_id] = executor

        # Prepare input data
        input_data = self._prepare_input_data(parent_context, sub_workflow)

        # Create child context for tracking
        child_context = self._create_child_context(parent_context, sub_workflow)
        self._active_executions[child_context.execution_id] = child_context

        # Emit event
        await self._emit_event("sub_workflow_started", {
            "parent_execution_id": str(parent_context.execution_id),
            "child_execution_id": str(child_context.execution_id),
            "workflow_id": str(sub_workflow.workflow_id or sub_workflow.id),
            "depth": new_depth,
        })

        try:
            # Build and run executor
            if executor.workflow:
                executor.build()
                result = await executor.run(
                    input_data,
                    timeout_seconds=sub_workflow.config.timeout_seconds,
                    metadata={
                        "parent_execution_id": str(parent_context.execution_id),
                        "depth": new_depth,
                    },
                )
            else:
                # No workflow set, return mock result
                result = WorkflowExecutorResult(
                    status=WorkflowExecutorStatus.COMPLETED,
                    outputs=[input_data],
                    execution_id=str(child_context.execution_id),
                    workflow_id=str(sub_workflow.workflow_id or sub_workflow.id),
                )

            # Convert to legacy result
            legacy_result = convert_executor_result_to_legacy(
                result,
                workflow_id=sub_workflow.workflow_id or sub_workflow.id,
                depth=new_depth,
            )

            # Map outputs to parent context if configured
            if sub_workflow.config.return_outputs:
                self._map_outputs(parent_context, sub_workflow, legacy_result.outputs)

            # Update child context
            child_context.completed_at = datetime.utcnow()
            child_context.status = legacy_result.status.value
            child_context.result = legacy_result.outputs

            # Emit completion event
            await self._emit_event("sub_workflow_completed", {
                "execution_id": str(child_context.execution_id),
                "result": legacy_result.to_dict(),
            })

            return legacy_result

        except asyncio.TimeoutError:
            child_context.status = "timeout"
            child_context.error = f"Timeout after {sub_workflow.config.timeout_seconds}s"
            child_context.completed_at = datetime.utcnow()

            return NestedWorkflowResultLegacy(
                execution_id=child_context.execution_id,
                workflow_id=sub_workflow.workflow_id or sub_workflow.id,
                status=NestedExecutionStatusLegacy.TIMEOUT,
                error=child_context.error,
                depth=new_depth,
            )

        except Exception as e:
            child_context.status = "failed"
            child_context.error = str(e)
            child_context.completed_at = datetime.utcnow()

            return NestedWorkflowResultLegacy(
                execution_id=child_context.execution_id,
                workflow_id=sub_workflow.workflow_id or sub_workflow.id,
                status=NestedExecutionStatusLegacy.FAILED,
                error=str(e),
                depth=new_depth,
            )

    def _prepare_input_data(
        self,
        parent_context: NestedExecutionContextLegacy,
        sub_workflow: SubWorkflowReferenceLegacy,
    ) -> Dict[str, Any]:
        """Prepare input data for sub-workflow execution."""
        input_data: Dict[str, Any] = {}

        # Apply input mapping
        for parent_key, child_key in sub_workflow.input_mapping.items():
            if parent_key in parent_context.variables:
                input_data[child_key] = parent_context.variables[parent_key]

        # Pass context if configured
        if sub_workflow.config.pass_context:
            input_data["_parent_context"] = parent_context.to_dict()

        return input_data

    def _create_child_context(
        self,
        parent_context: NestedExecutionContextLegacy,
        sub_workflow: SubWorkflowReferenceLegacy,
    ) -> NestedExecutionContextLegacy:
        """Create child execution context based on scope configuration."""
        child_variables: Dict[str, Any] = {}

        scope = sub_workflow.config.scope
        if scope == WorkflowScopeLegacy.INHERITED:
            child_variables = parent_context.variables.copy()
        elif scope == WorkflowScopeLegacy.SHARED:
            child_variables = parent_context.variables
        # ISOLATED: keep empty

        # Apply input mapping
        for parent_key, child_key in sub_workflow.input_mapping.items():
            if parent_key in parent_context.variables:
                child_variables[child_key] = parent_context.variables[parent_key]

        return NestedExecutionContextLegacy(
            execution_id=uuid4(),
            parent_execution_id=parent_context.execution_id,
            workflow_id=sub_workflow.workflow_id or sub_workflow.id,
            depth=parent_context.depth + 1,
            path=parent_context.path + [parent_context.execution_id],
            variables=child_variables,
            parent_variables=(
                parent_context.variables
                if scope == WorkflowScopeLegacy.SHARED
                else None
            ),
        )

    def _map_outputs(
        self,
        parent_context: NestedExecutionContextLegacy,
        sub_workflow: SubWorkflowReferenceLegacy,
        outputs: Dict[str, Any],
    ) -> None:
        """Map sub-workflow outputs back to parent context."""
        for child_key, parent_key in sub_workflow.output_mapping.items():
            if child_key in outputs:
                parent_context.variables[parent_key] = outputs[child_key]

    # -------------------------------------------------------------------------
    # Execution Tree
    # -------------------------------------------------------------------------

    def get_execution_tree(
        self,
        root_execution_id: UUID,
    ) -> Dict[str, Any]:
        """Get execution tree structure for visualization."""

        def build_tree(exec_id: UUID) -> Dict[str, Any]:
            context = self._active_executions.get(exec_id)
            if not context:
                return {"id": str(exec_id), "status": "not_found"}

            children = [
                build_tree(child_id)
                for child_id, child_ctx in self._active_executions.items()
                if child_ctx.parent_execution_id == exec_id
            ]

            return {
                "id": str(exec_id),
                "workflow_id": str(context.workflow_id),
                "depth": context.depth,
                "status": context.status,
                "started_at": context.started_at.isoformat(),
                "completed_at": context.completed_at.isoformat() if context.completed_at else None,
                "children": children,
            }

        return build_tree(root_execution_id)

    def get_active_executions(
        self,
        workflow_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of active executions."""
        executions = self._active_executions.values()

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        return [e.to_dict() for e in executions]

    # -------------------------------------------------------------------------
    # Cancellation
    # -------------------------------------------------------------------------

    async def cancel_nested_execution(
        self,
        execution_id: UUID,
        cascade: bool = True,
    ) -> bool:
        """Cancel a nested execution."""
        context = self._active_executions.get(execution_id)
        if not context:
            return False

        if cascade:
            children_to_cancel = [
                child_id
                for child_id, ctx in self._active_executions.items()
                if execution_id in ctx.path
            ]

            for child_id in children_to_cancel:
                child_ctx = self._active_executions.get(child_id)
                if child_ctx:
                    child_ctx.status = "cancelled"
                    child_ctx.completed_at = datetime.utcnow()

        context.status = "cancelled"
        context.completed_at = datetime.utcnow()

        await self._emit_event("execution_cancelled", {
            "execution_id": str(execution_id),
            "cascade": cascade,
        })

        return True

    def clear_completed_executions(
        self,
        older_than_seconds: int = 3600,
    ) -> int:
        """Clear completed executions older than specified seconds."""
        now = datetime.utcnow()
        to_remove = []

        for exec_id, context in self._active_executions.items():
            if context.status in ["completed", "failed", "cancelled", "timeout"]:
                if context.completed_at:
                    age = (now - context.completed_at).total_seconds()
                    if age > older_than_seconds:
                        to_remove.append(exec_id)

        for exec_id in to_remove:
            del self._active_executions[exec_id]

        return len(to_remove)

    # -------------------------------------------------------------------------
    # Event Handling
    # -------------------------------------------------------------------------

    def on_event(
        self,
        event_type: str,
        handler: Callable,
    ) -> None:
        """Register an event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def _emit_event(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Emit an event to all registered handlers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        total = len(self._active_executions)
        by_status: Dict[str, int] = {}
        by_depth: Dict[int, int] = {}

        for context in self._active_executions.values():
            by_status[context.status] = by_status.get(context.status, 0) + 1
            by_depth[context.depth] = by_depth.get(context.depth, 0) + 1

        return {
            "total_active_executions": total,
            "by_status": by_status,
            "by_depth": by_depth,
            "registered_sub_workflows": sum(
                len(sws) for sws in self._sub_workflows.values()
            ),
            "registered_executors": len(self._executors),
            "dependency_graph_size": len(self._dependency_graph),
            "max_global_depth": self._max_global_depth,
        }

    # -------------------------------------------------------------------------
    # Checkpoint Support
    # -------------------------------------------------------------------------

    async def on_checkpoint_save(self) -> Dict[str, Any]:
        """Get state for checkpointing."""
        executor_states = {}
        for exec_id, executor in self._executors.items():
            executor_states[exec_id] = await executor.on_checkpoint_save()

        return {
            "id": self._id,
            "max_global_depth": self._max_global_depth,
            "executor_states": executor_states,
            "active_executions": {
                str(k): v.to_dict()
                for k, v in self._active_executions.items()
            },
            "sub_workflows": {
                str(k): [sw.to_dict() for sw in v]
                for k, v in self._sub_workflows.items()
            },
        }

    async def on_checkpoint_restore(self, state: Dict[str, Any]) -> None:
        """Restore state from checkpoint."""
        # Restore executor states
        for exec_id, exec_state in state.get("executor_states", {}).items():
            if exec_id in self._executors:
                await self._executors[exec_id].on_checkpoint_restore(exec_state)

        logger.info(f"Restored state for manager {self._id}")


# =============================================================================
# Factory Functions
# =============================================================================


def migrate_nested_workflow_manager(
    manager_id: str,
    max_global_depth: int = 10,
    config: Optional[Dict[str, Any]] = None,
) -> NestedWorkflowManagerAdapter:
    """
    Create a NestedWorkflowManagerAdapter for migration.

    This is the primary entry point for migrating from Phase 2
    NestedWorkflowManager to Agent Framework WorkflowExecutor.

    Args:
        manager_id: Unique identifier for the manager
        max_global_depth: Maximum global nesting depth
        config: Additional configuration

    Returns:
        Configured NestedWorkflowManagerAdapter

    Example:
        ```python
        # Migrate from Phase 2
        manager = migrate_nested_workflow_manager("my-manager")

        # Register sub-workflow (same API as Phase 2)
        await manager.register_sub_workflow(parent_id, sub_ref)

        # Execute (uses new WorkflowExecutor internally)
        result = await manager.execute_sub_workflow(context, sub_ref)
        ```
    """
    return NestedWorkflowManagerAdapter(
        manager_id=manager_id,
        max_global_depth=max_global_depth,
        config=config,
    )


def create_nested_executor_from_legacy(
    reference: SubWorkflowReferenceLegacy,
    executor_fn: Optional[Callable] = None,
) -> WorkflowExecutorAdapter:
    """
    Create a WorkflowExecutorAdapter from legacy SubWorkflowReference.

    Args:
        reference: Phase 2 sub-workflow reference
        executor_fn: Optional async function for workflow logic

    Returns:
        Configured WorkflowExecutorAdapter

    Example:
        ```python
        legacy_ref = SubWorkflowReferenceLegacy(...)
        executor = create_nested_executor_from_legacy(legacy_ref, my_executor_fn)
        executor.build()
        result = await executor.run(input_data)
        ```
    """
    return convert_sub_workflow_reference_to_executor(reference, executor_fn)


def create_migration_context(
    execution_id: Optional[UUID] = None,
    workflow_id: Optional[UUID] = None,
    variables: Optional[Dict[str, Any]] = None,
    depth: int = 0,
) -> NestedExecutionContextLegacy:
    """
    Create a legacy execution context for migration testing.

    Args:
        execution_id: Execution ID (generated if not provided)
        workflow_id: Workflow ID (generated if not provided)
        variables: Context variables
        depth: Nesting depth

    Returns:
        NestedExecutionContextLegacy for testing
    """
    return NestedExecutionContextLegacy(
        execution_id=execution_id or uuid4(),
        parent_execution_id=None,
        workflow_id=workflow_id or uuid4(),
        depth=depth,
        path=[],
        variables=variables or {},
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Legacy Enums
    "NestedWorkflowTypeLegacy",
    "WorkflowScopeLegacy",
    "NestedExecutionStatusLegacy",
    # Legacy Data Classes
    "NestedWorkflowConfigLegacy",
    "SubWorkflowReferenceLegacy",
    "NestedExecutionContextLegacy",
    "NestedWorkflowResultLegacy",
    # Conversion Functions
    "convert_legacy_status_to_executor",
    "convert_executor_status_to_legacy",
    "convert_legacy_context_to_execution",
    "convert_execution_to_legacy_context",
    "convert_legacy_config_to_executor_config",
    "convert_executor_config_to_legacy",
    "convert_executor_result_to_legacy",
    "convert_legacy_result_to_executor",
    "convert_sub_workflow_reference_to_executor",
    # Adapter Class
    "NestedWorkflowManagerAdapter",
    # Factory Functions
    "migrate_nested_workflow_manager",
    "create_nested_executor_from_legacy",
    "create_migration_context",
]
