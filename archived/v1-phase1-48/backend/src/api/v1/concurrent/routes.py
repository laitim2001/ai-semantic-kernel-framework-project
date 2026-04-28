# =============================================================================
# IPA Platform - Concurrent Execution API Routes
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
# Sprint 14: ConcurrentBuilder 重構 (Phase 3 - P3-F1)
# Sprint 31: S31-3 - 完整遷移至適配器 (Phase 6)
#
# REST API endpoints for concurrent execution management.
#
# 架構更新 (Sprint 31):
#   - 所有 domain.workflows.executors 導入已移除
#   - 統一使用 ConcurrentAPIService 和適配器層
#   - 符合項目架構規範: 官方 API 集中於 integrations 層
#
# Phase 3+ Endpoints (Adapter-based):
#   - POST /concurrent/execute - Execute with ConcurrentBuilderAdapter
#   - GET /concurrent/{id}/status - Get execution status
#   - GET /concurrent/{id}/branches - Get all branch statuses
#   - POST /concurrent/{id}/cancel - Cancel entire execution
#   - POST /concurrent/{id}/branches/{bid}/cancel - Cancel specific branch
#   - GET /concurrent/stats - Get concurrent execution statistics
#
# All endpoints integrate with ConcurrentAPIService.
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
# Sprint 31: 使用適配器層導入 (取代 domain.workflows.executors)
from src.integrations.agent_framework.builders import (
    ConcurrentMode,
    ConcurrentBuilderAdapter,
    ConcurrentExecutorAdapter,
)
# Sprint 31: Import adapter service (主要服務層)
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
    """
    Convert API mode enum to ConcurrentMode from adapter layer.

    Sprint 31: 使用適配器層的 ConcurrentMode (取代 domain.workflows.executors)
    """
    mode_mapping = {
        ConcurrentModeEnum.ALL: ConcurrentMode.ALL,
        ConcurrentModeEnum.ANY: ConcurrentMode.ANY,
        ConcurrentModeEnum.MAJORITY: ConcurrentMode.MAJORITY,
        ConcurrentModeEnum.FIRST_SUCCESS: ConcurrentMode.FIRST_SUCCESS,
    }
    return mode_mapping.get(mode, ConcurrentMode.ALL)


# =============================================================================
# Dependencies (Sprint 31: 使用適配器服務)
# =============================================================================


# Sprint 31: 全域 ConcurrentAPIService 單例
_concurrent_api_service: Optional[ConcurrentAPIService] = None


def get_concurrent_service() -> ConcurrentAPIService:
    """
    Get ConcurrentAPIService instance.

    Sprint 31: 取代 ConcurrentStateManager 和 DeadlockDetector 依賴，
    統一使用 ConcurrentAPIService 進行狀態管理。
    """
    global _concurrent_api_service
    if _concurrent_api_service is None:
        _concurrent_api_service = get_concurrent_api_service()
    return _concurrent_api_service


# =============================================================================
# Sprint 31: 服務層狀態管理輔助函數
# =============================================================================


def _get_execution_from_service(
    service: ConcurrentAPIService,
    execution_id: UUID,
) -> Optional[Dict[str, Any]]:
    """從服務內部狀態獲取執行記錄。"""
    return service._executions.get(execution_id)


def _update_branch_in_service(
    service: ConcurrentAPIService,
    execution_id: UUID,
    branch_id: str,
    status: str,
    error: Optional[str] = None,
    result: Any = None,
) -> bool:
    """更新服務內部的分支狀態。"""
    execution = service._executions.get(execution_id)
    if execution is None:
        return False

    branches = execution.get("branches", [])
    for branch in branches:
        if branch.get("branch_id") == branch_id:
            branch["status"] = status
            if error:
                branch["error"] = error
            if result is not None:
                branch["result"] = result
            branch["completed_at"] = datetime.utcnow()
            return True
    return False


