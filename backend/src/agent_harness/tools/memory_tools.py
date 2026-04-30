"""
File: backend/src/agent_harness/tools/memory_tools.py
Purpose: memory_search / memory_write ToolSpecs + real handlers (51.2 Day 4).
Category: 範疇 2 (Tool Layer hosting Cat 3 backed handlers)
Scope: Phase 51 / Sprint 51.1 (placeholder) + Sprint 51.2 Day 4 (real handlers)

Description:
    51.1 Day 4.3 introduced the placeholder ToolSpecs so the registry could
    list them consistently with 17.md §3.1. 51.2 Day 4 wires real handlers
    that route to MemoryRetrieval (search) and per-scope MemoryLayer.write
    (write).

    Tenant context: handlers read tenant_id / user_id / session_id from
    ToolCall.arguments. The agent loop is expected to inject these from
    the authenticated execution context before invoking the executor. LLMs
    do NOT control these fields directly (loop injection happens after the
    LLM produces the tool call). Phase 53.3 will replace this with proper
    ExecutionContext threading (CARRY-030 joins CARRY-023 RBAC work).

    Schema additions in 51.2:
    - memory_search: `time_scales` array (axis 2)
    - memory_write: `time_scale` + `confidence`

    Schemas no longer declare "placeholder" in tags.

Owner: 範疇 3 (Memory) — handlers route into Cat 3 layers; 範疇 2 (Tool Layer)
       owns the spec registration.

Modification History:
    - 2026-04-30 (Sprint 51.2 Day 4): replace memory_placeholder_handler
      with real factory functions (make_memory_search_handler /
      make_memory_write_handler); update schemas with time_scales /
      time_scale / confidence; drop "placeholder" tag.
    - 2026-04-30 (Sprint 51.1 Day 4.3): initial placeholder ToolSpecs.

Carry items:
    - CARRY-030 (new): replace argument-passed tenant context with
      ExecutionContext threading (Phase 53.3; joins CARRY-023).
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from agent_harness._contracts import (
    ConcurrencyPolicy,
    MemoryHint,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)
from agent_harness.memory._abc import MemoryLayer
from agent_harness.memory.retrieval import MemoryRetrieval

ToolHandler = Callable[[ToolCall], Awaitable[str]]


MEMORY_SEARCH_SPEC: ToolSpec = ToolSpec(
    name="memory_search",
    description=(
        "Search across 5-layer memory (system / tenant / role / user / session) "
        "with optional time_scale axis (short_term / long_term / semantic). "
        "Returns top-k MemoryHints ranked by relevance * confidence."
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
            "time_scales": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["short_term", "long_term", "semantic"],
                },
                "default": ["long_term"],
            },
            "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(read_only=True, idempotent=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("builtin", "memory"),
)

MEMORY_WRITE_SPEC: ToolSpec = ToolSpec(
    name="memory_write",
    description=(
        "Persist a memory entry into the specified scope and time_scale. "
        "system scope is read-only at runtime (rejected). short_term writes "
        "for tenant/role layers are rejected (use session layer)."
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
            "time_scale": {
                "type": "string",
                "enum": ["short_term", "long_term", "semantic"],
                "default": "long_term",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.5,
            },
        },
        "required": ["scope", "key", "content"],
    },
    annotations=ToolAnnotations(read_only=False, destructive=False, idempotent=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("builtin", "memory"),
)

MEMORY_TOOL_SPECS: tuple[ToolSpec, ...] = (MEMORY_SEARCH_SPEC, MEMORY_WRITE_SPEC)


# ---------------------------------------------------------------------------
# Placeholder handler (kept as fallback for dev/test environments without DB)
# ---------------------------------------------------------------------------
async def memory_placeholder_handler(call: ToolCall) -> str:
    """Fallback handler used when no MemoryRetrieval / MemoryLayer is wired.

    Sprint 51.2 keeps this for backward compatibility with code paths that
    construct register_builtin_tools without injecting Cat 3 dependencies
    (e.g., dev startup before DB session_factory is ready). Production
    deployment must wire real handlers via make_memory_search_handler /
    make_memory_write_handler.
    """
    return json.dumps(
        {
            "ok": False,
            "error": (
                f"memory tool '{call.name}' has no Cat 3 backend wired; "
                "construct register_builtin_tools(memory_retrieval=..., "
                "memory_layers=...) to enable."
            ),
        }
    )


# ---------------------------------------------------------------------------
# Real handler factories (51.2 Day 4)
# ---------------------------------------------------------------------------
def make_memory_search_handler(retrieval: MemoryRetrieval) -> ToolHandler:
    """Factory: handler that routes memory_search ToolCall -> MemoryRetrieval.

    Reads tenant_id / user_id / session_id from ToolCall.arguments (loop
    injects from authenticated execution context). Returns JSON-serialized
    list of MemoryHint dicts.
    """

    async def handler(call: ToolCall) -> str:
        args: dict[str, Any] = dict(call.arguments)
        query = str(args.get("query", "")).strip()
        if not query:
            return json.dumps({"ok": False, "error": "query is required"})

        tenant_id = _parse_uuid(args.get("tenant_id"))
        user_id = _parse_uuid(args.get("user_id"))
        session_id = _parse_uuid(args.get("session_id"))

        scopes_raw = args.get("scopes") or ["session", "user", "tenant"]
        time_scales_raw = args.get("time_scales") or ["long_term"]
        top_k = int(args.get("top_k", 5))

        hints = await retrieval.search(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            scopes=tuple(scopes_raw),
            time_scales=tuple(time_scales_raw),
            top_k=top_k,
        )

        return json.dumps(
            {"ok": True, "hints": [_hint_to_dict(h) for h in hints]}
        )

    return handler


def make_memory_write_handler(layers: dict[str, MemoryLayer]) -> ToolHandler:
    """Factory: handler that routes memory_write ToolCall -> MemoryLayer.write.

    scope=system -> rejected (system layer read-only at runtime).
    Reads tenant_id / user_id / session_id from arguments (loop-injected).
    """

    async def handler(call: ToolCall) -> str:
        args: dict[str, Any] = dict(call.arguments)
        scope = str(args.get("scope", "")).strip()
        content = str(args.get("content", "")).strip()
        time_scale = args.get("time_scale", "long_term")
        confidence = float(args.get("confidence", 0.5))

        if scope == "system":
            return json.dumps(
                {
                    "ok": False,
                    "error": "system scope is read-only; use admin migration",
                }
            )

        layer = layers.get(scope)
        if layer is None:
            return json.dumps(
                {"ok": False, "error": f"scope '{scope}' has no layer wired"}
            )

        tenant_id = _parse_uuid(args.get("tenant_id"))
        # session layer overloads user_id slot for session_id
        if scope == "session":
            slot_user_id = _parse_uuid(args.get("session_id"))
        else:
            slot_user_id = _parse_uuid(args.get("user_id"))

        try:
            entry_id = await layer.write(
                content=content,
                tenant_id=tenant_id,
                user_id=slot_user_id,
                time_scale=time_scale,
                confidence=confidence,
            )
        except (ValueError, NotImplementedError) as exc:
            return json.dumps({"ok": False, "error": str(exc)})

        return json.dumps({"ok": True, "entry_id": str(entry_id), "scope": scope})

    return handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _hint_to_dict(hint: MemoryHint) -> dict[str, Any]:
    """Serialize MemoryHint dataclass into a JSON-friendly dict."""
    return {
        "hint_id": str(hint.hint_id),
        "layer": hint.layer,
        "time_scale": hint.time_scale,
        "summary": hint.summary,
        "confidence": hint.confidence,
        "relevance_score": hint.relevance_score,
        "full_content_pointer": hint.full_content_pointer,
        "timestamp": hint.timestamp.isoformat(),
        "last_verified_at": (
            hint.last_verified_at.isoformat() if hint.last_verified_at else None
        ),
        "verify_before_use": hint.verify_before_use,
        "source_tool_call_id": hint.source_tool_call_id,
        "expires_at": hint.expires_at.isoformat() if hint.expires_at else None,
        "tenant_id": str(hint.tenant_id) if hint.tenant_id else None,
    }


__all__ = [
    "MEMORY_SEARCH_SPEC",
    "MEMORY_WRITE_SPEC",
    "MEMORY_TOOL_SPECS",
    "make_memory_search_handler",
    "make_memory_write_handler",
    "memory_placeholder_handler",
]
