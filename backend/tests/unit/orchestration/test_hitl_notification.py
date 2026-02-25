"""
Unit Tests for HITL Notification Module

Comprehensive tests for TeamsMessageCard, TeamsCardBuilder, TeamsNotificationService,
EmailNotificationService, CompositeNotificationService, and NotificationResult.

Sprint 130: Phase 34 - HITL Notification Deep Testing
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.integrations.orchestration.hitl.controller import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
)
from src.integrations.orchestration.hitl.notification import (
    CompositeNotificationService,
    EmailNotificationService,
    NotificationResult,
    TeamsCardBuilder,
    TeamsMessageCard,
    TeamsNotificationService,
)
from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
    RoutingDecision,
    WorkflowType,
)
from src.integrations.orchestration.risk_assessor.assessor import (
    RiskAssessment,
    RiskFactor,
)


# =============================================================================
# Helper Factories
# =============================================================================


def _make_routing_decision() -> RoutingDecision:
    """Create a standard routing decision for testing."""
    return RoutingDecision(
        intent_category=ITIntentCategory.INCIDENT,
        sub_intent="etl_failure",
        confidence=0.95,
        routing_layer="pattern",
        risk_level=RiskLevel.HIGH,
        workflow_type=WorkflowType.MAGENTIC,
    )


def _make_risk_assessment() -> RiskAssessment:
    """Create a standard risk assessment for testing."""
    return RiskAssessment(
        level=RiskLevel.HIGH,
        score=0.8,
        requires_approval=True,
        approval_type="single",
        factors=[
            RiskFactor(
                name="intent",
                description="High risk intent",
                weight=0.5,
                impact="increase",
            ),
        ],
        reasoning="High risk operation",
    )


def _make_approval_request(
    request_id: str = "notif-001",
    status: ApprovalStatus = ApprovalStatus.PENDING,
    approved_by: str = None,
    approved_at: datetime = None,
    rejected_by: str = None,
    rejected_at: datetime = None,
    comment: str = None,
) -> ApprovalRequest:
    """Create an approval request for notification testing."""
    return ApprovalRequest(
        request_id=request_id,
        routing_decision=_make_routing_decision(),
        risk_assessment=_make_risk_assessment(),
        requester="user@example.com",
        expires_at=datetime.utcnow() + timedelta(minutes=30),
        status=status,
        approved_by=approved_by,
        approved_at=approved_at,
        rejected_by=rejected_by,
        rejected_at=rejected_at,
        comment=comment,
    )


def _make_mock_http_client(
    status_code: int = 200,
    response_text: str = "1",
) -> AsyncMock:
    """Create a mock httpx.AsyncClient."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = response_text
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


def _make_teams_service(
    mock_client: AsyncMock = None,
) -> TeamsNotificationService:
    """Create a TeamsNotificationService with mock client."""
    client = mock_client or _make_mock_http_client()
    return TeamsNotificationService(
        webhook_url="https://outlook.office.com/webhook/test",
        callback_base_url="https://api.example.com/v1/approvals",
        http_client=client,
    )


# =============================================================================
# Test TeamsMessageCard
# =============================================================================


class TestTeamsMessageCard:
    """Tests for TeamsMessageCard dataclass."""

    def test_to_dict_output_format(self):
        """Verify to_dict contains all required MessageCard fields."""
        card = TeamsMessageCard(
            title="Test Title",
            summary="Test Summary",
            theme_color="FF0000",
            sections=[{"activityTitle": "Section 1", "facts": []}],
            potential_actions=[{"@type": "OpenUri", "name": "Open"}],
        )

        data = card.to_dict()

        assert data["@type"] == "MessageCard"
        assert data["@context"] == "http://schema.org/extensions"
        assert data["title"] == "Test Title"
        assert data["summary"] == "Test Summary"
        assert data["themeColor"] == "FF0000"
        assert len(data["sections"]) == 1
        assert len(data["potentialAction"]) == 1

    def test_default_theme_color(self):
        """Verify default theme color is Microsoft Blue."""
        card = TeamsMessageCard(title="T", summary="S")

        assert card.theme_color == "0078D7"


# =============================================================================
# Test TeamsCardBuilder
# =============================================================================


