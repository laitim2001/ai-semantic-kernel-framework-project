"""
File: backend/src/agent_harness/context_mgmt/cache_manager.py
Purpose: PromptCacheManager ABC — prompt-cache breakpoint planning + invalidation.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1

Description:
    PromptCacheManager generates CacheBreakpoint markers that tell adapters
    where to insert provider-native cache_control directives (Anthropic
    cache_control, OpenAI prompt_cache_key, etc.). It also invalidates
    cached entries when memory writes / tool registry changes occur.

    Multi-tenant isolation: every cache key MUST start with tenant_id;
    cross-tenant lookups MUST miss. Concrete impl InMemoryCacheManager (Day 4)
    enforces this; 4 red-team tests guard against regression.

    LLM neutrality: PromptCacheManager itself does NOT call any LLM SDK.
    The provider_signature parameter (e.g. "azure_openai_gpt-5.4") lets
    concrete impls partition cache keys by adapter family.

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1

Related:
    - _contracts/cache.py CachePolicy (input)
    - _contracts/chat.py CacheBreakpoint (output, owner Cat 5 physical layer)
    - 10-server-side-philosophy.md §原則 1 (multi-tenant isolation)

Created: 2026-05-01 (Sprint 52.1, Day 1)
Last Modified: 2026-05-01 (Sprint 52.1 Day 4)

Modification History:
    - 2026-05-01: Add InMemoryCacheManager concrete impl with sha256 cache keys
      (tenant_id-first), TTL lazy expiry, tenant-scoped invalidation (Sprint 52.1 Day 4.1)
    - 2026-05-01: Initial creation (Sprint 52.1 Day 1) — PromptCacheManager ABC
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from agent_harness._contracts import CacheBreakpoint, CachePolicy, TraceContext


class PromptCacheManager(ABC):
    """Decides cache breakpoint placement + handles tenant-scoped invalidation."""

    @abstractmethod
    async def get_cache_breakpoints(
        self,
        *,
        tenant_id: UUID,
        policy: CachePolicy,
        trace_context: TraceContext | None = None,
    ) -> list[CacheBreakpoint]:
        """Return the list of CacheBreakpoint markers to attach to the prompt.

        Implementation reads policy 5 booleans (cache_system_prompt /
        cache_tool_definitions / cache_memory_layers / cache_recent_turns / enabled)
        and emits one CacheBreakpoint per enabled section, populating logical
        metadata (section_id / content_hash) for downstream invalidation.
        """
        ...

    @abstractmethod
    async def invalidate(
        self,
        *,
        tenant_id: UUID,
        reason: str,
        trace_context: TraceContext | None = None,
    ) -> None:
        """Drop all cache entries for a tenant.

        Called by Cat 3 (memory write hook) and Cat 2 (tool registry change hook).
        MUST be tenant-scoped: invalidate(tenant_a) MUST NOT affect tenant_b.
        """
        ...


# === InMemoryCacheManager (concrete) — Day 4.1 =============================
#
# Why dict-backed lazy TTL: the in-memory implementation is for unit / single-
# process scenarios (Phase 53.1+ will introduce Redis-backed). Lazy TTL keeps
# the data path simple — no background thread, no event loop pressure.
#
# Why a tenant index alongside the hashed key map: cache keys are sha256-hashed
# so tenant-prefix scans are impossible from the key alone. We maintain a
# parallel `dict[UUID, set[str]]` to enumerate keys for invalidate() without
# walking every entry; this also gives O(k) invalidation where k = entries
# of that tenant.
#
# Multi-tenant safety property (verified by 4 red-team tests in Day 4.2):
#   - Cache key is sha256(f"{tenant_id}:{section_id}:{content_hash}:{provider}")
#   - Same content for different tenants → different hashed key → no leak
#   - invalidate(A) only walks A's tenant index → does not touch B
#   - Different provider_signature → different keys (so multi-provider routing
#     can't accidentally serve another provider's response)


@dataclass
class _CacheEntry:
    breakpoint: CacheBreakpoint
    expires_at_monotonic: float  # time.monotonic()-based deadline; 0 means no TTL


def _sections_from_policy(policy: CachePolicy) -> list[tuple[str, int, str]]:
    """Map policy booleans to (section_id, position, breakpoint_type) tuples.

    Order matters — earlier sections are placed earlier in the prompt and
    have higher cache value (more stable content).
    """
    sections: list[tuple[str, int, str]] = []
    if policy.cache_system_prompt:
        sections.append(("system_prompt", 0, "persistent"))
    if policy.cache_tool_definitions:
        sections.append(("tool_definitions", 1, "persistent"))
    if policy.cache_memory_layers:
        sections.append(("memory_layers", 2, "ephemeral"))
    if policy.cache_recent_turns:
        sections.append(("recent_turns", 3, "ephemeral"))
    return sections


class InMemoryCacheManager(PromptCacheManager):
    """dict-backed PromptCacheManager. Single-process; Phase 53.1+ → Redis impl."""

    def __init__(self, *, provider_signature: str = "default") -> None:
        self._provider_signature = provider_signature
        self._cache: dict[str, _CacheEntry] = {}
        # tenant_id (str form, since UUID is hashable but we store as text in keys) → set of cache_key  # noqa: E501
        self._by_tenant: dict[str, set[str]] = {}

    # -- key formula (per Sprint 52.1 plan §1.4 + Day 4 red-team contract) --

    def _compute_cache_key(
        self,
        *,
        tenant_id: UUID,
        section_id: str,
        content_hash: str,
        provider_signature: str | None = None,
    ) -> str:
        """Tenant-id-first sha256 cache key.

        The tenant_id is the FIRST component of the hash input. This is a
        red-team-tested invariant: same content under different tenant_ids
        MUST produce different keys.
        """
        provider = provider_signature or self._provider_signature
        raw = f"{tenant_id}:{section_id}:{content_hash}:{provider}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _check_ttl(self, key: str) -> bool:
        """Lazy TTL: return True if key is still valid; drop and return False otherwise."""
        entry = self._cache.get(key)
        if entry is None:
            return False
        if entry.expires_at_monotonic and time.monotonic() >= entry.expires_at_monotonic:
            # expired; remove from both maps
            self._cache.pop(key, None)
            for keyset in self._by_tenant.values():
                keyset.discard(key)
            return False
        return True

    # -- public API --------------------------------------------------------

    async def get_cache_breakpoints(
        self,
        *,
        tenant_id: UUID,
        policy: CachePolicy,
        trace_context: TraceContext | None = None,
    ) -> list[CacheBreakpoint]:
        if not policy.enabled:
            return []

        breakpoints: list[CacheBreakpoint] = []
        ttl_deadline = time.monotonic() + policy.ttl_seconds if policy.ttl_seconds > 0 else 0.0

        for section_id, position, bp_type in _sections_from_policy(policy):
            # content_hash is filled by Cat 5 PromptBuilder (52.2). Day 4
            # uses a stable placeholder so the cache key is deterministic
            # for unit tests; production callers will supply real hashes
            # via PromptBuilder.invalidate_section() in 52.2.
            content_hash = f"<unknown:{section_id}>"

            cache_key = self._compute_cache_key(
                tenant_id=tenant_id,
                section_id=section_id,
                content_hash=content_hash,
            )

            bp = CacheBreakpoint(
                position=position,
                ttl_seconds=policy.ttl_seconds,
                breakpoint_type=bp_type,  # type: ignore[arg-type]
                section_id=section_id,
                content_hash=content_hash,
            )
            breakpoints.append(bp)

            # Register / refresh in cache map
            self._cache[cache_key] = _CacheEntry(
                breakpoint=bp,
                expires_at_monotonic=ttl_deadline,
            )
            self._by_tenant.setdefault(str(tenant_id), set()).add(cache_key)

        return breakpoints

    async def invalidate(
        self,
        *,
        tenant_id: UUID,
        reason: str,
        trace_context: TraceContext | None = None,
    ) -> None:
        keys = self._by_tenant.pop(str(tenant_id), set())
        for k in keys:
            self._cache.pop(k, None)

    # -- introspection helpers (testing) -----------------------------------

    def has_cached(
        self,
        *,
        tenant_id: UUID,
        section_id: str,
    ) -> bool:
        """Test-only helper: did the (tenant, section) entry survive?"""
        keys = self._by_tenant.get(str(tenant_id), set())
        for k in keys:
            if self._check_ttl(k) and self._cache[k].breakpoint.section_id == section_id:
                return True
        return False

    @property
    def cache_size(self) -> int:
        """Test-only helper: total live entries (after lazy TTL sweep on access)."""
        # Force-sweep expired before counting
        for k in list(self._cache.keys()):
            self._check_ttl(k)
        return len(self._cache)
