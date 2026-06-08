# Sprint 57.88 Plan — ESCALATE → Checkpoint → Resume (durable HITL pause-resume vertical line — 地基 A keystone spike)

**Purpose**: Ship the **first durable, connection-released pause-resume** on the production chat path — the keystone of 地基 A ("Loop 可暫停/可分裂"). Today a tool guardrail ESCALATE calls `HITLManager.wait_for_decision()` which **blocks in-process** (`loop.py` `_cat9_hitl_branch` ~:654), holding the SSE connection open until a human decides. That cannot serve the user's real scenario (**human approval takes hours-to-days**). This spike replaces the blocking wait, on ONE vertical line, with: ESCALATE → **checkpoint the loop state** (enriched enough to resume) → emit `ApprovalRequested` → terminate the run with `stop_reason="awaiting_approval"` so the **SSE connection is released** → (hours/days later) human approves via the EXISTING `POST /governance/approvals/{id}/decide` → the client calls a NEW `POST /chat/{session_id}/resume` → `AgentLoop.resume()` (today a pure-abstract stub) rebuilds the loop from the checkpoint, executes the approved tool, and continues to `end_turn` on a fresh SSE stream. Proven by an actual **drive-through** on the chat-v2 UI (real backend + real LLM), per the Drive-Through Acceptance hard constraint. **This is a SPIKE** (new lifecycle mechanism) → Day-4 design-note extract + 8-point quality gate (per `sprint-workflow.md §Step 5.5`).
**Category / Scope**: Cat 7 (State Mgmt — `resume()` impl + checkpoint enrichment) + Cat 1 (loop ESCALATE control flow → deferred-approval termination) + Cat 9 (HITL ESCALATE branch deferred mode) + Cat 12 (`awaiting_approval` stop_reason + resume stream) + platform-layer resume orchestration + chat router/SSE (NEW resume endpoint) + chat-v2 frontend (pause state + resume trigger — drive-through); Phase 57.88
**Created**: 2026-06-08
**Status**: Draft (scope below pending user approval; code execution gated on user approval + Day-0 GO)
**Source**: 5-point harness-deepening discussion (2026-06-07/08) — user chose 地基 A keystone as the highest-leverage first spike; user decisions: (2) HITL approval is hours-to-days → durable pause-resume required (not blocking wait); (3) finish 地基 A before subagent. + Day-0 reality grounding (Explore, 2026-06-08): reuse vs build map + 6 risk findings.

> **Modification History**
> - 2026-06-08: Initial creation — 地基 A keystone pause-resume vertical line; SPIKE (8-point design note); folds Day-0 grounding (reuse map + 6 risks) into §0

---

## 0. Background

The 5-point harness-deepening review (2026-06-07/08) clustered the user's chosen gaps into **two architectural capabilities**: 地基 A "Loop 可暫停/可分裂" (resume + checkpoint) and 地基 B "Loop 內可多次認知呼叫" (explicit cognition phases). The user chose to build **地基 A first** (it is the keystone that unlocks durable HITL pause-resume **and** the lifecycle骨架 the subagent child-loop needs), and confirmed the spike-first / drive-through-first approach.

This sprint = the **single narrowest vertical line** of 地基 A: one deterministic ESCALATE trigger → checkpoint → release connection → approve later → resume → continue, driven through the chat-v2 UI.

### ⚠️ Day-0 grounding findings (Explore, 2026-06-08; folded per `sprint-workflow.md §Step 2.5` — re-verified in Day-0 three-prong before code)

