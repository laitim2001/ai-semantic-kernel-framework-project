# Sprint 57.97 Plan — Multi-model profile (cheap tier for verification; the llm_judge runs on a cheaper deployment than the main action turn)

**Purpose**: The agent-harness-cc-parity assessment (`claudedocs/5-status/agent-harness-cc-parity-20260607.md` §4 C-class + 圖 D 波次 1) ranked **multi-model profile** the single highest-ROI untouched parity gap: today ONE `ChatClient` (Azure, single deployment) serves every phase — the main action turn AND the cheap-by-nature phases (verification / compaction / memory extraction) — so cheap phases overpay by running on the strong model. This sprint introduces a **thin `ModelProfile` value object** that pairs two pre-constructed `ChatClient` instances by role (`action` = strong, `cheap` = cheaper deployment) and routes the **verification (Cat 10 `LLMJudgeVerifier`)** call — which runs on EVERY request since 57.83 default-ON, making it the most drive-through-able cheap-tier target — onto the cheap client, while the main action turn (`loop.py:1954`) and compaction keep the strong client. The Day-0 Explore recon corrected/confirmed the design with file:line anchors: (1) the `ChatClient` ABC (`adapters/_base/chat_client.py:69`) has **NO `model=` param on `chat()`/`stream()`** — the deployment is fixed at adapter `__init__` (`azure_openai/adapter.py:121`) → per-call model selection would break the contract; the natural seam is **construct 2+ clients upfront + select by phase**; (2) the verifier, compactor and memory-extraction call sites **already accept a `ChatClient` at construction** (`LLMJudgeVerifier.__init__` `llm_judge.py:74`, `make_chat_compactor` `handler.py:364`, `memory/extraction.py`) → routing the cheap client to the verifier is a **construction-time injection, ABC-unchanged, loop.py-unchanged**; (3) no model-selection abstraction exists today (grep-0 `model_profile`/`model_tier`/`model_registry`); (4) the neutrality lint (`scripts/lint/check_llm_sdk_leak.py`) forbids `import openai`/`anthropic` outside `adapters/<provider>/` → `ModelProfile` holds only the provider-neutral `ChatClient` ABC (no SDK), constructed in `handler.py` (which MAY import the concrete adapter). Two design decisions locked 2026-06-09 (AskUserQuestion): the abstraction = a **thin `ModelProfile` value object** (`{action, cheap}` — single-source seam; future tiers add a field, not a new injection site) over direct injection; the first cheap-tier phase = **verification (llm_judge)** (drive-through-able every request) over compaction (needs a long conversation to trigger). Config adds `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` (+ cheap pricing) reusing the shared endpoint/key; **unset → cheap falls back to action** (byte-identical behavior, safe to ship without a 2nd deployment). The user confirmed a real cheaper Azure deployment is available → the **drive-through measures a real cost delta** (the verification call priced at the cheap rate, distinct from the strong main turn). This is a **new-domain spike** → Day-4 design-note extract is MANDATORY (`sprint-workflow.md §Step 5.5` 8-point gate) → `24-multi-model-profile-design.md`; record = CHANGE-064; the `ModelProfile` is a new provider-neutral contract → 17.md registration.

**Category / Scope**: Cat 4-adjacent / adapters layer (model selection across phases) × Cat 10 (Verification — the first cheap-tier consumer) × Cat 12 (Observability — the LLM-call model surfaces so the cost delta is visible). Backend: a NEW `ModelProfile` value object (`adapters/_base/model_profile.py`); `handler.py` builds a strong + a cheap `AzureOpenAIAdapter` and a `ModelProfile`, passing `profile.cheap` to the verifier factory and `profile.action` to the loop + compactor; `azure_openai/config.py` (or a handler-local builder) reads the cheap env vars with fallback; the LLM-call span carries the model/deployment (Day-1 confirm or add) so the cost delta is observable. **`loop.py` UNCHANGED** (it receives `profile.action`, the same strong client it gets today); **no ABC change**; **no DB/migration**. Phase 57.97

**Created**: 2026-06-09
**Status**: Draft (scope below; code execution gated on Day-0 GO — Day-0 Explore recon already run, findings in §0)
**Source**: `claudedocs/5-status/agent-harness-cc-parity-20260607.md` §4 (C-class) + §6 (建議優先序 1: multi-model profile, ROI 最高) + 圖 D 波次 1 R1 + `next-phase-candidates`-adjacent parity roadmap + AskUserQuestion 2026-06-09 (下一階段 = 多模型 profile; 抽象 = thin `ModelProfile` 值物件; 首階段 = verification (llm_judge); cheap deployment available → drive-through 量真 cost delta).

