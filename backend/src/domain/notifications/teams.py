"""
Teams Notification Service
==========================

Microsoft Teams notification service using Adaptive Cards for rich messaging.
Supports approval requests, execution notifications, and error alerts.

Sprint 3 - S3-4: Teams Notification Integration

Features:
- Adaptive Card v1.4 support
- Multiple notification types (approval, completion, error)
- Configurable webhooks per workflow/channel
- Retry mechanism for failed deliveries
- Notification templating

Author: IPA Platform Team
Created: 2025-11-30
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4
import asyncio


class NotificationType(str, Enum):
    """Notification type enumeration."""

    # Approval notifications
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_REMINDER = "approval_reminder"

    # Execution notifications
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"

    # Alert notifications
    ERROR_ALERT = "error_alert"
    WARNING_ALERT = "warning_alert"
    INFO_ALERT = "info_alert"

    # System notifications
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_STATUS = "system_status"


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationError(Exception):
    """Exception raised for notification failures."""

    def __init__(
        self,
        message: str,
        notification_type: Optional[NotificationType] = None,
        retry_count: int = 0,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.notification_type = notification_type
        self.retry_count = retry_count
        self.original_error = original_error


@dataclass
class TeamsNotificationConfig:
    """Teams notification configuration."""

    webhook_url: str
    enabled: bool = True
    channel_name: Optional[str] = None
    retry_count: int = 3
    retry_delay: float = 1.0  # seconds
    timeout: float = 10.0  # seconds

    # Rate limiting
    max_notifications_per_minute: int = 30

    # Customization
    app_name: str = "IPA Platform"
    app_url: str = "https://app.ipa-platform.com"
    theme_color: str = "#0078D4"  # Microsoft Blue


@dataclass
class NotificationResult:
    """Result of a notification attempt."""

    notification_id: UUID
    notification_type: NotificationType
    success: bool
    timestamp: datetime

    # Optional details
    message: Optional[str] = None
    retry_count: int = 0
    response_code: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "notification_id": str(self.notification_id),
            "notification_type": self.notification_type.value,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "retry_count": self.retry_count,
            "response_code": self.response_code,
        }


@dataclass
class TeamsCard:
    """Adaptive Card data structure."""

    title: str
    body: List[Dict[str, Any]]
    actions: List[Dict[str, Any]] = field(default_factory=list)
    theme_color: str = "#0078D4"

    def to_payload(self) -> Dict[str, Any]:
        """Convert to Teams webhook payload."""
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": self.body,
                        "actions": self.actions if self.actions else None,
                    },
                }
            ],
        }


class TeamsNotificationService:
    """
    Microsoft Teams notification service.

    Sends notifications to Teams channels via incoming webhooks
    using Adaptive Cards for rich content display.
    """

    def __init__(
        self,
        config: Optional[TeamsNotificationConfig] = None,
        http_client: Optional[Any] = None,
    ):
        """
        Initialize Teams notification service.

        Args:
            config: Teams notification configuration
            http_client: Optional HTTP client for sending requests (for testing)
        """
        self._config = config or TeamsNotificationConfig(
            webhook_url="",
            enabled=False,
        )
        self._http_client = http_client

        # Rate limiting
        self._notification_timestamps: List[datetime] = []

        # Event handlers
        self._on_success_handlers: List[Callable] = []
        self._on_failure_handlers: List[Callable] = []

        # Notification history (for testing/debugging)
        self._history: List[NotificationResult] = []
        self._max_history: int = 100

    @property
    def config(self) -> TeamsNotificationConfig:
        """Get current configuration."""
        return self._config

    @property
    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self._config.enabled and bool(self._config.webhook_url)

    def configure(self, config: TeamsNotificationConfig) -> None:
        """Update configuration."""
        self._config = config

    async def send_approval_request(
        self,
        checkpoint_id: str,
        workflow_name: str,
        content: str,
        approver: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        execution_id: Optional[str] = None,
    ) -> NotificationResult:
        """
        Send approval request notification.

        Args:
            checkpoint_id: Checkpoint requiring approval
            workflow_name: Name of the workflow
            content: Summary of content awaiting approval
            approver: Optional specific approver
            priority: Notification priority
            execution_id: Optional execution ID

        Returns:
            NotificationResult with send status
        """
        card = self._build_approval_card(
            checkpoint_id=checkpoint_id,
            workflow_name=workflow_name,
            content=content,
            approver=approver,
            priority=priority,
        )

        return await self._send_card(
            card=card,
            notification_type=NotificationType.APPROVAL_REQUEST,
        )

    async def send_execution_completed(
        self,
        execution_id: str,
        workflow_name: str,
        status: str,
        result_summary: str,
        duration: Optional[float] = None,
        step_count: Optional[int] = None,
    ) -> NotificationResult:
        """
        Send execution completed notification.

        Args:
            execution_id: Execution ID
            workflow_name: Name of the workflow
            status: Final execution status
            result_summary: Summary of results
            duration: Optional execution duration in seconds
            step_count: Optional number of steps executed

        Returns:
            NotificationResult with send status
        """
        card = self._build_completion_card(
            execution_id=execution_id,
            workflow_name=workflow_name,
            status=status,
            result_summary=result_summary,
            duration=duration,
            step_count=step_count,
        )

        notification_type = (
            NotificationType.EXECUTION_COMPLETED
            if status == "completed"
            else NotificationType.EXECUTION_FAILED
        )

        return await self._send_card(
            card=card,
            notification_type=notification_type,
        )

    async def send_error_alert(
        self,
        execution_id: str,
        workflow_name: str,
        error_message: str,
        error_type: Optional[str] = None,
        severity: NotificationPriority = NotificationPriority.HIGH,
    ) -> NotificationResult:
        """
        Send error alert notification.

        Args:
            execution_id: Execution ID where error occurred
            workflow_name: Name of the workflow
            error_message: Error description
            error_type: Optional error type/category
            severity: Alert severity level

        Returns:
            NotificationResult with send status
        """
        card = self._build_error_card(
            execution_id=execution_id,
            workflow_name=workflow_name,
            error_message=error_message,
            error_type=error_type,
            severity=severity,
        )

        return await self._send_card(
            card=card,
            notification_type=NotificationType.ERROR_ALERT,
        )

    async def send_custom_notification(
        self,
        title: str,
        body: List[Dict[str, Any]],
        actions: Optional[List[Dict[str, Any]]] = None,
        notification_type: NotificationType = NotificationType.INFO_ALERT,
    ) -> NotificationResult:
        """
        Send custom notification with arbitrary content.

        Args:
            title: Card title
            body: Adaptive Card body elements
            actions: Optional card actions
            notification_type: Type of notification

        Returns:
            NotificationResult with send status
        """
        card = TeamsCard(
            title=title,
            body=body,
            actions=actions or [],
            theme_color=self._config.theme_color,
        )

        return await self._send_card(
            card=card,
            notification_type=notification_type,
        )

    def _build_approval_card(
        self,
        checkpoint_id: str,
        workflow_name: str,
        content: str,
        approver: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> TeamsCard:
        """Build approval request Adaptive Card."""
        priority_emoji = {
            NotificationPriority.LOW: "📋",
            NotificationPriority.NORMAL: "🔔",
            NotificationPriority.HIGH: "⚡",
            NotificationPriority.URGENT: "🚨",
        }.get(priority, "🔔")

        body = [
            {
                "type": "TextBlock",
                "text": f"{priority_emoji} 審批請求",
                "weight": "bolder",
                "size": "large",
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "工作流", "value": workflow_name},
                    {"title": "優先級", "value": priority.value},
                ],
            },
        ]

        if approver:
            body[1]["facts"].append({"title": "審批人", "value": approver})

        body.extend([
            {
                "type": "TextBlock",
                "text": "待審批內容:",
                "weight": "bolder",
                "spacing": "medium",
            },
            {
                "type": "TextBlock",
                "text": content[:500],  # Limit content length
                "wrap": True,
            },
        ])

        actions = [
            {
                "type": "Action.OpenUrl",
                "title": "查看詳情並審批",
                "url": f"{self._config.app_url}/checkpoints/{checkpoint_id}",
            },
        ]

        return TeamsCard(
            title="審批請求",
            body=body,
            actions=actions,
            theme_color="#FFA500" if priority == NotificationPriority.URGENT else self._config.theme_color,
        )

    def _build_completion_card(
        self,
        execution_id: str,
        workflow_name: str,
        status: str,
        result_summary: str,
        duration: Optional[float] = None,
        step_count: Optional[int] = None,
    ) -> TeamsCard:
        """Build execution completion Adaptive Card."""
        status_config = {
            "completed": ("✅", "Good", "#28A745"),
            "failed": ("❌", "Attention", "#DC3545"),
            "cancelled": ("⚠️", "Warning", "#FFC107"),
        }

        emoji, color_type, theme = status_config.get(
            status, ("ℹ️", "Default", self._config.theme_color)
        )

        facts = [
            {"title": "工作流", "value": workflow_name},
            {"title": "狀態", "value": f"{emoji} {status}"},
            {"title": "執行 ID", "value": execution_id[:8] + "..."},
        ]

        if duration is not None:
            if duration < 60:
                duration_str = f"{duration:.1f} 秒"
            else:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes} 分 {seconds} 秒"
            facts.append({"title": "執行時間", "value": duration_str})

        if step_count is not None:
            facts.append({"title": "執行步驟", "value": str(step_count)})

        body = [
            {
                "type": "TextBlock",
                "text": f"{emoji} 工作流執行完成",
                "weight": "bolder",
                "size": "large",
                "color": color_type,
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
            {
                "type": "TextBlock",
                "text": "執行結果:",
                "weight": "bolder",
                "spacing": "medium",
            },
            {
                "type": "TextBlock",
                "text": result_summary[:300],
                "wrap": True,
            },
        ]

        actions = [
            {
                "type": "Action.OpenUrl",
                "title": "查看詳情",
                "url": f"{self._config.app_url}/executions/{execution_id}",
            },
        ]

        return TeamsCard(
            title="執行完成",
            body=body,
            actions=actions,
            theme_color=theme,
        )

    def _build_error_card(
        self,
        execution_id: str,
        workflow_name: str,
        error_message: str,
        error_type: Optional[str] = None,
        severity: NotificationPriority = NotificationPriority.HIGH,
    ) -> TeamsCard:
        """Build error alert Adaptive Card."""
        severity_config = {
            NotificationPriority.LOW: ("ℹ️", "#17A2B8"),
            NotificationPriority.NORMAL: ("⚠️", "#FFC107"),
            NotificationPriority.HIGH: ("🚨", "#DC3545"),
            NotificationPriority.URGENT: ("🔥", "#8B0000"),
        }

        emoji, theme = severity_config.get(
            severity, ("🚨", "#DC3545")
        )

        facts = [
            {"title": "工作流", "value": workflow_name},
            {"title": "嚴重程度", "value": severity.value},
        ]

        if error_type:
            facts.append({"title": "錯誤類型", "value": error_type})

        body = [
            {
                "type": "TextBlock",
                "text": f"{emoji} 執行錯誤",
                "weight": "bolder",
                "size": "large",
                "color": "attention",
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
            {
                "type": "TextBlock",
                "text": "錯誤信息:",
                "weight": "bolder",
                "spacing": "medium",
            },
            {
                "type": "TextBlock",
                "text": error_message[:200],
                "wrap": True,
                "color": "attention",
            },
        ]

        actions = [
            {
                "type": "Action.OpenUrl",
                "title": "查看詳情",
                "url": f"{self._config.app_url}/executions/{execution_id}",
            },
        ]

        return TeamsCard(
            title="錯誤告警",
            body=body,
            actions=actions,
            theme_color=theme,
        )

    async def _send_card(
        self,
        card: TeamsCard,
        notification_type: NotificationType,
    ) -> NotificationResult:
        """
        Send Adaptive Card to Teams webhook.

        Args:
            card: TeamsCard to send
            notification_type: Type of notification

        Returns:
            NotificationResult with send status
        """
        notification_id = uuid4()
        timestamp = datetime.utcnow()

        # Check if enabled
        if not self.is_enabled:
            result = NotificationResult(
                notification_id=notification_id,
                notification_type=notification_type,
                success=False,
                timestamp=timestamp,
                message="Notifications are disabled",
            )
            self._add_to_history(result)
            return result

        # Check rate limit
        if not self._check_rate_limit():
            result = NotificationResult(
                notification_id=notification_id,
                notification_type=notification_type,
                success=False,
                timestamp=timestamp,
                message="Rate limit exceeded",
            )
            self._add_to_history(result)
            return result

        # Send with retry
        payload = card.to_payload()
        last_error: Optional[Exception] = None

        for attempt in range(self._config.retry_count):
            try:
                response_code = await self._send_request(payload)

                if response_code == 200:
                    result = NotificationResult(
                        notification_id=notification_id,
                        notification_type=notification_type,
                        success=True,
                        timestamp=timestamp,
                        message="Notification sent successfully",
                        retry_count=attempt,
                        response_code=response_code,
                    )
                    self._add_to_history(result)
                    await self._trigger_success_handlers(result)
                    return result

                last_error = Exception(f"HTTP {response_code}")

            except Exception as e:
                last_error = e

            # Wait before retry (exponential backoff)
            if attempt < self._config.retry_count - 1:
                delay = self._config.retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        # All retries failed
        result = NotificationResult(
            notification_id=notification_id,
            notification_type=notification_type,
            success=False,
            timestamp=timestamp,
            message=f"Failed after {self._config.retry_count} attempts: {last_error}",
            retry_count=self._config.retry_count,
        )
        self._add_to_history(result)
        await self._trigger_failure_handlers(result)
        return result

    async def _send_request(self, payload: Dict[str, Any]) -> int:
        """
        Send HTTP request to Teams webhook.

        Args:
            payload: JSON payload to send

        Returns:
            HTTP response status code
        """
        # Use mock client for testing
        if self._http_client is not None:
            if asyncio.iscoroutinefunction(self._http_client):
                return await self._http_client(payload)
            return self._http_client(payload)

        # Real HTTP client (requires httpx)
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._config.webhook_url,
                    json=payload,
                    timeout=self._config.timeout,
                )
                return response.status_code
        except ImportError:
            raise NotificationError(
                "httpx is required for Teams notifications. "
                "Install with: pip install httpx"
            )

    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows sending."""
        now = datetime.utcnow()

        # Remove old timestamps
        cutoff = datetime.utcnow()
        self._notification_timestamps = [
            ts for ts in self._notification_timestamps
            if (now - ts).total_seconds() < 60
        ]

        # Check limit
        if len(self._notification_timestamps) >= self._config.max_notifications_per_minute:
            return False

        # Record this attempt
        self._notification_timestamps.append(now)
        return True

    def _add_to_history(self, result: NotificationResult) -> None:
        """Add result to history."""
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(
        self,
        notification_type: Optional[NotificationType] = None,
        success_only: bool = False,
        limit: int = 50,
    ) -> List[NotificationResult]:
        """Get notification history."""
        results = self._history.copy()

        if notification_type:
            results = [r for r in results if r.notification_type == notification_type]

        if success_only:
            results = [r for r in results if r.success]

        return results[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get notification statistics."""
        total = len(self._history)
        successful = sum(1 for r in self._history if r.success)
        failed = total - successful

        by_type: Dict[str, int] = {}
        for result in self._history:
            type_name = result.notification_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "by_type": by_type,
            "rate_limit_current": len(self._notification_timestamps),
            "rate_limit_max": self._config.max_notifications_per_minute,
        }

    def on_success(self, handler: Callable[[NotificationResult], None]) -> None:
        """Register success handler."""
        self._on_success_handlers.append(handler)

    def on_failure(self, handler: Callable[[NotificationResult], None]) -> None:
        """Register failure handler."""
        self._on_failure_handlers.append(handler)

    async def _trigger_success_handlers(self, result: NotificationResult) -> None:
        """Trigger all success handlers."""
        for handler in self._on_success_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(result)
                else:
                    handler(result)
            except Exception:
                pass  # Don't let handlers break notification flow

    async def _trigger_failure_handlers(self, result: NotificationResult) -> None:
        """Trigger all failure handlers."""
        for handler in self._on_failure_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(result)
                else:
                    handler(result)
            except Exception:
                pass

    def clear_history(self) -> int:
        """Clear notification history. Returns number of entries cleared."""
        count = len(self._history)
        self._history = []
        return count
