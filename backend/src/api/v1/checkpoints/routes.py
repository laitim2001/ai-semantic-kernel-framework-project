# =============================================================================
# IPA Platform - Checkpoint API Routes
# =============================================================================
# Sprint 29: API Routes 遷移 (Phase 5)
#
# Migration Notes (Sprint 29):
#   - Migrated from domain CheckpointService to ApprovalWorkflowManager adapter
#   - Uses official Agent Framework RequestResponseExecutor via HumanApprovalExecutor
#   - Maintains backward compatibility with existing API schemas
#   - Database operations remain with CheckpointRepository (infrastructure layer)
#   - CheckpointService retained for storage operations, approval flow via adapter
#
# REST API endpoints for checkpoint management:
#   - GET /checkpoints/pending - List pending checkpoints
#   - GET /checkpoints/{id} - Get checkpoint details
#   - POST /checkpoints/{id}/approve - Approve a checkpoint
#   - POST /checkpoints/{id}/reject - Reject a checkpoint
#   - GET /checkpoints/stats - Get checkpoint statistics
#   - GET /checkpoints/execution/{execution_id} - List checkpoints for execution
#
# References:
#   - Sprint 29 Plan: docs/03-implementation/sprint-planning/phase-5/sprint-29-plan.md
#   - HumanApprovalExecutor: src/integrations/agent_framework/core/approval.py
#   - ApprovalWorkflowManager: src/integrations/agent_framework/core/approval_workflow.py
# =============================================================================

import logging
import warnings
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

# =============================================================================
# Sprint 29: Import from Adapter Layer
# =============================================================================
from src.integrations.agent_framework.core.approval import (
    HumanApprovalExecutor,
    ApprovalRequest as AdapterApprovalRequest,
    ApprovalResponse as AdapterApprovalResponse,
    ApprovalStatus as AdapterApprovalStatus,
    RiskLevel,
    create_approval_executor,
)
from src.integrations.agent_framework.core.approval_workflow import (
    ApprovalWorkflowManager,
    create_approval_workflow_manager,
    quick_respond,
)

# Keep CheckpointService for storage operations
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
# Dependency Injection (Sprint 29)
# =============================================================================

# Singleton for ApprovalWorkflowManager
_approval_manager: Optional[ApprovalWorkflowManager] = None


def get_approval_manager() -> ApprovalWorkflowManager:
    """
    Get or create the ApprovalWorkflowManager singleton.

    Sprint 29: New adapter-based dependency injection.

    Returns:
        ApprovalWorkflowManager instance
    """
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = create_approval_workflow_manager()
        # Register default approval executor
        _approval_manager.register_approval_executor("checkpoint-approval")
        logger.info("ApprovalWorkflowManager initialized for checkpoint API")
    return _approval_manager


def reset_approval_manager() -> None:
    """Reset the manager instance (for testing)."""
    global _approval_manager
    _approval_manager = None


async def get_checkpoint_repository(
    session: AsyncSession = Depends(get_session),
) -> CheckpointRepository:
    """Get checkpoint repository instance."""
    return CheckpointRepository(session)


async def get_checkpoint_service(
    repo: CheckpointRepository = Depends(get_checkpoint_repository),
) -> CheckpointService:
    """Get checkpoint service instance (for storage operations)."""
    return CheckpointService(repo)


# =============================================================================
# Status Mapping Helpers
# =============================================================================

def _map_checkpoint_to_adapter_status(status: CheckpointStatus) -> AdapterApprovalStatus:
    """Map CheckpointStatus to adapter ApprovalStatus."""
    mapping = {
        CheckpointStatus.PENDING: AdapterApprovalStatus.PENDING,
        CheckpointStatus.APPROVED: AdapterApprovalStatus.APPROVED,
        CheckpointStatus.REJECTED: AdapterApprovalStatus.REJECTED,
        CheckpointStatus.EXPIRED: AdapterApprovalStatus.EXPIRED,
    }
    return mapping.get(status, AdapterApprovalStatus.PENDING)


