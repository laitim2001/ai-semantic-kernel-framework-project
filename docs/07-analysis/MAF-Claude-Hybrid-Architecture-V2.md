# 智能體編排平台：MAF + Claude Agent SDK 混合架構實現

> **文件版本**: 2.1
> **最後更新**: 2026-01-28
> **定位**: Agent Orchestration Platform (智能體編排平台)
> **狀態**: Phase 28 已完成 (99 Sprints, 2189 Story Points)
> **代碼庫規模**: ~120,000+ LOC (Backend), 130+ .tsx (Frontend)

---

## 實現狀態總覽

> **重要說明**: 本文件是 V1 (企業 IT 事件智能處理平台) 的全面更新。V2 重新定位為**智能體編排平台** --- 一個透過人機互動協調智能體集群處理複雜、不可預測任務的平台，與 n8n/Power Automate 等確定性工作流工具形成互補而非競爭關係。

### 各層實現狀態

| 層級 | 組件 | 檔案數 | LOC | 狀態 |
|------|------|--------|-----|------|
| **Layer 1** | Frontend | 130+ .tsx | 36 pages | ✅ REAL |
| **Layer 2** | API Layer | 56 route files | 526 endpoints | ✅ REAL |
| **Layer 3** | AG-UI Protocol | 23 files | ~7,984 | ✅ REAL |
| **Layer 4** | Phase 28 Orchestration | 40 files | ~13,795 | ✅ REAL - 含測試用 Mock |
| **Layer 5** | Hybrid Layer | 60 files | ~17,872 | ✅ REAL |
| **Layer 6** | MAF Builder Layer | 23 files | ~20,011 | ✅ REAL - 最成熟的整合層 |
| **Layer 7** | Claude SDK Layer | 47 files | ~12,267 | ✅ REAL |
| **Layer 8** | MCP Layer | 43 files | ~10,528 | ✅ REAL |
| **Layer 9** | Supporting Integrations | 36 files | ~8,640 | ⚠️ 部分完成 |
| **Layer 10** | Domain Layer | 114 files | ~39,941 | ✅ REAL |
| **Layer 11** | Infrastructure | 23 files | ~3,101 | ⚠️ RabbitMQ 為空殼 |
| | **總計** | **~600+ files** | **~120,000+ (Backend)** | |

### 已知問題

| # | 問題 | 影響 | 嚴重度 |
|---|------|------|--------|
| 1 | Messaging/RabbitMQ 整合為空 (`__init__.py` only) | 無法使用訊息佇列 | 中 |
| 2 | ContextSynchronizer 使用記憶體狀態 (無鎖、無 Redis) | 並行安全風險 | 高 |
| 3 | 單 Uvicorn Worker 預設 | 生產環境效能瓶頸 | 高 |
| 4 | Mock 類與生產代碼並置 | 代碼衛生問題 | 低 |
| 5 | Stub 密度 ~1.1% | 正常，活躍開發期可接受 | 低 |

---

## 執行摘要

IPA Platform 是一個**智能體編排平台 (Agent Orchestration Platform)**，透過 Microsoft Agent Framework (MAF) 與 Claude Agent SDK 的混合架構，協調智能體集群處理需要**判斷力、專業知識與人機互動**的複雜任務。

平台核心理念：

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   IPA Platform = Agent Orchestration Platform                        │
│   ═══════════════════════════════════════════                        │
│                                                                      │
│   「不是 n8n/Power Automate 的替代品，                               │
│     而是處理 n8n 無法處理的那些任務」                                │
│                                                                      │
│   MAF (Microsoft Agent Framework)                                    │
│   ─────────────────────────────────                                  │
│   • 結構化編排與治理                                                 │
│   • 多 Agent 協作模式 (Handoff, GroupChat, Magentic)                │
│   • 檢查點與狀態持久化                                               │
│   • 企業級審計追蹤                                                   │
│                                                                      │
│   Claude Agent SDK                                                   │
│   ─────────────────                                                  │
│   • 自主執行與深度推理                                               │
│   • Agentic Loop (自主迭代直到完成)                                  │
│   • Extended Thinking (複雜分析)                                     │
│   • 並行 Worker 執行                                                 │
│                                                                      │
│   AG-UI Protocol                                                     │
│   ──────────────                                                     │
│   • 即時 Agent 狀態串流                                              │
│   • Human-in-the-Loop 審批                                          │
│   • 思考過程可視化                                                   │
│                                                                      │
│   MCP (Model Context Protocol)                                       │
│   ─────────────────────────────                                      │
│   • 統一工具存取介面                                                 │
│   • 5 個 MCP Server (Azure, Shell, Filesystem, SSH, LDAP)           │
│   • 28 種權限模式、16 種審計模式                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 關鍵數據

- **Backend**: ~120,000+ LOC across 200+ integration files + 114 domain files
- **API**: 526 endpoints across 56 route files, 30+ modules
- **Frontend**: 130+ .tsx files, 36 pages, 80 components, 15 custom hooks
- **已完成**: 28 Phases, 99 Sprints, 2189 Story Points
- **專案啟動**: 2025-11-14
- **技術棧**: FastAPI + React 18 + PostgreSQL + Redis + RabbitMQ (planned)

---

## 1. 平台定位與價值主張

### 1.1 為什麼是「智能體編排平台」而非「工作流自動化」

V1 文件將本平台定位為「企業 IT 事件智能處理平台」，這個定位過於狹隘。實際上，平台的核心能力是**協調智能體集群**，適用於任何需要 AI 判斷力的複雜場景。

```
任務特徵分類：

┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   可預測、確定性任務                    不可預測、需判斷力的任務      │
│   ════════════════════                  ════════════════════════      │
│                                                                      │
│   「如果 X 則 Y」                       「分析情況，決定最佳方案」    │
│                                                                      │
│   • 新員工入職流程                      • 根因分析：為什麼系統掛了？ │
│   • 固定格式報表產出                    • 安全事件：這是否為攻擊？   │
│   • 定期資料備份                        • 資源規劃：如何分配預算？   │
│   • 審批路由 (固定規則)                 • 故障排除：哪裡出了問題？   │
│                                                                      │
│        ↓                                       ↓                     │
│   n8n / Power Automate                  IPA Platform                 │
│   (工作流自動化工具)                    (智能體編排平台)             │
│                                                                      │
│   特點：                                特點：                       │
│   • 視覺化流程設計                      • Agent 自主推理             │
│   • 確定性執行                          • 多 Agent 協作             │
│   • 固定邏輯分支                        • Human-in-the-Loop         │
│   • 無需 AI 判斷                        • 可觀測的決策過程           │
│   • 成本低、速度快                      • 適應性強、可學習           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 平台獨特價值

**場景一：使用者驅動的複雜任務**

```
使用者：「APAC Glider ETL Pipeline 連續第三天失敗，日報表完全無法產出」

