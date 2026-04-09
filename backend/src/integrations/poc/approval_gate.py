"""Approval Gate — PoC-level HITL checkpoint for agent team tool calls.

When an agent selects a HIGH-risk tool, the gate pauses that agent's
coroutine (via asyncio.sleep polling) and emits an APPROVAL_REQUIRED SSE
event.  Other agents in the asyncio.gather continue unblocked.

Risk classification is a simple tool-name whitelist (PoC-level).
The full RiskAssessor from orchestration/ can be wired in later.

Reuses existing infrastructure:
  - HITLController from integrations/orchestration/hitl/controller.py
  - APPROVAL_REQUIRED SSE event from sse_events.py
  - Approval API from api/v1/orchestration/approval_routes.py

PoC: Agent Team V4 — Sprint 154.
"""

import asyncio
import logging
import uuid
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Risk classification (PoC — tool-name whitelist)
# ---------------------------------------------------------------------------

class ToolRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


HIGH_RISK_TOOLS: set[str] = {
    "run_diagnostic_command",
    "query_database",
}

MEDIUM_RISK_TOOLS: set[str] = {
    "search_knowledge_base",
}


def assess_tool_risk(tool_name: str) -> ToolRiskLevel:
    """Classify a tool call's risk level by name."""
    if tool_name in HIGH_RISK_TOOLS:
        return ToolRiskLevel.HIGH
    if tool_name in MEDIUM_RISK_TOOLS:
        return ToolRiskLevel.MEDIUM
    return ToolRiskLevel.LOW


def requires_approval(tool_name: str) -> bool:
    """Return True if this tool requires human approval before execution."""
    return assess_tool_risk(tool_name) == ToolRiskLevel.HIGH


# ---------------------------------------------------------------------------
# Approval request + polling
# ---------------------------------------------------------------------------

async def request_and_await_approval(
    agent_name: str,
    tool_name: str,
    tool_args: dict[str, Any],
    session_id: str,
    emitter,
    hitl_controller,
    timeout_seconds: float = 300.0,
    poll_interval: float = 2.0,
) -> str:
    """Pause ONE agent while awaiting human approval for a tool call.

    Other agents in the asyncio.gather continue running — only this
    coroutine is blocked by asyncio.sleep during polling.

    Args:
        agent_name: Name of the requesting agent.
        tool_name: Tool that needs approval.
        tool_args: Arguments the agent wants to pass.
        session_id: Current team execution session ID.
        emitter: PipelineEventEmitter (must have emit_event method).
        hitl_controller: HITLController instance.
        timeout_seconds: Max wait for human decision (default 5 min).
        poll_interval: Seconds between status checks.

    Returns:
        "approved", "rejected", or "expired".
    """
    approval_id = str(uuid.uuid4())

    # 1. Emit APPROVAL_REQUIRED SSE event
    if emitter and hasattr(emitter, "emit_event"):
        await emitter.emit_event("APPROVAL_REQUIRED", {
            "approval_id": approval_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "arguments": _safe_args(tool_args),
            "risk_level": "high",
            "session_id": session_id,
            "message": (
                f"Agent '{agent_name}' wants to execute '{tool_name}'. "
                f"Approve or reject?"
            ),
        })

    # 2. Register approval request with HITLController
    try:
        await hitl_controller.request_approval(
            routing_decision=_make_minimal_routing_decision(tool_name),
            risk_assessment=_make_minimal_risk_assessment(tool_name),
            requester=f"agent:{agent_name}",
            timeout_minutes=int(timeout_seconds / 60) or 5,
            metadata={
                "approval_id": approval_id,
                "tool_name": tool_name,
                "tool_args": _safe_args(tool_args),
                "session_id": session_id,
                "agent_name": agent_name,
            },
        )
    except Exception as e:
        logger.warning(f"Failed to register approval with HITLController: {e}")
        # Fall through to polling with approval_id-based lookup

    # 3. Poll for decision
    logger.info(
        f"Agent {agent_name}: awaiting approval for '{tool_name}' "
        f"(id={approval_id}, timeout={timeout_seconds}s)"
    )
    elapsed = 0.0
    while elapsed < timeout_seconds:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        try:
            status = await hitl_controller.check_status(approval_id)
            status_val = status.value if hasattr(status, "value") else str(status)

            if status_val == "approved":
                logger.info(f"Agent {agent_name}: tool '{tool_name}' APPROVED")
                return "approved"
            if status_val == "rejected":
                logger.info(f"Agent {agent_name}: tool '{tool_name}' REJECTED")
                return "rejected"
            if status_val in ("expired", "cancelled"):
                logger.info(f"Agent {agent_name}: tool '{tool_name}' {status_val}")
                return "expired"
        except Exception as e:
            logger.debug(f"Approval status check error: {e}")
            # Continue polling

    logger.warning(f"Agent {agent_name}: approval timed out for '{tool_name}'")
    return "expired"


# ---------------------------------------------------------------------------
# Minimal stubs for HITLController compatibility
# ---------------------------------------------------------------------------
# The full orchestrator uses RoutingDecision and RiskAssessment from
# integrations/orchestration/. For the PoC we create minimal instances.

def _make_minimal_routing_decision(tool_name: str):
    """Create a minimal RoutingDecision for HITLController compatibility."""
    try:
        from src.integrations.orchestration.intent_router.models import (
            RoutingDecision,
            ITIntentCategory,
        )
        return RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            routing_layer="agent_team",
            confidence=1.0,
            reasoning=f"Agent team tool call: {tool_name}",
        )
    except ImportError:
        # If models not available, return a dict (HITLController may accept)
        return {"tool_name": tool_name, "source": "agent_team"}


def _make_minimal_risk_assessment(tool_name: str):
    """Create a minimal RiskAssessment for HITLController compatibility."""
    try:
        from src.integrations.orchestration.risk_assessor.assessor import RiskAssessment
        return RiskAssessment(
            overall_risk="high",
            requires_approval=True,
            risk_factors=[f"High-risk tool: {tool_name}"],
            mitigation_strategies=["Human approval required"],
        )
    except ImportError:
        return {
            "overall_risk": "high",
            "requires_approval": True,
            "tool_name": tool_name,
        }


def _safe_args(args: dict[str, Any], max_len: int = 500) -> dict[str, str]:
    """Truncate tool args for safe SSE/storage."""
    result = {}
    for k, v in (args or {}).items():
        s = str(v)
        result[k] = s[:max_len] if len(s) > max_len else s
    return result
