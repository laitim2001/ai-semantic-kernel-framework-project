"""Category 12: Observability (cross-cutting). See README.md.

Single-source map:
- Tracer ABC: _abc.py
- NoOpTracer / OTelTracer: tracer.py
- MetricRegistry / MetricSpec / REQUIRED_METRICS / emit: metrics.py
- OTelExporterConfig / build_tracer_provider / build_meter_provider: exporter.py
"""

from agent_harness.observability._abc import Tracer
from agent_harness.observability.exporter import (
    OTelExporterConfig,
    build_meter_provider,
    build_tracer_provider,
)
from agent_harness.observability.metrics import (
    REQUIRED_METRICS,
    MetricKind,
    MetricRegistry,
    MetricSpec,
    emit,
)
from agent_harness.observability.tracer import NoOpTracer, OTelTracer

__all__ = [
    "MetricKind",
    "MetricRegistry",
    "MetricSpec",
    "NoOpTracer",
    "OTelExporterConfig",
    "OTelTracer",
    "REQUIRED_METRICS",
    "Tracer",
    "build_meter_provider",
    "build_tracer_provider",
    "emit",
]
