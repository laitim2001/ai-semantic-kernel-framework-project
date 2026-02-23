# 智能體編排平台功能架構映射指南

> **文件版本**: 3.0
> **最後更新**: 2026-02-09
> **定位**: Agent Orchestration Platform (智能體編排平台)
> **前置文件**: `MAF-Claude-Hybrid-Architecture-V3.md` (架構總覽)
> **狀態**: Phase 29 已完成 (106 Sprints, ~2400 Story Points)
> **驗證方式**: 5 個專業分析 Agent 並行深度代碼庫逐一驗證

---

## 實現狀態總覽

> **重要說明**: 本文件是 V2 (59 功能, 2026-01-28) 的全面更新。
> V3 擴展至 **65 個功能**，新增 Phase 29 Agent Swarm Visualization 的 6 個功能。
> 基於 2026-02-09 的代碼庫由 5 個分析 Agent 逐一驗證，所有檔案行數均為實測值。

### 65 功能驗證結果

| 狀態 | 數量 | 比例 | 說明 |
|------|------|------|------|
| ✅ 完整實現 | 57 | 87.7% | 代碼庫中有完整實現與對應檔案 |
| ⚠️ 部分實現 | 4 | 6.2% | 有相關代碼但不完整或分散 |
| ❌ 未找到 / 最低限度 | 4 | 6.2% | 缺乏獨立實現或未找到 |
| | **65** | **93.8% 至少部分** | |

### 按類別統計

| 類別 | 功能數 | ✅ | ⚠️ | ❌ | 實現率 |
|------|--------|-----|-----|-----|--------|
| Agent 編排能力 | 12 | 12 | 0 | 0 | 100% |
| 人機協作能力 | 7 | 7 | 0 | 0 | 100% |
| 狀態與記憶能力 | 5 | 5 | 0 | 0 | 100% |
| 前端介面能力 | 8 | 5 | 1 | 2 | 62.5% 完整 |
| 連接與整合能力 | 11 | 8 | 2 | 1 | 73% 完整 |
| 智能決策能力 | 10 | 10 | 0 | 0 | 100% |
| 可觀測性能力 | 6 | 6 | 0 | 0 | 100% |
| **Agent Swarm 能力** | **6** | **6** | **0** | **0** | **100%** |

### V2 → V3 狀態變更

| 功能 | V2 狀態 | V3 狀態 | 變更原因 |
|------|---------|---------|----------|
| #31 WorkflowViz | ⚠️ 部分 | ❌ 未找到 | ReactFlow 確認未安裝 (package.json 驗證) |
| #49 SemanticRouter | ✅ | ✅ (增強) | CHANGE-003: 支援真實 Azure OpenAI embeddings |
| #50 LLMClassifier | ✅ | ✅ (增強) | CHANGE-003: 支援真實 Claude Haiku 分類 |
| #60-65 | - | ✅ NEW | Phase 29 Agent Swarm 新增 6 功能 |

---

## 執行摘要

IPA Platform 是一個**智能體編排平台 (Agent Orchestration Platform)**，透過 MAF + Claude Agent SDK 混合架構，協調智能體集群處理需要判斷力、專業知識與人機互動的複雜任務。

**65 個功能**構成平台的八大能力領域：

1. **Agent 編排** (12 功能) --- 12 種編排模式，從 Sequential 到 Magentic，全部基於 MAF Builder
2. **人機協作** (7 功能) --- 完整 HITL 生命週期：檢查點 → 審批 → 通知 → 前端介面
3. **狀態與記憶** (5 功能) --- Redis/Postgres 檢查點 + 對話記憶 + mem0 長期記憶
4. **前端介面** (8 功能) --- 39 頁面 + Unified Chat + DevUI + Dashboard
5. **連接與整合** (11 功能) --- InputGateway + 企業連接器 + A2A Protocol
6. **智能決策** (10 功能) --- 三層意圖路由 (已支援真實 LLM) + 自主決策 + Few-shot
7. **可觀測性** (6 功能) --- 審計 + 巡檢 + 指標 + 關聯分析
8. **Agent Swarm** (6 功能) --- 多 Agent 群集視覺化、即時追蹤、SSE 串流 **(Phase 29 NEW)**

---

## 1. 架構層級與功能映射總覽

