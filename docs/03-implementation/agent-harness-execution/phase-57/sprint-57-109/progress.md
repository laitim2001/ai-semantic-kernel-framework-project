# Sprint 57.109 Progress — C2: compaction cheap tier + `_compaction` ledger attribution + budget knob

**Plan**: [sprint-57-109-plan.md](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-109-plan.md)
**Branch**: `feature/sprint-57-109-compaction-cheap-tier` (base `main` `f4089fd9`)

---

## Day 0 — 2026-06-12 — Plan-vs-Repo three-prong verify

### Prong 1 — path verify ✅

All EDIT targets Glob-1 (`handler.py` / `_category_factories.py` / `_contracts/compaction.py` / `compactor/{semantic,hybrid,structural,_abc}.py` / `orchestrator_loop/loop.py` / `_contracts/events.py` / `api/v1/chat/router.py`); design note 24 = `24-multi-model-profile-design.md`; 5 compaction test suites present; NO new src files. Prong 3 — N/A confirmed (no DB / no migration; `cost_ledger` sub_type + `billing_outbox` suffix are 57.82 infrastructure).

### Prong 2 — content verify — Drift findings

| ID | Finding | Implication |
|----|---------|-------------|
| D1 ✅ | `_verification` mirror FULLY pinned: `LoopCompleted.verification_model` EXISTS (events.py:178-180); observer payload = `model: event.verification_model or event.model or _FALLBACK` + `sub_type_suffix: "_verification"` + `llm_idempotency_key(session_id, "_verification")`, guarded `verification_*_tokens > 0` (router.py:683-709) | compaction mirror is a literal copy with `compaction_*` fields + `"_compaction"` |
| D2 ✅ | `CompactionResult(` constructors: 9 src sites (structural ×2 / semantic ×4 / hybrid ×3) + 2 test sites — ALL keyword-style | +3 defaulted fields safe; zero constructor breakage |
| D3 🔴 | `_summarise` returns `str` (semantic.py:100-148), NOT the response — plan §3.2 "or its caller" resolves to: change `_summarise` return shape to carry usage/model (e.g. tuple), extract at :208 call site | small signature change inside SemanticCompactor (private method — no external callers) |
| D4 | Hybrid re-constructs results at 3 sites; ONLY :166-174 ("both stages did work") wraps a triggered semantic result → forward usage there; failed-semantic fallback (:136) + structural-only (:119/:156) + passthrough (:89/:147) keep zeros correctly | one-site forward, not a generic pass-through |
| D5 | `LoopCompleted` constructed at **3 loop.py sites** (:2607/:2631/:2656), all already passing `verification_*` kwargs | compaction kwargs added at all 3 |
| D6 | `ChatResponse` = `model: str` + `usage: TokenUsage \| None` (chat.py:122-130) | usage may be None → guard to 0 |
| D7 | verif accumulation idiom: locals init :2003-2005 → accumulate :2538-2541 → 3 ctor sites; compaction site (:2139 region, COMPACTION span :2124-2149, `ContextCompacted` yield :2158-2164) is in the SAME scope | `compaction_in/out/model` locals mirror verbatim |
| D8 ✅ | idempotency key = `f"{session_id}:llm:{suffix or 'loop'}"` (billing_outbox.py:75-77) | `_compaction` naturally distinct; ZERO billing_outbox change |
| D9 | `TokenUsage` fields are `prompt_tokens` / `completion_tokens` (chat.py:99-105) — NOT input/output | semantic capture maps prompt→input, completion→output |
| D10 | `_CHAT_TOKEN_BUDGET` comment says it mirrors AgentLoopImpl default (loop.py:193) | env knob doc must state the divergence is intentional (compaction budget tunable independently of loop budget) |
| D11 | `.env.example` carries commented `AZURE_OPENAI_CHEAP_*` template (:76-77); local cheap likely unset (`cheap is action`) | dt tier-delta lever: set cheap env BEFORE clean restart (57.97 lesson), fallback C1 tenant model-policy tab |
| D12 🆕 | quota reconcile (router.py:596-609) counts `verification_*_tokens` into `actual_tokens` (57.82 B-8: judge tokens are real consumption) | compaction tokens mirror in — fold into the US-2 router edit (same file/region; small) |

