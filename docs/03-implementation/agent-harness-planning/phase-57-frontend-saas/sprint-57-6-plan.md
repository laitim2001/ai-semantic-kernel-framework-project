# Sprint 57.6 — Reality Gap Fix Sprint (close R1+R2+R3+R4-partial+R5 + merged Phase 57.7 doc updates)

> **Sprint Type**: Phase 57+ fifth sprint — **Reality Gap Fix Sprint** closing top 5 RED findings from Sprint 57.5 V2 Reality Check + merged Phase 57.7 doc updates per Decision 4 (b);primary deliverable = real boot + DB persist + lint + doc alignment;NO new feature pages (5 frontend pages will ship Phase 57.x per Decision 3 (a) but NOT in this sprint)
> **Owner Categories**: §All (cross-cutting reality fix) — `scripts/dev.py` + `vite.config.ts` + `backend/src/api/main.py` (R1 entry-point/port drift) + uvicorn lifespan (R2 dotenv autoload) + chat router observers (R3 sessions/audit_log/cost_ledger/tool_calls DB persist) + 16.md ship timeline (R4-partial) + V2 lint scripts + new E2E real-LLM CI gate (R5) + Day 4 closeout doc updates (02.md / 16.md / SITUATION-V2 dual scoring / CLAUDE.md / sprint-workflow.md calibration matrix)
> **Phase**: 57 (Frontend SaaS — 5/N sprint;但 5/N 不開新 frontend page;先 close reality gap + doc updates;rolling planning per .claude/rules/sprint-workflow.md)
> **Workload**: 5 days (Day 0-4); bottom-up est ~22-26 hr (5 USs reality fix) + ~3 hr (5 doc updates merged closeout) = ~25-29 hr → calibrated commit **~13-15 hr** (multiplier **0.50** — `reality-gap-fix` NEW class 1st application;類比 audit cycle 0.55-0.60 加 small overhead for real fix code execution;若 ratio < 0.85 → reality gap fix 比預期更直接(因為 Sprint 57.5 已 surface fix path)→ adjust upward;若 ratio > 1.20 → fix path 比預期複雜 → catalog AD-Sprint-Plan-8;Phase 57.7 USs merged into Day 4 closeout per Decision 4 (b))
> **Branch**: `feature/sprint-57-6-reality-gap-fix`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: Sprint 57.5 V2 Reality Check & Smoke Test Sprint Day 4.5 user-confirmed Option D direction 2026-05-08 — 5 decisions locked: D1 Option (a) 全 5 USs / D2 Option (a) Phase 57.6 partial doc-only for R4 / D3 Option (a) Phase 57.x 逐個 ship 真實 page (16.md ship timeline NOT V3 defer) / D4 Option (b) merge Phase 57.7 USs into Phase 57.6 closeout / D5 Option (a) accept calibration baselines `reality-gap-fix` 0.50 + `reality-check` 0.85
> **AD logging (sub-scope)**: Closes 10 NEW AD-Reality-N (5 Phase 57.6 + 5 Phase 57.7 merged here) + AD-Sprint-Plan-7 calibration class proposal (`reality-check` 0.85 1-data-point baseline pending 2-3 sprint window evidence)

---

## Sprint Goal

Provide the **first reality gap closure sprint** following Sprint 57.5 V2 Reality Check by:

- **US-1** (AD-Reality-1 — R1 entry-point + port config drift unification): `scripts/dev.py` references real `backend/src/api/main.py` (NOT stub `backend/src/main.py`) + `vite.config.ts` proxy target points to backend port 8000 (NOT stub 8001) + remove stale stub `src/main.py` if exists OR add deprecation comment
- **US-2** (AD-Reality-2 — R2 .env autoload): uvicorn FastAPI lifespan startup hook adds `python-dotenv.load_dotenv()` call so `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_DEPLOYMENT_NAME` + `DB_*` + `REDIS_HOST` env vars auto-load on backend start; real_llm mode 不再 503
- **US-3** (AD-Reality-3 — R3 chat router observer wiring): `api/v1/chat.py` chat router LoopCompleted + ToolCallExecuted + GuardrailTriggered observers fire DB persist:
  - `sessions` table INSERT on conversation start
  - `audit_log` table INSERT chained entries on conversation events (operation = "conversation_started" / "tool_executed" / "verification_completed" / "guardrail_triggered")
  - `cost_ledger` table INSERT 2-entry split per LLMResponded (input/output) + per ToolCallExecuted (per-call entry)
  - `tool_calls` table INSERT per ToolCallExecuted with execution status + duration + result preview
- **US-4** (AD-Reality-4-partial — R4 5-page scope decision documentation): `16-frontend-design.md` adds explicit "V2 ship timeline" section listing:
  - 4 已 ship pages: cost-dashboard / sla-dashboard / tenant-settings / admin-tenants (Phase 57.1+57.3+57.4)
  - 8 待 ship Phase 57.x pages with priority hierarchy (critical 3 = chat-v2/governance/verification 因 backend 已 ship 優先 ~3 sprints × ~8-12 hr/page;其他 5 admin-side power user pages = agents/workflows/incidents/memory/audit/tools/admin/dashboard/devui ~5-7 sprints × ~8-12 hr/page = ~5-7 sprints frontend排程 stretching Phase 57.x to ~57.13+;NO V3 defer per Decision 3 (a))
- **US-5** (AD-Reality-5 — R5 AP-4 Potemkin lint extension + E2E real-LLM smoke gate):
  - NEW V2 lint script `scripts/lint/check_ap4_frontend_placeholder.py` scans `frontend/src/pages/*/index.tsx` for placeholder marker text ("Coming in Phase X" / "skeleton" / "TODO" / "land in subsequent sprints" / "placeholder")
  - Add 9th V2 lint to `run_all.py` orchestrator
  - NEW GitHub Actions workflow `.github/workflows/e2e-real-llm-smoke.yml` nightly schedule runs cost-bounded real Azure OpenAI smoke test (1 chat session + verifies SSE 8 events + DB delta verification)
