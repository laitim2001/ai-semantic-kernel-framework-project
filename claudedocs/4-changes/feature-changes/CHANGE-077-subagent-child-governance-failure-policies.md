# CHANGE-077: B4 — subagent child governance + child guardrail visibility + spawn failure policies

**Date**: 2026-06-13
**Sprint**: 57.110 (B4 — the LAST B-family harness-deepening slice; closes proposal §2.5)
**Scope**: 範疇 11 (Subagent) × 範疇 9 (Guardrails) × 範疇 8 (Error Handling) × platform_layer.governance × api/admin × thin chat-v2 FE

## Problem

The FORK/TEAMMATE child agent loops were deliberately LEAN (design note 20 §5 deferred): no
`guardrail_engine` → a child was a Cat 9 BYPASS — tenant escalate phrases, the C3
RiskyActionDetector, and the default Toxicity/SensitiveInfo detectors all governed the parent
but NOT the children it spawned (企業鐵律 violation: "child 不能成為 guardrail 旁路"). Child
guardrail activity was also invisible (GuardrailTriggered excluded from the relay subset), and
spawn failure semantics were implicit-only (every child failure soft-returned to the parent
LLM; no tenant choice; `SubagentBudget` had no failure_policy).

## Solution

1. **Child Cat 9 inheritance (US-1)**: both child-loop factories (`handler.py`) inject the
   parent's COMPOSED tenant-resolved engine (late-bound closure). No HITL wiring in a child →
   every ESCALATE fail-closes to BLOCK via loop.py's EXISTING invariant — **`loop.py` diff = 0**.
   Truthful `error="child_guardrail_blocked"` (fork/teammate stop_reason capture) replaces the
   misleading `empty_response` for blocked children. Recorded intentional behavior change:
   children of ALL tenants now run under the default guardrails too.
2. **Visibility (US-2)**: `GuardrailTriggered` joins `_TAO_CHILD_EVENT_TYPES` (rides the
   `subagent_child` wrapper — NO new wire type, count 24) + chat-v2 Tree child row
   (`guardrail escalate · <reason>`; chatStore projects `inner.reason`/`action`).
3. **Failure policies (US-3)**: `SubagentFailurePolicy` Literal (`fail_fast|fail_soft|fail_partial`)
   rides `SubagentBudget` (default `fail_soft` = byte-identical). `fail_fast`: the task_spawn
   handler raises `SubagentFailureEscalation` (NEW `_contracts/errors.py` type, registered
   `ErrorClass.FATAL` — the RateLimitExceededError mirror; never retried → no child re-spawn);
   `fail_partial`: executors salvage the child's partial output into `summary` (the nonlocal
   survives `wait_for` cancellation). Per-tenant via `HarnessPolicy.subagent_failure_policy`
   (12th field; joins `_STR_FIELDS`) + admin PUT/GET with literal validation (422).
4. **D-DAY3-1 fix-forward**: the drive-through caught a child REWRITING a blocked `os.system`
   call as `os.popen` — not in the C3 deny-list → it executed. Added
   `os.popen` + `os.spawn*/os.exec*` patterns to `DEFAULT_SANDBOX_PATTERNS` (+regression tests);
   the re-drive showed the child honestly giving up.

Threading: `handler.py` (cast from policy) → `make_default_executor(subagent_failure_policy=)`
→ `make_task_spawn_tool(failure_policy=)` → per-spawn `SubagentBudget`. 17.md: `SubagentBudget`
row updated + `SubagentFailurePolicy` NEW row.

## Verification

- Backend +19 tests, 0 del (full pytest 2502+4skip; subagent 90 / guardrails 23 / admin 23):
  engine-identity ×2 (capture-and-delegate on `make_chat_subagent_dispatcher`) · fail-closed
  pins (input-block / tool-soft-block / no-ApprovalRequested + event keeps action="escalate"
  while the run blocks) · relay forward · fail_fast raise + FATAL + LOOP-level terminal pin
  (`LoopTerminated` + exactly ONE spawn; needs production Cat 8 wiring) · fail_partial salvage
  (slow-tool timeout lever) · harness_policy round-trip + PUT 422/persist · popen regression.
- FE: Vitest 837 (+1 store projection); lint/build/mockup-fidelity 51 ✓. mypy 0/359 · run_all 10/10.
- **Drive-through PASS** (real UI + clean backend + real Azure gpt-5.2, zero dev-login): Leg A
  child `subprocess` blocked + Tree row renders the fire + parent honest; **D-DAY3-1** popen
  bypass caught → fix → Leg A-bis popen blocked, whoami did NOT run; Leg B PUT 200/422 live →
  task `"zzqx sentinel"` → child input-block (0 tok) → run terminated (no answer turn, no
  completion audit); flip-back verified all-None.

## Impact

Backend (Cat 11/9/8 + governance + admin) + thin FE label. `loop.py` / wire schema / codegen /
DB / migrations UNTOUCHED. Default path byte-identical for failure policies (`fail_soft`);
deliberate behavior change: children are now governed (the 鐵律 — not tenant-switchable).
Carryovers: `AD-LoopTerminated-Wire-Surface` (FATAL terminations invisible to the FE —
pre-existing, 57.58 shape) · `AD-Subagent-AsTool-FailFast` (as_tool_factory is an ABC method) ·
`AD-HarnessPolicy-Tab-FailurePolicy-Field` (the C3 tab lacks the new field; admin sets it via API).
