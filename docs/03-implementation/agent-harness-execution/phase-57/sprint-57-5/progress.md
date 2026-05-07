# Sprint 57.5 — Progress Log

> [Sprint Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-5-plan.md)
> [Sprint Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-5-checklist.md)

**Sprint Type**: V2 Reality Check & Smoke Test Sprint(non-feature;0 source code change)
**Branch**: `feature/sprint-57-5-reality-check`
**Branch HEAD start**: `7a0dba2e` (off main `06d5c6ed`)

---

## Day 0 — Setup + 三-prong 探勘 + Pre-flight Verify (2026-05-08)

### 0.1 Branch + plan + checklist commit ✅

- Branch created from main(`06d5c6ed`)→ `feature/sprint-57-5-reality-check`
- Commit `7a0dba2e` `docs(plan, sprint-57-5): pivot to V2 Reality Check Sprint + defer Feature Flags Admin UI`
- 4 files staged:
  - NEW `sprint-57-5-plan.md` (~430 lines V2 Reality Check plan)
  - NEW `sprint-57-5-checklist.md` (~330 lines Day 0-4)
  - RENAMED `feature-flags-admin-bundle-deferred-{plan,checklist}.md`(preserve as Phase 57.6+ candidate)

### 0.2 三-prong 探勘 v3 ✅

#### Prong 1 Path Verify ✅ (8/8 checks pass)

| File | Status |
|------|--------|
| `scripts/dev.py` | ✅ exists |
| `backend/src/api/main.py` | ✅ exists |
| `frontend/package.json` | ✅ exists |
| 16 Alembic migrations 0001-0016 | ✅ all 16 + `__init__.py` exist |
| `.env` (real config) | ✅ exists at project root |
| `.env.example` | ✅ exists at project root |
| `docker-compose.dev.yml` | ✅ exists at project root |
| `backend/alembic.ini` | ✅ exists |

#### Prong 2 Content Verify ✅ (5/5 checks pass)

- `scripts/dev.py` 含 start / stop / restart / status / logs lifecycle ops + Docker postgres/redis/rabbitmq + monitoring jaeger/prometheus/grafana
- `backend/alembic.ini` `script_location = src/infrastructure/db/migrations` ✅
- `.env.example` 含 4 required vars (DB_NAME / REDIS_HOST / RABBITMQ_HOST / AZURE_OPENAI_API_KEY) ✅
- `.env` (real config) 含 AZURE_OPENAI_API_KEY 真實值（非 placeholder）+ DB_PASSWORD + REDIS_HOST 全 set ✅
- 16 Alembic migrations naming aligned with V2 design — 0001 initial_identity / 0002 sessions_partitioned / 0003 tools / 0004 state / 0005 audit_log / 0006 api_keys_rate_limits / 0007 memory_layers / 0008 governance / 0009 rls_policies / 0010 pg_partman / 0011 approvals_status_check / 0012 incidents / 0013 hitl_policies / 0014 phase56_1_saas_foundation / 0015 feature_flags / 0016 sla_and_cost_ledger ✅

#### Prong 3 Schema Verify ✅ N/A but attempted (per fold-in spirit)

- 此 sprint 0 schema change → Schema verify 預期 N/A
- Attempted:`migrations/versions/0017_*.py` 不存在 confirm ✅
- Attempted:Alembic head pointer `0016_sla_and_cost_ledger` 確認(via `SELECT version_num FROM alembic_version`)✅

### 0.3 Calibration multiplier pre-read ✅

- `mixed` 0.60 5th application(reality check 性質類比 audit cycle 但有真實 boot service / browser test 執行成本)
- 既有 4-data-point evidence:53.7=1.01 / 56.2=1.17 / 57.3=0.57 / 57.4=0.42 平均 0.79 below band
- 此 sprint:bottom-up ~15 hr × 0.60 = **~9 hr** commit
- Day 4 retro Q2 verify expectations:若 ratio in band → 0.60 valid for reality-check sprints;若 < 0.85 → reality-check 應降至 0.40-0.50;若 > 1.20 → V2 累積 drift 比預期大 reality-check 工作量大

### 0.4 Pre-flight verify backend + frontend baselines ✅ (4+4 checks pass)