### 1.1 架構層級定義 (11 層模型)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    完整架構層級 (Phase 29, V3 - 11 層模型)                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Layer 1: 前端展示層 (Frontend Layer)                                               │
│  ════════════════════════════════════                                                │
│  • React 18 + TypeScript + Vite (port 3005)                                         │
│  • Unified Chat UI (25+ components)                                                 │
│  • AG-UI Components (chat, hitl, advanced)                                          │
│  • Agent Swarm Panel (16 components) ← NEW Phase 29                                │
│  • DevUI 開發者工具 • Dashboard • Approval Page • SwarmTestPage                    │
│                                                                                      │
│  Layer 2: API 路由層 (API Layer)                                                     │
│  ═══════════════════════════════                                                     │
│  • 39 API Route Modules, ~534 Endpoints, 41 Registered Routers                     │
│  • FastAPI + Uvicorn (port 8000)                                                    │
│  • NEW: Swarm API (3 status + 5 demo endpoints) ← Phase 29                        │
│                                                                                      │
│  Layer 3: AG-UI Protocol 層                                                          │
│  ═════════════════════════                                                           │
│  • SSE Bridge (Server-Sent Events) + Swarm Event Streaming                         │
│  • HITL 審批事件 + 思考過程串流 + Swarm CustomEvent                                │
│  • SharedState 前後端同步                                                            │
│                                                                                      │
│  Layer 4: Phase 28 編排入口層 (Orchestration Entry Layer)                             │
│  ════════════════════════════════════════════════════════                             │
│  • InputGateway + BusinessIntentRouter (三層瀑布式路由)                              │
│  • GuidedDialogEngine + RiskAssessor + HITLController                               │
│  • OrchestrationMetrics (893 LOC, OTel)                                             │
│                                                                                      │
│  Layer 5: 混合編排層 (Hybrid Orchestration Layer)                                    │
│  ════════════════════════════════════════════════                                    │
│  • HybridOrchestratorV2 (1,254 LOC)                                                │
│  • FrameworkSelector + ContextBridge + ContextSynchronizer                          │
│                                                                                      │
│  Layer 6: MAF Builder 層 (Agent Framework Layer)                                     │
│  ═══════════════════════════════════════════════                                     │
│  • 22 Builder files (from agent_framework import ...)                               │
│  • 53 files total, 37,209 LOC — 最成熟的整合層                                     │
│                                                                                      │
│  Layer 7: Claude SDK 執行層 (Execution Layer)                                        │
│  ════════════════════════════════════════════                                        │
│  • ClaudeSDKClient (AsyncAnthropic)                                                 │
│  • Autonomous Pipeline + Hook System + MCP Client                                   │
│  • 46 files, 15,098 LOC                                                             │
│                                                                                      │
│  Layer 8: MCP 工具層 (Tool Layer)                                                    │
│  ════════════════════════════════                                                    │
│  • 5 MCP Servers (Azure, Shell, Filesystem, SSH, LDAP)                             │
│  • Security: 28 permission patterns, 16 audit patterns                              │
│                                                                                      │
│  Layer 9: 支援整合層 (Supporting Integrations)                                       │
│  ═════════════════════════════════════════════                                       │
│  • Memory (mem0) | Patrol | Learning | Correlation | Audit | A2A                   │
│  • NEW: Swarm (7 files, 2,747 LOC) ← Phase 29                                     │
│                                                                                      │
│  Layer 10: 業務邏輯層 (Domain Layer)                                                  │
│  ══════════════════════════════════                                                  │
│  • 19 Domain Modules (112 files)                                                    │
│                                                                                      │
│  Layer 11: 基礎設施層 (Infrastructure Layer)                                         │
│  ════════════════════════════════════════════                                        │
│  • PostgreSQL 16 ✅ | Redis 7 ✅                                                     │
│  • RabbitMQ ❌ 空殼 | Storage ❌ 空目錄                                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| 層級 | 名稱 | 說明 | 檔案規模 (V3 驗證) |
|------|------|------|----------|
| **L1** | Frontend | React 18 + TypeScript + Vite | ~180 .tsx/.ts, 39 pages, 102+ components |
| **L2** | API Layer | 39 modules, ~534 endpoints | 137 route files, 41 routers |
| **L3** | AG-UI Protocol | SSE Bridge + HITL + Swarm Events | 23 files, ~9,531 LOC |
| **L4** | Phase 28 Orchestration | 三層意圖路由 + 引導對話 + 風險評估 + HITL | 39 files, ~15,753 LOC |
| **L5** | Hybrid Layer | HybridOrchestratorV2 + 框架切換 + 上下文橋接 | 59 files, ~21,197 LOC |
| **L6** | MAF Builder Layer | 22 Builders + 支援檔案，MAF 官方 API | 53 files, ~37,209 LOC |
| **L7** | Claude SDK Layer | 自主執行管線 + Hook 系統 | 46 files, ~15,098 LOC |
| **L8** | MCP Layer | 5 個 MCP Server + 安全模組 | 42 files, ~12,535 LOC |
| **L9** | Supporting + Swarm | 記憶、巡檢、學習、關聯、審計、A2A、**Swarm** | 43 files, ~12,592 LOC |
| **L10** | Domain Layer | 19 domain modules 業務邏輯 | 112 files, ~40,000+ LOC |
| **L11** | Infrastructure | PostgreSQL + Redis + RabbitMQ (空) + Storage (空) | ~22 files, ~3,101 LOC |

### 1.2 功能分類與架構層級對應

| 類別 | 主要層級 | 功能數 |
|------|----------|--------|
| Agent 編排能力 | Layer 6 (MAF Builder) + Layer 5 (Hybrid) | 12 |
| 人機協作能力 | Layer 4 (Orchestration) + Layer 3 (AG-UI) + Layer 1 (Frontend) | 7 |
| 狀態與記憶能力 | Layer 5 (Hybrid Checkpoint) + Layer 9 (Memory) + Layer 10 (Domain) | 5 |
| 前端介面能力 | Layer 1 (Frontend) | 8 |
| 連接與整合能力 | Layer 4 (InputGateway) + Layer 8 (MCP) + Layer 9 (A2A) | 11 |
| 智能決策能力 | Layer 4 (Intent Router) + Layer 5 (Hybrid) + Layer 7 (Claude SDK) | 10 |
| 可觀測性能力 | Layer 4 (Metrics) + Layer 9 (Patrol/Audit/Correlation) | 6 |
| **Agent Swarm 能力** | **Layer 9 (Swarm) + Layer 3 (AG-UI) + Layer 2 (API) + Layer 1 (Frontend)** | **6** |

