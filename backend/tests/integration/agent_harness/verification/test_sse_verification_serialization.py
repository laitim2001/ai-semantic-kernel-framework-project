"""
File: backend/tests/integration/agent_harness/verification/test_sse_verification_serialization.py
Purpose: Integration tests for SSE serialization of VerificationPassed / VerificationFailed events.
Category: Tests / Integration / 範疇 10 ↔ api/v1/chat boundary
Scope: Sprint 54.1 US-3 — closes feedback_sse_serializer_scope_check.md gap

Description:
    Verifies that the SSE serializer (api/v1/chat/sse.py) correctly handles
    the 2 Cat 10 LoopEvent subclasses introduced by Sprint 54.1 US-3:
    - VerificationPassed → "verification_passed" SSE event with score / type
    - VerificationFailed → "verification_failed" SSE event with reason /
      suggested_correction / type

    Without these isinstance branches the chat router would crash with
    NotImplementedError when verifier hooks emit these events. Per Drift D1
    from Sprint 54.1 Day 0 探勘, the serializer is at api/v1/chat/sse.py
    (NOT agent_harness/orchestrator_loop/sse.py).

Created: 2026-05-04 (Sprint 54.1 Day 3)

Related:
    - backend/src/api/v1/chat/sse.py
    - backend/src/agent_harness/_contracts/events.py — VerificationPassed/Failed
"""

from __future__ import annotations

from agent_harness._contracts import (
    TraceContext,
    VerificationFailed,
    VerificationPassed,
)
from api.v1.chat.sse import format_sse_message, serialize_loop_event


def test_serialize_verification_passed_full_payload() -> None:
    ctx = TraceContext.create_root()
    event = VerificationPassed(
        verifier="rules_based",
        verifier_type="rules_based",
        score=0.95,
        trace_context=ctx,
    )

    payload = serialize_loop_event(event)
    assert payload is not None
    assert payload["type"] == "verification_passed"
    data = payload["data"]
    assert data["verifier"] == "rules_based"
    assert data["verifier_type"] == "rules_based"
    assert data["score"] == 0.95
    assert data["trace_id"] == ctx.trace_id


def test_serialize_verification_failed_full_payload() -> None:
    ctx = TraceContext.create_root()
    event = VerificationFailed(
        verifier="llm_judge",
        verifier_type="llm_judge",
        reason="output contains hallucination",
        suggested_correction="Cite the source for claim X.",
        trace_context=ctx,
    )

    payload = serialize_loop_event(event)
    assert payload is not None
    assert payload["type"] == "verification_failed"
    data = payload["data"]
    assert data["verifier"] == "llm_judge"
    assert data["verifier_type"] == "llm_judge"
    assert data["reason"] == "output contains hallucination"
    assert data["suggested_correction"] == "Cite the source for claim X."
    assert data["trace_id"] == ctx.trace_id


def test_serialize_verification_passed_minimal_payload() -> None:
    """Backward compat: 49.1 stub used only `verifier` field; ensure defaults serialize."""
    event = VerificationPassed(verifier="x")
    payload = serialize_loop_event(event)
    assert payload is not None
    assert payload["type"] == "verification_passed"
    data = payload["data"]
    assert data["verifier"] == "x"
    assert data["verifier_type"] == ""
    assert data["score"] is None


def test_format_sse_message_for_verification_event_is_valid_wire_format() -> None:
    """Sanity: verification events produce a parseable SSE frame."""
    event = VerificationPassed(verifier="rules", score=0.9, verifier_type="rules_based")
    payload = serialize_loop_event(event)
    assert payload is not None
    frame = format_sse_message(payload["type"], payload["data"])
    assert frame.startswith(b"event: verification_passed\n")
    assert b"data: " in frame
    assert frame.endswith(b"\n\n")
