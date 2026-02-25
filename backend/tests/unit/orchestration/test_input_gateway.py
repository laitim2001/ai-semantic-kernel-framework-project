"""
Tests for InputGateway and Related Models

Comprehensive test coverage for:
- IncomingRequest model and factory methods
- SourceType enum
- GatewayConfig defaults and from_env
- InputGateway processing (user, ServiceNow, Prometheus)
- Handler registration and metrics

Sprint 130: S130-2 - Input Gateway Tests
"""

import os
from unittest.mock import patch

import pytest
import pytest_asyncio

from tests.mocks.orchestration import (
    create_mock_gateway,
    MockInputGateway,
    MockServiceNowHandler,
    MockPrometheusHandler,
    MockBaseHandler,
)
from src.integrations.orchestration.input_gateway.gateway import (
    InputGateway,
    GatewayConfig,
)
from src.integrations.orchestration.input_gateway.models import (
    IncomingRequest,
    SourceType,
    GatewayMetrics,
)
from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RoutingDecision,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def gateway() -> MockInputGateway:
    """Create a mock-backed InputGateway via factory."""
    return create_mock_gateway()


# =============================================================================
# TestIncomingRequest
# =============================================================================


class TestIncomingRequest:
    """Test IncomingRequest model and factory methods."""

    def test_from_user_input(self):
        """from_user_input should create request with content and user source."""
        request = IncomingRequest.from_user_input(
            text="ETL Pipeline 失敗了",
            request_id="req-001",
        )

        assert request.content == "ETL Pipeline 失敗了"
        assert request.source_type == "user"
        assert request.request_id == "req-001"
        assert isinstance(request.data, dict)
        assert len(request.data) == 0

    def test_from_servicenow_webhook(self):
        """from_servicenow_webhook should create request with data and ServiceNow headers."""
        payload = {
            "number": "INC0012345",
            "category": "incident",
            "subcategory": "software",
            "short_description": "ETL batch job failure",
            "priority": "2",
        }
        headers = {"X-ServiceNow-Webhook": "true", "Content-Type": "application/json"}

        request = IncomingRequest.from_servicenow_webhook(
            payload=payload,
            headers=headers,
            request_id="sn-001",
        )

        assert request.content == "ETL batch job failure"
        assert request.data == payload
        assert request.source_type == "servicenow"
        assert request.request_id == "sn-001"
        # Headers are normalized to lowercase
        assert request.has_header("x-servicenow-webhook") is True
        assert request.get_header("x-servicenow-webhook") == "true"

    def test_from_prometheus_webhook(self):
        """from_prometheus_webhook should create request with alerts data."""
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "alertname": "HighCPUUsage",
                    "status": "firing",
                    "annotations": {
                        "summary": "CPU usage above 90% for 5 minutes",
                    },
                    "labels": {
                        "severity": "critical",
                        "instance": "web-server-01",
                    },
                },
            ],
        }
        headers = {"X-Prometheus-Alertmanager": "true"}

        request = IncomingRequest.from_prometheus_webhook(
            payload=payload,
            headers=headers,
            request_id="prom-001",
        )

        assert request.content == "CPU usage above 90% for 5 minutes"
        assert request.data == payload
        assert request.source_type == "prometheus"
        assert request.request_id == "prom-001"
        assert request.has_header("x-prometheus-alertmanager") is True

    def test_incoming_request_to_dict(self):
        """to_dict should return a serializable dictionary."""
        request = IncomingRequest.from_user_input(
            text="查詢工單狀態",
            request_id="req-002",
        )

        result = request.to_dict()

        assert isinstance(result, dict)
        assert result["content"] == "查詢工單狀態"
        assert result["source_type"] == "user"
        assert result["request_id"] == "req-002"
        assert "timestamp" in result
        assert "data" in result
        assert "headers" in result
        assert "metadata" in result

    def test_get_header_and_has_header(self):
        """get_header and has_header should work case-insensitively."""
        request = IncomingRequest(
            content="test",
            headers={
                "X-Custom-Header": "custom-value",
                "Authorization": "Bearer token123",
            },
        )

        # has_header: case-insensitive
        assert request.has_header("x-custom-header") is True
        assert request.has_header("X-Custom-Header") is True
        assert request.has_header("authorization") is True
        assert request.has_header("nonexistent") is False

        # get_header: case-insensitive with default
        assert request.get_header("x-custom-header") == "custom-value"
        assert request.get_header("Authorization") == "Bearer token123"
        assert request.get_header("nonexistent") is None
        assert request.get_header("nonexistent", "fallback") == "fallback"


# =============================================================================
# TestSourceType
# =============================================================================


class TestSourceType:
    """Test SourceType enum."""

    def test_source_type_enum(self):
        """All expected source type values should exist."""
        assert SourceType.SERVICENOW.value == "servicenow"
        assert SourceType.PROMETHEUS.value == "prometheus"
        assert SourceType.USER.value == "user"
        assert SourceType.API.value == "api"
        assert SourceType.UNKNOWN.value == "unknown"

    def test_source_type_from_string(self):
        """from_string should map known strings and default to UNKNOWN."""
        assert SourceType.from_string("servicenow") == SourceType.SERVICENOW
        assert SourceType.from_string("SERVICENOW") == SourceType.SERVICENOW
        assert SourceType.from_string("prometheus") == SourceType.PROMETHEUS
        assert SourceType.from_string("user") == SourceType.USER
        assert SourceType.from_string("api") == SourceType.API
        assert SourceType.from_string("unknown") == SourceType.UNKNOWN
        assert SourceType.from_string("nonexistent_source") == SourceType.UNKNOWN
        assert SourceType.from_string("") == SourceType.UNKNOWN