IPA Platform 的處理方式 (非 n8n 可以做到的)：
─────────────────────────────────────────────
1. [意圖路由] 三層路由識別：IT 故障排查 + 高優先級
2. [引導對話] Agent 追問：哪個 Pipeline？錯誤訊息？影響範圍？
3. [風險評估] 判斷風險等級：涉及生產資料 → HIGH
4. [Agent 協作]
   ├─ 診斷 Agent → 查詢 Azure Data Factory 日誌
   ├─ 分析 Agent → Extended Thinking 分析根因
   └─ 修復 Agent → 提出修復方案
5. [HITL 審批] 生產環境變更 → 人工確認
6. [執行驗證] Agent 驗證修復結果、更新工單、通知團隊
7. [學習記錄] 記錄案例，未來類似問題加速處理
```

**場景二：確定性 IT 運維 → n8n (不在本平台範疇)**

```
事件：新員工入職 → 建立帳號 → 分配權限 → 發送歡迎郵件

這是 n8n/Power Automate 的強項：
────────────────────────────────
• 固定步驟、固定邏輯
• 不需要 AI 判斷
• 成本更低、更可靠
• 本平台不與其競爭
```

### 1.3 核心價值定位

| 維度 | IPA Platform 提供的價值 | n8n 提供的價值 |
|------|------------------------|----------------|
| **智能判斷** | Agent 自主分析、推理、決策 | 無 (固定規則) |
| **多 Agent 協作** | Handoff, GroupChat, 並行 Worker | 無 |
| **人機互動** | 即時審批、引導對話、思考可視化 | 固定審批節點 |
| **不確定性處理** | 適應性推理、動態策略調整 | 無 |
| **治理可見性** | 完整決策追蹤、審計日誌 | 基礎日誌 |
| **學習能力** | 案例學習、Few-shot 改進 | 無 |
| **確定性流程** | 非核心場景 | 核心強項 |
| **視覺化設計** | 開發中 | 成熟 |

---

## 2. 完整架構設計

### 2.1 十一層架構總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IPA Platform：智能體編排平台架構 (V2)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║  Layer 1: Frontend (使用者介面)                                       ║  │
│  ║  130+ .tsx | 36 pages | 80 components                                ║  │
│  ╠═══════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                        ║  │
│  ║   React 18 + TypeScript + Vite (port 3005)                            ║  │
│  ║   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             ║  │
│  ║   │ Unified  │  │  Agent   │  │ Workflow │  │   HITL   │             ║  │
│  ║   │ Chat UI  │  │ Dashboard│  │  Editor  │  │ Approval │             ║  │
│  ║   │ (25+comp)│  │          │  │          │  │  Cards   │             ║  │
│  ║   └──────────┘  └──────────┘  └──────────┘  └──────────┘             ║  │
│  ║         │              │              │              │                 ║  │
│  ║         └──────────────┴──────────────┴──────────────┘                ║  │
│  ║                              │ Fetch API                              ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 2: API Gateway (526 endpoints, 56 route files, 30+ modules)   ║  │
│  ║  FastAPI (port 8000) + 38 API route modules                          ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 3: AG-UI Protocol (即時 Agent UI)                              ║  │
│  ║  23 files, ~7,984 LOC | AG-UI SSE Bridge                             ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 4: Input & Routing (輸入閘道 + 意圖路由)                      ║  │
│  ║  40 files, ~13,795 LOC                                                ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  InputGateway            │   BusinessIntentRouter              │  ║  │
│  ║   │  (8 files, ~2,100 LOC)  │   (12 files, ~3,200 LOC)           │  ║  │
│  ║   │                          │                                     │  ║  │
│  ║   │  • ServiceNow Handler   │   • PatternMatcher   (< 10ms)      │  ║  │
│  ║   │  • Prometheus Handler   │   • SemanticRouter   (< 100ms)     │  ║  │
│  ║   │  • UserInput Handler    │   • LLMClassifier    (< 2000ms)    │  ║  │
│  ║   │  • Schema Validator     │   • CompletenessChecker             │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  GuidedDialog (5 files) │  RiskAssessor (3 files)             │  ║  │
│  ║   │  ~3,050 LOC             │  ~1,200 LOC                         │  ║  │
│  ║   │                          │                                     │  ║  │
│  ║   │  • Dialog Engine        │  • Risk Policies                    │  ║  │
│  ║   │  • Context Manager      │  • Assessment Engine                │  ║  │
│  ║   │  • Question Generator   │                                     │  ║  │
│  ║   │  • Refinement Rules     │  HITLController (4 files, ~1,900)   │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 5: Hybrid Orchestration (混合編排層)                           ║  │
│  ║  60 files, ~17,872 LOC                                                ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │            HybridOrchestratorV2 (1,103 LOC)                   │  ║  │
│  ║   │  中央協調器 - 整合所有 Phase 28 組件                           │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │  ║  │
│  ║   │  │ Framework    │  │ Context      │  │ Unified      │         │  ║  │
│  ║   │  │ Selector     │  │ Bridge       │  │ ToolExecutor │         │  ║  │
│  ║   │  │ (7 files)    │  │ (10 files)   │  │ (5 files)    │         │  ║  │
│  ║   │  │ ~1,600 LOC   │  │ ~3,300 LOC   │  │ ~1,900 LOC   │         │  ║  │
│  ║   │  └──────────────┘  └──────────────┘  └──────────────┘         │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │  ║  │
│  ║   │  │ Risk Engine  │  │ Switching    │  │ Checkpoint   │         │  ║  │
│  ║   │  │ (8 files)    │  │ Logic        │  │ Manager      │         │  ║  │
│  ║   │  │ ~2,200 LOC   │  │ (9 files)    │  │ (9 files)    │         │  ║  │
│  ║   │  │              │  │ ~2,500 LOC   │  │ ~2,850 LOC   │         │  ║  │
│  ║   │  └──────────────┘  └──────────────┘  └──────────────┘         │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 6: MAF Builder Layer (MAF 編排模式層)                          ║  │
│  ║  23 files, ~20,011 LOC                                                ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  9+ Builders (from agent_framework import ...)                │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌────────────┐  ┌────────────┐  ┌────────────┐               │  ║  │
│  ║   │  │  Handoff   │  │ GroupChat  │  │ Concurrent │               │  ║  │
│  ║   │  │  Builder   │  │  Builder   │  │  Builder   │               │  ║  │
│  ║   │  └────────────┘  └────────────┘  └────────────┘               │  ║  │
│  ║   │  ┌────────────┐  ┌────────────┐  ┌────────────┐               │  ║  │
│  ║   │  │  Magentic  │  │  Planning  │  │  Nested    │               │  ║  │
│  ║   │  │  Builder   │  │  Builder   │  │ Workflow   │               │  ║  │
│  ║   │  └────────────┘  └────────────┘  └────────────┘               │  ║  │
│  ║   │  ┌────────────┐  ┌────────────┐  ┌────────────┐               │  ║  │
│  ║   │  │  Workflow   │  │   Agent   │  │   Code     │               │  ║  │
│  ║   │  │ Executor   │  │ Executor   │  │Interpreter │               │  ║  │
│  ║   │  └────────────┘  └────────────┘  └────────────┘               │  ║  │
│  ║   │  + handoff_hitl, handoff_policy, handoff_capability,          │  ║  │
│  ║   │    handoff_context, handoff_service, groupchat_voting,        │  ║  │
│  ║   │    groupchat_orchestrator, edge_routing, *_migration          │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 7: Claude SDK Worker Layer (Claude 自主執行層)                 ║  │
│  ║  47 files, ~12,267 LOC                                                ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  ClaudeSDKClient (AsyncAnthropic) - 171 LOC                   │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │  ║  │
│  ║   │  │ Autonomous   │  │ Hook System  │  │ Tool System  │         │  ║  │
│  ║   │  │ (7 files)    │  │ (6 files)    │  │ (6 files)    │         │  ║  │
│  ║   │  │ ~2,050 LOC   │  │ ~1,350 LOC   │  │ ~1,430 LOC   │         │  ║  │
│  ║   │  │              │  │              │  │              │         │  ║  │
│  ║   │  │ • Analyzer   │  │ • Approval   │  │ • File Tool  │         │  ║  │
│  ║   │  │ • Planner    │  │ • Audit      │  │ • Command    │         │  ║  │
│  ║   │  │ • Executor   │  │ • Rate-limit │  │ • Web Tool   │         │  ║  │
│  ║   │  │ • Verifier   │  │ • Sandbox    │  │ • Registry   │         │  ║  │
│  ║   │  │ • Retry      │  │              │  │              │         │  ║  │
│  ║   │  │ • Fallback   │  │              │  │              │         │  ║  │
│  ║   │  └──────────────┘  └──────────────┘  └──────────────┘         │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────────┐  ┌──────────────┐                           │  ║  │
│  ║   │  │ MCP Client   │  │ Orchestrator │                           │  ║  │
│  ║   │  │ (8 files)    │  │ (5 files)    │                           │  ║  │
│  ║   │  │ ~2,050 LOC   │  │ ~1,350 LOC   │                           │  ║  │
│  ║   │  │              │  │              │                           │  ║  │
│  ║   │  │ • STDIO      │  │ • Allocator  │                           │  ║  │
│  ║   │  │ • HTTP       │  │ • Coordinator│                           │  ║  │
│  ║   │  │ • Manager    │  │ • Context    │                           │  ║  │
│  ║   │  │ • Discovery  │  │              │                           │  ║  │
│  ║   │  └──────────────┘  └──────────────┘                           │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 8: MCP Tool Layer (統一工具存取層)                             ║  │
│  ║  43 files, ~10,528 LOC                                                ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  5 MCP Servers + Core Protocol + Security                     │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  ║  │
│  ║   │  │  Azure   │  │  Shell   │  │Filesystem│  │   SSH    │      │  ║  │
│  ║   │  │ (9 files)│  │ (5 files)│  │ (5 files)│  │ (5 files)│      │  ║  │
│  ║   │  │VM,Monitor│  │          │  │          │  │          │      │  ║  │
│  ║   │  │Network   │  │          │  │          │  │ ┌──────┐ │      │  ║  │
│  ║   │  │Resource  │  │          │  │          │  │ │ LDAP │ │      │  ║  │
│  ║   │  │Storage   │  │          │  │          │  │ │(5 f) │ │      │  ║  │
│  ║   │  └──────────┘  └──────────┘  └──────────┘  │ └──────┘ │      │  ║  │
│  ║   │                                             └──────────┘      │  ║  │
│  ║   │  core/ (5 files): Protocol, Transport, Client, Types         │  ║  │
│  ║   │  security/ (3 files): 28 permission patterns, 16 audit       │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  Layer 9: Observability & Governance (可觀測性與治理)                 ║  │
│  ║  OrchestrationMetrics (763 LOC) + Patrol + Audit + Memory           ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  Layer 10: Domain Layer (業務邏輯層)                                  ║  │
│  ║  114 files, ~39,941 LOC | 20 domain modules                         ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  Layer 11: Infrastructure (基礎設施)                                  ║  │
│  ║  PostgreSQL 16 | Redis 7 | RabbitMQ (planned)                        ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 資料流概覽

```
使用者輸入 / 系統事件
        │
        ▼
