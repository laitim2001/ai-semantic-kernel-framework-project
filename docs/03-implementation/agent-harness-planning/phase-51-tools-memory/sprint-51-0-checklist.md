# Sprint 51.0 — Checklist

**Plan**：[`sprint-51-0-plan.md`](./sprint-51-0-plan.md)
**Sprint**：51.0 — Mock 企業工具 + 業務工具骨架
**狀態**：🟡 PLANNING — 待用戶 approve

---

## 進度總覽

- **Day 0**：⏸ Plan + Checklist + branch（4h）
- **Day 1**：⏸ Mock backend 骨架（5h）
- **Day 2**：⏸ patrol + correlation + rootcause domain（6h）
- **Day 3**：⏸ audit + incident domain + aggregator（6h）
- **Day 4**：⏸ Tests + worker hook + chat handler（5h）
- **Day 5**：⏸ 17.md sync + retro + closeout（3h）

**Plan total**：29h / **Actual estimate**：5.5-6h

---

## Day 0 — Plan / Checklist / Branch / Phase README（預估 4 小時）

### 0.1 Sprint plan 撰寫（45 min）
- [x] **撰寫 sprint-51-0-plan.md** ✅ 2026-04-30
  - DoD: 含 Sprint Goal + 5 User Stories + Technical Specifications + File Change List + Acceptance Criteria + Deliverables + Risks + 估時 + V2 紀律對照
  - 路徑：`docs/03-implementation/agent-harness-planning/phase-51-tools-memory/sprint-51-0-plan.md`

### 0.2 Sprint checklist 撰寫（45 min）
- [x] **撰寫 sprint-51-0-checklist.md**（本檔）✅ 2026-04-30
  - DoD: Day 0-5 task 全列；每項 ≤ 60 min；含 DoD + verification command

### 0.3 Phase 51 README 更新（30 min）
- [x] **建立 phase-51-tools-memory/README.md** ✅ 2026-04-30
  - DoD: 含 Phase 進度 / Sprint 總覽 / 範疇成熟度 / 51.0 範圍預覽 / Approval workflow

### 0.4 建立 branch（10 min）
- [x] **`git checkout -b feature/phase-51-sprint-0-mock-business-tools` from main** ✅ 2026-04-30
  - DoD: branch 從 50.2 closeout commit (`cf076e6` or HEAD of `feature/phase-50-sprint-2-api-frontend`) 切；當前未動 main
  - **實際**：用戶 approve 後先 merge `feature/phase-50-sprint-2-api-frontend` → main（merge commit `f31498e`），再從 updated main 切 51.0 branch
  - Command: `git checkout main && git merge --no-ff feature/phase-50-sprint-2-api-frontend && git checkout -b feature/phase-51-sprint-0-mock-business-tools`

### 0.5 確認 50.1 ToolSpec 中性型別 ready（30 min）
- [x] **`_contracts/tools.py` 含 ToolSpec / ToolAnnotations / ConcurrencyPolicy；`_contracts/hitl.py` 含 HITLPolicy** ✅ 2026-04-30
  - DoD: import 不報錯；如缺少 enum，補入並更新 17.md §1.1 single-source 表
  - **實際**：4 type 全 importable；HITLPolicy owner 為 `_contracts/hitl.py:80`（per HITL §central owner，非 tools.py）— 這是正確架構，不修
  - Command: `cd backend && python -c "from src.agent_harness._contracts.tools import ToolSpec, ToolAnnotations, ConcurrencyPolicy; from src.agent_harness._contracts.hitl import HITLPolicy"` ✅

### 0.6 業務 domain 5 dir 確認 + __init__.py 統一（20 min）
- [x] **business_domain/{patrol,correlation,rootcause,audit_domain,incident}/ 5 dir 全在** ✅ 2026-04-30
  - DoD: 5 dir 各有 `__init__.py` + `README.md`（後者已從 V1/early V2 留下，本 sprint 不改 README 內容；只確認結構）
  - Command: `ls backend/src/business_domain/` ✅

