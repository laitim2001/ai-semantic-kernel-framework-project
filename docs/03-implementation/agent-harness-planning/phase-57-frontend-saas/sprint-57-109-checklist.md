# Sprint 57.109 — Checklist (C2: compaction cheap tier — `make_chat_compactor(profile.cheap)` retier + `_compaction` cost-ledger attribution (57.82 mirror) + `CHAT_COMPACTION_TOKEN_BUDGET` knob → lowered-budget drive-through)

[Plan](./sprint-57-109-plan.md)

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `f4089fd9`) — DONE, catalogued in progress.md D1-D12
- [x] **Prong 1 — path verify**: EDIT files Glob-1 (`handler.py` / `_category_factories.py` / `_contracts/compaction.py` / `compactor/semantic.py` / `compactor/hybrid.py` / `compactor/structural.py` / `orchestrator_loop/loop.py` / `_contracts/events.py` / `api/v1/chat/router.py` / `.env.example`); test suites pinned (5 compaction suites + handler/profile tier tests + router observer tests + billing_outbox tests); design note 24 file path Glob'd (`24-multi-model-profile-design.md`); NO new src files expected
- [x] **Prong 2 — content verify** (D1 verification mirror fully pinned incl. `verification_model`; D3 `_summarise` returns str → return-shape change; D4 hybrid one-site forward; D5 LoopCompleted ×3 ctor sites; D9 TokenUsage = prompt/completion_tokens; D12 quota reconcile mirror fold-in): `ChatResponse` usage/model field names at the compactor seam · `_verification` enqueue payload shape incl. WHAT MODEL it attributes (router.py:683-709 + `LoopCompleted` verification fields — load-bearing for the mirror) · grep ALL `CompactionResult(` constructors (9 src + 2 test, keyword-style) · hybrid construct-vs-forward (hybrid.py:79-174) · verif accumulation idiom (loop.py:2003-2005/:2538-2541/:2607+:2631+:2656) · billing_outbox idempotency key shape (:75-77 — suffix participates) · `_CHAT_TOKEN_BUDGET` consumer sites · `.env` cheap config (commented template only — D11 dt lever) · structural-only compaction enqueues NOTHING (zero-usage guard mirror) · semantic retry path single-count seam (failed attempts raise — no usage to count)
- [x] **Prong 3 — schema verify**: N/A (no DB / no migration — cost_ledger sub_type + billing_outbox suffix are 57.82 infrastructure) — recorded explicitly
- [x] **Catalog drift** findings in progress.md Day 0 (D1-D12 + implications; plan §8 cross-ref)
- [x] **Go/no-go**: GO — D3 (private-method signature) + D12 (one-expression addition) shift scope < 10%

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-109-compaction-cheap-tier` (from `main` `f4089fd9`)

---

## Day 1 — Backend: retier + usage capture (US-1 + US-2 first half)

### 1.1 Compactor cheap retier (US-1)
- [ ] **`handler.py:460`**: `make_chat_compactor(profile.cheap)`; §321-327 comment block → three-tier consumer map (loop/prompt=action · verification=cheap 57.97 · compaction=cheap 57.109); MHist 1-line
- [ ] **Handler tier-pin test**: the built compactor's semantic client IS the profile's cheap client (mirror the 57.97 verifier-tier test shape); cheap-unset `cheap is action` covered by the existing profile test (cite, don't duplicate)
  - DoD: grep `make_chat_compactor(` → sole call site carries `profile.cheap` ✓

### 1.2 `CompactionResult` usage fields + semantic capture (US-2 backend half 1)
- [ ] **`_contracts/compaction.py`**: `CompactionResult` += `input_tokens: int = 0` + `output_tokens: int = 0` + `model: str = ""` (frozen, defaulted; MHist 1-line)
- [ ] **`semantic.py`**: `_summarise` (or its caller) reads the successful summarize `ChatResponse` usage + model into the result (retry = successful attempt only; failed-attempt blind spot documented)
- [ ] **`hybrid.py`**: forward (or copy) semantic's usage fields per Day-0 construct-vs-forward finding; structural results keep zeros
- [ ] **Unit tests CONVERT/ADD**: semantic mock returns usage → result carries it · structural result zeros · hybrid pass-through — 0 deletions across the 3 compactor suites
  - DoD: 5 compaction suites green unchanged counts +new cases ✓; mypy strict 0 ✓

---

## Day 2 — Backend: accumulator + LoopCompleted + observer + knob (US-2 second half + US-3)

### 2.1 Accumulator → `LoopCompleted` → observer `_compaction` (US-2 backend half 2)
- [ ] **`loop.py`** compaction site: fold triggered-result usage/model into the metrics accumulator (diff limited to the compaction site + accumulator class)
- [ ] **`_contracts/events.py`**: `LoopCompleted` += `compaction_input_tokens: int = 0` / `compaction_output_tokens: int = 0` / `compaction_model: str = ""` (defaulted; `loop_end` WIRE untouched — count 24, no codegen diff)
- [ ] **`router.py`** observer: `compaction_*_tokens > 0` → `billing_outbox.enqueue(sub_type_suffix="_compaction", model=<compaction model — truthful cheap>)`; zero-usage → NO enqueue (mirror :702-705)
- [ ] **Unit tests ADD**: accumulator fold · observer enqueue shape (`_compaction` suffix + cheap model + token counts) · zero-usage no-enqueue · idempotency key distinct from loop/`_verification`
  - DoD: grep `sub_type_suffix` → loop ""/`_verification`/`_compaction` three-way ✓; run_all 10/10 (count 24) ✓

### 2.2 Budget env knob (US-3)
- [ ] **`_category_factories.py`**: `_CHAT_TOKEN_BUDGET` env-read (`CHAT_COMPACTION_TOKEN_BUDGET`; default 100_000; non-int → default no-crash); `.env.example` documents it
- [ ] **Unit test ADD**: monkeypatched env honored + invalid-fallback
  - DoD: default path byte-identical (no env set → 100_000) ✓

---

## Day 3 — Full gates + drive-through (US-4) + CHANGE-076

### 3.1 Full gate sweep
- [ ] mypy strict 0 · black/isort/flake8 0 (all four, 57.107 lesson) · run_all 10/10 from repo root (count 24; no codegen diff) · full pytest 0 del vs 2462+4skip baseline · FE untouched holds (Vitest 836 / mockup-fidelity 51) · `loop.py` diff = compaction site + accumulator only · wire schema diff = empty

### 3.2 Drive-through (US-4 — real UI :3007 + fresh no-reload backend + real Azure; zero dev-login; Risk Class E clean restart with `CHAT_COMPACTION_TOKEN_BUDGET` set BEFORE start + orphan spawn-worker sweep)
- [ ] **Tier delta lever confirmed**: `.env` cheap deployment distinct from action (or set the dt tenant's cheap via the C1 model-policy tab — 57.104 proven)
- [ ] **Compaction triggers live**: lowered budget → multi-turn real conversation → `ContextCompacted` observed (raw events / SSE) with strategy + tokens_before/after real
- [ ] **Ledger reality**: cost ledger shows `{provider}_{cheap_model}_compaction_input/_output` rows with real token counts (cost dashboard or DB read) — model = the CHEAP deployment, NOT action
- [ ] **Quality + non-regression**: post-compaction answer still references an early-conversation fact (AP-7 in-the-flesh); memory extraction row still attributes the ACTION tier; normal default-budget session compacts nothing + enqueues nothing
- [ ] Screenshots + observed-vs-intended table in progress.md
  - DoD: ALL legs PASS; no tenant policy left modified (restore defaults after dt)

### 3.3 CHANGE-076
- [ ] `claudedocs/4-changes/feature-changes/CHANGE-076-compaction-cheap-tier-ledger-attribution.md` (1-page; spike design note NOT required — design-note-24 continuation, §5.5 NOT-apply)

---

## Day 4 — Closeout

### 4.1 Closeout
- [ ] retrospective.md Q1-Q7 + calibration (`multi-model-profile-spike` 0.55 2nd data point; agent-delegated: no) + progress.md final
- [ ] Design note 24 edit: "compaction cheap tier" invariant → resolved (extraction half stays open); MHist 1-line
- [ ] Navigators: CLAUDE.md Current-Sprint row + Last-Updated; MEMORY.md quality pointer + memory subfile; next-phase-candidates (closes proposal §3.4 C2; C-family 3/3 done; next slice B4 per interleave); sprint-workflow matrix row (2nd data point)
- [ ] PR (push + open on user authorization)
