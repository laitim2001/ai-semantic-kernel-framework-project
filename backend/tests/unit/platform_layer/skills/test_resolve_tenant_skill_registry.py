"""
File: backend/tests/unit/platform_layer/skills/test_resolve_tenant_skill_registry.py
Purpose: resolve_tenant_skill_registry + _SkillRegistryCache unit tests (Sprint 57.114 / US-3).
Category: Tests / Unit (platform_layer.skills — Skills System per-tenant catalog)
Created: 2026-06-13 (Sprint 57.114)

Pure unit tests (no DB) — the service's list_skills is monkeypatched so the
resolver's overlay / fail-open / TTL-cache behavior can be tested in isolation;
the cache's injectable-clock TTL is tested against _SkillRegistryCache directly.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import platform_layer.skills.service as svc_mod
from agent_harness.skills import SkillRegistry, get_default_skill_registry
from platform_layer.skills.service import (
    _SkillRegistryCache,
    invalidate_tenant_skill_registry,
    reset_skill_registry_cache,
    resolve_tenant_skill_registry,
)


class _FakeRow:
    """Stand-in for a TenantSkill ORM row (the resolver only reads these 3 attrs)."""

    def __init__(self, name: str, description: str, instructions: str) -> None:
        self.name = name
        self.description = description
        self.instructions = instructions


def _names(registry: SkillRegistry) -> set[str]:
    return {s.name for s in registry.list()}


async def test_db_none_returns_bundled() -> None:
    reset_skill_registry_cache()
    reg = await resolve_tenant_skill_registry(None, uuid4())
    assert "code-review" in _names(reg)  # the system-bundled set


async def test_no_rows_equals_bundled(monkeypatch: Any) -> None:
    reset_skill_registry_cache()

    async def _empty(db: Any, *, tenant_id: Any) -> list[_FakeRow]:
        return []

    monkeypatch.setattr(svc_mod.tenant_skill_service, "list_skills", _empty)
    reg = await resolve_tenant_skill_registry(object(), uuid4())
    assert "code-review" in _names(reg)
    assert "summarize" in _names(reg)


async def test_overlay_present(monkeypatch: Any) -> None:
    reset_skill_registry_cache()

    async def _rows(db: Any, *, tenant_id: Any) -> list[_FakeRow]:
        return [_FakeRow("tenant-skill", "d", "tenant body")]

    monkeypatch.setattr(svc_mod.tenant_skill_service, "list_skills", _rows)
    reg = await resolve_tenant_skill_registry(object(), uuid4())
    assert "tenant-skill" in _names(reg)
    assert "code-review" in _names(reg)  # bundled still present


async def test_overlay_overrides_bundled(monkeypatch: Any) -> None:
    reset_skill_registry_cache()

    async def _rows(db: Any, *, tenant_id: Any) -> list[_FakeRow]:
        return [_FakeRow("code-review", "d", "TENANT OVERRIDE BODY")]

    monkeypatch.setattr(svc_mod.tenant_skill_service, "list_skills", _rows)
    reg = await resolve_tenant_skill_registry(object(), uuid4())
    cr = reg.get("code-review")
    assert cr is not None
    assert cr.instructions == "TENANT OVERRIDE BODY"


async def test_fail_open_on_error(monkeypatch: Any) -> None:
    reset_skill_registry_cache()

    async def _boom(db: Any, *, tenant_id: Any) -> list[_FakeRow]:
        raise RuntimeError("db down")

    monkeypatch.setattr(svc_mod.tenant_skill_service, "list_skills", _boom)
    reg = await resolve_tenant_skill_registry(object(), uuid4())
    assert "code-review" in _names(reg)  # fail-open to the bundled set


async def test_cache_hit_skips_db(monkeypatch: Any) -> None:
    reset_skill_registry_cache()
    tid = uuid4()
    calls = {"n": 0}

    async def _rows(db: Any, *, tenant_id: Any) -> list[_FakeRow]:
        calls["n"] += 1
        return [_FakeRow("cached-skill", "d", "b")]

    monkeypatch.setattr(svc_mod.tenant_skill_service, "list_skills", _rows)
    await resolve_tenant_skill_registry(object(), tid)
    await resolve_tenant_skill_registry(object(), tid)
    assert calls["n"] == 1  # second resolve served from cache


async def test_invalidate_forces_reload(monkeypatch: Any) -> None:
    reset_skill_registry_cache()
    tid = uuid4()
    calls = {"n": 0}

    async def _rows(db: Any, *, tenant_id: Any) -> list[_FakeRow]:
        calls["n"] += 1
        return []

    monkeypatch.setattr(svc_mod.tenant_skill_service, "list_skills", _rows)
    await resolve_tenant_skill_registry(object(), tid)
    invalidate_tenant_skill_registry(tid)
    await resolve_tenant_skill_registry(object(), tid)
    assert calls["n"] == 2  # invalidation forced a fresh DB read


def test_cache_ttl_injectable_clock() -> None:
    now = {"t": 1000.0}
    cache = _SkillRegistryCache(ttl_s=60.0, clock=lambda: now["t"])
    reg = get_default_skill_registry()
    tid = uuid4()

    cache.put(tid, reg)
    assert cache.get(tid) is reg  # within TTL
    now["t"] = 1061.0
    assert cache.get(tid) is None  # expired

    cache.put(tid, reg)
    cache.invalidate(tid)
    assert cache.get(tid) is None  # invalidated

    cache.put(tid, reg)
    cache.clear()
    assert cache.get(tid) is None  # cleared
