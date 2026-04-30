"""
File: backend/src/agent_harness/observability/_abc.py
Purpose: Category 12 ABC — Tracer (cross-cutting tracing + metric ABC).
Category: 範疇 12 (Observability — cross-cutting)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 49.4)

Description:
    Cross-cutting concern: every other category's ABC accepts
    `trace_context: TraceContext`. Tracer.start_span() is called at
    each ABC entry; record_metric() emits 3-axis metrics (latency /
    token / cost).

    The OBSERVABILITY ABC lives here. The actual implementation
    (OTel + Jaeger + Prometheus exporters) lives in
    `platform/observability/` per architecture-design §5-layer.

Owner: 01-eleven-categories-spec.md §範疇 12
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Any

from agent_harness._contracts import MetricEvent, SpanCategory, TraceContext


class Tracer(ABC):
    """Cross-cutting tracing ABC. All categories receive Tracer-aware contexts."""

    @abstractmethod
    def start_span(
        self,
        *,
        name: str,
        category: SpanCategory,
        trace_context: TraceContext | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> AbstractAsyncContextManager[TraceContext]:
        """Async context manager that yields a child TraceContext."""
        ...

    @abstractmethod
    def record_metric(
        self,
        event: MetricEvent,
    ) -> None: ...

    @abstractmethod
    def get_current_context(self) -> TraceContext | None: ...
