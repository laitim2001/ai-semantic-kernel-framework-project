"""
File: backend/src/agent_harness/verification/_obs.py
Purpose: Cat 10 → Cat 12 observability glue — verification-specific span wrapper.
Category: 範疇 10 (Verification) × 範疇 12 (Observability)
Scope: Sprint 54.2 US-5 (origin) / Sprint 55.3 (delegation refactor)

Description:
    Verification-specific ergonomic wrapper around the cross-cutting
    `category_span` primitive in `agent_harness.observability.helpers`.
    Direct callers (emit `verifier.{name}` span under SpanCategory.VERIFICATION):
    rules_based.py + llm_judge.py.
    Indirect users (D19 reuse-inner pattern; do NOT call this directly):
    cat9_fallback.py + cat9_mutator.py — they delegate verification work to
    an inner LLMJudgeVerifier whose `verify()` already emits the span; the
    wrappers intentionally avoid double-instrumentation. Sprint 55.5
    AD-Cat10-Obs-Cat9Wrappers validates + sentinel-tests this design.
    No-op when tracer is None.

    Sprint 55.3 (AD-Cat12-Helpers-1): the no-op + start_span boilerplate
    moved to `observability/helpers.category_span`; this file now delegates
    to keep the existing call signature stable while removing duplication
    with `business_domain/_obs.py`.

Modification History (newest-first):
    - 2026-05-05: Sprint 55.5 — clarify direct vs indirect users (D19 reuse-inner)
    - 2026-05-04: Sprint 55.3 — delegate to category_span (closes AD-Cat12-Helpers-1)
    - 2026-05-04: Initial creation (Sprint 54.2 US-5 / AD-Cat10-Obs-1)

Related:
    - observability/helpers.py — category_span primitive (single owner)
    - observability/_abc.py — Tracer ABC
    - _contracts/observability.py — SpanCategory.VERIFICATION
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from agent_harness._contracts import SpanCategory
from agent_harness.observability import Tracer, category_span


@contextlib.asynccontextmanager
async def verification_span(
    tracer: Tracer | None,
    verifier_name: str,
) -> AsyncIterator[None]:
    """Async ctx mgr emitting `verifier.{name}` span under VERIFICATION; no-op if tracer is None.

    Delegates to `category_span` (Sprint 55.3 / AD-Cat12-Helpers-1).
    """
    async with category_span(tracer, f"verifier.{verifier_name}", SpanCategory.VERIFICATION):
        yield
