"""
Notification Service Implementation

Provides notification services for approval workflow, including Teams Webhook integration.

Sprint 97: Story 97-3 - Implement Approval Webhook (Phase 28)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..intent_router.models import RiskLevel
from .controller import ApprovalRequest, ApprovalStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Teams MessageCard Templates
# =============================================================================


@dataclass
class TeamsMessageCard:
    """
    Microsoft Teams MessageCard structure.

    Represents an Outlook Actionable Message card for Teams.

    Attributes:
        title: Card title
        summary: Card summary
        theme_color: Hex color code for card accent
        sections: List of card sections
        potential_actions: List of available actions
    """

    title: str
    summary: str
    theme_color: str = "0078D7"  # Microsoft Blue
    sections: List[Dict[str, Any]] = field(default_factory=list)
    potential_actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Teams MessageCard JSON format."""
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": self.summary,
            "themeColor": self.theme_color,
            "title": self.title,
            "sections": self.sections,
            "potentialAction": self.potential_actions,
        }


class TeamsCardBuilder:
    """
    Builder for creating Teams MessageCard objects.

    Provides fluent API for constructing approval request cards.

    Example:
        >>> card = TeamsCardBuilder()
        ...     .with_title("審批請求")
        ...     .with_theme_color("FF0000")
        ...     .add_fact("類別", "incident")
        ...     .add_approve_button("https://api.example.com/approve/123")
        ...     .add_reject_button("https://api.example.com/reject/123")
        ...     .build()
    """

    # Risk level color mapping
    RISK_COLORS: Dict[RiskLevel, str] = {
        RiskLevel.LOW: "00FF00",      # Green
        RiskLevel.MEDIUM: "FFA500",   # Orange
        RiskLevel.HIGH: "FF0000",     # Red
        RiskLevel.CRITICAL: "8B0000", # Dark Red
    }

    def __init__(self) -> None:
        """Initialize the card builder."""
        self._title = "審批請求"
        self._summary = "需要您的審批"
        self._theme_color = "0078D7"
        self._sections: List[Dict[str, Any]] = []
        self._actions: List[Dict[str, Any]] = []
        self._current_section: Optional[Dict[str, Any]] = None

    def with_title(self, title: str) -> "TeamsCardBuilder":
        """Set card title."""
        self._title = title
        return self

    def with_summary(self, summary: str) -> "TeamsCardBuilder":
        """Set card summary."""
        self._summary = summary
        return self

    def with_theme_color(self, color: str) -> "TeamsCardBuilder":
        """Set theme color (hex without #)."""
        self._theme_color = color.lstrip("#")
        return self

    def with_risk_level_color(self, risk_level: RiskLevel) -> "TeamsCardBuilder":
        """Set theme color based on risk level."""
        self._theme_color = self.RISK_COLORS.get(risk_level, "0078D7")
        return self

    def add_section(
        self,
        activity_title: str,
        activity_subtitle: Optional[str] = None,
        activity_image: Optional[str] = None,
    ) -> "TeamsCardBuilder":
        """
        Start a new section.

        Args:
            activity_title: Section title
            activity_subtitle: Optional subtitle
            activity_image: Optional image URL
        """
        self._current_section = {
            "activityTitle": activity_title,
            "facts": [],
        }
        if activity_subtitle:
            self._current_section["activitySubtitle"] = activity_subtitle
        if activity_image:
            self._current_section["activityImage"] = activity_image
        self._sections.append(self._current_section)
        return self

    def add_fact(self, name: str, value: str) -> "TeamsCardBuilder":
        """
        Add a fact to the current section.

        Args:
            name: Fact label
            value: Fact value
        """
        if not self._current_section:
            self.add_section("詳細資訊")
        self._current_section["facts"].append({"name": name, "value": value})
        return self

    def add_text(self, text: str, is_markdown: bool = False) -> "TeamsCardBuilder":
        """
        Add text to the current section.

        Args:
            text: Text content
            is_markdown: Whether text contains markdown
        """
        if not self._current_section:
            self.add_section("詳細資訊")
        self._current_section["text"] = text
        if is_markdown:
            self._current_section["markdown"] = True
        return self

    def add_approve_button(
        self,
        target_url: str,
        button_text: str = "批准",
    ) -> "TeamsCardBuilder":
        """
        Add approve action button.

        Args:
            target_url: URL to call when button is clicked
            button_text: Button label
        """
        self._actions.append({
            "@type": "HttpPOST",
            "name": button_text,
            "target": target_url,
            "body": json.dumps({"action": "approve"}),
            "headers": [
                {"name": "Content-Type", "value": "application/json"}
            ],
        })
        return self

    def add_reject_button(
        self,
        target_url: str,
        button_text: str = "拒絕",
    ) -> "TeamsCardBuilder":
        """
        Add reject action button.

        Args:
            target_url: URL to call when button is clicked
            button_text: Button label
        """
        self._actions.append({
            "@type": "HttpPOST",
            "name": button_text,
            "target": target_url,
            "body": json.dumps({"action": "reject"}),
            "headers": [
                {"name": "Content-Type", "value": "application/json"}
            ],
        })
        return self

    def add_open_url_button(
        self,
        url: str,
        button_text: str = "查看詳情",
    ) -> "TeamsCardBuilder":
        """
        Add open URL action button.

        Args:
            url: URL to open
            button_text: Button label
        """
        self._actions.append({
            "@type": "OpenUri",
            "name": button_text,
            "targets": [
                {"os": "default", "uri": url}
            ],
        })
        return self

    def build(self) -> TeamsMessageCard:
        """Build and return the TeamsMessageCard."""
        return TeamsMessageCard(
            title=self._title,
            summary=self._summary,
            theme_color=self._theme_color,
            sections=self._sections,
            potential_actions=self._actions,
        )


