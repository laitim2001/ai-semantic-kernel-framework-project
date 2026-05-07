# Sprint 57.5 — Checklist (V2 Reality Check & Smoke Test Sprint)

> [Sprint Plan](./sprint-57-5-plan.md)

**Sprint Goal**: 第一次 V2 真實 boot-up smoke test + 7-page browser test + 21-doc planning reality audit + gap report;**non-feature sprint** (0 source code change);primary deliverable = `v2-reality-gap-report.md`;pivoted from Feature Flags Admin UI plan (deferred to Phase 57.6+ candidate;files renamed `feature-flags-admin-bundle-deferred-{plan,checklist}.md`)。

---

## Day 0 — Setup + Branch + Pre-flight + Environment Health

### 0.1 Branch + plan + checklist commit
- [ ] **Branch from main(06d5c6ed)**
  - DoD:`git checkout -b feature/sprint-57-5-reality-check`
  - Verify:`git branch --show-current` → `feature/sprint-57-5-reality-check`
- [ ] **Commit plan + checklist + deferred-renamed files**
  - DoD:plan + checklist + `feature-flags-admin-bundle-deferred-{plan,checklist}.md` 全 staged + committed with conventional message `docs(plan, sprint-57-5): pivot to V2 Reality Check Sprint + defer Feature Flags Admin UI`
  - Verify:`git log --oneline -1` shows commit;`git status --short` clean

### 0.2 Day-0 三-prong 探勘 v3(reality check 性質;Prong 2 + 3 重點變成 environment readiness)
- [ ] **Prong 1 Path Verify**
  - `scripts/dev.py` exists(Glob)
  - `backend/src/api/main.py` exists
  - `frontend/package.json` exists
  - `backend/src/infrastructure/db/migrations/versions/0001_*.py` to `0016_sla_cost_ledger.py` 全 16 files exist(Glob)
  - `.env.example` exists at project root
  - `docker-compose.yml` or equivalent at project root(若 used)
  - Verify:Glob results + 列出 unexpected drift if any
- [ ] **Prong 2 Content Verify**
  - `scripts/dev.py` 包含 status / start commands(grep `def status` + `def start` or argparse subcommands)
  - `backend/alembic.ini` exists with `script_location = src/infrastructure/db/migrations`
  - Backend `.env` or `.env.example` 含 required env vars:`AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_DEPLOYMENT_NAME` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `REDIS_HOST`(grep verify each;若缺某 var → catalog as Day 0 D-finding)
  - Frontend `.env` 或 `vite.config.ts` 設置 backend proxy port 8000(grep verify)
- [ ] **Prong 3 Schema Verify**
  - 此 sprint 0 schema change → Schema verify N/A
  - **但 attempt 完成** per fold-in spirit:Grep `migrations/versions/0017_*.py` 不存在 confirm;`alembic current` head pointer = `0016_sla_cost_ledger`(若 0016 不存在 → critical D-finding)
  - Verify:N/A verdict logged in progress.md

### 0.3 Calibration multiplier pre-read
- [ ] **`mixed` 0.60 5th application (reality check 性質類比 audit cycle 但有真實 boot service / browser test 執行成本)**
  - 既有 4-data-point evidence:53.7=1.01 / 56.2=1.17 / 57.3=0.57 / 57.4=0.42 平均 0.79 below band(57.4 retro 已 logged AD-Sprint-Plan-6 candidate);本 sprint 為 5th data point — reality check 性質可能 ratio 類比 audit cycle 偏低 OR 反映實際 boot service / browser test 工作量
  - 此 sprint:bottom-up ~15 hr × 0.60 = **~9 hr** commit
  - Day 4 retro Q2 verify:若 ratio in band → 0.60 仍 valid for reality-check sprints;若 < 0.85 → reality-check 應降至 0.40-0.50;若 > 1.20 → V2 累積 drift 比預期大 reality-check 工作量大;3 種 case 都有 valuable signal

