# 智能體編排平台功能架構映射指南

> **文件版本**: 8.1
> **最後更新**: 2026-03-16
> **定位**: Agent Orchestration Platform (智能體編排平台)
> **前置文件**: `MAF-Claude-Hybrid-Architecture-V8.md` (架構總覽)
> **狀態**: Phase 34 已完成 (133 Sprints, ~2500+ Story Points)
> **驗證方式**: V8 Agent Team (22 分析 Agent + 3 交叉驗證 Agent) 全量源代碼 AST 級別驗證
> **前版**: V8.0 (2026-03-15, Phase 34), V7.0 (2026-02-11, Phase 29, 64 功能, 8+3 Agent 驗證)
> **V8.1 更新**: MAF RC4 升級 (`1.0.0b260114` → `1.0.0rc4`) 後的 Builder import 路徑、constructor API、類別重命名及 Claude SDK 同步更新反映

---

## 實現狀態總覽

> **重要說明**: 本文件是 V7 (64 功能) 的全面升級版本。V8 重新定義功能範圍為 **9 大類別 70 個計劃功能**，
> 基於 `phase2-sprint-plan-summary.md` 的完整功能清單。V8 另發現 **15 個計劃外功能**。
> V8 由 22 個分析 Agent 並行對整個代碼庫進行全量源代碼閱讀 (非 AST 抽樣)，再由 3 個交叉驗證 Agent 核實。
> 所有數據均來自 Phase 3 分析報告 (19 份) 和 Phase 4 驗證報告 (3 份)。

### 70 功能驗證結果

| 狀態 | 數量 | 比例 | 說明 |
|------|------|------|------|
| ✅ 完整實現 (COMPLETE) | 59 | 84.3% | 代碼庫中有完整實現，功能可運作 |
| ✅ 超額完成 (EXCEEDED) | 1 | 1.4% | E2 MCP: 計劃 5 個伺服器，實際交付 8 個 |
| ⚠️ 部分實現 (PARTIAL) | 2 | 2.9% | E1 ServiceNow (UAT only), E6 A2A (in-memory) |
| ⚠️ 分層完成 (SPLIT) | 4 | 5.7% | 整合層完成但 API 路由仍為 Stub (F7, G3, G4, G5) |
| ❌ 純 Stub/Mock | 0 | 0.0% | 無完全空殼功能 |
| ❌ 完全缺失 | 0 | 0.0% | 每個計劃功能至少有部分實現 |
| 📦 計劃外功能 | 15 | — | 有機增長的額外功能 |
| ⏸️ 已延後 (P3) | 4 | 5.7% | Phase 25 K8s/生產擴展 (計劃中標記為低優先) |

### 按類別統計

| 類別 | 功能數 | ✅ | ⚠️ | ❌ | 實現率 | V7 對比 |
|------|--------|-----|-----|-----|--------|---------|
| A. Agent 編排能力 | 16 | 16 | 0 | 0 | 100% | V7: 16/16 不變 |
| B. 人機協作能力 | 7 | 7 | 0 | 0 | 100% | V7: 7/7 不變 |
| C. 狀態與記憶能力 | 5 | 5 | 0 | 0 | 100% | V7: 5/5 不變 |
| D. 前端介面能力 | 11 | 11 | 0 | 0 | 100% | V7: 7/8 → V8: 11/11 (含 3 新功能) |
| E. 連接與整合能力 | 8 | 5 | 2 | 0 | 87.5% | V7: 11/11 → V8 重分類為 8 |
| F. 智能決策能力 | 7 | 6 | 1 | 0 | 85.7% | V7: 10/10 → V8 重分類為 7 |
| G. 可觀測性能力 | 5 | 2 | 3 | 0 | 40% 完整 | V7: 3/5 → V8: 2/5 完整 + 3 SPLIT |
| H. Agent Swarm 能力 | 4 | 4 | 0 | 0 | 100% | V7: 6/6 → V8 精簡為 4 |
| I. 安全能力 | 4 | 4 | 0 | 0 | 100% | V8 新增類別 |
| **未分類 (Phase 25)** | **4** | **0** | **0** | **4** | **已延後** | V7 未列出 |

> **V7→V8 類別變更說明**: V7 使用 64 功能 / 8 類別。V8 基於完整 Sprint Plan 重新定義為 70 功能 / 9 類別 (新增 I. 安全能力)。
> V7 的部分功能在 V8 中重新歸類 (如 InputGateway 併入 E, OrchestrationMetrics 歸為計劃外)。
> V8 新增 D10 ReactFlow DAG, D11 Agent Templates, E7 n8n Integration, E8 InputGateway 等。

### V7 → V8 狀態變更

| 指標 | V7 數值 | V8 數值 | 變更原因 |
|------|---------|---------|----------|
| 功能總數 (計劃) | 64 | **70** | V8 基於完整 Sprint Plan 重新盤點 |
| 計劃外功能 | — | **15** | V8 新增追蹤有機增長功能 |
| 類別數 | 8 | **9** | 新增安全能力類別 |
| 完整實現 | 54 (84.4%) | **59 (84.3%)** | 5 個新功能計入 |
| 部分實現 | 2 (3.1%) | **2 (2.9%)** | 同：E1 ServiceNow, E6 A2A |
| SPLIT 狀態 | — | **4 (5.7%)** | V8 新狀態：整合層完成但 API Stub |
| Backend LOC | ~228,700 | **~280,000+** | Phase 30-34 新增代碼 |
| API 端點 | 528 | **~550+** | 新增 orchestration, swarm, workflow-editor 端點 |
| Frontend .tsx/.ts 檔案 | 203 | **~250+** | 新增 agent-swarm, workflow-editor 組件 |
| MCP 伺服器 | 5 (計劃) | **8 (實際)** | 新增 n8n, ADF, D365 |
| MCP 工具數 | ~30 (計劃) | **64 (實際)** | 超額完成 |
| 已知問題 | 12 | **62** | V8 深度分析發現更多問題 |
| 驗證 Agent 數 | 8 | **25** | 22 分析 + 3 交叉驗證 |

---

## 執行摘要

本平台為企業級 AI 智能體編排系統，整合 Microsoft Agent Framework (MAF)、Claude Agent SDK、AG-UI Protocol 三大框架。
V8 分析基於 Phase 34 (Sprint 133) 代碼庫的全量源代碼閱讀，覆蓋：

- **Backend**: ~280,000+ LOC (Python), 76 core/infra 檔案, 94 API route 檔案, 20+ domain 模組, 12+ integration 模組
- **Frontend**: ~60,000+ LOC (TypeScript/React), 250+ .tsx/.ts 檔案, 41 pages, 82 components (unified-chat + agent-swarm + ag-ui)
- **API**: ~550+ REST 端點, 2 WebSocket 端點, 跨 30+ 路由模組
- **整合**: 8 MCP 伺服器 (64 工具), Claude SDK (10 子功能), AG-UI (7 核心功能 + 6 增強), Hybrid Orchestrator (Mediator Pattern)

**核心架構特徵**:
1. **三框架融合**: MAF (工作流編排) + Claude SDK (AI 推理) + AG-UI (即時互動)
2. **三層意圖路由**: Pattern Matcher (<10ms) → Semantic Router (<100ms) → LLM Classifier (<2000ms)
3. **四級風險控制**: LOW (自動) → MEDIUM (記錄) → HIGH (單人審批) → CRITICAL (多人審批)
4. **Mediator 模式**: Sprint 132 將 God Object 分解為 6 個獨立 Handler

**關鍵風險**: In-memory 持久化 (20+ 模組), API 路由未接通整合層 (4 功能), 前端靜默 Mock 降級 (10 頁面)

---

## 1. 架構層級與功能映射總覽

### 1.1 架構層級定義 (11 層)

```
┌─────────────────────────────────────────────────────────────────┐
│ L1  Frontend        │ React 18 + TypeScript + Vite              │
│                     │ 250+ .tsx/.ts, ~60,000+ LOC               │
│                     │ 41 pages, 82 components, 17 hooks         │
├─────────────────────┼───────────────────────────────────────────┤
│ L2  API Routes      │ FastAPI REST + WebSocket                  │
│                     │ 94 Python files, ~24,700 LOC              │
│                     │ ~550+ endpoints, 30+ modules              │
├─────────────────────┼───────────────────────────────────────────┤
│ L3  AG-UI Protocol  │ SSE Event Bridge + Thread Management     │
│                     │ 24 files, ~7,554 LOC                      │
│                     │ 7 core features + 6 enhancements          │
├─────────────────────┼───────────────────────────────────────────┤
│ L4  Orchestration   │ Intent Router + Dialog + Risk + HITL     │
│     (Phase 28)      │ ~40 files, ~12,000+ LOC                  │
│                     │ Three-tier routing + InputGateway          │
├─────────────────────┼───────────────────────────────────────────┤
│ L5  Hybrid Layer    │ Context Bridge + Mode Switcher + Risk    │
│     (Phase 13-14)   │ ~69 files, ~21,000 LOC                   │
│                     │ Mediator Pattern (Sprint 132)             │
├─────────────────────┼───────────────────────────────────────────┤
│ L6  Agent Framework │ MAF Builder Adapters + Core              │
│     (Phase 1-8)     │ 57 files, ~18,000+ LOC                   │
│     MAF RC4         │ 7 Primary Builders, ALL COMPLIANT (RC4)  │
├─────────────────────┼───────────────────────────────────────────┤
│ L7  Claude SDK      │ Anthropic SDK + Autonomous + Hooks       │
│     (Phase 12, 22)  │ ~40 files, ~12,000+ LOC                  │
│                     │ 10 sub-features                           │
├─────────────────────┼───────────────────────────────────────────┤
│ L8  MCP Servers     │ 8 Enterprise Integration Servers         │
│     (Phase 9-10+)   │ ~64 tools, ~12,400 LOC                   │
│                     │ Azure/FS/Shell/LDAP/SSH/n8n/ADF/D365      │
├─────────────────────┼───────────────────────────────────────────┤
│ L9  Domain Services │ Business Logic + State Machines           │
│                     │ 20+ modules, ~30,000+ LOC                 │
│                     │ Sessions (12,272 LOC), Workflows, Agents  │
├─────────────────────┼───────────────────────────────────────────┤
│ L10 Infrastructure  │ Database + Cache + Storage + Messaging   │
│                     │ 76 files (core+infra), ~7,300 LOC         │
│                     │ PostgreSQL 16 + Redis 7 + RabbitMQ (stub) │
├─────────────────────┼───────────────────────────────────────────┤
│ L11 Remaining       │ A2A, Swarm, Memory, Patrol, Correlation  │
│     Integrations    │ ~64 files across 12 modules               │
│                     │ Sprint 130 修復了 Correlation + RootCause  │
└─────────────────────┴───────────────────────────────────────────┘
```

### 1.2 功能到層級映射圖

| 類別 | 主要架構層級 | 功能數 |
|------|-------------|--------|
| A. Agent 編排能力 | L6 (Agent Framework) + L2 (API) + L9 (Domain) | 16 |
| B. 人機協作能力 | L4 (Orchestration) + L5 (Hybrid) + L6 (AF) | 7 |
| C. 狀態與記憶能力 | L9 (Domain) + L10 (Infrastructure) + L11 (Memory) | 5 |
| D. 前端介面能力 | L1 (Frontend) | 11 |
| E. 連接與整合能力 | L7 (Claude SDK) + L8 (MCP) + L3 (AG-UI) + L11 (A2A) | 8 |
| F. 智能決策能力 | L4 (Orchestration) + L5 (Hybrid) + L7 (Claude SDK) | 7 |
| G. 可觀測性能力 | L4 (Metrics) + L11 (Patrol/Correlation/RootCause) | 5 |
| H. Agent Swarm 能力 | L11 (Swarm) + L3 (AG-UI) + L2 (API) + L1 (Frontend) | 4 |
| I. 安全能力 | L10 (Core Auth/Sandbox) + L8 (MCP RBAC) | 4 |

### 1.3 功能與架構層級映射矩陣

| 層級 | 功能編號 | 功能數 |
|------|----------|--------|
| **L1** Frontend | D1-D11, H3 | 12 |
| **L2** API Layer | H2 + (所有功能皆有 API endpoint) | 1+ |
| **L3** AG-UI Protocol | E5 + SSE 串流橫切 (HITL + Swarm + Chat) | 橫切 |
| **L4** Orchestration | B6-B7, E8, F3-F6 | 8 |
| **L5** Hybrid Layer | B3-B5, E4, F2 | 5 |
| **L6** MAF Builder | A5-A16, B2 | 13 |
| **L7** Claude SDK | E3, F7 | 2 |
| **L8** MCP Layer | E2, I4 | 2 |
| **L9** Domain + Supporting | A1-A4, C1-C5, E6-E7, G1-G5, H1, H4 | 18 |
| **L10** Infrastructure | I1-I3 | 3 |
| **L11** Infrastructure Services | PostgreSQL + Redis backends | 橫切 |

### 1.4 架構層級功能分布

```
L1  Frontend:             ████████████  12 功能 (D1-D11 + H3 Swarm 前端)
L2  API:                  █            1 功能 (H2 Swarm API) + 橫切所有
L3  AG-UI:                (橫切)       E5 SSE 串流基礎設施
L4  Orchestration:        ████████     8 功能 (Phase 28 智能入口 + HITL)
L5  Hybrid:               █████        5 功能 (風險/切換/上下文)
L6  MAF Builder:          █████████████ 13 功能 (編排核心 + 擴展)
L7  Claude SDK:           ██           2 功能 (E3 SDK + F7 Autonomous)
L8  MCP:                  ██           2 功能 (E2 8 Servers + I4 RBAC)
L9  Domain+Supporting:    ██████████████████ 18 功能 (最大層級)
L10 Infrastructure:       ███          3 功能 (Auth + Sandbox)
L11 Infra Services:       (橫切)       PostgreSQL + Redis
```

