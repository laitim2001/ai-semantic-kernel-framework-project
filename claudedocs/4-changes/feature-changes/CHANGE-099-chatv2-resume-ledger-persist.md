# CHANGE-099: chat-v2 resume-path ledger persistence (tool round-trip + held-answer replay)

**Date**: 2026-06-17
**Sprint**: 57.132
**Scope**: 範疇 1 (Orchestrator Loop) + 範疇 3 (Memory / `messages` ledger) — backend only

## Problem

The 57.127 `messages` Cat-3 ledger (multi-turn context) + 57.129 intra-turn tool round-trip persist both live INSIDE `_run_turns`. The HITL **resume path** (`loop.resume()`) does its approval-specific work OUTSIDE `_run_turns`, so two kinds of resume-path message were appended to the in-memory buffer but NEVER persisted to the ledger:

- **Leg 1 (tool-kind)** — `AD-ChatV2-Resume-Tool-RoundTrips` (57.129 carryover): a paused-then-APPROVED tool's `[assistant tool_use, tool result]` round-trip. The assistant tool_use was rehydrated from the pause checkpoint (so the 57.129 `_run_turns` persist never ran — the cat9 ESCALATE early-returns before it); the tool result is appended in `resume()` itself.
- **Leg 2 (output/verification-kind)** — sibling gap surfaced during recon: an APPROVED held final answer delivered by the TERMINAL `_replay_approved_output` (no `_run_turns` drive → no end_turn persist).

Effect: after a HITL resume, a follow-up send `load()`s a ledger missing the approved tool's round-trip / the held answer → it can't reference what the approved tool returned or the delivered answer. The same multi-turn-context hole 57.129 fixed for the send path, but on the resume path.

The user (AskUserQuestion 2026-06-17) chose the **comprehensive** scope: fix BOTH legs.

## Root Cause

- `resume()` tool-kind APPROVED branch (`loop.py:3413-3449`) appends the tool result OUTSIDE `_run_turns` and drives the continuation without persisting the round-trip.
- `_replay_approved_output` (`loop.py:3505-3556`) re-emits the held answer but never calls `_persist_to_ledger`.
- The resume loop DOES have a `message_store` (ResumeService default builder = `build_real_llm_handler` → `handler.py:727`), so the persist is not a no-op — the call sites were simply missing.

## Solution

`backend/src/agent_harness/orchestrator_loop/loop.py` (EDIT, 2 call sites + 1 docstring):

- **Leg 1**: in the tool-kind APPROVED branch, after the `tool` result append, backward-scan `_resume_asst_idx` = last `role=="assistant"` and `await self._persist_to_ledger(messages[_resume_asst_idx:], turn_num=turn_count)`. Persists exactly `[assistant tool_use, *tool results]` as one atomic batch (mirrors the 57.129 contract; backward-scan handles a multi-call turn). Reached ONLY on APPROVED+exec → REJECTED/undecided return earlier → no dangling tool_use.
- **Leg 2**: in `_replay_approved_output`, after `yield Thinking`, `if answer_text: await self._persist_to_ledger([Message(role="assistant", content=answer_text)], turn_num=turn_count)`. Covers output-kind (57.93) + verification-kind (57.99 A2) APPROVE.
- `_persist_to_ledger` docstring generalized to list the resume-path call sites.

Explicitly NOT done: verification-REJECTED correction note (internal one-shot instruction, not conversation; coached answer already persisted by `_run_turns`); input/between_turns kinds (no out-of-loop append → no gap). NO new ABC / event / wire / codegen / migration / frontend.

Tests — `backend/tests/unit/agent_harness/orchestrator_loop/test_loop_pause_resume.py` (EDIT): `RecordingMessageStore` + `message_store` param on `_build_resume_loop` + 4 tests (tool round-trip atomic / no-store no-op / output-approved persists held answer / output-rejected persists nothing).

## Verification

- Gates: mypy `src` **0/372** · run_all **10/10** (wire 25 in-sync, LLM-SDK-leak clean) · backend pytest **2731 passed / 5 skipped** (baseline 2727 +4) · black/isort/flake8 clean. Pure backend (Vitest/mockup untouched).
- **Leg 1 — FULL drive-through PASS** (real chat-v2 UI + real backend PID 54504 + real Azure gpt-5.2, dan@acme.com/acme-prod, session `02fa6bfb-4061-4b3a-87aa-8e4ef7f90a76`): python_sandbox MEDIUM → HITL pause → **Approve & continue** (UI) → resume → "ODD". DB `messages` ledger: **seq=2 assistant tool_use(python_sandbox) + seq=3 tool result persisted AT RESUME** (the fix; pre-fix the resumed turn held only seq 1+4). End-to-end: a follow-up "What was the tool's `duration_seconds`?" → **"0.031"** (un-deducible from "ODD"; rehydrated from seq-3) — proves the round-trip rehydrates. Screenshot `docs/.../sprint-57-132/artifacts/drivethrough-57132-leg1-resume-ledger-PASS.jpeg`.
- **Leg 2 — unit + composition verified (NOT UI drive-through; honest)**: 2 unit tests exercise the real `resume()` output-kind path → `_replay_approved_output` → `_persist_to_ledger`; the persist primitive is runtime-proven by Leg-1. A real-LLM output-escalate UI drive-through did not trigger deterministically (the LLM answer didn't reliably contain the default `confidential` phrase / likely content-filter early-exit) → labeled gate-only, NOT claimed driven. Carryover `AD-ChatV2-Resume-Replay-Drive-Through`.

## Impact

Backend only. Closes `AD-ChatV2-Resume-Tool-RoundTrips` + the sibling held-answer gap. No wire/codegen/migration/frontend change; the FE already renders rehydrated context. A HITL-paused-then-resumed chat-v2 session now keeps full multi-turn context for the approved tool round-trip (drive-through proven) + the delivered held answer (unit proven).
