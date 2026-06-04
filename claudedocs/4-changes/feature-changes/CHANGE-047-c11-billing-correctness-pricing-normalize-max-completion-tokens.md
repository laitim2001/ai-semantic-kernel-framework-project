# CHANGE-047: C-11 billing-correctness — pricing key normalize + gpt-5.x max_completion_tokens

**Change Date**: 2026-06-04
**Change Type**: Feature Improvement (billing correctness)
**Status**: ✅ Completed (code + real-LLM Azure verified)
**Sprint**: 57.79
**Scope**: `platform_layer.billing` (pricing) + `adapters.azure_openai` (param naming)

## Change Summary

Closed the 2 billing gaps surfaced by the C-11 real-LLM smoke (#237):

- **`AD-Cost-Ledger-Model-Pricing-Key-Mismatch`** — pricing lookup now normalizes date-suffixed Azure model ids (`gpt-5.2-2025-12-11` → base `gpt-5.2`), so real deployments price correctly instead of silently recording $0.
- **`AD-Adapter-MaxTokens-NewModel-Param`** — the Azure adapter now emits `max_completion_tokens` for gpt-5.x (which rejects `max_tokens` with HTTP 400) and `max_tokens` for gpt-4.x and earlier.

## Change Reason

The C-11 real-LLM smoke recorded chat cost_ledger rows at `unit_cost=$0` (silent billing gap): the deployment returns `response.model='gpt-5.2-2025-12-11'` but `llm_pricing.yml` only had base keys (`gpt-4o-mini`, `gpt-5.4`) and `get_llm_pricing` did an exact dict lookup → MISS → $0. Separately, any token-capped call to a gpt-5.x deployment would 400 because the adapter hard-wired `max_tokens`, which gpt-5.x rejects.

## Detailed Changes

### Gap 1 — pricing key normalize (`platform_layer/billing/pricing.py` + `config/llm_pricing.yml`)
- `get_llm_pricing(provider, model)`: exact lookup first; on miss, strip a trailing `-YYYY-MM-DD` version suffix (`_strip_version_suffix` + `_VERSION_SUFFIX_RE = re.compile(r"-\d{4}-\d{2}-\d{2}$")`) and retry the base key. Returns None only if both miss.
- Design: cost_ledger rows keep the full `model` id (audit fidelity); only the price lookup normalizes. Robust to future date bumps — yaml maintains base keys only (vs brittle per-date keys).
- `llm_pricing.yml`: added `azure_openai.gpt-5.2` (input 1.75 / output 14.00 / cached 0.175 per million — user-provided) + bumped `last_updated`.

### Gap 2 — adapter max_completion_tokens (`adapters/azure_openai/adapter.py`)
- New module helper `_max_tokens_param_name(model_name)` → `"max_completion_tokens"` if `model_name.startswith("gpt-5")` else `"max_tokens"`.
- Both call-sites swapped (chat `:210-211` + stream `:282-283`): `kwargs[_max_tokens_param_name(self.config.model_name)] = request.max_tokens`.
- Judging field is `config.model_name` (not deployment_name — deployment ids carry no model-generation guarantee), so `model_name` must reflect the real deployment generation (see Deployment Requirement below).

## Modified Files List

- `backend/src/platform_layer/billing/pricing.py` (normalize + helper + `import re`)
- `backend/config/llm_pricing.yml` (gpt-5.2 price + last_updated)
- `backend/src/adapters/azure_openai/adapter.py` (param helper + 2 call-sites)
- `backend/tests/unit/platform_layer/billing/test_pricing_loader.py` (+4 normalize/None tests)
- `backend/tests/unit/adapters/azure_openai/test_max_tokens_param.py` (NEW, +8 param tests)

No frontend / migration / wire-schema / ORM change.

## Test Checklist

- [x] pricing normalize unit tests +4 (exact / date-suffix normalize / date-suffixed-unknown None / non-date no-false-normalize)
- [x] adapter param unit tests +8 (gpt-5.x → max_completion_tokens; gpt-4.x/3.5 → max_tokens)
- [x] mypy src/ 0 (331 files) / pytest 2121 passed, 4 skipped / run_all 10/10
- [x] real-LLM Azure verification (see below)

## Verification (real-LLM Azure)

- Startup log `pricing loader wired` confirmed (FIX-022, `main.py:167`; Risk Class E pass).
- adapter direct probe: `response.model='gpt-5.2-2025-12-11'`; Gap 1 pre-fix exact MISS ($0) → post-fix normalize → `LLMPricing(1.75/14.0/0.175)`; Gap 2 token-capped call → no 400.
- cost_ledger DB (real `CostLedgerService.record_llm_call` path): fix-applied `gpt-5.2-2025-12-11` → input unit_cost 0.00000175 / total 0.00194425 + output unit_cost 0.000014 / total 0.000168 (**>0**), side-by-side vs existing $0 rows (same model, pre-fix).

## Deployment Requirement

**Production / any env using a gpt-5.x deployment MUST set `AZURE_OPENAI_MODEL_NAME` to the real deployment generation** (e.g. `gpt-5.2`). The config default is `gpt-4o` (stale); if not aligned, Gap 2 mis-branches to `max_tokens` → 400 on gpt-5.x. Gap 1 is unaffected (it uses `response.model`).

## Carryover (out of scope)

- `AD-Chat-RealLLM-Orphan-Tool-Message` — chat router real_llm e2e is blocked by a pre-existing, UNRELATED message-structure 400 (`messages[3] role 'tool'` orphan; reproduces on a fresh tenant). NOT this sprint's fix. cost_ledger end-to-end was verified via the direct record path instead.
- B-7 / B-8 / C-15 (billing bundle) — separate sprints.