---

## 2. Category A: Agent 編排能力 (16 功能)

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | LOC | 驗證來源 |
|---|------|--------|------|----------|-----|----------|
| A1 | Agent CRUD + Framework Core | S1 | ✅ | `domain/agents/`, `api/v1/agents/` | 1,904 + API | phase3b-domain-part1, phase3a-api-part1 |
| A2 | Workflow Definition + Execution | S1-2 | ✅ | `api/v1/workflows/`, `domain/workflows/` | 12 endpoints | phase3a-api-part3, phase3b-domain-part3 |
| A3 | Tool Integration (ToolRegistry) | S1 | ✅ | `domain/agents/tools/` | 1,001 | phase3b-domain-part1 |
| A4 | Execution State Machine | S1 | ✅ | `domain/executions/state_machine.py` | 465 | phase3b-domain-part1 |
| A5 | Concurrent Execution (Fork-Join) | S7 | ✅ | `api/v1/concurrent/`, `builders/concurrent.py` | 1,633 | phase3a-api-part1, phase3c-af-part1 |
| A6 | Agent Handoff | S8 | ✅ | `api/v1/handoff/`, `builders/handoff.py` | 14 endpoints | phase3a-api-part2, phase3c-af-part1 |
| A7 | GroupChat Multi-agent | S9 | ✅ | `api/v1/groupchat/`, `builders/groupchat.py` | 42 endpoints | phase3a-api-part2, phase3c-af-part1 |
| A8 | Dynamic Planning | S10 | ✅ | `api/v1/planning/`, `builders/magentic.py` | ~46 endpoints | phase3a-api-part3, phase3c-af-part1 |
| A9 | Nested Workflow | S11 | ✅ | `api/v1/nested/`, `builders/nested_workflow.py` | 16 endpoints | phase3a-api-part2, phase3c-af-part1 |
| A10 | Code Interpreter | S37-38 | ✅ | `api/v1/code_interpreter/` | Azure OpenAI | phase3a-api-part1 |
| A11-A16 | MAF Builder Adapters | S13-33 | ✅ | `integrations/agent_framework/builders/` (24 files) | ~18,000+ | phase3c-af-part1, phase3c-af-part2 |

#### A1: Agent CRUD + Framework Core
- **狀態**: ✅ COMPLETE
- **Sprint**: S1 (Phase 1)
- **實現檔案**: `domain/agents/service.py` (342 LOC), `domain/agents/tools/registry.py` (377 LOC), `domain/agents/tools/builtin.py` (558 LOC), `api/v1/agents/` (完整 CRUD)
- **業務邏輯**: AgentService 通過 Adapter Pattern 委託至 AgentExecutorAdapter (Sprint 31 遷移)。ToolRegistry 單例管理工具註冊/搜尋。內建工具：HttpTool, DateTimeTool, calculate。Mock 工具：get_weather, search_knowledge_base (demo 用)
- **數據持久化**: PostgreSQL (via AgentRepository)
- **依賴關係**: AgentExecutorAdapter (integrations/agent_framework)
- **問題**: get_weather 和 search_knowledge_base 為 Mock demo 工具
- **驗證來源**: phase3b-domain-part1

#### A2: Workflow Definition + Execution
- **狀態**: ✅ COMPLETE
- **Sprint**: S1-2, S29, S133
- **實現檔案**: `api/v1/workflows/` (12 endpoints), `domain/workflows/` (via integrations)
- **業務邏輯**: 工作流 CRUD、定義驗證、執行觸發。Phase 34 新增 ReactFlow 可視化編輯器端點
- **數據持久化**: PostgreSQL (DB-backed)
- **依賴關係**: WorkflowBuilder (agent_framework), CheckpointService
- **問題**: 無
- **驗證來源**: phase3a-api-part3

#### A3: Tool Integration (ToolRegistry)
- **狀態**: ✅ COMPLETE
- **Sprint**: S1
- **實現檔案**: `domain/agents/tools/base.py` (383 LOC), `domain/agents/tools/registry.py` (377 LOC), `domain/agents/tools/builtin.py` (558 LOC)
- **業務邏輯**: BaseTool ABC + @tool decorator。ToolRegistry 支援 register/unregister/get/search/list_by_category。Claude SDK 額外有 10 個內建工具
- **數據持久化**: InMemory (registry dict)
- **依賴關係**: 被 AgentService、Claude SDK ToolManager 使用
- **問題**: 無
- **驗證來源**: phase3b-domain-part1

#### A4: Execution State Machine
- **狀態**: ✅ COMPLETE
- **Sprint**: S1
- **實現檔案**: `domain/executions/state_machine.py` (428 LOC)
- **業務邏輯**: 6 狀態 (PENDING → RUNNING → PAUSED → COMPLETED/FAILED/CANCELLED)，完整的狀態轉移驗證、歷史記錄、持續時間計算、LLM 成本追蹤
- **數據持久化**: InMemory (pure domain object, caller 負責持久化)
- **依賴關係**: 被 ExecutionService、WorkflowExecutor 使用
- **問題**: 無
- **驗證來源**: phase3b-domain-part1

#### A5: Concurrent Execution (Fork-Join)
- **狀態**: ✅ COMPLETE
- **Sprint**: S7
- **實現檔案**: `builders/concurrent.py` (1,633 LOC), `api/v1/concurrent/`
- **業務邏輯**: ConcurrentBuilderAdapter wraps official MAF ConcurrentBuilder。支援 4 種模式：ALL/ANY/MAJORITY/FIRST_SUCCESS。GatewayType、JoinCondition、自訂 aggregators、超時管理
- **數據持久化**: InMemory
- **依賴關係**: ConcurrentBuilder (agent_framework), `from agent_framework.orchestrations import ConcurrentBuilder` (COMPLIANT, V8.1: RC4 遷移至子模組, constructor 改為 `ConcurrentBuilder(participants=list)`)
- **問題**: In-memory only (C-01)
- **驗證來源**: phase3c-af-part1

#### A6: Agent Handoff
- **狀態**: ✅ COMPLETE
- **Sprint**: S8
- **實現檔案**: `builders/handoff.py` + 5 extension files (handoff_policy, capability, context, service, hitl), `api/v1/handoff/` (14 endpoints)
- **業務邏輯**: HandoffBuilderAdapter wraps official MAF HandoffBuilder。HandoffMode 枚舉、HandoffRoute 配置、execution result 追蹤、participant 管理
- **數據持久化**: InMemory (HITL endpoints)
- **依賴關係**: HandoffBuilder (agent_framework), `from agent_framework.orchestrations import HandoffBuilder` (COMPLIANT, V8.1: RC4 遷移至子模組, constructor 改為 `HandoffBuilder(participants=list)`)
- **問題**: HITL endpoints still in-memory (C-01)
- **驗證來源**: phase3c-af-part1, phase3a-api-part2

#### A7: GroupChat Multi-agent
- **狀態**: ✅ COMPLETE
- **Sprint**: S9
- **實現檔案**: `builders/groupchat.py` (1,310+ LOC), `api/v1/groupchat/` (42 endpoints, 1,770 LOC)
- **業務邏輯**: GroupChatBuilderAdapter wraps official MAF GroupChatBuilder。7 種 speaker 選擇策略 (AUTO/ROUND_ROBIN/RANDOM/MANUAL/PRIORITY/EXPERTISE/VOTING)。GroupChatState、participant 配置
- **數據持久化**: InMemory
- **依賴關係**: GroupChatBuilder (agent_framework), `from agent_framework.orchestrations import GroupChatBuilder` (COMPLIANT, V8.1: RC4 遷移至子模組, constructor 改為 `GroupChatBuilder(participants=list)`)
- **問題**: In-memory only; groupchat route file 過大 (1,770 LOC) (C-01)
- **驗證來源**: phase3c-af-part1, phase3a-api-part2

#### A8: Dynamic Planning
- **狀態**: ✅ COMPLETE
- **Sprint**: S10, S17, S24, S31
- **實現檔案**: `builders/magentic.py` (1,257+ LOC), `api/v1/planning/` (~46 endpoints, ~1,180 LOC)
- **業務邏輯**: MagenticBuilderAdapter wraps MAF MagenticBuilder。Task/Progress Ledger、fact extraction、planning、progress evaluation、3 種 human intervention (PLAN_REVIEW, TOOL_APPROVAL, STALL)。包含 PlanningAdapter CRUD、MultiTurn sessions、autonomous decisions、trial-and-error 學習
- **數據持久化**: InMemory (plans, decisions, trials in module-level dicts)
- **依賴關係**: MagenticBuilder (agent_framework), `from agent_framework.orchestrations import MagenticBuilder` (COMPLIANT, V8.1: RC4 遷移至子模組, constructor 改為 `MagenticBuilder(participants=list)`)
- **問題**: Large route file (~1,000 LOC); in-memory stores
- **驗證來源**: phase3c-af-part1, phase3a-api-part3

#### A9: Nested Workflow
- **狀態**: ✅ COMPLETE
- **Sprint**: S11
- **實現檔案**: `builders/nested_workflow.py`, `api/v1/nested/` (16 endpoints)
- **業務邏輯**: NestedWorkflowBuilder wraps MAF WorkflowBuilder，支援工作流遞迴組合與 adapter pattern
- **數據持久化**: Adapter delegation
- **依賴關係**: WorkflowBuilder (agent_framework), (COMPLIANT)
- **問題**: 無
- **驗證來源**: phase3c-af-part1, phase3a-api-part2

#### A10: Code Interpreter
- **狀態**: ✅ COMPLETE
- **Sprint**: S37-38
- **實現檔案**: `api/v1/code_interpreter/`, `integrations/agent_framework/builders/code_interpreter.py`
- **業務邏輯**: Azure OpenAI Assistants API 整合，支援代碼執行、結果回傳、檔案處理
- **數據持久化**: Azure OpenAI + InMemory
- **依賴關係**: Azure OpenAI SDK, agent_framework
- **問題**: chart 檔案固定存為 `chart.png` 無唯一性 (P2-18)
- **驗證來源**: phase3a-api-part1, phase3c-af-part2

#### A11-A16: MAF Builder Adapters (遷移)
- **狀態**: ✅ COMPLETE (ALL 7 PRIMARY BUILDERS COMPLIANT)
- **Sprint**: S13-33
- **實現檔案**: `integrations/agent_framework/builders/` (24 files), `core/` (9 files), root files (5 files) — 共 57 files
- **業務邏輯**: 7 個 Primary Builder Adapter 全部通過合規審計：ConcurrentBuilder, HandoffBuilder, GroupChatBuilder, MagenticBuilder, WorkflowExecutor, NestedWorkflow, PlanningAdapter。每個都正確 import 並使用 `self._builder = OfficialBuilder()`。另有 10 個 Extension Adapter (平台業務邏輯)、5 個 Migration Shim (Phase 2 向後相容)
- **數據持久化**: N/A (Adapter Pattern)
- **依賴關係**: `agent-framework>=1.0.0rc4,<2.0.0` 官方套件
- **問題**: edge_routing.py 缺少 MAF imports (W-1); core/context.py 使用 duck typing (W-2)
- **V8.1 RC4 遷移記錄**:
  - Orchestration Builders (ConcurrentBuilder, HandoffBuilder, GroupChatBuilder, MagenticBuilder) import 路徑從 `from agent_framework import` 遷移至 `from agent_framework.orchestrations import`
  - Builder constructor 從 fluent API `Builder()` + `.participants(list)` 改為 kwarg `Builder(participants=list)`
  - 4 組類別重命名以向後相容別名實施: `Agent as ChatAgent`, `Message as ChatMessage`, `WorkflowEvent as WorkflowStatusEvent`, `BaseContextProvider as ContextProvider`
  - 核心類別 (Workflow, Edge, WorkflowExecutor 等) 仍從頂層 `agent_framework` import (RC4 仍 re-export，GA 可能需遷移 — 見 R8)
  - 驗證結果: 17/17 integration tests pass, 221/222 adapter tests pass (詳見 `sdk-version-gap/POST-UPGRADE-Verification-Consensus.md`)
- **驗證來源**: phase3c-af-part1, phase3c-af-part2

---

## 3. Category B: 人機協作能力 (7 功能)

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | 驗證來源 |
|---|------|--------|------|----------|----------|
| B1 | Checkpoint Mechanism | S2 | ✅ | `domain/checkpoints/`, `api/v1/checkpoints/` | phase3b-domain-part1, phase3a-api-part1 |
| B2 | HITL Approval Flow | S2 | ✅ | `agent_framework/core/approval.py` + `approval_workflow.py` | phase3c-af-part1, phase3a-api-part1 |
| B3 | Risk Assessment Engine | S55 | ✅ | `hybrid/risk/` (2,422 LOC) | phase3c-hybrid-part1 |
| B4 | Mode Switcher | S56 | ✅ | `hybrid/switching/` | phase3c-hybrid-part2 |
| B5 | Unified Checkpoint | S57 | ✅ | `hybrid/checkpoint/` | phase3c-hybrid-part2 |
| B6 | HITL Controller (Phase 28) | S98 | ✅ | `orchestration/hitl/`, `api/v1/orchestration/` | phase3c-orch-part2, phase3a-api-part3 |
| B7 | Approval Routes (Phase 28) | S98 | ✅ | `api/v1/orchestration/approval_routes` | phase3a-api-part3 |

