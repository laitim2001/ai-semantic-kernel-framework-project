"""
File: backend/tests/unit/agent_harness/guardrails/test_tool_guardrail.py
Purpose: Unit tests for ToolGuardrail (Cat 9 US-4 — 3-stage approval stages 1+2).
Category: Tests / 範疇 9
Scope: Phase 53.3 / Sprint 53.3 Day 3

Created: 2026-05-03 (Sprint 53.3 Day 3)

Modification History (newest-first):
    - 2026-05-05: Sprint 55.4 Day 2 — add Stage 2.3 session counter tests (AD-Cat9-5)
    - 2026-05-03: Initial creation (Sprint 53.3 Day 3 — US-4)
"""

from __future__ import annotations

from uuid import UUID

import pytest

from agent_harness._contracts import TraceContext
from agent_harness.guardrails import GuardrailAction, GuardrailType
from agent_harness.guardrails.tool import (
    Capability,
    CapabilityMatrix,
    PermissionRule,
    ToolGuardrail,
)

TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


def _make_matrix() -> CapabilityMatrix:
    """Compact matrix exercising all permission combinations."""
    return CapabilityMatrix(
        capability_to_tools={
            Capability.READ_KB: ["search_kb", "get_doc"],
            Capability.WRITE_KB: ["delete_doc"],
            Capability.EXECUTE_SHELL: ["run_command"],
            Capability.SEND_NOTIFICATION: ["send_email"],
        },
        permission_rules={
            "search_kb": PermissionRule(
                role_required="any",
                tenant_scope="own_only",
            ),
            "get_doc": PermissionRule(
                role_required="any",
                tenant_scope="any",
            ),
            "delete_doc": PermissionRule(
                role_required="admin",
                tenant_scope="own_only",
                requires_approval=True,
            ),
            "run_command": PermissionRule(
                role_required="ops",
                tenant_scope="own_only",
                requires_approval=True,
            ),
            "send_email": PermissionRule(
                role_required="any",
                tenant_scope="own_only",
                requires_approval=True,
            ),
        },
    )


def _trace_context(
    *,
    tenant_id: UUID | None = TENANT_A,
    role: str | None = None,
) -> TraceContext:
    baggage = {"role": role} if role else {}
    return TraceContext(
        trace_id="t1",
        span_id="s1",
        tenant_id=tenant_id,
        baggage=baggage,
    )


# === Construction + invariants =============================================


def test_guardrail_type_is_tool() -> None:
    assert ToolGuardrail.guardrail_type == GuardrailType.TOOL


# === Tool name extraction ==================================================


@pytest.mark.asyncio
async def test_extract_tool_name_from_str() -> None:
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="search_kb", trace_context=_trace_context())
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_extract_tool_name_from_dict() -> None:
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content={"name": "search_kb"}, trace_context=_trace_context())
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_extract_tool_name_from_object_with_name_attr() -> None:
    class _MockToolCall:
        name = "search_kb"

    g = ToolGuardrail(_make_matrix())
    r = await g.check(content=_MockToolCall(), trace_context=_trace_context())
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_unextractable_content_blocks() -> None:
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content=12345, trace_context=_trace_context())
    assert r.action == GuardrailAction.BLOCK
    assert "cannot extract" in (r.reason or "")


# === Unknown tool ==========================================================


@pytest.mark.asyncio
async def test_unknown_tool_blocks() -> None:
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="not_in_matrix", trace_context=_trace_context())
    assert r.action == GuardrailAction.BLOCK
    assert "unknown tool" in (r.reason or "")
    assert r.risk_level == "HIGH"


# === Stage 2.1 — Role check ===============================================


@pytest.mark.asyncio
async def test_role_required_admin_passes_for_admin() -> None:
    g = ToolGuardrail(_make_matrix())
    # delete_doc requires admin AND requires_approval — admin role gets ESCALATE
    r = await g.check(content="delete_doc", trace_context=_trace_context(role="admin"))
    assert r.action == GuardrailAction.ESCALATE


@pytest.mark.asyncio
async def test_role_required_admin_blocks_for_user() -> None:
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="delete_doc", trace_context=_trace_context(role="user"))
    assert r.action == GuardrailAction.BLOCK
    assert "role required" in (r.reason or "")


@pytest.mark.asyncio
async def test_role_required_ops_blocks_for_admin() -> None:
    """run_command requires ops; admin is not ops."""
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="run_command", trace_context=_trace_context(role="admin"))
    assert r.action == GuardrailAction.BLOCK


@pytest.mark.asyncio
async def test_role_any_passes_without_role() -> None:
    """any-role tools pass without trace_context.baggage['role']."""
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="search_kb", trace_context=_trace_context())
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_role_required_blocks_when_no_role_attributed() -> None:
    """role_required != 'any' but no role in baggage → BLOCK."""
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="delete_doc", trace_context=_trace_context())
    assert r.action == GuardrailAction.BLOCK


# === Stage 2.2 — Tenant scope =============================================


@pytest.mark.asyncio
async def test_tenant_scope_own_only_blocks_without_tenant_id() -> None:
    """own_only tool but trace_context has tenant_id=None → BLOCK."""
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="search_kb", trace_context=_trace_context(tenant_id=None))
    assert r.action == GuardrailAction.BLOCK
    assert "tenant scope=own_only" in (r.reason or "")