- **D1 — Much is already built; net-new is small.** ✅ `ApprovalRequested`/`ApprovalReceived` events (`_contracts/events.py:382/388`) + `ApprovalRequest`/`ApprovalDecision` contracts (`_contracts/hitl.py:55-77`) + `HITLManager` ABC + `DefaultHITLManager` impl (`hitl/_abc.py:53-99`, platform_layer L69+) + **approval-decision endpoint** `POST /api/v1/governance/approvals/{request_id}/decide` (`governance/router.py:149-180`) + frontend `ApprovalCard.tsx` / `HITLTurn.tsx` + checkpoint base (`DBCheckpointer` + `state_snapshots` + tenant_id/RLS) **all exist**. → do NOT rebuild these.
- **D2 — The central tension: `wait_for_decision` is BLOCKING.** `_cat9_hitl_branch` (`loop.py:552-697`) calls `hitl_manager.wait_for_decision()` (~:654) which blocks in-process → holds the SSE connection. This directly conflicts with "release connection, resume hours/days later". → the spike's core change = a **deferred-approval mode** on this branch: checkpoint + emit + terminate (do NOT delete the blocking path; other callers may keep it).
- **D3 — `resume()` is a pure-abstract stub.** `orchestrator_loop/_abc.py:63-71` defines `resume(state, trace_context) -> AsyncIterator[LoopEvent]` with NO implementation. → implement a minimal `AgentLoopImpl.resume()` (this slice: re-enter at the pending approved tool, then continue).
- **D4 — Checkpoint does NOT store messages buffer / pending tool call.** `checkpointer.py:12-16` serializes DurableState + transient scalar summary only ("messages buffer + pending_tool_calls list are NOT serialized — rebuildable from message history"). → resume needs (a) the **pending tool call** (name + args + tool_call_id) and (b) the **approval_request_id linkage** + turn. This slice stores those in the checkpoint payload; messages are rebuilt from the messages DB table.
- **D5 — Migration head is `0027` (not the old `0022`).** `migrations/versions/` latest = `0027_user_password_hash`. → IF the `state_snapshots` payload column cannot hold the enriched checkpoint (Day-0 Prong-3 confirms its schema), migration `0028` adds it; **preferred path = no migration** (enrich the existing JSONB payload). `state_snapshots` is tenant-scoped + RLS already.
- **D6 — Frontend has the approval card but no pause/resume flow.** `chat_v2` renders `ApprovalCard` but has no "connection released → awaiting approval (paused)" state and no "approve → resume → new stream" wiring. → this slice adds the minimal pause state + resume trigger (the drive-through deliverable).

**Net**: a coherent vertical — `loop.py` gains a deferred-approval branch (checkpoint + `ApprovalRequested` + `LoopCompleted(stop_reason="awaiting_approval")`); the checkpoint payload is enriched with the pending tool call + approval linkage; `AgentLoopImpl.resume()` is implemented to re-enter and run the approved tool; a NEW `POST /chat/{session_id}/resume` opens a fresh SSE stream driving `resume()`; chat-v2 shows the paused state and wires approve→resume. The existing governance decide endpoint + approval events + frontend ApprovalCard are reused as-is.

---

## 1. Sprint Goal

On the production chat path, replace the blocking `wait_for_decision` (for the chat ESCALATE case) with a **durable pause-resume**: a tool guardrail ESCALATE checkpoints the loop (enriched with the pending tool call + approval_request_id + turn), emits the existing `ApprovalRequested` event, and terminates the run with `stop_reason="awaiting_approval"` so the SSE connection is released; the human approves (hours/days later) via the existing `POST /governance/approvals/{id}/decide`; the client then calls a NEW `POST /chat/{session_id}/resume` which drives the newly-implemented `AgentLoopImpl.resume()` — loading the checkpoint, rebuilding the loop, executing the approved tool (or emitting a block on reject), and continuing to `end_turn` on a fresh SSE stream. Prove it with integration tests **and an actual chat-v2 UI drive-through** (real backend + real LLM): pause → connection released → approve → resume → continuation + final answer rendered. **Multi-tenant 鐵律: resume re-derives tenant_id from JWT and rejects a checkpoint whose tenant_id ≠ caller's.** Day-4 design note (8-point gate). Defer: explicit cognition phases (地基 B), subagent, multi-model, non-tool ESCALATE types, session-list paused indicator.

---

## 2. User Stories

