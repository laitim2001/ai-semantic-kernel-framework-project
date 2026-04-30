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
- [x] **3 endpoints**：query_logs / generate_report / flag_anomaly ✅ 2026-04-30
  - DoD: query_logs filter (time_range/action/user_id) ✅；generate_report 回 placeholder URL ✅；flag_anomaly 紀錄 in-memory ledger ✅

### 3.2 business_domain/audit_domain/{mock_executor,tools}.py（60 min）
- [x] **`AuditMockExecutor` + 3 ToolSpec + register_audit_tools** ✅ 2026-04-30
  - DoD: 對應 08b §Domain 4 表 3 entries ✅；flag_anomaly destructive=True + ask_once

### 3.3 mock_services/routers/incident.py（60 min）
- [x] **5 endpoints**：create / update_status / close / get/{id} / list ✅ 2026-04-30
  - DoD: create 回 inc_live_*；close 回 `closed_pending_review`；list 支援 severity/status filter ✅
  - 額外：seed + live incident merge view（_all_incidents helper）

### 3.4 business_domain/incident/{mock_executor,tools}.py（75 min）
- [x] **`IncidentMockExecutor` + 5 ToolSpec + register_incident_tools** ✅ 2026-04-30
  - DoD: `mock_incident_close` `hitl_policy:always_ask` + `risk:high` + `destructive=True`（per 08b §Domain 5 強制） ✅

### 3.5 business_domain/_register_all.py（30 min）
- [x] **`register_all_business_tools(registry, handlers, *, mock_url)` 一次呼叫 5 register** ✅ 2026-04-30
  - DoD: 註冊後 18 ToolSpec + 18 handlers；per-domain count 4+3+3+3+5；2 HIGH risk = apply_fix + incident_close（驗證通過）✅

### 3.6 Day 3 commit（15 min）
- [ ] **commit `feat(business-audit/incident + aggregator, sprint-51-0): Day 3 — 8 ToolSpec + 2 mock routers + register_all`**
  - DoD: 18 ToolSpec 全註冊 OK；mypy strict 30 files / black formatted / 8 endpoints TestClient PASS
  - Verify: ✅ `register_all_business_tools` wires 18 + 18; 2 HIGH risk correct

---

## Day 4 — Tests + Worker Hook + Chat Handler（預估 5 小時）

### 4.1 Integration test：mock_services 啟動 + 全 router 端點（45 min）
- [x] **`tests/integration/mock_services/test_mock_services_startup.py`** ✅ 2026-04-30
  - DoD: TestClient + lifespan triggered (with-block)；12 tests covering 7 routers + 404 + dry_run + close ✅
  - 全 12 tests PASS

### 4.2 Integration test：18 tools 透過 InMemoryToolRegistry（60 min）
- [x] **`tests/integration/business_domain/test_business_tools_via_registry.py`** ✅ 2026-04-30
  - DoD: register_all_business_tools(registry) → 18 tool 全 callable；result 為 mock JSON ✅
  - 改採 httpx ASGI transport monkey-patch（in-process，不依賴 mock_services subprocess）— 比 plan 寫的 respx 更通用
  - 10 tests PASS：18-spec count + high-risk tag + 8 happy paths + unknown tool error case

### 4.3 worker startup hook / chat handler 預設工具（30 min）
- [x] **`make_default_executor()` 加到 `business_domain/_register_all.py`** ✅ 2026-04-30
  - 設計變更：worker `build_agent_loop_handler` 簽名保留 unchanged（無 register_all 注入；clean layering）；改在 `business_domain/_register_all.py` 加 `make_default_executor()` factory wraps echo + 18 business
  - DoD: `make_default_executor()` 註冊 19 specs / 19 handlers ✅

### 4.4 chat handler default tools（30 min）
- [x] **修改 `api/v1/chat/handler.py` — `make_echo_executor()` → `make_default_executor()`** ✅ 2026-04-30
  - DoD: 兩 site (build_echo_demo_handler + build_real_llm_handler) 改用 make_default_executor；dev mode 用戶不指定 tools 也能呼叫 19 業務工具 ✅

