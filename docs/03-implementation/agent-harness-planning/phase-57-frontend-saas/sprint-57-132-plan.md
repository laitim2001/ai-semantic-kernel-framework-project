# Sprint 57.132 Plan — chat-v2 resume-path ledger persistence

**Summary**: Two resume-path legs that close `AD-ChatV2-Resume-Tool-RoundTrips` (57.129 carryover) and a sibling gap surfaced during recon. The HITL resume path appends its out-of-loop messages (the paused-then-approved tool's round-trip; the output/verification held answer) to the in-memory buffer but never persists them to the `messages` Cat-3 ledger — so a follow-up send after a resumed turn rehydrates an incomplete conversation. The user (AskUserQuestion 2026-06-17) picked the **comprehensive** scope: fix BOTH the tool round-trip persist (Leg 1) AND the held-answer replay persist (Leg 2). PURE backend (1 src `loop.py` + 1 test edit); a drive-through is MANDATORY (HITL pause→approve→resume→follow-up is user-driven). NO design note (continuation of the 57.127/129 `messages` ledger).

**Status**: Approved-to-execute (user AskUserQuestion 2026-06-17 — picked "修全部 resume-path persist 缺口" over "只做 tool round-trip 字面 AD")
**Branch**: `feature/sprint-57-132-chatv2-resume-ledger-persist`
**Base**: `main` HEAD `75b177c0` (Sprint 57.131 — chat-v2 Inspector Turn model row + REFACTOR-008 template freeze, #309)
**Slice**: closes `AD-ChatV2-Resume-Tool-RoundTrips` (57.129 carryover) + sibling `AD-ChatV2-Resume-Replay-Answer-Persistence` (folded in per user scope). Standalone (not part of a multi-sprint arc; extends the 57.127→129 `messages` ledger to the resume path).
**Scope decisions**: (a) comprehensive — both legs in one sprint; (b) Leg 1 mirrors the 57.129 batch-persist contract (one atomic `[assistant tool_use, *tool results]` append, dangling-free); (c) the verification-REJECTED correction note is intentionally NOT persisted (it is an internal one-shot instruction, not conversation; the coached answer is already persisted by `_run_turns` end_turn); (d) input/between_turns kinds need NO change (no out-of-loop append → no gap).

---

## 0. Background

### The gap (AD-ChatV2-Resume-Tool-RoundTrips + sibling held-answer gap)

The 57.127 `messages` Cat-3 ledger gives chat-v2 multi-turn context: `run()` self-loads the prior conversation + persists each turn's messages, and 57.129 added the intra-turn tool round-trip persist — BUT only inside `_run_turns`. The **HITL resume path** (`loop.resume()`) does its approval-specific work OUTSIDE `_run_turns`:

- **Leg 1 (tool-kind)**: a paused-then-APPROVED tool is executed outside the loop; its `[assistant tool_use, tool result]` round-trip is appended to the in-memory buffer but never persisted.
- **Leg 2 (output/verification-kind)**: an APPROVED held final answer is re-emitted by `_replay_approved_output` (a TERMINAL path, no `_run_turns` drive) and never persisted.

### Why it matters (the missing capability)

After a user approves a paused tool (or an escalated answer) and the turn completes, the next send `load()`s a ledger that is MISSING the approved tool's round-trip / the held answer. The follow-up therefore can't reference what the approved tool returned (the exact 57.129-class bug, but on the resume path) or the delivered held answer — a silent multi-turn-context hole specific to HITL sessions.

### Root cause (recon code read, file:line; ALL re-verified §checklist 0.1)

| Layer | Reality (on `main` HEAD `75b177c0`) | Anchor |
|-------|-------------------------------------|--------|
| resume() tool-kind APPROVED | execs the pending tool OUTSIDE `_run_turns`, appends the `tool` result, drives `_run_turns` — never persists the round-trip | `loop.py:3413-3449` |
| run-path tool persist (57.129) | fires ONLY inside `_run_turns` TOOL_USE branch; at pause the cat9 ESCALATE early-returns BEFORE it | `loop.py:3098` / `:2786` |
| _replay_approved_output (output/verification APPROVED) | re-emits LLMResponded + Thinking + LoopCompleted; NO `_persist_to_ledger` | `loop.py:3505-3556` |
| resume loop HAS a message_store | ResumeService default builder = `build_real_llm_handler` which injects `message_store=message_store` → the persist is NOT a no-op | `service.py:121-132` / `handler.py:544,727` |
| rehydrated assistant tool_use keeps tool_calls | `messages_from_metadata` uses `_message_from_dict` (same serde 57.129 round-trips) | `loop.py:254-269` / `:3604` |

→ The fix must persist the resume path's out-of-loop messages to the same ledger, mirroring the 57.129 batch contract (a complete, well-formed unit — never a dangling tool_use).

### The design (PURE backend: 2 `loop.py` persist calls + tests)

```
# Leg 1 — resume() tool-kind APPROVED (loop.py ~3449, the `else` branch)
messages.append(Message(role="tool", content=tool_content, tool_call_id=pending_tc.id))   # existing
# NEW: persist the paused tool's complete round-trip ([assistant tool_use, *tool results]).
asst_idx = last index i where messages[i].role == "assistant"   # backward scan
if asst_idx is not None:
    await self._persist_to_ledger(messages[asst_idx:], turn_num=turn_count)

# Leg 2 — _replay_approved_output (loop.py ~3544, before yield LoopCompleted)
# NEW: persist the delivered held answer so a follow-up rehydrates it.
if answer_text:
    await self._persist_to_ledger([Message(role="assistant", content=answer_text)], turn_num=turn_count)
```

Backward-scan to the last `assistant` (not `messages[-1]-1`) makes Leg 1 robust to a multi-call turn where an earlier tool already executed before the escalated one (the slice then captures the complete `[assistant(N calls), tool(tc0)…, tool(tcN)]`). `if asst_idx is not None` skips the (unreachable) malformed bare-tool case rather than persisting a dangling tool.

### Ground truth (recon head-start — code read on `main` HEAD `75b177c0`; ALL re-verified §checklist 0.1)

- `loop.py:1907-1917` — `_persist_to_ledger(msgs, *, turn_num)` = best-effort `self._message_store.append(msgs, turn_num)`; no-op when store is None or msgs empty.
- `loop.py:3449` — the tool-kind APPROVED branch appends the `tool` result; the rehydrated buffer's last `assistant` carries the pending tool_call.
- `loop.py:3510` — `_replay_approved_output` already receives `turn_count` + `answer_text`.
- `handler.py:727` — `build_real_llm_handler` injects `message_store`; ResumeService uses it as the default builder (zero divergence).
- `test_loop_pause_resume.py` — `_paused_state` (tool-kind, messages=[user, assistant(tool_use)]) + `_paused_output_state` (response_snapshot.answer_text) + `SpyHITLManager` + `_build_resume_loop` already exist to mirror.

**Baselines (57.131 closeout)**: pytest ~2732 · wire 25 · Vitest 911 · mockup 51 · mypy 0/372 · run_all 10/10. Re-verify Day-0.

### STALE / drift findings (Day-0; full detail → progress.md — placeholder, filled in §checklist 0.1)

- **D-resume-store-wired** — confirm ResumeService → `build_real_llm_handler` → `message_store` is injected on the resume loop (else the persist is a silent no-op + drive-through fails).
- **D-asst-tool-calls** — confirm the rehydrated assistant tool_use retains `tool_calls` after `messages_from_metadata` (else a persisted bare tool breaks a follow-up LLM request).
- **D-baselines** — re-verify pytest / wire / mypy / run_all counts on `75b177c0`.

## 1. Sprint Goal

Close `AD-ChatV2-Resume-Tool-RoundTrips` (+ the sibling held-answer gap) so a chat-v2 follow-up after a HITL resume rehydrates the COMPLETE conversation — the approved tool's round-trip AND any delivered held answer. Proven by: gates green (mypy/run_all/pytest + new resume-persist unit tests) AND a MANDATORY drive-through (real UI + backend + Azure: a paused tool → approve → resume → a follow-up that references the approved tool's result, with the DB `messages` ledger showing the persisted round-trip). CHANGE-099; no design note.

## 2. User Stories

- **US-1** (Leg 1 — tool round-trip persist): 作為一個 chat-v2 使用者，我希望在批准一個暫停的工具後，後續訊息仍記得該工具回傳的內容，以便延續對話而不必重述。
- **US-2** (Leg 2 — held-answer replay persist): 作為一個 chat-v2 使用者，我希望在批准一個被攔截升級的答案後，後續訊息仍記得該答案，以便引用它。
- **US-3** (drive-through MANDATORY): 作為開發者，我要在真 UI + 真後端 + 真 LLM 上實際走完 pause→approve→resume→follow-up，並用 DB ledger 驗證 round-trip 已持久化。
- **US-4** (closeout): 作為維護者，我要 CHANGE-099 + retrospective + calibration + navigators 更新，AD 標 CLOSED。

## 3. Technical Specifications

### 3.0 Architecture (PURE backend; NO new ABC / event / wire / codegen / migration / frontend)

```
EDIT  backend/src/agent_harness/orchestrator_loop/loop.py
        - resume() tool-kind APPROVED branch (~3449): + persist the paused tool round-trip
        - _replay_approved_output (~3544): + persist the delivered held answer
        - _persist_to_ledger docstring (~1910): generalize "from TOOL_USE branch" → "+ resume path"
EDIT  backend/tests/unit/agent_harness/orchestrator_loop/test_loop_pause_resume.py
        - + a recording MessageStore + a message_store param on the resume builder
        - + Leg-1 tests (tool round-trip persisted atomically; rehydrates)
        - + Leg-2 test (held answer persisted on output/verification APPROVE)
UNTOUCHED  message_serde.py / message_store.py / DBMessageStore / handler.py / router.py / service.py
           (the store + serde + wiring already exist; this only adds 2 call sites)
```

### 3.1 Leg 1 — resume() tool-kind round-trip persist (US-1) — `loop.py`

- In the tool-kind APPROVED branch, immediately after `messages.append(Message(role="tool", …))` (`:3449`), compute `asst_idx` = the last index with `role == "assistant"` (backward scan); if found, `await self._persist_to_ledger(messages[asst_idx:], turn_num=turn_count)`.
- Mirrors the 57.129 contract: one atomic append of the complete `[assistant tool_use, *tool results]` unit; reached only after a successful approval+exec (REJECTED/undecided branches return earlier → never persist a dangling tool_use).

### 3.2 Leg 2 — held-answer replay persist (US-2) — `loop.py`

- In `_replay_approved_output`, after `yield Thinking(...)` and before `yield LoopCompleted(...)`: `if answer_text: await self._persist_to_ledger([Message(role="assistant", content=answer_text)], turn_num=turn_count)`.
- Covers BOTH output-kind (57.93) and verification-kind (57.99 A2) APPROVED (both deliver via `_replay_approved_output`). Mirrors the run() end_turn answer-persist shape.

### 3.3 What is explicitly NOT done

- verification-REJECTED correction note (`loop.py:3373`) — an internal one-shot revise instruction, NOT conversation; the coached turn's answer IS persisted by `_run_turns` end_turn. Persisting the note would pollute multi-turn context. Intentionally skipped.
- input / between_turns kinds — no out-of-loop append; the continuation's `_run_turns` already persists everything. No change.
- No new ABC / event / wire schema / codegen / migration / frontend.

### 3.4 Validation (US-1..US-4)

Gates: mypy `src` 0/372 · run_all 10/10 (wire 25) · pytest ~2732 + new · Vitest 911 (UNCHANGED — pure backend) · mockup 51 (UNCHANGED) · `npm run lint && npm run build` (NO `--silent`; UNCHANGED) · black/isort/flake8 clean · LLM-SDK-leak clean. Plus the §3 drive-through (MANDATORY).

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/agent_harness/orchestrator_loop/loop.py` | EDIT (2 persist call sites + 1 docstring) |
| 2 | `backend/tests/unit/agent_harness/orchestrator_loop/test_loop_pause_resume.py` | EDIT (recording store + resume builder param + 3 tests) |
| 3 | `claudedocs/4-changes/feature-changes/CHANGE-099-*.md` | NEW |
| — | `message_serde.py` / `state_mgmt/message_store.py` / `api/v1/chat/handler.py` / `router.py` / `platform_layer/resume/service.py` | **UNTOUCHED** |
| — | wire schema / codegen / Alembic migration / `frontend/**` | **UNTOUCHED** |

## 5. Acceptance Criteria

1. resume() tool-kind APPROVED persists `[assistant tool_use, *tool results]` as ONE atomic ledger append (unit test asserts the batch + dangling-free).
2. `_replay_approved_output` persists `[assistant(answer_text)]` for output/verification APPROVED (unit test asserts the held answer reaches the ledger).
3. Existing resume tests + the full suite stay green; no wire/codegen/migration/frontend change.
4. **Drive-through PASS (MANDATORY, real UI + backend + LLM)** — pause a real tool → approve → resume → a follow-up references the approved tool's result; DB `messages` ledger shows the persisted round-trip rows. Screenshot + observed-vs-intended in progress.md. (NOT gate-only.)
5. `AD-ChatV2-Resume-Tool-RoundTrips` (+ sibling) CLOSED; CHANGE-099; calibration recorded; navigators + next-phase-candidates updated.

## 6. Deliverables

- [ ] US-1 Leg 1 tool round-trip persist in resume()
- [ ] US-2 Leg 2 held-answer persist in `_replay_approved_output`
- [ ] US-3 drive-through PASS (real UI + backend + Azure) + DB ledger verify
- [ ] US-4 CHANGE-099 + closeout (retro + calibration + navigators)

## 7. Workload Calibration

- Scope class **`chatv2-resume-ledger-persist-wiring` 0.70** (NEW class, 1st data point). Between 57.128's `chatv2-resume-persistence-wiring` 0.55 (message_events resume persist, 1 leg, ran ~1.13 near band top → under-calibrated) and 57.129's `chatv2-ledger-tool-roundtrips-wiring` 0.85 (ceremony-heavy). This is resume-path × `messages` ledger × 2 legs with the HEAVIEST drive-through (HITL pause→approve→resume setup). Same "ceremony-not-code-accelerated" insight (57.120/122/123/126/129): tiny code (~8 lines) but a mandatory HITL drive-through dominates wall-clock. KEEP pending 2-3 sprint validation.
- **Agent-delegated: no** (parent-direct — surgical 2-call-site edit + targeted tests; no code-implementer agent). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~5.0 hr (code ~0.5 · tests ~1.0 · plan/checklist/Day-0 ~1.0 · drive-through w/ HITL setup ~1.5-2.0 · docs/closeout ~1.0) → class-calibrated commit ~3.5 hr (mult 0.70). Day-4 retro Q2 verifies.

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| resume loop has no message_store → persist is a silent no-op | Day-0 D-resume-store-wired confirms `build_real_llm_handler` injects it (`handler.py:727`); drive-through DB verify is the end-to-end proof |
| persisted bare tool (no preceding assistant) breaks a follow-up LLM request | backward-scan to last `assistant` + `if asst_idx is not None` skip; D-asst-tool-calls confirms serde keeps tool_calls |
| Risk Class E — stale `--reload` / orphan spawn-worker serves old code on :8000, masking the fix at drive-through | clean restart + verify the sole LIVE worker (Win32_Process PID/PPID/StartTime sweep) before driving; capture startup log |
| HITL drive-through setup cost (default policy escalates MEDIUM tools to the resume path; need per-tenant policy + a real escalating tool) | reuse the 57.128/129 drive-through recipe (admin PUT HITL policy + python_sandbox/escalate trigger) |
| Risk Class C — module-singleton across test event loops | unit tests use injected fakes (no module singleton); N/A but watch if a TestClient integration test is added |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- verification-REJECTED correction-note persist — intentionally not a gap (see §3.3); no AD.
- `message_events` / `messages` ledger consolidation; `turn_num` cross-send counter; pg_partman — deferred infra (next-phase-candidates).
- Any frontend change — the replay/rehydration is backend; the FE already renders rehydrated context.