# =============================================================================
# Teams Notification Service
# =============================================================================


@dataclass
class NotificationResult:
    """
    Result of a notification operation.

    Attributes:
        success: Whether notification was sent successfully
        message: Status message
        response_code: HTTP response code (if applicable)
        error: Error message if failed
    """

    success: bool
    message: str = ""
    response_code: Optional[int] = None
    error: Optional[str] = None


class TeamsNotificationService:
    """
    Microsoft Teams notification service using Incoming Webhooks.

    Sends approval request notifications to Teams channels with actionable cards.

    Configuration:
        - webhook_url: Teams Incoming Webhook URL
        - callback_base_url: Base URL for approval callback endpoints
        - timeout: HTTP request timeout in seconds

    Example:
        >>> service = TeamsNotificationService(
        ...     webhook_url="https://outlook.office.com/webhook/...",
        ...     callback_base_url="https://api.example.com/v1/approvals",
        ... )
        >>> result = await service.send_approval_request(request)
        >>> print(result.success)  # True
    """

    DEFAULT_TIMEOUT = 30.0  # seconds

    def __init__(
        self,
        webhook_url: str,
        callback_base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        Initialize Teams notification service.

        Args:
            webhook_url: Teams Incoming Webhook URL
            callback_base_url: Base URL for approval callbacks
            timeout: HTTP request timeout
            http_client: Optional custom HTTP client
        """
        self.webhook_url = webhook_url
        self.callback_base_url = callback_base_url.rstrip("/")
        self.timeout = timeout
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def send_approval_request(self, request: ApprovalRequest) -> NotificationResult:
        """
        Send approval request notification to Teams.

        Args:
            request: ApprovalRequest to notify about

        Returns:
            NotificationResult with send status
        """
        try:
            # Build the card
            card = self._build_approval_request_card(request)

            # Send to Teams
            client = await self._get_client()
            response = await client.post(
                self.webhook_url,
                json=card.to_dict(),
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                logger.info(f"Sent approval request notification: {request.request_id}")
                return NotificationResult(
                    success=True,
                    message="Notification sent successfully",
                    response_code=response.status_code,
                )
            else:
                logger.warning(
                    f"Teams notification failed: {response.status_code} - {response.text}"
                )
                return NotificationResult(
                    success=False,
                    message="Notification failed",
                    response_code=response.status_code,
                    error=response.text,
                )

        except httpx.TimeoutException as e:
            logger.error(f"Teams notification timeout: {e}")
            return NotificationResult(
                success=False,
                error="Request timeout",
            )
        except Exception as e:
            logger.error(f"Teams notification error: {e}")
            return NotificationResult(
                success=False,
                error=str(e),
            )

    async def send_approval_result(
        self,
        request: ApprovalRequest,
        approved: bool,
    ) -> NotificationResult:
        """
        Send approval result notification to Teams.

        Args:
            request: Completed ApprovalRequest
            approved: Whether request was approved

        Returns:
            NotificationResult with send status
        """
        try:
            # Build the result card
            card = self._build_result_card(request, approved)

            # Send to Teams
            client = await self._get_client()
            response = await client.post(
                self.webhook_url,
                json=card.to_dict(),
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                logger.info(
                    f"Sent approval result notification: {request.request_id} "
                    f"({'approved' if approved else 'rejected'})"
                )
                return NotificationResult(
                    success=True,
                    message="Result notification sent",
                    response_code=response.status_code,
                )
            else:
                return NotificationResult(
                    success=False,
                    response_code=response.status_code,
                    error=response.text,
                )

        except Exception as e:
            logger.error(f"Teams result notification error: {e}")
            return NotificationResult(
                success=False,
                error=str(e),
            )

    def _build_approval_request_card(self, request: ApprovalRequest) -> TeamsMessageCard:
        """Build Teams card for approval request."""
        # Determine title based on risk level
        risk_level = request.risk_assessment.level
        risk_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🔴",
            RiskLevel.CRITICAL: "⚠️",
        }.get(risk_level, "⚪")

        title = f"{risk_emoji} {risk_level.value.upper()} 風險操作審批請求"

        # Build card
        builder = TeamsCardBuilder()
        builder.with_title(title)
        builder.with_summary(f"需要審批: {request.routing_decision.intent_category.value}")
        builder.with_risk_level_color(risk_level)

        # Main section with request details
        intent_category = request.routing_decision.intent_category.value
        sub_intent = request.routing_decision.sub_intent or "一般"

        builder.add_section(
            activity_title=f"請求 ID: {request.request_id[:8]}...",
            activity_subtitle=f"提交者: {request.requester}",
        )

        builder.add_fact("意圖類別", intent_category)
        builder.add_fact("子意圖", sub_intent)
        builder.add_fact("風險等級", risk_level.value)
        builder.add_fact("風險分數", f"{request.risk_assessment.score:.2f}")
        builder.add_fact("審批類型", request.approval_type.value)

        # Add expiration info
        if request.expires_at:
            expires_str = request.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            builder.add_fact("過期時間", expires_str)

        # Add reasoning if available
        if request.risk_assessment.reasoning:
            builder.add_section("風險評估說明")
            builder.add_text(request.risk_assessment.reasoning, is_markdown=True)

        # Add action buttons
        approve_url = f"{self.callback_base_url}/{request.request_id}/approve"
        reject_url = f"{self.callback_base_url}/{request.request_id}/reject"

        builder.add_approve_button(approve_url, "✅ 批准")
        builder.add_reject_button(reject_url, "❌ 拒絕")

        # Add view details button if detail URL is in metadata
        if request.metadata.get("detail_url"):
            builder.add_open_url_button(
                request.metadata["detail_url"],
                "📋 查看詳情",
            )

        return builder.build()

    def _build_result_card(
        self,
        request: ApprovalRequest,
        approved: bool,
    ) -> TeamsMessageCard:
        """Build Teams card for approval result."""
        if approved:
            title = "✅ 審批已通過"
            theme_color = "00FF00"
            status_text = "已批准"
            actor = request.approved_by
            timestamp = request.approved_at
        else:
            title = "❌ 審批已拒絕"
            theme_color = "FF0000"
            status_text = "已拒絕"
            actor = request.rejected_by
            timestamp = request.rejected_at

        builder = TeamsCardBuilder()
        builder.with_title(title)
        builder.with_summary(f"審批結果: {status_text}")
        builder.with_theme_color(theme_color)

        builder.add_section(
            activity_title=f"請求 ID: {request.request_id[:8]}...",
        )

        builder.add_fact("狀態", status_text)
        builder.add_fact("處理人", actor or "系統")
        builder.add_fact("意圖類別", request.routing_decision.intent_category.value)
        builder.add_fact("子意圖", request.routing_decision.sub_intent or "一般")

        if timestamp:
            builder.add_fact("處理時間", timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"))

        if request.comment:
            builder.add_section("備註")
            builder.add_text(request.comment)

        return builder.build()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# =============================================================================
# Email Notification Service (Placeholder)
# =============================================================================


class EmailNotificationService:
    """
    Email notification service placeholder.

    To be implemented when email integration is required.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender_email: str,
        sender_password: Optional[str] = None,
    ):
        """Initialize email service."""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    async def send_approval_request(self, request: ApprovalRequest) -> bool:
        """Send approval request via email."""
        # Placeholder - implement with smtplib or external email service
        logger.warning("Email notification service not implemented")
        return False

    async def send_approval_result(
        self,
        request: ApprovalRequest,
        approved: bool,
    ) -> bool:
        """Send approval result via email."""
        # Placeholder
        logger.warning("Email notification service not implemented")
        return False


