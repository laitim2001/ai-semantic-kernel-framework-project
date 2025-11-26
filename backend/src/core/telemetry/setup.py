"""
OpenTelemetry Setup

Sprint 2 - Story S2-5: Monitoring Integration Service
Sprint 3 - Story S3-6: Distributed Tracing with Jaeger

Sets up OpenTelemetry tracing and metrics for the application.
Supports multiple exporters:
- Console (development)
- OTLP (Jaeger/OTEL Collector)
- Prometheus (metrics)
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple
from contextlib import contextmanager

from opentelemetry import trace, metrics, context
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap, inject, extract
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.composite import CompositePropagator

logger = logging.getLogger(__name__)

# Global instances
_tracer_provider: Optional[TracerProvider] = None
_meter_provider: Optional[MeterProvider] = None
_initialized: bool = False


def setup_telemetry(
    app=None,
    engine=None,
    service_name: str = "ipa-platform",
    service_version: str = "0.1.0",
    enable_console: bool = True,
    enable_otlp: bool = False,
    enable_jaeger: bool = False,
    enable_prometheus: bool = False,
) -> Tuple[TracerProvider, MeterProvider]:
    """
    Set up OpenTelemetry instrumentation.

    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine for database instrumentation
        service_name: Name of the service
        service_version: Version of the service
        enable_console: Enable console exporters (for development)
        enable_otlp: Enable OTLP exporter (for Jaeger/OTEL Collector)
        enable_jaeger: Enable legacy Jaeger Thrift exporter
        enable_prometheus: Enable Prometheus metrics

    Returns:
        Tuple of (TracerProvider, MeterProvider)
    """
    global _tracer_provider, _meter_provider, _initialized

    if _initialized:
        logger.info("OpenTelemetry already initialized, skipping...")
        return _tracer_provider, _meter_provider

    # Get configuration from environment
    otel_service_name = os.getenv("OTEL_SERVICE_NAME", service_name)
    environment = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development"))
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    jaeger_enabled = os.getenv("JAEGER_ENABLED", "false").lower() == "true"

    # Auto-enable OTLP if JAEGER_ENABLED or endpoint is set
    if jaeger_enabled or "OTEL_EXPORTER_OTLP_ENDPOINT" in os.environ:
        enable_otlp = True

    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: otel_service_name,
        SERVICE_VERSION: service_version,
        "environment": environment,
        "service.namespace": "ipa-platform",
        "deployment.environment": environment,
    })

    # Set up Tracer Provider
    _tracer_provider = TracerProvider(resource=resource)

    # Add span processors based on configuration
    if enable_console and environment == "development":
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("OpenTelemetry: Console span exporter enabled")

    if enable_otlp:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True,  # Use insecure for local development
            )
            _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OpenTelemetry: OTLP span exporter enabled ({otlp_endpoint})")
        except ImportError:
            logger.warning("OTLP exporter not available - install opentelemetry-exporter-otlp-proto-grpc")

    if enable_jaeger and not enable_otlp:
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            jaeger_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
            jaeger_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
            _tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info(f"OpenTelemetry: Jaeger Thrift exporter enabled ({jaeger_host}:{jaeger_port})")
        except ImportError:
            logger.warning("Jaeger exporter not available - install opentelemetry-exporter-jaeger")

    # Set the global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Set up Meter Provider
    metric_readers = []

    if enable_console and environment == "development":
        console_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=60000,  # Export every 60 seconds
        )
        metric_readers.append(console_reader)
        logger.info("OpenTelemetry: Console metric exporter enabled")

    if enable_prometheus:
        try:
            from opentelemetry.exporter.prometheus import PrometheusMetricReader
            prometheus_reader = PrometheusMetricReader()
            metric_readers.append(prometheus_reader)
            logger.info("OpenTelemetry: Prometheus metric exporter enabled")
        except ImportError:
            logger.warning("Prometheus exporter not available - install opentelemetry-exporter-prometheus")

    if not metric_readers:
        # Fallback to console if nothing configured
        metric_readers.append(PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=300000,  # 5 minutes for production default
        ))

    _meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(_meter_provider)

    # Set up propagators for distributed tracing
    # Support both W3C Trace Context and B3 for compatibility
    propagator = CompositePropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
        B3MultiFormat(),
    ])
    set_global_textmap(propagator)

    # Instrument FastAPI if app provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=_tracer_provider)
        logger.info("OpenTelemetry: FastAPI instrumentation enabled")

    # Instrument httpx for outbound HTTP calls
    HTTPXClientInstrumentor().instrument()
    logger.info("OpenTelemetry: HTTPX instrumentation enabled")

    # Instrument SQLAlchemy if engine provided
    if engine is not None:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,
            commenter_options={"db_framework": True},
        )
        logger.info("OpenTelemetry: SQLAlchemy instrumentation enabled")

    _initialized = True
    logger.info(f"OpenTelemetry setup complete for {otel_service_name} ({environment})")

    return _tracer_provider, _meter_provider


def get_tracer(name: str = __name__) -> trace.Tracer:
    """
    Get a tracer for the given name.

    Args:
        name: Name of the tracer (typically __name__)

    Returns:
        OpenTelemetry Tracer instance
    """
    return trace.get_tracer(name)


def get_meter(name: str = __name__) -> metrics.Meter:
    """
    Get a meter for the given name.

    Args:
        name: Name of the meter (typically __name__)

    Returns:
        OpenTelemetry Meter instance
    """
    return metrics.get_meter(name)


def get_current_span() -> Optional[Span]:
    """Get the current active span."""
    return trace.get_current_span()


def get_trace_id() -> Optional[str]:
    """Get the current trace ID as a hex string."""
    span = get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, '032x')
    return None


def get_span_id() -> Optional[str]:
    """Get the current span ID as a hex string."""
    span = get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, '016x')
    return None


@contextmanager
def create_span(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[dict] = None,
):
    """
    Context manager to create a new span.

    Args:
        name: Name of the span
        kind: Kind of span (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)
        attributes: Optional attributes to add to the span

    Yields:
        The created span
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=attributes or {},
    ) as span:
        yield span