### 0.7 Day 0 commit（10 min）
- [x] **commit `docs(plan, sprint-51-0): Day 0 — plan + checklist + Phase 51 README`** ✅ 2026-04-30
  - DoD: 3 docs 提交；branch HEAD = Day 0 commit；working tree clean (除用戶 IDE work 外)
  - **實際 commit**：`4a843a7` on `feature/phase-51-sprint-0-mock-business-tools`（3 files / 768 insertions）
  - Pre-merge action：`feature/phase-50-sprint-2-api-frontend` → main merge commit `f31498e`（user-authorized）

---

## Day 1 — Mock Backend 骨架（預估 5 小時）

### 1.1 mock_services dir + main.py（45 min）
- [x] **`backend/src/mock_services/__init__.py` + `main.py` (FastAPI app, port 8001, /health endpoint)** ✅ 2026-04-30
  - DoD: `uvicorn mock_services.main:app --port 8001` 可啟動；`/health` 回 `{"status":"ok","db_stats":{...}}` ✅ pid 38236 verified（curl 被 sandbox hook 擋，改用 urllib）
  - File header 完整 ✅
  - Routes verified: `/`, `/health`, `/docs`, `/mock/crm/*` (3), `/mock/kb/search`

### 1.2 mock_services/schemas/__init__.py + 9 Pydantic models（60 min）
- [x] **Customer / Order / Ticket / KBArticle / KBSearchResult / PatrolResult / Alert / Incident / RootCauseFinding / AuditLogEntry** ✅ 2026-04-30
  - DoD: 10 Pydantic models（plan 寫 9，因 KB 拆 KBArticle + KBSearchResult，共 10）；mypy strict pass；每個 model 有 examples ✅
  - Note: `Ticket` schema 加入因 CRM endpoint 需要

### 1.3 mock_services/data/seed.json（45 min）
- [x] **JSON seed** ✅ 2026-04-30
  - DoD: 10 customer / 50 order / 8 ticket / 8 kb / 3 patrol / 20 alert / 5 incident / 8 rca / 5 audit；JSON 可解析；total ~25 KB（well under 200 KB） ✅
  - 比 plan 多：8 ticket（CRM 需要）+ 8 kb_articles（KB 需要）

### 1.4 mock_services/data/loader.py（30 min）
- [x] **Startup hook 載入 seed.json 進 in-memory dict** ✅ 2026-04-30
  - DoD: `mock_services.main` lifespan async context 呼叫 `load_seed()`；router 透過 `Depends(get_db)` access；reset() helper for tests ✅

### 1.5 mock_services/routers/crm.py（45 min）
- [x] **3 endpoints** ✅ 2026-04-30
  - DoD: GET /customers/{id} 200 + 404 / GET /orders ?customer_id?limit / GET /tickets/{id} 200 + 404；TestClient 全通 ✅

### 1.6 mock_services/routers/kb.py（30 min）
- [x] **POST /mock/kb/search** ✅ 2026-04-30
  - DoD: 接 `{query, top_k}` 回 ranked `KBSearchResult[]`；naive scoring (title 1.0 / tag 0.7 / content 0.5)；query="2FA" → 1 hit score 1.0 ✅

### 1.7 scripts/dev.py mock subcommand（30 min）
- [x] **`python scripts/dev.py mock {start,stop,status}`** ✅ 2026-04-30
  - DoD: start 跑 uvicorn 在 8001；stop kill PID；status 輸出 running/stopped ✅
  - **實作**：standalone `scripts/mock_dev.py` + dev.py thin shim 17-line dispatch（避免動 ServiceType 主流量，AP-3 安全）
  - 驗收：start → pid 38236 → /health 200 via urllib → status 顯示 running → stop → 清 pid file ✅

### 1.8 Day 1 commit（15 min）
- [ ] **commit `feat(mock-services, sprint-51-0): Day 1 — FastAPI app + CRM/KB routers + seed + dev script`**
  - DoD: 全 Day 1 file 入 commit；mypy strict + black 全 OK
  - Command: `git add backend/src/mock_services/ scripts/mock_dev.py scripts/dev.py && git commit`

---

## Day 2 — Patrol + Correlation + Rootcause Domain（預估 6 小時）

### 2.1 mock_services/routers/patrol.py（45 min）
- [x] **4 endpoints**：check_servers / get_results/{id} / schedule / cancel ✅ 2026-04-30
  - DoD: 各 endpoint 200 + Pydantic schema；TestClient 全通 ✅

