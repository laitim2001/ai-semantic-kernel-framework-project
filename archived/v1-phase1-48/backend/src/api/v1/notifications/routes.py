"""
Notifications API Routes
========================

REST API endpoints for Teams notification services.

Sprint 3 - S3-4: Teams Notification Integration

Endpoints:
- POST /notifications/approval - Send approval request
- POST /notifications/completion - Send completion notification
- POST /notifications/error - Send error alert
- POST /notifications/custom - Send custom notification
- GET /notifications/history - Get notification history
- GET /notifications/statistics - Get notification statistics
- GET /notifications/config - Get current configuration
- PUT /notifications/config - Update configuration
- GET /notifications/types - List notification types
- GET /notifications/health - Health check

Author: IPA Platform Team
Created: 2025-11-30
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.notifications.schemas import (
    ApprovalNotificationRequest,
    CompletionNotificationRequest,
    ConfigurationResponse,
    ConfigurationUpdateRequest,
    CustomNotificationRequest,
    ErrorAlertRequest,
    HealthCheckResponse,
    NotificationHistoryResponse,
    NotificationResultResponse,
    NotificationStatisticsResponse,
    NotificationTypesResponse,
)
from src.domain.notifications import (
    NotificationPriority,
    NotificationType,
    TeamsNotificationConfig,
    TeamsNotificationService,
)


router = APIRouter(prefix="/notifications", tags=["notifications"])


# Global service instance (configured at startup)
_notification_service: Optional[TeamsNotificationService] = None


def get_notification_service() -> TeamsNotificationService:
    """Get or create notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = TeamsNotificationService()
    return _notification_service


def set_notification_service(service: TeamsNotificationService) -> None:
    """Set notification service instance (for testing)."""
    global _notification_service
    _notification_service = service


# ============================================================================
# Send Notification Endpoints
# ============================================================================

@router.post("/approval", response_model=NotificationResultResponse)
async def send_approval_notification(request: ApprovalNotificationRequest):
    """
    Send approval request notification to Teams.

    Sends an Adaptive Card with approval request details
    and a button to view and approve the checkpoint.
    """
    service = get_notification_service()

    # Map priority string to enum
    try:
        priority = NotificationPriority(request.priority.lower())
    except ValueError:
        priority = NotificationPriority.NORMAL

    result = await service.send_approval_request(
        checkpoint_id=request.checkpoint_id,
        workflow_name=request.workflow_name,
        content=request.content,
        approver=request.approver,
        priority=priority,
        execution_id=request.execution_id,
    )

    return NotificationResultResponse(
        notification_id=result.notification_id,
        notification_type=result.notification_type.value,
        success=result.success,
        timestamp=result.timestamp,
        message=result.message,
        retry_count=result.retry_count,
        response_code=result.response_code,
    )


@router.post("/completion", response_model=NotificationResultResponse)
async def send_completion_notification(request: CompletionNotificationRequest):
    """
    Send execution completion notification to Teams.

    Sends an Adaptive Card with execution results,
    status, duration, and a link to view details.
    """
    service = get_notification_service()

    result = await service.send_execution_completed(
        execution_id=request.execution_id,
        workflow_name=request.workflow_name,
        status=request.status,
        result_summary=request.result_summary,
        duration=request.duration,
        step_count=request.step_count,
    )

    return NotificationResultResponse(
        notification_id=result.notification_id,
        notification_type=result.notification_type.value,
        success=result.success,
        timestamp=result.timestamp,
        message=result.message,
        retry_count=result.retry_count,
        response_code=result.response_code,
    )


@router.post("/error", response_model=NotificationResultResponse)
async def send_error_alert(request: ErrorAlertRequest):
    """
    Send error alert notification to Teams.

    Sends an Adaptive Card with error details,
    severity indicator, and a link to view the execution.
    """
    service = get_notification_service()

    # Map severity string to enum
    try:
        severity = NotificationPriority(request.severity.lower())
    except ValueError:
        severity = NotificationPriority.HIGH

    result = await service.send_error_alert(
        execution_id=request.execution_id,
        workflow_name=request.workflow_name,
        error_message=request.error_message,
        error_type=request.error_type,
        severity=severity,
    )

    return NotificationResultResponse(
        notification_id=result.notification_id,
        notification_type=result.notification_type.value,
        success=result.success,
        timestamp=result.timestamp,
        message=result.message,
        retry_count=result.retry_count,
        response_code=result.response_code,
    )


@router.post("/custom", response_model=NotificationResultResponse)
async def send_custom_notification(request: CustomNotificationRequest):
    """
    Send custom notification with arbitrary content.

    Allows sending any Adaptive Card content for
    advanced or application-specific notifications.
    """
    service = get_notification_service()

    # Map notification type string to enum
    try:
        notification_type = NotificationType(request.notification_type.lower())
    except ValueError:
        notification_type = NotificationType.INFO_ALERT

    result = await service.send_custom_notification(
        title=request.title,
        body=request.body,
        actions=request.actions,
        notification_type=notification_type,
    )

    return NotificationResultResponse(
        notification_id=result.notification_id,
        notification_type=result.notification_type.value,
        success=result.success,
        timestamp=result.timestamp,
        message=result.message,
        retry_count=result.retry_count,
        response_code=result.response_code,
    )


