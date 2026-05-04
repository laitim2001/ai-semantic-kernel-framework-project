"""
File: backend/src/agent_harness/verification/_obs.py
Purpose: Cat 10 → Cat 12 observability glue — tracer span helper for verifiers.
Category: 範疇 10 (Verification) × 範疇 12 (Observability)
Scope: Sprint 54.2 US-5 (AD-Cat10-Obs-1 closure)

Description:
    Single helper used by all 4 verifier classes (rules_based / llm_judge /
    cat9_fallback / cat9_mutator) so that the span-or-noop pattern is
    written once, not duplicated per file. Per AD-Cat10-Obs-1 spec:
    `verifier.{name}` span is emitted under `SpanCategory.VERIFICATION`;
    no-op when tracer is None.

Created: 2026-05-04 (Sprint 54.2)

Related:
    - observability/_abc.py — Tracer ABC
    - _contracts/observability.py — SpanCategory.VERIFICATION
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from agent_harness._contracts import SpanCategory
from agent_harness.observability import Tracer


@contextlib.asynccontextmanager
async def verification_span(
    tracer: Tracer | None,
    verifier_name: str,
) -> AsyncIterator[None]:
    """Async ctx mgr emitting `verifier.{name}` span under VERIFICATION; no-op if tracer is None."""
    if tracer is None:
        yield
        return
    async with tracer.start_span(
        name=f"verifier.{verifier_name}",
        category=SpanCategory.VERIFICATION,
    ):
        yield
