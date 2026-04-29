"""
File: backend/tests/unit/agent_harness/observability/test_metrics.py
Purpose: Verify the 7 V2 required metrics are registered + emit() routing works.
Category: Tests / Observability
Scope: Phase 49 / Sprint 49.4 Day 3
"""

from __future__ import annotations

import pytest

from agent_harness.observability import (
    REQUIRED_METRICS,
    MetricRegistry,
    NoOpTracer,
    emit,
)


def test_seven_required_metrics_registered() -> None:
    """The 7 V2 metrics from observability-instrumentation.md §7 must all be present."""
    expected_names = {
        "agent_loop_duration_seconds",
        "tool_execution_duration_seconds",
        "llm_chat_duration_seconds",
        "llm_tokens_total",
        "verification_pass_rate",
        "loop_compaction_count",
        "loop_subagent_dispatch_count",
    }
    actual_names = {spec.name for spec in REQUIRED_METRICS}
    assert actual_names == expected_names

    registry = MetricRegistry()
    assert set(registry.required_names()) == expected_names


def test_emit_routes_to_tracer_with_correct_type() -> None:
    """emit() looks up MetricSpec.kind and creates MetricEvent with that type."""
    tracer = NoOpTracer()
    registry = MetricRegistry()

    emit(
        tracer,
        metric_name="agent_loop_duration_seconds",
        value=1.234,
        registry=registry,
        labels={"tenant_id": "t-1", "outcome": "success"},
    )

    assert len(tracer.recorded_metrics) == 1
    event = tracer.recorded_metrics[0]
    assert event.metric_name == "agent_loop_duration_seconds"
    assert event.metric_type == "histogram"
    assert event.value == 1.234
    assert event.labels == {"tenant_id": "t-1", "outcome": "success"}


def test_emit_unregistered_metric_raises() -> None:
    """Typo / unregistered metric name raises KeyError immediately at call site."""
    tracer = NoOpTracer()
    registry = MetricRegistry()

    with pytest.raises(KeyError):
        emit(
            tracer,
            metric_name="loop_compaction_kount",  # typo
            value=1.0,
            registry=registry,
        )
