# 36 — HITL Gate Consolidation + Destructive Risk-Floor (Sprint 57.124)

**Purpose**: Document the audit verdict + design decision that retired the `PermissionChecker` shadow gate and made destructive tools escalate via the load-bearing per-tenant `HITLPolicy`.
**Category / Scope**: Cat 2 (Tool Layer) + Cat 9 (Guardrails/HITL) + Cat 1 (Loop) / Phase 57 / Sprint 57.124
**Created**: 2026-06-16
**Status**: Active
**Closes**: `AD-PermissionChecker-Shadow-Gate-Phase58`

> **Modification History**
> - 2026-06-16: Initial creation (Sprint 57.124 — spike-extract design note, Track 1)

---

## 1. Spike Summary: the executor's PermissionChecker was a stale shadow gate that overrode the 57.122 per-tenant policy

**The audit question** (57.122 carryover): is `PermissionChecker` (Sprint 51.1) — a "parallel HITL abstraction not wired into the loop" — another Potemkin?

**The verdict (worse than a Potemkin)**: `PermissionChecker` IS active on 主流量 and CONFLICTS with the load-bearing per-tenant policy 57.122 shipped.

- `make_default_executor` (`backend/src/business_domain/_register_all.py:357`) builds `ToolExecutorImpl(registry=, handlers=, tracer=)` **without** a `permission_checker` → `ToolExecutorImpl.__init__` defaulted to `PermissionChecker()` (was `executor.py:145`). So it ran on every chat tool call.
- The loop runs `_cat9_tool_check` (`backend/src/agent_harness/orchestrator_loop/loop.py:2828`, the 57.122 guardrail + per-tenant `HITLPolicy` ESCALATE) FIRST, then `_tool_executor.execute` (`loop.py:2918`) which internally ran `PermissionChecker.check()` AGAIN.
- `PermissionChecker` had three HARDCODED dims (was `permissions.py:93-105`): dim 1 `hitl_policy ALWAYS_ASK/ASK_ONCE → REQUIRE_APPROVAL`; dim 2 `risk HIGH/CRITICAL → REQUIRE_APPROVAL`; dim 3 `destructive and not explicit_approval → DENY`. The loop's `exec_ctx` (`loop.py:2886-2890`) never sets `explicit_approval=True`.

**Consequences**:
- Dim 2 is the EXACT flat hardcoding 57.122 removed from `loop.py:1007`. It re-blocked a permissive tenant's `auto_approve_max_risk=HIGH`, silently overriding the load-bearing policy.
- Dim 3 unconditionally hard-DENY'd every destructive business tool in chat (incident/rootcause/patrol/audit), even after a human approved it via the 57.122 ESCALATE→resume — an "approved-but-still-fails" latent bug + an advertised-but-unrunnable tool surface.

## 2. Decision Matrix

| Option | What | Verdict |
|--------|------|---------|
| **A. Surgical** | Remove only the conflicting dims 1+2; KEEP dim 3 (destructive hard-DENY) | Rejected (user 2026-06-15). Fixes the override but leaves destructive tools advertised-but-unrunnable (a residual Potemkin) + the approved-but-fails bug. |
| **B. Complete (CHOSEN)** | Remove `PermissionChecker` entirely + compensate by flooring `destructive` → HIGH in `resolve_tool_risk` so destructive tools ESCALATE (human-approvable) via the per-tenant policy | **Chosen.** Single source of truth (`_cat9` + `HITLPolicy`); fixes both the override conflict AND the latent bug; destructive gating becomes per-tenant-policy-governed. |
| **C. Audit-only** | Document the conflict, fix later | Rejected. The conflict is a live correctness bug, not cosmetic. |

**Destructive → HIGH floor (not CRITICAL)** rationale: HIGH matches the pre-57.122 escalation default (`loop.py` `_cat9_hitl_branch` fell back to HIGH when no risk was threaded). Under the DEFAULT policy (`require_approval_min_risk=MEDIUM`) HIGH escalates; a tenant that explicitly trusts HIGH (`auto_approve_max_risk >= HIGH`) can auto-approve — the per-tenant policy stays load-bearing (the 57.122 philosophy).

## 3. Verified Invariants

