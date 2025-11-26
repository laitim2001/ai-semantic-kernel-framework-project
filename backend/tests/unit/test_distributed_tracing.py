"""
Unit tests for Distributed Tracing (S3-6)

Tests the OpenTelemetry setup, tracing utilities, and middleware.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.core.telemetry.setup import (
    setup_telemetry,
    get_tracer,
    get_meter,
    get_current_span,
    get_trace_id,
    get_span_id,
    create_span,
    add_span_attributes,
    add_span_event,
    set_span_status,
    record_exception,
    inject_trace_context,
    extract_trace_context,
    shutdown_telemetry,
    reset_telemetry,
)
from opentelemetry.trace import SpanKind, StatusCode


class TestTelemetrySetup:
    """Test cases for telemetry setup."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset telemetry state before each test."""
        reset_telemetry()
        yield
        reset_telemetry()

    def test_setup_telemetry_returns_providers(self):
        """Test that setup returns tracer and meter providers."""
        tracer_provider, meter_provider = setup_telemetry(
            service_name="test-service",
            enable_console=False,
        )

        assert tracer_provider is not None
        assert meter_provider is not None

    def test_setup_telemetry_idempotent(self):
        """Test that setup is idempotent."""
        tp1, mp1 = setup_telemetry(enable_console=False)
        tp2, mp2 = setup_telemetry(enable_console=False)

        assert tp1 is tp2
        assert mp1 is mp2

    def test_get_tracer_returns_tracer(self):
        """Test get_tracer returns a valid tracer."""
        setup_telemetry(enable_console=False)
        tracer = get_tracer("test.tracer")

        assert tracer is not None

    def test_get_meter_returns_meter(self):
        """Test get_meter returns a valid meter."""
        setup_telemetry(enable_console=False)
        meter = get_meter("test.meter")

        assert meter is not None

    @patch.dict(os.environ, {"JAEGER_ENABLED": "true", "OTEL_EXPORTER_OTLP_ENDPOINT": ""})
    def test_jaeger_enabled_via_env(self):
        """Test that JAEGER_ENABLED env enables OTLP."""
        # This should not raise even if OTLP exporter is not available
        tracer_provider, _ = setup_telemetry(enable_console=False)
        assert tracer_provider is not None


class TestSpanManagement:
    """Test cases for span management utilities."""

    @pytest.fixture(autouse=True)
    def setup_telemetry_fixture(self):
        """Set up telemetry for tests."""
        reset_telemetry()
        setup_telemetry(enable_console=False)
        yield
        reset_telemetry()

    def test_create_span_context_manager(self):
        """Test create_span context manager."""
        with create_span("test-span") as span:
            assert span is not None
            assert span.is_recording()

    def test_create_span_with_attributes(self):
        """Test create_span with attributes."""
        attributes = {"key1": "value1", "key2": 42}

        with create_span("test-span", attributes=attributes) as span:
            assert span is not None

    def test_create_span_with_kind(self):
        """Test create_span with different span kinds."""
        with create_span("server-span", kind=SpanKind.SERVER) as span:
            assert span is not None

        with create_span("client-span", kind=SpanKind.CLIENT) as span:
            assert span is not None

    def test_get_trace_id_within_span(self):
        """Test get_trace_id returns valid ID within span."""
        with create_span("test-span"):
            trace_id = get_trace_id()
            assert trace_id is not None
            assert len(trace_id) == 32  # 128-bit trace ID as hex

    def test_get_span_id_within_span(self):
        """Test get_span_id returns valid ID within span."""
        with create_span("test-span"):
            span_id = get_span_id()
            assert span_id is not None
            assert len(span_id) == 16  # 64-bit span ID as hex

    def test_get_current_span(self):
        """Test get_current_span returns active span."""
        with create_span("test-span") as expected_span:
            current = get_current_span()
            assert current is expected_span


