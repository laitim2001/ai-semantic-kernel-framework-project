# Sprint 57.97 Progress — Multi-model profile (cheap tier for verification)

**Plan**: [`sprint-57-97-plan.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-97-plan.md)
**Checklist**: [`sprint-57-97-checklist.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-97-checklist.md)
**Branch**: `feature/sprint-57-97-multi-model-profile` (from `main` `1ecee053`)

---

## Day 0 — 2026-06-09 — Plan-vs-Repo Verify + Branch

### Three-prong Day-0 verify (Explore recon + targeted reads)

- **Prong 1 (path)** — confirmed: `ChatClient` ABC `adapters/_base/chat_client.py:69-93` has NO `model=` param (model fixed at adapter `__init__`); `AzureOpenAIAdapter.__init__(config)` `azure_openai/adapter.py:121`; `build_real_llm_handler` `handler.py:297` builds ONE `AzureOpenAIAdapter(AzureOpenAIConfig())`; verifier factory `make_chat_verifier_registry(chat_client, template)` `handler.py:479`; compactor `make_chat_compactor(chat_client)` `:364`; `LLMJudgeVerifier.__init__(chat_client=)` `llm_judge.py:74`; `adapters/_base/__init__.py` re-export pattern (import + `__all__`).
- **Prong 2 (content)** — confirmed: verifier + compactor + memory accept a `ChatClient` at construction → cheap routing is DI-only (ABC/loop unchanged); grep-0 existing `ModelProfile`/`model_tier`/`model_registry`. **KEY**: `llm_judge.py:97-103` (Sprint 57.82 B-8) already captures `response.usage` + `response.model` into `VerificationResult` → a cheap verifier auto-reports the cheap model name for cost attribution.
- **Prong 2.5 (observability / drift)** — see Drift findings below (D-DAY0-1 design-note number; D-DAY1-1 cost mechanism surfaced Day-1).
- **Prong 3 (schema)** — N/A: no DB/migration/ORM/event-schema change.
- **Baseline**: `main` HEAD `1ecee053` (57.96 merged) — CI-green mypy 0/351 · pytest 2283 · run_all 10/10. Post-edit: mypy 0/**353** (+2 new modules).
- **Cheap deployment availability**: user confirmed a cheaper Azure deployment is available / can be created (AskUserQuestion 2026-06-09) → Day-3 drive-through can measure a real cost delta.
- **go/no-go = GO** — spike confirmed thin (DI-only verifier swap; cost attribution model-name already captured by 57.82; loop/ABC unchanged).

### Drift findings

- **D-DAY0-1 (design-note number)** — plan v0 assumed `21-multi-model-profile-design.md`; `Glob` showed **19-23 all taken** (19-pause-resume / 20-iam-deep-dive / 20-subagent-child-loop / 21-iam-invites / 22-iam-credentials / 23-iam-registration; note: a pre-existing duplicate `20-`). → use **24-multi-model-profile-design.md**. Plan + checklist fixed Day-0.
- **D-DAY1-1 (cost mechanism — refines plan §3.2/§3.4)** — the cost-ledger does NOT price via the adapter's `get_pricing()`. `cost_ledger.record_llm_call(provider, model, tokens, sub_type_suffix)` prices via `config/llm_pricing.yml` (`PricingLoader.get_llm_pricing(provider, model)`, model-keyed, Azure version-suffix stripped) and writes a sub_type `azure_openai_<model>_verification_input/output` (the `_verification` suffix is Sprint 57.82). **Consequences**: (a) the `AZURE_OPENAI_CHEAP_PRICING_*` env vars the plan proposed feed only the (vestigial) adapter config pricing — the cost-ledger ignores them (it ignores the strong tier's config pricing too) → they were a footgun → **dropped** (Karpathy §2). (b) The visible cost-ledger proof is the **model-attribution difference** in the sub_type (`_<cheap>_verification_*` vs `_<strong>_*`) — robust, no pricing dependency. (c) For a $ delta, BOTH the cheap and the strong model must be priced in `config/llm_pricing.yml`; per the FIX-022 §6.2 caveat the strong model may currently be unpriced ($0 rows) → Day-3 must align the yml. **Drive-through reframed** accordingly (model-attribution primary; $ delta secondary, needs yml).

### Branch
- Branch `feature/sprint-57-97-multi-model-profile` created from `main` `1ecee053`. Plan + checklist + this progress committed (Day-0 commit).

---

## Day 1 — 2026-06-09 — ModelProfile + cheap builder + verifier rewiring (US-1/US-2/US-3)

### Code (5 files)
- **`adapters/_base/model_profile.py` (NEW)** — `@dataclass(frozen=True) ModelProfile{action, cheap}`; provider-neutral (imports only `ChatClient`, no SDK); seam docstring.
- **`adapters/_base/__init__.py`** — re-export `ModelProfile` (import + `__all__` + single-source-map docstring).
- **`adapters/azure_openai/profile.py` (NEW)** — `build_azure_model_profile(strong_client)`: reads `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME`; set → 2nd `AzureOpenAIAdapter` (shared endpoint/key from env, overridden deployment + model name via explicit kwargs); unset → `cheap is strong_client` (byte-identical). Cost-attribution note in docstring (yml-keyed, not config pricing). **Simplified after D-DAY1-1**: dropped the cheap pricing env + `_env_float` + warning (footgun — cost-ledger uses yml).
- **`api/v1/chat/handler.py`** — `profile = build_azure_model_profile(chat_client)`; verifier ← `profile.cheap` (`make_chat_verifier_registry(profile.cheap, ...)`); loop / compactor / prompt / subagents keep `chat_client` (== profile.action). MHist + comment. `loop.py` UNCHANGED.
- **`.env.example`** — documented optional `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` + `AZURE_OPENAI_CHEAP_MODEL_NAME` (unset = fall back; cost via `config/llm_pricing.yml`).

### Validation (Day-1 partial — code-complete + type-clean; tests are Day-2)
- **mypy `src --strict` 0/353** (+2 new modules) ✅
- Tests (Day-2): `ModelProfile` value object / `build_azure_model_profile` fallback (unset→identity) + set (cheap config) / verifier-routing (judge ← cheap, loop ← action) / cost-attribution. Test location confirmed: `backend/tests/unit/adapters/_base/` (new) + `backend/tests/unit/adapters/azure_openai/`.
- `run_all` lints + full pytest + drive-through → Day-2/Day-3.

### Notes
- The wiring is honest-minimal: only the verifier moves to `profile.cheap`; the user-facing action turn + compaction + subagents stay strong. `ModelProfile` is constructed + consumed in `handler.py` (not threaded into the loop) — the seam is documented for future phases (compaction/thinking cheap-tier).
- **NOT claimed verified** — Day-1 is code-complete + mypy-clean ONLY. Behavioral tests (Day-2) + drive-through (Day-3, needs the cheap deployment + `llm_pricing.yml` alignment) pending.

### Remaining
- Day 2: backend tests (ModelProfile + builder + verifier-routing + cost-attribution) + run_all + full pytest.
- Day 3: align `config/llm_pricing.yml` (cheap + strong model) → drive-through (real UI + cheap deployment → verification sub_type = cheap model + $ delta).
- Day 4: design note `24-multi-model-profile-design.md` (8-pt gate) + CHANGE-064 + 17.md + closeout.
