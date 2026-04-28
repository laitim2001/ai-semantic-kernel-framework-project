# Phase 路線圖（Phase 49-55）

**建立日期**：2026-04-23
**版本**：V2.1（2026-04-28 PM review 修訂：16 → 22 sprint）

---

## 修訂說明（2026-04-28）

> 經 PM 視角獨立 review（5.5/10），發現原 16 sprint 普遍超載 1.5-2.5 倍：
> - Phase 49：3 sprint 包山包海（RLS / Worker queue 選型 / OTel / CI 全擠）
> - Phase 53.3：3 層 guardrails + V1 Risk/HITL 遷移 + frontend 約 2 週工作量
> - Phase 55：2 sprint 做 5 業務領域 + 完整 frontend + canary 結構性不可能
>
> **修訂方案 A（已採納）**：擴為 22 sprint 約 5.5 個月，保留完整 V2 scope。

> **重要聲明**：**V2 完成（Phase 55）≠ SaaS-ready**。SaaS Stage 1（多租戶內部）在 Phase 56-58。Phase 55 達到的是「核心 11 範疇 + 5 業務領域 + canary 試用」。詳見 [`15-saas-readiness.md`](./15-saas-readiness.md)。

---

## 總覽

| Phase | 名稱 | 原 sprint | **新 sprint** | 範疇覆蓋 | 預期成果 |
|-------|------|----------|-------------|---------|---------|
| **49** | Foundation | 3 | **4** | 0（基礎設施） | V2 骨架 + CI + DB + RLS + Workers + Adapters + OTel |
| **50** | Loop Core | 2 | 2 | 1 + 6 | 真 ReAct loop 跑通簡單對話 |
| **51** | Tools + Memory | 2 | **3** | 2 + 3 | 51.0 mock 工具 + 工具系統 + 5 層記憶 |
| **52** | Context + Prompt | 2 | 2 | 4 + 5 | 統一 PromptBuilder + Compaction + Caching |
| **53** | State + Error + Guardrails | 3 | **4** | 7 + 8 + 9 | 健壯性 + 治理（拆 Guardrails 核心 + Frontend） |
| **54** | Verification + Subagent | 2 | 2 | 10 + 11 | 自我修正 + 子代理 |
| **55** | Production | 2 | **5** | 業務領域 + canary | 5 業務 backend + frontend + 缺漏 6 頁 + 端到端 + canary |
| **合計** | | 16 | **22 sprint** | 全 11 + 範疇 12 | **真實對齊度 75%+** |

**總時程**：約 **5.5 個月**（每 sprint 1 週）

---

## Phase 49: Foundation（**4 sprint** ←原 3）

### 目標
建立 V2 完整骨架，所有後續 Phase 的依賴。**不寫業務邏輯**，只建基礎設施。

### Sprint 49.1: V1 封存 + V2 目錄骨架 + **CI Pipeline**
**工作量**：1 週

> **修訂**：原 49.1 沒包 CI；本次補入。CI 必須在 50.1 之前就緒（11.md 強制）。

**Deliverables**：
- [ ] `git tag v1-final-phase48`
- [ ] V1 完整移到 `archived/v1-phase1-48/`
- [ ] V2 backend 目錄樹建立（agent_harness/_contracts/ + 11 範疇 + observability/ + hitl/ + adapters/ + api/ + business_domain/ + governance/ + identity/ + observability/ + runtime/ + infrastructure/ + core/ + middleware）
- [ ] V2 frontend 目錄樹建立
- [ ] 每個範疇目錄的 README.md（簡短）
- [ ] 每個範疇的 ABC 定義（空殼，只有 interface）
- [ ] **第 12 範疇 observability/_abc.py**（Tracer ABC）
- [ ] **`agent_harness/_contracts/`** 跨範疇 single-source 型別空殼
- [ ] **`agent_harness/hitl/_abc.py`**（HITLManager ABC 空殼）
- [ ] `pyproject.toml` / `requirements.txt` V2 版本
- [ ] `package.json` V2 版本
- [ ] `docker-compose.dev.yml`
- [ ] **GitHub Actions CI workflow**：`backend-ci.yml`（black / isort / flake8 / mypy / pytest）+ `frontend-ci.yml`（lint / build / test）
- [ ] **PR 模板**（含「3 大原則 check + 17.md 介面表 check」）
- [ ] **明文聲明 V2 ≠ SaaS-ready**（00-v2-vision.md）

