# Sprint 57.132 — Checklist (chat-v2 resume-path ledger persistence: tool round-trip + held-answer replay)

[Plan](./sprint-57-132-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `75b177c0`)
- [x] **Prong 1 — path verify**: `loop.py` + `test_loop_pause_resume.py` present; `CHANGE-099` free; plan/checklist paths exist
- [x] **Prong 2 — content verify** (drift → progress.md):
  - [x] **D-resume-store-wired** — `build_real_llm_handler` injects `message_store` (`handler.py:727`) + ResumeService default builder uses it (`service.py:121-132`) → resume loop's persist is NOT a no-op ✅
  - [x] **D-asst-tool-calls** — `messages_from_metadata`/`_message_from_dict` round-trips `tool_calls` (`loop.py:254-269`); `_emit_state_checkpoint` stores `resume_messages` via `_message_to_dict` (`:3604`) ✅
  - [x] **D-persist-sig** — `_persist_to_ledger(msgs, *, turn_num)` signature + best-effort no-op guard (`loop.py:1907-1917`) ✅
  - [x] **D-replay-no-persist** — `_replay_approved_output` (`loop.py:3505-3556`) has NO `_persist_to_ledger` today (gap confirmed) ✅
- [x] **Prong 3 — schema verify**: N/A (no new DB table / migration / ORM column — reuses `messages` ledger)
- [x] **D-baselines** — pytest 2727+5skip · run_all 10/10 (wire 25 in-sync) · mypy 0/372 (Vitest/mockup untouched — pure backend)
- [x] **Catalog drift** — progress.md Day-0 table (all GREEN, 0% scope shift)
- [x] **Go/no-go** — both legs confirmed feasible (store wired + serde keeps tool_calls) → proceed

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-132-chatv2-resume-ledger-persist` (from `main` `75b177c0`)

---

## Day 1 — Leg 1: resume() tool round-trip persist (US-1)

### 1.1 Persist the paused-then-approved tool round-trip
- [x] **`loop.py` resume() tool-kind APPROVED branch (~3449): persist `messages[asst_idx:]`**
  - backward-scan `asst_idx` = last `role == "assistant"`; `if asst_idx is not None: await self._persist_to_ledger(messages[asst_idx:], turn_num=turn_count)`
  - placed AFTER the `tool` result append, BEFORE the shared `_run_turns` drive ✅
  - DoD: a tool-kind resume with a store persists exactly `[assistant tool_use, *tool results]` as ONE append; REJECTED/undecided never persist ✅
  - Verify: `pytest ...test_loop_pause_resume.py -q` → 35 passed

### 1.2 `_persist_to_ledger` docstring (Karpathy §3 keep-true)
- [x] **generalize "from the TOOL_USE branch" → "+ the resume() tool-approval + held-answer replay paths (57.132)"** ✅

### 1.3 Leg-1 tests — `test_loop_pause_resume.py`
- [x] **add a recording `MessageStore` fake + `message_store` param on the resume loop builder** (default None keeps existing callers green) ✅
- [x] **`test_resume_tool_roundtrip_persisted_atomically`** — exactly one append carrying a tool_use; batch = `[assistant, tool]`; assistant keeps tool_calls; tool has tool_call_id ✅
- [x] **`test_resume_tool_roundtrip_no_store_is_noop`** — tool-kind APPROVED, store=None → no crash (baseline) ✅
  - Verify: 35 passed (31 baseline + 4 new)

### 1.x Partial gate
- [x] mypy `src` 0/372 · black/isort/flake8 on the 2 files ✅

---

## Day 2 — Leg 2: held-answer replay persist (US-2) + full gate

### 2.1 Persist the delivered held answer
- [x] **`loop.py` `_replay_approved_output` (~3544): persist `[assistant(answer_text)]`**
  - after `yield Thinking(...)`, before `yield LoopCompleted(...)`; `if answer_text:` guard ✅
  - DoD: an output-kind (and verification-kind) APPROVE persists the held answer to the ledger ✅
  - `_replay_approved_output` docstring notes the persist ✅

### 2.2 Leg-2 test
- [x] **`test_resume_output_approved_persists_held_answer`** — `_paused_output_state` + store, APPROVED → `store.appended` contains `assistant("the held confidential answer")` ✅
- [x] **`test_resume_output_rejected_persists_nothing`** — output-kind REJECTED → block + `store.appended == []` ✅ (split into its own test → +4 total)

### 2.x Full gate
- [x] mypy `src` 0/372 · run_all 10/10 (wire 25 in-sync) · backend pytest 2731 passed/5 skip (+4) · Vitest/mockup UNTOUCHED (pure backend) · black/isort/flake8 clean · LLM-SDK-leak clean ✅

---

## Day 3 — Drive-through (US-3) — real UI + real backend + real LLM

### 3.1 Clean restart (Risk Class E)
- [x] killed stale :8000 (PID 14736, old code, no `--reload` → no orphan workers); started fresh PID 54504 (my code, "startup complete" + "pricing loader wired", sole owner); FE Vite untouched ✅

### 3.2 Drive-through (MANDATORY — NOT gate-only)
- [x] set HITL policy MEDIUM=always_ask (PUT hitl-policies auto=LOW/require=MEDIUM) → python_sandbox ESCALATEs → deferred pause ✅
- [x] **Leg 1**: turn 1 python_sandbox → HITL approval card (MEDIUM, approval_id b43f986b…) → pause ✅
- [x] **Leg 1**: clicked **Approve & continue** (UI) → resume → python_sandbox ran → answer "ODD" + verification 0.99 ✅
- [x] **Leg 1**: follow-up "duration_seconds?" (POST {message,session_id} only) → **"0.031"** (un-deducible; rehydrated from seq-3 tool result); messages_count 4→5→8 ✅
- [x] **Leg 1 DB verify**: ledger 4 rows — seq=2 assistant tool_use(python_sandbox) + seq=3 tool result **persisted AT RESUME** (the fix) ✅ (artifacts/verify_ledger.py)
- [x] Screenshot (`artifacts/drivethrough-57132-leg1-resume-ledger-PASS.jpeg`) + observed-vs-intended → progress.md Day 3 ✅
- [~] **Leg 2** (output/verification held-answer): real-LLM output-escalate did NOT trigger deterministically (no pause/ledger row — content-filter/LLM-phrasing non-determinism). **Honest: Leg-2 = unit + composition verified (NOT UI drive-through)** — 2 unit tests on the real resume()→`_replay_approved_output`→persist path + the persist primitive runtime-proven by Leg-1. Carryover `AD-ChatV2-Resume-Replay-Drive-Through` (deterministic escalate fixture).

---

## Day 4 — CHANGE-099 + closeout

### 4.1 CHANGE-099
- [x] **`CHANGE-099-chatv2-resume-ledger-persist.md`** (gap + 2-leg fix + drive-through PASS + AD closed). NO design note (continuation of 57.127/129 ledger) ✅

### 4.2 Closeout
- [x] retrospective.md Q1-Q7 + calibration (`chatv2-resume-ledger-persist-wiring` 0.70 → **re-pointed 0.85**, 1st pt ratio ~1.4-1.6 over) ✅
- [x] Final gate sweep: mypy 0/372 · run_all 10/10 · pytest 2731+5skip · black/isort/flake8 clean · Vitest/mockup UNTOUCHED · LLM-SDK-leak clean ✅
- [x] Navigators: CLAUDE.md Current-Sprint + Last-Updated · MEMORY.md pointer + subfile · next-phase-candidates (CLOSED `AD-ChatV2-Resume-Tool-RoundTrips` + sibling; NEW `AD-ChatV2-Resume-Replay-Drive-Through`) · sprint-workflow matrix (`chatv2-resume-ledger-persist-wiring` row) ✅
- [x] Anti-pattern self-check (retro Q5): AP-2/3/4/6/8/11 → 0 violations; v2 lints 10/10 ✅
- [x] **Commit** `6c3c898a` (11 files, +627) → ⏳ PR push + open → CI → merge: **PENDING USER CONFIRMATION** (push is outward-facing per Developer Preferences) → post-merge status flip after gh-verified MERGED