def add_span_attributes(attributes: dict):
    """Add attributes to the current span."""
    span = get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[dict] = None):
    """Add an event to the current span."""
    span = get_current_span()
    if span:
        span.add_event(name, attributes=attributes or {})


def set_span_status(status: StatusCode, description: Optional[str] = None):
    """Set the status of the current span."""
    span = get_current_span()
    if span:
        span.set_status(Status(status, description))


def record_exception(exception: Exception):
    """Record an exception in the current span."""
    span = get_current_span()
    if span:
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))


def inject_trace_context(carrier: dict) -> dict:
    """
    Inject trace context into a carrier (e.g., HTTP headers).

    Args:
        carrier: Dictionary to inject context into

    Returns:
        The carrier with injected context
    """
    inject(carrier)
    return carrier


def extract_trace_context(carrier: dict):
    """
    Extract trace context from a carrier (e.g., HTTP headers).

    Args:
        carrier: Dictionary containing trace context

    Returns:
        OpenTelemetry context
    """
    return extract(carrier)


def shutdown_telemetry():
    """Shutdown telemetry providers gracefully."""
    global _tracer_provider, _meter_provider, _initialized

    if _tracer_provider:
        _tracer_provider.shutdown()
        logger.info("OpenTelemetry: Tracer provider shutdown")

    if _meter_provider:
        _meter_provider.shutdown()
        logger.info("OpenTelemetry: Meter provider shutdown")

    _initialized = False


def reset_telemetry():
    """Reset telemetry for testing purposes."""
    global _tracer_provider, _meter_provider, _initialized
    shutdown_telemetry()
    _tracer_provider = None
    _meter_provider = None
    _initialized = False
