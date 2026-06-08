# Sprint 57.88 — Checklist (ESCALATE → Checkpoint → Resume — durable HITL pause-resume; 地基 A keystone spike)

**Plan**: [`sprint-57-88-plan.md`](./sprint-57-88-plan.md)
**Created**: 2026-06-08
**Status**: Draft (scope pending user approval; code gated on approval + Day-0 GO)

> Rule: only `[ ]` → `[x]`; never delete unchecked items; defer with `🚧 + reason`.
> SPIKE → Day-4 design-note extract + 8-point gate (`19-pause-resume-design.md`). Scope: ONE deterministic tool-ESCALATE → checkpoint → release → approve → resume → continue, driven through chat-v2 UI (real backend + real LLM).

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify
- [x] **Prong 1 (path)**: all anchors confirmed — `_cat9_hitl_branch` loop.py:552-697; `_abc.py:63-71` resume; `checkpointer.py:118-181`; events.py:382/388; hitl.py:55/69; HITLManager; `manager.py` DefaultHITLManager; governance decide; chat router:138 + `_stream_loop_events`; `state.py:75` StateSnapshot
- [x] **Prong 2 (content)**: shapes captured (progress.md Day-0) — `_cat9_hitl_branch(*, tc, ctx, guardrail_reason)`; ApprovalRequested{approval_request_id, risk_level}; ApprovalReceived{approval_request_id, decision}; **NO non-blocking get_decision** (D-DAY0-1, must add); stream ends on `LoopCompleted` (D-DAY0-3 → awaiting_approval closes cleanly); decisions in `approvals` table (status!=PENDING)
- [x] **Prong 3 (schema)**: `state_snapshots.state_data` JSONB holds `pending_approval` → **免 migration** (D-DAY0-2); tenant_id+RLS ✓; head `0027`
- [x] **Doc-location**: 17.md contract section; `19-pause-resume-design.md` free (18-handoff→20-iam; 19 skipped)
- [x] Catalogued D-DAY0-1..8 in progress.md; **go/no-go = GO**

### 0.2 Branch + decisions
- [x] Branch `feature/sprint-57-88-pause-resume` from `41f1ed05`; plan+checklist (`65ab34fc`); Day-0 progress
- [x] Locked: deferred = chat path only (blocking retained); resume trigger = NEW `POST /chat/{id}/resume`; checkpoint enrich in JSONB (**no migration** per D-DAY0-2); reuse `request_approval`; enum in `termination.py` not events.py (D-DAY0-7); **Agent-delegated: yes**

---

## Day 1 — Backend core (Stage 1)

### 1.1 Deferred-approval pause (US-1)
- [x] `TerminationReason.AWAITING_APPROVAL="awaiting_approval"` — in `termination.py:63` (D-DAY0-7: NOT events.py; parallel to 57.68 HANDOFF)
- [x] `loop.py` `_cat9_hitl_branch` deferred branch: `request_approval`+`ApprovalRequested` (reused) → `_emit_state_checkpoint(pending_approval)` → `LoopCompleted("awaiting_approval")`; NO `wait_for_decision` in deferred; blocking path untouched; main loop `cat9_terminated→return` (loop.py:1366) skips tool
- [x] discriminator = `hitl_deferred: bool = False` ctor flag (gated on +checkpointer+reducer+session_id, else fall back blocking)

### 1.2 Resumable checkpoint (US-2)
- [x] pending_approval `{tool_call{name,arguments,tool_call_id}, approval_request_id, turn}` in `DurableState.metadata` (D-DAY0-2)
- [x] round-trips via existing `_serialize/_deserialize_state_for_db` JSONB — **NO migration**
- [x] unit: checkpoint enrich/restore covered in `test_loop_pause_resume.py`

### 1.3 `resume()` implementation (US-3)
- [x] `AgentLoopImpl.resume(*, state, trace_context)`: read pending_approval → `get_decision` (non-blocking, NEW) → APPROVED: exec pending tool + append observation + `_resume_continuation`→end_turn; REJECTED→block+LoopCompleted; undecided→fail-closed. ⚠️ `_resume_continuation` = reduced loop copy (no Cat 8/9/4) — design-note open question (§9)
- [x] `HITLManager.get_decision` (ABC + DefaultHITLManager, shared `_read_decision_if_decided`; wait_for_decision refactored, 0 behavior change)
- [x] unit: `resume()` approved + rejected + undecided paths