**驗收**：
- ✅ V1 完全封存，不可意外修改
- ✅ V2 目錄樹通過 `tree` 視覺檢查
- ✅ `pip install -e .` 通過（即使無實作）
- ✅ `npm install` 通過
- ✅ `docker compose up` 啟動所有依賴服務
- ✅ **CI pipeline 在 PR 時自動跑（即使現在只是空殼，pipeline 必須 green）**

### Sprint 49.2: DB Schema + Async ORM 核心
**工作量**：1 週

> **修訂**：原 49.2 把 RLS + Audit append-only + Qdrant 全擠一週。本次拆出，本 sprint 只做 schema + ORM。

**Deliverables**：
- [ ] Alembic 初始化（從零）
- [ ] 第一批 ORM models（async SQLAlchemy）：
  - tenants / users / roles
  - sessions / messages
  - tool_calls / tool_results
  - state_snapshots（含 schema_version + StateVersion 雙因子）
  - tools_registry（DB 端 metadata）
- [ ] Connection pool + async session 測試
- [ ] Pydantic Settings 配置完整

**驗收**：
- ✅ Alembic migrate 從零跑通
- ✅ Async ORM CRUD 測試通過
- ✅ StateVersion (counter + content_hash) race condition 測試通過

### Sprint 49.3: RLS + Audit Append-Only + Qdrant Tenant 隔離
**工作量**：1 週

> **修訂（新拆）**：09.md 強調所有 session-scoped 表 RLS + per-request `SET LOCAL app.tenant_id`，這是 3-5 天獨立工作；audit append-only WORM 也是顯著工作量。

**Deliverables**：
- [ ] 14+ 張 multi-tenant 表的 RLS policies
- [ ] Per-request `SET LOCAL app.tenant_id` middleware
- [ ] Audit log append-only 機制（DB 觸發器 + WORM + hash chain）
- [ ] Approvals 表（HITL）
- [ ] Memory_layers 雙軸表（5 scope × 3 time scale）
- [ ] Vector DB（Qdrant）整合：tenant-aware namespace
- [ ] Red-team test：跨 tenant prompt injection 0 leak

**驗收**：
- ✅ RLS 強制：tenant A 任何 query 不可見 tenant B 資料
- ✅ Audit log append-only 機制（無法 UPDATE / DELETE）
- ✅ Qdrant tenant 隔離測試通過

### Sprint 49.4: Adapters + Worker Queue 選型 + OTel + Lint Rules
**工作量**：1 週

> **修訂**：原 49.3 把 4 件大事擠一週（Adapter / Worker queue 選型 / OTel / FastAPI / Frontend）。本次只保留 4 件，移除非必要。

**Deliverables**：
- [ ] `adapters/_base/chat_client.py` ABC（含 4 個新方法 count_tokens / get_pricing / supports_feature / model_info）
- [ ] `adapters/azure_openai/adapter.py` 實作（GPT-5.4）
- [ ] **Worker queue 選型決策（Celery vs Temporal）**：spike PoC 兩家對比 + 決策報告
- [ ] `runtime/workers/agent_loop_worker.py` 框架
- [ ] OpenTelemetry 整合（tracing + metrics + logging）
- [ ] **Lint rules**（pre-commit + CI）：
  - duplicate-dataclass-check（17.md §8.1）
  - cross-category-import-check（17.md §8.2）
  - sync-callback-check（17.md §8.3）
  - LLM SDK direct import check
- [ ] FastAPI 啟動 + 基本 middleware（tenant context）
- [ ] Frontend Vite 啟動 + 基本路由

