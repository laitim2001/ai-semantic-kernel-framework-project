"""
File: backend/src/agent_harness/observability/exporter.py
Purpose: OTel exporter configuration helpers — OTLP (traces) + Prometheus (metrics).
Category: 範疇 12 (Observability — cross-cutting)
Scope: Phase 49 / Sprint 49.4 Day 3

Description:
    Builds the OTel SDK provider chain:
    - TracerProvider with OTLPSpanExporter → Jaeger via OTLP/gRPC on :4317
    - MeterProvider with PrometheusMetricReader → /metrics endpoint scraped by Prometheus

    These are factory functions; the actual provider registration with the
    OTel global API happens in platform_layer/observability/setup.py
    (one-shot at FastAPI startup).

    All SDK imports are lazy so unit tests using NoOpTracer don't load OTel
    SDK exporters into memory.

Created: 2026-04-29 (Sprint 49.4 Day 3)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4 Day 3)

Related:
    - tracer.py — OTelTracer (consumer)
    - platform_layer/observability/setup.py — global init wiring
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OTelExporterConfig:
    """User-facing config; populated from env in setup.py."""

    service_name: str = "ipa-v2-backend"
    otlp_endpoint: str = "http://localhost:4317"
    otlp_insecure: bool = True
    prometheus_port: int = 0  # 0 = bind to FastAPI's /metrics, not standalone
    enable_console_export: bool = False  # for debugging; do not enable in prod


def build_tracer_provider(config: OTelExporterConfig) -> Any:
    """Build a TracerProvider with OTLP exporter pointed at Jaeger.

    Returns the TracerProvider; caller registers it via:
        opentelemetry.trace.set_tracer_provider(provider)
    """
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    resource = Resource.create({"service.name": config.service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=config.otlp_endpoint, insecure=config.otlp_insecure)
        )
    )
    if config.enable_console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    return provider


def build_meter_provider(config: OTelExporterConfig) -> Any:
    """Build a MeterProvider with Prometheus reader.

    Caller registers via opentelemetry.metrics.set_meter_provider(provider).
    The Prometheus reader exposes metrics on a separate port; if
    config.prometheus_port == 0, no standalone HTTP server is started — the
    backend's /metrics endpoint (Phase 49.4 Day 5) reads from the same reader.
    """
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": config.service_name})
    reader = PrometheusMetricReader()
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    return provider


__all__ = [
    "OTelExporterConfig",
    "build_meter_provider",
    "build_tracer_provider",
]