### 1.4 Backend green (Stage 1) — parent re-verified (gates run by parent, not trusted from agent report)
- [x] `mypy src/` 0/344; `run_all` 10/10 (incl. llm_sdk_leak, AP-1, AP-8); 56 passed (8 new pause-resume + loop regression + escalation e2e); zero regression

---

## Day 2 — Resume endpoint + platform service + integration tests (Stage 2)

### 2.1 Resume orchestration (US-4)
- [ ] `platform_layer/resume/service.py` `ResumeService.resume_session(*, session_id, tenant_id, user_id, db)`: load paused checkpoint; reject (no-paused / cross-tenant 404 / un-decided); drive `AgentLoopImpl.resume(...)`
- [ ] `POST /api/v1/chat/{session_id}/resume` SSE endpoint (JWT tenant/user; same serializer path); confirm normal stream closes cleanly on `awaiting_approval`

### 2.2 Integration tests (US-5)
- [ ] `test_chat_pause_resume.py`: ESCALATE deferred → `awaiting_approval` + checkpoint `pending_approval` persisted (tenant-scoped) + `ApprovalRequested`; record decision (governance endpoint); `/chat/{id}/resume` → APPROVED tool exec + continue end_turn + continuation streamed; REJECTED → block, no exec
- [ ] **multi-tenant**: resume with mismatched tenant JWT → 404 (鐵律); non-paused/un-decided → rejected
- [ ] `ResumeService` rejection-path unit tests

### 2.3 Backend sweep
- [ ] mypy 0; run_all 10/10; full `pytest tests/unit tests/integration` green (Risk Class C: ensure resume/new-endpoint tests override `get_db_session`)

---

## Day 3 — Frontend pause/resume wiring (Stage 3)

### 3.1 Paused state (US-5)
- [ ] chat-v2 store/components handle `LoopCompleted.stop_reason=="awaiting_approval"` → render "Awaiting approval (paused)" + `ApprovalCard`/`HITLTurn`; mark stream closed
### 3.2 Approve → resume (US-5)
- [ ] ApprovalCard approve → `POST /governance/approvals/{request_id}/decide` → `POST /chat/{session_id}/resume` → consume new SSE stream → render continuation + final answer (reuse `chatStore` SSE consumer)
### 3.3 Frontend green
- [ ] `npm run lint && npm run build` (NO `--silent`); `tsc` 0; Vitest green (+ new tests); `check:mockup-fidelity` ✓ (oklch baseline unchanged)

---

## Day 4 — Drive-through + Design note (8-point gate) + Closeout

### 4.1 Drive-through (US-5 — hard constraint)
- [ ] `dev.py start` (real backend) + `real_llm` + chat-v2 in browser (Playwright MCP or manual): message → paused state + stream closed → approve → continuation + final answer rendered
- [ ] Walk every control (approve button real? resume fires? continuation renders? labels real?) — no Potemkin
- [ ] Screenshots + "observed vs intended" diff → progress.md / CHANGE-056

### 4.2 Design note extract (US-5)
- [ ] `19-pause-resume-design.md` (NEW) — 8-point gate ALL (1 headers↔stories / 2 file:line / 3 decision matrix [deferred vs blocking; resume-endpoint vs governance-inline; JSONB-enrich vs migration] / 4 verify command / 5 fixture ref / 6 verified-vs-deferred / 7 rollback / 8 17.md cross-ref); verified-ratio ≥95%
- [ ] retrospective.md §Design Note Extract (8-point self-check)

### 4.3 Closeout
- [ ] Full validation (parent re-verified): pytest green / mypy src 0 / run_all 10/10 / Vitest / migration up+down (if any) / drive-through PASS
- [ ] 17.md `resume()`+checkpoint+`AWAITING_APPROVAL`; `CHANGE-056`
- [ ] progress.md (Day 0-4) + retrospective.md (Q1-Q7)
- [ ] Calibration: `loop-lifecycle-spike` 0.55 (NEW, 1 pt, caveated) + `agent_factor` 0.65; record `calibration-log.md §3`; carryover (generalized pause points / 地基 B / subagent / session-list paused badge) → next-phase-candidates.md
- [ ] MEMORY.md pointer + `project_phase57_88_pause_resume.md` subfile + CLAUDE.md lean
- [ ] commit (Day 0-4) + push + PR — user-authorized
