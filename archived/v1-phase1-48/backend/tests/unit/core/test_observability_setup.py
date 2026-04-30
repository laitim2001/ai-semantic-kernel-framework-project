"""Unit tests for OpenTelemetry observability setup.

Sprint 122, Story 122-2: Tests OTel SDK initialization, Azure Monitor
exporter configuration, and auto-instrumentation setup.
"""

import pytest
from unittest.mock import MagicMock, patch

from opentelemetry import trace, metrics


class TestSetupObservability:
    """Tests for setup_observability() function."""

    def test_disabled_returns_none(self):
        """When otel_enabled=False, should return None without initializing."""
        from src.core.observability.setup import setup_observability

        result = setup_observability(otel_enabled=False)
        assert result is None

    def test_enabled_returns_shutdown_callable(self):
        """When enabled, should return a callable for shutdown."""
        from src.core.observability.setup import setup_observability

        shutdown = setup_observability(
            service_name="test-service",
            connection_string="",
            otel_enabled=True,
        )
        assert shutdown is not None
        assert callable(shutdown)

        # Cleanup
        shutdown()

    def test_setup_with_empty_connection_string(self):
        """Should fall back to OTLP exporter when no Azure connection string."""
        from src.core.observability.setup import setup_observability

        shutdown = setup_observability(
            service_name="test-service",
            connection_string="",
            otel_enabled=True,
        )
        assert shutdown is not None
        shutdown()

    @patch("src.core.observability.setup._setup_azure_monitor_trace")
    def test_setup_with_connection_string_calls_azure(self, mock_azure):
        """Should configure Azure Monitor when connection string provided."""
        from src.core.observability.setup import setup_observability

        shutdown = setup_observability(
            service_name="test-service",
            connection_string="InstrumentationKey=test-key;IngestionEndpoint=https://test.in.applicationinsights.azure.com/",
            otel_enabled=True,
        )
        assert shutdown is not None
        mock_azure.assert_called_once()
        shutdown()

    def test_shutdown_callable_does_not_raise(self):
        """Shutdown callable should not raise exceptions."""
        from src.core.observability.setup import setup_observability

        shutdown = setup_observability(
            service_name="test-service",
            otel_enabled=True,
        )
        assert shutdown is not None
        # Should not raise
        shutdown()

    def test_sampling_rate_parameter(self):
        """Should accept sampling_rate parameter."""
        from src.core.observability.setup import setup_observability

        shutdown = setup_observability(
            service_name="test-service",
            otel_enabled=True,
            sampling_rate=0.5,
        )
        assert shutdown is not None
        shutdown()


class TestGetTracer:
    """Tests for get_tracer() function."""

    def test_returns_tracer_instance(self):
        """Should return a Tracer instance."""
        from src.core.observability.setup import get_tracer

        tracer = get_tracer()
        assert tracer is not None

    def test_tracer_can_create_span(self):
        """Tracer should be able to create spans."""
        from src.core.observability.setup import get_tracer

        tracer = get_tracer()
        with tracer.start_as_current_span("test-span") as span:
            assert span is not None


class TestGetMeter:
    """Tests for get_meter() function."""

    def test_returns_meter_instance(self):
        """Should return a Meter instance."""
        from src.core.observability.setup import get_meter

        meter = get_meter()
        assert meter is not None


class TestAutoInstrumentation:
    """Tests for _setup_auto_instrumentation()."""

    def test_auto_instrumentation_does_not_raise(self):
        """Auto-instrumentation should not raise even if packages missing."""
        from src.core.observability.setup import _setup_auto_instrumentation

        # Should not raise regardless of which packages are installed
        _setup_auto_instrumentation()

    @patch("src.core.observability.setup.logger")
    def test_auto_instrumentation_logs_status(self, mock_logger):
        """Should log status for each instrumentation attempt."""
        from src.core.observability.setup import _setup_auto_instrumentation

        _setup_auto_instrumentation()
        # Should have logged at least some debug/info messages
        assert mock_logger.info.called or mock_logger.debug.called
