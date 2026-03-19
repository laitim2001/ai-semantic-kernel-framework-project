# IPA Platform — Expected End-to-End Workflow Baseline

**Version**: 1.0
**Date**: 2026-03-19
**Purpose**: 作為端到端整合測試的基準文件，定義平台預期的完整工作流程
**Author**: Product Owner + AI Assistant

---

## 目錄

1. [流程總覽](#1-流程總覽)
2. [Step 1: 多入口 + 統一 Input Gateway + 用戶認證](#step-1-多入口--統一-input-gateway--用戶認證)
3. [Step 2: 併發 Session 管理](#step-2-併發-session-管理)
4. [Step 3: 三層意圖路由 + 風險評估](#step-3-三層意圖路由--風險評估)
5. [Step 4: Orchestrator Agent 編排決策](#step-4-orchestrator-agent-編排決策)
6. [Step 5: 任務分發到 Worker](#step-5-任務分發到-worker)
7. [Step 6: 子 Agent MCP 工具調用](#step-6-子-agent-mcp-工具調用)
8. [Step 7: 全程可觀測 + AG-UI 即時串流](#step-7-全程可觀測--ag-ui-即時串流)
9. [Step 8: 結果整合 + 統一回應](#step-8-結果整合--統一回應)
10. [Step 9: Session Resume + Checkpointing](#step-9-session-resume--checkpointing)
11. [Step 10: 記憶 + 知識 (Agentic RAG)](#step-10-記憶--知識-agentic-rag)
12. [端到端流程圖](#端到端流程圖)
13. [測試場景定義](#測試場景定義)
14. [驗收標準矩陣](#驗收標準矩陣)

---

## 1. 流程總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IPA Platform 端到端預期工作流程                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ① 多入口 (Web UI / API / ServiceNow / Prometheus)                         │
│       │                                                                     │
│       ↓                                                                     │
│  ② Input Gateway (統一標準化) → JWT 認證 → Session 管理 (CRUD)              │
│       │                              ↕ 併發 (多用戶 / 多 Session)           │
│       ↓                                                                     │
│  ③ 三層意圖路由 (Pattern→Semantic→LLM) + RiskAssessor (7維度)               │
│       │                              → 高風險? → HITL 審批                  │
│       ↓                                                                     │
│  ④ Orchestrator Agent (守門人/分流者)                                       │
│       │  判斷: 直接回答? 結構化任務? Extended Thinking? 混合? 群集?          │
│       │  底層: Checkpoint + Audit + AG-UI + ContextBridge                   │
│       ↓                                                                     │
│  ⑤ 任務分發                                                                │
│       ├─→ 直接回應 (簡單問答)                                               │
│       ├─→ MAF Workflow Engine (結構化任務)                                  │
│       ├─→ Claude Worker Pool (開放式推理)                                   │
│       └─→ Swarm Engine (多 Agent 協作)                                     │
│              │                                                              │
│              ↓                                                              │
│  ⑥ 子 Agent 工具調用 (統一 MCP 工具層)                                     │
│       │  Azure / Filesystem / LDAP / Shell / SSH / n8n / D365               │
│       ↓                                                                     │
│  ⑦ 全程可觀測 (AG-UI SSE 即時串流 + Swarm 事件 + 思考過程)                 │
│       │                                                                     │
│       ↓                                                                     │
│  ⑧ 結果整合 (LLM 綜合多 Worker 結果) → 統一回應用戶                        │
│       │                                                                     │
│       ↓                                                                     │
│  ⑨ Checkpointing (三層: L1 Redis / L2 PostgreSQL / L3 PostgreSQL)          │
│       │  Session 關閉 → 重開 → Resume 背景任務                             │
│       ↓                                                                     │
│  ⑩ 記憶 + 知識                                                             │
│       ├─ Working Memory (Redis 30min) → Session Memory (PG 7d)             │
│       ├─ Long-term Memory (mem0 + Qdrant) ← 自動摘要寫入                   │
│       ├─ RAG Pipeline (文檔→Chunk→Embed→向量索引→檢索→Rerank)              │
│       └─ Agent Skills (ITIL SOP 知識包)                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: 多入口 + 統一 Input Gateway + 用戶認證

### 預期行為

- 平台提供多種入口：Web UI（React Chat）、REST API、ServiceNow Webhook、Prometheus Alert
- 所有入口的請求經過 **InputGateway** 統一標準化為 `PipelineRequest` 格式
- 用戶通過 **JWT 認證** 登入平台，獲取 token
- 認證後用戶可以 **建立/繼續/刪除** 與 Orchestrator Agent 的對話 Session
- 每個 Session 綁定用戶身份，確保資料隔離

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| InputGateway | `integrations/orchestration/input_gateway/gateway.py` | 多源請求標準化 |
| Auth API | `api/v1/auth/routes.py` | JWT 認證（login/register/refresh） |
| Session CRUD | `api/v1/sessions/routes.py` | Session 生命週期管理 |
| SessionFactory | `integrations/hybrid/orchestrator/session_factory.py` | 每 Session 獨立 Mediator |
| PipelineRequest | `integrations/contracts/pipeline.py` | 統一請求格式 |

### 測試要點

- [ ] 用戶可以 POST /auth/login 取得 JWT token
- [ ] 帶 JWT 可以 POST /sessions 建立新 Session
- [ ] 帶 JWT 可以 GET /sessions 列出自己的 Sessions
- [ ] 帶 JWT 可以 DELETE /sessions/{id} 刪除 Session
- [ ] InputGateway 能接收 USER / SERVICENOW / PROMETHEUS 三種來源
- [ ] 未認證請求被 401 拒絕

---

## Step 2: 併發 Session 管理

### 預期行為

- 多個用戶可以 **同時** 與平台對話，每個用戶有獨立的 Session
- 系統使用 **async/await** (FastAPI + uvicorn) 處理併發請求
- **LLMCallPool** 控制 LLM API 併發上限（asyncio.Semaphore），防止 API 過載
- **SessionFactory** 為每個 Session 建立獨立的 OrchestratorMediator 實例
- 共享全域資源（LLM pool、Tool Registry）但隔離 Session 狀態

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| LLMCallPool | `core/performance/llm_pool.py` | 併發控制 + 優先級佇列 |
| SessionFactory | `integrations/hybrid/orchestrator/session_factory.py` | LRU Session 管理 |
| OrchestratorBootstrap | `integrations/hybrid/orchestrator/bootstrap.py` | 全域組件組裝 |

### 測試要點

- [ ] 同時發送 5 個不同 session_id 的 /orchestrator/chat 請求，全部成功返回
- [ ] LLMCallPool 的 Semaphore 限制同時 LLM 呼叫數量
- [ ] Session A 的狀態不影響 Session B
- [ ] SessionFactory 在達到 max_sessions 時正確 LRU 淘汰

---

## Step 3: 三層意圖路由 + 風險評估

### 預期行為

- 用戶輸入進入 **三層意圖路由系統**：
  - **L1 PatternMatcher** (< 10ms): 規則匹配已知模式（如「重啟」→ INCIDENT）
  - **L2 SemanticRouter** (< 100ms): 語義相似度匹配
  - **L3 LLMClassifier** (< 2000ms): LLM 作為最終分類器
- 路由結果包含：意圖類別、子意圖、信心度、風險等級、路由層級
- **RiskAssessor** 對用戶輸入進行 7 維度風險評估
- 高風險操作自動觸發 **HITL 審批**，用戶需等待人工審批才能繼續
- 風險評估結果包含：overall_level (LOW/MEDIUM/HIGH/CRITICAL)、score、requires_approval

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| BusinessIntentRouter | `integrations/orchestration/intent_router/router.py` | 三層路由協調 |
| RiskAssessor | `integrations/orchestration/risk_assessor/assessor.py` | 風險評估 |
| HITLController | `integrations/orchestration/hitl/controller.py` | 審批流程 |
| RoutingHandler | `integrations/hybrid/orchestrator/handlers/routing.py` | Pipeline 路由步驟 |
| ApprovalHandler | `integrations/hybrid/orchestrator/handlers/approval.py` | Pipeline 審批步驟 |

### 測試要點

- [ ] 輸入「ETL Pipeline 失敗」→ 正確識別為 INCIDENT 意圖
- [ ] 輸入「刪除生產數據庫」→ 風險評估為 CRITICAL + 觸發 HITL 審批
- [ ] 輸入「查看今天的報表」→ 風險評估為 LOW + 直接放行
- [ ] 審批 pending 狀態可透過 API 查詢
- [ ] 審批通過後任務繼續執行

---

## Step 4: Orchestrator Agent 編排決策

### 預期行為

- **Orchestrator Agent** 是整個編排層的守門人和分流者
- 它具備企業知識，了解不同類型的問題應該如何處理
- 根據路由結果，Agent 決定用哪種執行模式：
  - **直接回應**: 簡單問答，Agent 直接用 LLM 回答
  - **結構化任務 (Workflow)**: 已知模式，啟動 MAF Workflow
  - **開放式推理 (Extended Thinking)**: 複雜分析，使用 Claude 深度推理
  - **混合模式 (Hybrid)**: MAF 編排 + Claude 執行
  - **多 Agent 群集 (Swarm)**: 複雜協作任務，啟動 Swarm
- Agent 有 tool calling 能力，可調用 9+ 個工具
- 底層自動連結 Checkpointing、Audit Logger、AG-UI、ContextBridge

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| AgentHandler | `integrations/hybrid/orchestrator/agent_handler.py` | LLM 決策引擎 |
| OrchestratorMediator | `integrations/hybrid/orchestrator/mediator.py` | 7 步 Pipeline 協調 |
| FrameworkSelector | `integrations/hybrid/intent/router.py` | 執行模式選擇 |
| ToolRegistry | `integrations/hybrid/orchestrator/tools.py` | 工具目錄 + 執行 |
| ContextHandler | `integrations/hybrid/orchestrator/handlers/context.py` | 上下文管理 |
| OrchestratorBootstrap | `integrations/hybrid/orchestrator/bootstrap.py` | 全管線組裝 |

### 測試要點

- [ ] 簡單問題「你好」→ Agent 直接回應，不派發任務
- [ ] 複雜問題「分析過去一週的系統效能趨勢」→ Agent 選擇 Extended Thinking 或 Workflow
- [ ] Agent 回應包含 framework_used 欄位指示使用了哪種模式
- [ ] OrchestratorMediator 的 7 步 Pipeline 全部執行（可從 log 驗證）
- [ ] Tool Registry 列出 9+ 個可用工具

---

## Step 5: 任務分發到 Worker

### 預期行為

- 如果用戶輸入只是問題，Orchestrator Agent 直接回答
- 如果需要額外操作，Agent 透過 **dispatch tools** 分發任務：
  - `dispatch_workflow()` → MAF Workflow Engine（結構化多步驟任務）
  - `dispatch_to_claude()` → Claude Worker Pool（開放式推理）
  - `dispatch_swarm()` → Swarm Engine（多 Agent 協作）
- 每個 dispatch 建立 **Task 記錄**（TaskStore 持久化）
- Async dispatch 透過 **ARQ** 在後台 Worker 執行（脫離 HTTP 請求週期）
- 返回 `task_id` 供前端追蹤進度

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| DispatchHandlers | `integrations/hybrid/orchestrator/dispatch_handlers.py` | 9 個工具 handler |
| TaskService | `domain/tasks/service.py` | 任務 CRUD + 狀態轉換 |
| TaskStore | `infrastructure/storage/task_store.py` | 任務持久化 |
| ARQClient | `infrastructure/workers/arq_client.py` | 後台任務佇列 |
| Task API | `api/v1/tasks/routes.py` | 任務 REST API |
| ExecutionHandler | `integrations/hybrid/orchestrator/handlers/execution.py` | 框架分發 |

### 測試要點

- [ ] POST /tasks 可建立任務
- [ ] GET /tasks 可列出任務（含 status 過濾）
- [ ] dispatch_workflow 建立 Task 記錄 + 返回 task_id
- [ ] dispatch_swarm 建立 Task 記錄 + 返回 task_id
- [ ] 任務狀態從 PENDING → IN_PROGRESS → COMPLETED 正確轉換
- [ ] ARQ 可用時，任務在後台 Worker 執行

---

## Step 6: 子 Agent MCP 工具調用

### 預期行為

- 子 Agent（MAF Worker、Claude Worker、Swarm Worker）在執行任務時可調用 **MCP 工具**
- MCP 工具層提供統一的工具介面，底層連接不同的外部系統
- 工具透過 **MCPToolBridge** 動態發現並註冊到 OrchestratorToolRegistry
- 工具調用經過 **ToolSecurityGateway** 安全檢查（輸入消毒、權限驗證、速率限制）

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| MCP Core | `integrations/mcp/core/` | MCP 協議實作 |
| MCP Servers | `integrations/mcp/servers/` | 8 個 MCP 伺服器 |
| MCPToolBridge | `integrations/hybrid/orchestrator/mcp_tool_bridge.py` | MCP → ToolRegistry 橋接 |
| ToolSecurityGateway | `core/security/tool_gateway.py` | 4 層安全檢查 |
| PromptGuard | `core/security/prompt_guard.py` | Prompt Injection 防護 |

### 測試要點

- [ ] MCPToolBridge 能發現已註冊的 MCP 伺服器工具
- [ ] MCP 工具以 `mcp_{server}_{tool}` 格式出現在 ToolRegistry
- [ ] ToolSecurityGateway 攔截危險的工具參數
- [ ] 工具調用結果正確回傳到 Orchestrator

---

## Step 7: 全程可觀測 + AG-UI 即時串流

### 預期行為

- 整個對話過程中，所有事件即時串流到前端：
  - **RunStarted** → 管線開始
  - **StepStarted/Finished** → 每個 Pipeline 步驟
  - **TextMessageContent** → LLM 思考 token（增量串流）
  - **ToolCallStart/End** → 工具調用過程
  - **ApprovalRequired** → 需要人工審批
  - **RunFinished/Error** → 管線完成/錯誤
- Swarm 事件（Worker 啟動/完成/工具調用）同步串流
- **SSEEventBuffer** 支援斷線重連（Last-Event-ID 重播）
- **ObservabilityBridge** 連接 G3 Patrol / G4 Correlation / G5 RootCause

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| MediatorEventBridge | `integrations/ag_ui/mediator_bridge.py` | Mediator → AG-UI 轉換 |
| SSEEventBuffer | `integrations/ag_ui/sse_buffer.py` | 斷線重連暫存 |
| AG-UI API | `api/v1/ag_ui/routes.py` | SSE 串流端點 |
| ObservabilityHandler | `integrations/hybrid/orchestrator/handlers/observability.py` | 指標記錄 |
| ObservabilityBridge | `integrations/hybrid/orchestrator/observability_bridge.py` | G3/G4/G5 |

### 測試要點

- [ ] SSE 串流包含 RUN_STARTED → TEXT_MESSAGE_CONTENT → RUN_FINISHED 序列
- [ ] 工具調用產生 TOOL_CALL_START + TOOL_CALL_END 事件
- [ ] 斷線後重連帶 Last-Event-ID 能收到缺失的事件
- [ ] Swarm 執行時串流 Worker 狀態事件

---

## Step 8: 結果整合 + 統一回應

### 預期行為

- 如果只有一個 Worker，結果直接 pass-through 回應用戶
- 如果多個 Worker（Swarm 場景），使用 **LLM ResultSynthesiser** 綜合所有結果
- 結果透過 **TaskResultEnvelope** 標準化，包含：
  - 每個 Worker 的輸出、狀態、耗時、token 用量
  - 整體狀態（SUCCESS / PARTIAL / FAILED）
  - 綜合後的最終回應
- 最終回應通過 AG-UI SSE 串流回前端

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| ResultSynthesiser | `integrations/hybrid/orchestrator/result_synthesiser.py` | LLM 結果綜合 |
| TaskResultEnvelope | `integrations/hybrid/orchestrator/task_result_protocol.py` | 結果標準化 |
| TaskResultNormaliser | `integrations/hybrid/orchestrator/task_result_protocol.py` | MAF/Claude/Swarm 正規化 |

### 測試要點

- [ ] 單 Worker 結果直接回傳（不經 LLM 綜合）
- [ ] 多 Worker 結果經 LLM 綜合為一個連貫回應
- [ ] PARTIAL 狀態（部分 Worker 失敗）正確標記
- [ ] 回應包含 processing_time_ms 和 framework_used

---

## Step 9: Session Resume + Checkpointing

### 預期行為

- **三層 Checkpoint 系統** 自動保存狀態：
  - **L1 Conversation State** (Redis, TTL 24h): 對話消息、路由決策、審批狀態
  - **L2 Task State** (PostgreSQL, 永久): 任務記錄、進度、結果
  - **L3 Agent Execution State** (PostgreSQL, 永久): Agent 上下文、工具調用歷史
- 用戶關閉瀏覽器或 Session 斷開後：
  - **背景任務繼續執行**（透過 ARQ Worker）
  - 用戶重新打開平台，可以看到可恢復的 Sessions
  - 選擇 Resume 後，三層狀態合併恢復
- 場景範例：用戶要求 Agent 檢查資料庫 → 整理數據 → 交給某人審批。審批需要等待，用戶關閉視窗。任務在後台繼續。用戶回來後 Resume Session，看到任務進度和審批結果。

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| ConversationStateStore | `infrastructure/storage/conversation_state.py` | L1 Redis |
| TaskStore | `infrastructure/storage/task_store.py` | L2 PostgreSQL |
| ExecutionStateStore | `infrastructure/storage/execution_state.py` | L3 PostgreSQL |
| SessionRecoveryManager | `integrations/hybrid/orchestrator/session_recovery.py` | 三層恢復 |
| Session Resume API | `api/v1/orchestrator/session_routes.py` | 恢復端點 |
| ARQ Worker | `infrastructure/workers/` | 後台執行 |
| CircuitBreaker | `core/performance/circuit_breaker.py` | LLM 降級保護 |

### 測試要點

- [ ] GET /sessions/recoverable 列出有殘留狀態的 Sessions
- [ ] POST /sessions/{id}/resume 恢復 Session（回傳 layers_restored）
- [ ] 恢復後能看到之前的對話歷史（L1）
- [ ] 恢復後能看到任務進度（L2）
- [ ] 後台任務完成後，Resume 能看到結果
- [ ] CircuitBreaker 在 LLM 不可用時自動降級

---

## Step 10: 記憶 + 知識 (Agentic RAG)

### 預期行為

#### 記憶系統（三層）

- **Working Memory** (Redis, TTL 30min): 當前對話上下文、工具調用結果
- **Session Memory** (PostgreSQL, TTL 7d): 對話摘要、任務記錄
- **Long-term Memory** (mem0 + Qdrant): 永久記憶
  - **對話結束時**：自動生成結構化摘要（問題/處理/結果/教訓）寫入 Long-term
  - **新對話開始時**：自動搜索相關歷史記憶注入 Orchestrator 上下文
  - Working → Long-term 自動提升機制

#### 知識系統（Agentic RAG）

- **Agent Skills**: 結構化知識（ITIL SOP、Change Management、EA Reference）
- **Vector RAG**: 文檔 → 解析 → Chunking → Embedding → Qdrant 向量索引 → 檢索 → Reranking
- **Agentic RAG**: Orchestrator Agent **自主決定** 何時搜索知識庫（非被動觸發）
  - Agent 透過 `search_knowledge()` tool 主動查詢
  - Agent 透過 `search_memory()` tool 查詢歷史記憶
  - System Prompt 指示 Agent 在遇到專業問題時主動檢索

#### 記憶展現場景

```
用戶: 「你好，上次提到的 Pipeline 問題解決了嗎？」

Orchestrator (自動檢索記憶):
  → mem0 搜索: "Pipeline 問題" + user_id
  → 找到: "2026-03-15 CI/CD Pipeline timeout，原因是 Docker image 過大"

Orchestrator 回覆:
  「你好！上次您提到 CI/CD Pipeline timeout 的問題，我們分析後發現是
   Docker image 過大導致的，建議採用分層建構策略。請問效果如何？」
```

### 涉及組件

| 組件 | 檔案路徑 | 角色 |
|------|---------|------|
| OrchestratorMemoryManager | `integrations/hybrid/orchestrator/memory_manager.py` | 自動摘要 + 檢索注入 |
| UnifiedMemoryManager | `integrations/memory/unified_memory.py` | 三層記憶管理 |
| RAGPipeline | `integrations/knowledge/rag_pipeline.py` | 端到端 RAG |
| DocumentParser | `integrations/knowledge/document_parser.py` | 多格式解析 |
| KnowledgeRetriever | `integrations/knowledge/retriever.py` | Hybrid 搜索 + Reranking |
| AgentSkillsProvider | `integrations/knowledge/agent_skills.py` | ITIL SOP 知識包 |
| Knowledge API | `api/v1/knowledge/routes.py` | 知識庫 CRUD |

### 測試要點

- [ ] POST /knowledge/ingest 可匯入文檔到向量庫
- [ ] POST /knowledge/search 可搜索知識庫
- [ ] GET /knowledge/skills 列出 3 個 ITIL 技能
- [ ] 新對話時 ContextHandler 自動注入相關記憶到 context
- [ ] 對話結束後自動生成摘要寫入 Long-term Memory
- [ ] Agent 能自主調用 search_knowledge 和 search_memory

---

## 端到端流程圖

### 完整 10 步流程

```
Step 1          Step 2          Step 3          Step 4
  │               │               │               │
  ↓               ↓               ↓               ↓
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐
│Web UI│    │  Session  │    │ 3-Layer  │    │ Orchestrator │
│API   │───▶│  Factory  │───▶│ Routing  │───▶│    Agent     │
│SNOW  │    │  (JWT)    │    │ + Risk   │    │  (守門人)    │
│Prom  │    │  併發     │    │ + HITL   │    │              │
└──────┘    └──────────┘    └──────────┘    └──────┬───────┘
                                                    │
                                     ┌──────────────┼──────────────┐
                                     │              │              │
Step 5                               ↓              ↓              ↓
                              ┌──────────┐  ┌──────────┐  ┌──────────┐
                              │   MAF    │  │  Claude  │  │  Swarm   │
                              │ Workflow │  │ Workers  │  │  Engine  │
                              └────┬─────┘  └────┬─────┘  └────┬─────┘
                                   │             │             │
Step 6                             ↓             ↓             ↓
                              ┌─────────────────────────────────────┐
                              │        MCP 統一工具層                │
                              │  Azure│File│LDAP│Shell│SSH│n8n│D365 │
                              └───────────────────┬─────────────────┘
                                                  │
Step 7                        ┌───────────────────┤
                              │                   │
                              ↓                   ↓
                        ┌──────────┐        ┌──────────┐
                        │ AG-UI    │        │ Observ-  │
                        │ SSE 串流 │        │ ability  │
                        └──────────┘        └──────────┘
                                                  │
Step 8                                            ↓
                                          ┌──────────────┐
                                          │   Result     │
                                          │ Synthesiser  │
                                          │  → 統一回應  │
                                          └──────┬───────┘
                                                  │
Step 9-10                                         ↓
                                   ┌──────────────┼──────────────┐
                                   ↓              ↓              ↓
                            ┌──────────┐  ┌──────────┐  ┌──────────┐
                            │Checkpoint│  │  Memory  │  │Knowledge │
                            │ L1/L2/L3 │  │ 三層記憶 │  │ RAG+SOP  │
                            │ + Resume │  │ + 摘要   │  │ + Skills │
                            └──────────┘  └──────────┘  └──────────┘
```

---

## 測試場景定義

### Scenario A: 簡單問答（Step 1→3→4→8）

```
前置: 用戶已登入
輸入: 「你好，今天系統正常嗎？」
預期:
  1. InputGateway 接收請求
  2. L1 Pattern 匹配: GENERAL_INQUIRY
  3. Risk: LOW → 直接放行
  4. Orchestrator Agent 直接 LLM 回答
  5. AG-UI SSE 串流回應
  6. 不觸發任務派發
```

### Scenario B: 結構化任務（Step 1→3→4→5→6→7→8）

```
前置: 用戶已登入
輸入: 「請幫我檢查 Production DB 的連線狀態」
預期:
  1. 意圖: SYSTEM_MONITORING
  2. Risk: MEDIUM → Quick Review 放行
  3. Orchestrator 決定: Workflow 模式
  4. dispatch_workflow("db_health_check") → task_id
  5. MAF Workflow 調用 MCP Shell 工具: ping + SQL check
  6. AG-UI 串流工具調用進度
  7. 結果整合後回應用戶
```

### Scenario C: 高風險操作 + HITL（Step 1→3→審批→4→5→8）

```
前置: 用戶已登入
輸入: 「刪除 staging 環境的舊數據」
預期:
  1. 意圖: DATA_MANAGEMENT
  2. Risk: HIGH → 需要審批
  3. HITL 審批請求發送
  4. AG-UI 推送 ApprovalRequired 事件
  5. 審批通過後 → Orchestrator 執行
  6. 結果回應用戶
```

### Scenario D: Swarm 協作（Step 1→3→4→5→6→7→8）

```
前置: 用戶已登入
輸入: 「全面分析過去一週的系統問題，包括 log 分析、效能數據和告警統計」
預期:
  1. 意圖: COMPLEX_ANALYSIS
  2. Orchestrator 決定: Swarm 模式
  3. dispatch_swarm() → 3 個 Worker: LogAnalyzer + PerfAnalyzer + AlertAnalyzer
  4. 每個 Worker 調用不同 MCP 工具
  5. AG-UI 串流 Swarm 進度事件
  6. ResultSynthesiser 綜合 3 個結果
  7. 統一回應用戶
```

### Scenario E: Session Resume（Step 9）

```
前置: Scenario B 執行中，用戶關閉瀏覽器
步驟:
  1. 任務在 ARQ Worker 繼續執行
  2. 用戶重新登入
  3. GET /sessions/recoverable → 看到之前的 Session
  4. POST /sessions/{id}/resume → L1+L2+L3 恢復
  5. 看到任務進度和結果
```

### Scenario F: 跨 Session 記憶（Step 10）

```
Session 1:
  用戶: 「CI/CD Pipeline 超時了」
  Agent: 「建議檢查 Docker image 大小...」
  (對話結束 → 自動摘要寫入 Long-term Memory)

Session 2 (隔天):
  用戶: 「上次說的 Pipeline 問題」
  Agent (自動檢索記憶):
    「您好！上次提到 CI/CD Pipeline timeout，原因是 Docker image 過大...」
```

---

## 驗收標準矩陣

| # | 驗收項目 | 依賴服務 | 優先級 |
|---|---------|---------|--------|
| 1 | JWT 認證 → Session CRUD → Orchestrator Chat 端到端 | PG | P0 |
| 2 | 5 個併發 Session 同時回應 | PG + Redis | P0 |
| 3 | 三層意圖路由正確分類 | LLM API | P0 |
| 4 | 高風險操作觸發 HITL 審批 | PG | P1 |
| 5 | Orchestrator Agent 直接回答簡單問題 | LLM API | P0 |
| 6 | dispatch_workflow 建立 Task + 返回 task_id | PG | P1 |
| 7 | dispatch_swarm 啟動多 Worker 協作 | Redis | P1 |
| 8 | MCP 工具可被 Agent 動態調用 | 依工具 | P2 |
| 9 | ToolSecurityGateway 攔截危險操作 | 無 | P1 |
| 10 | AG-UI SSE 串流完整事件序列 | 無 | P0 |
| 11 | 斷線重連不丟事件 (Last-Event-ID) | Redis | P2 |
| 12 | ResultSynthesiser 綜合多結果 | LLM API | P1 |
| 13 | Session Resume 三層恢復 | PG + Redis | P1 |
| 14 | 後台任務繼續執行 (ARQ) | Redis | P2 |
| 15 | 自動摘要寫入 Long-term Memory | Qdrant | P2 |
| 16 | 新對話自動注入相關記憶 | Qdrant | P2 |
| 17 | search_knowledge 搜索知識庫 | Qdrant | P2 |
| 18 | Agent Skills (ITIL SOP) 可查詢 | 無 | P1 |

---

**文件用途**: 作為 E2E 整合測試的 baseline，定義「平台應該怎麼工作」。所有測試場景和驗收標準應基於此文件展開。
