"""
File: backend/tests/integration/memory/test_memory_tools_integration.py
Purpose: Integration tests — memory_search / memory_write via builtin registry.
Category: Tests / Cat 2 + Cat 3 integration
Scope: Phase 51 / Sprint 51.2 Day 4.5

Description:
    Verifies the full Day 4 wiring:
    1. register_builtin_tools(memory_retrieval=real, memory_layers=real)
       attaches real factory handlers (NOT memory_placeholder_handler).
    2. Real handlers route correctly into MemoryRetrieval.search() and
       MemoryLayer.write() with tenant context from arguments.
    3. system scope writes are rejected.
    4. time_scales filter passes through.

    Uses StubLayer (in-memory dict-backed) to avoid PG dependency in this
    integration suite. SessionLayer is the real in-memory implementation.
    Real DB-backed integration tests live in Day 5 e2e suite.

Created: 2026-04-30 (Sprint 51.2 Day 4.5)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

import pytest

from agent_harness._contracts import MemoryHint, ToolCall, TraceContext
from agent_harness.memory._abc import MemoryLayer, MemoryScope
from agent_harness.memory.layers.session_layer import SessionLayer
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.tools import register_builtin_tools
from agent_harness.tools.memory_tools import (
    make_memory_search_handler,
    make_memory_write_handler,
    memory_placeholder_handler,
)
from agent_harness.tools.registry import ToolRegistryImpl


class _StubUserLayer(MemoryLayer):
    """In-memory user layer stub (no PG; integration test only)."""

    scope = MemoryScope.USER

    def __init__(self) -> None:
        self._store: list[MemoryHint] = []
        self.write_args: list[dict[str, object]] = []

    async def read(
        self,
        *,
        query: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        time_scales: tuple[Literal["short_term", "long_term", "semantic"], ...] = (
            "long_term",
        ),
        max_hints: int = 10,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        if tenant_id is None or user_id is None:
            return []
        out: list[MemoryHint] = []
        for h in self._store:
            if h.tenant_id != tenant_id:
                continue
            if query.lower() in h.summary.lower():
                out.append(h)
            if len(out) >= max_hints:
                break
        return out

    async def write(
        self,
        *,
        content: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        time_scale: Literal["short_term", "long_term", "semantic"] = "long_term",
        confidence: float = 0.5,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        if tenant_id is None or user_id is None:
            raise ValueError("tenant_id and user_id required")
        new_id = uuid4()
        self.write_args.append(
            {
                "content": content,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "time_scale": time_scale,
                "confidence": confidence,
            }
        )
        self._store.append(
            MemoryHint(
                hint_id=new_id,
                layer="user",
                time_scale=time_scale,
                summary=content,
                confidence=confidence,
                relevance_score=1.0,
                full_content_pointer=f"stub:{new_id}",
                timestamp=datetime.now(timezone.utc),
                tenant_id=tenant_id,
            )
        )
        return new_id

    async def evict(self, **kwargs: object) -> None:
        return None

    async def resolve(self, hint: MemoryHint, **kwargs: object) -> str:
        for h in self._store:
            if h.hint_id == hint.hint_id:
                return h.summary
        return ""


@pytest.fixture
def wired_registry() -> tuple[ToolRegistryImpl, dict, _StubUserLayer, SessionLayer]:
    user_layer = _StubUserLayer()
    session_layer = SessionLayer()
    layers = {"user": user_layer, "session": session_layer}
    retrieval = MemoryRetrieval({"user": user_layer, "session": session_layer})

    registry = ToolRegistryImpl()
    handlers: dict = {}
    register_builtin_tools(
        registry,
        handlers,
        memory_retrieval=retrieval,
        memory_layers=layers,
    )
    return registry, handlers, user_layer, session_layer


@pytest.mark.asyncio
async def test_memory_handler_no_longer_raises_not_implemented(wired_registry) -> None:
    """Sanity: real handlers replace memory_placeholder_handler."""
    _, handlers, _, _ = wired_registry
    assert handlers["memory_search"] is not memory_placeholder_handler
    assert handlers["memory_write"] is not memory_placeholder_handler


@pytest.mark.asyncio
async def test_memory_write_then_search_via_registry(wired_registry) -> None:
    """End-to-end: write user fact, then search retrieves it."""
    _, handlers, user_layer, _ = wired_registry
    tenant = uuid4()
    user = uuid4()

    write_call = ToolCall(
        id="tc1",
        name="memory_write",
        arguments={
            "scope": "user",
            "key": "preference-1",
            "content": "user prefers detailed financial breakdowns",
            "time_scale": "long_term",
            "confidence": 0.9,
            "tenant_id": str(tenant),
            "user_id": str(user),
        },
    )
    write_resp = json.loads(await handlers["memory_write"](write_call))
    assert write_resp["ok"] is True
    assert write_resp["scope"] == "user"
    assert len(user_layer.write_args) == 1
    assert user_layer.write_args[0]["confidence"] == 0.9

    search_call = ToolCall(
        id="tc2",
        name="memory_search",
        arguments={
            "query": "detailed",
            "scopes": ["user"],
            "time_scales": ["long_term"],
            "tenant_id": str(tenant),
            "user_id": str(user),
        },
    )
    search_resp = json.loads(await handlers["memory_search"](search_call))
    assert search_resp["ok"] is True
    assert len(search_resp["hints"]) == 1
    assert search_resp["hints"][0]["layer"] == "user"
    assert search_resp["hints"][0]["time_scale"] == "long_term"


@pytest.mark.asyncio
async def test_memory_write_system_scope_rejected(wired_registry) -> None:
    _, handlers, _, _ = wired_registry
    call = ToolCall(
        id="tc3",
        name="memory_write",
        arguments={
            "scope": "system",
            "key": "policy-x",
            "content": "should be rejected",
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
        },
    )
    resp = json.loads(await handlers["memory_write"](call))
    assert resp["ok"] is False
    assert "read-only" in resp["error"].lower()


@pytest.mark.asyncio
async def test_memory_search_default_scopes_used_when_omitted(wired_registry) -> None:
    """Without explicit scopes, retrieval defaults to (session, user, tenant)."""
    _, handlers, user_layer, _ = wired_registry
    tenant = uuid4()
    user = uuid4()

    user_layer._store.append(
        MemoryHint(
            hint_id=uuid4(),
            layer="user",
            time_scale="long_term",
            summary="something seeded",
            confidence=0.7,
            relevance_score=1.0,
            full_content_pointer="stub",
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant,
        )
    )

    call = ToolCall(
        id="tc4",
        name="memory_search",
        arguments={
            "query": "seeded",
            "tenant_id": str(tenant),
            "user_id": str(user),
        },
    )
    resp = json.loads(await handlers["memory_search"](call))
    assert resp["ok"] is True
    assert len(resp["hints"]) == 1


@pytest.mark.asyncio
async def test_memory_search_top_k_limit(wired_registry) -> None:
    _, handlers, user_layer, _ = wired_registry
    tenant = uuid4()
    user = uuid4()

    for i in range(8):
        user_layer._store.append(
            MemoryHint(
                hint_id=uuid4(),
                layer="user",
                time_scale="long_term",
                summary=f"match-{i}",
                confidence=0.5,
                relevance_score=0.5,
                full_content_pointer="stub",
                timestamp=datetime.now(timezone.utc),
                tenant_id=tenant,
            )
        )

    call = ToolCall(
        id="tc5",
        name="memory_search",
        arguments={
            "query": "match",
            "scopes": ["user"],
            "top_k": 3,
            "tenant_id": str(tenant),
            "user_id": str(user),
        },
    )
    resp = json.loads(await handlers["memory_search"](call))
    assert resp["ok"] is True
    assert len(resp["hints"]) == 3


@pytest.mark.asyncio
async def test_memory_handlers_use_placeholder_when_no_backend() -> None:
    """register_builtin_tools without memory kwargs falls back to placeholder."""
    registry = ToolRegistryImpl()
    handlers: dict = {}
    register_builtin_tools(registry, handlers)
    assert handlers["memory_search"] is memory_placeholder_handler
    assert handlers["memory_write"] is memory_placeholder_handler


@pytest.mark.asyncio
async def test_search_factory_handles_missing_query() -> None:
    """Empty query yields error JSON, no exception."""
    layer = _StubUserLayer()
    retrieval = MemoryRetrieval({"user": layer})
    handler = make_memory_search_handler(retrieval)

    call = ToolCall(
        id="tc6",
        name="memory_search",
        arguments={"query": "", "tenant_id": str(uuid4())},
    )
    resp = json.loads(await handler(call))
    assert resp["ok"] is False
    assert "required" in resp["error"].lower()


@pytest.mark.asyncio
async def test_write_factory_handles_unknown_scope() -> None:
    """Scope without a wired layer -> error JSON."""
    handler = make_memory_write_handler({"user": _StubUserLayer()})

    call = ToolCall(
        id="tc7",
        name="memory_write",
        arguments={
            "scope": "role",
            "key": "k",
            "content": "x",
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
        },
    )
    resp = json.loads(await handler(call))
    assert resp["ok"] is False
    assert "no layer wired" in resp["error"]
