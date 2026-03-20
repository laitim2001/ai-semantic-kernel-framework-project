# Phase 42: E2E Pipeline Deep Integration — SSE + Task Dispatch + Swarm UI

## 概述

Phase 41 完成了 Chat Pipeline 的基礎接通（7 Handler 連接、IntentStatusChip、記憶系統），但經過詳細分析發現**核心架構缺口**：Pipeline 使用同步 POST 而非 SSE 串流，導致多個關鍵功能無法運作。

Phase 42 專注於**修復這些深層整合問題**，讓 10 步 E2E 流程真正端到端可運作。

> **Status**: 📋 規劃中 — 4 Sprints (144-147), ~40 SP

## 核心問題（Phase 41 後的 Gap 分析）

### 根因：同步 POST vs SSE 串流

Phase 41 將 Chat 接到 `/orchestrator/chat`（同步 POST），收到完整回應後用 typewriter 模擬串流。這破壞了：

| 功能 | 預期行為 | 實際行為 | 根因 |
|------|---------|---------|------|
| SSE 即時串流 | 逐 token 串流 | 同步等待 + 假打字 | 用 POST 不用 SSE |
| HITL 審批 | 中途暫停等審批 | 無法暫停 | 同步不可中斷 |
| Swarm 進度 | 即時顯示 Worker 狀態 | 無顯示 | swarmStore 未被填充 |
| 工具調用追蹤 | 即時顯示執行中 | 只顯示完成後 | 同步回傳全部結果 |
| 任務分發 | 顯示 TaskProgressCard | 無 task_id | AgentHandler 全 short-circuit |

### 10 步流程整合狀態

| 步驟 | 功能 | 後端 | 前端 | 綜合 |
|------|------|------|------|------|
| ① 多入口 + Gateway | InputGateway | PARTIAL | N/A | ⚠️ |
| ② Session 管理 | CRUD + 持久化 | PARTIAL（記憶體） | INTEGRATED | ⚠️ |
| ③ 三層路由 + 風險 | Pattern→Semantic→LLM + 7維度 | PARTIAL（Semantic 需訓練、風險簡化） | INTEGRATED（IntentStatusChip）| ⚠️ |
| ④ Orchestrator 決策 | 5 種分發模式 | PARTIAL（FrameworkSelector 全歸 CHAT） | PARTIAL（OrchestrationPanel 空閒）| ❌ |
| ⑤ 任務分發 | MAF/Claude/Swarm | PARTIAL（連接但不觸發） | PARTIAL（TaskProgressCard 就緒）| ❌ |
| ⑥ MCP 工具調用 | 8 個工具 | REGISTERED（未被 pipeline 調用） | PARTIAL（ToolCallTracker 就緒）| ❌ |
| ⑦ SSE 串流 | AG-UI 即時事件 | NOT_CONNECTED | NOT_INTEGRATED（用 typewriter）| ❌ |
| ⑧ 結果整合 | 多 Worker 結果合併 | PARTIAL | INTEGRATED（MessageList）| ⚠️ |
| ⑨ Session Resume | 恢復 + Checkpoint | PARTIAL（對話恢復、無 pipeline 狀態）| PARTIAL | ⚠️ |
| ⑩ 記憶 + 知識 | mem0 + RAG | CONNECTED（mem0）/ REGISTERED（RAG）| INTEGRATED（MemoryHint）| ⚠️ |

## 架構方案

### 方案 A（選用）：Orchestrator SSE 端點

新增 `POST /orchestrator/chat/stream` SSE 端點，mediator pipeline 每個步驟發送事件：

```
PIPELINE_START → ROUTING_COMPLETE → APPROVAL_REQUIRED → AGENT_THINKING →
TOOL_CALL_START → TOOL_CALL_END → TEXT_DELTA → TASK_DISPATCHED →
SWARM_WORKER_START → SWARM_PROGRESS → PIPELINE_COMPLETE
```

前端用 `EventSource` 或 `ReadableStream` 接收，即時更新 UI。

### 方案 B（備選）：AG-UI 事件橋接

利用現有 AG-UI SSE 基礎設施（`MediatorEventBridge`），將 mediator 事件映射到 AG-UI 協議事件。

## Sprint 規劃

| Sprint | 名稱 | Story Points | 重點 |
|--------|------|-------------|------|
| [Sprint 144](./sprint-144-plan.md) | FrameworkSelector 智能分發 + 任務創建 | ~10 | 讓複雜任務走 WORKFLOW/SWARM mode |
| [Sprint 145](./sprint-145-plan.md) | Orchestrator SSE 串流端點 | ~12 | 後端 SSE + 前端接收即時事件 |
| [Sprint 146](./sprint-146-plan.md) | Swarm UI 整合 + HITL 審批 | ~10 | AgentSwarmPanel 在 Chat + 審批流程 |
| [Sprint 147](./sprint-147-plan.md) | RAG Pipeline + Checkpoint + QA | ~8 | 知識檢索 + 狀態持久化 + 完整驗證 |

**總計**: ~40 Story Points (4 Sprints)

