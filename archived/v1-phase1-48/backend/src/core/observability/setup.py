"""OpenTelemetry SDK initialization with Azure Monitor exporters.

Sprint 122, Story 122-2: Configures TracerProvider, MeterProvider,
and auto-instrumentation for FastAPI, httpx, Redis, and asyncpg.

Usage:
    from src.core.observability.setup import setup_observability

    # In FastAPI lifespan:
    shutdown_fn = setup_observability(
        service_name="ipa-platform-backend",
        connection_string=settings.applicationinsights_connection_string,
        otel_enabled=settings.otel_enabled,
    )
    # At shutdown:
    if shutdown_fn:
        shutdown_fn()
"""

import logging
from typing import Callable, Optional

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

logger = logging.getLogger(__name__)

# Module-level tracer (initialized after setup)
_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None

_SERVICE_NAME = "ipa-platform"


def get_tracer() -> trace.Tracer:
    """Get the IPA Platform tracer instance.

    Returns a no-op tracer if observability has not been initialized.
    """
    if _tracer is not None:
        return _tracer
    return trace.get_tracer(_SERVICE_NAME)


def get_meter() -> metrics.Meter:
    """Get the IPA Platform meter instance.

    Returns a no-op meter if observability has not been initialized.
    """
    if _meter is not None:
        return _meter
    return metrics.get_meter(_SERVICE_NAME)


def setup_observability(
    service_name: str = "ipa-platform-backend",
    connection_string: str = "",
    otel_enabled: bool = True,
    sampling_rate: float = 1.0,
) -> Optional[Callable[[], None]]:
    """Initialize OpenTelemetry SDK with optional Azure Monitor exporters.

    Sets up TracerProvider, MeterProvider, and auto-instrumentation.
    When connection_string is provided, exports to Azure Monitor.
    Otherwise, uses OTLP exporter or console exporter for local dev.

    Args:
        service_name: OTel service name attribute.
        connection_string: Azure Application Insights connection string.
            If empty, Azure Monitor export is disabled.
        otel_enabled: Master switch for OTel. If False, no-op.
        sampling_rate: Trace sampling rate (0.0 to 1.0). Default 1.0 = 100%.

    Returns:
        A shutdown callable to flush and close providers, or None if disabled.
    """
    global _tracer, _meter

    if not otel_enabled:
        logger.info("OpenTelemetry is disabled (OTEL_ENABLED=false)")
        return None

    logger.info(
        "Initializing OpenTelemetry: service_name=%s, azure_monitor=%s, sampling=%.0f%%",
        service_name,
        bool(connection_string),
        sampling_rate * 100,
    )

    # --- Resource ---
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: "0.2.0",
            "deployment.environment": "production",
        }
    )

    # --- Trace Provider ---
    tracer_provider = TracerProvider(resource=resource)

    if connection_string:
        _setup_azure_monitor_trace(tracer_provider, connection_string)
    else:
        _setup_otlp_trace(tracer_provider)

    trace.set_tracer_provider(tracer_provider)
    _tracer = trace.get_tracer(service_name)

    # --- Meter Provider ---
    meter_provider = _create_meter_provider(resource, connection_string)
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter(service_name)

    # --- Auto-Instrumentation ---
    _setup_auto_instrumentation()

    logger.info("OpenTelemetry initialization complete")

    def _shutdown() -> None:
        """Flush and shut down all OTel providers."""
        logger.info("Shutting down OpenTelemetry providers...")
        tracer_provider.shutdown()
        meter_provider.shutdown()
        logger.info("OpenTelemetry shutdown complete")

    return _shutdown


def _setup_azure_monitor_trace(
    provider: TracerProvider,
    connection_string: str,
) -> None:
    """Configure Azure Monitor trace exporter.

    Args:
        provider: The TracerProvider to add the exporter to.
        connection_string: Application Insights connection string.
    """
    try:
        from azure.monitor.opentelemetry.exporter import (
            AzureMonitorTraceExporter,
        )

        exporter = AzureMonitorTraceExporter(connection_string=connection_string)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("Azure Monitor trace exporter configured")
    except ImportError:
        logger.warning(
            "azure-monitor-opentelemetry-exporter not installed, "
            "falling back to OTLP exporter"
        )
        _setup_otlp_trace(provider)


def _setup_otlp_trace(provider: TracerProvider) -> None:
    """Configure OTLP trace exporter for local development.

    Args:
        provider: The TracerProvider to add the exporter to.
    """
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter = OTLPSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("OTLP trace exporter configured")
    except ImportError:
        logger.info("No trace exporter available, using no-op")


def _create_meter_provider(
    resource: Resource,
    connection_string: str,
) -> MeterProvider:
    """Create MeterProvider with appropriate metric exporter.

    Args:
        resource: OTel resource with service attributes.
        connection_string: Application Insights connection string.

    Returns:
        Configured MeterProvider.
    """
    readers = []

    if connection_string:
        try:
            from azure.monitor.opentelemetry.exporter import (
                AzureMonitorMetricExporter,
            )

            metric_exporter = AzureMonitorMetricExporter(
                connection_string=connection_string
            )
            readers.append(
                PeriodicExportingMetricReader(
                    metric_exporter,
                    export_interval_millis=60000,
                )
            )
            logger.info("Azure Monitor metric exporter configured")
        except ImportError:
            logger.warning(
                "azure-monitor-opentelemetry-exporter not installed, "
                "metrics will not be exported to Azure Monitor"
            )

    return MeterProvider(resource=resource, metric_readers=readers)


def _setup_auto_instrumentation() -> None:
    """Enable auto-instrumentation for common libraries.

    Instruments FastAPI, httpx, Redis, and asyncpg if their
    respective OTel instrumentation packages are available.
    """
    # FastAPI
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor().instrument()
        logger.info("FastAPI auto-instrumentation enabled")
    except ImportError:
        logger.debug("FastAPI instrumentation package not available")

    # httpx
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        logger.info("httpx auto-instrumentation enabled")
    except ImportError:
        logger.debug("httpx instrumentation package not available")

    # Redis
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
        logger.info("Redis auto-instrumentation enabled")
    except ImportError:
        logger.debug("Redis instrumentation package not available")

    # asyncpg
    try:
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

        AsyncPGInstrumentor().instrument()
        logger.info("asyncpg auto-instrumentation enabled")
    except ImportError:
        logger.debug("asyncpg instrumentation package not available")
