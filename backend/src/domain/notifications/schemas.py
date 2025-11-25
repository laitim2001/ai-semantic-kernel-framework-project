"""
Notification Schemas (Pydantic Models)

Sprint 2 - Story S2-3: Teams Notification Service
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CONSOLE = "console"  # For local development


class NotificationType(str, Enum):
    """Types of notifications."""
    EXECUTION_SUCCESS = "execution_success"
    EXECUTION_FAILED = "execution_failed"
    CHECKPOINT_APPROVAL = "checkpoint_approval"
    SYSTEM_ALERT = "system_alert"
    CUSTOM = "custom"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class FactItem(BaseModel):
    """A fact item for Adaptive Cards."""
    title: str = Field(..., description="Fact title/label")
    value: str = Field(..., description="Fact value")


class ActionButton(BaseModel):
    """Action button for Adaptive Cards."""
    type: str = Field(default="Action.OpenUrl", description="Action type")
    title: str = Field(..., description="Button text")
    url: Optional[str] = Field(None, description="URL for OpenUrl action")
    data: Optional[dict[str, Any]] = Field(None, description="Data for Submit action")


class AdaptiveCardContent(BaseModel):
    """Adaptive Card content for Teams notifications."""
    title: str = Field(..., description="Card title", max_length=500)
    message: str = Field(..., description="Main message text")
    color: str = Field(default="0078D4", description="Theme color (hex without #)")
    facts: list[FactItem] = Field(default_factory=list, description="Key-value facts")
    actions: list[ActionButton] = Field(default_factory=list, description="Action buttons")
    image_url: Optional[str] = Field(None, description="Optional image URL")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Workflow Execution Complete",
                "message": "Your workflow has finished processing",
                "color": "28A745",
                "facts": [
                    {"title": "Duration", "value": "2m 30s"},
                    {"title": "Status", "value": "Success"}
                ],
                "actions": [
                    {"type": "Action.OpenUrl", "title": "View Details", "url": "https://example.com"}
                ]
            }
        }
    )


class NotificationRequest(BaseModel):
    """Request to send a notification."""
    notification_type: NotificationType = Field(..., description="Type of notification")
    priority: NotificationPriority = Field(
        default=NotificationPriority.NORMAL,
        description="Notification priority"
    )
    title: str = Field(..., description="Notification title", max_length=500)
    message: str = Field(..., description="Notification message")
    channel_id: Optional[str] = Field(None, description="Teams channel ID")
    recipient_email: Optional[str] = Field(None, description="Recipient email for DM")
    facts: list[FactItem] = Field(default_factory=list, description="Additional facts")
    actions: list[ActionButton] = Field(default_factory=list, description="Action buttons")
    context: Optional[dict[str, Any]] = Field(None, description="Additional context data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notification_type": "execution_success",
                "priority": "normal",
                "title": "✅ Workflow Complete",
                "message": "Data processing workflow finished successfully",
                "facts": [
                    {"title": "Execution ID", "value": "exec-123"},
                    {"title": "Duration", "value": "5 minutes"}
                ],
                "actions": [
                    {"type": "Action.OpenUrl", "title": "View Results", "url": "https://example.com/results"}
                ]
            }
        }
    )


class NotificationResponse(BaseModel):
    """Response after sending a notification."""
    success: bool = Field(..., description="Whether notification was sent successfully")
    notification_id: str = Field(..., description="Unique notification ID")
    status: NotificationStatus = Field(..., description="Current notification status")
    message: Optional[str] = Field(None, description="Status message")
    provider: str = Field(..., description="Notification provider used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "notification_id": "notif-abc123",
                "status": "sent",
                "message": "Notification delivered to Teams",
                "provider": "teams_webhook",
                "timestamp": "2025-01-01T00:00:00Z"
            }
        }
    )


class ExecutionNotificationContext(BaseModel):
    """Context for execution-related notifications."""
    execution_id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    workflow_name: str = Field(..., description="Workflow name")
    status: str = Field(..., description="Execution status")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class CheckpointNotificationContext(BaseModel):
    """Context for checkpoint approval notifications."""
    checkpoint_id: str = Field(..., description="Checkpoint ID")
    execution_id: str = Field(..., description="Execution ID")
    workflow_name: str = Field(..., description="Workflow name")
    step_number: int = Field(..., description="Current step number")
    step_name: Optional[str] = Field(None, description="Step name")
    proposed_action: Optional[str] = Field(None, description="Proposed action description")
    approve_url: Optional[str] = Field(None, description="Approval URL")
    reject_url: Optional[str] = Field(None, description="Rejection URL")


class TeamsWebhookConfig(BaseModel):
    """Configuration for Teams webhook."""
    webhook_url: str = Field(..., description="Teams incoming webhook URL")
    channel_name: Optional[str] = Field(None, description="Channel name for logging")
    enabled: bool = Field(default=True, description="Whether this webhook is enabled")


class NotificationConfig(BaseModel):
    """Overall notification configuration."""
    provider: str = Field(default="console", description="Provider: console, teams_webhook")
    teams_webhook_url: Optional[str] = Field(None, description="Teams webhook URL")
    default_channel: Optional[str] = Field(None, description="Default Teams channel")
    frontend_url: Optional[str] = Field(None, description="Frontend URL for links")
    api_url: Optional[str] = Field(None, description="API URL for callbacks")
