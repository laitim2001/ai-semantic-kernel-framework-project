# Sprint 49.1 Execution Progress

**Sprint**: 49.1 — V1 封存 + V2 目錄骨架 + CI Pipeline
**Plan**: [`sprint-49-1-plan.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-1-plan.md)
**Checklist**: [`sprint-49-1-checklist.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-1-checklist.md)
**Branch**: `feature/phase-49-sprint-1-v2-foundation`

---

## Day 1 (2026-04-29) — V1 封存 + 根層配置

### Pre-sprint cleanup (on `main`)

Before launching Sprint 49.1, the working tree had several pending
items from the prior session (V2 rules rewrite + various Phase 48 dev
logs + worktree planning + V1 metrics tests + graphify gitignore
tightening). 5 commits landed on main to bring the tree to a clean
state:

| Commit | Summary |
|--------|---------|
| `8c676ee` | `chore(rules)`: V2 rewrite for Phase 49 foundation (16 files, +4175/-305) |
| `1066e76` | `docs(phase-48)`: dev logs + V1 chat orchestrator analysis (5 files, +4126) |
| `1fb89ff` | `docs(worktree)`: merge planning + KB sprint stubs + PoC03 (9 files, +1985) |
| `00ac849` | `test(v1)`: wiring tests for orchestration metrics layer (4 files, +403) |
| `1d9b05f` | `chore(gitignore)`: exclude entire graphify-out/ directory (1 file) |

After these landed, `git status` was fully clean — Sprint 49.1 Day 1.1
DoD satisfied.

### Day 1.1 — Branch creation + verification

- ✅ `main` synced with `origin/main` (no diverging commits)
- ✅ No open Phase 48 PRs (`gh pr list --state open --search "phase-48"` empty)
- ✅ Branch created: `feature/phase-49-sprint-1-v2-foundation`

### Day 1.2 — V1 final tag

- ✅ Annotated tag `v1-final-phase48` created at commit `1d9b05f`
  - Message includes Phase 48 status (Sprint 180 complete, Sprint 181
    DEFERRED) and reference to V2 plans
- ✅ Pushed to `origin/v1-final-phase48`
  - Verified via `git ls-remote --tags origin`: tag SHA
    `65ee5d5b8e9886d576401b5a326a0bb82320ae04` (annotated) → object
    `1d9b05ff195118b94ee632857e8eaa277d87b6e3`

### Day 1.3 — V1 archive (commit `6f15d14`)

- ✅ `mkdir -p archived/v1-phase1-48`
- ✅ `git mv backend → archived/v1-phase1-48/backend`
- ✅ `git mv frontend → archived/v1-phase1-48/frontend`
- ✅ `git mv infrastructure → archived/v1-phase1-48/infrastructure`
- ✅ Created `archived/v1-phase1-48/README.md`:
  - READ-ONLY warning
  - V1 alignment baseline (~27%, per-category scorecard)
  - **Sprint 181 DEFERRED note** (per option 丙 chosen):
    completeness folder + guided_dialog migration not executed; V2
    will not reuse this work; preservation is for historical reference
  - V2 launch references (agent-harness-planning/ 19 docs)
- ✅ Verified preserved at root: `docs/`, `claudedocs/`, `reference/`
- 1682 file renames staged + README added → single commit

### Day 1.4 — Root config (commit `cec8505`)

Moved V1 root configs (now broken since they referenced root paths):
- `git mv docker-compose.yml → archived/v1-phase1-48/`
- `git mv docker-compose.override.yml → archived/v1-phase1-48/`
- `git mv docker-compose.prod.yml → archived/v1-phase1-48/`
- `git mv .env.example → archived/v1-phase1-48/.env.example`

Added V2 root configs:
- `docker-compose.dev.yml`: postgres / redis / rabbitmq / qdrant
  with `_v2` volume names + healthchecks (acceptance gate for Day 5.1)
