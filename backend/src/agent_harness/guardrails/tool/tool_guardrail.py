"""
File: backend/src/agent_harness/guardrails/tool/tool_guardrail.py
Purpose: Per tool_call permission guardrail (3-stage approval — stages 1+2).
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 3 (US-4)

Description:
    Runs once before each tool_call execution. Implements three-stage
    approval per CC pattern (per 01-eleven-categories-spec.md §範疇 9):
      Stage 1 (trust baseline) — assumed: user authenticated; tenant
              policy loaded into matrix at session start (orchestrator's
              responsibility, not this guardrail's).
      Stage 2 (permission check) — this guardrail: role check + tenant
              scope + (max-calls placeholder; defer to integration with
              session state). Implemented here.
      Stage 3 (explicit confirmation) — this guardrail returns ESCALATE
              when rule.requires_approval=True; orchestrator (or 53.4
              HITL infrastructure) presents the request via Teams / UI
              and waits for human decision. Wiring is 53.4 scope.

    User role looked up from `trace_context.baggage["role"]` (OTel
    pattern — arbitrary trace metadata travels in baggage). Sessions
    without role attribution fall through as "any" (open).

    Decision flow (fail-fast):
        unknown tool                → BLOCK (HIGH)
        role mismatch               → BLOCK (HIGH)
        tenant scope violation      → BLOCK (HIGH)
        rule.requires_approval=True → ESCALATE (MEDIUM)
        default                     → PASS

Key Components:
    - ToolGuardrail(Guardrail): guardrail_type = TOOL
    - _extract_tool_name: works for ToolCall (.name), dict ({"name":}), or str

Owner: 01-eleven-categories-spec.md §範疇 9 (3-stage approval)
Single-source: GuardrailResult / GuardrailAction in 17.md §1.1

Created: 2026-05-03 (Sprint 53.3 Day 3)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-4) — stages 1+2 wiring;
      stage 3 (explicit confirmation) deferred to 53.4 HITL infrastructure

Related:
    - guardrails/tool/capability_matrix.py — owns the policy registry
    - guardrails/_abc.py — Guardrail ABC contract
    - 01-eleven-categories-spec.md §範疇 9 §三階段審批
"""

from __future__ import annotations

from typing import Any

from agent_harness._contracts import TraceContext
from agent_harness.guardrails._abc import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
)
from agent_harness.guardrails.tool.capability_matrix import CapabilityMatrix


class ToolGuardrail(Guardrail):
    """Per tool_call permission guardrail.

    Args:
        matrix: CapabilityMatrix containing tool→capability + permission rules.
    """

    guardrail_type = GuardrailType.TOOL

    def __init__(self, matrix: CapabilityMatrix) -> None:
        self._matrix = matrix

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        tool_name = self._extract_tool_name(content)
        if tool_name is None:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason="cannot extract tool_name from content",
                risk_level="HIGH",
            )

        rule = self._matrix.get_rule(tool_name)
        if rule is None:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"unknown tool: {tool_name!r} not in capability_matrix",
                risk_level="HIGH",
            )

        # Stage 2.1 — role check
        if rule.role_required != "any":
            user_role = self._extract_user_role(trace_context)
            if user_role != rule.role_required:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=(f"role required: {rule.role_required!r}, " f"got: {user_role!r}"),
                    risk_level="HIGH",
                )

        # Stage 2.2 — tenant scope check (own_only requires trace_context.tenant_id)
        if rule.tenant_scope == "own_only":
            if trace_context is None or trace_context.tenant_id is None:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason="tenant scope=own_only but no tenant_id in trace_context",
                    risk_level="HIGH",
                )
            # The actual tenant-data isolation is enforced at the DB layer
            # (per multi-tenant-data.md). This guardrail's job is to refuse
            # when the *tool* is tenant-scoped but the call lacks tenant
            # context — which would let the DB query escape its WHERE clause.

        # Stage 2.3 — max calls per session (placeholder)
        # Integration with session-level state (session_id → counter) is
        # owned by the orchestrator's session manager; this guardrail
        # documents the intent without implementing the counter here to
        # avoid coupling the guardrail to session storage. When the
        # counter integration lands (53.4 / 54.x), this branch becomes
        # active.
        # TODO(53.4): wire in session call-counter via trace_context.session_id

        # Stage 3 — explicit confirmation (defer to HITL infrastructure)
        if rule.requires_approval:
            return GuardrailResult(
                action=GuardrailAction.ESCALATE,
                reason=(
                    f"tool {tool_name!r} requires approval "
                    f"(role={rule.role_required}, scope={rule.tenant_scope})"
                ),
                risk_level="MEDIUM",
            )

        return GuardrailResult(action=GuardrailAction.PASS)

    @staticmethod
    def _extract_tool_name(content: Any) -> str | None:
        """ToolCall (.name) → str; dict ({"name": ...}) → str; raw str → str."""
        if isinstance(content, str):
            return content
        # ToolCall instance has `.name` attribute
        name = getattr(content, "name", None)
        if isinstance(name, str):
            return name
        # dict shape (e.g. when wrapping primitives in tests)
        if isinstance(content, dict):
            v = content.get("name")
            if isinstance(v, str):
                return v
        return None

    @staticmethod
    def _extract_user_role(trace_context: TraceContext | None) -> str | None:
        """OTel baggage convention: role lives in trace_context.baggage["role"].

        Returns None when no role attributed (typical for unauthenticated
        sessions). Caller treats None as "no role match" except when
        rule.role_required == "any".
        """
        if trace_context is None or trace_context.baggage is None:
            return None
        return trace_context.baggage.get("role")