- **US-1 (deferred-approval pause)** — As the agent loop on the chat path, when a tool ESCALATEs and HITL is in deferred mode, I want to checkpoint my state, emit `ApprovalRequested`, and terminate with `stop_reason="awaiting_approval"` (instead of blocking on `wait_for_decision`), so the SSE connection is released and the human can take hours/days. → `loop.py` `_cat9_hitl_branch` deferred branch + `TerminationReason.AWAITING_APPROVAL`.
- **US-2 (resumable checkpoint)** — As the platform, when a loop pauses for approval, I want the checkpoint to carry enough to resume (the pending tool call + args + tool_call_id, the approval_request_id, the turn) so a later resume can re-enter exactly where it paused. → checkpoint payload enrichment (`checkpointer.py` + `_contracts/state.py`); messages rebuilt from the messages DB table.
- **US-3 (`resume()` implementation)** — As the agent loop, I want a real `resume()` that loads a paused checkpoint, checks the recorded approval decision, executes the approved pending tool (or emits a guardrail block on reject), and continues to `end_turn`, so a paused conversation can finish. → implement `AgentLoopImpl.resume()` (replaces the abstract stub).
- **US-4 (resume endpoint + stream)** — As the client, after the human approves, I want to call `POST /chat/{session_id}/resume` and receive a fresh SSE stream of the continuation, so the UI shows the conversation finishing. → NEW chat resume endpoint + platform resume orchestration (re-derives tenant_id/user_id from JWT; rejects cross-tenant / non-paused / un-decided).
- **US-5 (drive-through + design note)** — As a reviewer, I want (a) integration tests proving the full pause→approve→resume path incl. multi-tenant rejection, AND (b) an **actual chat-v2 UI drive-through** (real backend + real LLM) with screenshots + "observed vs intended" diff, plus a Day-4 design note (8-point gate) capturing the durable-pause-resume design + open questions, so the spike's learnings are extracted and the next slice (generalize beyond one trigger) is well-scoped.

---

## 3. Technical Specifications

### 3.0 Architecture (durable pause-resume vertical)

```
[RUN 1 — pause]
LLM emits tool call → Cat 9 tool check → ESCALATE → loop.py _cat9_hitl_branch (~:552-697)
        IF hitl_mode == deferred (chat path):
        → hitl_manager.request_approval(...)            [existing — creates ApprovalRequest row, returns request_id]
        → checkpointer.save(enriched: pending_tool_call{name,args,tool_call_id} + approval_request_id + turn)   [US-2]
        → yield ApprovalRequested(...)                   [existing event]
        → terminate: LoopCompleted(stop_reason="awaiting_approval")   [US-1 — NO blocking wait]
        ▼
chat router streams events → on stop_reason=="awaiting_approval" → close SSE stream cleanly   [connection RELEASED]
        ▼
chat-v2 UI: render "Awaiting approval (paused)" + ApprovalCard; stream closed   [US-5 drive-through]

        ⏳  hours / days  ⏳

[human approves]
POST /api/v1/governance/approvals/{request_id}/decide   [EXISTING — records ApprovalDecision]
        ▼
chat-v2 UI: approve action → (decision recorded) → POST /api/v1/chat/{session_id}/resume   [US-4]
        ▼
[RUN 2 — resume]  ResumeService → AgentLoopImpl.resume(loaded_state)   [US-3]
        → load checkpoint (pending_tool_call + approval_request_id + turn); rebuild messages from DB
        → read approval decision (non-blocking get)
            ├─ APPROVED → execute pending tool → append observation → continue loop → end_turn
            └─ REJECTED → emit GuardrailTriggered(block) → terminate
        → fresh SSE stream of the continuation
        ▼
chat-v2 UI: render continuation turns + final answer   [US-5 drive-through]
```

`loop.py` changes only the ESCALATE branch (add deferred mode) + gains a `resume()` method; no other control-flow rewrite. Resume orchestration (load + decision-check + re-enter) lives in a thin platform service (crosses checkpoint + approval DB + auth — not a loop concern). The blocking `wait_for_decision` path stays for non-chat / synchronous callers (additive, not a deletion).