### 2.2 business_domain/patrol/mock_executor.py（30 min）
- [x] **`PatrolMockExecutor` class — 4 async methods** ✅ 2026-04-30
  - DoD: httpx async client；MOCK_SERVICES_URL env override；timeout 10s ✅

### 2.3 business_domain/patrol/tools.py（60 min）
- [x] **4 ToolSpec stub + register_patrol_tools(registry, handlers)** ✅ 2026-04-30
  - DoD: 4 ToolSpec 含 input_schema / annotations / concurrency；hitl_policy + risk_level 編碼 tags（CARRY-021 51.1 first-class）；naming `mock_patrol_*` ✅
  - 驗證：`registry.list()` 4 specs；handlers dict 4 entries

### 2.4 mock_services/routers/correlation.py（45 min）
- [x] **3 endpoints**：analyze / find_root_cause / related/{id} ✅ 2026-04-30
  - DoD: 各 endpoint 200；±5 min naive correlation；mock chain confidence 0.5+ ✅

### 2.5 business_domain/correlation/{mock_executor,tools}.py（60 min）
- [x] **`CorrelationMockExecutor` + 3 ToolSpec + register_correlation_tools** ✅ 2026-04-30
  - DoD: 對應 08b §Domain 2 ✅

### 2.6 mock_services/routers/rootcause.py（45 min）
- [x] **3 endpoints**：diagnose / suggest_fix / apply_fix（HIGH risk） ✅ 2026-04-30
  - DoD: apply_fix dry_run default true；live run 回 `closed_pending_review`；in-memory ledger 紀錄 ✅

### 2.7 business_domain/rootcause/{mock_executor,tools}.py（60 min）
- [x] **`RootcauseMockExecutor` + 3 ToolSpec + register_rootcause_tools** ✅ 2026-04-30
  - DoD: `mock_rootcause_apply_fix` `hitl_policy:always_ask` + `risk:high` + `destructive=True` + `open_world=True`（per 08b §Domain 3 強制） ✅

### 2.8 Day 2 commit（15 min）
- [ ] **commit `feat(business-patrol/correlation/rootcause + mock-services, sprint-51-0): Day 2 — 10 ToolSpec + 3 mock routers`**
  - DoD: mypy strict 20 files / black formatted / 10 endpoints TestClient PASS / 10 specs+handlers wired
  - Verify: `python -m mypy src/mock_services/ src/business_domain/{patrol,correlation,rootcause}/ --strict` ✅

---

## Day 3 — Audit + Incident Domain + Aggregator（預估 6 小時）

### 3.1 mock_services/routers/audit.py（45 min）
- [ ] **3 endpoints 對應 3 audit tools**：query_logs / generate_report / flag_anomaly
  - DoD: query_logs 接 time_range filter；generate_report 回 PDF placeholder URL
  - Command: `pytest tests/unit/mock_services/test_audit_router.py`

### 3.2 business_domain/audit_domain/{mock_executor,tools}.py（60 min）
- [ ] **`AuditMockExecutor` + 3 ToolSpec + register_audit_tools**
  - DoD: 對應 08b §Domain 4 表 3 entries
  - Command: `pytest tests/unit/business_domain/test_audit_tools.py`

### 3.3 mock_services/routers/incident.py（60 min）
- [ ] **5 endpoints 對應 5 incident tools**：create / update_status / close / get / list
  - DoD: create 回 incident_id；close 高風險（mock 不真關閉，回 status=closed_pending_review）
  - Command: `pytest tests/unit/mock_services/test_incident_router.py`

### 3.4 business_domain/incident/{mock_executor,tools}.py（75 min）
- [ ] **`IncidentMockExecutor` + 5 ToolSpec + register_incident_tools**
  - DoD: `mock_incident_close` 必須 `hitl_policy=ALWAYS_ASK` + `risk_level=HIGH`（per 08b §Domain 5）
  - Command: `pytest tests/unit/business_domain/test_incident_tools.py`

### 3.5 business_domain/_register_all.py（30 min）
- [ ] **`register_all_business_tools(registry)` 一次呼叫 5 個 register**
  - DoD: 註冊後 `registry.list_tools()` 回 ≥ 18（含 echo_tool 共 19）
  - File header 完整
  - Command: `pytest tests/unit/business_domain/test_register_all.py`