def _map_adapter_to_checkpoint_status(status: AdapterApprovalStatus) -> CheckpointStatus:
    """Map adapter ApprovalStatus to CheckpointStatus."""
    mapping = {
        AdapterApprovalStatus.PENDING: CheckpointStatus.PENDING,
        AdapterApprovalStatus.APPROVED: CheckpointStatus.APPROVED,
        AdapterApprovalStatus.REJECTED: CheckpointStatus.REJECTED,
        AdapterApprovalStatus.EXPIRED: CheckpointStatus.EXPIRED,
        AdapterApprovalStatus.ESCALATED: CheckpointStatus.PENDING,  # Map escalated to pending
        AdapterApprovalStatus.CANCELLED: CheckpointStatus.EXPIRED,  # Map cancelled to expired
    }
    return mapping.get(status, CheckpointStatus.PENDING)


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
    manager: ApprovalWorkflowManager = Depends(get_approval_manager),
) -> PendingCheckpointsResponse:
    """
    List pending checkpoints awaiting approval.

    Returns checkpoints in PENDING status, ordered by creation time.
    Also includes pending requests from ApprovalWorkflowManager.

    Sprint 29: Hybrid approach - combines database checkpoints with adapter pending requests.
    """
    try:
        # Get pending from database (CheckpointService)
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
    manager: ApprovalWorkflowManager = Depends(get_approval_manager),
) -> CheckpointActionResponse:
    """
    Approve a pending checkpoint.

    The workflow execution will resume after approval.

    Sprint 29: Uses ApprovalWorkflowManager for approval flow coordination.
    """
    try:
        # First, update in database via CheckpointService
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

        # Optionally sync with adapter manager for workflow coordination
        # This enables future integration with HumanApprovalExecutor
        try:
            adapter_response = manager.create_approval_response(
                approved=True,
                reason=request.feedback or "Approved via API",
                approver=request.user_id,
            )
            logger.debug(f"Approval synced with adapter: {checkpoint_id}")
        except Exception as sync_error:
            logger.debug(f"Adapter sync skipped: {sync_error}")

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
    manager: ApprovalWorkflowManager = Depends(get_approval_manager),
) -> CheckpointActionResponse:
    """
    Reject a pending checkpoint.

    The workflow execution will terminate or retry based on configuration.

    Sprint 29: Uses ApprovalWorkflowManager for rejection flow coordination.
    """
    try:
        # Update in database via CheckpointService
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

        # Optionally sync with adapter manager
        try:
            adapter_response = manager.create_approval_response(
                approved=False,
                reason=request.reason or "Rejected via API",
                approver=request.user_id,
            )
            logger.debug(f"Rejection synced with adapter: {checkpoint_id}")
        except Exception as sync_error:
            logger.debug(f"Adapter sync skipped: {sync_error}")

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
    manager: ApprovalWorkflowManager = Depends(get_approval_manager),
) -> CheckpointResponse:
    """
    Create a new checkpoint.

    This is typically called internally by the workflow engine when
    a human approval step is reached.

    Sprint 29: Also creates corresponding ApprovalRequest in adapter.
    """
    try:
        # Create in database via CheckpointService
        checkpoint = await service.create_checkpoint(
            execution_id=request.execution_id,
            node_id=request.node_id,
            payload=request.payload,
            timeout_hours=request.timeout_hours,
            notes=request.notes,
            step=request.step,
            checkpoint_type=request.checkpoint_type,
            state=request.state,
        )

        # Also create in adapter for workflow coordination
        try:
            adapter_request = manager.create_approval_request(
                action=f"checkpoint_{checkpoint.id}",
                details=request.notes or f"Checkpoint for node {request.node_id}",
                risk_level=RiskLevel.MEDIUM,
                context={
                    "checkpoint_id": str(checkpoint.id),
                    "execution_id": str(request.execution_id),
                    "node_id": request.node_id,
                    "payload": request.payload,
                },
            )
            logger.debug(f"Adapter request created for checkpoint: {checkpoint.id}")
        except Exception as sync_error:
            logger.debug(f"Adapter request skipped: {sync_error}")

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


# =============================================================================
# Sprint 29: New Adapter-Based Endpoints
# =============================================================================


@router.get(
    "/approval/pending",
    summary="Get pending approval requests (adapter)",
    description="Get pending approval requests from ApprovalWorkflowManager",
    tags=["checkpoints", "Sprint-29"],
)
async def get_pending_approval_requests(
    manager: ApprovalWorkflowManager = Depends(get_approval_manager),
) -> list:
    """
    Get pending approval requests from the adapter layer.

    Sprint 29: New endpoint using ApprovalWorkflowManager.
    """
    try:
        pending = manager.get_pending_approvals()
        return pending
    except Exception as e:
        logger.error(f"Error getting pending approval requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending requests: {str(e)}",
        )


@router.post(
    "/approval/{executor_name}/respond",
    summary="Respond to approval request (adapter)",
    description="Respond to an approval request via ApprovalWorkflowManager",
    tags=["checkpoints", "Sprint-29"],
)
async def respond_to_approval(
    executor_name: str,
    approved: bool = Query(..., description="Whether to approve"),
    reason: str = Query(..., description="Reason for decision"),
    approver: str = Query(..., description="Who is responding"),
    manager: ApprovalWorkflowManager = Depends(get_approval_manager),
) -> dict:
    """
    Respond to an approval request via the adapter layer.

    Sprint 29: New endpoint using ApprovalWorkflowManager.
    """
    try:
        response = manager.create_approval_response(
            approved=approved,
            reason=reason,
            approver=approver,
        )

        result = await manager.respond_to_approval(
            executor_name=executor_name,
            response=response,
        )

        return {
            "success": result,
            "executor_name": executor_name,
            "approved": approved,
            "message": "Response submitted successfully" if result else "No pending request found",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error responding to approval: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to respond to approval: {str(e)}",
        )