- `.env.example` (V2): Azure OpenAI primary, Anthropic / OpenAI
  commented as optional adapters per LLM-provider-neutrality rule.
  Added Qdrant + JWT + OTel placeholders.
- `README.md`: V2 banner inserted at top (V2 active 2026-04-29
  comparison table, dev environment quickstart, links to V2 plans).
  Original V1 content preserved under explicit "V1 Historical Content"
  divider per plan.

`.env` (gitignored, user-managed) left untouched.

### Day 1.5 — Day 1 closeout

- This `progress.md` (current commit)
- Checklist updated: Day 1 items `[ ]` → `[x]`

---

## Day 1 Estimates vs Actual

| Day 1 task group | Plan estimate | Actual | Notes |
|------------------|---------------|--------|-------|
| 1.1 Verification + branch | 30 min | ~5 min | main was already clean from prior session |
| 1.2 V1 tag | 15 min | ~5 min | batched in single bash call |
| 1.3 V1 archive + README | 90 min | ~25 min | `git mv` was fast (no large file rewrites) |
| 1.4 Root config | 45 min | ~20 min | parallel write + edit operations |
| 1.5 Closeout | 10 min | ~10 min | this section + checklist marking |
| **Total Day 1** | **3h 10min** | **~65 min** | well under estimate; plan padded for first-time uncertainty |

Buffer reclaimed → can absorb Day 2 (heaviest day, 7.5h estimate) any
overrun without slipping the 5-day Sprint timeline.

---

## Open items / Notes for next sessions

- ⚠️ `discussion-log-20260426.md` left in modified state by user
  (active IDE editing observed). Not part of Sprint 49.1 scope; user
  will commit separately when finished.
- 📝 graphify post-commit hook keeps rebuilding the knowledge graph
  after every commit and warning that the graph (73824 nodes) is too
  large for HTML viz. Non-blocking but slow (~30 sec per commit). Can
  be addressed later (e.g. `--no-viz` or `.graphifyignore` extension).

## Day 2 (2026-04-29) — V2 backend skeleton (commit `5d630f2`)

### Day 2.1 — Backend root (3 files)
- `backend/pyproject.toml` (Python 3.11+, mypy strict, 7 pytest markers)
- `backend/requirements.txt` (FastAPI / SQLAlchemy / OTel; LLM SDKs deliberately excluded — Sprint 49.3 onwards)
- `backend/README.md` (5-layer architecture overview + LLM-neutrality rule + Quickstart)
- Plus: `backend/tests/{unit,integration}/.gitkeep`

### Day 2.2 — agent_harness/ 13 ABCs (13 dirs × 3 files = 39 files)

| Cat | ABC class(es) | Phase impl |
|-----|----------------|------------|
| 1 orchestrator_loop | AgentLoop | 50.1 |
| 2 tools | ToolRegistry, ToolExecutor | 51.1 |
| 3 memory | MemoryLayer, MemoryScope (5-layer enum) | 51.2 |
| 4 context_mgmt | Compactor, TokenCounter, PromptCacheManager | 52.1 |
| 5 prompt_builder | PromptBuilder | 52.2 |
| 6 output_parser | OutputParser, ParsedOutput | 50.1 |
| 7 state_mgmt | Checkpointer, Reducer | 53.1 |
| 8 error_handling | ErrorPolicy, CircuitBreaker, ErrorTerminator + ErrorClass enum | 53.2 |
| 9 guardrails | Guardrail, Tripwire (per 17.md §6 — Tripwire is Cat 9 NOT Cat 8) | 53.3-53.4 |
| 10 verification | Verifier | 54.1 |
| 11 subagent | SubagentDispatcher (4 modes, no worktree) | 54.2 |
| 12 observability | Tracer (cross-cutting; impl in `platform/observability/`) | 49.4+ |
| HITL | HITLManager (5 methods; centralization per 17.md §5) | 53.3-53.4 |

Plus: `agent_harness/__init__.py` with LLM-neutrality reminder.

### Day 2.2.5 — _contracts/ single-source types (11 files)

