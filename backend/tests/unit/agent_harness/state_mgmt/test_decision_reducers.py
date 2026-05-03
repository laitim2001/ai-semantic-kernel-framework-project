"""
File: backend/tests/unit/agent_harness/state_mgmt/test_decision_reducers.py
Purpose: Unit tests for HITLDecisionReducer + SubagentResultReducer patch builders.
Category: Tests / 範疇 7 (State Management)
Scope: Phase 53 / Sprint 53.4 US-5

Created: 2026-05-03 (Sprint 53.4 Day 2)
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_harness._contracts.hitl import ApprovalDecision, DecisionType
from agent_harness.state_mgmt.decision_reducers import (
    HITLDecisionReducer,
    SubagentResult,
    SubagentResultReducer,
)

# --- HITLDecisionReducer ---


def test_hitl_approved_patch_removes_pending_id_and_appends_message() -> None:
    request_id = uuid4()
    decision = ApprovalDecision(
        request_id=request_id,
        decision=DecisionType.APPROVED,
        reviewer="alice@test.com",
        decided_at=datetime.now(timezone.utc),
        reason="looks good",
    )
    patch = HITLDecisionReducer.build_patch(decision)

    assert patch["durable"]["pending_approval_ids_remove"] == [request_id]
    msgs = patch["transient"]["messages_append"]
    assert len(msgs) == 1
    assert "approved" in msgs[0]["content"]
    assert msgs[0]["metadata"]["kind"] == "hitl_decision"
    assert msgs[0]["metadata"]["decision"] == "APPROVED"


def test_hitl_rejected_patch_format() -> None:
    decision = ApprovalDecision(
        request_id=uuid4(),
        decision=DecisionType.REJECTED,
        reviewer="bob@test.com",
        decided_at=datetime.now(timezone.utc),
        reason="too risky",
    )
    patch = HITLDecisionReducer.build_patch(decision)
    msg = patch["transient"]["messages_append"][0]
    assert "rejected" in msg["content"]
    assert "too risky" in msg["content"]


def test_hitl_escalated_patch_no_reason() -> None:
    decision = ApprovalDecision(
        request_id=uuid4(),
        decision=DecisionType.ESCALATED,
        reviewer="system",
        decided_at=datetime.now(timezone.utc),
        reason=None,
    )
    patch = HITLDecisionReducer.build_patch(decision)
    msg = patch["transient"]["messages_append"][0]
    assert "escalated" in msg["content"]
    assert " — " not in msg["content"]  # no trailing reason separator


# --- SubagentResultReducer ---


def test_subagent_success_patch_metadata_keyed_by_id() -> None:
    sub_id = uuid4()
    result = SubagentResult(
        subagent_id=sub_id,
        status="success",
        output={"answer": 42},
    )
    patch = SubagentResultReducer.build_patch(result)

    metadata_key = f"subagent_result:{sub_id}"
    assert metadata_key in patch["durable"]["metadata_set"]
    stored = patch["durable"]["metadata_set"][metadata_key]
    assert stored["status"] == "success"
    assert stored["output"] == {"answer": 42}


def test_subagent_failed_patch_appends_message() -> None:
    sub_id = uuid4()
    result = SubagentResult(
        subagent_id=sub_id,
        status="failed",
        output={"error": "timeout"},
    )
    patch = SubagentResultReducer.build_patch(result)
    msg = patch["transient"]["messages_append"][0]
    assert msg["metadata"]["kind"] == "subagent_result"
    assert "failed" in msg["content"]
    assert msg["metadata"]["subagent_id"] == str(sub_id)


def test_two_parallel_subagents_metadata_keys_disjoint() -> None:
    """Two subagents should NOT overwrite each other's metadata."""
    a = SubagentResult(subagent_id=uuid4(), status="success", output={"v": 1})
    b = SubagentResult(subagent_id=uuid4(), status="success", output={"v": 2})
    patch_a = SubagentResultReducer.build_patch(a)
    patch_b = SubagentResultReducer.build_patch(b)

    keys_a = set(patch_a["durable"]["metadata_set"].keys())
    keys_b = set(patch_b["durable"]["metadata_set"].keys())
    assert keys_a.isdisjoint(keys_b)