┌─────────────────┐
│  InputGateway   │ ← ServiceNow / Prometheus / UserInput Handler
│  (來源標準化)    │
└────────┬────────┘
         │ UnifiedRequestEnvelope
         ▼
┌─────────────────┐
│ BusinessIntent  │ ← PatternMatcher → SemanticRouter → LLMClassifier
│    Router       │    (三層瀑布式路由)
│  (意圖路由)     │
└────────┬────────┘
         │ RoutingDecision {intent, completeness, risk_hint}
         │
    ┌────┴────┐
    │ 資訊    │
    │ 足夠?   │
    └────┬────┘
    Yes  │  No → GuidedDialogEngine (引導式對話收集)
         │                │
         │       ←────────┘ (補充後重新評估)
         ▼
┌─────────────────┐
│  RiskAssessor   │ ← 風險政策評估
│  (風險評估)     │
└────────┬────────┘
         │ RiskLevel: LOW / MEDIUM / HIGH / CRITICAL
         │
    ┌────┴────┐
    │ 需要    │
    │ 審批?   │
    └────┬────┘
    No   │  Yes → HITLController → Teams Notification → 等待審批
         │                │
         │       ←────────┘ (審批通過)
         ▼
┌─────────────────────────┐
│ HybridOrchestratorV2    │ ← 中央協調器
│ ┌─────────────────────┐ │
│ │ FrameworkSelector   │ │ ← 選擇 MAF 模式 or Claude 自主
│ │ ContextBridge       │ │ ← 上下文同步
│ │ UnifiedToolExecutor │ │ ← 統一工具路由
│ │ CheckpointManager   │ │ ← 4 種存儲後端
│ └─────────────────────┘ │
└────────────┬────────────┘
             │
    ┌────────┴────────┐
    │                  │
    ▼                  ▼
