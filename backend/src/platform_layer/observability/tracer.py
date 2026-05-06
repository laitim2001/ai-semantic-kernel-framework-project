"""
File: backend/src/platform_layer/observability/tracer.py
Purpose: Tracer FastAPI Depends factory — process-wide OTelTracer singleton (production).
Category: Platform / Observability (range cat 12 — process boundary)
Scope: Sprint 56.2 / Day 1 (US-1 — closes AD-Cat12-BusinessObs)

Description:
    Single ``get_tracer()`` Depends function that returns the production OTel-backed
    Tracer instance. Used at chat router boundary (api/v1/chat/router.py) to thread
    a real Tracer through BusinessServiceFactory → 5 business services so the
    9 service methods using ``category_span(self._tracer, ...)`` actually emit
    spans (instead of the no-op path triggered by tracer=None).

    Why this lives in platform_layer/observability/ (not agent_harness/):
    The OTel SDK process boundary is owned by platform_layer (49.4 setup.py
    initializes the SDK). agent_harness/observability/ owns the neutral Tracer
    ABC + concrete implementations (NoOpTracer + OTelTracer) — those are
    used directly by tests (NoOpTracer) and by this factory (OTelTracer).
    Splitting the factory here keeps the FastAPI Depends in the platform layer
    where the SDK lifecycle is owned.

    Why module-level singleton (not per-request):
    - OTelTracer.{_get_otel_tracer, _get_otel_meter} lazy-init internally; the
      same OTelTracer instance reused across requests is correct (and matches
      OTel SDK's own tracer/meter caching).
    - No event-loop-bound resources held → no AD-Test-1 reset fixture needed
      (per .claude/rules/testing.md §Module-level Singleton Reset Pattern catalog).
    - Tests override via ``app.dependency_overrides[get_tracer] = lambda: NoOpTracer()``.

Created: 2026-05-06 (Sprint 56.2 Day 1)

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.2 Day 1) — closes AD-Cat12-BusinessObs

Related:
    - agent_harness/observability/tracer.py — NoOpTracer + OTelTracer concrete impls
    - agent_harness/observability/_abc.py — Tracer ABC
    - agent_harness/observability/helpers.py — category_span async ctx mgr
    - platform_layer/observability/setup.py — process-wide OTel SDK init (49.4)
    - api/v1/chat/router.py — consumer (replaces tracer=None at L147)
    - business_domain/_service_factory.py — BusinessServiceFactory(tracer=...)
    - .claude/rules/observability-instrumentation.md
    - .claude/rules/testing.md §Module-level Singleton Reset Pattern (catalog non-membership)
"""

from __future__ import annotations

from agent_harness.observability._abc import Tracer
from agent_harness.observability.tracer import OTelTracer

_TRACER: Tracer | None = None


def get_tracer() -> Tracer:
    """Return the process-wide OTel-backed Tracer instance (lazy init).

    Used as a FastAPI ``Depends`` at chat router boundary to thread a real
    Tracer through BusinessServiceFactory → business services. Tests override
    via ``app.dependency_overrides[get_tracer] = lambda: NoOpTracer()`` to
    capture spans for assertions without an OTel collector running.
    """
    global _TRACER
    if _TRACER is None:
        _TRACER = OTelTracer()
    return _TRACER


__all__ = ["get_tracer"]
