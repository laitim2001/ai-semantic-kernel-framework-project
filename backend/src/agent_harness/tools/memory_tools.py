"""
File: backend/src/agent_harness/tools/memory_tools.py
Purpose: memory_search / memory_write placeholder ToolSpecs (51.1).
Category: 範疇 2 (Tool Layer; placeholders for Cat 3 Memory)
Scope: Phase 51 / Sprint 51.1 Day 4.3

Description:
    Cross-category tool placeholders so the registry can list them
    consistently with 17.md §3.1. Real handlers land in Sprint 51.2 when
    Cat 3 (Memory) ships its 5-layer store. 51.1 handler raises
    NotImplementedError so any accidental call fails loudly rather than
    silently no-op-ing.

    Both specs declared low-risk read/write at the spec level; per-tenant
    enforcement and MemoryHint integration land with 51.2 + 53.3.

Owner: 范疇 3 (Memory) — 51.2 fills behavior; 51.1 hosts placeholder ToolSpec only
Created: 2026-04-30 (Sprint 51.1 Day 4.3)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from agent_harness._contracts import (
    ConcurrencyPolicy,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)

ToolHandler = Callable[[ToolCall], Awaitable[str]]

MEMORY_SEARCH_SPEC: ToolSpec = ToolSpec(
    name="memory_search",
    description=(
        "Search across 5-layer memory (system / tenant / role / user / session) "
        "and return relevant entries. Sprint 51.2 wires real Cat 3 backend; "
        "51.1 raises NotImplementedError on call."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "scopes": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["system", "tenant", "role", "user", "session"],
                },
                "default": ["session", "user", "tenant"],
            },
            "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(read_only=True, idempotent=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("builtin", "memory", "placeholder"),
)

MEMORY_WRITE_SPEC: ToolSpec = ToolSpec(
    name="memory_write",
    description=(
        "Persist a memory entry into the specified scope. Sprint 51.2 wires "
        "real Cat 3 backend; 51.1 raises NotImplementedError on call."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["session", "user", "tenant", "role"],
                "description": "Target memory layer (system layer is read-only).",
            },
            "key": {"type": "string", "minLength": 1},
            "content": {"type": "string", "minLength": 1},
        },
        "required": ["scope", "key", "content"],
    },
    annotations=ToolAnnotations(read_only=False, destructive=False, idempotent=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("builtin", "memory", "placeholder"),
)

MEMORY_TOOL_SPECS: tuple[ToolSpec, ...] = (MEMORY_SEARCH_SPEC, MEMORY_WRITE_SPEC)


async def memory_placeholder_handler(call: ToolCall) -> str:
    raise NotImplementedError(
        f"memory tool '{call.name}' is a 51.1 placeholder; Sprint 51.2 wires Cat 3 backend"
    )