┌─────────┐    ┌──────────┐
│   MAF   │    │  Claude  │
│ Builder │    │  SDK     │
│ (9+種)  │    │ Worker   │
└────┬────┘    └────┬─────┘
     │              │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  MCP Layer   │ ← 5 MCP Servers
     │  (工具執行)  │    28 permission patterns
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ AG-UI SSE    │ ← 即時串流結果到前端
     │ (結果回傳)   │
     └──────────────┘
```

---

## 3. 核心能力矩陣

### 3.1 Agent 編排能力

| 能力 | 實現方式 | 檔案位置 | 狀態 |
|------|----------|----------|------|
| **Sequential 執行** | MAF Sequential Builder | `integrations/agent_framework/builders/workflow_executor.py` | ✅ |
| **Handoff 交接** | MAF Handoff Builder + Policy + Context | `builders/handoff.py`, `handoff_policy.py`, `handoff_context.py` | ✅ |
| **GroupChat 討論** | MAF GroupChat Builder + Voting | `builders/groupchat.py`, `groupchat_voting.py` | ✅ |
| **Magentic 推理** | MAF Magentic Builder | `builders/magentic.py` | ✅ |
| **並行執行** | MAF Concurrent Builder | `builders/concurrent.py` | ✅ |
| **巢狀工作流** | MAF Nested Workflow | `builders/nested_workflow.py` | ✅ |
| **Planning 規劃** | MAF Planning Builder | `builders/planning.py` | ✅ |
| **自主執行** | Claude SDK Autonomous | `claude_sdk/autonomous/executor.py` | ✅ |
| **深度推理** | Claude Extended Thinking | `claude_sdk/autonomous/analyzer.py` | ✅ |
| **框架切換** | Switching Logic (4 triggers) | `hybrid/switching/` (9 files, ~2,500 LOC) | ✅ |

**框架切換觸發條件**:

```
FrameworkSwitcher (integrations/hybrid/switching/)
├── user_trigger.py       → 使用者明確要求切換
├── failure_trigger.py    → 當前框架執行失敗
├── resource_trigger.py   → 資源限制 (token, 時間)
└── complexity_trigger.py → 任務複雜度變化
```

### 3.2 Human-in-the-Loop 能力

| 能力 | 實現方式 | 檔案位置 | 狀態 |
|------|----------|----------|------|
| **審批請求** | HITLController + ApprovalHandler | `orchestration/hitl/controller.py`, `approval_handler.py` | ✅ |
| **Teams 通知** | Notification Service | `orchestration/hitl/notification.py` | ✅ |
| **即時審批 UI** | AG-UI HITL Components | `ag_ui/features/human_in_loop.py` | ✅ |
| **引導式對話** | GuidedDialogEngine | `orchestration/guided_dialog/engine.py` | ✅ |
| **前端審批卡片** | React HITL Components | `frontend/src/components/ag-ui/hitl/` | ✅ |
| **Claude Hooks** | Approval + Sandbox Hooks | `claude_sdk/hooks/approval.py`, `sandbox.py` | ✅ |

### 3.3 工具與資源存取能力

| 能力 | 實現方式 | 檔案位置 | 狀態 |
|------|----------|----------|------|
| **Azure 管理** | Azure MCP Server (5 modules) | `mcp/servers/azure/` (9 files) | ✅ |
| **Shell 執行** | Shell MCP Server | `mcp/servers/shell/` (5 files) | ✅ |
| **檔案系統** | Filesystem MCP Server | `mcp/servers/filesystem/` (5 files) | ✅ |
| **SSH 遠端** | SSH MCP Server | `mcp/servers/ssh/` (5 files) | ✅ |
| **LDAP 查詢** | LDAP MCP Server | `mcp/servers/ldap/` (5 files) | ✅ |
| **統一路由** | UnifiedToolExecutor | `hybrid/execution/` (5 files, ~1,900 LOC) | ✅ |
| **權限控制** | Security Module | `mcp/security/` (3 files, 28 patterns) | ✅ |
| **Code Interpreter** | MAF CodeInterpreter Builder | `builders/code_interpreter.py` | ✅ |

### 3.4 可觀測性與治理能力

| 能力 | 實現方式 | 檔案位置 | 狀態 |
|------|----------|----------|------|
| **路由指標** | OrchestrationMetrics | `orchestration/metrics.py` (763 LOC) | ✅ |
| **OpenTelemetry** | OTel with fallback counters | `orchestration/metrics.py` | ✅ |
| **巡檢系統** | Patrol Agent (5 check types) | `patrol/` (11 files, ~2,142 LOC) | ✅ |
| **審計追蹤** | Decision Tracker + Report | `audit/` (4 files, ~972 LOC) | ⚠️ PARTIAL |
| **風險評估** | Risk Engine + Scorers | `hybrid/risk/` (8 files, ~2,200 LOC) | ✅ |
| **Checkpoint** | 4 storage backends | `hybrid/checkpoint/` (9 files, ~2,850 LOC) | ✅ |

**Checkpoint 儲存後端**:

```python
# integrations/hybrid/checkpoint/ (9 files, ~2,850 LOC)
├── memory_store.py     → 記憶體 (開發用)
├── redis_store.py      → Redis (推薦生產用)
├── postgres_store.py   → PostgreSQL (持久化)
└── filesystem_store.py → 檔案系統 (備用)
```

### 3.5 記憶與學習能力

| 能力 | 實現方式 | 檔案位置 | 狀態 |
|------|----------|----------|------|
| **統一記憶** | mem0 Integration | `memory/` (5 files, ~1,508 LOC) | ✅ |
| **向量嵌入** | Embedding Service | `memory/embeddings.py` | ✅ |
| **Few-shot 學習** | Learning Module | `learning/` (5 files, ~1,236 LOC) | ⚠️ PARTIAL |
| **案例提取** | Case Extractor | `learning/case_extractor.py` | ⚠️ PARTIAL |
| **相似度匹配** | Similarity Engine | `learning/similarity.py` | ⚠️ PARTIAL |
| **關聯分析** | Correlation Graph | `correlation/` (4 files, ~993 LOC) | ⚠️ PARTIAL |

---

## 4. 技術棧實現詳情

### 4.1 Layer 1: Frontend (130+ .tsx files)

```
frontend/src/
├── pages/ (36 pages)
│   ├── agents, workflows, dashboard
│   ├── DevUI (開發者工具)
│   └── Settings, Auth
├── components/ (80+ components)
│   ├── unified-chat/ (25+ components) ← 主聊天介面
│   ├── ag-ui/ (Chat, HITL, Advanced)
│   ├── ui/ (Shadcn UI)
│   └── layout, shared, auth, DevUI
├── hooks/ (15+ custom hooks)
├── api/ (Fetch API, NOT Axios)
├── store/, stores/ (Zustand)
└── types/, utils/
```

### 4.2 Layer 2: API Layer (526 endpoints, 56 route files)

API 層橫跨 30+ 模組，提供完整的 RESTful 介面:

```
backend/src/api/v1/
├── agents, workflows, sessions, executions
├── ag_ui, claude_sdk, hybrid, mcp
├── orchestration, autonomous, routing
├── patrol, correlation, rootcause, audit
└── auth, files, sandbox, checkpoints, etc.
```

### 4.3 Layer 3: AG-UI Protocol (23 files, ~7,984 LOC)

AG-UI (Agentic UI) 層實現了 Agent 狀態的即時前端可視化。

```python
# integrations/ag_ui/ (23 files, ~7,984 LOC)

