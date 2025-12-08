# =============================================================================
# IPA Platform - Nested Workflow API Routes
# =============================================================================
# Sprint 11: S11-5 Nested Workflow API
# Sprint 23: 重構以使用 NestedWorkflowAdapter (Phase 4)
#
# REST API endpoints for nested workflow management.
# Provides:
#   - POST /nested/configs - Create nested workflow configuration
#   - GET /nested/configs - List nested workflow configurations
#   - GET /nested/configs/{id} - Get specific configuration
#   - DELETE /nested/configs/{id} - Delete configuration
#   - POST /nested/sub-workflows/execute - Execute sub-workflow
#   - POST /nested/sub-workflows/batch - Batch execute sub-workflows
#   - GET /nested/sub-workflows/{id}/status - Get sub-workflow status
#   - POST /nested/sub-workflows/{id}/cancel - Cancel sub-workflow
#   - POST /nested/recursive/execute - Execute recursive workflow
#   - GET /nested/recursive/{id}/status - Get recursion status
#   - POST /nested/compositions - Create composition
#   - POST /nested/compositions/execute - Execute composition
#   - POST /nested/context/propagate - Propagate context
#   - GET /nested/context/flow/{id} - Get data flow events
#   - GET /nested/stats - Get nested workflow statistics
#
# Phase 4 Migration:
#   使用 NestedWorkflowAdapter 替代 domain 層實現
#   保留 API 相容性，內部邏輯使用適配器
# =============================================================================

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.v1.nested.schemas import (
    CompositionCreateRequest,
    CompositionExecuteRequest,
    CompositionExecuteResponse,
    CompositionResponse,
    CompositionTypeEnum,
    ContextPropagateRequest,
    ContextPropagateResponse,
    DataFlowEventResponse,
    DataFlowTrackerResponse,
    ExecutionStatusEnum,
    NestedWorkflowCreate,
    NestedWorkflowListResponse,
    NestedWorkflowResponse,
    NestedWorkflowStatsResponse,
    NestedWorkflowTypeEnum,
    PropagationTypeEnum,
    RecursionStatusResponse,
    RecursionStrategyEnum,
    RecursiveExecuteRequest,
    RecursiveExecuteResponse,
    SubWorkflowBatchRequest,
    SubWorkflowBatchResponse,
    SubWorkflowExecuteRequest,
    SubWorkflowExecuteResponse,
    SubWorkflowExecutionModeEnum,
    TerminationTypeEnum,
    WorkflowScopeEnum,
)

# =============================================================================
# Sprint 23: 使用適配器層替代 domain 層
# =============================================================================
from src.integrations.agent_framework.builders.nested_workflow import (
    NestedWorkflowAdapter,
    ContextPropagationStrategy,
    ExecutionMode,
    RecursionStatus,
    ContextConfig,
    RecursionConfig,
    RecursionState,
    SubWorkflowInfo,
    NestedExecutionResult,
    ContextPropagator,
    RecursiveDepthController,
    create_nested_workflow_adapter,
    create_sequential_nested_workflow,
    create_parallel_nested_workflow,
)

