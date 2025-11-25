"""
Notifications API Routes

Provides REST API endpoints for notification operations.
Sprint 2 - Story S2-3: Teams Notification Service

Endpoints:
- POST /api/v1/notifications/send           - Send a custom notification
- POST /api/v1/notifications/execution      - Send execution notification
- POST /api/v1/notifications/checkpoint     - Send checkpoint approval request
- POST /api/v1/notifications/alert          - Send system alert
- POST /api/v1/notifications/test           - Test notification endpoint
- GET  /api/v1/notifications/health         - Notification service health check
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.notifications.service import TeamsNotificationService, get_notification_service
from src.domain.notifications.schemas import (
    NotificationRequest,
    NotificationResponse,
    NotificationType,
    NotificationPriority,
    ExecutionNotificationContext,
    CheckpointNotificationContext,
    FactItem,
    ActionButton,
)
from src.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service_dep(
    session: AsyncSession = Depends(get_session)
) -> TeamsNotificationService:
    """Get notification service dependency."""
    return get_notification_service(session)


# ============================================
# Request/Response Models
# ============================================

class SendNotificationRequest(BaseModel):
    """Request to send a custom notification."""
    title: str = Field(..., description="Notification title", max_length=500)
    message: str = Field(..., description="Notification message")
    notification_type: str = Field(
        default="custom",
        description="Notification type (custom, execution_success, execution_failed, etc.)"
    )
    priority: str = Field(default="normal", description="Priority (low, normal, high, urgent)")
    facts: list[dict] = Field(default_factory=list, description="Key-value facts")
    actions: list[dict] = Field(default_factory=list, description="Action buttons")


class ExecutionNotificationRequest(BaseModel):
    """Request for execution notification."""
    execution_id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    workflow_name: str = Field(..., description="Workflow name")
    status: str = Field(..., description="Execution status (success, failed)")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class CheckpointNotificationRequest(BaseModel):
    """Request for checkpoint approval notification."""
    checkpoint_id: str = Field(..., description="Checkpoint ID")
    execution_id: str = Field(..., description="Execution ID")
    workflow_name: str = Field(..., description="Workflow name")
    step_number: int = Field(..., description="Step number")
    step_name: Optional[str] = Field(None, description="Step name")
    proposed_action: Optional[str] = Field(None, description="Proposed action")


class AlertNotificationRequest(BaseModel):
    """Request for system alert notification."""
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: str = Field(default="warning", description="Severity (info, warning, error, critical)")
    details: Optional[dict] = Field(None, description="Additional details")


class TestNotificationRequest(BaseModel):
    """Request to test notification."""
    title: str = Field(default="🧪 Test Notification", description="Test title")
    message: str = Field(default="This is a test notification from IPA Platform", description="Test message")


# ============================================
# Endpoints
# ============================================

@router.get("/health")
async def notification_health(
    service: TeamsNotificationService = Depends(get_notification_service_dep),
):
    """
    Notification service health check.

    Returns:
        Health status and provider information
    """
    return {
        "status": "healthy",
        "service": "notifications",
        "provider": service.provider.get_provider_name(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    service: TeamsNotificationService = Depends(get_notification_service_dep),
):
    """
    Send a custom notification.

    This endpoint allows sending custom notifications with
    arbitrary title, message, facts, and actions.
    """
    try:
        # Convert request to NotificationRequest
        facts = [FactItem(**f) for f in request.facts] if request.facts else []
        actions = [ActionButton(**a) for a in request.actions] if request.actions else []

        notification_request = NotificationRequest(
            notification_type=NotificationType(request.notification_type),
            priority=NotificationPriority(request.priority),
            title=request.title,
            message=request.message,
            facts=facts,
            actions=actions,
        )

        response = await service.send_notification(notification_request)
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notification: {str(e)}"
        )


@router.post("/execution", response_model=NotificationResponse)
async def send_execution_notification(
    request: ExecutionNotificationRequest,
    service: TeamsNotificationService = Depends(get_notification_service_dep),
):
    """
    Send execution notification (success or failure).

    Automatically formats the notification based on execution status.
    """
    try:
        context = ExecutionNotificationContext(
            execution_id=request.execution_id,
            workflow_id=request.workflow_id,
            workflow_name=request.workflow_name,
            status=request.status,
            duration_seconds=request.duration_seconds,
            error_message=request.error_message,
            completed_at=datetime.utcnow(),
        )

        if request.status.lower() in ["success", "completed"]:
            response = await service.send_execution_success(context)
        else:
            response = await service.send_execution_failed(context)

        return response

    except Exception as e:
        logger.error(f"Error sending execution notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notification: {str(e)}"
        )


@router.post("/checkpoint", response_model=NotificationResponse)
async def send_checkpoint_notification(
    request: CheckpointNotificationRequest,
    service: TeamsNotificationService = Depends(get_notification_service_dep),
):
    """
    Send checkpoint approval request notification.

    Includes approve/reject action buttons when URLs are configured.
    """
    try:
        # Build approval URLs
        api_url = service.api_url
        approve_url = f"{api_url}/api/v1/checkpoints/{request.checkpoint_id}/approve"
        reject_url = f"{api_url}/api/v1/checkpoints/{request.checkpoint_id}/reject"

        context = CheckpointNotificationContext(
            checkpoint_id=request.checkpoint_id,
            execution_id=request.execution_id,
            workflow_name=request.workflow_name,
            step_number=request.step_number,
            step_name=request.step_name,
            proposed_action=request.proposed_action,
            approve_url=approve_url,
            reject_url=reject_url,
        )

        response = await service.send_checkpoint_approval(context)
        return response

    except Exception as e:
        logger.error(f"Error sending checkpoint notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notification: {str(e)}"
        )


@router.post("/alert", response_model=NotificationResponse)
async def send_alert_notification(
    request: AlertNotificationRequest,
    service: TeamsNotificationService = Depends(get_notification_service_dep),
):
    """
    Send system alert notification.

    Supports different severity levels (info, warning, error, critical).
    """
    try:
        # Convert details dict to string dict if needed
        details = None
        if request.details:
            details = {k: str(v) for k, v in request.details.items()}

        response = await service.send_system_alert(
            title=request.title,
            message=request.message,
            severity=request.severity,
            details=details,
        )
        return response

    except Exception as e:
        logger.error(f"Error sending alert notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notification: {str(e)}"
        )


@router.post("/test", response_model=NotificationResponse)
async def test_notification(
    request: TestNotificationRequest = TestNotificationRequest(),
    service: TeamsNotificationService = Depends(get_notification_service_dep),
):
    """
    Test notification endpoint.

    Sends a test notification to verify the notification service is working.
    """
    try:
        notification_request = NotificationRequest(
            notification_type=NotificationType.CUSTOM,
            priority=NotificationPriority.NORMAL,
            title=request.title,
            message=request.message,
            facts=[
                FactItem(title="Provider", value=service.provider.get_provider_name()),
                FactItem(title="Timestamp", value=datetime.utcnow().isoformat()),
            ],
            actions=[
                ActionButton(
                    type="Action.OpenUrl",
                    title="View Documentation",
                    url="https://docs.ipa-platform.local",
                )
            ],
        )

        response = await service.send_notification(notification_request)
        return response

    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending test notification: {str(e)}"
        )
