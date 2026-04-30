"""
Notifications Unit Tests
========================

Unit tests for Teams notification service.

Sprint 3 - S3-4: Teams Notification Integration

Test Coverage:
- TeamsNotificationConfig creation and validation
- TeamsNotificationService methods
- Adaptive Card building
- Retry mechanism
- Rate limiting
- Event handlers
- History and statistics

Author: IPA Platform Team
Created: 2025-11-30
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.domain.notifications import (
    NotificationError,
    NotificationPriority,
    NotificationResult,
    NotificationType,
    TeamsCard,
    TeamsNotificationConfig,
    TeamsNotificationService,
)


# ============================================================================
# TeamsNotificationConfig Tests
# ============================================================================

class TestTeamsNotificationConfig:
    """Tests for TeamsNotificationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TeamsNotificationConfig(webhook_url="https://example.com/webhook")

        assert config.webhook_url == "https://example.com/webhook"
        assert config.enabled is True
        assert config.channel_name is None
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
        assert config.timeout == 10.0
        assert config.max_notifications_per_minute == 30
        assert config.app_name == "IPA Platform"
        assert config.theme_color == "#0078D4"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TeamsNotificationConfig(
            webhook_url="https://custom.com/webhook",
            enabled=False,
            channel_name="alerts",
            retry_count=5,
            retry_delay=2.0,
            max_notifications_per_minute=10,
            app_name="Custom App",
            theme_color="#FF0000",
        )

        assert config.webhook_url == "https://custom.com/webhook"
        assert config.enabled is False
        assert config.channel_name == "alerts"
        assert config.retry_count == 5
        assert config.retry_delay == 2.0
        assert config.max_notifications_per_minute == 10
        assert config.app_name == "Custom App"
        assert config.theme_color == "#FF0000"


# ============================================================================
# NotificationResult Tests
# ============================================================================

class TestNotificationResult:
    """Tests for NotificationResult."""

    def test_result_creation(self):
        """Test result creation with basic fields."""
        notification_id = uuid4()
        timestamp = datetime.utcnow()

        result = NotificationResult(
            notification_id=notification_id,
            notification_type=NotificationType.APPROVAL_REQUEST,
            success=True,
            timestamp=timestamp,
        )

        assert result.notification_id == notification_id
        assert result.notification_type == NotificationType.APPROVAL_REQUEST
        assert result.success is True
        assert result.timestamp == timestamp
        assert result.message is None
        assert result.retry_count == 0
        assert result.response_code is None

    def test_result_with_optional_fields(self):
        """Test result with all optional fields."""
        result = NotificationResult(
            notification_id=uuid4(),
            notification_type=NotificationType.ERROR_ALERT,
            success=False,
            timestamp=datetime.utcnow(),
            message="Failed to send",
            retry_count=3,
            response_code=500,
        )

        assert result.success is False
        assert result.message == "Failed to send"
        assert result.retry_count == 3
        assert result.response_code == 500

    def test_result_to_dict(self):
        """Test result serialization to dictionary."""
        notification_id = uuid4()
        timestamp = datetime.utcnow()

        result = NotificationResult(
            notification_id=notification_id,
            notification_type=NotificationType.EXECUTION_COMPLETED,
            success=True,
            timestamp=timestamp,
            message="Sent successfully",
            retry_count=1,
            response_code=200,
        )

        result_dict = result.to_dict()

        assert result_dict["notification_id"] == str(notification_id)
        assert result_dict["notification_type"] == "execution_completed"
        assert result_dict["success"] is True
        assert result_dict["message"] == "Sent successfully"
        assert result_dict["retry_count"] == 1
        assert result_dict["response_code"] == 200


# ============================================================================
# TeamsCard Tests
# ============================================================================