- **Day 4 closeout add-on (Phase 57.7 USs merged per Decision 4 (b))**:
  - AD-Reality-6: `02-architecture-design.md` flat-layer drift fold-in (`platform_layer/governance` reality vs paper `governance/` flat-layer claim) — update 02.md to document nested-layer reality
  - AD-Reality-7: `16-frontend-design.md` ship timeline statement (already in US-4)
  - AD-Reality-8: SITUATION-V2 §9 dual scoring format adoption (every future sprint entry adds code-level + runtime-level dual scoring header)
  - AD-Reality-9: CLAUDE.md project status reflect Phase 57.6 reality closure
  - AD-Reality-10: `sprint-workflow.md` §Workload Calibration matrix add `reality-gap-fix` 0.50 + `reality-check` 0.85 entries (promote AD-Sprint-Plan-7 with Sprint 57.6 + 57.5 evidence)

Sprint 結束後:
- (a) **Default boot path works end-to-end** — `python scripts/dev.py start` boots all services + frontend↔backend integration unbroken (NO vite proxy port drift)
- (b) **Real LLM mode works on default boot** — `.env` autoloaded; chat with real Azure OpenAI verifies SSE 8 events stream
- (c) **DB persistence verified** — chat session 結束後 `sessions` + `audit_log` + `cost_ledger` + `tool_calls` 表全有 row delta
- (d) **AP-4 Potemkin防再生機制 in CI** — frontend placeholder text 由 lint 阻擋;E2E real-LLM smoke gate 阻擋未來 sprint regress real-LLM mode
- (e) **Documentation alignment** — 02.md flat-layer drift folded;16.md ship timeline explicit;SITUATION-V2 dual scoring adoption;CLAUDE.md aligned;sprint-workflow.md calibration matrix updated

**主流量驗收標準**:
- ✅ `python scripts/dev.py start` succeeds + all 5 services healthy + frontend (3005) ↔ backend (8000) talk
- ✅ `curl POST /api/v1/chat` with real Azure OpenAI key set in `.env` → SSE 8 events captured + LoopCompleted with provider=azure_openai + tokens > 0
- ✅ `psql -c "SELECT count(*) FROM {sessions,audit_log,cost_ledger,tool_calls}"` → all 4 tables ≥ 1 row delta after 1 chat session
- ✅ `python scripts/lint/run_all.py` → 9/9 V2 lints green (含 NEW check_ap4_frontend_placeholder)
- ✅ E2E real-LLM smoke workflow runs nightly + green
- ✅ 02.md + 16.md + SITUATION-V2 + CLAUDE.md + sprint-workflow.md doc updates committed
- ✅ AD-Reality-1 to AD-Reality-10 all closed (10 ADs;5 reality fix + 5 doc updates)
- ✅ AD-Sprint-Plan-7 promoted via 2-data-point evidence (Sprint 57.5 ratio 1.04 + Sprint 57.6 ratio TBD)

---

## Background

### V2 進度 (2026-05-08 reality gap fix 起點)

