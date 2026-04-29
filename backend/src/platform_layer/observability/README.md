# platform/observability

Concrete implementation of `agent_harness.observability.Tracer` ABC.
Wraps OpenTelemetry SDK + Jaeger exporter + Prometheus exporter.

**Implementation Phase**: 49.4
**ABC location**: `backend/src/agent_harness/observability/_abc.py`
**Mandatory instrumentation points**: see `.claude/rules/observability-instrumentation.md` (5 must-instrument locations)
