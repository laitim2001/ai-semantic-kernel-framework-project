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

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 1) — PromptCacheManager ABC with get_cache_breakpoints + invalidate
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from agent_harness._contracts import CacheBreakpoint, CachePolicy


class PromptCacheManager(ABC):
    """Decides cache breakpoint placement + handles tenant-scoped invalidation."""

    @abstractmethod
    async def get_cache_breakpoints(
        self,
        *,
        tenant_id: UUID,
        policy: CachePolicy,
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
    ) -> None:
        """Drop all cache entries for a tenant.

        Called by Cat 3 (memory write hook) and Cat 2 (tool registry change hook).
        MUST be tenant-scoped: invalidate(tenant_a) MUST NOT affect tenant_b.
        """
        ...
