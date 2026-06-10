# CHANGE-065: Verification into the loop — the Cat 10 gate is an in-loop pre-delivery gear

**Change Date**: 2026-06-10
**Change Type**: Structural refactor (Cat 10 Verification moves from an outer wrapper into the orchestrator loop)
**Sprint**: 57.98 (A1 — harness-deepening Workflow A)
**Scope**: agent_harness/orchestrator_loop (Cat 1) × agent_harness/verification (Cat 10) × api/v1/chat (handler + router) × platform_layer/resume
**Status**: ✅ Day-2 complete (gate-green) — DRIVE-THROUGH pending (Day-3 US-6)

## Change Summary

Before this change, Cat 10 verification ran in an **outer wrapper** (`verification/correction_loop.py::run_with_verification`) that bracketed the chat router's `loop.run()` call: it consumed the loop's event stream, ran the verifiers on the final answer, and on failure RE-RAN the whole loop with a correction-augmented input (max 2 attempts). Two structural problems: (1) the wrapper only wrapped the chat **run()** path — a paused-then-resumed session (`loop.resume()`) was streamed un-wrapped, so **a resumed answer was never verified**; (2) each correction was a fresh top-level `run()`, discarding the prior context / prefix-cache.

This change moves verification **into** the loop as a pre-delivery gear. The `AgentLoopImpl` ctor now accepts a `verifier_registry`; `_run_turns` runs a `_cat10_verify_gate` on a FINAL candidate answer (AFTER the Cat 9 output guardrail, BEFORE the terminator). On PASS it delivers; on FAIL with budget left it appends the failed answer + a correction-feedback `user` Message and `continue`s — **the next turn re-answers in the SAME loop** (one re-enterable `_run_turns`, prefix-stable for the Cat 4 cache); on FAIL at the budget it emits `LoopCompleted(stop_reason="verification_failed")`. Because `resume()` drives the SAME `_run_turns` (Sprint 57.90) and the handler injects the registry into the ctor, **a resumed continuation is now verified for free** — closing problem (1).

The outer wrapper is **deleted**.

## Change Reason

`claudedocs/1-planning/harness-deepening-proposal-20260610.md` Workflow A (verification-into-loop) ranked this the first slice: the wrapper-based design left a real correctness hole (resume bypasses verification) and could not do in-context self-correction. The re-enterable `_run_turns` (the Sprint 57.89 payoff) made the move a ctor-injection + one gate method, not loop surgery.

## Detailed Changes