features/
├── human_in_loop.py   # HITL 審批 UI 事件
├── generative_ui.py   # 動態 UI 生成
├── predictive_ui.py   # 預測性 UI 更新
└── shared_state.py    # Agent-Frontend 共享狀態

events/                # AG-UI 事件定義
handlers/              # 事件處理器
bridge/                # SSE Bridge (Server-Sent Events)
```

**SSE 串流機制**:

```
Agent 執行過程
    │
    ├─ Thinking Event    → 前端顯示思考過程
    ├─ Tool Call Event   → 前端顯示工具調用
    ├─ HITL Event        → 前端顯示審批卡片
    ├─ Progress Event    → 前端更新進度條
    └─ Result Event      → 前端顯示最終結果

    全部透過 SSE (Server-Sent Events) 即時推送
```

### 4.4 Layer 4: Phase 28 Orchestration (40 files, ~13,795 LOC)

Phase 28 (Sprint 91-99, 235 Story Points) 實現了三層意圖路由系統，是平台的智能入口。

**三層瀑布式路由**:

```
使用者輸入: "ETL Pipeline 又失敗了"
                │
                ▼
┌──────────────────────────────────────────────┐
│ Tier 1: PatternMatcher (< 10ms)              │
│ integrations/orchestration/intent_router/    │
│ pattern_matcher/matcher.py                   │
│                                              │
│ 規則匹配 + 關鍵詞識別                        │
│ "ETL" + "失敗" → IT_INCIDENT (confidence 0.92)│
│                                              │
│ if confidence > 0.9: return result ✅         │
│ else: fallthrough ↓                          │
└──────────────────────────────────────────────┘
                │ (如未命中)
                ▼
┌──────────────────────────────────────────────┐
│ Tier 2: SemanticRouter (< 100ms)             │
│ semantic_router/router.py + routes.py        │
│                                              │
│ 向量相似度搜索                               │
│ 輸入 embedding vs 路由 embedding             │
│                                              │
│ if similarity > 0.85: return result ✅        │
│ else: fallthrough ↓                          │
└──────────────────────────────────────────────┘
                │ (如未命中)
                ▼
┌──────────────────────────────────────────────┐
│ Tier 3: LLMClassifier (< 2000ms)             │
│ llm_classifier/classifier.py + prompts.py   │
│                                              │
│ Claude Haiku 分類 + 完整度評估               │
│ 全面理解意圖 + 評估資訊完整度               │
│                                              │
│ return RoutingDecision ✅                     │
└──────────────────────────────────────────────┘
```

**引導式對話引擎**:

```python
# integrations/orchestration/guided_dialog/
# 5 files, ~3,050 LOC

engine.py           # GuidedDialogEngine - 核心對話引擎
context_manager.py  # 對話上下文管理
generator.py        # 問題生成器 (基於缺失資訊)
refinement_rules.py # 追問規則 (哪些資訊需要補充)
__init__.py
```

**風險評估器**:

```python
# integrations/orchestration/risk_assessor/
# 3 files, ~1,200 LOC

assessor.py   # 風險評估引擎
policies.py   # 風險政策定義 (操作類型 → 風險等級)
__init__.py
```

**HITL 控制器**:

```python
# integrations/orchestration/hitl/
# 4 files, ~1,900 LOC

controller.py        # HITL 控制器 (協調審批流程)
approval_handler.py  # 審批處理 (同意/拒絕/超時)
notification.py      # Teams 通知發送
__init__.py
```

**可觀測性指標**:

```python
# integrations/orchestration/metrics.py (763 LOC)
# OpenTelemetry with fallback counters

