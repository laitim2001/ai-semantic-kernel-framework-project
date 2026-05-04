"""
File: backend/src/business_domain/_obs.py
Purpose: Cat 12 observability glue for business-domain services — tracer span helper.
Category: Business Domain × 範疇 12 (Observability — cross-cutting)
Scope: Sprint 55.1 US-2 / Day 2.2

Description:
    Single helper used by all 5 business-domain services (incident / patrol /
    correlation / rootcause / audit_domain) so the span-or-noop pattern is
    written once, not duplicated per file. Mirrors the
    `agent_harness/verification/_obs.py verification_span` helper introduced
    in Sprint 54.2 US-5 (AD-Cat10-Obs-1) to keep observability glue uniform.

    Span name format: `business_service.{service_name}.{method}`
    Span category:    SpanCategory.TOOLS
        — Business services are invoked via Cat 2 ToolHandler at the tool
        execution boundary; their spans are children of the tool span.
        Adding a dedicated BUSINESS_DOMAIN SpanCategory would cross
        single-source ownership (17.md §SpanCategory enum), so we reuse
        TOOLS here. AD-Cat12-Helpers-1 (54.2 retro Q6 carryover) tracks the
        broader question of consolidating per-domain obs helpers + metrics.

D5 (scope): plan §US-5 specified 3 metrics (duration_seconds + calls_total +
    errors_total) emitted via `Tracer.record_metric()`. Reverted to span-only
    to match `verification_span` precedent and avoid duplicating MetricEvent
    construction across 25 service methods. Metrics deferred to
    AD-Cat12-Helpers-1 closure (Phase 55.2+); span timing already captured
    by the start_span ctx manager via OTel-derived implementations.

Created: 2026-05-04 (Sprint 55.1 Day 2)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Sprint 55.3 — delegate to category_span (closes AD-Cat12-Helpers-1)
    - 2026-05-04: Initial creation (Sprint 55.1 Day 2.2)

Related:
    - agent_harness/observability/helpers.py — category_span primitive (single owner; Sprint 55.3)
    - agent_harness/verification/_obs.py (sibling wrapper, Sprint 54.2)
    - agent_harness/observability/_abc.py — Tracer ABC
    - agent_harness/_contracts/observability.py — SpanCategory.TOOLS
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from agent_harness._contracts import SpanCategory
from agent_harness.observability import Tracer, category_span


@contextlib.asynccontextmanager
async def business_service_span(
    tracer: Tracer | None,
    *,
    service_name: str,
    method: str,
) -> AsyncIterator[None]:
    """Emit `business_service.{service_name}.{method}` span under TOOLS; no-op if tracer is None.

    Delegates to `category_span` (Sprint 55.3 / AD-Cat12-Helpers-1).

    Args:
        tracer: optional Tracer (None → no-op).
        service_name: domain service identifier (e.g. "incident", "patrol").
        method: service method name (e.g. "create", "list", "close").
    """
    async with category_span(
        tracer,
        f"business_service.{service_name}.{method}",
        SpanCategory.TOOLS,
    ):
        yield
