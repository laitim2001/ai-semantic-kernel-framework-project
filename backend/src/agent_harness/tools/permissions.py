"""
File: backend/src/agent_harness/tools/permissions.py
Purpose: 3-dimensional permission gate for tool execution (HITL / risk / annotations).
Category: 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 2.1

Description:
    `PermissionChecker.check()` evaluates a `(ToolSpec, ToolCall, ExecutionContext)`
    triple and returns a `PermissionDecision` (ALLOW / REQUIRE_APPROVAL / DENY).
    The checker is purely advisory — it returns a decision but does NOT
    interact with HITL ApprovalManager (that wiring lands in Phase 53.3).
    `ToolExecutorImpl` consumes the decision and translates it to a
    `ToolResult` with appropriate error semantics.

    Three dimensions evaluated (per sprint-51-1-plan.md §決策 4):
      1. ToolHITLPolicy
         - ALWAYS_ASK → REQUIRE_APPROVAL on every call
         - ASK_ONCE → REQUIRE_APPROVAL (51.1 conservative: treats every call
           as first-call; per-session first-call tracking lands in 53.3 when
           ApprovalManager is wired)
         - AUTO → no HITL contribution; fall through to dimensions 2/3
      2. RiskLevel
         - HIGH or CRITICAL → REQUIRE_APPROVAL (regardless of hitl_policy)
         - MEDIUM / LOW → no contribution
      3. ToolAnnotations.destructive
         - destructive=True AND ExecutionContext.explicit_approval=False
           → DENY (operator must explicitly authorize destructive call)
         - destructive=True AND explicit_approval=True → ALLOW

    Resolution order: DENY > REQUIRE_APPROVAL > ALLOW (most restrictive wins).

    Tenant-aware RBAC (per-tenant role check) is OUT OF SCOPE for 51.1
    (lands in Phase 53.3 governance sprint). `ExecutionContext.tenant_id`
    is captured here for forward-compatibility and tracer attribution but
    not yet evaluated in `check()`.

Key Components:
    - PermissionDecision: ALLOW / REQUIRE_APPROVAL / DENY enum
    - PermissionChecker: stateless `check()` returning Decision

Note: ExecutionContext is owned by `_contracts/tools.py` (single-source per
17.md §1.1) so the ToolExecutor ABC can reference it without depending on
this module. PermissionChecker imports it back from `_contracts`.

Owner: 01-eleven-categories-spec.md §範疇 2
Single-source: 17.md §2.1 (ToolExecutor pre-execution gate)

Created: 2026-04-30 (Sprint 51.1 Day 2.1)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 51.1 Day 2.1) — PermissionDecision
      enum + ExecutionContext dataclass + PermissionChecker.check() with
      3-dim resolution.

Related:
    - .registry (Day 1.4 ToolRegistryImpl)
    - .executor (Day 2.2 ToolExecutorImpl consumes decisions)
    - sprint-51-1-plan.md §決策 4
    - .claude/rules/multi-tenant-data.md (tenant_id forward-compat)
"""

from __future__ import annotations

from enum import Enum

from agent_harness._contracts import (
    ExecutionContext,
    RiskLevel,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)


class PermissionDecision(Enum):
    """Outcome of `PermissionChecker.check()`. Most restrictive wins."""

    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class PermissionChecker:
    """Stateless 3-dim gate: HITL policy / risk level / destructive annotation."""

    def check(
        self,
        spec: ToolSpec,
        call: ToolCall,
        context: ExecutionContext,
    ) -> PermissionDecision:
        # Dim 3 (most restrictive): destructive without explicit approval → DENY
        if spec.annotations.destructive and not context.explicit_approval:
            return PermissionDecision.DENY

        # Dim 1: HITL policy
        if spec.hitl_policy in (ToolHITLPolicy.ALWAYS_ASK, ToolHITLPolicy.ASK_ONCE):
            return PermissionDecision.REQUIRE_APPROVAL

        # Dim 2: high-risk regardless of HITL policy
        if spec.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return PermissionDecision.REQUIRE_APPROVAL

        return PermissionDecision.ALLOW