#### B1: Checkpoint Mechanism
- **狀態**: ✅ COMPLETE
- **Sprint**: S2, S28
- **實現檔案**: `domain/checkpoints/` (CheckpointStorage ABC + multiple backends)
- **業務邏輯**: 4 個後端：Memory、Redis、PostgreSQL、Filesystem。支援 checkpoint 建立/載入/刪除/列表
- **數據持久化**: PostgreSQL (via Repository + Storage) — 預設 InMemory
- **依賴關係**: 被 SessionRecoveryManager、HybridCheckpoint 使用
- **問題**: 預設為 InMemory (C-01)
- **驗證來源**: phase3b-domain-part1

#### B2: HITL Approval Flow
- **狀態**: ✅ COMPLETE
- **Sprint**: S2
- **實現檔案**: `agent_framework/core/approval.py`, `approval_workflow.py`
- **業務邏輯**: COMPLIANT — 使用官方 MAF Executor + handler 實現審批工作流
- **數據持久化**: InMemory (InMemoryApprovalStorage 為預設)
- **依賴關係**: agent_framework Executor, handler
- **問題**: InMemoryApprovalStorage 為預設 (C-01)
- **驗證來源**: phase3c-af-part1

#### B3: Risk Assessment Engine
- **狀態**: ✅ COMPLETE
- **Sprint**: S55
- **實現檔案**: `hybrid/risk/engine.py` (560 LOC), `risk/analyzers/` (3 files), `risk/scoring/scorer.py`
- **業務邏輯**: 7 種風險因子 (OPERATION/CONTEXT/PATTERN/PATH/COMMAND/FREQUENCY/ESCALATION)。3 種評分策略 (WEIGHTED_AVERAGE/MAX_WEIGHTED/HYBRID)。4 級風險等級 (LOW 0-0.3 / MEDIUM 0.3-0.6 / HIGH 0.6-0.85 / CRITICAL 0.85-1.0)。滑動視窗歷史分析 (max 100 entries)
- **數據持久化**: InMemory (AssessmentHistory)
- **依賴關係**: 被 HybridOrchestratorV2、OrchestrationRiskAssessor 使用
- **問題**: 風險引擎 hooks 為同步 (可能阻塞事件迴圈)
- **驗證來源**: phase3c-hybrid-part1

#### B4: Mode Switcher
- **狀態**: ✅ COMPLETE
- **Sprint**: S56
- **實現檔案**: `hybrid/switching/` (ModeSwitcher + 4 trigger detectors)
- **業務邏輯**: 完整的 trigger → switch → checkpoint → rollback 管線，支援 MAF ↔ Claude 動態切換
- **數據持久化**: Redis (SwitchCheckpoint) 或 InMemory
- **依賴關係**: RiskAssessmentEngine, ContextBridge
- **問題**: 兩套獨立的 checkpoint 系統可能造成混淆
- **驗證來源**: phase3c-hybrid-part2

#### B5: Unified Checkpoint
- **狀態**: ✅ COMPLETE
- **Sprint**: S57, S120
- **實現檔案**: `hybrid/checkpoint/` (4 backends: Memory, Redis, PostgreSQL, Filesystem)
- **業務邏輯**: HybridCheckpoint 支援 MAF + Claude states、risk snapshot、versioning、V1→V2 migration、JSON+ZLIB 壓縮、SHA-256 完整性驗證
- **數據持久化**: 4 個後端可選，預設 Memory
- **依賴關係**: SessionRecoveryManager, HybridOrchestratorV2
- **問題**: 預設為 MemoryCheckpointStorage (C-01)
- **驗證來源**: phase3c-hybrid-part2

#### B6: HITL Controller (Phase 28)
- **狀態**: ✅ COMPLETE
- **Sprint**: S98
- **實現檔案**: `orchestration/hitl/`, `api/v1/orchestration/` (28 endpoints)
- **業務邏輯**: HITLController 整合至 HybridOrchestratorV2。支援審批列表/詳情/決策提交/超時/升級。Pagination 為 in-memory (載入全部再切片)
- **數據持久化**: Redis 或 InMemory (HITLController)
- **依賴關係**: RiskAssessor, BusinessIntentRouter
- **問題**: Pagination in-memory 效能問題; 大量使用 hasattr() duck-typing
- **驗證來源**: phase3c-orch-part2, phase3a-api-part3

#### B7: Approval Routes (Phase 28)
- **狀態**: ✅ COMPLETE
- **Sprint**: S98
- **實現檔案**: `api/v1/orchestration/approval_routes`
- **業務邏輯**: 列出/取得/提交/超時/升級審批請求的 REST API
- **數據持久化**: 委託至 HITLController
- **依賴關係**: HITLController
- **問題**: 無
- **驗證來源**: phase3a-api-part3

---

## 4. Category C: 狀態與記憶能力 (5 功能)

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | LOC | 驗證來源 |
|---|------|--------|------|----------|-----|----------|
| C1 | Session Mode | S42-43 | ✅ | `domain/sessions/` (33 files) | 12,272 | phase3b-domain-part3 |
| C2 | AgentExecutor Unified Interface | S45-47 | ✅ | `domain/sessions/bridge.py` | ~850 | phase3b-domain-part3 |
| C3 | Redis LLM Cache | S2 | ✅ | `infrastructure/cache/`, `integrations/llm/` | — | phase3d-core-infra, phase3c-remaining |
| C4 | mem0 Memory System | S79-80 | ✅ | `integrations/memory/` (5 files) | — | phase3c-remaining |
| C5 | mem0 Polish | S90 | ✅ | `integrations/memory/`, `api/v1/memory/` | — | phase3c-remaining |

#### C1: Session Mode
- **狀態**: ✅ COMPLETE
- **Sprint**: S42-43, S45-47
- **實現檔案**: `domain/sessions/` — 33 files, ~12,272 LOC (最大且最關鍵的 domain 模組)
- **業務邏輯**: SessionAgentBridge 整合 SessionService (CRUD + 狀態機)、AgentExecutor (LLM 互動)、ToolCallHandler (工具審批)、SessionErrorHandler、SessionRecoveryManager、MetricsCollector。狀態機: CREATED → ACTIVE ↔ SUSPENDED → ENDED
- **數據持久化**: PostgreSQL (SQLAlchemySessionRepository) + Redis (SessionCache, Write-Through)
- **依賴關係**: agent_framework core, orchestration intent routing, infrastructure/database
- **問題**: 雙事件系統 (ExecutionEvent + SessionEvent 共存); bridge.py ~850 LOC 可分解; DeadlockDetector 使用 singleton
- **驗證來源**: phase3b-domain-part3

#### C2: AgentExecutor Unified Interface
- **狀態**: ✅ COMPLETE
- **Sprint**: S45-47
- **實現檔案**: `domain/sessions/bridge.py` (~850 LOC), `executor.py`, `streaming.py`, `tool_handler.py`, `approval.py`, `error_handler.py`, `recovery.py`, `metrics.py`
- **業務邏輯**: SessionAgentBridge 統一 AgentExecutor + StreamingLLMHandler + ToolCallHandler + ToolApprovalManager + ErrorHandler + RecoveryManager + MetricsCollector
- **數據持久化**: 委託至 SessionService (PostgreSQL + Redis)
- **依賴關係**: SessionService, AgentService, orchestration
- **問題**: bridge.py 過大 (~850 LOC)，可考慮分解
- **驗證來源**: phase3b-domain-part3

#### C3: Redis LLM Cache
- **狀態**: ✅ COMPLETE
- **Sprint**: S2
- **實現檔案**: `core/config.py` (cache settings), `infrastructure/cache/`, `integrations/llm/`
- **業務邏輯**: LLM 回應快取層，cache_enabled + cache_ttl 設定。Redis 作為快取後端
- **數據持久化**: Redis
- **依賴關係**: infrastructure/redis_client
- **問題**: 無
- **驗證來源**: phase3d-core-infra, phase3c-remaining

#### C4: mem0 Memory System
- **狀態**: ✅ COMPLETE
- **Sprint**: S79-80
- **實現檔案**: `integrations/memory/` (5 files), `api/v1/memory/`
- **業務邏輯**: 三層記憶系統 (working/episodic/semantic)。Redis + PostgreSQL + mem0/Qdrant 後端。每層可選且優雅降級
- **數據持久化**: Redis + PostgreSQL + Qdrant
- **依賴關係**: mem0 library, Qdrant client
- **問題**: 無
- **驗證來源**: phase3c-remaining

#### C5: mem0 Polish
- **狀態**: ✅ COMPLETE
- **Sprint**: S90
- **實現檔案**: `integrations/memory/`, `api/v1/memory/`
- **業務邏輯**: 記憶搜尋 UI 整合、三層模型確認
- **數據持久化**: 同 C4
- **依賴關係**: 同 C4
- **問題**: 無
- **驗證來源**: phase3c-remaining

---

## 5. Category D: 前端介面能力 (11 功能)

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | LOC | 驗證來源 |
|---|------|--------|------|----------|-----|----------|
| D1 | Dashboard | S5 | ✅ | `pages/dashboard/` (5 files) | ~862 | phase3e-frontend-part1 |
| D2 | Workflow Management Pages | S5 | ✅ | `pages/workflows/` (5 files) | ~2,041 | phase3e-frontend-part1 |
| D3 | Agent Management Pages | S5 | ✅ | `pages/agents/` (4 files) | ~2,040 | phase3e-frontend-part1 |
| D4 | Approval Workbench | S5 | ✅ | `pages/approvals/ApprovalsPage.tsx` | ~260 | phase3e-frontend-part1 |
| D5 | AG-UI Components | S58-61 | ✅ | `pages/ag-ui/`, `components/ag-ui/` (12 files) | ~2,900 | phase3e-frontend-part2 |
| D6 | UnifiedChat | S62-65 | ✅ | `pages/UnifiedChat.tsx` + 27 components | ~7,100 | phase3e-frontend-part1, part2 |
| D7 | Login/Signup | S70 | ✅ | `pages/auth/` (2 files) | ~520 | phase3e-frontend-part1 |
| D8 | DevUI Pages | S87-89 | ✅ | `pages/DevUI/` (7 files) | ~1,682 | phase3e-frontend-part1 |
| D9 | Agent Swarm Visualization | S100-106 | ✅ | `components/agent-swarm/` (15+4+2 files) | ~4,700 | phase3e-frontend-part2, part3 |
| D10 | ReactFlow Workflow DAG | S133 | ✅ | `components/workflow-editor/` | ~350+ | phase3e-frontend-part3 |
| D11 | Agent Templates | S4 | ✅ | `pages/templates/TemplatesPage.tsx` | ~230 | phase3e-frontend-part1 |

#### D1: Dashboard
- **狀態**: ✅ COMPLETE
- **Sprint**: S5
- **實現檔案**: `pages/dashboard/DashboardPage.tsx` (87 LOC), `PerformancePage.tsx` (469 LOC), 4 sub-components (StatsCards, ExecutionChart, PendingApprovals, RecentExecutions)
- **業務邏輯**: DashboardPage 使用真實 DB 查詢。子組件 (ExecutionChart, PerformancePage) 有 Mock fallback
- **數據持久化**: 讀取 PostgreSQL
- **依賴關係**: Backend API `/dashboard/*`
- **問題**: 10 個頁面靜默降級至 Mock 資料 (H-08); N+1 查詢模式 (M-03); stats 端點靜默吞掉例外 (M-04)
- **驗證來源**: phase3e-frontend-part1

#### D2: Workflow Management Pages
- **狀態**: ✅ COMPLETE
- **Sprint**: S5, S29, S133
- **實現檔案**: `WorkflowsPage.tsx` (170), `WorkflowDetailPage.tsx` (400), `CreateWorkflowPage.tsx` (700), `EditWorkflowPage.tsx` (750), `WorkflowEditorPage.tsx` (21)
- **業務邏輯**: 完整 CRUD，清單/詳情/建立/編輯/ReactFlow 編輯器
- **數據持久化**: 讀取 PostgreSQL
- **依賴關係**: Backend workflows API
- **問題**: Create/Edit 頁面 ~80% 代碼重複 (M-12)
- **驗證來源**: phase3e-frontend-part1

#### D3: Agent Management Pages
- **狀態**: ✅ COMPLETE
- **Sprint**: S5
- **實現檔案**: `AgentsPage.tsx` (230), `AgentDetailPage.tsx` (360), `CreateAgentPage.tsx` (750), `EditAgentPage.tsx` (700)
- **業務邏輯**: 完整 CRUD，清單/詳情/建立/編輯
- **數據持久化**: 讀取 PostgreSQL
- **依賴關係**: Backend agents API
- **問題**: Create/Edit 頁面 ~80% 代碼重複 (M-12)
- **驗證來源**: phase3e-frontend-part1

#### D4: Approval Workbench
- **狀態**: ✅ COMPLETE
- **Sprint**: S5
- **實現檔案**: `pages/approvals/ApprovalsPage.tsx` (~260 LOC)
- **業務邏輯**: 審批工作台，顯示待審項目，支援批准/拒絕操作
- **數據持久化**: 讀取 API
- **依賴關係**: Backend approval API
- **問題**: API 失敗時 Mock fallback
- **驗證來源**: phase3e-frontend-part1

#### D5: AG-UI Components
- **狀態**: ✅ COMPLETE
- **Sprint**: S58-61
- **實現檔案**: `pages/ag-ui/` (7 demo components), `components/ag-ui/` (12 files, ~2,900 LOC)
- **業務邏輯**: 7 個 AG-UI 功能 demo (AgenticChat, ToolRendering, HITL, GenerativeUI, ToolUI, SharedState, Predictive)。chat/ 子組件 (MessageBubble, ToolCallCard, StreamingIndicator)。hitl/ (ApprovalList, ApprovalBanner)。advanced/ (CustomUIRenderer, DynamicForm, DynamicChart, DynamicCard, DynamicTable)
- **數據持久化**: 無 (demo 用模擬資料)
- **依賴關係**: AG-UI SSE bridge
- **問題**: 6/7 demos 使用模擬資料
- **驗證來源**: phase3e-frontend-part2