### 0.4 Pre-flight verify(main green baseline 不變 — 0 source code change)
- [ ] **Backend baselines (pre-sprint snapshot)**
  - `python -m pytest backend/tests/ -q --tb=no` → 1598 collected / 0 failures(57.4 baseline)
  - `python -m mypy backend/src --strict` → 0 errors / 295 source files
  - `python scripts/lint/run_all.py` → 8 V2 lints 8/8 green
  - `grep -rn "import openai\|import anthropic" backend/src/agent_harness/` → 0(LLM SDK leak)
  - Verify:All 4 baselines documented in progress.md ✅ (1598 / 0/295 / 8/8 / 0)
- [ ] **Frontend baselines (pre-sprint snapshot)**
  - `cd frontend && npm run lint` → clean
  - `cd frontend && npm run build` → success / 75 modules / 209.11 kB
  - `cd frontend && npm run test` → 35 unit tests pass(57.4 baseline)
  - Playwright e2e 23 tests baseline(57.4 closeout)
  - Verify:All 4 baselines documented in progress.md ✅

### 0.5 Decide boot path + env var verification
- [ ] **Verify env vars set / Docker stack availability**
  - Check `.env` exists at project root(NOT just `.env.example`);若 missing → user 需手動建立
  - `python -c "import os; print(os.environ.get('AZURE_OPENAI_API_KEY', 'MISSING'))"`(via dev shell)— 若 MISSING → US-2 real LLM call deferred 到 Phase 58
  - `docker ps` → confirm Docker daemon 運行(若 used)
  - `psql --version` → confirm PostgreSQL client 可用
  - `redis-cli --version` → confirm Redis client 可用
  - 結果 catalog at Day 0 D-findings(若 missing critical env → revise plan §Risks per AD-Plan-1)

### 0.6 Day 0 progress.md commit + push
- [ ] **Catalogue D-findings + decide Day 1 boot path**
  - 列出 Day 0 D-findings(env vars / Docker / 缺 dependency)
  - Document 三-prong attempt time + findings count
  - Verify:`docs/03-implementation/agent-harness-execution/phase-57/sprint-57-5/progress.md` exists with Day 0 section ✅
- [ ] **Day 0 commit + push**
  - DoD:progress.md staged + committed `docs(progress, sprint-57-5): Day 0 三-prong + env health + boot path decision`
  - Verify:`git log --oneline -1` shows commit;remote up-to-date

---

## Day 1 — US-1 Service Boot + DB Migrations + Seed + US-2 Backend API Smoke

### 1.1 Boot all services
- [ ] **`python scripts/dev.py status`**
  - DoD:execute + capture output to progress.md
  - Verify:status output 列出 backend / frontend / PG / Redis 各狀態
- [ ] **`python scripts/dev.py start` (or manual)**
  - DoD:all services start 成功 (no fatal error)
  - Manual fallback (if scripts/dev.py 不 work):
    - Docker:`docker compose up -d postgres redis`
    - Backend:`cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`(background process — DO NOT kill node;keep running)
    - Frontend:`cd frontend && npm run dev`(background process — DO NOT kill node)
  - Verify:All processes spawned without fatal errors
- [ ] **Health check 4 services**
  - `curl http://localhost:8000/health` → 200 + JSON response
  - `curl http://localhost:3005/` → 200 + HTML response
  - `psql -h localhost -U $DB_USER -d $DB_NAME -c "SELECT 1"` → 1
  - `redis-cli -h localhost PING` → PONG
  - Verify:All 4 commands succeed;若 fail → catalog Critical Gap-N + decide whether continue Day 1 or pivot per Risk Class D

### 1.2 Apply Alembic migrations (16 migrations)
- [ ] **`cd backend && alembic upgrade head`**
  - DoD:execute + capture output (列出 0001 → 0016 progressive apply OR baseline + only new migrations)
  - Verify:`alembic current` → `0016_sla_cost_ledger`(per CLAUDE.md memory + 56.3 ship)
- [ ] **List all tables**
  - `psql -c "\dt"` 列出 all tables
  - Expected ~30 tables(tenants / users / sessions / audit_log / agent_state_snapshots / verification_logs / subagent_runs / hitl_policies / hitl_approval_requests / hitl_audit / feature_flags / cost_ledger / sla_violations / sla_reports / etc.)
  - Verify:expected baseline tables 全部 present;若 missing → catalog Critical Gap

