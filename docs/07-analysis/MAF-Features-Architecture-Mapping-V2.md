# 智能體編排平台功能架構映射指南

> **文件版本**: 2.1
> **最後更新**: 2026-01-28
> **定位**: Agent Orchestration Platform (智能體編排平台)
> **前置文件**: `MAF-Claude-Hybrid-Architecture-V2.md` (架構總覽)
> **狀態**: Phase 28 已完成 (99 Sprints, 2189 Story Points)

---

## 實現狀態總覽

> **重要說明**: 本文件是 V1 (`MAF-Features-Architecture-Mapping.md`, 50 功能) 的全面更新。
> V2 擴展至 **59 個功能**，基於 2026-01-28 的代碼庫逐一驗證。
> 功能編號 #1-#59 為 V2 重新編排，不沿用 V1 編號。

### 59 功能驗證結果

| 狀態 | 數量 | 比例 | 說明 |
|------|------|------|------|
| ✅ 完整實現 | 52 | 88.1% | 代碼庫中有完整實現與對應檔案 |
| ⚠️ 部分實現 | 4 | 6.8% | 有相關代碼但不完整或分散 |
| ❌ 未找到 / 最低限度 | 3 | 5.1% | 缺乏獨立實現或未找到 |
| | **59** | **94.9% 至少部分** | |

### 按類別統計

| 類別 | 功能數 | ✅ | ⚠️ | ❌ | 實現率 |
|------|--------|-----|-----|-----|--------|
| Agent 編排能力 | 12 | 12 | 0 | 0 | 100% |
| 人機協作能力 | 7 | 7 | 0 | 0 | 100% |
| 狀態與記憶能力 | 5 | 5 | 0 | 0 | 100% |
| 前端介面能力 | 8 | 6 | 2 | 0 | 75% 完整 |
| 連接與整合能力 | 11 | 8 | 2 | 1 | 73% 完整 |
| 智能決策能力 | 10 | 10 | 0 | 0 | 100% |
| 可觀測性能力 | 6 | 6 | 0 | 0 | 100% |

### Phase 7-11 替代說明

| 原計劃功能 | 替代實現 | 狀態 |
|-----------|---------|------|
| #7 LLM 服務整合 | ClaudeSDKClient (`claude_sdk/client.py`) | ✅ 已覆蓋 |
| #8 Code Interpreter | CodeInterpreterAdapter (`builders/code_interpreter.py`) | ✅ 已覆蓋 |
| #9 MCP Architecture | Claude MCP Integration (`claude_sdk/mcp/`) | ✅ 已覆蓋 |
| #10 Session Mode | Claude Session API | ✅ 已覆蓋 |
| #11 Agent-Session | HybridEventBridge | ✅ 已覆蓋 |

---

## 執行摘要

IPA Platform 是一個**智能體編排平台 (Agent Orchestration Platform)**，透過 MAF + Claude Agent SDK 混合架構，協調智能體集群處理需要判斷力、專業知識與人機互動的複雜任務。

**59 個功能**構成平台的六大能力領域：

1. **Agent 編排** (12 功能) --- 12 種編排模式，從 Sequential 到 Magentic，全部基於 MAF Builder
2. **人機協作** (7 功能) --- 完整 HITL 生命週期：檢查點 → 審批 → 通知 → 前端介面
3. **狀態與記憶** (5 功能) --- Redis/Postgres 檢查點 + 對話記憶 + mem0 長期記憶
4. **前端介面** (8 功能) --- 36 頁面 + Unified Chat + DevUI + Dashboard
5. **連接與整合** (11 功能) --- InputGateway + 企業連接器 + A2A Protocol
6. **智能決策** (10 功能) --- 三層意圖路由 + 自主決策 + Few-shot 學習
7. **可觀測性** (6 功能) --- 審計 + 巡檢 + 指標 + 關聯分析

與 n8n/Power Automate 的關係：**互補而非競爭**。n8n 處理確定性工作流，IPA Platform 處理需要 AI 判斷力的不確定性任務。

---

## 1. 架構層級與功能映射總覽

### 1.1 架構層級定義 (11 層模型)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    完整架構層級 (Phase 28, V2 - 11 層模型)                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Layer 1: 前端展示層 (Frontend Layer)                                               │
│  ════════════════════════════════════                                                │
│  • React 18 + TypeScript + Vite (port 3005)                                         │
│  • Unified Chat UI (25+ components)                                                 │
│  • AG-UI Components (chat, hitl, advanced)                                          │
│  • DevUI 開發者工具 • Dashboard • Approval Page                                    │
│                                                                                      │
│  Layer 2: API 路由層 (API Layer)                                                     │
│  ═══════════════════════════════                                                     │
│  • 38 API Route Modules, 526 Endpoints                                              │
│  • FastAPI + Uvicorn (port 8000)                                                    │
│                                                                                      │
│  Layer 3: AG-UI Protocol 層                                                          │
│  ═════════════════════════                                                           │
│  • SSE Bridge (Server-Sent Events)                                                  │
│  • HITL 審批事件 + 思考過程串流                                                     │
│  • SharedState 前後端同步                                                            │
│                                                                                      │
│  Layer 4: Phase 28 編排入口層 (Orchestration Entry Layer)                             │
│  ════════════════════════════════════════════════════════                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐        │
│  │                         InputGateway                                     │        │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐  │        │
│  │  │ServiceNowHdlr│  │PrometheusHdlr │  │UserInputHdlr │  │WebhookHdlr│  │        │
│  │  └──────────────┘  └───────────────┘  └──────────────┘  └───────────┘  │        │
│  └─────────────────────────────────────────────────────────────────────────┘        │
│  ┌─────────────────────────────────────────────────────────────────────────┐        │
│  │            BusinessIntentRouter (三層瀑布式路由)                         │        │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │        │
│  │  │ PatternMatcher │→→│ SemanticRouter │→→│ LLMClassifier  │             │        │
│  │  │  (< 10ms)      │  │  (< 100ms)     │  │  (< 2000ms)    │             │        │
│  │  └────────────────┘  └────────────────┘  └────────────────┘             │        │
│  └─────────────────────────────────────────────────────────────────────────┘        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐                     │
│  │GuidedDialogEngine│  │   RiskAssessor   │  │ HITLController │                     │
│  │   (引導式對話)    │  │   (風險評估)     │  │  (人機協作)    │                     │
│  └──────────────────┘  └──────────────────┘  └────────────────┘                     │
│                                                                                      │
│  Layer 5: 混合編排層 (Hybrid Orchestration Layer)                                    │
│  ════════════════════════════════════════════════                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐        │
│  │  HybridOrchestratorV2                                                    │        │
│  │  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐      │        │
│  │  │FrameworkSelector│  │ContextBridge   │  │ContextSynchronizer   │      │        │
│  │  │ (MAF vs Claude) │  │ (MAF↔SDK 橋接) │  │ (上下文同步)         │      │        │
│  │  └─────────────────┘  └────────────────┘  └──────────────────────┘      │        │
│  └─────────────────────────────────────────────────────────────────────────┘        │
│                                                                                      │
│  Layer 6: MAF Builder 層 (Agent Framework Layer)                                     │
│  ═══════════════════════════════════════════════                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐        │
│  │  9+ Official MAF Builders (from agent_framework import ...)              │        │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │        │
│  │  │ Sequential │ │ Concurrent │ │ GroupChat  │ │  Handoff   │           │        │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │        │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │        │
│  │  │  Nested    │ │  Planning  │ │  Magentic  │ │  Voting    │           │        │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │        │
│  └─────────────────────────────────────────────────────────────────────────┘        │
│                                                                                      │
│  Layer 7: Claude SDK 執行層 (Execution Layer)                                        │
│  ════════════════════════════════════════════                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐        │
│  │  Claude Agent SDK Runtime                                                │        │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │        │
│  │  │ Analyzer │→│ Planner  │→│ Executor │→│ Verifier │→│ Hooks    │     │        │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │        │
│  │  • Agentic Loop (自主迭代) • Extended Thinking • Retry + Fallback      │        │
│  └─────────────────────────────────────────────────────────────────────────┘        │
│                                                                                      │
│  Layer 8: MCP 工具層 (Tool Layer)                                                    │
│  ════════════════════════════════                                                    │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐               │
│  │  Azure   │ │  Shell   │ │ Filesystem │ │   SSH    │ │   LDAP   │               │
│  │ (5 mods) │ │ (5 mods) │ │  (5 mods)  │ │ (5 mods) │ │ (5 mods) │               │
│  └──────────┘ └──────────┘ └────────────┘ └──────────┘ └──────────┘               │
│  • Security Module: 28 permission patterns, 16 audit patterns, RBAC               │
│                                                                                      │
│  Layer 9: 支援整合層 (Supporting Integrations)                                       │
│  ═════════════════════════════════════════════                                       │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐ ┌───────┐ ┌──────────┐          │
│  │ Memory │ │ Patrol │ │ Learning │ │Correlation│ │ Audit │ │   A2A    │          │
│  │ (mem0) │ │(5 chks)│ │(few-shot)│ │ (analyzer)│ │(trail)│ │(protocol)│          │
│  └────────┘ └────────┘ └──────────┘ └───────────┘ └───────┘ └──────────┘          │
│                                                                                      │
│  Layer 10: 業務邏輯層 (Domain Layer)                                                  │
│  ══════════════════════════════════                                                  │
│  • 20 Domain Modules (114 files, ~39,941 LOC)                                       │
│  • Orchestration, Agents, Workflows, Sessions, Executions, Templates...             │
│                                                                                      │
│  Layer 11: 基礎設施層 (Infrastructure Layer)                                         │
│  ════════════════════════════════════════════                                        │
│  ┌────────────┐  ┌──────────┐  ┌──────────────────────────────┐                     │
│  │ PostgreSQL │  │  Redis   │  │ RabbitMQ (⚠️ 空殼，待實現)   │                     │
│  │  16+       │  │  7+      │  │                               │                     │
│  └────────────┘  └──────────┘  └──────────────────────────────┘                     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| 層級 | 名稱 | 說明 | 檔案規模 |
|------|------|------|----------|
| **Layer 1** | Frontend | React 18 + TypeScript + Vite | 130+ .tsx, 36 pages |
| **Layer 2** | API Layer | 38 API route modules, 526 endpoints | 56 route files |
| **Layer 3** | AG-UI Protocol | SSE Bridge + HITL UI + 共享狀態 | 23 files, ~7,984 LOC |
| **Layer 4** | Phase 28 Orchestration | 三層意圖路由 + 引導對話 + 風險評估 + HITL | 40 files, ~13,795 LOC |
| **Layer 5** | Hybrid Layer | HybridOrchestratorV2 + 框架切換 + 上下文橋接 | 60 files, ~17,872 LOC |
| **Layer 6** | MAF Builder Layer | 9+ Builders，MAF 官方 API 整合 | 23 files, ~20,011 LOC |
| **Layer 7** | Claude SDK Layer | 自主執行管線 + Hook 系統 | 47 files, ~12,267 LOC |
| **Layer 8** | MCP Layer | 5 個 MCP Server + 安全模組 | 43 files, ~10,528 LOC |
| **Layer 9** | Supporting Integrations | 記憶、巡檢、學習、關聯分析、審計 | 36 files, ~8,640 LOC |
| **Layer 10** | Domain Layer | 20 domain modules 業務邏輯 | 114 files, ~39,941 LOC |
| **Layer 11** | Infrastructure | PostgreSQL + Redis + RabbitMQ (planned) | 23 files, ~3,101 LOC |

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