# =============================================================================
# TestGatewayConfig
# =============================================================================


class TestGatewayConfig:
    """Test GatewayConfig defaults and environment loading."""

    def test_gateway_config_defaults(self):
        """Default config values should be set correctly."""
        config = GatewayConfig()

        assert config.enable_schema_validation is True
        assert config.enable_metrics is True
        assert config.default_source_type == "user"
        assert config.max_content_length == 0
        assert config.servicenow_header == "x-servicenow-webhook"
        assert config.prometheus_header == "x-prometheus-alertmanager"

    def test_gateway_config_from_env(self):
        """from_env should read configuration from environment variables."""
        env_vars = {
            "GATEWAY_ENABLE_SCHEMA_VALIDATION": "false",
            "GATEWAY_ENABLE_METRICS": "false",
            "GATEWAY_DEFAULT_SOURCE_TYPE": "api",
            "GATEWAY_MAX_CONTENT_LENGTH": "5000",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = GatewayConfig.from_env()

        assert config.enable_schema_validation is False
        assert config.enable_metrics is False
        assert config.default_source_type == "api"
        assert config.max_content_length == 5000


# =============================================================================
# TestInputGateway
# =============================================================================


class TestInputGateway:
    """Test InputGateway processing different request types."""

    @pytest.mark.asyncio
    async def test_gateway_user_input(self, gateway: MockInputGateway):
        """Processing user text should return a RoutingDecision."""
        request = IncomingRequest.from_user_input(
            text="ETL Pipeline 今天凌晨失敗了，影響到報表產出",
        )

        decision = await gateway.process(request)

        assert isinstance(decision, RoutingDecision)
        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.confidence > 0.0

    @pytest.mark.asyncio
    async def test_gateway_servicenow_input(self, gateway: MockInputGateway):
        """Processing ServiceNow webhook should return a RoutingDecision."""
        payload = {
            "number": "INC0067890",
            "category": "incident",
            "subcategory": "software",
            "short_description": "Database connection timeout",
            "priority": "1",
        }

        request = IncomingRequest.from_servicenow_webhook(payload=payload)

        decision = await gateway.process(request)

        assert isinstance(decision, RoutingDecision)
        assert decision.intent_category is not None
        assert decision.confidence > 0.0

    @pytest.mark.asyncio
    async def test_gateway_prometheus_input(self, gateway: MockInputGateway):
        """Processing Prometheus alert should return a RoutingDecision."""
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "alertname": "HighMemoryUsage",
                    "status": "firing",
                    "annotations": {
                        "summary": "Memory usage exceeds 95%",
                    },
                    "labels": {
                        "severity": "warning",
                        "instance": "app-server-02",
                    },
                },
            ],
        }

        request = IncomingRequest.from_prometheus_webhook(payload=payload)

        decision = await gateway.process(request)

        assert isinstance(decision, RoutingDecision)
        assert decision.intent_category is not None

    @pytest.mark.asyncio
    async def test_gateway_register_handler(self, gateway: MockInputGateway):
        """Registering a custom handler should make it available for processing."""
        custom_handler = MockBaseHandler(
            handler_type_name="custom",
            default_intent="request",
            default_sub_intent="custom_request",
        )

        gateway.register_handler("custom_source", custom_handler)

        assert "custom_source" in gateway.source_handlers

        # Process a request with the custom source
        request = IncomingRequest(
            content="custom request data",
            headers={"x-webhook-source": "custom_source"},
        )
        decision = await gateway.process(request)

        assert isinstance(decision, RoutingDecision)
        assert decision.intent_category == ITIntentCategory.REQUEST

    @pytest.mark.asyncio
    async def test_gateway_unregister_handler(self, gateway: MockInputGateway):
        """Unregistering a handler should remove it from source_handlers."""
        assert "servicenow" in gateway.source_handlers

        gateway.unregister_handler("servicenow")

        assert "servicenow" not in gateway.source_handlers

    def test_gateway_metrics(self, gateway: MockInputGateway):
        """get_metrics should return a dict and reset_metrics should clear it."""
        metrics = gateway.get_metrics()

        assert isinstance(metrics, dict)
        assert "total_requests" in metrics
        assert "servicenow_requests" in metrics
        assert "prometheus_requests" in metrics
        assert "user_requests" in metrics
        assert "validation_errors" in metrics
        assert "avg_latency_ms" in metrics
        assert "p95_latency_ms" in metrics

        # Initial metrics should all be zero
        assert metrics["total_requests"] == 0

        # Reset and verify still returns valid dict
        gateway.reset_metrics()
        metrics_after = gateway.get_metrics()
        assert metrics_after["total_requests"] == 0

    @pytest.mark.asyncio
    async def test_gateway_metrics_after_processing(self, gateway: MockInputGateway):
        """Metrics should update after processing requests."""
        # Use a ServiceNow request which routes to the servicenow handler
        # and increments servicenow_requests counter
        sn_request = IncomingRequest.from_servicenow_webhook(
            payload={
                "number": "INC0099999",
                "category": "incident",
                "short_description": "Test metric tracking",
            }
        )
        await gateway.process(sn_request)

        metrics = gateway.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["servicenow_requests"] == 1

        # Process a user input that goes through the business_router path
        # (source_type="user" matches the "user" source handler in MockInputGateway,
        # but we can also test with a request that has no matching handler header
        # and no source_type to trigger the business_router fallback path)
        user_request = IncomingRequest(content="查詢系統狀態")
        await gateway.process(user_request)

        metrics_after = gateway.get_metrics()
        assert metrics_after["total_requests"] == 2
