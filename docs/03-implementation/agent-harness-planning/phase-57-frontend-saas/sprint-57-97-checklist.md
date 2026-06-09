# Sprint 57.97 — Checklist (Multi-model profile — cheap tier for verification; the llm_judge runs on a cheaper deployment than the main action turn)

**Plan**: [`sprint-57-97-plan.md`](./sprint-57-97-plan.md)
**Created**: 2026-06-09
**Status**: Day 0-1 done (code-complete + mypy 0/353); Day 2 tests next; drive-through (Day 3) needs the cheap deployment + llm_pricing.yml alignment

> Rule: only `[ ]` → `[x]`; never delete unchecked items; defer with `🚧 + reason`.
> **Spike** (new-domain: first multi-model profile) → Day-4 design-note extract MANDATORY (`sprint-workflow.md §Step 5.5` 8-pt gate) → `24-multi-model-profile-design.md`. Record = CHANGE-064 + 17.md `ModelProfile` registration. Gate = full backend pytest green (NET delta) + **drive-through PASS** (verification demonstrably ran on the cheap deployment with a visible cost delta vs the strong main turn). Locked scope (AskUserQuestion 2026-06-09): abstraction = **thin `ModelProfile` value object** `{action, cheap}`; first cheap-tier phase = **verification (llm_judge)**; cheap deployment **available** → drive-through measures a real cost delta. Out: compaction/memory/thinking cheap-tier, loop threading, per-tenant policy, `ModelProfileChatClient` ABC.

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify
- [x] **Prong 1 (path)**: re-confirm the Explore recon anchors — `ChatClient` ABC `adapters/_base/chat_client.py:69-93` (no `model=` param) / `AzureOpenAIAdapter.__init__` `azure_openai/adapter.py:121-127` + `config.py:34-98` (deployment/pricing) / `build_real_llm_handler` `api/v1/chat/handler.py:283-297` (single `AzureOpenAIAdapter`) + the verifier factory call (~`:265`) + `make_chat_compactor` (`:364`) / `LLMJudgeVerifier.__init__` `verification/llm_judge.py:74` + call `:90` / `loop.py:1954` action call / `check_llm_sdk_leak.py:37-43` / `adapters/_base/__init__.py` re-export pattern. (progress.md Day-0 Prong 1)
- [x] **Prong 2 (content)**: confirm — (a) per-call model param absent → per-construction seam; (b) verifier + compactor accept `ChatClient` at construction → cheap routing is DI-only, ABC/loop unchanged; (c) grep-0 existing `ModelProfile`/`model_tier`/`model_registry`; (d) `ModelProfile` holding only the ABC keeps neutrality; (e) **the verification cost path** — read WHERE the verification call cost/tokens are computed (verifier-local `self._chat.get_pricing()` vs central using the loop client) + whether `VerificationResult` captures `model`. (progress.md Day-0 Prong 2)
- [x] **Prong 2.5 (observability / drift)**: confirm — **D1**: does the LLM-call Trace span (Cat 12) carry a `model`/`deployment` attribute? (drive-through visible proof) — if NOT, adding it is in-scope (small). **D2**: the cheap config build path — can `AzureOpenAIConfig` (BaseSettings) be partially overridden via explicit kwargs (cheap deployment/pricing + shared endpoint/key) without a subclass? **D3**: `build_echo_demo_handler` has no real verifier → confirm only `build_real_llm_handler` builds the profile. **D4 (drift vs recon)**: the recon said "verifier shares THIS handler's adapter ~`:265`" — confirm the exact factory name (`make_chat_verifier_registry` vs `make_chat_verifier`) + signature accepts a `ChatClient`. (progress.md Day-0 Prong 2.5)
- [x] **Prong 3 (schema)**: N/A — no DB/migration/ORM/event-schema change (`check_event_schema_sync` unaffected). Confirm no new table/column.
- [x] **Baseline capture**: baseline = `main` HEAD (57.96 merged `1ecee053`; CI-green pytest 2283 / mypy 0/351 / run_all 10/10) — capture exact pytest number at branch creation; record NET delta after edits
- [x] **Design-note number locate**: `Glob docs/03-implementation/agent-harness-planning/2*-*.md` → **CONFIRMED 24** is the next free number (19-23 taken: 19-pause-resume / 20-iam-deep-dive / 20-subagent-child-loop / 21-iam-invites / 22-iam-credentials / 23-iam-registration) — plan drift D1 (plan v0 assumed 21) fixed
- [x] **Cheap deployment availability**: confirm the cheaper Azure deployment exists / can be created + the env var names to set (`AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` + cheap pricing) — needed BEFORE the Day-3 drive-through restart
- [x] Catalogue Day-0/Day-1 drift in progress.md; **go/no-go decision = GO** (D-DAY0-1 design-note number + D-DAY1-1 cost mechanism catalogued) (feasibility: cheap routing is DI-only; loop/ABC unchanged; the cost-attribution + span-model are the conditional bits to confirm)

