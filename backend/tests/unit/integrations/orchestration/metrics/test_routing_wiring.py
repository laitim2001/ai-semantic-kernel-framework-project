"""Unit tests for BusinessIntentRouter OpenTelemetry metrics wiring.

Sprint 005 (OTL-01 routing subset): verify that BusinessIntentRouter.route()
emits all four routing metrics via record_routing_request() and that
routing exceptions skip emit (so a broken metric path can never break
routing itself).

Strategy: use empty-string input to bypass all 3 routing layers (the
internal ``_build_empty_decision`` short-circuits without touching
pattern / semantic / LLM), then for the exception test make
pattern_matcher.match raise.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.integrations.orchestration import metrics as metrics_mod
from src.integrations.orchestration.intent_router.models import ITIntentCategory
from src.integrations.orchestration.intent_router.router import BusinessIntentRouter


@pytest.fixture
def fallback_collector(monkeypatch):
    collector = metrics_mod.OrchestrationMetricsCollector(use_opentelemetry=False)
    monkeypatch.setattr(metrics_mod, "_metrics_collector", collector)
    return collector


def _labels(hist_or_counter, filter_fn=None):
    dicts = [dict(k) for k in hist_or_counter._values.keys()]
    return [d for d in dicts if filter_fn is None or filter_fn(d)]


def _make_router() -> BusinessIntentRouter:
    """Router with pure Mock dependencies — safe because empty-input short
    circuits before any layer is invoked."""
    return BusinessIntentRouter(
        pattern_matcher=MagicMock(),
        semantic_router=MagicMock(),
        llm_classifier=MagicMock(),
    )


@pytest.mark.asyncio
async def test_successful_route_emits_four_routing_metrics(fallback_collector):
    router = _make_router()

    decision = await router.route("")  # empty → _build_empty_decision
    assert decision.intent_category == ITIntentCategory.UNKNOWN
    assert decision.routing_layer == "none"

    # 1. requests_total counter
    counter = fallback_collector._counters["orchestration_routing_requests_total"]
    assert len(counter._values) == 1
    key = list(counter._values.keys())[0]
    assert counter._values[key] == 1

    # 2. routing_latency histogram
    latency_hist = fallback_collector._histograms[
        "orchestration_routing_latency_seconds"
    ]
    latency_entries = _labels(latency_hist)
    assert len(latency_entries) == 1
    # 3. routing_confidence histogram
    conf_hist = fallback_collector._histograms["orchestration_routing_confidence"]
    assert len(_labels(conf_hist)) == 1
    # 4. completeness_score histogram
    comp_hist = fallback_collector._histograms["orchestration_completeness_score"]
    assert len(_labels(comp_hist)) == 1


@pytest.mark.asyncio
async def test_labels_intent_category_and_layer(fallback_collector):
    router = _make_router()
    await router.route("")

    counter = fallback_collector._counters["orchestration_routing_requests_total"]
    label_dict = dict(list(counter._values.keys())[0])
    assert label_dict["intent_category"] == ITIntentCategory.UNKNOWN.value
    assert label_dict["layer_used"] == "none"

    latency_hist = fallback_collector._histograms[
        "orchestration_routing_latency_seconds"
    ]
    latency_label = dict(list(latency_hist._values.keys())[0])
    assert latency_label == {"layer_used": "none"}


@pytest.mark.asyncio
async def test_route_exception_skips_emit(fallback_collector):
    pattern_matcher = MagicMock()
    pattern_matcher.match.side_effect = RuntimeError("matcher broken")
    router = BusinessIntentRouter(
        pattern_matcher=pattern_matcher,
        semantic_router=MagicMock(),
        llm_classifier=MagicMock(),
    )

    with pytest.raises(RuntimeError):
        await router.route("some actionable input")

    # decision is None in the finally block → no emit should happen.
    counter = fallback_collector._counters["orchestration_routing_requests_total"]
    assert counter._values == {}
    for name in (
        "orchestration_routing_latency_seconds",
        "orchestration_routing_confidence",
        "orchestration_completeness_score",
    ):
        assert fallback_collector._histograms[name]._values == {}