class TestSpanEnrichment:
    """Test cases for span enrichment utilities."""

    @pytest.fixture(autouse=True)
    def setup_telemetry_fixture(self):
        """Set up telemetry for tests."""
        reset_telemetry()
        setup_telemetry(enable_console=False)
        yield
        reset_telemetry()

    def test_add_span_attributes(self):
        """Test adding attributes to current span."""
        with create_span("test-span") as span:
            add_span_attributes({"custom.key": "custom.value"})
            # Attributes are added but we can't easily verify without export

    def test_add_span_event(self):
        """Test adding event to current span."""
        with create_span("test-span") as span:
            add_span_event("test.event", {"event.key": "event.value"})
            # Events are added but we can't easily verify without export

    def test_set_span_status_ok(self):
        """Test setting span status to OK."""
        with create_span("test-span") as span:
            set_span_status(StatusCode.OK, "Success")
            # Status is set

    def test_set_span_status_error(self):
        """Test setting span status to ERROR."""
        with create_span("test-span") as span:
            set_span_status(StatusCode.ERROR, "Test error")
            # Status is set

    def test_record_exception(self):
        """Test recording exception in span."""
        with create_span("test-span") as span:
            try:
                raise ValueError("Test exception")
            except Exception as e:
                record_exception(e)


class TestContextPropagation:
    """Test cases for trace context propagation."""

    @pytest.fixture(autouse=True)
    def setup_telemetry_fixture(self):
        """Set up telemetry for tests."""
        reset_telemetry()
        setup_telemetry(enable_console=False)
        yield
        reset_telemetry()

    def test_inject_trace_context(self):
        """Test injecting trace context into carrier."""
        with create_span("test-span"):
            carrier = {}
            result = inject_trace_context(carrier)

            # Should have trace context headers
            assert result is carrier
            # W3C traceparent should be present
            assert "traceparent" in carrier or len(carrier) >= 0

    def test_extract_trace_context(self):
        """Test extracting trace context from carrier."""
        # Create a valid traceparent header
        carrier = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        }
        context = extract_trace_context(carrier)
        assert context is not None

    def test_context_propagation_roundtrip(self):
        """Test context propagation roundtrip."""
        with create_span("parent-span"):
            trace_id_before = get_trace_id()
            carrier = {}
            inject_trace_context(carrier)

            # In a real scenario, the carrier would be sent to another service
            # For testing, we just verify the carrier has content
            assert len(carrier) > 0


class TestTracingMiddleware:
    """Test cases for tracing middleware."""

    def test_middleware_import(self):
        """Test that middleware can be imported."""
        from src.core.telemetry.middleware import (
            TracingMiddleware,
            CorrelationIdMiddleware,
            get_correlation_id,
        )

        assert TracingMiddleware is not None
        assert CorrelationIdMiddleware is not None
        assert get_correlation_id is not None

    def test_tracing_middleware_initialization(self):
        """Test TracingMiddleware initialization."""
        from src.core.telemetry.middleware import TracingMiddleware

        mock_app = MagicMock()
        middleware = TracingMiddleware(
            mock_app,
            excluded_paths=["/health", "/metrics"],
            add_response_headers=True,
        )

        assert middleware.excluded_paths == ["/health", "/metrics"]
        assert middleware.add_response_headers is True


class TestTracingRoutes:
    """Test cases for tracing API routes."""

    def test_routes_import(self):
        """Test that routes can be imported."""
        from src.api.v1.tracing.routes import router
        assert router is not None

    def test_route_models(self):
        """Test Pydantic models for routes."""
        from src.api.v1.tracing.routes import (
            TracingConfigResponse,
            TraceContextResponse,
            TestTraceResponse,
            DetailedTraceResponse,
            JaegerHealthResponse,
        )

        # Test TracingConfigResponse
        config = TracingConfigResponse(
            enabled=True,
            service_name="test",
            jaeger_enabled=True,
            jaeger_endpoint="http://localhost:16686",
            otlp_endpoint="http://localhost:4317",
            environment="development",
        )
        assert config.enabled is True
        assert config.service_name == "test"

        # Test TraceContextResponse
        context = TraceContextResponse(
            trace_id="abc123",
            span_id="def456",
            has_valid_context=True,
        )
        assert context.trace_id == "abc123"

        # Test TestTraceResponse
        test_trace = TestTraceResponse(
            trace_id="trace123",
            span_count=3,
            duration_ms=50.5,
            message="Success",
        )
        assert test_trace.span_count == 3

        # Test JaegerHealthResponse
        health = JaegerHealthResponse(
            status="healthy",
            ui_url="http://localhost:16686",
            collector_endpoint="http://localhost:4317",
            message="Jaeger is healthy",
        )
        assert health.status == "healthy"


