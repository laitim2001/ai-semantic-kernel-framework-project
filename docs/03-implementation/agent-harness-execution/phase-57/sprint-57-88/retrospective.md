# Sprint 57.88 Retrospective — durable HITL pause-resume spike (地基 A keystone)

**Sprint**: 57.88 / **Branch**: `feature/sprint-57-88-pause-resume` / **Closed**: 2026-06-08
**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-88-plan.md`
**Type**: SPIKE → design note `19-pause-resume-design.md` (8-point gate)

---

## Q1 — What was the goal, and did we hit it?

Goal: replace the blocking `wait_for_decision` (chat path) with a durable pause-resume — ESCALATE → checkpoint → release connection → approve hours/days later → `resume()` → continue to `end_turn`, proven by a chat-v2 drive-through. **Hit in full.** All 5 US shipped; drive-through PASSED on real backend + real Azure gpt-5.2; all gates green (mypy 0/346, pytest 2229, run_all 10/10, Vitest 772, mockup-fidelity baseline 53 unchanged); design note + 17.md contract + CHANGE-056 written.

## Q2 — Estimate accuracy (calibration)

- Scope class: **`loop-lifecycle-spike` 0.55 (NEW, 1 data point, pending validation)** — backend+frontend SPIKE introducing a new loop lifecycle mechanism with a Day-4 design note + drive-through leg; analogous to `backend-control-transfer-spike` 0.55 (57.68) but with a frontend drive-through.
- `agent_factor`: **`mechanical-greenfield-design-decisions` 0.65** for Day 1/2 (agent-delegated: yes — 2 staged code-implementer for backend core + endpoint/service/tests + parent independent re-verify each); Day 3/4 parent-direct (frontend surgical wiring + ESCALATE trigger + drive-through debug → `agent_factor` 1.0 for those days).
- Plan committed: bottom-up ~20 hr → class-calibrated ~11 hr (0.55) → agent-adjusted ~7.2 hr (0.65).
- **Ratio CAVEATED (no clean wall-clock)** — multi-session + `/compact` mid-sprint + a 3-defect drive-through hunt (stale-worker diagnosis + FK + service-wire) dominate the wall-clock; the "focused human hours" denominator is structurally unmeasurable in staged-delegation + drive-through-debug mode. **KEEP both multipliers, no generalization on 1 data point.** This is the **12th consecutive agent-delegated sprint with no clean measure (57.63→57.88)** → reinforces `AD-Calibration-AgentDelegated-WallClock-Measure`.
- Record to `calibration-log.md §3`.

## Q3 — What went well

- **Day-0 three-prong paid off**: D-DAY0-2 (JSONB → no migration) + D-DAY0-7 (enum in `termination.py` not events.py) + D-DAY0-8 (chat_v2 frontend already rich) reshaped scope cleanly before code.
- **The blocking path stayed untouched** — deferred mode is a pure additive discriminator; `approval-card.spec.ts` (legacy blocking HITL) stayed green throughout.
- **Drive-through caught 3 real defects every gate was green on** — exactly the Drive-Through Acceptance constraint's value. Risk Class E (stale `--reload` worker), the FK savepoint-visibility bug, and the ResumeService HITLManager wiring gap were all invisible to mypy/pytest/lint/Vitest.
- **Registry-derived ESCALATE matrix** avoided `ToolGuardrail`'s unknown-tool→BLOCK trap (a static echo-only matrix would have broken memory/subagent/business tools) — Explore blast-radius audit confirmed 0 test breakage before wiring.

## Q4 — What to improve / lessons

- **Risk Class E is real and costly** — 3 drive-through attempts were burned on a stale spawn-worker before diagnosis. Lesson reinforced: for startup/wiring verification, kill ALL workers + run a single process you control + capture the startup log proving the wiring fired. (Already codified in sprint-workflow.md §Common Risk Classes E.)
- **Integration tests masked 2 of the 3 defects** — they pre-create the session row (masked the FK bug) and inject a mock loop that already has a hitl_manager (masked the service-wire gap). A test closer to the real builder would have caught the service-wire gap; the FK bug is genuinely an HTTP-transaction-boundary issue only a real request surfaces. Honest boundary kept in the test-design notes.
- **`_resume_continuation` is a reduced loop copy** — the honest fidelity caveat (omits Cat 8/9/4) is the top carryover; production needs run()'s core refactored into a shared re-enterable loop.

## Q5 — Action items / carryover (→ `next-phase-candidates.md`)

- `AD-Resume-Continuation-Fidelity` — refactor run()'s core into a shared re-enterable loop (or resume re-arms full Cat 8/9/4 machinery); enable multi-pause-per-run.
- `AD-Resume-Checkpoint-Bloat` — a `messages` table / bounded summary + checkpoint TTL (replace self-contained `resume_messages`).
- `AD-Resume-Tenant-Capability-Policy` — per-tenant `capability_matrix.yaml` (which tools require approval per tenant/role) vs the current registry-derived matrix.
- `AD-Resume-Reject-Path` — reject-then-resume (emit block + clean checkpoint) or a dangling-checkpoint reaper.
- Generalized pause points / session-list paused badge + cross-device resume / approval notification / 地基 B cognition phases / subagent child-loop (the 地基 A 骨架 now feeds it).
- `AD-Calibration-AgentDelegated-WallClock-Measure` (carryover, 12th consecutive).

## Q6 — Discipline self-check

- ☑ Plan → Checklist → Day-0 verify → Code → Update checklist → Progress → Retro (5-step honored)
- ☑ No future sprint plan pre-written (rolling)
- ☑ No unchecked `[ ]` deleted
- ☑ Multi-tenant 鐵律 (cross-tenant resume → 404, tenant-scoped checkpoint query + `get_decision`)
- ☑ LLM neutrality (resume service + endpoint provider-free; `check_llm_sdk_leak` 0)
- ☑ File headers + MHist updated (loop/handler/service/router/chatService); MHist 1-line max
- ☑ Drive-Through Acceptance (hard constraint) — actually driven, not gate-only

## Q7 — Numbers

mypy 0/346 · run_all 10/10 · pytest 2229 passed / 4 skipped · Vitest 772 passed / 134 files · mockup-fidelity oklch baseline 53 unchanged · 6 commits (65ab34fc plan/checklist → 603c615c Stage-1 → bc8f567c Stage-2 → 21c49b28 Stage-3 → 9a06b795 Day-4 ESCALATE → 99d04f60 Day-4 drive-through fixes).

---

## §Design Note Extract (spike sprint — 8-point self-check)

**File**: `docs/03-implementation/agent-harness-planning/19-pause-resume-design.md`
**Verified ratio (estimated)**: ≥ 95% (every technical claim carries file:line + a reproducible test/drive-through; deferred items explicitly fenced in §5)
**8-Point Quality Gate**:
- [x] 1. Section headers map to US-1..US-5 (§1 Spike Summary enumerates each)
- [x] 2. Every claim has file:line (`loop.py:798-833` / `:1841` / `:2183-2185`; `handler.py:286-300/331`; `router.py:279/780`; `service.py:94-129/168-181`; `termination.py:63`)
- [x] 3. Decision matrix — 6 decisions, options + chosen + rejected reasons (D1-D6)
- [x] 4. Verification commands — backend pytest + frontend vitest + drive-through reproduce, all listed
- [x] 5. Test fixtures — `conftest.py` `db_session`; coroutine-direct test-design honesty note; ESCALATE-trigger no-fixture note
- [x] 6. Open invariants fenced — §5 (4 NEW ADs + deferred list), distinct from §3 Verified
- [x] 7. Rollback — discriminator-revert path + `< 1 hr` estimate + sentinel (blocking path untouched)
- [x] 8. 17.md cross-ref — §4.1 LoopEvent + §5.2 `get_decision` ABC + §5.3 deferred rule registered

**Reviewer pass**: self-review (parent), 2026-06-08.