# ============================================================================
# History & Statistics Endpoints
# ============================================================================

@router.get("/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    notification_type: Optional[str] = Query(None, description="Filter by type"),
    success_only: bool = Query(False, description="Only show successful"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
):
    """
    Get notification history.

    Returns recent notifications with optional filtering
    by type and success status.
    """
    service = get_notification_service()

    # Map type string to enum if provided
    type_filter = None
    if notification_type:
        try:
            type_filter = NotificationType(notification_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid notification type: {notification_type}",
            )

    results = service.get_history(
        notification_type=type_filter,
        success_only=success_only,
        limit=limit,
    )

    return NotificationHistoryResponse(
        results=[
            NotificationResultResponse(
                notification_id=r.notification_id,
                notification_type=r.notification_type.value,
                success=r.success,
                timestamp=r.timestamp,
                message=r.message,
                retry_count=r.retry_count,
                response_code=r.response_code,
            )
            for r in results
        ],
        total=len(results),
    )


@router.get("/statistics", response_model=NotificationStatisticsResponse)
async def get_notification_statistics():
    """
    Get notification statistics.

    Returns success/failure counts, success rate,
    and breakdown by notification type.
    """
    service = get_notification_service()
    stats = service.get_statistics()

    return NotificationStatisticsResponse(
        total=stats["total"],
        successful=stats["successful"],
        failed=stats["failed"],
        success_rate=stats["success_rate"],
        by_type=stats["by_type"],
        rate_limit_current=stats["rate_limit_current"],
        rate_limit_max=stats["rate_limit_max"],
    )


@router.delete("/history")
async def clear_notification_history():
    """
    Clear notification history.

    Returns the number of entries that were cleared.
    """
    service = get_notification_service()
    count = service.clear_history()

    return {"cleared": count, "message": f"Cleared {count} notification history entries"}


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/config", response_model=ConfigurationResponse)
async def get_configuration():
    """
    Get current notification configuration.

    Note: webhook_url is not exposed for security.
    """
    service = get_notification_service()
    config = service.config

    return ConfigurationResponse(
        enabled=config.enabled,
        channel_name=config.channel_name,
        retry_count=config.retry_count,
        retry_delay=config.retry_delay,
        max_notifications_per_minute=config.max_notifications_per_minute,
        app_name=config.app_name,
        app_url=config.app_url,
        theme_color=config.theme_color,
    )


@router.put("/config", response_model=ConfigurationResponse)
async def update_configuration(request: ConfigurationUpdateRequest):
    """
    Update notification configuration.

    Only provided fields will be updated.
    """
    service = get_notification_service()
    current = service.config

    # Create updated config
    new_config = TeamsNotificationConfig(
        webhook_url=request.webhook_url or current.webhook_url,
        enabled=request.enabled if request.enabled is not None else current.enabled,
        channel_name=request.channel_name or current.channel_name,
        retry_count=request.retry_count if request.retry_count is not None else current.retry_count,
        retry_delay=request.retry_delay if request.retry_delay is not None else current.retry_delay,
        max_notifications_per_minute=(
            request.max_notifications_per_minute
            if request.max_notifications_per_minute is not None
            else current.max_notifications_per_minute
        ),
        app_name=request.app_name or current.app_name,
        app_url=request.app_url or current.app_url,
        theme_color=request.theme_color or current.theme_color,
    )

    service.configure(new_config)

    return ConfigurationResponse(
        enabled=new_config.enabled,
        channel_name=new_config.channel_name,
        retry_count=new_config.retry_count,
        retry_delay=new_config.retry_delay,
        max_notifications_per_minute=new_config.max_notifications_per_minute,
        app_name=new_config.app_name,
        app_url=new_config.app_url,
        theme_color=new_config.theme_color,
    )


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/types", response_model=NotificationTypesResponse)
async def list_notification_types():
    """
    List all available notification types.
    """
    return NotificationTypesResponse(
        types=[t.value for t in NotificationType]
    )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Check notification service health.

    Returns service status, configuration state,
    and rate limit availability.
    """
    service = get_notification_service()
    config = service.config
    history = service.get_history(limit=1)

    return HealthCheckResponse(
        service="notifications",
        status="healthy" if service.is_enabled else "disabled",
        enabled=config.enabled,
        webhook_configured=bool(config.webhook_url),
        rate_limit_available=config.max_notifications_per_minute - len(service._notification_timestamps),
        last_notification=history[0].timestamp if history else None,
    )
