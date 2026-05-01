"""
File: backend/src/agent_harness/tools/hitl_tools.py
Purpose: request_approval built-in tool — escalates to human reviewer.
Category: 範疇 2 (Tool Layer; consumes §HITL central contracts)
Scope: Phase 51 / Sprint 51.1 Day 4.2

Description:
    `request_approval` lets an agent explicitly request operator approval
    mid-flight (e.g., "I am about to send an external email; please
    confirm"). 51.1 ships a placeholder implementation that returns a
    structured ToolResult including a `pending_approval_id` (deterministic
    UUID derived from call.id); the real ApprovalManager wiring lands in
    Phase 53.3.

    The tool's own `hitl_policy=ALWAYS_ASK` is self-referential: every
    invocation by definition requires approval. ToolExecutorImpl will
    therefore short-circuit with PermissionDecision.REQUIRE_APPROVAL
    before this handler runs in production. The handler is reached only
    when the operator has already pre-authorized via
    `ExecutionContext.explicit_approval=True` (e.g., during testing /
    dry-run). When the handler does run, it returns a payload describing
    what would be requested — useful for tracing and dry-runs.

Owner: 01-eleven-categories-spec.md §HITL 中央化 / 範疇 2
Created: 2026-04-30 (Sprint 51.1 Day 4.2)
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from uuid import NAMESPACE_OID, uuid5

from agent_harness._contracts import (
    ConcurrencyPolicy,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)

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


async def request_approval_handler(call: ToolCall) -> str:
    """Return a structured approval-request payload (51.1 placeholder).

    Real ApprovalManager wiring lands in Phase 53.3. Until then, the
    handler emits a deterministic placeholder ID derived from the
    ToolCall id so traces are reproducible.
    """
    message = str(call.arguments["message"])
    severity = str(call.arguments.get("severity", "medium"))
    pending_id = str(uuid5(NAMESPACE_OID, f"approval:{call.id}"))
    return json.dumps(
        {
            "pending_approval_id": pending_id,
            "message": message,
            "severity": severity,
            "status": "pending",
            "note": "51.1 placeholder; ApprovalManager wires in Phase 53.3",
        }
    )