#### D6: UnifiedChat
- **狀態**: ✅ COMPLETE
- **Sprint**: S62-65, S66, S69, S73-75, S99
- **實現檔案**: `pages/UnifiedChat.tsx` (~900 LOC), 27+ unified-chat 組件 (~6,200 LOC)
- **業務邏輯**: 主聊天介面，整合 Claude API via AG-UI SSE。組件樹：ChatHeader + ChatArea (MessageList → MessageBubble + ApprovalMessageCard) + ChatInput + WorkflowSidePanel + OrchestrationPanel + ModeIndicator + RiskIndicator + ChatHistoryPanel + FileUpload。8 個預設工具 (5 低風險自動執行, 3 高風險需 HITL)
- **數據持久化**: localStorage (threads via useChatThreads)
- **依賴關係**: useAGUI hook, useOrchestration hook, AG-UI SSE bridge
- **問題**: ~20 個 console.log 語句 (M-14); localStorage-only thread storage; 2 個 TODO 註解; orchestrationEnabled 硬編碼為 true (L-16)
- **驗證來源**: phase3e-frontend-part1, phase3e-frontend-part2

#### D7: Login/Signup
- **狀態**: ✅ COMPLETE
- **Sprint**: S70
- **實現檔案**: `pages/auth/LoginPage.tsx` (~230 LOC), `SignupPage.tsx` (~290 LOC)
- **業務邏輯**: Email/password 登入 + 註冊。表單驗證 (email 格式, 密碼強度, 確認密碼)
- **數據持久化**: 委託至 Backend auth API
- **依賴關係**: useAuthStore (Zustand)
- **問題**: 無
- **驗證來源**: phase3e-frontend-part1

#### D8: DevUI Pages
- **狀態**: ✅ COMPLETE
- **Sprint**: S87-89
- **實現檔案**: `pages/DevUI/` (7 files: index, Layout, TraceList, TraceDetail, LiveMonitor, Settings, AGUITestPanel)
- **業務邏輯**: 開發者工具 UI。TraceList/TraceDetail 為完整實現。LiveMonitor 和 Settings 為 "Coming Soon" 佔位符
- **數據持久化**: 讀取 devtools API (in-memory backend)
- **依賴關係**: Backend devtools API
- **問題**: 2 個 "Coming Soon" 佔位符頁面 (LiveMonitor, Settings)
- **驗證來源**: phase3e-frontend-part1

#### D9: Agent Swarm Visualization
- **狀態**: ✅ COMPLETE
- **Sprint**: S100-106
- **實現檔案**: `components/agent-swarm/` (15 components + 4 hooks + 2 type files), `pages/SwarmTestPage.tsx` (~845 LOC)
- **業務邏輯**: 完整的 Agent Swarm 視覺化工具組。Mock mode (useSwarmMock) + Real mode (useSwarmReal SSE)。SwarmHeader + OverallProgress + WorkerCardList + WorkerDetailDrawer。Zustand store (useSwarmStore) 管理即時狀態
- **數據持久化**: Zustand (前端狀態管理)
- **依賴關係**: Backend swarm SSE API, useSwarmStore
- **問題**: 無。乾淨的 TypeScript 實現
- **驗證來源**: phase3e-frontend-part2, phase3e-frontend-part3

#### D10: ReactFlow Workflow DAG (V8 新增)
- **狀態**: ✅ COMPLETE
- **Sprint**: S133 (Phase 34)
- **實現檔案**: `components/workflow-editor/WorkflowCanvas.tsx` (~350 LOC), 4 custom node types (AgentNode, ConditionNode, ActionNode, StartEndNode), 2 custom edge types (DefaultEdge, ConditionalEdge)
- **業務邏輯**: ReactFlow 視覺化 DAG 編輯器。Dagre 自動排版 (TB/LR)。拖拽 + 自動儲存 (2s debounce)。TanStack Query 資料管理。匯出 JSON。MiniMap + Controls + Background
- **數據持久化**: 委託至 Backend workflows API
- **依賴關係**: ReactFlow, Dagre, TanStack Query, useWorkflowData hook
- **問題**: 無
- **驗證來源**: phase3e-frontend-part3

#### D11: Agent Templates (V8 新增追蹤)
- **狀態**: ✅ COMPLETE
- **Sprint**: S4
- **實現檔案**: `pages/templates/TemplatesPage.tsx` (~230 LOC)
- **業務邏輯**: 模板清單頁面，支援分類、搜尋
- **數據持久化**: 讀取 Backend templates API
- **依賴關係**: Backend templates API
- **問題**: "Use Template" 按鈕沒有 handler (非功能性) (H-11)
- **驗證來源**: phase3e-frontend-part1

---

## 6. Category E: 連接與整合能力 (8 功能)

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | 驗證來源 |
|---|------|--------|------|----------|----------|
| E1 | ServiceNow Connector | S2 | ⚠️ PARTIAL | `api/v1/connectors/` | phase3a-api-part1 |
| E2 | MCP Architecture (8 Servers) | S39-41+ | ✅ EXCEEDED | `integrations/mcp/` (~12,400 LOC) | phase3c-mcp-part1, part2 |
| E3 | Claude Agent SDK | S48-50 | ✅ | `integrations/claude_sdk/` (~12,000+ LOC) | phase3c-claude-sdk |
| E4 | Hybrid MAF+Claude | S52-54 | ✅ | `integrations/hybrid/` (~21,000 LOC) | phase3c-hybrid-part1, part2 |
| E5 | AG-UI Protocol (SSE) | S58-61 | ✅ | `integrations/ag_ui/` (24 files, ~7,554 LOC) | phase3c-ag-ui |
| E6 | A2A Protocol | S82 | ⚠️ PARTIAL | `integrations/a2a/` (4 files) | phase3c-remaining |
| E7 | n8n Integration | S82+ | ✅ | `integrations/n8n/`, `api/v1/n8n/` | phase3c-remaining, phase3a-api-part2 |
| E8 | InputGateway | S95 | ✅ | `orchestration/input_gateway/` | phase3c-orch-part1 |

#### E1: ServiceNow Connector
- **狀態**: ⚠️ PARTIAL
- **Sprint**: S2
- **實現檔案**: `api/v1/connectors/` (UAT test only)
- **業務邏輯**: ServiceNow 連接器存在但僅為 "UAT test only" 端點，非生產就緒
- **數據持久化**: InMemory (registry + state)
- **依賴關係**: ConnectorRegistry
- **問題**: 非生產就緒；僅測試用端點
- **驗證來源**: phase3a-api-part1

#### E2: MCP Architecture (8 Servers, 64 Tools)
- **狀態**: ✅ EXCEEDED (計劃 5，實際 8)
- **Sprint**: S39-41, S114, S124, S125, S129
- **實現檔案**: `integrations/mcp/servers/` — 8 個伺服器，`security/` — RBAC 權限系統

| 伺服器 | 工具數 | LOC | 外部 SDK | Sprint |
|--------|--------|-----|----------|--------|
| Azure | 24 | ~2,700 | azure-identity, azure-mgmt-* | Phase 9-10 |
| Filesystem | 6 | ~1,300 | pathlib (stdlib) | Phase 9-10 |
| Shell | 2 | ~700 | subprocess (stdlib) | Phase 9-10 |
| LDAP | 6+AD | ~2,000 | ldap3 | Phase 9-10, S114 |
| SSH | 6 | ~1,500 | paramiko | Phase 9-10 |
| n8n | 6 | ~1,100 | httpx | S124 |
| ADF | 8 | ~1,300 | httpx (Azure REST) | S125 |
| D365 | 6 | ~1,800 | httpx (OData) | S129 |
| **合計** | **64** | **~12,400** | — | — |

- **業務邏輯**: 所有 8 個伺服器連接真實外部服務 (非 Mock)。4 級 RBAC (NONE/READ/EXECUTE/ADMIN)，glob patterns，priority-based evaluation，deny-first，dual-mode (log/enforce)。MCPPermissionChecker 已整合至所有 8 個伺服器
- **數據持久化**: N/A (外部服務)
- **依賴關係**: azure SDK, ldap3, paramiko, httpx
- **問題**: Shell/SSH HITL 命令白名單僅記錄不阻止 (H-12, H-13); MCP Permission 預設模式為 "log" 非 "enforce" (H-07); AuditLogger 未接線 (H-06)
- **驗證來源**: phase3c-mcp-part1, phase3c-mcp-part2

#### E3: Claude Agent SDK
- **狀態**: ✅ COMPLETE
- **Sprint**: S48-50, S79, S81, S104
- **實現檔案**: `integrations/claude_sdk/` — ~40 files, ~12,000+ LOC

| 子功能 | 檔案 | 說明 |
|--------|------|------|
| Core Client | `client.py` (357 LOC) | AsyncAnthropic SDK，streaming + extended thinking |
| Sessions | `session.py` (287 LOC) | Multi-turn agentic loop + fork |
| Query | `query.py` (345 LOC) | One-shot agentic loop + attachments |
| State Persistence | `session_state.py` (576 LOC) | Compression + mem0 整合 |
| Autonomous | `autonomous/` (7 files, ~2,587 LOC) | Analyzer + Planner + Executor + Verifier + Retry + Fallback |
| Hooks | `hooks/` (5 files, ~1,384 LOC) | Approval(90) + Sandbox(85) + RateLimit(70) + Audit(50) |
| Hybrid Selection | `hybrid/` (6 files, ~2,166 LOC) | CapabilityMatcher + FrameworkSelector + HybridOrchestrator + ContextSynchronizer |
| MCP | `mcp/` (7 files, ~3,207 LOC) | ToolDiscovery + MCPManager + stdio/http servers |
| Orchestrator | `orchestrator/` (4 files, ~1,630 LOC) | ClaudeCoordinator + TaskAllocator + ContextManager |

- **業務邏輯**: 使用真實 `from anthropic import AsyncAnthropic` SDK。Agentic loop (tool_use → execute → feed back)。Extended Thinking (`interleaved-thinking-2025-05-14` beta header)。6 種 Smart Fallback 策略
- **數據持久化**: InMemory + Claude API
- **依賴關係**: `anthropic>=0.84.0` (V8.1: 正式加入 requirements.txt), mem0
- **問題**: Streaming 未在 Session.query() 中實現 (M-07); MCP tool 整合 registry 為 stub (M-08); ContextSynchronizer 非執行緒安全 (H-04)
- **V8.1 Claude SDK 更新記錄**:
  - 預設模型 ID: `claude-haiku-4-5-20251001` (client.py:38)
  - Extended Thinking header: `interleaved-thinking-2025-05-14` (原 `extended-thinking-2025-04-30`)
  - 殘留: 5 個源碼檔 + 8 個測試檔仍用舊模型 ID (R1, HIGH); docstring 過時 (R5, LOW)
- **驗證來源**: phase3c-claude-sdk, sdk-version-gap/POST-UPGRADE-Verification-Consensus.md

#### E4: Hybrid MAF+Claude
- **狀態**: ✅ COMPLETE (+ Sprint 132 重構)
- **Sprint**: S52-54, S132
- **實現檔案**: `integrations/hybrid/` — ~69 files, ~21,000 LOC
- **業務邏輯**: 4 大子系統：intent/ (FrameworkSelector, 1,223 LOC), context/ (ContextBridge 932 LOC + ContextSynchronizer 629 LOC, 3,080 LOC), risk/ (RiskAssessmentEngine, 2,422 LOC), orchestrator/ (Mediator Pattern, Sprint 132)。Sprint 132 將 God Object orchestrator_v2.py (1,254 LOC) 分解為 OrchestratorMediator + 6 Handler (Routing/Dialog/Approval/Execution/Context/Observability)
- **數據持久化**: InMemory (context cache), Redis (switch checkpoints)
- **依賴關係**: BusinessIntentRouter, GuidedDialogEngine, HITLController, RiskAssessor
- **問題**: ContextBridge cache 非執行緒安全 (H-04); God Object facade 仍為主要入口點
- **驗證來源**: phase3c-hybrid-part1, phase3c-hybrid-part2

#### E5: AG-UI Protocol (SSE)
- **狀態**: ✅ COMPLETE
- **Sprint**: S58-61, S66-67, S69, S75, S101, S119
- **實現檔案**: `integrations/ag_ui/` — 24 files, ~7,554 LOC
- **業務邏輯**: 完整 AG-UI Protocol 實現。11 種事件類型 (RUN_STARTED/FINISHED, TEXT_MESSAGE_START/CONTENT/END, TOOL_CALL_START/ARGS/END, STATE_SNAPSHOT/DELTA, CUSTOM)。7 核心功能 + 6 增強 (HITL tool event, Heartbeat, Step progress, File attachment, Swarm events, Redis thread storage)。HybridEventBridge (1,080 LOC) 為 SSE 串流核心。Write-Through Thread caching pattern
- **數據持久化**: InMemory (ApprovalStorage, ChatSession, SharedState, PredictiveState) + Redis (ThreadRepository via Sprint 119)
- **依賴關係**: HybridOrchestratorV2, Claude SDK
- **問題**: ApprovalStorage/ChatSession/SharedState/PredictiveState 皆為 in-memory (C-01); SSE 重連邏輯在前端 hook 中為 stub; 不支援真正的 token-by-token streaming (M-21)
- **驗證來源**: phase3c-ag-ui

#### E6: A2A Protocol
- **狀態**: ⚠️ PARTIAL
- **Sprint**: S82
- **實現檔案**: `integrations/a2a/` (4 files), `api/v1/a2a/`
- **業務邏輯**: A2A Protocol 完整序列化 (12 MessageTypes)。Discovery 使用加權匹配
- **數據持久化**: InMemory (agent registry + messages, 無外部傳輸)
- **依賴關係**: 無外部依賴
- **問題**: In-memory only, 無外部傳輸層
- **驗證來源**: phase3c-remaining, phase3a-api-part1