### 1.3 功能實現狀態速查表

| # | 功能名稱 | 狀態 | 架構層級 | 主要實現位置 |
|---|---------|------|----------|-------------|
| 1 | Sequential 編排 | ✅ | L6 | `builders/workflow_executor.py:388` |
| 2 | Concurrent 並行 | ✅ | L6 | `builders/concurrent.py:721` |
| 3 | GroupChat 群組 | ✅ | L6 | `builders/groupchat.py:992` |
| 4 | Handoff 交接 | ✅ | L6 | `builders/handoff.py:208` |
| 5 | Nested Workflows | ✅ | L6 | `builders/nested_workflow.py:565` |
| 6 | Sub-workflow | ✅ | L10 | `domain/orchestration/nested/sub_executor.py` |
| 7 | Recursive Patterns | ✅ | L10 | `recursive_handler.py` + `workflow_manager.py:655` |
| 8 | Dynamic Planning | ✅ | L6 | `builders/planning.py:186` + DynamicPlanner |
| 9 | Magentic 推理鏈 | ✅ | L6 | `builders/magentic.py:957` |
| 10 | Voting 投票 | ✅ | L6 | `builders/groupchat_voting.py` |
| 11 | Capability Matcher | ✅ | L6 | `builders/handoff_capability.py:341` |
| 12 | Termination 條件 | ✅ | L6 | `groupchat.py` + `handoff.py` TerminationType |
| 13 | HITL Checkpoints | ✅ | L3 | `ag_ui/features/human_in_loop.py` |
| 14 | HITL Manager | ✅ | L6 | `builders/handoff_hitl.py:326` |
| 15 | HITLController | ✅ | L4 | `orchestration/hitl/controller.py:237` |
| 16 | Approval Handler | ✅ | L4 | `orchestration/hitl/approval_handler.py:305` |
| 17 | Teams Notification | ✅ | L4 | `orchestration/hitl/notification.py` |
| 18 | HITL 功能擴展 | ✅ | L3-L6 | Full HITL stack across 4 modules |
| 19 | Pending Approval Page | ✅ | L1 | `frontend/src/pages/approvals/` |
| 20 | Redis/Postgres Checkpoint | ✅ | L5 | `hybrid/checkpoint/backends/` (redis.py, postgres.py) |
| 21 | Conversation Memory | ✅ | L5 | `session_state.py` + `redis_store.py` + `postgres_store.py` |
| 22 | Context Transfer | ✅ | L5 | `context/bridge.py` + `sync/synchronizer.py` |
| 23 | Multi-turn Dialog | ✅ | L10 | `domain/orchestration/multiturn/` (3 files) |
| 24 | mem0 長期記憶 | ✅ | L9 | `memory/mem0_client.py` + `unified_memory.py` |
| 25 | Modern Web UI | ✅ | L1 | 36 pages across `frontend/src/pages/` |
| 26 | DevUI 開發者介面 | ✅ | L1 | 7 DevUI files in `frontend/src/` |
| 27 | Dashboard 儀表板 | ✅ | L1 | `DashboardPage` + components |
| 28 | Stats Cards | ✅ | L1 | `StatsCards.tsx` |
| 29 | Approval Page | ✅ | L1 | `ApprovalsPage.tsx` |
| 30 | Performance Page | ✅ | L1 | `PerformancePage.tsx` |
| 31 | WorkflowViz 視覺化 | ⚠️ | L1 | ReactFlow references 但無獨立視覺化元件 |
| 32 | Notification System | ⚠️ | L1 | 僅 Header 中的 toast，無專用通知系統 |
| 33 | Cross-system Connectors | ✅ | L8 | `dynamics365`, `servicenow`, `sharepoint` connectors |
| 34 | Enhanced Gateway | ⚠️ | L4+L8 | 分散於 client + orchestrator，無獨立閘道 |
| 35 | n8n Trigger | ✅ | L4 | `triggers/webhook.py` |
| 36 | InputGateway | ✅ | L4 | `input_gateway/gateway.py` |
| 37 | ServiceNow Handler | ✅ | L4 | InputGateway ServiceNow handler |
| 38 | Prometheus Handler | ✅ | L4 | InputGateway Prometheus handler |
| 39 | UserInput Handler | ✅ | L4 | InputGateway UserInput handler |
| 40 | A2A Protocol | ✅ | L9 | `a2a/` (protocol.py, router.py, discovery.py) |
| 41 | Collaboration Protocol | ⚠️ | L9 | 由 A2A 基礎功能覆蓋 |
| 42 | Cross-scenario 協作 | ❌ | - | 未找到獨立實現 |
| 43 | Handoff Service | ✅ | L6 | `builders/handoff_service.py:222` |
| 44 | Intelligent Routing | ✅ | L5 | `hybrid/intent/` (FrameworkSelector) |
| 45 | Autonomous Decision | ✅ | L7 | `autonomous/` (analyzer, planner, executor, verifier) |
| 46 | Trial-and-Error | ✅ | L7 | `retry.py` + `fallback.py` + `trial_error.py` |
| 47 | Few-shot Learning | ✅ | L9 | `learning/few_shot.py` |
| 48 | PatternMatcher | ✅ | L4 | `intent_router/pattern_matcher/matcher.py` |
| 49 | SemanticRouter | ✅ | L4 | `intent_router/semantic_router/router.py` |
| 50 | LLMClassifier | ✅ | L4 | `intent_router/llm_classifier/classifier.py` |
| 51 | GuidedDialogEngine | ✅ | L4 | `orchestration/guided_dialog/engine.py` |
| 52 | RiskAssessor | ✅ | L4 | `orchestration/risk_assessor/assessor.py` |
| 53 | CompletenessChecker | ✅ | L4 | `intent_router/` completeness module |
| 54 | Audit Trail | ✅ | L9 | `audit/` + `domain/audit/` |
| 55 | Redis Cache | ✅ | L9+L11 | `llm_cache.py` + redis backends |
| 56 | OrchestrationMetrics | ✅ | L4 | `orchestration/metrics.py:298` |
| 57 | Correlation Analysis | ✅ | L9 | `correlation/` (analyzer.py, graph.py) |
| 58 | Patrol 巡檢 | ✅ | L9 | `patrol/` (agent, scheduler, 5 checks) |
| 59 | Agent Templates | ✅ | L10+L1 | `domain/templates/` + frontend templates |