Per 17.md §1 — every cross-category dataclass / enum has exactly ONE
home. Categories import from `agent_harness._contracts` only:

| File | Types |
|------|-------|
| chat.py | Message, ChatRequest, ChatResponse, ContentBlock, ToolCall, TokenUsage, StopReason, CacheBreakpoint |
| tools.py | ToolSpec, ToolAnnotations, ConcurrencyPolicy, ToolResult |
| state.py | LoopState, TransientState, DurableState, StateVersion |
| events.py | LoopEvent + 22 concrete subclasses (per 17.md §4.1) |
| memory.py | MemoryHint |
| prompt.py | PromptArtifact (re-exports CacheBreakpoint) |
| verification.py | VerificationResult |
| subagent.py | SubagentBudget, SubagentResult, SubagentMode (enum, 4 modes) |
| observability.py | TraceContext, MetricEvent, SpanCategory (13-value enum) |
| hitl.py | ApprovalRequest, ApprovalDecision, HITLPolicy, RiskLevel, DecisionType |
| __init__.py | Unified re-export of all 50+ symbols |

### Day 2.3 — adapters/ (7 files)

| File | Content |
|------|---------|
| `__init__.py` | provider-neutrality reminder |
| `_base/__init__.py` | re-export ChatClient + dataclasses |
| `_base/chat_client.py` | **ChatClient ABC** with 7 abstract methods (chat / stream / count_tokens / get_pricing / supports_feature / model_info) + ModelInfo + PricingInfo + StreamEvent |
| `_base/README.md` | Why this matters (LLM-neutrality), 7-method surface |
| `azure_openai/README.md` | V2 primary, Sprint 49.3 implementation deliverables |
| `anthropic/README.md` | Reserved placeholder for Phase 50+ |
| `maf/README.md` | Conditional placeholder, Sprint 54.2 if needed |

### Day 2.4 — Verification

- ✅ All 13 ABCs successfully importable
- ✅ Unified `_contracts` import returns all 50+ types
- ✅ ChatClient ABC importable
- ✅ `grep "import openai/anthropic/agent_framework"` returns empty in `agent_harness/`
- ✅ Single commit `5d630f2` (64 files, including 41 .py + 17 README)

### Estimates vs Actual (Day 2)

| Section | Plan estimate | Actual | Notes |
|---------|---------------|--------|-------|
| 2.1 backend root | 45 min | ~10 min | parallel writes |
| 2.2 13 ABCs | ~3h 40min | ~50 min | template-similar; followed 17.md §2.1 owner table exactly |
| 2.2.5 _contracts (11 files) | 60 min | ~20 min | most complex was events.py with 22 subclasses |
| 2.3 adapters/ | 45 min | ~10 min | ChatClient ABC was the bulk |
| 2.4 verify + commit | 30 min | ~5 min | imports succeeded first try |
| **Total Day 2** | **7h** | **~95 min** | 23% of estimate |

Buffer accumulated → Days 3-5 can absorb any complexity surprises.

## Day 3 (2026-04-29) — V2 backend platform / api / infra / core (commit pending)

### Day 3.1 — platform/ (12 files)
- governance/{risk,hitl,audit}/ — 3 subdirs each with __init__.py + README
- identity/, observability/, workers/ — each with __init__.py + README

### Day 3.2 — api/v1/ (5 files)
- chat/, governance/ — placeholders with detailed Phase planning READMEs
- **health.py — REAL impl**: GET /api/v1/health returns
  `HealthResponse(status="ok", version="2.0.0-alpha")` via APIRouter

### Day 3.3 — business_domain/ (7 files, INTENTIONALLY EMPTY for Sprint 49.x)
- README warns "Phase 55 才動工"; lists 5 domains × ~24 tools mapping
- 5 domain subdirs with __init__.py only (no impl)

### Day 3.4 — infrastructure/ (9 files)
- db/, cache/, messaging/, storage/ — each with __init__.py + README