#### E7: n8n Integration (V8 新增追蹤)
- **狀態**: ✅ COMPLETE
- **Sprint**: S82+
- **實現檔案**: `integrations/n8n/` (3 files), `api/v1/n8n/`
- **業務邏輯**: n8n REST API 整合 via httpx。Webhook + HMAC 安全驗證
- **數據持久化**: InMemory (config/callbacks)
- **依賴關係**: httpx, n8n API
- **問題**: Config/callbacks in-memory (C-01)
- **驗證來源**: phase3c-remaining, phase3a-api-part2

#### E8: InputGateway (V8 新增追蹤)
- **狀態**: ✅ COMPLETE
- **Sprint**: S95
- **實現檔案**: `orchestration/input_gateway/gateway.py` (~370 LOC), `models.py` (~250 LOC), `schema_validator.py` (~370 LOC), 3 source handlers
- **業務邏輯**: 統一入口閘道，自動識別來源類型 (user/webhook/alert)。3 個 source handlers (ServiceNow, Prometheus, UserInput)。JSON schema 驗證
- **數據持久化**: N/A (pass-through)
- **依賴關係**: BusinessIntentRouter (downstream)
- **問題**: Source handlers 使用 Mock fallback
- **驗證來源**: phase3c-orch-part1

---

## 7. Category F: 智能決策能力 (7 功能)

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | LOC | 驗證來源 |
|---|------|--------|------|----------|-----|----------|
| F1 | LLM Service Layer | S34-36 | ✅ | `integrations/llm/` (6 files) | — | phase3c-remaining |
| F2 | Intent Router (Hybrid) | S52 | ✅ | `hybrid/intent/router.py` (FrameworkSelector) | 1,223 | phase3c-hybrid-part1 |
| F3 | Three-tier Routing | S91-97 | ✅ | `orchestration/intent_router/` (~12 files) | ~5,000+ | phase3c-orch-part1 |
| F4 | Guided Dialog Engine | S94, S97 | ✅ | `orchestration/guided_dialog/` (4 files) | ~3,529 | phase3c-orch-part1 |
| F5 | Business Intent Router | S96 | ✅ | `orchestration/intent_router/router.py` | 623 | phase3c-orch-part1 |
| F6 | LLM Classifier | S97, S128 | ✅ | `orchestration/intent_router/llm_classifier/` | ~1,230 | phase3c-orch-part1 |
| F7 | Claude Autonomous Planning | S79 | ⚠️ SPLIT | API: `api/v1/autonomous/` (STUB) / Integration: `claude_sdk/autonomous/` (COMPLETE) | ~2,587 | phase3a-api-part1, phase3c-claude-sdk |

#### F1: LLM Service Layer
- **狀態**: ✅ COMPLETE
- **Sprint**: S34-36
- **實現檔案**: `integrations/llm/` (6 files)
- **業務邏輯**: AzureOpenAILLMService 使用官方 `openai.AsyncAzureOpenAI` SDK。真實 API 呼叫 + retry 邏輯 + error handling。工廠模式自動偵測環境，僅在非生產環境降級至 mock
- **數據持久化**: Redis (LLM response cache)
- **依賴關係**: openai SDK, Azure OpenAI credentials
- **問題**: 無
- **驗證來源**: phase3c-remaining

#### F2: Intent Router (Hybrid)
- **狀態**: ✅ COMPLETE
- **Sprint**: S52
- **實現檔案**: `hybrid/intent/router.py` (FrameworkSelector), `classifiers/rule_based.py`, `analyzers/complexity.py`, `analyzers/multi_agent.py`
- **業務邏輯**: 兩層路由 (IT intent + framework selection)。RuleBasedClassifier (關鍵字模式, EN+ZH-TW 雙語)。ComplexityAnalyzer (步驟/依賴評分)。MultiAgentDetector (協作偵測)
- **數據持久化**: InMemory (session context)
- **依賴關係**: BusinessIntentRouter (downstream)
- **問題**: 無
- **驗證來源**: phase3c-hybrid-part1

#### F3: Three-tier Routing (Pattern → Semantic → LLM)
- **狀態**: ✅ COMPLETE
- **Sprint**: S91-97, S115, S128
- **實現檔案**: `orchestration/intent_router/` — PatternMatcher (~350 LOC + 400 LOC YAML), SemanticRouter (~370 LOC + ~300 LOC routes + Azure 實作 ~620 LOC), LLMClassifier (~280 LOC + prompts ~200 LOC + cache ~250 LOC + evaluation ~500 LOC), CompletenessChecker (~320 LOC + rules ~660 LOC)
- **業務邏輯**: 三層級聯路由：Tier 1 PatternMatcher (<10ms, 30+ regex rules, conf>=0.90) → Tier 2 SemanticRouter (<100ms, vector similarity, sim>=0.85, 15 routes) → Tier 3 LLMClassifier (<2000ms, 真實 LLM API 呼叫)。5 種 ITIL 意圖分類 (INCIDENT/REQUEST/CHANGE/QUERY/UNKNOWN)。CompletenessChecker 欄位完整性檢查
- **數據持久化**: InMemory (classification cache)
- **依賴關係**: LLMServiceProtocol, Azure OpenAI (embeddings), Azure AI Search (向量索引)
- **問題**: 無 — 真實 embeddings，非 mock
- **驗證來源**: phase3c-orch-part1

#### F4: Guided Dialog Engine
- **狀態**: ✅ COMPLETE
- **Sprint**: S94, S97
- **實現檔案**: `guided_dialog/engine.py` (593 LOC), `context_manager.py` (1,163 LOC), `generator.py` (1,151 LOC), `refinement_rules.py` (622 LOC)
- **業務邏輯**: 狀態機：INITIAL → GATHERING → COMPLETE/HANDOFF。關鍵設計：後續回合使用規則式欄位提取 (incremental update)，不重新呼叫 LLM。Template-based 問題生成 (繁體中文)。RefinementRules 更新 sub_intent。支援 LLM 模式 (Sprint 97) 但預設使用 template
- **數據持久化**: InMemory (session storage: `_dialog_sessions` dict)
- **依賴關係**: BusinessIntentRouter (initial classification), CompletenessChecker
- **問題**: In-memory session storage (C-01)
- **驗證來源**: phase3c-orch-part1

#### F5: Business Intent Router
- **狀態**: ✅ COMPLETE
- **Sprint**: S96
- **實現檔案**: `orchestration/intent_router/router.py` (623 LOC)
- **業務邏輯**: BusinessIntentRouter 協調三層路由 + completeness checking。返回 RoutingDecision (intent_category, sub_intent, confidence, routing_layer, workflow_type, risk_level)
- **數據持久化**: N/A (coordinator)
- **依賴關係**: PatternMatcher, SemanticRouter, LLMClassifier, CompletenessChecker
- **問題**: 無
- **驗證來源**: phase3c-orch-part1

#### F6: LLM Classifier
- **狀態**: ✅ COMPLETE
- **Sprint**: S97, S128
- **實現檔案**: `llm_classifier/classifier.py` (~280 LOC), `prompts.py` (~200 LOC), `cache.py` (~250 LOC), `evaluation.py` (~500 LOC)
- **業務邏輯**: 真實 LLM 呼叫 via LLMServiceProtocol (Azure OpenAI/Claude/Mock)。快取、評估套件、graceful degradation (init 失敗時降級至 mock)
- **數據持久化**: InMemory (classification cache)
- **依賴關係**: LLMServiceProtocol
- **問題**: 真實 router init 失敗時降級至 mock (F6 fallback pattern)
- **驗證來源**: phase3c-orch-part1

#### F7: Claude Autonomous Planning
- **狀態**: ⚠️ SPLIT (API: STUB / Integration: COMPLETE)
- **Sprint**: S79
- **實現檔案**: API: `api/v1/autonomous/` (379 LOC, 100% mock) / Integration: `integrations/claude_sdk/autonomous/` (7 files, ~2,587 LOC, COMPLETE)
- **業務邏輯**: API 層為 UAT stub，生成假步驟 `["analyze", "plan", "prepare", "execute", "cleanup"]`，無 Claude SDK 整合。整合層為完整實現：EventAnalyzer (Extended Thinking) + AutonomousPlanner (decision tree) + PlanExecutor (streaming) + ResultVerifier (validation + learning) + RetryPolicy (failure classification) + SmartFallback (6 strategies)
- **數據持久化**: InMemory (API task store)
- **依賴關係**: API: 無。Integration: anthropic SDK
- **問題**: API 路由未接通整合層 (C-03)。模組 docstring 明確寫 "Phase 22 Testing"
- **驗證來源**: phase3a-api-part1, phase3c-claude-sdk

---

## 8. Category G: 可觀測性能力 (5 功能)

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | 驗證來源 |
|---|------|--------|------|----------|----------|
| G1 | Audit Logging | S3 | ✅ | `domain/audit/` (758 LOC), `api/v1/audit/` | phase3b-domain-part1, phase3a-api-part1 |
| G2 | DevUI Tracing | S4, S66-68 | ✅ | `domain/devtools/tracer.py` (777 LOC), `api/v1/devtools/` | phase3b-domain-part1, phase3a-api-part2 |
| G3 | Patrol Monitoring | S82, S130 | ⚠️ SPLIT | API: `api/v1/patrol/` (STUB) / Integration: `integrations/patrol/` (COMPLETE) | phase3a-api-part3, phase3c-remaining |
| G4 | Event Correlation | S82, S130 | ⚠️ SPLIT | API: `api/v1/correlation/` (STUB) / Integration: `integrations/correlation/` (COMPLETE) | phase3a-api-part1, phase3c-remaining |
| G5 | Root Cause Analysis | S82, S130 | ⚠️ SPLIT | API: `api/v1/rootcause/` (STUB) / Integration: `integrations/rootcause/` (COMPLETE) | phase3a-api-part3, phase3c-remaining |

#### G1: Audit Logging
- **狀態**: ✅ COMPLETE
- **Sprint**: S3
- **實現檔案**: `domain/audit/logger.py` (728 LOC), `api/v1/audit/` (7 audit + 6 decision endpoints)
- **業務邏輯**: AuditLogger 支援 20 種 action types, 9 種 resource types, 4 級 severity。完整的 query/filter、execution trail、CSV/JSON export 功能
- **數據持久化**: **InMemory only** (list, max_entries 限制) — 無 DB 持久化
- **依賴關係**: 被多個模組使用 (agents, workflows, etc.)
- **問題**: In-memory audit 為合規風險 (C-01)
- **驗證來源**: phase3b-domain-part1

#### G2: DevUI Tracing
- **狀態**: ✅ COMPLETE
- **Sprint**: S4, S66-68
- **實現檔案**: `domain/devtools/tracer.py` (777 LOC), `api/v1/devtools/` (12 endpoints)
- **業務邏輯**: ExecutionTracer 完整的 trace/span/event 系統。支援 timeline 視覺化、event 過濾、statistics 計算
- **數據持久化**: **InMemory** (traces dict, 可無限增長)
- **依賴關係**: 被 API devtools endpoints 使用
- **問題**: In-memory traces 可無限增長 (C-01)
- **驗證來源**: phase3b-domain-part1

#### G3: Patrol Monitoring
- **狀態**: ⚠️ SPLIT
- **Sprint**: S82 (API), S130 (Integration fix)
- **實現檔案**: API: `api/v1/patrol/` (9 endpoints, STUB — all mock/hardcoded)。Integration: `integrations/patrol/` (11 files, COMPLETE — 5 real checks using psutil/HTTP/filesystem)
- **業務邏輯**: 整合層完整：5 種真實檢查 (HTTP health, process monitor, filesystem, metric threshold, custom script)。使用 psutil 系統資料。API 層仍為 stub
- **數據持久化**: InMemory (API), Real system data (Integration)
- **依賴關係**: psutil, httpx
- **問題**: API 路由未接通整合層 (C-05); API 使用 time.sleep() 在 async handler 中 (blocking)
- **驗證來源**: phase3a-api-part3, phase3c-remaining

#### G4: Event Correlation
- **狀態**: ⚠️ SPLIT
- **Sprint**: S82 (API), S130 (Integration fix)
- **實現檔案**: API: `api/v1/correlation/` (7 endpoints, STUB — 100% mock, uuid4() + hardcoded values)。Integration: `integrations/correlation/` (6 files, COMPLETE — Sprint 130 修復)
- **業務邏輯**: **Sprint 130 重大修復**：整合層現使用 EventDataSource (Azure Monitor/App Insights REST API)、EventCollector (deduplication + aggregation)。優雅降級至空結果 (不再回傳假資料)。API 層仍生成假資料
- **數據持久化**: InMemory (API mock), Real Azure Monitor (Integration)
- **依賴關係**: Azure Monitor REST API, App Insights
- **問題**: API 路由未接通整合層 (C-02)
- **驗證來源**: phase3a-api-part1, phase3c-remaining

#### G5: Root Cause Analysis
- **狀態**: ⚠️ SPLIT
- **Sprint**: S82 (API), S130 (Integration fix)
- **實現檔案**: API: `api/v1/rootcause/` (4 endpoints, STUB — hardcoded)。Integration: `integrations/rootcause/` (5 files, COMPLETE — Sprint 130 修復)
- **業務邏輯**: **Sprint 130 重大修復**：整合層現使用 CaseRepository (15 真實 IT Ops seed cases) + CaseMatcher (multi-dimensional scoring: text similarity + category + severity + recency)。優雅降級至空結果。API 層仍硬編碼
- **數據持久化**: InMemory (API), CaseRepository seed data (Integration)
- **依賴關係**: CorrelationAnalyzer (upstream)
- **問題**: API 路由未接通整合層 (C-04)
- **驗證來源**: phase3a-api-part3, phase3c-remaining

