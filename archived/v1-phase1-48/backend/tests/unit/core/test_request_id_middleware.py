"""Unit tests for RequestIdMiddleware.

Sprint 122, Story 122-3: Tests X-Request-ID header tracking,
UUID generation, ContextVar propagation, and response headers.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.logging.middleware import RequestIdMiddleware, request_id_var


def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with RequestIdMiddleware."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    async def test_endpoint():
        """Return the current request_id from ContextVar."""
        return {"request_id": request_id_var.get("")}

    @app.get("/nested")
    async def nested_endpoint():
        """Verify request_id is accessible in nested calls."""
        rid = request_id_var.get("")
        return {"request_id": rid, "has_id": bool(rid)}

    return app


class TestRequestIdMiddleware:
    """Tests for RequestIdMiddleware behavior."""

    def setup_method(self):
        """Create fresh test client for each test."""
        self.app = _create_test_app()
        self.client = TestClient(self.app)

    def test_generates_uuid_when_no_header(self):
        """Should auto-generate UUID4 when X-Request-ID not provided."""
        response = self.client.get("/test")
        assert response.status_code == 200

        # Response should include X-Request-ID header
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None

        # Should be a valid UUID
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    def test_uses_client_provided_request_id(self):
        """Should use X-Request-ID from client when provided."""
        custom_id = "req-custom-12345"
        response = self.client.get(
            "/test",
            headers={"X-Request-ID": custom_id},
        )
        assert response.status_code == 200

        # Response header should echo the same ID
        assert response.headers.get("X-Request-ID") == custom_id

        # Endpoint should see the same ID via ContextVar
        assert response.json()["request_id"] == custom_id

    def test_contextvar_populated_during_request(self):
        """ContextVar should hold request_id during request lifecycle."""
        custom_id = "req-ctx-test-789"
        response = self.client.get(
            "/test",
            headers={"X-Request-ID": custom_id},
        )
        assert response.json()["request_id"] == custom_id

    def test_response_always_includes_header(self):
        """X-Request-ID should always be in response headers."""
        # Without client header
        response1 = self.client.get("/test")
        assert "X-Request-ID" in response1.headers

        # With client header
        response2 = self.client.get(
            "/test",
            headers={"X-Request-ID": "provided-id"},
        )
        assert response2.headers["X-Request-ID"] == "provided-id"

    def test_different_requests_get_different_ids(self):
        """Each request should get a unique ID when not provided."""
        response1 = self.client.get("/test")
        response2 = self.client.get("/test")

        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]

        assert id1 != id2

    def test_nested_endpoint_sees_request_id(self):
        """Request ID should be accessible in nested route handlers."""
        response = self.client.get(
            "/nested",
            headers={"X-Request-ID": "nested-test-id"},
        )
        data = response.json()
        assert data["request_id"] == "nested-test-id"
        assert data["has_id"] is True

    def test_contextvar_reset_after_request(self):
        """ContextVar should be reset after request completes."""
        # Make a request to populate the ContextVar
        self.client.get(
            "/test",
            headers={"X-Request-ID": "should-be-cleared"},
        )

        # After the request, the ContextVar default should be empty
        assert request_id_var.get("") == ""


class TestRequestIdVar:
    """Tests for the request_id_var ContextVar."""

    def test_default_is_empty_string(self):
        """Default value should be empty string."""
        assert request_id_var.get("") == ""

    def test_can_set_and_get(self):
        """Should support set/get operations."""
        token = request_id_var.set("test-id-123")
        assert request_id_var.get() == "test-id-123"
        request_id_var.reset(token)
        assert request_id_var.get("") == ""
