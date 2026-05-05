"""
File: backend/src/api/v1/chat/_verifier_factory.py
Purpose: Build default Cat 10 VerifierRegistry for chat router 2-mode wiring per AD-Cat10-Wire-1.
Category: API / Cat 10 wiring (delegates to agent_harness.verification owner per 17.md §Cat 10)
Scope: Sprint 55.5 (Audit Cycle Mini-Sprint #3 narrow — Group D backend)

Description:
    Two-piece public API for chat router Cat 10 wiring:

    1. build_default_verifier_registry() — constructs a VerifierRegistry
       containing one no-op RulesBasedVerifier(rules=[]). No-op rules emit
       VerificationPassed events without blocking; production callers can
       extend the registry with additional verifiers (LLMJudgeVerifier
       template) before passing into run_with_verification.

    2. select_verifier_registry(mode) — maps the Settings.chat_verification_mode
       Literal to the verifier_registry kwarg expected by run_with_verification:

       - "disabled" → None (wrapper transparently delegates to loop.run() per
                      correction_loop.py:99-106 — backwards-compat preserved
                      byte-for-byte;existing 54.1 behavior)
       - "enabled"  → populated registry (wrapper runs verifiers + self-correction
                      loop max 2 attempts per 54.1 spec)

    Option E 2-mode design (post-D4+D5 drift response):
    real `run_with_verification` signature uses verifier_registry (registry-based,
    not single verifier) + no `mode` parameter. The wrapper's existing empty-registry
    short-circuit makes 2-mode dispatch sufficient — no shadow mode needed; no
    17.md §Cat 10 contract change required.

Owner: api/v1/chat (delegates to agent_harness.verification single-source per 17.md)

Created: 2026-05-05 (Sprint 55.5 Day 1)
Last Modified: 2026-05-05

Modification History (newest-first):
    - 2026-05-05: Sprint 55.5 — initial Cat 10 chat router 2-mode wire (AD-Cat10-Wire-1)

Related:
    - api/v1/chat/router.py — `_stream_loop_events()` L197 consumer
    - agent_harness/verification/correction_loop.py — run_with_verification (54.1)
    - agent_harness/verification/registry.py — VerifierRegistry (54.1)
    - core/config/__init__.py — Settings.chat_verification_mode field
    - sprint-55-5-plan.md (phase-55-production)
"""

from __future__ import annotations

from typing import Literal

from agent_harness.verification import RulesBasedVerifier, VerifierRegistry

VerificationMode = Literal["disabled", "enabled"]


def build_default_verifier_registry() -> VerifierRegistry:
    """Construct a VerifierRegistry containing a single no-op RulesBasedVerifier.

    No-op rules (empty list) emit VerificationPassed events on every invocation
    without blocking the agent loop — this is intentional for 'enabled' mode's
    safe-rollout default. Production callers may extend the registry with
    additional verifiers (e.g. LLMJudgeVerifier from 54.1 templates) before
    passing into run_with_verification.
    """
    registry = VerifierRegistry()
    registry.register(RulesBasedVerifier(rules=[]))
    return registry


def select_verifier_registry(mode: VerificationMode) -> VerifierRegistry | None:
    """Map chat_verification_mode setting to the verifier_registry kwarg.

    Args:
        mode: One of "disabled" or "enabled" (validated by pydantic Literal
              at Settings construction time; invalid values rejected before
              reaching this function).

    Returns:
        - None when mode == "disabled" — wrapper transparently delegates to
          loop.run() per correction_loop.py:99-106 (54.1 backwards-compat).
        - Populated VerifierRegistry when mode == "enabled" — wrapper runs
          verifiers + self-correction loop (max 2 attempts).
    """
    if mode == "enabled":
        return build_default_verifier_registry()
    return None


__all__ = [
    "VerificationMode",
    "build_default_verifier_registry",
    "select_verifier_registry",
]