- **22/22 sprints (100%) main progress completed** + **Phase 56-58 SaaS Stage 1 3/3 ✅ CLOSED** + **Phase 57+ Frontend SaaS 3/N completed** (57.1 v2 + 57.3 + 57.4) + **Sprint 57.5 V2 Reality Check ✅ COMPLETE** (PR #112 + #113)
- main HEAD: `426fce7b` (Sprint 57.5 closeout PR #113) — Day 0 will verify
- pytest baseline 1598 / mypy --strict 0/295 source files / 8 V2 lints 8/8 green / LLM SDK leak 0
- Vitest baseline 35 / Playwright e2e baseline 23
- Vite build 75 modules / 209.11 kB
- **28 runtime D-findings catalogued** (Sprint 57.5: 7 RED + 13 YELLOW + 8 GREEN)
- **21-doc paper audit complete** (Sprint 57.5: 9 strongly aligned + 8 mostly w/ drift + 4 significant gap)
- **Dual scoring framework**: code-level ★★★★ ~85% / runtime-level ★★ ~40%
- **Default boot smoke test count: 0 successful end-to-end** — Sprint 57.5 surfaced D-12 + D-21 + D-27 entry-point/port drift + D-20 .env autoload missing + D-16/17/18 chat DB persist not firing

### 為什麼 Phase 57.6 是 Reality Gap Fix 而非 feature work

Per Sprint 57.5 retrospective Q5 + Day 4.5 user decisions:

1. **Code-level ~85% + runtime-level ~40% gap is closeable** with focused 1-2 sprint Phase 57.6 + 57.7 effort (per gap report §3.1 Candidate A)
2. **Option D (A+C 組合) user preference** — fix Reality Gap THEN re-baseline THEN feature work
3. **5 user decisions locked** at Sprint 57.5 Day 4.5: 全 5 USs (D1) / Phase 57.6 partial doc-only (D2) / 16.md ship timeline NOT V3 defer (D3) / merge Phase 57.7 into 57.6 closeout (D4) / accept baselines (D5)
4. **AP-4 防再生機制 critical** — without lint extension, future sprints will continue producing placeholder pages bypassing CI gates

**Reality Gap Fix Sprint 性質區分**:
- 不是 feature sprint (NO new pages / NO new endpoints / NO new tables)
- 不是 audit cycle bundle (audit cycle 通常 fold-in process AD;此 sprint 是 reality fix + doc alignment)
- 不是 reality check sprint (Sprint 57.5 已做;此 sprint 是 act on findings)
- **是 reality fix sprint** — 主要 deliverable 是 closing R1+R2+R3+R4-partial+R5 + 5 doc updates closing AD-Reality-1 to AD-Reality-10

### 既有結構 (Day 0 plan-time 探勘 grep 將驗證 Sprint 57.5 D-findings)

✅ **以下 Sprint 57.5 surfaced runtime drifts pending Day 0 verify**:

```
backend/src/
├── api/main.py                 # ✅ Real entry (Sprint 49.4+)
├── main.py?                    # ⚠️ D-12 stub from Sprint 49.1 may still exist;Day 0 grep verify
├── api/v1/chat.py              # ✅ chat router with observer hooks (Sprint 53.5/56.3) — D-16/17/18 DB persist not firing
└── ...

scripts/dev.py                  # ⚠️ D-12 references stub `src/main.py` instead of `src/api/main.py`;Day 0 grep verify

frontend/
├── vite.config.ts              # ⚠️ D-27 proxy target hardcoded 8001 vs backend default 8000;Day 0 grep verify
└── ...

.env / .env.example             # ⚠️ D-20 uvicorn doesn't autoload .env via lifespan;Day 0 grep verify
```

✅ **以下 16.md current state pending US-4 update**:

```
16-frontend-design.md
├── 12-page list (paper claim)
├── per-Sprint接手時序 table (chat 50.2 / governance 53.4 / 3 業務頁 55.2 / 6 缺漏頁 55.3 / auth 49.4)
└── ⚠️ NO explicit "V2 ship timeline" section listing 4 ship + 8 待 ship Phase 57.x;US-4 will add
```

✅ **以下 8 V2 lints baseline pending US-5 NEW 9th lint**:

```
scripts/lint/run_all.py
├── check_ap1.py (no Pipeline-disguised-as-Loop)
├── check_promptbuilder.py (single-source)
├── check_sole_mutator.py (state mgmt)
├── check_neutrality.py (LLM SDK leak)
├── check_rls_policies.py (multi-tenant RLS gaps)
├── check_cross_category.py (range boundaries)
├── check_no_orphan_code.py (AP-2)
├── check_observability_spans.py (Cat 12)
└── ⚠️ NO check_ap4_frontend_placeholder.py;US-5 will add as 9th
```

### V2 紀律 9 項對齊確認

1. **Server-Side First** ✅ Reality fix 對齊 — 試圖 fix server-side 真實能 serve
2. **LLM Provider Neutrality** ✅ 此 sprint 不動 LLM 鏈路;但會 verify 主流量真的能切到 Azure OpenAI live (US-2 lifespan dotenv)
3. **CC Reference 不照搬** ✅ Reality fix 為 V2-specific
4. **17.md Single-source** ✅ Reality fix 不新增任何 cross-category interface;chat router observer 用既有 ObservabilityHook + AuditAppendOnlyService + CostLedgerService + ToolCallRepository
5. **11+1 範疇歸屬** ✅ US-1~US-3 歸屬 platform layer (entry-point + middleware + observers);US-4~US-5 為 documentation + lint cross-cutting (Cat 12 觀測性 + AP-4 防護)
6. **04 anti-patterns** ✅✅✅ **此 sprint 主要對齊 AP-4 (Potemkin) 防再生 + AP-7 (Context rot) lint enforcement** + AP-9 (Verification) E2E real-LLM gate
7. **Sprint workflow** ✅ plan → checklist → Day 0 三-prong → Day 1-4 → progress + retro;本文件鏡射 57.5 plan 結構 (9 sections + metadata block;5 USs;Day 0-4 structure)
8. **File header convention** ✅ 此 sprint 寫 source code (US-1 / US-2 / US-3 / US-5 modify Python + TypeScript files;US-4 modify Markdown);全加 file header per convention
9. **Multi-tenant rule** ✅ Reality fix 不違反;chat router observer DB persist 用 tenant_id (Multi-tenant 鐵律 #1+#2+#3 都 honor)

---

## User Stories

### US-1: AD-Reality-1 — Entry-Point + Port Config Drift Unification

**As** the V2 platform engineer
**I want** `scripts/dev.py` to reference real `backend/src/api/main.py` AND `vite.config.ts` proxy target backend port 8000 (NOT stub 8001) AND remove or deprecate stale `backend/src/main.py` stub if exists
**So that** default boot path `python scripts/dev.py start` works end-to-end + frontend↔backend integration unbroken

**Acceptance**:
- `scripts/dev.py` updated:`uvicorn main:app` → `uvicorn api.main:app` (or equivalent path resolution; verify exact import path of real entry)
- `frontend/vite.config.ts` updated:`server.proxy['/api'].target = 'http://localhost:8000'` (NOT 8001;若 8001 是 historical valid → keep both as alternative)
- Investigate `backend/src/main.py` stub:
  - 若 exists + dead → remove with deprecation commit message
  - 若 exists + still used somewhere → grep usage + refactor / add deprecation comment
- Manual verify post-fix:`python scripts/dev.py start` boots backend on 8000 + frontend on 3005 + frontend can curl backend /health via proxy
- Day 1 fixed evidence:capture `python scripts/dev.py status` output showing all services healthy
- Closes AD-Reality-1 + Sprint 57.5 D-12 + D-21 + D-27

### US-2: AD-Reality-2 — uvicorn Lifespan dotenv Autoload

**As** the V2 platform engineer
**I want** uvicorn FastAPI lifespan startup hook to call `python-dotenv.load_dotenv()` so that `.env` file values auto-load on backend start
**So that** `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_DEPLOYMENT_NAME` + `DB_*` + `REDIS_HOST` are available without manual `set -a; source .env` shell prep + real_llm mode 不再 503

**Acceptance**:
- `backend/src/api/main.py` (or appropriate lifespan module) adds:
  ```python
  from contextlib import asynccontextmanager
  from dotenv import load_dotenv

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      load_dotenv()  # AD-Reality-2: autoload .env on startup
      yield
  ```
- `app = FastAPI(lifespan=lifespan)` parameter wired
- `python-dotenv` confirmed in `backend/requirements.txt` (likely already there for testing; if not → add)
- Day 1 fixed evidence:`python scripts/dev.py start` followed by `curl POST /api/v1/chat` real_llm mode → SSE LLMResponded with provider=azure_openai (NOT 503)
- Sprint 57.5 D-20 closed
- Closes AD-Reality-2

### US-3: AD-Reality-3 — Chat Router Observer Wiring (4-stream DB Persist)

**As** the V2 platform engineer
**I want** `api/v1/chat.py` chat router observer hooks to fire DB persist for sessions / audit_log / cost_ledger / tool_calls tables on relevant LoopEvents
**So that** chat session 結束後 DB has 5+ row delta verified end-to-end (NOT in-memory-only)

**Acceptance**:
- `api/v1/chat.py` chat router:
  - On conversation start (LoopStarted event): `INSERT INTO sessions (id, tenant_id, user_id, started_at, ...) VALUES (...)` via SessionRepository (or equivalent ORM call)
  - On LoopCompleted: `INSERT INTO audit_log (operation='conversation_started', ...)` chain entry via AuditAppendOnlyService.append()
  - On LLMResponded: `INSERT INTO cost_ledger (cost_type='llm_call', sub_type='{provider}_{model}_input', input_tokens=...) + (sub_type='{provider}_{model}_output', output_tokens=...)` via CostLedgerService.record_llm_call() (per Sprint 57.2 AD-Cost-Ledger-Token-Split 2-entry split)
  - On ToolCallExecuted: `INSERT INTO tool_calls (id, session_id, tool_name, status, duration_ms, result_preview)` via ToolCallRepository + `INSERT INTO cost_ledger (cost_type='tool_call', sub_type='{tool_name}')` via CostLedgerService.record_tool_call()
  - On GuardrailTriggered: `INSERT INTO audit_log (operation='guardrail_triggered', ...)` chain entry
  - On VerificationPassed/Failed: `INSERT INTO audit_log (operation='verification_completed', ...)` chain entry
- 18+ unit tests added for observer wiring (mock repositories + assert call counts)
- 1 integration test added: full chat e2e w/ real Azure OpenAI + verifies all 4 tables get expected row counts
- Day 1 fixed evidence:`psql -c "SELECT count(*) FROM {sessions,audit_log,cost_ledger,tool_calls}"` → all 4 tables ≥ 1 row delta
- Sprint 57.5 D-16 + D-17 + D-18 closed
- Closes AD-Reality-3

### US-4: AD-Reality-4-partial — 16.md V2 Ship Timeline Statement

**As** the V2 documentation maintainer
**I want** `16-frontend-design.md` to add explicit "V2 Ship Timeline" section listing 4 已 ship pages + 8 待 ship Phase 57.x pages with priority hierarchy
**So that** stakeholders + future AI sessions have ground-truth on V2 frontend scope (NOT V3 defer per Decision 3 (a))

**Acceptance**:
- `16-frontend-design.md` adds NEW section "## V2 Ship Timeline (Phase 57.6+ — per Sprint 57.5 reality audit + Day 4.5 Decision 3)" containing:
  - **Already shipped (Phase 57.1+57.3+57.4)**:
    - cost-dashboard (Sprint 57.1 v2)
    - sla-dashboard (Sprint 57.1 v2)
    - tenant-settings (Sprint 57.3)
    - admin-tenants (Sprint 57.4)
  - **Sprint 57.7-57.9 priority (critical 3 pages — backend ship complete, frontend wiring needed)**:
    - chat-v2 (replace 50.2 skeleton with real chat UX wired to chat router; ~10-12 hr)
    - governance (replace 53.5 placeholder with real approvals UX wired to GovernanceService; ~10-12 hr)
    - verification (replace 54.1 placeholder with real verification panel wired to VerificationService; ~10-12 hr)
  - **Sprint 57.10-57.13+ deferred (5 admin-side power user pages)**:
    - agents / workflows / incidents / memory / audit / tools / admin / dashboard / devui (per 16.md original 12-page list; ~5-7 sprints × ~8-12 hr/page; NO V3 defer)
  - **NOT V3 defer** (Decision 3 (a)): all 8 待 ship pages will be developed in Phase 57.x stretching Phase 57.x timeline accordingly
- Optional `16-frontend-design.md` Section "Per-Sprint接手時序" table updated with Phase 57.x sprint allocations for the 8 待 ship pages
- File header MHist updated with `2026-05-09: Sprint 57.6 — add V2 Ship Timeline section per Decision 3 (a) (closes AD-Reality-4-partial + AD-Reality-7)`
- Closes AD-Reality-4-partial + AD-Reality-7 (merged Phase 57.7 US)

### US-5: AD-Reality-5 — AP-4 Potemkin Lint Extension + E2E Real-LLM Smoke Gate

**As** the V2 platform engineer
**I want** NEW V2 lint script `scripts/lint/check_ap4_frontend_placeholder.py` + NEW GitHub Actions workflow `.github/workflows/e2e-real-llm-smoke.yml`
**So that** future sprints can't introduce frontend placeholder text + can't regress real-LLM mode without CI catching it

**Acceptance**:
- NEW `scripts/lint/check_ap4_frontend_placeholder.py`:
  - Scan `frontend/src/pages/*/index.tsx` (NOT just App.tsx — every page)
  - Forbidden text patterns:
    - "Coming in Phase X" / "Coming soon" (literal regex)
    - "skeleton" / "placeholder" (case-insensitive substring in JSX text content)
    - "TODO" / "FIXME" (in JSX text content; NOT in `// comments`)
    - "land in subsequent sprints" / "will be added later" (literal)
    - "Not implemented" / "WIP" (case-insensitive)
  - Scope: text content inside JSX tags `<p>`, `<span>`, `<div>`, `<h1-6>`, `<a>`
  - Exit 0 = clean / non-zero = N placeholder findings with line numbers
  - Exempt: comments inside `{/* ... */}` JSX block (these are dev notes not user-visible)
- `scripts/lint/run_all.py` orchestrator adds 9th V2 lint
- NEW `.github/workflows/e2e-real-llm-smoke.yml`:
  - Trigger: `schedule: cron '0 4 * * *'` (nightly 4AM UTC) + `workflow_dispatch` (manual trigger)
  - Runs:
    - Spin up PG + Redis services
    - `alembic upgrade head` apply migrations
    - Seed default tenant
    - `curl POST /api/v1/chat` with real Azure OpenAI key (from GitHub Secrets `AZURE_OPENAI_API_KEY` etc.)
    - Verify SSE 8 events captured + LLMResponded + LoopCompleted with tokens > 0
    - `psql` verify sessions / audit_log / cost_ledger / tool_calls all ≥ 1 row delta
  - Cost guard: `max_tokens: 100` to bound cost; 1 chat session per nightly run = ~$0.01-0.05 USD/run
  - Required-check status: NOT add to branch protection 5 active checks (這是 nightly, not per-PR; 添加會 break PR merging when nightly fail) — runs as informational status
- 8 V2 lints → 9 V2 lints; 1 NEW E2E real-LLM workflow
- Sprint 57.5 R5 closed
- Closes AD-Reality-5

### Day 4 Closeout Add-On (Phase 57.7 USs Merged per Decision 4 (b))

**Day 4.6** (closeout) writes:
- AD-Reality-6: `02-architecture-design.md` flat-layer drift fold-in — update §Architecture Diagram to show `platform_layer/{governance,identity,observability}/` nested-layer reality (NOT paper `governance/` flat-layer); add §Naming Drift Note 2026-05-09 explaining nested-layer rationale
- AD-Reality-8: SITUATION-V2 §9 milestones row format adoption — add header rule "every future sprint entry MUST include code-level + runtime-level dual scoring at end of entry summary"
- AD-Reality-9: CLAUDE.md project status reflect Phase 57.6 reality closure — Latest Sprint + main HEAD + Last Updated + Current Phase + main HEAD bottom field
- AD-Reality-10: `sprint-workflow.md` §Workload Calibration matrix table add 2 new rows:
  - `reality-gap-fix` 0.50 multiplier (1-data-point baseline; this Sprint 57.6)
  - `reality-check` 0.85 multiplier (2-data-point baseline; Sprint 57.5 + 57.6 evidence — promote AD-Sprint-Plan-7 to validated rule if 2-3 sprint window evidence sufficient)

---

## Technical Specifications

### US-1: Entry-Point + Port Config Drift Unification

```python
# scripts/dev.py — Day 1 reference change
- subprocess.run(["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"], ...)
+ subprocess.run(["uvicorn", "api.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"], cwd="backend/src", ...)
```

```typescript
// frontend/vite.config.ts — Day 1 reference change
server: {
  proxy: {
    '/api': {
-     target: 'http://localhost:8001',
+     target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

### US-2: uvicorn Lifespan dotenv Autoload

```python
# backend/src/api/main.py — Day 1 reference change
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """AD-Reality-2 (Sprint 57.6): autoload .env on backend start."""
    load_dotenv()
    yield
    # Cleanup (none currently)

app = FastAPI(lifespan=lifespan)
# ... rest of app config
```

### US-3: Chat Router Observer Wiring

```python
# backend/src/api/v1/chat.py — Day 1-2 reference change
async def _stream_loop_events(loop: AgentLoop, session_id: UUID, tenant_id: UUID, ...):
    # Persist session row at start
    await session_repo.create_session(session_id=session_id, tenant_id=tenant_id, ...)

    async for event in loop.run(...):
        # Emit SSE
        yield format_sse(event)

        # NEW AD-Reality-3 observers:
        if isinstance(event, LoopStarted):
            await audit_service.append(operation="conversation_started", session_id=session_id, ...)
        elif isinstance(event, LLMResponded):
            await cost_ledger.record_llm_call(
                tenant_id=tenant_id,
                provider=event.provider,
                model=event.model,
                input_tokens=event.usage.input_tokens,
                output_tokens=event.usage.output_tokens,
                cached_tokens=event.usage.cached_tokens,
            )
        elif isinstance(event, ToolCallExecuted):
            await tool_call_repo.create(...)
            await cost_ledger.record_tool_call(tenant_id=tenant_id, tool_name=event.tool_name, ...)
        elif isinstance(event, GuardrailTriggered):
            await audit_service.append(operation="guardrail_triggered", ...)
        elif isinstance(event, (VerificationPassed, VerificationFailed)):
            await audit_service.append(operation="verification_completed", ...)
        elif isinstance(event, LoopCompleted):
            await audit_service.append(operation="conversation_completed", ...)
```

### US-5: AP-4 Frontend Placeholder Lint

```python
# scripts/lint/check_ap4_frontend_placeholder.py — Day 3 NEW script
import re
import sys
from pathlib import Path

FORBIDDEN_PATTERNS = [
    r"\bComing\s+(?:in\s+Phase\s+\w+|soon)\b",
    r"\b(?:skeleton|placeholder)\b",
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bland\s+in\s+subsequent\s+sprints\b",
    r"\b(?:will\s+be\s+added\s+later|Not\s+implemented|WIP)\b",
]

def check_file(path: Path) -> list[tuple[int, str]]:
    """Return list of (line_no, matched_text) for forbidden patterns in JSX text content."""
    findings = []
    text = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), 1):
        # Skip comments {/* ... */} (dev notes)
        if "{/*" in line and "*/}" in line:
            continue
        for pattern in FORBIDDEN_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                findings.append((line_no, match.group(0)))
    return findings

def main():
    pages_dir = Path("frontend/src/pages")
    if not pages_dir.exists():
        print(f"❌ {pages_dir} not found", file=sys.stderr)
        sys.exit(2)

    total_findings = 0
    for page_file in pages_dir.glob("*/index.tsx"):
        findings = check_file(page_file)
        if findings:
            print(f"❌ {page_file}:")
            for line_no, matched in findings:
                print(f"  L{line_no}: {matched}")
            total_findings += len(findings)

    if total_findings:
        print(f"\n❌ {total_findings} AP-4 Potemkin placeholder findings (frontend)")
        sys.exit(1)
    print("✅ No AP-4 Potemkin frontend placeholder text")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### US-5: E2E Real-LLM Smoke Workflow

```yaml
# .github/workflows/e2e-real-llm-smoke.yml — Day 3 NEW workflow
name: E2E Real-LLM Smoke (Nightly)

on:
  schedule:
    - cron: '0 4 * * *'  # 04:00 UTC daily
  workflow_dispatch: {}

jobs:
  e2e-real-llm-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: ipa_platform
          POSTGRES_USER: ipa_user
          POSTGRES_PASSWORD: ipa_password
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports: ['6379:6379']

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Apply Alembic migrations
        run: |
          cd backend
          alembic upgrade head

      - name: Seed default tenant
        env:
          DB_NAME: ipa_platform
          DB_USER: ipa_user
          DB_PASSWORD: ipa_password
        run: |
          cd backend
          python scripts/seed_default_tenant.py

      - name: Start backend
        env:
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
          AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          AZURE_OPENAI_DEPLOYMENT_NAME: ${{ secrets.AZURE_OPENAI_DEPLOYMENT_NAME }}
        run: |
          cd backend/src
          python -m uvicorn api.main:app --port 8000 &
          sleep 5
          curl -f http://localhost:8000/health || exit 1

      - name: Real-LLM smoke chat
        env:
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
        run: |
          # Single chat session with cost guard
          python tests/e2e/real_llm_smoke.py --max-tokens 100 --tenant-id ${{ env.TENANT_ID }}

      - name: Verify DB row delta
        run: |
          psql -h localhost -U ipa_user -d ipa_platform <<EOF
          SELECT count(*) FROM sessions;
          SELECT count(*) FROM audit_log;
          SELECT count(*) FROM cost_ledger;
          SELECT count(*) FROM tool_calls;
          EOF
          # Verify all ≥ 1
```

### Risk Class A/B/C/D — Reality Gap Fix 特殊 risks

- **Risk Class A (paths-filter)**: 已 closed by 55.6 Option Z;不適用
- **Risk Class B (mypy unused-ignore)**: 此 sprint 寫 source code → applicable;若 NEW lint script + test files 觸發 Linux/Windows mypy drift → use `# type: ignore[..., unused-ignore]` pattern per `.claude/rules/code-quality.md`
- **Risk Class C (module-level singleton)**: US-3 chat router observer + US-2 dotenv lifespan 可能 surface singleton lifecycle issue (e.g. cost_ledger / audit_service singletons across event loops);若 boot crashes → catalogue + fix per `.claude/rules/testing.md` §Module-level Singleton Reset Pattern
- **Risk Class D (Reality Check carryover)**: Sprint 57.5 D-findings 有些可能 fix path 比預期複雜 (e.g. `backend/src/main.py` stub history may have unexpected dependencies); Day 0 三-prong + Day 1 mid-day decision gates required
- **Risk Class E (NEW for Reality Fix)**: GitHub Secrets for E2E real-LLM workflow may not be configured at this Sprint;**Mitigation**:Day 3 US-5 workflow file 寫好 + commit + 但 nightly schedule disabled (commented out) until secrets provisioned in next sprint or Phase 58 production launch (per AD-CI-6); workflow_dispatch manual trigger preserved
- **Risk Class F (NEW for Reality Fix)**: AD-Reality-3 chat router observer wiring may surface 17.md cross-category interface drift (e.g. ToolCallRepository ABC may need expansion if existing methods不夠);**Mitigation**:Day 0 Prong 2 content verify confirms existing ABCs + repositories support all needed methods;若 needed → log AD + revise plan §Risks (do NOT silently expand 17.md per AD-Plan-1 audit-trail discipline)

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 主進度 22/22 (100%) 不變;Phase 56-58 SaaS Stage 1 backend 3/3 不變;Phase 57+ Frontend SaaS 3/N 不變(此 sprint 不算 4/N — 是 reality gap fix 性質)
- [ ] All 8 V2 lints 不變 + NEW 9th lint check_ap4_frontend_placeholder added (US-5)
- [ ] Backend pytest baseline 1598 → 1616+ (+18 minimum from US-3 18+ unit + 1 integration + US-2 1 unit + US-5 lint test 0)
- [ ] Backend mypy --strict 0 errors 不變(NEW source code 全 typed)
- [ ] Backend LLM SDK leak: 0 不變
- [ ] Anti-pattern checklist:此 sprint 主要 close AP-4 (US-5 lint extension) + AP-7 防護 (E2E real-LLM nightly catches context rot regression)
- [ ] 5 active CI checks green
- [ ] Frontend `npm run lint && npm run build` clean(0 frontend source code change;US-5 lint scans既有 frontend code)
- [ ] Frontend Vitest 35 不變(0 frontend test change)
- [ ] Playwright e2e 23 不變(此 sprint 不開新 Playwright)
- [ ] All 5 services boot up 成功 via `python scripts/dev.py start`(US-1 + US-2)
- [ ] POST /api/v1/chat real_llm mode SSE 8 events stream 完整(US-2)
- [ ] DB persist verified all 4 tables ≥ 1 row delta after 1 chat session(US-3)
- [ ] 16.md V2 Ship Timeline section added(US-4)
- [ ] check_ap4_frontend_placeholder.py exists + run_all.py 9 lints orchestrated(US-5)
- [ ] e2e-real-llm-smoke.yml workflow file committed(US-5)
- [ ] Day 4 closeout 5 doc updates committed (02.md / SITUATION-V2 / CLAUDE.md / sprint-workflow.md / + 16.md from US-4)
- [ ] 10 NEW AD-Reality-N + AD-Sprint-Plan-7 全 closed
- [ ] retrospective.md ≥ 250 lines per file-header-convention.md
- [ ] memory snapshot project_phase57_6_reality_gap_fix.md ≤ 80 lines per V2 紀律
- [ ] MEMORY.md index +1 entry

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Branch + Pre-flight + 三-prong + Calibration

- 0.1 Branch from main `426fce7b` + commit plan + checklist
- 0.2 Day-0 三-prong 探勘(per AD-Plan-3 + AD-Plan-4 promoted rules):
  - **Prong 1 Path Verify**:`scripts/dev.py` exists / `backend/src/api/main.py` exists / `backend/src/main.py` (stub D-12) status / `frontend/vite.config.ts` exists / `backend/requirements.txt` 含 python-dotenv? / `backend/src/api/v1/chat.py` exists with observer hook structure / `scripts/lint/run_all.py` orchestrator + 8 existing lint scripts / `.github/workflows/` directory
  - **Prong 2 Content Verify**:`scripts/dev.py` 真實 references which entry path (grep `uvicorn.*main:app`) / `vite.config.ts` 真實 proxy target (grep `target.*http`) / `backend/src/api/main.py` 已有 lifespan hook 嗎 (grep `@asynccontextmanager` + `lifespan`) / `chat.py` 既有 observer hooks structure (grep `record_llm_call|append|create_session|tool_call_repo`) / 17.md ABCs status (ToolCallRepository / AuditAppendOnlyService / CostLedgerService / SessionRepository) — confirm all exist + signature matches plan assumptions
  - **Prong 3 Schema Verify**:`sessions` + `audit_log` + `cost_ledger` + `tool_calls` 表 schema 確認 (grep ORM in `backend/src/infrastructure/db/models/`) — confirm columns match observer wiring needs (e.g. `tool_calls.tool_name VARCHAR` exists; `cost_ledger.input_tokens INT` exists per 56.3 schema)
- 0.3 Calibration multiplier pre-read(`reality-gap-fix` 0.50 NEW class 1st application;若 ratio in band [0.85, 1.20] → 0.50 baseline validated;若 < 0.85 → fix path 比預期更直接 → adjust upward toward 0.65;若 > 1.20 → fix path 比預期複雜 → AD-Sprint-Plan-8 catalogue)
- 0.4 Pre-flight verify(backend pytest baseline 1598 / 8 V2 lints baseline 8/8 / mypy baseline 0/295 / frontend Vitest 35 + Playwright 23 + Vite build 75 modules / 209.11 kB)
- 0.5 Day 0 progress.md commit + push;catalogue D-findings (predicted 0-5 D-findings since Sprint 57.5 已 surface most)

### Day 1 — US-1 Entry-Point Drift + US-2 dotenv Lifespan

- 1.1 US-1 implement:`scripts/dev.py` import path fix + `vite.config.ts` proxy port fix + `backend/src/main.py` stub status (remove or deprecate per Day 0 探勘 finding)
- 1.2 US-1 manual verify:`python scripts/dev.py start` boots backend on 8000 + frontend on 3005 + capture log
- 1.3 US-2 implement:`backend/src/api/main.py` lifespan hook + `python-dotenv` in requirements.txt (verify or add)
- 1.4 US-2 manual verify:after fix, `curl POST /api/v1/chat` real_llm mode (real Azure OpenAI key in `.env`) → SSE LLMResponded with provider=azure_openai (NOT 503)
- 1.5 1 unit test added for lifespan dotenv autoload (assert `os.environ["AZURE_OPENAI_API_KEY"]` available after lifespan startup)
- 1.6 Day 1 commit + push + progress.md(catalog any mid-day D-findings)

### Day 2 — US-3 Chat Router Observer Wiring (4-stream DB Persist)

- 2.1 US-3 implement:`api/v1/chat.py` chat router observer hooks for 4-stream DB persist (sessions / audit_log / cost_ledger / tool_calls)
- 2.2 US-3 unit tests:18+ unit tests added for each observer hook (mock repositories + assert call counts per event type)
- 2.3 US-3 integration test:1 full chat e2e with real Azure OpenAI + verify all 4 tables get expected row counts
- 2.4 US-3 manual verify:`python scripts/dev.py start` followed by `curl POST /api/v1/chat` then `psql -c "SELECT count(*) FROM {sessions,audit_log,cost_ledger,tool_calls}"` → all 4 tables ≥ 1 row delta
- 2.5 Day 2 commit + push + progress.md

### Day 3 — US-4 16.md Ship Timeline + US-5 AP-4 Lint + E2E Real-LLM Workflow

- 3.1 US-4 implement:`16-frontend-design.md` add NEW "V2 Ship Timeline" section listing 4 ship + 8 待 ship Phase 57.x with priority hierarchy
- 3.2 US-4 file header MHist update
- 3.3 US-5 implement:NEW `scripts/lint/check_ap4_frontend_placeholder.py` lint script
- 3.4 US-5 wire:`scripts/lint/run_all.py` orchestrator add 9th V2 lint
- 3.5 US-5 manual verify:`python scripts/lint/run_all.py` → 9/9 V2 lints green;若 既有 chat-v2 / governance / verification placeholder text → lint会先報 N findings → log Day 3 finding (lint catches existing AP-4 instances; not a regression but confirmation of Sprint 57.5 D-23+24+25)
- 3.6 US-5 E2E workflow:NEW `.github/workflows/e2e-real-llm-smoke.yml` schedule (cron disabled until Phase 58 secrets provisioning per AD-CI-6) + workflow_dispatch trigger preserved
- 3.7 Day 3 commit + push + progress.md

### Day 4 — US-5 close + Closeout (Phase 57.7 USs Merged) + Retro + PR

- 4.1 US-5 close:final verify check_ap4_frontend_placeholder lint orchestrated + e2e-real-llm-smoke.yml committed
- 4.2 retrospective.md(6 必答 + 5 USs reality fix Q3 generalizable lessons + Q4 audit debt deferred + Q5 next steps)
- 4.3 Memory snapshot `memory/project_phase57_6_reality_gap_fix.md`
- 4.4 MEMORY.md index update
- 4.5 Open PR + CI green + solo-dev merge to main
- 4.6 Closeout PR (Phase 57.7 USs merged per Decision 4 (b)):
  - AD-Reality-6: 02.md flat-layer drift fold-in
  - AD-Reality-8: SITUATION-V2 §9 dual scoring format adoption
  - AD-Reality-9: CLAUDE.md sync to **Phase 57+ SaaS Frontend 4/N (Sprint 57.6 Reality Gap Fix Sprint closed) + dual scoring header**
  - AD-Reality-10: sprint-workflow.md §Workload Calibration matrix add `reality-gap-fix` 0.50 + `reality-check` 0.85 entries (promote AD-Sprint-Plan-7)
- 4.7 User decision interaction (Phase 57.7+ direction):
  - Phase 57.7 candidate: chat-v2 real ship (~10-12 hr) per Decision 3 (a) priority hierarchy
  - OR pivot to other Phase 57.x feature work
  - Per rolling planning 紀律:不預寫 Phase 57.7 plan;等 user 明確選定 scope 才起草

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `scripts/dev.py` | MODIFIED | ~10 (entry path fix) |
| `frontend/vite.config.ts` | MODIFIED | ~3 (proxy port fix) |
| `backend/src/main.py` (stub) | DELETED or DEPRECATED | -10 to 0 (per Day 0 探勘 decision) |
| `backend/src/api/main.py` | MODIFIED | +20 (lifespan + dotenv) |
| `backend/requirements.txt` | MODIFIED (if needed) | +1 (python-dotenv if missing) |
| `backend/src/api/v1/chat.py` | MODIFIED | +40 (4-stream observer hooks) |
| `backend/tests/unit/api/v1/test_chat_observer_hooks.py` | NEW | ~250 (18+ unit tests) |
| `backend/tests/unit/api/test_main_lifespan.py` | NEW | ~30 (1 unit test) |
| `backend/tests/integration/test_chat_db_persist_e2e.py` | NEW | ~80 (1 integration test) |
| `docs/03-implementation/agent-harness-planning/16-frontend-design.md` | MODIFIED | +50 (V2 Ship Timeline section) |
| `scripts/lint/check_ap4_frontend_placeholder.py` | NEW | ~80 |
| `scripts/lint/run_all.py` | MODIFIED | +5 (9th lint orchestrator entry) |
| `.github/workflows/e2e-real-llm-smoke.yml` | NEW | ~80 |
| `docs/03-implementation/agent-harness-planning/02-architecture-design.md` | MODIFIED | +20 (Day 4 closeout: flat-layer drift fold-in) |
| `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` | MODIFIED | +30 (Day 4 closeout: §9 dual scoring header rule + §11 Last Updated + new 57.6 milestone row) |
| `CLAUDE.md` | MODIFIED | +20 (Day 4 closeout: Latest Sprint + main HEAD + Last Updated + Current Phase + main HEAD bottom) |
| `.claude/rules/sprint-workflow.md` | MODIFIED | +15 (Day 4 closeout: Calibration matrix add reality-gap-fix 0.50 + reality-check 0.85) |
| `docs/.../sprint-57-6/{progress,retrospective}.md` | NEW | ~600 |
| `memory/project_phase57_6_reality_gap_fix.md` | NEW | ~80 |
| `MEMORY.md` | MODIFIED | +1 line index entry |
| `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-6-{plan,checklist}.md` | NEW (this commit) | ~700 plan + ~330 checklist |

**Total**: ~80 source LOC + ~360 test LOC + ~165 lint+CI LOC + ~1200 docs LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ✅ Sprint 57.5 main + closeout PR merged → main HEAD `426fce7b` (Day 0 verify)
- ✅ `scripts/dev.py` exists per CLAUDE.md
- ✅ `backend/src/api/main.py` real entry exists (Sprint 49.4+;Day 0 Prong 1 verify)
- ✅ `backend/src/api/v1/chat.py` exists with observer hook structure (Sprint 53.5+56.3;Day 0 Prong 2 verify既有 hooks 與 plan 假設一致)
- ✅ All required ABCs + Repositories exist per 17.md (ToolCallRepository / AuditAppendOnlyService / CostLedgerService / SessionRepository — Day 0 Prong 2 verify signature)
- ✅ `python-dotenv` in requirements.txt (Day 0 Prong 2 verify;若缺 → US-2 add)
- ⚠️ User has Azure OpenAI live endpoint + API key + deployment configured in `.env` (Day 1 US-2 manual verify needs real LLM call; if not → US-2 unit test 仍能寫 + manual verify defer to Sprint 57.7+)
- ⚠️ User has PostgreSQL 16 + Redis 7 running locally OR Docker Compose stack ready (Day 0 verify;若缺 → spin up first)
- ⚠️ GitHub Secrets `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_DEPLOYMENT_NAME` for E2E real-LLM workflow:NOT required this sprint (workflow file 寫好 + cron disabled until Phase 58 production launch per AD-CI-6;workflow_dispatch manual trigger preserved for testing)

### Risk Classes (per sprint-workflow.md §Common Risk Classes + Reality Fix NEW)

**Risk Class A (paths-filter)**: 已 closed by 55.6 Option Z;不適用

**Risk Class B (mypy unused-ignore)**: applicable;US-3 + US-5 寫 NEW source code → use `# type: ignore[..., unused-ignore]` pattern when Linux/Windows mypy 行為 different

**Risk Class C (module-level singleton)**: US-3 chat router observer + US-2 dotenv lifespan 可能 surface singleton lifecycle issue;若 boot crashes → catalog + fix per `.claude/rules/testing.md` §Module-level Singleton Reset Pattern

**Risk Class D (Reality Check carryover)**: Sprint 57.5 D-findings 有些 fix path 比預期複雜;Day 0 三-prong + Day 1 mid-day decision gates required

**Risk Class E (NEW for Reality Fix)**: GitHub Secrets for E2E workflow may not be configured;**Mitigation**:cron disabled commit + workflow_dispatch preserved + AD-CI-6 promotion path

**Risk Class F (NEW for Reality Fix)**: 17.md cross-category interface drift if existing ABCs不足;**Mitigation**:Day 0 Prong 2 verify;NO silent expansion per AD-Plan-1 audit-trail

### Day 0 三-prong 探勘 D-findings v3 (catalogued during Day 0)

**D1** TBD — pending Day 0 path verify (`scripts/dev.py` entry path)
**D2** TBD — pending Day 0 content verify (`vite.config.ts` proxy target)
**D3** TBD — pending Day 0 schema verify (sessions/audit_log/cost_ledger/tool_calls schema vs observer needs)

(Day 0 完成後 fill in;若 0 critical D-findings → continue Day 1 normal;若 ≥ 1 critical → revise plan §Risks per AD-Plan-1 audit-trail)
