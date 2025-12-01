# =============================================================================
# IPA Platform - Triggers Unit Tests
# =============================================================================
# Sprint 3: 集成 & 可靠性 - n8n 觸發與錯誤處理
#
# Tests for:
#   - WebhookTriggerConfig
#   - WebhookPayload
#   - TriggerResult
#   - WebhookTriggerService
#   - Signature verification
#   - Retry mechanism
# =============================================================================

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.domain.triggers.webhook import (
    SignatureAlgorithm,
    SignatureVerificationError,
    TriggerResult,
    WebhookConfigNotFoundError,
    WebhookDisabledError,
    WebhookError,
    WebhookPayload,
    WebhookStatus,
    WebhookTriggerConfig,
    WebhookTriggerService,
)


# =============================================================================
# WebhookTriggerConfig Tests
# =============================================================================


class TestWebhookTriggerConfig:
    """Tests for WebhookTriggerConfig."""

    def test_initialization(self):
        """Test basic initialization."""
        workflow_id = uuid4()
        config = WebhookTriggerConfig(
            workflow_id=workflow_id,
            secret="test-secret-key-123",
        )

        assert config.workflow_id == workflow_id
        assert config.secret == "test-secret-key-123"
        assert config.enabled is True
        assert config.retry_enabled is True
        assert config.max_retries == 3
        assert config.algorithm == SignatureAlgorithm.HMAC_SHA256

    def test_initialization_with_options(self):
        """Test initialization with custom options."""
        workflow_id = uuid4()
        config = WebhookTriggerConfig(
            workflow_id=workflow_id,
            secret="secret",
            callback_url="https://example.com/callback",
            enabled=False,
            retry_enabled=False,
            max_retries=5,
            retry_delay_seconds=2.0,
            algorithm=SignatureAlgorithm.HMAC_SHA512,
        )

        assert config.callback_url == "https://example.com/callback"
        assert config.enabled is False
        assert config.retry_enabled is False
        assert config.max_retries == 5
        assert config.retry_delay_seconds == 2.0
        assert config.algorithm == SignatureAlgorithm.HMAC_SHA512

    def test_to_dict(self):
        """Test serialization."""
        workflow_id = uuid4()
        config = WebhookTriggerConfig(
            workflow_id=workflow_id,
            secret="my-secret",
        )

        result = config.to_dict()

        assert result["workflow_id"] == str(workflow_id)
        assert result["secret"] == "***"  # Secret should be masked
        assert result["enabled"] is True
        assert "created_at" in result


# =============================================================================
# WebhookPayload Tests
# =============================================================================


class TestWebhookPayload:
    """Tests for WebhookPayload."""

    def test_initialization(self):
        """Test basic initialization."""
        payload = WebhookPayload(
            data={"message": "test"},
        )

        assert payload.data == {"message": "test"}
        assert payload.source == "n8n"

    def test_from_request(self):
        """Test creation from request."""
        body = json.dumps({"key": "value"}).encode("utf-8")
        headers = {
            "X-Webhook-Signature": "sha256=abc123",
            "X-Webhook-Timestamp": "2025-01-01T00:00:00Z",
            "X-Webhook-Source": "custom",
        }

        payload = WebhookPayload.from_request(body, headers)

        assert payload.data == {"key": "value"}
        assert payload.signature == "sha256=abc123"
        assert payload.timestamp == "2025-01-01T00:00:00Z"
        assert payload.source == "custom"

    def test_from_request_invalid_json(self):
        """Test creation with invalid JSON."""
        body = b"not-json"
        headers = {}

        payload = WebhookPayload.from_request(body, headers)

        assert "raw" in payload.data
        assert payload.data["raw"] == "not-json"

    def test_from_request_empty_body(self):
        """Test creation with empty body."""
        body = b""
        headers = {}

        payload = WebhookPayload.from_request(body, headers)

        assert payload.data == {}


# =============================================================================
# TriggerResult Tests
# =============================================================================


