"""
File: backend/src/platform_layer/handoff/persona_registry.py
Purpose: Minimal target_agent → system_prompt persona registry for Cat 11 HANDOFF.
Category: platform_layer (Cat 11 HANDOFF support — session-boot persona)
Scope: Phase 57 / Sprint 57.68 (A-3b backend slice, Stage 1)

Description:
    A THIN STAND-IN persona catalog mapping a HANDOFF target_agent string to a
    system prompt. When the agent loop emits a HANDOFF, the platform handoff
    service resolves the target agent here to decide whether the handoff is
    valid (unknown target → no session booted) and which persona the booted
    child session runs under (stored in session meta_data["agent_role"], later
    resolved by the chat handler).

    DESIGN-NOTE OPEN QUESTION (deliberately minimal — not the final design):
    a real platform needs a DB-backed, per-tenant agent catalog (custom
    personas, allowed tools, memory scopes, risk limits). This module is a
    hardcoded dict so the A-3b control-transfer vertical can be proven
    end-to-end without first building that catalog. A future sprint replaces
    this with the real catalog; resolve_persona() keeps its signature.

    Pure stdlib; LLM-provider-neutral (no SDK import).

Key Components:
    - PERSONA_REGISTRY: dict[str, str] — target_agent → system_prompt
    - resolve_persona(target_agent): str | None — None for unknown targets

Created: 2026-06-02 (Sprint 57.68 A-3b)
Last Modified: 2026-06-02

Modification History (newest-first):
    - 2026-06-02: Initial creation (Sprint 57.68 A-3b) — minimal handoff persona stand-in

Related:
    - platform_layer/handoff/service.py — consumer (HandoffService.boot_handoff)
    - 01-eleven-categories-spec.md §範疇 11 — HANDOFF control transfer
    - sprint-57-68-plan.md §3.3 — persona resolution (US-3)
"""

from __future__ import annotations

# === Persona registry ======================================================
# Why: A HANDOFF must resolve target_agent → a real system prompt so the booted
# child session runs as the target (not the demo persona = Potemkin). A small
# typed dict is the YAGNI stand-in pending a real per-tenant agent catalog
# (design-note open question). Names mirror the canonical example roles used
# across Cat 11 fixtures ("researcher" / "reviewer").
PERSONA_REGISTRY: dict[str, str] = {
    "researcher": (
        "You are a research specialist agent. Investigate the user's question "
        "thoroughly, gather supporting evidence, cite sources where possible, "
        "and produce a structured, well-organized findings summary."
    ),
    "reviewer": (
        "You are a critical review specialist agent. Carefully assess the work "
        "handed to you for correctness, completeness, and risks. Point out "
        "concrete issues and concrete improvements; be specific and honest."
    ),
    "planner": (
        "You are a planning specialist agent. Break the user's goal into a "
        "clear, ordered set of verifiable steps, identify dependencies and "
        "risks, and state the success criteria for each step."
    ),
}


def resolve_persona(target_agent: str) -> str | None:
    """Resolve a HANDOFF target_agent to its system prompt.

    Args:
        target_agent: the target agent identifier carried by the HANDOFF
            (e.g. "researcher"). Whitespace-trimmed before lookup.

    Returns:
        The target agent's system prompt, or None when target_agent is empty /
        whitespace / not a known persona. Callers MUST treat None as an invalid
        handoff (no session booted).
    """
    key = (target_agent or "").strip()
    if not key:
        return None
    return PERSONA_REGISTRY.get(key)


__all__ = ["PERSONA_REGISTRY", "resolve_persona"]
