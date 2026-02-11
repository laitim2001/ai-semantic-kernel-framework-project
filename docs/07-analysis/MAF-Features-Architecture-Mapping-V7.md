# 智能體編排平台功能架構映射指南

> **文件版本**: 7.0
> **最後更新**: 2026-02-11
> **定位**: Agent Orchestration Platform (智能體編排平台)
> **前置文件**: `MAF-Claude-Hybrid-Architecture-V7.md` (架構總覽)
> **狀態**: Phase 29 已完成 (106 Sprints, ~2400 Story Points)
> **驗證方式**: Agent Team (5 分析 Agent + 3 交叉驗證 Agent) 並行深度代碼庫驗證
> **前版**: V6.0 (2026-02-11), V3.0 (2026-02-09)

---

## 實現狀態總覽

> **重要說明**: 本文件是 V6 (64 功能, 2026-02-11) 的格式重整與數據修正版本。
> V7 維持 **64 個功能**，修正 V6 中的 2 個小差異 (>800 行檔案數 57→58, 端點數 530→528)。
> Backend LOC 從 V6 的 ~130,000 修正為 **~228,700** (V6 因 Windows 環境 xargs 截斷嚴重低估)。
> 基於 2026-02-11 的代碼庫由 5+3 個分析/交叉驗證 Agent 逐一驗證，所有檔案行數均為實測值。

### 64 功能驗證結果

| 狀態 | 數量 | 比例 | 說明 |
|------|------|------|------|
| ✅ 完整實現 | 54 | 84.4% | 代碼庫中有完整實現 (含 REAL+MOCK fallback) |
| ⚠️ 部分實現 | 2 | 3.1% | 有代碼結構但數據來源為硬編碼/模擬 |
| ❌ 未找到 | 1 | 1.6% | 缺乏獨立實現或依賴未安裝 |
| ✅ 擴展功能 | 7 | 10.9% | Builder 擴展功能，非獨立 feature |
| | **64** | **95.3% 至少部分** | |

### 按類別統計

| 類別 | 功能數 | ✅ | ⚠️ | ❌ | 實現率 |
|------|--------|-----|-----|-----|--------|
| Agent 編排能力 | 16 | 16 | 0 | 0 | 100% |
| 人機協作能力 | 7 | 7 | 0 | 0 | 100% |
| 狀態與記憶能力 | 5 | 5 | 0 | 0 | 100% |
| 前端介面能力 | 8 | 7 | 0 | 1 | 87.5% 完整 |
| 連接與整合能力 | 11 | 11 | 0 | 0 | 100% |
| 智能決策能力 | 10 | 10 | 0 | 0 | 100% |
| 可觀測性能力 | 5 | 3 | 2 | 0 | 60% 完整 |
| **Agent Swarm 能力** | **6** | **6** | **0** | **0** | **100%** |

