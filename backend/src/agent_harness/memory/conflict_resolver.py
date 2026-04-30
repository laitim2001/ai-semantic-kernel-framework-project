"""
File: backend/src/agent_harness/memory/conflict_resolver.py
Purpose: 4-rule conflict resolution between competing MemoryHints.
Category: 範疇 3 (Memory) / Conflict resolution
Scope: Phase 51 / Sprint 51.2 Day 3

Description:
    When MemoryRetrieval returns multiple hints describing the same fact
    (potentially from different layers / time scales), this module picks
    one. Rules apply in order; the first decisive rule wins:

    Rule 1: Single hint with confidence >= 0.8 -> return it.
    Rule 2: Hints verified within last 7 days -> latest wins.
    Rule 3: Layer specificity (user > role > tenant > system; session
            takes top precedence as it is the most contextual).
            If unique top-priority -> return it.
    Rule 4: Still ambiguous -> raise RequiresHumanReviewError so the
            caller can route to HITL (Phase 53.3 wires `request_clarification`
            tool; 51.2 ships the exception only).

Owner: 01-eleven-categories-spec.md §範疇 3 (Memory) - 衝突解決規則
Single-source: 17.md §1.1 (MemoryHint)

Created: 2026-04-30 (Sprint 51.2 Day 3.2)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent_harness._contracts import MemoryHint

# Layer priority: higher value = more specific / preferred when tied.
# Session is the most immediate context (current conversation turn);
# user is durable per-user; role applies to a job function; tenant is
# org-wide; system is the broadest (least specific).
_LAYER_PRIORITY: dict[str, int] = {
    "session": 5,
    "user": 4,
    "role": 3,
    "tenant": 2,
    "system": 1,
}


class RequiresHumanReviewError(Exception):
    """Raised when conflict cannot be auto-resolved (Rule 4 fallback)."""


def resolve(hints: list[MemoryHint], *, now: datetime | None = None) -> MemoryHint:
    """Apply 4 rules in order; return the resolved hint.

    Args:
        hints: candidate hints (must be non-empty).
        now: optional override for "current time" (used in tests for
            deterministic last_verified_at comparisons). Default = utc now.

    Raises:
        ValueError: if hints is empty.
        RequiresHumanReviewError: if all 4 rules fail to disambiguate.
    """
    if not hints:
        raise ValueError("Cannot resolve empty hint list")
    if len(hints) == 1:
        return hints[0]

    # Rule 1: high-confidence wins iff exactly one hint clears 0.8
    high_conf = [h for h in hints if h.confidence >= 0.8]
    if len(high_conf) == 1:
        return high_conf[0]

    # Rule 2: freshly verified (within 7 days) - latest verified wins
    cutoff_now = now or datetime.now(timezone.utc)
    fresh = [
        h
        for h in hints
        if h.last_verified_at is not None
        and (cutoff_now - h.last_verified_at) < timedelta(days=7)
    ]
    if fresh:
        # max by last_verified_at; mypy needs the assert because filter
        # made it non-None but the type is still datetime | None
        return max(fresh, key=lambda h: h.last_verified_at or datetime.min.replace(tzinfo=timezone.utc))

    # Rule 3: layer specificity - unique top priority wins
    priorities = {_LAYER_PRIORITY.get(h.layer, 0) for h in hints}
    top_priority = max(priorities)
    top_hints = [h for h in hints if _LAYER_PRIORITY.get(h.layer, 0) == top_priority]
    if len(top_hints) == 1:
        return top_hints[0]

    # Rule 4: still tied - escalate to HITL
    raise RequiresHumanReviewError(
        f"Cannot auto-resolve {len(hints)} hints across layers "
        f"{[h.layer for h in hints]}; HITL review required."
    )


__all__ = ["resolve", "RequiresHumanReviewError"]
