"""Platform / Governance / HITL — public exports.

Implements `agent_harness.hitl.HITLManager` ABC (per 17.md §5).
Backed by existing `approvals` table from Sprint 49.3.
"""

from __future__ import annotations

from platform_layer.governance.hitl.manager import DefaultHITLManager
from platform_layer.governance.hitl.state_machine import (
    ApprovalState,
    InvalidTransitionError,
    is_terminal,
    validate_transition,
)

__all__ = [
    "DefaultHITLManager",
    "ApprovalState",
    "InvalidTransitionError",
    "is_terminal",
    "validate_transition",
]
