"""
File: backend/src/agent_harness/verification/registry.py
Purpose: VerifierRegistry — pluggable per-request collection of Verifiers.
Category: 範疇 10 (Verification Loops)
Scope: Sprint 54.1 US-1

Description:
    Per-request DI container holding a list of Verifier instances. Insertion
    order is preserved so callers can stack cheap rules-based verifiers
    before expensive LLM-judge verifiers (fail-fast on cheap path).

    Per AD-Test-1 (53.6 retrospective): NOT a module-level singleton. Each
    request constructs its own VerifierRegistry; this avoids the event-loop
    cache cascade bug that bit ServiceFactory in 53.6 Day 4.

Owner: 01-eleven-categories-spec.md §範疇 10

Created: 2026-05-04 (Sprint 54.1 Day 1)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.1 US-1) — per-request DI pattern
"""

from __future__ import annotations

from agent_harness.verification._abc import Verifier


class VerifierRegistry:
    """Per-request DI container for Verifiers. Insertion order preserved."""

    def __init__(self) -> None:
        self._verifiers: list[Verifier] = []

    def register(self, verifier: Verifier) -> None:
        """Append verifier to the registry (insertion order preserved)."""
        self._verifiers.append(verifier)

    def get_all(self) -> list[Verifier]:
        """Return a defensive copy of all registered verifiers in insertion order."""
        return list(self._verifiers)

    def clear(self) -> None:
        """Remove all registered verifiers (used by tests for isolation)."""
        self._verifiers.clear()

    def __len__(self) -> int:
        return len(self._verifiers)