### Day 3.5 — core/ + middleware/ (7 files)
- core/config — REAL pydantic Settings stub (env / log_level / DB / Redis
  / JWT) with @lru_cache get_settings()
- core/exceptions — IPABaseException
- core/logging — Phase 49.4 placeholder
- middleware/tenant.py — get_current_tenant FastAPI dep (raises 501; impl Sprint 49.2)
- middleware/auth.py — get_current_user FastAPI dep (raises 501; impl Sprint 49.3)

### Day 3.6 — main.py
- FastAPI app: title="IPA Platform V2", version from Settings
- Includes /api/v1/health router
- Root / endpoint returns app info

### Day 3.7 — Verification
- ✅ App imports successfully
- ✅ 6 routes registered (4 OpenAPI auto + / + /api/v1/health)
- ✅ All Day 3 imports succeed
- ⏳ Real uvicorn run + curl deferred to Day 5 integration acceptance

### Estimates vs Actual (Day 3)
| Section | Plan estimate | Actual |
|---------|---------------|--------|
| 3.1 platform/ | 80 min | ~15 min |
| 3.2 api/v1/ | 60 min | ~10 min |
| 3.3 business_domain/ | 30 min | ~5 min |
| 3.4 infrastructure/ | 30 min | ~10 min |
| 3.5 core/ + middleware/ | 45 min | ~10 min |
| 3.6 main.py | 30 min | ~5 min |
| 3.7 verify + commit | 30 min | ~5 min |
| **Total Day 3** | **5h** | **~60 min** | 20% of estimate

### Sprint 49.1 cumulative

| Day | Plan | Actual | Ratio |
|-----|------|--------|-------|
| Day 1 | 3h 10min | ~65 min | 35% |
| Day 2 | 7h | ~95 min | 23% |
| Day 3 | 5h | ~60 min | 20% |
| **Cumulative** | **15h 10min** | **~3h 40min** | **24%** |

## Day 4 (2026-04-29) — V2 frontend skeleton (commits `006321e` + `c798f95`)

### Day 4.1 — frontend root (6 files)
- package.json: React 18 + Vite 5 + Zustand 5 + RR 6 + ESLint 9 + TS 5.6 + @types/node 20
- tsconfig.json: strict + path alias `@/*` → `src/*`
- tsconfig.node.json: composite, types: ["node"] for vite.config.ts
- vite.config.ts: port 3007 (avoid V1 collision) + /api proxy → :8001
- index.html: lang=zh-Hant, module main.tsx
- README.md: architecture map + 5-phase roadmap + V2 vs V1

### Day 4.2 — src/ main files
- main.tsx: StrictMode + BrowserRouter + App
- App.tsx: 4 routes (/ Home + chat-v2 + governance + verification)
- 8 .gitkeep for components/{ui,layout,shared}, hooks/, api/, stores/, types/, utils/, public/

### Day 4.3 — Pages placeholders (6 files)
- pages/chat-v2/{index.tsx, README.md} — Phase 50.2
- pages/governance/{index.tsx, README.md} — Phase 53.3-53.4
- pages/verification/{index.tsx, README.md} — Phase 54.1

### Day 4.4 — Features placeholders (7 README only)
- orchestrator-loop / tools / memory / state-mgmt / guardrails /
  verification / subagent — each lists 3-4 planned components +
  backend pair + first implementation sprint

### Day 4.5 — Verification

- ✅ `npm install`: 43 packages, 0 errors (2 audit warnings non-blocking)
- ✅ `npm run build`: 36 modules → dist/index-*.js (165 KB / gzip 54 KB) in 519 ms
- ⏸️ `npm run dev`: skipped (CLAUDE.md "do not stop node.js processes" rule;
  defer real Vite dev server to Day 5.2 / user manual run)
- ⏸️ `npm run lint`: deferred (ESLint 9 flat config not yet built; build/typecheck
  is primary Day 4 gate; lint config will land in a later sprint when actual
  source code exists to lint)

### Two commits