### 1.3 功能實現狀態速查表

| # | 功能名稱 | 狀態 | 架構層級 | 主要實現位置 | V3 行數 |
|---|---------|------|----------|-------------|---------|
| 1 | Sequential 編排 | ✅ | L6 | `builders/workflow_executor.py` | 1,308 |
| 2 | Concurrent 並行 | ✅ | L6 | `builders/concurrent.py` | 1,633 |
| 3 | GroupChat 群組 | ✅ | L6 | `builders/groupchat.py` | 1,912 |
| 4 | Handoff 交接 | ✅ | L6 | `builders/handoff.py` | 994 |
| 5 | Nested Workflows | ✅ | L6 | `builders/nested_workflow.py` | 1,307 |
| 6 | Sub-workflow | ✅ | L10 | `domain/orchestration/nested/sub_executor.py` | - |
| 7 | Recursive Patterns | ✅ | L10 | `recursive_handler.py` + `workflow_manager.py` | - |
| 8 | Dynamic Planning | ✅ | L6 | `builders/planning.py` | 1,364 |
| 9 | Magentic 推理鏈 | ✅ | L6 | `builders/magentic.py` | 1,809 |
| 10 | Voting 投票 | ✅ | L6 | `builders/groupchat_voting.py` | 736 |
| 11 | Capability Matcher | ✅ | L6 | `builders/handoff_capability.py` | 1,050 |
| 12 | Termination 條件 | ✅ | L6 | `groupchat.py` + `handoff.py` TerminationType | - |
| 13 | HITL Checkpoints | ✅ | L3 | `ag_ui/features/human_in_loop.py` | 744 |
| 14 | HITL Manager | ✅ | L6 | `builders/handoff_hitl.py` | 1,005 |
| 15 | HITLController | ✅ | L4 | `orchestration/hitl/controller.py` | 788 |
| 16 | Approval Handler | ✅ | L4 | `orchestration/hitl/approval_handler.py` | 693 |
| 17 | Teams Notification | ✅ | L4 | `orchestration/hitl/notification.py` | 732 |
| 18 | HITL 功能擴展 | ✅ | L3-L6 | Full HITL stack across 4 modules | - |
| 19 | Pending Approval Page | ✅ | L1 | `frontend/src/pages/approvals/` | - |
| 20 | Redis/Postgres Checkpoint | ✅ | L5 | `hybrid/checkpoint/backends/` | redis 438, postgres 485 |
| 21 | Conversation Memory | ✅ | L5 | `session_state.py` + stores | 575 |
| 22 | Context Transfer | ✅ | L5 | `context/bridge.py` + `synchronizer.py` | 932 + 629 |
| 23 | Multi-turn Dialog | ✅ | L10 | `domain/orchestration/multiturn/` (3 files) | - |
| 24 | mem0 長期記憶 | ✅ | L9 | `memory/mem0_client.py` + `unified_memory.py` | 446 + 683 |
| 25 | Modern Web UI | ✅ | L1 | 39 page files, 25 routable, 23 routes | - |
| 26 | DevUI 開發者介面 | ✅ | L1 | 7 DevUI pages + 16 components | - |
| 27 | Dashboard 儀表板 | ✅ | L1 | `DashboardPage` + 4 sub-components | - |
| 28 | Stats Cards | ✅ | L1 | `StatsCards.tsx` | - |
| 29 | Approval Page | ✅ | L1 | `ApprovalsPage.tsx` | - |
| 30 | Performance Page | ✅ | L1 | `PerformancePage.tsx` | - |
| 31 | WorkflowViz 視覺化 | ❌ | L1 | ReactFlow **未安裝** (package.json 驗證) | - |
| 32 | Notification System | ⚠️ | L1 | Header toast only，無通知中心 | - |
| 33 | Cross-system Connectors | ✅ | L8 | `dynamics365`, `servicenow`, `sharepoint` | - |
| 34 | Enhanced Gateway | ⚠️ | L4+L8 | 分散於 client + orchestrator | - |
| 35 | n8n Trigger | ✅ | L4 | `triggers/webhook.py` | - |
| 36 | InputGateway | ✅ | L4 | `input_gateway/gateway.py` + 5 handlers | ~400 |
| 37 | ServiceNow Handler | ✅ | L4 | `source_handlers/servicenow_handler.py` | 399 |
| 38 | Prometheus Handler | ✅ | L4 | `source_handlers/prometheus_handler.py` | 412 |
| 39 | UserInput Handler | ✅ | L4 | `source_handlers/user_input_handler.py` | 294 |
| 40 | A2A Protocol | ✅ | L9 | `a2a/` (4 files) | 888 total |
| 41 | Collaboration Protocol | ⚠️ | L9 | 由 A2A 基礎功能覆蓋 | - |
| 42 | Cross-scenario 協作 | ❌ | - | **未找到** | - |
| 43 | Handoff Service | ✅ | L6 | `builders/handoff_service.py` | 821 |
| 44 | Intelligent Routing | ✅ | L5 | `hybrid/intent/` (7 files) | ~1,600 |
| 45 | Autonomous Decision | ✅ | L7 | `autonomous/` (7 files) | ~2,800 |
| 46 | Trial-and-Error | ✅ | L7 | `retry.py` + `fallback.py` | 393 + 587 |
| 47 | Few-shot Learning | ✅ | L9 | `learning/few_shot.py` | 456 |
| 48 | PatternMatcher | ✅ | L4 | `pattern_matcher/matcher.py` | 358 |
| 49 | SemanticRouter | ✅ | L4 | `semantic_router/router.py` (**真實 Azure OpenAI**) | 465 |
| 50 | LLMClassifier | ✅ | L4 | `llm_classifier/classifier.py` (**真實 Claude Haiku**) | 438 |
| 51 | GuidedDialogEngine | ✅ | L4 | `guided_dialog/` (engine + context_manager + generator) | 593+1163+1151 |
| 52 | RiskAssessor | ✅ | L4 | `risk_assessor/` (assessor + policies) | 639+711 |
| 53 | CompletenessChecker | ✅ | L4 | `completeness/` (checker + rules) | 443+658 |
| 54 | Audit Trail | ✅ | L9 | `audit/` (4 files) | 1,166 total |
| 55 | Redis Cache | ✅ | L9+L11 | `llm_cache.py` + redis backends | - |
| 56 | OrchestrationMetrics | ✅ | L4 | `orchestration/metrics.py` | 893 |
| 57 | Correlation Analysis | ✅ | L9 | `correlation/` (4 files) | 1,188 total |
| 58 | Patrol 巡檢 | ✅ | L9 | `patrol/` (11 files) | 2,541 total |
| 59 | Agent Templates | ✅ | L10+L1 | `domain/templates/` + frontend | - |
| **60** | **SwarmTracker** | **✅** | **L9** | **`swarm/tracker.py`** | **693** |
| **61** | **SwarmEventEmitter** | **✅** | **L9** | **`swarm/events/emitter.py`** | **634** |
| **62** | **SwarmIntegration** | **✅** | **L9** | **`swarm/swarm_integration.py`** | **404** |
| **63** | **Swarm API** | **✅** | **L2** | **`api/v1/swarm/` (5 files, 8 endpoints)** | **~1,064** |
| **64** | **Swarm Frontend Panel** | **✅** | **L1** | **16 components + 4 hooks in `agent-swarm/`** | **~3,000** |
| **65** | **SwarmTestPage** | **✅** | **L1** | **`SwarmTestPage.tsx` + useSwarmMock + useSwarmReal** | **844+623+603** |