### 1.3 Seed default data
- [ ] **Seed default tenant**
  - SQL:`INSERT INTO tenants (id, code, display_name, state, plan, ...) VALUES (gen_random_uuid(), 'default-tenant', 'Default Test Tenant', 'ACTIVE', 'ENTERPRISE', ...)` (or via seed script)
  - 寫 SQL 至 `docs/.../sprint-57-5/seed_data.sql` for repeatability
  - Verify:`psql -c "SELECT * FROM tenants WHERE code='default-tenant'"` returns 1 row
- [ ] **Seed admin user (super-admin platform role)**
  - SQL:`INSERT INTO users ...` with super-admin role JWT-encoded for testing
  - Verify:`psql -c "SELECT * FROM users WHERE platform_role='super_admin'"` returns ≥ 1 row
- [ ] **Seed 4 baseline feature flags**
  - Via FeatureFlagsService.seed_defaults() — Python one-liner:
    ```python
    cd backend && python -c "
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from core.feature_flags import get_feature_flags_service
    async def main():
        engine = create_async_engine('postgresql+asyncpg://...')
        Session = async_sessionmaker(engine)
        async with Session() as s:
            svc = get_feature_flags_service(s)
            inserted = await svc.seed_defaults()
            await s.commit()
            print(f'Seeded {inserted} flags')
    asyncio.run(main())
    "
    ```
  - Verify:`psql -c "SELECT name, default_enabled FROM feature_flags ORDER BY name"` returns 4 rows(thinking_enabled / verification_enabled / llm_caching_enabled / pii_masking)

### 1.4 Backend API real smoke test
- [ ] **POST /api/v1/chat real Azure OpenAI live**
  - DoD:curl with real session + tenant + simple message → SSE stream captured to log file
  - SSE assertions:LLMRequested + LLMResponded(provider=azure_openai + tokens > 0) + LoopCompleted(8 fields per 57.2)events captured
  - SSE stream 完整 close (non-hang) — measure with timeout 60s
  - 若 Azure OpenAI key MISSING → mark deferred + skip
  - Verify:SSE log file ≥ 5 events captured;all event types present
- [ ] **GET /api/v1/admin/tenants list (57.4)**
  - `curl -H "Authorization: Bearer $ADMIN_JWT" http://localhost:8000/api/v1/admin/tenants` → 200 + items array containing default-tenant
  - Verify:JSON response 含 ≥ 1 item
- [ ] **GET /api/v1/admin/tenants/{id} single (57.3)**
  - `curl ... http://localhost:8000/api/v1/admin/tenants/$TID` → 200 + TenantResponse 10 fields
  - Verify:JSON response 含 id / code / state / plan / ...
- [ ] **GET cost-summary + sla-report (56.3)**
  - `curl ... "http://localhost:8000/api/v1/admin/tenants/$TID/cost-summary?month=2026-05"` → 200
  - `curl ... "http://localhost:8000/api/v1/admin/tenants/$TID/sla-report?month=2026-05"` → 200
  - Verify:two responses 結構合理(cost-summary 含 by_type;sla-report 含 metrics)

### 1.5 Cat 9 + Cat 10 real fire test
- [ ] **Cat 9 PII detection real fire**
  - POST /api/v1/chat with body containing PII test (`"my SSN is 123-45-6789"`) → SSE stream
  - Look for SSE GuardrailTriggered event(若 PII detector wired)
  - Catalog:✅ fired / ❌ not fired(若 ❌ → AP-4 Potemkin candidate driving Phase 57.6+)
- [ ] **Cat 10 verification real fire (若 CHAT_VERIFICATION_MODE=enabled)**
  - Check env var `CHAT_VERIFICATION_MODE`(per 55.5 ship default disabled)
  - 若 enabled:POST /chat → SSE VerificationPassed/Failed event captured
  - 若 disabled:catalog as expected;Phase 57.6+ flip operational decision
  - Catalog 觀察結果