---

## 9. Category H: Agent Swarm 能力 (4 功能)

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | 驗證來源 |
|---|------|--------|------|----------|----------|
| H1 | Swarm Manager + Workers | S100-102 | ✅ | `integrations/swarm/` (7 files), `api/v1/swarm/` (8 endpoints) | phase3c-remaining, phase3a-api-part3 |
| H2 | Swarm SSE Events | S103 | ✅ | `api/v1/swarm/` (SSE streaming) | phase3a-api-part3 |
| H3 | Swarm Frontend Panel | S104-105 | ✅ | `components/agent-swarm/` (15+4+2 files) | phase3e-frontend-part2, part3 |
| H4 | Swarm Tests | S106 | ✅ | Tests exist | phase3c-remaining |

#### H1: Swarm Manager + Workers
- **狀態**: ✅ COMPLETE
- **Sprint**: S100-102
- **實現檔案**: `integrations/swarm/` (7 files), `api/v1/swarm/` (8 endpoints)
- **業務邏輯**: Thread-safe SwarmTracker。SwarmIntegrationBridge 整合 ClaudeCoordinator。支援 worker 生命週期管理、任務分配、進度追蹤
- **數據持久化**: InMemory + optional Redis
- **依賴關係**: ClaudeCoordinator (claude_sdk/orchestrator)
- **問題**: 無
- **驗證來源**: phase3c-remaining, phase3a-api-part3

#### H2: Swarm SSE Events
- **狀態**: ✅ COMPLETE
- **Sprint**: S103
- **實現檔案**: `api/v1/swarm/` (SSE streaming endpoints)
- **業務邏輯**: SSE event system with throttling/batching。整合至 AG-UI HybridEventBridge
- **數據持久化**: N/A (streaming)
- **依賴關係**: SwarmTracker, AG-UI Bridge
- **問題**: 無
- **驗證來源**: phase3a-api-part3

#### H3: Swarm Frontend Panel
- **狀態**: ✅ COMPLETE
- **Sprint**: S104-105
- **實現檔案**: `components/agent-swarm/` — 15 components + 4 hooks + 2 type files (~4,700 LOC)
- **業務邏輯**: 完整視覺化工具組。SwarmHeader + OverallProgress + WorkerCardList + WorkerDetailDrawer。支援 Mock mode (useSwarmMock) + Real mode (useSwarmReal SSE)。Zustand store 狀態管理
- **數據持久化**: Zustand (前端 state)
- **依賴關係**: Backend swarm SSE API, useSwarmStore
- **問題**: 無
- **驗證來源**: phase3e-frontend-part2, phase3e-frontend-part3

#### H4: Swarm Tests
- **狀態**: ✅ COMPLETE
- **Sprint**: S106
- **實現檔案**: `components/agent-swarm/__tests__/` (12 test files)
- **業務邏輯**: Swarm 功能的測試覆蓋
- **數據持久化**: N/A
- **依賴關係**: N/A
- **問題**: 無
- **驗證來源**: phase3c-remaining

---

## 10. Category I: 安全能力 (4 功能) — V8 新增類別

### 總覽

| # | 功能 | Sprint | 狀態 | 主要檔案 | 驗證來源 |
|---|------|--------|------|----------|----------|
| I1 | JWT Authentication | S70 | ✅ | `core/auth.py` | phase3d-core-infra |
| I2 | Global Auth Middleware | S111 | ✅ | `core/auth.py` (protected_router) | phase3d-core-infra |
| I3 | Sandbox Isolation | S77-78 | ✅ | `core/sandbox/` | phase3d-core-infra, phase3a-api-part3 |
| I4 | MCP Permission System | S39 | ✅ | `mcp/security/` | phase3c-mcp-part1 |

#### I1: JWT Authentication
- **狀態**: ✅ COMPLETE
- **Sprint**: S70
- **實現檔案**: `core/auth.py`
- **業務邏輯**: JWT (HS256, 1-hour expiry) + bcrypt (via passlib) + HTTPBearer。create_access_token, decode_token, hash_password, verify_password。輕量驗證 + 完整 DB 驗證雙模式
- **數據持久化**: PostgreSQL (User model)
- **依賴關係**: python-jose, passlib, infrastructure/database
- **問題**: JWT secret 硬編碼 `"change-this-to-a-secure-random-string"` (需生產環境配置)
- **驗證來源**: phase3d-core-infra

#### I2: Global Auth Middleware
- **狀態**: ✅ COMPLETE
- **Sprint**: S111
- **實現檔案**: `core/auth.py` (protected_router)
- **業務邏輯**: protected_router with auth dependency injection。覆蓋所有 API routes (但缺少 RBAC 角色檢查)
- **數據持久化**: N/A
- **依賴關係**: JWT auth
- **問題**: 無 RBAC 角色檢查在破壞性操作上 (H-01); Rate limiter 為 in-memory (H-14)
- **驗證來源**: phase3d-core-infra

#### I3: Sandbox Isolation
- **狀態**: ✅ COMPLETE
- **Sprint**: S77-78
- **實現檔案**: `core/sandbox/config.py` (ProcessSandboxConfig), `core/sandbox/ipc.py`, `api/v1/sandbox/` (6 endpoints)
- **業務邏輯**: Process-level sandbox。ProcessSandboxConfig + IPC 通訊。環境變數過濾、sensitive data masking、path traversal prevention
- **數據持久化**: N/A (process isolation)
- **依賴關係**: subprocess
- **問題**: 模擬 sandbox，非真實容器隔離 (H-09)
- **驗證來源**: phase3d-core-infra

#### I4: MCP Permission System
- **狀態**: ✅ COMPLETE
- **Sprint**: S39, S113
- **實現檔案**: `mcp/security/permissions.py`, `mcp/security/permission_checker.py`
- **業務邏輯**: 4 級 RBAC (NONE/READ/EXECUTE/ADMIN)。glob patterns、priority-based evaluation、deny-first。dual-mode (log/enforce)。已整合至所有 8 個 MCP servers
- **數據持久化**: InMemory (policy storage)
- **依賴關係**: MCPProtocol
- **問題**: 預設模式為 "log" (不阻止); dev/test 環境自動授予 ADMIN (H-07)
- **驗證來源**: phase3c-mcp-part1

---

## 11. 計劃外功能 (15 Unplanned Extras)

以下功能不在原始 Sprint Plan 的 9 大類別中，但已在代碼庫中實現：

| # | 功能 | 模組 | 來源 Sprint | 狀態 | 說明 |
|---|------|------|------------|------|------|
| U1 | 3 額外 MCP Servers (n8n, ADF, D365) | `integrations/mcp/` | S124, S125, S129 | ✅ | 計劃 5 伺服器，實際交付 8 個，64 tools |
| U2 | Learning / Few-Shot System | `integrations/learning/` | S4 | ✅ | LearningService + build_few_shot_prompt()。SequenceMatcher (生產應用 embeddings) |
| U3 | Notification System | `api/v1/notifications/` | S3 | ✅ | TeamsNotificationService，11 endpoints，Adaptive Card v1.4 |
| U4 | IT Incident Processing | `integrations/incident/` | — | ✅ | 完整事件處理管線 (correlation + rootcause + LLM) |
| U5 | Shared Protocols Module | `integrations/shared/` | — | ✅ | 跨模組 Protocol 定義 |
| U6 | Performance Monitoring API | `api/v1/performance/` | S12 | ⚠️ | 11 endpoints，Phase2 stats 硬編碼 |
| U7 | Prompt Management API | `api/v1/prompts/` | S3 | ✅ | 11 endpoints，模板管理 |
| U8 | Routing Engine API | `api/v1/routing/` | S3 | ✅ | 14 endpoints，ScenarioRouter |
| U9 | Version Control API | `api/v1/versioning/` | S4 | ✅ | 14 endpoints，版本控制 |
| U10 | Trigger/Webhook API | `api/v1/triggers/` | S3 | ✅ | 9 endpoints，觸發器管理 |
| U11 | Mediator Pattern Refactor | `hybrid/orchestrator/mediator.py` | S132 | ✅ | HybridOrchestratorV2 God Object 分解為 Mediator + 6 Handler |
| U12 | Extended Thinking (Claude) | `claude_sdk/client.py` | S104 | ✅ | beta header streaming |
| U13 | Multi-Agent Coordinator | `claude_sdk/orchestrator/` | S81 | ✅ | ClaudeCoordinator + TaskAllocator |
| U14 | Orchestration Metrics (OTel) | `orchestration/metrics.py` | S99 | ✅ | ~893 LOC, dual-mode OTel + fallback, 12+ metric types |
| U15 | Structured Logging + OTel | `core/logging`, `core/observability` | — | ✅ | Full OTel integration with Azure Monitor |

---

## 12. 功能成熟度矩陣

### 成熟度定義

| 等級 | 名稱 | 定義 |
|------|------|------|
| L0 | Stub | 僅有 API 外殼，無真實業務邏輯 |
| L1 | Prototype | 基本功能完成但使用 in-memory 儲存 |
| L2 | Functional | 功能完整，有部分持久化，可用於開發/測試 |
| L3 | Production-Ready | 完整持久化、錯誤處理、安全控制 |
| L4 | Enterprise | L3 + 監控、自動擴展、災難恢復 |

### 按類別成熟度

| 類別 | 成熟度 | 理由 |
|------|--------|------|
| A. Agent 編排 | **L2** | 功能完整，MAF 合規，但大量 in-memory storage |
| B. 人機協作 | **L2** | 風險引擎完整，checkpoint 支援多後端，但預設 in-memory |
| C. 狀態與記憶 | **L3** | Sessions 使用 PostgreSQL + Redis，mem0 三層記憶架構 |
| D. 前端介面 | **L2** | 功能齊全，但 10 頁面有 mock fallback，2 個 placeholder |
| E. 連接與整合 | **L2-L3** | MCP 超額完成 (L3)，Claude SDK 完整 (L2)，A2A in-memory (L1) |
| F. 智能決策 | **L2-L3** | 三層路由使用真實 LLM (L3)，Autonomous API stub (L0) |
| G. 可觀測性 | **L1** | Audit/DevUI 為 in-memory (L1)，3 個 API stub 未接通 (L0) |
| H. Agent Swarm | **L2** | 完整功能 + 前端視覺化，optional Redis |
| I. 安全 | **L2** | JWT + RBAC 完成，但 sandbox 為模擬，rate limiter in-memory |

### 成熟度分布

```
L0 (Stub):      ████ 4 功能 (API stubs: F7-API, G3-API, G4-API, G5-API)
L1 (Prototype):  ██████████ 10 功能 (in-memory only: G1, G2, E6, 等)
L2 (Functional): ████████████████████████████████████████ 40 功能
L3 (Prod-Ready): ████████████████ 16 功能 (Sessions, Workflows, MCP, Auth, 等)
L4 (Enterprise): 0 功能
```

### Top 10 已知問題 (按影響力排序)

| Rank | ID | 問題 | 嚴重度 | 影響範圍 |
|------|-----|------|--------|----------|
| 1 | C-01 | In-memory storage 跨 20+ 模組 | CRITICAL | 全域 |
| 2 | H-03 | Global singleton anti-pattern | HIGH | 10+ 模組 |
| 3 | C-02 | Correlation API routes 100% mock | CRITICAL | G4 |
| 4 | C-04 | Root cause API routes 100% mock | CRITICAL | G5 |
| 5 | C-07 | SQL injection via f-string | CRITICAL | 2 stores |
| 6 | C-08 | API key prefix 暴露在 AG-UI | CRITICAL | E5 |
| 7 | H-15 | 缺少 React Error Boundaries | HIGH | 5+ 組件 |
| 8 | H-08 | 前端靜默 mock 降級 | HIGH | 10 頁面 |
| 9 | H-06 | MCP AuditLogger 未接線 | HIGH | 8 servers |
| 10 | M-01 | `datetime.utcnow()` 已棄用 | MEDIUM | 6+ files |

### 風險區域摘要

| 風險 | 嚴重度 | 影響功能 |
|------|--------|----------|
| In-memory storage (重啟資料遺失) | HIGH | A5, A6, A7, B1, B2, G1, G2 API routes |
| API stubs 未接通真實整合層 | MEDIUM | F7, G3, G4, G5 |
| 前端 mock fallbacks | MEDIUM | D1-D4, D11 (10 pages) |
| ServiceNow 僅 UAT | LOW | E1 |
| A2A Protocol in-memory | LOW | E6 |
| Rate limiter in-memory | LOW | I2 |

### 問題統計

| 嚴重度 | 數量 | 說明 |
|--------|------|------|
| CRITICAL | 8 | In-memory, mock APIs, SQL injection, API key exposure |
| HIGH | 16 | Singleton, mock fallbacks, missing RBAC, Error Boundaries |
| MEDIUM | 22 | Deprecated APIs, code duplication, console.log leaks |
| LOW | 16 | UI inconsistencies, unused variables, filename conventions |
| **合計** | **62** | 來自 22 份 Agent 報告去重 |

---

## 13. 功能整合分析

### 13.1 Mock 類統計

V8 分析發現生產代碼中存在大量 Mock 類別，混淆生產代碼與測試代碼邊界：

| 位置 | Mock 類別 | 數量 |
|------|----------|------|
| orchestration/ | MockSemanticRouter, MockBusinessIntentRouter, MockLLMClassifier, MockCompletenessChecker, MockUserInputHandler, MockServiceNowHandler, MockPrometheusHandler, MockBaseHandler, MockSchemaValidator, MockInputGateway, MockNotificationService, MockQuestionGenerator, MockLLMClient (含嵌套 MockContent+MockResponse), MockGuidedDialogEngine, MockConversationContextManager | 17 |
| llm/ | MockLLMService | 1 |
| agent_framework/ | _MockGroupChatWorkflow, Mock fallbacks in nested_workflow, magentic | 3+ |