---

## 2. 功能詳細映射

> **路徑約定**: 以下所有路徑均相對於 `backend/src/integrations/`，除非另有標註。
> Frontend 路徑相對於 `frontend/src/`。行號為 V3 驗證時的實測行數。

### 2.1 Agent 編排能力 (12 功能)

12 種編排模式全部基於 MAF Builder Layer，使用 `from agent_framework import` 官方 API。

| # | 功能 | 狀態 | 層級 | 實現檔案 | V3 驗證行數 |
|---|------|------|------|----------|------------|
| 1 | **Sequential** | ✅ | L6 | `agent_framework/builders/workflow_executor.py` | 1,308 |
| 2 | **Concurrent** | ✅ | L6 | `agent_framework/builders/concurrent.py` | 1,633 |
| 3 | **GroupChat** | ✅ | L6 | `agent_framework/builders/groupchat.py` | 1,912 |
| 4 | **Handoff** | ✅ | L6 | `agent_framework/builders/handoff.py` | 994 |
| 5 | **Nested Workflows** | ✅ | L6 | `agent_framework/builders/nested_workflow.py` | 1,307 |
| 6 | **Sub-workflow** | ✅ | L10 | `domain/orchestration/nested/sub_executor.py` | - |
| 7 | **Recursive** | ✅ | L10 | `domain/orchestration/nested/recursive_handler.py` | - |
| 8 | **Dynamic Planning** | ✅ | L6 | `agent_framework/builders/planning.py` | 1,364 |
| 9 | **Magentic** | ✅ | L6 | `agent_framework/builders/magentic.py` | 1,809 |
| 10 | **Voting** | ✅ | L6 | `agent_framework/builders/groupchat_voting.py` | 736 |
| 11 | **Capability Matcher** | ✅ | L6 | `agent_framework/builders/handoff_capability.py` | 1,050 |
| 12 | **Termination** | ✅ | L6 | `groupchat.py` + `handoff.py` TerminationType | - |

**支援檔案** (均位於 `agent_framework/builders/`):
- `handoff_hitl.py` (1,005) - HITL 整合 Handoff
- `handoff_policy.py` (513) - Handoff 策略管理
- `handoff_context.py` (855) - 上下文傳遞
- `handoff_service.py` (821) - Handoff 服務層
- `groupchat_orchestrator.py` (883) - GroupChat 編排
- `edge_routing.py` (884) - 邊緣路由
- `*_migration.py` (5 files) - 遷移適配器
- `__init__.py` (805) - 統一重新匯出