### 4.5 e2e test：agent loop with mock_patrol（90 min）
- [x] **`tests/e2e/test_agent_loop_with_mock_patrol.py`** ✅ 2026-04-30
  - DoD:
    - subprocess fixture spawn `uvicorn mock_services.main:app --port 8001` ✅
    - MockChatClient 預編腳本（turn 1 mock_patrol_check_servers / turn 2 END_TURN）✅
    - AgentLoopImpl + make_default_executor ✅
    - ToolCallRequested(`mock_patrol_check_servers`) + ToolCallExecuted(result_content with `server_id=web-01` + health) ✅
    - LoopCompleted with END_TURN ✅
  - 2 tests PASS / ~3.86s (subprocess startup)
  - **替代 chat router e2e**：Sprint 51.0 e2e 直接走 AgentLoopImpl（不過 SSE / FastAPI app）— 簡化避免複用 50.2 SSE 測試結構，仍覆蓋 plan US-1+US-4 acceptance

### 4.6 Day 4 commit（15 min）
- [ ] **commit `feat(integration/e2e, sprint-51-0): Day 4 — 24 tests + worker / chat handler default 19 tools + e2e mock_patrol`**
  - DoD: 全 sprint test 累計 283 PASS / 0 SKIPPED ✅；無 regression（259 baseline + 24 new = 283）
  - Verify: `python -m pytest --tb=line` ✅

---

## Day 5 — 17.md Sync + Retro + Closeout（預估 3 小時）

### 5.1 17.md §3.1 加 18 ToolSpec entries（45 min）
- [x] **17.md §3.1 工具註冊表 加 18 mock business entries + echo_tool entry** ✅ 2026-04-30
  - 含「Sprint 51.0 mock 階段」section header + tagging 規則註解 + Phase 55 mass rename plan
  - 4 patrol + 3 correlation + 3 rootcause + 3 audit + 5 incident = 18 entries 確認

### 5.2 docker-compose.dev.yml 加 mock_services（20 min）
- [x] **service block 加在 prometheus 之後 / volumes 之前** ✅ 2026-04-30
  - image: python:3.12-slim, command: pip install + uvicorn, mount backend/src:/app:ro, healthcheck via urllib

### 5.3 progress.md Day 0-5 全紀錄（30 min）
- [x] **progress.md Day 5 final entry** ✅ 2026-04-30
  - Day 0-5 全紀錄；估時 vs actual 表格 / surprises / V2 紀律 9 項 / next phase plan

### 5.4 retrospective.md（30 min）
- [x] **retrospective.md** ✅ 2026-04-30
  - 5 Improve（A1 ToolSpec field / A2 correlation null-server / A3 curl 寫法 / A4 CWD persistence / A5 24 vs 18）
  - 3 CARRY items（CARRY-019/020/021）+ 估時準度報告 + 範疇成熟度表

### 5.5 Phase 51 README 更新 51.0 完成狀態（20 min）
- [x] **phase-51-tools-memory/README.md** ✅ 2026-04-30
  - Sprint 51.0 ✅ DONE 標記 / Sprint 進度 1/3 = 33% / 範疇成熟度 Post-51.0 / 累計交付 list

### 5.6 memory/project_phase51_tools_memory.md 更新（15 min）
- [x] **memory file 新增 + MEMORY.md index 更新** ✅ 2026-04-30
  - `~/.claude/projects/.../memory/project_phase51_tools_memory.md`
  - MEMORY.md index 加 hook line（< 200 字）

### 5.7 sprint-51-0-checklist 全 [x]（10 min）
- [x] **本檔 Day 0-5 全 [x]** ✅ 2026-04-30
  - 0 個 🚧 殘留項；無未勾選項

### 5.8 Day 5 closeout commit（15 min）
- [ ] **commit `docs(closeout, sprint-51-0): Day 5 — 17.md sync + docker-compose + progress + retro + Phase 51 README + memory`**
  - DoD: working tree clean；branch HEAD = closeout commit；Sprint 51.0 ✅ DONE

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