**驗收**：
- ✅ Adapter 可呼叫 Azure OpenAI 並回傳結果
- ✅ ChatClient ABC 全 4 方法測試覆蓋
- ✅ Worker 可接收任務並執行
- ✅ OTel trace 可在 Jaeger 看到（含 trace_context propagation）
- ✅ Lint rules 全部生效（人工製造違反測試）
- ✅ FastAPI `/health` 通過
- ✅ Frontend 顯示空白 chat 頁面

### Phase 49 結束驗收
- 11 範疇 + 範疇 12 成熟度全部 Level 0（合理 — 還沒實作）
- 整體基礎設施 100% 就緒
- CI / Lint / OTel 全部上線
- 接下來可開始實作範疇

---

## Phase 50: Loop Core（2 sprint）

### 目標
**最重要的 Phase**。實作真正的 TAO loop，跑通最簡單的 agent 對話。

### Sprint 50.1: 範疇 1 + 範疇 6 核心
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/01_orchestrator_loop/loop.py` — `AgentLoop` 主類
- [ ] `agent_harness/01_orchestrator_loop/events.py` — Loop events
- [ ] `agent_harness/01_orchestrator_loop/termination.py` — 終止條件
- [ ] `agent_harness/06_output_parser/parser.py` — Native tool_calls 解析
- [ ] `agent_harness/06_output_parser/classifier.py` — Output 分類
- [ ] 簡單 in-memory tool（測試用，例：`echo_tool`）
- [ ] 第一個端到端測試：「用戶問 X → loop 跑 → 回答 X」

**驗收**：
- ✅ Loop 是真 `while True`，由 `stop_reason` 退出
- ✅ Tool 結果以 user message 回注
- ✅ SSE 事件流完整
- ✅ Anti-Pattern 1（Pipeline 偽裝 Loop）零違反

### Sprint 50.2: API + Frontend 對接
**工作量**：1 週

**Deliverables**：
- [ ] `api/v1/chat/` 端點（POST /chat with SSE）
- [ ] `platform/workers/agent_loop_worker.py` 整合 loop
- [ ] Frontend `pages/chat-v2/` 基本介面
- [ ] Frontend 顯示 loop events（thinking / tool_call / tool_result / final）
- [ ] 第一個演示案例：「問 Echo 工具的 X，回答 X」

**驗收**：
- ✅ 用戶在前端輸入訊息 → 看到完整 loop 過程 → 拿到答案
- ✅ 範疇 1 達 Level 3（接入主流量）
- ✅ 範疇 6 達 Level 4（完全 native）

---

## Phase 51: Tools + Memory（**3 sprint** ←原 2）

### Sprint 51.0: Mock 企業工具 + 業務工具骨架（**新增**）
**工作量**：1 週

> **新增理由（PM review）**：原 51.1 只交 4 類工具，企業 D365/SAP 工具被推遲到 55，意味 51-54 之間 demo 沒有業務材料。本 sprint 補一個 mock backend，讓 52-54 demo 真實可跑。

**Deliverables**：
- [ ] Mock CRM backend（FastAPI 子服務）：簡化 customer / order / ticket APIs
- [ ] Mock KB backend：simple semantic search
- [ ] **5 業務 domain 骨架**（business_domain/{patrol,correlation,rootcause,audit,incident}/）— Phase 55 接手前的空殼 + register_*_tools 入口
- [ ] **08b-business-tools-spec.md 對應的 24 個工具 ToolSpec stub**（指向 mock backend）
- [ ] Mock data seed（10 customer / 50 order / 20 alert / 5 incident）

**驗收**：
- ✅ Agent 可以呼叫 `mock_crm_search_customer` 拿到 mock 結果
- ✅ Agent 可以呼叫 `mock_patrol_check_servers` 拿到 mock 結果
- ✅ 後續 sprint demo 案例不再用 echo_tool

### Sprint 51.1: 範疇 2 工具層
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/02_tools/registry.py` — ToolRegistry
- [ ] `agent_harness/02_tools/spec.py` — ToolSpec 定義
- [ ] `agent_harness/02_tools/executor.py` — 執行引擎（read 並行 / write 序列）
- [ ] `agent_harness/02_tools/permissions.py` — 權限檢查
- [ ] `agent_harness/02_tools/sandbox.py` — Sandbox 抽象
- [ ] 內建工具：
  - `memory_tools.py`（占位，等 51.2）
  - `search_tools.py`（web_search via Azure 或 Bing）
  - `exec_tools.py`（python_sandbox via container）
  - `hitl_tools.py`（request_approval）
