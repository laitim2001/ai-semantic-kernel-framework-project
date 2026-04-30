# Sprint 51.0 — Mock 企業工具 + 業務工具骨架

**Phase**: 51（Tools + Memory）
**Sprint 順序**：1 / 3（Phase 51 第 1 個 sprint）
**啟動日期**：2026-04-30
**預期完成**：2026-05-06（1 週 / 5 工作日）
**範疇歸屬**：業務領域層（5 domain）+ Mock backend（platform/test infra）+ 範疇 2 ToolSpec stub
**狀態**：🟡 PLANNING — 待用戶 approve

---

## Sprint Goal

> **一句話**：建立 5 業務 domain mock backend + 18 個 ToolSpec stub，讓後續 Sprint（51.1+ / 52+ / 53+ / 54+）的 demo 不再依賴 echo_tool，端到端流量可呼叫真實業務工具。

**為什麼此 sprint 必要**（per `06-phase-roadmap.md` §51.0 修訂理由）：
- 原 51.1 只交 4 類通用工具（memory / search / exec / hitl）
- 5 業務 domain 工具（patrol / correlation / rootcause / audit / incident）原排入 Phase 55
- → Phase 51-54 的 demo 沒有業務材料，只能用 echo_tool
- → Phase 55 才接 5 domain 過於緊張（PM review 5.5/10 → 採方案 A 擴 22 sprint）

**51.0 解法**：把 5 domain 的 **mock backend + ToolSpec stub** 提前到 51.0，讓 ToolSpec 接口先穩定，Phase 55 接手時只需替換 mock implementation 為真實 enterprise integration（D365 / SAP / ServiceNow）。

---

## User Stories

### US-1：作為 AI 助手 demo 場景設計者
**我希望** 能在 51.1+ sprint 中呼叫 `mock_patrol_check_servers` 等真實業務工具
**以便** 不再用 `echo_tool` 假裝 demo，端到端流量更貼近真實業務情境

**驗收**：51.0 closeout 後，agent_loop 跑「巡檢 server 健康」對話可拿到 mock JSON 結果

### US-2：作為範疇 2 工具層維護者
**我希望** 5 domain 的 ToolSpec stub 在 51.0 就定形（schema / annotations / hitl_policy / concurrency）
**以便** 51.1 升級 ToolRegistry / ToolExecutor 時，stub 不必重寫，只需重註冊

**驗收**：18 個 ToolSpec 完整宣告 input_schema + ToolAnnotations + ConcurrencyPolicy + HITLPolicy + risk_level；51.1 切換 registry 時 schema 0 變動

### US-3：作為 Phase 55 業務領域實作者
**我希望** business_domain/{patrol,correlation,rootcause,audit_domain,incident}/ 5 dir 在 51.0 就有 register_<domain>_tools(registry) 入口
**以便** Phase 55 直接替換 mock implementation 為真實整合，不必動 register pattern

**驗收**：5 個 register 函式 signature 統一；切換 implementation 時只動 `tools.py` 內部，外部 import path 不變

### US-4：作為主流量驗證守護者
**我希望** Sprint 51.0 closeout 時主流量（POST /api/v1/chat/ → AgentLoopImpl → mock 工具呼叫）端到端可跑
**以便** 51.0 落地後立刻可在 chat-v2 frontend 看到 ToolCallCard 顯示業務工具結果（非 echo）

**驗收**：1 個 e2e 測試 + 用戶手動 smoke（CARRY-019）可看到 `tool_name=mock_patrol_check_servers` + result_content 為 mock JSON

### US-5：作為 V2 紀律守護者
**我希望** 51.0 不違反任何 V2 9 大紀律（Server-Side First / LLM Provider Neutrality / 17.md Single-source / 範疇歸屬 / AP / Sprint workflow / file header / multi-tenant / observability）
**以便** Phase 51 起點乾淨，後續 51.1/51.2 不必補欠

**驗收**：5 V2 lints 全 OK / mypy strict / 0 LLM SDK leak / 0 cross-category violation / 0 AP-1 violation / 17.md 同步更新

---

## Technical Specifications

### 架構決策

#### 決策 1：Mock backend 放置位置
**選擇**：`backend/src/mock_services/`（新建）
**Alternative considered**：
- ❌ Standalone repo — 太重，跨 repo coordination 開銷
- ❌ 主 backend 內 sub-router（mounted at /mock）— 模糊「production vs test infra」邊界，違反 V2 紀律
- ✅ `backend/src/mock_services/` 單獨 FastAPI app（startup 啟動為獨立 process，port 8001）

