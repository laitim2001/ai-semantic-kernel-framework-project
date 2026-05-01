"""
File: backend/src/agent_harness/_contracts/cache.py
Purpose: Single-source dataclass for prompt-cache policy (Cat 4 PromptCacheManager input).
Category: cross-category single-source contracts (per 17.md §1.1)
Scope: Phase 52 / Sprint 52.1

Description:
    CachePolicy expresses per-tenant + per-loop caching configuration.
    Cat 4 PromptCacheManager.get_cache_breakpoints() reads this to decide
    which CacheBreakpoint markers to attach (system / tools / memory layers).

    CacheBreakpoint itself lives in _contracts/chat.py:122 (51.1, owner Cat 5
    physical layer; 52.1 extended with Cat 4 logical metadata fields). This
    module deliberately does NOT redefine CacheBreakpoint to honour the
    single-source rule (17.md §1.1).

Key Components:
    - CachePolicy: 5 cache_* booleans + ttl_seconds + invalidate_on triggers

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §1.1
Related:
    - _contracts/chat.py CacheBreakpoint (extended in 52.1 Day 1)
    - 10-server-side-philosophy.md §原則 1 (multi-tenant isolation)

Created: 2026-05-01 (Sprint 52.1, Day 1)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 1) — define CachePolicy
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CachePolicy:
    """Caching configuration per (tenant_id, loop_session). Frozen for safe sharing."""

    enabled: bool = True
    """Master toggle. False = PromptCacheManager returns []."""

    cache_system_prompt: bool = True
    """Cache the system message (largest stable section, highest cache value)."""

    cache_tool_definitions: bool = True
    """Cache the serialised ToolSpec list (changes only when tools registry changes)."""

    cache_memory_layers: bool = True
    """Cache injected memory hint blocks (per Cat 3 layer; invalidate on memory write)."""

    cache_recent_turns: bool = False
    """Cache last N turns. Default False — recent turns mutate often, low hit rate."""

    ttl_seconds: int = 300
    """Default cache TTL. Anthropic ephemeral max ~5 min; OpenAI session-bound."""

    invalidate_on: list[str] = field(default_factory=list)
    """Trigger labels that force cache invalidation (e.g. ['memory_write', 'tool_registry_change'])."""
