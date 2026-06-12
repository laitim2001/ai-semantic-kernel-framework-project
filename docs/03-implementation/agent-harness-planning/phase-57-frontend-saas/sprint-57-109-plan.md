# Sprint 57.109 Plan — C2: compaction cheap tier (semantic summarize → `profile.cheap`) + compaction cost-ledger attribution (`_compaction` sub_type, the 57.82 verification mirror) + ops-tunable compaction budget knob — memory extraction stays strong by design

**Status**: Draft (pending user approval)
**Branch**: `feature/sprint-57-109-compaction-cheap-tier`
**Base**: `main` HEAD `f4089fd9` (post-#283 merge)
**Slice**: C2 per the interleave decision (RBAC → C3 → B3 → UX ✅ → **C2** → B4) — the LAST C-family slice; closes harness-deepening proposal §3.4 C2 (design note 24 first carryover: "compaction cheap tier").
**Scope decisions**: (a) the proposal DoD "ledger 顯示 compaction tokens 降級" requires NEW attribution plumbing — compaction LLM usage is captured NOWHERE today (the summarize call bypasses loop events); mirror the 57.82 `_verification` chain exactly. (b) compaction is UNREACHABLE in a real-UI drive-through at today's thresholds (75k tokens / 30 turns, both per-run transient) — add an env-tunable token budget (`CHAT_COMPACTION_TOKEN_BUDGET`, default 100_000 unchanged) as the ops knob + drive-through lever (57.106 escalate-phrase precedent: a real governable lever, not a test hack).

---

## 0. Background

Proposal §3.4 C2: "compaction cheap tier（`semantic.py` summarize → profile.cheap）+ 30+ turn 長對話品質 gate（AP-7 測試既有要求）；memory extraction 維持 strong（無 benchmark 前不降）" — DoD "30+ turn 長對話 compaction 走 cheap tier，壓縮品質測試續綠，ledger 顯示 compaction tokens 降級". The ChatClient consumer map (proposal line 208) marks semantic compactor as the named cheap candidate; verification already moved (57.97), per-tenant model selection already governs both tiers (C1 57.104).

### Design decision (one-line retier + 57.82-mirror attribution + env knob; wire/codegen/FE/DB ALL untouched)

- **Retier is one line**: `handler.py:460` `compactor = make_chat_compactor(chat_client)` → `make_chat_compactor(profile.cheap)`. When no cheap deployment is configured, `build_azure_model_profile` returns `cheap is action` (profile.py:84-85) → env-only deployments stay byte-identical (safe rollout, the 57.97 invariant).
- **Attribution mirrors 57.82 exactly**: verification chain = `VerificationResult.input_tokens/output_tokens` (verification.py:42-46) → loop accumulator → `LoopCompleted.verification_*` → router observer enqueues `sub_type_suffix="_verification"` (router.py:702-705) → `record_llm_call` (cost_ledger.py:107-141). Compaction gets the same shape: `CompactionResult` += defaulted usage fields (semantic.py captures the summarize `ChatResponse` usage + model) → loop.py compaction site (:2139 region) feeds the accumulator → `LoopCompleted` += compaction token fields → observer enqueues `sub_type_suffix="_compaction"`. Ledger rows: `{provider}_{cheap_model}_compaction_input` + `_compaction_output`.
- **Env knob**: `_CHAT_TOKEN_BUDGET` (_category_factories.py:97, hardcoded 100_000) reads `CHAT_COMPACTION_TOKEN_BUDGET` env with the same default. Real ops use (budget tuning per deployment) + the only practical drive-through trigger.
- **Memory extraction UNTOUCHED**: extraction stays on `profile.action` per the proposal (precision-sensitive; no benchmark yet — design note 24 keeps that invariant open).
- **Rejected**: threading ModelProfile into the loop (proposal §233 — deferred-indefinitely, construction-time DI covers all real needs); new `context_compacted` wire fields or FE rendering (no consumer — the ledger/cost dashboard is the surface; chatStore:631 keeps rawEvents-only); a per-tenant compaction-policy field on `harness_policy` (YAGNI until a tenant asks — env-level suffices; the C3 meta_data pattern is the graduation path); retiering memory extraction (benchmark-gated).

### Ground truth (Day-0 head-start — 2 Explore recon agents + direct greps, file:line anchors on `main` HEAD `f4089fd9`)

- **Compactor wiring**: `make_chat_compactor(chat_client)` (_category_factories.py:101-114) → `HybridCompactor(StructuralCompactor(), SemanticCompactor(chat_client=...), token_budget=_CHAT_TOKEN_BUDGET, ...)`; sole call site `handler.py:460`; the client passed is `profile.action` (handler.py:327). `_CHAT_TOKEN_BUDGET = 100_000` / `_CHAT_TOKEN_THRESHOLD_RATIO = 0.75` (:97-98).
- **Summarize call**: `SemanticCompactor._summarise()` → `self.chat_client.chat(request, trace_context=...)` (semantic.py:130; retry 1+1, `SemanticCompactionFailedError` on exhaustion). Its usage/model is read NOWHERE (greps: no `usage`/`input_tokens` reads in semantic.py beyond state estimates).
- **Verification attribution chain (the mirror)**: `VerificationResult.input_tokens/output_tokens` defaults 0 (verification.py:42-46) → accumulator → `LoopCompleted.verification_input_tokens/verification_output_tokens` → router.py:690-710 observer (`sub_type_suffix": "_verification"` at :705) → `record_llm_call` with `sub_type_suffix` (cost_ledger.py:107-141; idempotency split billing_outbox.py:75-77).
- **Compaction loop site**: `loop.py:2139` `compact_if_needed(...)` inside the COMPACTION span (:2124-2149); `ContextCompacted` yielded only when triggered (:2158-2164). `ContextCompacted` (events.py:232-237) carries tokens_before/after/strategy/messages_compacted/duration_ms — NO summarize usage/model (wire stays as-is).
- **Trigger reachability**: transient `turn_count`/`tokens_used` reset per `run()` (loop.py:1881-1882); chat main-loop `max_turns=50` default (loop.py:388); NO env override exists → 75k tokens / 30 turns unreachable in a drive-through without the knob.
- **Tests today**: 5 compaction suites, 1,118 lines (unit structural/semantic/hybrid + integration `test_loop_compaction_30turn.py` + `test_compaction_latency_slo.py`) — all mock-client; the cheap retier does not disturb them. Full pytest baseline 2462+4skip; wire count 24; FE Vitest 836 / mockup-fidelity 51 (untouched this sprint).

### STALE / drift anchors to re-confirm in the formal Day-0 三-prong (§ checklist 0.1)

`ChatResponse` usage/model field availability at the compactor seam (what exactly does `chat()` return — `input_tokens`/`output_tokens`/`model` names?) · what MODEL the `_verification` enqueue attributes (does `LoopCompleted` carry a verification model, or does the observer reuse the loop `event.model`? — the compaction mirror must attribute the CHEAP model truthfully) · `CompactionResult` constructor sites (structural.py / semantic.py / hybrid.py / no-op paths / tests — frozen dataclass, defaulted fields, keyword-style?) · hybrid result pass-through (does HybridCompactor re-construct or forward semantic's result? hybrid.py:59-78) · accumulator class name + where verification tokens are folded (loop.py:3500-3510 region) · `LoopCompleted` constructor sites keyword-style · billing_outbox idempotency key shape for a new suffix (:75-77) · `_CHAT_TOKEN_BUDGET` import sites · `.env.example` compaction/cheap entries (AZURE_OPENAI_CHEAP_* present?) · design note 24 file path (Glob) · structural-only compaction (no LLM call) must enqueue NOTHING (zero-usage guard mirror of `verification_*tokens > 0` at router.py:702).

## 1. Sprint Goal

Compaction's semantic summarize runs on the tenant's CHEAP tier (`profile.cheap` — per-tenant governable via the C1 model policy; env-only deployments without a cheap config stay byte-identical), its real LLM usage lands in the cost ledger as `{provider}_{model}_compaction_input/_output` rows (the 57.82 `_verification` mirror — today that cost is invisible), the compaction token budget becomes env-tunable (`CHAT_COMPACTION_TOKEN_BUDGET`, default unchanged), and the 30+ turn quality gates stay green with zero test deletions — proven by a real-UI drive-through (lowered budget → live `ContextCompacted` → cheap-model `_compaction` ledger rows; memory extraction verified still strong). Closes proposal §3.4 C2.

## 2. User Stories

- **US-1**: 作為 platform，我希望 `make_chat_compactor` 收到 `profile.cheap`（取代 `handler.py:460` 的 action client），以便 semantic summarize 跑 cheap tier；cheap 未配置時 `cheap is action` 行為 byte-identical（57.97 不變量），且 per-tenant model policy（C1）自動同時治理 compaction tier。
- **US-2**: 作為 tenant admin，我希望 compaction summarize 的真實 usage（input/output tokens + 真實 cheap model 名）經 `CompactionResult` → accumulator → `LoopCompleted` → router observer 以 `sub_type_suffix="_compaction"` 入 cost ledger（鏡像 57.82 `_verification`），以便成本面板誠實顯示 compaction 開銷在哪個 tier；structural-only / 未觸發 compaction 時零 enqueue。
- **US-3**: 作為 ops，我希望 compaction token budget 可由 `CHAT_COMPACTION_TOKEN_BUDGET` env 調整（default 100_000 不變、invalid 值 fallback default），以便部署層調參——同時是 drive-through 的觸發桿。
- **US-4**: 作為 reviewer，我希望 drive-through 證明：lowered budget + 真 LLM 對話 → compaction 真實觸發（`ContextCompacted` 在 wire/raw events 可見）→ cost ledger 出現 cheap model 的 `_compaction` rows → 對話品質未劣化（compaction 後 agent 仍能引用早期上下文）→ memory extraction 仍走 action tier——全程真 UI + 真後端 + 真 Azure。

## 3. Technical Specifications

### 3.0 Architecture (backend-only; wire count 24 UNCHANGED; no codegen / no FE / no DB / no migration; loop.py touched at the compaction site + accumulator only)

```
handler.py:460:        compactor = make_chat_compactor(profile.cheap)        # was: chat_client (action)
_category_factories:   _CHAT_TOKEN_BUDGET = int(os.environ.get("CHAT_COMPACTION_TOKEN_BUDGET", 100_000)-shaped)
_contracts/compaction: CompactionResult += {input_tokens: int = 0, output_tokens: int = 0, model: str = ""}
semantic.py:           _summarise captures ChatResponse usage + model into the result
loop.py compaction site: feeds accumulator (compaction_input/output_tokens + model)
_contracts/events.py:  LoopCompleted += compaction token/model fields (defaulted; wire loop_end UNTOUCHED)
router.py observer:    compaction tokens > 0 → billing_outbox.enqueue(sub_type_suffix="_compaction", model=<cheap model>)
cost_ledger / billing_outbox: UNCHANGED (sub_type_suffix mechanism is 57.82 infrastructure)
memory extraction / prompt builder / subagents / verification: UNTOUCHED (stay on their current tiers)
```

### 3.1 Compactor cheap retier (US-1)

`handler.py:460` passes `profile.cheap`; the §321-327 comment block updated to document the THREE-tier consumer map (loop/prompt=action · verification=cheap 57.97 · compaction=cheap 57.109). `make_chat_compactor` signature unchanged. Handler-level unit test pins the compactor's semantic client IS the profile's cheap client (mirror the 57.97 verifier-tier test shape). Cheap-unset path: existing profile tests already pin `cheap is action` — no new test needed, cite it.

### 3.2 Compaction cost attribution (US-2 — the 57.82 mirror)

`CompactionResult` (frozen, _contracts/compaction.py:48-72) += `input_tokens: int = 0` + `output_tokens: int = 0` + `model: str = ""` (defaulted → structural/no-op constructors stay valid; grep ALL constructors at Day-0). `SemanticCompactor._summarise` reads the summarize `ChatResponse` usage/model into the result (retry path: count the SUCCESSFUL attempt; failed attempts' usage is a known blind spot — documented, not silently dropped). Hybrid forwards semantic's fields (Day-0 confirms construct-vs-forward). loop.py compaction site folds result usage into the metrics accumulator; `LoopCompleted` += `compaction_input_tokens: int = 0` / `compaction_output_tokens: int = 0` / `compaction_model: str = ""` (defaulted; `loop_end` WIRE SCHEMA untouched — count 24, no codegen). Router observer: `compaction_input_tokens > 0 or compaction_output_tokens > 0` → enqueue with `sub_type_suffix="_compaction"` + the compaction model (truthful cheap attribution — exact model-field shape pinned at Day-0 from the `_verification` precedent). Idempotency: distinct suffix → distinct key (verify billing_outbox.py:75-77 shape).

### 3.3 Compaction budget env knob (US-3)

`_category_factories.py` `_CHAT_TOKEN_BUDGET` becomes env-read (`CHAT_COMPACTION_TOKEN_BUDGET`; default 100_000; non-int → default, no crash). Module-import-time read is acceptable (matches existing const placement; the backend restarts on env change anyway — Risk Class E discipline applies at drive-through). `.env.example` documents it. Unit test: monkeypatched env → factory threshold honors it.

### 3.4 What is explicitly NOT done

Memory extraction stays `profile.action` (proposal: benchmark-gated; design note 24 invariant stays open for that half); NO `context_compacted` wire/FE changes (ledger + cost dashboard are the surface); NO per-tenant compaction policy (env-level only; C3 meta_data pattern = graduation path); NO ModelProfile threading into the loop (proposal §233); NO change to compaction strategy/threshold logic, structural compactor, or the 75% ratio; failed-attempt usage counting (blind spot documented in CHANGE record).

### 3.5 Validation (US-1..US-4)

Unit (backend): handler compactor-tier pin · `CompactionResult` defaults + semantic usage capture (mock client returns usage → result carries it; structural result zeros) · accumulator fold + `LoopCompleted` fields · observer `_compaction` enqueue (tokens > 0) + zero-usage no-enqueue · env knob honored + invalid-fallback. Integration: existing 30-turn + latency-SLO suites green UNCHANGED (0 del — the AP-7 quality gate). Gates: mypy strict 0 · run_all 10/10 (count 24 UNCHANGED; no codegen diff) · full pytest 0 del · FE untouched (Vitest 836 / mockup-fidelity 51 hold trivially) · `loop.py` diff = compaction-site fold + accumulator only.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/api/v1/chat/handler.py` | EDIT — :460 `profile.cheap` + tier-map comment |
| 2 | `backend/src/api/v1/chat/_category_factories.py` | EDIT — `_CHAT_TOKEN_BUDGET` env-read |
| 3 | `backend/src/agent_harness/_contracts/compaction.py` | EDIT — `CompactionResult` +3 defaulted fields |
| 4 | `backend/src/agent_harness/context_mgmt/compactor/semantic.py` | EDIT — capture summarize usage/model |
| 5 | `backend/src/agent_harness/context_mgmt/compactor/hybrid.py` | EDIT (if construct-not-forward per Day-0) |
| 6 | `backend/src/agent_harness/orchestrator_loop/loop.py` | EDIT — compaction site → accumulator fold |
| 7 | `backend/src/agent_harness/_contracts/events.py` | EDIT — `LoopCompleted` +3 defaulted fields |
| 8 | `backend/src/api/v1/chat/router.py` | EDIT — observer `_compaction` enqueue |
| 9 | `.env.example` | EDIT — document `CHAT_COMPACTION_TOKEN_BUDGET` |
| 10 | backend tests: compactor semantic/structural/hybrid CONVERT + handler tier pin + observer enqueue + knob ADD | CONVERT/ADD (0 deletions) |
| — | wire schema / codegen artifacts / FE / DB / migrations / memory extraction / verification | **UNTOUCHED** |

## 5. Acceptance Criteria

1. The chat compactor's semantic client IS `profile.cheap` (test-pinned); cheap-unset env keeps `cheap is action` → byte-identical behavior (existing profile test cited).
2. A triggered semantic compaction produces exactly 2 ledger entries `{provider}_{cheap_model}_compaction_input/_output` with real token counts + truthful model; structural-only or no-trigger runs enqueue NOTHING.
3. `CHAT_COMPACTION_TOKEN_BUDGET` env honored (default 100_000; invalid → default).
4. All 5 existing compaction suites + full pytest green with 0 deletions; wire count 24 unchanged; no codegen diff; mypy/run_all/format chain green; `loop.py` diff limited to the compaction site + accumulator.
5. Real-LLM drive-through PASS: lowered budget → live `ContextCompacted` → cheap-model `_compaction` ledger rows → post-compaction answer still references early-conversation facts → memory extraction row still on action tier. Closes proposal §3.4 C2; design note 24 "compaction cheap tier" invariant marked resolved (extraction half stays open).

## 6. Deliverables

- [ ] US-1 compactor cheap retier + handler tier-pin test
- [ ] US-2 attribution chain (CompactionResult → accumulator → LoopCompleted → observer `_compaction`) + tests
- [ ] US-3 env knob + `.env.example` + test
- [ ] US-4 drive-through PASS (screenshots + observed-vs-intended + ledger rows)
- [ ] CHANGE-076 + closeout (retro Q1-Q7 + calibration + navigators + design note 24 edit + next-phase-candidates)

## 7. Workload Calibration

- Scope class **`multi-model-profile-spike` 0.55** — 2nd data point (57.97 1st pt ratio ~0.93 IN band: same shape — a ChatClient consumer retiered to cheap + attribution + drive-through, adapters/billing seam, parent-direct, no FE). NOT `config-tiering-model-policy-spike` 0.60 (that family is full-stack admin-PUT/GET + tenant tab; C2 has no admin surface).
- **Agent-delegated: no** — parent-direct (loop.py accumulator + observer billing edits are correctness-sensitive; total diff is small); `agent_factor = 1.0`, 3-segment form.
- Bottom-up est ~8 hr (US-1 ~1 + US-2 ~3 + US-3 ~0.5 + drive-through ~1.5 + docs/closeout ~2) → class-calibrated commit ~4.5 hr (mult 0.55). Day 4 retro Q2 verifies.

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| `ChatResponse` may not expose usage/model at the compactor seam | Day-0 Prong-2 reads the `ChatResponse` contract (the loop reads usage from it every turn — fields exist; pin exact names) |
| `_verification` enqueue's MODEL attribution shape unknown (does LoopCompleted carry a verification model?) | Day-0 reads router.py:690-710 + LoopCompleted fields; mirror EXACTLY — if verification mis-attributes the action model, fix-forward compaction truthfully and log an AD for verification |
| Frozen-dataclass field additions break constructors (`CompactionResult` ×3 strategies + tests; `LoopCompleted`) | defaulted fields + Day-0 grep ALL constructor sites (keyword-style check — 57.108 D7 precedent) |
| billing_outbox idempotency key collides for the new suffix | Day-0 reads :75-77 (the `_verification` split precedent says suffix participates in the key) |
| Drive-through trigger unreachable at default thresholds | the US-3 env knob IS the lever (set BEFORE the clean restart — Risk Class E + 57.97 orphaned-spawn-worker sweep) |
| Local cheap deployment not configured (`AZURE_OPENAI_CHEAP_*` unset → cheap is action → dt can't show tier delta) | Day-0 checks `.env`; fallback lever = C1 per-tenant model policy tab sets a distinct cheap deployment for the dt tenant (proven in the 57.104 drive-through) |
| Hybrid re-constructs the result and drops semantic's usage fields | Day-0 reads hybrid.py:59-78; forward-or-copy explicitly |
| Retry path double-counts usage on retry-then-success | count the successful attempt only; failed-attempt usage = documented blind spot (CHANGE-076) |
| Risk Class E — stale backend masks the retier at drive-through | clean no-reload restart + `Win32_Process` orphan sweep + startup probe before driving |
| 30-turn integration suite breaks on the result-field change | suites are mock-based asserting trigger/strategy fields — defaulted additions are invisible; run them first on Day 1 |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- Memory extraction cheap tier (benchmark-gated — design note 24 invariant stays open).
- Per-tenant compaction policy on `harness_policy` meta_data (graduate when a tenant needs it; C3 pattern ready).
- `context_compacted` FE rendering / Inspector compaction visualization (own UX slice if demanded).
- ModelProfile threading into the loop (proposal §233 deferred-indefinitely).
- Verification model-attribution fix if Day-0 finds it wrong (own AD, not folded in).
- B4 / A3 (next slices per interleave).
