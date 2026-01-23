# =============================================================================
# IPA Platform - HITL Approval API Routes
# =============================================================================
# Sprint 98: Phase 28 Integration - HITLController API
#
# REST API endpoints for Human-in-the-Loop approval workflow management.
# Supports approval requests, decisions, and Teams webhook callbacks.
#
# Endpoints:
#   GET /approvals - List pending approvals
#   GET /approvals/{approval_id} - Get approval details
#   POST /approvals/{approval_id}/decision - Submit approval decision
#   POST /approvals/{approval_id}/callback - Teams webhook callback
# =============================================================================

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field

from src.integrations.orchestration import (
    HITLController,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    create_hitl_controller,
    create_mock_hitl_controller,
    InMemoryApprovalStorage,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class ApprovalDecision(str, Enum):
    """Approval decision types."""

    APPROVE = "approve"
    REJECT = "reject"


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ApprovalSummary(BaseModel):
    """Summary of an approval request."""

    approval_id: str = Field(..., description="Unique approval request ID")
    status: str = Field(..., description="Approval status")
    requester: str = Field(..., description="User who requested approval")
    intent_category: Optional[str] = Field(
        None,
        description="IT intent category",
    )
    risk_level: Optional[str] = Field(
        None,
        description="Risk level (low, medium, high, critical)",
    )
    created_at: datetime = Field(..., description="Request creation time")
    expires_at: Optional[datetime] = Field(
        None,
        description="Request expiration time",
    )


class ApprovalDetailResponse(BaseModel):
    """Detailed approval request information."""

    approval_id: str = Field(..., description="Unique approval request ID")
    status: str = Field(..., description="Approval status")
    approval_type: str = Field(..., description="Type of approval required")
    requester: str = Field(..., description="User who requested approval")

    # Routing decision info
    intent_category: Optional[str] = Field(None, description="IT intent category")
    sub_intent: Optional[str] = Field(None, description="Sub-intent")
    workflow_type: Optional[str] = Field(None, description="Workflow type")

    # Risk assessment info
    risk_level: Optional[str] = Field(None, description="Risk level")
    risk_score: Optional[float] = Field(None, description="Risk score (0-1)")
    risk_factors: Optional[List[str]] = Field(None, description="Risk factors")

    # Timestamps
    created_at: datetime = Field(..., description="Request creation time")
    expires_at: Optional[datetime] = Field(None, description="Request expiration time")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    rejected_at: Optional[datetime] = Field(None, description="Rejection timestamp")

    # Decision info
    approved_by: Optional[str] = Field(None, description="Approver")
    rejected_by: Optional[str] = Field(None, description="Rejector")
    comment: Optional[str] = Field(None, description="Approval/rejection comment")

    # History
    history: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Approval event history",
    )

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata",
    )


class ApprovalListResponse(BaseModel):
    """Response for listing approvals."""

    approvals: List[ApprovalSummary] = Field(
        ...,
        description="List of approval requests",
    )
    total: int = Field(..., description="Total number of approvals")
    pending_count: int = Field(..., description="Number of pending approvals")


class SubmitDecisionRequest(BaseModel):
    """Request to submit an approval decision."""

    decision: ApprovalDecision = Field(
        ...,
        description="Approval decision (approve/reject)",
    )
    approver: str = Field(
        ...,
        description="User making the decision",
    )
    comment: Optional[str] = Field(
        None,
        description="Optional comment or reason",
    )


class DecisionResponse(BaseModel):
    """Response after submitting a decision."""

    approval_id: str = Field(..., description="The approval request ID")
    decision: str = Field(..., description="The decision made")
    status: str = Field(..., description="New status after decision")
    message: str = Field(..., description="Result message")


class TeamsCallbackRequest(BaseModel):
    """Teams Adaptive Card action callback payload."""

    action_type: str = Field(..., description="Action type (approve/reject)")
    approval_id: str = Field(..., description="Approval request ID")
    user_id: str = Field(..., description="Teams user ID")
    user_name: Optional[str] = Field(None, description="Teams user name")
    comment: Optional[str] = Field(None, description="Optional comment")


