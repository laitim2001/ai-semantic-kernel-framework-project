# =============================================================================
# IPA Platform - Nested Workflow Manager
# =============================================================================
# Sprint 11: S11-1 NestedWorkflowManager
#
# Manages nested workflow structures including:
# - Workflow hierarchy management
# - Sub-workflow registration and execution
# - Context propagation between levels
# - Depth limiting and cycle detection
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Protocol, Callable, Awaitable
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class NestedWorkflowType(str, Enum):
    """
    嵌套工作流類型

    Defines different types of nested workflows:
    - INLINE: Inline defined sub-workflow
    - REFERENCE: Reference to existing workflow
    - DYNAMIC: Dynamically generated sub-workflow
    - RECURSIVE: Recursive self-calling workflow
    """
    INLINE = "inline"
    REFERENCE = "reference"
    DYNAMIC = "dynamic"
    RECURSIVE = "recursive"


class WorkflowScope(str, Enum):
    """
    工作流作用域

    Defines context sharing behavior:
    - ISOLATED: Completely isolated, independent context
    - INHERITED: Inherits parent workflow context
    - SHARED: Shared context with bidirectional sync
    """
    ISOLATED = "isolated"
    INHERITED = "inherited"
    SHARED = "shared"


# =============================================================================
# Protocols
# =============================================================================


class WorkflowServiceProtocol(Protocol):
    """Protocol for workflow service dependency."""

    async def get_workflow(self, workflow_id: UUID) -> Optional[Dict[str, Any]]:
        """Get workflow by ID."""
        ...


