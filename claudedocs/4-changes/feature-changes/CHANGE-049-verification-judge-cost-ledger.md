# CHANGE-049: Verification judge LLM token → cost ledger + quota (B-8 leg-1, blocker A)

**Date**: 2026-06-05
**Sprint**: 57.82
**Change Type**: Feature Improvement (billing correctness)
**Status**: ✅ Completed (pending push + PR)
**Scope**: 範疇 10 (Verification Loops) + platform_layer/billing + api/v1/chat

## Change Summary

When chat verification is enabled, the LLM **judge** call's token usage is now recorded in the cost ledger (as a distinct `_verification` sub_type) and counted against tenant quota. Previously the judge call's tokens were silently discarded → billing + quota under-report. Closes B-8 **blocker A** (`AD-Cat10-Judge-Cost-Ledger`), the billing leg of the 完整 B-8 epic. The default `chat_verification_mode` is **unchanged** (`disabled`) — this is a correctness fix that activates only on the enabled path.

## Change Reason

The B-8 analysis (`cat10-verification-default-enable-analysis-20260601.md`) identified 3 launch-blockers before `chat_verification_mode` can be flipped to `enabled`. Blocker A is the only one in the billing-correctness key-chain (鑰匙鏈②): the `LLMJudgeVerifier` makes an independent LLM call whose tokens never flow through the AgentLoop accumulator, so they appear in neither the cost ledger nor the quota reconcile. Fixing it now (even with the default still `disabled`) means billing is correct the moment verification is ever enabled.

## Detailed Changes

**Capture (US-1)**:
- `VerificationResult` +`input_tokens: int = 0` / `output_tokens: int = 0` / `model: str | None = None` (judge-only; rules_based/external default 0/None).
- `LLMJudgeVerifier.verify()` captures `response.usage` (prompt→input, completion→output) + `response.model` into the result via `dataclasses.replace` (covers valid + malformed-parse paths; the fail-closed exception path keeps 0 — the call may not have completed).

**Bubble (US-2)** — design Option 1 (user-locked AskUserQuestion):
- `LoopCompleted` +`verification_input_tokens` / `verification_output_tokens` / `verification_model`, kept SEPARATE from loop input/output_tokens.
- `run_with_verification` wrapper accumulates judge tokens across all verifiers + all correction attempts (the loop's accumulator is frozen by the time verification runs in the wrapper) and stamps all 3 LoopCompleted yield points (non-end_turn=0 / all-pass / exhausted).

**Record (US-3)**:
- `CostLedgerService.record_llm_call` +optional `sub_type_suffix: str = ""` → `{provider}_{model}{suffix}_input/_output` (default "" keeps loop sub_types byte-identical).
- Chat router LoopCompleted observer: a distinct best-effort judge `record_llm_call(sub_type_suffix="_verification")` + quota `record_usage(actual_tokens = total + verification_in + verification_out)`.

**Contract (US-4)**:
- `17-cross-category-interfaces.md` §1.1 VerificationResult + §4.1 LoopCompleted updated.
- `sse.py` NOT changed (drift D3): verification tokens are server-side billing only, consistent with the loop's own tokens (which are also not on the SSE wire); the router observer reads the event object directly.

## Modified Files List

| File | Change |
|------|--------|
| `agent_harness/_contracts/verification.py` | +3 judge token fields on VerificationResult |
| `agent_harness/verification/llm_judge.py` | capture response.usage + model |
| `agent_harness/_contracts/events.py` | +3 verification token fields on LoopCompleted |
| `agent_harness/verification/correction_loop.py` | wrapper accumulate + stamp 3 yield points |
| `platform_layer/billing/cost_ledger.py` | record_llm_call +sub_type_suffix |
| `api/v1/chat/router.py` | judge record_llm_call (_verification) + quota includes judge |
| `docs/.../17-cross-category-interfaces.md` | §1.1 + §4.1 contract sync |
| `tests/unit/.../test_llm_judge.py` | +3 token-capture tests |
| `tests/unit/.../test_correction_loop.py` | +`_TokenVerifier` + 5 accumulation tests |
| `tests/integration/api/test_chat_cost_ledger.py` | +`_VerificationStubLoop`/`_SpyQuota` + 2 billing/quota tests |

## Verification

- `mypy src/` 0 errors (332 files); `black/isort/flake8` 0.
- `pytest` 2147 passed / 4 skipped (+10 new tests).
- `run_all.py` 10/10 (check_llm_sdk_leak + check_cross_category_import + check_event_schema_sync green).
- Integration: distinct `_verification_input/_output` ledger entry written (4 rows = loop 2 + judge 2, quantities {120,8}); quota actual_tokens = 1628 (1500 loop + 128 judge).
- Default-disabled / non-end_turn / passthrough paths assert verification token fields = 0 (no extra entry, quota unchanged).

## Impact

Backend + docs only. No DB/schema change. No frontend (no wire change). Default behavior unchanged (`disabled`). The fix is a correctness pre-requisite for B-8 leg 2 (57.83: general judge template + real-LLM e2e + flip default). Per-verifier cost attribution deferred (all judge tokens aggregate into one `_verification` sub_type).