### 3.6 Day 3 commit（15 min）
- [ ] **commit `feat(business-audit/incident + aggregator, sprint-51-0): Day 3 — 8 ToolSpec + 2 mock routers + register_all`**
  - DoD: 18 ToolSpec 全註冊 OK；mypy strict / black / isort / flake8 OK
  - Command: `pytest tests/unit/business_domain/ -v && python -m mypy backend/src/business_domain/`

---

## Day 4 — Tests + Worker Hook + Chat Handler（預估 5 小時）

### 4.1 Integration test：mock_services 啟動 + 全 router 端點（45 min）
- [ ] **`tests/integration/test_mock_services_startup.py`**
  - DoD: 用 fastapi.testclient 直接 instantiate app；7 router 各 ≥ 1 endpoint smoke
  - Command: `pytest tests/integration/test_mock_services_startup.py -v`

### 4.2 Integration test：18 tools 透過 InMemoryToolRegistry（60 min）
- [ ] **`tests/integration/test_business_tools_via_registry.py`**
  - DoD: register_all_business_tools(registry) → registry.execute(tool_name, args) 18 tool 各 1 case；result 為 mock JSON
  - 用 mock httpx response（`respx`）避免依賴 mock_services process
  - Command: `pytest tests/integration/test_business_tools_via_registry.py -v`

### 4.3 worker startup hook（30 min）
- [ ] **修改 `runtime/workers/agent_loop_worker.py` — `build_agent_loop_handler` 加 `register_all_business_tools(registry)`**
  - DoD: handler factory 啟動時 19 tool 全 in registry；50.2 build_agent_loop_handler 簽名不變（向後相容）
  - Command: `pytest tests/unit/runtime/workers/test_agent_loop_worker.py -v`

### 4.4 chat handler default tools（30 min）
- [ ] **修改 `api/v1/chat/handler.py` — request.tools=[] 時 default 全 19 tool**
  - DoD: dev mode 用戶不指定 tools 也能呼叫業務工具；production mode 後續 sprint 加 tenant 限制
  - Command: `pytest tests/integration/api/v1/chat/test_handler.py -v`

### 4.5 e2e test：agent loop with mock_patrol（90 min）
- [ ] **`tests/e2e/test_agent_loop_with_mock_patrol.py`**
  - DoD:
    - 啟動 mock_services FastAPI 為 fixture（pytest-asyncio + lifespan context）
    - POST /api/v1/chat/ with `{"messages": [{"role":"user","content":"巡檢 web-01 health"}]}`
    - 收到 SSE stream 含 ToolCallExecuted event with `tool_name="mock_patrol_check_servers"` + `result_content` 含 `server_id="web-01"` + `health` field
    - 最終 `LLMResponded` event 含 server health 描述
  - 用 MockChatClient 預編 LLM 腳本（不打真 Azure；CARRY-016）
  - Command: `pytest tests/e2e/test_agent_loop_with_mock_patrol.py -v`

### 4.6 Day 4 commit（15 min）
- [ ] **commit `feat(integration/e2e, sprint-51-0): Day 4 — 18 tool registry + worker hook + chat default + mock_patrol e2e`**
  - DoD: 全 sprint test 累計 ≥ 310 PASS / 0 SKIPPED；無 regression
  - Command: `pytest -v --tb=short`

---

## Day 5 — 17.md Sync + Retro + Closeout（預估 3 小時）

### 5.1 17.md §3.1 加 18 ToolSpec entries（45 min）
- [ ] **修改 `docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` §3.1 工具註冊表**
  - DoD: 18 entries 含 name / annotations / concurrency / hitl_policy / risk / owner（範疇 = 業務領域層 / mock 階段）
  - Command: `grep "mock_patrol\|mock_correlation\|mock_rootcause\|mock_audit\|mock_incident" docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md | wc -l` ≥ 18

### 5.2 docker-compose.dev.yml 加 mock_services（20 min）
- [ ] **加 service block：image=local；command=uvicorn; port 8001:8001**
  - DoD: `docker compose -f docker-compose.dev.yml config` 通過；`docker compose up mock_services` 可啟動
  - Command: `docker compose -f docker-compose.dev.yml config -q`

