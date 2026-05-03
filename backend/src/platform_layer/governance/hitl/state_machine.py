"""
File: backend/src/platform_layer/governance/hitl/state_machine.py
Purpose: HITL approval state machine — defines valid state transitions and rejection rules.
Category: Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.4 US-2

Description:
    HITL approvals progress through states:
        pending → approved | rejected | escalated | expired

    Once a terminal state (approved/rejected/expired) is reached, no further
    transitions are allowed. ESCALATED loops back to pending (with a new
    expected_role) — see HITLManager.escalate().

    Owner: §HITL Centralization (per 17.md §5).
    Single-source: 17.md §5.2.

Created: 2026-05-03 (Sprint 53.4 Day 1)
Last Modified: 2026-05-03

Modification History:
    - 2026-05-03: Initial creation (Sprint 53.4 Day 1)

Related:
    - 01-eleven-categories-spec.md §HITL Centralization
    - 17-cross-category-interfaces.md §5
    - sprint-53-4-plan.md §US-2
"""

from __future__ import annotations

from enum import Enum


class ApprovalState(str, Enum):
    """Lifecycle states for an ApprovalRequest in the HITLManager."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


# === State transition matrix ===
# Why: Centralizing transitions in one constant prevents scattered ad-hoc
# checks. Terminal states (approved/rejected/expired) have empty allowed-set.
# ESCALATED is non-terminal — manager will re-emit a new pending request
# under a higher reviewer tier (handled by HITLManager.escalate()).
_VALID_TRANSITIONS: dict[ApprovalState, frozenset[ApprovalState]] = {
    ApprovalState.PENDING: frozenset(
        {
            ApprovalState.APPROVED,
            ApprovalState.REJECTED,
            ApprovalState.ESCALATED,
            ApprovalState.EXPIRED,
        }
    ),
    ApprovalState.APPROVED: frozenset(),
    ApprovalState.REJECTED: frozenset(),
    ApprovalState.ESCALATED: frozenset(
        # ESCALATED is itself terminal for the original request;
        # a fresh PENDING request is created for the escalated tier.
    ),
    ApprovalState.EXPIRED: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when an attempted state transition violates the state machine."""


def validate_transition(from_state: ApprovalState, to_state: ApprovalState) -> None:
    """Validate a state transition; raise InvalidTransitionError if invalid."""
    allowed = _VALID_TRANSITIONS.get(from_state, frozenset())
    if to_state not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from {from_state.value} to {to_state.value}; "
            f"allowed: {sorted(s.value for s in allowed)}"
        )


def is_terminal(state: ApprovalState) -> bool:
    """Return True if the state has no further valid transitions."""
    return len(_VALID_TRANSITIONS.get(state, frozenset())) == 0