### 1.6 DB-side verification
- [ ] **audit_log entries**
  - `psql -c "SELECT operation, count(*) FROM audit_log GROUP BY operation"` 
  - Expected operations include:conversation_started / tool_executed / verification_completed / approval_requested(post Day 1 chat)
  - Catalog rows count + operation distribution
- [ ] **cost_ledger entries**
  - `psql -c "SELECT cost_type, sub_type, count(*) FROM cost_ledger GROUP BY cost_type, sub_type"`
  - Expected:llm_call entries with sub_type=`{provider}_{model}_input` + `_output` per 57.2 split
  - 若 0 rows after Day 1 chat → AP-4 Potemkin candidate(56.3 cost ledger 沒 wired correctly)

### 1.7 Day 1 commit + push + progress.md
- [ ] **Commit US-1 + US-2 evidence**
  - Stage progress.md + seed_data.sql + chat_sse.log + screenshots if any
  - Commit:`docs(progress, sprint-57-5): Day 1 service boot + DB migrations + seed + backend API real smoke`
  - Catalog Critical Gaps in progress.md per finding
  - Verify:`git log main..HEAD --oneline` shows new commit;remote up-to-date

---

## Day 2 — US-3 Frontend Browser Manual Test (7 Pages)

### 2.1 Open browser + capture Home
- [ ] **Open http://localhost:3005 in real browser (Chrome / Firefox / Edge)**
  - DoD:URL loads + Home page renders without console error
  - Capture screenshot saved to `docs/.../sprint-57-5/screenshots/01_home.png`
  - Verify:File exists + > 50 KB(real screenshot not blank)

### 2.2-2.8 Per-page browser test (7 pages)
- [ ] **chat-v2 (50.2 ship)**
  - Navigate via Home Link → `/chat-v2`
  - Send "hello" message
  - Observe SSE events render in UI(LLM thinking / response chunks)
  - Screenshot `02_chat.png`
  - Catalog:✅ functional / ⚠️ partial(具體 issue) / ❌ broken
- [ ] **governance (53.5 ship)**
  - Navigate to `/governance`
  - See approvals list — 若 0 approvals,觀察 empty state
  - 若 ≥ 1 approval:click approve/reject test action(reverse if test data)
  - Screenshot `03_governance.png`
  - Catalog
- [ ] **verification (54.1)**
  - Navigate to `/verification`(若 route exists)
  - See verification panel
  - Screenshot `04_verification.png`
  - Catalog(若 route 不存在 → 列為 AP-4 Potemkin candidate)
- [ ] **cost-dashboard (57.1 v2 ship)**
  - Navigate to `/cost-dashboard`
  - Select month from picker(default current month)
  - See cost cards + breakdown table
  - Screenshot `05_cost.png`
  - Catalog
- [ ] **sla-dashboard (57.1 v2 ship)**
  - Navigate to `/sla-dashboard`
  - Select month
  - See 6 SLA metric cards
  - Screenshot `06_sla.png`
  - Catalog
- [ ] **tenant-settings (57.3 ship)**
  - Navigate to `/tenant-settings/?tenant_id=$TID`
  - See view (state badge + plan badge + JSON details)
  - Click Edit → modify display_name → Save
  - See success toast OR error
  - Screenshot `07_tenant_settings.png`
  - Catalog
- [ ] **admin-tenants (57.4 ship)**
  - Navigate to `/admin-tenants`
  - See tenant list (≥ 1 default tenant)
  - Filter by state=ACTIVE → list refreshes
  - Search "default" → list refreshes
  - Click View row → navigate to tenant-settings
  - Screenshot `08_admin_tenants.png`
  - Catalog

### 2.9 Catalogue results + Critical Gaps
- [ ] **Per-page result table in progress.md**
  - 7 rows + Home;each:status / specific issue / Phase 57.6+ implication
  - Identify Critical Gaps(any ❌ broken page)+ MAJOR Concerns(any ⚠️ partial)