- [ ] JSONSchema 強制驗證

**驗收**：
- ✅ 所有工具透過 Registry 註冊
- ✅ 工具執行有權限檢查
- ✅ Sandbox 隔離（python_sandbox 不能存取主機）
- ✅ 範疇 2 達 Level 3

### Sprint 51.2: 範疇 3 記憶層
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/03_memory/layers/` — 5 層記憶實作
- [ ] `agent_harness/03_memory/retrieval.py` — 多層檢索
- [ ] `agent_harness/03_memory/extraction.py` — 背景記憶提取（worker）
- [ ] Memory tools 接入 registry（`memory_search` / `memory_write`）
- [ ] 「線索→驗證」工作流範例
- [ ] 第二個演示案例：「Agent 用 memory_search 找過去資料 + 用工具驗證」

**驗收**：
- ✅ 5 層記憶獨立可測
- ✅ Tenant 隔離測試通過
- ✅ Agent 可主動呼叫 memory_search
- ✅ 範疇 3 達 Level 3

---

## Phase 52: Context + Prompt（2 sprint）

### Sprint 52.1: 範疇 4 Context Mgmt
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/04_context_mgmt/compactor.py` — Compaction
- [ ] `agent_harness/04_context_mgmt/observation_masker.py`
- [ ] `agent_harness/04_context_mgmt/jit_retrieval.py`
- [ ] `agent_harness/04_context_mgmt/token_counter.py`
- [ ] Loop 整合：每輪 check compaction
- [ ] 30+ turn 對話測試案例

**驗收**：
- ✅ 30 turn 不 OOM
- ✅ Compaction 後對話品質保持
- ✅ Token 計算精確
- ✅ 範疇 4 達 Level 3

### Sprint 52.2: 範疇 5 PromptBuilder
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/05_prompt_builder/builder.py` — 統一入口
- [ ] `agent_harness/05_prompt_builder/strategies.py` — Lost-in-middle 等策略
- [ ] `agent_harness/05_prompt_builder/templates.py`
- [ ] Loop 強制使用 PromptBuilder（lint rule）
- [ ] Memory layers 真注入測試

**驗收**：
- ✅ 100% 主流量透過 PromptBuilder
- ✅ Lost-in-middle 策略可配置
- ✅ Memory 真注入有測試證明
- ✅ 範疇 5 達 Level 4

---

## Phase 53: State + Error + Guardrails（**4 sprint** ←原 3）

> **修訂（PM review）**：原 53.3 是「黑洞」（3 層 guardrails + V1 Risk/HITL 遷移 + audit + frontend governance 約 2 週工作量）。本次拆 53.3 → 53.3 (Guardrails 核心) + 53.4 (Governance Frontend + HITL 整合)。

### Sprint 53.1: 範疇 7 State Mgmt
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/07_state_mgmt/state.py` — Typed LoopState
- [ ] `agent_harness/07_state_mgmt/checkpointer.py`
- [ ] `agent_harness/07_state_mgmt/time_travel.py`
- [ ] HITL pause/resume 完整流程
- [ ] Frontend `state_timeline` 組件

**驗收**：
- ✅ 每輪 loop 自動 checkpoint
- ✅ HITL 後可從 checkpoint 恢復
- ✅ Time-travel debug 可用
- ✅ 範疇 7 達 Level 4