class TestTeamsCardBuilderDeep:
    """Tests for TeamsCardBuilder fluent API."""

    def test_fluent_chaining(self):
        """Verify builder methods return self for chaining."""
        builder = TeamsCardBuilder()

        result = (
            builder
            .with_title("Title")
            .with_summary("Summary")
            .with_theme_color("AABBCC")
        )

        assert result is builder

    def test_with_risk_level_color_low(self):
        """Verify LOW risk maps to green."""
        card = TeamsCardBuilder().with_risk_level_color(RiskLevel.LOW).build()
        assert card.theme_color == "00FF00"

    def test_with_risk_level_color_medium(self):
        """Verify MEDIUM risk maps to orange."""
        card = TeamsCardBuilder().with_risk_level_color(RiskLevel.MEDIUM).build()
        assert card.theme_color == "FFA500"

    def test_with_risk_level_color_high(self):
        """Verify HIGH risk maps to red."""
        card = TeamsCardBuilder().with_risk_level_color(RiskLevel.HIGH).build()
        assert card.theme_color == "FF0000"

    def test_with_risk_level_color_critical(self):
        """Verify CRITICAL risk maps to dark red."""
        card = TeamsCardBuilder().with_risk_level_color(RiskLevel.CRITICAL).build()
        assert card.theme_color == "8B0000"

    def test_add_fact_creates_default_section(self):
        """Verify add_fact auto-creates a section if none exists."""
        card = (
            TeamsCardBuilder()
            .add_fact("Key", "Value")
            .build()
        )

        assert len(card.sections) == 1
        assert card.sections[0]["facts"][0]["name"] == "Key"
        assert card.sections[0]["facts"][0]["value"] == "Value"

    def test_add_text_to_section(self):
        """Verify add_text sets text on current section."""
        card = (
            TeamsCardBuilder()
            .add_section("Details")
            .add_text("Some explanation", is_markdown=True)
            .build()
        )

        assert card.sections[0]["text"] == "Some explanation"
        assert card.sections[0]["markdown"] is True

    def test_add_section_with_subtitle_and_image(self):
        """Verify add_section stores subtitle and image."""
        card = (
            TeamsCardBuilder()
            .add_section(
                "Title",
                activity_subtitle="Sub",
                activity_image="https://img.example.com/logo.png",
            )
            .build()
        )

        section = card.sections[0]
        assert section["activityTitle"] == "Title"
        assert section["activitySubtitle"] == "Sub"
        assert section["activityImage"] == "https://img.example.com/logo.png"

    def test_add_approve_button(self):
        """Verify approve button has correct structure."""
        card = (
            TeamsCardBuilder()
            .add_approve_button("https://api.example.com/approve/123")
            .build()
        )

        action = card.potential_actions[0]
        assert action["@type"] == "HttpPOST"
        assert action["target"] == "https://api.example.com/approve/123"
        body = json.loads(action["body"])
        assert body["action"] == "approve"

    def test_add_reject_button(self):
        """Verify reject button has correct structure."""
        card = (
            TeamsCardBuilder()
            .add_reject_button("https://api.example.com/reject/123")
            .build()
        )

        action = card.potential_actions[0]
        assert action["@type"] == "HttpPOST"
        assert action["target"] == "https://api.example.com/reject/123"
        body = json.loads(action["body"])
        assert body["action"] == "reject"

    def test_add_open_url_button(self):
        """Verify open URL button has correct structure."""
        card = (
            TeamsCardBuilder()
            .add_open_url_button("https://dashboard.example.com/details")
            .build()
        )

        action = card.potential_actions[0]
        assert action["@type"] == "OpenUri"
        assert action["targets"][0]["os"] == "default"
        assert action["targets"][0]["uri"] == "https://dashboard.example.com/details"


# =============================================================================
# Test TeamsNotificationService
# =============================================================================


