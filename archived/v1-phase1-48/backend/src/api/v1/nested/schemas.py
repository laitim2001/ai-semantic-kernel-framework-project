# =============================================================================
# IPA Platform - Nested Workflow API Schemas
# =============================================================================
# Sprint 11: S11-5 Nested Workflow API
#
# Pydantic schemas for Nested Workflow API endpoints.
# Provides request/response validation for:
#   - Nested workflow registration and management
#   - Sub-workflow execution
#   - Recursive pattern execution
#   - Workflow composition
#   - Context propagation
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class NestedWorkflowTypeEnum(str, Enum):
    """Nested workflow type options for API requests."""

    INLINE = "inline"
    REFERENCE = "reference"
    DYNAMIC = "dynamic"
    RECURSIVE = "recursive"


class WorkflowScopeEnum(str, Enum):
    """Workflow scope options for context sharing."""

    ISOLATED = "isolated"
    INHERITED = "inherited"
    SHARED = "shared"


class SubWorkflowExecutionModeEnum(str, Enum):
    """Sub-workflow execution mode options."""

    SYNC = "sync"
    ASYNC = "async"
    FIRE_AND_FORGET = "fire_and_forget"
    CALLBACK = "callback"


class RecursionStrategyEnum(str, Enum):
    """Recursion strategy options."""

    DEPTH_FIRST = "depth_first"
    BREADTH_FIRST = "breadth_first"
    PARALLEL = "parallel"


class TerminationTypeEnum(str, Enum):
    """Recursion termination type options."""

    CONDITION = "condition"
    MAX_DEPTH = "max_depth"
    MAX_ITERATIONS = "max_iterations"
    TIMEOUT = "timeout"
    CONVERGENCE = "convergence"
    USER_ABORT = "user_abort"


class CompositionTypeEnum(str, Enum):
    """Composition type options."""

    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    SWITCH = "switch"


