"""
File: backend/src/agent_harness/tools/hitl_tools.py
Purpose: request_approval built-in tool — flows through HITLManager (§HITL 中央化).
Category: 範疇 2 (Tool Layer; consumes §HITL central contracts)
Scope: Phase 53 / Sprint 53.4 US-3 (post 51.1 placeholder)

Description:
    `request_approval` lets an agent explicitly request operator approval
    mid-flight. As of Sprint 53.4 the handler is bound to an HITLManager
    instance via `make_request_approval_handler(hitl_manager, ...)`; calling
    the handler creates a real ApprovalRequest persisted to the `approvals`
    table and returns a structured payload with the request_id.

    The tool's own `hitl_policy=ALWAYS_ASK` is self-referential: every
    invocation by definition requires approval. ToolExecutorImpl will
    therefore short-circuit with PermissionDecision.REQUIRE_APPROVAL
    before this handler runs in production. The handler is reached only
    when pre-authorized (e.g., explicit_approval=True during testing /
    dry-run, or after the user already approved out-of-band).

Created: 2026-04-30 (Sprint 51.1 Day 4.2)
Last Modified: 2026-05-03

Modification History (newest-first):
    - 2026-05-03: Sprint 53.4 US-3 — bind to HITLManager; persist real
                  ApprovalRequest. Removed 51.1 placeholder UUID logic.
    - 2026-04-30: Initial creation as 51.1 placeholder.

Related:
    - 17-cross-category-interfaces.md §5 (HITL centralization)
    - platform_layer/governance/hitl/manager.py (DefaultHITLManager)
    - sprint-53-4-plan.md §US-3
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from agent_harness._contracts import (
    ApprovalRequest,
    ConcurrencyPolicy,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)
from agent_harness.hitl import HITLManager

ToolHandler = Callable[[ToolCall], Awaitable[str]]

REQUEST_APPROVAL_SPEC: ToolSpec = ToolSpec(
    name="request_approval",
    description=(
        "Request explicit human approval for the next action. Provides a "
        "message describing the proposed action and severity ('low' / "
        "'medium' / 'high' / 'critical'). The agent loop pauses on "
        "REQUIRE_APPROVAL until an operator decision arrives."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Human-readable description of the proposed action.",
                "minLength": 1,
            },
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Risk severity for routing to appropriate reviewer tier.",
                "default": "medium",
            },
        },
        "required": ["message"],
    },
    annotations=ToolAnnotations(
        read_only=False,
        destructive=False,  # the request itself is not destructive
        idempotent=False,
        open_world=False,
    ),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.ALWAYS_ASK,
    risk_level=RiskLevel.MEDIUM,
    tags=("builtin", "hitl"),
)


_SEVERITY_TO_RISK = {
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}


def make_request_approval_handler(
    hitl_manager: HITLManager,
    *,
    tenant_id_resolver: Callable[[ToolCall], UUID],
    session_id_resolver: Callable[[ToolCall], UUID],
    default_sla_seconds: int = 14400,
) -> ToolHandler:
    """Build a handler bound to an HITLManager + tenant/session resolvers.

    The resolvers exist because ToolCall does not carry tenant_id / session_id
    by itself — the orchestrator decides those at call time. Tests can pass
    constant resolvers; production wires them to the loop's TraceContext.
    """

    async def request_approval_handler(call: ToolCall) -> str:
        message = str(call.arguments["message"])
        severity = str(call.arguments.get("severity", "medium"))
        risk_level = _SEVERITY_TO_RISK.get(severity, RiskLevel.MEDIUM)

        req = ApprovalRequest(
            request_id=uuid4(),
            tenant_id=tenant_id_resolver(call),
            session_id=session_id_resolver(call),
            requester="tools:request_approval",
            risk_level=risk_level,
            payload={"summary": message, "severity": severity, "tool_call_id": call.id},
            sla_deadline=datetime.now(timezone.utc) + timedelta(seconds=default_sla_seconds),
            context_snapshot={},
        )
        request_id = await hitl_manager.request_approval(req)

        return json.dumps(
            {
                "pending_approval_id": str(request_id),
                "message": message,
                "severity": severity,
                "status": "pending",
            }
        )

    return request_approval_handler


# === Legacy handler (kept for registry compat; deprecated post-53.4) ============
# Why: tools/__init__.py registers handlers at import time without an
# HITLManager instance. Production wires HITLManager via
# make_request_approval_handler(); the tools registry can have it injected
# during ToolExecutor construction. This legacy handler exists so existing
# call sites still resolve while migration is in progress.
async def request_approval_handler(call: ToolCall) -> str:
    """DEPRECATED: returns a deterministic placeholder ID without persistence.

    Production code must use `make_request_approval_handler(hitl_manager, ...)`
    to obtain a handler that actually persists ApprovalRequests.
    """
    from uuid import NAMESPACE_OID, uuid5

    message = str(call.arguments["message"])
    severity = str(call.arguments.get("severity", "medium"))
    pending_id = str(uuid5(NAMESPACE_OID, f"approval:{call.id}"))
    return json.dumps(
        {
            "pending_approval_id": pending_id,
            "message": message,
            "severity": severity,
            "status": "pending",
            "note": (
                "DEPRECATED placeholder; bind HITLManager via "
                "make_request_approval_handler() for real persistence"
            ),
        }
    )
