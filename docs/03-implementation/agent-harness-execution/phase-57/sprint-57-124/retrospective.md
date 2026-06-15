# Sprint 57.124 Retrospective — HITL gate consolidation + 2 chrome/governance Potemkin fixes

**Closed**: 2026-06-16 · **Branch**: `feature/sprint-57-124-hitl-gate-consolidation` (from `main` `6a691621`)
**Scope class**: `mixed-multidomain-bundle` (0.65) · **Agent-delegated**: no (parent-direct, `agent_factor` 1.0)

---

## Q1 — What was delivered?

A user-chosen 3-track bundle (the next C-class items after 57.122/57.123):

- **Item 1 (Track 1, the meaty one)** — closed `AD-PermissionChecker-Shadow-Gate-Phase58`. The audit found `PermissionChecker` (Sprint 51.1) is NOT a benign Potemkin but a stale shadow gate active on 主流量 that overrides the 57.122 load-bearing per-tenant `HITLPolicy` (dim 2 = the flat hardcoding 57.122 removed; dim 3 hard-DENY'd every destructive tool even after approval). Fix B (user-chosen): removed `PermissionChecker` from the executor + DELETED `permissions.py`; compensated by flooring `destructive` → HIGH in `resolve_tool_risk` so destructive tools escalate-then-run via the per-tenant policy. Single source of truth = loop `_cat9` + `HITLPolicy`.
- **Item 2** — closed `AD-NotificationsPanel-Backend-Feed` (honest-label). Extracted the fixture to a shared `notificationsFixture.ts`; added a visible `BackendGapBanner` DEMO disclosure to `NotificationsPanel`; the bell badge derives from the shared `DEMO_UNREAD_COUNT` (dropped the standalone `FIXTURE_UNREAD_COUNT`).
- **Item 3** — closed `AD-HITL-Policy-Threshold-Validation`. Admin HITL-policy PUT `@model_validator` rejects `auto >= require` → 422.

CHANGE-091 + design note 36 (Track 1). NO migration / wire (24) / codegen; mockup-fidelity 51 unchanged.

## Q2 — Estimate accuracy / calibration

- Plan §Workload: bottom-up ~9.0 hr → class-calibrated commit ~5.85 hr (`mixed-multidomain-bundle` 0.65), parent-direct (`agent_factor` 1.0).
- **Actual ≈ commit (ratio ≈ 1.0-1.1, IN band)**. The PermissionChecker test surgery (more obsolete tests than the plan named — 10 removed across 3 files, not the 3 the plan listed) + the Risk Class E orphan-worker restart detour added wall-clock; offset by the Day-0 `D-escalate-coverage` landing GREEN with zero scope shift (no `CHAT_HITL_ESCALATE_TOOLS` change), and Items 2+3 being small + mechanical.
- **`mixed-multidomain-bundle` 0.65 → KEEP** (this data point IN band; matrix 3-sprint mean ~0.8-0.9 latest 57.107 IN band).

## Q3 — What went well?

- **Audit-before-plan was the right call.** The 3 items were selected together, but Item 1 was an AUDIT whose outcome (is PermissionChecker a Potemkin? remove/wire/keep?) determined scope. Doing the reconnaissance (executor path, `_cat9`, `make_default_executor`, the destructive tools, `CHAT_HITL_ESCALATE_TOOLS`) BEFORE drafting the plan produced an accurate plan + surfaced the safety crux (D-escalate-coverage) as the central Day-0 check.
- **D-escalate-coverage was the linchpin and landed GREEN.** Enumerating every tool PermissionChecker non-ALLOW'd + confirming each still escalates post-removal (all 8 are risk ≥ MEDIUM → escalate under the default policy; floor adds permissive-tenant protection) gave high confidence the removal was safe BEFORE writing code. No `CHAT_HITL_ESCALATE_TOOLS` change needed.
- **The destructive floor is the elegant compensating change.** It moves the dim-3 protection into the load-bearing policy path instead of an unconditional executor hard-DENY → fixes the override conflict AND the approved-but-fails latent bug in one move.
- **Real-component integration tests carried Item 1's verification** where the live-LLM trigger couldn't: `test_loop_hitl_policy` drives the actual `AgentLoopImpl`, `test_executor` the actual `ToolExecutorImpl`.
- **Full backend pytest 2703 passed** — the structural removal (a whole component deleted) caused zero broad regression.
- Items 2+3 live drive-throughs both PASS (DEMO banner via real bell/panel; 422 via real backend + real admin session).

## Q4 — What to improve?

- **Plan under-counted the PermissionChecker test surgery.** The plan named 3 test files; reality was 10 obsolete tests across those 3 (executor gate tests + builtin approval tests + the enum/resolution tests). A grep for the gate's assertion strings (`approval required` / `permission denied`) at Day-0 would have sized this precisely. (Folded into the Day-0 habit: when removing a component, grep its BEHAVIOR assertions, not just its imports.)
- **The Item-1 live drive-through is genuinely hard** (no deterministic destructive-tool LLM trigger). Documented honestly via `AD-DriveThrough-Deterministic-Tool-Trigger`; the real-component integration tests are the deterministic substitute. A future "forced tool-call" drive-through harness (inject a tool_call without the LLM) would close this cleanly.

## Q5 — Anti-pattern self-check

- **AP-2 (side-track / duplicate path)**: ✅ CLOSED — the stale `PermissionChecker` shadow gate removed; single source of truth.
- **AP-4 (Potemkin)**: ✅ — Item 2 fixture now DEMO-disclosed (`check_ap4_frontend_placeholder` green); Item 1 destructive gating is real (per-tenant policy), not advertised-but-blocked.
- **AP-1 (pipeline-as-loop)** N/A · **AP-3 (cross-dir scatter)** ✅ (Cat boundaries respected; `check_cross_category_import` green) · **AP-6 (bridge debt)** ✅ (removed a duplicate abstraction, didn't add one).
- v2 lints **10/10** · 0 violations.

## Q6 — Carryover

- **`AD-ExecutionContext-ExplicitApproval-Tidy`** (NEW, 🟢) — `ExecutionContext.explicit_approval` (`_contracts/tools.py:122`) lost its sole consumer (PermissionChecker dim 3); the frozen-dataclass field is retained for forward-compat. Removing it is a separate contract structural change.
- **Item-1 deterministic destructive-tool drive-through** (🟢) — a forced tool-call harness (inject a `tool_call` bypassing the LLM) would let the destructive escalate→run path be driven live without depending on gpt-5.2 calling a destructive tool.
- **`PermissionChecker` annotation dims** (`open_world` etc.) were never gated; not introduced (no carryover, just noted).
- Remaining C-class / chrome Potemkin + operator-portal audit backlog (see `next-phase-candidates.md`).

## Q7 — Lessons

1. **Audit items need reconnaissance before the plan.** When a selected item is "audit whether X is a Potemkin", the audit outcome IS the scope — scout first, then plan. (This sprint did it right.)
2. **Removing a component = grep its behavior, not just its imports.** The blast radius of deleting `PermissionChecker` included tests asserting its EFFECT (`approval required` / `permission denied` strings), not only its imports. Day-0 should grep both.
3. **A compensating change can turn a risky removal into a net improvement.** Removing the shadow gate alone would have regressed destructive-tool safety; the destructive HIGH-floor turned it into a fix for the override conflict AND the approved-but-fails bug.
4. **Real-component integration tests are a legitimate drive-through substitute when the LLM trigger is non-deterministic** — but say so honestly (NOT "drive-through verified" for the un-driven UI path).

---

## Design Note Extract (spike sprint)

**File**: `docs/03-implementation/agent-harness-planning/36-hitl-gate-consolidation-destructive-floor.md`
**Verified ratio (estimated)**: ~95%
**8-Point Quality Gate**: [x] 1 section headers · [x] 2 file:line · [x] 3 decision matrix · [x] 4 verification command · [x] 5 test fixtures · [x] 6 open invariants demarcated · [x] 7 rollback · [x] 8 17.md cross-ref
**Reviewer pass**: self-review (parent-direct)
