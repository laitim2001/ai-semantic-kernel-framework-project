# =============================================================================
# IPA Platform - Execution API Routes
# =============================================================================
# Sprint 29: API Routes 遷移 (Phase 5)
#
# Migration Notes (Sprint 29):
#   - Migrated from domain ExecutionStateMachine to EnhancedExecutionStateMachine adapter
#   - Uses official Agent Framework event system integration
#   - Maintains backward compatibility with existing API schemas
#   - Database operations remain with ExecutionRepository (infrastructure layer)
#   - Resume/checkpoint operations preserved for S29-4 migration
#
# REST API endpoints for execution management:
#   - GET /executions/ - List executions with filtering
#   - GET /executions/{id} - Get execution details
#   - POST /executions/{id}/cancel - Cancel an execution
#   - GET /executions/{id}/transitions - Get valid state transitions
#   - POST /executions/{id}/resume - Resume paused execution
#
# References:
#   - Sprint 29 Plan: docs/03-implementation/sprint-planning/phase-5/sprint-29-plan.md
#   - EnhancedExecutionStateMachine: src/integrations/agent_framework/core/state_machine.py
# =============================================================================

import logging
import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.executions.schemas import (
    ExecutionCancelResponse,
    ExecutionCreateRequest,
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionStatsResponse,
    ExecutionSummaryResponse,
    ResumeRequest,
    ResumeResponse,
    ResumeStatusResponse,
    ValidTransitionsResponse,
)

