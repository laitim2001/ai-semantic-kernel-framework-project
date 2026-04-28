"""Unit tests for Pipeline Step OpenTelemetry metrics wiring.

Sprint 005 (OTL-02): verify that PipelineStep.execute() emits the
``orchestration_pipeline_step_latency_ms`` histogram and the
``orchestration_pipeline_step_errors_total`` counter on the correct
paths (success / error / HITL-pause / Dialog-pause).

Uses a fresh fallback (in-memory) collector so no OpenTelemetry SDK
backend is required.
"""

from __future__ import annotations

import pytest

from src.integrations.orchestration import metrics as metrics_mod
from src.integrations.orchestration.pipeline.context import PipelineContext
from src.integrations.orchestration.pipeline.exceptions import (
    DialogPauseException,
    HITLPauseException,
)
from src.integrations.orchestration.pipeline.steps.base import PipelineStep


@pytest.fixture
def fallback_collector(monkeypatch):
    """Swap global collector with a fresh fallback-only instance per test."""
    collector = metrics_mod.OrchestrationMetricsCollector(use_opentelemetry=False)
    monkeypatch.setattr(metrics_mod, "_metrics_collector", collector)
    return collector


def _ctx() -> PipelineContext:
    return PipelineContext(user_id="u1", session_id="s1", task="hello")


def _labels(hist_or_counter, filter_fn=None):
    """Return list of label dicts from a FallbackCounter / FallbackHistogram."""
    keys = list(hist_or_counter._values.keys())
    dicts = [dict(k) for k in keys]
    return [d for d in dicts if filter_fn is None or filter_fn(d)]


class _SuccessStep(PipelineStep):
    @property
    def name(self) -> str:
        return "memory_read"

    @property
    def step_index(self) -> int:
        return 1

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        return context


class _FailStep(PipelineStep):
    @property
    def name(self) -> str:
        return "intent_analysis"

    @property
    def step_index(self) -> int:
        return 2

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        raise ValueError("boom")


class _HITLStep(PipelineStep):
    @property
    def name(self) -> str:
        return "hitl_gate"

    @property
    def step_index(self) -> int:
        return 4

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        raise HITLPauseException(
            approval_id="app-1",
            checkpoint_id="ckpt-1",
            risk_level="high",
        )


class _DialogStep(PipelineStep):
    @property
    def name(self) -> str:
        return "intent_analysis"

    @property
    def step_index(self) -> int:
        return 2

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        raise DialogPauseException(
            dialog_id="d-1",
            questions=["What is the impact?"],
            missing_fields=["impact"],
            checkpoint_id="ckpt-1",
        )


@pytest.mark.asyncio
async def test_successful_step_emits_latency_histogram(fallback_collector):
    await _SuccessStep().execute(_ctx())

    hist = fallback_collector._histograms["orchestration_pipeline_step_latency_ms"]
    success = _labels(hist, lambda d: d.get("status") == "success")
    assert len(success) == 1
    assert success[0]["step_name"] == "memory_read"
    assert success[0]["step_index"] == "1"

    counter = fallback_collector._counters["orchestration_pipeline_step_errors_total"]
    assert counter._values == {}


@pytest.mark.asyncio
async def test_failed_step_emits_error_counter(fallback_collector):
    with pytest.raises(ValueError):
        await _FailStep().execute(_ctx())

    counter = fallback_collector._counters["orchestration_pipeline_step_errors_total"]
    err = _labels(counter)
    assert len(err) == 1
    assert err[0] == {
        "step_name": "intent_analysis",
        "step_index": "2",
        "error_type": "ValueError",
    }
    # Counter value for that label == 1
    key = tuple(sorted(err[0].items()))
    assert counter._values[key] == 1

    hist = fallback_collector._histograms["orchestration_pipeline_step_latency_ms"]
    error_hist = _labels(hist, lambda d: d.get("status") == "error")
    assert len(error_hist) == 1


@pytest.mark.asyncio
async def test_hitl_pause_not_counted_as_error(fallback_collector):
    with pytest.raises(HITLPauseException):
        await _HITLStep().execute(_ctx())

    counter = fallback_collector._counters["orchestration_pipeline_step_errors_total"]
    assert counter._values == {}

    hist = fallback_collector._histograms["orchestration_pipeline_step_latency_ms"]
    paused = _labels(hist, lambda d: d.get("status") == "paused")
    assert len(paused) == 1
    assert paused[0]["step_name"] == "hitl_gate"
    assert paused[0]["step_index"] == "4"


@pytest.mark.asyncio
async def test_dialog_pause_not_counted_as_error(fallback_collector):
    with pytest.raises(DialogPauseException):
        await _DialogStep().execute(_ctx())

    counter = fallback_collector._counters["orchestration_pipeline_step_errors_total"]
    assert counter._values == {}

    hist = fallback_collector._histograms["orchestration_pipeline_step_latency_ms"]
    paused = _labels(hist, lambda d: d.get("status") == "paused")
    assert len(paused) == 1
    assert paused[0]["step_name"] == "intent_analysis"


@pytest.mark.asyncio
async def test_labels_include_step_name_and_index(fallback_collector):
    await _SuccessStep().execute(_ctx())

    hist = fallback_collector._histograms["orchestration_pipeline_step_latency_ms"]
    all_labels = _labels(hist)
    assert len(all_labels) == 1
    assert all_labels[0] == {
        "step_name": "memory_read",
        "step_index": "1",
        "status": "success",
    }
