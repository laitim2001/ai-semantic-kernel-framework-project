"""
Unit Tests for L4a/L4b Layer Contracts.

Tests for:
- Shared contracts (InputSource, RoutingRequest, RoutingResult)
- L4a contracts (InputProcessorProtocol, InputValidationResult, InputProcessingMetrics)
- L4b contracts (RoutingLayerProtocol, RoutingPipelineResult, DecisionEngineProtocol)
- Abstract base class enforcement
- Adapter functions (incoming_request_to_routing_request, routing_decision_to_routing_result)

Sprint 116: L4a/L4b Layer Split Contracts (Phase 34)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from src.integrations.orchestration.contracts import (
    InputGatewayProtocol,
    InputSource,
    RouterProtocol,
    RoutingRequest,
    RoutingResult,
    incoming_request_to_routing_request,
    routing_decision_to_routing_result,
)
from src.integrations.orchestration.input.contracts import (
    InputProcessingMetrics,
    InputProcessorProtocol,
    InputValidationResult,
    InputValidatorProtocol,
)
from src.integrations.orchestration.intent_router.contracts import (
    DecisionEngineProtocol,
    LayerExecutionMetric,
    RoutingLayerProtocol,
    RoutingPipelineResult,
)


# =============================================================================
# InputSource Enum Tests
# =============================================================================


class TestInputSource:
    """Tests for InputSource enum."""

    def test_all_values_exist(self):
        """All InputSource values should be defined."""
        assert InputSource.WEBHOOK_SERVICENOW.value == "webhook_servicenow"
        assert InputSource.WEBHOOK_PROMETHEUS.value == "webhook_prometheus"
        assert InputSource.HTTP_API.value == "http_api"
        assert InputSource.SSE_STREAM.value == "sse_stream"
        assert InputSource.USER_CHAT.value == "user_chat"
        assert InputSource.RITM.value == "ritm"
        assert InputSource.UNKNOWN.value == "unknown"

    def test_string_conversion(self):
        """InputSource should convert to and from string."""
        assert str(InputSource.WEBHOOK_SERVICENOW) == "InputSource.WEBHOOK_SERVICENOW"
        assert InputSource("webhook_servicenow") == InputSource.WEBHOOK_SERVICENOW
        assert InputSource("unknown") == InputSource.UNKNOWN

    def test_is_str_subclass(self):
        """InputSource should be a str subclass for JSON serialization."""
        assert isinstance(InputSource.USER_CHAT, str)
        assert InputSource.USER_CHAT == "user_chat"

    def test_invalid_value_raises(self):
        """Invalid value should raise ValueError."""
        with pytest.raises(ValueError):
            InputSource("nonexistent_source")

    def test_total_count(self):
        """There should be exactly 7 input source types."""
        assert len(InputSource) == 7


# =============================================================================
# RoutingRequest Tests
# =============================================================================


class TestRoutingRequest:
    """Tests for RoutingRequest dataclass."""

    def test_creation_with_defaults(self):
        """Should create RoutingRequest with default values."""
        request = RoutingRequest(query="test query")
        assert request.query == "test query"
        assert request.intent_hint is None
        assert request.context == {}
        assert request.source == InputSource.UNKNOWN
        assert request.request_id is None
        assert isinstance(request.timestamp, datetime)
        assert request.metadata == {}
        assert request.priority is None

    def test_creation_with_all_fields(self):
        """Should create RoutingRequest with all fields specified."""
        ts = datetime(2026, 2, 24, 12, 0, 0)
        request = RoutingRequest(
            query="reset password",
            intent_hint="request",
            context={"user_id": "u123"},
            source=InputSource.USER_CHAT,
            request_id="req-001",
            timestamp=ts,
            metadata={"channel": "web"},
            priority=2,
        )
        assert request.query == "reset password"
        assert request.intent_hint == "request"
        assert request.context == {"user_id": "u123"}
        assert request.source == InputSource.USER_CHAT
        assert request.request_id == "req-001"
        assert request.timestamp == ts
        assert request.metadata == {"channel": "web"}
        assert request.priority == 2

    def test_to_dict(self):
        """Should serialize to dictionary correctly."""
        ts = datetime(2026, 1, 15, 10, 30, 0)
        request = RoutingRequest(
            query="ETL pipeline failed",
            source=InputSource.WEBHOOK_PROMETHEUS,
            request_id="r-42",
            timestamp=ts,
            priority=1,
        )
        result = request.to_dict()
        assert result["query"] == "ETL pipeline failed"
        assert result["source"] == "webhook_prometheus"
        assert result["request_id"] == "r-42"
        assert result["timestamp"] == "2026-01-15T10:30:00"
        assert result["priority"] == 1
        assert result["intent_hint"] is None
        assert result["context"] == {}
        assert result["metadata"] == {}

    def test_from_dict(self):
        """Should deserialize from dictionary correctly."""
        data = {
            "query": "need new VM",
            "intent_hint": "request",
            "context": {"dept": "IT"},
            "source": "user_chat",
            "request_id": "req-99",
            "timestamp": "2026-02-20T08:00:00",
            "metadata": {"lang": "zh-TW"},
            "priority": 3,
        }
        request = RoutingRequest.from_dict(data)
        assert request.query == "need new VM"
        assert request.intent_hint == "request"
        assert request.context == {"dept": "IT"}
        assert request.source == InputSource.USER_CHAT
        assert request.request_id == "req-99"
        assert request.timestamp == datetime(2026, 2, 20, 8, 0, 0)
        assert request.metadata == {"lang": "zh-TW"}
        assert request.priority == 3

    def test_from_dict_with_unknown_source(self):
        """Should default to UNKNOWN for unrecognized source strings."""
        data = {"query": "test", "source": "totally_invalid_source"}
        request = RoutingRequest.from_dict(data)
        assert request.source == InputSource.UNKNOWN

    def test_from_dict_missing_fields(self):
        """Should handle missing fields with defaults."""
        data = {}
        request = RoutingRequest.from_dict(data)
        assert request.query == ""
        assert request.intent_hint is None
        assert request.context == {}
        assert request.source == InputSource.UNKNOWN
        assert request.request_id is None
        assert isinstance(request.timestamp, datetime)
        assert request.metadata == {}
        assert request.priority is None

    def test_roundtrip_serialization(self):
        """to_dict -> from_dict should produce equivalent object."""
        original = RoutingRequest(
            query="server down",
            intent_hint="incident",
            context={"severity": "high"},
            source=InputSource.WEBHOOK_SERVICENOW,
            request_id="sn-123",
            timestamp=datetime(2026, 3, 1, 12, 0, 0),
            metadata={"ticket": "INC001"},
            priority=1,
        )
        serialized = original.to_dict()
        restored = RoutingRequest.from_dict(serialized)

        assert restored.query == original.query
        assert restored.intent_hint == original.intent_hint
        assert restored.context == original.context
        assert restored.source == original.source
        assert restored.request_id == original.request_id
        assert restored.timestamp == original.timestamp
        assert restored.metadata == original.metadata
        assert restored.priority == original.priority

    def test_from_dict_with_none_timestamp(self):
        """Should handle None timestamp by generating current time."""
        data = {"query": "test", "timestamp": None}
        request = RoutingRequest.from_dict(data)
        assert isinstance(request.timestamp, datetime)

    def test_from_dict_with_input_source_enum(self):
        """Should handle InputSource enum as source value."""
        data = {"query": "test", "source": InputSource.HTTP_API}
        # If source is already an InputSource, it should not go through string conversion
        # but from_dict expects a dict from serialized data, so this tests edge case
        request = RoutingRequest.from_dict(data)
        assert request.source == InputSource.HTTP_API


# =============================================================================
# RoutingResult Tests
# =============================================================================


class TestRoutingResult:
    """Tests for RoutingResult dataclass."""

    def test_creation_with_defaults(self):
        """Should create RoutingResult with default values."""
        result = RoutingResult(intent="incident")
        assert result.intent == "incident"
        assert result.sub_intent == ""
        assert result.confidence == 0.0
        assert result.matched_layer == ""
        assert result.workflow_type == ""
        assert result.risk_level == "LOW"
        assert result.completeness is True
        assert result.missing_fields == []
        assert result.metadata == {}

    def test_creation_with_all_fields(self):
        """Should create RoutingResult with all fields specified."""
        result = RoutingResult(
            intent="change",
            sub_intent="firewall_rule",
            confidence=0.95,
            matched_layer="pattern",
            workflow_type="magentic",
            risk_level="HIGH",
            completeness=False,
            missing_fields=["impact_analysis"],
            metadata={"rule_id": "r-55"},
        )
        assert result.intent == "change"
        assert result.sub_intent == "firewall_rule"
        assert result.confidence == 0.95
        assert result.matched_layer == "pattern"
        assert result.workflow_type == "magentic"
        assert result.risk_level == "HIGH"
        assert result.completeness is False
        assert result.missing_fields == ["impact_analysis"]
        assert result.metadata == {"rule_id": "r-55"}

    def test_to_dict(self):
        """Should serialize to dictionary correctly."""
        result = RoutingResult(
            intent="request",
            sub_intent="vm_provision",
            confidence=0.88,
            matched_layer="semantic",
            workflow_type="sequential",
            risk_level="MEDIUM",
        )
        d = result.to_dict()
        assert d["intent"] == "request"
        assert d["sub_intent"] == "vm_provision"
        assert d["confidence"] == 0.88
        assert d["matched_layer"] == "semantic"
        assert d["workflow_type"] == "sequential"
        assert d["risk_level"] == "MEDIUM"
        assert d["completeness"] is True
        assert d["missing_fields"] == []
        assert d["metadata"] == {}

    def test_from_dict(self):
        """Should deserialize from dictionary correctly."""
        data = {
            "intent": "incident",
            "sub_intent": "database_down",
            "confidence": 0.97,
            "matched_layer": "pattern",
            "workflow_type": "magentic",
            "risk_level": "CRITICAL",
            "completeness": False,
            "missing_fields": ["affected_service"],
            "metadata": {"alert_id": "a-1"},
        }
        result = RoutingResult.from_dict(data)
        assert result.intent == "incident"
        assert result.sub_intent == "database_down"
        assert result.confidence == 0.97
        assert result.matched_layer == "pattern"
        assert result.workflow_type == "magentic"
        assert result.risk_level == "CRITICAL"
        assert result.completeness is False
        assert result.missing_fields == ["affected_service"]
        assert result.metadata == {"alert_id": "a-1"}

    def test_from_dict_missing_fields(self):
        """Should handle missing fields with defaults."""
        data = {}
        result = RoutingResult.from_dict(data)
        assert result.intent == ""
        assert result.sub_intent == ""
        assert result.confidence == 0.0
        assert result.matched_layer == ""
        assert result.workflow_type == ""
        assert result.risk_level == "LOW"
        assert result.completeness is True
        assert result.missing_fields == []
        assert result.metadata == {}

    def test_roundtrip_serialization(self):
        """to_dict -> from_dict should produce equivalent object."""
        original = RoutingResult(
            intent="query",
            sub_intent="server_status",
            confidence=0.75,
            matched_layer="llm",
            workflow_type="simple",
            risk_level="LOW",
            completeness=True,
            missing_fields=[],
            metadata={"model": "haiku"},
        )
        serialized = original.to_dict()
        restored = RoutingResult.from_dict(serialized)

        assert restored.intent == original.intent
        assert restored.sub_intent == original.sub_intent
        assert restored.confidence == original.confidence
        assert restored.matched_layer == original.matched_layer
        assert restored.workflow_type == original.workflow_type
        assert restored.risk_level == original.risk_level
        assert restored.completeness == original.completeness
        assert restored.missing_fields == original.missing_fields
        assert restored.metadata == original.metadata


# =============================================================================
# InputGatewayProtocol (ABC) Tests
# =============================================================================


class TestInputGatewayProtocol:
    """Tests for InputGatewayProtocol abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Should not be able to instantiate abstract class directly."""
        with pytest.raises(TypeError):
            InputGatewayProtocol()

    def test_subclass_must_implement_receive(self):
        """Subclass missing receive should raise TypeError."""

        class PartialGateway(InputGatewayProtocol):
            async def validate(self, raw_input):
                return True

        with pytest.raises(TypeError):
            PartialGateway()

    def test_subclass_must_implement_validate(self):
        """Subclass missing validate should raise TypeError."""

        class PartialGateway(InputGatewayProtocol):
            async def receive(self, raw_input):
                return RoutingRequest(query="")

        with pytest.raises(TypeError):
            PartialGateway()

    def test_complete_subclass_instantiates(self):
        """Complete subclass should instantiate successfully."""

        class ConcreteGateway(InputGatewayProtocol):
            async def receive(self, raw_input):
                return RoutingRequest(query=str(raw_input))

            async def validate(self, raw_input):
                return raw_input is not None

        gateway = ConcreteGateway()
        assert gateway is not None


# =============================================================================
# RouterProtocol (ABC) Tests
# =============================================================================


class TestRouterProtocol:
    """Tests for RouterProtocol abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Should not be able to instantiate abstract class directly."""
        with pytest.raises(TypeError):
            RouterProtocol()

    def test_subclass_must_implement_route(self):
        """Subclass missing route should raise TypeError."""

        class PartialRouter(RouterProtocol):
            def get_available_layers(self):
                return ["pattern"]

        with pytest.raises(TypeError):
            PartialRouter()

    def test_subclass_must_implement_get_available_layers(self):
        """Subclass missing get_available_layers should raise TypeError."""

        class PartialRouter(RouterProtocol):
            async def route(self, request):
                return RoutingResult(intent="unknown")

        with pytest.raises(TypeError):
            PartialRouter()

    def test_complete_subclass_instantiates(self):
        """Complete subclass should instantiate successfully."""

        class ConcreteRouter(RouterProtocol):
            async def route(self, request):
                return RoutingResult(intent="query")

            def get_available_layers(self):
                return ["pattern", "semantic", "llm"]

        router = ConcreteRouter()
        assert router is not None
        assert router.get_available_layers() == ["pattern", "semantic", "llm"]


# =============================================================================
# InputProcessorProtocol (ABC) Tests
# =============================================================================


class TestInputProcessorProtocol:
    """Tests for InputProcessorProtocol abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Should not be able to instantiate abstract class directly."""
        with pytest.raises(TypeError):
            InputProcessorProtocol()

    def test_subclass_must_implement_all_methods(self):
        """Subclass missing any method should raise TypeError."""

        class Partial1(InputProcessorProtocol):
            async def process(self, raw_input):
                return RoutingRequest(query="")

            def can_handle(self, raw_input):
                return True

        with pytest.raises(TypeError):
            Partial1()

        class Partial2(InputProcessorProtocol):
            async def process(self, raw_input):
                return RoutingRequest(query="")

            def get_source_type(self):
                return InputSource.USER_CHAT

        with pytest.raises(TypeError):
            Partial2()

    def test_complete_subclass_instantiates(self):
        """Complete subclass should instantiate successfully."""

        class ConcreteProcessor(InputProcessorProtocol):
            async def process(self, raw_input):
                return RoutingRequest(query=str(raw_input))

            def can_handle(self, raw_input):
                return isinstance(raw_input, str)

            def get_source_type(self):
                return InputSource.USER_CHAT

        processor = ConcreteProcessor()
        assert processor.can_handle("hello")
        assert not processor.can_handle(123)
        assert processor.get_source_type() == InputSource.USER_CHAT


# =============================================================================
# InputValidationResult Tests
# =============================================================================


class TestInputValidationResult:
    """Tests for InputValidationResult dataclass."""

    def test_valid_result(self):
        """Should create a valid result."""
        result = InputValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.sanitized_input is None

    def test_invalid_result_with_errors(self):
        """Should create invalid result with error messages."""
        result = InputValidationResult(
            is_valid=False,
            errors=["Missing required field: content", "Invalid source type"],
            warnings=["Deprecated header format"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "Missing required field: content" in result.errors
        assert len(result.warnings) == 1

    def test_with_sanitized_input(self):
        """Should store sanitized input."""
        result = InputValidationResult(
            is_valid=True,
            sanitized_input={"query": "cleaned text"},
        )
        assert result.sanitized_input == {"query": "cleaned text"}

    def test_to_dict(self):
        """Should serialize to dictionary correctly."""
        result = InputValidationResult(
            is_valid=False,
            errors=["bad input"],
            warnings=["check format"],
        )
        d = result.to_dict()
        assert d["is_valid"] is False
        assert d["errors"] == ["bad input"]
        assert d["warnings"] == ["check format"]
        # sanitized_input should not be in to_dict output
        assert "sanitized_input" not in d


# =============================================================================
# InputValidatorProtocol (ABC) Tests
# =============================================================================


class TestInputValidatorProtocol:
    """Tests for InputValidatorProtocol abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Should not be able to instantiate abstract class directly."""
        with pytest.raises(TypeError):
            InputValidatorProtocol()

    def test_complete_subclass_instantiates(self):
        """Complete subclass should instantiate successfully."""

        class ConcreteValidator(InputValidatorProtocol):
            def validate(self, raw_input, source):
                if raw_input is None:
                    return InputValidationResult(
                        is_valid=False, errors=["Input is None"]
                    )
                return InputValidationResult(is_valid=True)

        validator = ConcreteValidator()
        valid = validator.validate("test", InputSource.USER_CHAT)
        assert valid.is_valid is True

        invalid = validator.validate(None, InputSource.UNKNOWN)
        assert invalid.is_valid is False
        assert "Input is None" in invalid.errors


# =============================================================================
# InputProcessingMetrics Tests
# =============================================================================


class TestInputProcessingMetrics:
    """Tests for InputProcessingMetrics dataclass."""

    def test_creation_defaults(self):
        """Should create with zero-value defaults."""
        metrics = InputProcessingMetrics()
        assert metrics.total_received == 0
        assert metrics.total_validated == 0
        assert metrics.total_rejected == 0
        assert metrics.by_source == {}
        assert metrics.avg_processing_time_ms == 0.0

    def test_record_accepted(self):
        """Should record accepted processing event."""
        metrics = InputProcessingMetrics()
        metrics.record(InputSource.USER_CHAT, 15.0, accepted=True)

        assert metrics.total_received == 1
        assert metrics.total_validated == 1
        assert metrics.total_rejected == 0
        assert metrics.by_source == {"user_chat": 1}
        assert metrics.avg_processing_time_ms == 15.0

    def test_record_rejected(self):
        """Should record rejected processing event."""
        metrics = InputProcessingMetrics()
        metrics.record(InputSource.WEBHOOK_SERVICENOW, 5.0, accepted=False)

        assert metrics.total_received == 1
        assert metrics.total_validated == 0
        assert metrics.total_rejected == 1
        assert metrics.by_source == {"webhook_servicenow": 1}

    def test_record_multiple_sources(self):
        """Should track counts per source."""
        metrics = InputProcessingMetrics()
        metrics.record(InputSource.USER_CHAT, 10.0, accepted=True)
        metrics.record(InputSource.USER_CHAT, 12.0, accepted=True)
        metrics.record(InputSource.WEBHOOK_PROMETHEUS, 8.0, accepted=True)
        metrics.record(InputSource.HTTP_API, 20.0, accepted=False)

        assert metrics.total_received == 4
        assert metrics.total_validated == 3
        assert metrics.total_rejected == 1
        assert metrics.by_source["user_chat"] == 2
        assert metrics.by_source["webhook_prometheus"] == 1
        assert metrics.by_source["http_api"] == 1

    def test_running_average(self):
        """Should compute correct running average."""
        metrics = InputProcessingMetrics()
        metrics.record(InputSource.USER_CHAT, 10.0, accepted=True)
        assert metrics.avg_processing_time_ms == 10.0

        metrics.record(InputSource.USER_CHAT, 20.0, accepted=True)
        assert metrics.avg_processing_time_ms == 15.0

        metrics.record(InputSource.USER_CHAT, 30.0, accepted=True)
        assert metrics.avg_processing_time_ms == 20.0

    def test_to_dict(self):
        """Should serialize to dictionary correctly."""
        metrics = InputProcessingMetrics()
        metrics.record(InputSource.RITM, 12.5, accepted=True)
        metrics.record(InputSource.RITM, 17.5, accepted=False)

        d = metrics.to_dict()
        assert d["total_received"] == 2
        assert d["total_validated"] == 1
        assert d["total_rejected"] == 1
        assert d["by_source"] == {"ritm": 2}
        assert d["avg_processing_time_ms"] == 15.0


# =============================================================================
# RoutingLayerProtocol (ABC) Tests
# =============================================================================


class TestRoutingLayerProtocol:
    """Tests for RoutingLayerProtocol abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Should not be able to instantiate abstract class directly."""
        with pytest.raises(TypeError):
            RoutingLayerProtocol()

    def test_subclass_missing_classify_raises(self):
        """Subclass missing classify should raise TypeError."""

        class PartialLayer(RoutingLayerProtocol):
            def get_layer_name(self):
                return "test"

            def get_confidence_threshold(self):
                return 0.8

        with pytest.raises(TypeError):
            PartialLayer()

    def test_complete_subclass_instantiates(self):
        """Complete subclass should instantiate successfully."""

        class ConcreteLayer(RoutingLayerProtocol):
            async def classify(self, request):
                return RoutingResult(intent="incident", confidence=0.95)

            def get_layer_name(self):
                return "pattern"

            def get_confidence_threshold(self):
                return 0.90

        layer = ConcreteLayer()
        assert layer.get_layer_name() == "pattern"
        assert layer.get_confidence_threshold() == 0.90


# =============================================================================
# LayerExecutionMetric Tests
# =============================================================================


class TestLayerExecutionMetric:
    """Tests for LayerExecutionMetric dataclass."""

    def test_creation(self):
        """Should create LayerExecutionMetric with all fields."""
        metric = LayerExecutionMetric(
            layer_name="pattern",
            execution_time_ms=8.5,
            confidence=0.95,
            matched=True,
            metadata={"rule_id": "r-10"},
        )
        assert metric.layer_name == "pattern"
        assert metric.execution_time_ms == 8.5
        assert metric.confidence == 0.95
        assert metric.matched is True
        assert metric.metadata == {"rule_id": "r-10"}

    def test_creation_defaults(self):
        """Should create with default metadata."""
        metric = LayerExecutionMetric(
            layer_name="llm",
            execution_time_ms=1500.0,
            confidence=0.7,
            matched=False,
        )
        assert metric.metadata == {}


# =============================================================================
# RoutingPipelineResult Tests
# =============================================================================


class TestRoutingPipelineResult:
    """Tests for RoutingPipelineResult dataclass."""

    def test_creation_minimal(self):
        """Should create with minimal result."""
        result = RoutingPipelineResult(
            result=RoutingResult(intent="unknown"),
        )
        assert result.result.intent == "unknown"
        assert result.layers_attempted == []
        assert result.total_time_ms == 0.0

    def test_matched_layer_property(self):
        """Should return the name of the matched layer."""
        layers = [
            LayerExecutionMetric("pattern", 5.0, 0.6, matched=False),
            LayerExecutionMetric("semantic", 50.0, 0.92, matched=True),
        ]
        result = RoutingPipelineResult(
            result=RoutingResult(intent="request", matched_layer="semantic"),
            layers_attempted=layers,
            total_time_ms=55.0,
        )
        assert result.matched_layer == "semantic"

    def test_matched_layer_none_when_no_match(self):
        """Should return None when no layer matched."""
        layers = [
            LayerExecutionMetric("pattern", 5.0, 0.3, matched=False),
            LayerExecutionMetric("semantic", 50.0, 0.4, matched=False),
        ]
        result = RoutingPipelineResult(
            result=RoutingResult(intent="unknown"),
            layers_attempted=layers,
        )
        assert result.matched_layer is None

    def test_layers_tried_count(self):
        """Should return correct count of attempted layers."""
        layers = [
            LayerExecutionMetric("pattern", 5.0, 0.6, matched=False),
            LayerExecutionMetric("semantic", 50.0, 0.85, matched=False),
            LayerExecutionMetric("llm", 1200.0, 0.9, matched=True),
        ]
        result = RoutingPipelineResult(
            result=RoutingResult(intent="incident"),
            layers_attempted=layers,
        )
        assert result.layers_tried_count == 3

    def test_layers_tried_count_empty(self):
        """Should return 0 when no layers attempted."""
        result = RoutingPipelineResult(
            result=RoutingResult(intent="unknown"),
        )
        assert result.layers_tried_count == 0

    def test_to_dict(self):
        """Should serialize to dictionary correctly."""
        layers = [
            LayerExecutionMetric("pattern", 7.123, 0.95123, matched=True),
        ]
        result = RoutingPipelineResult(
            result=RoutingResult(intent="incident", confidence=0.95),
            layers_attempted=layers,
            total_time_ms=7.123,
        )
        d = result.to_dict()
        assert d["result"]["intent"] == "incident"
        assert d["result"]["confidence"] == 0.95
        assert len(d["layers_attempted"]) == 1
        assert d["layers_attempted"][0]["layer_name"] == "pattern"
        assert d["layers_attempted"][0]["execution_time_ms"] == 7.12
        assert d["layers_attempted"][0]["confidence"] == 0.951
        assert d["layers_attempted"][0]["matched"] is True
        assert d["total_time_ms"] == 7.12
        assert d["matched_layer"] == "pattern"

    def test_to_dict_no_match(self):
        """Should serialize correctly when no layer matched."""
        result = RoutingPipelineResult(
            result=RoutingResult(intent="unknown"),
        )
        d = result.to_dict()
        assert d["matched_layer"] is None
        assert d["layers_attempted"] == []


# =============================================================================
# DecisionEngineProtocol (ABC) Tests
# =============================================================================


class TestDecisionEngineProtocol:
    """Tests for DecisionEngineProtocol abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Should not be able to instantiate abstract class directly."""
        with pytest.raises(TypeError):
            DecisionEngineProtocol()

    def test_subclass_must_implement_route(self):
        """Subclass missing route should raise TypeError."""

        class PartialEngine(DecisionEngineProtocol):
            def get_pipeline_config(self):
                return {}

        with pytest.raises(TypeError):
            PartialEngine()

    def test_complete_subclass_instantiates(self):
        """Complete subclass should instantiate successfully."""

        class ConcreteEngine(DecisionEngineProtocol):
            async def route(self, request):
                return RoutingPipelineResult(
                    result=RoutingResult(intent="query"),
                )

            def get_pipeline_config(self):
                return {
                    "layers": ["pattern", "semantic", "llm"],
                    "timeout_ms": 3000,
                }

        engine = ConcreteEngine()
        config = engine.get_pipeline_config()
        assert "layers" in config
        assert len(config["layers"]) == 3


# =============================================================================
# Adapter Function: incoming_request_to_routing_request
# =============================================================================


class TestIncomingRequestToRoutingRequest:
    """Tests for incoming_request_to_routing_request adapter function."""

    def test_convert_user_input(self):
        """Should convert user input IncomingRequest."""

        @dataclass
        class MockIncomingRequest:
            content: str = "reset my password"
            data: Dict[str, Any] = field(default_factory=dict)
            source_type: Optional[str] = "user"
            request_id: Optional[str] = "req-1"
            timestamp: datetime = field(default_factory=datetime.utcnow)
            metadata: Dict[str, Any] = field(default_factory=dict)

        incoming = MockIncomingRequest()
        result = incoming_request_to_routing_request(incoming)

        assert result.query == "reset my password"
        assert result.source == InputSource.USER_CHAT
        assert result.request_id == "req-1"

    def test_convert_servicenow_source(self):
        """Should map servicenow source type correctly."""

        @dataclass
        class MockIncomingRequest:
            content: str = "Server down"
            data: Dict[str, Any] = field(default_factory=dict)
            source_type: Optional[str] = "servicenow"
            request_id: Optional[str] = "INC001"
            timestamp: datetime = field(default_factory=datetime.utcnow)
            metadata: Dict[str, Any] = field(default_factory=dict)

        incoming = MockIncomingRequest()
        result = incoming_request_to_routing_request(incoming)

        assert result.source == InputSource.WEBHOOK_SERVICENOW
        assert result.query == "Server down"
        assert result.request_id == "INC001"

    def test_convert_prometheus_source(self):
        """Should map prometheus source type correctly."""

        @dataclass
        class MockIncomingRequest:
            content: str = "High CPU usage"
            data: Dict[str, Any] = field(default_factory=lambda: {"alerts": []})
            source_type: Optional[str] = "prometheus"
            request_id: Optional[str] = None
            timestamp: datetime = field(default_factory=datetime.utcnow)
            metadata: Dict[str, Any] = field(default_factory=dict)

        incoming = MockIncomingRequest()
        result = incoming_request_to_routing_request(incoming)

        assert result.source == InputSource.WEBHOOK_PROMETHEUS
        assert result.context == {"alerts": []}

    def test_convert_api_source(self):
        """Should map api source type correctly."""

        @dataclass
        class MockIncomingRequest:
            content: str = "check status"
            data: Dict[str, Any] = field(default_factory=dict)
            source_type: Optional[str] = "api"
            request_id: Optional[str] = None
            timestamp: datetime = field(default_factory=datetime.utcnow)
            metadata: Dict[str, Any] = field(default_factory=dict)

        incoming = MockIncomingRequest()
        result = incoming_request_to_routing_request(incoming)
        assert result.source == InputSource.HTTP_API

    def test_convert_unknown_source(self):
        """Should fall back to provided source for unknown source_type."""

        @dataclass
        class MockIncomingRequest:
            content: str = ""
            data: Dict[str, Any] = field(default_factory=dict)
            source_type: Optional[str] = "totally_unknown"
            request_id: Optional[str] = None
            timestamp: datetime = field(default_factory=datetime.utcnow)
            metadata: Dict[str, Any] = field(default_factory=dict)

        incoming = MockIncomingRequest()
        result = incoming_request_to_routing_request(
            incoming, source=InputSource.SSE_STREAM
        )
        assert result.source == InputSource.SSE_STREAM

    def test_convert_none_source_type(self):
        """Should fall back to UNKNOWN when source_type is None."""

        @dataclass
        class MockIncomingRequest:
            content: str = "test"
            data: Dict[str, Any] = field(default_factory=dict)
            source_type: Optional[str] = None
            request_id: Optional[str] = None
            timestamp: datetime = field(default_factory=datetime.utcnow)
            metadata: Dict[str, Any] = field(default_factory=dict)

        incoming = MockIncomingRequest()
        result = incoming_request_to_routing_request(incoming)
        assert result.source == InputSource.UNKNOWN

    def test_convert_missing_fields(self):
        """Should handle object with missing attributes gracefully."""

        class MinimalRequest:
            pass

        incoming = MinimalRequest()
        result = incoming_request_to_routing_request(incoming)

        assert result.query == ""
        assert result.context == {}
        assert result.source == InputSource.UNKNOWN
        assert result.request_id is None
        assert isinstance(result.timestamp, datetime)
        assert result.metadata == {}

    def test_convert_preserves_metadata(self):
        """Should preserve metadata from IncomingRequest."""

        @dataclass
        class MockIncomingRequest:
            content: str = "test"
            data: Dict[str, Any] = field(default_factory=dict)
            source_type: Optional[str] = "user"
            request_id: Optional[str] = None
            timestamp: datetime = field(default_factory=datetime.utcnow)
            metadata: Dict[str, Any] = field(
                default_factory=lambda: {"channel": "web", "user_agent": "browser"}
            )

        incoming = MockIncomingRequest()
        result = incoming_request_to_routing_request(incoming)
        assert result.metadata == {"channel": "web", "user_agent": "browser"}

    def test_convert_none_data_becomes_empty_dict(self):
        """Should convert None data to empty dict."""

        class NoneDataRequest:
            content = "test"
            data = None
            source_type = "user"
            request_id = None
            timestamp = datetime.utcnow()
            metadata = {}

        incoming = NoneDataRequest()
        result = incoming_request_to_routing_request(incoming)
        assert result.context == {}

    def test_convert_none_metadata_becomes_empty_dict(self):
        """Should convert None metadata to empty dict."""

        class NoneMetaRequest:
            content = "test"
            data = {}
            source_type = "user"
            request_id = None
            timestamp = datetime.utcnow()
            metadata = None

        incoming = NoneMetaRequest()
        result = incoming_request_to_routing_request(incoming)
        assert result.metadata == {}


# =============================================================================
# Adapter Function: routing_decision_to_routing_result
# =============================================================================


class TestRoutingDecisionToRoutingResult:
    """Tests for routing_decision_to_routing_result adapter function."""

    def test_convert_basic_decision(self):
        """Should convert a basic RoutingDecision."""
        from enum import Enum

        class MockCategory(Enum):
            INCIDENT = "incident"

        class MockWorkflow(Enum):
            MAGENTIC = "magentic"

        class MockRisk(Enum):
            HIGH = "high"

        @dataclass
        class MockDecision:
            intent_category: MockCategory = MockCategory.INCIDENT
            sub_intent: str = "database_down"
            confidence: float = 0.95
            workflow_type: MockWorkflow = MockWorkflow.MAGENTIC
            risk_level: MockRisk = MockRisk.HIGH
            completeness: Any = None
            routing_layer: str = "pattern"
            metadata: Dict[str, Any] = field(default_factory=dict)

        decision = MockDecision()
        result = routing_decision_to_routing_result(decision)

        assert result.intent == "incident"
        assert result.sub_intent == "database_down"
        assert result.confidence == 0.95
        assert result.workflow_type == "magentic"
        assert result.risk_level == "high"
        assert result.matched_layer == "pattern"
        assert result.completeness is True
        assert result.missing_fields == []

    def test_convert_with_completeness_info(self):
        """Should extract completeness info from RoutingDecision."""

        @dataclass
        class MockCompleteness:
            is_complete: bool = False
            missing_fields: List[str] = field(
                default_factory=lambda: ["impact_analysis", "urgency"]
            )

        @dataclass
        class MockDecision:
            intent_category: str = "change"
            sub_intent: str = "firewall_update"
            confidence: float = 0.88
            workflow_type: str = "sequential"
            risk_level: str = "MEDIUM"
            completeness: MockCompleteness = field(
                default_factory=MockCompleteness
            )
            routing_layer: str = "semantic"
            metadata: Dict[str, Any] = field(default_factory=dict)

        decision = MockDecision()
        result = routing_decision_to_routing_result(decision)

        assert result.intent == "change"
        assert result.completeness is False
        assert result.missing_fields == ["impact_analysis", "urgency"]

    def test_convert_string_values(self):
        """Should handle plain string values (no .value attribute)."""

        @dataclass
        class MockDecision:
            intent_category: str = "query"
            sub_intent: str = "server_status"
            confidence: float = 0.7
            workflow_type: str = "simple"
            risk_level: str = "LOW"
            completeness: Any = None
            routing_layer: str = "llm"
            metadata: Dict[str, Any] = field(default_factory=dict)

        decision = MockDecision()
        result = routing_decision_to_routing_result(decision)

        assert result.intent == "query"
        assert result.workflow_type == "simple"
        assert result.risk_level == "LOW"

    def test_convert_missing_attributes(self):
        """Should handle object with missing attributes gracefully."""

        class MinimalDecision:
            pass

        decision = MinimalDecision()
        result = routing_decision_to_routing_result(decision)

        assert result.intent == ""
        assert result.sub_intent == ""
        assert result.confidence == 0.0
        assert result.matched_layer == ""
        assert result.workflow_type == ""
        assert result.risk_level == "LOW"
        assert result.completeness is True
        assert result.missing_fields == []
        assert result.metadata == {}

    def test_convert_with_confidence_score_fallback(self):
        """Should fall back to confidence_score if confidence is missing."""

        class DecisionWithScore:
            intent_category = "incident"
            confidence_score = 0.92
            routing_layer = "pattern"
            metadata = {}

        decision = DecisionWithScore()
        result = routing_decision_to_routing_result(decision)

        # confidence attr does not exist, should fall back to confidence_score
        assert result.confidence == 0.92

    def test_convert_with_none_sub_intent(self):
        """Should handle None sub_intent."""

        @dataclass
        class MockDecision:
            intent_category: str = "request"
            sub_intent: Optional[str] = None
            confidence: float = 0.8
            workflow_type: str = "simple"
            risk_level: str = "LOW"
            completeness: Any = None
            routing_layer: str = "pattern"
            metadata: Dict[str, Any] = field(default_factory=dict)

        decision = MockDecision()
        result = routing_decision_to_routing_result(decision)
        assert result.sub_intent == ""

    def test_convert_preserves_metadata(self):
        """Should preserve metadata from RoutingDecision."""

        @dataclass
        class MockDecision:
            intent_category: str = "incident"
            sub_intent: str = "network"
            confidence: float = 0.9
            workflow_type: str = "magentic"
            risk_level: str = "HIGH"
            completeness: Any = None
            routing_layer: str = "pattern"
            metadata: Dict[str, Any] = field(
                default_factory=lambda: {"rule_id": "r-10", "matched_pattern": "network.*down"}
            )

        decision = MockDecision()
        result = routing_decision_to_routing_result(decision)
        assert result.metadata == {"rule_id": "r-10", "matched_pattern": "network.*down"}

    def test_convert_none_metadata_becomes_empty_dict(self):
        """Should convert None metadata to empty dict."""

        class NoneMetaDecision:
            intent_category = "query"
            metadata = None

        decision = NoneMetaDecision()
        result = routing_decision_to_routing_result(decision)
        assert result.metadata == {}

    def test_convert_with_real_routing_decision(self):
        """Should convert a real RoutingDecision from the existing models."""
        from src.integrations.orchestration.intent_router.models import (
            CompletenessInfo,
            ITIntentCategory,
            RiskLevel,
            RoutingDecision as RealRoutingDecision,
            WorkflowType,
        )

        completeness = CompletenessInfo(
            is_complete=False,
            missing_fields=["affected_service"],
            completeness_score=0.6,
        )
        decision = RealRoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="database_down",
            confidence=0.95,
            workflow_type=WorkflowType.MAGENTIC,
            risk_level=RiskLevel.CRITICAL,
            completeness=completeness,
            routing_layer="pattern",
            metadata={"rule_id": "r-db-001"},
        )
        result = routing_decision_to_routing_result(decision)

        assert result.intent == "incident"
        assert result.sub_intent == "database_down"
        assert result.confidence == 0.95
        assert result.workflow_type == "magentic"
        assert result.risk_level == "critical"
        assert result.completeness is False
        assert result.missing_fields == ["affected_service"]
        assert result.matched_layer == "pattern"
        assert result.metadata == {"rule_id": "r-db-001"}

    def test_convert_with_none_completeness_fields(self):
        """Should handle completeness object with None fields."""

        class MockCompleteness:
            is_complete = None
            missing_fields = None

        @dataclass
        class MockDecision:
            intent_category: str = "query"
            sub_intent: str = ""
            confidence: float = 0.5
            workflow_type: str = "simple"
            risk_level: str = "LOW"
            completeness: Any = field(default_factory=MockCompleteness)
            routing_layer: str = "llm"
            metadata: Dict[str, Any] = field(default_factory=dict)

        decision = MockDecision()
        result = routing_decision_to_routing_result(decision)
        assert result.completeness is True
        assert result.missing_fields == []