# =============================================================================
# Sprint 29: Import from Adapter Layer
# =============================================================================
from src.integrations.agent_framework.core.state_machine import (
    EnhancedExecutionStateMachine,
    EVENT_TO_DOMAIN_STATUS,
    DOMAIN_TO_EVENT_STATUS,
)
from src.domain.executions import (
    ExecutionStatus,
    InvalidStateTransitionError,
)
from src.infrastructure.database.repositories.execution import ExecutionRepository
from src.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/executions",
    tags=["executions"],
    responses={
        404: {"description": "Execution not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Dependency Injection
# =============================================================================


async def get_execution_repository(
    session: AsyncSession = Depends(get_session),
) -> ExecutionRepository:
    """Get execution repository instance."""
    return ExecutionRepository(session)


# =============================================================================
# Helper Functions (Sprint 29)
# =============================================================================


def validate_state_transition(current_status: str, target_status: str) -> bool:
    """
    Validate if a state transition is allowed.

    Sprint 29: Uses EnhancedExecutionStateMachine class methods.

    Args:
        current_status: Current execution status
        target_status: Target execution status

    Returns:
        True if transition is valid
    """
    try:
        from_status = ExecutionStatus(current_status)
        to_status = ExecutionStatus(target_status)
        return EnhancedExecutionStateMachine.can_transition(from_status, to_status)
    except ValueError:
        return False


# =============================================================================
# List Executions
# =============================================================================


@router.get(
    "/",
    response_model=ExecutionListResponse,
    summary="List executions",
    description="Get a paginated list of executions with optional filtering",
)
async def list_executions(
    workflow_id: Optional[UUID] = Query(
        None, description="Filter by workflow ID"
    ),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Records per page"),
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> ExecutionListResponse:
    """
    List executions with pagination and filtering.

    Supports filtering by:
    - workflow_id: Get executions for a specific workflow
    - status: Filter by execution status (pending, running, etc.)
    """
    try:
        if workflow_id:
            executions, total = await repo.get_by_workflow(
                workflow_id=workflow_id,
                page=page,
                page_size=page_size,
                status=status_filter,
            )
        elif status_filter:
            executions, total = await repo.get_by_status(
                status=status_filter,
                page=page,
                page_size=page_size,
            )
        else:
            executions, total = await repo.list(
                page=page,
                page_size=page_size,
                order_by="created_at",
                order_desc=True,
            )

        items = [
            ExecutionSummaryResponse(
                id=ex.id,
                workflow_id=ex.workflow_id,
                status=ex.status,
                started_at=ex.started_at,
                completed_at=ex.completed_at,
                llm_calls=ex.llm_calls,
                llm_tokens=ex.llm_tokens,
                llm_cost=float(ex.llm_cost),
                created_at=ex.created_at,
            )
            for ex in executions
        ]

        pages = math.ceil(total / page_size) if total > 0 else 1

        return ExecutionListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listing executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list executions: {str(e)}",
        )


# =============================================================================
# Create Execution
# =============================================================================


@router.post(
    "/",
    response_model=ExecutionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create execution",
    description="Create a new execution record for a workflow",
)
async def create_execution(
    request: ExecutionCreateRequest,
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> ExecutionDetailResponse:
    """
    Create a new execution record.

    This creates a pending execution that can be used for checkpoint testing.
    For actual workflow execution, use POST /workflows/{id}/execute.
    """
    try:
        # Create execution record
        execution = await repo.create(
            workflow_id=request.workflow_id,
            status=request.status,
            input_data=request.input_data,
        )

        return ExecutionDetailResponse(
            id=execution.id,
            workflow_id=execution.workflow_id,
            status=execution.status,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            result=execution.result,
            error=execution.error,
            llm_calls=execution.llm_calls,
            llm_tokens=execution.llm_tokens,
            llm_cost=float(execution.llm_cost),
            triggered_by=execution.triggered_by,
            input_data=execution.input_data,
            duration_seconds=execution.duration_seconds,
            created_at=execution.created_at,
            updated_at=execution.updated_at,
        )

    except Exception as e:
        logger.error(f"Error creating execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create execution: {str(e)}",
        )


# =============================================================================
# Get Execution Details
# =============================================================================


@router.get(
    "/{execution_id}",
    response_model=ExecutionDetailResponse,
    summary="Get execution details",
    description="Get detailed information about a specific execution",
)
async def get_execution(
    execution_id: UUID,
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> ExecutionDetailResponse:
    """
    Get detailed execution information including LLM statistics.
    """
    try:
        execution = await repo.get(execution_id)

        if execution is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        return ExecutionDetailResponse(
            id=execution.id,
            workflow_id=execution.workflow_id,
            status=execution.status,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            result=execution.result,
            error=execution.error,
            llm_calls=execution.llm_calls,
            llm_tokens=execution.llm_tokens,
            llm_cost=float(execution.llm_cost),
            triggered_by=execution.triggered_by,
            input_data=execution.input_data,
            duration_seconds=execution.duration_seconds,
            created_at=execution.created_at,
            updated_at=execution.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution: {str(e)}",
        )


# =============================================================================
# Cancel Execution
# =============================================================================


@router.post(
    "/{execution_id}/cancel",
    response_model=ExecutionCancelResponse,
    summary="Cancel execution",
    description="Cancel a pending, running, or paused execution",
)
async def cancel_execution(
    execution_id: UUID,
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> ExecutionCancelResponse:
    """
    Cancel an execution.

    Only executions in PENDING, RUNNING, or PAUSED status can be cancelled.
    Terminal states (COMPLETED, FAILED, CANCELLED) cannot be cancelled.

    Sprint 29: Uses EnhancedExecutionStateMachine for validation.
    """
    try:
        execution = await repo.get(execution_id)

        if execution is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        # Validate transition using adapter
        current_status = execution.status
        if not validate_state_transition(current_status, "cancelled"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel execution in {current_status} status",
            )

        # Perform cancellation
        updated = await repo.cancel(execution_id)

        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel execution",
            )

        return ExecutionCancelResponse(
            id=updated.id,
            status=updated.status,
            message=f"Execution cancelled successfully from {current_status} status",
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
# Get Valid Transitions
# =============================================================================


@router.get(
    "/{execution_id}/transitions",
    response_model=ValidTransitionsResponse,
    summary="Get valid state transitions",
    description="Get list of valid status transitions for an execution",
)
async def get_valid_transitions(
    execution_id: UUID,
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> ValidTransitionsResponse:
    """
    Get valid state transitions for the current execution status.

    Sprint 29: Uses EnhancedExecutionStateMachine for state machine operations.
    """
    try:
        execution = await repo.get(execution_id)

        if execution is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        try:
            current_status = ExecutionStatus(execution.status)
        except ValueError:
            current_status = ExecutionStatus.PENDING

        # Use adapter class methods
        valid_transitions = EnhancedExecutionStateMachine.get_valid_transitions(current_status)
        is_terminal = EnhancedExecutionStateMachine.is_terminal(current_status)

        return ValidTransitionsResponse(
            current_status=current_status.value,
            valid_transitions=[s.value for s in valid_transitions],
            is_terminal=is_terminal,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transitions for {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transitions: {str(e)}",
        )


# =============================================================================
# Get Running Executions
# =============================================================================


@router.get(
    "/status/running",
    response_model=list[ExecutionSummaryResponse],
    summary="Get running executions",
    description="Get all currently running executions",
)
async def get_running_executions(
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> list[ExecutionSummaryResponse]:
    """
    Get all executions currently in RUNNING status.
    """
    try:
        executions = await repo.get_running()

        return [
            ExecutionSummaryResponse(
                id=ex.id,
                workflow_id=ex.workflow_id,
                status=ex.status,
                started_at=ex.started_at,
                completed_at=ex.completed_at,
                llm_calls=ex.llm_calls,
                llm_tokens=ex.llm_tokens,
                llm_cost=float(ex.llm_cost),
                created_at=ex.created_at,
            )
            for ex in executions
        ]

    except Exception as e:
        logger.error(f"Error getting running executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get running executions: {str(e)}",
        )


# =============================================================================
# Get Recent Executions
# =============================================================================


@router.get(
    "/status/recent",
    response_model=list[ExecutionSummaryResponse],
    summary="Get recent executions",
    description="Get most recent executions",
)
async def get_recent_executions(
    limit: int = Query(10, ge=1, le=100, description="Maximum number to return"),
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> list[ExecutionSummaryResponse]:
    """
    Get most recent executions across all workflows.
    """
    try:
        executions = await repo.get_recent(limit=limit)

        return [
            ExecutionSummaryResponse(
                id=ex.id,
                workflow_id=ex.workflow_id,
                status=ex.status,
                started_at=ex.started_at,
                completed_at=ex.completed_at,
                llm_calls=ex.llm_calls,
                llm_tokens=ex.llm_tokens,
                llm_cost=float(ex.llm_cost),
                created_at=ex.created_at,
            )
            for ex in executions
        ]

    except Exception as e:
        logger.error(f"Error getting recent executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent executions: {str(e)}",
        )


# =============================================================================
# Get Workflow Statistics
# =============================================================================


@router.get(
    "/workflows/{workflow_id}/stats",
    response_model=ExecutionStatsResponse,
    summary="Get workflow execution statistics",
    description="Get aggregated statistics for workflow executions",
)
async def get_workflow_stats(
    workflow_id: UUID,
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> ExecutionStatsResponse:
    """
    Get aggregated execution statistics for a specific workflow.

    Returns totals and averages for:
    - Total executions
    - LLM API calls
    - Token usage
    - Cost
    - Duration
    """
    try:
        stats = await repo.get_stats_by_workflow(workflow_id)

        return ExecutionStatsResponse(
            total_executions=stats["total_executions"],
            total_llm_calls=stats["total_llm_calls"],
            total_llm_tokens=stats["total_llm_tokens"],
            total_llm_cost=stats["total_llm_cost"],
            avg_duration_seconds=stats["avg_duration_seconds"],
        )

    except Exception as e:
        logger.error(f"Error getting stats for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow stats: {str(e)}",
        )


# =============================================================================
# Resume Execution (Sprint 2)
# NOTE: CheckpointService usage preserved for S29-4 migration
# =============================================================================


@router.post(
    "/{execution_id}/resume",
    response_model=ResumeResponse,
    summary="Resume paused execution",
    description="Resume a paused workflow execution after checkpoint approval",
)
async def resume_execution(
    execution_id: UUID,
    request: ResumeRequest,
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> ResumeResponse:
    """
    Resume a paused workflow execution.

    Resumes execution after human approval of a checkpoint.
    Can specify a specific checkpoint or use the latest approved checkpoint.

    NOTE: Uses domain CheckpointService - will be migrated in S29-4.
    """
    from src.domain.checkpoints import CheckpointService
    from src.domain.workflows.resume_service import WorkflowResumeService, ResumeStatus
    from src.infrastructure.database.repositories.checkpoint import CheckpointRepository

    try:
        # Get checkpoint repository from same session
        checkpoint_repo = CheckpointRepository(repo._session)
        checkpoint_service = CheckpointService(checkpoint_repo)
        resume_service = WorkflowResumeService(checkpoint_service, repo)

        if request.checkpoint_id:
            # Resume from specific checkpoint
            result = await resume_service.resume_from_checkpoint(
                execution_id=execution_id,
                checkpoint_id=request.checkpoint_id,
            )
        else:
            # Resume with approval (finds latest pending checkpoint)
            result = await resume_service.resume_with_approval(
                execution_id=execution_id,
                user_id=request.user_id,
                response=request.response,
            )

        if result.status == ResumeStatus.NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.message,
            )

        if result.status in (
            ResumeStatus.INVALID_STATE,
            ResumeStatus.CHECKPOINT_PENDING,
            ResumeStatus.CHECKPOINT_REJECTED,
            ResumeStatus.CHECKPOINT_EXPIRED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message,
            )

        if result.status == ResumeStatus.ERROR:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message,
            )

        return ResumeResponse(
            status=result.status.value,
            execution_id=result.execution_id,
            checkpoint_id=result.checkpoint_id,
            message=result.message,
            resumed_at=result.resumed_at,
            next_node_id=result.next_node_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume execution: {str(e)}",
        )


# =============================================================================
# Get Resume Status (Sprint 2)
# NOTE: CheckpointService usage preserved for S29-4 migration
# =============================================================================


@router.get(
    "/{execution_id}/resume-status",
    response_model=ResumeStatusResponse,
    summary="Get resume status",
    description="Get the resume status for a paused execution",
)
async def get_resume_status(
    execution_id: UUID,
    repo: ExecutionRepository = Depends(get_execution_repository),
) -> ResumeStatusResponse:
    """
    Get the resume status for an execution.

    Returns information about pending checkpoints and whether
    the execution can be resumed.

    NOTE: Uses domain CheckpointService - will be migrated in S29-4.
    """
    from src.domain.checkpoints import CheckpointService
    from src.domain.workflows.resume_service import WorkflowResumeService
    from src.infrastructure.database.repositories.checkpoint import CheckpointRepository

    try:
        # Get checkpoint repository from same session
        checkpoint_repo = CheckpointRepository(repo._session)
        checkpoint_service = CheckpointService(checkpoint_repo)
        resume_service = WorkflowResumeService(checkpoint_service, repo)

        status_info = await resume_service.get_resume_status(execution_id)

        return ResumeStatusResponse(
            can_resume=status_info["can_resume"],
            reason=status_info["reason"],
            current_status=status_info.get("current_status"),
            pending_count=status_info.get("pending_count", 0),
            approved_count=status_info.get("approved_count", 0),
            pending_checkpoints=status_info.get("pending_checkpoints", []),
        )

    except Exception as e:
        logger.error(f"Error getting resume status for {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resume status: {str(e)}",
        )