class ExecutionServiceProtocol(Protocol):
    """Protocol for execution service dependency."""

    async def execute_workflow(
        self,
        workflow_id: UUID,
        inputs: Dict[str, Any],
        parent_execution_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Execute a workflow."""
        ...

    async def execute_workflow_definition(
        self,
        definition: Dict[str, Any],
        inputs: Dict[str, Any],
        parent_execution_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Execute a workflow from inline definition."""
        ...

    async def cancel_execution(self, execution_id: UUID) -> bool:
        """Cancel an execution."""
        ...


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class NestedWorkflowConfig:
    """
    嵌套工作流配置

    Configuration for nested workflow behavior including depth limits,
    timeout settings, retry policies, and context handling.
    """
    workflow_type: NestedWorkflowType = NestedWorkflowType.REFERENCE
    scope: WorkflowScope = WorkflowScope.INHERITED
    max_depth: int = 5
    timeout_seconds: int = 600
    retry_on_failure: bool = True
    max_retries: int = 2
    pass_context: bool = True
    return_outputs: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
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
    def from_dict(cls, data: Dict[str, Any]) -> "NestedWorkflowConfig":
        """Create config from dictionary."""
        return cls(
            workflow_type=NestedWorkflowType(data.get("workflow_type", "reference")),
            scope=WorkflowScope(data.get("scope", "inherited")),
            max_depth=data.get("max_depth", 5),
            timeout_seconds=data.get("timeout_seconds", 600),
            retry_on_failure=data.get("retry_on_failure", True),
            max_retries=data.get("max_retries", 2),
            pass_context=data.get("pass_context", True),
            return_outputs=data.get("return_outputs", True),
        )


@dataclass
class SubWorkflowReference:
    """
    子工作流引用

    Represents a reference to a sub-workflow within a parent workflow,
    including configuration, mappings, and execution state.
    """
    id: UUID
    parent_workflow_id: UUID
    workflow_id: Optional[UUID]  # For REFERENCE type
    definition: Optional[Dict[str, Any]]  # For INLINE/DYNAMIC type
    config: NestedWorkflowConfig
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    position: int = 0
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert reference to dictionary."""
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
class NestedExecutionContext:
    """
    嵌套執行上下文

    Maintains execution context for nested workflows including
    variables, execution path, and parent relationships.
    """
    execution_id: UUID
    parent_execution_id: Optional[UUID]
    workflow_id: UUID
    depth: int
    path: List[UUID]  # Execution path from root to current
    variables: Dict[str, Any]
    parent_variables: Optional[Dict[str, Any]] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
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


# =============================================================================
# Nested Workflow Manager
# =============================================================================


class NestedWorkflowManager:
    """
    嵌套工作流管理器

    Manages nested workflow structures with support for:
    - Registering and tracking sub-workflows
    - Executing sub-workflows with context propagation
    - Cycle detection in workflow dependencies
    - Depth limiting to prevent infinite nesting
    - Execution tree visualization
    """

    def __init__(
        self,
        workflow_service: Optional[WorkflowServiceProtocol] = None,
        execution_service: Optional[ExecutionServiceProtocol] = None,
        max_global_depth: int = 10
    ):
        """
        Initialize NestedWorkflowManager.

        Args:
            workflow_service: Service for workflow operations
            execution_service: Service for execution operations
            max_global_depth: Maximum global nesting depth
        """
        self.workflow_service = workflow_service
        self.execution_service = execution_service
        self.max_global_depth = max_global_depth

        # Active nested executions
        self._active_executions: Dict[UUID, NestedExecutionContext] = {}

        # Sub-workflow references by parent
        self._sub_workflows: Dict[UUID, List[SubWorkflowReference]] = {}

        # Workflow dependency graph for cycle detection
        self._dependency_graph: Dict[UUID, Set[UUID]] = {}

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

    # =========================================================================
    # Sub-Workflow Registration
    # =========================================================================

    async def register_sub_workflow(
        self,
        parent_workflow_id: UUID,
        sub_workflow: SubWorkflowReference
    ) -> SubWorkflowReference:
        """
        註冊子工作流

        Register a sub-workflow with a parent workflow.

        Args:
            parent_workflow_id: Parent workflow ID
            sub_workflow: Sub-workflow reference

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
                # Remove the added dependency
                self._dependency_graph[parent_workflow_id].discard(sub_workflow.workflow_id)
                raise ValueError(
                    f"Circular dependency detected when adding sub-workflow "
                    f"'{sub_workflow.workflow_id}' to parent '{parent_workflow_id}'"
                )

        # Add to sub-workflows list
        if parent_workflow_id not in self._sub_workflows:
            self._sub_workflows[parent_workflow_id] = []

        self._sub_workflows[parent_workflow_id].append(sub_workflow)

        # Sort by position
        self._sub_workflows[parent_workflow_id].sort(key=lambda x: x.position)

        logger.info(f"Registered sub-workflow {sub_workflow.id} for parent {parent_workflow_id}")

        return sub_workflow

    def unregister_sub_workflow(
        self,
        parent_workflow_id: UUID,
        sub_workflow_id: UUID
    ) -> bool:
        """
        取消註冊子工作流

        Remove a sub-workflow from a parent workflow.

        Args:
            parent_workflow_id: Parent workflow ID
            sub_workflow_id: Sub-workflow ID to remove

        Returns:
            True if removed, False if not found
        """
        if parent_workflow_id not in self._sub_workflows:
            return False

        original_count = len(self._sub_workflows[parent_workflow_id])
        self._sub_workflows[parent_workflow_id] = [
            sw for sw in self._sub_workflows[parent_workflow_id]
            if sw.id != sub_workflow_id
        ]

        # Also clean up dependency graph
        sub_wf = next(
            (sw for sw in self._sub_workflows.get(parent_workflow_id, [])
             if sw.id == sub_workflow_id),
            None
        )
        if sub_wf and sub_wf.workflow_id:
            self._dependency_graph.get(parent_workflow_id, set()).discard(sub_wf.workflow_id)

        return len(self._sub_workflows[parent_workflow_id]) < original_count

    def get_sub_workflows(
        self,
        parent_workflow_id: UUID
    ) -> List[SubWorkflowReference]:
        """
        獲取子工作流列表

        Get all sub-workflows for a parent workflow.

        Args:
            parent_workflow_id: Parent workflow ID

        Returns:
            List of sub-workflow references
        """
        return self._sub_workflows.get(parent_workflow_id, [])

    # =========================================================================
    # Cycle Detection
    # =========================================================================

    def _has_cycle(self, start_id: UUID) -> bool:
        """
        檢測循環依賴

        Detect circular dependencies using DFS.

        Args:
            start_id: Starting workflow ID

        Returns:
            True if cycle detected, False otherwise
        """
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

    def get_dependency_chain(
        self,
        workflow_id: UUID,
        max_depth: int = 10
    ) -> List[UUID]:
        """
        獲取依賴鏈

        Get the dependency chain for a workflow.

        Args:
            workflow_id: Workflow ID
            max_depth: Maximum depth to traverse

        Returns:
            List of workflow IDs in dependency order
        """
        chain: List[UUID] = []
        visited: Set[UUID] = set()

        def traverse(wf_id: UUID, depth: int) -> None:
            if wf_id in visited or depth > max_depth:
                return
            visited.add(wf_id)
            chain.append(wf_id)

            for dep in self._dependency_graph.get(wf_id, set()):
                traverse(dep, depth + 1)

        traverse(workflow_id, 0)
        return chain

    # =========================================================================
    # Sub-Workflow Execution
    # =========================================================================

    async def execute_sub_workflow(
        self,
        parent_context: NestedExecutionContext,
        sub_workflow: SubWorkflowReference
    ) -> Dict[str, Any]:
        """
        執行子工作流

        Execute a sub-workflow within a parent context.

        Args:
            parent_context: Parent execution context
            sub_workflow: Sub-workflow reference

        Returns:
            Execution result

        Raises:
            ValueError: If depth limit exceeded
            TimeoutError: If execution times out
        """
        # Check depth limits
        new_depth = parent_context.depth + 1
        if new_depth > sub_workflow.config.max_depth:
            raise ValueError(
                f"Maximum nesting depth ({sub_workflow.config.max_depth}) exceeded "
                f"at depth {new_depth}"
            )

        if new_depth > self.max_global_depth:
            raise ValueError(
                f"Global maximum nesting depth ({self.max_global_depth}) exceeded "
                f"at depth {new_depth}"
            )

        # Create child context
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
            # Execute based on type
            result = await self._execute_by_type(child_context, sub_workflow)

            # Map outputs to parent context
            if sub_workflow.config.return_outputs:
                self._map_outputs(parent_context, sub_workflow, result)

            child_context.completed_at = datetime.utcnow()
            child_context.status = "completed"
            child_context.result = result

            # Emit completion event
            await self._emit_event("sub_workflow_completed", {
                "execution_id": str(child_context.execution_id),
                "result": result,
            })

            return result

        except asyncio.TimeoutError:
            child_context.status = "timeout"
            child_context.error = f"Timeout after {sub_workflow.config.timeout_seconds}s"
            raise TimeoutError(
                f"Sub-workflow {sub_workflow.id} timed out "
                f"after {sub_workflow.config.timeout_seconds} seconds"
            )

        except Exception as e:
            child_context.status = "failed"
            child_context.error = str(e)

            # Handle retry
            if sub_workflow.config.retry_on_failure:
                # Retry logic would go here
                pass

            raise

        finally:
            child_context.completed_at = datetime.utcnow()
            # Keep in active executions for tree visualization

    async def _execute_by_type(
        self,
        context: NestedExecutionContext,
        sub_workflow: SubWorkflowReference
    ) -> Dict[str, Any]:
        """Execute sub-workflow based on its type."""
        wf_type = sub_workflow.config.workflow_type

        if wf_type == NestedWorkflowType.REFERENCE:
            return await self._execute_reference_workflow(context, sub_workflow)
        elif wf_type == NestedWorkflowType.INLINE:
            return await self._execute_inline_workflow(context, sub_workflow)
        elif wf_type == NestedWorkflowType.DYNAMIC:
            return await self._execute_dynamic_workflow(context, sub_workflow)
        elif wf_type == NestedWorkflowType.RECURSIVE:
            return await self._execute_recursive_workflow(context, sub_workflow)
        else:
            raise ValueError(f"Unknown workflow type: {wf_type}")

    async def _execute_reference_workflow(
        self,
        context: NestedExecutionContext,
        sub_workflow: SubWorkflowReference
    ) -> Dict[str, Any]:
        """
        執行引用的工作流

        Execute a workflow by reference.
        """
        if not self.execution_service:
            # Fallback: return mock result
            logger.warning("No execution service, returning mock result")
            return {
                "status": "completed",
                "workflow_id": str(sub_workflow.workflow_id),
                "inputs": context.variables,
                "mock": True,
            }

        return await asyncio.wait_for(
            self.execution_service.execute_workflow(
                workflow_id=sub_workflow.workflow_id,
                inputs=context.variables,
                parent_execution_id=context.parent_execution_id
            ),
            timeout=sub_workflow.config.timeout_seconds
        )

    async def _execute_inline_workflow(
        self,
        context: NestedExecutionContext,
        sub_workflow: SubWorkflowReference
    ) -> Dict[str, Any]:
        """
        執行內聯定義的工作流

        Execute an inline-defined workflow.
        """
        definition = sub_workflow.definition
        if not definition:
            raise ValueError("Inline workflow requires definition")

        if not self.execution_service:
            logger.warning("No execution service, returning mock result")
            return {
                "status": "completed",
                "definition": definition,
                "inputs": context.variables,
                "mock": True,
            }

        return await asyncio.wait_for(
            self.execution_service.execute_workflow_definition(
                definition=definition,
                inputs=context.variables,
                parent_execution_id=context.parent_execution_id
            ),
            timeout=sub_workflow.config.timeout_seconds
        )

    async def _execute_dynamic_workflow(
        self,
        context: NestedExecutionContext,
        sub_workflow: SubWorkflowReference
    ) -> Dict[str, Any]:
        """
        執行動態生成的工作流

        Execute a dynamically generated workflow.
        """
        definition = sub_workflow.definition or {}

        # Check if there's a generator function
        generator = definition.get("generator")
        if callable(generator):
            if asyncio.iscoroutinefunction(generator):
                definition = await generator(context.variables)
            else:
                definition = generator(context.variables)

        if not self.execution_service:
            logger.warning("No execution service, returning mock result")
            return {
                "status": "completed",
                "dynamic": True,
                "definition": definition,
                "inputs": context.variables,
                "mock": True,
            }

        return await asyncio.wait_for(
            self.execution_service.execute_workflow_definition(
                definition=definition,
                inputs=context.variables,
                parent_execution_id=context.parent_execution_id
            ),
            timeout=sub_workflow.config.timeout_seconds
        )

    async def _execute_recursive_workflow(
        self,
        context: NestedExecutionContext,
        sub_workflow: SubWorkflowReference
    ) -> Dict[str, Any]:
        """
        執行遞歸工作流

        Execute a recursive workflow with termination checking.
        """
        definition = sub_workflow.definition or {}

        # Check termination condition
        termination_condition = definition.get("termination_condition")
        if termination_condition and callable(termination_condition):
            if termination_condition(context.variables):
                return {
                    "status": "terminated",
                    "depth": context.depth,
                    "reason": "termination_condition_met",
                }

        # Execute as reference workflow
        return await self._execute_reference_workflow(context, sub_workflow)

    # =========================================================================
    # Context Management
    # =========================================================================

    def _create_child_context(
        self,
        parent_context: NestedExecutionContext,
        sub_workflow: SubWorkflowReference
    ) -> NestedExecutionContext:
        """
        建立子執行上下文

        Create child execution context based on scope configuration.
        """
        child_variables: Dict[str, Any] = {}

        # Handle variables based on scope
        scope = sub_workflow.config.scope

        if scope == WorkflowScope.INHERITED:
            child_variables = parent_context.variables.copy()
        elif scope == WorkflowScope.SHARED:
            child_variables = parent_context.variables  # Shared reference
        # ISOLATED: keep empty child_variables

        # Apply input mapping
        for parent_key, child_key in sub_workflow.input_mapping.items():
            if parent_key in parent_context.variables:
                child_variables[child_key] = parent_context.variables[parent_key]

        return NestedExecutionContext(
            execution_id=uuid4(),
            parent_execution_id=parent_context.execution_id,
            workflow_id=sub_workflow.workflow_id or sub_workflow.id,
            depth=parent_context.depth + 1,
            path=parent_context.path + [parent_context.execution_id],
            variables=child_variables,
            parent_variables=(
                parent_context.variables
                if scope == WorkflowScope.SHARED
                else None
            ),
        )

    def _map_outputs(
        self,
        parent_context: NestedExecutionContext,
        sub_workflow: SubWorkflowReference,
        result: Dict[str, Any]
    ) -> None:
        """
        將子工作流輸出映射回父上下文

        Map sub-workflow outputs back to parent context.
        """
        for child_key, parent_key in sub_workflow.output_mapping.items():
            if child_key in result:
                parent_context.variables[parent_key] = result[child_key]

    # =========================================================================
    # Execution Tree
    # =========================================================================

    def get_execution_tree(
        self,
        root_execution_id: UUID
    ) -> Dict[str, Any]:
        """
        獲取執行樹結構

        Get the execution tree structure for visualization.

        Args:
            root_execution_id: Root execution ID

        Returns:
            Tree structure as dictionary
        """
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
        workflow_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取活躍執行列表

        Get list of active executions, optionally filtered by workflow.
        """
        executions = self._active_executions.values()

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        return [e.to_dict() for e in executions]

    # =========================================================================
    # Cancellation
    # =========================================================================

    async def cancel_nested_execution(
        self,
        execution_id: UUID,
        cascade: bool = True
    ) -> bool:
        """
        取消嵌套執行

        Cancel a nested execution, optionally cascading to children.

        Args:
            execution_id: Execution ID to cancel
            cascade: Whether to cancel child executions

        Returns:
            True if cancelled successfully
        """
        context = self._active_executions.get(execution_id)
        if not context:
            return False

        if cascade:
            # Find and cancel all child executions
            children_to_cancel = [
                child_id
                for child_id, ctx in self._active_executions.items()
                if execution_id in ctx.path
            ]

            for child_id in children_to_cancel:
                if self.execution_service:
                    await self.execution_service.cancel_execution(child_id)
                child_ctx = self._active_executions.get(child_id)
                if child_ctx:
                    child_ctx.status = "cancelled"

        # Cancel the execution itself
        if self.execution_service:
            await self.execution_service.cancel_execution(execution_id)

        context.status = "cancelled"
        context.completed_at = datetime.utcnow()

        # Emit event
        await self._emit_event("execution_cancelled", {
            "execution_id": str(execution_id),
            "cascade": cascade,
        })

        return True

    def clear_completed_executions(
        self,
        older_than_seconds: int = 3600
    ) -> int:
        """
        清理已完成的執行

        Clear completed executions older than specified seconds.

        Args:
            older_than_seconds: Age threshold in seconds

        Returns:
            Number of executions cleared
        """
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

    # =========================================================================
    # Event Handling
    # =========================================================================

    def on_event(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        註冊事件處理器

        Register an event handler.

        Args:
            event_type: Event type to handle
            handler: Async handler function
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def _emit_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Emit an event to all registered handlers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取統計信息

        Get manager statistics.
        """
        total = len(self._active_executions)
        by_status = {}
        by_depth = {}

        for context in self._active_executions.values():
            # By status
            by_status[context.status] = by_status.get(context.status, 0) + 1

            # By depth
            by_depth[context.depth] = by_depth.get(context.depth, 0) + 1

        return {
            "total_active_executions": total,
            "by_status": by_status,
            "by_depth": by_depth,
            "registered_sub_workflows": sum(
                len(sws) for sws in self._sub_workflows.values()
            ),
            "dependency_graph_size": len(self._dependency_graph),
            "max_global_depth": self.max_global_depth,
        }
