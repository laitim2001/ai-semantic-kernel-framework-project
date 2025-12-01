# =============================================================================
# IPA Platform - Checkpoint API Routes
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# REST API endpoints for checkpoint management.
# Provides:
#   - GET /checkpoints/pending - List pending checkpoints
#   - GET /checkpoints/{id} - Get checkpoint details
#   - POST /checkpoints/{id}/approve - Approve a checkpoint
#   - POST /checkpoints/{id}/reject - Reject a checkpoint
#   - GET /checkpoints/stats - Get checkpoint statistics
#   - GET /checkpoints/execution/{execution_id} - List checkpoints for execution
#
# All endpoints require checkpoint repository dependency injection.
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.checkpoints.schemas import (
    ApprovalRequest,
    CheckpointActionResponse,
    CheckpointCreateRequest,
    CheckpointListResponse,
    CheckpointResponse,
    CheckpointStatsResponse,
    PendingCheckpointsResponse,
    RejectionRequest,
)
from src.domain.checkpoints import CheckpointService, CheckpointStatus
from src.infrastructure.database.repositories.checkpoint import CheckpointRepository
from src.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/checkpoints",
    tags=["checkpoints"],
    responses={
        404: {"description": "Checkpoint not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Dependency Injection
# =============================================================================


async def get_checkpoint_repository(
    session: AsyncSession = Depends(get_session),
) -> CheckpointRepository:
    """Get checkpoint repository instance."""
    return CheckpointRepository(session)


async def get_checkpoint_service(
    repo: CheckpointRepository = Depends(get_checkpoint_repository),
) -> CheckpointService:
    """Get checkpoint service instance."""
    return CheckpointService(repo)


# =============================================================================
# List Pending Checkpoints
# =============================================================================


@router.get(
    "/pending",
    response_model=PendingCheckpointsResponse,
    summary="List pending checkpoints",
    description="Get checkpoints awaiting human approval",
)
async def list_pending_checkpoints(
    limit: int = Query(50, ge=1, le=100, description="Maximum number to return"),
    execution_id: Optional[UUID] = Query(None, description="Filter by execution ID"),
    service: CheckpointService = Depends(get_checkpoint_service),
) -> PendingCheckpointsResponse:
    """
    List pending checkpoints awaiting approval.

    Returns checkpoints in PENDING status, ordered by creation time.
    """
    try:
        checkpoints = await service.get_pending_approvals(
            limit=limit,
            execution_id=execution_id,
        )

        items = [
            CheckpointResponse(
                id=cp.id,
                execution_id=cp.execution_id,
                node_id=cp.node_id,
                status=cp.status.value,
                payload=cp.payload,
                response=cp.response,
                responded_by=cp.responded_by,
                responded_at=cp.responded_at,
                expires_at=cp.expires_at,
                created_at=cp.created_at,
                notes=cp.notes,
            )
            for cp in checkpoints
        ]

        return PendingCheckpointsResponse(
            items=items,
            count=len(items),
        )

    except Exception as e:
        logger.error(f"Error listing pending checkpoints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pending checkpoints: {str(e)}",
        )


# =============================================================================
# Get Checkpoint Details
# =============================================================================


@router.get(
    "/{checkpoint_id}",
    response_model=CheckpointResponse,
    summary="Get checkpoint details",
    description="Get detailed information about a specific checkpoint",
)
async def get_checkpoint(
    checkpoint_id: UUID,
    service: CheckpointService = Depends(get_checkpoint_service),
) -> CheckpointResponse:
    """
    Get checkpoint details by ID.
    """
    try:
        checkpoint = await service.get_checkpoint(checkpoint_id)

        if checkpoint is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint {checkpoint_id} not found",
            )

        return CheckpointResponse(
            id=checkpoint.id,
            execution_id=checkpoint.execution_id,
            node_id=checkpoint.node_id,
            status=checkpoint.status.value,
            payload=checkpoint.payload,
            response=checkpoint.response,
            responded_by=checkpoint.responded_by,
            responded_at=checkpoint.responded_at,
            expires_at=checkpoint.expires_at,
            created_at=checkpoint.created_at,
            notes=checkpoint.notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting checkpoint {checkpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get checkpoint: {str(e)}",
        )


# =============================================================================
# Approve Checkpoint
# =============================================================================


@router.post(
    "/{checkpoint_id}/approve",
    response_model=CheckpointActionResponse,
    summary="Approve checkpoint",
    description="Approve a pending checkpoint to continue workflow execution",
)
async def approve_checkpoint(
    checkpoint_id: UUID,
    request: ApprovalRequest,
    service: CheckpointService = Depends(get_checkpoint_service),
) -> CheckpointActionResponse:
    """
    Approve a pending checkpoint.

    The workflow execution will resume after approval.
    """
    try:
        checkpoint = await service.approve_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=request.user_id,
            response=request.response,
            feedback=request.feedback,
        )

        if checkpoint is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint {checkpoint_id} not found",
            )

        return CheckpointActionResponse(
            id=checkpoint.id,
            status=checkpoint.status.value,
            message="Checkpoint approved successfully",
            responded_at=checkpoint.responded_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving checkpoint {checkpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve checkpoint: {str(e)}",
        )


# =============================================================================
# Reject Checkpoint
# =============================================================================


@router.post(
    "/{checkpoint_id}/reject",
    response_model=CheckpointActionResponse,
    summary="Reject checkpoint",
    description="Reject a pending checkpoint to terminate or retry workflow",
)
async def reject_checkpoint(
    checkpoint_id: UUID,
    request: RejectionRequest,
    service: CheckpointService = Depends(get_checkpoint_service),
) -> CheckpointActionResponse:
    """
    Reject a pending checkpoint.

    The workflow execution will terminate or retry based on configuration.
    """
    try:
        checkpoint = await service.reject_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=request.user_id,
            reason=request.reason,
            response=request.response,
        )

        if checkpoint is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint {checkpoint_id} not found",
            )

        return CheckpointActionResponse(
            id=checkpoint.id,
            status=checkpoint.status.value,
            message=f"Checkpoint rejected: {request.reason or 'No reason provided'}",
            responded_at=checkpoint.responded_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting checkpoint {checkpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject checkpoint: {str(e)}",
        )


# =============================================================================
# Get Checkpoints by Execution
# =============================================================================


@router.get(
    "/execution/{execution_id}",
    response_model=CheckpointListResponse,
    summary="List checkpoints for execution",
    description="Get all checkpoints associated with a workflow execution",
)
async def list_checkpoints_by_execution(
    execution_id: UUID,
    include_expired: bool = Query(False, description="Include expired checkpoints"),
    service: CheckpointService = Depends(get_checkpoint_service),
) -> CheckpointListResponse:
    """
    List all checkpoints for a specific execution.
    """
    try:
        checkpoints = await service.get_checkpoints_by_execution(
            execution_id=execution_id,
            include_expired=include_expired,
        )

        items = [
            CheckpointResponse(
                id=cp.id,
                execution_id=cp.execution_id,
                node_id=cp.node_id,
                status=cp.status.value,
                payload=cp.payload,
                response=cp.response,
                responded_by=cp.responded_by,
                responded_at=cp.responded_at,
                expires_at=cp.expires_at,
                created_at=cp.created_at,
                notes=cp.notes,
            )
            for cp in checkpoints
        ]

        return CheckpointListResponse(
            items=items,
            total=len(items),
        )

    except Exception as e:
        logger.error(f"Error listing checkpoints for execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list checkpoints: {str(e)}",
        )


# =============================================================================
# Get Checkpoint Statistics
# =============================================================================


@router.get(
    "/stats",
    response_model=CheckpointStatsResponse,
    summary="Get checkpoint statistics",
    description="Get aggregated checkpoint statistics",
)
async def get_checkpoint_stats(
    execution_id: Optional[UUID] = Query(None, description="Filter by execution ID"),
    service: CheckpointService = Depends(get_checkpoint_service),
) -> CheckpointStatsResponse:
    """
    Get checkpoint statistics.

    Returns counts by status and average response time.
    """
    try:
        stats = await service.get_stats(execution_id)

        return CheckpointStatsResponse(
            pending=stats["pending"],
            approved=stats["approved"],
            rejected=stats["rejected"],
            expired=stats["expired"],
            total=stats["total"],
            avg_response_seconds=stats["avg_response_seconds"],
        )

    except Exception as e:
        logger.error(f"Error getting checkpoint stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get checkpoint stats: {str(e)}",
        )


# =============================================================================
# Create Checkpoint (Internal API)
# =============================================================================


@router.post(
    "/",
    response_model=CheckpointResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create checkpoint",
    description="Create a new checkpoint for human approval (internal use)",
)
async def create_checkpoint(
    request: CheckpointCreateRequest,
    service: CheckpointService = Depends(get_checkpoint_service),
) -> CheckpointResponse:
    """
    Create a new checkpoint.

    This is typically called internally by the workflow engine when
    a human approval step is reached.
    """
    try:
        checkpoint = await service.create_checkpoint(
            execution_id=request.execution_id,
            node_id=request.node_id,
            payload=request.payload,
            timeout_hours=request.timeout_hours,
            notes=request.notes,
        )

        return CheckpointResponse(
            id=checkpoint.id,
            execution_id=checkpoint.execution_id,
            node_id=checkpoint.node_id,
            status=checkpoint.status.value,
            payload=checkpoint.payload,
            response=checkpoint.response,
            responded_by=checkpoint.responded_by,
            responded_at=checkpoint.responded_at,
            expires_at=checkpoint.expires_at,
            created_at=checkpoint.created_at,
            notes=checkpoint.notes,
        )

    except Exception as e:
        logger.error(f"Error creating checkpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkpoint: {str(e)}",
        )


# =============================================================================
# Expire Old Checkpoints (Admin API)
# =============================================================================


@router.post(
    "/expire",
    summary="Expire old checkpoints",
    description="Mark expired checkpoints (admin operation)",
)
async def expire_checkpoints(
    service: CheckpointService = Depends(get_checkpoint_service),
) -> dict:
    """
    Expire checkpoints past their expiration time.

    This is typically called by a scheduled job.
    """
    try:
        count = await service.expire_old_checkpoints()

        return {
            "message": f"Expired {count} checkpoints",
            "count": count,
        }

    except Exception as e:
        logger.error(f"Error expiring checkpoints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to expire checkpoints: {str(e)}",
        )