> **Modification History**
> - 2026-06-09: Initial creation — multi-model profile spike; thin ModelProfile {action, cheap}; verification (llm_judge) routed to cheap deployment; config cheap env + fallback; loop.py/ABC UNCHANGED; design-note 21 mandatory (spike)

---

## 0. Background

The cc-parity assessment (snapshot at Sprint 57.87) concluded the core loop is at parity with the ideal/CC harness, and the truly-worth-building gaps are 5 C-class items; **multi-model profile** was ranked #1 by ROI (compact/think/verify on a cheap model → direct cost saving; the provider-neutral `ChatClient` ABC already paved the road). The last 9 sprints (57.88-57.96) built 地基 A (pause-resume) + Cat 11 child-loop; this sprint pivots to波次 1 R1. The user selected multi-model profile (AskUserQuestion 2026-06-09) and locked the abstraction (thin `ModelProfile`) + first phase (verification) + confirmed a cheap deployment is available.

### Ground truth (Day-0 head-start — Explore recon, file:line anchors)

A read-only Explore "multi-model-profile surface" recon mapped the real code:

- **Model selection is PER-CLIENT-CONSTRUCTION, not per-call (premise CONFIRMED).** `ChatClient` ABC `adapters/_base/chat_client.py:69-93` — `async def chat(request, *, cache_breakpoints=None, trace_context=None)` + `def stream(...)`; **NO `model=`/`deployment=` param**. `AzureOpenAIAdapter.__init__` (`azure_openai/adapter.py:121-127`) takes `config: AzureOpenAIConfig` and the deployment is immutable instance state (`self.config.deployment_name`, used at `:197`). → cannot switch model mid-call; the seam is **build 2+ clients upfront, select by phase**.
- **The cheap-tier call sites already accept a `ChatClient` at construction (premise CONFIRMED — thin spike).** Four harness LLM call sites: action `loop.py:1954` (`self._chat_client.chat`), **verification `verification/llm_judge.py:90`** (`self._chat.chat`; ctor `:74` `self._chat = chat_client`), compaction `context_mgmt/compactor/semantic.py:130` (`self.chat_client.chat`), memory `memory/extraction.py:85`. All receive the client by DI at construction → routing the cheap client to the verifier is `make_chat_verifier_registry(chat_client=profile.cheap)` — **no ABC change, no loop.py change**.
- **Construction + injection path.** `api/v1/chat/handler.py:283-297` (`build_real_llm_handler`) checks `AZURE_OPENAI_{ENDPOINT,API_KEY,DEPLOYMENT_NAME}` then `chat_client = AzureOpenAIAdapter(AzureOpenAIConfig())` — a SINGLE instance shared by the loop + verifier + compactor (the recon noted line ~265 "verifier shares THIS handler's adapter"). The verifier factory + compactor factory are called here with that single client.
- **Config is single-deployment (premise CONFIRMED).** `azure_openai/config.py:34-98` `AzureOpenAIConfig(BaseSettings, env_prefix="AZURE_OPENAI_")` — `deployment_name` `:56`, `model_name` `:` (default gpt-4o), `model_family` Literal[gpt/gpt-mini/gpt-nano], pricing `pricing_input_per_million` (2.50) / `pricing_output_per_million` (10.00) / `pricing_cached_input_per_million` (1.25). One deployment per instance; a cheap tier needs a SECOND config (cheap deployment + cheap pricing, sharing endpoint/key/api_version).
- **No existing model-selection abstraction (premise CONFIRMED).** grep-0 for `model_profile`/`model_tier`/`model_registry`/`ModelProfile`/`get_model` in `backend/src`. This sprint introduces the first.
- **Neutrality is lint-enforced.** `scripts/lint/check_llm_sdk_leak.py:37-43` maps `openai→azure_openai` etc.; any SDK import outside `adapters/<provider>/` → CI FAIL. `agent_harness/**` has zero provider imports. → `ModelProfile` references only the `ChatClient` ABC (no SDK); it is constructed in `handler.py` (under `api/`, MAY import the concrete adapter).
- **`ChatClient` is a locked single-source contract.** 17.md §2.1: `ChatClient` owner `10-server-side-philosophy.md` 原則 2, methods `chat`/`stream`/`count_tokens`/`get_pricing`/`supports_feature`/`model_info`. `ModelProfile` must NOT modify it — it WRAPS/SELECTS pre-built clients. → `ModelProfile` is a NEW small contract (registered in 17.md), not a `ChatClient` change.
- **Cost attribution is the drive-through crux (Day-1 verify).** The recon flagged: the verifier's cost should be computed from the verifier's client `get_pricing()` (so a cheap judge auto-prices cheap); Day-1 confirm WHERE the verification call's cost is computed (verifier-local using `self._chat.get_pricing()` vs central using the loop's client) and whether the LLM-call Trace span carries a `model`/`deployment` attribute. If the per-call model is not already observable, adding a `model` attribute to the LLM-call span is a small in-scope addition so the drive-through shows verification=cheap vs action=strong.
- **This is a new-domain spike** → Day-4 design-note extract MANDATORY (`24-multi-model-profile-design.md`, 8-point gate; Day-0 confirmed next available doc number = 24 — 19-23 taken: 19-pause-resume / 20-iam-deep-dive / 20-subagent-child-loop / 21-iam-invites / 22-iam-credentials / 23-iam-registration) + CHANGE-064 + 17.md `ModelProfile` registration.

