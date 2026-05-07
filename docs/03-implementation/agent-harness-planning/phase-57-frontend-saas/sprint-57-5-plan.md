# Sprint 57.5 — V2 Reality Check & Smoke Test Sprint (boot all services + 7-page browser test + 21-doc planning audit + gap report)

> **Sprint Type**: Phase 57+ fourth sprint — **honest reality verification gate** before further feature work;non-feature sprint;deliverable = gap report + boot-up evidence + browser screenshots + V2 planning doc 21 份 reality audit;pivoted from Feature Flags Admin UI plan (deferred to Phase 57.6+ candidate per `feature-flags-admin-bundle-deferred-{plan,checklist}.md`)
> **Owner Categories**: §All (cross-cutting reality check) — boot scripts / 16 Alembic migrations / 8 V2 lints / 21 V2 planning docs / 7 frontend pages / 3 SaaS Stage 1 backend stacks / 12 範疇 + Cat 12 cross-cutting
> **Phase**: 57 (Frontend SaaS — 4/N sprint;但 4/N 不開新 frontend feature,先 audit 已交付 22+5+SaaS3+Frontend3 = **33 deliverables 是否真的 functional**;rolling planning per .claude/rules/sprint-workflow.md)
> **Workload**: 5 days (Day 0-4); bottom-up est ~15 hr → calibrated commit **~9 hr** (multiplier **0.60** — `mixed` 5th application;reality check 性質類比 audit cycle 但有真實 boot service / browser test 執行成本 — 比 audit cycle 0.40 重,比 medium-backend 0.85 輕;若 ratio < 0.85 → 與其他 audit 分類比較;若 ratio > 1.20 → 反映 V2 累積 drift 比預期大)
> **Branch**: `feature/sprint-57-5-reality-check`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: User concern raised 2026-05-08 — V2 重構 6 個月 22+5 sprint 累積但 0 次真實 boot-up smoke test 風險;主流量驗證原則 (V2 紀律 5 大核心約束 #2) + AP-4 Potemkin Feature 累積風險;user-approved 2026-05-08 pivot from Feature Flags Admin UI to Reality Check
> **AD logging (sub-scope)**: NEW Reality Check Sprint as V2 inflection-point gate;若發現 critical gap → catalog as AD-Reality-N;若 21 V2 planning docs 全 verified → 強證據 V2 22+5 ship 真的 functional(unlikely scenario per honest expectation);若 found ≥ 5 gaps → AD-Reality-N entries 為 Phase 57.6+ scope source

---

## Sprint Goal

Provide the **first end-to-end reality verification gate** for V2 重構 22 sprint + 5 carryover bundle + Phase 56-58 SaaS Stage 1 + Phase 57+ Frontend 3/N(共 33 deliverables)by:

- **US-1**: Service boot health check + 16 Alembic migrations apply + seed default data — `python scripts/dev.py start`(or manual) → all 5 services(backend / frontend / PostgreSQL / Redis / RabbitMQ optional)healthy;`alembic upgrade head` 0001-0016 全成功;seed default tenant + admin user + 4 baseline feature flags via SQL/script
- **US-2**: Backend API real smoke test — POST /api/v1/chat 真實打到 Azure OpenAI live + 收 SSE 8 events stream;GET admin endpoints(57.4 list / 57.3 single / 56.3 cost-summary / 56.3 sla-report)curl 200;Cat 9 Guardrails 真實 fire(送 PII test message);Cat 10 Verification 真實 fire(若 CHAT_VERIFICATION_MODE=enabled);audit chain + cost ledger DB 真實 entries
- **US-3**: Frontend browser manual test — http://localhost:3005 real browser;7 pages 逐頁試:Home / chat-v2 / governance / verification / cost-dashboard / sla-dashboard / tenant-settings / admin-tenants;每頁 capture screenshot + 記錄 broken / 401/403 / 空白 / mock-only behavior;list real-vs-paper UX gaps
- **US-4**: V2 planning doc 21 份 reality audit — 開 `docs/03-implementation/agent-harness-planning/00-v2-vision.md` 到 `17-cross-category-interfaces.md` + `v2-review-integration-report-20260428.md` 21 份;對每份 catalog:概念 → 在哪段 code? → 真的 wired? → drift 嚴重程度;產出 `v2-reality-gap-report.md`
- **US-5**: Gap report 統合 + retrospective(6 必答)+ decide Phase 57.6+ direction(基於 gap report 中 top 5 critical findings 由 user 選擇方向);memory snapshot;SITUATION-V2 §9 + CLAUDE.md sync to **Phase 57+ SaaS Frontend 4/N (Sprint 57.5 closed — V2 Reality Check)** + flag 33 deliverables verified count

Sprint 結束後:
- (a) **第一次 V2 真實 boot-up smoke test 完成** — 22+5+SaaS3+Frontend3 累積 deliverables 是否 functional 有了 reality 證據(不再只靠 CI green + mock test)
- (b) **Gap report 產出** — `v2-reality-gap-report.md` 列出至少 5 個「規劃 vs 真實」差距(realistic;22 sprint 累積必有 drift)+ 可能 surface AP-4 Potemkin Feature 案例(若有 → 必須 Phase 57.6+ 修)
- (c) **Phase 57+ 後續方向 user-decided** — 基於 gap report top 5 critical findings + user 偏好(修 critical gaps / 繼續 feature work / pivot to AD-Reality-N audit)
- (d) **Browser screenshot evidence** — 7 frontend pages 真實 render 的證據;若 broken → catalog 並 inform Phase 57.6+ scope
- (e) **V2 紀律自我審視 transparency** — 對齊主流量驗證原則(V2 紀律 #2)+ AP-4 反模式檢查(11 條反模式檢查清單)真實 verification

**主流量驗收標準**:
- ✅ All 5 services 全部成功 boot up(backend uvicorn + frontend vite + PostgreSQL + Redis + RabbitMQ optional)
- ✅ All 16 Alembic migrations 0001-0016 alembic upgrade head 成功
- ✅ Default tenant + admin user + 4 baseline feature flags 真實 DB 中 seeded
- ✅ POST /api/v1/chat 真實打到 Azure OpenAI live API + SSE event stream 包含 LLMResponded(provider=azure_openai + tokens > 0)
- ✅ All 7 frontend pages browser open + render(screenshot evidence)
- ✅ V2 planning doc 21 份 reality audit 完成 + gap report ≥ 5 findings catalogued
- ✅ Retrospective 6 必答 + Phase 57.6+ direction proposal listed
- ❌ 不要求 0 gaps — gap 是預期 + valuable;0 gap 反而 suspicious

---

## Background

### V2 進度 (2026-05-08 reality check 起點)

- **22/22 sprints (100%) main progress completed** + **Phase 56-58 SaaS Stage 1 3/3 ✅ CLOSED** + **Phase 57+ Frontend SaaS 3/N completed**(57.1 v2 + 57.3 + 57.4)
- main HEAD: `06d5c6ed` (Sprint 57.4 closeout PR #111) — Day 0 verified
- pytest baseline 1598 / mypy --strict 0/295 source files / 8 V2 lints 8/8 green / LLM SDK leak 0
- Vitest baseline 35 / Playwright e2e baseline 23 (**全 mock-based** — 用 page.route browser-layer mock per 57.1 v2 D19 + 57.3 D13 + 57.4 D14)
- Vite build 75 modules / 209.11 kB
- **真實 boot-up smoke test count: 0 次** — V2 重構 6 個月從未做過

### 為什麼 57.5 Pivot 為 Reality Check 而非 Feature Flags Admin UI

User concern raised 2026-05-08(legitimate engineering instinct):

1. **V2 22+5 sprint 全靠 CI green + mock e2e — 從未真實 boot service 跑** — pytest 1598 全用 fixture / TestClient 不打到真實 PG + Redis + Azure OpenAI live API;Vitest 全 mock service / store;Playwright e2e 全 page.route() browser-layer mock(57.1 v2 D19 + 57.3 D13 + 57.4 D14 明確記載)
2. **AP-4 Potemkin Feature 累積風險** — V2 紀律核心約束 #2「主流量驗證原則」要求「任何功能必須能在 UnifiedChat-V2 → API → Agent Loop 主流量中驗證」;但 6 個月 22+5 sprint 從未真實主流量驗證 → AP-4 風險未被偵測累積
3. **V2 規劃文件 00-17 (21 份) 從未做過 reality audit** — 規劃 vs 實際 drift 必然存在(22 sprint × 5 個月 演化),但無 audit 紀錄 → cannot answer "若關掉某 module 會壞什麼"
4. **誠實工程文化** — 累積 22 sprint 紙面 success 後,reality check 是 ladder-of-progress 必要 gate;類比軟體業界 "demo on Friday" 文化但延遲了 6 個月
5. **Phase 57+ feature work 風險** — 若繼續加 feature(如 Feature Flags Admin UI / Onboarding wizard / Audit log frontend / DR / GDPR / SaaS Stage 2)而 V2 baseline 有 hidden gaps → 新 feature 可能 build on broken foundation → return on investment 低

**Reality check Sprint 性質區分**:
- 不是 feature sprint(0 new endpoints / 0 new components / 0 new tables)
- 不是 audit cycle bundle(audit cycle 通常 fold-in process AD;此 sprint 是 reality verification + gap discovery)
- 不是 maintenance sprint(不修 bugs;只 surface them)
- **是 honesty sprint** — 主要 deliverable 是 gap report + screenshot evidence + retrospective decision

### 既有結構(Day 0 plan-time 探勘 grep 已驗證以下事實)

✅ **以下 layout 是 plan-time 已 verified via grep**:

```
backend/src/                                       # 22+5 sprint 累積
├── api/main.py                                    # ✅ uvicorn entry
├── api/v1/admin/{tenants,cost_summary,sla_reports}.py   # ✅ 56.1 + 56.3 + 57.3 + 57.4
├── api/v1/chat.py                                 # ✅ 50.2 ship
├── core/feature_flags.py                          # ✅ 56.1 (4 baseline flags)
├── infrastructure/db/migrations/versions/         # ✅ 0001 - 0016 (16 migrations)
└── ...

frontend/src/                                      # Phase 57+ 3/N + 53.5/56 既有
├── App.tsx                                        # ✅ all routes registered
├── pages/                                         # ✅ 7 pages
│   ├── chat-v2/                                   # ✅ 50.2 ship
│   ├── governance/                                # ✅ 53.5 ship
│   ├── verification/                              # ✅ 54.1 ship?
│   ├── cost-dashboard/                            # ✅ 57.1 v2 ship
│   ├── sla-dashboard/                             # ✅ 57.1 v2 ship
│   ├── tenant-settings/                           # ✅ 57.3 ship
│   └── admin-tenants/                             # ✅ 57.4 ship
└── ...

scripts/dev.py                                     # ✅ existing (V2 unified dev environment per CLAUDE.md)
```

✅ **以下 21 份 V2 planning docs (Day 3 reality audit 對象)**:

```
docs/03-implementation/agent-harness-planning/
├── README.md (整體導覽)
├── 00-v2-vision.md
├── 01-eleven-categories-spec.md (核心 11+1 範疇 spec)
├── 02-architecture-design.md
├── 03-rebirth-strategy.md
├── 04-anti-patterns.md (11 條反模式)
├── 05-reference-strategy.md
├── 06-phase-roadmap.md
├── 07-tech-stack-decisions.md
├── 08-glossary.md
├── 08b-business-tools-spec.md
├── 09-db-schema-design.md
├── 10-server-side-philosophy.md (3 大原則)
├── 11-test-strategy.md
├── 12-category-contracts.md
├── 13-deployment-and-devops.md
├── 14-security-deep-dive.md
├── 15-saas-readiness.md
├── 16-frontend-design.md
├── 17-cross-category-interfaces.md (Single-source registry)
└── v2-review-integration-report-20260428.md
```

### V2 紀律 9 項對齊確認

1. **Server-Side First** ✅ Reality check 對齊 — 試圖 verify server-side actually serves
2. **LLM Provider Neutrality** ✅ 此 sprint 不動 LLM 鏈路;但會 verify 主流量真的能切到 Azure OpenAI live(part of US-2 smoke)
3. **CC Reference 不照搬** ✅ Reality check 為 V2-specific
4. **17.md Single-source** ✅ Reality check 不新增任何 cross-category interface
5. **11+1 範疇歸屬** ✅ US-1~US-5 全 cross-cutting reality check 不歸屬任何單一範疇
6. **04 anti-patterns** ✅✅✅ **此 sprint 主要對齊 AP-4 (Potemkin Feature)** + AP-9 (Verification Loops);其餘 11 條反模式可在 Day 3 audit 中被自我檢查
7. **Sprint workflow** ✅ plan → checklist → Day 0 三-prong → Day 1-4 → progress + retro;本文件鏡射 57.4 plan 結構(11 sections + metadata block)
8. **File header convention** ✅ 此 sprint 不寫 source code(0 new file);`v2-reality-gap-report.md` 加 file header
9. **Multi-tenant rule** ✅ Reality check seed default tenant 用標準 multi-tenant pattern;不違反

---

## User Stories

### US-1: Service Boot Health Check + DB Migrations + Seed Defaults

**As** the V2 sprint executor
**I want** to verify all V2 services can actually boot up in development environment + Alembic migrations 0001-0016 全 apply + seed initial data
**So that** subsequent reality tests have a working baseline + we discover any boot-time failures early

**Acceptance**:
- `python scripts/dev.py status` 執行成功 + capture output to progress.md
- `python scripts/dev.py start` (或 manual `uvicorn` + `npm run dev` + Docker compose up PG + Redis) → all services healthy
- Backend `curl http://localhost:8000/health` → 200
- Frontend `curl http://localhost:3005/` → 200 + HTML response
- PostgreSQL `psql -c "SELECT 1"` → 1
- Redis `redis-cli PING` → PONG
- `alembic upgrade head` 從 baseline 應用到 0016 全成功(若已有 schema → 確認 `alembic current` = `0016_sla_cost_ledger`)
- `psql -c "\dt"` 列出全部 tables(預期 ~30+ tables: tenants / users / sessions / audit_log / agent_state_snapshots / verification_logs / subagent_runs / hitl_policies / hitl_approval_requests / hitl_audit / feature_flags / cost_ledger / sla_violations / sla_reports / etc.)
- Seed scripts(or SQL):default tenant `code='default-tenant', state='ACTIVE', plan='ENTERPRISE'` + admin user with super-admin platform role + 4 baseline feature flags via FeatureFlagsService.seed_defaults
- Verify seeded data in DB via `psql` SELECT
- Catalogue any boot-time errors / 缺 env vars / 缺 dependency / port conflict;若 1+ service 無法 boot → catalogue as Critical Gap-1 (driving Phase 57.6+ scope)

### US-2: Backend API Real Smoke Test

**As** the V2 sprint executor
**I want** to fire real HTTP requests to all major V2 endpoints + verify SSE streams + verify DB-side effects
**So that** we have evidence that 22+5+SaaS3 backend deliverables actually work end-to-end (not just unit-tested with mocks)

**Acceptance**:
- POST /api/v1/chat with real session_id + tenant_id headers + simple message body → SSE event stream:
  - LLMRequested event captured
  - LLMResponded event captured (provider=azure_openai, model=gpt-5.4 or actual configured, tokens > 0)
  - LoopCompleted event captured (with all 8 fields per 57.2 — input_tokens / output_tokens / total_turns / total_tool_calls / total_subagents / total_verifications / provider / model)
  - SSE stream 完整 close(non-hang)
- GET /api/v1/admin/tenants (57.4 list) → 200 + items array containing seeded default tenant
- GET /api/v1/admin/tenants/{id} (57.3) → 200 + TenantResponse 10 fields
- PATCH /api/v1/admin/tenants/{id} (57.3) → 200 + audit chain entry verified in DB
- GET /api/v1/admin/tenants/{id}/cost-summary?month=YYYY-MM (56.3) → 200 (after firing 1+ chat)
- GET /api/v1/admin/tenants/{id}/sla-report?month=YYYY-MM (56.3) → 200
- Cat 9 Guardrails real fire test:POST /api/v1/chat with PII in message body("my SSN is 123-45-6789") → SSE GuardrailTriggered event captured(若 PII detector wired)
- Cat 10 Verification real fire test (若 CHAT_VERIFICATION_MODE=enabled):POST /api/v1/chat → SSE VerificationPassed/Failed event captured
- DB verification:`psql -c "SELECT operation, count(*) FROM audit_log GROUP BY operation"` 列出 audit chain entries 真實累積(operations 包含 conversation_started / tool_executed / verification_completed / etc.)
- DB verification:`psql -c "SELECT cost_type, sub_type, count(*) FROM cost_ledger GROUP BY cost_type, sub_type"` 列出 cost ledger entries(56.3 ship — input/output token splits + per-tool entries)
- Catalogue any 4xx/5xx errors / SSE timeout / missing event / DB silent failures(這些都是 critical findings driving Phase 57.6+)

### US-3: Frontend Browser Manual Test (7 Pages)

**As** the V2 sprint executor
**I want** to actually open each frontend page in real browser + verify render + interact + capture screenshots
**So that** we have visual evidence that 7 pages真的 functional + identify any broken pages / 401-403 issues / mock-only flows

**Acceptance**:
- Open http://localhost:3005 in real browser (Chrome / Firefox);capture Home page screenshot
- For each of 7 pages, navigate via Home Link + capture screenshot + interact:
  - **chat-v2**(50.2):send simple message → see SSE events render in UI → see assistant response → screenshot
  - **governance**(53.5):see approvals list → click approve/reject (test action) → see updated state → screenshot
  - **verification**(54.1?):see verification panel → screenshot
  - **cost-dashboard**(57.1 v2):select month → see cost cards + breakdown → screenshot
  - **sla-dashboard**(57.1 v2):select month → see 6 SLA metric cards → screenshot
  - **tenant-settings**(57.3):use ?tenant_id=... query → see view → click Edit → modify display_name → save → see audit toast → screenshot
  - **admin-tenants**(57.4):see tenant list → filter by state=ACTIVE → search "default" → click View row → navigate to tenant-settings → screenshot
- Catalogue per-page result:✅ functional / ⚠️ partial(列出 issue) / ❌ broken(列出 error)
- 收集 broken pages → catalogue as Critical Gap-N driving Phase 57.6+ scope
- 收集 mock-only paths(若 frontend 沒 wire to real backend → 列為 AP-4 Potemkin candidates)
- 結果:`docs/03-implementation/agent-harness-execution/phase-57/sprint-57-5/screenshots/` 含 8+ screenshots(Home + 7 pages min)

### US-4: V2 Planning Doc 21 份 Reality Audit

**As** the V2 sprint executor
**I want** to read each of 21 V2 planning docs + cross-check against actual code/DB/runtime behavior + produce gap report
**So that** we can identify regions of "paper-only" planning vs "actually-implemented" planning

**Acceptance**:
- Read 21 V2 planning docs(00-17 + v2-review-integration-report)逐份;~10-15 min each
- For each doc, catalog in `v2-reality-gap-report.md`:
  - **Doc title**
  - **Concept summary** (1-3 sentences)
  - **Where in code?** (path / module / 找 grep evidence)
  - **Wired in main flow?** (主流量 verify;若 unwired → AP-4 candidate)
  - **Drift severity**:🟢 GREEN(完全 aligned)/ 🟡 YELLOW(minor drift acceptable)/ 🔴 RED(major drift / Potemkin / unimplemented)
  - **Phase 57.6+ implication**(若 RED → 必須 fix scope)
- 重點 audit areas:
  - 00 Vision:V2 vision delivered? V2 ≠ SaaS-ready 是否 honored?
  - 01 11+1 Categories:Cat 1-12 全 Level 4? Cat 9 Level 5 真的是?
  - 02 Architecture 5-layer:5 layer (api/business_domain/agent_harness/platform_layer/adapters/infrastructure) 真的 in place?
  - 04 Anti-patterns:11 條反模式 — AP-1 ~ AP-11 真的全綠?
  - 06 Roadmap:22 sprint 真的 ship 了什麼?
  - 10 Server-Side Philosophy:3 原則 enforced (server-side / LLM neutral / CC reference)?
  - 17 Cross-Category Interfaces:24 dataclass + 19 ABC + 22 LoopEvent 全 wired?
- Output:`v2-reality-gap-report.md`(~300-500 lines;structured per doc)+ summary section listing top 5 critical Phase 57.6+ scope candidates

### US-5: Gap Report Synthesis + Retrospective + Phase 57.6+ Direction Decision

**As** the V2 sprint executor
**I want** to synthesize US-1~US-4 findings + write retrospective + propose Phase 57.6+ direction options for user choice
**So that** Sprint 57.5 closes with actionable gap-driven roadmap rather than just data dump

**Acceptance**:
- `v2-reality-gap-report.md` synthesis section listing:
  - Top 5 critical findings (with severity + impact + effort estimate)
  - Top 5 informational findings (drift acceptable but worth tracking)
  - Phase 57.6+ candidate scope mapping (which findings → which sprint)
- retrospective.md(6 必答):
  - Q1 What went well — 真實 boot-up 哪些順利 + audit 哪些 doc 真的 well-aligned
  - Q2 What didn't go well + calibration ratio(`mixed` 0.60 5th application;若 actual >> commit → V2 累積 drift 大;若 actual << commit → V2 alignment 比預期好)
  - Q3 What we learned — V2 reality vs paper learnings(generalizable)
  - Q4 Audit Debt deferred — top 5 findings 中哪些 carry-forward 為 Phase 57.6+ AD-Reality-N
  - Q5 Next steps + Phase 57.6+ direction proposal(rolling planning;不寫具體未來 sprint 任務,只寫 carryover 候選 + user decision required)
  - Q6 Solo-dev policy validation
- Memory snapshot `memory/project_phase57_5_v2_reality_check.md`
- SITUATION-V2 §9 + CLAUDE.md sync to **Phase 57+ SaaS Frontend 4/N (Sprint 57.5 closed — V2 Reality Check & 33 deliverables verified count)**
- 結尾 user decision question:基於 gap report top 5 critical findings,Phase 57.6+ direction 選擇:
  - (a) 修 critical gaps 1-by-1(maintenance focus)
  - (b) 繼續 feature work(若 gaps non-critical)
  - (c) Pivot to AD-Reality-N audit cycle 連續 mini-sprints
  - (d) Other user-specified direction

---

## Technical Specifications

### Service Boot Sequence (Day 1 reference)

```bash
# Step 1: Status check
python scripts/dev.py status

# Step 2: Start all (or manual)
python scripts/dev.py start
# Or manual:
docker compose up -d postgres redis  # if Docker
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev  # 3005 per .env

# Step 3: Verify health
curl http://localhost:8000/health
curl http://localhost:3005/
psql -h localhost -U ipa_user -d ipa_platform -c "SELECT 1"
redis-cli PING

# Step 4: DB migrations
cd backend && alembic upgrade head
alembic current  # should output 0016_sla_cost_ledger

# Step 5: Seed defaults
psql -c "INSERT INTO tenants (id, code, display_name, state, plan, ...) VALUES (...);"
# OR via seed script if exists
python -c "from core.feature_flags import FeatureFlagsService; ..."  # seed 4 baseline flags
```

### Real API Smoke Test (Day 1 reference)

```bash
# Chat endpoint with real Azure OpenAI live
curl -N -H "Content-Type: application/json" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Authorization: Bearer $JWT" \
  -X POST http://localhost:8000/api/v1/chat \
  -d '{"messages": [{"role": "user", "content": "hello"}]}' \
  | tee chat_sse.log

# Inspect SSE events
grep -E "LLMRequested|LLMResponded|LoopCompleted" chat_sse.log

# Admin endpoints
curl -H "Authorization: Bearer $ADMIN_JWT" http://localhost:8000/api/v1/admin/tenants
curl -H "Authorization: Bearer $ADMIN_JWT" http://localhost:8000/api/v1/admin/tenants/$TENANT_ID
curl -H "Authorization: Bearer $ADMIN_JWT" "http://localhost:8000/api/v1/admin/tenants/$TENANT_ID/cost-summary?month=2026-05"
curl -H "Authorization: Bearer $ADMIN_JWT" "http://localhost:8000/api/v1/admin/tenants/$TENANT_ID/sla-report?month=2026-05"

# DB-side verification
psql -c "SELECT operation, count(*) FROM audit_log GROUP BY operation"
psql -c "SELECT cost_type, sub_type, count(*) FROM cost_ledger GROUP BY cost_type, sub_type"
```

### Frontend Browser Test (Day 2 reference)

Browser checklist per page (manual + screenshot):

| Page | URL | Action | Expected | Screenshot |
|------|-----|--------|----------|------------|
| Home | / | open | nav links visible | `01_home.png` |
| chat-v2 | /chat-v2 | send "hello" | SSE events render + response | `02_chat.png` |
| governance | /governance | view list | approvals visible | `03_governance.png` |
| verification | /verification | view panel | verification UI | `04_verification.png` |
| cost-dashboard | /cost-dashboard | select month | cost cards | `05_cost.png` |
| sla-dashboard | /sla-dashboard | select month | 6 SLA cards | `06_sla.png` |
| tenant-settings | /tenant-settings/?tenant_id=$TID | view + edit | view + form | `07_tenant_settings.png` |
| admin-tenants | /admin-tenants | filter+click | list + nav | `08_admin_tenants.png` |

Catalogue per page:
- ✅ functional fully
- ⚠️ partial (specific issue listed)
- ❌ broken (error logged)

### V2 Planning Doc Audit Pattern (Day 3 reference)

```markdown
## Doc-1: 00-v2-vision.md

**Concept summary**: V2 vision = "agent harness 11+1 範疇 重新出發",V2 ≠ SaaS-ready (Phase 56+ 才 SaaS Stage 1)

**Where in code?**:
- 11 範疇:`backend/src/agent_harness/{orchestrator_loop,tools,memory,context_mgmt,prompt_builder,output_parser,state_mgmt,error_handling,guardrails,verification,subagent}/` 12 dirs(11 + observability)
- §HITL Centralization:`backend/src/agent_harness/hitl/`
- 5-layer 架構:`backend/src/{api,business_domain,agent_harness,platform_layer,adapters,infrastructure}/`

**Wired in main flow?**:
- POST /api/v1/chat → AgentLoop.run → 12 範疇 cross-cutting? Day 1 US-2 verify

**Drift severity**: TBD (filled at Day 3 review time)

**Phase 57.6+ implication**: TBD
```

### Risk Class A/B/C — Reality Check 特殊 risks

- Risk Class A: paths-filter retired by 55.6 Option Z;此 sprint 不適用
- Risk Class B: cross-platform mypy unused-ignore — 此 sprint 不寫 source code 不適用
- Risk Class C: module-level singleton — 此 sprint 不寫 unit test 但 Day 1 真實 boot 可能 surface singleton lifecycle issue;catalogue
- **Risk Class D (NEW for Reality Check)**: Day 0 / Day 1 service boot failure 可能 immediately abort sprint — **Mitigation**:Day 0 第一件事就是 boot health check;若失敗 → 直接降為 audit cycle 模式 (純 doc audit Day 3 並 catalogue Phase 57.6+ MUST-FIX)
- **Risk Class E (NEW for Reality Check)**: Reality 比預期糟很多 → Day 4 retrospective 寫起來可能 painful;**Mitigation**:這就是 sprint 主要 deliverable + V2 紀律 #2 主流量驗證 真實 enforcement;誠實面對是工程文化價值

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 主進度 22/22 (100%) 不變;Phase 56-58 SaaS Stage 1 backend 3/3 不變;Phase 57+ Frontend SaaS 3/N 不變(此 sprint 不算 4/N — 是 reality check 性質)
- [ ] All 8 V2 lints 不變(此 sprint 0 source code change)
- [ ] Backend pytest baseline 1598 不變(此 sprint 0 new test;但 boot real services 本身就是 reality test)
- [ ] Backend mypy --strict 0 errors 不變(0 source code change)
- [ ] Backend LLM SDK leak: 0 不變
- [ ] Anti-pattern checklist:此 sprint 主要 verify AP-4 (Potemkin) + AP-9 (Verification);其他 11 條 checklist 在 Day 3 audit 觀察
- [ ] 5 active CI checks green
- [ ] Frontend `npm run lint && npm run build` clean(0 source code change)
- [ ] Frontend Vitest 35 不變(0 source code change)
- [ ] Playwright e2e 23 不變(此 sprint 不開新 Playwright;但 Day 2 manual browser test 提供 visual evidence)
- [ ] All 5 services boot up 成功(US-1)
- [ ] All 16 Alembic migrations 0001-0016 apply 成功(US-1)
- [ ] POST /api/v1/chat real SSE event stream 完整(US-2)
- [ ] All 7 frontend pages browser-tested + screenshot evidence(US-3)
- [ ] V2 planning doc 21 份 reality audit 完成(US-4)
- [ ] `v2-reality-gap-report.md` produced ≥ 5 findings(US-5)
- [ ] Phase 57.6+ direction 由 user decided(US-5)

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Branch + Pre-flight + Decide Boot Path

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 三-prong 探勘(per AD-Plan-3 + AD-Plan-4 fold-in promoted;57.5 Reality Check 不同於 feature sprint — Prong 2 + Prong 3 重點變成 verify environment)— **Prong 1 Path Verify**:`scripts/dev.py` exists / `backend/src/api/main.py` exists / `frontend/package.json` exists / `backend/src/infrastructure/db/migrations/versions/0001_*.py` to `0016_sla_cost_ledger.py` 全 16 files exist / `.env.example` exists;**Prong 2 Content Verify**:`scripts/dev.py status/start` commands available(grep `argparse` or click);`alembic.ini` exists;`docker-compose.yml` exists(check Docker stack);**Prong 3 Schema Verify**:N/A(reality check 不改 schema)
- 0.3 Calibration multiplier pre-read(`mixed` 0.60 5th application — reality check 性質;若 ratio in band → 0.60 KEEP;若 outside → reality check 工作量比預期不對 → log AD)
- 0.4 Pre-flight verify(backend pytest baseline 1598 / 8 V2 lints baseline / mypy baseline / frontend Vitest 35 + Playwright 23 + Vite build 75 modules / 209.11 kB)
- 0.5 Decide boot path(`python scripts/dev.py start` or manual;check env vars set: AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_DEPLOYMENT_NAME / DB_NAME / DB_USER / DB_PASSWORD / REDIS_HOST)
- 0.6 Day 0 progress.md commit + push;catalogue D-findings if env not ready

### Day 1 — US-1 Service Boot + DB Migrations + Seed + US-2 Backend API Smoke

- 1.1 Boot all services(`python scripts/dev.py start` or manual)
- 1.2 Verify health (curl /health / curl frontend / psql / redis-cli PING)
- 1.3 Apply Alembic migrations (`alembic upgrade head` → `alembic current` = 0016)
- 1.4 List all tables + verify expected ~30 tables present
- 1.5 Seed default tenant + admin user + 4 baseline feature flags via SQL/script
- 1.6 Backend API smoke:POST /api/v1/chat real → SSE 8 events + grep 8 fields
- 1.7 Backend admin endpoints smoke:GET tenants list / GET tenant single / GET cost-summary / GET sla-report
- 1.8 Cat 9 PII test:POST /chat with PII → SSE GuardrailTriggered captured
- 1.9 Cat 10 verification test:若 enabled → SSE VerificationPassed/Failed captured
- 1.10 DB verification:audit_log + cost_ledger entries SQL count
- 1.11 Day 1 commit + push + progress.md(catalogue D-findings;若 boot fail → mark Critical Gap)

### Day 2 — US-3 Frontend Browser Manual Test (7 Pages)

- 2.1 Open http://localhost:3005 in real browser(Chrome / Firefox / Edge)
- 2.2 Home page:capture screenshot;list nav links visible
- 2.3 chat-v2:send "hello" → see SSE events render → see response → screenshot
- 2.4 governance:see approvals list → screenshot
- 2.5 verification:see verification panel → screenshot
- 2.6 cost-dashboard:select month → see cost cards → screenshot
- 2.7 sla-dashboard:select month → see 6 SLA cards → screenshot
- 2.8 tenant-settings:?tenant_id=$TID → view + edit → screenshot
- 2.9 admin-tenants:list + filter + click row → tenant-settings → screenshot
- 2.10 Catalogue per-page result + collect Critical Gaps for any broken page
- 2.11 Day 2 commit + push + progress.md + screenshot directory commit

### Day 3 — US-4 V2 Planning Doc 21 份 Reality Audit

- 3.1 Open and read 21 V2 planning docs (~10-15 min each = ~3-5 hr)
- 3.2 For each doc:catalog Concept / Code location / Wired? / Drift severity / Phase 57.6+ implication
- 3.3 Output `v2-reality-gap-report.md` ~300-500 lines structured per doc
- 3.4 Highlight top 5 critical RED findings + top 5 YELLOW informational findings
- 3.5 Synthesis section:Phase 57.6+ candidate scope mapping (which findings → which sprint)
- 3.6 Day 3 commit + push + progress.md

### Day 4 — US-5 Closeout: Retrospective + Phase 57.6+ Direction Decision

- 4.1 retrospective.md(6 必答 + reality check sprint specific Q3 generalizable lessons + Q4 audit debt deferred to Phase 57.6+ + Q5 next steps proposal)
- 4.2 Memory snapshot `memory/project_phase57_5_v2_reality_check.md`
- 4.3 MEMORY.md index update
- 4.4 Open PR + CI green + solo-dev merge to main(此 sprint 0 source code 但 docs 大量;PR description 強調 reality check 性質)
- 4.5 Closeout PR(SITUATION-V2 §9 + CLAUDE.md sync to **Phase 57+ SaaS Frontend 4/N (Sprint 57.5 closed — V2 Reality Check & 33 deliverables verified count)** + flag 33 deliverables verified count + Phase 57.6+ direction TBD per user)
- 4.6 User decision interaction:基於 gap report top 5 critical findings → Phase 57.6+ direction 選擇

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `docs/.../sprint-57-5/{progress,retrospective}.md` | NEW | ~600 |
| `docs/.../sprint-57-5/v2-reality-gap-report.md` | NEW | **~400-600 (this is the primary deliverable)** |
| `docs/.../sprint-57-5/screenshots/{01_home,02_chat,03_governance,04_verification,05_cost,06_sla,07_tenant_settings,08_admin_tenants}.png` | NEW | 8+ binary files |
| `docs/.../sprint-57-5/seed_data.sql` (or seed script) | NEW | ~50 (default tenant + admin user + flags via FeatureFlagsService.seed_defaults call) |
| `memory/project_phase57_5_v2_reality_check.md` | NEW | ~80 |
| `MEMORY.md` | MODIFIED | +1 line index entry |
| `CLAUDE.md` | MODIFIED | sync Phase 57+ Frontend 4/N (Reality Check) |
| `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` | MODIFIED | §9 milestones row + §11 Last Updated |
| `feature-flags-admin-bundle-deferred-{plan,checklist}.md` | (already renamed Day 0;commit) | 0 (already exists) |

**Total**: 0 source LOC + 0 test LOC + ~1100 docs LOC + 8 screenshots

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ✅ `scripts/dev.py` exists per CLAUDE.md (V2 unified dev environment)
- ✅ `.env.example` exists with required env var templates
- ✅ `docker-compose.yml` if Docker stack used
- ✅ All 16 Alembic migrations 0001-0016 exist in `backend/src/infrastructure/db/migrations/versions/`
- ✅ Backend `uvicorn` entry exists at `backend/src/api/main.py`
- ✅ Frontend `package.json` + Vite config exist
- ⚠️ User has Azure OpenAI live endpoint + API key + deployment name configured (real LLM call needed for Day 1 US-2 SSE smoke);若 not → Day 1 SSE 部分降級為 verified-deferred-to-Phase-58
- ⚠️ User has PostgreSQL 16 + Redis 7 running locally(Docker stack OK);若 not → Day 0 第一件事 spin up Docker

### Risk Classes (per sprint-workflow.md §Common Risk Classes + Reality Check NEW)

**Risk Class A (paths-filter)**: 已 closed by 55.6 Option Z;不適用

**Risk Class B (mypy unused-ignore)**: 不適用此 sprint(0 source code change)

**Risk Class C (module-level singleton)**: 此 sprint 不寫 test 但 Day 1 真實 boot 可能 surface singleton lifecycle issue;若 backend boot crashes due to module-level state → catalogue 為 Critical Gap 並 fix in Phase 57.6+

**Risk Class D (NEW Reality Check)**: Day 0 / Day 1 service boot failure → mitigation:第一件事 boot health check;若 multiple services 無法 boot → 降級為 pure doc-audit mode(US-2 + US-3 deferred;US-4 + US-5 仍進行 + 將 boot failure catalogue 為 Phase 57.6+ MUST-FIX-FIRST scope)

**Risk Class E (NEW Reality Check)**: Reality 比預期糟很多 → mitigation:這就是 sprint 主要 deliverable + V2 紀律 #2 主流量驗證真實 enforcement;誠實面對 + 用 gap report 驅動 Phase 57.6+

### Day 0 三-prong 探勘 D-findings v3 (catalogued during Day 0)

**D1** TBD — pending Day 0 environment health check
**D2** TBD — pending Day 0 env vars verification
**D3** TBD — pending Day 0 Docker stack availability

(Day 0 完成後 fill in;若 0 critical D-findings → continue Day 1 normal;若 ≥ 1 critical → revise plan §Risks per AD-Plan-1 audit-trail)

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| User 沒有真實 Azure OpenAI live endpoint + API key 配置 | Day 0 verify env vars;若 not → Day 1 US-2 SSE smoke 降級為 mock(用 OpenAI compatibility mock + 標明 deferred to Phase 58 production launch);仍可 verify SSE event format 正確 |
| Backend PG/Redis 啟動失敗(Docker not running 或 port conflict) | Day 0 第一件事 verify;若 fail → Phase 57.6+ MUST-FIX-FIRST scope candidate;Sprint 57.5 仍可 do US-3 + US-4 + US-5 paper audit |
| Day 2 frontend 多 page broken → screenshot 都是 error UX | 這就是 sprint 主要 deliverable;誠實 catalogue 並驅動 Phase 57.6+ |
| Day 3 V2 planning doc 21 份 audit 比預期慢(每 doc 15-20 min × 21 = 5-7 hr) | 若超時 → 改 batch summary mode(每 doc 5 min concise);prefer breadth over depth in 1st reality audit |
| Day 4 retrospective 寫不下去因為 reality 比預期糟太多 | 這就是 sprint 價值;Q3-Q5 寫越誠實越好 |
| Sprint scope shift > 50% → abort threshold per AD-Plan-1 | 若 Day 1 即 surface 5+ Critical Gaps → 直接 sprint pivot 為 audit cycle bundle(類似 53.7 / 55.3-55.6);Day 4 reflects 這 pivot |

---

## Definition of Done

詳見 §Acceptance Criteria — Sprint-Wide。

---

## References

- User concern raised 2026-05-08(legitimate AP-4 Potemkin Feature 累積風險 + V2 紀律 #2 主流量驗證原則)
- 04-anti-patterns.md §AP-4 Potemkin Features(此 sprint 主要對齊)+ §AP-9 Verification Loops
- 10-server-side-philosophy.md §3 大原則(Day 1 US-2 真實 verify §1 server-side + §2 LLM neutrality)
- 06-phase-roadmap.md §22 sprint(Day 3 audit 對象)
- 17-cross-category-interfaces.md §single-source registry(Day 3 audit 重點)
- 13-deployment-and-devops.md §dev environment(Day 0/1 boot reference)
- CLAUDE.md §Service Startup + §Development Commands + §Sprint Execution Workflow
- .claude/rules/sprint-workflow.md §Common Risk Classes + §Step 2.5 Day-0 三-prong 探勘
- Sprint 57.4 plan + checklist (format template — 11 sections + metadata block / 5 days Day 0-4)
- `feature-flags-admin-bundle-deferred-{plan,checklist}.md` (deferred Phase 57.6+ candidate;Sprint 57.5 pivoted away from this)