### Go/no-go: **GO** — D3 (private-method signature) + D12 (one-expression addition) shift scope < 10%; all other findings confirm the plan shape.

---

## Day 1-2 — 2026-06-12 — Backend: retier + attribution + knob (US-1 + US-2 + US-3)

### Shipped

- **US-1 retier**: `handler.py:460+` → `make_chat_compactor(profile.cheap)` + three-tier consumer-map comment; 2 tier-pin tests (cheap routes to compactor / cheap-unset shares the action client — 57.97 mirror).
- **US-2 attribution**: `CompactionResult` +3 defaulted fields → `semantic.py` `_summarise` returns `(text, prompt, completion, model)` (D3) → `hybrid.py` :166 merged-result forward (D4) → **`ContextCompacted` +3 server-side fields** → loop.py yield carries them → router accumulates off the events + enqueues `sub_type_suffix="_compaction"` at LoopCompleted + folds into quota actual (D12). Tests: semantic ×2 / hybrid ×1 / cost-ledger integration ×4 (distinct `_compaction` row at the cheap model name / structural-zero no-enqueue / multi-compaction accumulates into ONE row / quota fold).
- **US-3 knob**: `_compaction_token_budget()` env-read (`CHAT_COMPACTION_TOKEN_BUDGET`; default 100k; invalid/non-positive → default) + budget threaded to ALL THREE compactors (D13) + `.env.example` + 7 unit cases.

### Drift findings (Day 1)

| ID | Finding | Implication |
|----|---------|-------------|
| D-DAY1-1 🔴 (design correction) | The plan §3.2 LoopCompleted-mirror is the WRONG carrier: `yield LoopCompleted(` has **30+ ctor sites** in loop.py (vs the 3 the verif kwargs ride), and compaction can trigger on ANY turn — a MAX_TURNS/budget exit after a compaction would silently drop the cost. Implemented instead: usage rides **`ContextCompacted`** (dataclass-only fields, wire untouched — the `handoff_context`/pre-57.108 `LLMResponded` precedent); the router accumulates off the events and bills at LoopCompleted. | `loop.py` diff shrinks to ONE yield site (+3 kwargs); EVERY termination path bills correctly — strictly better than the verification precedent it mirrors. Plan §3.2 kept as written (audit trail); this entry is the correction record. |
| D-DAY1-2 | NEW test file `tests/unit/api/v1/chat/test_category_factories.py` collided with the EXISTING `tests/unit/api/test_category_factories.py` (pytest unique-basename rule; standalone run passed, full run failed at collection) | knob tests appended to the EXISTING 57.63 file instead; duplicate deleted. Lesson: Glob the basename across the test tree before creating any new test file. |
| D-DAY1-3 | Resume path (router.py:976 `loop.resume`) has NO billing/quota observers — loop + verification tokens are already unbilled there (pre-existing) | compaction mirrors the main path only; noted in CHANGE-076 (candidate `AD-Resume-Billing-Observers`) |

### Gates (Day 1-2)

mypy **0/359** · black/isort/flake8 **0** · run_all **10/10** from repo root (event count/wire UNCHANGED — `check_event_schema_sync` green with NO codegen diff) · full pytest **2470+4skip non-e2e + 8 e2e = 2478 ≡ baseline 2462 + 16 new, 0 del** · `loop.py` diff = 1 yield site + MHist · touched suites: compactor 3 files / handler / factory / cost-ledger all green.

---

## Day 3 — 2026-06-12 — Drive-through (US-4) — PASS after two load-bearing findings

**Setup**: real UI :3007 (Vite PID 31616) + fresh no-reload backend (Risk Class E: killed stale 33124, sole-owner verified) + real Azure (action `gpt-5.2` / cheap `gpt-5.4-mini` — both already in `.env` from the 57.97 dt) + zero dev-login (founder@dt57105.test password-login, tenant `dt57105-rbac`). Knobs set BEFORE start: `CHAT_COMPACTION_TOKEN_BUDGET=2000` (+ later `CHAT_COMPACTION_KEEP_RECENT_TURNS=1` — see D-DAY3-2).

