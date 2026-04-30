"""
File: backend/tests/e2e/test_lead_then_verify_workflow.py
Purpose: e2e demo of the lead-then-verify workflow per Cat 3 design.
Category: Tests / e2e / Cat 3 demo
Scope: Phase 51 / Sprint 51.2 Day 5.2

Description:
    Demonstrates the "memory hint as lead, not fact" pattern. A stale user
    memory hint is fetched via memory_search; the caller (simulated agent)
    sees verify_before_use=True and confidence drift, then either:
    1. Calls a verification tool (mock CRM here) and updates memory when
       the live result diverges from the stored hint, or
    2. Confirms the hint is still consistent and proceeds without rewrite.

    51.2 simplification: this exercises the pattern at handler level (no
    full agent loop). End-to-end via UnifiedChat-V2 lands as part of the
    Phase 52+ integration once PromptBuilder injects MemoryHints into the
    system prompt.

Created: 2026-04-30 (Sprint 51.2 Day 5.2)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

import pytest

from agent_harness._contracts import MemoryHint, ToolCall, TraceContext
from agent_harness.memory._abc import MemoryLayer, MemoryScope
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.tools.memory_tools import (
    make_memory_search_handler,
    make_memory_write_handler,
)


class _UserLayerStub(MemoryLayer):
    """User layer stub that supports seeded hints + records writes."""

    scope = MemoryScope.USER

    def __init__(self) -> None:
        self._store: list[MemoryHint] = []

    def seed(self, hint: MemoryHint) -> None:
        self._store.append(hint)

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
        new_id = uuid4()
        self._store.append(
            MemoryHint(
                hint_id=new_id,
                layer="user",
                time_scale=time_scale,
                summary=content,
                confidence=confidence,
                relevance_score=1.0,
                full_content_pointer=f"user:{new_id}",
                timestamp=datetime.now(timezone.utc),
                last_verified_at=datetime.now(timezone.utc),
                verify_before_use=False,
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


async def _mock_crm_search_customer(*, customer_id: str) -> dict[str, object]:
    """Test double for the mock_crm_search_customer business tool."""
    return {"customer_id": customer_id, "preference": "concise summaries"}


@pytest.mark.asyncio
async def test_agent_uses_stale_hint_then_verifies_with_mock_tool() -> None:
    """When stored hint says X but live data says Y, agent rewrites memory."""
    user_layer = _UserLayerStub()
    tenant = uuid4()
    user = uuid4()

    stale_id = uuid4()
    user_layer.seed(
        MemoryHint(
            hint_id=stale_id,
            layer="user",
            time_scale="long_term",
            summary="customer prefers detailed breakdowns",
            confidence=0.6,
            relevance_score=0.6,
            full_content_pointer=f"user:{stale_id}",
            timestamp=datetime.now(timezone.utc) - timedelta(days=30),
            last_verified_at=datetime.now(timezone.utc) - timedelta(days=30),
            verify_before_use=True,
            tenant_id=tenant,
        )
    )

    retrieval = MemoryRetrieval({"user": user_layer})
    search_handler = make_memory_search_handler(retrieval)
    write_handler = make_memory_write_handler({"user": user_layer})

    search_resp = json.loads(
        await search_handler(
            ToolCall(
                id="s1",
                name="memory_search",
                arguments={
                    "query": "customer",
                    "scopes": ["user"],
                    "tenant_id": str(tenant),
                    "user_id": str(user),
                },
            )
        )
    )
    assert search_resp["ok"] is True
    assert len(search_resp["hints"]) == 1
    hint = search_resp["hints"][0]
    assert hint["verify_before_use"] is True

    crm_result = await _mock_crm_search_customer(customer_id="acme-001")
    drifted = crm_result["preference"] != "detailed breakdowns"
    assert drifted is True

    write_resp = json.loads(
        await write_handler(
            ToolCall(
                id="w1",
                name="memory_write",
                arguments={
                    "scope": "user",
                    "key": "preference",
                    "content": f"customer prefers {crm_result['preference']}",
                    "confidence": 0.9,
                    "tenant_id": str(tenant),
                    "user_id": str(user),
                },
            )
        )
    )
    assert write_resp["ok"] is True

    requery = json.loads(
        await search_handler(
            ToolCall(
                id="s2",
                name="memory_search",
                arguments={
                    "query": "concise",
                    "scopes": ["user"],
                    "tenant_id": str(tenant),
                    "user_id": str(user),
                },
            )
        )
    )
    assert requery["ok"] is True
    assert len(requery["hints"]) == 1
    assert "concise" in requery["hints"][0]["summary"].lower()
    assert requery["hints"][0]["verify_before_use"] is False


@pytest.mark.asyncio
async def test_lead_then_verify_consistent_path() -> None:
    """When live data matches stored hint, agent proceeds without rewrite."""
    user_layer = _UserLayerStub()
    tenant = uuid4()
    user = uuid4()

    fresh_id = uuid4()
    user_layer.seed(
        MemoryHint(
            hint_id=fresh_id,
            layer="user",
            time_scale="long_term",
            summary="customer prefers concise summaries",
            confidence=0.85,
            relevance_score=0.85,
            full_content_pointer=f"user:{fresh_id}",
            timestamp=datetime.now(timezone.utc),
            last_verified_at=datetime.now(timezone.utc) - timedelta(days=2),
            verify_before_use=True,
            tenant_id=tenant,
        )
    )

    retrieval = MemoryRetrieval({"user": user_layer})
    search_handler = make_memory_search_handler(retrieval)

    search_resp = json.loads(
        await search_handler(
            ToolCall(
                id="s3",
                name="memory_search",
                arguments={
                    "query": "concise",
                    "scopes": ["user"],
                    "tenant_id": str(tenant),
                    "user_id": str(user),
                },
            )
        )
    )
    assert len(search_resp["hints"]) == 1

    crm_result = await _mock_crm_search_customer(customer_id="acme-002")
    consistent = (
        crm_result["preference"] in search_resp["hints"][0]["summary"].lower()
    )
    assert consistent is True

    assert len(user_layer._store) == 1
