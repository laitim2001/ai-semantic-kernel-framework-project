"""
Teams Notification Service

Implements Microsoft Teams notification delivery with Adaptive Cards.
Sprint 2 - Story S2-3

Features:
- Adaptive Card formatting for rich notifications
- Console/Mock provider for local development (zero Azure cost)
- Webhook provider for production Teams integration
- Execution success/failure notifications
- Checkpoint approval request notifications
- Audit logging integration

Usage:
    service = TeamsNotificationService(db=session)

    # Send execution success notification
    await service.send_execution_success(execution)

    # Send checkpoint approval request
    await service.send_checkpoint_approval(checkpoint, execution)
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.audit.service import AuditService
from src.infrastructure.database.models.audit_log import AuditAction
from .schemas import (
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
    NotificationType,
    NotificationPriority,
    AdaptiveCardContent,
    FactItem,
    ActionButton,
    ExecutionNotificationContext,
    CheckpointNotificationContext,
)

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    @abstractmethod
    async def send(
        self,
        card: AdaptiveCardContent,
        channel_id: Optional[str] = None,
    ) -> NotificationResponse:
        """Send notification via this provider."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass


class ConsoleNotificationProvider(NotificationProvider):
    """
    Console provider for local development.

    Prints notifications to console instead of sending to Teams.
    Useful for development and testing without Azure costs.
    """

    async def send(
        self,
        card: AdaptiveCardContent,
        channel_id: Optional[str] = None,
    ) -> NotificationResponse:
        """Print notification to console."""
        notification_id = f"console-{uuid4().hex[:8]}"

        # Format console output
        print("\n" + "=" * 60)
        print("📢 TEAMS NOTIFICATION (Console Mode)")
        print("=" * 60)
        print(f"🎯 Title: {card.title}")
        print(f"💬 Message: {card.message}")
        print(f"🎨 Color: #{card.color}")

        if card.facts:
            print("\n📋 Facts:")
            for fact in card.facts:
                print(f"   • {fact.title}: {fact.value}")

        if card.actions:
            print("\n🔘 Actions:")
            for action in card.actions:
                print(f"   • [{action.title}] -> {action.url or action.data}")

        if channel_id:
            print(f"\n📍 Channel: {channel_id}")

        print("=" * 60 + "\n")

        logger.info(f"Console notification sent: {card.title}")

        return NotificationResponse(
            success=True,
            notification_id=notification_id,
            status=NotificationStatus.CONSOLE,
            message="Notification printed to console (development mode)",
            provider=self.get_provider_name(),
        )

    def get_provider_name(self) -> str:
        return "console"


class TeamsWebhookProvider(NotificationProvider):
    """
    Microsoft Teams Webhook provider.

    Sends Adaptive Card notifications via Teams Incoming Webhook.
    """

    def __init__(self, webhook_url: str, timeout: float = 10.0):
        self.webhook_url = webhook_url
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    async def send(
        self,
        card: AdaptiveCardContent,
        channel_id: Optional[str] = None,
    ) -> NotificationResponse:
        """Send notification via Teams webhook."""
        notification_id = f"teams-{uuid4().hex[:8]}"

        # Build Adaptive Card payload
        payload = self._build_adaptive_card(card)

        try:
            response = await self._client.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                logger.info(f"Teams notification sent: {card.title}")
                return NotificationResponse(
                    success=True,
                    notification_id=notification_id,
                    status=NotificationStatus.SENT,
                    message="Notification sent to Teams",
                    provider=self.get_provider_name(),
                )
            else:
                error_msg = f"Teams webhook error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return NotificationResponse(
                    success=False,
                    notification_id=notification_id,
                    status=NotificationStatus.FAILED,
                    message=error_msg,
                    provider=self.get_provider_name(),
                )

        except httpx.HTTPError as e:
            error_msg = f"Teams webhook request failed: {e}"
            logger.error(error_msg)
            return NotificationResponse(
                success=False,
                notification_id=notification_id,
                status=NotificationStatus.FAILED,
                message=error_msg,
                provider=self.get_provider_name(),
            )

    def _build_adaptive_card(self, card: AdaptiveCardContent) -> dict:
        """Build Teams Adaptive Card payload."""
        body = [
            {
                "type": "Container",
                "style": "emphasis",
                "items": [
                    {
                        "type": "TextBlock",
                        "size": "Large",
                        "weight": "Bolder",
                        "text": card.title,
                        "wrap": True,
                        "color": "Accent",
                    }
                ],
            },
            {
                "type": "TextBlock",
                "text": card.message,
                "wrap": True,
                "spacing": "Medium",
            },
        ]

        # Add facts
        if card.facts:
            facts = [{"title": f.title, "value": f.value} for f in card.facts]
            body.append({
                "type": "FactSet",
                "facts": facts,
                "spacing": "Medium",
            })

        # Add image if present
        if card.image_url:
            body.append({
                "type": "Image",
                "url": card.image_url,
                "size": "Medium",
                "spacing": "Medium",
            })

        # Build actions
        actions = []
        for action in card.actions:
            if action.type == "Action.OpenUrl" and action.url:
                actions.append({
                    "type": "Action.OpenUrl",
                    "title": action.title,
                    "url": action.url,
                })
            elif action.type == "Action.Submit" and action.data:
                actions.append({
                    "type": "Action.Submit",
                    "title": action.title,
                    "data": action.data,
                })

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": body,
                        "actions": actions if actions else None,
                    },
                }
            ],
        }

    def get_provider_name(self) -> str:
        return "teams_webhook"

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