class TestTeamsCard:
    """Tests for TeamsCard."""

    def test_card_creation(self):
        """Test card creation."""
        card = TeamsCard(
            title="Test Card",
            body=[{"type": "TextBlock", "text": "Hello"}],
            actions=[{"type": "Action.OpenUrl", "title": "Click", "url": "https://example.com"}],
        )

        assert card.title == "Test Card"
        assert len(card.body) == 1
        assert len(card.actions) == 1
        assert card.theme_color == "#0078D4"

    def test_card_to_payload(self):
        """Test card conversion to Teams payload."""
        card = TeamsCard(
            title="Test",
            body=[{"type": "TextBlock", "text": "Content"}],
            actions=[],
        )

        payload = card.to_payload()

        assert payload["type"] == "message"
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"

        content = payload["attachments"][0]["content"]
        assert content["type"] == "AdaptiveCard"
        assert content["version"] == "1.4"
        assert content["body"] == [{"type": "TextBlock", "text": "Content"}]


# ============================================================================
# TeamsNotificationService Tests
# ============================================================================

class TestTeamsNotificationService:
    """Tests for TeamsNotificationService."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client that returns 200."""
        return AsyncMock(return_value=200)

    @pytest.fixture
    def service(self, mock_http_client):
        """Create service with mock HTTP client."""
        config = TeamsNotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            retry_count=3,
            retry_delay=0.01,  # Fast retries for testing
        )
        return TeamsNotificationService(config=config, http_client=mock_http_client)

    @pytest.fixture
    def disabled_service(self):
        """Create disabled service."""
        config = TeamsNotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=False,
        )
        return TeamsNotificationService(config=config)

    # -------------------------------------------------------------------------
    # Configuration Tests
    # -------------------------------------------------------------------------

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.is_enabled is True
        assert service.config.webhook_url == "https://example.com/webhook"

    def test_service_disabled(self, disabled_service):
        """Test disabled service."""
        assert disabled_service.is_enabled is False

    def test_configure(self, service):
        """Test configuration update."""
        new_config = TeamsNotificationConfig(
            webhook_url="https://new.com/webhook",
            enabled=True,
            app_name="New App",
        )

        service.configure(new_config)

        assert service.config.webhook_url == "https://new.com/webhook"
        assert service.config.app_name == "New App"

    # -------------------------------------------------------------------------
    # Send Approval Request Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_approval_request_success(self, service, mock_http_client):
        """Test successful approval request notification."""
        result = await service.send_approval_request(
            checkpoint_id="cp-123",
            workflow_name="Test Workflow",
            content="Please review and approve this step.",
            approver="admin@example.com",
            priority=NotificationPriority.HIGH,
        )

        assert result.success is True
        assert result.notification_type == NotificationType.APPROVAL_REQUEST
        assert result.retry_count == 0
        mock_http_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_approval_request_disabled(self, disabled_service):
        """Test approval request when service is disabled."""
        result = await disabled_service.send_approval_request(
            checkpoint_id="cp-123",
            workflow_name="Test Workflow",
            content="Please approve.",
        )

        assert result.success is False
        assert "disabled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_send_approval_request_priority_levels(self, service, mock_http_client):
        """Test approval request with different priority levels."""
        for priority in NotificationPriority:
            result = await service.send_approval_request(
                checkpoint_id="cp-123",
                workflow_name="Workflow",
                content="Content",
                priority=priority,
            )

            assert result.success is True

    # -------------------------------------------------------------------------
    # Send Completion Notification Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_execution_completed_success(self, service, mock_http_client):
        """Test successful execution completed notification."""
        result = await service.send_execution_completed(
            execution_id="exec-123",
            workflow_name="Data Processing",
            status="completed",
            result_summary="Processed 1000 records successfully.",
            duration=120.5,
            step_count=5,
        )

        assert result.success is True
        assert result.notification_type == NotificationType.EXECUTION_COMPLETED

    @pytest.mark.asyncio
    async def test_send_execution_failed_status(self, service, mock_http_client):
        """Test execution failed notification."""
        result = await service.send_execution_completed(
            execution_id="exec-456",
            workflow_name="Data Import",
            status="failed",
            result_summary="Import failed due to connection timeout.",
        )

        assert result.success is True
        assert result.notification_type == NotificationType.EXECUTION_FAILED

    @pytest.mark.asyncio
    async def test_send_execution_without_optional_fields(self, service, mock_http_client):
        """Test execution notification without optional fields."""
        result = await service.send_execution_completed(
            execution_id="exec-789",
            workflow_name="Simple Task",
            status="completed",
            result_summary="Done.",
        )

        assert result.success is True

    # -------------------------------------------------------------------------
    # Send Error Alert Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_error_alert_success(self, service, mock_http_client):
        """Test successful error alert notification."""
        result = await service.send_error_alert(
            execution_id="exec-error",
            workflow_name="Critical Process",
            error_message="Database connection failed.",
            error_type="DatabaseError",
            severity=NotificationPriority.URGENT,
        )

        assert result.success is True
        assert result.notification_type == NotificationType.ERROR_ALERT

    @pytest.mark.asyncio
    async def test_send_error_alert_severity_levels(self, service, mock_http_client):
        """Test error alert with different severity levels."""
        for severity in NotificationPriority:
            result = await service.send_error_alert(
                execution_id="exec-test",
                workflow_name="Test",
                error_message="Test error",
                severity=severity,
            )

            assert result.success is True

    # -------------------------------------------------------------------------
    # Send Custom Notification Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_custom_notification_success(self, service, mock_http_client):
        """Test successful custom notification."""
        result = await service.send_custom_notification(
            title="Custom Alert",
            body=[
                {"type": "TextBlock", "text": "This is a custom message."},
            ],
            actions=[
                {"type": "Action.OpenUrl", "title": "More Info", "url": "https://example.com"},
            ],
            notification_type=NotificationType.INFO_ALERT,
        )

        assert result.success is True
        assert result.notification_type == NotificationType.INFO_ALERT

    # -------------------------------------------------------------------------
    # Retry Mechanism Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry mechanism on HTTP failure."""
        call_count = 0

        async def failing_then_success(payload):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return 500
            return 200

        config = TeamsNotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            retry_count=3,
            retry_delay=0.01,
        )
        service = TeamsNotificationService(config=config, http_client=failing_then_success)

        result = await service.send_approval_request(
            checkpoint_id="cp-123",
            workflow_name="Test",
            content="Test",
        )

        assert result.success is True
        assert result.retry_count == 2  # Succeeded on 3rd attempt (index 2)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_fail(self):
        """Test when all retry attempts fail."""
        async def always_fail(payload):
            return 500

        config = TeamsNotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            retry_count=3,
            retry_delay=0.01,
        )
        service = TeamsNotificationService(config=config, http_client=always_fail)

        result = await service.send_approval_request(
            checkpoint_id="cp-123",
            workflow_name="Test",
            content="Test",
        )

        assert result.success is False
        assert result.retry_count == 3
        assert "Failed after 3 attempts" in result.message

    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
        """Test retry on exception."""
        call_count = 0

        async def exception_then_success(payload):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Network error")
            return 200

        config = TeamsNotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            retry_count=3,
            retry_delay=0.01,
        )
        service = TeamsNotificationService(config=config, http_client=exception_then_success)

        result = await service.send_approval_request(
            checkpoint_id="cp-123",
            workflow_name="Test",
            content="Test",
        )

        assert result.success is True
        assert result.retry_count == 1

    # -------------------------------------------------------------------------
    # Rate Limiting Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limiting."""
        async def mock_client(payload):
            return 200

        config = TeamsNotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            max_notifications_per_minute=2,
            retry_delay=0.01,
        )
        service = TeamsNotificationService(config=config, http_client=mock_client)

        # Send notifications up to limit
        result1 = await service.send_approval_request("cp-1", "Workflow", "Content")
        result2 = await service.send_approval_request("cp-2", "Workflow", "Content")
        result3 = await service.send_approval_request("cp-3", "Workflow", "Content")

        assert result1.success is True
        assert result2.success is True
        assert result3.success is False
        assert "rate limit" in result3.message.lower()

    # -------------------------------------------------------------------------
    # History Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_history_recording(self, service, mock_http_client):
        """Test notification history recording."""
        await service.send_approval_request("cp-1", "Workflow 1", "Content 1")
        await service.send_error_alert("exec-1", "Workflow 2", "Error")

        history = service.get_history()

        assert len(history) == 2
        assert history[0].notification_type == NotificationType.APPROVAL_REQUEST
        assert history[1].notification_type == NotificationType.ERROR_ALERT

    @pytest.mark.asyncio
    async def test_history_filtering_by_type(self, service, mock_http_client):
        """Test history filtering by notification type."""
        await service.send_approval_request("cp-1", "Workflow", "Content")
        await service.send_error_alert("exec-1", "Workflow", "Error")
        await service.send_approval_request("cp-2", "Workflow", "Content")

        approval_history = service.get_history(
            notification_type=NotificationType.APPROVAL_REQUEST
        )

        assert len(approval_history) == 2
        assert all(r.notification_type == NotificationType.APPROVAL_REQUEST for r in approval_history)

    @pytest.mark.asyncio
    async def test_history_filtering_success_only(self, service, mock_http_client):
        """Test history filtering for successful notifications only."""
        await service.send_approval_request("cp-1", "Workflow", "Content")

        # Disable and send (will fail)
        service.configure(TeamsNotificationConfig(webhook_url="", enabled=False))
        await service.send_approval_request("cp-2", "Workflow", "Content")

        success_history = service.get_history(success_only=True)

        assert len(success_history) == 1
        assert success_history[0].success is True

    @pytest.mark.asyncio
    async def test_history_limit(self, service, mock_http_client):
        """Test history limit."""
        for i in range(5):
            await service.send_approval_request(f"cp-{i}", "Workflow", "Content")

        history = service.get_history(limit=3)

        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_clear_history(self, service, mock_http_client):
        """Test clearing history."""
        await service.send_approval_request("cp-1", "Workflow", "Content")
        await service.send_error_alert("exec-1", "Workflow", "Error")

        count = service.clear_history()

        assert count == 2
        assert len(service.get_history()) == 0

    # -------------------------------------------------------------------------
    # Statistics Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_statistics(self, service, mock_http_client):
        """Test statistics calculation."""
        await service.send_approval_request("cp-1", "Workflow", "Content")
        await service.send_error_alert("exec-1", "Workflow", "Error")

        # Disable and send (will fail)
        service.configure(TeamsNotificationConfig(webhook_url="", enabled=False))
        await service.send_approval_request("cp-2", "Workflow", "Content")

        stats = service.get_statistics()

        assert stats["total"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.1)
        assert "approval_request" in stats["by_type"]

    # -------------------------------------------------------------------------
    # Event Handler Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_success_handler(self, service, mock_http_client):
        """Test success event handler."""
        handler_called = False
        received_result = None

        def on_success(result):
            nonlocal handler_called, received_result
            handler_called = True
            received_result = result

        service.on_success(on_success)
        await service.send_approval_request("cp-1", "Workflow", "Content")

        assert handler_called is True
        assert received_result.success is True

    @pytest.mark.asyncio
    async def test_failure_handler(self):
        """Test failure event handler."""
        handler_called = False
        received_result = None

        def on_failure(result):
            nonlocal handler_called, received_result
            handler_called = True
            received_result = result

        async def always_fail(payload):
            return 500

        config = TeamsNotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            retry_count=1,
            retry_delay=0.01,
        )
        service = TeamsNotificationService(config=config, http_client=always_fail)
        service.on_failure(on_failure)

        await service.send_approval_request("cp-1", "Workflow", "Content")

        assert handler_called is True
        assert received_result.success is False

    @pytest.mark.asyncio
    async def test_async_handler(self, service, mock_http_client):
        """Test async event handler."""
        handler_called = False

        async def async_on_success(result):
            nonlocal handler_called
            await asyncio.sleep(0.001)
            handler_called = True

        service.on_success(async_on_success)
        await service.send_approval_request("cp-1", "Workflow", "Content")

        assert handler_called is True