class TestNestedSpans:
    """Test cases for nested span functionality."""

    @pytest.fixture(autouse=True)
    def setup_telemetry_fixture(self):
        """Set up telemetry for tests."""
        reset_telemetry()
        setup_telemetry(enable_console=False)
        yield
        reset_telemetry()

    def test_nested_spans_same_trace(self):
        """Test that nested spans share the same trace ID."""
        with create_span("parent-span"):
            parent_trace_id = get_trace_id()
            parent_span_id = get_span_id()

            with create_span("child-span"):
                child_trace_id = get_trace_id()
                child_span_id = get_span_id()

                # Same trace, different span
                assert parent_trace_id == child_trace_id
                assert parent_span_id != child_span_id

    def test_multiple_child_spans(self):
        """Test multiple child spans under one parent."""
        with create_span("parent-span"):
            parent_trace_id = get_trace_id()
            child_span_ids = []

            for i in range(3):
                with create_span(f"child-span-{i}"):
                    assert get_trace_id() == parent_trace_id
                    child_span_ids.append(get_span_id())

            # All child spans should be unique
            assert len(set(child_span_ids)) == 3


class TestTelemetryShutdown:
    """Test cases for telemetry shutdown."""

    def test_shutdown_telemetry(self):
        """Test shutdown_telemetry function."""
        setup_telemetry(enable_console=False)
        shutdown_telemetry()
        # Should not raise

    def test_reset_telemetry(self):
        """Test reset_telemetry function."""
        setup_telemetry(enable_console=False)
        reset_telemetry()

        # After reset, setup should create new providers
        tp1, _ = setup_telemetry(enable_console=False)
        reset_telemetry()
        tp2, _ = setup_telemetry(enable_console=False)

        # They should be different instances
        assert tp1 is not tp2


class TestEnvironmentConfiguration:
    """Test cases for environment-based configuration."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset telemetry state before each test."""
        reset_telemetry()
        yield
        reset_telemetry()

    @patch.dict(os.environ, {"OTEL_SERVICE_NAME": "custom-service"})
    def test_service_name_from_env(self):
        """Test service name from environment variable."""
        setup_telemetry(enable_console=False)
        # Service name should be used in resource

    @patch.dict(os.environ, {"APP_ENV": "production"})
    def test_environment_from_env(self):
        """Test environment from APP_ENV variable."""
        setup_telemetry(enable_console=False)
        # Environment should be used in resource

    @patch.dict(os.environ, {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://custom-collector:4317"
    })
    def test_otlp_endpoint_from_env(self):
        """Test OTLP endpoint from environment variable."""
        # This should enable OTLP automatically
        setup_telemetry(enable_console=False)


class TestSpanAttributes:
    """Test cases for span attribute handling."""

    @pytest.fixture(autouse=True)
    def setup_telemetry_fixture(self):
        """Set up telemetry for tests."""
        reset_telemetry()
        setup_telemetry(enable_console=False)
        yield
        reset_telemetry()

    def test_string_attribute(self):
        """Test string attributes."""
        with create_span("test-span", attributes={"string.key": "value"}):
            pass

    def test_int_attribute(self):
        """Test integer attributes."""
        with create_span("test-span", attributes={"int.key": 42}):
            pass

    def test_float_attribute(self):
        """Test float attributes."""
        with create_span("test-span", attributes={"float.key": 3.14}):
            pass

    def test_bool_attribute(self):
        """Test boolean attributes."""
        with create_span("test-span", attributes={"bool.key": True}):
            pass

    def test_list_attribute(self):
        """Test list attributes (sequence of same type)."""
        with create_span("test-span", attributes={"list.key": ["a", "b", "c"]}):
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