---

## 2. 功能詳細映射

> **路徑約定**: 以下所有路徑均相對於 `backend/src/integrations/`，除非另有標註。
> Frontend 路徑相對於 `frontend/src/`。
> 行號 (如 `:388`) 為驗證時的近似位置，可能因後續修改而微幅偏移。

### 2.1 Agent 編排能力 (12 功能)

本平台的核心差異化能力。12 種編排模式全部基於 MAF Builder Layer，透過 `from agent_framework import` 使用官方 API。這是平台與 n8n 等工具的**根本性差異** --- n8n 的「節點」是確定性函式，而本平台的「Agent」具備自主推理能力。

| # | 功能 | 狀態 | 層級 | 實現檔案 | 能力說明 |
|---|------|------|------|----------|----------|
| 1 | **Sequential** | ✅ | L6 | `agent_framework/builders/workflow_executor.py:388` | 順序式 Agent 管線，支援檢查點 |
| 2 | **Concurrent** | ✅ | L6 | `agent_framework/builders/concurrent.py:721` | 並行 Agent 執行 + 結果聚合 |
| 3 | **GroupChat** | ✅ | L6 | `agent_framework/builders/groupchat.py:992` | 多 Agent 群組討論 + Speaker Selection |
| 4 | **Handoff** | ✅ | L6 | `agent_framework/builders/handoff.py:208` | Agent 間任務交接 + Policy + Context |
| 5 | **Nested Workflows** | ✅ | L6 | `agent_framework/builders/nested_workflow.py:565` | 巢狀工作流，子流程嵌入 |
| 6 | **Sub-workflow** | ✅ | L10 | `domain/orchestration/nested/sub_executor.py` | 子工作流獨立執行器 |
| 7 | **Recursive** | ✅ | L10 | `domain/orchestration/recursive_handler.py` + `workflow_manager.py:655` | 遞迴模式處理 |
| 8 | **Dynamic Planning** | ✅ | L6 | `agent_framework/builders/planning.py:186` + DynamicPlanner | 動態任務規劃 |
| 9 | **Magentic** | ✅ | L6 | `agent_framework/builders/magentic.py:957` | 推理鏈 Agent 模式 |
| 10 | **Voting** | ✅ | L6 | `agent_framework/builders/groupchat_voting.py` | 多數決 / 加權投票 / 一票否決 |
| 11 | **Capability Matcher** | ✅ | L6 | `agent_framework/builders/handoff_capability.py:341` | Agent 能力匹配與路由 |
| 12 | **Termination** | ✅ | L6 | `groupchat.py` + `handoff.py` TerminationType enum | 終止條件定義 (max_rounds, consensus, custom) |

**支援檔案** (均位於 `agent_framework/builders/`):
- `handoff_hitl.py` - HITL 整合的 Handoff
- `handoff_policy.py` - Handoff 策略管理 (round-robin, priority, capability-based)
- `handoff_context.py` - 上下文傳遞
- `handoff_service.py` - Handoff 服務層
- `groupchat_orchestrator.py` - GroupChat 編排
- `edge_routing.py` - 邊緣路由
- `*_migration.py` (4 files) - 遷移適配器

**驗證**: `cd backend && python scripts/verify_official_api_usage.py` -- All 5 checks must pass

**核心編排模式流程圖**:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  #1 Sequential 編排                                                                  │
│                                                                                      │
│  SequentialBuilder ──▶ Diagnostic ──▶ Remediation ──▶ Verification                  │
│                        Worker         Worker          Worker                         │
│                          │              │               │                            │
│                      [Checkpoint]   [Checkpoint]    [Checkpoint]                     │
│                                                                                      │
│  代碼: SequentialBuilder().add_step(w1).add_step(w2).with_checkpointing().build()   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  #2 Concurrent 並行執行                                                              │
│                                                                                      │
│  ConcurrentBuilder                                                                   │
│       │                                                                              │
│       ├──▶ Worker A (Log Analysis)      ──┐                                         │
│       ├──▶ Worker B (Metric Check)      ──┼──▶ Aggregator ──▶ Result               │
│       └──▶ Worker C (Config Validation) ──┘                                         │
│                                                                                      │
│  雙層並行：MAF 層調度 + Claude 子 Agent 層再並行                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  #3 GroupChat 群組討論                                                                │
│                                                                                      │
│              ┌─────────────────────────┐                                             │
│              │   GroupChat Manager     │                                             │
│              │   (Speaker Selection)   │                                             │
│              └───────────┬─────────────┘                                             │
│                          │                                                           │
│       ┌──────────────────┼──────────────────┐                                        │
│       ▼                  ▼                  ▼                                        │
│  ┌─────────┐       ┌─────────┐       ┌─────────┐                                    │
│  │Researcher│◀────▶│  Coder  │◀────▶│ Reviewer │                                    │
│  │ Worker  │       │ Worker  │       │ Worker  │                                    │
│  └─────────┘       └─────────┘       └─────────┘                                    │
│                          │                                                           │
│                    [Voting: 多數決 / 加權 / 一票否決]                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  #4 Handoff 交接                                                                     │
│                                                                                      │
│                      ┌─────────────┐                                                 │
│                      │   Triage    │                                                 │
│                      │   Worker    │                                                 │
│                      └──────┬──────┘                                                 │
│               ┌─────────────┼─────────────┐                                          │
│               ▼             ▼             ▼                                          │
│        ┌──────────┐  ┌──────────┐  ┌──────────┐                                      │
│        │ Network  │  │ Database │  │ Security │                                      │
│        │Specialist│  │Specialist│  │Specialist│                                      │
│        └────┬─────┘  └────┬─────┘  └────┬─────┘                                      │
│             └─────────────┴─────────────┘                                            │
│                           │                                                          │
│                    Return to Triage                                                   │
│  Context Transfer: 自動傳遞診斷結果、嘗試方案、相關日誌                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  #8 Dynamic Planning + #9 Magentic 推理鏈                                            │
│                                                                                      │
│   MAF 編排層 (高層規劃)                Claude Worker (執行層規劃)                    │
│   ═════════════════════                ════════════════════════                      │
│                                                                                      │
│   Planning Adapter                      Claude Agent SDK                             │
│   • 決定使用哪種 Workflow               • Extended Thinking 規劃執行步驟            │
│   • 決定分派給哪些 Worker               • 自主決定工具調用順序                       │
│   • 風險驅動的決策                      • 動態調整策略（試錯）                       │
│                                                                                      │
│         ┌─────────────┐                    ┌─────────────┐                           │
│         │   MAF       │                    │   Claude    │                           │
│         │  Magentic   │ ──────────────────▶│  Extended   │                           │
│         │  Pattern    │   分派高層任務      │  Thinking   │                           │
│         └─────────────┘                    └─────────────┘                           │
│               │                                  │                                   │
│               ▼                                  ▼                                   │
│         監控進度                            自主執行                                 │
│         調整計劃                            反饋結果                                 │
│                                                                                      │
│  雙層規劃：戰略層 (MAF) + 戰術層 (Claude)                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**編排模式選擇指引**:

| 場景 | 推薦模式 | 原因 |
|------|----------|------|
| 線性流程 (診斷→修復→驗證) | Sequential (#1) | 步驟有序、有依賴 |
| 多系統同時探查 | Concurrent (#2) | 獨立任務並行加速 |
| 多專家協作分析 | GroupChat (#3) | 需要討論和共識 |
| 任務升級/轉交 | Handoff (#4) | 能力不匹配時轉交 |
| 複雜任務分解 | Nested (#5) + Planning (#8) | 大任務拆分為子任務 |
| 推理密集型 | Magentic (#9) | 需要深度推理鏈 |

### 2.2 人機協作能力 (7 功能)

完整的 HITL (Human-in-the-Loop) 生命週期，橫跨 Backend 4 個模組 + Frontend 審批介面。

| # | 功能 | 狀態 | 層級 | 實現檔案 | 能力說明 |
|---|------|------|------|----------|----------|
| 13 | **HITL Checkpoints** | ✅ | L3 | `ag_ui/features/human_in_loop.py` | AG-UI Protocol 審批事件定義 |
| 14 | **HITL Manager** | ✅ | L6 | `builders/handoff_hitl.py:326` | MAF Handoff 整合 HITL |
| 15 | **HITLController** | ✅ | L4 | `orchestration/hitl/controller.py:237` | 中央 HITL 協調控制器 |
| 16 | **Approval Handler** | ✅ | L4 | `orchestration/hitl/approval_handler.py:305` | 同意/拒絕/超時處理 |
| 17 | **Teams Notification** | ✅ | L4 | `orchestration/hitl/notification.py` | TeamsCardBuilder + Webhook |
| 18 | **HITL 功能擴展** | ✅ | L3-L6 | 跨 4 模組完整 stack | Claude Hooks + AG-UI + Frontend |
| 19 | **Pending Approval Page** | ✅ | L1 | `frontend/src/pages/approvals/` | 待審批管理頁面 |

**HITL 完整生命週期**:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  HITL (Human-in-the-Loop) 生命週期流程                                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐                      │
│  │ RiskAssessor │────▶│HITLController│────▶│ ApprovalHandler  │                      │
│  │  風險 > 閾值  │     │  #15 (L4)    │     │   #16 (L4)       │                      │
│  └──────────────┘     └──────────────┘     └────────┬─────────┘                      │
│                                                      │                               │
│                              ┌───────────────────────┼───────────────────────┐        │
│                              ▼                       ▼                       ▼        │
│                     ┌──────────────┐       ┌──────────────┐       ┌──────────────┐   │
│                     │Teams 通知    │       │AG-UI SSE     │       │ 超時升級     │   │
│                     │Adaptive Card │       │審批事件       │       │ (Escalation) │   │
│                     │  #17 (L4)    │       │  #13 (L3)    │       │              │   │
│                     └──────┬───────┘       └──────┬───────┘       └──────────────┘   │
│                            │                       │                                  │
│                            ▼                       ▼                                  │
│                     ┌──────────────┐       ┌──────────────┐                           │
│                     │ Teams 審批   │       │ Web UI 審批  │                           │
│                     │              │       │  #19 (L1)   │                           │
│                     └──────┬───────┘       └──────┬───────┘                           │
│                            │                       │                                  │
│                            └───────────┬───────────┘                                  │
│                                        ▼                                              │
│                              ┌──────────────────┐                                     │
│                              │ ✅ Approve       │                                     │
│                              │ ❌ Reject        │                                     │
│                              │ ⏰ Timeout       │                                     │
│                              └────────┬─────────┘                                     │
│                                       ▼                                               │
│                              Resume / Reject / Escalate Execution                     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 狀態與記憶能力 (5 功能)

多層次狀態管理：即時狀態 (Redis)、持久化 (Postgres)、長期記憶 (mem0)。

| # | 功能 | 狀態 | 層級 | 實現檔案 | 能力說明 |
|---|------|------|------|----------|----------|
| 20 | **Redis/Postgres Checkpoint** | ✅ | L5 | `hybrid/checkpoint/backends/redis.py`, `postgres.py` | 4 種後端 (memory/redis/postgres/filesystem) |
| 21 | **Conversation Memory** | ✅ | L5 | `hybrid/session_state.py` + `redis_store.py` + `postgres_store.py` | 對話狀態持久化 |
| 22 | **Context Transfer** | ✅ | L5 | `hybrid/context/bridge.py` + `sync/synchronizer.py` | MAF ↔ Claude SDK 上下文橋接 |
| 23 | **Multi-turn Dialog** | ✅ | L10 | `domain/orchestration/multiturn/` (3 files) | 多輪對話管理 |
| 24 | **mem0 長期記憶** | ✅ | L9 | `memory/mem0_client.py` + `unified_memory.py` | 統一記憶 + 向量嵌入 |

**Checkpoint 4 後端設計理由**:

| 後端 | 適用場景 | 特性 |
|------|----------|------|
| Memory | 開發/測試 | 快速，無持久化 |
| Redis | 生產推薦 | 快速，TTL，適合熱數據 |
| PostgreSQL | 合規要求 | 持久化，可查詢，審計 |
| Filesystem | 備用方案 | 簡單，無依賴 |

**多層次狀態管理架構**:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  狀態與記憶多層架構                                                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─── 即時層 (Hot) ────────────────────────────────────────────────────────────┐      │
│  │  Redis Cache (#55)                                                          │      │
│  │  • 對話狀態 (session_state.py)                                              │      │
│  │  • LLM 回應快取 (llm_cache.py)                                              │      │
│  │  • Checkpoint 熱數據                                                        │      │
│  │  TTL: 分鐘~小時級                                                           │      │
│  └─────────────────────────────────────────────────────────────────────────────┘      │
│                                                                                      │
│  ┌─── 持久層 (Warm) ──────────────────────────────────────────────────────────┐      │
│  │  PostgreSQL (#20)                                                           │      │
│  │  • Checkpoint 持久化                                                        │      │
│  │  • 對話歷史 (postgres_store.py)                                              │      │
│  │  • 審計記錄                                                                 │      │
│  │  保留: 天~月級                                                               │      │
│  └─────────────────────────────────────────────────────────────────────────────┘      │
│                                                                                      │
│  ┌─── 長期層 (Cold) ──────────────────────────────────────────────────────────┐      │
│  │  mem0 (#24)                                                                 │      │
│  │  • 統一記憶 (unified_memory.py)                                              │      │
│  │  • 向量嵌入 (Qdrant)                                                        │      │
│  │  • 跨 Session 知識累積                                                      │      │
│  │  保留: 永久                                                                  │      │
│  └─────────────────────────────────────────────────────────────────────────────┘      │
│                                                                                      │
│  Context Bridge (#22): MAF State ⇄ Claude SDK Context 雙向橋接                       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**已知問題**: `ContextSynchronizer` (位於 `hybrid/context/`) 使用記憶體 dict 存儲，無 `asyncio.Lock`，在多 Worker 場景下存在競爭條件風險 (嚴重度: 高)。

### 2.4 前端介面能力 (8 功能)

React 18 + TypeScript + Vite 前端，36 頁面、80+ 元件、15+ Custom Hooks。

| # | 功能 | 狀態 | 層級 | 實現檔案 | 能力說明 |
|---|------|------|------|----------|----------|
| 25 | **Modern Web UI** | ✅ | L1 | 36 pages in `frontend/src/pages/` | 完整 SPA 應用 |
| 26 | **DevUI** | ✅ | L1 | 7 DevUI files | 開發者工具介面 |
| 27 | **Dashboard** | ✅ | L1 | `DashboardPage` + components | 監控儀表板 |
| 28 | **Stats Cards** | ✅ | L1 | `StatsCards.tsx` | 統計數據卡片 |
| 29 | **Approval Page** | ✅ | L1 | `ApprovalsPage.tsx` | 待審批管理 |
| 30 | **Performance Page** | ✅ | L1 | `PerformancePage.tsx` | 效能監控 |
| 31 | **WorkflowViz** | ⚠️ | L1 | ReactFlow references (無獨立視覺化) | 有 ReactFlow 依賴引用但無完整工作流視覺化元件 |
| 32 | **Notification System** | ⚠️ | L1 | Header toast only | 僅 Header 內的 toast 通知，無獨立通知中心 |

**說明**: #31 和 #32 是平台已知的前端缺口。ReactFlow 已在依賴中但未建構完整的工作流視覺化編輯器；通知系統僅有基礎 toast 實現。

**Frontend 技術棧**:
- **框架**: React 18 + TypeScript + Vite (port 3005)
- **UI 庫**: Shadcn UI (`components/ui/`)
- **狀態管理**: Zustand (`store/`, `stores/`)
- **API 通訊**: Fetch API (非 Axios)
- **聊天核心**: Unified Chat UI (25+ components in `components/unified-chat/`)
- **Agentic UI**: AG-UI components (`components/ag-ui/` - chat, hitl, advanced)
- **Custom Hooks**: 15+ hooks (`hooks/`)

### 2.5 連接與整合能力 (11 功能)

多渠道輸入 + 企業連接器 + Agent-to-Agent 互操作。本類別涵蓋三個子領域：

- **輸入接入** (#35-39): InputGateway 統一多渠道事件接入
- **企業連接** (#33-34, #43): MCP Server 包裝的企業系統連接器
- **互操作** (#40-42): Agent-to-Agent 通訊協議

| # | 功能 | 狀態 | 層級 | 實現檔案 | 能力說明 |
|---|------|------|------|----------|----------|
| 33 | **Cross-system Connectors** | ✅ | L8 | `dynamics365`, `servicenow`, `sharepoint` connectors | 企業系統連接器 (MCP 包裝) |
| 34 | **Enhanced Gateway** | ⚠️ | L4+L8 | 分散於 client + orchestrator | 無獨立統一閘道，功能分散 |
| 35 | **n8n Trigger** | ✅ | L4 | `orchestration/triggers/webhook.py` | Webhook 觸發整合 |
| 36 | **InputGateway** | ✅ | L4 | `orchestration/input_gateway/gateway.py` | 統一輸入閘道 (8 files, ~2,100 LOC) |
| 37 | **ServiceNow Handler** | ✅ | L4 | InputGateway ServiceNow handler | ServiceNow 事件接入 |
| 38 | **Prometheus Handler** | ✅ | L4 | InputGateway Prometheus handler | Prometheus 告警接入 |
| 39 | **UserInput Handler** | ✅ | L4 | InputGateway UserInput handler | 使用者直接輸入接入 |
| 40 | **A2A Protocol** | ✅ | L9 | `a2a/protocol.py`, `router.py`, `discovery.py` | Agent-to-Agent 通訊 |
| 41 | **Collaboration Protocol** | ⚠️ | L9 | 由 A2A 基礎功能覆蓋 | 無獨立協作協議，A2A 提供基礎 |
| 42 | **Cross-scenario 協作** | ❌ | - | **未找到** | 跨場景 (如 CS↔IT) 專用協作機制未實現 |
| 43 | **Handoff Service** | ✅ | L6 | `agent_framework/builders/handoff_service.py:222` | Handoff 服務層抽象 |

**MCP Layer 詳情** (Layer 8, 43 files, ~10,528 LOC):

| MCP Server | 檔案數 | 功能模組 | 用途 |
|------------|--------|----------|------|
| Azure | 9 | VM, Resource, Monitor, Network, Storage | Azure 雲端資源管理 |
| Shell | 5 | 命令執行 | 本地系統操作 |
| Filesystem | 5 | 檔案操作 | 檔案讀寫 |
| SSH | 5 | 遠端連線 | 遠端系統管理 |
| LDAP | 5 | 目錄查詢 | 使用者/群組管理 |

安全模組: `mcp/security/` (3 files) --- 28 permission patterns, 16 audit patterns, RBAC integration

**InputGateway 資料流**:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  InputGateway 多渠道接入與路由流程                                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐               │
│  │ServiceNow    │  │Prometheus     │  │User Message  │  │n8n Webhook│               │
│  │Incident      │  │Alert          │  │(Chat UI)     │  │Trigger    │               │
│  └──────┬───────┘  └──────┬────────┘  └──────┬───────┘  └─────┬─────┘               │
│         │                 │                   │                │                      │
│         └─────────────────┴───────┬───────────┴────────────────┘                      │
│                                   ▼                                                  │
│                    ┌──────────────────────────┐                                       │
│                    │      InputGateway        │                                       │
│                    │   (來源標準化 + 驗證)     │                                       │
│                    └────────────┬─────────────┘                                       │
│                                ▼                                                     │
│                    ┌──────────────────────────┐                                       │
│                    │ UnifiedRequestEnvelope   │                                       │
│                    │ {source, payload, meta}  │                                       │
│                    └────────────┬─────────────┘                                       │
│                                ▼                                                     │
│                    ┌──────────────────────────┐                                       │
│                    │  BusinessIntentRouter    │                                       │
│                    │  (三層瀑布式路由)         │                                       │
│                    └────────────┬─────────────┘                                       │
│                                ▼                                                     │
│                    ┌──────────────────────────┐                                       │
│                    │  RoutingDecision         │                                       │
│                    │  {intent, risk, action}  │                                       │
│                    └──────────────────────────┘                                       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.6 智能決策能力 (10 功能)

三層意圖路由 (Phase 28, Sprint 91-99, 235 Story Points) + Claude SDK 自主決策 + Few-shot 學習。這是平台「智能」的核心所在。

| # | 功能 | 狀態 | 層級 | 實現檔案 | 能力說明 |
|---|------|------|------|----------|----------|
| 44 | **Intelligent Routing** | ✅ | L5 | `hybrid/intent/` (FrameworkSelector, 7 files, ~1,600 LOC) | MAF vs Claude SDK 智能選擇 |
| 45 | **Autonomous Decision** | ✅ | L7 | `claude_sdk/autonomous/` (analyzer, planner, executor, verifier) | Claude 自主分析-規劃-執行-驗證管線 |
| 46 | **Trial-and-Error** | ✅ | L7 | `claude_sdk/autonomous/retry.py` + `fallback.py` + `trial_error.py` | 重試 + 降級 + 試錯機制 |
| 47 | **Few-shot Learning** | ✅ | L9 | `learning/few_shot.py` | 案例學習與模式匹配 |
| 48 | **PatternMatcher** | ✅ | L4 | `orchestration/intent_router/pattern_matcher/matcher.py` | 三層路由 Tier 1: 規則匹配 (< 10ms) |
| 49 | **SemanticRouter** | ✅ | L4 | `orchestration/intent_router/semantic_router/router.py` | 三層路由 Tier 2: 向量相似度 (< 100ms) |
| 50 | **LLMClassifier** | ✅ | L4 | `orchestration/intent_router/llm_classifier/classifier.py` | 三層路由 Tier 3: LLM 分類 (< 2000ms) |
| 51 | **GuidedDialogEngine** | ✅ | L4 | `orchestration/guided_dialog/engine.py` (~3,050 LOC total) | 引導式對話收集缺失資訊 |
| 52 | **RiskAssessor** | ✅ | L4 | `orchestration/risk_assessor/assessor.py` (~1,200 LOC total) | 風險等級評估 (LOW/MED/HIGH/CRITICAL) |
| 53 | **CompletenessChecker** | ✅ | L4 | `orchestration/intent_router/` completeness module | 資訊完整度檢查 |

**三層瀑布式路由**:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  BusinessIntentRouter - 三層瀑布式路由 (Phase 28)                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  User Input                                                                          │
│      │                                                                               │
│      ▼                                                                               │
│  ┌────────────────────────┐                                                          │
│  │  Tier 1: PatternMatcher │  < 10ms   │  命中率: ~60%                               │
│  │  規則匹配 + 關鍵詞識別  │           │  regex + keyword patterns                   │
│  └──────────┬─────────────┘                                                          │
│             │ 未命中                                                                 │
│             ▼                                                                        │
│  ┌────────────────────────┐                                                          │
│  │  Tier 2: SemanticRouter │  < 100ms  │  命中率: ~25%                               │
│  │  向量相似度搜索         │           │  embedding similarity                       │
│  └──────────┬─────────────┘                                                          │
│             │ 未命中                                                                 │
│             ▼                                                                        │
│  ┌────────────────────────┐                                                          │
│  │  Tier 3: LLMClassifier  │  < 2000ms │  命中率: ~15%                               │
│  │  Claude Haiku 分類      │           │  LLM-based classification                   │
│  └──────────┬─────────────┘                                                          │
│             │                                                                        │
│             ▼                                                                        │
│  ┌────────────────────────────────────────────────────────┐                           │
│  │  RoutingDecision {intent, completeness, risk_hint}      │                           │
│  └────────────────────────────────────────────────────────┘                           │
│                                                                                      │
│  結果: ~85% 請求不需 LLM 調用，平均延遲 ~50ms，API 成本降低 ~85%                    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**自主決策管線**:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  Claude SDK Autonomous Decision Pipeline (#45-46)                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Task Input                                                                          │
│      │                                                                               │
│      ▼                                                                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐                        │
│  │ Analyzer │───▶│ Planner  │───▶│ Executor │───▶│ Verifier │                        │
│  │ 分析任務  │    │ 規劃步驟  │    │ Agentic  │    │ 驗證結果  │                        │
│  │ 需求     │    │          │    │ Loop 執行 │    │          │                        │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘                        │
│                                                       │                              │
│                                              ┌────────┴────────┐                     │
│                                              │     結果?       │                     │
│                                              └────────┬────────┘                     │
│                                         ┌─────────────┼─────────────┐                │
│                                         ▼             ▼             ▼                │
│                                    ┌─────────┐   ┌─────────┐  ┌──────────┐           │
│                                    │ ✅ 成功  │   │  Retry  │  │ Fallback │           │
│                                    │  完成   │   │ 重試策略 │  │ 降級方案 │           │
│                                    └─────────┘   └────┬────┘  └────┬─────┘           │
│                                                       │            │                 │
│                                                       ▼            ▼                 │
│                                                  ┌──────────────────┐                │
│                                                  │ Trial-and-Error  │                │
│                                                  │ 嘗試→驗證→調整→  │                │
│                                                  │ 再嘗試 (max N)   │                │
│                                                  └──────────────────┘                │
│                                                                                      │
│  安全機制: 每次嘗試有審計記錄 • 危險操作需 HITL 審批 • Checkpoint 回滾               │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**FrameworkSelector 決策邏輯** (`hybrid/intent/`):
- 結構化任務 (已知模式) → MAF Builder
- 開放式推理 (需要 Extended Thinking) → Claude SDK
- 混合任務 → MAF 編排 + Claude Worker 執行
- 支援 4 種動態切換觸發: user_trigger, failure_trigger, resource_trigger, complexity_trigger

### 2.7 可觀測性能力 (6 功能)

審計追蹤 + Redis 快取 + 指標系統 + 關聯分析 + 巡檢。企業級治理的關鍵支撐。

| # | 功能 | 狀態 | 層級 | 實現檔案 | 能力說明 |
|---|------|------|------|----------|----------|
| 54 | **Audit Trail** | ✅ | L9 | `audit/` (4 files, ~972 LOC) + `domain/audit/` | 決策追蹤與審計報告 |
| 55 | **Redis Cache** | ✅ | L9+L11 | `llm/llm_cache.py` + redis backends | LLM 回應快取 + Redis 存儲 |
| 56 | **OrchestrationMetrics** | ✅ | L4 | `orchestration/metrics.py` (763 LOC) | 路由/對話/風險/HITL 指標 + OTel |
| 57 | **Correlation Analysis** | ✅ | L9 | `correlation/analyzer.py`, `graph.py` (4 files, ~993 LOC) | 事件關聯圖分析 |
| 58 | **Patrol 巡檢** | ✅ | L9 | `patrol/` (11 files, ~2,142 LOC) | 5 種巡檢: Health/Perf/Security/Resource/Config |
| 59 | **Agent Templates** | ✅ | L10+L1 | `domain/templates/` + frontend templates | Agent 範本管理 |

**OrchestrationMetrics 指標體系**:

| 指標類別 | 追蹤內容 |
|----------|----------|
| Routing | 各層命中率 (pattern/semantic/llm)、延遲分布、決策信心度 |
| Dialog | 對話輪次分布、資訊完成率、用戶放棄率 |
| Risk | 風險等級分布 (LOW/MED/HIGH/CRITICAL)、審批通過率 |
| HITL | 審批請求量、等待時間、超時升級率 |
| Execution | 框架選擇分布 (MAF vs Claude)、完成率、執行時間 |

**OTel 整合**: 優先使用 OpenTelemetry (如果可用)，自動降級到 fallback counters (dict-based)，零配置啟動。

**巡檢 5 類型**: Health Check (服務健康)、Performance (效能)、Security (安全合規)、Resource (資源使用率)、Configuration (配置一致性)

---

## 3. 功能整合總覽

### 3.1 功能與架構層級映射矩陣

| 層級 | 功能編號 | 功能數 |
|------|----------|--------|
| **L1** Frontend | #19, #25-32 | 9 |
| **L2** API Layer | (所有功能皆有 API endpoint) | - |
| **L3** AG-UI Protocol | #13, #18 | 2 |
| **L4** Phase 28 Orchestration | #15-17, #35-39, #48-53, #56 | 14 |
| **L5** Hybrid Layer | #20-22, #44 | 4 |
| **L6** MAF Builder | #1-5, #8-12, #14, #43 | 14 |
| **L7** Claude SDK | #45-46 | 2 |
| **L8** MCP Layer | #33 | 1 |
| **L9** Supporting | #24, #40-41, #47, #54-55, #57-58 | 8 |
| **L10** Domain Layer | #6-7, #23, #59 | 4 |
| **L11** Infrastructure | #55 (Redis backend) | 1 |
| 跨層 / 未找到 | #34 (⚠️ 分散), #42 (❌) | 2 |

### 3.2 架構層級功能分布統計

```
L1  Frontend:             █████████  9 功能
L2  API:                  -          (橫切所有功能)
L3  AG-UI:                ██         2 功能
L4  Orchestration:        ██████████████ 14 功能 (Phase 28 智能入口)
L5  Hybrid:               ████       4 功能
L6  MAF Builder:          ██████████████ 14 功能 (最密集 - 編排核心)
L7  Claude SDK:           ██         2 功能
L8  MCP:                  █          1 功能 (工具層，非功能導向)
L9  Supporting:           ████████   8 功能
L10 Domain:               ████       4 功能
L11 Infrastructure:       █          1 功能
```

**觀察**: Layer 6 (MAF Builder) 和 Layer 4 (Phase 28 Orchestration) 各承載 14 個功能，是平台功能最密集的兩層。這反映了「Agent 編排」和「智能路由」作為平台核心能力的設計意圖。

### 3.3 功能缺口分析

| 功能 | 狀態 | 缺口描述 | 影響 | 建議優先級 |
|------|------|----------|------|-----------|
| #31 WorkflowViz | ⚠️ | ReactFlow 依賴存在但無完整視覺化 | 缺少視覺化工作流編輯器 | P2 |
| #32 Notification System | ⚠️ | 僅 Header toast，無通知中心 | 使用者可能錯過重要通知 | P2 |
| #34 Enhanced Gateway | ⚠️ | 閘道功能分散無統一入口 | 架構清晰度降低 | P3 |
| #41 Collaboration Protocol | ⚠️ | 僅有 A2A 基礎覆蓋 | 跨 Agent 協作能力受限 | P3 |
| #42 Cross-scenario | ❌ | 完全未找到 | 跨業務場景協作不可用 | P3 |

---

## 4. 智能體編排平台能力總結

### 4.0 V1 → V2 功能演進對照

| 維度 | V1 (50 功能) | V2 (59 功能) | 變化 |
|------|-------------|-------------|------|
| 功能總數 | 50 | 59 | +9 (Phase 28 新增) |
| 定位 | 企業 IT 事件智能處理平台 | Agent Orchestration Platform | 重新定位 |
| 編排模式 | 12 | 12 | 不變 (核心穩定) |
| 人機協作 | 6 | 7 | +1 (Pending Approval Page) |
| 狀態管理 | 5 | 5 | 不變 |
| 前端介面 | 8 | 8 | 不變 (增加驗證深度) |
| 連接與整合 | 8 | 11 | +3 (InputGateway handlers) |
| 智能決策 | 6 | 10 | +4 (三層路由, GuidedDialog, Risk, Completeness) |
| 可觀測性 | 5 | 6 | +1 (OrchestrationMetrics) |
| 驗證方式 | 自評 | 代碼庫逐一驗證 (file:line) | 證據導向 |
| 文件格式 | ASCII 圖表 (1876 行) | ASCII 圖表 + 緊湊表格 (混合) | 視覺化 + 數據密度兼顧 |

### 4.1 平台核心能力對照

| 能力維度 | IPA Platform 現狀 | 與 n8n 的差異 |
|----------|-------------------|---------------|
| **Agent 編排** | 12 種模式 (Sequential → Magentic) | n8n 無 Agent 概念 |
| **人機協作** | 完整 HITL 生命週期 + Teams 通知 | n8n 僅固定審批節點 |
| **自主推理** | Claude SDK Autonomous Pipeline | n8n 無 AI 推理 |
| **智能路由** | 三層瀑布式 (10ms → 100ms → 2s) | n8n 固定路由規則 |
| **狀態持久化** | 4 種 Checkpoint Backend | n8n 基礎狀態 |
| **工具存取** | 5 MCP Server + 28 權限模式 | n8n 豐富的整合節點 (優勢) |
| **可觀測性** | OTel + 巡檢 + 審計 + 關聯分析 | n8n 基礎日誌 |
| **視覺化設計** | ⚠️ ReactFlow 開發中 | n8n 成熟的視覺化編輯 (優勢) |
| **確定性流程** | 非核心場景 | n8n 核心強項 (優勢) |

### 4.2 功能覆蓋率總結

- **88.1%** (52/59) 功能完整實現，有明確的代碼檔案和行號作為證據
- **94.9%** (56/59) 至少有部分實現
- **5.1%** (3/59) 存在缺口 (1 個未找到 + 2 個僅有最低限度覆蓋)

最強領域：
- Agent 編排 (12/12, 100%) --- 9+ MAF Builder 全部使用官方 API
- 人機協作 (7/7, 100%) --- 橫跨 4 個模組的完整 HITL stack
- 智能決策 (10/10, 100%) --- Phase 28 三層路由 + Claude 自主決策
- 可觀測性 (6/6, 100%) --- 審計 + 巡檢 + 指標 + 關聯分析

待改善領域：
- 前端介面 (6/8 完整) --- 工作流視覺化和通知系統需要強化
- 連接與整合 (8/11 完整) --- 跨場景協作、統一閘道需要補齊

### 4.3 平台獨特價值場景

IPA Platform 處理的是 n8n 無法處理的任務 --- 需要 AI 判斷力的不確定性任務：

| 場景類型 | IPA Platform 處理方式 | 為何 n8n 不適用 |
|----------|----------------------|----------------|
| **根因分析** | 多 Agent 協作診斷 + Extended Thinking | 需要推理，非固定規則 |
| **安全事件** | 風險評估 + HITL 審批 + 自主調查 | 需要判斷，每次都不同 |
| **資源規劃** | GroupChat 討論 + Voting 決策 | 需要多角度分析 |
| **複雜故障排除** | Sequential 診斷 + Trial-and-Error | 需要試錯和學習 |
| **新型態問題** | Few-shot Learning + Autonomous | 無既定流程可循 |

### 4.4 已知技術債與風險

| # | 問題 | 影響功能 | 嚴重度 | 狀態 |
|---|------|----------|--------|------|
| 1 | ContextSynchronizer 使用記憶體狀態 (無鎖、無 Redis) | #22 Context Transfer | 高 | 待修復 |
| 2 | 單 Uvicorn Worker 預設 | 全平台 | 高 | 生產環境需調整 |
| 3 | RabbitMQ 整合為空 (`__init__.py` only) | 非同步任務分派 | 中 | 待實現 |
| 4 | Mock 類與生產代碼並置 | 代碼衛生 | 低 | 可接受 |
| 5 | Stub 密度 ~1.1% | 活躍開發 | 低 | 正常 |
| 6 | Learning 模組部分完成 | #47 Few-shot | 中 | 功能可用但案例庫待充實 |

### 4.5 架構演進建議

| 優先級 | 方向 | 目標 | 涉及功能 |
|--------|------|------|----------|
| P0 | 生產化 | ContextSynchronizer 並行安全、Multi-Worker Uvicorn | #22 |
| P1 | 前端補齊 | ReactFlow 工作流視覺化、通知中心 | #31, #32 |
| P1 | 整合完善 | 統一閘道重構、跨場景協作 | #34, #41, #42 |
| P2 | 學習閉環 | Few-shot 學習案例庫完善、持續改進 | #47 |
| P3 | 擴展 MCP | 新增 K8s / Database / Email MCP Server | 新功能 |
| P3 | 基礎設施 | RabbitMQ 訊息佇列實現 | 基礎設施 |

---

## 5. 端到端場景：功能如何協同運作

以下展示一個典型場景如何串聯多個功能：

**場景**: 使用者報告「APAC Glider ETL Pipeline 連續第三天失敗，日報表無法產出」

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  端到端場景流程：ETL Pipeline 故障處理                                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  User: "APAC Glider ETL Pipeline 連續第三天失敗"                                     │
│      │                                                                               │
│      ▼  [#39 UserInput → #36 InputGateway]                                          │
│  ┌──────────────────────┐                                                            │
│  │ UnifiedRequestEnvelope│                                                            │
│  └──────────┬───────────┘                                                            │
│             ▼  [#48 PatternMatcher]                                                  │
│  "ETL"+"失敗" → IT_INCIDENT (confidence 0.92)                                       │
│             │                                                                        │
│             ▼  [#53 CompletenessChecker]                                             │
│  缺失: 錯誤訊息, 影響範圍, 已嘗試修復                                               │
│             │                                                                        │
│             ▼  [#51 GuidedDialogEngine]                                              │
│  追問: "請提供 Pipeline 錯誤日誌" / "影響哪些下游系統?"                              │
│             │                                                                        │
│             ▼  [#52 RiskAssessor]                                                    │
│  生產資料 + 連續失敗 → Risk: HIGH                                                    │
│             │                                                                        │
│             ▼  [#15 HITLController → #17 Teams → #19 Approval Page]                  │
│  ┌──────────────────────────────────────┐                                             │
│  │ 🔴 高風險審批: IT Manager 批准執行   │                                             │
│  └──────────┬───────────────────────────┘                                             │
│             ▼  [#44 Intelligent Routing]                                              │
│  診斷任務需要推理 → Claude SDK + MAF Sequential 混合                                 │
│             │                                                                        │
│             ▼  [#1 Sequential + #2 Concurrent + #45 Autonomous]                       │
│  Sequential: 診斷 → 修復 → 驗證                                                     │
│  Concurrent: 同時查詢 ADF / SQL / K8s                                                │
│  Autonomous: Claude 分析日誌 → 規劃修復 → 執行                                       │
│             │                                                                        │
│             ▼  [#33 MCP Connectors + #20 Checkpoint]                                 │
│  Azure MCP: 查詢 ADF 日誌 │ Shell MCP: 執行修復腳本                                 │
│  每步驟 Redis Checkpoint 持久化                                                      │
│             │                                                                        │
│             ▼  [#46 Trial-and-Error → #56 Metrics → #54 Audit]                       │
│  驗證修復 → 若失敗重試備選方案 → 記錄指標和審計                                      │
│             │                                                                        │
│             ▼  [#47 Few-shot + #25 Web UI + #27 Dashboard]                            │
│  案例學習 → AG-UI SSE 串流結果 → Dashboard 更新統計                                  │
│                                                                                      │
│  涉及 16 個功能，橫跨 8 個架構層級 (L1, L4-L9, L11)                                │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| 步驟 | 涉及功能 | 處理過程 |
|------|----------|----------|
| 1. 事件接入 | #39 UserInput Handler, #36 InputGateway | 使用者透過 Chat UI 輸入，InputGateway 標準化為 UnifiedRequestEnvelope |
| 2. 意圖路由 | #48 PatternMatcher | 「ETL」+「失敗」匹配 IT_INCIDENT 模式，confidence 0.92 > 0.9，直接命中 |
| 3. 完整度檢查 | #53 CompletenessChecker | 檢測缺失：具體錯誤訊息、影響範圍、已嘗試的修復 |
| 4. 引導對話 | #51 GuidedDialogEngine | 自動追問：「請提供 Pipeline 的錯誤日誌」「影響哪些下游系統？」 |
| 5. 風險評估 | #52 RiskAssessor | 涉及生產資料 + 連續失敗 → Risk Level: HIGH |
| 6. HITL 審批 | #15 HITLController, #17 Teams Notification | 高風險操作需審批，發送 Teams Adaptive Card 給 IT Manager |
| 7. 審批處理 | #16 Approval Handler, #19 Approval Page | Manager 透過 Teams 或 Web UI 批准執行 |
| 8. 框架選擇 | #44 Intelligent Routing | 診斷任務需要推理 → 選擇 Claude SDK + MAF Sequential 混合 |
| 9. 編排執行 | #1 Sequential, #2 Concurrent | Sequential: 診斷→修復→驗證；其中診斷階段 Concurrent 查詢多系統 |
| 10. 自主分析 | #45 Autonomous Decision | Claude Analyzer 分析日誌 → Planner 規劃修復 → Executor 執行 |
| 11. 工具調用 | #33 Connectors (MCP) | 透過 Azure MCP Server 查詢 ADF 日誌、Shell MCP 執行修復腳本 |
| 12. 狀態持久化 | #20 Checkpoint, #21 Memory | 每步驟 Checkpoint 存入 Redis；對話歷史持久化 |
| 13. 結果驗證 | #46 Trial-and-Error | Verifier 確認修復；若失敗，Retry 嘗試備選方案 |
| 14. 指標記錄 | #56 Metrics, #54 Audit | OrchestrationMetrics 記錄延遲、路由命中；Audit 記錄決策鏈 |
| 15. 學習記錄 | #47 Few-shot | 記錄案例，未來類似問題加速處理 |
| 16. 結果呈現 | #25 Web UI, #27 Dashboard | AG-UI SSE 即時串流結果到前端，Dashboard 更新統計 |

**此場景涉及 16 個功能** (#1, #2, #15-17, #19-21, #25, #27, #33, #36, #39, #44-48, #51-54, #56)，橫跨 8 個架構層級 (L1, L4-L9, L11)，展現了平台作為 Agent Orchestration Platform 的完整能力鏈。

---

## 附錄 A: V1 → V2 功能編號對照

V2 重新編排了功能編號 (#1-#59)，以下為 V1 主要功能對應：

| V1 # | V1 名稱 | V2 # | V2 名稱 | 備註 |
|-------|---------|-------|---------|------|
| 1 | 順序式 Agent 編排 | 1 | Sequential | 相同 |
| 2 | 人機協作檢查點 | 13 | HITL Checkpoints | 重新分類至人機協作 |
| 3 | 跨系統連接器 | 33 | Cross-system Connectors | 相同 |
| 4 | 跨場景協作 | 42 | Cross-scenario | V2 驗證為 ❌ 未找到 |
| 5 | Few-shot 學習 | 47 | Few-shot Learning | 相同 |
| 15 | Concurrent 並行 | 2 | Concurrent | 相同 |
| 18 | GroupChat | 3 | GroupChat | 相同 |
| 19 | Agent Handoff | 4 | Handoff | 相同 |
| 35 | Redis/Postgres Checkpoint | 20 | Redis/Postgres Checkpoint | 相同 |
| 39 | A2A | 40 | A2A Protocol | 相同 |
| - | (新增) | 48-53 | Phase 28 智能決策組件 | V2 新增 |
| - | (新增) | 56 | OrchestrationMetrics | V2 新增 |

> 完整的 V1 50 功能均已在 V2 的 59 功能中覆蓋或重新分類。V2 新增的 9 個功能主要來自 Phase 28 三層意圖路由系統。

---

## 附錄 B: 關鍵數據快速參考

### 代碼庫規模

| 指標 | 數值 |
|------|------|
| Backend LOC | ~120,000+ |
| Backend Integration Files | 200+ |
| Backend Domain Files | 114 |
| API Endpoints | 526 |
| API Route Files | 56 |
| API Route Modules | 38 |
| Frontend .tsx Files | 130+ |
| Frontend Pages | 36 |
| Frontend Components | 80+ |
| Frontend Custom Hooks | 15+ |
| MAF Builders | 9+ (官方 API) |
| MCP Servers | 5 |
| MCP Permission Patterns | 28 |
| MCP Audit Patterns | 16 |
| Checkpoint Backends | 4 |
| Patrol Check Types | 5 |
| Intent Router Layers | 3 |

### 專案里程碑

| 指標 | 數值 |
|------|------|
| 專案啟動 | 2025-11-14 |
| 已完成 Phases | 28 |
| 已完成 Sprints | 99 |
| Story Points | 2,189 |
| Phase 28 (三層路由) | Sprint 91-99, 235 SP |
| 技術棧 | FastAPI + React 18 + PostgreSQL + Redis |

---

## 更新歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 2.1 | 2026-01-28 | 補回 V1 架構圖示：11 層架構總覽圖、核心編排模式流程圖 (Sequential/Concurrent/GroupChat/Handoff/Planning)、HITL 生命週期圖、三層路由瀑布圖、自主決策管線圖、狀態記憶多層架構圖、InputGateway 資料流圖、端到端場景流程圖 |
| 2.0 | 2026-01-28 | 全面重寫：擴展至 59 功能；逐一代碼驗證；重新定位為 Agent Orchestration Platform；緊湊表格格式；新增功能缺口分析與平台能力對照 |
| 1.4 | 2026-01-22 | V1 最終版本 - 50 功能，含 Phase 28 更新 |
| 1.3 | 2026-01-16 | Phase 28 三層意圖路由系統更新 |
| 1.2 | 2026-01-10 | Phase 20 AG-UI 整合更新 |
| 1.1 | 2025-12-20 | Phase 15 Claude SDK 整合 |
| 1.0 | 2025-12-01 | 初始版本 - 企業 IT 事件智能處理平台 |