class OrchestrationMetrics:
    # 路由指標: 各層命中率、延遲
    # 對話指標: 對話輪次、完成率
    # 風險指標: 各風險等級分布
    # HITL 指標: 審批時間、通過率
```

### 4.5 Layer 5: Hybrid Layer (60 files, ~17,872 LOC)

混合層是整個平台的中央協調者，整合 MAF 與 Claude SDK，提供統一的編排體驗。

**HybridOrchestratorV2** (`orchestrator_v2.py`, 1,103 LOC):

```
HybridOrchestratorV2
├── imports Phase 28 components (InputGateway, IntentRouter, etc.)
├── FrameworkSelector → 選擇 MAF or Claude SDK
├── ContextBridge → 兩個框架間的上下文同步
├── UnifiedToolExecutor → 統一工具路由
├── CheckpointManager → 狀態持久化
├── RiskEngine → 風險評分
└── SwitchingLogic → 框架動態切換
```

**子模組詳情**:

| 子模組 | 檔案數 | LOC | 核心職責 |
|--------|--------|-----|----------|
| intent/ | 7 | ~1,600 | FrameworkSelector, 分類器, 分析器 |
| context/ | 10 | ~3,300 | ContextBridge, 同步, 映射 |
| execution/ | 5 | ~1,900 | UnifiedToolExecutor, 工具路由 |
| risk/ | 8 | ~2,200 | Risk Engine, 評分器, 分析器 |
| switching/ | 9 | ~2,500 | 框架切換 (user/failure/resource/complexity triggers) |
| checkpoint/ | 9 | ~2,850 | 4 種儲存後端 (memory/redis/postgres/filesystem) |

### 4.6 Layer 6: MAF Builder Layer (23 files, ~20,011 LOC)

此層是本平台最成熟的整合層。所有 Builder 均使用官方 `from agent_framework import` 語句，建立真正的 MAF 實例。

**Builder 清單與用途**:

| Builder | 檔案 | 用途 | API 驗證 |
|---------|------|------|----------|
| Handoff | `handoff.py` | Agent 間任務交接 | ✅ `from agent_framework` |
| GroupChat | `groupchat.py` | 多 Agent 群組討論 | ✅ `from agent_framework` |
| Concurrent | `concurrent.py` | 並行 Agent 執行 | ✅ `from agent_framework` |
| Magentic | `magentic.py` | 推理鏈 Agent | ✅ `from agent_framework` |
| Planning | `planning.py` | 任務規劃 Agent | ✅ `from agent_framework` |
| Nested Workflow | `nested_workflow.py` | 巢狀工作流 | ✅ `from agent_framework` |
| Workflow Executor | `workflow_executor.py` | 工作流執行器 | ✅ `from agent_framework` |
| Agent Executor | `agent_executor.py` | Agent 執行器 | ✅ `from agent_framework` |
| Code Interpreter | `code_interpreter.py` | 代碼解釋器 | ✅ `from agent_framework` |

**支援檔案**:
- `handoff_hitl.py` - HITL 整合的 Handoff
- `handoff_policy.py` - Handoff 策略管理
- `handoff_capability.py` - 能力匹配
- `handoff_context.py` - 上下文傳遞
- `handoff_service.py` - Handoff 服務層
- `groupchat_voting.py` - GroupChat 投票機制
- `groupchat_orchestrator.py` - GroupChat 編排
- `edge_routing.py` - 邊緣路由
- `*_migration.py` (4 files) - 遷移適配器

**驗證方式**:

```bash
cd backend && python scripts/verify_official_api_usage.py
# All 5 checks must pass
```

### 4.7 Layer 7: Claude SDK Layer (47 files, ~12,267 LOC)

Claude SDK 層提供自主執行能力，是平台的「智慧引擎」。

**核心客戶端**:

```python
# integrations/claude_sdk/client.py (171 LOC)
# 使用 AsyncAnthropic - 真正的 API 客戶端
from anthropic import AsyncAnthropic
```

**自主執行管線**:

```
Task Input
    │
    ▼
┌──────────────┐
│   Analyzer   │ ← 分析任務需求和上下文
│  (analyzer.py)│
└──────┬───────┘
       ▼
┌──────────────┐
│   Planner    │ ← 規劃執行步驟
│  (planner.py) │
└──────┬───────┘
       ▼
┌──────────────┐
│  Executor    │ ← 執行計劃 (Agentic Loop)
│ (executor.py) │
└──────┬───────┘
       ▼
┌──────────────┐
│  Verifier    │ ← 驗證執行結果
│ (verifier.py) │
└──────┬───────┘
       │
  ┌────┴────┐
  │ 成功?   │
  └────┬────┘
  Yes  │  No → Retry (retry.py) → Fallback (fallback.py)
       │
       ▼
  Task Complete