class CallbackResponse(BaseModel):
    """Response to Teams callback."""

    success: bool = Field(..., description="Whether callback succeeded")
    message: str = Field(..., description="Response message")
    status: str = Field(..., description="New approval status")


# =============================================================================
# Global State
# =============================================================================

# Global HITL controller instance
_hitl_controller: Optional[HITLController] = None


def get_hitl_controller() -> HITLController:
    """Get or create the HITL controller instance."""
    global _hitl_controller
    if _hitl_controller is None:
        try:
            # Try to create with in-memory storage for now
            # In production, use Redis storage
            _hitl_controller = create_hitl_controller()
        except Exception as e:
            logger.warning(f"Failed to create HITL controller, using mock: {e}")
            _hitl_controller, _, _ = create_mock_hitl_controller()
    return _hitl_controller


# =============================================================================
# Router
# =============================================================================

approval_router = APIRouter(prefix="/orchestration/approvals", tags=["HITL Approvals"])


# =============================================================================
# Endpoints
# =============================================================================


@approval_router.get(
    "",
    response_model=ApprovalListResponse,
)
async def list_approvals(
    status_filter: Optional[str] = None,
    approver: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> ApprovalListResponse:
    """
    List approval requests.

    By default, returns all pending approvals. Use filters to narrow results.

    Args:
        status_filter: Filter by status (pending, approved, rejected, expired)
        approver: Filter by assigned approver
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        ApprovalListResponse with approval summaries
    """
    controller = get_hitl_controller()

    try:
        # Get pending requests
        pending_requests = await controller.list_pending_requests(approver=approver)

        # Convert to summaries
        summaries = []
        for req in pending_requests:
            # Filter by status if specified
            if status_filter and req.status.value != status_filter:
                continue

            # Extract intent and risk info from routing decision
            intent_category = None
            risk_level = None
            if hasattr(req, "routing_decision") and req.routing_decision:
                if hasattr(req.routing_decision, "intent_category"):
                    intent_category = req.routing_decision.intent_category.value \
                        if hasattr(req.routing_decision.intent_category, "value") \
                        else str(req.routing_decision.intent_category)
            if hasattr(req, "risk_assessment") and req.risk_assessment:
                if hasattr(req.risk_assessment, "risk_level"):
                    risk_level = req.risk_assessment.risk_level.value \
                        if hasattr(req.risk_assessment.risk_level, "value") \
                        else str(req.risk_assessment.risk_level)

            summaries.append(ApprovalSummary(
                approval_id=req.request_id,
                status=req.status.value,
                requester=req.requester,
                intent_category=intent_category,
                risk_level=risk_level,
                created_at=req.created_at,
                expires_at=req.expires_at,
            ))

        # Apply pagination
        total = len(summaries)
        paginated = summaries[offset : offset + limit]

        return ApprovalListResponse(
            approvals=paginated,
            total=total,
            pending_count=len([s for s in summaries if s.status == "pending"]),
        )

    except Exception as e:
        logger.error(f"Failed to list approvals: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list approvals: {str(e)}",
        )


@approval_router.get(
    "/{approval_id}",
    response_model=ApprovalDetailResponse,
)
async def get_approval(approval_id: str) -> ApprovalDetailResponse:
    """
    Get detailed information about an approval request.

    Args:
        approval_id: The approval request ID

    Returns:
        ApprovalDetailResponse with full approval details
    """
    controller = get_hitl_controller()

    try:
        request = await controller.get_request(approval_id)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval request not found: {approval_id}",
            )

        # Extract routing decision info
        intent_category = None
        sub_intent = None
        workflow_type = None
        if hasattr(request, "routing_decision") and request.routing_decision:
            rd = request.routing_decision
            if hasattr(rd, "intent_category"):
                intent_category = rd.intent_category.value \
                    if hasattr(rd.intent_category, "value") \
                    else str(rd.intent_category)
            if hasattr(rd, "sub_intent"):
                sub_intent = rd.sub_intent
            if hasattr(rd, "workflow_type"):
                workflow_type = rd.workflow_type.value \
                    if hasattr(rd.workflow_type, "value") \
                    else str(rd.workflow_type)

        # Extract risk assessment info
        risk_level = None
        risk_score = None
        risk_factors = None
        if hasattr(request, "risk_assessment") and request.risk_assessment:
            ra = request.risk_assessment
            if hasattr(ra, "risk_level"):
                risk_level = ra.risk_level.value \
                    if hasattr(ra.risk_level, "value") \
                    else str(ra.risk_level)
            if hasattr(ra, "risk_score"):
                risk_score = ra.risk_score
            if hasattr(ra, "factors"):
                risk_factors = [
                    f.description if hasattr(f, "description") else str(f)
                    for f in ra.factors
                ]

        # Convert history
        history = None
        if hasattr(request, "history") and request.history:
            history = [
                event.to_dict() if hasattr(event, "to_dict") else vars(event)
                for event in request.history
            ]

        return ApprovalDetailResponse(
            approval_id=request.request_id,
            status=request.status.value,
            approval_type=request.approval_type.value,
            requester=request.requester,
            intent_category=intent_category,
            sub_intent=sub_intent,
            workflow_type=workflow_type,
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            created_at=request.created_at,
            expires_at=request.expires_at,
            approved_at=request.approved_at,
            rejected_at=request.rejected_at,
            approved_by=request.approved_by,
            rejected_by=request.rejected_by,
            comment=request.comment,
            history=history,
            metadata=request.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get approval: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get approval: {str(e)}",
        )


