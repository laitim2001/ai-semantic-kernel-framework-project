"""
Telemetry Module for IPA Platform

Sprint 2 - Story S2-5: Monitoring Integration Service
Sprint 3 - Story S3-6: Distributed Tracing with Jaeger

Provides OpenTelemetry instrumentation for:
- Distributed tracing (spans)
- Metrics collection
- Log correlation
- Context propagation

Local Development: Uses console exporters for zero-cost development
Production: Configured for Jaeger / OTLP / Prometheus
"""
from .setup import (
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
from .metrics import MetricsService, get_metrics_service

__all__ = [
    # Setup and core functions
    "setup_telemetry",
    "get_tracer",
    "get_meter",
    "shutdown_telemetry",
    "reset_telemetry",
    # Span management
    "get_current_span",
    "get_trace_id",
    "get_span_id",
    "create_span",
    "add_span_attributes",
    "add_span_event",
    "set_span_status",
    "record_exception",
    # Context propagation
    "inject_trace_context",
    "extract_trace_context",
    # Metrics
    "MetricsService",
    "get_metrics_service",
]