**理由**：
- mock_services 明確標記「非 production」，避免誤上線
- 獨立 port 8001 不影響 main API（8000）
- 啟停由 `scripts/dev.py mock start/stop` 控制
- Phase 55 真實 enterprise integration 上線時，刪 mock_services dir 不影響其他代碼

#### 決策 2：ToolSpec stub 與 mock backend 通訊方式
**選擇**：HTTP client（httpx async）— ToolSpec executor 內部 call mock_services 的 REST endpoint
**Alternative considered**：
- ❌ Direct in-process function call — 違反「mock 應仿真網路 IO」原則，未來真實 integration 也是 HTTP
- ✅ HTTP call to `http://localhost:8001/mock/{domain}/...`

**理由**：
- 讓 ToolSpec 的 executor 從 51.0 起就習慣 async HTTP IO 模式
- 51.1 / Phase 55 替換真實 integration 時，HTTP 呼叫模式不變

#### 決策 3：Mock data seed 規模
**選擇**：依 06-phase-roadmap §51.0 deliverables 規定 — 10 customer / 50 order / 20 alert / 5 incident（額外加：3 patrol / 5 audit log / 8 root cause finding）
**儲存**：JSON file in `backend/src/mock_services/data/seed.json`（不入 PostgreSQL，避免污染主 DB）
**載入**：mock_services startup 時讀入 in-memory dict

#### 決策 4：ToolRegistry 註冊時機
**選擇**：51.0 暫用 50.1 `InMemoryToolRegistry`（CARRY-017 deprecation 留 51.1）
**註冊路徑**：`runtime/workers/agent_loop_worker.py` startup 時呼叫 `register_all_business_tools(registry)` aggregator
**51.1 升級**：切到 Level 3 ToolRegistry 時，aggregator 簽名不變，僅 registry 實作 swap

#### 決策 5：Tool 數量採 spec 18 不是 roadmap 24
**選擇**：18 個 ToolSpec stub（per `08b-business-tools-spec.md`：4 patrol + 3 correlation + 3 rootcause + 3 audit + 5 incident）
**處置 roadmap 24 差異**：在 retrospective.md 記錄；如 user 認為需擴到 24，留 51.1 backlog
**Naming convention**：`mock_<domain>_<action>` — 強調這是 mock 階段（51.0/52-54 demo 用），Phase 55 改為正式 `<domain>_<action>` 時統一 rename

### Single-source 同步

| 項目 | 位置 | Owner |
|-----|------|-------|
| ToolSpec 中性型別 | `_contracts/tools.py`（已存在 from 50.1） | 範疇 2 |
| ToolAnnotations / ConcurrencyPolicy / HITLPolicy enum | `_contracts/tools.py` 或 `_contracts/policies.py` | 範疇 2 + §HITL |
| 業務工具註冊 entry | `business_domain/<domain>/tools.py` 各自 | 業務領域層 |
| Mock backend Pydantic schema | `mock_services/schemas/<domain>.py` | mock_services |
| 17.md §3.1 工具註冊表 | 加 18 entries | Contract owner |

### 範疇歸屬規則

```
agent_harness/tools/_inmemory.py        ← 範疇 2 stub（50.1，51.1 deprecate）
agent_harness/tools/_abc.py             ← 範疇 2 ABC（50.1）
business_domain/patrol/tools.py         ← 業務層（51.0 新增 — register_patrol_tools）
business_domain/patrol/mock_executor.py ← 業務層（51.0 新增 — call mock_services HTTP）
business_domain/correlation/tools.py    ← 業務層（51.0 新增）
... (5 domain × 2 file = 10 file)
mock_services/main.py                   ← 平台輔助層（51.0 新建獨立 FastAPI app）
mock_services/routers/{crm,kb,patrol,correlation,rootcause,audit,incident}.py
mock_services/data/seed.json
```

**禁止**：
- ❌ business_domain import openai / anthropic（per llm-provider-neutrality.md）
- ❌ tools.py 直接 import mock_services（mock_services 是 runtime 啟動的 process，business_domain 透過 HTTP URL 呼叫）
- ❌ 跨 domain import（patrol 不可 import correlation）

