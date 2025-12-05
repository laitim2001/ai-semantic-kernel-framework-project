# =============================================================================
# IPA Platform - Concurrent Execution API Routes
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# REST API endpoints for concurrent execution management.
# Provides:
#   - POST /concurrent/execute - Execute concurrent tasks
#   - GET /concurrent/{id}/status - Get execution status
#   - GET /concurrent/{id}/branches - Get all branch statuses
#   - POST /concurrent/{id}/cancel - Cancel entire execution
#   - POST /concurrent/{id}/branches/{bid}/cancel - Cancel specific branch
#   - GET /concurrent/stats - Get concurrent execution statistics
#
# All endpoints integrate with ConcurrentExecutor and StateManager.
# =============================================================================

import logging
from datetime import datetime
from typing import Optional
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
