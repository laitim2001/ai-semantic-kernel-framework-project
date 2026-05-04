"""
File: backend/src/agent_harness/observability/helpers.py
Purpose: Cat 12 cross-cutting span primitive — single owner of no-op + start_span boilerplate.
Category: 範疇 12 (Observability — cross-cutting)
Scope: Sprint 55.3 / AD-Cat12-Helpers-1

Description:
    Single primitive `category_span` extracted from sibling _obs.py wrappers
    (verification/_obs.py / business_domain/_obs.py) so the no-op + start_span
    pattern is owned in one place. Per-subsystem wrappers (verification_span
    / business_service_span / future subagent_span / future error_handling_span)
    delegate here for the common boilerplate, and add their own ergonomic
    signatures + category mapping. This avoids each subsystem re-implementing
    the `if tracer is None: yield/return` + `async with tracer.start_span(...)`
    block (DRY violation accumulating per 54.2 retro Q5).

Created: 2026-05-04 (Sprint 55.3)

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.3) — extract from verification + business_domain _obs

Related:
    - agent_harness/verification/_obs.py — delegates to category_span (origin Sprint 54.2)
    - business_domain/_obs.py — delegates to category_span (origin Sprint 55.1)
    - agent_harness/observability/_abc.py — Tracer ABC
    - agent_harness/_contracts/observability.py — SpanCategory enum
    - 17-cross-category-interfaces.md §Contract 12
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from agent_harness._contracts import SpanCategory
from agent_harness.observability._abc import Tracer


@contextlib.asynccontextmanager
async def category_span(
    tracer: Tracer | None,
    name: str,
    category: SpanCategory,
) -> AsyncIterator[None]:
    """Async ctx mgr emitting span ``name`` under ``category``; no-op when tracer is None.

    This is the single primitive owned by Cat 12 cross-cutting layer. All
    subsystem-specific span helpers (verification_span / business_service_span
    / future subagent_span / future error_handling_span) should delegate here
    rather than re-implement the no-op + start_span boilerplate.

    The TraceContext yielded by ``Tracer.start_span`` is intentionally
    discarded; callers that need the TraceContext should use ``Tracer.start_span``
    directly. This helper is for the common case where caller only needs the
    timing / categorization of a logical block.

    Args:
        tracer: optional Tracer (None → no-op).
        name: span name (subsystem prefix included by caller, e.g. "verifier.foo").
        category: SpanCategory enum value (VERIFICATION / TOOLS / SUBAGENT / etc.).
    """
    if tracer is None:
        yield
        return
    async with tracer.start_span(name=name, category=category):
        yield