### 3.1 Deferred-approval pause (US-1) — `loop.py` `_cat9_hitl_branch` (~:552-697) + `TerminationReason`
- Add a `hitl_mode` discriminator (e.g. on the HITL manager or loop config): `blocking` (existing `wait_for_decision`) | `deferred` (NEW). Chat path = `deferred`.
- Deferred branch: `request_approval` (existing, get `request_id`) → `checkpointer.save(...)` enriched (§3.2) → `yield ApprovalRequested` (existing) → terminate via `LoopCompleted(stop_reason="awaiting_approval")` (NEW `TerminationReason.AWAITING_APPROVAL="awaiting_approval"`, parallel to 57.68's `HANDOFF`). No `wait_for_decision` call in this branch.
- Day-0 Prong-2 reads the exact `_cat9_hitl_branch` shape + the `ApprovalRequested`/`LoopCompleted` field lists before editing (`AD-Day0-Codegen-Existing-Shape-Capture` lesson — read the real shape).

### 3.2 Resumable checkpoint (US-2) — `checkpointer.py` + `_contracts/state.py`
- Enrich the checkpoint payload with a `pending_approval` block: `{ tool_call: {name, args, tool_call_id}, approval_request_id, turn }`. Stored in the **existing `state_snapshots` payload** (Day-0 Prong-3 confirms the column holds it → **no migration preferred**; fallback = migration `0028` adds a JSONB column).
- `checkpointer.save()`/`load()` serialize/deserialize the new block. Messages are NOT stored — `resume()` rebuilds them from the messages DB table (D4).
- Multi-tenant: the checkpoint row is already tenant-scoped (`state_snapshots` RLS); resume re-checks tenant_id (§3.4).

### 3.3 `resume()` implementation (US-3) — `loop.py` (`AgentLoopImpl.resume`) replacing `_abc.py:63-71` stub
- `resume(state, trace_context)`: from the loaded checkpoint — rebuild `LoopState` (messages from DB + `pending_approval`); read the recorded approval decision via a **non-blocking** `HITLManager.get_decision(approval_request_id)` (Day-0 Prong-2: confirm a non-blocking getter exists; if only `wait_for_decision` exists, add a thin `get_decision`).
  - APPROVED → execute the pending tool via the existing tool executor → append the observation as a tool message → continue the normal loop to `end_turn`.
  - REJECTED/ESCALATED → emit `GuardrailTriggered(block)` (existing) → terminate.
- This slice handles exactly ONE pending tool approval (not arbitrary mid-phase resume); broader resume points are a design-note open question (§9).

### 3.4 Resume endpoint + orchestration (US-4) — `api/v1/chat/router.py` (NEW endpoint) + `platform_layer/resume/service.py` (NEW)
- NEW `POST /api/v1/chat/{session_id}/resume` → `StreamingResponse` (same SSE serializer path as the normal chat stream). Re-derives `tenant_id`/`user_id` from JWT (standard chat auth dependency).
- NEW `ResumeService.resume_session(*, session_id, tenant_id, user_id, db)`: load the paused checkpoint; **reject** if (a) no paused checkpoint, (b) `checkpoint.tenant_id != tenant_id` (鐵律 — 404, no info leak), (c) approval not yet decided. On OK → drive `AgentLoopImpl.resume(...)` and stream its events.
- The existing governance decide endpoint is unchanged; the client orchestrates approve-then-resume.

### 3.5 SSE stream close on pause (US-1) — `api/v1/chat/router.py` / `sse.py`
- The normal chat stream loop ends when it sees `LoopCompleted`; `stop_reason="awaiting_approval"` is just another terminal stop_reason → the stream closes cleanly (no new mechanism; verify the stream-end path keys off `LoopCompleted`, not a specific stop_reason). Frontend distinguishes via `stop_reason`.

### 3.6 Frontend pause + resume wiring (US-5 drive-through) — `frontend/src/features/chat_v2/`
- Handle `LoopCompleted.stop_reason == "awaiting_approval"`: render a "paused — awaiting approval" state (reuse `ApprovalCard`/`HITLTurn`), mark the stream closed.
- Wire the ApprovalCard approve action → `POST /governance/approvals/{request_id}/decide` (decision) → then `POST /chat/{session_id}/resume` → consume the new SSE stream → render the continuation turns + final answer. (Reuse the existing SSE consumer in `chatStore`.)
- No session-list "paused" indicator this slice (§9).

### 3.7 Lint / neutrality / doc single-source
- `check_llm_sdk_leak` 0 (resume service + endpoint are provider-free; `agent_harness/**` only gets the deferred branch + `resume()` + checkpoint fields — no SDK). `check_rls_policies` green (no new table; `state_snapshots` already RLS; migration `0028` — if needed — adds a column, not a table).
- **Doc single-source**: 17.md — `resume()` / checkpoint-`pending_approval` contract + `AWAITING_APPROVAL` stop_reason; the Day-4 design note (`19-pause-resume-design.md`) is the durable-pause-resume design authority. (Day-0 confirms `19` is the next free design-note number.)

### 3.8 Validation (US-5)
- **Integration** (`test_chat_pause_resume.py` NEW): drive a loop whose tool ESCALATEs in deferred mode → assert (a) `LoopCompleted.stop_reason=="awaiting_approval"`; (b) a checkpoint persisted with the `pending_approval` block (tool_call + approval_request_id + turn), tenant-scoped; (c) `ApprovalRequested` emitted; record a decision via the governance endpoint; call `/chat/{id}/resume` → assert (d) the approved tool executed, (e) the loop continued to `end_turn`, (f) the continuation streamed. Reject case: decision=REJECTED → `GuardrailTriggered` block, no tool exec. **Multi-tenant**: resume with a different tenant's JWT → 404.
- **Unit**: deferred-branch stop_reason; checkpoint enrich/restore round-trip; `resume()` approved + rejected paths (mock db + tool executor); `ResumeService` rejection paths (no-paused / cross-tenant / un-decided).
- **Drive-through** (the hard constraint): real backend (`dev.py start`) + real LLM (`real_llm`) + chat-v2 UI in a browser — send a message that triggers the approval tool → see paused state + stream closed → approve → see continuation + final answer. Screenshots + "observed vs intended" diff into progress.md. (Playwright MCP or manual.)
- **migration** (only if `0028` needed): `alembic upgrade`/`downgrade` clean.

---

## 4. File Change List

| File | Change |
|------|--------|
| `backend/src/agent_harness/orchestrator_loop/loop.py` | **EDIT** — `_cat9_hitl_branch` deferred mode (checkpoint + ApprovalRequested + `awaiting_approval` terminate) (US-1); implement `AgentLoopImpl.resume()` (US-3) |
| `backend/src/agent_harness/orchestrator_loop/_abc.py` | **EDIT** — `resume()` doc (no longer "stub") (US-3) |
| `backend/src/agent_harness/_contracts/state.py` | **EDIT** — `pending_approval` block in checkpoint payload shape (US-2) |
| `backend/src/agent_harness/_contracts/events.py` | **EDIT** — `TerminationReason.AWAITING_APPROVAL` (US-1) |
| `backend/src/agent_harness/state_mgmt/checkpointer.py` | **EDIT** — serialize/deserialize `pending_approval` (US-2) |
| `backend/src/agent_harness/hitl/_abc.py` | **EDIT (maybe)** — non-blocking `get_decision(request_id)` if absent (US-3); deferred-mode discriminator |
| `backend/src/platform_layer/hitl/...` (DefaultHITLManager) | **EDIT (maybe)** — implement `get_decision` (US-3) |
| `backend/src/platform_layer/resume/service.py` | **NEW** — `ResumeService.resume_session` (load + decision-check + re-enter; tenant guard) (US-4) |
| `backend/src/api/v1/chat/router.py` | **EDIT** — NEW `POST /chat/{session_id}/resume` SSE endpoint; confirm stream closes on `awaiting_approval` (US-4/US-1) |
| `backend/src/api/v1/chat/handler.py` / `sse.py` | **EDIT (as needed)** — resume stream wiring (US-4) |
| `frontend/src/features/chat_v2/...` (store + components) | **EDIT** — `awaiting_approval` paused state + approve→decide→resume→new-stream wiring (US-5) |
| `backend/src/infrastructure/db/migrations/versions/0028_*.py` | **NEW (conditional)** — only if `state_snapshots` payload can't hold `pending_approval` (US-2) |
| `backend/tests/integration/api/test_chat_pause_resume.py` | **NEW** — full pause→approve→resume + reject + multi-tenant (US-5) |
| `backend/tests/unit/...` | **NEW/extend** — deferred branch + checkpoint round-trip + `resume()` + `ResumeService` (US-5) |
| `docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` | **EDIT** — `resume()` + checkpoint `pending_approval` + `AWAITING_APPROVAL` |
| `docs/03-implementation/agent-harness-planning/19-pause-resume-design.md` | **NEW (Day-4 extract)** — durable pause-resume design note (8-point gate) |
| `claudedocs/4-changes/feature-changes/CHANGE-056-durable-pause-resume.md` | **NEW** — change record |

No Azure-adapter change. No new DB table (column-only if any).

---

## 5. Acceptance Criteria

- A chat-path tool ESCALATE in deferred mode ends the run with `stop_reason="awaiting_approval"` (no blocking `wait_for_decision`); the SSE connection is released; `ApprovalRequested` is emitted.
- A checkpoint persists the `pending_approval` block (tool_call + approval_request_id + turn), tenant-scoped; `resume()` rebuilds the loop from it (messages from DB).
- After a decision is recorded via the existing governance endpoint, `POST /chat/{session_id}/resume` drives `resume()`: APPROVED → the pending tool executes + the loop continues to `end_turn` on a fresh stream; REJECTED → a `GuardrailTriggered` block, no tool exec.
- **Multi-tenant**: resume with a mismatched tenant JWT → 404 (no info leak); resume of a non-paused / un-decided session → rejected.
- **Drive-through PASS** (hard constraint): on chat-v2 UI with real backend + real LLM — message → paused state + closed stream → approve → continuation + final answer rendered; screenshots + observed-vs-intended diff recorded.
- All existing tests green; `mypy --strict src/` 0; 10/10 V2 lints (LLM SDK leak 0); frontend lint/build green (no `--silent`); Vitest unchanged except new tests. Day-4 design note passes the 8-point gate.

---

## 6. Deliverables

- [ ] `loop.py` deferred-approval branch + `TerminationReason.AWAITING_APPROVAL` (US-1)
- [ ] checkpoint `pending_approval` enrichment — `_contracts/state.py` + `checkpointer.py` (US-2)
- [ ] `AgentLoopImpl.resume()` — approved + rejected paths (US-3)
- [ ] non-blocking `get_decision` (if absent) (US-3)
- [ ] `ResumeService` + `POST /chat/{session_id}/resume` SSE endpoint + tenant guard (US-4)
- [ ] chat-v2 paused state + approve→decide→resume→new-stream wiring (US-5)
- [ ] integration `test_chat_pause_resume.py` + unit tests + multi-tenant (US-5)
- [ ] **drive-through on chat-v2 UI (real backend + real LLM) — screenshots + observed-vs-intended** (US-5)
- [ ] 17.md contract update; `19-pause-resume-design.md` Day-4 design note (8-point gate) (US-5)
- [ ] CHANGE-056 + progress.md + retrospective.md

---

## 7. Workload Calibration

Scope class: **`loop-lifecycle-spike` (0.55, NEW — pending validation)** — a backend+frontend SPIKE introducing a new loop lifecycle mechanism (deferred pause + checkpoint enrichment + `resume()` + resume endpoint + frontend drive-through) with a mandatory Day-4 design note; analogous to `backend-control-transfer-spike` 0.55 (57.68) but with a frontend drive-through leg. **Agent-delegated: yes** (staged: Stage-1 backend core — deferred branch + checkpoint enrich + `resume()` + events; Stage-2 resume endpoint + platform service + backend tests; Stage-3 frontend wiring; drive-through + design note parent-driven). `agent_factor` **`mechanical-greenfield-design-decisions` 0.65** (genuine design: pause/resume control flow, checkpoint shape, resume re-entry, tenant guard on resume).

> Bottom-up est ~20 hr → class-calibrated commit ~11 hr (mult 0.55) → agent-adjusted commit ~7.2 hr (agent_factor 0.65).

Caveat: `loop-lifecycle-spike` is a single unvalidated data point — record caveated, do NOT generalize. If Day-1 shows the resume/checkpoint shape is larger than one sprint, slice (defer the reject path or the frontend leg to a follow-up, keep the approved happy-path drive-through) and re-confirm scope (§9).

---

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **D2 — `wait_for_decision` is blocking; conflicts with release-connection** | the deferred branch does NOT call `wait_for_decision`; it checkpoints + emits + terminates with `awaiting_approval`. Blocking path retained for other callers (additive) |
| **D4 — checkpoint lacks messages / pending tool call** | enrich the checkpoint with `pending_approval` (tool_call + approval_request_id + turn); rebuild messages from the messages DB table in `resume()` |
| **D3 — `resume()` is abstract** | implement `AgentLoopImpl.resume()` for exactly the one pending-tool case this slice; broader resume points deferred (§9) |
| **D5 — migration head 0027; payload column unknown** | Day-0 Prong-3 reads `state_snapshots` schema; prefer enriching the existing JSONB payload (no migration); fallback `0028` adds a column (RLS unchanged) |
| **Multi-tenant leakage on resume** | resume re-derives tenant_id from JWT; rejects checkpoint whose tenant_id ≠ caller (404, no leak); integration asserts cross-tenant 404 (鐵律 1) |
| **Decision read race / un-decided resume** | `ResumeService` rejects if approval not yet decided; `get_decision` is a non-blocking read of the recorded `ApprovalDecision` |
| **Stale message history at resume (hours/days later)** | messages persist per-turn in the messages table (not GC'd in the spike window); design note flags long-horizon retention as an open question (§9) |
| **Drive-through reveals a Potemkin (dead control / not rendered)** | the drive-through IS the acceptance gate; any dead control / un-rendered continuation = not done, fix to working (Drive-Through Acceptance constraint) |
| **Loop control-flow regression** | only the ESCALATE branch + a new `resume()` method change; existing blocking path + happy-path loop untouched; full pytest re-run |
| **`ApprovalRequested`/`LoopCompleted`/`_cat9_hitl_branch` exact shape** | Day-0 Prong-2 reads the real shapes before editing (`AD-Day0-Codegen-Existing-Shape-Capture`) |
| **Scope > 1 sprint** | this slice = ONE deterministic tool-ESCALATE trigger, one pending-tool resume, one drive-through; generalization deferred (§9); Day-1 slice further if needed (§7) |
| **LLM-neutrality** | resume service + endpoint provider-free; `agent_harness/**` only gets the branch + `resume()` + checkpoint fields; `check_llm_sdk_leak` gates |

---

## 9. Out of Scope (this sprint; carryover toward full 地基 A + 地基 B)

- **Generalized pause points** — this slice resumes exactly ONE pending-tool approval; pausing/resuming at arbitrary phases (input ESCALATE, mid-thinking, between turns) is a design-note open question.
- **地基 B explicit cognition phases** (independent thinking / self-critique phases, multi-model profile) — the user's other chosen direction; separate later sprint.
- **Subagent child-loop** — geba A's lifecycle骨架 from this spike feeds it, but the subagent build is a distinct (larger) sprint after 地基 A.
- **Session-list "paused / awaiting approval" indicator + cross-device resume** — this slice drives through within one browser session (stream closes, approve, resume); a session-list paused badge + resume-from-list is a follow-up.
- **Long-horizon message retention / checkpoint TTL** — durability across days assumes messages persist; retention policy is an open question.
- **Notification on approval-needed** (email / webhook to the approver) — out of scope; the approver uses the existing governance approvals view.
- **Replacing the blocking `wait_for_decision` everywhere** — deferred mode is added for the chat path only; the blocking path stays for synchronous callers.
