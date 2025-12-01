"""
Notifications API Schemas
=========================

Pydantic schemas for notification API endpoints.

Sprint 3 - S3-4: Teams Notification Integration
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================

class ApprovalNotificationRequest(BaseModel):
    """Request to send approval notification."""

    checkpoint_id: str = Field(..., description="Checkpoint ID requiring approval")
    workflow_name: str = Field(..., description="Name of the workflow")
    content: str = Field(..., description="Summary of content awaiting approval")
    approver: Optional[str] = Field(None, description="Specific approver email/name")
    priority: str = Field("normal", description="Priority: low, normal, high, urgent")
    execution_id: Optional[str] = Field(None, description="Related execution ID")


class CompletionNotificationRequest(BaseModel):
    """Request to send execution completion notification."""

    execution_id: str = Field(..., description="Execution ID")
    workflow_name: str = Field(..., description="Name of the workflow")
    status: str = Field(..., description="Execution status: completed, failed, cancelled")
    result_summary: str = Field(..., description="Summary of execution results")
    duration: Optional[float] = Field(None, description="Execution duration in seconds")
    step_count: Optional[int] = Field(None, description="Number of steps executed")


class ErrorAlertRequest(BaseModel):
    """Request to send error alert notification."""

    execution_id: str = Field(..., description="Execution ID where error occurred")
    workflow_name: str = Field(..., description="Name of the workflow")
    error_message: str = Field(..., description="Error description")
    error_type: Optional[str] = Field(None, description="Error type/category")
    severity: str = Field("high", description="Severity: low, normal, high, urgent")


class CustomNotificationRequest(BaseModel):
    """Request to send custom notification."""

    title: str = Field(..., description="Notification title")
    body: List[Dict[str, Any]] = Field(..., description="Adaptive Card body elements")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="Card actions")
    notification_type: str = Field("info_alert", description="Notification type")


class ConfigurationUpdateRequest(BaseModel):
    """Request to update notification configuration."""

    webhook_url: Optional[str] = Field(None, description="Teams webhook URL")
    enabled: Optional[bool] = Field(None, description="Enable/disable notifications")
    channel_name: Optional[str] = Field(None, description="Channel name for reference")
    retry_count: Optional[int] = Field(None, ge=0, le=5, description="Max retry attempts")
    retry_delay: Optional[float] = Field(None, ge=0.1, le=10.0, description="Initial retry delay")
    max_notifications_per_minute: Optional[int] = Field(None, ge=1, le=100, description="Rate limit")
    app_name: Optional[str] = Field(None, description="Application name in cards")
    app_url: Optional[str] = Field(None, description="Application URL for links")
    theme_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Theme color")


# ============================================================================
# Response Schemas
# ============================================================================

class NotificationResultResponse(BaseModel):
    """Response for notification send result."""

    notification_id: UUID
    notification_type: str
    success: bool
    timestamp: datetime
    message: Optional[str] = None
    retry_count: int = 0
    response_code: Optional[int] = None


class NotificationHistoryResponse(BaseModel):
    """Response for notification history."""

    results: List[NotificationResultResponse]
    total: int


class NotificationStatisticsResponse(BaseModel):
    """Response for notification statistics."""

    total: int
    successful: int
    failed: int
    success_rate: float
    by_type: Dict[str, int]
    rate_limit_current: int
    rate_limit_max: int


class ConfigurationResponse(BaseModel):
    """Response for notification configuration."""

    enabled: bool
    channel_name: Optional[str]
    retry_count: int
    retry_delay: float
    max_notifications_per_minute: int
    app_name: str
    app_url: str
    theme_color: str
    # Note: webhook_url is intentionally not exposed for security


class NotificationTypesResponse(BaseModel):
    """Response listing available notification types."""

    types: List[str]


class HealthCheckResponse(BaseModel):
    """Response for notification service health check."""

    service: str = "notifications"
    status: str
    enabled: bool
    webhook_configured: bool
    rate_limit_available: int
    last_notification: Optional[datetime] = None