| Commit | Notes |
|--------|-------|
| `006321e` | feat(frontend-shared): Day 4 frontend skeleton (35 files) |
| `c798f95` | chore(gitignore): exclude *.tsbuildinfo + vite.config.{d.ts,js} (cleanup of accidentally tracked TS build artifacts) |

### Estimates vs Actual (Day 4)
| Section | Plan estimate | Actual |
|---------|---------------|--------|
| 4.1 root config | 60 min | ~10 min |
| 4.2 src main | 60 min | ~5 min |
| 4.3 pages | 45 min | ~5 min |
| 4.4 features | 55 min | ~5 min |
| 4.5 verify (npm install + build) | 60 min | ~5 min |
| **Total Day 4** | **5h** | **~30 min** | 10% of estimate

### Sprint 49.1 cumulative

| Day | Plan | Actual | Ratio |
|-----|------|--------|-------|
| Day 1 | 3h 10min | ~65 min | 35% |
| Day 2 | 7h | ~95 min | 23% |
| Day 3 | 5h | ~60 min | 20% |
| Day 4 | 5h | ~30 min | 10% |
| **Cumulative** | **20h 10min** | **~4h 10min** | **21%** |

### Open items
- ⏸️ ESLint 9 flat config not yet created (no production code exists to lint yet)
- ⏸️ Vite dev server not manually validated (defer to Day 5 or user-driven)
- ⏸️ npm audit reports 2 moderate severity vulnerabilities (transitive deps); fix in later sprint

## Day 5 (2026-04-29) — CI Pipeline + Docker + integration + closeout

### Day 5.0 — CI Pipeline (commit `d535235`)

- `.github/workflows/backend-ci.yml`: setup-python 3.11 → black → isort → flake8 → mypy strict → pytest → **LLM SDK leak check** (grep agent_harness/ for openai/anthropic/agent_framework — fails CI on hit)
- `.github/workflows/frontend-ci.yml`: setup-node 20 → npm ci → lint → build → dist verification
- `.github/PULL_REQUEST_TEMPLATE.md`: 3 principles + 17.md interface check + 11-point anti-patterns + multi-tenant + CI gates
- `frontend/eslint.config.js` (built Day 5, deferred from Day 4): ESLint 9 flat config — `npm run lint` 0 warnings

### Day 5.1 — Docker compose

`docker compose -f docker-compose.dev.yml up -d` → 4 services up:

| Service | Status |
|---------|--------|
| postgres | Up 16s, healthy |
| redis | Up 16s, healthy |
| rabbitmq | Up 16s, healthy |
| qdrant | Up 16s, health: starting (warming, normal) |

### Day 5.2 — End-to-end startup

- ✅ FastAPI app loads via `from main import app` (6 routes: `/`, `/api/v1/health`, `/docs`, `/docs/oauth2-redirect`, `/openapi.json`, `/redoc`)
- ✅ `health()` coroutine returns `HealthResponse(status='ok', version='2.0.0-alpha')` (validated via direct call; uvicorn subprocess hit by hook restrictions; TestClient hit by platform shadow before fix)
- ⏸ `npm run dev` deferred (CLAUDE.md "no node.js process" rule); `npm run build` validated as proxy

### Day 5.3 — Code quality (commit `6ee07dc`)

Fixed 4 issues found:
- Shorten chat.py:3 line >100 chars (flake8 E501)
- Black-format 2 files (chat_client.py, subagent.py)
- Remove 3 unused `# type: ignore[unreachable]` comments (mypy)
- Update backend/README.md + platform_layer/__init__.py docstring

| Check | Result |
|-------|--------|
| black --check src/ | All 73 files clean ✅ |
| isort --check src/ | Clean ✅ |
| flake8 src/ | Clean ✅ |
| mypy --strict src/ | "Success: no issues found in 73 source files" ✅ |
| npm run lint | 0 warnings ✅ |
| npm run build | 36 modules / 165 KB / 519 ms ✅ |