# ============================================================================
# Enum Tests
# ============================================================================

class TestNotificationEnums:
    """Tests for notification enums."""

    def test_notification_type_values(self):
        """Test NotificationType enum values."""
        assert NotificationType.APPROVAL_REQUEST.value == "approval_request"
        assert NotificationType.EXECUTION_COMPLETED.value == "execution_completed"
        assert NotificationType.ERROR_ALERT.value == "error_alert"
        assert NotificationType.SYSTEM_MAINTENANCE.value == "system_maintenance"

    def test_notification_priority_values(self):
        """Test NotificationPriority enum values."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


# ============================================================================
# Exception Tests
# ============================================================================

class TestNotificationError:
    """Tests for NotificationError exception."""

    def test_error_creation(self):
        """Test error creation."""
        error = NotificationError(
            "Failed to send",
            notification_type=NotificationType.APPROVAL_REQUEST,
            retry_count=3,
        )

        assert str(error) == "Failed to send"
        assert error.notification_type == NotificationType.APPROVAL_REQUEST
        assert error.retry_count == 3
        assert error.original_error is None

    def test_error_with_original(self):
        """Test error with original exception."""
        original = Exception("Network error")
        error = NotificationError(
            "Send failed",
            original_error=original,
        )

        assert error.original_error == original


# ============================================================================
# Card Building Tests
# ============================================================================

class TestCardBuilding:
    """Tests for Adaptive Card building."""

    @pytest.fixture
    def service(self):
        """Create service for card building tests."""
        config = TeamsNotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            app_url="https://app.example.com",
        )
        return TeamsNotificationService(config=config)

    def test_build_approval_card(self, service):
        """Test approval card building."""
        card = service._build_approval_card(
            checkpoint_id="cp-123",
            workflow_name="Test Workflow",
            content="Please approve this step.",
            approver="admin@example.com",
            priority=NotificationPriority.HIGH,
        )

        assert card.title == "審批請求"
        assert len(card.body) > 0
        assert len(card.actions) == 1
        assert "cp-123" in card.actions[0]["url"]

    def test_build_completion_card_success(self, service):
        """Test completion card for successful execution."""
        card = service._build_completion_card(
            execution_id="exec-123",
            workflow_name="Data Process",
            status="completed",
            result_summary="All tasks completed.",
            duration=120.5,
            step_count=5,
        )

        assert card.title == "執行完成"
        assert card.theme_color == "#28A745"  # Green for success

    def test_build_completion_card_failed(self, service):
        """Test completion card for failed execution."""
        card = service._build_completion_card(
            execution_id="exec-456",
            workflow_name="Import",
            status="failed",
            result_summary="Failed due to error.",
        )

        assert card.theme_color == "#DC3545"  # Red for failure

    def test_build_error_card(self, service):
        """Test error card building."""
        card = service._build_error_card(
            execution_id="exec-error",
            workflow_name="Critical",
            error_message="Connection timeout",
            error_type="TimeoutError",
            severity=NotificationPriority.URGENT,
        )

        assert card.title == "錯誤告警"
        assert card.theme_color == "#8B0000"  # Dark red for urgent

    def test_build_error_card_different_severities(self, service):
        """Test error card with different severities."""
        severity_colors = {
            NotificationPriority.LOW: "#17A2B8",
            NotificationPriority.NORMAL: "#FFC107",
            NotificationPriority.HIGH: "#DC3545",
            NotificationPriority.URGENT: "#8B0000",
        }

        for severity, expected_color in severity_colors.items():
            card = service._build_error_card(
                execution_id="exec",
                workflow_name="Test",
                error_message="Error",
                severity=severity,
            )

            assert card.theme_color == expected_color
