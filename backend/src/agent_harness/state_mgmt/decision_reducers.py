"""
File: backend/src/agent_harness/state_mgmt/decision_reducers.py
Purpose: Convenience helpers that build update patches for DefaultReducer to
         merge HITL decisions and subagent results into LoopState.
Category: 範疇 7 (State Management)
Scope: Phase 53 / Sprint 53.4 US-5

Description:
    DefaultReducer is the sole mutator of LoopState (per 53.1 design). These
    helpers do NOT subclass Reducer — they produce the canonical update dicts
    that DefaultReducer.merge() consumes. This keeps the sole-mutator contract
    intact while giving callers (HITL flow / subagent dispatch) a typed API.

    HITLDecisionReducer.build_patch(decision) → dict for DefaultReducer.merge()
    SubagentResultReducer.build_patch(result)   → dict for DefaultReducer.merge()

Key Components:
    - HITLDecisionReducer: builds patches for HITL decision integration
    - SubagentResultReducer: builds patches for subagent result aggregation

Created: 2026-05-03 (Sprint 53.4 Day 2)

Modification History:
    - 2026-05-03: Initial creation (Sprint 53.4 Day 2 US-5)

Related:
    - state_mgmt/reducer.py (DefaultReducer — sole mutator)
    - _contracts/hitl.py (ApprovalDecision)
    - 17-cross-category-interfaces.md §5
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from agent_harness._contracts.hitl import ApprovalDecision, DecisionType


@dataclass(frozen=True)
class SubagentResult:
    """Compact summary of a subagent run for state merging."""

    subagent_id: UUID
    status: str  # "success" | "failed" | "cancelled"
    output: dict[str, Any]


# === HITLDecisionReducer ===
# Why: HITL flow needs to remove the decided request_id from
# DurableState.pending_approval_ids and append a marker message to
# TransientState.messages so the loop can resume with context.
# Alternative considered:
#   - Direct DefaultReducer.merge() call by HITL caller — rejected:
#     scatter the patch shape across modules (AP-3).
class HITLDecisionReducer:
    """Build a DefaultReducer-compatible patch from an ApprovalDecision."""

    @staticmethod
    def build_patch(decision: ApprovalDecision) -> dict[str, Any]:
        """Return update dict to pass to DefaultReducer.merge()."""
        marker = {
            "role": "system",
            "content": HITLDecisionReducer._format_decision(decision),
            "metadata": {
                "kind": "hitl_decision",
                "request_id": str(decision.request_id),
                "decision": decision.decision.value,
                "reviewer": decision.reviewer,
            },
        }
        return {
            "transient": {
                "messages_append": [marker],
            },
            "durable": {
                "pending_approval_ids_remove": [decision.request_id],
            },
        }

    @staticmethod
    def _format_decision(decision: ApprovalDecision) -> str:
        verb = {
            DecisionType.APPROVED: "approved",
            DecisionType.REJECTED: "rejected",
            DecisionType.ESCALATED: "escalated",
        }[decision.decision]
        reason = f" — {decision.reason}" if decision.reason else ""
        return f"HITL request {decision.request_id} {verb} by {decision.reviewer}{reason}"


# === SubagentResultReducer ===
# Why: Subagent dispatcher needs to append the result summary to
# TransientState.messages and store the structured result under
# DurableState.metadata so resume can recover it.
# Alternative considered:
#   - Storing in TransientState — rejected: subagent results often outlive a
#     single turn (Cat 11 reuse pattern).
class SubagentResultReducer:
    """Build a DefaultReducer-compatible patch from a SubagentResult."""

    @staticmethod
    def build_patch(result: SubagentResult) -> dict[str, Any]:
        """Return update dict to pass to DefaultReducer.merge()."""
        marker = {
            "role": "system",
            "content": (f"Subagent {result.subagent_id} finished with status=" f"{result.status}"),
            "metadata": {
                "kind": "subagent_result",
                "subagent_id": str(result.subagent_id),
                "status": result.status,
            },
        }
        # Store structured result under metadata — keyed by subagent_id so
        # multiple parallel subagents do not overwrite each other.
        metadata_key = f"subagent_result:{result.subagent_id}"
        return {
            "transient": {
                "messages_append": [marker],
            },
            "durable": {
                "metadata_set": {
                    metadata_key: {
                        "status": result.status,
                        "output": result.output,
                    },
                },
            },
        }