---

## 1. Sprint Goal

Introduce a thin `ModelProfile` value object pairing a strong (`action`) and a cheap (`cheap`) pre-constructed `ChatClient`, and route the verification (Cat 10 `LLMJudgeVerifier`) LLM call onto `profile.cheap` while the main action turn (`loop.py:1954`) and compaction keep `profile.action`: (1) a NEW provider-neutral `ModelProfile` value object (`adapters/_base/model_profile.py`) holding `action`/`cheap` `ChatClient` refs; (2) `handler.py` builds a strong `AzureOpenAIAdapter` + (if `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` set) a cheap `AzureOpenAIAdapter` reusing the shared endpoint/key with cheap deployment + cheap pricing — **unset → cheap = action (byte-identical behavior)** — assembles `ModelProfile`, and passes `profile.cheap` to the verifier factory + `profile.action` to the loop + compactor; (3) the verification cost is attributed to the cheap model (verifier uses `self._chat.get_pricing()`; Day-1 confirm/wire) and the LLM-call model/deployment is observable (Trace span attribute — Day-1 confirm or add) so the cost delta is visible. **`loop.py` UNCHANGED (receives `profile.action`); no `ChatClient` ABC change; no DB/migration; neutrality green (`ModelProfile` holds only the ABC).** Tests assert the fallback (cheap unset → cheap is action) + the verifier receives the cheap client (not the action client) + cost attribution uses cheap pricing + neutrality. **Drive-through**: with a real cheap deployment configured, a chat-v2 request → the verification (llm_judge) call demonstrably ran on the cheap deployment (distinct model in the Trace span / cheap pricing in the cost) while the main turn ran on the strong deployment → a real, visible cost delta. Out of scope: compaction / memory-extraction / thinking cheap-tier (the seam is built; this sprint only wires verification); threading `ModelProfile` into the loop; per-tenant model policy (Config 分層 is a separate parity gap); the cheap-judge quality tradeoff (documented as an open invariant, not resolved).

---

## 2. User Stories

- **US-1 (the `ModelProfile` value object)** — As the adapters/contract maintainer, I want a thin provider-neutral `ModelProfile` pairing `action` + `cheap` `ChatClient`s, so phase→model routing has a single-source seam without touching the `ChatClient` ABC or importing any SDK. → NEW `@dataclass(frozen=True) ModelProfile` in `adapters/_base/model_profile.py` with `action: ChatClient` + `cheap: ChatClient`; a `for_phase(...)`-style accessor is NOT added (YAGNI — callers read `.cheap`/`.action` directly this sprint); 17.md registration.
- **US-2 (cheap config + fallback)** — As the operator, I want a cheap deployment configured via env (reusing the shared Azure endpoint/key) with a safe fallback, so the feature ships even without a 2nd deployment and a long conversation isn't needed to benefit. → `handler.py` (or an `azure_openai` builder) reads `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` (+ cheap `MODEL_NAME` + cheap pricing); if set → build a cheap `AzureOpenAIConfig`/adapter (shared endpoint/api_key/api_version, cheap deployment + pricing); if UNSET → `cheap = action` (the SAME instance) so behavior is byte-identical and cost reporting is unchanged.
- **US-3 (verification runs on the cheap tier)** — As the cost owner, I want the per-request verification (llm_judge, default-ON since 57.83) to run on the cheap model while the user-facing action turn keeps the strong model. → `handler.py` passes `profile.cheap` to the verifier factory (`make_chat_verifier_registry`/`LLMJudgeVerifier`); the loop (`AgentLoopImpl(chat_client=profile.action)`) + compactor (`make_chat_compactor(profile.action)`) keep the strong client. The action turn's behavior/cost is unchanged.
- **US-4 (cost attribution + observability + no neutrality break; loop unchanged)** — As the observability/loop maintainer, I want the verification cost attributed to the cheap model + the per-call model visible, with no SDK leak and `loop.py` untouched. → the verification cost uses the verifier client's `get_pricing()` (Day-1 confirm/wire); the LLM-call Trace span carries `model`/`deployment` (Day-1 confirm or add — small) so the verification call shows cheap vs the action call strong; `check_llm_sdk_leak` 0 (`ModelProfile` holds only the ABC); `loop.py` diff = 0.
- **US-5 (drive-through acceptance — verification really ran cheap, cost delta visible)** — As the user, I want to actually SEE that verification used the cheap deployment end-to-end with a real cost delta. → drive-through (real UI + real backend + real Azure, with `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` set to a real cheaper deployment): a chat-v2 request → the verification (llm_judge) call ran on the cheap deployment (the Trace span shows the cheap model / the cost line is cheap-priced) while the main turn ran on the strong deployment → screenshot + observed-vs-intended diff (before this sprint: one model for everything; after: verification cheap, action strong) in progress.md. (No "gate-only" claimed as drive-through.)