```

**Hook 系統** (安全護欄):

| Hook | 用途 | 觸發時機 |
|------|------|----------|
| `approval.py` | 高風險操作前請求人工審批 | 工具調用前 |
| `audit.py` | 記錄所有操作到審計日誌 | 每次操作 |
| `rate_limit.py` | API 調用速率限制 | API 調用前 |
| `sandbox.py` | 沙箱環境隔離 | 代碼執行前 |

### 4.8 Layer 8: MCP Layer (43 files, ~10,528 LOC)

MCP (Model Context Protocol) 層提供統一的工具存取介面，讓 Agent 能安全地操作外部系統。

**5 個 MCP Server**:

| Server | 檔案數 | 功能模組 | 用途 |
|--------|--------|----------|------|
| Azure | 9 | VM, Resource, Monitor, Network, Storage | Azure 雲端資源管理 |
| Shell | 5 | 命令執行 | 本地系統操作 |
| Filesystem | 5 | 檔案操作 | 檔案讀寫 |
| SSH | 5 | 遠端連線 | 遠端系統管理 |
| LDAP | 5 | 目錄查詢 | 使用者/群組管理 |

**安全設計**:

```
Security Module (mcp/security/, 3 files)
├── 28 permission patterns → 細粒度權限控制
├── 16 audit patterns     → 操作審計記錄
└── RBAC integration      → 角色權限映射
```

### 4.9 Layer 9: Supporting Integrations

| 模組 | 檔案數 | LOC | 用途 | 狀態 |
|------|--------|-----|------|------|
| memory/ | 5 | ~1,508 | mem0 客戶端, 向量嵌入, 統一記憶 | ✅ REAL |
| patrol/ | 11 | ~2,142 | 5 種巡檢類型, 排程器, 巡檢 Agent | ✅ REAL |
| llm/ | 7 | ~1,789 | Azure OpenAI 客戶端 (AsyncAzureOpenAI verified) | ✅ REAL |
| learning/ | 5 | ~1,236 | Few-shot 學習, 案例提取, 相似度匹配 | ⚠️ PARTIAL |
| correlation/ | 4 | ~993 | 圖分析, 關聯識別 | ⚠️ PARTIAL |
| audit/ | 4 | ~972 | 決策追蹤, 報告 | ⚠️ PARTIAL |

### 4.10 Layer 10: Domain Layer (114 files, ~39,941 LOC)

業務邏輯層包含 20 個 domain modules，是平台的業務核心。

### 4.11 Layer 11: Infrastructure (23 files, ~3,101 LOC)

| 組件 | 狀態 | 說明 |
|------|------|------|
| PostgreSQL 16 | ✅ 運行中 | 主資料庫 (port 5432) |
| Redis 7 | ✅ 運行中 | 快取 (port 6379) |
| RabbitMQ | ⚠️ 空殼 | 僅 `__init__.py`，尚未實現 |

---

## 5. 並行處理架構

### 5.1 各層並行能力現狀

| 層級 | 並行模式 | 現狀 | 限制 |
|------|----------|------|------|
| **Layer 4: Routing** | 瀑布式 (非並行) | 三層依序嘗試 | 設計如此，非問題 |
| **Layer 5: Hybrid** | asyncio 協程 | 支援並行任務分派 | ContextSynchronizer 無鎖 |
| **Layer 6: MAF** | MAF Concurrent Builder | 原生並行支援 | 受 MAF SDK 限制 |
| **Layer 7: Claude SDK** | AsyncAnthropic | 原生 async | 單 Worker 處理序列 |
| **Layer 8: MCP** | 獨立 Server 進程 | 各 Server 獨立 | 無跨 Server 並行控制 |
| **Layer 2: API** | FastAPI async | 原生支援 | 單 Uvicorn Worker |
| **Layer 1: Frontend** | React 18 並行渲染 | 支援 | 正常 |

### 5.2 已知並行問題

**問題 1: ContextSynchronizer 記憶體狀態 (嚴重度: 高)**

```python
# integrations/hybrid/context/ 的 ContextSynchronizer
# 使用 dict 作為記憶體存儲，無 threading.Lock
# 在多 Worker 或高並行場景下有競爭條件風險

# 現況:
state = {}  # In-memory, no locks

# 建議:
# - 添加 asyncio.Lock
# - 或遷移到 Redis (已有 redis_store.py 可復用)
```

**問題 2: 單 Uvicorn Worker (嚴重度: 高)**

```
# 現況:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 僅 1 個 Worker，所有請求序列處理

# 建議 (生產環境):
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
# 或使用 Gunicorn:
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

**問題 3: RabbitMQ 未實現 (嚴重度: 中)**

```
# integrations/infrastructure/messaging/
# 僅有 __init__.py，無實際實現
# 影響: 無法使用非同步訊息佇列進行任務分派
```

### 5.3 並行處理改善規劃

```
Phase 目標                        優先級    依賴
──────────────────────────────────────────────────
1. ContextSynchronizer + Lock     高        無
2. Multi-Worker Uvicorn           高        無
3. RabbitMQ 訊息佇列實現          中        Docker
4. Worker Pool 容器化             低        K8s
```

---

## 6. 關鍵設計決策

### 6.1 為什麼是 MAF + Claude SDK 混合而非單一框架

| 考量 | MAF 單獨 | Claude SDK 單獨 | 混合架構 (選擇) |
|------|----------|----------------|-----------------|
| 結構化編排 | ✅ 原生支援 | ❌ 需自建 | ✅ MAF 處理 |
| 自主推理 | ❌ 無 | ✅ Extended Thinking | ✅ Claude 處理 |
| 檢查點 | ✅ 內建 | ❌ 需自建 | ✅ MAF + 4 backends |
| 工具存取 | ⚠️ 有限 | ✅ MCP 原生 | ✅ 統一 MCP |
| 企業治理 | ✅ 審計追蹤 | ⚠️ 需 Hooks | ✅ 兩者結合 |
| 動態切換 | ❌ | ❌ | ✅ SwitchingLogic |

### 6.2 三層意圖路由的設計理由

```
為什麼不直接用 LLM 分類所有意圖?

成本與延遲考量:
────────────────
PatternMatcher:  < 10ms,   $0 (規則匹配)     → 處理 60% 常見請求
SemanticRouter:  < 100ms,  $0 (向量計算)     → 處理 25% 語義請求
LLMClassifier:   < 2000ms, $$ (API 調用)     → 處理 15% 複雜請求

結果: ~85% 請求不需要 LLM 調用
      平均延遲從 ~2000ms 降至 ~50ms
      API 成本降低 ~85%
```

### 6.3 Checkpoint 4 後端設計

```
為什麼需要 4 種 Checkpoint 儲存後端?

Memory:     開發和測試時使用 (快速, 無持久化)
Redis:      生產推薦 (快速, TTL, 適合熱數據)
PostgreSQL: 合規要求 (持久化, 可查詢, 審計)
Filesystem: 備用方案 (簡單, 無依賴)

根據環境自動選擇，支持運行時切換。
```

### 6.4 AG-UI SSE vs WebSocket

```
為什麼選擇 SSE 而非 WebSocket?

1. Agent 通信是單向的: Agent → 前端 (狀態更新)
2. 前端 → Agent 的指令走標準 HTTP API
3. SSE 更簡單、自動重連、防火牆友好
4. 與 FastAPI 原生整合更順暢
5. 不需要雙向即時通信的場景

但保留 WebSocket 作為未來選項 (如即時協作編輯)。
```

### 6.5 MCP 而非直接 API 整合