### Day-1 — loop ctor + the in-loop gate (US-1 / US-2)
- `orchestrator_loop/loop.py` — `AgentLoopImpl.__init__` gains `verifier_registry: VerifierRegistry | None = None` + `max_correction_attempts: int = 2`. NEW `_cat10_verify_gate()` (runs the registry's verifiers → VerificationPassed/Failed events + best-effort persist + judge-token accumulation) + `_VerifyVerdict` + `_build_correction_block`, integrated into `_run_turns` (gated on `is_final_answer AND registry non-empty`). `VERIFICATION_FAILED_STOP_REASON` constant. Judge tokens (Sprint 57.82) stamped on the terminal `LoopCompleted`.
- `verification/persistence.py` (NEW) — `persist_verification_event()` extracted verbatim from the wrapper so the gate + the (now-deleted) wrapper shared ONE writer; the gate lazy-imports it.

### Day-2 — durable counter + resume/replay + wrapper retire (US-3 / US-4 / US-5)
- **US-3 durable counter** (D-DAY2-1): `verification_attempts` rides `metadata["verification_attempts"]` on the pause checkpoint (NOT a new `DurableState` scalar — the checkpoint (de)serializer is an explicit field allowlist, while `metadata` round-trips verbatim per the 57.88 `pending_approval` precedent). Threaded through `_emit_state_checkpoint` + `_emit_deferred_pause` + the 3 mid-correction pause chains (between-turns / output-escalate / tool-HITL). `resume()` reads it back; `run()` defaults 0 (fresh-run reset).
- **US-4 resume coverage / replay**: no new code — `resume()` drives the shared `_run_turns` + the handler injects the registry → the resumed answer is verified. `_replay_approved_output` re-emits the snapshot directly (no parse→gate), so an approved replay is not re-verified by code-path isolation.
- **US-5 wrapper retire**: `handler.py` builds the registry BEFORE the loop and injects `verifier_registry=` into the ctor; all 3 builders return the `AgentLoopImpl` ALONE (tuple dropped). `router.py` drops the `verifier_registry` plumbing and replaces the wrapper call with `async for event in loop.run(...)`. `verification/correction_loop.py` **deleted**; `verification/__init__.py` drops `run_with_verification` + `VERIFICATION_FAILED_STOP_REASON`, re-exports `persist_verification_event`.
- **D-DAY2-2**: `build_handler` had many more tuple-unpackers than Day-0 Q7 claimed (incl. production `platform_layer/resume/service.py`); all converted to single-value.
- **D-DAY2-3**: deleting the wrapper removed the `__init__`→`run_with_verification`→`orchestrator_loop` import cycle, so `loop.py` switched its `VerifierRegistry` (TYPE_CHECKING) + `persist_verification_event` (lazy) imports from the PRIVATE submodules to the PACKAGE → `check_cross_category_import` green.
- **D-DAY2-4**: with verification default-ON, injecting the registry made the in-loop gate fire on the keystone/tier2 mock-loop wiring tests (whose verifier client is the fake-Azure adapter, not the swapped mock) → a real fake-endpoint network retry (20-min runtime) + perturbed mock sequence. Fix: pin `CHAT_VERIFICATION_MODE=disabled` in their `_set_fake_azure` (they test wiring, not verification) → 4.06s.

### Test conversions (Never-Delete via git mv)
- `test_correction_loop.py` → `test_inloop_gate_tokens.py`; `test_correction_loop_persist.py` → `test_inloop_gate_persist.py` — rewritten to drive `AgentLoopImpl` in-loop. `test_loop_verification_gate.py` (Day-1) covers PASS / FAIL-then-PASS / FAIL-at-max / no-registry / empty-registry. Stale-docstring sweep across 8 files.

## Modified Files List

| File | Change |
|------|--------|
| `backend/src/agent_harness/orchestrator_loop/loop.py` | EDIT — ctor verifier param + `_cat10_verify_gate` + durable counter threading |
| `backend/src/agent_harness/verification/persistence.py` | NEW — shared `persist_verification_event` |
| `backend/src/agent_harness/verification/correction_loop.py` | **DELETED** — wrapper retired |
| `backend/src/agent_harness/verification/__init__.py` | EDIT — drop wrapper re-exports; re-export persist |
| `backend/src/api/v1/chat/handler.py` | EDIT — inject registry into ctor; builders return loop alone |
| `backend/src/api/v1/chat/router.py` | EDIT — drop wrapper; `loop.run()` direct |
| `backend/src/platform_layer/resume/service.py` | EDIT — build_real_llm_handler returns loop alone |
| `backend/src/core/config/__init__.py`, `infrastructure/db/{models,repositories}/verification_log.py`, `verification/{cat9_mutator,tools}.py`, `api/v1/chat/sse.py` | EDIT — stale-docstring sweep |
| `backend/tests/unit/agent_harness/verification/test_inloop_gate_{tokens,persist}.py` | RENAMED + rewritten (Never-Delete) |
| `backend/tests/unit/agent_harness/orchestrator_loop/test_loop_verification_gate.py` | EDIT — +empty-registry |
| `backend/tests/integration/api/test_chat_{keystone,tier2}_wiring.py` | EDIT — pin verification disabled (D-DAY2-4) |
| `backend/tests/{...}/test_handler.py`, `test_audit_log_observer.py`, `test_chat_{e2e,handoff,verification_smoke,hitl_production_wiring,category_activation_wiring}.py` | EDIT — single-value build_handler / patch targets |

## Verification

- `pytest backend/tests/unit/agent_harness/orchestrator_loop/test_loop_verification_gate.py` — gate PASS / FAIL-then-PASS / FAIL-at-max / no-registry / empty-registry.
- `pytest backend/tests/unit/agent_harness/verification/test_inloop_gate_{tokens,persist}.py` — judge-token accounting + non-final skip + persistence hook.
- **Gate**: `mypy src` 0/353 · `python scripts/lint/run_all.py` 10/10 (AP-1 — `continue` in a while-driven `_run_turns`, not a pipeline; `check_cross_category_import`; SDK-leak 0) · `pytest -m "not real_llm"` **2290 passed + 4 skipped** · black/isort/flake8 clean.
- **Drive-through (Day-3 US-6, pending)**: real UI + backend + Azure — a fail-then-pass in-loop correction visible in the Inspector AND a resumed session's post-resume answer verified.

## Impact

- **Behavioral (production)**: a resumed (HITL-paused) chat answer is now verified (was un-verified pre-57.98). In-loop self-correction re-answers in the same loop (prefix-stable) instead of a fresh top-level run. No SSE wire / event-schema / DB / frontend change (`VerificationPassed/Failed` contracts unchanged).
- **Test-env**: wiring tests that build a real_llm handler + drive a mock loop must pin `CHAT_VERIFICATION_MODE=disabled` (the gate is now in-loop; D-DAY2-4).
- **Rollback**: revert the commit; the `CHAT_VERIFICATION_MODE` env still disables verification (registry=None → gate dormant → byte-identical to a non-verified run).