def _complete_execution_in_service(
    service: ConcurrentAPIService,
    execution_id: UUID,
    status: str,
    error: Optional[str] = None,
) -> bool:
    """標記服務內部的執行為完成。"""
    execution = service._executions.get(execution_id)
    if execution is None:
        return False

    execution["status"] = status
    if error:
        execution["error"] = error
    execution["completed_at"] = datetime.utcnow()
    return True


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
    service: ConcurrentAPIService = Depends(get_concurrent_service),
) -> ConcurrentExecuteResponse:
    """
    Execute a workflow concurrently with multiple branches.

    Sprint 31: 透過 ConcurrentAPIService 執行 (使用適配器層)

    Supports four execution modes:
    - ALL: Wait for all branches to complete
    - ANY: Return when any branch completes
    - MAJORITY: Wait for majority of branches
    - FIRST_SUCCESS: Return on first successful branch
    """
    try:
        execution_id = uuid4()
        created_at = datetime.utcnow()

        # Sprint 31: 透過 ConcurrentAPIService 創建執行
        # 內部使用 ConcurrentBuilderAdapter 管理狀態
        adapter_request = AdapterExecuteRequest(
            workflow_id=execution_id,
            mode=request.mode.value,
            timeout_seconds=request.timeout_seconds or 300,
            max_concurrency=request.max_concurrency or 10,
            tasks=[],  # 將在實際執行時填充
            input_data=request.input_data if hasattr(request, 'input_data') else None,
        )

        # 創建執行記錄 (透過服務內部狀態管理)
        service._executions[execution_id] = {
            "id": execution_id,
            "mode": request.mode.value,
            "status": "pending",
            "created_at": created_at,
            "timeout_seconds": request.timeout_seconds or 300,
            "max_concurrency": request.max_concurrency or 10,
            "branches": [],
        }

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
    service: ConcurrentAPIService = Depends(get_concurrent_service),
) -> ExecutionStatusResponse:
    """
    Get detailed status of a concurrent execution.

    Sprint 31: 透過 ConcurrentAPIService 獲取狀態 (使用適配器層)

    Returns:
    - Overall execution status
    - Progress percentage
    - Branch completion counts
    - Individual branch details
    """
    try:
        # Sprint 31: 使用服務內部狀態
        execution_state = _get_execution_from_service(service, execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        # Calculate progress and counts from service state
        branches = execution_state.get("branches", [])
        total_branches = len(branches)
        completed_branches = sum(
            1 for b in branches
            if b.get("status") in ["completed", "failed", "cancelled", "timed_out"]
        )
        failed_branches = sum(
            1 for b in branches if b.get("status") == "failed"
        )
        running_branches = sum(
            1 for b in branches if b.get("status") == "running"
        )

        progress = (
            (completed_branches / total_branches * 100)
            if total_branches > 0
            else 0.0
        )

        # Convert branches to BranchInfo
        branch_infos = [
            BranchInfo(
                branch_id=b.get("branch_id", ""),
                status=_convert_branch_status(b.get("status", "pending")),
                started_at=b.get("started_at"),
                completed_at=b.get("completed_at"),
                duration_ms=(
                    (b["completed_at"] - b["started_at"]).total_seconds() * 1000
                    if b.get("started_at") and b.get("completed_at")
                    else None
                ),
                result=b.get("result"),
                error=b.get("error"),
            )
            for b in branches
        ]

        # Determine overall status
        exec_status = execution_state.get("status", "pending")
        if exec_status == "completed":
            overall_status = ExecutionStatusEnum.COMPLETED
        elif exec_status == "failed":
            overall_status = ExecutionStatusEnum.FAILED
        elif exec_status == "cancelled":
            overall_status = ExecutionStatusEnum.CANCELLED
        elif running_branches > 0:
            overall_status = ExecutionStatusEnum.RUNNING
        else:
            overall_status = ExecutionStatusEnum.PENDING

        # Calculate duration
        duration_seconds = None
        started_at = execution_state.get("started_at") or execution_state.get("created_at")
        completed_at = execution_state.get("completed_at")
        if started_at:
            end_time = completed_at or datetime.utcnow()
            duration_seconds = (end_time - started_at).total_seconds()

        return ExecutionStatusResponse(
            execution_id=execution_id,
            workflow_id=execution_state.get("id", UUID("00000000-0000-0000-0000-000000000000")),
            status=overall_status,
            mode=ConcurrentModeEnum(execution_state.get("mode", "all")),
            progress=progress,
            total_branches=total_branches,
            completed_branches=completed_branches,
            failed_branches=failed_branches,
            running_branches=running_branches,
            branches=branch_infos,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            result=execution_state.get("result"),
            error=execution_state.get("error"),
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
    service: ConcurrentAPIService = Depends(get_concurrent_service),
) -> BranchListResponse:
    """
    Get all branches for a concurrent execution.

    Sprint 31: 透過 ConcurrentAPIService 獲取分支 (使用適配器層)

    Returns detailed information about each branch including:
    - Status, timing, results, and errors
    """
    try:
        # Sprint 31: 使用服務內部狀態
        execution_state = _get_execution_from_service(service, execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        branches = execution_state.get("branches", [])

        branch_infos = [
            BranchInfo(
                branch_id=b.get("branch_id", ""),
                status=_convert_branch_status(b.get("status", "pending")),
                started_at=b.get("started_at"),
                completed_at=b.get("completed_at"),
                duration_ms=(
                    (b["completed_at"] - b["started_at"]).total_seconds() * 1000
                    if b.get("started_at") and b.get("completed_at")
                    else None
                ),
                result=b.get("result"),
                error=b.get("error"),
            )
            for b in branches
        ]

        terminal_statuses = ["completed", "failed", "cancelled", "timed_out"]
        completed = sum(1 for b in branches if b.get("status") in terminal_statuses)
        running = sum(1 for b in branches if b.get("status") == "running")
        failed = sum(1 for b in branches if b.get("status") == "failed")

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
    service: ConcurrentAPIService = Depends(get_concurrent_service),
) -> BranchStatusResponse:
    """
    Get detailed status of a specific branch.

    Sprint 31: 透過 ConcurrentAPIService 獲取分支狀態 (使用適配器層)
    """
    try:
        # Sprint 31: 使用服務內部狀態
        execution_state = _get_execution_from_service(service, execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        branches = execution_state.get("branches", [])
        branch = next((b for b in branches if b.get("branch_id") == branch_id), None)

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch {branch_id} not found in execution {execution_id}",
            )

        duration_ms = None
        if branch.get("started_at") and branch.get("completed_at"):
            duration_ms = (branch["completed_at"] - branch["started_at"]).total_seconds() * 1000

        terminal_statuses = ["completed", "failed", "cancelled", "timed_out"]
        is_terminal = branch.get("status") in terminal_statuses

        return BranchStatusResponse(
            execution_id=execution_id,
            branch_id=branch_id,
            status=_convert_branch_status(branch.get("status", "pending")),
            progress=100.0 if is_terminal else 0.0,
            started_at=branch.get("started_at"),
            completed_at=branch.get("completed_at"),
            duration_ms=duration_ms,
            result=branch.get("result"),
            error=branch.get("error"),
            metadata=branch.get("metadata", {}),
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
    service: ConcurrentAPIService = Depends(get_concurrent_service),
) -> ExecutionCancelResponse:
    """
    Cancel an entire concurrent execution.

    Sprint 31: 透過 ConcurrentAPIService 取消執行 (使用適配器層)

    This will:
    - Cancel all running branches
    - Mark the execution as cancelled
    - Clean up resources
    """
    try:
        # Sprint 31: 使用服務內部狀態
        execution_state = _get_execution_from_service(service, execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        exec_status = execution_state.get("status", "pending")
        if exec_status in ["completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel execution in {exec_status} state",
            )

        # Cancel all running branches
        cancelled_branches = []
        terminal_statuses = ["completed", "failed", "cancelled", "timed_out"]
        branches = execution_state.get("branches", [])
        for branch in branches:
            branch_id = branch.get("branch_id", "")
            if branch.get("status") not in terminal_statuses:
                _update_branch_in_service(
                    service=service,
                    execution_id=execution_id,
                    branch_id=branch_id,
                    status="cancelled",
                    error="Cancelled by user request",
                )
                cancelled_branches.append(branch_id)

        # Update execution status
        _complete_execution_in_service(
            service=service,
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
    service: ConcurrentAPIService = Depends(get_concurrent_service),
) -> BranchCancelResponse:
    """
    Cancel a specific branch within a concurrent execution.

    Sprint 31: 透過 ConcurrentAPIService 取消分支 (使用適配器層)
    """
    try:
        # Sprint 31: 使用服務內部狀態
        execution_state = _get_execution_from_service(service, execution_id)

        if execution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        branches = execution_state.get("branches", [])
        branch = next((b for b in branches if b.get("branch_id") == branch_id), None)

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch {branch_id} not found",
            )

        terminal_statuses = ["completed", "failed", "cancelled", "timed_out"]
        if branch.get("status") in terminal_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel branch in {branch.get('status')} state",
            )

        # Cancel the branch
        _update_branch_in_service(
            service=service,
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
    service: ConcurrentAPIService = Depends(get_concurrent_service),
) -> ConcurrentStatsResponse:
    """
    Get aggregated statistics for concurrent executions.

    Sprint 31: 透過 ConcurrentAPIService 獲取統計 (使用適配器層)

    Returns:
    - Execution counts by status
    - Branch statistics
    - Mode distribution
    - Success rates
    """
    try:
        # Sprint 31: 從服務內部狀態計算統計
        executions = list(service._executions.values())
        total = len(executions)
        completed = sum(1 for e in executions if e.get("status") == "completed")
        failed = sum(1 for e in executions if e.get("status") == "failed")
        cancelled = sum(1 for e in executions if e.get("status") == "cancelled")
        active = sum(1 for e in executions if e.get("status") in ["pending", "running"])

        # Calculate branch statistics
        all_branches = []
        for e in executions:
            all_branches.extend(e.get("branches", []))
        total_branches = len(all_branches)
        avg_branches = total_branches / total if total > 0 else 0.0

        # Calculate mode distribution
        mode_counts: Dict[str, int] = {}
        for e in executions:
            mode = e.get("mode", "all")
            mode_counts[mode] = mode_counts.get(mode, 0) + 1

        # Calculate success rate
        success_rate = (completed / total * 100) if total > 0 else 0.0

        return ConcurrentStatsResponse(
            total_executions=total,
            active_executions=active,
            completed_executions=completed,
            failed_executions=failed,
            cancelled_executions=cancelled,
            total_branches=total_branches,
            avg_branches_per_execution=avg_branches,
            avg_duration_seconds=0.0,  # 簡化版本
            total_duration_seconds=0.0,
            mode_distribution=mode_counts,
            success_rate=success_rate,
            deadlocks_detected=0,  # 適配器內部處理
            deadlocks_resolved=0,
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
    service: ConcurrentAPIService = Depends(get_concurrent_service),
) -> dict:
    """
    Health check endpoint for concurrent execution service.

    Sprint 31: 透過 ConcurrentAPIService 進行健康檢查 (使用適配器層)
    移除了 DeadlockDetector 直接依賴，死鎖檢測現在由適配器內部處理。
    """
    try:
        # Sprint 31: 從服務內部狀態獲取統計
        executions = list(service._executions.values())
        active = sum(1 for e in executions if e.get("status") in ["pending", "running"])
        total = len(executions)

        return {
            "status": "healthy",
            "service": {
                "active_executions": active,
                "total_executions": total,
                "implementation": "ConcurrentAPIService (Adapter-based)",
            },
            "deadlock_detection": {
                "status": "managed_by_adapter",
                "note": "Deadlock detection is handled internally by ConcurrentBuilderAdapter",
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
