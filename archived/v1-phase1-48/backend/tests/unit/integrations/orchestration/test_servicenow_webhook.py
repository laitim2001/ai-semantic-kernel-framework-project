"""
Unit Tests for ServiceNow Webhook Receiver.

Sprint 114: AD 場景基礎建設 (Phase 32)
"""

import pytest

from src.integrations.orchestration.input.servicenow_webhook import (
    ServiceNowRITMEvent,
    ServiceNowWebhookReceiver,
    WebhookAuthConfig,
    WebhookValidationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_config() -> WebhookAuthConfig:
    """Create test auth config."""
    return WebhookAuthConfig(
        auth_type="shared_secret",
        shared_secret="test-secret-12345",
        allowed_ips=["10.0.0.0/8", "192.168.1.100"],
        enabled=True,
    )


@pytest.fixture
def receiver(auth_config: WebhookAuthConfig) -> ServiceNowWebhookReceiver:
    """Create test webhook receiver."""
    return ServiceNowWebhookReceiver(auth_config)


@pytest.fixture
def valid_payload() -> dict:
    """Create valid RITM event payload."""
    return {
        "sys_id": "abc123def456",
        "number": "RITM0012345",
        "state": "1",
        "cat_item": "cat_sys_id_001",
        "cat_item_name": "AD Account Unlock",
        "requested_for": "john.doe",
        "requested_by": "jane.smith",
        "short_description": "Unlock AD account for john.doe",
        "variables": {
            "affected_user": "john.doe",
            "reason": "Forgot password, locked out after 5 attempts",
        },
        "priority": "3",
    }


# ---------------------------------------------------------------------------
# ServiceNowRITMEvent Model Tests
# ---------------------------------------------------------------------------


class TestServiceNowRITMEvent:
    """Tests for RITM event data model."""

    def test_valid_event(self, valid_payload: dict) -> None:
        """Test creating valid event from payload."""
        event = ServiceNowRITMEvent(**valid_payload)
        assert event.sys_id == "abc123def456"
        assert event.number == "RITM0012345"
        assert event.cat_item_name == "AD Account Unlock"
        assert event.variables["affected_user"] == "john.doe"

    def test_empty_sys_id_rejected(self) -> None:
        """Test that empty sys_id is rejected."""
        with pytest.raises(Exception):
            ServiceNowRITMEvent(sys_id="", number="RITM001")

    def test_whitespace_sys_id_rejected(self) -> None:
        """Test that whitespace-only sys_id is rejected."""
        with pytest.raises(Exception):
            ServiceNowRITMEvent(sys_id="   ", number="RITM001")

    def test_minimal_event(self) -> None:
        """Test creating event with minimal required fields."""
        event = ServiceNowRITMEvent(sys_id="abc", number="RITM001")
        assert event.state == "1"
        assert event.priority == "3"
        assert event.variables == {}

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        event = ServiceNowRITMEvent(sys_id="abc", number="RITM001")
        assert event.cat_item == ""
        assert event.cat_item_name == ""
        assert event.description is None
        assert event.assignment_group is None


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


class TestWebhookAuthentication:
    """Tests for webhook authentication."""

    def test_valid_secret(self, receiver: ServiceNowWebhookReceiver) -> None:
        """Test valid shared secret passes validation."""
        assert receiver.validate_shared_secret("test-secret-12345") is True

    def test_invalid_secret(self, receiver: ServiceNowWebhookReceiver) -> None:
        """Test invalid shared secret raises error."""
        with pytest.raises(WebhookValidationError) as exc_info:
            receiver.validate_shared_secret("wrong-secret")
        assert exc_info.value.status_code == 401

    def test_missing_secret(self, receiver: ServiceNowWebhookReceiver) -> None:
        """Test missing secret raises error."""
        with pytest.raises(WebhookValidationError) as exc_info:
            receiver.validate_shared_secret(None)
        assert exc_info.value.status_code == 401

    def test_no_secret_configured(self) -> None:
        """Test that no secret configured skips validation."""
        config = WebhookAuthConfig(shared_secret=None)
        r = ServiceNowWebhookReceiver(config)
        assert r.validate_shared_secret(None) is True


# ---------------------------------------------------------------------------
# IP Validation Tests
# ---------------------------------------------------------------------------


class TestIPValidation:
    """Tests for IP whitelist validation."""

    def test_allowed_ip_in_cidr(self, receiver: ServiceNowWebhookReceiver) -> None:
        """Test IP within allowed CIDR range."""
        assert receiver.validate_ip("10.1.2.3") is True

    def test_allowed_exact_ip(self, receiver: ServiceNowWebhookReceiver) -> None:
        """Test exact IP match."""
        assert receiver.validate_ip("192.168.1.100") is True

    def test_disallowed_ip(self, receiver: ServiceNowWebhookReceiver) -> None:
        """Test IP outside whitelist raises error."""
        with pytest.raises(WebhookValidationError) as exc_info:
            receiver.validate_ip("203.0.113.1")
        assert exc_info.value.status_code == 403

    def test_no_whitelist_allows_all(self) -> None:
        """Test empty whitelist allows all IPs."""
        config = WebhookAuthConfig(allowed_ips=[])
        r = ServiceNowWebhookReceiver(config)
        assert r.validate_ip("8.8.8.8") is True


# ---------------------------------------------------------------------------
# Idempotency Tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Tests for duplicate event detection."""

    def test_first_event_not_duplicate(
        self, receiver: ServiceNowWebhookReceiver
    ) -> None:
        """Test first processing of event is not a duplicate."""
        assert receiver.is_duplicate("event_001") is False

    def test_second_event_is_duplicate(
        self, receiver: ServiceNowWebhookReceiver
    ) -> None:
        """Test second processing of same event is detected."""
        receiver.mark_processed("event_001")
        assert receiver.is_duplicate("event_001") is True

    def test_different_events_not_duplicate(
        self, receiver: ServiceNowWebhookReceiver
    ) -> None:
        """Test different events are not duplicates."""
        receiver.mark_processed("event_001")
        assert receiver.is_duplicate("event_002") is False

    def test_cache_eviction(self) -> None:
        """Test cache eviction when max size reached."""
        config = WebhookAuthConfig()
        r = ServiceNowWebhookReceiver(config)
        r.MAX_CACHE_SIZE = 10

        for i in range(15):
            r.mark_processed(f"event_{i:03d}")

        # Some old events should have been evicted
        assert len(r._processed_events) <= 10


# ---------------------------------------------------------------------------
# Event Processing Tests
# ---------------------------------------------------------------------------


class TestEventProcessing:
    """Tests for event processing flow."""

    @pytest.mark.asyncio
    async def test_process_new_event(
        self,
        receiver: ServiceNowWebhookReceiver,
        valid_payload: dict,
    ) -> None:
        """Test processing a new event returns tracking ID."""
        event = ServiceNowRITMEvent(**valid_payload)
        result = await receiver.process_event(event)

        assert result["status"] == "accepted"
        assert "tracking_id" in result
        assert result["ritm_number"] == "RITM0012345"
        assert "received_at" in result

    @pytest.mark.asyncio
    async def test_process_duplicate_event(
        self,
        receiver: ServiceNowWebhookReceiver,
        valid_payload: dict,
    ) -> None:
        """Test processing duplicate event raises 409."""
        event = ServiceNowRITMEvent(**valid_payload)
        await receiver.process_event(event)

        with pytest.raises(WebhookValidationError) as exc_info:
            await receiver.process_event(event)
        assert exc_info.value.status_code == 409

    def test_parse_valid_payload(
        self,
        receiver: ServiceNowWebhookReceiver,
        valid_payload: dict,
    ) -> None:
        """Test parsing valid RITM payload."""
        event = receiver.parse_ritm_event(valid_payload)
        assert event.number == "RITM0012345"
        assert event.cat_item_name == "AD Account Unlock"

    def test_parse_invalid_payload(
        self, receiver: ServiceNowWebhookReceiver
    ) -> None:
        """Test parsing invalid payload raises ValueError."""
        with pytest.raises(ValueError):
            receiver.parse_ritm_event({"invalid": "data"})


# ---------------------------------------------------------------------------
# Disabled Webhook Tests
# ---------------------------------------------------------------------------


class TestDisabledWebhook:
    """Tests for disabled webhook behavior."""

    @pytest.mark.asyncio
    async def test_disabled_webhook_rejects(self) -> None:
        """Test disabled webhook rejects all requests."""
        config = WebhookAuthConfig(enabled=False)
        r = ServiceNowWebhookReceiver(config)

        with pytest.raises(WebhookValidationError) as exc_info:
            await r.validate_request(secret_header="any")
        assert exc_info.value.status_code == 503