---

## File Change List（共 ~30 檔）

### 新建（27 檔）

#### Mock backend（7 檔）
- `backend/src/mock_services/__init__.py`
- `backend/src/mock_services/main.py`（FastAPI app，port 8001）
- `backend/src/mock_services/routers/crm.py`（customer / order / ticket）
- `backend/src/mock_services/routers/kb.py`（semantic_search）
- `backend/src/mock_services/routers/patrol.py`
- `backend/src/mock_services/routers/correlation.py`
- `backend/src/mock_services/routers/rootcause.py`
- `backend/src/mock_services/routers/audit.py`
- `backend/src/mock_services/routers/incident.py`
- `backend/src/mock_services/schemas/__init__.py`（Pydantic models）
- `backend/src/mock_services/data/seed.json`

> 算到目錄結構：總共 mock_services 11 file，但 routers 各算 1 → 6 + main + __init__ + schemas/__init__ + seed.json + (future) = ~10-11 files。為簡化此處列為 **mock backend ~10 files**。

#### 業務 domain tools（10 檔）
- `business_domain/patrol/tools.py`（4 ToolSpec + register_patrol_tools）
- `business_domain/patrol/mock_executor.py`（HTTP call helpers）
- `business_domain/correlation/tools.py`（3 ToolSpec + register_correlation_tools）
- `business_domain/correlation/mock_executor.py`
- `business_domain/rootcause/tools.py`（3 ToolSpec + register_rootcause_tools）
- `business_domain/rootcause/mock_executor.py`
- `business_domain/audit_domain/tools.py`（3 ToolSpec + register_audit_tools）
- `business_domain/audit_domain/mock_executor.py`
- `business_domain/incident/tools.py`（5 ToolSpec + register_incident_tools）
- `business_domain/incident/mock_executor.py`

#### Aggregator（1 檔）
- `business_domain/_register_all.py` — `register_all_business_tools(registry)` 一次呼叫 5 個 register

#### Tests（~10 檔）
- `tests/unit/business_domain/test_patrol_tools.py`
- `tests/unit/business_domain/test_correlation_tools.py`
- `tests/unit/business_domain/test_rootcause_tools.py`
- `tests/unit/business_domain/test_audit_tools.py`
- `tests/unit/business_domain/test_incident_tools.py`
- `tests/unit/business_domain/test_register_all.py`
- `tests/unit/mock_services/test_mock_routers.py`（CRM / KB / 5 domain 端點各 1 smoke）
- `tests/integration/test_mock_services_startup.py`
- `tests/integration/test_business_tools_via_registry.py`（透過 InMemoryToolRegistry 驗證 18 stub 全 callable）
- `tests/e2e/test_agent_loop_with_mock_patrol.py`（核心 e2e — agent 呼叫 mock_patrol_check_servers）

### 修改（5 檔）

- `backend/src/runtime/workers/agent_loop_worker.py` — 加 `register_all_business_tools(registry)` startup hook
- `backend/src/api/v1/chat/handler.py` — chat 啟動時若 `tools=[]` default 全業務工具註冊（dev mode）
- `docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` — §3.1 加 18 ToolSpec entries
- `scripts/dev.py` — 加 `mock-services` subcommand（start/stop/status）
- `docker-compose.dev.yml` — 加 `mock_services` service block

---

## Acceptance Criteria

### 必過（DoD）

1. ✅ 18 個 ToolSpec 全 register 成功；`registry.list_tools()` 列出 18 個（+ echo_tool）
2. ✅ Mock backend 跑得起來（`scripts/dev.py mock start` → `curl http://localhost:8001/health` 200）
3. ✅ Mock backend 7 個 router 各 ≥ 1 endpoint smoke test PASS（CRM / KB / 5 domain）
4. ✅ Agent loop 透過 InMemoryToolExecutor 呼叫 `mock_patrol_check_servers(scope=["web-01"])` 拿到 mock JSON 結果（包含 server_id / health / metrics）
5. ✅ e2e 測試 `test_agent_loop_with_mock_patrol` PASS — agent prompt「巡檢 web-01」→ tool_call → mock result → final answer 含 server health
6. ✅ 17.md §3.1 加 18 entries（含 ToolSpec name / annotations / concurrency / hitl_policy / risk）
7. ✅ pytest 全 PASS（50.2 baseline 259 → 51.0 預期 ~310 PASS / 0 SKIPPED）
8. ✅ mypy strict / V2 5 lints / black / isort / flake8 全 OK
9. ✅ LLM SDK leak grep = 0（`grep -r "import openai\|import anthropic" business_domain/`）
10. ✅ Cross-category import lint OK（business_domain 不 import other domain；不 import agent_harness/<num>_*/ 私有模組）
11. ✅ AP-1 lint clean（mock_executor 不寫 pipeline 偽裝 loop）
12. ✅ Frontend chat-v2 manual smoke（CARRY-019，可推到 51.x backlog）— ToolCallCard 顯示 mock_patrol 結果