### 2.10 Day 2 commit + push + progress.md + screenshots
- [ ] **Commit US-3**
  - Stage 8 PNG files + progress.md update
  - Commit:`docs(progress, sprint-57-5): Day 2 frontend browser manual test 7 pages + screenshot evidence`
  - Verify:`git log main..HEAD --oneline` shows new commit;`ls docs/.../sprint-57-5/screenshots/` shows 8+ files

---

## Day 3 — US-4 V2 Planning Doc 21 份 Reality Audit

### 3.1 Read 21 V2 planning docs (~10-15 min each)
- [ ] **00-v2-vision.md** — Concept / Code location / Wired? / Drift severity / Phase 57.6+ implication
- [ ] **01-eleven-categories-spec.md** — 11+1 範疇 全 Level 4 verified? Cat 9 Level 5 真實?
- [ ] **02-architecture-design.md** — 5-layer 架構 真實 in place?
- [ ] **03-rebirth-strategy.md** — V1 archived / V2 重構 strategy 對齊?
- [ ] **04-anti-patterns.md** — 11 條反模式 真實全綠?
- [ ] **05-reference-strategy.md** — Reference docs 真實使用?
- [ ] **06-phase-roadmap.md** — 22 sprint 真實 ship?
- [ ] **07-tech-stack-decisions.md** — 技術選型 與實際 stack 一致?
- [ ] **08-glossary.md** — 術語 與實際代碼一致?
- [ ] **08b-business-tools-spec.md** — 5 domain × 24 工具 真實 wired?
- [ ] **09-db-schema-design.md** — DB schema 與 0001-0016 migrations 一致?
- [ ] **10-server-side-philosophy.md** — 3 大原則 enforced?
- [ ] **11-test-strategy.md** — 測試金字塔 70/25/5 比例 真實?
- [ ] **12-category-contracts.md** — Contracts 真實 wired?
- [ ] **13-deployment-and-devops.md** — Dev / CI / Docker / DR 真實 in place?
- [ ] **14-security-deep-dive.md** — STRIDE / OWASP / GDPR 真實 covered?
- [ ] **15-saas-readiness.md** — SaaS Stage 1 真實 delivered?
- [ ] **16-frontend-design.md** — 12 頁 frontend design 哪幾頁 ship 哪幾頁 not?
- [ ] **17-cross-category-interfaces.md** — 24 dataclass + 19 ABC + 22 LoopEvent 全 wired?
- [ ] **README.md (整體導覽)** — 21 份 doc 結構導覽 真實 reflect?
- [ ] **v2-review-integration-report-20260428.md** — 兩輪 expert review integration 真實 fold-in?

### 3.2 Output v2-reality-gap-report.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-5/v2-reality-gap-report.md`**
  - Per-doc section (21 sections):title / concept / code location / wired / drift severity / Phase 57.6+ implication
  - Synthesis section:
    - Top 5 critical RED findings (with severity + impact + effort estimate)
    - Top 5 YELLOW informational findings
    - Top 5 GREEN well-aligned regions
    - Phase 57.6+ candidate scope mapping
  - File header per file-header-convention.md
  - Verify:`wc -l v2-reality-gap-report.md` ≥ 300 lines

### 3.3 Day 3 commit + push + progress.md
- [ ] **Commit US-4**
  - Stage v2-reality-gap-report.md + progress.md update
  - Commit:`docs(progress, sprint-57-5): Day 3 V2 planning doc 21 份 reality audit + gap report`
  - Verify:`git log main..HEAD --oneline` shows new commit

---

## Day 4 — US-5 Closeout: Retrospective + Phase 57.6+ Direction Decision

### 4.1 Retrospective.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-5/retrospective.md`**
  - Q1 What went well — 真實 boot-up 哪些順利 + audit 哪些 doc 真實 well-aligned
  - Q2 What didn't go well + calibration ratio(`mixed` 0.60 5th application;若 actual >> commit → V2 累積 drift 大;若 actual << commit → V2 alignment 比預期好)
  - Q3 What we learned — V2 reality vs paper learnings(generalizable lessons)
  - Q4 Audit Debt deferred — top 5 findings 中哪些 carry-forward 為 Phase 57.6+ AD-Reality-N
  - Q5 Next steps + Phase 57.6+ direction proposal(rolling planning;不寫具體未來 sprint 任務,只寫 carryover 候選 + user decision required)
  - Q6 Solo-dev policy validation
  - Verify:`wc -l retrospective.md` ≥ 250 lines(reality check 因發現多於常規 sprint,期望 retro 較長)