### 0.2 Branch
- [x] Branch `feature/sprint-57-97-multi-model-profile` from `main` (`1ecee053`)
- [x] plan + checklist + progress committed (Day-0 commit)

---

## Day 1 — `ModelProfile` value object + cheap config + verifier rewiring (US-1/US-2/US-3)

### 1.1 The `ModelProfile` value object (US-1)
- [x] **`adapters/_base/model_profile.py`** — NEW `@dataclass(frozen=True) ModelProfile` (`action: ChatClient`, `cheap: ChatClient`); imports ONLY `ChatClient` (no SDK); seam docstring (future tiers add a field defaulting to action); file-header
  - DoD: `mypy src/ --strict` 0; `ModelProfile(action=mock, cheap=mock)` constructs + is frozen
- [x] **`adapters/_base/__init__.py`** — re-export `ModelProfile` (match the package pattern); MHist
  - DoD: `from adapters._base import ModelProfile` works; `check_llm_sdk_leak` 0

### 1.2 Cheap config + fallback (US-2)
- [x] **cheap config builder** (in `handler.py` or `azure_openai` helper — Day-0 D2 pick): read `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME`; SET → build a cheap `AzureOpenAIConfig` (shared endpoint/api_key/api_version + cheap deployment/model/pricing from `AZURE_OPENAI_CHEAP_*`, documented defaults + warning log if pricing unset); UNSET → `cheap = action` (same instance); MHist
  - DoD: unset → `profile.cheap is profile.action`; set → distinct adapter, `cheap.get_pricing()` = cheap rate
- [x] **`.env.example`** — document `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` + cheap pricing (optional; unset = fall back to main deployment)

### 1.3 Verifier wired to the cheap tier (US-3)
- [x] **`api/v1/chat/handler.py`** — build `action` + `cheap` adapters → `profile = ModelProfile(...)`; verifier factory ← `profile.cheap`; `AgentLoopImpl(chat_client=profile.action)` + `make_chat_compactor(profile.action)` + memory extraction ← `profile.action`; MHist
  - DoD: `LLMJudgeVerifier._chat is profile.cheap`; loop `_chat_client is profile.action`; cheap unset → both same instance
- [x] **mypy clean** on the backend files (full `src --strict` 0)

---

## Day 2 — Cost attribution + observability (US-4) + tests (US-1..US-4)

### 2.1 Cost attribution + span model (US-4)
- [ ] **verification cost path** (Day-0 Prong 2 locate) — confirm the verification cost uses the verifier client's `get_pricing()` (cheap-priced); if computed centrally with the loop client, wire it to the verifier's pricing; MHist (conditional)
  - DoD: a verification run with a cheap-priced client records cheap cost
- [ ] **LLM-call span `model` attribute** (Day-0 Prong 2.5 D1) — confirm the LLM-call Trace span carries `model`/`deployment`; if not, add it (reads `config.deployment_name`/`model_info()`); MHist (conditional)
  - DoD: the verification call's span shows the cheap deployment; the action call's span shows the strong deployment
- [ ] **`loop.py` diff = 0** — `git diff main..HEAD -- backend/src/agent_harness/orchestrator_loop/loop.py` empty
- [ ] **`check_llm_sdk_leak` 0** — `ModelProfile` + handler wiring don't leak an SDK import outside `adapters/<provider>/`

### 2.2 Backend tests (US-1..US-4)
- [ ] **`ModelProfile` value object** — constructs with 2 mock clients; frozen/immutable; module imports only the ABC (NEW `test_model_profile.py`)
- [ ] **cheap-config fallback** — env unset → `profile.cheap is profile.action` (identity); set → distinct adapter, cheap deployment + cheap pricing
- [ ] **verifier-routing** — `build_real_llm_handler` → `LLMJudgeVerifier._chat is profile.cheap` + loop `_chat_client is profile.action`; cheap unset → both same instance (no behavior change)
- [ ] **cost-attribution** — verification with a cheap-priced client → recorded verification cost = cheap pricing (not action pricing)
- [ ] **existing 57.83 verification + handler tests green** — UNCHANGED (the verifier now gets the cheap client but the default-ON behavior is identical when cheap=action)