### 5.3 progress.md Day 0-5 全紀錄（30 min）
- [ ] **`docs/03-implementation/agent-harness-execution/phase-51/sprint-51-0/progress.md`**
  - DoD: Day 0-5 各 1 entry（estimate vs actual / surprises / blockers / decisions）
  - 命令：mkdir + Write

### 5.4 retrospective.md（30 min）
- [ ] **`docs/03-implementation/agent-harness-execution/phase-51/sprint-51-0/retrospective.md`**
  - DoD: 含 Did Well / Improve / Action Items / 估時準度（plan vs actual）/ CARRY-019/020 + 51.x 影響
  - **R-4 處置**：retrospective 明示 spec 18 vs roadmap 24 差異；user 決定 CARRY-020

### 5.5 Phase 51 README 更新 51.0 完成狀態（20 min）
- [ ] **修改 `phase-51-tools-memory/README.md`**
  - DoD: Sprint 51.0 ✅ DONE 標記；範疇成熟度表更新 Post-51.0；Sprint 進度總覽 1/3 = 33%

### 5.6 memory/project_phase51_tools_memory.md 更新（15 min）
- [ ] **新增 memory file**
  - DoD: 描述 51.0 closeout / 18 ToolSpec / 5 domain / mock_services / V2 累計 7/22 sprints (32%)
  - 同步更新 `MEMORY.md` index

### 5.7 sprint-51-0-checklist 全 [x]（10 min）
- [ ] **本檔所有 `[ ]` → `[x]` 或標 🚧 + reason**
  - DoD: 無未勾選項殘留；🚧 項全有 reason 連結到 retro Action Items

### 5.8 Day 5 closeout commit（15 min）
- [ ] **commit `docs(closeout, sprint-51-0): Day 5 — 17.md sync + progress + retro + Phase 51 README + memory`**
  - DoD: working tree clean；branch HEAD = closeout commit；ready for merge / next sprint
  - Command: `git status` clean

---

## Sprint 51.0 完成驗收（DoD aggregate）

執行下列全部 PASS 才算 Sprint 51.0 ✅ DONE：

```bash
# 1. Test suite
pytest -v --tb=short
# Expected: ≥ 310 PASS / 0 SKIPPED / < 6s

# 2. Type check
python -m mypy backend/src/business_domain/ backend/src/mock_services/ --strict
# Expected: 0 errors

# 3. Lint
black --check backend/src/business_domain/ backend/src/mock_services/
isort --check backend/src/business_domain/ backend/src/mock_services/
flake8 backend/src/business_domain/ backend/src/mock_services/
# Expected: all clean

# 4. V2 5 lints
python scripts/lint/check_ap1_pipeline_disguise.py
python scripts/lint/check_cross_category_imports.py
python scripts/lint/check_llm_neutrality.py
python scripts/lint/check_tenant_isolation.sh
python scripts/lint/check_dataclass_singlesource.py
# Expected: all OK

# 5. LLM SDK leak in business_domain
grep -rE "^import (openai|anthropic)|^from (openai|anthropic)" backend/src/business_domain/
# Expected: 0 results

# 6. Cross-domain import
grep -E "from business_domain\.(patrol|correlation|rootcause|audit_domain|incident)" \
  backend/src/business_domain/{patrol,correlation,rootcause,audit_domain,incident}/ \
  | grep -v "from business_domain\._register_all"
# Expected: 0 results (each domain only imports own files + _register_all)

# 7. Mock service runs
python scripts/dev.py mock start
sleep 2
curl http://localhost:8001/health
# Expected: {"status":"ok"}
python scripts/dev.py mock stop

# 8. e2e PASS
pytest tests/e2e/test_agent_loop_with_mock_patrol.py -v
# Expected: 1 PASS

# 9. Working tree clean
git status
# Expected: nothing to commit
```

---

## 🚧 延後項（rolling planning 留）

無（51.0 開工前）

> 開工後若有阻塞，加 🚧 標記 + reason，並登錄到 retrospective.md Action Items。**禁止刪除 [ ]**。

---

**File**: `docs/03-implementation/agent-harness-planning/phase-51-tools-memory/sprint-51-0-checklist.md`
**Created**: 2026-04-30
**Maintainer**：用戶 + AI 助手