### 建議過（不阻擋）

13. 🟡 Mock backend Docker container 化（51.x backlog）
14. 🟡 24 工具完整補齊（roadmap 規定）— 51.1 backlog
15. 🟡 Tracing on mock_executor HTTP call（51.x or Phase 53 觀測強化）

---

## Dependencies & Risks

### 依賴

- ✅ 50.1 `InMemoryToolRegistry` + `_inmemory.py`（已就緒）
- ✅ 50.1 `ToolSpec` + `ToolAnnotations` + `HITLPolicy` enum in `_contracts/tools.py`（已就緒；Sprint 51.0 Day 0 確認）
- ✅ 50.2 `ToolCallExecuted` event 含 `result_content`（已就緒，frontend 可顯示）
- ⏸ 真實 ToolRegistry / ToolExecutor / Sandbox（51.1 — 51.0 不依賴）
- ⏸ Memory layer（51.2 — 51.0 不依賴）

### 風險

| ID | 風險 | 機率 | 影響 | 緩解 |
|----|-----|-----|-----|------|
| R-1 | 18 ToolSpec schema 設計不周；51.1 切換時要 rewrite | 中 | 中 | Day 0 先看 08b spec 全部 schema fields；Day 4 e2e 驗證至少 3 ToolSpec 真實 callable 後才複製 pattern 到其他 |
| R-2 | mock_services FastAPI 跑在 8001 但 dev 腳本 / docker-compose 沒整合，需手動啟動 | 中 | 低 | Day 1 加 `scripts/dev.py mock` 子命令；Day 3 加 docker-compose service block |
| R-3 | business_domain/<domain>/tools.py 違反「不跨 domain import」 | 低 | 高 | 5 domain 設計時各自獨立；register 函式只 import 自己 domain 的 mock_executor |
| R-4 | Roadmap 24 vs spec 18 數量差，user 期待不一致 | 中 | 低 | retrospective.md 記錄；51.1 plan 時 user 決定要不要補 6 個 |
| R-5 | mock JSON schema 在 frontend ToolCallCard 顯示醜 / 太大 | 低 | 中 | mock backend 限 result_content < 4 KB；ToolCallCard truncate（51.x） |
| R-6 | InMemoryToolRegistry 51.1 deprecate 後 51.0 stub 全要重註冊 | 低 | 低 | register_<domain>_tools(registry) 介面通用；51.1 swap registry 不影響 stubs |

---

## Deliverables（Sprint Goal Mapping）

- [ ] **D-1**: 5 業務 domain tools.py + register 函式（10 檔，US-2 + US-3）
- [ ] **D-2**: 18 個 ToolSpec stub（含完整 schema + annotations，US-2）
- [ ] **D-3**: Mock backend FastAPI app（port 8001，7 router，~10 檔，US-1）
- [ ] **D-4**: Mock data seed JSON（10/50/20/5 + extras，US-1）
- [ ] **D-5**: Aggregator `register_all_business_tools(registry)`（US-3 + US-4）
- [ ] **D-6**: Worker startup hook + chat handler default tools 加載（US-4）
- [ ] **D-7**: 17.md §3.1 18 entries 同步（US-2 + US-5）
- [ ] **D-8**: ~10 個 test files（unit + integration + 1 e2e，US-4）
- [ ] **D-9**: scripts/dev.py mock subcommand + docker-compose 整合（R-2）
- [ ] **D-10**: progress.md / retrospective.md / Phase 51 README 更新 / sprint-51-0-checklist 全 [x]（V2 紀律）

---

## 估時