```
為什麼用 MCP Server 包裝工具而非直接 API 調用?

1. 統一介面: 所有工具遵循相同的 Protocol
2. 安全隔離: 每個 Server 獨立進程，隔離故障
3. 權限統一: 28 種 permission patterns 統一管理
4. 審計統一: 16 種 audit patterns 統一記錄
5. Agent 無關: MAF 和 Claude SDK 都能使用同一套工具
6. 可擴展: 新增工具只需新增 MCP Server
```

---

## 7. 可觀測性設計

### 7.1 指標體系

```python
# integrations/orchestration/metrics.py (763 LOC)

OrchestrationMetrics:
├── Routing Metrics
│   ├── 各層命中率 (pattern/semantic/llm)
│   ├── 各層延遲分布
│   └── 路由決策信心度分布
├── Dialog Metrics
│   ├── 對話輪次分布
│   ├── 資訊完成率
│   └── 用戶放棄率
├── Risk Metrics
│   ├── 風險等級分布 (LOW/MEDIUM/HIGH/CRITICAL)
│   └── 審批通過率
├── HITL Metrics
│   ├── 審批請求量
│   ├── 審批等待時間
│   └── 超時升級率
└── Execution Metrics
    ├── 框架選擇分布 (MAF vs Claude)
    ├── 任務完成率
    └── 執行時間分布
```

### 7.2 OpenTelemetry 整合

```
OrchestrationMetrics 設計:
─────────────────────────
• 優先使用 OpenTelemetry (如果可用)
• 自動降級到 fallback counters (dict-based)
• 零配置啟動，不因 OTel 不可用而失敗
• 生產環境接入 Azure Monitor / Grafana
```

### 7.3 巡檢系統

```python
# integrations/patrol/ (11 files, ~2,142 LOC)

Patrol Agent:
├── 5 種巡檢類型
│   ├── Health Check     → 服務健康狀態
│   ├── Performance      → 效能指標
│   ├── Security         → 安全合規
│   ├── Resource         → 資源使用率
│   └── Configuration    → 配置一致性
├── Scheduler            → 定時巡檢排程
└── Agent                → 自主巡檢 Agent
```

### 7.4 審計追蹤

```
Decision Audit Trail (每次 Agent 決策記錄):
─────────────────────────────────────────
1. Intent Classification → 為什麼歸類為此意圖
2. Risk Assessment       → 為什麼判定此風險等級
3. Framework Selection   → 為什麼選擇 MAF/Claude
4. Tool Invocations      → 調用了哪些工具，結果如何
5. HITL Decisions        → 人工審批的決定和理由
6. Execution Result      → 最終結果和驗證
```

---

## 8. 總結與展望

### 8.1 平台定位總結

IPA Platform 是一個**智能體編排平台**，其核心定位：

1. **不是 n8n 的替代品** --- 確定性工作流由 n8n/Power Automate 處理
2. **處理不確定性任務** --- 需要 AI 判斷力、推理能力、人機互動的複雜場景
3. **MAF + Claude SDK 混合** --- 結構化治理 + 自主智慧，各取所長
4. **企業級治理** --- 完整審計、HITL 審批、風險評估、可觀測性
5. **統一工具存取** --- MCP Protocol 提供安全、統一的外部系統操作

### 8.2 實現成熟度

```
成熟度評估 (基於代碼量和完成度):

Layer 1:  Frontend        ████████████████████ 90% (130+ .tsx, 36 pages)
Layer 2:  API             ████████████████████ 95% (526 endpoints)
Layer 3:  AG-UI           ████████████████░░░░ 80% (~8K LOC, SSE bridge)
Layer 4:  Orchestration   ████████████████████ 90% (~14K LOC, Phase 28)
Layer 5:  Hybrid          ████████████████░░░░ 85% (~18K LOC, 60 files)
Layer 6:  MAF Builder     ████████████████████ 95% (~20K LOC, 9+ builders)
Layer 7:  Claude SDK      ████████████████░░░░ 80% (~12K LOC, 47 files)
Layer 8:  MCP             ████████████████░░░░ 80% (~11K LOC, 5 servers)
Layer 9:  Supporting      ████████████░░░░░░░░ 65% (memory ✅, learning ⚠️)
Layer 10: Domain          ████████████████████ 90% (~40K LOC, 114 files)
Layer 11: Infrastructure  ████████░░░░░░░░░░░░ 45% (RabbitMQ empty)
```

### 8.3 後續規劃重點

| 優先級 | 項目 | 原因 |
|--------|------|------|
| **P0** | ContextSynchronizer 並行安全 | 生產環境必要 |
| **P0** | Multi-Worker Uvicorn | 生產環境效能 |
| **P1** | RabbitMQ 訊息佇列實現 | 非同步任務分派 |
| **P1** | Learning 模組完善 | 平台學習能力 |
| **P2** | Worker Pool 容器化 | 擴展性 |
| **P2** | Mock/Production 代碼分離 | 代碼衛生 |
| **P3** | 更多 MCP Server | 工具生態擴展 |

### 8.4 架構演進方向

```
V2 (現在) → V3 (下一步)
─────────────────────────

V2: 混合編排 + 三層路由 + HITL + MCP
    ↓
V3 目標:
    ├── 生產化 (Multi-Worker, Message Queue, Container)
    ├── 學習閉環 (Few-shot 學習 + 案例庫完善)
    ├── 擴展 MCP 生態 (更多 Server: K8s, Database, etc.)
    └── 多 Agent 協調 (Worker Pool, Task Market)
```

---

## 更新歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 2.1 | 2026-01-28 | 架構層級命名統一：將 Layer A/B 改為 L1-L11 標準編號；補齊 L10 Domain Layer 和 L11 Infrastructure 標籤；Section 4.x 按 L1→L11 順序重排；Section 5.1 和 8.2 補齊缺失層級標號 |
| 2.0 | 2026-01-28 | 全面重寫：重新定位為 Agent Orchestration Platform；更新所有層級的實際 LOC 和檔案數；新增平台定位、核心能力矩陣、並行處理分析；基於代碼庫調查更新實現狀態 |
| 1.3 | 2026-01-16 | Phase 28 三層意圖路由系統更新 |
| 1.2 | 2026-01-10 | Phase 20 AG-UI 整合更新 |
| 1.1 | 2025-12-20 | Phase 15 Claude SDK 整合 |
| 1.0 | 2025-12-01 | 初始版本 - 企業 IT 事件智能處理平台 |