---

## 3. Technical Specifications

### 3.0 Architecture (build 2 clients upfront, select by phase; only the verifier moves to cheap this sprint)

```
BEFORE (57.96)                                   57.97 (verification on cheap tier)
  handler.build_real_llm_handler:                  handler.build_real_llm_handler:
    chat_client = AzureOpenAIAdapter(Config())       action = AzureOpenAIAdapter(Config())                 # strong (unchanged)
                                                      cheap  = AzureOpenAIAdapter(CheapConfig())            # NEW (or = action if env unset)
                                                      profile = ModelProfile(action=action, cheap=cheap)   # NEW thin value object
    loop = AgentLoopImpl(chat_client=chat_client)    loop = AgentLoopImpl(chat_client=profile.action)      # strong (UNCHANGED behavior)
    compactor = make_chat_compactor(chat_client)     compactor = make_chat_compactor(profile.action)       # strong
    verifier  = make_chat_verifier(chat_client)      verifier  = make_chat_verifier(profile.cheap)         # CHEAP  ← the only routing change

  loop.py:1954  self._chat_client.chat(...)         loop.py UNCHANGED (gets profile.action == today's client when cheap unset)

  verification/llm_judge.py:90  self._chat.chat()   self._chat is now profile.cheap → judge runs cheap; cost via self._chat.get_pricing()
  Trace span (LLM call)                             carries model/deployment → verification span shows cheap, action span shows strong
```

`ModelProfile` is constructed AND consumed entirely in `handler.py` this sprint (it does NOT thread into the loop) — the seam is documented in the design note for future phases (compaction/thinking/memory cheap-tier) to add a field + read it, without a new injection site.

### 3.1 The `ModelProfile` value object (US-1)
- `backend/src/adapters/_base/model_profile.py` — NEW `@dataclass(frozen=True) ModelProfile` with `action: ChatClient` + `cheap: ChatClient`. Provider-neutral (imports only `ChatClient` from `.chat_client`; NO SDK). Docstring documents the seam: future tiers add a field (e.g. `compaction`, `thinking`) defaulting to `action`; callers read the field for their phase. NO `for_phase()` dispatch method (YAGNI — direct `.cheap`/`.action` reads this sprint). File-header per convention.
- Export it from `adapters/_base/__init__.py` (Day-1 confirm the package re-export pattern).
- DoD: `mypy src/ --strict` 0; `ModelProfile(action=mock, cheap=mock)` constructs; `check_llm_sdk_leak` 0.

### 3.2 Cheap config + fallback (US-2)
- Cheap config construction (in `handler.py` or a small `azure_openai` builder fn — Day-1 pick the tidier site): read `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` from env. If **set**: build a cheap `AzureOpenAIConfig` reusing the shared `endpoint`/`api_key`/`api_version` (the strong config's values) but overriding `deployment_name` = cheap, `model_name` = `AZURE_OPENAI_CHEAP_MODEL_NAME` (default to the cheap deployment string), `model_family`/`context_window`/`max_output_tokens` (sensible cheap defaults), and pricing = `AZURE_OPENAI_CHEAP_PRICING_INPUT_PER_MILLION` / `..._OUTPUT_PER_MILLION` / `..._CACHED_INPUT_PER_MILLION` (cheap rates — documented defaults if unset, with a one-line warning log so cost isn't silently mis-attributed). Construct a cheap `AzureOpenAIAdapter`. If **unset**: `cheap = action` (the SAME adapter instance) — no second client, byte-identical behavior + cost.
- `.env.example` — document the new optional vars (`AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` + cheap pricing) with a comment that unset = fall back to the main deployment.
- DoD: env unset → `profile.cheap is profile.action` (identity); env set → a distinct cheap adapter with the cheap deployment + cheap pricing.