---

## Day 3 — Full regression + drive-through (US-5) + CHANGE-064

### 3.1 Full gate sweep
- [ ] **Full backend pytest green (NET delta documented)** — baseline 2283 → expected +N; NO test deleted; 57.83 verification tests UNCHANGED + green
- [ ] **mypy 0 + run_all 10/10 + format chain** — mypy `src --strict` 0; run_all **10/10** (LLM SDK leak 0; AP-1; AP-4; `check_event_schema_sync` unaffected; check_cross_category_import green); `black`/`isort`/`flake8 src tests` clean — **run each INDEPENDENTLY, not `&&`-chained** (57.95 CI lesson)

### 3.2 Drive-through (US-5 — verification ran on the cheap deployment, visible cost delta)
- [ ] **Cheap deployment configured** — `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` (+ cheap pricing) set in `.env` to a real cheaper deployment BEFORE the restart
- [ ] **Clean backend restart (Risk Class E)** — kill stale 57.96 reloader+spawn-worker (python, not node); verify :8000 FREE → `dev.py start backend` → fresh PID owns :8000 (built with the cheap env); frontend node untouched; Azure live
- [ ] **Drove a chat-v2 request through real UI + real backend + real Azure** — BEFORE (this sprint): one model for everything; AFTER: the verification (llm_judge) call ran on the cheap deployment (Trace span model = cheap / cost line cheap-priced) while the main turn ran on the strong deployment. Observed-vs-intended table in progress.md Day 3.2
  - Evidence: `artifacts/sprint-57-97-{1-trace-verification-cheap-model,2-cost-delta}.png` + snapshot
- [ ] **Cost-delta confirm** — the verification cost is demonstrably lower (cheap pricing) than it would be on the strong model; the action turn cost unchanged

### 3.3 CHANGE-064 + design note + 17.md
- [ ] `claudedocs/4-changes/feature-changes/CHANGE-064-multi-model-profile-verification.md` written
- [ ] **`17-cross-category-interfaces.md`** — register `ModelProfile` (provider-neutral value object pairing `ChatClient`s; owner = design note 21)

---

## Day 4 — Closeout (+ spike design note)

### 4.1 Design note (MANDATORY — spike)
- [ ] **`24-multi-model-profile-design.md`** (Day-0 confirmed number) — per `claudedocs/templates/spike-design-note-template.md`; 8-point quality gate verified in retrospective.md:
  - [ ] 1. Section header maps to the spike US (e.g. "US-3: verification on cheap tier as wired in 57.97")
  - [ ] 2. each technical claim has file:line (e.g. `LLMJudgeVerifier._chat ← profile.cheap` at `handler.py:NNN`)
  - [ ] 3. Decision matrix (per-call vs per-construction; thin value object vs `ModelProfileChatClient` ABC vs direct injection)
  - [ ] 4. verification command (`pytest .../test_model_profile.py`)
  - [ ] 5. test fixture reference
  - [ ] 6. Open invariants split (verified: verifier runs cheap, cost cheap-priced / deferred-NOT-verified: compaction/thinking cheap-tier, per-tenant policy, cheap-judge accuracy benchmark)
  - [ ] 7. rollback path (unset `AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME` / revert the verifier factory arg)
  - [ ] 8. 17.md cross-ref (`ModelProfile` registered)

### 4.2 Closeout
- [ ] Full validation (parent re-verified): pytest +N / mypy 0/351 / run_all 10/10 / 57.83 verification tests unchanged / `loop.py` diff = 0 / **drive-through PASS** (screenshots + before/after observed-vs-intended cost delta)
- [ ] progress.md (Day 0-3.2) + retrospective.md (Q1-Q7) + **design-note 8-pt gate self-check recorded**
- [ ] Calibration: `multi-model-profile-spike` 0.55 (1st data point) + `agent_factor` 1.0 (parent-direct); recorded `calibration-log.md §3` + `sprint-workflow.md §Scope-class matrix` row; carryover (compaction/memory/thinking cheap-tier / loop threading / per-tenant policy / cheap-judge accuracy / non-Azure cheap tier) → next-phase-candidates.md
- [ ] MEMORY.md pointer + `project_phase57_97_multi_model_profile.md` subfile + CLAUDE.md lean (Current Sprint row + Last Updated) + CHANGE-064 + design-note 21 + 17.md registration
- [ ] commit (Day 0-N) + push + PR — **push + PR pending user authorization**