### Sprint 53.2: 範疇 8 Error Handling
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/08_error_handling/categories.py` — 4 類錯誤
- [ ] `agent_harness/08_error_handling/retry.py`
- [ ] `agent_harness/08_error_handling/recovery.py`
- [ ] LLM-recoverable 錯誤回注機制
- [ ] 故障注入測試

**驗收**：
- ✅ 4 類錯誤分類清晰
- ✅ Retry cap = 2
- ✅ Tool 失敗回注 LLM 不 raise
- ✅ 範疇 8 達 Level 4

### Sprint 53.3: 範疇 9 Guardrails 核心（**拆分**）
**工作量**：1 週

> **修訂**：本 sprint 只做 guardrail 引擎本體，不做 frontend / V1 邏輯遷移。

**Deliverables**：
- [ ] `agent_harness/guardrails/engine.py`
- [ ] `agent_harness/guardrails/input_guardrail.py` — PII / jailbreak
- [ ] `agent_harness/guardrails/output_guardrail.py` — 毒性 + LLM-as-judge second-pass
- [ ] `agent_harness/guardrails/tool_guardrail.py` — 權限檢查
- [ ] `agent_harness/guardrails/tripwire.py` — ABC + plugin registry
- [ ] `OutputGuardrailAction` enum（reroll / sanitize / abort / escalate）
- [ ] `CapabilityMatrix`（CC ~40 capability 對應）
- [ ] WORM + hash chain 強驗證

**驗收**：
- ✅ 3 層 guardrails 全部運作
- ✅ Tripwire 觸發即停（ABC + plugin 機制）
- ✅ Audit log append-only 不可篡改驗證（hash chain）
- ✅ 範疇 9 達 Level 4 核心

### Sprint 53.4: Governance Frontend + V1 HITL/Risk 遷移 + §HITL 中央化整合
**工作量**：1 週

> **新增（PM review）**：原 53.3 把 4 件大事擠一週本來就不可能；本 sprint 專注 frontend + V1 遷移 + 中央化。

**Deliverables**：
- [ ] `governance/risk/` — V1 政策化風險評估邏輯遷移
- [ ] `governance/hitl/` — V1 HITL 邏輯遷移
- [ ] `governance/audit/` — 審計查詢 API
- [ ] **§HITL 中央化整合**：HITLManager 完整實作 + 範疇 2/9 caller 改用此入口
- [ ] **HITLDecisionReducer + SubagentResultReducer 完整實作**（範疇 7 Reducer 配合 HITL）
- [ ] Teams notification webhook
- [ ] Frontend `pages/governance/approvals/`（pending list + decision modal）
- [ ] Frontend inline chat approval card（SSE ApprovalRequested event）

**驗收**：
- ✅ HITL 審批跨 session 4 小時後仍可 resume
- ✅ Multi-instance 部署：任一 worker 都可 pickup pending approval
- ✅ HITL fallback 3 種政策（reject / escalate / approve_with_audit）正確
- ✅ Tenant A reviewer 看不到 tenant B pending
- ✅ HITL 審批通過 Teams 通知
- ✅ 範疇 9 達 Level 4+（連同 §HITL 中央化）

---

## Phase 54: Verification + Subagent（2 sprint）

### Sprint 54.1: 範疇 10 Verification
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/10_verification/verifier_base.py` ABC
- [ ] `agent_harness/10_verification/rules_verifier.py`
- [ ] `agent_harness/10_verification/llm_judge.py`
- [ ] `agent_harness/10_verification/correction_loop.py`
- [ ] Loop 整合：結束前必跑 verification
- [ ] Frontend `verification_panel` 組件

**驗收**：
- ✅ Verification 主流量強制
- ✅ Self-correction 最多 2 次
- ✅ LLM-judge 用獨立 subagent
- ✅ 範疇 10 達 Level 4

### Sprint 54.2: 範疇 11 Subagent
**工作量**：1 週

**Deliverables**：
- [ ] `agent_harness/11_subagent/dispatcher.py`
- [ ] `agent_harness/11_subagent/modes/` — Fork / Teammate / Handoff / AsTool
- [ ] `agent_harness/11_subagent/mailbox.py`
- [ ] `adapters/maf/` — MAF Builders 整合（從 V1 遷移）
- [ ] `task_spawn` / `handoff` tools 接入 registry
- [ ] Subagent 強制返回 ≤ 2K token 摘要

**驗收**：
- ✅ 4 種 subagent 模式運作
- ✅ MAF GroupChat 透過 tool 介面可觸發
- ✅ Subagent 失敗不 crash 父
- ✅ 範疇 11 達 Level 4

