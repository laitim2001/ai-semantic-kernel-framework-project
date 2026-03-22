# 現有架構完整盤點

## 日期：2026-03-22
## 目的：Phase 42-43 後的完整系統狀態

---

## 雙架構並存

### 舊架構：HybridOrchestratorV2（Phase 13，Sprint 132 deprecated）
- 檔案：`backend/src/integrations/hybrid/orchestrator_v2.py` (~1,254 LOC)
- 狀態：**已棄用** — 內部委派到 OrchestratorMediator
- 仍被使用：`api/v1/ag-ui/` 和 `api/v1/hybrid/` 端點

### 新架構：OrchestratorMediator（Phase 39，目前主要）
- 檔案：`backend/src/integrations/hybrid/orchestrator/mediator.py`
- 使用：`api/v1/orchestrator/chat` 和 `/chat/stream` 端點

---

## API 路由對照表

| 路由 | 編排器 | Bridge |
|------|--------|--------|
| `POST /ag-ui` (SSE) | HybridOrchestratorV2 → Mediator | HybridEventBridge |
| `POST /orchestrator/chat` | Mediator（直接） | 無 |
| `POST /orchestrator/chat/stream` | Mediator + PipelineEventEmitter | 自建 SSE |
| `POST /hybrid/execute` | HybridOrchestratorV2 | 無 |

---

## Mediator 7-Handler Pipeline

```
1. ContextHandler     → HybridContext 初始化 + 記憶注入
2. RoutingHandler     → InputGateway + BusinessIntentRouter + FrameworkSelector
3. DialogHandler      → GuidedDialogEngine (條件性 short-circuit)
4. ApprovalHandler    → RiskAssessor + HITLController (條件性 short-circuit)
5. AgentHandler       → LLM + function calling (條件性 short-circuit)
6. ExecutionHandler   → MAF / Claude / Swarm 三路分發
7. ObservabilityHandler → 指標收集 + Checkpoint
```

---

## MAF Builders（24 個，全部 REAL）

| 編排模式 | Builder | MAF 類別 | 使用狀態 |
|---------|---------|---------|---------|
| Sequential | WorkflowExecutorAdapter | WorkflowBuilder | ✅ WORKFLOW_MODE 使用 |
| Concurrent | ConcurrentBuilderAdapter | ConcurrentBuilder | ✅ 存在未接入 |
| GroupChat | GroupChatBuilderAdapter | GroupChatBuilder | ✅ 有獨立 API |
| Handoff | HandoffBuilderAdapter | HandoffBuilder | ✅ 存在未接入 |
| MagenticOne | MagenticBuilderAdapter | MagenticBuilder | ✅ 存在未接入 |

---

## orchestration/ 層（Phase 28，39 檔案）

全部自研業務邏輯，不包裝 MAF：

| 子模組 | 核心類別 | 消費者 |
|--------|---------|--------|
| intent_router/ | BusinessIntentRouter（三層路由） | RoutingHandler |
| guided_dialog/ | GuidedDialogEngine（多輪對話） | DialogHandler |
| input_gateway/ | InputGateway（來源識別） | RoutingHandler |
| risk_assessor/ | RiskAssessor（7 維度） | ApprovalHandler |
| hitl/ | HITLController（審批管理） | ApprovalHandler |
| audit/ | AuditLogger | ObservabilityHandler |

---

## LLM 層

| 檔案 | 角色 |
|------|------|
| `llm/protocol.py` | LLMServiceProtocol (generate + generate_structured + chat_with_tools) |
| `llm/azure_openai.py` | AzureOpenAILLMService（唯一生產實作） |
| `llm/factory.py` | LLMServiceFactory（只支援 azure/mock） |
| `llm/mock.py` | MockLLMService（測試用） |
| `llm/cached.py` | CachedLLMService（Redis 快取包裝） |
| `claude_sdk/client.py` | AsyncAnthropic 直連（獨立路徑，不走 Protocol） |

---

## Phase 42 交付（Sprint 144-147, ~40 SP）

- FrameworkSelector 2 分類器 + Function Calling 8 tools
- Mode Selector UI (Chat/Workflow/Swarm) + force_mode
- SSE 即時串流 + PipelineEventEmitter
- HITL 審批（SSE + asyncio.Event）
- AgentSwarmPanel 嵌入 Chat
- Session 持久化 + Checkpoint
- REFACTOR-001 LLMServiceProtocol.chat_with_tools()
- AG-UI 事件映射 + Bootstrap 修復

## Phase 43 交付（Sprint 148, 部分）

- TaskDecomposer + 5 Worker Roles
- SwarmWorkerExecutor（真實 LLM + function calling）
- asyncio.gather 並行（Semaphore 控制）
- 4 Worker 卡片在 Chat 中顯示

## Phase 43 未完成

- Worker 內容為空問題（3/4 專家）
- WorkerDetailDrawer 真實數據
- 結果整合（ResultAggregator）
- 整體評估：自建 Swarm 不應繼續，改用 MAF MagenticOne

---

## 待解決的架構債務

1. **SSE 雙軌**：PipelineEventEmitter（自建）vs AG-UI Protocol（標準）
2. **MediatorEventBridge 閒置**：Sprint 135 建來取代 HybridEventBridge，但未遷移
3. **AG-UI 路由仍經 V2**：未完成遷移到 Mediator
4. **Swarm 完全自建**：未使用 MAF GroupChat/MagenticOne
5. **LLM 單 Provider**：只有 Azure OpenAI，沒有 Anthropic
