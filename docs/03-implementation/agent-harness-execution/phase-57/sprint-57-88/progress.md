# Sprint 57.88 Progress — durable HITL pause-resume spike (地基 A keystone)

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-88-plan.md`
**Branch**: `feature/sprint-57-88-pause-resume` (from `41f1ed05`)

---

## Day 0 — 2026-06-08 — Plan-vs-Repo Verify + Branch

### Branch
- `feature/sprint-57-88-pause-resume` created; plan + checklist committed (`65ab34fc`).

### Three-prong verify (GO)

**Prong 1 (path)** — all anchors confirmed: `loop.py` `_cat9_hitl_branch` L552-697; `_abc.py:63-71` `resume()` abstract; `checkpointer.py:118-181` save/load; `_contracts/events.py:382/388` Approval events; `_contracts/hitl.py:55/69` ApprovalRequest/Decision; `hitl/_abc.py` HITLManager; `platform_layer/governance/hitl/manager.py` DefaultHITLManager; `governance/router.py` decide endpoint; `chat/router.py` L138 + `_stream_loop_events`; `infrastructure/db/models/state.py` StateSnapshot.

**Prong 2 (content)** — exact shapes captured:
- `ApprovalRequested(LoopEvent)`: `approval_request_id: UUID|None`, `risk_level: str` (events.py:382).
- `ApprovalReceived(LoopEvent)`: `approval_request_id: UUID|None`, `decision: str` (events.py:388).
- `ApprovalDecision`: `request_id, decision: DecisionType, reviewer, decided_at, reason` (hitl.py:69).
- `LoopCompleted`: `stop_reason: str = "end_turn"` + totals + 57.68 handoff_* + 57.82 verification_* fields (events.py:127+).
- `_cat9_hitl_branch(self, *, tc, ctx, guardrail_reason) -> AsyncIterator[LoopEvent]` (loop.py:552): request_approval (L620) → ApprovalRequested (L645) → **wait_for_decision (L654, BLOCKING)** → ApprovalReceived (L681) → APPROVED returns (caller executes tool, L687) / REJECTED→GuardrailTriggered (L692).
- `HITLManager` methods: `request_approval / wait_for_decision / get_pending / decide / get_policy` — **NO non-blocking get_decision** (must add).
- chat `_stream_loop_events` ends on seeing `LoopCompleted` (no stop_reason gate) → emitting `awaiting_approval` stop_reason closes the stream cleanly. ✅
- chat endpoint deps: `get_current_tenant / get_current_user_id / get_service_factory / get_db_session` (router.py:138) → resume endpoint mirrors these.

**Prong 3 (schema)** — `StateSnapshot` (state.py:75): `id, session_id, tenant_id (TenantScopedMixin+RLS), version, parent_version, turn_num, state_data: JSONB, state_hash, reason, created_at`. ✅ `state_data` JSONB holds `pending_approval` → **NO migration**. Migration head `0027`. ✅

### Drift findings

- **D-DAY0-1** — No non-blocking `get_decision` on HITLManager (only blocking `wait_for_decision` poll-loop). → add `get_decision(request_id) -> ApprovalDecision | None` to ABC + DefaultHITLManager (single read of the `approvals` table where `status != PENDING`). _Implication: US-3._
- **D-DAY0-2** — `state_snapshots.state_data` is JSONB → **免 migration** (enrich payload). _Implication: drop conditional `0028`; US-2 thinner._
- **D-DAY0-3** — chat SSE stream ends on `LoopCompleted` (no stop_reason gate) → `awaiting_approval` closes stream cleanly; frontend distinguishes via stop_reason. _Implication: §3.5 confirmed, no router stream-end change needed._
- **D-DAY0-4** — `_cat9_hitl_branch` APPROVED/REJECTED split is simple (L687-697) → easy to add a `deferred` branch (checkpoint + emit + `awaiting_approval` terminate) before the `wait_for_decision` call. _Implication: US-1 low-risk._
- **D-DAY0-5** — No chat `resume` endpoint + no `AgentLoopImpl.resume()` impl (abstract). → build both (US-3/US-4). _As planned._
- **D-DAY0-6** — Approval event dataclasses CONFIRMED (events.py:382/388) — earlier "inferred" resolved. _No risk._
- **D-DAY0-7 (plan correction)** — `TerminationReason` is an **Enum in `orchestrator_loop/termination.py:52`** (NOT `_contracts/events.py` as plan §3.1/§4 stated); existing values incl. `HANDOFF`, `CANCELLED`, `END_TURN`, `GUARDRAIL_BLOCKED`, `TRIPWIRE`, `MAX_TURNS`, `TOKEN_BUDGET`, `ERROR`. → add `AWAITING_APPROVAL = "awaiting_approval"` there; mirror the `handoff` stop_reason pattern at loop.py:1313.
- **D-DAY0-8** — Frontend `chat_v2` exists + rich (store/chatStore.ts, hooks/useLoopEventStream.ts, services/chatService.ts, components/ApprovalCard.tsx, turns/HITLTurn.tsx, blocks/*, generated/loopEvents.generated.ts). Day-0 verify agent's "not found" was a search miss. _Implication: frontend leg feasible as planned._
- **design note**: `19-*.md` free in planning root (18-handoff, then 20-iam…; 19 skipped) → `19-pause-resume-design.md` confirmed.

### go/no-go = **GO** (scope unchanged; migration dropped per D-DAY0-2; enum location corrected per D-DAY0-7)

---

## Day 1 — 2026-06-08 — Backend core (Stage 1)

Agent-delegated (code-implementer) + **parent re-verify (gates run by parent, not trusted from report)**.

### Done (US-1/US-2/US-3 backend)
- **US-1 deferred pause** — `TerminationReason.AWAITING_APPROVAL` added (`termination.py:63`, parent). `loop.py` `_cat9_hitl_branch` two-mode: deferred (gated on `hitl_deferred + checkpointer + reducer + session_id`; else falls back to blocking) → `request_approval` + `ApprovalRequested` (reused) → checkpoint enriched + `LoopCompleted(awaiting_approval)` → return (NO `wait_for_decision`). `AgentLoopImpl.__init__ += hitl_deferred: bool = False` (existing blocking behavior fully preserved). Main loop's `cat9_terminated → return` (loop.py:1366) propagates the terminate (tool NOT executed).
- **US-2 resumable checkpoint** — pending_approval `{tool_call{name,arguments,tool_call_id}, approval_request_id, turn}` stored in `DurableState.metadata["pending_approval"]` (already round-trips via `_serialize/_deserialize_state_for_db` JSONB) → **NO migration** (per D-DAY0-2).
- **US-3 resume** — `HITLManager.get_decision(request_id) -> ApprovalDecision | None` (ABC + `DefaultHITLManager`, shared `_read_decision_if_decided` helper; `wait_for_decision` refactored onto it, zero behavior change). `AgentLoopImpl.resume()` implemented (replaces stub): read pending_approval → get_decision → APPROVED exec pending tool + append observation + `_resume_continuation` to end_turn / REJECTED→block / undecided→fail-closed.

### Parent re-verify (gates run by parent)
- `mypy src/` **0 issues / 344 files** ✅
- `pytest tests/unit/.../orchestrator_loop/ + escalation e2e` **56 passed** ✅ (incl. 8 new `test_loop_pause_resume.py`: deferred pause / blocking regression / get_decision pending↔decided / resume approved+rejected+undecided)
- `python scripts/lint/run_all.py` **10/10 green** ✅ (AP-1 / promptbuilder AP-8 / llm_sdk_leak / sole_mutator / rls / event_schema_sync …)
- Code read (parent): deferred branch + `resume()` + `_resume_continuation` — write↔read `pending_approval` shape consistent.

### ⚠️ Carried fidelity caveat (→ design note §open-questions; honest boundary, NOT a Potemkin)
- **`_resume_continuation` is a SECOND, reduced copy of run()'s loop body** — a real while-true (passes AP-1) that goes through PromptBuilder.build() (passes AP-8) + honors max_turns/token_budget, BUT **deliberately omits run()'s Cat 8 retry / Cat 9 guardrail+tripwire / Cat 4 compaction / per-turn checkpoint+span** (docstring loop.py:1890-1896 + plan §9). OK for the spike happy-path drive-through (approved tool → LLM收尾, no second escalating tool call), but **production needs run()'s core refactored into a shared re-enterable loop** (or resume to re-arm full machinery). Also: continuation cannot itself pause again (no checkpoint) — one-approval-per-run this slice.
- Minor: `_cat9_hitl_branch` added `session_id` param is shadowed by `ctx.session_id` (loop.py:616) — dead param, harmless (left per Karpathy §3).

### Files changed (Stage-1)
- `agent_harness/orchestrator_loop/loop.py` (deferred branch + resume + _resume_continuation + _emit_state_checkpoint + hitl_deferred ctor + thread state/turn)
- `agent_harness/orchestrator_loop/termination.py` (AWAITING_APPROVAL) + `_abc.py` (resume docstring)
- `agent_harness/hitl/_abc.py` + `platform_layer/governance/hitl/manager.py` (get_decision)
- `tests/unit/agent_harness/orchestrator_loop/test_loop_pause_resume.py` (NEW, 8) + `tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py` (FakeHITLManager.get_decision)

### Next: Day 2 — Stage-2 (ResumeService + `POST /chat/{id}/resume` + integration tests + multi-tenant)

---

## Day 2 — 2026-06-08 — Resume endpoint + platform service (Stage 2)

Agent-delegated (code-implementer) + **parent re-verify (gates run by parent + ResumeService/endpoint/tests read by parent)**.

### Two grounding-driven decisions (locked in spec)
- **Decision A — wire `hitl_deferred=True`** in chat path: `handler.py` `build_real_llm_handler` → `AgentLoopImpl(..., hitl_deferred=(hitl_manager is not None))`. Without this the deferred branch never activates (Day-2 grounding caught it; checkpointer/reducer/hitl_manager were already injected).
- **Decision B — checkpoint self-contains messages** (no `messages` table exists in the codebase): the deferred-pause `_emit_state_checkpoint` writes `metadata["resume_messages"]` (pause-only — normal post_llm/post_tool checkpoints stay empty, no bloat). ResumeService rehydrates `transient.messages` from it. Production should use a messages table / bounded summary (checkpoint-bloat = design-note open question, plan §9).

### Done (US-4/US-5 backend)
- **ResumeService** (`platform_layer/resume/service.py` NEW) — `resume_session(*, session_id, tenant_id, user_id, db) -> ResumeResult | None`: latest `reason="orchestrator_loop:hitl_pause"` snapshot for **(session_id, tenant_id)** (cross-tenant → no row → None → 404, 鐵律) → `DBCheckpointer.load(version)` → overlay messages from metadata → build loop via injected `build_loop` (default = real `build_real_llm_handler`, **zero divergence**). `messages_from_metadata` + msg↔dict helpers in `loop.py` (exported via `__init__`).
- **`POST /chat/{session_id}/resume`** (`router.py`) — `Depends(get_current_tenant / get_current_user_id / get_db_session / get_resume_service)` (mirrors chat auth); None → 404; `StreamingResponse(_stream_resume_events)` (drives `loop.resume()`, reuses `serialize_loop_event`).
- Builder extraction → abandoned (>60-line closure churn); ResumeService reuses `build_real_llm_handler` directly + `build_loop` DI for tests (the spec's sanctioned fallback).

### Parent re-verify (gates run by parent)
- `mypy src/` **0 issues / 346 files** ✅
- `pytest` pause-resume e2e + chat_e2e + escalation + orchestrator_loop unit → **71 passed** ✅; implementer's wider sweep: chat/hitl/checkpointer 49 + integration/api 435 green.
- `python scripts/lint/run_all.py` **10/10 green** ✅
- Code read (parent): ResumeService tenant-guard ✓; endpoint `Depends` wiring ✓ (the gap the coroutine-test can't reach); 5 integration tests **genuine** (real loop.run → ESCALATE → checkpoint → real governance decide → resume_chat → tool exec / end_turn; + reject + cross-tenant 404 + no-paused 404).

### Test-design note (honest)
- Integration tests drive the endpoint **coroutines directly** (not via TestClient HTTP) — shared asyncpg `db_session` is bound to the test loop; TestClient's portal loop → "Future attached to a different loop" (Risk Class C). Still exercises the REAL `resume_chat` + `decide_approval` + ResumeService + `loop.resume()` + SSE serializer; **only HTTP transport is bypassed** (covered by the Day-4 chat-v2 drive-through). The `Depends()` auth wiring (which the coroutine call bypasses) was parent-read-verified instead.

### Files changed (Stage-2)
- `api/v1/chat/handler.py` (hitl_deferred wire) · `api/v1/chat/router.py` (resume endpoint + `_stream_resume_events` + `get_resume_service`)
- `agent_harness/orchestrator_loop/loop.py` (msg↔dict helpers + `_emit_state_checkpoint` resume_messages) + `__init__.py` (export `messages_from_metadata`)
- `platform_layer/resume/service.py` + `__init__.py` (NEW) · `tests/integration/api/test_chat_pause_resume_e2e.py` (NEW, 5)

### Next: Day 3 — Stage-3 frontend (chat-v2 paused state + approve→decide→resume→new stream) → Day 4 drive-through + design note

---