---

## Phase 55: Production（**5 sprint** ←原 2）

> **修訂（PM review）**：原 2 sprint 做 5 業務領域 + 完整 frontend + canary + 文件「結構性不可能」。拆 5 sprint。

### Sprint 55.1: 業務領域 Backend（5 domains）
**工作量**：1 週

> **修訂**：51.0 已建 mock backend + 業務 domain 骨架；本 sprint 將 mock 轉真實業務邏輯。

**Deliverables**：
- [ ] `business_domain/patrol/` 真實業務 service 層
- [ ] `business_domain/correlation/` 真實業務 service 層
- [ ] `business_domain/rootcause/` 真實業務 service 層
- [ ] `business_domain/audit_domain/` 真實業務 service 層
- [ ] `business_domain/incident/` 真實業務 service 層
- [ ] 24 個業務工具透過 ToolRegistry 註冊（依 08b-business-tools-spec.md）
- [ ] 高風險工具（rootcause_apply_fix / incident_close）`always_ask` 路徑驗證
- [ ] 業務領域 API（`api/v1/agents` / `workflows` 等 backend endpoint）

**驗收**：
- ✅ 5 個業務領域 service 可獨立呼叫
- ✅ Agent 可透過 tool 呼叫業務 service
- ✅ Tenant 隔離測試（A 看不到 B 的 incident / patrol result）
- ✅ 高風險工具 multi-reviewer 機制驗證

### Sprint 55.2: 業務 Frontend（agents / workflows / incidents）
**工作量**：1 週

**Deliverables**：
- [ ] `pages/agents/`：agent topology 視覺化（React Flow 自訂 node）
- [ ] `pages/workflows/`：工具呼叫鏈視覺化
- [ ] `pages/incidents/`：incident 列表 + 詳情 + 行動建議
- [ ] State timeline 整合（範疇 7 time-travel debug）
- [ ] Subagent tree 整合（範疇 11）

**驗收**：
- ✅ 3 個業務 frontend 頁完整可用
- ✅ a11y / i18n 通過 16-frontend-design.md 標準

### Sprint 55.3: 缺漏 6 頁前端 + DevUI（**新增**）
**工作量**：1 週

> **新增理由（PM review）**：16-frontend-design.md 列 9 個前端頁，路線圖只排到 chat（50.2）+ governance（53.4）+ agents/workflows/incidents（55.2）= 5 頁，**缺 6 頁**。本 sprint 補完。

**Deliverables**：
- [ ] `pages/memory/` — Memory inspector（5 scope × 3 time scale 雙軸瀏覽）
- [ ] `pages/audit/` — Audit log viewer（含 hash chain 驗證）
- [ ] `pages/tools/` — Tools admin（ToolSpec 配置 / version / hitl_policy）
- [ ] `pages/admin/` — Tenant / user / role 管理
- [ ] `pages/dashboard/` — KPI dashboard（usage / cost / approval / errors）
- [ ] `pages/devui/` 完整：11 範疇 + 範疇 12 成熟度 dashboard + trace_viewer 嵌入

**驗收**：
- ✅ 9 頁前端全部就緒（不含 phase 56+ saas admin）
- ✅ DevUI 11 範疇 + 範疇 12 成熟度可視化

### Sprint 55.4: 端到端整合 + 性能調優
**工作量**：1 週

**Deliverables**：
- [ ] 完整端到端測試案例：「APAC Q2 銷售下降 15% 分析」（demo case）
- [ ] 完整端到端測試案例：「Server CPU 異常 → patrol → correlation → rootcause → incident」（IT-ops case）
- [ ] 性能調優：p95 < 5s（簡單）/ < 5min（複雜）
- [ ] 負載測試：100 concurrent session / tenant
- [ ] Cost benchmark（per session avg cost）
- [ ] Multi-Provider Routing 真實切換測試（Azure OpenAI ↔ Anthropic mock）

**驗收**：
- ✅ 2 個端到端閉環測試通過
- ✅ 性能達標（p95 SLO）
- ✅ Cost per session 在預算內

