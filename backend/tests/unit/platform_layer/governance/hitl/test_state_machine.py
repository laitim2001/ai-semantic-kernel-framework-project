"""
File: backend/tests/unit/platform_layer/governance/hitl/test_state_machine.py
Purpose: Unit tests for HITL approval state machine (validate_transition + is_terminal).
Category: Tests / Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.4 US-2

Created: 2026-05-03 (Sprint 53.4 Day 1)
"""

from __future__ import annotations

import pytest

from platform_layer.governance.hitl.state_machine import (
    ApprovalState,
    InvalidTransitionError,
    is_terminal,
    validate_transition,
)

# --- Valid transitions ---


def test_pending_to_approved_valid() -> None:
    validate_transition(ApprovalState.PENDING, ApprovalState.APPROVED)


def test_pending_to_rejected_valid() -> None:
    validate_transition(ApprovalState.PENDING, ApprovalState.REJECTED)


def test_pending_to_escalated_valid() -> None:
    validate_transition(ApprovalState.PENDING, ApprovalState.ESCALATED)


def test_pending_to_expired_valid() -> None:
    validate_transition(ApprovalState.PENDING, ApprovalState.EXPIRED)


# --- Invalid transitions ---


def test_approved_is_terminal() -> None:
    """APPROVED has no outgoing transitions."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(ApprovalState.APPROVED, ApprovalState.REJECTED)


def test_rejected_is_terminal() -> None:
    with pytest.raises(InvalidTransitionError):
        validate_transition(ApprovalState.REJECTED, ApprovalState.APPROVED)


def test_expired_is_terminal() -> None:
    with pytest.raises(InvalidTransitionError):
        validate_transition(ApprovalState.EXPIRED, ApprovalState.APPROVED)


def test_escalated_is_terminal_for_original_request() -> None:
    """ESCALATED is terminal for the original request; a fresh PENDING is
    created for the higher tier (handled by HITLManager.escalate())."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(ApprovalState.ESCALATED, ApprovalState.APPROVED)


# --- Terminal state predicate ---


def test_is_terminal_approved() -> None:
    assert is_terminal(ApprovalState.APPROVED) is True


def test_is_terminal_pending_false() -> None:
    assert is_terminal(ApprovalState.PENDING) is False


def test_invalid_error_message_contains_states() -> None:
    """Error message names both states for debuggability."""
    with pytest.raises(InvalidTransitionError) as exc_info:
        validate_transition(ApprovalState.APPROVED, ApprovalState.REJECTED)
    msg = str(exc_info.value)
    assert "approved" in msg
    assert "rejected" in msg
