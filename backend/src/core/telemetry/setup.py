"""
OpenTelemetry Setup

Sprint 2 - Story S2-5: Monitoring Integration Service

Sets up OpenTelemetry tracing and metrics for the application.
Local development uses console exporters for zero-cost operation.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat

logger = logging.getLogger(__name__)

# Global instances
_tracer_provider: Optional[TracerProvider] = None
_meter_provider: Optional[MeterProvider] = None


def setup_telemetry(
    app=None,
    engine=None,
    service_name: str = "ipa-platform",
    service_version: str = "0.1.0",
    enable_console: bool = True,
    enable_jaeger: bool = False,
    enable_prometheus: bool = False,
) -> tuple[TracerProvider, MeterProvider]:
    """
    Set up OpenTelemetry instrumentation.

    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine for database instrumentation
        service_name: Name of the service
        service_version: Version of the service
        enable_console: Enable console exporters (for development)
        enable_jaeger: Enable Jaeger exporter (for production tracing)
        enable_prometheus: Enable Prometheus metrics (for production)

    Returns:
        Tuple of (TracerProvider, MeterProvider)
    """
    global _tracer_provider, _meter_provider

    # Get configuration from environment
    otel_service_name = os.getenv("OTEL_SERVICE_NAME", service_name)
    environment = os.getenv("ENVIRONMENT", "development")

    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: otel_service_name,
        SERVICE_VERSION: service_version,
        "environment": environment,
        "service.namespace": "ipa-platform",
    })

    # Set up Tracer Provider
    _tracer_provider = TracerProvider(resource=resource)

    # Add span processors based on configuration
    if enable_console or environment == "development":
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("OpenTelemetry: Console span exporter enabled")

    if enable_jaeger:
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            jaeger_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
            jaeger_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
            _tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info(f"OpenTelemetry: Jaeger exporter enabled ({jaeger_host}:{jaeger_port})")
        except ImportError:
            logger.warning("Jaeger exporter not available - install opentelemetry-exporter-jaeger")

    # Set the global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Set up Meter Provider
    metric_readers = []

    if enable_console or environment == "development":
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

    # Set up B3 propagation for distributed tracing
    set_global_textmap(B3MultiFormat())

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


def shutdown_telemetry():
    """Shutdown telemetry providers gracefully."""
    global _tracer_provider, _meter_provider

    if _tracer_provider:
        _tracer_provider.shutdown()
        logger.info("OpenTelemetry: Tracer provider shutdown")

    if _meter_provider:
        _meter_provider.shutdown()
        logger.info("OpenTelemetry: Meter provider shutdown")
