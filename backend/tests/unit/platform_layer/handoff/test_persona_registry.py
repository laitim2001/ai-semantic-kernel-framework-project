"""
File: backend/tests/unit/platform_layer/handoff/test_persona_registry.py
Purpose: Unit tests for the Cat 11 HANDOFF persona registry (Sprint 57.68 A-3b)
Category: Tests
Created: 2026-06-02
Modified: 2026-06-02
"""

from __future__ import annotations

from platform_layer.handoff.persona_registry import (
    PERSONA_REGISTRY,
    resolve_persona,
)


def test_resolve_persona_known_returns_prompt() -> None:
    for agent in PERSONA_REGISTRY:
        prompt = resolve_persona(agent)
        assert prompt is not None
        assert isinstance(prompt, str)
        assert prompt.strip()


def test_resolve_persona_known_trims_whitespace() -> None:
    assert resolve_persona("  researcher  ") == PERSONA_REGISTRY["researcher"]


def test_resolve_persona_unknown_returns_none() -> None:
    assert resolve_persona("nonexistent-agent") is None


def test_resolve_persona_empty_returns_none() -> None:
    assert resolve_persona("") is None
    assert resolve_persona("   ") is None