**風險**: 多個 Mock class 透過 `__init__.py` 匯出為公開 API，在生產環境中可能被錯誤引用。LLMClassifier init 失敗時靜默降級至 mock (F6 fallback pattern)。

### 13.2 InMemory 存儲風險矩陣

V8 深度分析發現 **20+ 個模組** 使用 in-memory 存儲，重啟後資料遺失：

| Class / Pattern | 位置 | 影響功能 | 風險等級 |
|----------------|------|----------|---------|
| `InMemoryApprovalStorage` | `hitl/controller.py` | B6 HITL Approval | CRITICAL |
| `InMemoryCheckpointStorage` | `hybrid/switching/switcher.py` | B4 Framework Switching | HIGH |
| `InMemoryCheckpointStorage` | `agent_framework/checkpoint.py` | A11+ Checkpoint | HIGH |
| `InMemoryThreadRepository` | `ag_ui/thread/storage.py` | E5 AG-UI Threads | HIGH |
| `InMemoryDialogSessionStorage` | `guided_dialog/context_manager.py` | F4 GuidedDialog | MEDIUM |
| `InMemoryTransport` | `mcp/core/transport.py` | E2 MCP Transport | MEDIUM |
| `InMemoryAuditStorage` | `mcp/security/audit.py` | I4 MCP Audit | MEDIUM |
| Module-level dicts | `builders/magentic.py`, `concurrent.py`, etc. | A5-A8 Plans/Decisions | HIGH |
| `_dialog_sessions` dict | `guided_dialog/engine.py` | F4 Dialog Sessions | MEDIUM |
| AuditLogger list | `domain/audit/logger.py` | G1 Audit Logging | CRITICAL |
| ExecutionTracer dict | `domain/devtools/tracer.py` | G2 DevUI Tracing | HIGH |
| A2A agent registry | `integrations/a2a/` | E6 A2A Protocol | MEDIUM |
| Classification cache | `intent_router/` | F3, F6 Routing Cache | LOW |
| n8n config/callbacks | `integrations/n8n/` | E7 n8n Integration | LOW |

### 13.3 SPLIT 狀態分析 (V8 新增)

V8 新發現 "SPLIT" 模式：整合層完成但 API 路由仍為 stub。以下 4 個功能存在此問題：

| 功能 | API 層狀態 | 整合層狀態 | 差距描述 |
|------|-----------|-----------|----------|
| F7 Claude Autonomous | ❌ STUB (379 LOC, 100% mock) | ✅ COMPLETE (7 files, ~2,587 LOC) | API 生成假步驟 `["analyze", "plan", ...]`，無 SDK 整合 |
| G3 Patrol Monitoring | ❌ STUB (9 endpoints, hardcoded) | ✅ COMPLETE (11 files, 5 real checks) | API 使用 `time.sleep()` 阻塞 async handler |
| G4 Event Correlation | ❌ STUB (7 endpoints, uuid4() + mock) | ✅ COMPLETE (Sprint 130 修復) | 整合層已使用 Azure Monitor REST API |
| G5 Root Cause Analysis | ❌ STUB (4 endpoints, hardcoded) | ✅ COMPLETE (Sprint 130 修復) | 整合層有 15 真實 seed cases + CaseMatcher |

**修復方式**: 將 API 路由的 mock response 替換為 `await integration_service.method()` 呼叫。

### 13.4 九大能力矩陣

| 能力 | 成熟度 | 功能數 | 實現率 | 主要風險 |
|------|--------|--------|--------|----------|
| A. 多框架代理協作 | L2 Functional | 16 | 100% | In-memory storage; MAF 為 preview |
| B. 人機協作 | L2 Functional | 7 | 100% | InMemoryApprovalStorage 為預設; checkpoint 多系統 |
| C. 狀態與記憶 | L3 Prod-Ready | 5 | 100% | Sessions 使用 PostgreSQL+Redis (最成熟) |
| D. 前端介面 | L2 Functional | 11 | 100% | 10 頁面靜默 Mock fallback; 2 placeholder |
| E. 連接與整合 | L2-L3 Mixed | 8 | 87.5% | MCP 超額完成 (L3); A2A in-memory (L1) |
| F. 智能決策 | L2-L3 Mixed | 7 | 85.7% | 三層路由使用真實 LLM (L3); Autonomous API stub (L0) |
| G. 可觀測性 | L1 Prototype | 5 | 40% 完整 | Audit/DevUI in-memory; 3 API stub 未接通 |
| H. Agent Swarm | L2 Functional | 4 | 100% | 完整功能 + 前端視覺化 + optional Redis |
| I. 安全 | L2 Functional | 4 | 100% | JWT 完成但 sandbox 為模擬; rate limiter in-memory |

### 13.5 安全風險評估

| 風險 | 嚴重度 | 證據 |
|------|--------|------|
| **JWT secret 硬編碼** | CRITICAL | `"change-this-to-a-secure-random-string"` in `core/auth.py` |
| **SQL injection via f-string** | CRITICAL | 2 個 store 使用 f-string 組合 SQL (C-07) |
| **API key prefix 暴露** | CRITICAL | AG-UI event stream 中包含 API key 前綴 (C-08) |
| **缺少 RBAC 角色檢查** | HIGH | protected_router 存在但無角色權限 (H-01) |
| **MCP Permission 預設 "log"** | HIGH | dev/test 環境自動授予 ADMIN (H-07) |
| **Shell/SSH 白名單僅記錄** | HIGH | 危險命令被記錄但不被阻止 (H-12, H-13) |
| **Rate limiter in-memory** | HIGH | 重啟後 rate limit 計數器歸零 (H-14) |
| **缺少 React Error Boundaries** | HIGH | 5+ 組件缺少錯誤邊界 (H-15) |
| **Sandbox 為模擬** | MEDIUM | Process-level 非真實容器隔離 (H-09) |
| **CORS 允許所有方法/標頭** | MEDIUM | `allow_methods=["*"]`, `allow_headers=["*"]` |

---

## 14. V7 → V8 變更記錄

### 14.1 新增功能 (V8 vs V7)

| 功能 | 類別 | Sprint | 說明 |
|------|------|--------|------|
| D10 ReactFlow Workflow DAG | 前端 | S133 | Phase 34 新增視覺化 DAG 編輯器 |
| D11 Agent Templates | 前端 | S4 | V7 未追蹤，V8 獨立列出 |
| E7 n8n Integration | 連接 | S82+ | V7 未獨立列出 |
| E8 InputGateway | 連接 | S95 | V7 列為連接類別子功能 |
| I1-I4 安全能力 (4) | 安全 | S39-S113 | V8 新增獨立安全類別 |

### 14.2 類別調整

| V7 | V8 | 說明 |
|----|-----|------|
| 8 類別, 64 功能 | 9 類別, 70 功能 | 新增 I. 安全能力類別 |
| Agent Swarm: 6 功能 | Agent Swarm: 4 功能 | 精簡合併為 4 個核心功能 |
| 前端: 8 功能 | 前端: 11 功能 | 新增 D10, D11; 重新分類 |
| 無 Phase 25 追蹤 | Phase 25: 4 功能 (已延後) | 明確追蹤已延後的 K8s/生產擴展 |

### 14.3 Sprint 130 重大修復

V7 正確標記 `correlation/` 和 `rootcause/` 為 STUB (假/硬編碼資料)。Sprint 130 修復了兩個模組的**整合層**：

| 模組 | V7 狀態 | V8 整合層狀態 | V8 API 層狀態 | 說明 |
|------|---------|-------------|-------------|------|
| correlation/ | ⚠️ 假資料 | ✅ COMPLETE | ❌ STUB | EventDataSource + Azure Monitor/App Insights |
| rootcause/ | ⚠️ 硬編碼 | ✅ COMPLETE | ❌ STUB | CaseRepository + 15 seed cases + CaseMatcher |

> **V8 新發現**: V7 未區分 API 層和整合層。V8 揭示 "SPLIT" 模式：整合層已修復但 API 路由仍為 stub。

### 14.4 Sprint 132 架構重構

| 變更 | 說明 |
|------|------|
| HybridOrchestratorV2 | God Object (1,254 LOC) 分解為 OrchestratorMediator + 6 Handler |
| Mediator Pattern | RoutingHandler, DialogHandler, ApprovalHandler, ExecutionHandler, ContextHandler, ObservabilityHandler |
| 向後相容 | orchestrator_v2.py 保留為 facade，委託至 Mediator |

### 14.5 V8 分析方法論升級

| 指標 | V7 | V8 | 說明 |
|------|----|----|------|
| 分析 Agent 數 | 5+3 | 22+3 | 4.4x 增加 |
| 分析報告 | 未明確 | 19 份 Phase 3 + 3 份 Phase 4 | 結構化多階段分析 |
| 問題發現 | 12 | 62 | 5.2x 增加 (深度分析) |
| 功能驗證 | 64 | 70 計劃 + 15 計劃外 | 更完整的功能追蹤 |
| 代碼覆蓋 | 部分 AST | 全量源代碼閱讀 | 每行代碼均有 Agent 閱讀 |

---

## 15. 端到端場景

### 場景一：IT 事件處理 (三層路由 + HITL + 並行執行)

```
使用者：「ETL Pipeline 在生產環境出錯了，影響了三個下游系統」

┌──────────────────────────────────────────────────────────────┐
│  IT 事件處理流程 (涉及 16+ 功能)                                 │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  User Input (UnifiedChat D6)                                   │
│      │                                                         │
│      ▼  [E8 InputGateway → UserInputHandler]                   │
│  來源識別: USER                                                │
│      │                                                         │
│      ▼  [F3 Three-tier IntentRouter]                           │
│      ├── F3/Tier1 PatternMatcher: "ETL" + "生產" → INCIDENT   │
│      │   (< 10ms, confidence 0.95 >= 0.90 → 直接返回)          │
│      │                                                         │
│      ▼  [F5 BusinessIntentRouter → CompletenessChecker]        │
│  is_sufficient: true (有環境+影響範圍)                          │
│      │                                                         │
│      ▼  [B3 RiskAssessor — 7 維度評估]                         │
│  base: INCIDENT=0.8 + 生產環境+0.3 + 影響系統>3 → CRITICAL    │
│      │                                                         │
│      ▼  [B6 HITLController → Teams Notification]               │
│  approval_type="multi" → 發送 Teams Adaptive Card              │
│      │                                                         │
│      ▼  (等待審批, timeout 30 min)                              │
│      │                                                         │
│      ▼  [B4 ModeSwitcher / FrameworkSelector]                   │
│  INCIDENT + 結構化任務 → MAF (WORKFLOW_MODE)                    │
│      │                                                         │
│      ▼  [A5 ConcurrentBuilder — 4 並行 Worker]                 │
│      ├── Worker 1: 診斷 ETL 故障                               │
│      ├── Worker 2: 檢查下游系統狀態                             │
│      ├── Worker 3: 備份受影響數據                               │
│      └── Worker 4: 準備修復方案                                 │
│                                                                │
│  涉及功能: A5, B3, B4, B6, C1, D6, E8, F3, F5               │
│  橫跨 7 個架構層級 (L1, L2, L4, L5, L6, L9, L10)             │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

**V8 路徑驗證**:
- ✅ InputGateway → IntentRouter → RiskAssessor → HITLController 路徑完整
- ✅ Sprint 130 修復了 Correlation/RootCause 整合層，可用於事件分析
- ⚠️ API 路由層 (G3-G5) 仍為 STUB，需手動連接整合層
- ⚠️ Swarm 不在主 HybridOrchestratorV2.execute_with_routing() 流程中

### 場景二：Agent Swarm 多專家協作分析

```
使用者：「分析我們的安全基礎設施，識別潛在漏洞」

┌──────────────────────────────────────────────────────────────┐
│  Swarm 多 Agent 協作場景                                        │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  User Input                                                    │
│      │                                                         │
│      ▼  [E8 InputGateway → F3 PatternMatcher]                  │
│  IT_SECURITY_AUDIT (confidence 0.95)                          │
│      │                                                         │
│      ▼  [B3 RiskAssessor → B6 HITLController]                  │
│  Risk: HIGH → 需要審批                                        │
│      │                                                         │
│      ▼  [B4 Hybrid Switching — 選擇 Swarm 模式]               │
│  複雜分析 → Claude SDK + Concurrent + Swarm 模式              │
│      │                                                         │
│      ▼  [H1 SwarmTracker — 建立群集]                           │
│  SwarmMode: PARALLEL, 4 Workers                               │
│      │                                                         │
│      ├──▶ Worker 1: ANALYST (網路安全) [H2 SSE: WorkerStarted] │
│      ├──▶ Worker 2: ANALYST (權限審計) [H2 SSE: WorkerStarted] │
│      ├──▶ Worker 3: REVIEWER (合規檢查) [H2 SSE: WorkerStarted]│
│      └──▶ Worker 4: CODER (修復建議)   [H2 SSE: WorkerStarted] │
│           │         │         │         │                      │
│           ▼         ▼         ▼         ▼                      │
│      [H1 SwarmIntegrationBridge → ClaudeCoordinator]           │
│           │         │         │         │                      │
│      [H2 SSE: WorkerThinking, WorkerToolCall, WorkerProgress]  │
│           │         │         │         │                      │
│           └────┬────┴────┬────┘         │                      │
│                ▼         ▼              ▼                      │
│      [H3 Swarm Frontend Panel 即時顯示]                        │
│      • WorkerCard × 4 (各 Worker 狀態)                        │
│      • OverallProgress (整體進度)                              │
│      • ExtendedThinkingPanel (思考過程)                        │
│      • ToolCallsPanel (工具調用)                               │
│                                                                │
│  涉及功能: B3, B6, B4, E8, F3, H1-H4                         │
│  橫跨 6 個架構層級 (L1, L2, L4, L5, L7, L9)                 │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