class TestTeamsNotificationServiceDeep:
    """Tests for TeamsNotificationService HTTP interactions."""

    @pytest.mark.asyncio
    async def test_send_approval_request_success(self):
        """Verify successful webhook post returns success result."""
        mock_client = _make_mock_http_client(status_code=200)
        service = _make_teams_service(mock_client)
        request = _make_approval_request()

        result = await service.send_approval_request(request)

        assert result.success is True
        assert result.response_code == 200
        assert "success" in result.message.lower()
        mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_approval_request_failure_non_200(self):
        """Verify non-200 response returns failure result."""
        mock_client = _make_mock_http_client(status_code=429, response_text="Rate limited")
        service = _make_teams_service(mock_client)
        request = _make_approval_request()

        result = await service.send_approval_request(request)

        assert result.success is False
        assert result.response_code == 429
        assert result.error == "Rate limited"

    @pytest.mark.asyncio
    async def test_send_approval_request_timeout(self):
        """Verify timeout returns failure result."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
        service = _make_teams_service(mock_client)
        request = _make_approval_request()

        result = await service.send_approval_request(request)

        assert result.success is False
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_approval_result_approved(self):
        """Verify sending approved result notification."""
        mock_client = _make_mock_http_client(status_code=200)
        service = _make_teams_service(mock_client)
        now = datetime.utcnow()
        request = _make_approval_request(
            status=ApprovalStatus.APPROVED,
            approved_by="admin@example.com",
            approved_at=now,
            comment="Approved for deploy",
        )

        result = await service.send_approval_result(request, approved=True)

        assert result.success is True
        assert result.response_code == 200

        post_call = mock_client.post.call_args
        card_json = post_call.kwargs.get("json") or post_call[1].get("json")
        assert "通過" in card_json["title"]

    @pytest.mark.asyncio
    async def test_send_approval_result_rejected(self):
        """Verify sending rejected result notification."""
        mock_client = _make_mock_http_client(status_code=200)
        service = _make_teams_service(mock_client)
        now = datetime.utcnow()
        request = _make_approval_request(
            status=ApprovalStatus.REJECTED,
            rejected_by="admin@example.com",
            rejected_at=now,
            comment="Not appropriate",
        )

        result = await service.send_approval_result(request, approved=False)

        assert result.success is True

        post_call = mock_client.post.call_args
        card_json = post_call.kwargs.get("json") or post_call[1].get("json")
        assert "拒絕" in card_json["title"]


# =============================================================================
# Test CompositeNotificationService
# =============================================================================


class TestCompositeNotificationServiceDeep:
    """Tests for CompositeNotificationService broadcast behavior."""

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_services(self):
        """Verify notification is sent to all registered services."""
        service_a = AsyncMock()
        service_a.send_approval_request = AsyncMock(return_value=True)
        service_b = AsyncMock()
        service_b.send_approval_request = AsyncMock(return_value=True)

        composite = CompositeNotificationService(services=[service_a, service_b])
        request = _make_approval_request()

        result = await composite.send_approval_request(request)

        assert result is True
        service_a.send_approval_request.assert_awaited_once()
        service_b.send_approval_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_services_returns_false(self):
        """Verify empty service list returns False."""
        composite = CompositeNotificationService(services=[])
        request = _make_approval_request()

        result = await composite.send_approval_request(request)

        assert result is False

    @pytest.mark.asyncio
    async def test_partial_success_still_returns_true(self):
        """Verify True is returned if at least one service succeeds."""
        service_ok = AsyncMock()
        service_ok.send_approval_request = AsyncMock(return_value=True)
        service_fail = AsyncMock()
        service_fail.send_approval_request = AsyncMock(return_value=False)

        composite = CompositeNotificationService(services=[service_ok, service_fail])
        request = _make_approval_request()

        result = await composite.send_approval_request(request)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_approval_result_no_services(self):
        """Verify send_approval_result returns False with no services."""
        composite = CompositeNotificationService(services=[])
        request = _make_approval_request()

        result = await composite.send_approval_result(request, approved=True)

        assert result is False


# =============================================================================
# Test EmailNotificationService
# =============================================================================


class TestEmailNotificationService:
    """Tests for EmailNotificationService placeholder."""

    @pytest.mark.asyncio
    async def test_send_approval_request_returns_false(self):
        """Verify placeholder returns False."""
        service = EmailNotificationService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender_email="noreply@example.com",
        )
        request = _make_approval_request()

        result = await service.send_approval_request(request)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_approval_result_returns_false(self):
        """Verify placeholder returns False."""
        service = EmailNotificationService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            sender_email="noreply@example.com",
        )
        request = _make_approval_request()

        result = await service.send_approval_result(request, approved=True)

        assert result is False


# =============================================================================
# Test NotificationResult
# =============================================================================


class TestNotificationResult:
    """Tests for NotificationResult dataclass."""

    def test_success_result(self):
        """Verify success result fields."""
        result = NotificationResult(
            success=True,
            message="Sent",
            response_code=200,
        )

        assert result.success is True
        assert result.message == "Sent"
        assert result.response_code == 200
        assert result.error is None

    def test_failure_result(self):
        """Verify failure result fields."""
        result = NotificationResult(
            success=False,
            message="Failed",
            response_code=500,
            error="Internal error",
        )

        assert result.success is False
        assert result.error == "Internal error"
        assert result.response_code == 500
