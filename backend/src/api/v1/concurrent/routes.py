# =============================================================================
# IPA Platform - Concurrent Execution API Routes
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
# Sprint 14: ConcurrentBuilder 重構 (Phase 3 - P3-F1)
#
# REST API endpoints for concurrent execution management.
#
# Phase 2 Endpoints (Legacy):
#   - POST /concurrent/execute - Execute concurrent tasks
#   - GET /concurrent/{id}/status - Get execution status
#   - GET /concurrent/{id}/branches - Get all branch statuses
#   - POST /concurrent/{id}/cancel - Cancel entire execution
#   - POST /concurrent/{id}/branches/{bid}/cancel - Cancel specific branch
#   - GET /concurrent/stats - Get concurrent execution statistics
#
# Phase 3 Endpoints (Adapter-based):
#   - POST /concurrent/v2/execute - Execute with ConcurrentBuilderAdapter
#   - GET /concurrent/v2/{id} - Get execution details
#   - GET /concurrent/v2/stats - Get adapter statistics
#
# Migration Support:
#   - use_adapter query parameter to switch implementations
#   - Automatic fallback for compatibility
#
# All endpoints integrate with ConcurrentExecutor and StateManager.
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.v1.concurrent.schemas import (
    BranchCancelRequest,
    BranchCancelResponse,
    BranchInfo,
    BranchListResponse,
    BranchStatusEnum,
    BranchStatusResponse,
    ConcurrentExecuteRequest,
    ConcurrentExecuteResponse,
    ConcurrentModeEnum,
    ConcurrentStatsResponse,
    ExecutionCancelRequest,
    ExecutionCancelResponse,
    ExecutionStatusEnum,
    ExecutionStatusResponse,
)
from src.domain.workflows.executors import (
    ConcurrentExecutor,
    ConcurrentMode,
    ConcurrentStateManager,
    get_state_manager,
)
from src.domain.workflows.deadlock_detector import (
    DeadlockDetector,
    get_deadlock_detector,
)
# Sprint 14: Import adapter service
from src.api.v1.concurrent.adapter_service import (
    ConcurrentAPIService,
    ExecuteRequest as AdapterExecuteRequest,
    ExecuteResponse as AdapterExecuteResponse,
    get_concurrent_api_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/concurrent",
    tags=["concurrent"],
    responses={
        404: {"description": "Execution or branch not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_branch_status(status: str) -> BranchStatusEnum:
    """Convert internal branch status to API enum."""
    status_mapping = {
        "pending": BranchStatusEnum.PENDING,
        "running": BranchStatusEnum.RUNNING,
        "completed": BranchStatusEnum.COMPLETED,
        "failed": BranchStatusEnum.FAILED,
        "cancelled": BranchStatusEnum.CANCELLED,
        "timed_out": BranchStatusEnum.TIMED_OUT,
    }
    return status_mapping.get(status.lower(), BranchStatusEnum.PENDING)


def _convert_execution_status(status: str) -> ExecutionStatusEnum:
    """Convert internal execution status to API enum."""
    status_mapping = {
        "pending": ExecutionStatusEnum.PENDING,
        "running": ExecutionStatusEnum.RUNNING,
        "waiting": ExecutionStatusEnum.WAITING,
        "completed": ExecutionStatusEnum.COMPLETED,
        "failed": ExecutionStatusEnum.FAILED,
        "cancelled": ExecutionStatusEnum.CANCELLED,
        "timed_out": ExecutionStatusEnum.TIMED_OUT,
    }
    return status_mapping.get(status.lower(), ExecutionStatusEnum.PENDING)


def _convert_mode(mode: ConcurrentModeEnum) -> ConcurrentMode:
    """Convert API mode enum to internal ConcurrentMode."""
    mode_mapping = {
        ConcurrentModeEnum.ALL: ConcurrentMode.ALL,
        ConcurrentModeEnum.ANY: ConcurrentMode.ANY,
        ConcurrentModeEnum.MAJORITY: ConcurrentMode.MAJORITY,
        ConcurrentModeEnum.FIRST_SUCCESS: ConcurrentMode.FIRST_SUCCESS,
    }
    return mode_mapping.get(mode, ConcurrentMode.ALL)


# =============================================================================
# Dependencies
# =============================================================================


def get_concurrent_state_manager() -> ConcurrentStateManager:
    """Get concurrent state manager instance."""
    return get_state_manager()


def get_concurrent_deadlock_detector() -> DeadlockDetector:
    """Get deadlock detector instance."""
    return get_deadlock_detector()


# =============================================================================
# Execute Concurrent Tasks
# =============================================================================


@router.post(
    "/execute",
    response_model=ConcurrentExecuteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute concurrent tasks",
    description="Start a concurrent execution with Fork-Join pattern",
)
async def execute_concurrent(
    request: ConcurrentExecuteRequest,
    state_manager: ConcurrentStateManager = Depends(get_concurrent_state_manager),
) -> ConcurrentExecuteResponse:
    """
    Execute a workflow concurrently with multiple branches.

    Supports four execution modes:
    - ALL: Wait for all branches to complete
    - ANY: Return when any branch completes
    - MAJORITY: Wait for majority of branches
    - FIRST_SUCCESS: Return on first successful branch
    """
    try:
        execution_id = uuid4()
        created_at = datetime.utcnow()

        # Create execution state
        execution_state = state_manager.create_execution(
            execution_id=execution_id,
            mode=_convert_mode(request.mode),
            timeout=request.timeout_seconds or 300,
            max_concurrency=request.max_concurrency or 10,
        )

        # Initialize branches (in real implementation, this would be based on workflow)
        branches: list[BranchInfo] = []

        logger.info(
            f"Created concurrent execution {execution_id} "
            f"with mode={request.mode}, timeout={request.timeout_seconds}s"
        )

        return ConcurrentExecuteResponse(
            execution_id=execution_id,
            status=ExecutionStatusEnum.PENDING,
            mode=request.mode,
            branches=branches,
            created_at=created_at,
            timeout_seconds=request.timeout_seconds or 300,
            message=f"Concurrent execution created with mode={request.mode.value}",
        )

    except Exception as e:
        logger.error(f"Error creating concurrent execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create concurrent execution: {str(e)}",
        )


# =============================================================================
# Get Execution Status
# =============================================================================


@router.get(
    "/{execution_id}/status",
    response_model=ExecutionStatusResponse,
    summary="Get execution status",
    description="Get the current status of a concurrent execution",
)
async def get_execution_status(
    execution_id: UUID,
    state_manager: ConcurrentStateManager = Depends(get_concurrent_state_manager),
) -> ExecutionStatusResponse:
    """
    Get detailed status of a concurrent execution.

    Returns:
    - Overall execution status
    - Progress percentage
    - Branch completion counts
    - Individual branch details
    """
    try:
        execution_state = state_manager.get_execution(execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        # Calculate progress and counts
        branches = list(execution_state.branches.values())
        total_branches = len(branches)
        completed_branches = sum(1 for b in branches if b.is_terminal)
        failed_branches = sum(
            1 for b in branches if b.status.value == "failed"
        )
        running_branches = sum(
            1 for b in branches if b.status.value == "running"
        )

        progress = (
            (completed_branches / total_branches * 100)
            if total_branches > 0
            else 0.0
        )

        # Convert branches to BranchInfo
        branch_infos = [
            BranchInfo(
                branch_id=b.branch_id,
                status=_convert_branch_status(b.status.value),
                started_at=b.started_at,
                completed_at=b.completed_at,
                duration_ms=(
                    (b.completed_at - b.started_at).total_seconds() * 1000
                    if b.started_at and b.completed_at
                    else None
                ),
                result=b.result,
                error=b.error,
            )
            for b in branches
        ]

        # Determine overall status
        if execution_state.is_completed:
            overall_status = ExecutionStatusEnum.COMPLETED
        elif execution_state.is_failed:
            overall_status = ExecutionStatusEnum.FAILED
        elif running_branches > 0:
            overall_status = ExecutionStatusEnum.RUNNING
        else:
            overall_status = ExecutionStatusEnum.PENDING

        # Calculate duration
        duration_seconds = None
        if execution_state.started_at:
            end_time = execution_state.completed_at or datetime.utcnow()
            duration_seconds = (end_time - execution_state.started_at).total_seconds()

        return ExecutionStatusResponse(
            execution_id=execution_id,
            workflow_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
            status=overall_status,
            mode=ConcurrentModeEnum(execution_state.mode.value),
            progress=progress,
            total_branches=total_branches,
            completed_branches=completed_branches,
            failed_branches=failed_branches,
            running_branches=running_branches,
            branches=branch_infos,
            started_at=execution_state.started_at,
            completed_at=execution_state.completed_at,
            duration_seconds=duration_seconds,
            result=execution_state.merged_result,
            error=execution_state.error,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution status: {str(e)}",
        )


# =============================================================================
# Get Branch List
# =============================================================================


@router.get(
    "/{execution_id}/branches",
    response_model=BranchListResponse,
    summary="Get all branches",
    description="Get status of all branches for an execution",
)
async def get_branches(
    execution_id: UUID,
    state_manager: ConcurrentStateManager = Depends(get_concurrent_state_manager),
) -> BranchListResponse:
    """
    Get all branches for a concurrent execution.

    Returns detailed information about each branch including:
    - Status, timing, results, and errors
    """
    try:
        execution_state = state_manager.get_execution(execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        branches = list(execution_state.branches.values())

        branch_infos = [
            BranchInfo(
                branch_id=b.branch_id,
                status=_convert_branch_status(b.status.value),
                started_at=b.started_at,
                completed_at=b.completed_at,
                duration_ms=(
                    (b.completed_at - b.started_at).total_seconds() * 1000
                    if b.started_at and b.completed_at
                    else None
                ),
                result=b.result,
                error=b.error,
            )
            for b in branches
        ]

        completed = sum(1 for b in branches if b.is_terminal)
        running = sum(1 for b in branches if b.status.value == "running")
        failed = sum(1 for b in branches if b.status.value == "failed")

        return BranchListResponse(
            execution_id=execution_id,
            branches=branch_infos,
            total=len(branches),
            completed=completed,
            running=running,
            failed=failed,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting branches for {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get branches: {str(e)}",
        )


# =============================================================================
# Get Single Branch Status
# =============================================================================


@router.get(
    "/{execution_id}/branches/{branch_id}",
    response_model=BranchStatusResponse,
    summary="Get branch status",
    description="Get detailed status of a specific branch",
)
async def get_branch_status(
    execution_id: UUID,
    branch_id: str,
    state_manager: ConcurrentStateManager = Depends(get_concurrent_state_manager),
) -> BranchStatusResponse:
    """
    Get detailed status of a specific branch.
    """
    try:
        execution_state = state_manager.get_execution(execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        branch = execution_state.branches.get(branch_id)

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch {branch_id} not found in execution {execution_id}",
            )

        duration_ms = None
        if branch.started_at and branch.completed_at:
            duration_ms = (branch.completed_at - branch.started_at).total_seconds() * 1000

        return BranchStatusResponse(
            execution_id=execution_id,
            branch_id=branch_id,
            status=_convert_branch_status(branch.status.value),
            progress=100.0 if branch.is_terminal else 0.0,
            started_at=branch.started_at,
            completed_at=branch.completed_at,
            duration_ms=duration_ms,
            result=branch.result,
            error=branch.error,
            metadata=branch.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting branch {branch_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get branch status: {str(e)}",
        )


# =============================================================================
# Cancel Execution
# =============================================================================


@router.post(
    "/{execution_id}/cancel",
    response_model=ExecutionCancelResponse,
    summary="Cancel execution",
    description="Cancel an entire concurrent execution",
)
async def cancel_execution(
    execution_id: UUID,
    request: Optional[ExecutionCancelRequest] = None,
    state_manager: ConcurrentStateManager = Depends(get_concurrent_state_manager),
) -> ExecutionCancelResponse:
    """
    Cancel an entire concurrent execution.

    This will:
    - Cancel all running branches
    - Mark the execution as cancelled
    - Clean up resources
    """
    try:
        execution_state = state_manager.get_execution(execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        if execution_state.is_completed or execution_state.is_failed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel execution in {execution_state.status} state",
            )

        # Cancel all running branches
        cancelled_branches = []
        for branch_id, branch in execution_state.branches.items():
            if not branch.is_terminal:
                state_manager.update_branch_status(
                    execution_id=execution_id,
                    branch_id=branch_id,
                    status="cancelled",
                    error="Cancelled by user request",
                )
                cancelled_branches.append(branch_id)

        # Update execution status
        state_manager.complete_execution(
            execution_id=execution_id,
            status="cancelled",
            error=request.reason if request else "Cancelled by user request",
        )

        logger.info(
            f"Cancelled execution {execution_id} "
            f"with {len(cancelled_branches)} branches"
        )

        return ExecutionCancelResponse(
            execution_id=execution_id,
            status=ExecutionStatusEnum.CANCELLED,
            cancelled_branches=cancelled_branches,
            message=f"Execution cancelled. {len(cancelled_branches)} branches stopped.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel execution: {str(e)}",
        )


# =============================================================================
# Cancel Branch
# =============================================================================


@router.post(
    "/{execution_id}/branches/{branch_id}/cancel",
    response_model=BranchCancelResponse,
    summary="Cancel branch",
    description="Cancel a specific branch in an execution",
)
async def cancel_branch(
    execution_id: UUID,
    branch_id: str,
    request: Optional[BranchCancelRequest] = None,
    state_manager: ConcurrentStateManager = Depends(get_concurrent_state_manager),
) -> BranchCancelResponse:
    """
    Cancel a specific branch within a concurrent execution.
    """
    try:
        execution_state = state_manager.get_execution(execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        branch = execution_state.branches.get(branch_id)

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch {branch_id} not found",
            )

        if branch.is_terminal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel branch in {branch.status.value} state",
            )

        # Cancel the branch
        state_manager.update_branch_status(
            execution_id=execution_id,
            branch_id=branch_id,
            status="cancelled",
            error=request.reason if request else "Cancelled by user request",
        )

        logger.info(f"Cancelled branch {branch_id} in execution {execution_id}")

        return BranchCancelResponse(
            execution_id=execution_id,
            branch_id=branch_id,
            status=BranchStatusEnum.CANCELLED,
            message=f"Branch {branch_id} cancelled successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling branch {branch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel branch: {str(e)}",
        )


# =============================================================================
# Get Statistics
# =============================================================================


@router.get(
    "/stats",
    response_model=ConcurrentStatsResponse,
    summary="Get statistics",
    description="Get concurrent execution statistics",
)
async def get_stats(
    state_manager: ConcurrentStateManager = Depends(get_concurrent_state_manager),
    deadlock_detector: DeadlockDetector = Depends(get_concurrent_deadlock_detector),
) -> ConcurrentStatsResponse:
    """
    Get aggregated statistics for concurrent executions.

    Returns:
    - Execution counts by status
    - Branch statistics
    - Mode distribution
    - Success rates
    - Deadlock statistics
    """
    try:
        # Get state manager statistics
        sm_stats = state_manager.get_statistics()

        # Get deadlock detector statistics
        dd_stats = deadlock_detector.get_statistics()

        # Calculate mode distribution
        mode_distribution = sm_stats.get("mode_distribution", {})

        # Calculate success rate
        total = sm_stats.get("total_executions", 0)
        completed = sm_stats.get("completed_executions", 0)
        success_rate = (completed / total * 100) if total > 0 else 0.0

        return ConcurrentStatsResponse(
            total_executions=sm_stats.get("total_executions", 0),
            active_executions=sm_stats.get("active_executions", 0),
            completed_executions=sm_stats.get("completed_executions", 0),
            failed_executions=sm_stats.get("failed_executions", 0),
            cancelled_executions=sm_stats.get("cancelled_executions", 0),
            total_branches=sm_stats.get("total_branches", 0),
            avg_branches_per_execution=sm_stats.get("avg_branches_per_execution", 0.0),
            avg_duration_seconds=sm_stats.get("avg_duration_seconds", 0.0),
            total_duration_seconds=sm_stats.get("total_duration_seconds", 0.0),
            mode_distribution=mode_distribution,
            success_rate=success_rate,
            deadlocks_detected=dd_stats.get("deadlocks_detected", 0),
            deadlocks_resolved=dd_stats.get("deadlocks_resolved", 0),
        )

    except Exception as e:
        logger.error(f"Error getting concurrent stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}",
        )


# =============================================================================
# Health Check
# =============================================================================


@router.get(
    "/health",
    summary="Health check",
    description="Check concurrent execution service health",
)
async def health_check(
    state_manager: ConcurrentStateManager = Depends(get_concurrent_state_manager),
    deadlock_detector: DeadlockDetector = Depends(get_concurrent_deadlock_detector),
) -> dict:
    """
    Health check endpoint for concurrent execution service.
    """
    try:
        sm_stats = state_manager.get_statistics()
        dd_stats = deadlock_detector.get_statistics()

        return {
            "status": "healthy",
            "state_manager": {
                "active_executions": sm_stats.get("active_executions", 0),
                "total_executions": sm_stats.get("total_executions", 0),
            },
            "deadlock_detector": {
                "is_monitoring": dd_stats.get("is_monitoring", False),
                "waiting_tasks": dd_stats.get("waiting_tasks", 0),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# =============================================================================
# Phase 3: V2 Adapter-based Endpoints (Sprint 14)
# =============================================================================
# These endpoints use the new ConcurrentBuilderAdapter from Agent Framework.
# They provide the same functionality with improved performance and features.
# =============================================================================


def get_api_service() -> ConcurrentAPIService:
    """Get ConcurrentAPIService instance for dependency injection."""
    return get_concurrent_api_service()


@router.post(
    "/v2/execute",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Execute concurrent tasks (V2 - Adapter)",
    description="Execute concurrent tasks using ConcurrentBuilderAdapter (Phase 3)",
    tags=["concurrent-v2"],
)
async def execute_concurrent_v2(
    workflow_id: Optional[UUID] = Query(None, description="Workflow ID"),
    mode: ConcurrentModeEnum = Query(ConcurrentModeEnum.ALL, description="Execution mode"),
    timeout_seconds: int = Query(300, ge=1, le=3600, description="Timeout in seconds"),
    max_concurrency: int = Query(10, ge=1, le=100, description="Max concurrent tasks"),
    use_adapter: bool = Query(True, description="Use new adapter (True) or legacy (False)"),
    api_service: ConcurrentAPIService = Depends(get_api_service),
) -> Dict[str, Any]:
    """
    Execute concurrent tasks using the new ConcurrentBuilderAdapter.

    This endpoint uses the Phase 3 adapter-based implementation that wraps
    the official Microsoft Agent Framework ConcurrentBuilder.

    Features:
    - ALL mode: Wait for all tasks to complete
    - ANY mode: Return when any task completes
    - MAJORITY mode: Wait for majority of tasks
    - FIRST_SUCCESS mode: Return on first successful task

    Args:
        workflow_id: Optional workflow ID
        mode: Execution mode (all, any, majority, first_success)
        timeout_seconds: Global timeout (1-3600 seconds)
        max_concurrency: Maximum concurrent tasks (1-100)
        use_adapter: Use new adapter (True) or legacy implementation (False)

    Returns:
        Execution response with results and branch information
    """
    try:
        # Create adapter request
        request = AdapterExecuteRequest(
            workflow_id=workflow_id,
            mode=mode.value,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            tasks=[],  # Tasks would be populated from workflow
            input_data={},
        )

        # Execute
        response = await api_service.execute(request, use_adapter=use_adapter)

        # Convert to dict for JSON response
        return {
            "execution_id": str(response.execution_id),
            "status": response.status,
            "mode": response.mode,
            "total_tasks": response.total_tasks,
            "completed_tasks": response.completed_tasks,
            "failed_tasks": response.failed_tasks,
            "results": response.results,
            "errors": response.errors,
            "duration_ms": response.duration_ms,
            "branches": response.branches,
            "started_at": response.started_at.isoformat() if response.started_at else None,
            "completed_at": response.completed_at.isoformat() if response.completed_at else None,
            "use_adapter": use_adapter,
            "message": f"Executed with {'adapter' if use_adapter else 'legacy'} implementation",
        }

    except Exception as e:
        logger.error(f"Error in v2 execute: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute concurrent tasks: {str(e)}",
        )


@router.get(
    "/v2/{execution_id}",
    response_model=Dict[str, Any],
    summary="Get execution details (V2)",
    description="Get execution details from adapter service",
    tags=["concurrent-v2"],
)
async def get_execution_v2(
    execution_id: UUID,
    api_service: ConcurrentAPIService = Depends(get_api_service),
) -> Dict[str, Any]:
    """
    Get execution details from the adapter service.

    Args:
        execution_id: Execution UUID

    Returns:
        Execution details including request, response, and adapter info
    """
    try:
        execution = api_service.get_execution(execution_id)

        if execution is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        response = execution.get("response")
        return {
            "execution_id": str(execution_id),
            "status": response.status if response else "unknown",
            "mode": response.mode if response else "unknown",
            "total_tasks": response.total_tasks if response else 0,
            "completed_tasks": response.completed_tasks if response else 0,
            "failed_tasks": response.failed_tasks if response else 0,
            "results": response.results if response else {},
            "errors": response.errors if response else {},
            "duration_ms": response.duration_ms if response else 0,
            "branches": response.branches if response else [],
            "use_adapter": execution.get("use_adapter", True),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting v2 execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution: {str(e)}",
        )


@router.get(
    "/v2/stats",
    response_model=Dict[str, Any],
    summary="Get adapter statistics (V2)",
    description="Get statistics from the adapter service",
    tags=["concurrent-v2"],
)
async def get_stats_v2(
    api_service: ConcurrentAPIService = Depends(get_api_service),
) -> Dict[str, Any]:
    """
    Get statistics from the ConcurrentAPIService.

    Returns:
        Statistics including total executions, adapter vs legacy usage, and success rates
    """
    try:
        stats = api_service.get_statistics()
        return {
            **stats,
            "implementation": "ConcurrentBuilderAdapter (Phase 3)",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting v2 stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}",
        )


@router.get(
    "/v2/health",
    summary="Health check (V2)",
    description="Check adapter service health",
    tags=["concurrent-v2"],
)
async def health_check_v2(
    api_service: ConcurrentAPIService = Depends(get_api_service),
) -> Dict[str, Any]:
    """
    Health check for the V2 adapter-based concurrent execution service.
    """
    try:
        stats = api_service.get_statistics()
        return {
            "status": "healthy",
            "implementation": "ConcurrentBuilderAdapter",
            "phase": "Phase 3 (Sprint 14)",
            "adapter_service": {
                "total_executions": stats.get("total_executions", 0),
                "adapter_executions": stats.get("adapter_executions", 0),
                "legacy_executions": stats.get("legacy_executions", 0),
                "registered_executors": stats.get("registered_executors", 0),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"V2 health check failed: {e}")
        return {
            "status": "unhealthy",
            "implementation": "ConcurrentBuilderAdapter",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get(
    "/v2/executions",
    response_model=Dict[str, Any],
    summary="List executions (V2)",
    description="List all executions from adapter service",
    tags=["concurrent-v2"],
)
async def list_executions_v2(
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    api_service: ConcurrentAPIService = Depends(get_api_service),
) -> Dict[str, Any]:
    """
    List all executions from the adapter service.

    Args:
        limit: Maximum number of results (1-1000)
        offset: Pagination offset

    Returns:
        List of executions with pagination info
    """
    try:
        executions = api_service.list_executions(limit=limit, offset=offset)
        return {
            "executions": [
                {
                    "execution_id": str(e.get("execution_id")),
                    "use_adapter": e.get("use_adapter", True),
                    "status": e.get("response", {}).status if e.get("response") else "unknown",
                }
                for e in executions
            ],
            "count": len(executions),
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error listing v2 executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list executions: {str(e)}",
        )
