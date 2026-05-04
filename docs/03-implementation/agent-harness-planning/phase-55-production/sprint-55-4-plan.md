# Sprint 55.4 — Plan: Audit Cycle Mini-Sprint #2 (Groups B + C)

**Phase**: 55 (Production / V2 Closure Audit Cycles)
**Sprint Type**: Audit Cycle Mini-Sprint #2 (post-V2 22/22 closure)
**Branch**: `feature/sprint-55-4-audit-cycle-B-C`
**Estimated Duration**: 5 days (Day 0-4)
**Status**: Day 0 — Plan / Checklist drafting
**Author**: AI Assistant (laitim2001 ack)
**Created**: 2026-05-04

> **Modification History**
> - 2026-05-04: Initial draft (Sprint 55.4 Day 0)

---

## Sprint Goal

Close 5 carryover Audit Debt items (Groups B + C per scope ack) targeting Cat 8 (Error Handling) + Cat 9 (Guardrails) backend enhancements:

- **Group B** (Cat 8 backend, ~3-4 hr bottom-up):
  - **AD-Cat8-1** — RedisBudgetStore + fakeredis integration test (0% → ≥80% coverage)
  - **AD-Cat8-2** — RetryPolicyMatrix wire 進 AgentLoop end-to-end retry-with-backoff loop
  - **AD-Cat8-3** — Soft-failure 路徑保留 original Exception type (not synthesize Exception(str))
- **Group C** (Cat 9 backend, ~2-3 hr bottom-up):
  - **AD-Cat9-5** — ToolGuardrail max-calls-per-session counter (TODO at tool_guardrail.py:129)
  - **AD-Cat9-6** — WORMAuditLog real-DB integration tests (currently unit-only)

**Outcome**: 5 ADs closed; first application of **AD-Sprint-Plan-4 scope-class multiplier matrix** (medium-backend class → 0.65); V2 22/22 unchanged (audit cycle, not main progress).

---

## Background

### Audit Cycle Roadmap Progress

```
✅ Sprint 55.3 (audit cycle 1) — Groups A + G — DONE (PR #87 / #88 merged)
⏳ Sprint 55.4 (audit cycle 2) — Groups B + C — Cat 8 + Cat 9 backend ← THIS SPRINT
⏳ Sprint 55.5 (audit cycle 3) — Groups D + E — Cat 10 + Cat 11 backend
⏳ Sprint 55.6 (audit cycle 4) — Group F — Cat 10 frontend
   Group H (#31 / AD-CI-5 / AD-CI-6) — infra track, no sprint binding
```

55.3 closed 6 ADs with calibration ratio **2.81 way over band** when applying multiplier 0.40 to medium-backend scope. Sprint 55.4 is **first application of AD-Sprint-Plan-4 scope-class matrix** (medium-backend → multiplier 0.65). Goal: ratio in [0.85, 1.20] band.

### Day-0 Pre-flight Findings (AD-Plan-1 + AD-Plan-2 self-applied)

Per AD-Plan-1 (mandatory grep verify) + AD-Plan-2 (Day-0 path verify for every plan §File Change List entry, NEW from 55.3 retro):

| Finding | Source | Implication |
|---------|--------|-------------|
| All 5 target classes already exist (RedisBudgetStore / RetryPolicyMatrix / ErrorTerminator / ToolGuardrail / WORMAuditLog) at expected paths | Glob + Grep | **D1 — AD scope shifts from `create new` to `enhance + integration test`** for each AD |
| `tool_guardrail.py:129` already has explicit TODO `wire in session call-counter via trace_context.session_id` marking AD-Cat9-5 exact wire-point | Grep on tool_guardrail.py | **D2 — AD-Cat9-5 has clean hook ready**;just needs implementation behind the TODO marker |
| `test_redis_budget_store.py` exists in `tests/integration/agent_harness/error_handling/` at 149 lines | Glob + wc | **D3 — AD-Cat8-1 "0% coverage" baseline (53.2 retro) is outdated**;need to verify what exists covers vs what AD-Cat8-1 spec calls for(specifically fakeredis-based tests vs current real Redis dependency)|