## Sprint 144: FrameworkSelector 智能分發 + 任務創建

### 目標
讓 FrameworkSelector 能根據用戶輸入的複雜度正確判斷 CHAT_MODE vs WORKFLOW_MODE vs SWARM，並在 WORKFLOW/SWARM 時實際創建任務和分發。

### User Stories

**S144-1: FrameworkSelector 規則增強 (4 SP)**
- 新增 LLM-based intent analysis（不只是規則匹配）
- 關鍵字識別：「同時」「並行」「多個」→ SWARM_MODE
- 關鍵字識別：「建立」「執行」「部署」「檢查所有」→ WORKFLOW_MODE
- 只有純問答/閒聊才保持 CHAT_MODE
- SwarmModeHandler.analyze_for_swarm() 正確觸發

**S144-2: ExecutionHandler 實際分發 (3 SP)**
- WORKFLOW_MODE → 創建 Task + 調用 MAF executor
- SWARM_MODE → 創建 Swarm session + 分發到多個 Worker
- 返回 task_id/swarm_id 到 PipelineResponse

**S144-3: TaskService 整合 (3 SP)**
- Pipeline 中創建的任務寫入 TaskStore
- 任務狀態更新（running → completed/failed）
- 前端 TaskProgressCard 能讀取真實任務

## Sprint 145: Orchestrator SSE 串流端點

### 目標
新增 SSE 串流端點，Pipeline 每個步驟即時推送事件到前端。

### User Stories

**S145-1: 後端 SSE 端點 (5 SP)**
- `POST /orchestrator/chat/stream` → SSE EventSource
- Mediator pipeline 每步發送事件（routing、approval、agent、execution）
- 事件格式對齊 AG-UI 協議

**S145-2: 前端 SSE 接收 (4 SP)**
- UnifiedChat 改用 SSE 端點（取代同步 POST）
- 即時更新 IntentStatusChip、ToolCallTracker、MessageList
- 移除 typewriter 假串流，改用真實 token streaming

**S145-3: AG-UI 事件橋接 (3 SP)**
- MediatorEventBridge 將 pipeline 事件映射到 AG-UI 事件
- 統一事件格式，支援前端重用

## Sprint 146: Swarm UI 整合 + HITL 審批

### 目標
在 Chat 中顯示 Swarm 多 Worker 執行視覺化，並啟用 HITL 審批流程。

### User Stories

**S146-1: AgentSwarmPanel 嵌入 Chat (4 SP)**
- Swarm 事件填充 swarmStore（透過 SSE）
- UnifiedChat 顯示 AgentSwarmPanel（右側/下方）
- WorkerCard 即時更新進度

**S146-2: HITL 審批流程 (3 SP)**
- 高風險操作暫停 Pipeline 等待審批
- SSE 推送 APPROVAL_REQUIRED 事件
- InlineApproval 在 Chat 中渲染，用戶批准/拒絕
- 批准後 Pipeline 繼續執行

**S146-3: DialogHandler 修復 (3 SP)**
- 修復 GuidedDialogEngine 初始化（缺 router 參數）
- 修復 HITLController 初始化（缺 storage 參數）
- 對話引導流程在 Chat 中可視化

## Sprint 147: RAG Pipeline + Checkpoint + QA

### 目標
連接 RAG 知識檢索、實現 Checkpoint 持久化、完整 E2E 驗證。

### User Stories

**S147-1: RAG Pipeline 連接 (3 SP)**
- search_knowledge 工具在 pipeline 中可調用
- 知識檢索結果注入 LLM prompt
- 前端顯示知識來源引用

**S147-2: Checkpoint 持久化 (3 SP)**
- Pipeline 執行中自動保存 Checkpoint
- Session Resume 恢復 Pipeline 狀態（不只是對話歷史）
- 使用 PostgreSQL backend（取代 in-memory）

**S147-3: E2E 完整驗證 (2 SP)**
- 6 個 Scenario (A-F) 全部在 Chat 中可演示
- 10 步流程全部有可視化對應
- Playwright 自動化測試

## 前置條件

- ✅ Phase 41 — Chat Pipeline 基礎接通（7 Handler）
- ✅ 記憶系統啟用（mem0 + Redis）
- ✅ 三層路由 + IntentStatusChip
- ✅ semantic-router 已安裝
- ✅ ExecutionHandler: claude=True, maf=True, swarm=True

## 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| SSE 端點改動大 | 高 | 漸進式：先加 SSE 端點，保留 POST fallback |
| Swarm 實際執行複雜 | 中 | 先用模擬 Worker，後接真實 Agent |
| FrameworkSelector 分類不準 | 中 | 加 LLM fallback + 用戶可手動選模式 |
| HITL 暫停機制需改 mediator | 中 | 用 async event + callback pattern |

---

**Phase 42 前置**: Phase 41 (Chat Pipeline Integration)
**總 Story Points**: ~40 pts
**Sprint 範圍**: Sprint 144-147
**技術棧**: FastAPI SSE + React EventSource + Zustand + AG-UI Protocol
