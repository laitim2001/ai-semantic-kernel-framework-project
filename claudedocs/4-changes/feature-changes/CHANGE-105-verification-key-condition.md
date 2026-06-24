# CHANGE-105: Verification key-condition judge (per-task condition template + A/B accuracy spike)

**Date**: 2026-06-24
**Sprint**: 57.138
**Scope**: Cat 10 (Verification Loops — judge template + eval); backend-only, NO loop.py / config / handler / migration / wire / frontend change

## Problem

The Cat 10 LLM judge (`LLMJudgeVerifier`) screens the candidate answer against `output_quality.txt` — a fixed GENERIC 5-failure-mode list (refuses / incoherent / empty / off-topic / contradicts-trace), the same for every request. It is structurally blind to **instruction-following** failures: an answer that violates a precise task constraint (5 items when "exactly 3" was asked, a paragraph when "one word" was asked, a missing required unit) is still coherent / on-topic / non-empty → the generic judge PASSES it. Research #8 (EMNLP2024 key-condition verifier): the judge should EXTRACT the per-task must-satisfy conditions for THIS request and check each. Closes `AD-Verification-KeyCondition-PerTask` (research opportunity #8, the 3rd item in the canonical research §5 ranked order after #6 + #3).

## Root Cause

The judge is template-driven (`_build_prompt` substitutes `{output}` + `{trace}` into the named template; `_parse_response` needs only `passed` + optional `score`/`reason`/`suggested_correction`). The generic template never asks the judge to derive task-specific conditions, so the judge's verdict is "is this a usable answer?" rather than "does this satisfy condition 1, 2, 3?". There was also no number measuring whether per-task condition extraction actually catches more without over-flagging.

## Solution

Evidence-first thin spike (same shape as 57.136/57.137): ship the mechanism as a selectable template, measure with a permanent A/B harness, let evidence gate the default.

1. **`templates/key_condition.txt`** (Cat 10, NEW): a per-task condition judge prompt — Step 1 EXTRACT the request's must-satisfy conditions from `{trace}` (count / format / ordering / inclusion / explicit constraints; "do not invent conditions the request does not clearly state" = the false-positive guard); Step 2 CHECK `{output}` against each; Step 3 ALSO apply the generic usability floor (refuses / incoherent / empty / off-topic / contradicts-trace); verdict `passed=true` IFF every CRITICAL condition met AND the floor holds. Same JSON contract (per-condition detail rides `reason`) + the same `{output}`/`{trace}` placeholders → composes with the A3 trace-aware judge with **NO `llm_judge.py` change**.
2. **Selectable via the EXISTING lever — zero code**: `load_template`/`list_templates` glob `*.txt` (`templates/__init__.py:47,64`), so adding the file auto-makes `key_condition` loadable + listed; the handler's `chat_verification_judge_template` setting (env `CHAT_VERIFICATION_JUDGE_TEMPLATE`, `handler.py:660`) + the per-tenant `in list_templates()` path (`handler.py:663`, 57.106 C3) both resolve it. **DEFAULT stays `output_quality`** (byte-unchanged).
3. **`scripts/benchmark_key_condition.py`** (Cat 10 eval, NEW): permanent A/B harness mirroring `benchmark_judge.py`. Runs BOTH templates (`output_quality` + `key_condition`) over a labeled corpus (trace-aware) and reports `generic_accuracy` / `key_condition_accuracy` / `key_condition_gain` (key_cond − generic accuracy on the `instruction_violation` class) / `false_positive_rate` (acceptable cases key_condition wrongly fails) / `key_condition_recommended` (gain ≥ `GAIN_FLOOR` 0.30 AND fp ≤ `FP_CEILING` 0.20). Golden fixture `key_condition_cases.yaml` (6 instruction_violation + 5 acceptable incl. over-flag traps) + CI-safe unit `test_benchmark_key_condition.py` (+9).
4. **`test_judge_templates.py`** (EDIT): `key_condition` added to the parametrized load+placeholder test + a dedicated test (condition-extraction language + 3 condition axes + the retained floor criteria + the false-positive guard).

## A/B Result (real Azure, 11 cases × 2 templates, cheap-tier judge temp 0.0)