→ Drift findings D1-D3 catalogued in §Risks (per AD-Plan-1 audit-trail rule;plan §Spec NOT silently rewritten);Day 1+ may add D4-Dn.

---

## Audit Debt Items

### AD-Cat8-1 — RedisBudgetStore + fakeredis Integration Test (Cat 8)

**Source**: 53.2 retrospective Q5

**Why**: RedisBudgetStore was created in Sprint 53.2 but lacked test coverage. Plan stated "0% coverage";Day 0 探勘 D3 found existing 149-line test_redis_budget_store.py — sharper scope = verify uses **fakeredis** (in-memory test double) per testing.md, not real Redis dependency.

**Spec**:
1. Read existing `tests/integration/agent_harness/error_handling/test_redis_budget_store.py`(149 lines)
2. Verify if it uses **fakeredis** or relies on real Redis container
3. If real Redis → migrate to fakeredis(per testing.md AP-10 mock-vs-real ABC pattern)
4. Add coverage gaps:
   - `consume_budget` → reduces remaining budget
   - `restore_budget` → undoes consumption
   - `get_remaining` → returns current budget
   - Concurrent access pattern(2 simultaneous consume calls don't double-count)
   - TTL expiry behavior
5. Coverage target: ≥80% line coverage on `_redis_store.py`

**Estimated**: 1.5-2 hr

**Files**:
- `backend/tests/integration/agent_harness/error_handling/test_redis_budget_store.py` — edit / migrate to fakeredis
- `backend/src/agent_harness/error_handling/_redis_store.py` — read only(no source change expected unless coverage gaps reveal bugs)

---

### AD-Cat8-2 — RetryPolicyMatrix Wire to AgentLoop (Cat 8)

**Source**: 53.2 retrospective Q5

**Why**: RetryPolicyMatrix exists in `error_handling/retry.py` but is not wired into AgentLoop's main run loop end-to-end. Errors propagate without retry-with-backoff orchestration. Operations expecting retry behavior fall through to immediate fail.

**Spec**:
1. Read `agent_harness/error_handling/retry.py` — confirm RetryPolicyMatrix interface
2. Read `agent_harness/orchestrator_loop/agent_loop.py` — find current error handling code path
3. Identify wire-point: when LLM call fails (transient retry-eligible), or when tool call fails, AgentLoop should consult RetryPolicyMatrix → retry with backoff
4. Implement wire:
   - AgentLoop accepts `retry_policy: RetryPolicyMatrix | None = None` in constructor
   - On exception of retry-eligible types(transient网络 / 5xx / rate-limited), call retry_policy.should_retry(...)
   - Apply backoff via `asyncio.sleep` per matrix
   - Max retries enforced;exceeded → error path continues
5. Tests:
   - `test_agent_loop_retry_integration.py`(new)— 3 scenarios:transient error → retry success / 5xx → 3-retry backoff / non-retry-eligible → immediate fail
   - Existing `test_retry.py` regression(no break)

**Estimated**: 2-2.5 hr

**Files**:
- `backend/src/agent_harness/orchestrator_loop/agent_loop.py` — edit (add retry_policy param + wire)
- `backend/tests/integration/agent_harness/orchestrator_loop/test_agent_loop_retry_integration.py` — new

---

### AD-Cat8-3 — Soft-Failure Path Preserve Original Exception Type (Cat 8)

**Source**: 53.2 retrospective Q5

**Why**: ErrorTerminator's soft-failure path currently synthesizes `Exception(str(e))`,losing original exception type information. Downstream code can't `isinstance(e, NetworkTimeoutError)` for type-specific recovery.

**Spec**:
1. Read `agent_harness/error_handling/terminator.py` — find synthesize call site
2. Refactor to preserve original via:
   - Option A: `raise OriginalExceptionType(str(e)) from e`(re-construct same type)
   - Option B: store original in `__cause__` chain;wrap in `SoftFailureError(original=e)`(preserves chain + adds soft-fail context)
   - **Decide in Day 1** based on existing terminator code structure
3. Tests:
   - `test_terminator.py` — 3 scenarios:NetworkTimeoutError → preserved / ValueError → preserved / generic Exception → preserved
   - Existing 188 lines regression preserved

**Estimated**: 1 hr

**Files**:
- `backend/src/agent_harness/error_handling/terminator.py` — edit
- `backend/tests/unit/agent_harness/error_handling/test_terminator.py` — edit (3 new tests)

---

### AD-Cat9-5 — ToolGuardrail max-calls-per-session Counter (Cat 9)

**Source**: 53.3 retrospective Q5 + Day 0 探勘 D2

**Why**: `tool_guardrail.py:129` has explicit TODO `wire in session call-counter via trace_context.session_id`. Without it,a runaway agent can call same tool 100+ times within one session — guardrail caps at policy max but doesn't enforce per-session quota.

**Spec**:
1. Read `tool_guardrail.py:120-150` to understand current counter logic
2. Implement session call-counter:
   - Storage:in-memory `dict[session_id, dict[tool_name, count]]`(simple);or delegate to RedisBudgetStore for multi-instance safe
   - **Decide in Day 1** based on production needs(in-memory acceptable for single-instance;Redis for multi-instance)
3. On each `ToolGuardrail.check(tool_name, trace_context)` call:
   - Read max-calls policy from CapabilityMatrix(`max_calls_per_session: int | None`)
   - Increment counter for `(session_id, tool_name)`
   - If counter > max → return BLOCK with reason;else ALLOW
4. Tests:
   - `test_tool_guardrail.py`(edit)— 4 new scenarios:under-cap / at-cap / over-cap / different sessions independent
   - Existing 256 lines regression preserved

**Estimated**: 1.5-2 hr

**Files**:
- `backend/src/agent_harness/guardrails/tool/tool_guardrail.py` — edit (replace TODO with impl)
- `backend/src/agent_harness/guardrails/tool/capability_matrix.py` — edit if `max_calls_per_session` needs declaration
- `backend/tests/unit/agent_harness/guardrails/test_tool_guardrail.py` — edit (4 new tests)

---

### AD-Cat9-6 — WORMAuditLog Real-DB Integration Tests (Cat 9)

**Source**: 53.3 retrospective Q5

**Why**: WORMAuditLog has 195-line unit test (mock DB) but no real-DB integration test verifying:hash chain unbroken after real INSERTs / append-only trigger fires when UPDATE attempted / verify_chain pagination works on 1000+ rows.

**Spec**:
1. Read `worm_log.py` + existing `test_worm_log.py` (195 lines unit)
2. Create new integration test:
   - `test_worm_log_db_integration.py` in `tests/integration/agent_harness/guardrails/`
3. 4-6 integration tests:
   - Insert sequence → hash chain links correctly across rows
   - UPDATE attempt → DB trigger blocks(per audit_log_append_only.py migration 0005)
   - DELETE attempt → DB trigger blocks
   - verify_chain on 100+ rows → no break detected
   - Two concurrent inserts → both succeed, chain extends correctly
4. Use `db_session` fixture pattern from existing integration tests

**Estimated**: 1.5-2 hr

**Files**:
- `backend/tests/integration/agent_harness/guardrails/test_worm_log_db_integration.py` — new

---

## Technical Specifications

### Calibration Multiplier Strategy (AD-Sprint-Plan-4 First Application)

| Sprint | Scope class | Mult | Bottom-up | Committed | Actual | Ratio |
|--------|-------------|------|-----------|-----------|--------|-------|
| 53.7 | mixed | 0.55 | 13.5 hr | 7.4 hr | 7.5 hr | 1.01 ✅ |
| 54.1 | medium-backend | 0.55 | 18.5 hr | 10.2 hr | 7 hr | 0.69 below |
| 54.2 | medium-backend | 0.55 | 22.5 hr | 12.4 hr | 8 hr | 0.65 below |
| 55.1 | large multi-domain | 0.50 | 22 hr | 11 hr | 7.5 hr | 0.68 below |
| 55.2 | audit cycle | 0.40 | 17.5 hr | 7 hr | 7.7 hr | 1.10 ✅ |
| 55.3 | mixed-leaning-medium | 0.40 | 11.25 hr | 4 hr | 11.5 hr | 2.81 ⚠️ over |
| **55.4** | **medium-backend** | **0.65** | **~7-9 hr** | **~5-6 hr** | TBD | 1st matrix application |

**Strategy** (per AD-Sprint-Plan-4 medium-backend class):
- Multiplier 0.65 corresponds to retro evidence on 54.1+54.2 (0.65-0.69 ratios when 0.55 was applied to medium-backend) → 0.55 * (0.55/0.65) ≈ 0.47 effective when scope-corrected → for in-band, multiplier needs to LIFT to 0.65-0.75 range
- Day 4 retro Q2 must verify ratio in [0.85, 1.20] band
- If outside → AD-Sprint-Plan-5 logged to refine medium-backend class multiplier

### Cat 8 + Cat 9 Boundary Preservation

- AD-Cat8-2 (AgentLoop wire) does NOT modify Cat 1 internals beyond accepting `retry_policy: RetryPolicyMatrix | None` constructor param (preserves 17.md single-source for LoopState)
- AD-Cat9-5 (counter) stays inside Cat 9 (`tool_guardrail.py`);does NOT cross into Cat 7 state mutation (Cat 7 sole-mutator preserved per Sprint 55.3 AD-Cat7-1)
- AD-Cat9-6 integration tests do NOT modify production code

### LLM Provider Neutrality

- All 5 ADs touch backend Python only;no LLM SDK imports introduced
- AD-Cat8-2 retry logic is generic transient-error handling (not provider-specific)

---

## Acceptance Criteria

| Criterion | Target | Verify |
|-----------|--------|--------|
| AD-Cat8-1 closed | RedisBudgetStore covered ≥80% via fakeredis-based tests | `pytest --cov=src/agent_harness/error_handling/_redis_store.py` |
| AD-Cat8-2 closed | AgentLoop accepts retry_policy + 3 integration scenarios green | `pytest test_agent_loop_retry_integration.py` |
| AD-Cat8-3 closed | ErrorTerminator preserves original Exception type (3 type tests green) | `pytest test_terminator.py -k preserves_type` |
| AD-Cat9-5 closed | tool_guardrail.py:129 TODO replaced with impl + 4 session-counter tests green | grep `TODO(53.4)` returns 0 in tool_guardrail.py + `pytest test_tool_guardrail.py` |
| AD-Cat9-6 closed | 4-6 real-DB integration tests in test_worm_log_db_integration.py green | `pytest test_worm_log_db_integration.py` |
| Tests added | ≥+13 (AD-Cat8-1: 3-4, AD-Cat8-2: 3, AD-Cat8-3: 3, AD-Cat9-5: 4, AD-Cat9-6: 4-6) | pytest count: 1434 → ≥1447 |
| 7 V2 lints | All green | `python scripts/lint/run_all.py` exit 0 |
| LLM SDK leak | 0 | grep check (CI enforced) |
| mypy --strict | 0 errors | `mypy backend/src --strict` |
| Calibration ratio | ∈ [0.85, 1.20] (AD-Sprint-Plan-4 1st application) | Day 4 retro Q2 |

---

## Day-by-Day Plan

### Day 0 — Plan / Checklist + Day-0 探勘 (½ day)

- Verify working tree clean on main `a7724261`
- Branch `feature/sprint-55-4-audit-cycle-B-C` created
- Day-0 探勘 grep(AD-Plan-1 + AD-Plan-2 newly self-applied)— 4 grep + 5 Glob calls
- Drift findings catalogued: D1-D3
- Read 55.3 plan template (13 sections / Day 0-4)
- Write `sprint-55-4-plan.md`(this file)+ `sprint-55-4-checklist.md`
- Write Day 0 `progress.md`
- Commit Day 0(plan + checklist + progress)

### Day 1 — AD-Cat8-1 + AD-Cat8-3 (~2.5 hr)

- AD-Cat8-1: read existing test_redis_budget_store.py;verify fakeredis vs real Redis;migrate if needed;add coverage gap tests
- AD-Cat8-3: refactor terminator.py soft-failure path to preserve Exception type;add 3 type tests
- Update progress.md Day 1 entry
- 2 commits

### Day 2 — AD-Cat8-2 (~2-2.5 hr)

- Read agent_loop.py + retry.py to identify wire-point
- Implement retry_policy param + integration logic
- Write 3 integration tests
- Run all error_handling + orchestrator_loop tests
- Update progress.md Day 2 entry + commit

### Day 3 — AD-Cat9-5 + AD-Cat9-6 (~3-4 hr)

- AD-Cat9-5: replace tool_guardrail.py:129 TODO with session counter impl + 4 tests
- AD-Cat9-6: write 4-6 real-DB integration tests for worm_log
- Run all guardrails tests
- Update progress.md Day 3 entry + 2 commits

### Day 4 — Retrospective + Closeout (~1 hr)

- Run full pytest baseline + 7 V2 lints + LLM SDK leak
- Compute calibration ratio (AD-Sprint-Plan-4 1st application validation)
- Drift findings final catalog
- Write retrospective.md (6 必答 Q1-Q6)
- Update SITUATION-V2-SESSION-START.md §8 + §9 + history
- Update memory + MEMORY.md
- Push branch + open PR + watch CI green + merge
- Closeout PR for SHA fill-in if needed

---

## File Change List (Day-0 Path-Verified per AD-Plan-2)

### Edit Files (5)
- `backend/src/agent_harness/error_handling/terminator.py` — AD-Cat8-3 (path verified ✓)
- `backend/src/agent_harness/orchestrator_loop/agent_loop.py` — AD-Cat8-2 (path verified ✓)
- `backend/src/agent_harness/guardrails/tool/tool_guardrail.py` — AD-Cat9-5 (path verified ✓ + L129 TODO confirmed)
- `backend/src/agent_harness/guardrails/tool/capability_matrix.py` — AD-Cat9-5 (path verified ✓)
- `backend/tests/integration/agent_harness/error_handling/test_redis_budget_store.py` — AD-Cat8-1 (path verified ✓ exists 149 lines)
- `backend/tests/unit/agent_harness/error_handling/test_terminator.py` — AD-Cat8-3 (path verified ✓ exists 188 lines)
- `backend/tests/unit/agent_harness/guardrails/test_tool_guardrail.py` — AD-Cat9-5 (path verified ✓ exists 256 lines)

### New Files (2)
- `backend/tests/integration/agent_harness/orchestrator_loop/test_agent_loop_retry_integration.py` — AD-Cat8-2 (path verified ✓ NOT exists)
- `backend/tests/integration/agent_harness/guardrails/test_worm_log_db_integration.py` — AD-Cat9-6 (path verified ✓ NOT exists)

---

## Dependencies & Risks

### Dependencies

- **Internal**:
  - AD-Cat8-1 fakeredis migration depends on `fakeredis` Python package availability (verify in Day 1)
  - AD-Cat8-2 wire depends on AgentLoop refactor not breaking 13 existing AgentLoop tests
  - AD-Cat9-6 real-DB tests depend on Alembic migration 0005_audit_log_append_only being applied (verified locally)
- **External**:None

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **R1**(fakeredis package not installed)| Med | Low | Day 1 morning verify;if missing, add to pyproject.toml dev deps |
| **R2**(AgentLoop retry refactor breaks Cat 1 single-source)| Low | Med | Constructor-only param;no LoopState mutation |
| **R3**(Cat 9 session counter race condition)| Low | Med | In-memory dict per-session + per-tool key;single-instance OK;Redis upgrade tracked separately |
| **R4**(WORM real-DB tests flaky under concurrent insert)| Low | Low | Use db_session fixture's transactional rollback for hermetic isolation |
| **R5**(Calibration ratio outside [0.85, 1.20] band)| Med | Low | scope-class matrix 1st application;if outside, AD-Sprint-Plan-5 logged for refinement(not project-blocking)|

### Drift Findings (Day-0 探勘 — AD-Plan-1 + AD-Plan-2 self-applied)

- **D1** All 5 target classes already exist (no `create new` deliverables;all are `enhance + integration test`)
- **D2** tool_guardrail.py:129 TODO marker confirms AD-Cat9-5 exact wire-point — clean implementation hook
- **D3** test_redis_budget_store.py exists 149 lines — AD-Cat8-1 "0% coverage" baseline outdated;sharper scope = verify fakeredis-based + add coverage gaps

→ Day 1+ may add D4-Dn drift findings(catalog in progress.md;non-disruptive;preserves audit trail per AD-Plan-1)

### Common Risk Classes (per `sprint-workflow.md` §Common Risk Classes)

- **Risk Class A** (paths-filter): Sprint 55.4 PR will be backend-only → "Frontend E2E (chromium headless)" required check skipping → apply AD-CI-5 paths-filter workaround at Day 4

---

## Workload (per AD-Sprint-Plan-4 medium-backend class)

```
Scope class:    medium-backend
Multiplier:     0.65 (AD-Sprint-Plan-4 1st application;evidence:54.1+54.2 ratios 0.65-0.69 under 0.55 multiplier suggest scope was actually compressing more)
Bottom-up est:  ~7-9 hr (mid 8.5)
Calibrated:     ~8.5 × 0.65 = ~5.5 hr commit
```

**Day 4 retrospective Q2 verification**:
- If ratio ∈ [0.85, 1.20] → 0.65 confirmed for medium-backend class
- If outside band → AD-Sprint-Plan-5 logged with refined matrix value(e.g., 0.55 if under or 0.75 if over)

---

## Out of Scope

| Item | Why Out | Where |
|------|---------|-------|
| AD-Cat9-1-WireDetectors | operator-driven non-sprint(per 55.3 retro)| ops runbook |
| Group D (Cat 10 backend: Wire-1, Obs-Cat9Wrappers) | depends on chat router obs strategy | → Sprint 55.5 |
| Group E (Cat 11: Multiturn / SSEEvents / ParentCtx) | bottom-up ~6-8 hr large;needs dedicated sprint | → Sprint 55.5 |
| Group F (Cat 10 frontend) | frontend-only;separate calibration class | → Sprint 55.6 |
| Group H (#31 / AD-CI-5 / AD-CI-6) | infra track, no sprint binding | → infra track |
| Phase 56+ (SaaS Stage 1) | needs user approval first | → Phase 56+ |

---

## AD Carryover Sub-Scope

If 55.4 hits time-box pressure,**rolling carryover** priority(largest to smallest):

1. AD-Cat9-6 Day 3 → 55.5(integration tests;non-blocking for production)
2. AD-Cat8-2 Day 2 → 55.5(retry wire;regression risk if rushed)
3. AD-Cat8-1 Day 1 → 55.5(test enhancement;non-blocking)

> **Note**: Carryover should be exception, not rule. 55.4 calibration validation depends on closing all 5 ADs.

---

## Definition of Done

- ☐ All 5 ADs closed per acceptance criteria
- ☐ Tests added ≥+13 (cumulative 1434 → ≥1447)
- ☐ 7 V2 lints green
- ☐ pytest unit + integration green
- ☐ mypy --strict 0 errors
- ☐ LLM SDK leak 0 (CI enforced)
- ☐ black + isort + flake8 green
- ☐ Calibration ratio computed in retro Q2 (AD-Sprint-Plan-4 1st application)
- ☐ Drift findings catalogued (D1-Dn)
- ☐ retrospective.md with 6 必答 Q1-Q6
- ☐ SITUATION-V2-SESSION-START.md §8 updated (close 5 AD;add new AD if any)
- ☐ PR opened + CI green + merged to main
- ☐ Closeout PR for SHA fill-in if needed

---

## References

- **`SITUATION-V2-SESSION-START.md`** §8 Open Items(source of 5 ADs)
- **Sprint 55.3 retrospective.md** — AD-Sprint-Plan-4 + AD-Plan-2 origin
- **Sprint 53.2 retrospective** — origin of AD-Cat8-1/2/3
- **Sprint 53.3 retrospective** — origin of AD-Cat9-5/6
- **Sprint 55.3 plan + checklist** — format template (13 sections / Day 0-4)
- **`.claude/rules/sprint-workflow.md`** §Step 2.5 (Day-0 verify) + §Step 5 (progress.md per-day estimates)
- **`.claude/rules/file-header-convention.md`** §格式 (1-line MHist)
- **`.claude/rules/testing.md`** §AP-10 mock-vs-real ABC pattern (AD-Cat8-1 fakeredis)

---

**Status**: Day 0 — pending user approval before Day 1 code starts.