# =============================================================================
# Composite Notification Service
# =============================================================================


class CompositeNotificationService:
    """
    Composite notification service that sends to multiple channels.

    Combines multiple notification services (Teams, Email, etc.) and sends
    notifications to all configured channels.
    """

    def __init__(self, services: List[Any] = None):
        """
        Initialize composite service.

        Args:
            services: List of notification service instances
        """
        self.services = services or []

    def add_service(self, service: Any) -> None:
        """Add a notification service."""
        self.services.append(service)

    async def send_approval_request(self, request: ApprovalRequest) -> bool:
        """
        Send approval request to all services.

        Args:
            request: ApprovalRequest to notify about

        Returns:
            True if at least one service succeeded
        """
        if not self.services:
            logger.warning("No notification services configured")
            return False

        results = await asyncio.gather(
            *[s.send_approval_request(request) for s in self.services],
            return_exceptions=True,
        )

        successes = sum(
            1 for r in results
            if isinstance(r, (bool, NotificationResult)) and (
                r is True or (isinstance(r, NotificationResult) and r.success)
            )
        )

        return successes > 0

    async def send_approval_result(
        self,
        request: ApprovalRequest,
        approved: bool,
    ) -> bool:
        """
        Send approval result to all services.

        Args:
            request: Completed ApprovalRequest
            approved: Whether request was approved

        Returns:
            True if at least one service succeeded
        """
        if not self.services:
            return False

        results = await asyncio.gather(
            *[s.send_approval_result(request, approved) for s in self.services],
            return_exceptions=True,
        )

        successes = sum(
            1 for r in results
            if isinstance(r, (bool, NotificationResult)) and (
                r is True or (isinstance(r, NotificationResult) and r.success)
            )
        )

        return successes > 0