| metric | value |
|--------|-------|
| generic accuracy (all) | 90.91% (10/11) |
| key_condition accuracy (all) | **90.91%** (tie) |
| generic acc on instruction_violation | 83.33% (5/6) |
| key_condition acc on instruction_violation | **100.00% (6/6)** |
| **key_condition_gain** (instruction_violation: key_cond − generic) | **+16.67%** |
| **false_positive_rate** (acceptable wrongly failed) | **20.00% (1/5)** |
| thresholds (gain ≥ 30% AND fp ≤ 20%) | **NOT recommended** |
| generic tokens / key_condition tokens | 4090 / 7493 (~1.8×) |

**Verdict: directionally better at instruction-following catching, but NOT a default flip.** The key_condition judge caught **all 6** instruction violations (100%) vs the generic judge's 5/6 (+16.67pp on that class) — but it **over-flagged 1 acceptable answer** (20% FP) and costs ~1.8× the tokens, so overall accuracy is a **tie** (90.91% each) and it does NOT clear the recommendation thresholds. Notable nuance: the generic judge is **less blind than the theory predicted** (83% on instruction_violation, not ~0%) because A3 trace-awareness lets it reason "the user asked for exactly 3 and got 5 → contradicts the trace". So explicit per-task condition extraction adds a real-but-marginal catch at a false-positive + token cost — matching the reconciliation assessment ("#8 partially done / refinable; priority low").

**Decision**: keep `output_quality` as DEFAULT (zero behavior change); ship `key_condition` as a SELECTABLE env / per-tenant opt-in (the existing `chat_verification_judge_template` lever) for instruction-adherence-strict tenants who accept the higher FP + token cost. The harness is permanent + re-runnable on a larger / harder corpus.

## Verification

- **Gate**: pytest **2797 passed + 5 skip** (baseline 2786 + 11 new = 2 template tests + 9 harness tests) · mypy `src` **0/374** · v2 lints **10/10** (`python scripts/lint/run_all.py` cwd=root; incl. check_llm_sdk_leak — the harness uses the Verifier ABC, the Azure profile is built only in `main()`) · black/isort/flake8 clean. Frontend sentinels unchanged (backend-only): Vitest 915 / mockup 51 / wire 25.
- **A/B harness (real Azure)**: `RUN_AZURE_INTEGRATION=1 python scripts/benchmark_key_condition.py` → gain +16.67% / fp 20% / NOT recommended; report → `sprint-57-138/artifacts/key_condition_report.{md,json}`. CI-safe unit covers load/run/build_report + the recommendation matrix (no Azure).
- **Drive-through PASS (兩者結合)** (real chat-v2 UI + real backend + real Azure gpt-5.2, jamie@acme.com·operator·acme-prod):
  - **ARM A (key_condition active)**: `CHAT_VERIFICATION_JUDGE_TEMPLATE=key_condition` → "List exactly 3 primary colors." → "Red, blue, yellow" → verification_passed (llm_judge 0.99) → end_turn. The key_condition judge ran on the main flow + correctly passed the compliant answer (no over-flag). Screenshot `dt-57138-keycond-active-verification-passed.jpeg`.
  - **ARM B (default unchanged)**: env unset (default `output_quality`) → "What is the capital of France?" → "Paris" → verification_passed (0.99) → end_turn. The default path is byte-unchanged. Screenshot `dt-57138-default-template-no-regression.jpeg`.
  - **Why the CATCH is the harness not the UI**: a real LLM complies with a simple instruction on demand, so a clean instruction-violation-then-catch can't be forced in a live UI (same honest limit as 57.136). The UI proves selectability + no-regression; the A/B harness proves the catch. We do NOT claim the UI drove the catch.

## Impact

Backend-only. Default behavior is byte-identical (`output_quality`). The `key_condition` template is opt-in via the existing setting (env / per-tenant). No schema, no new wire event, no frontend, no `VerificationResult` contract change, no loop.py/config/handler change. Rollback = leave the setting at `output_quality` (the default) or delete the template file. Follow-ups: two-phase extract-then-check (`AD-Verification-KeyCondition-TwoPhase-Phase58`, only if Option A proves material value), surfacing the structured conditions array (`AD-Verification-Conditions-Surface-Phase58`), flipping the default (1-line config change only if a future A/B clears the thresholds).
