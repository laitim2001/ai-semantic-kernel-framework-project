"""
File: backend/src/agent_harness/_contracts/hitl.py
Purpose: Single-source HITL types (ApprovalRequest / ApprovalDecision / HITLPolicy).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Description:
    HITL (Human-in-the-Loop) was previously scattered across categories
    2 / 7 / 8 / 9 in V1. V2 centralizes via §HITL Centralization (per
    17.md §5). All categories use these contract types; only HITLManager
    (in agent_harness/hitl/) implements behavior.

Owner: 01-eleven-categories-spec.md §HITL 中央化
Single-source: 17.md §1.1, §5

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §HITL 中央化
    - 17-cross-category-interfaces.md §5 (HITL centralization)
    - 14-security-deep-dive.md (compliance requirements)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class RiskLevel(Enum):
    """Risk levels driving HITL routing thresholds."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DecisionType(Enum):
    """Reviewer decisions."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"  # bumped to higher reviewer tier


@dataclass(frozen=True)
class ApprovalRequest:
    """Submitted by category 2 (tools) or category 9 (guardrails)."""

    request_id: UUID
    tenant_id: UUID
    session_id: UUID
    requester: str  # e.g. "tools" / "guardrails"
    risk_level: RiskLevel
    payload: dict[str, Any]
    sla_deadline: datetime
    context_snapshot: dict[str, Any]  # for human reviewer's UI


@dataclass(frozen=True)
class ApprovalDecision:
    """Reviewer's decision; merged back into LoopState by Reducer."""

    request_id: UUID
    decision: DecisionType
    reviewer: str
    decided_at: datetime
    reason: str | None = None


@dataclass(frozen=True)
class HITLPolicy:
    """Per-tenant policy: which risk levels require approval, who reviews."""

    tenant_id: UUID
    auto_approve_max_risk: RiskLevel = RiskLevel.LOW
    require_approval_min_risk: RiskLevel = RiskLevel.MEDIUM
    reviewer_groups_by_risk: dict[RiskLevel, list[str]] = field(default_factory=dict)
    sla_seconds_by_risk: dict[RiskLevel, int] = field(default_factory=dict)