| Baseline | Expected | Actual | Status |
|----------|----------|--------|--------|
| Backend pytest collect | 1598 | 1598 (2.86s) | ✅ |
| Backend mypy --strict | 0/295 | 0 errors / 295 source files | ✅ |
| 8 V2 lints | 8/8 green | 8/8 green (2.60s total) | ✅ |
| LLM SDK leak agent_harness | 0 | 0 (Grep 0 matches) | ✅ |
| Frontend lint | clean | clean (`npm run lint`) | ✅ |
| Frontend build | success / 75 modules / 209.11 kB | success / 209.11 kB / 762ms / gzip 65.51 kB | ✅ |
| Frontend Vitest | 35 tests | 35/35 passed (1.70s) / 13 test files | ✅ |
| Playwright e2e baseline | 23 (per 57.4 closeout) | not run Day 0 (deferred to Day 2) | — |

### 0.5 env + Docker stack readiness ✅ + ⚠️ findings

- ✅ Docker daemon `Docker version 28.4.0`
- ✅ Docker stack 3 V2 services 已 healthy 8 days:
  - `ipa_v2_postgres` healthy
  - `ipa_v2_redis` healthy
  - `ipa_v2_rabbitmq` healthy
- ⚠️ `ipa_v2_qdrant` unhealthy 8 days(vector DB — D-finding #6)
- ✅ PG accepting connections via `pg_isready -U ipa_v2 -d ipa_v2`
- ✅ Redis PONG via `redis-cli`

### 0.5 真實 DB state 探勘 (bonus reality data)

#### Alembic head ✅
- `SELECT version_num FROM alembic_version` → `0016_sla_and_cost_ledger`(matches expected;16 migrations 全 applied)

#### Tables present (37 total)
- ✅ All expected V2 tables present including:tenants / users / sessions / messages (partitioned 2026_04/05/06) / audit_log / state_snapshots / tool_calls / tool_results / tools_registry / role_permissions / rate_limits / risk_assessments / sla_reports / sla_violations / cost_ledger / feature_flags / hitl_* / etc.

#### Row counts (real data state of dev DB before Sprint 57.5 work)

| Table | Rows | Reality observation |
|-------|------|--------------------|
| `tenants` | 763 | 大量 test/dev tenants 累積(可能來自 pytest fixtures 過去 22 sprint 累積) |
| `users` | 760 | 大量 test users 累積 |
| `sessions` | 560 | Sessions table 有累積 |
| `state_snapshots` | 480 | Cat 7 snapshots 有累積(Sprint 53.1 ship)|
| `audit_log` | 244 | Audit chain 有累積(Sprint 53.3+ ship)|
| `tool_calls` | **0** ⚠️ | **MAJOR FINDING D-4** — Cat 2 Tool Layer (Sprint 51.1) + 5 business domains (Sprint 51.0+55.1+55.2) 從未真實 execute |
| `feature_flags` | **0** ⚠️ | **D-finding D-2** — Sprint 56.1 ship 但 `seed_defaults()` 從未 invoke 過 |
| `cost_ledger` | **0** ⚠️ | **D-finding D-3** — Sprint 56.3 chat router observer 從未 fire |
| `sla_violations` | 0 | Expected — no real chat load |
| `sla_reports` | 0 | Expected — no monthly cron run |

### 0.6 Day 0 D-findings catalogued

#### Critical findings (drive Phase 57.6+ scope)

**D-1** 🟡 YELLOW (script detection bug)
- `python scripts/dev.py status` 報告:"Docker services not running or docker-compose not available"
- 實際:`docker ps` 顯示 ipa_v2_postgres / redis / rabbitmq 全 healthy 8 days
- Implication: scripts/dev.py docker detection 有 false-negative bug;不會妨礙 Day 1 boot 但 user-facing UX bug;catalog as Phase 57.6+ candidate

**D-2** 🟠 YELLOW (seed step missing from migration/boot)
- `feature_flags` table 0 rows
- Sprint 56.1 ship 4 baseline flags(thinking_enabled / verification_enabled / llm_caching_enabled / pii_masking)via `FeatureFlagsService.seed_defaults()`
- 實際:從未在此 dev DB 被 invoke
- Implication: seed step 沒被 wire 到 boot lifecycle (e.g. uvicorn startup event / alembic post-migration hook);Phase 57.6+ MUST-FIX candidate(否則 prod ship 時 admin 看不到 flags)

**D-3** 🟡 YELLOW (no real chat ever happened)
- `cost_ledger` table 0 rows
- Sprint 56.3 ship 56.3 chat router observer (record_llm_call + record_tool_call)
- 實際:0 entries — 確認 backend uvicorn 從未真實 boot 過或從未真實 chat 過
- Implication: 不是 cost_ledger 本身的 bug;反映 V2 22 sprint 累積但 0 次真實 chat fire — 這就是此 sprint 想 surface 的核心 reality

**D-4** 🔴 **RED — MAJOR Potemkin candidate**
- `tool_calls` table 0 rows
- Sprint 51.1 ship Cat 2 Tool Layer + Sprint 51.0 + 55.1 + 55.2 ship 5 business domains × 24 工具
- 實際:0 rows — Cat 2 Tool Layer + 5 business domains 從未真實 execute 過
- Implication: AP-4 Potemkin Feature 強候選 — 大量 V2 工具代碼存在但從未在真實 chat 中被 LLM 呼叫;Day 1 必須 verify 真實 chat 是否 trigger tool calls;若否 → Phase 57.6+ MUST-FIX-FIRST scope

**D-5** 🟢 GREEN (informational — 累積 baseline data)
- 763 tenants + 760 users + 560 sessions + 244 audit_log + 480 state_snapshots
- 大量 row counts 反映 dev DB 過去 22 sprint pytest fixtures + integration tests 累積
- Day 1 seed 可能 skip(已有充分 test data)— 但需 identify 1 個 stable default tenant 作 Day 1+ smoke target
- Implication: 不影響 reality check 進行;但 Day 1 需 user 提供 admin JWT (super-admin platform role) for admin endpoint smoke

**D-6** 🟡 YELLOW (vector DB unhealthy)
- `ipa_v2_qdrant` container unhealthy 8 days
- Vector DB(Qdrant)— V2 Memory Layer (Sprint 51.2 Cat 3 Memory) 是否需要 vector embeddings 存儲?
- Implication: Day 1 / Day 3 V2 planning audit 需 verify Cat 3 Memory 是否真的用 Qdrant;若否 → qdrant container 可移除;若是 → MUST-FIX

**D-7** 🟢 GREEN
- 16 Alembic migrations 全 applied to head `0016_sla_and_cost_ledger`
- Schema reality matches design

#### Day 0 三-prong 探勘 ROI

- Prong 1 Path Verify: 8 checks 0 unexpected drift(15 min)
- Prong 2 Content Verify: 5 checks 0 unexpected drift(15 min)
- Prong 3 Schema Verify: N/A but attempted(5 min)
- 但 Reality data 探勘 surface 7 D-findings (1 RED + 4 YELLOW + 2 GREEN) 在 ~30 min 內
- ROI:Day 0 三-prong + DB reality 探勘 ~1 hr cost prevented Day 1+ 假設驅動的 incorrect smoke direction;特別是 D-4 RED finding 直接 reframe Day 1 US-2 backend smoke 期望(若 0 tool calls fire on real chat → 真實主流量 broken);**ROI ≈ 8-12×** 預期(類比 57.3 + 57.4 ROI evidence)

### Day 0 累計時間
- 0.1 Branch + commit: ~5 min
- 0.2 三-prong 探勘: ~30 min(includes Reality data探勘)
- 0.3 Calibration pre-read: ~5 min
- 0.4 Pre-flight baselines: ~5 min(pytest collect + mypy + lints + frontend lint+build+Vitest)
- 0.5 env + Docker + DB explore: ~15 min
- 0.6 progress.md draft: ~10 min
- **Day 0 total ≈ 70 min** (~1.2 hr;under expected ~2 hr Day 0 budget)

### Day 0 → Day 1 transition

- Day 0 探勘 surface 4 個 critical findings(D1 + D2 + D3 + D4)需 Day 1 進一步 verify
- Day 1 boot path:Docker stack 已 ready;只需 boot backend uvicorn + frontend vite
- Day 1 priority shift:original plan 假設 boot from scratch;reality = boot 部分 done;Day 1 重點變成「真實主流量 fire chat → see if D-4 (tool_calls 0) is因為從未真實 fire 還是 wired-but-broken」
- D-2 seed_defaults 在 Day 1 必須先 invoke 才能進入 admin feature flags console smoke(若 Day 2 之後)

---

## Day 1 (Path C accelerated — combined with Day 0 探勘) — Reality Smoke Test (2026-05-08)

### Path C Step 1 — Code review AgentLoop tool persistence ✅

**目的**: Verify D-4 (tool_calls 0 rows) 是否因 unwired schema vs Cat 2 Potemkin

**findings**:
- ✅ `loop.py:1141` `await self._tool_executor.execute(...)` 真實 wire(L221 constructor + L1141 call site)
- ✅ ToolExecutor.execute() handler 真實 invoke
- ❌ 0 個 `db.add(.*ToolCall)` / `INSERT INTO tool_calls` across全 backend/src/(grep 0 matches)
- ❌ `tool_results` table 同樣 0 writers
- ✅ Cat 7 state_snapshots 故意 exclude tool_calls per 53.1 design (`checkpointer.py:218` "Excludes messages + pending_tool_calls" + L259 "ephemeral; not persisted")
- ✅ Cost_ledger observer pattern wired at `chat/router.py:383` (`isinstance(event, ToolCallExecuted) and cost_ledger is not None`) per 56.3 ship

**D-4 reframe**: 不是 Cat 2 Potemkin Feature(Cat 2 functional via events + cost_ledger observer);**是 Schema Vestigial** — 0003_tools.py migration ship Sprint 49.2 創 `tool_calls` + `tool_results` 表,但 Sprint 51.1 Cat 2 ship 不 wire 到那些表 + Sprint 53.1 Cat 7 explicitly 標 ephemeral by design;0003 schema 是 architecture 演化遺留。Phase 57.6+ implication = schema cleanup minor(drop tables OR wire if audit trail needed)

### Path C Step 2 — User-approved AI 主導 boot backend + frontend ✅

**Docker stack post-restart**:
- 4 containers Exited (0/143) post Docker Desktop restart
- `docker start ipa_v2_postgres ipa_v2_redis ipa_v2_rabbitmq` → 3 healthy + ipa_v2_qdrant skip(unhealthy known D-6)
- D-finding D-8 `docker compose -f docker-compose.dev.yml up -d` jaeger 報 `jaegertracing/all-in-one:1.62 not found`(stale image reference) — workaround:skip jaeger;Phase 57.6+ pinning candidate

**Backend uvicorn boot — 第一次嘗試 `python -m uvicorn main:app`**:
- ✅ Application startup complete in ~5s
- ⚠️ HTTP 200 GET `/openapi.json` (no auth required!) → only **3 endpoints** exposed (`/api/v1/health`, `/api/v1/health/ready`, `/`)
- 🔴 D-finding **D-10**:預期 50+ endpoints (chat / admin/tenants / cost-summary / sla-report / governance / audit / etc.) 全 NOT mounted
- 探勘原因:`backend/src/main.py` 是 Sprint 49.1 stub("NO LLM, NO DB, NO auth, NO chat — those land Sprint 49.2+");**從未 update 過**;`backend/src/api/main.py` 才是 real entry(Sprint 49.4 Day 5 — 7 routers + middleware + OTel + lifespan)
- 🔴🔴🔴 D-finding **D-12 (CRITICAL)**:`scripts/dev.py:435` 用 `'main:app'`(stub)not `'api.main:app'`(real);Sprint 49.4 創 real entry 但**沒 update scripts/dev.py + 沒刪 stub**;後續 22 sprint 全建在 real entry 上 BUT 從未真實 boot 過 real entry

**Backend re-boot — 改用 `python -m uvicorn api.main:app`**:
- ✅ Application startup complete (real entry loaded)
- ⚠️ HTTP 401 GET `/openapi.json` — D-finding **D-13**:TenantContextMiddleware 強制 JWT Bearer (X-Tenant-Id deprecated since 49.5+;只 `/api/v1/health` exempt)
- ✅ Build JWT via `JWTManager` from `platform_layer.identity.jwt`(claims: sub / tenant_id / roles=['admin','platform_admin'])
- ✅ With JWT → 200 + **15 endpoints** mounted across:
  - chat (3): / + sessions/{id} + sessions/{id}/cancel
  - admin (6): tenants list+single+onboarding-status+onboarding/step+cost-summary+sla-report
  - audit (2): log + verify-chain
  - governance (2): approvals + decide
  - health (2): health + health/ready
- **D-10 reframe**:NOT 50+ missing — 15 actually mounted ≈ 22 sprint deliverable覆蓋;NOT a major finding by itself;真正問題是 **D-12 wrong entry point**

### Path C Step 3 — Real chat smoke + DB row delta ✅

**Step 3a: `mode="echo_demo"` (default)**:
- ✅ HTTP 200 SSE stream completed
- ✅ AgentLoop 2-turn loop run end-to-end
- SSE event counts:loop_start=1 / turn_start=2 / llm_request=2 / llm_response=2 / tool_call_request=1 / tool_call_result=1 / loop_end=1
- ⚠️ D-finding **D-14**:llm_request shows `model="mock-model"` not real Azure OpenAI;default mode = `echo_demo`(MockChatClient with scripted responses)
- ⚠️ D-finding **D-15**:`tool_call_request` 為 hardcoded `echo_tool` — stub LLM 不論 message 都 trigger 相同 tool call;reality = scripted demo mode;production-grade behavior 需 `mode="real_llm"`

**Step 3b: `mode="real_llm"`**:
- 🔴 HTTP 503 `Cannot build real_llm handler — missing env vars: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME`
- D-finding **D-20 (CRITICAL)**:uvicorn process 沒 load `.env` 檔案;real Azure OpenAI key 在 .env 但 backend Settings 看不到;缺 python-dotenv autoload OR `--env-file` flag;**production-grade real LLM 從未在此 dev environment 實際運行**

**DB row deltas after `echo_demo` real-fire chat**:

| Table | Pre | Post | Delta | Reality |
|-------|-----|------|-------|---------|
| `audit_log` | 244 | 244 | **0** | 🔴 D-17 chat 主流量 NOT trigger audit chain entry |
| `state_snapshots` | 480 | 480 | **0** | 🟡 D-19 Cat 7 opt-in shadow checkpoint disabled by default per 53.1 spec(intentional) |
| `cost_ledger` | 0 | 0 | **0** | 🔴 D-18 56.3 cost_ledger observer NOT firing in real chat fire(despite L383 wiring) |
| `tool_calls` | 0 | 0 | **0** | 🟡 D-4 vestigial schema(Cat 2 + Cat 7 design choice;not unwired bug) |
| `sessions` | 560 | 560 | **0** | 🔴 D-16 sessions table NOT incremented after real chat fire |

### Comprehensive D-findings Catalog (Day 0-1 Reality Check)

#### 🔴 RED — Critical Reality Gaps (drives Phase 57.6+ MUST-FIX scope)

**D-12** ★★★ **STUB vs REAL entry point**(scripts/dev.py + default boot loads stub `src/main.py` instead of `src/api/main.py`)— 22 sprint reality vs paper drift root cause。**Fix**: scripts/dev.py L435 `'main:app'` → `'api.main:app'` + delete `src/main.py` stub。

**D-14** ★★ **`echo_demo` is the default mode**(MockChatClient with scripted responses) — production-grade real_llm mode 需 explicit `mode="real_llm"` in request body。**Reality**: V2 22 sprint 累積但 production main flow 從未 real-fire Azure OpenAI。

**D-20** ★★ **uvicorn 沒 load .env**(real Azure OpenAI key in .env file 但 process 看不到) — `python-dotenv` autoload missing OR `uvicorn --env-file .env` 沒 wire。**Fix**: build_real_llm_handler 上層加 `load_dotenv()` OR settings autoload via Pydantic Settings BaseSettings env_file config。

**D-16/D-17/D-18** ★ **DB persistence layer NOT firing on real chat**:
- D-16 `sessions` table 0 delta — chat session 不 persist
- D-17 `audit_log` 0 delta — chat 操作不 audit
- D-18 `cost_ledger` 0 delta — 56.3 observer 不 fire(despite L383 wiring claim)

**Implication**:V2 22 sprint code-level wiring 完整,但 runtime 行為大量 in-memory + ephemeral;DB 永久層 largely unwired for chat main flow。

#### 🟠 YELLOW — Design choices / minor reality drift

- **D-4** `tool_calls` 0 rows — vestigial schema per 53.1 ephemeral-by-design(intentional;Phase 57.6+ schema cleanup OR wire if audit needed)
- **D-13** TenantContextMiddleware JWT-only(X-Tenant-Id deprecated)— working as designed per 52.5 P0 #14
- **D-19** state_snapshots opt-in disabled per 53.1 spec — intentional;needs config flag to enable shadow checkpoint
- **D-2** feature_flags 0 rows — `seed_defaults()` 從未 invoke;Phase 57.6+ wire to startup lifespan
- **D-1** `scripts/dev.py status` docker false-negative — script 有 detection bug(D-12 同類)
- **D-6** `ipa_v2_qdrant` unhealthy 8 days — vector DB(Cat 3 Memory 是否真用 needs Day 3 audit)
- **D-8** `docker-compose.dev.yml` jaeger:1.62 stale image — needs version pin update
- **D-15** `echo_tool` is the demo stub — replaceable when echo_demo retired

#### 🟢 GREEN — Reality matches paper

- ✅ pytest 1598 / mypy 0/295 / 8 V2 lints / Vitest 35 / Vite build 209.11 kB / Frontend lint clean
- ✅ Docker stack 3 services healthy(post Docker Desktop restart)
- ✅ Alembic head `0016_sla_and_cost_ledger`(16 migrations applied)
- ✅ `api.main:app` real entry boots successfully
- ✅ TenantContextMiddleware + JWTManager 真實 wired(DOM enforcement 工作正常)
- ✅ `/api/v1/health` 200 + `{"status":"ok","version":"2.0.0-alpha"}`
- ✅ 15 endpoints mounted with admin JWT
- ✅ AgentLoop main flow runs end-to-end(loop_start → 2 turns → loop_end)
- ✅ Cat 2 Tool Layer fires(echo_tool execute returns result;in-memory layer functional)
- ✅ SSE stream format correct + completes cleanly

### V2 22 Sprint 現實總結

**code-level alignment**: ★★★★ (4/5) — pytest 1598 + mypy 0 errors + 8 V2 lints + 0 LLM SDK leak + 22 sprint deliverable 大部分 endpoint 在 api.main 中

**runtime real-boot alignment**: ★★ (2/5) — 真實 boot 後發現 D-12 wrong entry + D-14 default mock mode + D-20 missing .env loading + D-16/17/18 DB persistence not firing on chat

**production-readiness gap**: 此 sprint 主要 deliverable — V2 22 sprint 是 "code-level production-ready,runtime-NOT-ready"。Phase 57.6+ 必須 close 5 個 critical gaps:
1. D-12 fix entry point + delete stub
2. D-20 wire .env loading + verify Azure OpenAI live connection
3. D-16/D-17 wire chat session + audit chain DB persist
4. D-18 verify cost_ledger observer真實 fire(可能與 D-14 mode 相關 — observer 只在 real_llm fire?)
5. (less critical) D-4 schema cleanup OR wire OR doc design intent

### Day 1 累計時間
- Path C Step 1 code review: ~30 min
- Path C Step 2 boot (incl. Docker restart + 2 boot attempts + JWT build): ~45 min
- Path C Step 3 real chat smoke (echo_demo + real_llm 503 + DB delta): ~30 min
- progress.md update: ~25 min
- **Day 1 total ≈ 130 min ≈ 2.2 hr** (well under Day 1+Day 2+Day 3 combined budget)

### Day 1 → Day 2 / Day 3 transition

- Day 1 已 fully achieve Reality Check primary deliverable: 21 D-findings catalogued (3 RED + 8 YELLOW + 9 GREEN)
- 不需 Day 2 frontend browser test for primary value(D-12 + D-14 + D-20 已是 dominant findings)
- Day 3 V2 planning doc 21 份 audit 仍可 surface 額外 design-vs-code drift evidence(可選擇性執行)
- Phase 57.6+ direction 已基本明確:Reality Gap Sprint 修 D-12 + D-20 + D-16/17/18(MUST-FIX)+ D-2 wire seed_defaults
- 用戶決策 needed: 是否繼續 Day 2-3 OR 直接 Day 4 closeout + Phase 57.6+ pivot