# =============================================================================
# Factory Functions
# =============================================================================


def create_teams_notification_service(
    webhook_url: str,
    callback_base_url: str,
    timeout: float = 30.0,
) -> TeamsNotificationService:
    """
    Factory function to create Teams notification service.

    Args:
        webhook_url: Teams Incoming Webhook URL
        callback_base_url: Base URL for approval callbacks
        timeout: HTTP request timeout

    Returns:
        TeamsNotificationService instance
    """
    return TeamsNotificationService(
        webhook_url=webhook_url,
        callback_base_url=callback_base_url,
        timeout=timeout,
    )


def create_composite_notification_service(
    teams_webhook_url: Optional[str] = None,
    callback_base_url: Optional[str] = None,
) -> CompositeNotificationService:
    """
    Factory function to create composite notification service.

    Args:
        teams_webhook_url: Optional Teams webhook URL
        callback_base_url: Base URL for approval callbacks

    Returns:
        CompositeNotificationService instance
    """
    service = CompositeNotificationService()

    if teams_webhook_url and callback_base_url:
        teams_service = create_teams_notification_service(
            webhook_url=teams_webhook_url,
            callback_base_url=callback_base_url,
        )
        service.add_service(teams_service)

    return service


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Card structures
    "TeamsMessageCard",
    "TeamsCardBuilder",
    # Results
    "NotificationResult",
    # Services
    "TeamsNotificationService",
    "EmailNotificationService",
    "CompositeNotificationService",
    # Factory functions
    "create_teams_notification_service",
    "create_composite_notification_service",
]
