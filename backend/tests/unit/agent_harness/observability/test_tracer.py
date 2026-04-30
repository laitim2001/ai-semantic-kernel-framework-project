"""
File: backend/tests/unit/agent_harness/observability/test_tracer.py
Purpose: Unit tests for NoOpTracer (Tracer ABC compliance + propagation).
Category: Tests / Observability
Scope: Phase 49 / Sprint 49.4 Day 3
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent_harness._contracts import SpanCategory, TraceContext
from agent_harness.observability import NoOpTracer, Tracer


@pytest.mark.asyncio
async def test_noop_tracer_is_tracer() -> None:
    """NoOpTracer must satisfy Tracer ABC (cannot instantiate otherwise)."""
    tracer = NoOpTracer()
    assert isinstance(tracer, Tracer)


@pytest.mark.asyncio
async def test_span_propagates_trace_id_and_links_parent() -> None:
    """Child span shares parent's trace_id; child.parent_span_id == parent.span_id."""
    tracer = NoOpTracer()
    parent = TraceContext.create_root()
    async with tracer.start_span(
        name="loop_turn",
        category=SpanCategory.ORCHESTRATOR,
        trace_context=parent,
    ) as child:
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.span_id != parent.span_id
        assert tracer.get_current_context() is child

    # After exit, current context restored
    assert tracer.get_current_context() is None


@pytest.mark.asyncio
async def test_nested_spans_share_root_trace() -> None:
    """Nested spans all share the same trace_id."""
    tracer = NoOpTracer()
    tenant = uuid4()
    root = TraceContext(tenant_id=tenant)

    async with tracer.start_span(
        name="outer", category=SpanCategory.ORCHESTRATOR, trace_context=root
    ) as outer:
        async with tracer.start_span(name="inner", category=SpanCategory.TOOLS) as inner:
            assert inner.trace_id == root.trace_id
            assert inner.parent_span_id == outer.span_id
            assert inner.tenant_id == tenant


@pytest.mark.asyncio
async def test_record_metric_collects_events() -> None:
    """NoOpTracer.record_metric() stores events for inspection."""
    from datetime import datetime, timezone

    from agent_harness._contracts import MetricEvent

    tracer = NoOpTracer()
    event = MetricEvent(
        metric_name="loop_compaction_count",
        metric_type="counter",
        value=1.0,
        timestamp=datetime.now(timezone.utc),
        category=SpanCategory.CONTEXT_MGMT,
        labels={"tenant_id": "t-1"},
    )
    tracer.record_metric(event)
    assert len(tracer.recorded_metrics) == 1
    assert tracer.recorded_metrics[0].metric_name == "loop_compaction_count"