### 4.2 Memory snapshot + MEMORY.md index
- [ ] **Create `memory/project_phase57_5_v2_reality_check.md`**
  - Same format as `project_phase57_4_admin_tenants_list.md` (≤ 80 lines per memory budget per V2 紀律)
  - Frontmatter complete
- [ ] **Update MEMORY.md index** add 1 line entry

### 4.3 Open PR + CI green + solo-dev merge
- [ ] **Push branch + open PR**
  - Push:`git push -u origin feature/sprint-57-5-reality-check`
  - PR title:`Sprint 57.5 — V2 Reality Check & Smoke Test Sprint (boot all services + 7-page browser test + 21-doc audit + gap report)`
  - PR body:Sprint goal + 5 USs + acceptance + gap report top 5 critical findings + Phase 57.6+ direction TBD per user decision
  - Verify:5 active CI checks green(此 sprint 0 source code → CI 應快速 green);solo-dev policy review_count=0 satisfied
- [ ] **Squash merge to main**
  - DoD:GitHub UI squash + merge;branch deleted post-merge
  - Verify:main HEAD updated

### 4.4 Closeout PR
- [ ] **Closeout branch + PR**
  - Branch:`chore/sprint-57-5-closeout`
  - Updates:SITUATION-V2 §9 milestones row + §11 Last Updated + Update history;CLAUDE.md Phase / Latest Sprint / main HEAD / Last Updated / Current Phase fields(flag 33 deliverables verified count)
  - Commit message:`docs(closeout, sprint-57-5): SITUATION-V2 + CLAUDE.md sync to V2 Reality Check + Phase 57.6+ direction TBD`
  - PR body:reference Sprint 57.5 PR + summary stats(0 source code change / 8+ screenshots / 21 docs audited / N gaps catalogued / calibration ratio)
  - Verify:Squash merge to main;both branches deleted;working tree clean

### 4.5 User decision interaction (Phase 57.6+ direction)
- [ ] **Present gap report top 5 critical findings + user decision question**
  - Direction options (depending on findings):
    - (a) 修 critical gaps 1-by-1(maintenance focus;Phase 57.6+ = AD-Reality-N audit cycle bundle)
    - (b) 繼續 feature work(若 gaps non-critical;Phase 57.6+ = revive Feature Flags Admin UI from `feature-flags-admin-bundle-deferred-{plan,checklist}.md` OR pick other Phase 57.x candidates)
    - (c) Pivot to specific gap-driven sprint(e.g. Phase 57.6 = "fix Cat 9 wired-but-mocked detection" 等具體 gap-driven scope)
    - (d) Other user-specified direction
  - Per rolling planning 紀律:不預寫 Phase 57.6 plan;等 user 明確選定 scope 才起草

---

## 重要備註

- **此 sprint 0 source code change** — 只動 docs / progress / retrospective / screenshots / seed_data.sql
- **此 sprint 不算入 Phase 57+ Frontend SaaS 4/N counter** — 它是 reality check 性質 verification gate;Frontend SaaS 進度仍 3/N 不變
- **若 Day 0 / Day 1 出現 critical service boot failures → 直接 sprint pivot 為 pure doc-audit mode** (US-2 + US-3 deferred to Phase 57.6+;US-4 + US-5 仍 進行 + 將 boot failure catalogue 為 Phase 57.6+ MUST-FIX-FIRST scope)
- **誠實 over completeness** — Day 4 retrospective 不必 sugar-coat;reality 比預期糟是 sprint 主要 deliverable + V2 紀律 #2 主流量驗證真實 enforcement 的價值
- **不殺 node 流程** — 啟動 backend uvicorn / frontend vite 後保留 running(per CLAUDE.md global rule;node 流程同時跑 claude code)
