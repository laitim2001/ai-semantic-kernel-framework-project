"""
File: backend/tests/unit/business_domain/test_obs.py
Purpose: business_service_span ctx mgr — 3 cases (noop / success / exception propagates).
Category: Tests / Business Domain / Cat 12 obs glue
Scope: Sprint 55.1 / Day 2.2

Created: 2026-05-04 (Sprint 55.1 Day 2)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import pytest

from agent_harness._contracts import SpanCategory, TraceContext
from agent_harness.observability import Tracer
from business_domain._obs import business_service_span


class _RecordingTracer(Tracer):
    """Minimal Tracer mock that records start_span calls."""

    def __init__(self) -> None:
        self.spans: list[tuple[str, SpanCategory]] = []

    def start_span(  # type: ignore[override]
        self,
        *,
        name: str,
        category: SpanCategory,
        trace_context: TraceContext | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Any:
        self.spans.append((name, category))

        @asynccontextmanager
        async def _cm() -> Any:
            yield TraceContext.create_root()

        return _cm()

    def record_metric(self, event: Any) -> None:  # noqa: D401
        pass

    def get_current_context(self) -> TraceContext | None:
        return None


@pytest.mark.asyncio
async def test_business_service_span_noop_when_tracer_none() -> None:
    """tracer=None → ctx mgr is a no-op; body still runs."""
    ran = False
    async with business_service_span(None, service_name="incident", method="create"):
        ran = True
    assert ran is True


@pytest.mark.asyncio
async def test_business_service_span_emits_under_tools() -> None:
    """tracer present → start_span called with TOOLS category + correct name."""
    tracer = _RecordingTracer()
    async with business_service_span(tracer, service_name="incident", method="list"):
        pass
    assert tracer.spans == [("business_service.incident.list", SpanCategory.TOOLS)]


@pytest.mark.asyncio
async def test_business_service_span_propagates_exception() -> None:
    """Exception inside body must propagate (ctx mgr does not swallow)."""
    tracer = _RecordingTracer()
    with pytest.raises(RuntimeError, match="boom"):
        async with business_service_span(tracer, service_name="incident", method="close"):
            raise RuntimeError("boom")
    # span still recorded (entered before raise)
    assert tracer.spans == [("business_service.incident.close", SpanCategory.TOOLS)]