### 3.3 Verification wired to the cheap tier (US-3)
- `api/v1/chat/handler.py` — build `action` + `cheap` adapters → `profile = ModelProfile(...)`; pass `profile.cheap` to the verifier factory (the call the recon located near `:265`, `make_chat_verifier_registry`/`make_chat_verifier`); pass `profile.action` to `AgentLoopImpl(chat_client=...)` + `make_chat_compactor(...)` + (unchanged) memory extraction. The verifier factory + `LLMJudgeVerifier.__init__(chat_client=...)` already accept a `ChatClient` → no signature change. (Day-1 confirm the exact factory name + that the echo/demo handler path is untouched — it has no real verifier.)
- DoD: the constructed `LLMJudgeVerifier._chat` is `profile.cheap`; the loop's `_chat_client` is `profile.action`.

### 3.4 Cost attribution + observability proof (US-4)
- Verification cost: Day-1 read where the verification LLM call's cost/tokens are recorded (the recon noted `VerificationResult` captures `input_tokens`/`output_tokens`/`model`). Confirm the cost uses the verifier client's `get_pricing()` (so a cheap judge auto-prices cheap). If the cost is computed centrally using the loop's client pricing (wrong for a cheap judge), wire it to use the verifier's client pricing (small, in-scope — the spike's correctness crux).
- Observability: Day-1 confirm the LLM-call Trace span (Cat 12) carries a `model`/`deployment` attribute. If not, add it (small) so the drive-through shows verification span model = cheap vs action span model = strong. The `model_info()`/config already expose the deployment name; the span attribute reads it.
- Neutrality + loop: `ModelProfile` imports only the ABC (`check_llm_sdk_leak` 0); `loop.py` diff = 0 (it receives `profile.action`).
- DoD: a request with the cheap deployment set → the verification cost line is cheap-priced + the verification span model = cheap deployment.

### 3.5 What is explicitly NOT done + Lint / neutrality / 17.md / design note
- **NOT done (separate slices / open invariants)**: compaction / memory-extraction / thinking cheap-tier (the seam is built; only verification wired this sprint); threading `ModelProfile` into the loop; a `for_phase()` dispatcher; per-tenant model policy (= the separate "Config 分層" parity gap); the cheap-judge ACCURACY tradeoff (a cheaper judge may be less reliable — documented as a design-note Open Invariant, validated empirically in the drive-through but NOT formally benchmarked this sprint); non-Azure cheap tiers (the seam is provider-neutral but only Azure is wired).
- **Lint / neutrality**: `check_llm_sdk_leak` 0 (`ModelProfile` holds only `ChatClient`; the concrete adapters are built in `handler.py` under `api/`). `check_ap1_pipeline_disguise` green (no loop change). AP-4 green (this is real cost routing, not a Potemkin). `category-boundaries`: `ModelProfile` in `adapters/_base/` (the home of `ChatClient`); the wiring is in `api/v1/chat/handler.py`; no new cross-category ABC beyond the registered `ModelProfile` value object. `run_all` 10/10 (no event-schema change → `check_event_schema_sync` unaffected).
- **17.md (registration)**: add a `ModelProfile` row in §2.1 (or the adapters/_base contract section) referencing `24-multi-model-profile-design.md` as owner — a NEW provider-neutral value object pairing `ChatClient`s by role; note it does NOT modify the `ChatClient` ABC.
- **Design note (MANDATORY — spike)**: `24-multi-model-profile-design.md` (Day-0 confirm next number) per `sprint-workflow.md §Step 5.5` 8-point quality gate + `claudedocs/templates/spike-design-note-template.md` (Spike Summary / Decision Matrix [per-call vs per-construction; thin value object vs ModelProfileChatClient ABC vs direct injection] / Verified Invariants [the verifier runs cheap, file:line] / Cross-Category Contracts [ModelProfile in 17.md] / Open Invariants [cheap-judge accuracy; other phases not wired; per-tenant policy] / Rollback [unset the env / revert the factory arg] / References / MHist).

### 3.6 Validation (US-1..US-5)
- **mypy `src/ --strict` 0**; `run_all` 10/10; `black`/`isort`/`flake8 src/ tests/` clean (run each INDEPENDENTLY, not `&&`-chained — the 57.95 CI lesson).
- **pytest (backend)**:
  - **NEW** `ModelProfile` test: constructs with two mock clients; `frozen` (immutable); holds the ABC (neutrality — no SDK import in the module).
  - **NEW** cheap-config fallback test: env `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` UNSET → the built `profile.cheap is profile.action`; SET → a distinct adapter whose config has the cheap deployment + cheap pricing (`get_pricing()` returns the cheap rate).
  - **NEW** verifier-routing test: `build_real_llm_handler` (mock adapters or env-driven) → the `LLMJudgeVerifier._chat` is `profile.cheap`; the loop's `_chat_client` is `profile.action`; when cheap unset, both are the same instance (no behavior change).
  - **NEW** cost-attribution test: a verification run with a cheap-priced client → the recorded verification cost uses the cheap pricing (not the action pricing).
  - **Existing** verification (57.83) + handler tests UNCHANGED + green; `loop.py` diff = 0.
  - Full backend suite green (NET delta documented — expect +N new, 0 deletions).
- **Drive-through** (US-5): real UI + real backend + real Azure, with `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` set to a real cheaper deployment — a chat-v2 request → confirm the verification (llm_judge) call ran on the cheap deployment (Trace span model = cheap / cost line cheap-priced) while the main turn ran on the strong deployment; screenshot + observed-vs-intended diff in progress.md. (Per CLAUDE.md §Drive-Through Acceptance — "the verification demonstrably used the cheap model with a visible cost delta" is the leg-specific assertion; the cost saving existing in code alone is gate/probe, not drive-through.)

---

## 4. File Change List

| File | Change |
|------|--------|
| `backend/src/adapters/_base/model_profile.py` (NEW) | **NEW** — `@dataclass(frozen=True) ModelProfile` (`action`/`cheap`: `ChatClient`); provider-neutral; seam docstring. File-header. |
| `backend/src/adapters/_base/__init__.py` | **EDIT** — re-export `ModelProfile` (Day-1 confirm pattern). MHist 1-line. |
| `backend/src/api/v1/chat/handler.py` | **EDIT** — build strong + cheap `AzureOpenAIAdapter` (cheap from `AZURE_OPENAI_CHEAP_*` env, fallback cheap=action); `ModelProfile`; pass `profile.cheap` to the verifier factory, `profile.action` to loop + compactor. MHist 1-line. |
| `backend/src/adapters/azure_openai/config.py` or a handler-local cheap-config builder (Day-1 pick) | **EDIT (conditional)** — a helper to build a cheap `AzureOpenAIConfig` reusing shared endpoint/key + cheap deployment/pricing. MHist 1-line. |
| `backend/src/<verification cost path>` (Day-1 locate) | **EDIT (conditional)** — ensure the verification cost uses the verifier client's `get_pricing()` (cheap-priced). MHist 1-line. |
| `backend/src/<LLM-call span site>` (Day-1 locate — adapter or loop span) | **EDIT (conditional)** — add `model`/`deployment` span attribute so the per-call model is observable. MHist 1-line. |
| `.env.example` | **EDIT** — document `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` + cheap pricing (optional; unset = fall back to main deployment). |
| `backend/tests/.../test_model_profile*.py` (NEW) | **NEW** — `ModelProfile` value object + cheap-config fallback + verifier-routing + cost-attribution. |
| `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-97-plan.md` + `-checklist.md` | **NEW** — this plan + checklist. |
| `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-97/progress.md` + `retrospective.md` | **NEW** — Day 0-N progress + retro (with the spike design-note 8-pt self-check). |
| `claudedocs/4-changes/feature-changes/CHANGE-064-multi-model-profile-verification.md` | **NEW** — the change record. |
| `docs/03-implementation/agent-harness-planning/24-multi-model-profile-design.md` (Day-0 confirm number) | **NEW (MANDATORY — spike)** — design-note extract (8-pt gate). |
| `docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` | **EDIT** — register `ModelProfile` (provider-neutral value object pairing `ChatClient`s; owner = design note 21). |

**NOT in this list (unchanged)**: `loop.py` (diff = 0 — receives `profile.action`) · the `ChatClient` ABC (`chat_client.py` — WRAPPED, not changed) · the compactor + memory-extraction call SITES (still get the strong client; only their handler argument is `profile.action` instead of the bare client — a rename, not a behavior change) · no DB/migration · no event schema (`check_event_schema_sync` unaffected) · no frontend (the drive-through reads the existing Trace/cost UI).

---

## 5. Acceptance Criteria

- A NEW provider-neutral `ModelProfile(action, cheap)` value object exists in `adapters/_base/`, holding only `ChatClient` refs (no SDK import); 17.md registered; `ChatClient` ABC unchanged (US-1).
- `handler.py` builds a strong + a cheap adapter (cheap from `AZURE_OPENAI_CHEAP_*` with `unset → cheap = action` byte-identical fallback) and a `ModelProfile`; cheap pricing/deployment flow into the cheap config (US-2).
- The verification (`LLMJudgeVerifier`) call runs on `profile.cheap`; the main action turn (`loop.py:1954`) + compaction run on `profile.action`; the action turn's behavior/cost is unchanged (US-3).
- The verification cost is attributed to the cheap pricing; the per-call model is observable (Trace span model attr); `check_llm_sdk_leak` 0; `loop.py` diff = 0 (US-4).
- `mypy --strict src/` 0; `run_all` 10/10; `black`/`isort`/`flake8 src/ tests/` clean (run independently); full backend pytest green (NET deltas documented); CHANGE-064 + **design-note 21 (8-pt gate)** + 17.md `ModelProfile` registration.
- **Drive-through PASS**: real UI + real backend + real Azure with a real cheap deployment — the verification call demonstrably ran on the cheap deployment (Trace span model = cheap / cost line cheap-priced) while the main turn ran on the strong deployment; screenshot + observed-vs-intended diff. (No "gate-only" claimed as drive-through.)

---

## 6. Deliverables

- [ ] `ModelProfile(action, cheap)` value object in `adapters/_base/model_profile.py` + re-export + 17.md registration (US-1)
- [ ] Cheap config builder + `AZURE_OPENAI_CHEAP_*` env (fallback cheap=action) + `.env.example` doc (US-2)
- [ ] `handler.py` builds strong + cheap adapters + `ModelProfile`; verifier ← `profile.cheap`; loop + compactor ← `profile.action` (US-3)
- [ ] Verification cost cheap-priced (verifier `get_pricing()`); LLM-call span `model` attribute (Day-1 confirm/add); `loop.py` diff = 0; `check_llm_sdk_leak` 0 (US-4)
- [ ] Tests (backend): `ModelProfile` value object / cheap-config fallback (unset→identity) / verifier-routing (judge gets cheap, loop gets action) / cost-attribution (cheap pricing) / 57.83 verification tests unchanged (US-1..US-4)
- [ ] mypy 0 + run_all 10/10 + format chain (run independently) (validation)
- [ ] **drive-through PASS** (real UI + real backend + real Azure + real cheap deployment; verification ran cheap, visible cost delta; screenshot + before/after diff) (US-5)
- [ ] CHANGE-064 + progress.md + retrospective.md + **design-note 21 (8-pt gate)** + 17.md `ModelProfile` registration
- [ ] commit (Day 0-N) — push + PR user-authorized

---

## 7. Workload Calibration

Scope class: **`multi-model-profile-spike` (NEW, 0.55 mid-band) — 1st data point, pending 2-3 sprint validation**. A new-domain backend spike (NEW value-object contract + config + factory rewiring + conditional cost/observability wiring + design-note extract), distinct from the recent Cat 11 / pause-resume classes. The work splits: `ModelProfile` value object + 17.md (~1 hr) / cheap config builder + env + fallback + `.env.example` (~2 hr) / verifier rewiring + cost-attribution verify/wire (~2 hr) / observability (span model attr — conditional) (~1 hr) / tests (~3 hr) / drive-through (configure a real cheap deployment + drive + show cost delta) (~2 hr) / docs (design-note 8-pt gate + CHANGE-064 + progress + retro + 17.md) (~3 hr). Dominant costs = tests + design-note + drive-through (the cheap-deployment configuration + cost-delta verification are parent correctness work). **Agent-delegated: no** (parent-direct) — the cost-attribution correctness and the drive-through (a real-money cost-delta assertion) are parent verification work; the config plumbing + tests could be agent-delegated once this seam lands. `agent_factor = 1.0`; does NOT extend the AgentDelegated-WallClock streak.

> Bottom-up est ~14 hr → class-calibrated commit ~7.5 hr (mult 0.55). **Agent-delegated: no.**

If Day-1 shows the wiring ripples wider than the spec'd files (e.g. the verification cost is computed centrally in the loop using the loop's client → moving it to the verifier's pricing cascades; the LLM-call span has no model attribute and adding it touches every adapter; the verifier factory shape forces an ABC change; `AzureOpenAIConfig` BaseSettings can't be partially overridden without a subclass), STOP and re-scope rather than rush.