### Day 5.4 — Import acceptance (commit `6ee07dc`)

`backend/tests/unit/test_imports.py` — 4 tests, all PASSED:

| Test | Verifies |
|------|----------|
| test_eleven_plus_one_categories_importable | 13 ABCs (11 + Cat 12 + HITL) all importable + abstract |
| test_contracts_unified_export | 50+ types from `_contracts/` (incl. 22 LoopEvent subclasses) + StopReason 6 values + SubagentMode 4 modes (NO worktree) + SpanCategory 13 values + RiskLevel + DecisionType |
| test_chat_client_abc_importable | ChatClient + ModelInfo + PricingInfo + StreamEvent |
| test_no_llm_sdk_imports_in_agent_harness | Regex grep agent_harness/ for `import openai/anthropic/agent_framework` returns empty |

`pytest tests/unit/test_imports.py -v` → **4 passed in 0.11s**

### ⚠️ Mid-Sprint blocker: `platform/` shadow Python stdlib

**Discovered Day 5.4** when first pytest run failed with cryptic
`AttributeError: module 'platform' has no attribute 'system'`.

**Root cause**: `backend/src/platform/` shadows Python stdlib `platform`
when on sys.path via `PYTHONPATH=src`. Transitive deps using
`platform.python_implementation()` (rich/attr/faker) break.

**Resolution**: Renamed `platform/` → `platform_layer/`, bundled into
commit `d535235`. All tests pass after rename.

**Follow-up captured in retrospective.md**:
- Update agent-harness-planning/02-architecture-design.md + 06-phase-roadmap.md to use `platform_layer/`
- Add CI lint to block reintroduction of bare `platform/`
- Sprint 49.2+ planning uses new name

### Day 5.5 — Documentation

- ✅ `retrospective.md` complete (outcome + estimates + went-well + surprises + Sprint 49.2 prerequisites + sign-off)
- ✅ `progress.md` (this file) Day 1-5 complete
- ⏸ `agent-harness-planning/README.md` Sprint 49.2 link — deferred until 49.2 plan exists (rolling planning)
- ⏸ `artifacts/` 5 evidence files — deferred (CI auto-produces from Sprint 49.2; Day 5 evidence embedded in retrospective text)

### Day 5 commits

| Commit | Summary |
|--------|---------|
| `d535235` | chore(ci): CI workflows + PR template + ESLint flat config (also platform→platform_layer rename) |
| `6ee07dc` | fix(core): code quality fixes + test_imports.py |
| (this closeout commit) | docs(sprint-49-1): Day 5 closeout — retrospective + checklist + progress |

PR creation skipped per user direction; commits pushed to origin
directly.

### Estimates vs Actual (Day 5)

| Section | Plan | Actual |
|---------|------|--------|
| 5.0 CI + ESLint | 60 min | ~25 min |
| 5.1 Docker | 45 min | ~5 min |
| 5.2 E2E startup | 30 min | ~15 min |
| 5.3 Code quality | 45 min | ~15 min |
| 5.4 Imports + test | 45 min | ~15 min |
| 5.5 Documentation | 45 min | ~25 min |
| 5.6 Closeout | 45 min | ~10 min |
| **Total Day 5** | **5h** | **~110 min** | 37% of estimate

### Sprint 49.1 Final Cumulative

| Day | Plan | Actual | Ratio |
|-----|------|--------|-------|
| Day 1 | 3h 10min | ~65 min | 35% |
| Day 2 | 7h | ~95 min | 23% |
| Day 3 | 5h | ~60 min | 20% |
| Day 4 | 5h | ~30 min | 10% |
| Day 5 | 5h | ~110 min | 37% |
| **Total** | **25h 10min** | **~6h 0min** | **24%** |

## Sprint 49.1 ✅ DONE (pending push to origin)

See `retrospective.md` for full sign-off. Next: **Sprint 49.2 — DB
Schema + Async ORM** (rolling planning; plan + checklist to be created
at start of next session).
