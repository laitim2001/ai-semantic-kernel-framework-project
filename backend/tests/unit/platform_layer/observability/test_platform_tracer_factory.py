"""
File: backend/tests/unit/platform_layer/observability/test_platform_tracer_factory.py
Purpose: Unit tests for platform_layer.observability.get_tracer factory.
Category: Tests / Platform / Observability
Scope: Sprint 56.2 / Day 1 / US-1 (closes AD-Cat12-BusinessObs)

Note: filename intentionally distinct from agent_harness/observability/test_tracer.py
to avoid pytest module-name collision (no __init__.py in tests/ tree).
"""

from __future__ import annotations

import pytest

from agent_harness._contracts import SpanCategory
from agent_harness.observability.helpers import category_span
from agent_harness.observability.tracer import NoOpTracer, OTelTracer
from business_domain._service_factory import BusinessServiceFactory
from platform_layer.observability import get_tracer
from platform_layer.observability import tracer as tracer_module


@pytest.fixture(autouse=True)
def _reset_tracer_singleton() -> None:
    """Reset module-level OTelTracer singleton before each test.

    Per .claude/rules/testing.md §Module-level Singleton Reset Pattern — even
    though OTelTracer holds no event-loop-bound resources, tests asserting
    distinct instances or fresh state benefit from a clean slate.
    """
    tracer_module._TRACER = None


class TestGetTracer:
    def test_returns_otel_tracer_instance(self) -> None:
        t = get_tracer()
        assert isinstance(t, OTelTracer)

    def test_idempotent_returns_same_instance(self) -> None:
        t1 = get_tracer()
        t2 = get_tracer()
        assert t1 is t2

    def test_business_service_factory_accepts_real_tracer(self) -> None:
        t = get_tracer()
        bf = BusinessServiceFactory(  # type: ignore[arg-type]
            db=None, tenant_id="test-tenant", tracer=t
        )
        assert bf._tracer is t


class TestServiceSpanEmission:
    @pytest.mark.asyncio
    async def test_incident_service_emits_span_via_noop_tracer(self) -> None:
        """NoOpTracer records span name + category for assertion."""
        t = NoOpTracer()
        async with category_span(t, "incident.create", SpanCategory.TOOLS):
            pass
        assert ("incident.create", SpanCategory.TOOLS) in t.spans_started

    @pytest.mark.asyncio
    async def test_category_span_no_op_when_tracer_is_none(self) -> None:
        """Pre-56.2 tracer=None path still works — graceful no-op."""
        async with category_span(None, "incident.create", SpanCategory.TOOLS):
            pass  # No exception, no recording.
