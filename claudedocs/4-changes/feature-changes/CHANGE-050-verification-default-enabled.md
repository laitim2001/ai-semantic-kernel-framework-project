# CHANGE-050: General output_quality judge + flip chat verification default to enabled (B-8 leg-2)

**Date**: 2026-06-05
**Sprint**: 57.83
**Change Type**: Feature Improvement (verification rollout)
**Status**: ✅ Completed (pending push + PR)
**Scope**: 範疇 10 (Verification Loops) + core/config

## Change Summary

Shipped a general final-output **quality judge** template (`output_quality`), measured it against real Azure, and **flipped the `chat_verification_mode` default from `disabled` to `enabled`** on the data. Final-output verification (a lightweight quality judge + self-correction) is now ON by default for the main `real_llm` chat path. Closes B-8 / `AD-Cat10-Wire-1-Production` (the final leg of the 完整 B-8 epic).

## Change Reason

B-8's remaining 3 launch-blockers (from `cat10-verification-default-enable-analysis-20260601.md`): the default `safety_review` judge was Cat 9-fitted (blocker B), the enabled path had zero real-LLM test (blocker C), and the default was `disabled` (the flip). Leg 1 (57.82) had already fixed blocker A (judge cost/quota). This change closes B + C + the flip.

## Detailed Changes

**Blocker B — general quality judge**:
- NEW `verification/templates/output_quality.txt`. First drafted as a 4-dimension "fail on any" judge (per AskUserQuestion Q1), then re-tuned in-sprint to a **lightweight "clearly-failed-only" judge** (flag ONLY refusal/incoherent/empty/off-topic; "a short, correct answer PASSES; when in doubt, pass; default to passed=true") after measurement.
- `core/config`: default `chat_verification_judge_template` `"safety_review"` → `"output_quality"`.

**Blocker C — real-LLM measurement** (`claudedocs/5-status/cat10-verification-real-llm-measurement-20260605.md`):
- Real Azure, 8 normal + 2 nonsense prompts, `CHAT_VERIFICATION_MODE=enabled`.
- Pass 1 (fail-on-any judge): FP ~75% → DO-NOT-FLIP.
- Pass 2 (lightweight judge): **FP 0%** (normal all pass, 0 corrections, ~5s) + nonsense correctly failed → FLIP.

**The flip** (data-gated, Q2):
- `core/config`: default `chat_verification_mode` `"disabled"` → `"enabled"`.
- `test_config_verification.py`: `test_default_is_disabled` → `test_default_is_enabled`.

## Modified Files List

| File | Change |
|------|--------|
| `agent_harness/verification/templates/output_quality.txt` | NEW lightweight clearly-failed-only judge |
| `agent_harness/verification/templates/__init__.py` | docstring: output_quality in default-templates list |
| `core/config/__init__.py` | default judge template → output_quality; default mode → enabled |
| `tests/unit/agent_harness/verification/test_judge_templates.py` | output_quality in parametrize + lightweight-criteria test |
| `tests/unit/core/test_config_verification.py` | default template test + default mode → enabled |
| `claudedocs/5-status/cat10-verification-real-llm-measurement-20260605.md` | NEW measurement artifact (2 passes + verdict) |

## Verification

- mypy src/ 0 (332); black/isort/flake8 0.
- pytest 2150 passed / 4 skipped (+3 vs 2147); run_all 10/10 (check_llm_sdk_leak + check_event_schema_sync green).
- Real-Azure measurement: lightweight judge FP 0% (8/8 normal pass, 0 corrections), nonsense caught.
- Flip-impact grep: only `test_config_verification` depended on the default; full pytest confirms no regression.

## Impact

Production behavior change: the main `real_llm` chat path now runs final-output verification by default. Each chat adds ~1 judge LLM call (~5s tail, within the §範疇10 SLO) + judge cost (~$0.0047/chat, billed via leg-1's `_verification` ledger). echo_demo unaffected (builds no verifier registry). Instant rollback available via `CHAT_VERIFICATION_MODE=disabled`. Carryover: monitor real-traffic verification_failed rate (0% FP is from an 8-prompt sample).
