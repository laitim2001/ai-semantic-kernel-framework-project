"""
Unit tests for InputGateway

Tests:
- Source identification from headers
- Routing to appropriate handlers
- Metrics tracking
- Error handling

Sprint 95: Story 95-1 - InputGateway Tests (Phase 28)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.orchestration.input_gateway import (
    InputGateway,
    MockInputGateway,
    IncomingRequest,
    GatewayConfig,
    create_mock_gateway,
)
from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RoutingDecision,
)


class TestInputGateway:
    """Tests for InputGateway class."""

    def test_gateway_initialization(self):
        """Test gateway initializes with correct config."""
        config = GatewayConfig()
        handlers = {}
        gateway = InputGateway(source_handlers=handlers, config=config)

        assert gateway.config == config
        assert gateway.source_handlers == handlers
        assert gateway.business_router is None

    def test_identify_source_servicenow_header(self):
        """Test ServiceNow source identification via header."""
        gateway = InputGateway(source_handlers={})
        request = IncomingRequest(
            content="test",
            headers={"x-servicenow-webhook": "true"},
        )

        source = gateway._identify_source(request)
        assert source == "servicenow"

    def test_identify_source_prometheus_header(self):
        """Test Prometheus source identification via header."""
        gateway = InputGateway(source_handlers={})
        request = IncomingRequest(
            content="test",
            headers={"x-prometheus-alertmanager": "true"},
        )

        source = gateway._identify_source(request)
        assert source == "prometheus"

    def test_identify_source_explicit_type(self):
        """Test source identification via explicit source_type."""
        gateway = InputGateway(source_handlers={})
        request = IncomingRequest(
            content="test",
            source_type="custom_source",
        )

        source = gateway._identify_source(request)
        assert source == "custom_source"

    def test_identify_source_default_user(self):
        """Test default source is user."""
        gateway = InputGateway(source_handlers={})
        request = IncomingRequest(content="test")

        source = gateway._identify_source(request)
        assert source == "user"

    @pytest.mark.asyncio
    async def test_process_servicenow_request(self):
        """Test processing ServiceNow webhook request."""
        mock_handler = AsyncMock()
        mock_decision = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="software_issue",
            confidence=1.0,
            routing_layer="servicenow_mapping",
        )
        mock_handler.process.return_value = mock_decision

        gateway = InputGateway(
            source_handlers={"servicenow": mock_handler},
        )

        request = IncomingRequest(
            content="test",
            data={"number": "INC001", "category": "incident"},
            headers={"x-servicenow-webhook": "true"},
        )

        result = await gateway.process(request)

        mock_handler.process.assert_called_once_with(request)
        assert result.intent_category == ITIntentCategory.INCIDENT

    @pytest.mark.asyncio
    async def test_process_user_request_with_router(self):
        """Test processing user request with business router."""
        mock_router = AsyncMock()
        mock_decision = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            routing_layer="pattern",
        )
        mock_router.route.return_value = mock_decision

        gateway = InputGateway(
            source_handlers={},
            business_router=mock_router,
        )

        request = IncomingRequest(content="ETL failed")

        result = await gateway.process(request)

        mock_router.route.assert_called_once_with("ETL failed")
        assert result.intent_category == ITIntentCategory.INCIDENT

    @pytest.mark.asyncio
    async def test_process_no_handler_available(self):
        """Test processing when no handler is available."""
        gateway = InputGateway(source_handlers={})

        request = IncomingRequest(content="test")

        result = await gateway.process(request)

        assert result.intent_category == ITIntentCategory.UNKNOWN
        assert "No handler" in result.reasoning

    def test_metrics_tracking(self):
        """Test gateway tracks metrics correctly."""
        gateway = InputGateway(
            source_handlers={},
            config=GatewayConfig(enable_metrics=True),
        )

        assert gateway._metrics.total_requests == 0

        # Metrics are updated during process()
        metrics = gateway.get_metrics()
        assert "total_requests" in metrics
        assert "avg_latency_ms" in metrics

    def test_register_handler(self):
        """Test dynamic handler registration."""
        gateway = InputGateway(source_handlers={})
        mock_handler = MagicMock()

        gateway.register_handler("custom", mock_handler)

        assert "custom" in gateway.source_handlers
        assert gateway.source_handlers["custom"] == mock_handler

    def test_unregister_handler(self):
        """Test handler unregistration."""
        mock_handler = MagicMock()
        gateway = InputGateway(source_handlers={"custom": mock_handler})

        gateway.unregister_handler("custom")

        assert "custom" not in gateway.source_handlers


class TestMockInputGateway:
    """Tests for MockInputGateway."""

    def test_mock_gateway_initialization(self):
        """Test mock gateway initializes with mock handlers."""
        gateway = MockInputGateway()

        assert "servicenow" in gateway.source_handlers
        assert "prometheus" in gateway.source_handlers
        assert "user" in gateway.source_handlers
        assert gateway.business_router is not None

    @pytest.mark.asyncio
    async def test_mock_gateway_process_servicenow(self):
        """Test mock gateway processes ServiceNow requests."""
        gateway = MockInputGateway()

        request = IncomingRequest.from_servicenow_webhook({
            "number": "INC001",
            "category": "incident",
            "subcategory": "software",
            "short_description": "Test incident",
        })

        result = await gateway.process(request)

        assert result.intent_category in [
            ITIntentCategory.INCIDENT,
            ITIntentCategory.REQUEST,
            ITIntentCategory.CHANGE,
        ]

    @pytest.mark.asyncio
    async def test_mock_gateway_process_prometheus(self):
        """Test mock gateway processes Prometheus requests."""
        gateway = MockInputGateway()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": [{
                "alertname": "HighCPUUsage",
                "status": "firing",
                "labels": {"severity": "critical"},
            }]
        })

        result = await gateway.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT


class TestCreateMockGateway:
    """Tests for create_mock_gateway factory."""

    def test_create_mock_gateway(self):
        """Test factory creates mock gateway."""
        gateway = create_mock_gateway()

        assert isinstance(gateway, MockInputGateway)
        assert len(gateway.source_handlers) >= 3
