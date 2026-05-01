"""
File: tests/unit/agent_harness/context_mgmt/test_cache_manager.py
Purpose: Unit tests for InMemoryCacheManager (impl: cache_manager.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 4.2

8 tests (4 red-team for tenant isolation):
  - test_set_and_get_breakpoints
  - test_ttl_expiry
  - test_invalidate_by_tenant
  - 🛡️ test_cross_tenant_same_content_no_leak           (red-team 1)
  - 🛡️ test_invalidate_isolation                        (red-team 2)
  - 🛡️ test_cache_key_includes_tenant_id_first          (red-team 3)
  - 🛡️ test_provider_signature_isolation                (red-team 4)
  - test_default_cache_policy_5_booleans

Multi-tenant safety: any red-team test failing = sprint blocker.
"""

from __future__ import annotations

import hashlib
import time
from uuid import uuid4

import pytest

from agent_harness._contracts import CachePolicy
from agent_harness.context_mgmt.cache_manager import InMemoryCacheManager


@pytest.mark.asyncio
async def test_set_and_get_breakpoints() -> None:
    """Default policy emits 3 breakpoints (system + tools + memory); cache populated."""
    mgr = InMemoryCacheManager()
    tenant = uuid4()
    policy = CachePolicy()  # all defaults

    bps = await mgr.get_cache_breakpoints(tenant_id=tenant, policy=policy)

    section_ids = {bp.section_id for bp in bps}
    assert section_ids == {"system_prompt", "tool_definitions", "memory_layers"}
    # cache_recent_turns default False → no recent_turns breakpoint
    assert "recent_turns" not in section_ids
    # Cache should have those 3 entries registered
    assert mgr.cache_size == 3
    # has_cached helper finds them
    for sid in ("system_prompt", "tool_definitions", "memory_layers"):
        assert mgr.has_cached(tenant_id=tenant, section_id=sid)


@pytest.mark.asyncio
async def test_ttl_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    """After ttl_seconds elapses, entries expire on next access (lazy TTL)."""
    mgr = InMemoryCacheManager()
    tenant = uuid4()
    policy = CachePolicy(ttl_seconds=10)

    base_time = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: base_time)
    await mgr.get_cache_breakpoints(tenant_id=tenant, policy=policy)
    assert mgr.cache_size == 3

    # Fast-forward past TTL
    monkeypatch.setattr(time, "monotonic", lambda: base_time + 11)
    assert mgr.cache_size == 0
    assert not mgr.has_cached(tenant_id=tenant, section_id="system_prompt")


@pytest.mark.asyncio
async def test_invalidate_by_tenant() -> None:
    """invalidate(tenant) removes that tenant's entries."""
    mgr = InMemoryCacheManager()
    tenant = uuid4()

    await mgr.get_cache_breakpoints(tenant_id=tenant, policy=CachePolicy())
    assert mgr.cache_size == 3

    await mgr.invalidate(tenant_id=tenant, reason="memory_write")
    assert mgr.cache_size == 0
    assert not mgr.has_cached(tenant_id=tenant, section_id="system_prompt")


# ============================================================================
# 🛡️ Red-team tests (4 total) — tenant isolation. Any failure = sprint blocker.
# ============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_same_content_no_leak() -> None:
    """🛡️ red-team 1: same section_id+content_hash for different tenants → DIFFERENT keys."""
    mgr = InMemoryCacheManager()
    tenant_a = uuid4()
    tenant_b = uuid4()

    # Manually compute keys with the same section/content for both tenants
    key_a = mgr._compute_cache_key(
        tenant_id=tenant_a,
        section_id="system_prompt",
        content_hash="hash123",
    )
    key_b = mgr._compute_cache_key(
        tenant_id=tenant_b,
        section_id="system_prompt",
        content_hash="hash123",
    )
    assert (
        key_a != key_b
    ), "Cross-tenant cache key collision detected — multi-tenant isolation broken!"


@pytest.mark.asyncio
async def test_invalidate_isolation() -> None:
    """🛡️ red-team 2: invalidate(tenant_a) MUST NOT affect tenant_b entries."""
    mgr = InMemoryCacheManager()
    tenant_a = uuid4()
    tenant_b = uuid4()

    await mgr.get_cache_breakpoints(tenant_id=tenant_a, policy=CachePolicy())
    await mgr.get_cache_breakpoints(tenant_id=tenant_b, policy=CachePolicy())
    assert mgr.cache_size == 6  # 3 each

    await mgr.invalidate(tenant_id=tenant_a, reason="memory_write")
    assert mgr.cache_size == 3
    assert not mgr.has_cached(tenant_id=tenant_a, section_id="system_prompt")
    # tenant_b entries must remain
    assert mgr.has_cached(tenant_id=tenant_b, section_id="system_prompt")
    assert mgr.has_cached(tenant_id=tenant_b, section_id="tool_definitions")
    assert mgr.has_cached(tenant_id=tenant_b, section_id="memory_layers")


@pytest.mark.asyncio
async def test_cache_key_includes_tenant_id_first() -> None:
    """🛡️ red-team 3: tenant_id MUST be the first component of the cache key hash input."""
    mgr = InMemoryCacheManager(provider_signature="azure_openai_gpt-4o")
    tenant = uuid4()

    actual_key = mgr._compute_cache_key(
        tenant_id=tenant,
        section_id="system_prompt",
        content_hash="abc",
    )

    expected_input = f"{tenant}:system_prompt:abc:azure_openai_gpt-4o"
    expected_key = hashlib.sha256(expected_input.encode("utf-8")).hexdigest()
    assert (
        actual_key == expected_key
    ), "Cache key formula deviated from `tenant_id:section_id:content_hash:provider` order"


@pytest.mark.asyncio
async def test_provider_signature_isolation() -> None:
    """🛡️ red-team 4: same tenant + content but different provider_signature → DIFFERENT keys."""
    mgr_azure = InMemoryCacheManager(provider_signature="azure_openai_gpt-4o")
    mgr_anthropic = InMemoryCacheManager(provider_signature="anthropic_claude-3.7")
    tenant = uuid4()

    key_azure = mgr_azure._compute_cache_key(
        tenant_id=tenant,
        section_id="system_prompt",
        content_hash="hash",
    )
    key_anthropic = mgr_anthropic._compute_cache_key(
        tenant_id=tenant,
        section_id="system_prompt",
        content_hash="hash",
    )
    assert (
        key_azure != key_anthropic
    ), "Provider signature is not partitioning the cache — cross-provider leak!"


# ============================================================================
# Policy default sanity
# ============================================================================


def test_default_cache_policy_5_booleans() -> None:
    """CachePolicy default: 4 booleans True (system/tools/memory enabled, recent_turns off)."""
    p = CachePolicy()
    assert p.enabled is True
    assert p.cache_system_prompt is True
    assert p.cache_tool_definitions is True
    assert p.cache_memory_layers is True
    assert p.cache_recent_turns is False
    assert p.ttl_seconds == 300
    assert p.invalidate_on == []