### 2.2 人機協作能力 (7 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V3 驗證行數 |
|---|------|------|------|----------|------------|
| 13 | **HITL Checkpoints** | ✅ | L3 | `ag_ui/features/human_in_loop.py` | 744 |
| 14 | **HITL Manager** | ✅ | L6 | `builders/handoff_hitl.py` | 1,005 |
| 15 | **HITLController** | ✅ | L4 | `orchestration/hitl/controller.py` | 788 |
| 16 | **Approval Handler** | ✅ | L4 | `orchestration/hitl/approval_handler.py` | 693 |
| 17 | **Teams Notification** | ✅ | L4 | `orchestration/hitl/notification.py` | 732 |
| 18 | **HITL 功能擴展** | ✅ | L3-L6 | 跨 4 模組完整 stack | - |
| 19 | **Pending Approval Page** | ✅ | L1 | `frontend/src/pages/approvals/` | - |

### 2.3 狀態與記憶能力 (5 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V3 驗證行數 |
|---|------|------|------|----------|------------|
| 20 | **Redis/Postgres Checkpoint** | ✅ | L5 | `hybrid/checkpoint/backends/` | redis 438, postgres 485, fs 469, mem 295 |
| 21 | **Conversation Memory** | ✅ | L5 | `claude_sdk/session_state.py` | 575 |
| 22 | **Context Transfer** | ✅ | L5 | `hybrid/context/bridge.py` + `sync/synchronizer.py` | 932 + 629 |
| 23 | **Multi-turn Dialog** | ✅ | L10 | `domain/orchestration/multiturn/` (3 files) | - |
| 24 | **mem0 長期記憶** | ✅ | L9 | `memory/mem0_client.py` + `unified_memory.py` | 446 + 683 |

**已知問題**: `ContextSynchronizer` 使用 `Dict` 存儲，無 `asyncio.Lock`，在並行場景下有競爭條件風險 (嚴重度: 高)。

### 2.4 前端介面能力 (8 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | 說明 |
|---|------|------|------|----------|------|
| 25 | **Modern Web UI** | ✅ | L1 | 39 page files, 25 routable, 23 routes | SPA + Vite |
| 26 | **DevUI** | ✅ | L1 | 7 pages + 16 DevUI components | 開發者工具 |
| 27 | **Dashboard** | ✅ | L1 | `DashboardPage` + 4 sub-components | 監控儀表板 |
| 28 | **Stats Cards** | ✅ | L1 | `StatsCards.tsx` | 統計卡片 |
| 29 | **Approval Page** | ✅ | L1 | `ApprovalsPage.tsx` | 待審批管理 |
| 30 | **Performance Page** | ✅ | L1 | `PerformancePage.tsx` | 效能監控 |
| 31 | **WorkflowViz** | ❌ | L1 | ReactFlow **未安裝** | package.json 無此依賴 |
| 32 | **Notification System** | ⚠️ | L1 | Header toast only | 無專用通知中心 |

**V3 驗證發現**: #31 狀態從 V2 的 ⚠️ 降級為 ❌。`package.json` 中無 `@xyflow/react` 或 `reactflow` 依賴。`.claude/skills/react-flow/` 目錄存在但未使用。Swarm 視覺化使用自訂卡片元件而非 ReactFlow。

**Frontend 技術棧** (V3 驗證):
- **框架**: React ^18.2.0 + TypeScript ^5.3.3 + Vite ^5.0.11
- **UI 庫**: Shadcn/Radix (16 primitives, 12 Radix packages)
- **狀態管理**: Zustand ^4.4.7 + immer ^11.1.3 + React Query ^5.17.0
- **API 通訊**: **Fetch API** (非 Axios，Axios 未在 dependencies 中)
- **Custom Hooks**: 20 (16 top-level + 4 internal swarm hooks)
- **Stores**: 3 (authStore, unifiedChatStore, **swarmStore** NEW)

### 2.5 連接與整合能力 (11 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V3 驗證行數 |
|---|------|------|------|----------|------------|
| 33 | **Cross-system Connectors** | ✅ | L8 | MCP Server 包裝 | - |
| 34 | **Enhanced Gateway** | ⚠️ | L4+L8 | 分散，無獨立閘道 | - |
| 35 | **n8n Trigger** | ✅ | L4 | `triggers/webhook.py` | - |
| 36 | **InputGateway** | ✅ | L4 | `input_gateway/gateway.py` + handlers | ~400 |
| 37 | **ServiceNow Handler** | ✅ | L4 | `source_handlers/servicenow_handler.py` | 399 |
| 38 | **Prometheus Handler** | ✅ | L4 | `source_handlers/prometheus_handler.py` | 412 |
| 39 | **UserInput Handler** | ✅ | L4 | `source_handlers/user_input_handler.py` | 294 |
| 40 | **A2A Protocol** | ✅ | L9 | `a2a/` (discovery 351, protocol 293, router 183) | 888 |
| 41 | **Collaboration Protocol** | ⚠️ | L9 | A2A 基礎覆蓋 | - |
| 42 | **Cross-scenario** | ❌ | - | **未找到** | - |
| 43 | **Handoff Service** | ✅ | L6 | `builders/handoff_service.py` | 821 |

