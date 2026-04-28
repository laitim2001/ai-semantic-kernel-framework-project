"""
Unit tests for Source Handlers

Tests:
- ServiceNowHandler mapping and pattern fallback
- PrometheusHandler alert pattern matching
- UserInputHandler delegation to BusinessIntentRouter

Sprint 95: Story 95-3, 95-4, 95-5 - Source Handler Tests (Phase 28)
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.orchestration.input_gateway import (
    IncomingRequest,
    ServiceNowHandler,
    MockServiceNowHandler,
    PrometheusHandler,
    MockPrometheusHandler,
    UserInputHandler,
    MockUserInputHandler,
)
from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    PatternMatchResult,
)


class TestServiceNowHandler:
    """Tests for ServiceNowHandler."""

    def test_handler_type(self):
        """Test handler type identifier."""
        handler = ServiceNowHandler()
        assert handler.handler_type == "servicenow"

    @pytest.mark.asyncio
    async def test_process_incident_software(self):
        """Test processing incident/software category."""
        handler = ServiceNowHandler()

        request = IncomingRequest.from_servicenow_webhook({
            "number": "INC0012345",
            "category": "incident",
            "subcategory": "software",
            "short_description": "Application crashed",
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "software_issue"
        assert result.confidence == 1.0
        assert "servicenow_mapping" in result.routing_layer

    @pytest.mark.asyncio
    async def test_process_incident_hardware(self):
        """Test processing incident/hardware category."""
        handler = ServiceNowHandler()

        request = IncomingRequest.from_servicenow_webhook({
            "number": "INC0012346",
            "category": "incident",
            "subcategory": "hardware",
            "short_description": "Server disk failure",
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "hardware_failure"

    @pytest.mark.asyncio
    async def test_process_request_access(self):
        """Test processing request/access category."""
        handler = ServiceNowHandler()

        request = IncomingRequest.from_servicenow_webhook({
            "number": "REQ0012345",
            "category": "request",
            "subcategory": "access",
            "short_description": "Need access to production DB",
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.REQUEST
        assert result.sub_intent == "access_request"

    @pytest.mark.asyncio
    async def test_process_change_emergency(self):
        """Test processing change/emergency category."""
        handler = ServiceNowHandler()

        request = IncomingRequest.from_servicenow_webhook({
            "number": "CHG0012345",
            "category": "change",
            "subcategory": "emergency",
            "short_description": "Emergency hotfix deployment",
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.CHANGE
        assert result.sub_intent == "emergency_change"

    @pytest.mark.asyncio
    async def test_process_with_pattern_fallback(self):
        """Test pattern matcher fallback for unknown category."""
        mock_pattern_matcher = MagicMock()
        mock_pattern_matcher.match.return_value = PatternMatchResult(
            matched=True,
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
            matched_pattern="ETL.*失敗",
        )

        handler = ServiceNowHandler(pattern_matcher=mock_pattern_matcher)

        request = IncomingRequest.from_servicenow_webhook({
            "number": "INC0012345",
            "category": "incident",
            "subcategory": "unknown_category",  # Not in mapping
            "short_description": "ETL Pipeline 失敗",
        })

        result = await handler.process(request)

        mock_pattern_matcher.match.assert_called_once()
        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "etl_failure"

    @pytest.mark.asyncio
    async def test_process_priority_to_risk_mapping(self):
        """Test priority to risk level mapping."""
        handler = ServiceNowHandler()

        # Critical priority
        request = IncomingRequest.from_servicenow_webhook({
            "number": "INC001",
            "category": "incident",
            "subcategory": "software",
            "short_description": "Critical issue",
            "priority": "1",
        })

        result = await handler.process(request)
        assert result.risk_level.value == "critical"

    @pytest.mark.asyncio
    async def test_process_latency_under_10ms(self):
        """Test processing latency is under target."""
        handler = ServiceNowHandler()

        request = IncomingRequest.from_servicenow_webhook({
            "number": "INC001",
            "category": "incident",
            "subcategory": "software",
            "short_description": "Test",
        })

        result = await handler.process(request)

        assert result.processing_time_ms < 50  # Allow some margin

    @pytest.mark.asyncio
    async def test_process_empty_data(self):
        """Test handling empty data."""
        handler = ServiceNowHandler()

        request = IncomingRequest(data={})

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.UNKNOWN


class TestPrometheusHandler:
    """Tests for PrometheusHandler."""

    def test_handler_type(self):
        """Test handler type identifier."""
        handler = PrometheusHandler()
        assert handler.handler_type == "prometheus"

    @pytest.mark.asyncio
    async def test_process_high_cpu_alert(self):
        """Test processing high CPU alert."""
        handler = PrometheusHandler()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": [{
                "alertname": "HighCPUUsage",
                "status": "firing",
                "labels": {"severity": "warning"},
            }]
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "performance_issue"

    @pytest.mark.asyncio
    async def test_process_service_down_alert(self):
        """Test processing service down alert."""
        handler = PrometheusHandler()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": [{
                "alertname": "ServiceDown",
                "status": "firing",
                "labels": {"severity": "critical"},
            }]
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "service_down"

    @pytest.mark.asyncio
    async def test_process_memory_alert(self):
        """Test processing memory alert."""
        handler = PrometheusHandler()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": [{
                "alertname": "HighMemoryUsage",
                "status": "firing",
                "labels": {"severity": "warning"},
            }]
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "memory_issue"

    @pytest.mark.asyncio
    async def test_process_disk_alert(self):
        """Test processing disk alert."""
        handler = PrometheusHandler()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": [{
                "alertname": "DiskSpaceLow",
                "status": "firing",
                "labels": {"severity": "warning"},
            }]
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "disk_issue"

    @pytest.mark.asyncio
    async def test_process_critical_severity_risk(self):
        """Test critical severity maps to critical risk."""
        handler = PrometheusHandler()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": [{
                "alertname": "ServiceDown",
                "status": "firing",
                "labels": {"severity": "critical"},
            }]
        })

        result = await handler.process(request)
        assert result.risk_level.value == "critical"

    @pytest.mark.asyncio
    async def test_process_extracts_metadata(self):
        """Test metadata extraction from alerts."""
        handler = PrometheusHandler()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": [{
                "alertname": "HighCPU",
                "status": "firing",
                "labels": {"instance": "server-01", "severity": "warning"},
                "annotations": {"summary": "High CPU on server-01"},
            }]
        })

        result = await handler.process(request)

        assert result.metadata.get("alertname") == "HighCPU"
        assert result.metadata.get("labels", {}).get("instance") == "server-01"
        assert result.metadata.get("summary") == "High CPU on server-01"

    @pytest.mark.asyncio
    async def test_process_empty_alerts(self):
        """Test handling empty alerts array."""
        handler = PrometheusHandler()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": []
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.UNKNOWN


class TestUserInputHandler:
    """Tests for UserInputHandler."""

    def test_handler_type(self):
        """Test handler type identifier."""
        handler = UserInputHandler()
        assert handler.handler_type == "user"

    @pytest.mark.asyncio
    async def test_process_delegates_to_router(self):
        """Test processing delegates to business router."""
        from src.integrations.orchestration.intent_router.models import (
            CompletenessInfo,
            RoutingDecision,
            WorkflowType,
            RiskLevel,
        )

        mock_router = AsyncMock()
        mock_router.route.return_value = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
            workflow_type=WorkflowType.SEQUENTIAL,
            risk_level=RiskLevel.MEDIUM,
            completeness=CompletenessInfo(),
            routing_layer="pattern",
            metadata={},
        )

        handler = UserInputHandler(business_router=mock_router)

        request = IncomingRequest.from_user_input("ETL 今天跑失敗了")

        result = await handler.process(request)

        mock_router.route.assert_called_once_with("ETL 今天跑失敗了")
        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "etl_failure"

    @pytest.mark.asyncio
    async def test_process_normalizes_input(self):
        """Test input normalization."""
        mock_router = AsyncMock()
        from src.integrations.orchestration.intent_router.models import (
            CompletenessInfo,
            RoutingDecision,
            WorkflowType,
            RiskLevel,
        )
        mock_router.route.return_value = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            completeness=CompletenessInfo(),
            metadata={},
        )

        handler = UserInputHandler(business_router=mock_router)

        # Input with extra whitespace
        request = IncomingRequest(content="  ETL   failed   today  ")

        result = await handler.process(request)

        # Should normalize to single spaces
        mock_router.route.assert_called_once_with("ETL failed today")

    @pytest.mark.asyncio
    async def test_process_empty_input(self):
        """Test handling empty input."""
        handler = UserInputHandler(business_router=MagicMock())

        request = IncomingRequest(content="")

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.UNKNOWN

    @pytest.mark.asyncio
    async def test_process_no_router_configured(self):
        """Test error when no router configured."""
        handler = UserInputHandler(business_router=None)

        request = IncomingRequest.from_user_input("test")

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.UNKNOWN
        assert "not configured" in result.reasoning


class TestMockServiceNowHandler:
    """Tests for MockServiceNowHandler."""

    @pytest.mark.asyncio
    async def test_mock_processes_request(self):
        """Test mock handler processes requests."""
        handler = MockServiceNowHandler()

        request = IncomingRequest.from_servicenow_webhook({
            "number": "INC001",
            "category": "incident",
            "subcategory": "software",
            "short_description": "Test",
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT


class TestMockPrometheusHandler:
    """Tests for MockPrometheusHandler."""

    @pytest.mark.asyncio
    async def test_mock_processes_request(self):
        """Test mock handler processes requests."""
        handler = MockPrometheusHandler()

        request = IncomingRequest.from_prometheus_webhook({
            "alerts": [{
                "alertname": "HighCPU",
                "status": "firing",
            }]
        })

        result = await handler.process(request)

        assert result.intent_category == ITIntentCategory.INCIDENT


class TestMockUserInputHandler:
    """Tests for MockUserInputHandler."""

    @pytest.mark.asyncio
    async def test_mock_processes_request(self):
        """Test mock handler processes requests."""
        handler = MockUserInputHandler()

        request = IncomingRequest.from_user_input("ETL failed")

        result = await handler.process(request)

        assert result.intent_category in [
            ITIntentCategory.INCIDENT,
            ITIntentCategory.REQUEST,
            ITIntentCategory.QUERY,
            ITIntentCategory.CHANGE,
            ITIntentCategory.UNKNOWN,
        ]