class TeamsNotificationService:
    """
    Main service for sending Teams notifications.

    Supports multiple providers:
    - console: Development mode (prints to console)
    - teams_webhook: Production mode (sends to Teams)

    Example:
        service = TeamsNotificationService(db=session)

        # Send custom notification
        await service.send_notification(
            NotificationRequest(
                notification_type=NotificationType.CUSTOM,
                title="Hello Teams!",
                message="This is a test notification",
            )
        )

        # Send execution success
        await service.send_execution_success(execution_context)
    """

    def __init__(
        self,
        db: AsyncSession,
        webhook_url: Optional[str] = None,
        provider_type: Optional[str] = None,
    ):
        """
        Initialize TeamsNotificationService.

        Args:
            db: Database session for audit logging
            webhook_url: Teams webhook URL (optional, uses env var if not provided)
            provider_type: Provider type ('console' or 'teams_webhook')
        """
        self.db = db
        self.audit_service = AuditService(db)

        # Determine provider
        self.webhook_url = webhook_url or os.getenv("TEAMS_WEBHOOK_URL", "")
        provider = provider_type or os.getenv("NOTIFICATION_PROVIDER", "console")

        if provider == "teams_webhook" and self.webhook_url:
            self.provider = TeamsWebhookProvider(self.webhook_url)
        else:
            self.provider = ConsoleNotificationProvider()
            if provider == "teams_webhook" and not self.webhook_url:
                logger.warning("TEAMS_WEBHOOK_URL not set, falling back to console provider")

        # URLs for links in notifications
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.api_url = os.getenv("API_URL", "http://localhost:8080")

    async def send_notification(
        self,
        request: NotificationRequest,
    ) -> NotificationResponse:
        """
        Send a notification.

        Args:
            request: Notification request with title, message, etc.

        Returns:
            NotificationResponse with delivery status
        """
        # Build adaptive card
        card = AdaptiveCardContent(
            title=request.title,
            message=request.message,
            color=self._get_color_for_type(request.notification_type),
            facts=request.facts,
            actions=request.actions,
        )

        # Send via provider
        response = await self.provider.send(card, request.channel_id)

        # Log to audit
        await self._log_notification(request, response)

        return response

    async def send_execution_success(
        self,
        context: ExecutionNotificationContext,
    ) -> NotificationResponse:
        """
        Send workflow execution success notification.

        Args:
            context: Execution context with details

        Returns:
            NotificationResponse
        """
        facts = [
            FactItem(title="Execution ID", value=context.execution_id),
            FactItem(title="Workflow", value=context.workflow_name),
        ]

        if context.duration_seconds:
            facts.append(FactItem(
                title="Duration",
                value=f"{context.duration_seconds:.1f}s"
            ))

        if context.completed_at:
            facts.append(FactItem(
                title="Completed At",
                value=context.completed_at.strftime("%Y-%m-%d %H:%M:%S")
            ))

        actions = [
            ActionButton(
                type="Action.OpenUrl",
                title="View Details",
                url=f"{self.frontend_url}/executions/{context.execution_id}",
            )
        ]

        request = NotificationRequest(
            notification_type=NotificationType.EXECUTION_SUCCESS,
            priority=NotificationPriority.NORMAL,
            title="✅ Workflow Execution Successful",
            message=f"Workflow **{context.workflow_name}** completed successfully",
            facts=facts,
            actions=actions,
            context=context.model_dump(),
        )

        return await self.send_notification(request)

    async def send_execution_failed(
        self,
        context: ExecutionNotificationContext,
    ) -> NotificationResponse:
        """
        Send workflow execution failed notification.

        Args:
            context: Execution context with details

        Returns:
            NotificationResponse
        """
        facts = [
            FactItem(title="Execution ID", value=context.execution_id),
            FactItem(title="Workflow", value=context.workflow_name),
        ]

        if context.error_message:
            # Truncate long error messages
            error_text = context.error_message[:200]
            if len(context.error_message) > 200:
                error_text += "..."
            facts.append(FactItem(title="Error", value=error_text))

        if context.completed_at:
            facts.append(FactItem(
                title="Failed At",
                value=context.completed_at.strftime("%Y-%m-%d %H:%M:%S")
            ))

        actions = [
            ActionButton(
                type="Action.OpenUrl",
                title="View Error Details",
                url=f"{self.frontend_url}/executions/{context.execution_id}",
            ),
        ]

        request = NotificationRequest(
            notification_type=NotificationType.EXECUTION_FAILED,
            priority=NotificationPriority.HIGH,
            title="❌ Workflow Execution Failed",
            message=f"Workflow **{context.workflow_name}** failed with error",
            facts=facts,
            actions=actions,
            context=context.model_dump(),
        )

        return await self.send_notification(request)

    async def send_checkpoint_approval(
        self,
        context: CheckpointNotificationContext,
    ) -> NotificationResponse:
        """
        Send checkpoint approval request notification.

        Args:
            context: Checkpoint context with details

        Returns:
            NotificationResponse
        """
        facts = [
            FactItem(title="Execution ID", value=context.execution_id),
            FactItem(title="Workflow", value=context.workflow_name),
            FactItem(title="Step", value=str(context.step_number)),
        ]

        if context.step_name:
            facts.append(FactItem(title="Step Name", value=context.step_name))

        if context.proposed_action:
            facts.append(FactItem(title="Proposed Action", value=context.proposed_action))

        actions = []

        if context.approve_url:
            actions.append(ActionButton(
                type="Action.OpenUrl",
                title="✅ Approve",
                url=context.approve_url,
            ))

        if context.reject_url:
            actions.append(ActionButton(
                type="Action.OpenUrl",
                title="❌ Reject",
                url=context.reject_url,
            ))

        request = NotificationRequest(
            notification_type=NotificationType.CHECKPOINT_APPROVAL,
            priority=NotificationPriority.HIGH,
            title="⏸️ Workflow Approval Required",
            message=f"Workflow **{context.workflow_name}** is waiting for approval at step {context.step_number}",
            facts=facts,
            actions=actions,
            context=context.model_dump(),
        )

        return await self.send_notification(request)

    async def send_system_alert(
        self,
        title: str,
        message: str,
        severity: str = "warning",
        details: Optional[dict[str, str]] = None,
    ) -> NotificationResponse:
        """
        Send system alert notification.

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
            details: Additional details as key-value pairs

        Returns:
            NotificationResponse
        """
        severity_icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨",
        }

        icon = severity_icons.get(severity, "ℹ️")
        formatted_title = f"{icon} {title}"

        facts = []
        if details:
            for key, value in details.items():
                facts.append(FactItem(title=key, value=value))

        priority = NotificationPriority.URGENT if severity in ["error", "critical"] else NotificationPriority.HIGH

        request = NotificationRequest(
            notification_type=NotificationType.SYSTEM_ALERT,
            priority=priority,
            title=formatted_title,
            message=message,
            facts=facts,
        )

        return await self.send_notification(request)

    def _get_color_for_type(self, notification_type: NotificationType) -> str:
        """Get theme color for notification type."""
        colors = {
            NotificationType.EXECUTION_SUCCESS: "28A745",  # Green
            NotificationType.EXECUTION_FAILED: "DC3545",   # Red
            NotificationType.CHECKPOINT_APPROVAL: "FFC107", # Yellow
            NotificationType.SYSTEM_ALERT: "17A2B8",       # Blue
            NotificationType.CUSTOM: "0078D4",             # Microsoft Blue
        }
        return colors.get(notification_type, "0078D4")

    async def _log_notification(
        self,
        request: NotificationRequest,
        response: NotificationResponse,
    ):
        """Log notification to audit log."""
        try:
            action = (
                AuditAction.NOTIFICATION_SENT
                if response.success
                else AuditAction.NOTIFICATION_FAILED
            )

            await self.audit_service.log(
                action=action,
                resource_type="notification",
                resource_name=f"{request.notification_type.value}-{response.notification_id}",
                changes={
                    "notification_id": response.notification_id,
                    "notification_type": request.notification_type.value,
                    "title": request.title,
                    "provider": response.provider,
                    "status": response.status.value,
                    "success": response.success,
                },
            )
        except Exception as e:
            logger.error(f"Failed to log notification audit: {e}")


def get_notification_service(
    db: AsyncSession,
    webhook_url: Optional[str] = None,
    provider_type: Optional[str] = None,
) -> TeamsNotificationService:
    """
    Factory function to create TeamsNotificationService.

    Args:
        db: Database session
        webhook_url: Optional Teams webhook URL
        provider_type: Optional provider type override

    Returns:
        TeamsNotificationService instance
    """
    return TeamsNotificationService(
        db=db,
        webhook_url=webhook_url,
        provider_type=provider_type,
    )