### 2.6 智能決策能力 (10 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V3 驗證行數 |
|---|------|------|------|----------|------------|
| 44 | **Intelligent Routing** | ✅ | L5 | `hybrid/intent/` (7 files) | ~1,600 |
| 45 | **Autonomous Decision** | ✅ | L7 | `autonomous/` (7 files) | ~2,800 |
| 46 | **Trial-and-Error** | ✅ | L7 | `retry.py` + `fallback.py` | 393 + 587 |
| 47 | **Few-shot Learning** | ✅ | L9 | `learning/few_shot.py` | 456 |
| 48 | **PatternMatcher** | ✅ | L4 | `pattern_matcher/matcher.py` | 358 |
| 49 | **SemanticRouter** | ✅ | L4 | `semantic_router/router.py` | 465 |
| 50 | **LLMClassifier** | ✅ | L4 | `llm_classifier/classifier.py` | 438 |
| 51 | **GuidedDialogEngine** | ✅ | L4 | `guided_dialog/` (4 core files) | ~3,700 total |
| 52 | **RiskAssessor** | ✅ | L4 | `risk_assessor/` (2 core files) | ~1,350 total |
| 53 | **CompletenessChecker** | ✅ | L4 | `completeness/` (checker + rules) | ~1,100 total |

**V3 重要更新 (CHANGE-003)**:
- #49 SemanticRouter 現支援**真實 Azure OpenAI embeddings** (非 Mock)
- #50 LLMClassifier 現支援**真實 Claude Haiku** 分類 (非 Mock)
- 透過 `USE_REAL_ROUTER` 環境變數控制，無 API key 時自動降級至 Mock

### 2.7 可觀測性能力 (6 功能)

| # | 功能 | 狀態 | 層級 | 實現檔案 | V3 驗證行數 |
|---|------|------|------|----------|------------|
| 54 | **Audit Trail** | ✅ | L9 | `audit/` (decision_tracker 447, report 341, types 296) | 1,166 |
| 55 | **Redis Cache** | ✅ | L9+L11 | `llm/cached.py` + `infrastructure/cache/llm_cache.py` | - |
| 56 | **OrchestrationMetrics** | ✅ | L4 | `orchestration/metrics.py` | 893 |
| 57 | **Correlation Analysis** | ✅ | L9 | `correlation/` (analyzer 523, graph 430) | 1,188 |
| 58 | **Patrol 巡檢** | ✅ | L9 | `patrol/` (agent 454, scheduler 362, 5 checks) | 2,541 |
| 59 | **Agent Templates** | ✅ | L10+L1 | `domain/templates/` + frontend | - |

### 2.8 Agent Swarm 能力 (6 功能) — Phase 29 NEW

Phase 29 (Sprint 100-106) 新增的多 Agent 群集即時視覺化系統。

| # | 功能 | 狀態 | 層級 | 實現檔案 | V3 驗證行數 |
|---|------|------|------|----------|------------|
| 60 | **SwarmTracker** | ✅ | L9 | `swarm/tracker.py` | 693 |
| 61 | **SwarmEventEmitter** | ✅ | L9 | `swarm/events/emitter.py` | 634 |
| 62 | **SwarmIntegration** | ✅ | L9 | `swarm/swarm_integration.py` | 404 |
| 63 | **Swarm API** | ✅ | L2 | `api/v1/swarm/` (5 files) | ~1,064 |
| 64 | **Swarm Frontend Panel** | ✅ | L1 | 16 components + 4 hooks in `agent-swarm/` | ~3,000 |
| 65 | **SwarmTestPage** | ✅ | L1 | `SwarmTestPage.tsx` + useSwarmMock + useSwarmReal | 844+623+603 |

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
| **L1** Frontend | #19, #25-32, #64-65 | 11 |
| **L2** API Layer | #63 + (所有功能皆有 API endpoint) | 1+ |
| **L3** AG-UI Protocol | #13, #18 | 2 |
| **L4** Phase 28 Orchestration | #15-17, #35-39, #48-53, #56 | 14 |
| **L5** Hybrid Layer | #20-22, #44 | 4 |
| **L6** MAF Builder | #1-5, #8-12, #14, #43 | 14 |
| **L7** Claude SDK | #45-46 | 2 |
| **L8** MCP Layer | #33 | 1 |
| **L9** Supporting + Swarm | #24, #40-41, #47, #54-55, #57-58, **#60-62** | 11 |
| **L10** Domain Layer | #6-7, #23, #59 | 4 |
| **L11** Infrastructure | #55 (Redis backend) | 1 |

### 3.2 架構層級功能分布

```
L1  Frontend:             ███████████  11 功能 (含 Swarm 前端)
L2  API:                  █            1 功能 (Swarm API) + 橫切所有
L3  AG-UI:                ██           2 功能
L4  Orchestration:        ██████████████ 14 功能 (Phase 28 智能入口)
L5  Hybrid:               ████         4 功能
L6  MAF Builder:          ██████████████ 14 功能 (編排核心)
L7  Claude SDK:           ██           2 功能
L8  MCP:                  █            1 功能
L9  Supporting+Swarm:     ███████████  11 功能 (含 Swarm 後端)
L10 Domain:               ████         4 功能
L11 Infrastructure:       █            1 功能
```

### 3.3 功能缺口分析

| 功能 | 狀態 | 缺口描述 | 影響 | 建議優先級 |
|------|------|----------|------|-----------|
| #31 WorkflowViz | ❌ | ReactFlow 未安裝，無視覺化工作流編輯器 | 缺少核心視覺化能力 | P1 |
| #32 Notification System | ⚠️ | 僅 Header toast | 使用者可能錯過通知 | P2 |
| #34 Enhanced Gateway | ⚠️ | 功能分散無統一入口 | 架構清晰度 | P3 |
| #41 Collaboration Protocol | ⚠️ | 僅 A2A 基礎 | 跨 Agent 協作受限 | P3 |
| #42 Cross-scenario | ❌ | 完全未找到 | 跨場景協作不可用 | P3 |

