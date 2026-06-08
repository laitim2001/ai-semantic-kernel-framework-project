# CHANGE-056: Durable HITL Pause-Resume (地基 A keystone)

**Change Date**: 2026-06-08
**Sprint**: 57.88
**Change Type**: New Feature (loop lifecycle mechanism — SPIKE)
**Status**: ✅ Completed (drive-through-verified)
**Scope**: Cat 1 (Orchestrator Loop) + Cat 7 (State Mgmt) + Cat 9 (HITL) + Cat 12 (`awaiting_approval` stop_reason) + platform_layer.resume + chat router/SSE + chat-v2 frontend

## Change Summary

On the production chat path, the blocking `HITLManager.wait_for_decision()` (which held the SSE connection open until a human decided) is replaced by a **durable pause-resume**: a tool guardrail ESCALATE checkpoints the loop, emits `ApprovalRequested`, and terminates with `stop_reason="awaiting_approval"` so the SSE connection is **released**. Hours/days later the human approves via the existing `POST /governance/approvals/{id}/decide`; the client then calls a NEW `POST /chat/{session_id}/resume` which drives the newly-implemented `AgentLoopImpl.resume()` — loading the checkpoint, executing the approved tool, and continuing to `end_turn` on a fresh SSE stream. This is the 地基 A keystone ("Loop 可暫停/可分裂").

## Change Reason

The user's real HITL scenario is **hours-to-days** approval latency. The blocking wait cannot serve it (holds a connection per pending approval). Durable pause-resume releases all resources and re-derives the loop on resume — and is the lifecycle 骨架 the subagent child-loop will reuse.

## Detailed Changes

- **US-1 deferred pause** — `loop.py` `_cat9_hitl_branch` gains a deferred mode (gated on `hitl_deferred + checkpointer + reducer + session_id`; else falls back to blocking): `request_approval` + `ApprovalRequested` (reused) → checkpoint enriched → `LoopCompleted(stop_reason="awaiting_approval")` → return (no `wait_for_decision`). NEW `TerminationReason.AWAITING_APPROVAL`.
- **US-2 resumable checkpoint** — `pending_approval` (pending tool call + approval_request_id + turn) + `resume_messages` (conversation buffer) stored in the existing `state_snapshots` JSONB metadata (pause-only — no bloat on normal checkpoints). **No migration**.
- **US-3 `resume()`** — implements the abstract stub: read `pending_approval` → non-blocking `HITLManager.get_decision` → APPROVED exec pending tool + `_resume_continuation` to end_turn / REJECTED block / undecided fail-closed. NEW `HITLManager.get_decision` (ABC + `DefaultHITLManager`; `wait_for_decision` refactored onto a shared helper, 0 behavior change).
- **US-4 resume endpoint** — NEW `ResumeService.resume_session` (load latest paused checkpoint for (session, tenant) → cross-tenant/no-row → 404 → rebuild loop via the real chat builder, zero divergence) + `POST /chat/{session_id}/resume` SSE endpoint (mirrors chat auth deps).
- **US-5 frontend + drive-through** — `chatService.resumeChat` (+ shared `consumeSSEStream`), `useLoopEventStream.resume()`, `HITLTurn` Approve → decide → `resume()` guarded on `stopReason==="awaiting_approval"`, `chatStore` clears the stale waiting indicator on `loop_start`. Drive-through PASSED (real backend + real Azure gpt-5.2).
- **ESCALATE trigger** — `handler.py` `build_real_llm_handler` wires the real Cat 9 `ToolGuardrail` with a **registry-derived** `CapabilityMatrix` (every exposed tool → PASS rule, `CHAT_HITL_ESCALATE_TOOLS={"echo_tool"}` → `requires_approval`); `hitl_deferred=(hitl_manager is not None)`.

### Two defects the drive-through caught that all gates were green on
1. **Risk Class E** — a stale uvicorn `--reload` spawn-worker (pre-edit code) survived `dev.py restart` and served `:8000` via SO_REUSEADDR → echo never escalated. Fixed by running a clean no-`--reload` uvicorn; a standalone diagnostic proved the on-disk code escalates.
2. **🔴 FK fix** (`router.py:279`) — the chat session row was created in the request's still-open transaction (savepoint), invisible to the HITL manager's own connection during SSE streaming → `request_approval` INSERT raised `approvals_session_id_fkey`. Fixed with `await db.commit()` after `create_session`. Tests skip the observer (`SESSIONS_CHAT_OBSERVER=false`).
3. **🔴 ResumeService HITLManager wire** (`service.py`) — `_default_build_loop` called `build_real_llm_handler` WITHOUT `hitl_manager` → resumed loop's `_hitl_manager=None` → `resume()` failed closed. Fixed by resolving `get_service_factory().get_hitl_manager()` (the same process-singleton the pause used).

## Modified Files List

- `backend/src/agent_harness/orchestrator_loop/loop.py` (deferred branch + `resume()` + `_resume_continuation` + `_emit_state_checkpoint` enrich + `messages_from_metadata` + `hitl_deferred` ctor)
- `backend/src/agent_harness/orchestrator_loop/termination.py` (`AWAITING_APPROVAL`) + `_abc.py` (resume doc) + `__init__.py` (export `messages_from_metadata`)
- `backend/src/agent_harness/hitl/_abc.py` + `backend/src/platform_layer/governance/hitl/manager.py` (`get_decision`)
- `backend/src/platform_layer/resume/service.py` + `__init__.py` (NEW)
- `backend/src/api/v1/chat/handler.py` (ESCALATE matrix + `hitl_deferred`) + `router.py` (resume endpoint + FK `db.commit`)
- `frontend/src/features/chat_v2/{services/chatService.ts, hooks/useLoopEventStream.ts, components/turns/HITLTurn.tsx, store/chatStore.ts}`
- Tests: `backend/tests/unit/agent_harness/orchestrator_loop/test_loop_pause_resume.py` (8) + `backend/tests/integration/api/test_chat_pause_resume_e2e.py` (5) + `frontend/tests/unit/chat_v2/{chatStore.pauseResume.test.ts (3), HITLTurn.resume.test.tsx (3)}`
- Docs: `19-pause-resume-design.md` (NEW) + `17-cross-category-interfaces.md` (§4.1 + §5.2-5.3)

## Test Checklist

- [x] `mypy src/` 0 / 346 files
- [x] `python scripts/lint/run_all.py` 10/10 (LLM SDK leak 0, AP-1, AP-8, RLS, event-schema-sync)
- [x] Full backend `pytest` 2229 passed / 4 skipped
- [x] Frontend `npm run lint` (no `--silent`) + `npx tsc --noEmit` + `npm run build` exit 0
- [x] `npx vitest run` 772 passed / 134 files
- [x] `npm run check:mockup-fidelity` ✓ (oklch baseline 53 unchanged)
- [x] **Drive-through PASS** (chat-v2 UI + real backend + real Azure gpt-5.2): pause → released stream → approve → continuation + final answer rendered; screenshots recorded

## Honest Boundaries (see `19-pause-resume-design.md §5`)

`_resume_continuation` omits run()'s Cat 8 retry / Cat 9 guardrail / Cat 4 compaction (one-approval-per-run this slice); `resume_messages` self-contains the buffer (no `messages` table → checkpoint-bloat); ESCALATE matrix is registry-derived (no per-tenant policy yaml); reject path doesn't resume (dangling checkpoint). All catalogued as carryover ADs.