### Drift findings (Day 3)

| ID | Finding | Implication |
|----|---------|-------------|
| D-DAY3-1 🔴 (load-bearing) | First dt attempt (6 setup messages + tool-trigger message): compaction CHECK runs every turn (live `context_compacted` frames, tokens 2294/4794 > the 1500 threshold) but ALWAYS `messages_compacted=0` — **the chat main flow carries conversation continuity in Cat 3 memory (a memory hint returned BLUEFIN), NOT restored message history**; a loop run holds ONE user message, so the semantic cutoff `len(user_indices) > keep_recent_turns(5)` is structurally unreachable. The hybrid "triggered" frames were structural-tagged no-ops. | Semantic compaction was a latent main-flow no-op since 52.1 (invisible until this dt). Two consequences: (a) the `CHAT_COMPACTION_KEEP_RECENT_TURNS` knob (D-DAY3-2); (b) carryover `AD-Semantic-Compaction-User-Turn-Anchor` — the user-turn-anchored cutoff may deserve a message-count anchor in a future Cat 4 slice. |
| D-DAY3-2 (scope add, knob #2) | With keep=5 fixed, the only zero-code trigger is 6 successful B1 mid-run injections — timing-infeasible (the run finishes faster than the inject cadence; 1/6 landed). Added `CHAT_COMPACTION_KEEP_RECENT_TURNS` env knob (default 5 UNCHANGED; min 1 — a 0 would make the cutoff `user_indices[-0]` == `[0]`, a silent full-keep bug) threaded to both sub-compactors + 7 unit cases + `.env.example`. Same ops-knob family as US-3. | dt recipe became: keep=1 + budget=2000 → ONE successful B1 injection puts `user_indices=2 > 1` → semantic engages for real. |
| D-DAY3-3 | `billing_outbox` count for `_compaction` across the WHOLE dt day = exactly 1 (only the keep=1 run) — every earlier session/run enqueued NOTHING | live confirmation of the zero-usage guard (structural-only/no-op compactions bill nothing) |

### Observed vs intended (the PASS run — trace `5653b0c3eefb4d53b855f7c07aba51b6`)

| Step | Intended | Observed |
|------|----------|----------|
| 12-group patrol run + B1 inject "Note: my project codename is BLUEFIN." | inject lands mid-run | `message_injected` frame + "injected mid-run" UserTurn tag ✓ |
| Next turn pre-check | semantic compaction triggers | `context_compacted` **tokens_before=9824 → tokens_after=2679, messages_compacted=8, duration 3535ms** (a REAL summarize LLM call) ✓ |
| Summarize runs on the CHEAP tier | ledger attributes the cheap model | `billing_outbox` `{session}:llm:_compaction` payload model **`gpt-5.4-mini-2026-03-17`** (the live `response.model`, vs action `gpt-5.2`), in=260/out=149, status=done ✓ |
| Drainer materializes | cost_ledger rows | `azure_openai_gpt-5.4-mini-2026-03-17_compaction_input` 260 tok / **$0.000195** + `_compaction_output` 149 tok / **$0.0006705** (priced, non-zero) ✓ |
| Post-compaction quality | run continues; early fact survivable | turn-5 `prompt_built estimated_input_tokens=3411` (down from 9824); final answer block "my project codename is **BLUEFIN**" + `verification_passed llm_judge score=0.99` + `loop_end stop=end_turn turns=5` ✓ |
| Memory extraction tier | stays action | code-pinned only (handler tier-map comment + extraction.py untouched in the diff) — extraction emits no ledger row, so runtime tier is NOT observable; reported honestly as gate-level |

Screenshots: `artifacts/dt57109-compaction-run.png` + `dt57109-context-compacted-event.png` (9824→2679 frame in view) + `dt57109-final-turn-post-compaction.png`; full text evidence `artifacts/dt57109-run4-snapshot.yml` (never-commit).

### Gates (final, Day 3)

mypy 0/359 · flake8 0 · run_all 10/10 · full pytest **2477+4skip non-e2e + 8 e2e = 2485 ≡ baseline 2462 + 23 new, 0 del** (16 Day-1/2 + 7 keep-knob cases).

---