---

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **Cheap deployment not configured at drive-through time** | The user confirmed a cheaper deployment is available. Day-0/Day-3: confirm/create the cheap Azure deployment + set `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` + cheap pricing in `.env`. If unavailable at drive-through, the fallback (cheap=action) still ships + tests pass, but the drive-through cost-delta is deferred (record honestly as "seam verified, cost-delta pending real deployment" — NOT a full drive-through PASS). |
| **Cost computed centrally with the loop's client (cheap judge mis-priced)** | Day-1 read the verification cost path. If central, wire it to use the verifier client's `get_pricing()` (the spike's correctness crux). A cost-attribution test guards it (cheap-priced client → cheap cost). |
| **Per-call model not observable (drive-through has no visible proof)** | Day-1 confirm the LLM-call span carries `model`/`deployment`. If not, add the attribute (small, reads `config.deployment_name`/`model_info()`). The drive-through anchors on the Trace span model = cheap vs action = strong (and/or the cost line). |
| **`AzureOpenAIConfig` (BaseSettings) hard to partially override for the cheap tier** | Build the cheap `AzureOpenAIConfig` by passing explicit kwargs (cheap deployment/model/pricing) + reusing the strong config's `endpoint`/`api_key`/`api_version` — BaseSettings accepts explicit kwargs overriding env. Avoid a cheap-prefixed BaseSettings subclass unless the kwarg path is messy (Day-1 pick the tidier site). |
| **Fallback not byte-identical (behavior drift when cheap unset)** | When `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` unset, set `cheap = action` (the SAME instance, identity) — not a second adapter with the same config. A test asserts `profile.cheap is profile.action`. The verifier then gets the same client it gets today → byte-identical. |
| **Cheap judge accuracy regression (verification less reliable)** | Out of scope to formally benchmark; documented as a design-note Open Invariant. The drive-through observes the judge still functions on the cheap model; if it visibly mis-verifies, note it + recommend keeping the judge on the strong tier (the seam supports per-phase choice). The action turn is NEVER cheap (user-facing quality preserved). |
| **Neutrality (SDK leak)** | `ModelProfile` imports only `ChatClient` (the ABC); the concrete `AzureOpenAIAdapter` is built in `handler.py` (under `api/`, allowed). `check_llm_sdk_leak` gates. |
| **Echo/demo handler path** | The echo/demo handler has no real verifier — Day-1 confirm `build_echo_demo_handler` is untouched (only `build_real_llm_handler` builds the profile). |
| **Risk Class E (stale `--reload` backend)** | Clean restart before the drive-through (kill stale uvicorn reloader+worker; verify :8000 OWNER is the fresh PID) — the cheap client is built at startup from env; a stale process built before the env change runs the single-client path. Bit 57.91-96 (6 consecutive). The cheap env vars must be set BEFORE the restart. |
| **Risk Class C (test isolation)** | The profile is per-handler (per request), no module singleton; mock-adapter tests don't touch real env. Run the full suite; existing chat conftest reset fixtures cover the handler. |
| **Over-engineering (Scope creep)** | Only the verifier moves to cheap this sprint; NO `for_phase()` dispatcher, NO loop threading, NO compaction/thinking/memory cheap-tier, NO per-tenant policy (Karpathy §2/§3). |
| **Smuggling unrelated change** | The diff is exactly: `ModelProfile` + `__init__` re-export + `handler.py` wiring + cheap-config builder + (conditional) cost/span wiring + `.env.example` + tests + docs. `loop.py`/`ChatClient`-ABC/compactor-memory-call-sites/frontend/DB diff = 0 (the compactor/memory args become `profile.action`, a rename). |
| **`&&`-chained format checks mask failures (57.95 CI lesson)** | Run `black --check`/`isort --check`/`flake8`/`mypy` INDEPENDENTLY before push. |

---

## 9. Out of Scope (this sprint; → separate slices / ADs)

- **Compaction / memory-extraction / thinking cheap-tier** — the seam (`ModelProfile`) is built; only verification is wired. Adding `profile.compaction` etc. is a follow-on (the design note documents the pattern). Compaction is the highest token-volume target but needs a long conversation to drive-through.
- **Threading `ModelProfile` into the loop** — this sprint keeps it handler-local (constructed + consumed in `handler.py`). Threading it into `AgentLoopImpl` for in-loop per-phase selection is a separate slice.
- **Per-tenant model policy (Config 分層)** — a tenant choosing its own model/budget/guardrail override is the SEPARATE "Config 分層" parity gap (cc-parity §7.3), not this sprint.
- **Cheap-judge accuracy benchmark** — documented as a design-note Open Invariant; not formally measured.
- **Non-Azure cheap tiers** — the seam is provider-neutral but only the Azure adapter is wired; an Anthropic/OpenAI cheap tier is a follow-on.
- **A `ModelProfileChatClient` ABC implementation** (per-call phase dispatch) — rejected (the ABC has no phase param; would break the contract — see design-note Decision Matrix).
