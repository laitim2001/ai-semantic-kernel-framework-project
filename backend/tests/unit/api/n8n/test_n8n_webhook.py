"""Tests for n8n Webhook API Routes.

Sprint 124: n8n Integration — Mode 1 + Mode 2

Tests cover:
    - Webhook endpoint (POST /api/v1/n8n/webhook)
    - Workflow-specific webhook (POST /api/v1/n8n/webhook/{workflow_id})
    - HMAC signature verification
    - Connection status endpoint (GET /api/v1/n8n/status)
    - Configuration endpoints (GET/PUT /api/v1/n8n/config)
    - Webhook payload validation
    - Action routing (analyze, classify, execute, query, notify)
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.n8n.routes import router, _n8n_config
from src.api.v1.n8n.schemas import (
    N8nWebhookPayload,
    N8nWebhookResponse,
    N8nStatusResponse,
    N8nConfigResponse,
    N8nConfigUpdate,
    WebhookAction,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a test FastAPI app with n8n router."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def valid_webhook_payload():
    """Create a valid webhook payload."""
    return {
        "workflow_id": "wf-test-123",
        "execution_id": "exec-test-456",
        "action": "analyze",
        "data": {"incident_id": "INC001", "description": "Server down"},
        "callback_url": "http://n8n:5678/webhook/callback",
        "metadata": {"source": "test"},
    }


@pytest.fixture(autouse=True)
def reset_config():
    """Reset n8n config between tests."""
    original = _n8n_config.copy()
    yield
    _n8n_config.update(original)


# ---------------------------------------------------------------------------
# Webhook Endpoint Tests
# ---------------------------------------------------------------------------


class TestWebhookEndpoint:
    """Tests for POST /api/v1/n8n/webhook."""

    def test_webhook_analyze_action(self, client, valid_webhook_payload):
        """Test webhook with analyze action."""
        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "analyze"
        assert data["request_id"]  # Should have a UUID
        assert data["result"]["action"] == "analyze"

    def test_webhook_classify_action(self, client, valid_webhook_payload):
        """Test webhook with classify action."""
        valid_webhook_payload["action"] = "classify"

        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "classify"

    def test_webhook_execute_action(self, client, valid_webhook_payload):
        """Test webhook with execute action."""
        valid_webhook_payload["action"] = "execute"

        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "execute"

    def test_webhook_query_action(self, client, valid_webhook_payload):
        """Test webhook with query action."""
        valid_webhook_payload["action"] = "query"

        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "query"

    def test_webhook_notify_action(self, client, valid_webhook_payload):
        """Test webhook with notify action."""
        valid_webhook_payload["action"] = "notify"
        valid_webhook_payload["data"] = {"message": "Task completed"}

        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "notify"
        assert data["result"]["acknowledged"] is True

    def test_webhook_invalid_action(self, client, valid_webhook_payload):
        """Test webhook with invalid action returns 422."""
        valid_webhook_payload["action"] = "invalid_action"

        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
        )

        assert response.status_code == 422  # Pydantic validation error


# ---------------------------------------------------------------------------
# Workflow-Specific Webhook Tests
# ---------------------------------------------------------------------------


class TestWorkflowWebhook:
    """Tests for POST /api/v1/n8n/webhook/{workflow_id}."""

    def test_workflow_webhook_overrides_workflow_id(self, client, valid_webhook_payload):
        """Test that URL workflow_id overrides payload."""
        response = client.post(
            "/api/v1/n8n/webhook/wf-override-999",
            json=valid_webhook_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # The result should reflect the URL workflow_id
        assert data["result"]["analysis"]["source_workflow"] == "wf-override-999"


# ---------------------------------------------------------------------------
# HMAC Signature Verification Tests
# ---------------------------------------------------------------------------


class TestHMACVerification:
    """Tests for HMAC signature verification."""

    def test_webhook_without_hmac_secret_passes(self, client, valid_webhook_payload):
        """Test webhook passes when HMAC secret is not configured."""
        # Default: no HMAC secret configured, should pass
        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
        )

        assert response.status_code == 200

    @patch("src.api.v1.n8n.routes._WEBHOOK_HMAC_SECRET", "test-secret-key")
    def test_webhook_with_valid_hmac(self, client, valid_webhook_payload):
        """Test webhook passes with valid HMAC signature."""
        # Must use the exact same bytes that TestClient sends
        payload_bytes = json.dumps(
            valid_webhook_payload, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        expected_sig = hmac.new(
            b"test-secret-key", payload_bytes, hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/api/v1/n8n/webhook",
            content=payload_bytes,
            headers={
                "X-N8N-Signature": f"sha256={expected_sig}",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200

    @patch("src.api.v1.n8n.routes._WEBHOOK_HMAC_SECRET", "test-secret-key")
    def test_webhook_with_invalid_hmac(self, client, valid_webhook_payload):
        """Test webhook rejects invalid HMAC signature."""
        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
            headers={"X-N8N-Signature": "sha256=invalid_signature"},
        )

        assert response.status_code == 401

    @patch("src.api.v1.n8n.routes._WEBHOOK_HMAC_SECRET", "test-secret-key")
    def test_webhook_without_signature_header(self, client, valid_webhook_payload):
        """Test webhook rejects missing signature when HMAC is configured."""
        response = client.post(
            "/api/v1/n8n/webhook",
            json=valid_webhook_payload,
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Payload Validation Tests
# ---------------------------------------------------------------------------


class TestPayloadValidation:
    """Tests for webhook payload validation."""

    def test_missing_workflow_id(self, client):
        """Test payload without workflow_id returns 422."""
        payload = {
            "execution_id": "exec-1",
            "action": "analyze",
            "data": {},
        }
        response = client.post("/api/v1/n8n/webhook", json=payload)
        assert response.status_code == 422

    def test_missing_execution_id(self, client):
        """Test payload without execution_id returns 422."""
        payload = {
            "workflow_id": "wf-1",
            "action": "analyze",
            "data": {},
        }
        response = client.post("/api/v1/n8n/webhook", json=payload)
        assert response.status_code == 422

    def test_missing_action(self, client):
        """Test payload without action returns 422."""
        payload = {
            "workflow_id": "wf-1",
            "execution_id": "exec-1",
            "data": {},
        }
        response = client.post("/api/v1/n8n/webhook", json=payload)
        assert response.status_code == 422

    def test_empty_data_is_allowed(self, client):
        """Test that empty data dict is allowed."""
        payload = {
            "workflow_id": "wf-1",
            "execution_id": "exec-1",
            "action": "query",
        }
        response = client.post("/api/v1/n8n/webhook", json=payload)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Connection Status Tests
# ---------------------------------------------------------------------------


class TestStatusEndpoint:
    """Tests for GET /api/v1/n8n/status."""

    def test_status_without_api_key(self, client, monkeypatch):
        """Test status when API key is not configured."""
        monkeypatch.delenv("N8N_API_KEY", raising=False)

        response = client.get("/api/v1/n8n/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disconnected"
        assert data["healthy"] is False
        assert "not configured" in data["error"].lower()


# ---------------------------------------------------------------------------
# Configuration Endpoint Tests
# ---------------------------------------------------------------------------


class TestConfigEndpoints:
    """Tests for GET/PUT /api/v1/n8n/config."""

    def test_get_config(self, client):
        """Test getting current configuration."""
        response = client.get("/api/v1/n8n/config")

        assert response.status_code == 200
        data = response.json()
        assert "base_url" in data
        assert "timeout" in data
        assert "max_retries" in data
        assert "api_key_configured" in data
        assert "webhook_hmac_configured" in data
        # Should NOT expose actual secrets
        assert "api_key" not in data

    def test_update_config_base_url(self, client):
        """Test updating base URL."""
        response = client.put(
            "/api/v1/n8n/config",
            json={"base_url": "http://new-n8n:5678"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["base_url"] == "http://new-n8n:5678"

    def test_update_config_timeout(self, client):
        """Test updating timeout."""
        response = client.put(
            "/api/v1/n8n/config",
            json={"timeout": 60},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["timeout"] == 60

    def test_update_config_invalid_timeout(self, client):
        """Test updating timeout with invalid value returns 422."""
        response = client.put(
            "/api/v1/n8n/config",
            json={"timeout": 1},  # Below minimum of 5
        )

        assert response.status_code == 422

    def test_update_config_invalid_base_url(self, client):
        """Test updating base_url with invalid URL returns 422."""
        response = client.put(
            "/api/v1/n8n/config",
            json={"base_url": "not-a-url"},
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Schema Model Tests
# ---------------------------------------------------------------------------


class TestSchemaModels:
    """Tests for Pydantic schema models."""

    def test_webhook_payload_all_actions(self):
        """Test all WebhookAction enum values are valid."""
        for action in WebhookAction:
            payload = N8nWebhookPayload(
                workflow_id="wf-1",
                execution_id="exec-1",
                action=action,
            )
            assert payload.action == action

    def test_webhook_payload_defaults(self):
        """Test webhook payload default values."""
        payload = N8nWebhookPayload(
            workflow_id="wf-1",
            execution_id="exec-1",
            action=WebhookAction.ANALYZE,
        )
        assert payload.data == {}
        assert payload.callback_url is None
        assert payload.metadata == {}

    def test_config_update_validation(self):
        """Test N8nConfigUpdate validation."""
        update = N8nConfigUpdate(
            base_url="http://localhost:5678",
            timeout=30,
            max_retries=3,
        )
        assert update.base_url == "http://localhost:5678"
        assert update.timeout == 30
        assert update.max_retries == 3

    def test_config_update_strips_trailing_slash(self):
        """Test base_url trailing slash is stripped."""
        update = N8nConfigUpdate(base_url="http://localhost:5678/")
        assert update.base_url == "http://localhost:5678"
