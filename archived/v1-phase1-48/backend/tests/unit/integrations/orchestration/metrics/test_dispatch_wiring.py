"""Unit tests for Dispatch Executor OpenTelemetry metrics wiring.

Sprint 005 (OTL-03): verify that BaseExecutor.execute() emits the
``orchestration_dispatch_latency_ms`` histogram and the
``orchestration_dispatch_errors_total`` counter for success / result-status
/ exception paths.
"""

from __future__ import annotations

import pytest

from src.integrations.orchestration import metrics as metrics_mod
from src.integrations.orchestration.dispatch.executors.base import BaseExecutor
from src.integrations.orchestration.dispatch.models import (
    DispatchRequest,
    DispatchResult,
    ExecutionRoute,
)


@pytest.fixture
def fallback_collector(monkeypatch):
    collector = metrics_mod.OrchestrationMetricsCollector(use_opentelemetry=False)
    monkeypatch.setattr(metrics_mod, "_metrics_collector", collector)
    return collector


def _req(route: ExecutionRoute = ExecutionRoute.DIRECT_ANSWER) -> DispatchRequest:
    return DispatchRequest(route=route, task="hi", user_id="u1", session_id="s1")


def _labels(hist_or_counter, filter_fn=None):
    dicts = [dict(k) for k in hist_or_counter._values.keys()]
    return [d for d in dicts if filter_fn is None or filter_fn(d)]


class _SuccessExecutor(BaseExecutor):
    @property
    def name(self) -> str:
        return "direct_answer"

    async def _execute(self, request, event_queue=None):
        return DispatchResult(
            route=request.route, response_text="ok", status="completed"
        )


class _TimeoutExecutor(BaseExecutor):
    @property
    def name(self) -> str:
        return "subagent"

    async def _execute(self, request, event_queue=None):
        return DispatchResult(route=request.route, status="timeout")


class _FailExecutor(BaseExecutor):
    @property
    def name(self) -> str:
        return "team"

    async def _execute(self, request, event_queue=None):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_successful_dispatch_emits_latency(fallback_collector):
    await _SuccessExecutor().execute(_req())

    hist = fallback_collector._histograms["orchestration_dispatch_latency_ms"]
    entries = _labels(hist)
    assert len(entries) == 1
    assert entries[0] == {"executor": "direct_answer", "status": "completed"}

    counter = fallback_collector._counters["orchestration_dispatch_errors_total"]
    assert counter._values == {}


@pytest.mark.asyncio
async def test_dispatch_exception_emits_error_counter(fallback_collector):
    with pytest.raises(RuntimeError):
        await _FailExecutor().execute(_req(ExecutionRoute.TEAM))

    counter = fallback_collector._counters["orchestration_dispatch_errors_total"]
    err = _labels(counter)
    assert len(err) == 1
    assert err[0] == {"executor": "team", "error_type": "RuntimeError"}
    key = tuple(sorted(err[0].items()))
    assert counter._values[key] == 1

    hist = fallback_collector._histograms["orchestration_dispatch_latency_ms"]
    error_hist = _labels(hist, lambda d: d.get("status") == "error")
    assert len(error_hist) == 1
    assert error_hist[0]["executor"] == "team"


@pytest.mark.asyncio
async def test_result_status_field_flows_into_label(fallback_collector):
    await _TimeoutExecutor().execute(_req(ExecutionRoute.SUBAGENT))

    hist = fallback_collector._histograms["orchestration_dispatch_latency_ms"]
    timeout = _labels(hist, lambda d: d.get("status") == "timeout")
    assert len(timeout) == 1
    assert timeout[0]["executor"] == "subagent"

    # No error counter increment for non-exception status.
    counter = fallback_collector._counters["orchestration_dispatch_errors_total"]
    assert counter._values == {}
