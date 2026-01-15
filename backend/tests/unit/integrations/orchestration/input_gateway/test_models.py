"""
Unit tests for Input Gateway Models

Tests:
- IncomingRequest model
- SourceType enum
- GatewayConfig
- GatewayMetrics

Sprint 95: Story 95-1 - Model Tests (Phase 28)
"""

import pytest
from datetime import datetime

from backend.src.integrations.orchestration.input_gateway import (
    IncomingRequest,
    SourceType,
    GatewayConfig,
    GatewayMetrics,
)


class TestSourceType:
    """Tests for SourceType enum."""

    def test_from_string_valid(self):
        """Test converting valid strings."""
        assert SourceType.from_string("servicenow") == SourceType.SERVICENOW
        assert SourceType.from_string("prometheus") == SourceType.PROMETHEUS
        assert SourceType.from_string("user") == SourceType.USER
        assert SourceType.from_string("api") == SourceType.API

    def test_from_string_case_insensitive(self):
        """Test case insensitivity."""
        assert SourceType.from_string("SERVICENOW") == SourceType.SERVICENOW
        assert SourceType.from_string("ServiceNow") == SourceType.SERVICENOW

    def test_from_string_unknown(self):
        """Test unknown string returns UNKNOWN."""
        assert SourceType.from_string("invalid") == SourceType.UNKNOWN
        assert SourceType.from_string("") == SourceType.UNKNOWN


class TestIncomingRequest:
    """Tests for IncomingRequest model."""

    def test_basic_initialization(self):
        """Test basic request initialization."""
        request = IncomingRequest(content="test message")

        assert request.content == "test message"
        assert request.data == {}
        assert request.headers == {}
        assert request.source_type is None

    def test_headers_normalized(self):
        """Test headers are normalized to lowercase."""
        request = IncomingRequest(
            content="test",
            headers={"X-Custom-Header": "value", "Content-Type": "application/json"},
        )

        assert "x-custom-header" in request.headers
        assert "content-type" in request.headers

    def test_get_header(self):
        """Test case-insensitive header retrieval."""
        request = IncomingRequest(
            content="test",
            headers={"x-servicenow-webhook": "true"},
        )

        assert request.get_header("X-ServiceNow-Webhook") == "true"
        assert request.get_header("X-SERVICENOW-WEBHOOK") == "true"
        assert request.get_header("nonexistent") is None
        assert request.get_header("nonexistent", "default") == "default"

    def test_has_header(self):
        """Test header existence check."""
        request = IncomingRequest(
            content="test",
            headers={"x-custom": "value"},
        )

        assert request.has_header("x-custom") is True
        assert request.has_header("X-Custom") is True
        assert request.has_header("nonexistent") is False

    def test_from_user_input(self):
        """Test factory method for user input."""
        request = IncomingRequest.from_user_input(
            "ETL failed today",
            request_id="req-001",
        )

        assert request.content == "ETL failed today"
        assert request.source_type == "user"
        assert request.request_id == "req-001"

    def test_from_servicenow_webhook(self):
        """Test factory method for ServiceNow webhook."""
        payload = {
            "number": "INC0012345",
            "category": "incident",
            "short_description": "Test incident",
        }

        request = IncomingRequest.from_servicenow_webhook(payload)

        assert request.content == "Test incident"
        assert request.source_type == "servicenow"
        assert request.request_id == "INC0012345"
        assert request.has_header("x-servicenow-webhook")
        assert request.data == payload

    def test_from_prometheus_webhook(self):
        """Test factory method for Prometheus webhook."""
        payload = {
            "alerts": [{
                "alertname": "HighCPU",
                "status": "firing",
                "annotations": {"summary": "High CPU on server-01"},
            }]
        }

        request = IncomingRequest.from_prometheus_webhook(payload)

        assert request.content == "High CPU on server-01"
        assert request.source_type == "prometheus"
        assert request.has_header("x-prometheus-alertmanager")
        assert request.data == payload

    def test_to_dict(self):
        """Test serialization to dictionary."""
        request = IncomingRequest(
            content="test",
            data={"key": "value"},
            source_type="user",
            request_id="123",
        )

        result = request.to_dict()

        assert result["content"] == "test"
        assert result["data"] == {"key": "value"}
        assert result["source_type"] == "user"
        assert result["request_id"] == "123"
        assert "timestamp" in result

    def test_timestamp_auto_set(self):
        """Test timestamp is automatically set."""
        request = IncomingRequest(content="test")

        assert isinstance(request.timestamp, datetime)


class TestGatewayConfig:
    """Tests for GatewayConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GatewayConfig()

        assert config.enable_schema_validation is True
        assert config.enable_metrics is True
        assert config.default_source_type == "user"
        assert config.max_content_length == 0
        assert config.servicenow_header == "x-servicenow-webhook"
        assert config.prometheus_header == "x-prometheus-alertmanager"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = GatewayConfig(
            enable_schema_validation=False,
            enable_metrics=False,
            default_source_type="api",
            max_content_length=1000,
        )

        assert config.enable_schema_validation is False
        assert config.enable_metrics is False
        assert config.default_source_type == "api"
        assert config.max_content_length == 1000


class TestGatewayMetrics:
    """Tests for GatewayMetrics model."""

    def test_initial_values(self):
        """Test initial metric values."""
        metrics = GatewayMetrics()

        assert metrics.total_requests == 0
        assert metrics.servicenow_requests == 0
        assert metrics.prometheus_requests == 0
        assert metrics.user_requests == 0
        assert metrics.validation_errors == 0
        assert metrics.latencies == []

    def test_avg_latency_empty(self):
        """Test average latency with no data."""
        metrics = GatewayMetrics()

        assert metrics.avg_latency_ms == 0.0

    def test_avg_latency_calculation(self):
        """Test average latency calculation."""
        metrics = GatewayMetrics()
        metrics.latencies = [10.0, 20.0, 30.0]

        assert metrics.avg_latency_ms == 20.0

    def test_p95_latency_empty(self):
        """Test P95 latency with no data."""
        metrics = GatewayMetrics()

        assert metrics.p95_latency_ms == 0.0

    def test_p95_latency_calculation(self):
        """Test P95 latency calculation."""
        metrics = GatewayMetrics()
        # Create 100 latencies from 1-100
        metrics.latencies = list(range(1, 101))

        # P95 should be around 95
        assert metrics.p95_latency_ms >= 95

    def test_record_latency(self):
        """Test recording latency."""
        metrics = GatewayMetrics()

        metrics.record_latency(10.0)
        metrics.record_latency(20.0)

        assert len(metrics.latencies) == 2
        assert metrics.latencies == [10.0, 20.0]

    def test_record_latency_max_limit(self):
        """Test latency list is capped at 1000."""
        metrics = GatewayMetrics()

        # Record more than 1000 latencies
        for i in range(1100):
            metrics.record_latency(float(i))

        assert len(metrics.latencies) == 1000

    def test_to_dict(self):
        """Test serialization to dictionary."""
        metrics = GatewayMetrics()
        metrics.total_requests = 100
        metrics.servicenow_requests = 50
        metrics.record_latency(10.0)

        result = metrics.to_dict()

        assert result["total_requests"] == 100
        assert result["servicenow_requests"] == 50
        assert "avg_latency_ms" in result
        assert "p95_latency_ms" in result
