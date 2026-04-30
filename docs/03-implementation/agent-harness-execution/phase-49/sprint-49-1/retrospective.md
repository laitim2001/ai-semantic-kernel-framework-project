# Sprint 49.1 Retrospective

**Sprint**: 49.1 — V1 封存 + V2 目錄骨架 + CI Pipeline
**Branch**: `feature/phase-49-sprint-1-v2-foundation`
**Started**: 2026-04-29 (after pre-sprint cleanup of 5 commits on main)
**Closed**: 2026-04-29
**Plan**: [`sprint-49-1-plan.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-1-plan.md)
**Story Points**: 26 (planned) → all completed

---

## Outcome summary

Sprint 49.1 delivered the **complete V2 foundation skeleton** that
all 21 subsequent sprints depend on:

| Deliverable | Status |
|-------------|--------|
| V1 (Phase 1-48) archived to `archived/v1-phase1-48/` | ✅ |
| Tag `v1-final-phase48` pushed to origin | ✅ |
| V2 `backend/` with 5-layer architecture skeleton | ✅ |
| 11+1 categories (`agent_harness/`) ABCs all importable | ✅ |
| Cross-category single-source `_contracts/` package (10 files + unified `__init__.py`) | ✅ |
| `ChatClient` ABC at `adapters/_base/` (LLM-provider-neutrality) | ✅ |
| `HITLManager` ABC centralizing HITL (per 17.md §5) | ✅ |
| V2 `frontend/` skeleton with placeholder pages + features | ✅ |
| Docker compose dev infra (postgres / redis / rabbitmq / qdrant) | ✅ |
| GitHub Actions CI (backend + frontend workflows + PR template) | ✅ |
| All linters pass (black / isort / flake8 / mypy strict) | ✅ |
| `test_imports.py` covers Sprint 49.1 acceptance | ✅ |

---

## Estimates vs Actual

| Day | Plan | Actual | Ratio |
|-----|------|--------|-------|
| Day 1 — V1 archive + root config | 3h 10min | ~65 min | 35% |
| Day 2 — agent_harness 13 ABCs + _contracts + adapters | 7h | ~95 min | 23% |
| Day 3 — platform / api / infra / core | 5h | ~60 min | 20% |
| Day 4 — frontend skeleton | 5h | ~30 min | 10% |
| Day 5 — CI + Docker + verification + closeout | 5h | ~110 min | 37% |
| **Total Sprint** | **25 h** | **~6 h** | **24%** |

Plan estimates carried generous buffer (first-time uncertainty, CRLF
issues, integration validation). Actual execution was much faster
because:
1. AI tooling parallelizes file generation
2. ABC stubs follow consistent template once first one is settled
3. Most categories had no novel decisions — just translate 17.md owner
   table into Python ABC classes

Day 5 was the longest day (relative to estimate buffer) due to the
discovered `platform/` shadow blocker requiring rename + linter
fixes + writing test_imports.py.

---

## What went well

### 1. Pre-sprint cleanup discipline

Before the sprint launched, the working tree had several pending
items from the prior session (V2 rules rewrite + various Phase 48 dev
logs + worktree planning + V1 metrics tests). 5 commits cleared these
to main, putting `git status` in a fully clean state — satisfying
Day 1.1 first DoD.

### 2. 17.md as authoritative ABC reference

`17-cross-category-interfaces.md` made Day 2 (the heaviest day, 13
ABCs + 10 contract files) trivial. Each ABC's surface, owner, and
rationale was already documented; my job was just translation.

### 3. `_contracts/` single-source pattern enforced from Day 1

Every category's `_abc.py` imports types from
`agent_harness._contracts` only. No type duplication. Lint check (CI
backend job) future-proofs this against drift.

### 4. LLM-provider-neutrality verified end-to-end

- No `import openai` / `import anthropic` / `import agent_framework`
  in `agent_harness/`
- Test `test_no_llm_sdk_imports_in_agent_harness` codifies this for CI
- CI workflow grep blocks any future PR that violates

### 5. Sprint workflow discipline followed

Per `.claude/rules/sprint-workflow.md`:
- Plan → Checklist created BEFORE coding ✅
- Checklist updated incrementally ([ ] → [x]) ✅
- Never deleted unchecked items (Phase 42 violation NOT repeated) ✅
- Daily progress entries before commits ✅
- File-by-file commit attribution preserved ✅

---

## What surprised us / what to improve

### 1. ⚠️ `platform/` package name shadows Python stdlib `platform`

**Severity**: Blocker for testing (would block all Sprint 49.2+ tests).

The V2 architecture plan called the platform layer simply `platform/`.
But this name shadows Python's stdlib `platform` module when added to
`sys.path`. Any third-party library using `platform.python_implementation()`
or `platform.system()` (which is most of them via httpx → rich → attr,
or pytest+faker) breaks immediately.

**Discovered during Day 5.4** when running pytest for the first time.

**Fix**: Renamed `backend/src/platform/` → `backend/src/platform_layer/`.

**Action items**:
- [ ] Update `agent-harness-planning/02-architecture-design.md` 5-layer
      architecture diagram to use `platform_layer/`
- [ ] Update `agent-harness-planning/06-phase-roadmap.md` references
- [ ] Update any other plan docs that reference `platform/` (Sprint
      49.2+ planning will catch these incrementally)
- [ ] Add a CI lint that blocks future re-introduction of bare
      `platform/` package

### 2. ⏸ ESLint config deferred from Day 4 → built in Day 5

ESLint 9 uses flat config (`eslint.config.js`) which differs from older
`.eslintrc.*` patterns. Day 4 deferred building it; Day 5 added a
minimal flat config that works with the existing deps in
`frontend/package.json`. Now `npm run lint` passes with zero warnings.

### 3. ⏸ Real `npm run dev` / `uvicorn` validation deferred

Per `CLAUDE.md` rule "do not stop any node.js process", AI cannot
freely start long-running dev servers. We validated:
- `npm run build` passed ✅ (one-shot, doesn't keep server running)
- FastAPI app + `/api/v1/health` validated via direct call (avoiding
  `TestClient` due to platform shadow before fix; now works) ✅
- Docker compose up brought 4 services healthy ✅

User should manually run `uvicorn src.main:app --port 8001` and
`npm run dev` to confirm interactive validation, but acceptance gates
are satisfied.

### 4. Build artifacts accidentally tracked then forward-fixed

Day 4 commit `006321e` accidentally tracked TS/Vite build artifacts:
- `*.tsbuildinfo` (TS incremental cache)
- `vite.config.{d.ts,js}` (composite emit side effects)

Forward-fix commit `c798f95` added gitignore patterns + `git rm
--cached`. Files remain in 006321e history (preserved per checklist
sacred rule about audit trail).

**Action item**: Build artifact patterns should be added to `.gitignore`
template at sprint kickoff for any new language/tooling, not after the
fact.

---

## Cumulative branch state

```
feature/phase-49-sprint-1-v2-foundation
├─ 6f15d14 Day 1.3: archive V1 to archived/v1-phase1-48/
├─ cec8505 Day 1.4: V2 root config (docker-compose.dev.yml + .env.example + README V2 banner)
├─ bfc8f64 Day 1.5: closeout (progress.md + checklist Day 1 marked)
├─ 5d630f2 Day 2: V2 backend skeleton (11+1 ABCs + _contracts + adapters base)
├─ c6f2c34 Day 2 closeout
├─ f4bde09 Day 3: V2 platform / api / infra / core / middleware
├─ dfd972c Day 3 closeout
├─ 006321e Day 4: V2 frontend skeleton
├─ c798f95 Day 4 cleanup: gitignore TS/Vite build artifacts
├─ 50a70db Day 4 closeout
├─ d535235 Day 5.0: CI workflows + PR template + ESLint flat config + (platform→platform_layer rename swept in)
├─ 6ee07dc Day 5.3-5.4: code quality fixes + test_imports.py
└─ (closeout commit, this) Day 5 closeout
```

13 commits total on the branch (including this closeout).

---

## Sprint 49.2 prerequisites unblocked

This sprint completes prerequisites for Sprint 49.2 (DB Schema +
Async ORM):

- ✅ `backend/src/infrastructure/db/` directory exists with README
- ✅ Pydantic Settings (`core.config.Settings`) has `database_url` field
- ✅ Multi-tenant rule (`.claude/rules/multi-tenant-data.md`) authoritative
- ✅ `_contracts/state.py` has `LoopState` / `TransientState` / `DurableState`
      ready to map to ORM models
- ✅ Test framework (pytest + asyncio mode) configured + 4 tests passing
- ✅ CI gate enforces all linters before merge
- ✅ Branch + workflow conventions established

Sprint 49.2 plan + checklist creation: **NEXT** (rolling planning per
`.claude/rules/sprint-workflow.md`).

---

## Approvals & sign-off

- [x] All checklist items closed (or explicitly deferred with `🚧` annotation)
- [x] All linters pass
- [x] `test_imports.py` 4/4 tests pass
- [x] Docker compose: 4 services healthy
- [x] Working tree clean (except user's IDE-edited discussion-log, unrelated)
- [x] Branch ready to push to `origin`
- [x] No PR creation required (per user direction); merge handled
      directly by user.

**Sprint 49.1 status**: ✅ DONE (pending push)