# Sprint 25: 保留 domain 層導入
# 這些類提供擴展功能，由適配器包裝使用
# 注意: 這些是保留的擴展功能，不是棄用代碼
from src.domain.orchestration.nested import (
    CompositionType,
    DataFlowTracker,
    NestedWorkflowConfig,
    NestedWorkflowManager,
    NestedWorkflowType,
    PropagationType,
    RecursionStrategy,
    RecursivePatternHandler,
    SubWorkflowExecutionMode,
    SubWorkflowExecutor,
    TerminationType,
    WorkflowCompositionBuilder,
    WorkflowScope,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/nested",
    tags=["nested"],
    responses={
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Global Instances (to be replaced with proper DI)
# Sprint 23: 添加 NestedWorkflowAdapter 實例
# =============================================================================


# 新適配器實例 (Sprint 23)
_nested_adapters: Dict[UUID, NestedWorkflowAdapter] = {}
_adapter_context_propagator: Optional[ContextPropagator] = None
_adapter_depth_controller: Optional[RecursiveDepthController] = None

# 舊 domain 層實例 (標記為 Deprecated，將在 Sprint 25 移除)
_nested_manager: Optional[NestedWorkflowManager] = None
_sub_executor: Optional[SubWorkflowExecutor] = None
_recursive_handler: Optional[RecursivePatternHandler] = None
_composition_builder: Optional[WorkflowCompositionBuilder] = None
_context_propagator_legacy: Optional[Any] = None  # 使用 domain 層的 ContextPropagator
_data_flow_tracker: Optional[DataFlowTracker] = None


# =============================================================================
# Sprint 23: 新適配器依賴函數
# =============================================================================


def get_nested_adapter(adapter_id: str = "default") -> NestedWorkflowAdapter:
    """
    獲取或創建 NestedWorkflowAdapter。

    Sprint 23: 新的依賴注入函數，使用適配器層。

    Args:
        adapter_id: 適配器 ID

    Returns:
        NestedWorkflowAdapter 實例
    """
    global _nested_adapters
    key = UUID(adapter_id) if adapter_id != "default" else uuid4()

    if key not in _nested_adapters:
        _nested_adapters[key] = create_nested_workflow_adapter(
            id=str(key),
            max_depth=10,
            context_strategy=ContextPropagationStrategy.INHERITED,
        )
    return _nested_adapters[key]


def get_adapter_context_propagator() -> ContextPropagator:
    """
    獲取適配器的上下文傳播器。

    Sprint 23: 使用新適配器層的 ContextPropagator。

    Returns:
        ContextPropagator 實例
    """
    global _adapter_context_propagator
    if _adapter_context_propagator is None:
        config = ContextConfig(strategy=ContextPropagationStrategy.INHERITED)
        _adapter_context_propagator = ContextPropagator(config)
    return _adapter_context_propagator


def get_adapter_depth_controller() -> RecursiveDepthController:
    """
    獲取適配器的遞歸深度控制器。

    Sprint 23: 使用新適配器層的 RecursiveDepthController。

    Returns:
        RecursiveDepthController 實例
    """
    global _adapter_depth_controller
    if _adapter_depth_controller is None:
        config = RecursionConfig(max_depth=10, timeout_seconds=300.0)
        _adapter_depth_controller = RecursiveDepthController(config)
    return _adapter_depth_controller


# =============================================================================
# 舊依賴函數 (標記為 Deprecated)
# =============================================================================


def get_nested_manager() -> NestedWorkflowManager:
    """
    Get or create nested workflow manager.

    Deprecated: 將在 Sprint 25 移除，請使用 get_nested_adapter()
    """
    global _nested_manager
    if _nested_manager is None:
        _nested_manager = NestedWorkflowManager()
    return _nested_manager


def get_sub_executor() -> SubWorkflowExecutor:
    """
    Get or create sub-workflow executor.

    Deprecated: 將在 Sprint 25 移除，請使用 NestedWorkflowAdapter.run()
    """
    global _sub_executor
    if _sub_executor is None:
        _sub_executor = SubWorkflowExecutor()
    return _sub_executor


def get_recursive_handler() -> RecursivePatternHandler:
    """
    Get or create recursive pattern handler.

    Deprecated: 將在 Sprint 25 移除，請使用 NestedWorkflowAdapter 的遞歸控制
    """
    global _recursive_handler
    if _recursive_handler is None:
        _recursive_handler = RecursivePatternHandler()
    return _recursive_handler


def get_composition_builder() -> WorkflowCompositionBuilder:
    """
    Get or create composition builder.

    Deprecated: 將在 Sprint 25 移除，請使用 NestedWorkflowAdapter 的組合功能
    """
    global _composition_builder
    if _composition_builder is None:
        _composition_builder = WorkflowCompositionBuilder()
    return _composition_builder


def get_context_propagator() -> Any:
    """
    Get or create context propagator.

    Deprecated: 將在 Sprint 25 移除，請使用 get_adapter_context_propagator()
    """
    global _context_propagator_legacy
    # 使用新的適配器層
    return get_adapter_context_propagator()


def get_data_flow_tracker() -> DataFlowTracker:
    """
    Get or create data flow tracker.

    Deprecated: 將在 Sprint 25 整合到適配器層
    """
    global _data_flow_tracker
    if _data_flow_tracker is None:
        _data_flow_tracker = DataFlowTracker()
    return _data_flow_tracker


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_workflow_type(wf_type: NestedWorkflowTypeEnum) -> NestedWorkflowType:
    """Convert API enum to domain enum."""
    mapping = {
        NestedWorkflowTypeEnum.INLINE: NestedWorkflowType.INLINE,
        NestedWorkflowTypeEnum.REFERENCE: NestedWorkflowType.REFERENCE,
        NestedWorkflowTypeEnum.DYNAMIC: NestedWorkflowType.DYNAMIC,
        NestedWorkflowTypeEnum.RECURSIVE: NestedWorkflowType.RECURSIVE,
    }
    return mapping.get(wf_type, NestedWorkflowType.REFERENCE)


def _convert_scope(scope: WorkflowScopeEnum) -> WorkflowScope:
    """Convert API enum to domain enum."""
    mapping = {
        WorkflowScopeEnum.ISOLATED: WorkflowScope.ISOLATED,
        WorkflowScopeEnum.INHERITED: WorkflowScope.INHERITED,
        WorkflowScopeEnum.SHARED: WorkflowScope.SHARED,
    }
    return mapping.get(scope, WorkflowScope.INHERITED)


def _convert_execution_mode(mode: SubWorkflowExecutionModeEnum) -> SubWorkflowExecutionMode:
    """Convert API enum to domain enum."""
    mapping = {
        SubWorkflowExecutionModeEnum.SYNC: SubWorkflowExecutionMode.SYNC,
        SubWorkflowExecutionModeEnum.ASYNC: SubWorkflowExecutionMode.ASYNC,
        SubWorkflowExecutionModeEnum.FIRE_AND_FORGET: SubWorkflowExecutionMode.FIRE_AND_FORGET,
        SubWorkflowExecutionModeEnum.CALLBACK: SubWorkflowExecutionMode.CALLBACK,
    }
    return mapping.get(mode, SubWorkflowExecutionMode.SYNC)


def _convert_recursion_strategy(strategy: RecursionStrategyEnum) -> RecursionStrategy:
    """Convert API enum to domain enum."""
    mapping = {
        RecursionStrategyEnum.DEPTH_FIRST: RecursionStrategy.DEPTH_FIRST,
        RecursionStrategyEnum.BREADTH_FIRST: RecursionStrategy.BREADTH_FIRST,
        RecursionStrategyEnum.PARALLEL: RecursionStrategy.PARALLEL,
    }
    return mapping.get(strategy, RecursionStrategy.DEPTH_FIRST)


def _convert_composition_type(comp_type: CompositionTypeEnum) -> CompositionType:
    """Convert API enum to domain enum."""
    mapping = {
        CompositionTypeEnum.SEQUENCE: CompositionType.SEQUENCE,
        CompositionTypeEnum.PARALLEL: CompositionType.PARALLEL,
        CompositionTypeEnum.CONDITIONAL: CompositionType.CONDITIONAL,
        CompositionTypeEnum.LOOP: CompositionType.LOOP,
        CompositionTypeEnum.SWITCH: CompositionType.SWITCH,
    }
    return mapping.get(comp_type, CompositionType.SEQUENCE)


def _convert_propagation_type(prop_type: PropagationTypeEnum) -> PropagationType:
    """Convert API enum to domain enum."""
    mapping = {
        PropagationTypeEnum.COPY: PropagationType.COPY,
        PropagationTypeEnum.REFERENCE: PropagationType.REFERENCE,
        PropagationTypeEnum.MERGE: PropagationType.MERGE,
        PropagationTypeEnum.FILTER: PropagationType.FILTER,
    }
    return mapping.get(prop_type, PropagationType.COPY)


def _convert_status_to_enum(status: str) -> ExecutionStatusEnum:
    """Convert status string to API enum."""
    mapping = {
        "pending": ExecutionStatusEnum.PENDING,
        "running": ExecutionStatusEnum.RUNNING,
        "completed": ExecutionStatusEnum.COMPLETED,
        "failed": ExecutionStatusEnum.FAILED,
        "cancelled": ExecutionStatusEnum.CANCELLED,
        "timeout": ExecutionStatusEnum.TIMEOUT,
    }


# =============================================================================
# Sprint 23: 適配器層轉換函數
# =============================================================================


def _convert_scope_to_adapter(scope: WorkflowScopeEnum) -> ContextPropagationStrategy:
    """
    Convert API scope enum to adapter context strategy.

    Sprint 23: 將 API 層的 WorkflowScope 轉換為適配器層的 ContextPropagationStrategy。
    """
    mapping = {
        WorkflowScopeEnum.ISOLATED: ContextPropagationStrategy.ISOLATED,
        WorkflowScopeEnum.INHERITED: ContextPropagationStrategy.INHERITED,
        WorkflowScopeEnum.SHARED: ContextPropagationStrategy.MERGED,
    }
    return mapping.get(scope, ContextPropagationStrategy.INHERITED)


def _convert_propagation_to_adapter(prop_type: PropagationTypeEnum) -> ContextPropagationStrategy:
    """
    Convert API propagation type to adapter context strategy.

    Sprint 23: 將 API 層的 PropagationType 轉換為適配器層的 ContextPropagationStrategy。
    """
    mapping = {
        PropagationTypeEnum.COPY: ContextPropagationStrategy.INHERITED,
        PropagationTypeEnum.REFERENCE: ContextPropagationStrategy.INHERITED,  # 不支持 REFERENCE
        PropagationTypeEnum.MERGE: ContextPropagationStrategy.MERGED,
        PropagationTypeEnum.FILTER: ContextPropagationStrategy.FILTERED,
    }
    return mapping.get(prop_type, ContextPropagationStrategy.INHERITED)


def _convert_composition_to_execution_mode(comp_type: CompositionTypeEnum) -> ExecutionMode:
    """
    Convert API composition type to adapter execution mode.

    Sprint 23: 將 API 層的 CompositionType 轉換為適配器層的 ExecutionMode。
    """
    mapping = {
        CompositionTypeEnum.SEQUENCE: ExecutionMode.SEQUENTIAL,
        CompositionTypeEnum.PARALLEL: ExecutionMode.PARALLEL,
        CompositionTypeEnum.CONDITIONAL: ExecutionMode.CONDITIONAL,
        CompositionTypeEnum.LOOP: ExecutionMode.SEQUENTIAL,  # 使用遞歸處理
        CompositionTypeEnum.SWITCH: ExecutionMode.CONDITIONAL,
    }
    return mapping.get(comp_type, ExecutionMode.SEQUENTIAL)


def _convert_recursion_status_to_enum(status: RecursionStatus) -> ExecutionStatusEnum:
    """
    Convert adapter recursion status to API execution status.

    Sprint 23: 將適配器層的 RecursionStatus 轉換為 API 層的 ExecutionStatusEnum。
    """
    mapping = {
        RecursionStatus.PENDING: ExecutionStatusEnum.PENDING,
        RecursionStatus.RUNNING: ExecutionStatusEnum.RUNNING,
        RecursionStatus.COMPLETED: ExecutionStatusEnum.COMPLETED,
        RecursionStatus.FAILED: ExecutionStatusEnum.FAILED,
        RecursionStatus.DEPTH_EXCEEDED: ExecutionStatusEnum.FAILED,
        RecursionStatus.TIMEOUT: ExecutionStatusEnum.TIMEOUT,
    }
    return mapping.get(status, ExecutionStatusEnum.PENDING)


# =============================================================================
# Nested Workflow Configuration Endpoints
# =============================================================================


@router.post(
    "/configs",
    response_model=NestedWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create nested workflow configuration",
    description="Register a new nested workflow configuration",
)
async def create_nested_config(
    request: NestedWorkflowCreate,
    manager: NestedWorkflowManager = Depends(get_nested_manager),
) -> NestedWorkflowResponse:
    """Create a new nested workflow configuration."""
    try:
        config = NestedWorkflowConfig(
            parent_workflow_id=request.parent_workflow_id,
            workflow_type=_convert_workflow_type(request.workflow_type),
            scope=_convert_scope(request.scope),
            max_depth=request.max_depth,
            timeout_seconds=request.timeout_seconds,
            metadata=request.metadata or {},
        )

        result = await manager.register_nested_workflow(
            parent_workflow_id=request.parent_workflow_id,
            sub_workflow_id=request.sub_workflow_id,
            config=config,
        )

        return NestedWorkflowResponse(
            config_id=config.config_id,
            parent_workflow_id=request.parent_workflow_id,
            name=request.name,
            workflow_type=request.workflow_type,
            scope=request.scope,
            sub_workflow_id=request.sub_workflow_id,
            max_depth=request.max_depth,
            timeout_seconds=request.timeout_seconds,
            created_at=datetime.utcnow(),
            metadata=request.metadata or {},
        )

    except Exception as e:
        logger.error(f"Failed to create nested config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create nested configuration: {str(e)}",
        )


@router.get(
    "/configs",
    response_model=NestedWorkflowListResponse,
    summary="List nested workflow configurations",
    description="Get all nested workflow configurations with pagination",
)
async def list_nested_configs(
    parent_workflow_id: Optional[UUID] = Query(None, description="Filter by parent"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    manager: NestedWorkflowManager = Depends(get_nested_manager),
) -> NestedWorkflowListResponse:
    """List nested workflow configurations."""
    try:
        # Get all configurations
        all_configs = manager._configs

        # Filter by parent if specified
        if parent_workflow_id:
            filtered = {
                k: v for k, v in all_configs.items()
                if v.parent_workflow_id == parent_workflow_id
            }
        else:
            filtered = all_configs

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size

        items = []
        for config in list(filtered.values())[start:end]:
            items.append(NestedWorkflowResponse(
                config_id=config.config_id,
                parent_workflow_id=config.parent_workflow_id,
                name=f"nested_{config.config_id}",
                workflow_type=NestedWorkflowTypeEnum(config.workflow_type.value),
                scope=WorkflowScopeEnum(config.scope.value),
                sub_workflow_id=None,
                max_depth=config.max_depth,
                timeout_seconds=config.timeout_seconds,
                created_at=datetime.utcnow(),
                metadata=config.metadata,
            ))

        return NestedWorkflowListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Failed to list nested configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/configs/{config_id}",
    response_model=NestedWorkflowResponse,
    summary="Get nested workflow configuration",
    description="Get a specific nested workflow configuration by ID",
)
async def get_nested_config(
    config_id: UUID,
    manager: NestedWorkflowManager = Depends(get_nested_manager),
) -> NestedWorkflowResponse:
    """Get a specific nested workflow configuration."""
    config = manager._configs.get(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )

    return NestedWorkflowResponse(
        config_id=config.config_id,
        parent_workflow_id=config.parent_workflow_id,
        name=f"nested_{config.config_id}",
        workflow_type=NestedWorkflowTypeEnum(config.workflow_type.value),
        scope=WorkflowScopeEnum(config.scope.value),
        sub_workflow_id=None,
        max_depth=config.max_depth,
        timeout_seconds=config.timeout_seconds,
        created_at=datetime.utcnow(),
        metadata=config.metadata,
    )


@router.delete(
    "/configs/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete nested workflow configuration",
    description="Delete a nested workflow configuration",
)
async def delete_nested_config(
    config_id: UUID,
    manager: NestedWorkflowManager = Depends(get_nested_manager),
) -> None:
    """Delete a nested workflow configuration."""
    if config_id not in manager._configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )

    del manager._configs[config_id]
    logger.info(f"Deleted nested config: {config_id}")


# =============================================================================
# Sub-Workflow Execution Endpoints
# =============================================================================


@router.post(
    "/sub-workflows/execute",
    response_model=SubWorkflowExecuteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute sub-workflow",
    description="Execute a sub-workflow with specified mode",
)
async def execute_sub_workflow(
    request: SubWorkflowExecuteRequest,
    executor: SubWorkflowExecutor = Depends(get_sub_executor),
) -> SubWorkflowExecuteResponse:
    """Execute a sub-workflow."""
    try:
        mode = _convert_execution_mode(request.mode)

        result = await executor.execute(
            sub_workflow_id=request.sub_workflow_id,
            inputs=request.inputs,
            mode=mode,
            timeout=request.timeout_seconds,
            metadata=request.metadata,
        )

        # For sync mode, result is the actual execution result
        if request.mode == SubWorkflowExecutionModeEnum.SYNC:
            return SubWorkflowExecuteResponse(
                execution_id=UUID(result.get("execution_id", str(uuid4()))) if isinstance(result.get("execution_id"), str) else uuid4(),
                sub_workflow_id=request.sub_workflow_id,
                mode=request.mode,
                status=ExecutionStatusEnum.COMPLETED,
                result=result,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
        else:
            # For async modes, result contains execution info
            return SubWorkflowExecuteResponse(
                execution_id=UUID(result.get("execution_id", str(uuid4()))),
                sub_workflow_id=request.sub_workflow_id,
                mode=request.mode,
                status=_convert_status_to_enum(result.get("status", "pending")),
                result=None,
                started_at=datetime.utcnow(),
            )

    except Exception as e:
        logger.error(f"Failed to execute sub-workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute sub-workflow: {str(e)}",
        )


@router.post(
    "/sub-workflows/batch",
    response_model=SubWorkflowBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch execute sub-workflows",
    description="Execute multiple sub-workflows in parallel or sequence",
)
async def batch_execute_sub_workflows(
    request: SubWorkflowBatchRequest,
    executor: SubWorkflowExecutor = Depends(get_sub_executor),
) -> SubWorkflowBatchResponse:
    """Execute multiple sub-workflows."""
    try:
        batch_id = uuid4()

        if request.parallel:
            results = await executor.execute_parallel(
                sub_workflows=request.sub_workflows,
                timeout=request.timeout_seconds,
            )
        else:
            results = await executor.execute_sequential(
                sub_workflows=request.sub_workflows,
                pass_outputs=request.pass_outputs,
                stop_on_error=request.stop_on_error,
                timeout=request.timeout_seconds,
            )

        completed = sum(1 for r in results if r.get("status") != "failed")
        failed = len(results) - completed

        return SubWorkflowBatchResponse(
            batch_id=batch_id,
            total_workflows=len(request.sub_workflows),
            completed=completed,
            failed=failed,
            results=results,
            status=ExecutionStatusEnum.COMPLETED if failed == 0 else ExecutionStatusEnum.FAILED,
        )

    except Exception as e:
        logger.error(f"Failed to batch execute: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/sub-workflows/{execution_id}/status",
    response_model=SubWorkflowExecuteResponse,
    summary="Get sub-workflow status",
    description="Get the status of a sub-workflow execution",
)
async def get_sub_workflow_status(
    execution_id: UUID,
    executor: SubWorkflowExecutor = Depends(get_sub_executor),
) -> SubWorkflowExecuteResponse:
    """Get sub-workflow execution status."""
    try:
        result = await executor.get_execution_status(execution_id)

        if "error" in result and result.get("error") == "Execution not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        return SubWorkflowExecuteResponse(
            execution_id=UUID(result.get("execution_id", str(execution_id))),
            sub_workflow_id=UUID(result.get("sub_workflow_id", str(uuid4()))),
            mode=SubWorkflowExecutionModeEnum(result.get("mode", "sync")),
            status=_convert_status_to_enum(result.get("status", "pending")),
            result=result.get("result"),
            error=result.get("error"),
            started_at=datetime.fromisoformat(result["started_at"]) if result.get("started_at") else None,
            completed_at=datetime.fromisoformat(result["completed_at"]) if result.get("completed_at") else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/sub-workflows/{execution_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel sub-workflow",
    description="Cancel a running sub-workflow execution",
)
async def cancel_sub_workflow(
    execution_id: UUID,
    executor: SubWorkflowExecutor = Depends(get_sub_executor),
) -> dict:
    """Cancel a sub-workflow execution."""
    try:
        success = await executor.cancel_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found or not cancellable",
            )

        return {"message": "Execution cancelled", "execution_id": str(execution_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Recursive Execution Endpoints
# =============================================================================


@router.post(
    "/recursive/execute",
    response_model=RecursiveExecuteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute recursive workflow",
    description="Execute a workflow recursively with specified strategy",
)
async def execute_recursive(
    request: RecursiveExecuteRequest,
    handler: RecursivePatternHandler = Depends(get_recursive_handler),
) -> RecursiveExecuteResponse:
    """Execute a workflow recursively."""
    try:
        strategy = _convert_recursion_strategy(request.strategy)

        config = RecursionConfig(
            workflow_id=request.workflow_id,
            strategy=strategy,
            max_depth=request.max_depth,
            max_iterations=request.max_iterations,
            timeout_seconds=request.timeout_seconds,
            enable_memoization=request.enable_memoization,
        )

        result = await handler.execute(
            config=config,
            initial_inputs=request.inputs,
        )

        state = handler.get_execution_state(result.get("execution_id"))

        return RecursiveExecuteResponse(
            execution_id=UUID(result.get("execution_id", str(uuid4()))),
            workflow_id=request.workflow_id,
            strategy=request.strategy,
            status=_convert_status_to_enum(result.get("status", "completed")),
            current_depth=state.current_depth if state else 0,
            total_iterations=state.iteration_count if state else 0,
            result=result.get("result"),
            termination_type=TerminationTypeEnum(result.get("termination_type", "max_iterations")) if result.get("termination_type") else None,
            started_at=state.started_at if state else datetime.utcnow(),
            completed_at=state.completed_at if state else None,
            memoization_hits=state.memoization_hits if state else 0,
        )

    except Exception as e:
        logger.error(f"Failed to execute recursive: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/recursive/{execution_id}/status",
    response_model=RecursionStatusResponse,
    summary="Get recursion status",
    description="Get the status of a recursive execution",
)
async def get_recursion_status(
    execution_id: UUID,
    handler: RecursivePatternHandler = Depends(get_recursive_handler),
) -> RecursionStatusResponse:
    """Get recursive execution status."""
    state = handler.get_execution_state(execution_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found",
        )

    elapsed = 0.0
    if state.started_at:
        end_time = state.completed_at or datetime.utcnow()
        elapsed = (end_time - state.started_at).total_seconds()

    return RecursionStatusResponse(
        execution_id=execution_id,
        status=_convert_status_to_enum(state.status),
        current_depth=state.current_depth,
        max_depth=state.max_depth,
        iteration_count=state.iteration_count,
        max_iterations=state.max_iterations,
        elapsed_seconds=elapsed,
        memoization_stats={
            "hits": state.memoization_hits,
            "cache_size": len(state.memoization_cache),
        },
    )


# =============================================================================
# Composition Endpoints
# =============================================================================


@router.post(
    "/compositions",
    response_model=CompositionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow composition",
    description="Create a new workflow composition",
)
async def create_composition(
    request: CompositionCreateRequest,
    builder: WorkflowCompositionBuilder = Depends(get_composition_builder),
) -> CompositionResponse:
    """Create a workflow composition."""
    try:
        composition_id = uuid4()

        # Build composition from request
        for block in request.blocks:
            comp_type = _convert_composition_type(block.composition_type)

            if comp_type == CompositionType.SEQUENCE:
                builder.sequence()
            elif comp_type == CompositionType.PARALLEL:
                builder.parallel()
            elif comp_type == CompositionType.CONDITIONAL:
                builder.conditional(block.nodes[0].condition if block.nodes else "true")
            elif comp_type == CompositionType.LOOP:
                builder.loop(block.loop_condition or "false", block.max_iterations)
            elif comp_type == CompositionType.SWITCH:
                builder.switch(block.switch_expression or "default")

            for node in block.nodes:
                builder.add_workflow(node.workflow_id, node.inputs)

            builder.end()

        node_count = sum(len(b.nodes) for b in request.blocks)

        return CompositionResponse(
            composition_id=composition_id,
            name=request.name,
            description=request.description,
            block_count=len(request.blocks),
            node_count=node_count,
            created_at=datetime.utcnow(),
            metadata=request.metadata or {},
        )

    except Exception as e:
        logger.error(f"Failed to create composition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/compositions/execute",
    response_model=CompositionExecuteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute workflow composition",
    description="Execute a workflow composition",
)
async def execute_composition(
    request: CompositionExecuteRequest,
    builder: WorkflowCompositionBuilder = Depends(get_composition_builder),
) -> CompositionExecuteResponse:
    """Execute a workflow composition."""
    try:
        execution_id = uuid4()

        result = await builder.execute(
            inputs=request.inputs,
            timeout=request.timeout_seconds,
        )

        return CompositionExecuteResponse(
            execution_id=execution_id,
            composition_id=request.composition_id,
            status=ExecutionStatusEnum.COMPLETED if result.get("status") != "failed" else ExecutionStatusEnum.FAILED,
            completed_blocks=result.get("completed_blocks", 0),
            total_blocks=result.get("total_blocks", 0),
            result=result,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to execute composition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Context Propagation Endpoints
# =============================================================================


@router.post(
    "/context/propagate",
    response_model=ContextPropagateResponse,
    status_code=status.HTTP_200_OK,
    summary="Propagate context",
    description="Propagate context between workflows",
)
async def propagate_context(
    request: ContextPropagateRequest,
    propagator: ContextPropagator = Depends(get_context_propagator),
    tracker: DataFlowTracker = Depends(get_data_flow_tracker),
) -> ContextPropagateResponse:
    """Propagate context between workflows."""
    try:
        prop_type = _convert_propagation_type(request.propagation_type)

        # Apply key mappings if provided
        if request.key_mappings:
            for src, tgt in request.key_mappings.items():
                propagator.map_key(src, tgt)

        # Propagate context
        filter_keys_set: Optional[Set[str]] = None
        if request.filter_keys:
            filter_keys_set = set(request.filter_keys)

        result = propagator.propagate_downstream(
            parent_context=request.context,
            propagation_type=prop_type,
            filter_keys=filter_keys_set,
        )

        # Track the flow
        for key in result.keys():
            tracker.record_flow(
                source_workflow_id=request.source_workflow_id,
                target_workflow_id=request.target_workflow_id,
                variable_name=key,
                old_value=None,
                new_value=result.get(key),
                direction=tracker._events[0].direction if tracker._events else None,
                propagation_type=prop_type,
            )

        return ContextPropagateResponse(
            source_workflow_id=request.source_workflow_id,
            target_workflow_id=request.target_workflow_id,
            propagation_type=request.propagation_type,
            keys_propagated=list(result.keys()),
            propagated_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to propagate context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/context/flow/{workflow_id}",
    response_model=list[DataFlowEventResponse],
    summary="Get data flow events",
    description="Get data flow events for a workflow",
)
async def get_data_flow_events(
    workflow_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    tracker: DataFlowTracker = Depends(get_data_flow_tracker),
) -> list[DataFlowEventResponse]:
    """Get data flow events for a workflow."""
    try:
        events = tracker.get_events(workflow_id=workflow_id, limit=limit)

        return [
            DataFlowEventResponse(
                event_id=e.event_id,
                timestamp=e.timestamp,
                source_workflow_id=e.source_workflow_id,
                target_workflow_id=e.target_workflow_id,
                variable_name=e.variable_name,
                direction=e.direction.value if e.direction else "downstream",
                propagation_type=PropagationTypeEnum(e.propagation_type.value),
            )
            for e in events
        ]

    except Exception as e:
        logger.error(f"Failed to get flow events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/context/tracker/stats",
    response_model=DataFlowTrackerResponse,
    summary="Get data flow tracker statistics",
    description="Get statistics from the data flow tracker",
)
async def get_tracker_stats(
    tracker: DataFlowTracker = Depends(get_data_flow_tracker),
) -> DataFlowTrackerResponse:
    """Get data flow tracker statistics."""
    stats = tracker.get_statistics()

    return DataFlowTrackerResponse(
        total_events=stats["total_events"],
        unique_workflows=stats["unique_workflows"],
        unique_variables=stats["unique_variables"],
        by_direction=stats["by_direction"],
        by_propagation_type=stats["by_propagation_type"],
        top_variables=stats["top_variables"],
    )


# =============================================================================
# Statistics Endpoints
# =============================================================================


@router.get(
    "/stats",
    response_model=NestedWorkflowStatsResponse,
    summary="Get nested workflow statistics",
    description="Get overall statistics for nested workflows",
)
async def get_nested_stats(
    manager: NestedWorkflowManager = Depends(get_nested_manager),
    executor: SubWorkflowExecutor = Depends(get_sub_executor),
    handler: RecursivePatternHandler = Depends(get_recursive_handler),
) -> NestedWorkflowStatsResponse:
    """Get nested workflow statistics."""
    try:
        # Get manager stats
        manager_stats = manager.get_statistics()

        # Get executor stats
        executor_stats = executor.get_statistics()

        # Get handler stats
        handler_stats = handler.get_statistics()

        total_executions = executor_stats["total_executions"] + handler_stats["total_executions"]
        active = len(executor.get_active_executions())

        by_type = executor_stats.get("by_mode", {})
        by_scope = {}

        for config in manager._configs.values():
            scope_val = config.scope.value
            by_scope[scope_val] = by_scope.get(scope_val, 0) + 1

        return NestedWorkflowStatsResponse(
            total_nested_configs=manager_stats["total_configs"],
            total_executions=total_executions,
            active_executions=active,
            completed_executions=executor_stats.get("by_status", {}).get("completed", 0),
            failed_executions=executor_stats.get("by_status", {}).get("failed", 0),
            average_depth=manager_stats["average_depth"],
            max_depth_reached=manager_stats["max_depth_used"],
            by_type=by_type,
            by_scope=by_scope,
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

