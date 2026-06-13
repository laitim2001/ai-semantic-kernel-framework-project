"""
File: backend/tests/unit/agent_harness/skills/test_skills_overlay.py
Purpose: Unit tests for SkillRegistry.with_overlay (per-tenant overlay primitive; 57.114 US-1).
Category: Tests / Unit (範疇 5 Prompt Construction — Skills System)
Created: 2026-06-13 (Sprint 57.114)

Pure tests (no DB): override-by-name, add-new, empty-equals-base, no-mutation of
the base / bundled singleton, deterministic order.
"""

from __future__ import annotations

from agent_harness.skills import Skill, SkillRegistry, get_default_skill_registry


def _reg(*skills: Skill) -> SkillRegistry:
    registry = SkillRegistry()
    for skill in skills:
        registry.register(skill)
    return registry


def _get(registry: SkillRegistry, name: str) -> Skill:
    skill = registry.get(name)
    assert skill is not None
    return skill


def test_overlay_adds_new_names() -> None:
    base = _reg(Skill("a", "da", "ia"))
    out = base.with_overlay([Skill("b", "db", "ib")])
    assert {s.name for s in out.list()} == {"a", "b"}
    assert _get(out, "a").instructions == "ia"
    assert _get(out, "b").instructions == "ib"


def test_overlay_same_name_overrides() -> None:
    base = _reg(Skill("a", "da", "bundled-body"))
    out = base.with_overlay([Skill("a", "da2", "tenant-body")])
    assert len(out.list()) == 1
    assert _get(out, "a").instructions == "tenant-body"
    assert _get(out, "a").description == "da2"


def test_overlay_empty_equals_base() -> None:
    base = _reg(Skill("a", "da", "ia"), Skill("b", "db", "ib"))
    out = base.with_overlay([])
    assert {s.name for s in out.list()} == {"a", "b"}


def test_overlay_does_not_mutate_base_or_singleton() -> None:
    bundled = get_default_skill_registry()
    before = {s.name for s in bundled.list()}
    overlaid = bundled.with_overlay([Skill("tenant-only", "d", "i")])
    after = {s.name for s in bundled.list()}
    assert before == after  # singleton unchanged
    assert "tenant-only" not in before
    assert "tenant-only" in {s.name for s in overlaid.list()}


def test_overlay_order_bundled_first_then_new() -> None:
    base = _reg(Skill("a", "d", "i"), Skill("b", "d", "i"))
    out = base.with_overlay([Skill("c", "d", "i")])
    assert [s.name for s in out.list()] == ["a", "b", "c"]