> **V3→V7 類別對照**: V3 可觀測性有 6 功能 (#54-#59)，V6/V7 將 #59 Agent Templates 歸入前端介面，
> Observability 調整為 5 功能。V3 功能 #42 Cross-scenario 在 V6/V7 中被合併進 A2A Protocol (#46)。

### V6 → V7 狀態變更

| 指標 | V6 數值 | V7 數值 | 變更原因 |
|------|---------|---------|----------|
| 功能總數 | 64 | **64** | 不變 |
| Backend LOC | ~130,000+ | **~228,700** | V6 xargs 截斷導致嚴重低估 |
| API 端點 | 530 | **528** | 排除 docstring 中的 decorator |
| >800 行檔案 | 57 | **58** | 重新統計 50 backend + 8 frontend |
| Checkpoint 系統 | 2 (dual) | **4 (quad)** | 實際有 4 個獨立系統 |
| 功能分類 | V6 英文 | **V7 繁體中文** | 格式對齊 V3 |

---

## 執行摘要

IPA Platform 是一個**智能體編排平台 (Agent Orchestration Platform)**，透過 MAF + Claude Agent SDK 混合架構，協調智能體集群處理需要判斷力、專業知識與人機互動的複雜任務。

**64 個功能**構成平台的八大能力領域：

1. **Agent 編排** (16 功能) --- 9 個 Builder adapter + 7 個擴展，全部基於 MAF Builder (8/9 有 MAF import)
2. **人機協作** (7 功能) --- 完整 HITL 生命週期：檢查點 → 審批 → 通知 → 前端介面
3. **狀態與記憶** (5 功能) --- Redis/Postgres 檢查點 + 3 層統一記憶 (Redis→PostgreSQL→mem0+Qdrant)
4. **前端介面** (8 功能) --- 39 頁面 + Unified Chat + DevUI + Dashboard + Auth
5. **連接與整合** (11 功能) --- InputGateway + 5 個 MCP Server + A2A Protocol
6. **智能決策** (10 功能) --- 三層意圖路由 (已支援真實 LLM) + 自主決策 + 混合切換
7. **可觀測性** (5 功能) --- 審計 + 巡檢 + 指標 (correlation/rootcause 為 STUB)
8. **Agent Swarm** (6 功能) --- 多 Agent 群集視覺化、即時追蹤、SSE 串流 **(Phase 29)**

---

## 1. 架構層級與功能映射總覽

### 1.1 架構層級定義 (11 層模型)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    完整架構層級 (Phase 29, V7 - 11 層模型)                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Layer 1: 前端展示層 (Frontend Layer)                                               │
│  ════════════════════════════════════                                                │
│  • React 18 + TypeScript + Vite (port 3005)                                         │
│  • 203 .tsx/.ts 檔案, 47,630 LOC                                                    │
│  • Unified Chat UI (25+ components) + AG-UI Components                              │
│  • Agent Swarm Panel (15 components + 4 hooks) ← Phase 29                          │
│  • DevUI 開發者工具 • Dashboard • Approval Page • SwarmTestPage                    │
│                                                                                      │
│  Layer 2: API 路由層 (API Layer)                                                     │
│  ═══════════════════════════════                                                     │
│  • 39 API Route Modules, ~528 Endpoints, 47 Registered Routers                     │
│  • FastAPI + Uvicorn (port 8000)                                                    │
│  • Swarm API (3 status + 5 demo endpoints) ← Phase 29                              │
│                                                                                      │
│  Layer 3: AG-UI Protocol 層                                                          │
│  ═════════════════════════                                                           │
│  • SSE Bridge (Server-Sent Events) + Swarm Event Streaming                         │
│  • HITL 審批事件 + 思考過程串流 + Swarm CustomEvent                                │
│  • SharedState 前後端同步                                                            │
│  • 23 files, 9,531 LOC                                                              │
│                                                                                      │
│  Layer 4: Phase 28 編排入口層 (Orchestration Entry Layer)                             │
│  ════════════════════════════════════════════════════════                             │
│  • InputGateway + BusinessIntentRouter (三層瀑布式路由)                              │
│  • GuidedDialogEngine + RiskAssessor + HITLController                               │
│  • OrchestrationMetrics (893 LOC, OTel)                                             │
│  • 39 files, 15,753 LOC                                                             │
│                                                                                      │
│  Layer 5: 混合編排層 (Hybrid Orchestration Layer)                                    │
│  ════════════════════════════════════════════════                                    │
│  • HybridOrchestratorV2 (1,254 LOC)                                                │
│  • FrameworkSelector + ContextBridge + ContextSynchronizer                          │
│  • ModeSwitcher + 4 Trigger Detectors                                               │
│  • 60 files, 21,197 LOC                                                             │
│                                                                                      │
│  Layer 6: MAF Builder 層 (Agent Framework Layer)                                     │
│  ═══════════════════════════════════════════════                                     │
│  • 23 Builder files (24,211 LOC)                                                    │
│  • 53 files total, 37,209 LOC — 最成熟的整合層                                     │
│  • 8 Builders 使用 from agent_framework import (1 standalone)                       │
│                                                                                      │
│  Layer 7: Claude SDK 執行層 (Execution Layer)                                        │
│  ════════════════════════════════════════════                                        │
│  • ClaudeSDKClient (AsyncAnthropic)                                                 │
│  • Autonomous Pipeline + Hook System + MCP Client                                   │
│  • 47 files, 15,098 LOC                                                             │
│                                                                                      │
│  Layer 8: MCP 工具層 (Tool Layer)                                                    │
│  ════════════════════════════════                                                    │
│  • 5 MCP Servers (Azure, Shell, Filesystem, SSH, LDAP)                             │
│  • 43 files, 12,535 LOC                                                             │
│  • Security: 28 permission patterns, 16 audit patterns                              │
│                                                                                      │
│  Layer 9: 支援整合層 (Supporting Integrations)                                       │
│  ═════════════════════════════════════════════                                       │
│  • Memory (mem0) | Patrol | Learning | Correlation | Audit | A2A                   │
│  • Swarm (7 files, 2,747 LOC) ← Phase 29                                           │
│  • 49 files, 14,340 LOC                                                             │
│                                                                                      │
│  Layer 10: 業務邏輯層 (Domain Layer)                                                  │
│  ══════════════════════════════════                                                  │
│  • 20 Domain Modules (112 files, 47,214 LOC)                                       │
│                                                                                      │
│  Layer 11: 基礎設施層 (Infrastructure Layer)                                         │
│  ════════════════════════════════════════════                                        │
│  • PostgreSQL 16 ✅ | Redis 7 ✅                                                     │
│  • RabbitMQ ❌ 空殼 | Storage ❌ 空目錄                                              │
│  • 22 files, 3,401 LOC                                                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| 層級 | 名稱 | 說明 | 檔案規模 (V7 驗證) |
|------|------|------|----------|
| **L1** | Frontend | React 18 + TypeScript + Vite | 203 .tsx/.ts, 47,630 LOC, 39 pages, 127 component files |
| **L2** | API Layer | 39 modules, ~528 endpoints | 138 route files, 47 routers |
| **L3** | AG-UI Protocol | SSE Bridge + HITL + Swarm Events | 23 files, 9,531 LOC |
| **L4** | Phase 28 Orchestration | 三層意圖路由 + 引導對話 + 風險評估 + HITL | 39 files, 15,753 LOC |
| **L5** | Hybrid Layer | HybridOrchestratorV2 + 框架切換 + 上下文橋接 | 60 files, 21,197 LOC |
| **L6** | MAF Builder Layer | 23 Builders + 支援檔案，MAF 官方 API | 53 files, 37,209 LOC |
| **L7** | Claude SDK Layer | 自主執行管線 + Hook 系統 | 47 files, 15,098 LOC |
| **L8** | MCP Layer | 5 個 MCP Server + 安全模組 | 43 files, 12,535 LOC |
| **L9** | Supporting + Swarm | 記憶、巡檢、學習、關聯、審計、A2A、**Swarm** | 49 files, 14,340 LOC |
| **L10** | Domain Layer | 20 domain modules 業務邏輯 | 112 files, 47,214 LOC |
| **L11** | Infrastructure | PostgreSQL + Redis + RabbitMQ (空) + Storage (空) | 22 files, 3,401 LOC |

### 1.2 功能分類與架構層級對應

| 類別 | 主要層級 | 功能數 |
|------|----------|--------|
| Agent 編排能力 | Layer 6 (MAF Builder) + Layer 10 (Domain) | 16 |
| 人機協作能力 | Layer 4 (Orchestration) + Layer 3 (AG-UI) + Layer 1 (Frontend) | 7 |
| 狀態與記憶能力 | Layer 5 (Hybrid Checkpoint) + Layer 9 (Memory) | 5 |
| 前端介面能力 | Layer 1 (Frontend) | 8 |
| 連接與整合能力 | Layer 4 (InputGateway) + Layer 8 (MCP) + Layer 9 (A2A) | 11 |
| 智能決策能力 | Layer 4 (Intent Router) + Layer 5 (Hybrid) + Layer 7 (Claude SDK) | 10 |
| 可觀測性能力 | Layer 4 (Metrics) + Layer 9 (Audit/Patrol/Correlation) | 5 |
| **Agent Swarm 能力** | **Layer 9 (Swarm) + Layer 3 (AG-UI) + Layer 2 (API) + Layer 1 (Frontend)** | **6** |

### 1.3 功能實現狀態速查表

| # | 功能名稱 | 狀態 | 架構層級 | 主要實現位置 | V7 行數 |
|---|---------|------|----------|-------------|---------|
| 1 | WorkflowExecutor (Sequential) | ✅ | L6 | `builders/workflow_executor.py` | 1,308 |
| 2 | ConcurrentBuilder (Parallel) | ✅ | L6 | `builders/concurrent.py` | 1,633 |
| 3 | GroupChatBuilder | ✅ | L6 | `builders/groupchat.py` | 1,912 |
| 4 | HandoffBuilder | ✅ | L6 | `builders/handoff.py` | 994 |
| 5 | NestedWorkflow | ✅ | L6 | `builders/nested_workflow.py` | 1,307 |
| 6 | PlanningAdapter (Dynamic) | ✅ | L6 | `builders/planning.py` | 1,364 |
| 7 | MagenticBuilder | ✅ | L6 | `builders/magentic.py` | 1,809 |
| 8 | AgentExecutor | ✅ | L6 | `builders/agent_executor.py` | 699 |
| 9 | CodeInterpreter | ✅ | L6 | `builders/code_interpreter.py` | 868 |
| 10 | GroupChat Voting | ✅ | L6 | `builders/groupchat_voting.py` | 736 |
| 11 | Capability Matching | ✅ | L6 | `builders/handoff_capability.py` | 1,050 |
| 12 | Handoff HITL | ✅ | L6 | `builders/handoff_hitl.py` | 1,005 |
| 13 | Edge Routing | ✅ | L6 | `builders/edge_routing.py` | 884 |
| 14 | GroupChat Orchestrator | ✅ | L6 | `builders/groupchat_orchestrator.py` | 883 |
| 15 | Sub-workflow Execution | ✅ | L10 | `domain/orchestration/nested/sub_executor.py` | - |
| 16 | Recursive Patterns | ✅ | L10 | `domain/orchestration/nested/recursive_handler.py` | - |
| 17 | Checkpoint System | ✅ | L10 | `domain/checkpoints/storage.py` + `service.py` | - |
| 18 | Approval Workflow | ✅ | L4 | `orchestration/hitl/controller.py` | 788 |
| 19 | HITL Manager | ✅ | L6 | `builders/handoff_hitl.py` | 1,005 |
| 20 | Approval Handler | ✅ | L4 | `orchestration/hitl/approval_handler.py` | 693 |
| 21 | Teams Notification | ✅ | L4 | `orchestration/hitl/notification.py` | 732 |
| 22 | Frontend HITL Components | ✅ | L1 | `components/ag-ui/hitl/` | - |
| 23 | Inline Approval (Chat) | ✅ | L1 | `components/unified-chat/ApprovalDialog.tsx` | - |
| 24 | Redis Checkpoints | ✅ | L5 | `hybrid/checkpoint/backends/redis.py` | 438 |
| 25 | PostgreSQL Checkpoints | ✅ | L5 | `hybrid/checkpoint/backends/postgres.py` | 485 |
| 26 | Unified Memory (3-layer) | ✅ | L9 | `memory/unified_memory.py` | 683 |
| 27 | mem0 Integration | ✅ | L9 | `memory/mem0_client.py` | 446 |
| 28 | Embeddings Service | ✅ | L9 | `memory/embeddings.py` | - |
| 29 | Dashboard | ✅ | L1 | `pages/dashboard/DashboardPage.tsx` | - |
| 30 | Unified Chat | ✅ | L1 | `components/unified-chat/` (25+ files) | - |
| 31 | Agent Management | ✅ | L1 | `pages/agents/` (4 pages) | - |
| 32 | Workflow Management | ✅ | L1 | `pages/workflows/` (4 pages) | - |
| 33 | DevUI Developer Tools | ✅ | L1 | `DevUI/` (15) + `pages/DevUI/` (7) | - |
| 34 | AG-UI Demo | ✅ | L1 | `pages/ag-ui/AGUIDemoPage.tsx` + 8 sub | - |
| 35 | Workflow Visualization | ❌ | L1 | ReactFlow **未安裝** (package.json 驗證) | - |
| 36 | Auth (Login/Signup) | ✅ | L1 | `pages/auth/LoginPage.tsx`, `SignupPage.tsx` | - |
| 37 | InputGateway | ✅ | L4 | `input_gateway/gateway.py` + handlers | 419 |
| 38 | ServiceNow Handler | ✅ | L4 | `source_handlers/servicenow_handler.py` | 399 |
| 39 | Prometheus Handler | ✅ | L4 | `source_handlers/prometheus_handler.py` | 412 |
| 40 | User Input Handler | ✅ | L4 | `source_handlers/user_input_handler.py` | 294 |
| 41 | MCP Azure Server | ✅ | L8 | `mcp/servers/azure/server.py` | 333 |
| 42 | MCP Filesystem Server | ✅ | L8 | `mcp/servers/filesystem/server.py` | - |
| 43 | MCP LDAP Server | ✅ | L8 | `mcp/servers/ldap/server.py` | - |
| 44 | MCP Shell Server | ✅ | L8 | `mcp/servers/shell/server.py` | - |
| 45 | MCP SSH Server | ✅ | L8 | `mcp/servers/ssh/server.py` | - |
| 46 | A2A Protocol | ✅ | L9 | `a2a/protocol.py` + `discovery.py` | 294+352 |
| 47 | A2A Agent Discovery | ✅ | L9 | `a2a/discovery.py` | 352 |
| 48 | Three-tier Intent Router | ✅ | L4 | `intent_router/router.py` | 639 |
| 49 | PatternMatcher (Tier 1) | ✅ | L4 | `intent_router/pattern_matcher/matcher.py` | 411 |
| 50 | SemanticRouter (Tier 2) | ✅ | L4 | `intent_router/semantic_router/router.py` | 466 |
| 51 | LLMClassifier (Tier 3) | ✅ | L4 | `intent_router/llm_classifier/classifier.py` | 439 |
| 52 | CompletenessChecker | ✅ | L4 | `intent_router/completeness/checker.py` | - |
| 53 | GuidedDialogEngine | ✅ | L4 | `guided_dialog/engine.py` | 593 |
| 54 | RiskAssessor | ✅ | L4 | `risk_assessor/assessor.py` | 639 |
| 55 | Autonomous Planning | ✅ | L7 | `claude_sdk/autonomous/` (8 files) | ~2,800 |
| 56 | Smart Fallback | ✅ | L7 | `claude_sdk/autonomous/fallback.py` | 587 |
| 57 | Hybrid Framework Switching | ✅ | L5 | `hybrid/switching/` (11 files) | ~829+ |
| 58 | Decision Audit Tracker | ✅ | L9 | `audit/decision_tracker.py` | 448 |
| 59 | Patrol Agent | ✅ | L9 | `patrol/agent.py` + `scheduler.py` | 280+ |
| 60 | Correlation Analyzer | ⚠️ | L9 | `correlation/analyzer.py` | 524 |
| 61 | Root Cause Analyzer | ⚠️ | L9 | `rootcause/analyzer.py` | 520 |
| 62 | OrchestrationMetrics | ✅ | L4 | `orchestration/metrics.py` | 893 |
| 63 | SwarmTracker | ✅ | L9 | `swarm/tracker.py` | 694 |
| 64 | SwarmIntegration + SSE | ✅ | L9 | `swarm/swarm_integration.py` + `events/` | 404+1,077 |
| 65 | Swarm API | ✅ | L2 | `api/v1/swarm/` (2 route files) | ~1,064 |
| 66 | Swarm Frontend Panel | ✅ | L1 | `agent-swarm/` (15 components + 4 hooks) | ~3,000 |
| 67 | SwarmTestPage | ✅ | L1 | `SwarmTestPage.tsx` + useSwarmMock + useSwarmReal | 844+623+603 |
| 68 | Swarm Models | ✅ | L9 | `swarm/models.py` | 393 |

---

## 2. 功能詳細映射

> **路徑約定**: 以下所有路徑均相對於 `backend/src/integrations/`，除非另有標註。
> Frontend 路徑相對於 `frontend/src/`。行號為 V7 驗證時的實測行數。

### 2.1 Agent 編排能力 (16 功能)

9 個 Builder adapter + 7 個擴展功能。8/9 Builder 使用 `from agent_framework import` 官方 API。

#### 9 個 Builder Adapter

| # | 功能 | 狀態 | 層級 | 實現檔案 | V7 驗證行數 | MAF Import |
|---|------|------|------|----------|------------|------------|
| 1 | **WorkflowExecutor** (Sequential) | ✅ | L6 | `agent_framework/builders/workflow_executor.py` | 1,308 | `WorkflowExecutor, SubWorkflowRequestMessage` |
| 2 | **ConcurrentBuilder** (Parallel) | ✅ | L6 | `agent_framework/builders/concurrent.py` | 1,633 | `ConcurrentBuilder` |
| 3 | **GroupChatBuilder** | ✅ | L6 | `agent_framework/builders/groupchat.py` | 1,912 | `GroupChatBuilder` (有 `_MockGroupChatWorkflow` fallback) |
| 4 | **HandoffBuilder** | ✅ | L6 | `agent_framework/builders/handoff.py` | 994 | `HandoffBuilder, HandoffAgentUserRequest` |
| 5 | **NestedWorkflow** | ✅ | L6 | `agent_framework/builders/nested_workflow.py` | 1,307 | `WorkflowBuilder, Workflow, WorkflowExecutor` (有 Mock fallback) |
| 6 | **PlanningAdapter** (Dynamic) | ✅ | L6 | `agent_framework/builders/planning.py` | 1,364 | `MagenticBuilder, Workflow` |
| 7 | **MagenticBuilder** | ✅ | L6 | `agent_framework/builders/magentic.py` | 1,809 | `MagenticBuilder, StandardMagenticManager` (有 Mock fallback) |
| 8 | **AgentExecutor** | ✅ | L6 | `agent_framework/builders/agent_executor.py` | 699 | `ChatAgent, ChatMessage, Role` (**V6 修正: 確實有 MAF import**) |
| 9 | **CodeInterpreter** | ✅ | L6 | `agent_framework/builders/code_interpreter.py` | 868 | **無** (使用 Azure `AssistantManagerService`，非 agent_framework) |

**V7 注意**: 僅 #9 CodeInterpreter 違反項目 CRITICAL 規則要求 `from agent_framework import`。V5 曾錯誤地將 #8 列為違規，V6 已修正。

#### 7 個擴展功能

| # | 功能 | 狀態 | 層級 | 實現檔案 | V7 驗證行數 | 角色 |
|---|------|------|------|----------|------------|------|
| 10 | **GroupChat Voting** | ✅ | L6 | `builders/groupchat_voting.py` | 736 | 投票式 speaker 選擇 |
| 11 | **Capability Matching** | ✅ | L6 | `builders/handoff_capability.py` | 1,050 | 加權能力匹配 |
| 12 | **Handoff HITL** | ✅ | L6 | `builders/handoff_hitl.py` | 1,005 | HITL 整合 Handoff |
| 13 | **Edge Routing** | ✅ | L6 | `builders/edge_routing.py` | 884 | FanOut/FanIn 路由 |
| 14 | **GroupChat Orchestrator** | ✅ | L6 | `builders/groupchat_orchestrator.py` | 883 | Orchestrator/manager 選擇 |
| 15 | **Sub-workflow Execution** | ✅ | L10 | `domain/orchestration/nested/sub_executor.py` | - | 嵌套子工作流 |
| 16 | **Recursive Patterns** | ✅ | L10 | `domain/orchestration/nested/recursive_handler.py` | - | 遞迴工作流處理 |

**支援檔案** (均位於 `agent_framework/builders/`):
- `handoff_policy.py` (513) - Handoff 策略管理
- `handoff_context.py` (855) - 上下文傳遞
- `handoff_service.py` (821) - Handoff 服務層
- `*_migration.py` (5 files) - 遷移適配器
- `__init__.py` (805) - 統一重新匯出

**並行執行模式** (ConcurrentBuilder):
- `ALL`: 等待所有任務完成 (`asyncio.gather`)
- `ANY`: 任一完成即返回 (`asyncio.wait(FIRST_COMPLETED)`)
- `MAJORITY`: 多數完成即返回
- `FIRST_SUCCESS`: 首個成功即返回

### 2.2 人機協作能力 (7 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V7 驗證行數 |
|---|------|------|------|----------|------------|
| 17 | **Checkpoint System** | ✅ | L10 | `domain/checkpoints/storage.py` + `service.py` | - |
| 18 | **Approval Workflow** | ✅ | L4 | `orchestration/hitl/controller.py` | 788 |
| 19 | **HITL Manager** | ✅ | L6 | `builders/handoff_hitl.py` | 1,005 |
| 20 | **Approval Handler** | ✅ | L4 | `orchestration/hitl/approval_handler.py` | 693 |
| 21 | **Teams Notification** | ✅ | L4 | `orchestration/hitl/notification.py` (有 `MockNotificationService`) | 732 |
| 22 | **Frontend HITL Components** | ✅ | L1 | `components/ag-ui/hitl/` | - |
| 23 | **Inline Approval (Chat)** | ✅ | L1 | `components/unified-chat/ApprovalDialog.tsx` | - |

**CRITICAL 風險**: `InMemoryApprovalStorage` 為 HITLController 的工廠預設 (controller.py:743)。重啟後所有待處理審批丟失。

**審批狀態機**:
```
PENDING → APPROVED (由審批者操作)
PENDING → REJECTED (由審批者操作)
PENDING → EXPIRED  (超時自動, 30 min)
PENDING → CANCELLED (由請求者取消)
```

### 2.3 狀態與記憶能力 (5 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V7 驗證行數 |
|---|------|------|------|----------|------------|
| 24 | **Redis Checkpoints** | ✅ | L5 | `hybrid/checkpoint/backends/redis.py` | 438 |
| 25 | **PostgreSQL Checkpoints** | ✅ | L5 | `hybrid/checkpoint/backends/postgres.py` | 485 |
| 26 | **Unified Memory (3-layer)** | ✅ | L9 | `memory/unified_memory.py` | 683 |
| 27 | **mem0 Integration** | ✅ | L9 | `memory/mem0_client.py` | 446 |
| 28 | **Embeddings Service** | ✅ | L9 | `memory/embeddings.py` | - |

**3 層統一記憶架構**: Redis (30min TTL) → PostgreSQL (7-day TTL) → mem0+Qdrant (permanent)

**已知問題**:
- `ContextSynchronizer` 使用 `Dict` 存儲，無 `asyncio.Lock`，在並行場景下有競爭條件風險 (嚴重度: CRITICAL)
- 存在 **4 個獨立 Checkpoint 系統**（hybrid/checkpoint, agent_framework/checkpoint, agent_framework/multiturn/checkpoint_storage, domain/checkpoints），無統一協調

### 2.4 前端介面能力 (8 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | 說明 |
|---|------|------|------|----------|------|
| 29 | **Dashboard** | ✅ | L1 | `DashboardPage` + 4 sub-components | React Query, 真實 DB 查詢 |
| 30 | **Unified Chat** | ✅ | L1 | `components/unified-chat/` (25+ files) | SSE streaming, agent panel |
| 31 | **Agent Management** | ✅ | L1 | `pages/agents/` (4 pages) | 完整 CRUD + Mock fallback |
| 32 | **Workflow Management** | ✅ | L1 | `pages/workflows/` (4 pages) | 完整 CRUD + Mock fallback |
| 33 | **DevUI Developer Tools** | ✅ | L1 | `DevUI/` (15) + `pages/DevUI/` (7) | Traces, monitor, events |
| 34 | **AG-UI Demo** | ✅ | L1 | `pages/ag-ui/AGUIDemoPage.tsx` + 8 sub | 7 功能 demo 頁面 |
| 35 | **Workflow Visualization** | ❌ | L1 | ReactFlow **未安裝** | package.json 無 `@xyflow/react` 依賴 |
| 36 | **Auth (Login/Signup)** | ✅ | L1 | `pages/auth/LoginPage.tsx`, `SignupPage.tsx` | JWT auth, ProtectedRoute |

**V7 驗證發現**:
- #35 WorkflowViz: `package.json` 中無 `@xyflow/react` 或 `reactflow` 依賴。`.claude/skills/react-flow/` 目錄存在但未使用。Swarm 視覺化使用自訂卡片元件而非 ReactFlow。
- **10 個頁面靜默 Mock fallback** (無視覺指示器): ApprovalsPage, WorkflowsPage, WorkflowDetailPage, TemplatesPage, AuditPage, AgentsPage, AgentDetailPage, RecentExecutions, PendingApprovals, ExecutionChart

**Frontend 技術棧** (V7 驗證):
- **框架**: React ^18.2.0 + TypeScript ^5.3.3 + Vite ^5.0.11
- **UI 庫**: Shadcn/Radix (16 primitives, 12 Radix packages)
- **狀態管理**: Zustand ^4.4.7 + immer ^11.1.3 + React Query ^5.17.0
- **API 通訊**: **Fetch API** (非 Axios)
- **Custom Hooks**: 20 (16 top-level + 4 internal swarm hooks)
- **Stores**: 3+1 (authStore, unifiedChatStore, swarmStore + 1 test)

### 2.5 連接與整合能力 (11 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V7 驗證行數 |
|---|------|------|------|----------|------------|
| 37 | **InputGateway** | ✅ | L4 | `input_gateway/gateway.py` + handlers (有 `MockInputGateway`) | 419 |
| 38 | **ServiceNow Handler** | ✅ | L4 | `source_handlers/servicenow_handler.py` (有 Mock) | 399 |
| 39 | **Prometheus Handler** | ✅ | L4 | `source_handlers/prometheus_handler.py` (有 Mock) | 412 |
| 40 | **User Input Handler** | ✅ | L4 | `source_handlers/user_input_handler.py` (有 Mock) | 294 |
| 41 | **MCP Azure Server** | ✅ | L8 | `mcp/servers/azure/server.py` | 333 |
| 42 | **MCP Filesystem Server** | ✅ | L8 | `mcp/servers/filesystem/server.py` | - |
| 43 | **MCP LDAP Server** | ✅ | L8 | `mcp/servers/ldap/server.py` | - |
| 44 | **MCP Shell Server** | ✅ | L8 | `mcp/servers/shell/server.py` | - |
| 45 | **MCP SSH Server** | ✅ | L8 | `mcp/servers/ssh/server.py` | - |
| 46 | **A2A Protocol** | ✅ | L9 | `a2a/protocol.py` (12 MessageTypes, 完整序列化) | 294 |
| 47 | **A2A Agent Discovery** | ✅ | L9 | `a2a/discovery.py` (加權匹配; in-memory only) | 352 |

### 2.6 智能決策能力 (10 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V7 驗證行數 |
|---|------|------|------|----------|------------|
| 48 | **Three-tier Intent Router** | ✅ | L4 | `intent_router/router.py` (有 `MockBusinessIntentRouter`) | 639 |
| 49 | **PatternMatcher** (Tier 1) | ✅ | L4 | `intent_router/pattern_matcher/matcher.py` | 411 |
| 50 | **SemanticRouter** (Tier 2) | ✅ | L4 | `intent_router/semantic_router/router.py` (有 `MockSemanticRouter`) | 466 |
| 51 | **LLMClassifier** (Tier 3) | ✅ | L4 | `intent_router/llm_classifier/classifier.py` (有 `MockLLMClassifier`) | 439 |
| 52 | **CompletenessChecker** | ✅ | L4 | `intent_router/completeness/checker.py` (有 Mock) | - |
| 53 | **GuidedDialogEngine** | ✅ | L4 | `guided_dialog/engine.py` + context_manager + generator | 593+1,163+1,151 |
| 54 | **RiskAssessor** | ✅ | L4 | `risk_assessor/assessor.py` + policies | 639+711 |
| 55 | **Autonomous Planning** | ✅ | L7 | `claude_sdk/autonomous/` (8 files) | ~2,800 |
| 56 | **Smart Fallback** | ✅ | L7 | `claude_sdk/autonomous/fallback.py` (6 策略) | 587 |
| 57 | **Hybrid Framework Switching** | ✅ | L5 | `hybrid/switching/` (ModeSwitcher + 4 trigger detectors) | ~829+ |

**三層瀑布式路由邏輯**:
```
Layer 1: PatternMatcher (< 10ms) → confidence >= 0.90 → 返回
Layer 2: SemanticRouter (< 100ms) → similarity >= 0.85 → 返回
Layer 3: LLMClassifier (< 2000ms) → 最後手段，總是返回結果
```

**V7 重要更新**:
- #50 SemanticRouter 支援**真實 Azure OpenAI embeddings** (有 `MockSemanticRouter` fallback)
- #51 LLMClassifier 支援**真實 Claude Haiku** 分類 (有 `MockLLMClassifier` fallback)
- 透過 `USE_REAL_ROUTER` 環境變數控制，無 API key 時自動降級至 Mock

### 2.7 可觀測性能力 (5 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V7 驗證行數 |
|---|------|------|------|----------|------------|
| 58 | **Decision Audit Tracker** | ✅ | L9 | `audit/decision_tracker.py` + `report_generator.py` | 448+341 |
| 59 | **Patrol Agent** | ✅ | L9 | `patrol/` (agent 280+, scheduler 362, 5 checks) | 2,541 total |
| 60 | **Correlation Analyzer** | ⚠️ | L9 | `correlation/analyzer.py` (**所有 5 個數據方法回傳假數據**) | 524 |
| 61 | **Root Cause Analyzer** | ⚠️ | L9 | `rootcause/analyzer.py` (**硬編碼 2 個 HistoricalCase**) | 520 |
| 62 | **OrchestrationMetrics** | ✅ | L4 | `orchestration/metrics.py` (OTel Counter/Histogram/Gauge) | 893 |

**Correlation Analyzer 深度分析** (#60):

演算法為真實實作 (`find_correlations()`, `_time_correlation()`, `_dependency_correlation()`, `_semantic_correlation()`)。
但**所有 5 個數據存取方法**回傳虛構資料：

| 方法 | 行號 | 回傳內容 | 問題 |
|------|------|----------|------|
| `_get_event()` | 427 | `Event(title=f"Event {event_id}")` | 不論輸入均回傳相同結構 |
| `_get_events_in_range()` | 441 | 5 個硬編碼事件 | 固定數量 |
| `_get_dependencies()` | 461 | 虛構依賴列表 | 每元件固定 1 個 |
| `_get_events_for_component()` | 476 | 1 個硬編碼事件 | 固定 1 個 |
| `_search_similar_events()` | 492 | 2 個結果 (0.85, 0.72) | **search_text 被忽略** |

註解 (行 424): `# Helper methods (模擬實現，實際應連接真實數據源)`

**Root Cause Analyzer 深度分析** (#61):

框架為真實實作 (假說生成、Claude prompting)。但 `get_similar_patterns()` 回傳固定 2 個 `HistoricalCase`。
註解: `# 模擬歷史案例查詢`

### 2.8 Agent Swarm 能力 (6 功能) — Phase 29

Phase 29 (Sprint 100-106) 新增的多 Agent 群集即時視覺化系統。**項目中品質最佳的模組**。

| # | 功能 | 狀態 | 層級 | 實現檔案 | V7 驗證行數 |
|---|------|------|------|----------|------------|
| 63 | **SwarmTracker** | ✅ | L9 | `swarm/tracker.py` (Thread-safe RLock, optional Redis) | 694 |
| 64 | **SwarmIntegration + SSE** | ✅ | L9 | `swarm/swarm_integration.py` + `events/emitter.py` + `events/types.py` | 404+634+393 |
| 65 | **Swarm API** | ✅ | L2 | `api/v1/swarm/routes.py` + `demo.py` | ~1,064 |
| 66 | **Swarm Frontend Panel** | ✅ | L1 | 15 components + 4 hooks in `agent-swarm/` | ~3,000 |
| 67 | **SwarmTestPage** | ✅ | L1 | `SwarmTestPage.tsx` + useSwarmMock + useSwarmReal | 844+623+603 |
| 68 | **Swarm Models** | ✅ | L9 | `swarm/models.py` | 393 |

**Swarm 資料模型**:
- WorkerType: 9 enum (RESEARCH, WRITER, DESIGNER, REVIEWER, COORDINATOR, ANALYST, CODER, TESTER, CUSTOM)
- WorkerStatus: 7 lifecycle (PENDING → RUNNING → THINKING → TOOL_CALLING → COMPLETED/FAILED/CANCELLED)
- SwarmMode: 3 modes (SEQUENTIAL, PARALLEL, HIERARCHICAL)
- SwarmStatus: 5 states (INITIALIZING, RUNNING, PAUSED, COMPLETED, FAILED)

**Swarm SSE 事件類型** (9 event types):
SwarmCreated, SwarmStatusUpdate, SwarmCompleted, WorkerStarted, WorkerProgress, WorkerThinking, WorkerToolCall, WorkerMessage, WorkerCompleted

**Swarm API 端點** (8 endpoints):

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/v1/swarm/{swarm_id}` | 群集狀態 |
| GET | `/api/v1/swarm/{swarm_id}/workers` | Worker 列表 |
| GET | `/api/v1/swarm/{swarm_id}/workers/{worker_id}` | Worker 詳情 |
| POST | `/api/v1/swarm/demo/start` | 啟動 Demo |
| GET | `/api/v1/swarm/demo/status/{swarm_id}` | Demo 狀態 |
| POST | `/api/v1/swarm/demo/stop/{swarm_id}` | 停止 Demo |
| GET | `/api/v1/swarm/demo/scenarios` | 場景列表 |
| GET | `/api/v1/swarm/demo/events/{swarm_id}` | SSE 事件流 |

**Swarm 測試覆蓋** (跨 4 個測試類別):

| 類別 | 路徑 | 檔案數 |
|------|------|--------|
| Unit | `tests/unit/swarm/` | 5 |
| Integration | `tests/integration/swarm/` | 2 |
| E2E | `tests/e2e/swarm/` | 1 |
| Performance | `tests/performance/swarm/` | 1 |

**Swarm Frontend 元件**:

| 元件 | Sprint | 用途 |
|------|--------|------|
| AgentSwarmPanel | 102 | 主面板 (loading/empty/active) |
| SwarmHeader | 102 | 模式和狀態顯示 |
| OverallProgress | 102 | 狀態感知進度條 |
| WorkerCard | 102 | 個別 Worker 狀態卡片 |
| WorkerCardList | 102 | Worker 卡片網格 |
| SwarmStatusBadges | 102 | 狀態徽章集合 |
| WorkerDetailDrawer | 103 | 側邊抽屜 (Worker 詳情) |
| WorkerDetailHeader | 103 | 抽屜標題 |
| CurrentTask | 103 | 當前任務顯示 |
| ToolCallItem | 103 | 工具調用視覺化 |
| ToolCallsPanel | 103 | 工具調用列表 |
| MessageHistory | 103 | Worker 對話歷史 |
| CheckpointPanel | 103 | Worker 檢查點 |
| ExtendedThinkingPanel | 104 | Extended Thinking 視覺化 |
| WorkerActionList | 104 | 統一操作時間線 |

---

## 3. 功能整合總覽

### 3.1 功能與架構層級映射矩陣

| 層級 | 功能編號 | 功能數 |
|------|----------|--------|
| **L1** Frontend | #22-23, #29-36, #66-67 | 12 |
| **L2** API Layer | #65 + (所有功能皆有 API endpoint) | 1+ |
| **L3** AG-UI Protocol | SSE 串流橫切 (HITL + Swarm + Chat) | 橫切 |
| **L4** Phase 28 Orchestration | #18, #20-21, #37-40, #48-54, #62 | 15 |
| **L5** Hybrid Layer | #24-25, #57 | 3 |
| **L6** MAF Builder | #1-14, #19 | 15 |
| **L7** Claude SDK | #55-56 | 2 |
| **L8** MCP Layer | #41-45 | 5 |
| **L9** Supporting + Swarm | #26-28, #46-47, #58-61, #63-64, #68 | 12 |
| **L10** Domain Layer | #15-17 | 3 |
| **L11** Infrastructure | PostgreSQL + Redis backends | 橫切 |

### 3.2 架構層級功能分布

```
L1  Frontend:             ████████████  12 功能 (含 Swarm 前端)
L2  API:                  █            1 功能 (Swarm API) + 橫切所有
L3  AG-UI:                (橫切)       SSE 串流基礎設施
L4  Orchestration:        ███████████████ 15 功能 (Phase 28 智能入口)
L5  Hybrid:               ███          3 功能
L6  MAF Builder:          ███████████████ 15 功能 (編排核心)
L7  Claude SDK:           ██           2 功能
L8  MCP:                  █████        5 功能
L9  Supporting+Swarm:     ████████████  12 功能 (含 Swarm 後端)
L10 Domain:               ███          3 功能
L11 Infrastructure:       (橫切)       PostgreSQL + Redis
```

### 3.3 Mock 類統計 (18 個 class，15 個檔案)

| 位置 | Mock 類別 | 數量 |
|------|----------|------|
| orchestration/ | MockSemanticRouter, MockBusinessIntentRouter, MockLLMClassifier, MockCompletenessChecker, MockUserInputHandler, MockServiceNowHandler, MockPrometheusHandler, MockBaseHandler, MockSchemaValidator, MockInputGateway, MockNotificationService, MockQuestionGenerator, MockLLMClient (含嵌套 MockContent+MockResponse), MockGuidedDialogEngine, MockConversationContextManager | 17 |
| llm/ | MockLLMService | 1 |

**風險**: 9 個 Mock class 透過 `__init__.py` 匯出為公開 API，混淆生產代碼與測試代碼邊界。

### 3.4 InMemory 存儲風險 (9 個 class，8 個檔案)

| Class | 位置 | 影響功能 | 風險等級 |
|-------|------|----------|---------|
| `InMemoryApprovalStorage` | `hitl/controller.py:647` | #18 Approval Workflow | CRITICAL |
| `InMemoryCheckpointStorage` | `hybrid/switching/switcher.py:183` | #57 Framework Switching | HIGH |
| `InMemoryCheckpointStorage` | `agent_framework/checkpoint.py:653` | Checkpoint 系統 | HIGH |
| `InMemoryConversationMemoryStore` | `domain/orchestration/memory/in_memory.py:29` | 對話記憶 | HIGH |
| `InMemoryThreadRepository` | `ag_ui/thread/storage.py:276` | #30 Unified Chat | HIGH |
| `InMemoryCache` | `ag_ui/thread/storage.py:341` | AG-UI 快取 | MEDIUM |
| `InMemoryDialogSessionStorage` | `guided_dialog/context_manager.py:752` | #53 GuidedDialog | MEDIUM |
| `InMemoryTransport` | `mcp/core/transport.py:321` | MCP 傳輸 | MEDIUM |
| `InMemoryAuditStorage` | `mcp/security/audit.py:265` | MCP 安全審計 | MEDIUM |

### 3.5 Stub 分析

| 功能 | 代碼存在 | 數據來源 | 問題 |
|------|----------|----------|------|
| #60 Correlation | 真實演算法 | 所有 5 個數據方法硬編碼 | 「模擬實現」 |
| #61 Root Cause | 真實框架 | 2 個硬編碼 HistoricalCase | 「模擬歷史案例查詢」 |

### 3.6 功能缺口分析

| 功能 | 狀態 | 缺口描述 | 影響 | 建議優先級 |
|------|------|----------|------|-----------|
| #35 WorkflowViz | ❌ | ReactFlow 未安裝，無視覺化工作流編輯器 | 缺少核心視覺化能力 | P1 |
| #60 Correlation | ⚠️ | 演算法真實但所有數據方法回傳假數據 | 分析結果完全不可信 | P1 |
| #61 Root Cause | ⚠️ | 框架真實但歷史匹配為硬編碼 | 根因分析準確度受限 | P1 |

---

## 4. 智能體編排平台能力總結

### 4.0 V3 → V6 → V7 功能演進對照

| 維度 | V3 (65 功能) | V6 (64 功能) | V7 (64 功能) | V6→V7 變化 |
|------|-------------|-------------|-------------|-----------|
| 功能總數 | 65 | 64 | **64** | 不變 |
| 類別數 | 8 | 8 | **8** | 不變 |
| Phases | 29 | 29 | **29** | 不變 |
| Sprints | 106 | 106 | **106** | 不變 |
| Backend LOC | ~130K | ~130K | **~228.7K** | **重大修正** |
| Frontend LOC | 未統計 | 未統計 | **47,630** | 新增指標 |
| API 端點 | ~534 | 530 | **528** | 微調 (排除 docstring) |
| >800 行檔案 | 57 | 57 | **58** | +1 |
| Checkpoint 系統 | 2 (dual) | 2 (dual) | **4 (quad)** | 重新統計 |
| Mock classes | 18 | 18 | **18** | 不變 |
| InMemory classes | 9 | 9 | **9** | 不變 |
| 驗證方式 | 5 Agent | 5 Agent Team | **5+3 Agent** | 增加交叉驗證 |

### 4.1 八大能力矩陣

| 能力 | 成熟度 | 功能數 | 實現率 | 主要風險 |
|------|--------|--------|--------|----------|
| 多框架代理協作 | PoC | 16 | 100% | code_interpreter 缺 MAF import; MAF 為 preview |
| 人機協作 | PoC | 7 | 100% | InMemoryApprovalStorage 為預設 |
| 狀態與記憶 | PoC | 5 | 100% | ContextSynchronizer 無鎖; 4 重 checkpoint 未協調 |
| 前端介面 | PoC | 8 | 87.5% | ReactFlow 未安裝; 10 頁面靜默 Mock |
| 連接與整合 | PoC | 11 | 100% | A2A in-memory only |
| 智能決策 | 需改進 | 10 | 100% | 17 個 Mock 類別; 靜默降級 |
| 可觀測性 | 需改進 | 5 | 60% | correlation/rootcause 為 STUB |
| Agent Swarm | PoC | 6 | 100% | **項目最佳模組** (Thread-safe, 4 類測試) |

### 4.2 安全風險評估 (V7 新增)

| 風險 | 嚴重度 | 證據 |
|------|--------|------|
| **93% API 端點無認證** | CRITICAL | 僅 38/528 使用 auth middleware (3 個路由模組) |
| **無 HTTP rate limiting** | CRITICAL | 無 middleware 級別節流 |
| **硬編碼 JWT secret** | HIGH | `"change-this-to-a-secure-random-string"` |
| **CORS 允許所有方法/標頭** | HIGH | `allow_methods=["*"]`, `allow_headers=["*"]` |
| **CORS origin 端口不匹配** | HIGH | 預設 3000，frontend 在 3005 |
| **Docker 硬編碼憑證** | MEDIUM | n8n + Grafana 使用 admin/admin123 |

### 4.3 已知技術債與風險 (V7 更新)

| # | 問題 | 影響功能 | 嚴重度 |
|---|------|----------|--------|
| 1 | ContextSynchronizer 記憶體狀態 (無鎖, 2 個實作) | #24-25 | CRITICAL |
| 2 | 18 Mock 類在生產代碼中 (9 透過 __init__.py 匯出) | 全域 | CRITICAL |
| 3 | correlation/ 所有數據方法回傳虛構資料 | #60 | CRITICAL |
| 4 | rootcause/ 硬編碼 2 個 HistoricalCase | #61 | CRITICAL |
| 5 | InMemoryApprovalStorage 為 HITL 預設 | #18 | CRITICAL |
| 6 | 9 InMemory 存儲類跨 8 個檔案 | 多功能 | CRITICAL |
| 7 | Auth 覆蓋率僅 7% (38/528 端點) | 全域 | CRITICAL |
| 8 | 無 HTTP rate limiting | 全域 | HIGH |
| 9 | RabbitMQ 完全空殼 | 非同步分派 | HIGH |
| 10 | infrastructure/storage/ 空目錄 | 架構完整性 | HIGH |
| 11 | 單 Uvicorn Worker + reload=True 硬編碼 | 全平台 | HIGH |
| 12 | Vite proxy 端口不匹配: 8010 != 8000 | Frontend→Backend | HIGH |
| 13 | CORS origin 端口不匹配: 3000 != 3005 | 跨域請求 | HIGH |
| 14 | code_interpreter.py 缺少 MAF import | #9 | HIGH |
| 15 | 58 檔案超過 800 行 (5 超過 1,500) | 維護性 | MEDIUM |
| 16 | ReactFlow 未安裝 | #35 | MEDIUM |
| 17 | 54 console.log (authStore 有 5 個 — auth 洩漏風險) | 程式碼品質 | MEDIUM |
| 18 | ~323 空函數體 (204 pass + 119 ellipsis) | 功能完整性 | MEDIUM |
| 19 | 4 重 Checkpoint 系統未協調 | 狀態管理 | MEDIUM |
| 20 | A2A in-memory only | #46-47 | MEDIUM |
| 21 | Docker Compose Prometheus/Grafana 版本衝突 | 監控 | MEDIUM |
| 22 | API 測試覆蓋率僅 33% (13/39 模組) | 品質保證 | MEDIUM |
| 23 | store/ vs stores/ 分裂 | 前端組織 | LOW |
| 24 | 6 hooks 未從 barrel 匯出 | 前端組織 | LOW |
| 25 | Frontend 單元測試僅 Phase 29 | 品質保證 | LOW |

### 4.4 架構演進建議

| 優先級 | 方向 | 目標 | 涉及功能 |
|--------|------|------|----------|
| P0 | 安全 | 為剩餘 490 端點加上 auth + rate limiting | 全域 |
| P0 | 生產化 | ContextSynchronizer 並行安全 + Multi-Worker Uvicorn | #24-25 |
| P0 | 代碼衛生 | 18 Mock 類遷移至 tests/fixtures/ | 全域 |
| P1 | 數據真實 | correlation/rootcause 連接真實數據源 | #60, #61 |
| P1 | 資料持久 | 9 InMemory 替換為 Redis/Postgres | 多功能 |
| P1 | 前端補齊 | ReactFlow 工作流視覺化安裝與實現 | #35 |
| P2 | 基礎設施 | RabbitMQ 實現或移除; 修復 Vite/CORS 端口 | 基礎設施 |
| P2 | 品質提升 | 移除 54 console.log + 分拆大檔案 + 統一 Checkpoint | 全域 |
| P3 | 擴展 | 新增 MCP Server + A2A 持久化 | 新功能 |

---

## 5. 端到端場景

### 場景一：IT 事件處理 (16 功能協同)

```
使用者：「ETL Pipeline 在生產環境出錯了，影響了三個下游系統」

┌──────────────────────────────────────────────────────────────┐
│  IT 事件處理流程 (涉及 16 功能)                                  │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  User Input (Chat UI)                                         │
│      │                                                         │
│      ▼  [#37 InputGateway → #40 UserInputHandler]             │
│  來源識別: USER                                                │
│      │                                                         │
│      ▼  [#48 Three-tier IntentRouter]                          │
│      ├── #49 PatternMatcher: "ETL" + "生產" → INCIDENT (0.95)  │
│      │   (< 10ms, confidence >= 0.90 → 直接返回)               │
│      │                                                         │
│      ▼  [#52 CompletenessChecker]                              │
│  is_sufficient: true (有環境+影響範圍)                          │
│      │                                                         │
│      ▼  [#54 RiskAssessor — 7 維度評估]                        │
│  base: INCIDENT=0.8 + 生產環境+0.3 + 影響系統>3 → CRITICAL    │
│      │                                                         │
│      ▼  [#18 HITLController → #21 Teams Notification]          │
│  approval_type="multi" → 發送 Teams Adaptive Card              │
│      │                                                         │
│      ▼  (等待審批, timeout 30 min)                              │
│      │                                                         │
│      ▼  [#57 FrameworkSelector]                                 │
│  INCIDENT + 結構化任務 → MAF (WORKFLOW_MODE)                    │
│      │                                                         │
│      ▼  [#2 ConcurrentBuilder — 4 並行 Worker]                 │
│      ├── Worker 1: 診斷 ETL 故障                               │
│      ├── Worker 2: 檢查下游系統狀態                             │
│      ├── Worker 3: 備份受影響數據                               │
│      └── Worker 4: 準備修復方案                                 │
│                                                                │
│  涉及: #2, #18, #21, #24-25, #29-30, #37, #40, #48-49,       │
│        #52, #54, #55-56, #57, #58, #62                        │
│  橫跨 7 個架構層級 (L1, L2, L4, L5, L6, L7, L9)              │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

**端到端流程驗證結果** (flow-analyzer Agent):
- ✅ 32/37 路徑有效 (86.5%)
- ⚠️ 4 路徑有變更 (SemanticRouter/LLMClassifier 預設 Mock; Swarm 不在主流程; Teams Bot 無入口; RiskAssessor 評分機制與文件描述不同)
- ❌ 1 路徑不存在 (HITL 超時升級到 IT Director)

### 場景二：Agent Swarm 多專家協作分析

```
使用者：「分析我們的安全基礎設施，識別潛在漏洞」

┌──────────────────────────────────────────────────────────────┐
│  Swarm 多 Agent 協作場景                                        │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  User Input                                                    │
│      │                                                         │
│      ▼  [#37 InputGateway → #49 PatternMatcher]               │
│  IT_SECURITY_AUDIT (confidence 0.95)                          │
│      │                                                         │
│      ▼  [#54 RiskAssessor → #18 HITLController]               │
│  Risk: HIGH → 需要審批                                        │
│      │                                                         │
│      ▼  [#57 Hybrid Switching — 選擇 Swarm 模式]              │
│  複雜分析 → Claude SDK + Concurrent + Swarm 模式              │
│      │                                                         │
│      ▼  [#63 SwarmTracker — 建立群集]                         │
│  SwarmMode: PARALLEL, 4 Workers                               │
│      │                                                         │
│      ├──▶ Worker 1: ANALYST (網路安全) [#64 SSE: WorkerStarted]│
│      ├──▶ Worker 2: ANALYST (權限審計) [#64 SSE: WorkerStarted]│
│      ├──▶ Worker 3: REVIEWER (合規檢查) [#64 SSE: WorkerStarted]│
│      └──▶ Worker 4: CODER (修復建議)   [#64 SSE: WorkerStarted]│
│           │         │         │         │                      │
│           ▼         ▼         ▼         ▼                      │
│      [#64 SwarmIntegration 橋接 ClaudeCoordinator]            │
│           │         │         │         │                      │
│      [#64 SSE: WorkerThinking, WorkerToolCall, WorkerProgress]│
│           │         │         │         │                      │
│           └────┬────┴────┬────┘         │                      │
│                ▼         ▼              ▼                      │
│      [#66 Swarm Frontend Panel 即時顯示]                      │
│      • WorkerCard × 4 (各 Worker 狀態)                        │
│      • OverallProgress (整體進度)                              │
│      • ExtendedThinkingPanel (思考過程)                        │
│      • ToolCallsPanel (工具調用)                               │
│                                                                │
│  涉及 10 個功能: #18, #37, #49, #54, #57, #63-68             │
│  橫跨 6 個架構層級 (L1, L2, L4, L5, L7, L9)                 │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

**重要發現**: Swarm 目前不整合在 `HybridOrchestratorV2.execute_with_routing()` 的主流程中。它透過獨立的 Demo API (`/api/v1/swarm/demo/start`) 觸發，使用模擬進度。真實的 Swarm 執行需要 `ClaudeCoordinator`（在 `claude_sdk/orchestrator`）作為上游呼叫者。

### 場景三 (對比)：n8n 適合的場景

對於**結構化、可預測、規則式**的自動化任務（如固定時間備份、定期報表產生），n8n 的視覺化工作流編排器更為合適。IPA Platform 的價值在於需要**判斷力、即時決策、多 Agent 協作**的複雜場景。

---

## 附錄 A: 代碼庫規模快速參考 (V7 驗證)

| 指標 | V6 數值 | V7 數值 | 變化 |
|------|---------|---------|------|
| Backend .py files | ~630+ | **611** | 修正 (V6 可能含 pycache) |
| **Backend LOC** | **~130,000+** | **~228,700** | **重大修正 (+75%)** |
| Frontend .tsx/.ts | 203 | **203** | 不變 |
| **Frontend LOC** | 未統計 | **47,630** | 新增指標 |
| Integration modules | 16 | **16** | 不變 |
| Integration files | 315 | **315** | 不變 |
| Integration LOC | ~125,700 | **125,700** | 不變 |
| Domain modules | 20 | **20** | 不變 |
| Domain files | 112 | **112** | 不變 |
| Domain LOC | ~40,000+ | **47,214** | 首次精確統計 |
| API Route Modules | 39 | **39** | 不變 |
| API Route Files | 137 | **138** | +1 (demo.py) |
| API Registered Routers | 47 | **47** | 不變 |
| API Endpoints | 530 | **528** | -2 (排除 docstring) |
| Frontend Pages | 39 (37 tsx) | **39** | 不變 |
| Frontend Component Files | 110 | **127** | 修正 |
| Frontend Hooks | 20 | **20** | 不變 |
| Frontend Stores | 3 | **3+1 test** | 精確 |
| Frontend Routes | 23 | **23** | 不變 |
| Test Files | 247 pure + 58 support | **247+58** | 不變 |
| MAF Builder Files | 23 | **23** | 不變 |
| MCP Servers | 5 | **5** | 不變 |
| Checkpoint Systems | 2 | **4** | 修正 (4 個獨立系統) |
| Mock classes | 18 | **18** | 不變 |
| InMemory classes | 9 | **9** | 不變 |
| Empty function bodies | ~323 | **323** | 不變 |
| Files > 800 lines | 57 | **58** | +1 (50 BE + 8 FE) |
| console.log | 54 | **54** | 不變 |
| Phases Completed | 29 | **29** | 不變 |
| Sprints Completed | 106 | **106** | 不變 |

> **V7 LOC 修正說明**: V6 聲稱 Backend LOC 約 130,000+，但實際 `backend/src/` 為 ~228,700 LOC。
> 差異原因：V6 使用 `find | xargs wc -l | tail -1` 統計，在 Windows/MSYS2 環境下因 xargs
> 命令行長度限制導致大量檔案被截斷未計入。V7 使用 `xargs -I{} wc -l {}` 逐檔計算，避免截斷問題。
> 單 integrations/ 就有 125,700 LOC，已超過 V6 的全部 Backend 估計值。

---

## 附錄 B: V6→V7 功能編號對照

V6 使用不同的編號系統 (1-68)，V7 保持 V6 編號但以 V3 的繁體中文格式呈現。

| V6 # | V7 # | 名稱 | V6 狀態 | V7 狀態 |
|------|------|------|---------|---------|
| 1-9 | 1-9 | Builder Adapters | REAL/REAL+MOCK | ✅ |
| 10-16 | 10-16 | Extensions | Extension | ✅ |
| 17-23 | 17-23 | HITL | REAL/REAL+MOCK | ✅ |
| 24-28 | 24-28 | State & Memory | REAL | ✅ |
| 29-36 | 29-36 | Frontend | REAL/MISSING | ✅/❌ |
| 37-47 | 37-47 | Connectivity | REAL/REAL+MOCK | ✅ |
| 48-57 | 48-57 | Intelligent Decision | REAL/REAL+MOCK | ✅ |
| 58-62 | 58-62 | Observability | REAL/STUB | ✅/⚠️ |
| 63-68 | 63-68 | Agent Swarm | REAL | ✅ |

**V6→V7 狀態轉換規則**:

| V6 Status | V7 Status | 說明 |
|-----------|-----------|------|
| REAL | ✅ | 完整實現 |
| REAL+MOCK | ✅ | 完整實現（有 Mock fallback 時加註） |
| STUB | ⚠️ | 部分實現（有代碼但數據造假） |
| MISSING | ❌ | 未找到 |
| Extension | ✅ | 擴展功能（歸入主分類） |

---

## 更新歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 7.0 | 2026-02-11 | **格式重整 + 數據修正版**：以 V3 繁體中文格式重寫 V6 內容；Backend LOC 從 ~130K **修正為 ~228.7K** (V6 xargs 截斷)；端點 530→528 (排除 docstring)；>800 行檔案 57→58；Checkpoint 系統 2→4 (新發現)；新增 Frontend LOC 47,630；新增安全風險評估章節；新增端到端流程驗證 (32/37 路徑有效)；新增八大能力矩陣；8+3 Agent 並行驗證 (V6 為 5 Agent) |
| 6.0 | 2026-02-11 | 全面更新：5 Agent Team 並行驗證；64 功能維持不變；修正 V5 的 11 項錯誤 (agent_executor MAF, Mock 18, endpoints 530 等)；新增安全指標 (Auth 7%, Rate Limiting, CORS)；新增測試覆蓋指標 |
| 3.0 | 2026-02-09 | 全面重寫：5 Agent 並行深度驗證；擴展至 65 功能 (+6 Swarm)；#31 降級 ❌；#49/#50 真實化 |
| 2.1 | 2026-01-28 | 補回 V1 架構圖示 |
| 2.0 | 2026-01-28 | 全面重寫：擴展至 59 功能 |
| 1.0 | 2025-12-01 | 初始版本 - 50 功能 |
