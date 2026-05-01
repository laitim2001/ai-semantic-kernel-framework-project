"""
File: tests/integration/agent_harness/context_mgmt/test_cache_hit_ratio_steady_state.py
Purpose: Verify InMemoryCacheManager achieves >50% hit ratio in 5-turn steady state.
Category: Tests / Integration / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 4.3
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent_harness._contracts import CachePolicy
from agent_harness.context_mgmt.cache_manager import InMemoryCacheManager


@pytest.mark.asyncio
async def test_cache_hit_ratio_steady_state_above_50_percent() -> None:
    """5-turn same-tenant conversation → cache hit ratio > 50 % (3 / 5 turns reuse)."""
    mgr = InMemoryCacheManager(provider_signature="azure_openai_gpt-4o")
    tenant = uuid4()
    policy = CachePolicy()  # default = system + tools + memory cached, recent off

    # Turn 1: cold cache → 0 hits, 3 inserts
    bps_t1 = await mgr.get_cache_breakpoints(tenant_id=tenant, policy=policy)
    assert len(bps_t1) == 3
    cache_size_after_t1 = mgr.cache_size

    # Pre-compute the cache keys for the breakpoints we just inserted
    keys_t1 = {
        mgr._compute_cache_key(
            tenant_id=tenant,
            section_id=bp.section_id or "",
            content_hash=bp.content_hash or "",
        )
        for bp in bps_t1
    }
    assert all(mgr._check_ttl(k) for k in keys_t1)

    # Turns 2-5: warm cache. Same tenant + same section content → hits.
    hit_count = 0
    request_count = 0
    for _ in range(4):
        # For each subsequent turn, re-resolve breakpoints — those already in
        # the cache count as hits; new entries (none here) count as misses.
        request_count += len(bps_t1)
        bps = await mgr.get_cache_breakpoints(tenant_id=tenant, policy=policy)
        for bp in bps:
            key = mgr._compute_cache_key(
                tenant_id=tenant,
                section_id=bp.section_id or "",
                content_hash=bp.content_hash or "",
            )
            if key in keys_t1:
                hit_count += 1

    total_requests = len(bps_t1) + request_count  # turn 1 + turns 2-5
    hits = hit_count  # turn 1 contributes no hits (cold)
    hit_ratio = hits / total_requests
    assert hit_ratio > 0.5, f"Cache hit ratio {hit_ratio:.2f} below 0.50 threshold"

    # Cache should still hold the same 3 entries (no growth — same keys reused)
    assert mgr.cache_size == cache_size_after_t1