@pytest.mark.asyncio
async def test_tenant_scope_any_passes_without_tenant_id() -> None:
    """tenant_scope='any' (e.g. external API) does not require tenant_id."""
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="get_doc", trace_context=_trace_context(tenant_id=None))
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_tenant_scope_own_only_passes_with_tenant_id() -> None:
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="search_kb", trace_context=_trace_context(tenant_id=TENANT_A))
    assert r.action == GuardrailAction.PASS


# === Stage 3 — Explicit confirmation (ESCALATE) ===========================


@pytest.mark.asyncio
async def test_requires_approval_returns_escalate() -> None:
    """rule.requires_approval=True → ESCALATE (defer Stage 3 to 53.4)."""
    g = ToolGuardrail(_make_matrix())
    # send_email: any role + requires_approval
    r = await g.check(content="send_email", trace_context=_trace_context())
    assert r.action == GuardrailAction.ESCALATE
    assert r.risk_level == "MEDIUM"
    assert "requires approval" in (r.reason or "")


# === Multi-tenant isolation ===============================================


@pytest.mark.asyncio
async def test_multitenant_tenant_a_admin_cannot_affect_tenant_b() -> None:
    """Tenant A admin requesting delete_doc with tenant B in trace context.
    The role + own_only checks pass (admin role + tenant B set), so guardrail
    returns ESCALATE. The actual cross-tenant data access is enforced at
    the DB layer (per multi-tenant-data.md), NOT at this guardrail.
    This test documents the responsibility split.
    """
    g = ToolGuardrail(_make_matrix())
    r = await g.check(
        content="delete_doc",
        trace_context=_trace_context(tenant_id=TENANT_B, role="admin"),
    )
    # Guardrail returns ESCALATE — DB layer (RLS / app filter) enforces
    # data isolation. The guardrail's job is permission-checking, not
    # data-isolation.
    assert r.action == GuardrailAction.ESCALATE


# === No trace context fallback ============================================


@pytest.mark.asyncio
async def test_pass_without_trace_context_for_any_role_any_scope() -> None:
    """get_doc requires no role and no tenant scope — passes everywhere."""
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="get_doc", trace_context=None)
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_block_without_trace_context_when_role_required() -> None:
    g = ToolGuardrail(_make_matrix())
    r = await g.check(content="delete_doc", trace_context=None)
    # No baggage → role None → BLOCK
    assert r.action == GuardrailAction.BLOCK


# === Stage 2.3 max-calls-per-session counter (Sprint 55.4 — closes AD-Cat9-5) =


SESSION_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
SESSION_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make_quota_matrix(max_calls: int = 3) -> CapabilityMatrix:
    """Single-tool matrix with max_calls_per_session quota."""
    return CapabilityMatrix(
        capability_to_tools={Capability.READ_KB: ["query_tool"]},
        permission_rules={
            "query_tool": PermissionRule(
                role_required="any",
                tenant_scope="any",
                max_calls_per_session=max_calls,
            ),
        },
    )


def _session_context(session_uuid: UUID) -> TraceContext:
    return TraceContext(
        trace_id="t1",
        span_id="s1",
        tenant_id=TENANT_A,
        session_id=session_uuid,
    )


@pytest.mark.asyncio
async def test_max_calls_under_cap_passes() -> None:
    """1st call when max_calls_per_session=3 → PASS."""
    g = ToolGuardrail(_make_quota_matrix(max_calls=3))
    r = await g.check(content={"name": "query_tool"}, trace_context=_session_context(SESSION_A))
    assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_max_calls_at_cap_passes() -> None:
    """All 3 calls when max=3 → PASS (last one is the cap-edge)."""
    g = ToolGuardrail(_make_quota_matrix(max_calls=3))
    ctx = _session_context(SESSION_A)
    for _ in range(3):
        r = await g.check(content={"name": "query_tool"}, trace_context=ctx)
        assert r.action == GuardrailAction.PASS


@pytest.mark.asyncio
async def test_max_calls_over_cap_blocks() -> None:
    """4th call when max=3 → BLOCK with reason and HIGH risk."""
    g = ToolGuardrail(_make_quota_matrix(max_calls=3))
    ctx = _session_context(SESSION_A)
    for _ in range(3):
        await g.check(content={"name": "query_tool"}, trace_context=ctx)
    r = await g.check(content={"name": "query_tool"}, trace_context=ctx)
    assert r.action == GuardrailAction.BLOCK
    assert "max calls per session exceeded" in r.reason
    assert r.risk_level == "HIGH"


@pytest.mark.asyncio
async def test_max_calls_per_session_isolation() -> None:
    """Session A reaches cap; session B counter independent."""
    g = ToolGuardrail(_make_quota_matrix(max_calls=3))
    ctx_a = _session_context(SESSION_A)
    ctx_b = _session_context(SESSION_B)
    # Session A: 3 calls fill the cap
    for _ in range(3):
        r = await g.check(content={"name": "query_tool"}, trace_context=ctx_a)
        assert r.action == GuardrailAction.PASS
    # Session B: 1st call still under cap (independent counter)
    r_b = await g.check(content={"name": "query_tool"}, trace_context=ctx_b)
    assert r_b.action == GuardrailAction.PASS
    # Session A: 4th call → BLOCK (cap on A only)
    r_a = await g.check(content={"name": "query_tool"}, trace_context=ctx_a)
    assert r_a.action == GuardrailAction.BLOCK