| Day | 主題 | 預估 | 累計 |
|-----|------|-----|-----|
| 0 | Plan + Checklist + branch + Phase README | 4h | 4h |
| 1 | Mock backend 骨架（main.py / routers / data seed / scripts） | 5h | 9h |
| 2 | 5 domain tools.py + ToolSpec stubs（patrol + correlation + rootcause） | 6h | 15h |
| 3 | 5 domain tools.py + ToolSpec stubs（audit + incident） + mock_executor + aggregator | 6h | 21h |
| 4 | Tests（unit + integration + e2e）+ worker hook + chat handler | 5h | 26h |
| 5 | 17.md sync + retro + closeout + memory update | 3h | 29h |

**Plan total**：~29h（規劃 28 SP / 1 週上限）
**Actual estimate**（per V2 6 sprint 平均 ~19% 估時準度）：~5.5-6h

---

## V2 紀律對照（9 項）

| # | 紀律 | 對應檢查 |
|---|------|---------|
| 1 | Server-Side First | mock_services 在 backend，所有 mock data 在 server；frontend 只透過 SSE 看 tool result |
| 2 | LLM Provider Neutrality | business_domain/* 0 LLM SDK import（grep 驗證） |
| 3 | CC Reference 不照搬 | Mock backend 是 V2 自行設計，未抄 CC subagent_handler pattern |
| 4 | 17.md Single-source | §3.1 加 18 ToolSpec entries 同 commit |
| 5 | 11+1 範疇歸屬 | tools.py = 業務層；mock_executor = 業務層 helper；mock_services = 平台輔助；agent_harness/tools/* 50.1 不動 |
| 6 | 04 Anti-patterns | AP-1 lint clean；AP-2 mock_services 不滲透到 production code；AP-6 ToolSpec 中性介面（不綁 mock backend URL，URL 透過 config 注入） |
| 7 | Sprint workflow | Day 0 plan/checklist；Day 1-5 嚴格 plan→checklist→code→update→commit |
| 8 | File header convention | 27 新檔每檔有 V2 file header（File / Purpose / Category / Created / Modification History） |
| 9 | Multi-tenant rule | 51.0 mock backend 不 tenant-aware（簡化）；51.1 接 real registry 時加 tenant_id；retrospective 標記 R-7 |

---

## Out of Scope（明確不做）

- ❌ 24 工具補齊（roadmap）— 51.1 backlog 決定
- ❌ Mock backend tenant-aware（簡化；51.1+ 加）
- ❌ Mock backend persistence（記憶體即可，restart 重置）
- ❌ Frontend chat-v2 ToolCallCard 顯示優化（51.x 後續 UX sprint）
- ❌ ToolRegistry / ToolExecutor / Sandbox 真實實作（51.1）
- ❌ Memory tools（51.2）
- ❌ 真實 enterprise integration（D365 / SAP / ServiceNow — Phase 55）
- ❌ Tracing / metrics on mock_executor（51.x 或 Phase 53 觀測強化）
- ❌ Streaming partial-token（CARRY-015，52.1）
- ❌ Real Azure OpenAI demo（CARRY-016，用戶手動）
- ❌ vitest install + frontend tests（CARRY-010，51.x Day 0）

---

## Carry-forward 候選（從 50.2）

50.2 closeout 留 9 CARRY items；51.0 暫不接以下：

- CARRY-010 vitest install — 51.x Day 0 接
- CARRY-011 Tailwind retrofit — 53.4
- CARRY-012 dev e2e manual smoke — 用戶 trigger
- CARRY-013 npm audit — 51.x
- CARRY-014 DB-backed sessions — 51.x
- CARRY-015 streaming — 52.1
- CARRY-016 Real Azure run — 用戶
- CARRY-017 InMemory deprecation — 51.1（51.0 仍用 InMemory）
- CARRY-018 AST AP-1 lint — 51.x backlog

51.0 新增 CARRY 候選：
- **CARRY-019**：frontend chat-v2 ToolCallCard 顯示 mock 業務工具結果 manual smoke（用戶手動）
- **CARRY-020**：roadmap 24 vs spec 18 工具差異決策（user review）

---

## Approval

- [ ] User review plan
- [ ] User review checklist
- [ ] User approve → AI 助手執行 Day 0（建 branch + commit plan/checklist）

---

**File**: `docs/03-implementation/agent-harness-planning/phase-51-tools-memory/sprint-51-0-plan.md`
**Created**: 2026-04-30
**Maintainer**：用戶 + AI 助手
