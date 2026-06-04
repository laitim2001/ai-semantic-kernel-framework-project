# Sprint 57.79 Retrospective — C-11 billing-correctness

**Sprint**: 57.79
**Closed**: 2026-06-04
**Branch**: `feature/sprint-57-79-c11-billing-gaps`
**Closes**: `AD-Cost-Ledger-Model-Pricing-Key-Mismatch` + `AD-Adapter-MaxTokens-NewModel-Param`

---

## Q1. Goal achieved?

✅ Yes. Both C-11 billing gaps closed + real-LLM Azure verified:
- Gap 1: pricing date-suffix normalize → `gpt-5.2-2025-12-11` prices off base `gpt-5.2`; cost_ledger DB unit_cost>0 (was $0).
- Gap 2: adapter emits `max_completion_tokens` for gpt-5.x → token-capped call no 400.
- Gates: mypy src/ 0 (331) / pytest 2121 (+12) / run_all 10/10.

## Q2. Estimate accuracy

- Plan: bottom-up ~7.5 hr → class-calibrated commit ~6 hr (`medium-backend` 0.80, `agent_factor` 1.0 parent-direct).
- Actual: ~5-6 hr equivalent. Code (Gap 1 + Gap 2 + tests) was small/fast (~1.5 hr); the bulk was Day-3 real-LLM verification + e2e debug (config.model_name staleness discovery + chat router 400 root-cause + cost_ledger record-path bypass) (~3-4 hr).
- Ratio ~1.0. `medium-backend` 0.80 held for a parent-direct billing sprint. **NOT agent-delegated** → the 16-consecutive-agent-delegated wall-clock caveat does not apply.

## Q3. What went well

- **Day-0 三-prong caught the staleness trap upfront** (D-DAY0-6): plan flagged config.model_name could be stale; Day-3 confirmed it (`gpt-4o` default vs `gpt-5.2` deployment) — so the `.env` alignment + deployment requirement were anticipated, not surprises.
- **Adapter-direct probe was the right verification tool**: isolated the 2 fixes against real Azure cleanly (response.model + pricing + token-cap) without the full chat stack — fast, cheap (~$0.01), precise.
- **Bypassed an unrelated blocker without scope creep**: when chat router e2e hit a pre-existing UNRELATED 400, used the direct `CostLedgerService.record_llm_call` path to prove cost_ledger unit_cost>0 at the DB level (same path the router calls) — got the user's required DB evidence without debugging an out-of-scope chat issue.
- **Pricing normalize design chose robustness**: date-suffix strip (not per-date yaml keys) means future deployment version bumps won't silently regress to $0.

## Q4. Lessons

- **`.env` `DB_*` keys are V1 leftovers** — backend uses `core.config settings.database_url` (default `ipa_v2`), not the `.env` `DB_NAME=ipa_platform` keys. Cost ~2 failed DSN attempts before reading `core/config:45`. (The compact summary's `ipa_v2` DSN was correct; the `.env` `DB_*` keys are misleading.)
- **A config default can silently defeat a fix**: Gap 2's `model_name`-keyed branch is correct, but the `gpt-4o` default makes it a no-op until `AZURE_OPENAI_MODEL_NAME` is aligned. Surfaced as a deployment requirement — a code fix alone wasn't enough.
- **chat router real_llm has a pre-existing prompt-assembly bug** (`messages[3]` orphan tool message) independent of billing — logged carryover.

## Q5. Improvements next sprint

- When a sprint touches a model/pricing identity, verify the **runtime config value** (not just code) early — the `.env`/config default mismatch is a recurring C-11 theme (FIX-022 §6.2 noted it; this sprint confirmed it end-to-end).

## Q6. Carryover

- `AD-Chat-RealLLM-Orphan-Tool-Message` — chat router real_llm e2e blocked by pre-existing message-structure 400 (NOT billing).
- **Deployment requirement**: production/other envs must set `AZURE_OPENAI_MODEL_NAME` to the real deployment generation for Gap 2 to take effect.
- B-7 (ErrorBudget Redis) / B-8 (Verification default) / C-15 — billing bundle, separate sprints.
- Auto-sync pricing from provider API (`llm_pricing.yml:3` future idea) — stays manual yaml.

## Q7. Risks

- Low. Backend-only, 2 targeted fixes, no schema/migration. Pricing normalize is anchored (`-YYYY-MM-DD$`) so it can't over-strip (unit-tested). The deployment requirement is documented; if missed, the symptom (400 on gpt-5.x token-capped calls) is loud, not silent.

---

## Design Note Extract

NO — feature-continuation (2 targeted billing fixes; no new contract / no 17.md change).
