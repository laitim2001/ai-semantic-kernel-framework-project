"""
Telemetry Module for IPA Platform

Sprint 2 - Story S2-5: Monitoring Integration Service

Provides OpenTelemetry instrumentation for:
- Distributed tracing (spans)
- Metrics collection
- Log correlation

Local Development: Uses console exporters for zero-cost development
Production: Configured for Azure Monitor / Jaeger / Prometheus
"""
from .setup import setup_telemetry, get_tracer, get_meter
from .metrics import MetricsService, get_metrics_service

__all__ = [
    "setup_telemetry",
    "get_tracer",
    "get_meter",
    "MetricsService",
    "get_metrics_service",
]
