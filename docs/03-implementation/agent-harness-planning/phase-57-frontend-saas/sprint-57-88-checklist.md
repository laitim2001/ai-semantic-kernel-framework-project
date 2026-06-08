# Sprint 57.88 — Checklist (ESCALATE → Checkpoint → Resume — durable HITL pause-resume; 地基 A keystone spike)

**Plan**: [`sprint-57-88-plan.md`](./sprint-57-88-plan.md)
**Created**: 2026-06-08
**Status**: Draft (scope pending user approval; code gated on approval + Day-0 GO)

> Rule: only `[ ]` → `[x]`; never delete unchecked items; defer with `🚧 + reason`.
> SPIKE → Day-4 design-note extract + 8-point gate (`19-pause-resume-design.md`). Scope: ONE deterministic tool-ESCALATE → checkpoint → release → approve → resume → continue, driven through chat-v2 UI (real backend + real LLM).

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify
- [ ] **Prong 1 (path)**: `loop.py` `_cat9_hitl_branch` (~:552-697) + `wait_for_decision` call (~:654); `_abc.py:63-71` `resume()`; `checkpointer.py:12-16/68-70/94-100`; `_contracts/state.py`; `_contracts/events.py:382/388` (Approval events) + `LoopCompleted`/`TerminationReason`; `_contracts/hitl.py:55-77`; `hitl/_abc.py:53-99`; `governance/router.py:149-180` (decide endpoint); `chat/router.py`+`handler.py`+`sse.py`; `chat_v2` `ApprovalCard.tsx`/`HITLTurn.tsx`+store
- [ ] **Prong 2 (content)**: exact `_cat9_hitl_branch` flow + `ApprovalRequested`/`LoopCompleted` field lists; does a **non-blocking `get_decision`** exist on `HITLManager` (or only `wait_for_decision`)?; how the chat stream ends (keys off `LoopCompleted`, not a specific stop_reason?); how `DefaultHITLManager` stores/reads the `ApprovalDecision`; chat-v2 SSE consumer + stop_reason handling
- [ ] **Prong 3 (schema)**: `state_snapshots` table schema — can its payload column hold the `pending_approval` block (→ **no migration**)? if not → `0028` plan; confirm tenant_id + RLS; migration head = `0027`
- [ ] **Doc-location**: 17.md target section for `resume()`/checkpoint contract; design note `19-pause-resume-design.md` (confirm `19` free)
- [ ] Catalogue D-DAY0-1.. in progress.md; **go/no-go**

### 0.2 Branch + decisions
- [ ] Branch `feature/sprint-57-88-pause-resume` from latest `main`; plan+checklist commit; Day-0 progress commit
- [ ] Lock decisions: deferred mode = chat path only (blocking retained); resume trigger = NEW `POST /chat/{id}/resume` (governance decide unchanged); checkpoint enrich in existing JSONB (migration only if Prong-3 forces); ONE tool trigger = reuse `request_approval`; **Agent-delegated: yes** (Stage 1-3 below; drive-through + design note parent-driven)

---

## Day 1 — Backend core (Stage 1)

### 1.1 Deferred-approval pause (US-1)
- [ ] `TerminationReason.AWAITING_APPROVAL="awaiting_approval"` (`_contracts/events.py`; parallel to 57.68 HANDOFF)
- [ ] `loop.py` `_cat9_hitl_branch` deferred branch: `request_approval` → `checkpointer.save(enriched)` → `yield ApprovalRequested` → `LoopCompleted(stop_reason="awaiting_approval")`; NO `wait_for_decision` in deferred path; blocking path untouched
- [ ] `hitl_mode` discriminator wired (chat path = deferred)

### 1.2 Resumable checkpoint (US-2)
- [ ] `_contracts/state.py` checkpoint payload += `pending_approval {tool_call{name,args,tool_call_id}, approval_request_id, turn}`
- [ ] `checkpointer.py` save/load round-trips `pending_approval`; (conditional) migration `0028` if Prong-3 forced — up/down clean vs live Postgres
- [ ] unit: checkpoint enrich/restore round-trip

### 1.3 `resume()` implementation (US-3)
- [ ] `AgentLoopImpl.resume(state, trace_context)`: load checkpoint → rebuild messages from DB → read decision (`get_decision`, non-blocking; add if absent) → APPROVED: exec pending tool + append observation + continue to end_turn; REJECTED: `GuardrailTriggered` block + terminate
- [ ] unit: `resume()` approved + rejected paths (mock db + tool executor)

### 1.4 Backend green (Stage 1)
- [ ] black/isort/flake8; `mypy src/` 0; `check_llm_sdk_leak` 0; `run_all` 10/10; new unit tests pass

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
