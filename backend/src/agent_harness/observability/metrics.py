"""
File: backend/src/agent_harness/observability/metrics.py
Purpose: MetricRegistry — 7 V2 required metrics + emit helper.
Category: 範疇 12 (Observability — cross-cutting)
Scope: Phase 49 / Sprint 49.4 Day 3

Description:
    Defines the 7 metrics every Phase 50+ implementation MUST emit per
    .claude/rules/observability-instrumentation.md §7 必埋 metric:

        1. agent_loop_duration_seconds      (histogram) — full loop end-to-end
        2. tool_execution_duration_seconds  (histogram) — per Cat 2 tool call
        3. llm_chat_duration_seconds        (histogram) — adapter chat() roundtrip
        4. llm_tokens_total                 (counter)   — labeled input/output/cached
        5. verification_pass_rate           (gauge)     — Cat 10 self-correction
        6. loop_compaction_count            (counter)   — Cat 4 compaction triggers
        7. loop_subagent_dispatch_count     (counter)   — Cat 11 dispatch count

    MetricRegistry exposes a typed `emit(...)` helper so call sites don't
    pass strings around. The actual recording goes through a Tracer
    (NoOpTracer for tests, OTelTracer in production).

Created: 2026-04-29 (Sprint 49.4 Day 3)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4 Day 3) — 7 required metrics

Related:
    - tracer.py — Tracer.record_metric() consumer
    - .claude/rules/observability-instrumentation.md §7 必埋 metric
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from agent_harness._contracts import MetricEvent, SpanCategory, TraceContext
from agent_harness.observability._abc import Tracer

MetricKind = Literal["counter", "gauge", "histogram"]


@dataclass(frozen=True)
class MetricSpec:
    """Single metric definition. Frozen — registry is read-only post-init."""

    name: str
    kind: MetricKind
    category: SpanCategory
    description: str
    unit: str = ""


# ---------------------------------------------------------------------------
# 7 V2 required metrics — single-source per observability-instrumentation.md
# ---------------------------------------------------------------------------

REQUIRED_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(
        name="agent_loop_duration_seconds",
        kind="histogram",
        category=SpanCategory.ORCHESTRATOR,
        description="End-to-end loop duration (Cat 1)",
        unit="s",
    ),
    MetricSpec(
        name="tool_execution_duration_seconds",
        kind="histogram",
        category=SpanCategory.TOOLS,
        description="Per-tool execution duration (Cat 2)",
        unit="s",
    ),
    MetricSpec(
        name="llm_chat_duration_seconds",
        kind="histogram",
        category=SpanCategory.OUTPUT_PARSER,
        description="ChatClient.chat() roundtrip (adapter layer; emitted from Cat 6)",
        unit="s",
    ),
    MetricSpec(
        name="llm_tokens_total",
        kind="counter",
        category=SpanCategory.OUTPUT_PARSER,
        description="Token counter labeled by type=input/output/cached",
        unit="tokens",
    ),
    MetricSpec(
        name="verification_pass_rate",
        kind="gauge",
        category=SpanCategory.VERIFICATION,
        description="Cat 10 verifier pass rate (0.0..1.0)",
        unit="ratio",
    ),
    MetricSpec(
        name="loop_compaction_count",
        kind="counter",
        category=SpanCategory.CONTEXT_MGMT,
        description="Cat 4 compaction trigger count",
        unit="events",
    ),
    MetricSpec(
        name="loop_subagent_dispatch_count",
        kind="counter",
        category=SpanCategory.SUBAGENT,
        description="Cat 11 subagent dispatch count",
        unit="events",
    ),
)


class _DuplicateMetricError(ValueError):
    pass


class MetricRegistry:
    """Registry of MetricSpec keyed by name. Pre-loaded with REQUIRED_METRICS."""

    def __init__(self) -> None:
        self._specs: dict[str, MetricSpec] = {}
        for spec in REQUIRED_METRICS:
            self.register(spec)

    def register(self, spec: MetricSpec) -> None:
        if spec.name in self._specs:
            raise _DuplicateMetricError(f"metric {spec.name!r} already registered")
        self._specs[spec.name] = spec

    def get(self, name: str) -> MetricSpec | None:
        return self._specs.get(name)

    def all(self) -> tuple[MetricSpec, ...]:
        return tuple(self._specs.values())

    def required_names(self) -> tuple[str, ...]:
        return tuple(s.name for s in REQUIRED_METRICS)


def emit(
    tracer: Tracer,
    *,
    metric_name: str,
    value: float,
    registry: MetricRegistry,
    labels: dict[str, str] | None = None,
    trace_context: TraceContext | None = None,
) -> None:
    """Type-safe metric emission. Looks up MetricSpec by name; raises KeyError if not registered.

    Call sites (e.g., AgentLoop) use this to ensure they only emit registered
    metrics — typos surface immediately.
    """
    spec = registry.get(metric_name)
    if spec is None:
        raise KeyError(
            f"metric {metric_name!r} not registered. " f"Known: {registry.required_names()}"
        )

    event = MetricEvent(
        metric_name=metric_name,
        metric_type=spec.kind,
        value=value,
        timestamp=datetime.now(timezone.utc),
        category=spec.category,
        labels=labels or {},
        trace_context=trace_context,
    )
    tracer.record_metric(event)


__all__ = [
    "MetricKind",
    "MetricRegistry",
    "MetricSpec",
    "REQUIRED_METRICS",
    "emit",
]