@approval_router.post(
    "/{approval_id}/decision",
    response_model=DecisionResponse,
)
async def submit_decision(
    approval_id: str,
    request: SubmitDecisionRequest,
) -> DecisionResponse:
    """
    Submit an approval decision.

    Args:
        approval_id: The approval request ID
        request: Decision details

    Returns:
        DecisionResponse confirming the decision
    """
    controller = get_hitl_controller()

    try:
        # Check request exists
        approval_req = await controller.get_request(approval_id)
        if not approval_req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval request not found: {approval_id}",
            )

        # Process decision
        is_approved = request.decision == ApprovalDecision.APPROVE
        updated_request = await controller.process_approval(
            request_id=approval_id,
            approved=is_approved,
            approver=request.approver,
            comment=request.comment,
        )

        decision_word = "approved" if is_approved else "rejected"
        return DecisionResponse(
            approval_id=approval_id,
            decision=request.decision.value,
            status=updated_request.status.value,
            message=f"Request {decision_word} successfully by {request.approver}",
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to submit decision: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit decision: {str(e)}",
        )


@approval_router.post(
    "/{approval_id}/callback",
    response_model=CallbackResponse,
)
async def teams_callback(
    approval_id: str,
    callback: TeamsCallbackRequest,
) -> CallbackResponse:
    """
    Handle Teams Adaptive Card action callback.

    Called when a user clicks an action button in Teams.

    Args:
        approval_id: The approval request ID
        callback: Teams callback payload

    Returns:
        CallbackResponse confirming the action
    """
    controller = get_hitl_controller()

    try:
        # Map action type to decision
        is_approved = callback.action_type.lower() == "approve"

        # Process decision
        updated_request = await controller.process_approval(
            request_id=approval_id,
            approved=is_approved,
            approver=callback.user_id,
            comment=callback.comment or f"Action via Teams by {callback.user_name or callback.user_id}",
        )

        action_word = "approved" if is_approved else "rejected"
        return CallbackResponse(
            success=True,
            message=f"Request {action_word} by {callback.user_name or callback.user_id}",
            status=updated_request.status.value,
        )

    except ValueError as e:
        return CallbackResponse(
            success=False,
            message=str(e),
            status="error",
        )
    except Exception as e:
        logger.error(f"Teams callback error: {e}", exc_info=True)
        return CallbackResponse(
            success=False,
            message=f"Error processing callback: {str(e)}",
            status="error",
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "approval_router",
    "ApprovalSummary",
    "ApprovalDetailResponse",
    "ApprovalListResponse",
    "SubmitDecisionRequest",
    "DecisionResponse",
    "TeamsCallbackRequest",
    "CallbackResponse",
    "ApprovalDecision",
]