**V8 重要發現**: Swarm 目前不整合在 `HybridOrchestratorV2.execute_with_routing()` 的主流程中。它透過獨立的 Demo API (`/api/v1/swarm/demo/start`) 觸發，使用模擬進度。真實的 Swarm 執行需要 `ClaudeCoordinator`（在 `claude_sdk/orchestrator`）作為上游呼叫者。Sprint 132 的 Mediator Pattern 重構為未來整合提供了更好的架構基礎。

### 場景三：三層路由降級處理

```
使用者：「幫我處理一下這個問題」(模糊輸入)

┌──────────────────────────────────────────────────────────────┐
│  模糊輸入的三層路由降級 + 引導對話                                │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  User Input                                                    │
│      │                                                         │
│      ▼  [E8 InputGateway]                                      │
│  來源識別: USER                                                │
│      │                                                         │
│      ▼  [F3/Tier1 PatternMatcher]                              │
│  結果: 無匹配 (confidence < 0.90)                              │
│      │                                                         │
│      ▼  [F3/Tier2 SemanticRouter — Azure OpenAI Embeddings]    │
│  結果: 最高 similarity 0.72 < 0.85 → 降級                     │
│      │                                                         │
│      ▼  [F3/Tier3 LLMClassifier — Azure OpenAI/Claude]        │
│  結果: QUERY (confidence 0.65), is_complete: false             │
│      │                                                         │
│      ▼  [F4 GuidedDialogEngine]                                │
│  狀態: INITIAL → GATHERING                                     │
│  產生引導問題 (繁體中文 template):                              │
│  「請問您想處理的是什麼類型的問題？(事件/服務請求/變更/查詢)」    │
│      │                                                         │
│      ▼  [使用者回覆：「是一個權限問題」]                         │
│      │                                                         │
│      ▼  [F4 規則式欄位提取 (不重新呼叫 LLM)]                   │
│  增量更新: sub_intent = ACCESS_MANAGEMENT                      │
│  狀態: GATHERING → COMPLETE                                    │
│      │                                                         │
│      ▼  繼續正常處理流程...                                     │
│                                                                │
│  涉及功能: E8, F3 (全三層), F4, F5, F6                        │
│  關鍵設計: 後續回合使用規則式提取，避免重複 LLM 呼叫            │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 附錄 A: 驗證報告來源追溯表

### Phase 3 分析報告 (19 份)

| 報告 | Agent | 範圍 | 檔案數 | LOC |
|------|-------|------|--------|-----|
| phase3a-api-layer-part1 | A1 | API: a2a → correlation (14 modules) | 46 | 15,868 |
| phase3a-api-layer-part2 | A2 | API: dashboard → nested (11 modules) | — | — |
| phase3a-api-layer-part3 | A3 | API: orchestration → workflows (14 modules) | 48 | ~8,900 |
| phase3b-domain-part1 | B1 | Domain: agents → files (8 modules) | 28 | ~8,654 |
| phase3b-domain-part2 | B2 | Domain: learning → workflows (10 modules) | — | — |
| phase3b-domain-part3 | B3 | Domain: sessions (critical) + cross-ref | 33 | ~12,272 |
| phase3c-af-part1 | C1 | Integration: agent_framework builders + core | 57 | ~18,000+ |
| phase3c-af-part2 | C2 | Integration: agent_framework remaining | 20 | ~3,200 |
| phase3c-hybrid-part1 | C3 | Integration: hybrid (intent, context, risk) | 69 | ~21,000 |
| phase3c-hybrid-part2 | C4 | Integration: hybrid (switching, execution, checkpoint) | — | — |
| phase3c-orch-part1 | C5 | Integration: orchestration (routing, dialog) | ~40 | ~12,000+ |
| phase3c-orch-part2 | C6 | Integration: orchestration (risk, HITL, metrics) | — | — |
| phase3c-claude-sdk | C7 | Integration: claude_sdk (10 sub-features) | ~40 | ~12,000+ |
| phase3c-mcp-part1 | C8 | Integration: MCP core + security | — | — |
| phase3c-mcp-part2 | C9 | Integration: MCP 8 servers | — | ~12,400 |
| phase3c-ag-ui | C10 | Integration: AG-UI protocol | 24 | ~7,554 |
| phase3c-remaining | C11 | Integration: 12 remaining modules | ~64 | — |
| phase3d-core-infra | D1 | Core + Infrastructure + main.py | 76 | ~7,300 |
| phase3e-frontend-part1 | E1 | Frontend: pages (41 files) | 41 | ~10,200 |
| phase3e-frontend-part2 | E2 | Frontend: components (unified-chat, agent-swarm, ag-ui) | 82 | ~13,800 |
| phase3e-frontend-part3 | E3 | Frontend: shared components, workflow-editor, UI | — | — |
| phase3e-frontend-part4 | E4 | Frontend: hooks, stores, API, utils, types | — | — |

### Phase 4 驗證報告 (3 份)

| 報告 | 用途 |
|------|------|
| phase4-validation-plan-vs-reality | 70 功能逐一驗證 (計劃 vs 實際) |
| phase4-validation-issue-registry | 62 問題去重分類 (CRITICAL/HIGH/MEDIUM/LOW) |
| phase4-validation-e2e-flows | 端到端場景驗證 |

### 功能到報告對照

| 功能 ID | 主要驗證報告 |
|---------|------------|
| A1-A10 | phase3a-api (part1-3), phase3b-domain-part1, phase3c-af-part1 |
| A11-A16 | phase3c-af-part1 (compliance audit) |
| B1-B2 | phase3b-domain-part1, phase3c-af-part1 |
| B3-B5 | phase3c-hybrid-part1, phase3c-hybrid-part2 |
| B6-B7 | phase3c-orch-part2, phase3a-api-part3 |
| C1-C2 | phase3b-domain-part3 |
| C3 | phase3d-core-infra |
| C4-C5 | phase3c-remaining |
| D1-D11 | phase3e-frontend (part1-4) |
| E1 | phase3a-api-part1 |
| E2 | phase3c-mcp-part1, phase3c-mcp-part2 |
| E3 | phase3c-claude-sdk |
| E4 | phase3c-hybrid-part1, phase3c-hybrid-part2 |
| E5 | phase3c-ag-ui |
| E6 | phase3c-remaining, phase3a-api-part1 |
| E7-E8 | phase3c-remaining, phase3c-orch-part1 |
| F1 | phase3c-remaining |
| F2 | phase3c-hybrid-part1 |
| F3-F6 | phase3c-orch-part1 |
| F7 | phase3a-api-part1 (API), phase3c-claude-sdk (Integration) |
| G1-G2 | phase3b-domain-part1 |
| G3-G5 | phase3a-api (part1/3) + phase3c-remaining |
| H1-H4 | phase3c-remaining, phase3a-api-part3, phase3e-frontend (part2-3) |
| I1-I2 | phase3d-core-infra |
| I3 | phase3d-core-infra, phase3a-api-part3 |
| I4 | phase3c-mcp-part1 |

---

## 附錄 B: 代碼庫統計

### Backend 層級統計

| 層級 | 目錄 | .py 檔案數 | LOC (估計) |
|------|------|-----------|-----------|
| API Routes | `api/v1/` | 94 | ~24,700 |
| Domain | `domain/` | 80+ | ~30,000+ |
| Integration: Agent Framework | `integrations/agent_framework/` | 57 | ~18,000+ |
| Integration: Hybrid | `integrations/hybrid/` | 69 | ~21,000 |
| Integration: Orchestration | `integrations/orchestration/` | ~40 | ~12,000+ |
| Integration: Claude SDK | `integrations/claude_sdk/` | ~40 | ~12,000+ |
| Integration: MCP | `integrations/mcp/` | — | ~12,400 |
| Integration: AG-UI | `integrations/ag_ui/` | 24 | ~7,554 |
| Integration: Remaining (12) | `integrations/*` | ~64 | — |
| Core + Infrastructure | `core/`, `infrastructure/` | 76 | ~7,300 |
| **Backend 合計** | — | **~540+** | **~280,000+** |

### Frontend 層級統計

| 類別 | 檔案數 | LOC (估計) |
|------|--------|-----------|
| Pages | 41 | ~10,200 |
| Components (unified-chat) | 31 | ~6,200 |
| Components (agent-swarm) | 33 | ~4,700 |
| Components (ag-ui) | 12 | ~2,900 |
| Components (workflow-editor) | 10+ | ~1,500 |
| Components (DevUI) | 15 | ~2,000 |
| Components (UI/shared) | 30+ | ~3,000 |
| Hooks | 17 | ~2,000 |
| Stores | 5+ | ~1,000 |
| API/Types/Utils | 20+ | ~3,000 |
| **Frontend 合計** | **~250+** | **~60,000+** |

### 數據持久化分布

| 類型 | 模組數 | 說明 |
|------|--------|------|
| PostgreSQL (完整 DB) | 4 | agents, sessions, workflows, auth |
| Redis Cache | 3 | sessions (cache), LLM cache, switch checkpoints |
| Real External Services | 8 | MCP servers (Azure, LDAP, SSH, etc.) |
| InMemory Only | 20+ | audit, devtools, a2a, approval, dialog sessions, etc. |
| Filesystem | 2 | file uploads, filesystem sandbox |
| Mock/Stub (API layer) | 4 | autonomous, correlation, patrol, rootcause (API routes) |

### API 端點分布 (Part 1-3 合計)

| 模組 | 端點數 | 評估 |
|------|--------|------|
| orchestration/ | 28 | MOSTLY COMPLETE |
| planning/ | ~46 | COMPLETE |
| claude_sdk/ | ~40 | COMPLETE |
| groupchat/ | 42 | COMPLETE (in-memory) |
| ag_ui/ | ~30 | COMPLETE |
| sessions/ | ~20 | MOSTLY COMPLETE |
| handoff/ | 14 | COMPLETE |
| agents/ | ~12 | COMPLETE |
| workflows/ | 12 | COMPLETE |
| routing/ | 14 | COMPLETE |
| versioning/ | 14 | COMPLETE |
| notifications/ | 11 | COMPLETE |
| performance/ | 11 | MOSTLY COMPLETE |
| templates/ | 11 | COMPLETE |
| prompts/ | 11 | COMPLETE |
| patrol/ | 9 | STUB |
| triggers/ | 9 | COMPLETE |
| swarm/ | 8 | COMPLETE |
| audit/ | 13 | COMPLETE (in-memory) |
| devtools/ | 12 | COMPLETE (in-memory) |
| sandbox/ | 6 | COMPLETE |
| rootcause/ | 4 | STUB |
| **合計** | **~550+** | — |

---

---

## 更新歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 8.1 | 2026-03-16 | **MAF RC4 升級反映**: L6 Builder import 路徑遷移至 `agent_framework.orchestrations` (4 Builders); constructor API fluent→kwarg; 4 組類別重命名別名; L7 Claude SDK 更新 (`anthropic>=0.84.0`, 模型 ID `claude-haiku-4-5-20251001`, Extended Thinking header 更新); A5-A8 依賴路徑更新; A11-A16 遷移記錄; E3 SDK 更新記錄; 新增 R8 GA 升級風險追蹤 |
| 8.0 | 2026-03-15 | **V8 全面升級**: 22+3 Agent 全量源代碼閱讀；功能範圍從 64 擴展至 **70 計劃 + 15 計劃外**；新增 I. 安全能力類別 (9→9 類別)；新增 SPLIT 狀態追蹤 (4 功能)；Backend LOC ~228K→**~280K+**；問題發現 12→**62**；新增端到端場景驗證；新增 Mock/InMemory/安全風險系統分析；Sprint 130 Correlation/RootCause 整合層修復；Sprint 132 Mediator Pattern 架構重構；Sprint 133 ReactFlow DAG 視覺化 |
| 7.0 | 2026-02-11 | **格式重整 + 數據修正版**：以 V3 繁體中文格式重寫 V6 內容；Backend LOC 從 ~130K **修正為 ~228.7K**；端點 530→528；>800 行檔案 57→58；Checkpoint 系統 2→4；新增 Frontend LOC 47,630；新增安全風險評估章節；新增端到端流程驗證；8+3 Agent 並行驗證 |
| 6.0 | 2026-02-11 | 全面更新：5 Agent Team 並行驗證；64 功能維持不變；修正 V5 的 11 項錯誤；新增安全指標 |
| 3.0 | 2026-02-09 | 全面重寫：5 Agent 並行深度驗證；擴展至 65 功能 (+6 Swarm) |
| 2.1 | 2026-01-28 | 補回 V1 架構圖示 |
| 2.0 | 2026-01-28 | 全面重寫：擴展至 59 功能 |
| 1.0 | 2025-12-01 | 初始版本 - 50 功能 |

---

*本文件由 V8 分析團隊 (22 分析 Agent + 3 交叉驗證 Agent) 基於全量源代碼閱讀生成。*
*每個功能的狀態均有對應的 Phase 3 Agent 報告作為驗證來源，可追溯至具體的檔案路徑與行號。*
*所有資料來源為 Phase 3 分析報告 (19 份) 和 Phase 4 驗證報告 (3 份)，V7 僅用作格式參考。*
*V8.1 更新 (2026-03-16): MAF RC4 升級後的 import 路徑、constructor API、類別重命名及 Claude SDK 同步更新。驗證來源: `sdk-version-gap/POST-UPGRADE-Verification-Consensus.md`。*
