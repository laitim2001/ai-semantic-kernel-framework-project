"""
Checkpoints API Routes

Sprint 2 - Story S2-4: Teams Approval Flow

Provides REST API endpoints for checkpoint approval operations.

Endpoints:
- POST /api/v1/checkpoints                    - Create a checkpoint
- GET  /api/v1/checkpoints                    - List pending checkpoints
- GET  /api/v1/checkpoints/{checkpoint_id}    - Get checkpoint details
- POST /api/v1/checkpoints/{checkpoint_id}/approve  - Approve checkpoint
- POST /api/v1/checkpoints/{checkpoint_id}/reject   - Reject checkpoint
- GET  /api/v1/checkpoints/execution/{execution_id} - Get checkpoints by execution
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.checkpoints.service import CheckpointService, get_checkpoint_service
from src.domain.checkpoints.schemas import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointApprovalRequest,
    CheckpointRejectionRequest,
    CheckpointListResponse,
)
from src.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkpoints", tags=["Checkpoints"])


def get_checkpoint_service_dep(
    session: AsyncSession = Depends(get_session),
) -> CheckpointService:
    """Get checkpoint service dependency."""
    return get_checkpoint_service(session)


# ============================================
# Endpoints
# ============================================

@router.post("", response_model=CheckpointResponse, status_code=status.HTTP_201_CREATED)
async def create_checkpoint(
    data: CheckpointCreate,
    workflow_name: Optional[str] = Query(None, description="Workflow name for notification"),
    service: CheckpointService = Depends(get_checkpoint_service_dep),
):
    """
    Create a new checkpoint for approval.

    This endpoint creates a checkpoint that pauses workflow execution
    and sends a Teams notification for approval.

    Args:
        data: Checkpoint creation data
        workflow_name: Optional workflow name for notification context

    Returns:
        Created checkpoint
    """
    try:
        checkpoint = await service.create_checkpoint(
            data=data,
            workflow_name=workflow_name,
            send_notification=True,
        )
        return CheckpointResponse.model_validate(checkpoint)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating checkpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating checkpoint: {str(e)}",
        )


@router.get("", response_model=CheckpointListResponse)
async def list_pending_checkpoints(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    service: CheckpointService = Depends(get_checkpoint_service_dep),
):
    """
    List all pending checkpoints.

    Returns paginated list of checkpoints waiting for approval.
    """
    try:
        return await service.get_pending_checkpoints(
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f"Error listing checkpoints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing checkpoints: {str(e)}",
        )


@router.get("/{checkpoint_id}", response_model=CheckpointResponse)
async def get_checkpoint(
    checkpoint_id: UUID,
    service: CheckpointService = Depends(get_checkpoint_service_dep),
):
    """
    Get checkpoint details by ID.

    Args:
        checkpoint_id: Checkpoint UUID

    Returns:
        Checkpoint details
    """
    checkpoint = await service.get_checkpoint(checkpoint_id)

    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkpoint {checkpoint_id} not found",
        )

    return CheckpointResponse.model_validate(checkpoint)


@router.get("/execution/{execution_id}", response_model=list[CheckpointResponse])
async def get_checkpoints_by_execution(
    execution_id: UUID,
    step_index: Optional[int] = Query(None, ge=0, description="Filter by step index"),
    service: CheckpointService = Depends(get_checkpoint_service_dep),
):
    """
    Get all checkpoints for an execution.

    Args:
        execution_id: Execution UUID
        step_index: Optional filter by step index

    Returns:
        List of checkpoints for the execution
    """
    try:
        checkpoints = await service.get_checkpoint_by_execution(
            execution_id=execution_id,
            step_index=step_index,
        )
        return [CheckpointResponse.model_validate(cp) for cp in checkpoints]

    except Exception as e:
        logger.error(f"Error getting checkpoints for execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting checkpoints: {str(e)}",
        )


@router.post("/{checkpoint_id}/approve", response_model=CheckpointResponse)
async def approve_checkpoint(
    checkpoint_id: UUID,
    data: Optional[CheckpointApprovalRequest] = None,
    user_id: Optional[UUID] = Query(None, description="Approving user ID (temp: should come from auth)"),
    service: CheckpointService = Depends(get_checkpoint_service_dep),
):
    """
    Approve a checkpoint.

    Approves the checkpoint and resumes workflow execution.
    In production, user_id should come from authentication context.

    Args:
        checkpoint_id: Checkpoint UUID
        data: Optional approval feedback
        user_id: Approving user ID (temporary parameter)

    Returns:
        Updated checkpoint
    """
    # TODO: Get user_id from authentication context
    # For now, use a default UUID if not provided
    if user_id is None:
        user_id = UUID("00000000-0000-0000-0000-000000000001")

    try:
        checkpoint = await service.approve_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            data=data,
        )
        return CheckpointResponse.model_validate(checkpoint)

    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    except Exception as e:
        logger.error(f"Error approving checkpoint {checkpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving checkpoint: {str(e)}",
        )


@router.post("/{checkpoint_id}/reject", response_model=CheckpointResponse)
async def reject_checkpoint(
    checkpoint_id: UUID,
    data: CheckpointRejectionRequest,
    user_id: Optional[UUID] = Query(None, description="Rejecting user ID (temp: should come from auth)"),
    service: CheckpointService = Depends(get_checkpoint_service_dep),
):
    """
    Reject a checkpoint.

    Rejects the checkpoint and terminates workflow execution.
    In production, user_id should come from authentication context.

    Args:
        checkpoint_id: Checkpoint UUID
        data: Rejection reason (required)
        user_id: Rejecting user ID (temporary parameter)

    Returns:
        Updated checkpoint
    """
    # TODO: Get user_id from authentication context
    if user_id is None:
        user_id = UUID("00000000-0000-0000-0000-000000000001")

    try:
        checkpoint = await service.reject_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            data=data,
        )
        return CheckpointResponse.model_validate(checkpoint)

    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    except Exception as e:
        logger.error(f"Error rejecting checkpoint {checkpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting checkpoint: {str(e)}",
        )


@router.post("/expire-check", status_code=status.HTTP_200_OK)
async def check_expired_checkpoints(
    service: CheckpointService = Depends(get_checkpoint_service_dep),
):
    """
    Check and expire overdue checkpoints.

    This endpoint is meant to be called by a scheduled job.

    Returns:
        Number of checkpoints expired
    """
    try:
        expired_count = await service.check_expired_checkpoints()
        return {
            "message": f"Expired {expired_count} checkpoints",
            "expired_count": expired_count,
        }
    except Exception as e:
        logger.error(f"Error checking expired checkpoints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking expired checkpoints: {str(e)}",
        )