class ExecutionStatusEnum(str, Enum):
    """Nested execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class PropagationTypeEnum(str, Enum):
    """Context propagation type options."""

    COPY = "copy"
    REFERENCE = "reference"
    MERGE = "merge"
    FILTER = "filter"


# =============================================================================
# Nested Workflow Schemas
# =============================================================================


class NestedWorkflowCreate(BaseModel):
    """Request schema for creating a nested workflow configuration."""

    parent_workflow_id: UUID = Field(..., description="Parent workflow ID")
    name: str = Field(..., min_length=1, max_length=100, description="Nested workflow name")
    workflow_type: NestedWorkflowTypeEnum = Field(
        NestedWorkflowTypeEnum.REFERENCE, description="Type of nested workflow"
    )
    scope: WorkflowScopeEnum = Field(
        WorkflowScopeEnum.INHERITED, description="Context scope"
    )
    sub_workflow_id: Optional[UUID] = Field(
        None, description="Sub-workflow ID (for REFERENCE type)"
    )
    inline_definition: Optional[Dict[str, Any]] = Field(
        None, description="Inline workflow definition (for INLINE type)"
    )
    max_depth: int = Field(
        10, ge=1, le=100, description="Maximum nesting depth"
    )
    timeout_seconds: int = Field(
        600, ge=1, le=7200, description="Execution timeout"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "parent_workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "data_processing_nested",
                "workflow_type": "reference",
                "scope": "inherited",
                "sub_workflow_id": "660e8400-e29b-41d4-a716-446655440001",
                "max_depth": 5,
                "timeout_seconds": 300,
            }
        }


class NestedWorkflowResponse(BaseModel):
    """Response schema for nested workflow operations."""

    config_id: UUID = Field(..., description="Configuration ID")
    parent_workflow_id: UUID = Field(..., description="Parent workflow ID")
    name: str = Field(..., description="Nested workflow name")
    workflow_type: NestedWorkflowTypeEnum = Field(..., description="Workflow type")
    scope: WorkflowScopeEnum = Field(..., description="Context scope")
    sub_workflow_id: Optional[UUID] = Field(None, description="Sub-workflow ID")
    max_depth: int = Field(..., description="Maximum nesting depth")
    timeout_seconds: int = Field(..., description="Timeout in seconds")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class NestedWorkflowListResponse(BaseModel):
    """Response schema for listing nested workflows."""

    items: List[NestedWorkflowResponse] = Field(..., description="Nested workflows")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


# =============================================================================
# Sub-Workflow Execution Schemas
# =============================================================================


class SubWorkflowExecuteRequest(BaseModel):
    """Request schema for executing a sub-workflow."""

    sub_workflow_id: UUID = Field(..., description="Sub-workflow ID to execute")
    inputs: Dict[str, Any] = Field(
        default_factory=dict, description="Input parameters"
    )
    mode: SubWorkflowExecutionModeEnum = Field(
        SubWorkflowExecutionModeEnum.SYNC, description="Execution mode"
    )
    timeout_seconds: Optional[int] = Field(
        None, ge=1, le=3600, description="Execution timeout"
    )
    parent_execution_id: Optional[UUID] = Field(
        None, description="Parent execution ID for context"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sub_workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "inputs": {"data": "process this"},
                "mode": "sync",
                "timeout_seconds": 120,
            }
        }


class SubWorkflowExecuteResponse(BaseModel):
    """Response schema for sub-workflow execution."""

    execution_id: UUID = Field(..., description="Execution ID")
    sub_workflow_id: UUID = Field(..., description="Sub-workflow ID")
    mode: SubWorkflowExecutionModeEnum = Field(..., description="Execution mode")
    status: ExecutionStatusEnum = Field(..., description="Current status")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")


class SubWorkflowBatchRequest(BaseModel):
    """Request schema for batch sub-workflow execution."""

    sub_workflows: List[Dict[str, Any]] = Field(
        ..., description="List of sub-workflows to execute"
    )
    parallel: bool = Field(True, description="Execute in parallel")
    pass_outputs: bool = Field(
        True, description="Pass outputs between sequential workflows"
    )
    stop_on_error: bool = Field(
        True, description="Stop batch on error"
    )
    timeout_seconds: Optional[int] = Field(
        None, ge=1, le=7200, description="Batch timeout"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sub_workflows": [
                    {"id": "550e8400-e29b-41d4-a716-446655440000", "inputs": {"step": 1}},
                    {"id": "550e8400-e29b-41d4-a716-446655440001", "inputs": {"step": 2}},
                ],
                "parallel": True,
                "stop_on_error": True,
                "timeout_seconds": 600,
            }
        }


class SubWorkflowBatchResponse(BaseModel):
    """Response schema for batch sub-workflow execution."""

    batch_id: UUID = Field(..., description="Batch execution ID")
    total_workflows: int = Field(..., description="Total workflows in batch")
    completed: int = Field(..., description="Completed workflows")
    failed: int = Field(..., description="Failed workflows")
    results: List[Dict[str, Any]] = Field(..., description="Individual results")
    status: ExecutionStatusEnum = Field(..., description="Overall status")


# =============================================================================
# Recursive Execution Schemas
# =============================================================================


class RecursiveExecuteRequest(BaseModel):
    """Request schema for recursive workflow execution."""

    workflow_id: UUID = Field(..., description="Workflow ID to execute recursively")
    inputs: Dict[str, Any] = Field(
        default_factory=dict, description="Initial input parameters"
    )
    strategy: RecursionStrategyEnum = Field(
        RecursionStrategyEnum.DEPTH_FIRST, description="Recursion strategy"
    )
    max_depth: int = Field(10, ge=1, le=100, description="Maximum recursion depth")
    max_iterations: int = Field(100, ge=1, le=10000, description="Maximum iterations")
    timeout_seconds: int = Field(600, ge=1, le=7200, description="Execution timeout")
    termination_condition: Optional[str] = Field(
        None, description="Termination condition expression"
    )
    enable_memoization: bool = Field(
        True, description="Enable result memoization"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "inputs": {"value": 10},
                "strategy": "depth_first",
                "max_depth": 5,
                "max_iterations": 50,
                "timeout_seconds": 300,
                "termination_condition": "value <= 1",
            }
        }


class RecursiveExecuteResponse(BaseModel):
    """Response schema for recursive workflow execution."""

    execution_id: UUID = Field(..., description="Execution ID")
    workflow_id: UUID = Field(..., description="Workflow ID")
    strategy: RecursionStrategyEnum = Field(..., description="Recursion strategy")
    status: ExecutionStatusEnum = Field(..., description="Current status")
    current_depth: int = Field(..., description="Current recursion depth")
    total_iterations: int = Field(..., description="Total iterations executed")
    result: Optional[Dict[str, Any]] = Field(None, description="Final result")
    termination_type: Optional[TerminationTypeEnum] = Field(
        None, description="How recursion terminated"
    )
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    memoization_hits: int = Field(0, description="Cache hits from memoization")


class RecursionStatusResponse(BaseModel):
    """Response schema for recursion status queries."""

    execution_id: UUID = Field(..., description="Execution ID")
    status: ExecutionStatusEnum = Field(..., description="Current status")
    current_depth: int = Field(..., description="Current depth")
    max_depth: int = Field(..., description="Maximum depth")
    iteration_count: int = Field(..., description="Current iteration count")
    max_iterations: int = Field(..., description="Maximum iterations")
    elapsed_seconds: float = Field(..., description="Elapsed time")
    memoization_stats: Dict[str, int] = Field(..., description="Memoization statistics")


# =============================================================================
# Composition Schemas
# =============================================================================


class CompositionNodeCreate(BaseModel):
    """Schema for creating a composition node."""

    node_id: Optional[str] = Field(None, description="Optional node identifier")
    workflow_id: UUID = Field(..., description="Workflow ID for this node")
    inputs: Dict[str, Any] = Field(
        default_factory=dict, description="Node inputs"
    )
    condition: Optional[str] = Field(
        None, description="Condition expression for conditional nodes"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Node metadata"
    )


class CompositionBlockCreate(BaseModel):
    """Schema for creating a composition block."""

    block_id: Optional[str] = Field(None, description="Optional block identifier")
    composition_type: CompositionTypeEnum = Field(
        ..., description="Type of composition"
    )
    nodes: List[CompositionNodeCreate] = Field(
        default_factory=list, description="Nodes in this block"
    )
    loop_condition: Optional[str] = Field(
        None, description="Loop condition (for LOOP type)"
    )
    max_iterations: int = Field(
        100, ge=1, le=10000, description="Max iterations for loops"
    )
    switch_expression: Optional[str] = Field(
        None, description="Switch expression (for SWITCH type)"
    )
    case_mappings: Optional[Dict[str, str]] = Field(
        None, description="Case mappings for switch"
    )


class CompositionCreateRequest(BaseModel):
    """Request schema for creating a workflow composition."""

    name: str = Field(..., min_length=1, max_length=100, description="Composition name")
    description: Optional[str] = Field(None, description="Description")
    blocks: List[CompositionBlockCreate] = Field(
        ..., description="Composition blocks"
    )
    template_name: Optional[str] = Field(
        None, description="Optional template name (map_reduce, pipeline, etc.)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "data_pipeline",
                "description": "Sequential data processing pipeline",
                "blocks": [
                    {
                        "composition_type": "sequence",
                        "nodes": [
                            {"workflow_id": "550e8400-e29b-41d4-a716-446655440000"},
                            {"workflow_id": "550e8400-e29b-41d4-a716-446655440001"},
                        ],
                    }
                ],
            }
        }


class CompositionResponse(BaseModel):
    """Response schema for composition operations."""

    composition_id: UUID = Field(..., description="Composition ID")
    name: str = Field(..., description="Composition name")
    description: Optional[str] = Field(None, description="Description")
    block_count: int = Field(..., description="Number of blocks")
    node_count: int = Field(..., description="Total number of nodes")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class CompositionExecuteRequest(BaseModel):
    """Request schema for executing a composition."""

    composition_id: UUID = Field(..., description="Composition ID to execute")
    inputs: Dict[str, Any] = Field(
        default_factory=dict, description="Initial inputs"
    )
    timeout_seconds: int = Field(
        600, ge=1, le=7200, description="Execution timeout"
    )
    fail_fast: bool = Field(
        False, description="Stop on first failure"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "composition_id": "550e8400-e29b-41d4-a716-446655440000",
                "inputs": {"data": "input value"},
                "timeout_seconds": 300,
                "fail_fast": True,
            }
        }


class CompositionExecuteResponse(BaseModel):
    """Response schema for composition execution."""

    execution_id: UUID = Field(..., description="Execution ID")
    composition_id: UUID = Field(..., description="Composition ID")
    status: ExecutionStatusEnum = Field(..., description="Current status")
    completed_blocks: int = Field(..., description="Completed blocks")
    total_blocks: int = Field(..., description="Total blocks")
    result: Optional[Dict[str, Any]] = Field(None, description="Final result")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")


# =============================================================================
# Context Propagation Schemas
# =============================================================================


class ContextPropagateRequest(BaseModel):
    """Request schema for context propagation."""

    source_workflow_id: UUID = Field(..., description="Source workflow ID")
    target_workflow_id: UUID = Field(..., description="Target workflow ID")
    context: Dict[str, Any] = Field(..., description="Context to propagate")
    propagation_type: PropagationTypeEnum = Field(
        PropagationTypeEnum.COPY, description="Propagation type"
    )
    filter_keys: Optional[List[str]] = Field(
        None, description="Keys to filter (for FILTER type)"
    )
    key_mappings: Optional[Dict[str, str]] = Field(
        None, description="Key name mappings"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "target_workflow_id": "550e8400-e29b-41d4-a716-446655440001",
                "context": {"user_id": "123", "data": {"key": "value"}},
                "propagation_type": "copy",
            }
        }


class ContextPropagateResponse(BaseModel):
    """Response schema for context propagation."""

    source_workflow_id: UUID = Field(..., description="Source workflow ID")
    target_workflow_id: UUID = Field(..., description="Target workflow ID")
    propagation_type: PropagationTypeEnum = Field(..., description="Propagation type")
    keys_propagated: List[str] = Field(..., description="Keys that were propagated")
    propagated_at: datetime = Field(..., description="Propagation timestamp")


class DataFlowEventResponse(BaseModel):
    """Response schema for data flow events."""

    event_id: UUID = Field(..., description="Event ID")
    timestamp: datetime = Field(..., description="Event timestamp")
    source_workflow_id: UUID = Field(..., description="Source workflow")
    target_workflow_id: UUID = Field(..., description="Target workflow")
    variable_name: str = Field(..., description="Variable name")
    direction: str = Field(..., description="Flow direction")
    propagation_type: PropagationTypeEnum = Field(..., description="Propagation type")


class DataFlowTrackerResponse(BaseModel):
    """Response schema for data flow tracker statistics."""

    total_events: int = Field(..., description="Total tracked events")
    unique_workflows: int = Field(..., description="Unique workflows")
    unique_variables: int = Field(..., description="Unique variables")
    by_direction: Dict[str, int] = Field(..., description="Events by direction")
    by_propagation_type: Dict[str, int] = Field(..., description="Events by type")
    top_variables: List[List[Union[str, int]]] = Field(
        ..., description="Most propagated variables"
    )


# =============================================================================
# Statistics Schemas
# =============================================================================


class NestedWorkflowStatsResponse(BaseModel):
    """Response schema for nested workflow statistics."""

    total_nested_configs: int = Field(..., description="Total nested configs")
    total_executions: int = Field(..., description="Total executions")
    active_executions: int = Field(..., description="Active executions")
    completed_executions: int = Field(..., description="Completed executions")
    failed_executions: int = Field(..., description="Failed executions")
    average_depth: float = Field(..., description="Average nesting depth")
    max_depth_reached: int = Field(..., description="Maximum depth reached")
    by_type: Dict[str, int] = Field(..., description="Executions by workflow type")
    by_scope: Dict[str, int] = Field(..., description="Executions by scope")