| # | Invariant | Evidence (file:line / test) |
|---|-----------|------------------------------|
| 1 | `resolve_tool_risk` floors destructive → HIGH (LOW/MEDIUM → HIGH; CRITICAL unchanged; non-destructive unchanged) | `_contracts/hitl.py:147-150`; `test_hitl_decision.py::test_resolve_tool_risk_destructive_floor` (7 params) |
| 2 | The destructive floor dominates the per-rule MEDIUM-floor | `test_hitl_decision.py::test_destructive_floor_beats_rule_flag` |
| 3 | A destructive LOW-risk tool ESCALATEs via the REAL loop under the default policy + the ApprovalRequest carries HIGH | `loop.py:546-549` + `test_loop_hitl_policy.py::test_destructive_tool_escalates_via_high_floor_under_default` (drives the actual `AgentLoopImpl._cat9_tool_check`) |
| 4 | A moderately-permissive tenant (auto=MEDIUM) would auto-run a MEDIUM-risk destructive tool WITHOUT the floor; the floor makes it escalate | `test_hitl_decision.py::test_destructive_floor_escalates_under_moderate_tenant` |
| 5 | The executor no longer permission-gates: a destructive/ALWAYS_ASK tool reaches the handler (no "permission denied"/"approval required" from the executor) | `executor.py` (gate block removed); `test_executor.py::test_executor_runs_destructive_high_risk_tool_no_gate` |
| 6 | D-escalate-coverage GREEN: every tool PermissionChecker previously non-ALLOW'd (8 ALWAYS_ASK/ASK_ONCE, all risk ≥ MEDIUM) still escalates under the default policy; no `CHAT_HITL_ESCALATE_TOOLS` change needed | progress.md Day-0 coverage table; `handler.py:178` `CHAT_HITL_ESCALATE_TOOLS={"echo_tool"}` |
| 7 | No broad regression from the removal | full backend pytest **2703 passed / 5 skipped** |

**Verification command**: `cd backend && python -m pytest tests/unit/agent_harness/guardrails/test_hitl_decision.py tests/integration/agent_harness/governance/test_loop_hitl_policy.py tests/unit/agent_harness/tools/test_executor.py -q` → all pass.

## 4. Cross-Category Contracts

- `resolve_tool_risk(spec_risk, *, rule_requires_approval, destructive=False)` — Cat 9 contract in `_contracts/hitl.py` (single-source per 17.md §5 HITL centralization). The `destructive` param is additive + backward-compatible (default False) → no caller break (`loop.py:548` is the only production caller). **No new ABC**; no 17.md §registry entry needed (extends an existing pure function).
- `ToolExecutorImpl` (17.md §2.1) — its responsibility narrows to schema-validate + dispatch + rate-limit + metrics/span; tool GATING moves entirely to Cat 9 (`_cat9_tool_check`). No signature change to the `ToolExecutor` ABC (the removed `permission_checker` was a ctor kwarg on the impl, not the ABC).

## 5. Open Invariants (NOT verified this spike)

- **Live UI drive-through of the destructive escalate→run path** — NOT done. gpt-5.2 declined to call a destructive business tool (`0 tool calls`), so the chat-v2 escalation could not be observed live (`AD-DriveThrough-Deterministic-Tool-Trigger`). Verified instead by the real-component integration tests (§3 invariant 3+5). Deferred: a deterministic destructive-tool trigger (e.g. a dedicated demo tool or a forced tool-call harness).
- **`ExecutionContext.explicit_approval` removal** — the field's sole consumer (PermissionChecker dim 3) is gone; the frozen-dataclass field is retained for forward-compat. `AD-ExecutionContext-ExplicitApproval-Tidy` tracks removing it (a separate contract structural change).
- **`PermissionChecker`'s other annotation dims** (`open_world` etc.) — never gated; not introduced.

## 6. Rollback

- Revert the 9 src files + restore `permissions.py` from git (`git revert` of the 57.124 commit). The executor's `permission_checker` kwarg + gate block return; `resolve_tool_risk` drops the `destructive` param. ~1 hr. No migration/data to undo (backend-internal behavior only). The removed PermissionChecker tests would need restoring (or kept removed if only the destructive floor is reverted).
- Partial rollback (keep the removal, drop the floor): if the destructive HIGH-floor proves too aggressive for some tenant, the floor is a single `if destructive` clause in `resolve_tool_risk` — removing it reverts destructive tools to plain risk-threshold behavior (a LOW-risk destructive tool would then auto-run under the default policy — the safety trade-off the floor exists to prevent).

## 7. References

- `04-anti-patterns.md` AP-2 (side-track / duplicate path) + AP-4 (Potemkin) — the audit lens.
- `17-cross-category-interfaces.md` §5 (HITL centralization) / §2.1 (ToolExecutor).
- `35-hitl-risk-threshold-semantics.md` (Sprint 57.122 — the per-tenant policy read-side this consolidates onto).
- `CHANGE-091-hitl-gate-consolidation-bundle.md` (the 3-track change record).
- `.claude/rules/sprint-workflow.md` §Step 2.5 (Day-0 D-escalate-coverage discipline).

## 8. 8-Point Quality Gate (self-review)

1. ✅ Section headers tied to the spike (§1 audit verdict, §2 decision).
2. ✅ Every technical claim has file:line (`executor.py`, `loop.py:2828/2918/546-549`, `hitl.py:147-150`, `handler.py:178`).
3. ✅ Decision matrix with A/B/C + rejection reasons (§2).
4. ✅ Verification command (§3).
5. ✅ Test fixture references (`test_hitl_decision.py`, `test_loop_hitl_policy.py`, `test_executor.py`).
6. ✅ Open invariants demarcated (§5 — live UI trigger NOT done; honest).
7. ✅ Rollback path (§6).
8. ✅ 17.md cross-ref (§4 — no new contract; extends existing pure fn + narrows impl responsibility).

**Verified ratio (estimated)**: ~95% (every invariant in §3 is test- or grep-backed; §5 honestly demarcates the un-driven live path).