---

## 4. 智能體編排平台能力總結

### 4.0 V1 → V2 → V3 功能演進對照

| 維度 | V1 (50 功能) | V2 (59 功能) | V3 (65 功能) | V2→V3 變化 |
|------|-------------|-------------|-------------|-----------|
| 功能總數 | 50 | 59 | **65** | +6 (Phase 29) |
| 類別數 | 7 | 7 | **8** | +1 (Agent Swarm) |
| Phases | 28 | 28 | **29** | +1 |
| Sprints | 99 | 99 | **106** | +7 |
| 編排模式 | 12 | 12 | 12 | 不變 |
| 人機協作 | 6→7 | 7 | 7 | 不變 |
| 狀態管理 | 5 | 5 | 5 | 不變 |
| 前端介面 | 8 | 8 | 8 | #31 降級 ⚠️→❌ |
| 連接整合 | 8→11 | 11 | 11 | 不變 |
| 智能決策 | 6→10 | 10 | 10 | #49/#50 真實化 |
| 可觀測性 | 5→6 | 6 | 6 | 不變 |
| Agent Swarm | - | - | **6** | **全新** |
| 驗證方式 | 自評 | 代碼庫逐一驗證 | **5 Agent 並行深度驗證** | 最高精度 |
| Integration 模組 | 15 | 15 | **16** | +swarm/ |
| API 模組 | 38 | 38 | **39** | +swarm/ |
| API 端點 | ~526 | ~526 | **~534** | +8 |
| Backend LOC | ~120K | ~120K | **~130K** | +~10K |
| Frontend 檔案 | 130+ | 130+ | **~180** | +~50 |

### 4.1 功能覆蓋率總結

- **87.7%** (57/65) 功能完整實現
- **93.8%** (61/65) 至少有部分實現
- **6.2%** (4/65) 存在缺口

最強領域：
- Agent 編排 (12/12, 100%) --- 22 Builder files, 37,209 LOC
- 人機協作 (7/7, 100%) --- 橫跨 4 模組 HITL stack
- 智能決策 (10/10, 100%) --- 三層路由 + 真實 LLM + Claude 自主
- 可觀測性 (6/6, 100%) --- 審計 + 巡檢 + 指標 + 關聯
- **Agent Swarm (6/6, 100%) --- 全新，跨 4 個測試類別完整覆蓋**

待改善領域：
- 前端介面 (5/8 完整) --- WorkflowViz 未實現，通知系統不完整
- 連接整合 (8/11 完整) --- 跨場景協作、統一閘道需補齊

### 4.2 已知技術債與風險 (V3 更新)

| # | 問題 | 影響功能 | 嚴重度 | V2 狀態 | V3 狀態 |
|---|------|----------|--------|---------|---------|
| 1 | ContextSynchronizer 記憶體狀態 (無鎖) | #22 | 高 | 已知 | **確認** |
| 2 | 單 Uvicorn Worker + reload=True | 全平台 | 高 | 已知 | **確認** |
| 3 | RabbitMQ 空殼 | 非同步分派 | 高 | 已知 | **確認** |
| 4 | 18 Mock 類在生產代碼中 | 代碼衛生 | 高 | 低 (V2) | **升級至高** |
| 5 | 6 InMemory* 存儲預設 | 資料持久性 | 高 | - | **新發現** |
| 6 | ReactFlow 未安裝 | #31 | 中 | - | **新發現** |
| 7 | 54 console.log 在前端 | 代碼品質 | 中 | - | **新發現** |
| 8 | 15 檔案超過 800 行限制 | 維護性 | 中 | - | **新發現** |
| 9 | infrastructure/storage/ 空目錄 | 架構完整性 | 中 | - | **新發現** |
| 10 | Stub 密度 ~6.6% (非 V2 的 1.1%) | 功能真實性 | 中 | 低 (1.1%) | **修正至 6.6%** |
| 11 | 10 個過時 TODO 引用已完成 Sprint | 代碼衛生 | 低 | - | **新發現** |

### 4.3 架構演進建議

| 優先級 | 方向 | 目標 | 涉及功能 |
|--------|------|------|----------|
| P0 | 生產化 | ContextSynchronizer 並行安全 + Multi-Worker Uvicorn | #22 |
| P0 | 代碼衛生 | 18 Mock 類遷移至 tests/fixtures/ | 全局 |
| P1 | 前端補齊 | ReactFlow 工作流視覺化安裝與實現 | #31 |
| P1 | 資料持久 | 6 InMemory* 替換為 Redis/Postgres | 多功能 |
| P1 | 整合完善 | 統一閘道重構、跨場景協作 | #34, #41, #42 |
| P2 | 基礎設施 | RabbitMQ 實現或移除 | 基礎設施 |
| P2 | 品質提升 | 移除 54 console.log + 分拆大檔案 | 全局 |
| P3 | 擴展 MCP | 新增 K8s / Database / Email MCP Server | 新功能 |

---

## 5. 端到端場景

### 場景一：ETL Pipeline 故障處理 (16 功能協同)