class TestTriggerResult:
    """Tests for TriggerResult."""

    def test_success_result(self):
        """Test success result."""
        execution_id = uuid4()
        result = TriggerResult(
            success=True,
            execution_id=execution_id,
            message="Workflow triggered",
        )

        assert result.success is True
        assert result.execution_id == execution_id
        assert result.error is None

    def test_failure_result(self):
        """Test failure result."""
        result = TriggerResult(
            success=False,
            error="Connection failed",
            retry_count=3,
        )

        assert result.success is False
        assert result.error == "Connection failed"
        assert result.retry_count == 3

    def test_to_dict(self):
        """Test serialization."""
        execution_id = uuid4()
        result = TriggerResult(
            success=True,
            execution_id=execution_id,
            duration_ms=150.5,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["execution_id"] == str(execution_id)
        assert data["duration_ms"] == 150.5


# =============================================================================
# WebhookTriggerService Tests
# =============================================================================


class TestWebhookTriggerService:
    """Tests for WebhookTriggerService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return WebhookTriggerService()

    @pytest.fixture
    def config(self):
        """Create test config."""
        return WebhookTriggerConfig(
            workflow_id=uuid4(),
            secret="test-secret-key-12345",
            callback_url="https://example.com/callback",
        )

    # -------------------------------------------------------------------------
    # Configuration Management Tests
    # -------------------------------------------------------------------------

    def test_register_config(self, service, config):
        """Test registering config."""
        service.register_config(config)

        assert service.get_config(config.workflow_id) == config

    def test_unregister_config(self, service, config):
        """Test unregistering config."""
        service.register_config(config)
        result = service.unregister_config(config.workflow_id)

        assert result is True
        assert service.get_config(config.workflow_id) is None

    def test_unregister_nonexistent_config(self, service):
        """Test unregistering non-existent config."""
        result = service.unregister_config(uuid4())
        assert result is False

    def test_list_configs(self, service, config):
        """Test listing configs."""
        service.register_config(config)

        configs = service.list_configs()

        assert len(configs) == 1
        assert configs[0] == config

    # -------------------------------------------------------------------------
    # Signature Verification Tests
    # -------------------------------------------------------------------------

    def test_verify_signature_valid(self, service):
        """Test valid signature verification."""
        payload = b'{"data": "test"}'
        secret = "my-secret-key"

        # Generate signature
        signature = service.generate_signature(payload, secret)

        # Verify
        is_valid = service.verify_signature(payload, signature, secret)

        assert is_valid is True

    def test_verify_signature_invalid(self, service):
        """Test invalid signature rejection."""
        payload = b'{"data": "test"}'
        secret = "my-secret-key"

        is_valid = service.verify_signature(
            payload,
            "sha256=invalid-signature",
            secret,
        )

        assert is_valid is False

    def test_verify_signature_wrong_secret(self, service):
        """Test wrong secret rejection."""
        payload = b'{"data": "test"}'
        signature = service.generate_signature(payload, "correct-secret")

        is_valid = service.verify_signature(payload, signature, "wrong-secret")

        assert is_valid is False

    def test_verify_signature_sha512(self, service):
        """Test SHA512 signature."""
        payload = b'{"data": "test"}'
        secret = "my-secret-key"
        algorithm = SignatureAlgorithm.HMAC_SHA512

        signature = service.generate_signature(payload, secret, algorithm)
        is_valid = service.verify_signature(payload, signature, secret, algorithm)

        assert is_valid is True
        assert signature.startswith("sha512=")

    def test_generate_signature_sha256(self, service):
        """Test SHA256 signature generation."""
        payload = b'test payload'
        secret = "secret"

        signature = service.generate_signature(payload, secret)

        assert signature.startswith("sha256=")
        assert len(signature) > 10

    def test_verify_signature_without_prefix(self, service):
        """Test signature verification without algorithm prefix."""
        payload = b'test'
        secret = "secret"

        # Generate and strip prefix
        full_sig = service.generate_signature(payload, secret)
        raw_sig = full_sig.split("=", 1)[1]

        is_valid = service.verify_signature(payload, raw_sig, secret)

        assert is_valid is True

    # -------------------------------------------------------------------------
    # Trigger Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_trigger_success(self, service, config):
        """Test successful trigger."""
        service.register_config(config)

        # Mock executor
        mock_executor = AsyncMock(return_value={"execution_id": uuid4()})
        service._workflow_executor = mock_executor

        payload = WebhookPayload(data={"test": "data"})

        result = await service.trigger(
            workflow_id=config.workflow_id,
            payload=payload,
        )

        assert result.success is True
        assert result.execution_id is not None
        mock_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_config_not_found(self, service):
        """Test trigger with missing config."""
        payload = WebhookPayload(data={})

        with pytest.raises(WebhookConfigNotFoundError):
            await service.trigger(
                workflow_id=uuid4(),
                payload=payload,
            )

    @pytest.mark.asyncio
    async def test_trigger_disabled(self, service, config):
        """Test trigger when disabled."""
        config.enabled = False
        service.register_config(config)

        payload = WebhookPayload(data={})

        with pytest.raises(WebhookDisabledError):
            await service.trigger(
                workflow_id=config.workflow_id,
                payload=payload,
            )

    @pytest.mark.asyncio
    async def test_trigger_invalid_signature(self, service, config):
        """Test trigger with invalid signature."""
        service.register_config(config)

        payload = WebhookPayload(
            data={},
            signature="sha256=invalid",
        )
        raw_body = b'{"test": "data"}'

        with pytest.raises(SignatureVerificationError):
            await service.trigger(
                workflow_id=config.workflow_id,
                payload=payload,
                raw_body=raw_body,
            )

    @pytest.mark.asyncio
    async def test_trigger_with_valid_signature(self, service, config):
        """Test trigger with valid signature."""
        service.register_config(config)

        raw_body = b'{"test": "data"}'
        signature = service.generate_signature(raw_body, config.secret)

        payload = WebhookPayload(
            data={"test": "data"},
            signature=signature,
        )

        result = await service.trigger(
            workflow_id=config.workflow_id,
            payload=payload,
            raw_body=raw_body,
        )

        assert result.success is True

    # -------------------------------------------------------------------------
    # Retry Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, service, config):
        """Test retry mechanism on failure."""
        config.retry_delay_seconds = 0.01  # Short delay for testing
        config.max_retries = 2
        service.register_config(config)

        # Mock executor that fails twice then succeeds
        call_count = 0

        async def mock_executor(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"execution_id": uuid4()}

        service._workflow_executor = mock_executor

        payload = WebhookPayload(data={})

        result = await service.trigger(
            workflow_id=config.workflow_id,
            payload=payload,
        )

        assert result.success is True
        assert result.retry_count == 2
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, service, config):
        """Test max retries exceeded."""
        config.retry_delay_seconds = 0.01
        config.max_retries = 2
        service.register_config(config)

        # Mock executor that always fails
        service._workflow_executor = AsyncMock(
            side_effect=Exception("Permanent failure")
        )

        payload = WebhookPayload(data={})

        result = await service.trigger(
            workflow_id=config.workflow_id,
            payload=payload,
        )

        assert result.success is False
        assert result.retry_count == 2
        assert "Permanent failure" in result.error

    @pytest.mark.asyncio
    async def test_retry_disabled(self, service, config):
        """Test with retry disabled."""
        config.retry_enabled = False
        service.register_config(config)

        service._workflow_executor = AsyncMock(side_effect=Exception("Failure"))

        payload = WebhookPayload(data={})

        result = await service.trigger(
            workflow_id=config.workflow_id,
            payload=payload,
        )

        assert result.success is False
        assert result.retry_count == 0

    # -------------------------------------------------------------------------
    # Callback Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_callback_sent_on_success(self, service, config):
        """Test callback sent on success."""
        service.register_config(config)

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        service._http_client = mock_client

        payload = WebhookPayload(data={})

        result = await service.trigger(
            workflow_id=config.workflow_id,
            payload=payload,
        )

        assert result.success is True
        mock_client.post.assert_called_once()

        # Verify callback URL
        call_args = mock_client.post.call_args
        assert call_args[0][0] == config.callback_url

    @pytest.mark.asyncio
    async def test_callback_failure_does_not_affect_result(self, service, config):
        """Test callback failure doesn't affect trigger result."""
        service.register_config(config)

        # Mock HTTP client that fails
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Network error"))
        mock_client.aclose = AsyncMock()

        service._http_client = mock_client

        payload = WebhookPayload(data={})

        result = await service.trigger(
            workflow_id=config.workflow_id,
            payload=payload,
        )

        # Trigger should still succeed
        assert result.success is True

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_handle_error(self, service, config):
        """Test error handling."""
        service.register_config(config)

        error = WebhookError("Test error", code="TEST_ERROR")

        response = await service.handle_error(
            workflow_id=config.workflow_id,
            error=error,
        )

        assert response["success"] is False
        assert response["error"] == "Test error"
        assert response["error_code"] == "TEST_ERROR"


# =============================================================================
# Exception Tests
# =============================================================================


class TestWebhookExceptions:
    """Tests for webhook exceptions."""

    def test_webhook_error(self):
        """Test base webhook error."""
        error = WebhookError("Test message", code="TEST_CODE")

        assert str(error) == "Test message"
        assert error.code == "TEST_CODE"

    def test_signature_verification_error(self):
        """Test signature verification error."""
        error = SignatureVerificationError()

        assert "Invalid signature" in str(error)
        assert error.code == "INVALID_SIGNATURE"

    def test_config_not_found_error(self):
        """Test config not found error."""
        workflow_id = uuid4()
        error = WebhookConfigNotFoundError(workflow_id)

        assert str(workflow_id) in str(error)
        assert error.code == "CONFIG_NOT_FOUND"

    def test_disabled_error(self):
        """Test disabled error."""
        workflow_id = uuid4()
        error = WebhookDisabledError(workflow_id)

        assert str(workflow_id) in str(error)
        assert error.code == "WEBHOOK_DISABLED"


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enums."""

    def test_webhook_status_values(self):
        """Test webhook status values."""
        assert WebhookStatus.PENDING.value == "pending"
        assert WebhookStatus.PROCESSING.value == "processing"
        assert WebhookStatus.COMPLETED.value == "completed"
        assert WebhookStatus.FAILED.value == "failed"
        assert WebhookStatus.RETRYING.value == "retrying"

    def test_signature_algorithm_values(self):
        """Test signature algorithm values."""
        assert SignatureAlgorithm.HMAC_SHA256.value == "hmac-sha256"
        assert SignatureAlgorithm.HMAC_SHA512.value == "hmac-sha512"