### Sprint 55.5: Canary + 文件完整化 + Retro
**工作量**：1 週

**Deliverables**：
- [ ] Canary 測試（內部 1-2 用戶試用）
- [ ] API 文件完整（OpenAPI 3.0 generation）
- [ ] 操作手冊（admin / developer / end-user 三套）
- [ ] Phase 49-55 整體 retro
- [ ] **明文聲明 V2 完成 ≠ SaaS-ready**（為 Phase 56-58 鋪墊）
- [ ] V2 → V3 路線圖（如 Phase 56+ Cost Tracking 第 13 範疇 / Phase 57 多 provider 並行 / Phase 58 SaaS Stage 1）

**驗收**：
- ✅ Canary 用戶滿意度 > 80%
- ✅ 11 範疇 + 範疇 12 全部達 Level 4+（75%+ 對齊度）
- ✅ 文件 100% 涵蓋產品 surface
- ✅ Retro 產出可執行的下階段方向

---

## 風險緩解策略

### 時程超期風險
| 緩解 | 動作 |
|------|------|
| 範疇優先級 | 核心 6 個範疇（1, 2, 3, 6, 9, 11）優先；其他可砍級 |
| Scope 調整 | 每 Phase 結束 retro 檢查可否砍 scope |
| 並行開發 | 範疇間獨立性高，可平行開發（前提：合約清晰） |

### 技術風險
| 風險 | 緩解 |
|------|------|
| GPT-5.4 能力不足 | Phase 49.3 早期測試 |
| Worker queue 選錯 | Phase 49.3 PoC 對比 |
| Context rot 嚴重 | Phase 52 重點處理 |

---

## 後續 Phase（55 之後）

V2 Phase 49-55 完成後可規劃：

- **Phase 56**：性能優化 + K8s 部署
- **Phase 57**：多模型並行（Claude + GPT 切換）
- **Phase 58**：UI/UX 改進
- **Phase 59**：商業化準備（多租戶 SaaS）
- **Phase 60+**：新範疇擴展（如成本控制、A/B 測試）

---

## Sprint 文件命名規範

每個 Sprint 在 `agent-harness-planning/phase-XX-name/` 下建立：

```
phase-49-foundation/
├── sprint-49-1-plan.md           ← V1 封存 + 骨架 + CI
├── sprint-49-1-checklist.md
├── sprint-49-2-plan.md           ← DB Schema + ORM 核心
├── sprint-49-2-checklist.md
├── sprint-49-3-plan.md           ← RLS + Audit + Qdrant 隔離
├── sprint-49-3-checklist.md
├── sprint-49-4-plan.md           ← Adapters + Worker queue + OTel + Lint
└── sprint-49-4-checklist.md

phase-51-tools-memory/
├── sprint-51-0-plan.md           ← Mock 工具 + 業務骨架（新增）
├── sprint-51-1-plan.md           ← 範疇 2
└── sprint-51-2-plan.md           ← 範疇 3

phase-53-state-error-guardrails/
├── sprint-53-1-plan.md           ← 範疇 7
├── sprint-53-2-plan.md           ← 範疇 8
├── sprint-53-3-plan.md           ← 範疇 9 核心
└── sprint-53-4-plan.md           ← Governance Frontend + HITL（新增）

phase-55-production/
├── sprint-55-1-plan.md           ← 業務 backend
├── sprint-55-2-plan.md           ← 業務 frontend
├── sprint-55-3-plan.md           ← 缺漏 6 頁（新增）
├── sprint-55-4-plan.md           ← E2E + 性能
└── sprint-55-5-plan.md           ← Canary + 文件 + Retro
```

執行紀錄在 `agent-harness-execution/phase-49/sprint-49-1/`：
```
phase-49/
└── sprint-49-1/
    ├── progress.md           ← 每日進度
    ├── retrospective.md      ← Sprint 回顧
    └── artifacts/            ← 產出文件
```

---

## 下一步

1. 確認本路線圖
2. 啟動 Phase 49 Sprint 49.1
3. 建立 `phase-49-foundation/sprint-49-1-plan.md` + `sprint-49-1-checklist.md`