(與 V2 相同，涉及 #1, #2, #15-17, #19-21, #25, #27, #33, #36, #39, #44-48, #51-54, #56)

### 場景二：Agent Swarm 多專家協作分析 (NEW)

```
使用者：「分析我們的安全基礎設施，識別潛在漏洞」

┌──────────────────────────────────────────────────────────────┐
│  Swarm 多 Agent 協作場景                                        │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  User Input                                                    │
│      │                                                         │
│      ▼  [#36 InputGateway → #48 PatternMatcher]               │
│  IT_SECURITY_AUDIT (confidence 0.95)                          │
│      │                                                         │
│      ▼  [#52 RiskAssessor → #15 HITLController]               │
│  Risk: HIGH → 需要審批                                        │
│      │                                                         │
│      ▼  [#44 Intelligent Routing]                              │
│  複雜分析 → Claude SDK + Concurrent + Swarm 模式              │
│      │                                                         │
│      ▼  [#60 SwarmTracker — 建立群集]                         │
│  SwarmMode: PARALLEL, 4 Workers                               │
│      │                                                         │
│      ├──▶ Worker 1: ANALYST (網路安全) [#61 SSE: WorkerStarted]│
│      ├──▶ Worker 2: ANALYST (權限審計) [#61 SSE: WorkerStarted]│
│      ├──▶ Worker 3: REVIEWER (合規檢查) [#61 SSE: WorkerStarted]│
│      └──▶ Worker 4: CODER (修復建議)   [#61 SSE: WorkerStarted]│
│           │         │         │         │                      │
│           ▼         ▼         ▼         ▼                      │
│      [#62 SwarmIntegration 橋接 ClaudeCoordinator]            │
│           │         │         │         │                      │
│      [#61 SSE: WorkerThinking, WorkerToolCall, WorkerProgress]│
│           │         │         │         │                      │
│           └────┬────┴────┬────┘         │                      │
│                ▼         ▼              ▼                      │
│      [#64 Swarm Frontend Panel 即時顯示]                      │
│      • WorkerCard × 4 (各 Worker 狀態)                        │
│      • OverallProgress (整體進度)                              │
│      • ExtendedThinkingPanel (思考過程)                        │
│      • ToolCallsPanel (工具調用)                               │
│                                                                │
│  涉及 12 個功能: #15, #36, #44, #48, #52, #60-65            │
│  橫跨 6 個架構層級 (L1, L2, L4, L5, L7, L9)                 │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 附錄 A: 代碼庫規模快速參考 (V3 驗證)

| 指標 | V2 數值 | V3 數值 | 變化 |
|------|---------|---------|------|
| Backend .py files | ~600 | ~630+ | +30 |
| Backend LOC | ~120,000+ | ~130,000+ | +10,000 |
| Integration modules | 15 | 16 | +1 (swarm/) |
| Integration files | 200+ | ~315 | 精確計算 |
| Integration LOC | - | ~125,700 | 首次精確統計 |
| Domain modules | 20 | 19 | 修正 |
| Domain files | 114 | 112 | 修正 |
| API Route Modules | 38 | 39 | +1 (swarm/) |
| API Route Files | 56 | 137 | 精確計算 |
| API Registered Routers | - | 41 | 首次統計 |
| API Endpoints | 526 | ~534 | +8 |
| Frontend .tsx/.ts | 130+ | ~180 | +50 |
| Frontend Pages | 36 | 39 files (25 routable) | 精確計算 |
| Frontend Components | 80+ | 102+ | +22 |
| Frontend Hooks | 15+ | 20 | +5 |
| Frontend Stores | 2 | 3 | +1 (swarmStore) |
| Frontend Routes | ~20 | 23 | +3 |
| Test Files | ~280 | 305 | +25 |
| MAF Builders | 9+ | 22 builder files | 精確計算 |
| MCP Servers | 5 | 5 | 不變 |
| Checkpoint Backends | 4 | 4 | 不變 |
| Phases Completed | 28 | 29 | +1 |
| Sprints Completed | 99 | 106 | +7 |

---

## 附錄 B: V2→V3 功能編號對照

V3 功能 #1-#59 編號與 V2 完全相同。V3 新增 #60-#65 (Agent Swarm)。

| V3 # | V3 名稱 | 狀態 | 來源 |
|------|---------|------|------|
| 60 | SwarmTracker | ✅ | Phase 29, Sprint 100 |
| 61 | SwarmEventEmitter | ✅ | Phase 29, Sprint 101 |
| 62 | SwarmIntegration | ✅ | Phase 29, Sprint 101 |
| 63 | Swarm API | ✅ | Phase 29, Sprint 100+107 |
| 64 | Swarm Frontend Panel | ✅ | Phase 29, Sprint 102-104 |
| 65 | SwarmTestPage | ✅ | Phase 29, Sprint 105 |

---

## 更新歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 3.0 | 2026-02-09 | 全面重寫：5 Agent 並行深度驗證；擴展至 65 功能 (+6 Swarm)；新增 Agent Swarm 能力類別；所有行數實測；#31 降級 ❌；#49/#50 真實化 (CHANGE-003)；更新技術債 (18 Mock, 6 InMemory, 6.6% stub density)；Integration 模組 15→16；API 模組 38→39 |
| 2.1 | 2026-01-28 | 補回 V1 架構圖示 |
| 2.0 | 2026-01-28 | 全面重寫：擴展至 59 功能；逐一代碼驗證 |
| 1.0 | 2025-12-01 | 初始版本 - 50 功能 |
