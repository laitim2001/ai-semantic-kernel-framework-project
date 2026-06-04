# Sprint 57.79 — Checklist (C-11 billing-correctness: pricing key normalize + adapter max_tokens param)

**Plan**: `sprint-57-79-plan.md`
**Branch**: `feature/sprint-57-79-c11-billing-gaps` (from `main` `3c3e85df`)
**Closes**: `AD-Cost-Ledger-Model-Pricing-Key-Mismatch` + `AD-Adapter-MaxTokens-NewModel-Param`

---

## Day 0 — Plan-vs-Repo Verify + Branch + Decisions

### 0.1 Day-0 verify (parent grep + 1 researcher pass, main `3c3e85df`)
- [x] **Prong 1 (path)** — confirm: `platform_layer/billing/pricing.py`, `config/llm_pricing.yml`, `adapters/azure_openai/adapter.py`, `adapters/azure_openai/config.py`, `tests/unit/billing/test_pricing_loader.py`, e2e `e2e-real-llm-smoke.yml`.
- [x] **Prong 2 (content)** — D-DAY0-1..7 in plan §0 (pricing key flow response.model→exact lookup→None; yaml lacks gpt-5.2; max_tokens hard-wired ×2; config fields; staleness trap; test gaps).
- [x] **Prong 3 (schema)** — N/A (no DB table / migration / ORM change).
- [x] **go/no-go** — GO; user-locked: 2 code fixes + real-LLM Azure verify (user `.env` live key). 2 dependencies flagged (D1 gpt-5.2 price user-provided; D2 live .env).

### 0.2 Branch + decisions
- [x] **Branch created** `feature/sprint-57-79-c11-billing-gaps`
- [x] **Decisions locked**: pricing-lookup date-suffix normalize (over yaml full-date-key, robustness) + adapter `model_name`-prefix param branch; parent-direct (NOT agent-delegated — billing care + real-LLM collab); real-LLM verify THIS sprint.
- [x] **Day-0 commit** plan + checklist + progress.md Day 0

---

## Day 1 — Gap 1: pricing key normalize + gpt-5.2 yaml (US-1/US-3)

### 1.1 pricing lookup normalize
- [x] **`get_llm_pricing` date-suffix normalize** in `pricing.py`
  - exact lookup first; on miss strip trailing `-YYYY-MM-DD` (`_strip_version_suffix` module helper, `re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model)`); retry base key
  - `import re`; return None only if both miss
  - DoD: mypy clean ✅; cost_ledger row keeps full `model` (audit) but pricing matches base

### 1.2 gpt-5.2 yaml price (D1 resolved — user-provided 2026-06-04)
- [x] **add `azure_openai.gpt-5.2`** to `config/llm_pricing.yml` — input 1.75 / output 14.00 / cached 0.175 (user-provided) + bumped `last_updated` 2026-06-04

### 1.3 Gap-1 unit tests
- [x] **`test_pricing_loader.py`** (extend, real yaml fixture) — gpt-5.2 exact; `gpt-5.2-2025-12-11` → base (normalize); date-suffixed unknown base → None; non-date suffix no false normalize. 9 pass.

---

## Day 2 — Gap 2: adapter max_completion_tokens for gpt-5.x (US-2)

### 2.1 param-name helper + call-sites
- [x] **`_max_tokens_param_name(model_name)`** module helper in `adapter.py` — `"max_completion_tokens" if model_name.startswith("gpt-5") else "max_tokens"`
- [x] **swap 2 call-sites** — `:210-211` (chat) + `:282-283` (stream): `kwargs[_max_tokens_param_name(self.config.model_name)] = request.max_tokens` (module fn + config.model_name; simpler than instance wrapper)
  - DoD: mypy clean ✅; both paths covered; judging field = config.model_name (NOT deployment_name)

### 2.2 Gap-2 unit tests
- [x] **adapter param test** — NEW `test_max_tokens_param.py` (8 parametrized: gpt-5.x → max_completion_tokens; gpt-4.x/3.5 → max_tokens)
- [ ] **cost_ledger None-branch** — 🚧 deferred to Day 3 real-LLM (pricing normalize fully unit-covered; cost_ledger→unit_cost>0 end-to-end proven by Day-3 real run; avoids redundant heavy mock)

---

## Day 3 — real-LLM Azure verification (US-5) — user `.env`

### 3.1 clean restart + startup log (Risk Class E)
- [x] **clean start backend** — :8000 free (no stale `--reload` worker to kill); started no-reload single process
- [x] **confirm startup log** `pricing loader wired` (`main.py:167`) — FIX-022 wiring fired ✅

### 3.2 real-LLM smoke (local `.env`, NOT GitHub secrets)
- [x] **response.model captured** = `gpt-5.2-2025-12-11` (adapter direct probe, real Azure)
- [x] **align config.model_name** — `.env` `AZURE_OPENAI_MODEL_NAME=gpt-5.2` (was stale `gpt-4o` default; D-DAY0-6 confirmed)
- [x] **cost_ledger `unit_cost_usd > 0`** — via direct `CostLedgerService.record_llm_call('gpt-5.2-2025-12-11')`: input 0.00000175/0.00194425 + output 0.000014/0.000168, side-by-side vs existing $0 rows (chat router e2e blocked by unrelated 400 — see 3.3; bypassed via record path)

### 3.3 token-capped call (no 400)
- [x] **token-capped call no 400** — adapter `max_completion_tokens` for gpt-5.x accepted (real Azure)
- [ ] **confirm e2e workflow path** — 🚧 chat router real_llm e2e blocked by pre-existing UNRELATED 400 (`messages[3] role 'tool'` orphan); carryover `AD-Chat-RealLLM-Orphan-Tool-Message`; workflow path not verified this sprint

---

## Day 4 — Sweep + Closeout

### 4.1 Full sweep
- [x] **Backend gates** — `mypy src/` 0 (331) + `pytest` 2121 passed/4 skipped (+12 vs 2109) + `python scripts/lint/run_all.py` 10/10 (check_rls_policies unchanged; check_llm_sdk_leak green)
- [x] **No frontend** — 0 frontend changes (backend-only sprint)
- [x] **Read all changed code** — normalize anchored to date suffix; param branch both paths; yaml price real (user-provided); no fabricated values

### 4.2 Closeout docs
- [x] **CHANGE-047** in `claudedocs/4-changes/feature-changes/`
- [x] **progress.md** Day 0-4 (incl. Day 3 real-LLM evidence) + **retrospective.md** Q1-Q7
- [x] **Checklist** all `[x]` (only 3.3 e2e-workflow-path 🚧 carryover — unrelated chat 400)
- [x] **Calibration** record (medium-backend 0.80; agent_factor 1.0 parent-direct; ratio ~1.0; NOT agent-delegated)
- [x] **AD status**: `AD-Cost-Ledger-Model-Pricing-Key-Mismatch` + `AD-Adapter-MaxTokens-NewModel-Param` CLOSED; next-phase-candidates.md updated (+ carryover AD-Chat-RealLLM-Orphan-Tool-Message + deployment req)
- [x] **MEMORY subfile + pointer** + **CLAUDE.md lean**
- [x] **Design note?** — NO (feature-continuation)

### 4.3 Ship
- [x] **Commit mapping** Day-0+Gap1+Gap2 (`c8c12f3c`) / closeout (pending) / Area-A closeout doc (`bfaa1e20`)
- [ ] **Push + PR** (user-gated — explicit authorization required)
