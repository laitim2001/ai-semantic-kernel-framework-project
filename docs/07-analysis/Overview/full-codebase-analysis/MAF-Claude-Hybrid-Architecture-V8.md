# 智能體編排平台：MAF + Claude Agent SDK 混合架構實現

> **文件版本**: 8.1
> **最後更新**: 2026-03-16
> **定位**: Agent Orchestration Platform (智能體編排平台)
> **狀態**: Phase 34 已完成 (133 Sprints, ~2500+ Story Points)
> **代碼庫規模**: Backend 725 .py files, 258,904 LOC | Frontend 214 .tsx/.ts files, 49,357 LOC
> **驗證方式**: AST 靜態分析 + 8 Agent 並行深度代碼庫驗證 + 5 端到端流程追蹤 + 22 份分析報告交叉驗證
> **前版**: V8.0 (2026-03-15, Phase 34), V7.0 (2026-02-11, Phase 29), V6.0, V3.0
> **分析基準日期**: 2026-03-15
> **V8.1 更新**: MAF RC4 升級 (`1.0.0b260114` → `1.0.0rc4`) + Claude SDK 同步更新反映至分析內容

---

## 實現狀態總覽

### AST 靜態分析數據 (2026-03-15 掃描)

| 指標 | Backend | Frontend | 合計 |
|------|---------|----------|------|
| **檔案數** | 725 .py | 214 .tsx/.ts | 939 |
| **總行數** | 258,904 | 49,357 | 308,261 |
| **有效代碼行** | 197,671 | 37,428 | 235,099 |
| **類別數** | 2,316 | — | 2,316 |
| **函數/方法數** | 7,607 | — | 7,607 |
| **已實現函數** | 7,322 (96.3%) | — | 7,322 |
| **空函數/Stub** | 285 (3.7%) | — | 285 |
| **元件數** | — | 153 | 153 |
| **介面/型別** | — | 579 | 579 |
| **API 端點** | 560 | — | 560 |
| **有 Auth 端點** | 31 (5.5%) | — | 31 |
| **無 Auth 端點** | 529 (94.5%) | — | 529 |
| **InMemory 模式** | 30 處 | — | 30 |
| **Mock 模式** | 119 處 | 115 處 | 234 |
| **測試檔案** | 360 | 38 | 398 |
| **測試函數/案例** | 9,965 | 306 | 10,271 |

### 逐層 AST 數據

| 層級 | 檔案數 | 總行數 | 代碼行 | 類別 | 函數 | 空函數 |
|------|--------|--------|--------|------|------|--------|
| API (api/v1) | 143 | 46,133 | 34,496 | 701 | 896 | 0 |
| Domain | 112+ | ~47,200+ | ~36,000+ | 350+ | 1,200+ | 52 |
| Integration: agent_framework | 57 | 38,040 | 28,248 | 296 | 1,311 | 63 |
| Integration: hybrid | 73 | 24,252 | 18,152 | 208 | 749 | 45 |
| Integration: mcp | 73 | 20,920 | 17,000 | 117 | 583 | 8 |
| Integration: claude_sdk | 47 | 15,180 | 11,625 | 145 | 493 | 12 |
| Integration: ag_ui | 24 | 9,836 | 7,554 | 85 | 290 | 11 |
| Integration: orchestration | ~40 | ~16,000 | ~12,000 | 150+ | 500+ | 17 |
| Integration: 其他 (12 modules) | ~64 | ~18,000+ | ~14,000+ | 130+ | 420+ | 3 |
| Core | 34+ | ~10,200 | ~7,800 | 76 | 340 | 1 |
| Infrastructure | 39+ | ~6,300 | ~4,700 | 30+ | 150+ | 5 |
| Frontend | 214 | 49,357 | 37,428 | — | — | — |

### 62 項已驗證問題摘要

| 嚴重度 | 數量 | 關鍵代表 |
|--------|------|----------|
| **CRITICAL** | 8 | C-01 全域 InMemory 存儲 (20+ 模組)、C-02/C-04 Correlation/RootCause API 100% Mock、C-07 SQL 注入、C-08 API Key 暴露 |
| **HIGH** | 16 | H-01 無 RBAC、H-03 全域 Singleton、H-04 ContextBridge 無鎖、H-08 前端靜默 Mock、H-11 Chat 僅 localStorage |
| **MEDIUM** | 22 | M-01 datetime.utcnow() 棄用、M-02 os.environ 違規、M-03 N+1 查詢、M-06 Report Generator 空函數體 |
| **LOW** | 16 | L-01 Barrel Export 不一致、L-02 檔案命名不一致、L-16 TODO 註解 |

**Top 20 已知問題** (完整 62 項清單見附錄 C):

| # | 問題 | 影響 | 嚴重度 |
|---|------|------|--------|
| C-01 | 全域 InMemory 存儲 — 重啟遺失所有狀態 | 20+ modules | CRITICAL |
| C-02 | Correlation API routes 100% Mock | 7 endpoints | CRITICAL |
| C-03 | Autonomous API routes 100% Mock | api/v1/autonomous/ | CRITICAL |
| C-04 | RootCause API routes 100% Mock | 4 endpoints | CRITICAL |
| C-05 | Patrol API routes 100% Mock | 9 endpoints | CRITICAL |
| C-06 | messaging/ STUB (RabbitMQ 僅 1 行註解) | infrastructure/ | CRITICAL |
| C-07 | SQL injection via f-string table name | postgres_store.py | CRITICAL |
| C-08 | API key prefix 暴露於 AG-UI 回應 | ag_ui/ response | CRITICAL |
| H-01 | 無 RBAC 在破壞性操作 | cache, connectors, agents | HIGH |
| H-02 | ag_ui /test/* 不受 APP_ENV 限制 | api/v1/ag_ui/ | HIGH |
| H-03 | 全域 Singleton anti-pattern | 10+ modules | HIGH |
| H-04 | ContextBridge._context_cache 無鎖 | hybrid/context/ | HIGH |
| H-05 | Checkpoint 使用非官方 API | hybrid/checkpoint/ | HIGH |
| H-06 | MCP AuditLogger 未接線 | 8 servers | HIGH |
| H-08 | 前端 10 頁面靜默降級 Mock | Dashboard, Agents... | HIGH |
| H-11 | Chat 歷史僅 localStorage | UnifiedChat.tsx | HIGH |
| H-12 | Shell/SSH HITL = log-only | mcp/servers/ | HIGH |
| H-14 | Rate limiter InMemory | middleware/ | HIGH |
| H-15 | 缺少 React Error Boundaries | 5+ components | HIGH |
| M-01 | datetime.utcnow() deprecated | 6+ files | MEDIUM |

### V7 → V8 關鍵變更

| 維度 | V7 (Phase 29) | V8 (Phase 34) | 變更 |
|------|---------------|---------------|------|
| Sprints | 106 | 133 | +27 sprints |
| Backend LOC | ~228,700 | 258,904 (AST) | +30,204 |
| Frontend LOC | ~47,630 | 49,357 (AST) | +1,727 |
| Backend Files | 611 | 725 | +114 |
| Frontend Files | 203 | 214 | +11 |
| MCP Servers | 5 | 8 | +3 (n8n, ADF, D365) |
| MCP Tools | 53 | 64 | +11 |
| Correlation/RootCause | STUB (硬編碼) | FIXED (Sprint 130) | 真實數據源 |
| HybridOrchestratorV2 | God Object | Mediator Pattern (Sprint 132) | 6 Handler 解耦 |
| 前端視覺化 | Swarm Panel | + ReactFlow Workflow DAG (Sprint 133) | +DAG 視覺化 |
| 測試覆蓋 | 未量化 | 10,271 測試案例 (AST) | 首次精確量化 |
| 驗證方式 | 5+3 Agent | AST + 8 Agent + E2E + 22 報告 | 更嚴謹 |
| 問題數 | 未統一 | 62 項去重分類 | 首次統一 Registry |

---

## 執行摘要

IPA Platform 是一個企業級智能體編排平台，採用 Microsoft Agent Framework (MAF) + Claude Agent SDK 混合架構，透過 AG-UI Protocol 實現前後端即時串流通訊。平台核心定位為 IT 運維智能化 (AIOps)，目標市場為台灣/香港企業。

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   IPA Platform = Agent Orchestration Platform (V8)                   │
│   ═══════════════════════════════════════════                        │
│                                                                      │
│   「不是 n8n/Power Automate 的替代品，                               │
│     而是處理 n8n 無法處理的那些任務」                                │
│                                                                      │
│   MAF (Microsoft Agent Framework)                                    │
│   ─────────────────────────────────                                  │
│   • 結構化編排與治理                                                 │
│   • 多 Agent 協作模式 (Handoff, GroupChat, Magentic)                │
│   • 檢查點與狀態持久化 (4 backends)                                  │
│   • 企業級審計追蹤                                                   │
│   • 9 個 Builder Adapter (7 MAF compliant + 2 standalone)           │
│                                                                      │
│   Claude Agent SDK                                                   │
│   ─────────────────                                                  │
│   • AsyncAnthropic 真實 SDK 整合                                    │
│   • Agentic Loop (自主迭代直到完成)                                  │
│   • Extended Thinking (複雜分析推理)                                 │
│   • 並行 Worker 執行 (ClaudeCoordinator, 4 modes)                   │
│   • 10 個 Tool 定義 (file, search, code, bash 等)                   │
│                                                                      │
│   AG-UI Protocol                                                     │
│   ──────────────                                                     │
│   • 即時 Agent 狀態串流 (11 event types)                            │
│   • Human-in-the-Loop 審批 (3 套系統)                               │
│   • 思考過程可視化 (Extended Thinking streaming)                     │
│   • Agent Swarm 群集即時視覺化 (15 components + 4 hooks)            │
│   • 7 大 Features (SharedState, FileAttach, ThreadStore 等)         │
│                                                                      │
│   MCP (Model Context Protocol)                                       │
│   ─────────────────────────────                                      │
│   • 統一工具存取介面                                                 │
│   • 8 個 MCP Server (Azure, Shell, FS, SSH, LDAP, n8n, ADF, D365)  │
│   • 64 種工具、28 種權限模式、16 種審計模式                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 關鍵數據

- **Backend**: 258,904 LOC across 725 .py files (integration 141,248 + domain 47,200+ + API 46,133 + core 10,200 + infra 6,300)
- **Frontend**: 49,357 LOC across 214 .tsx/.ts files (153 components, 17 hooks, 39 pages)
- **API Endpoints**: 560 (31 with Auth, 529 global protected_router)
- **Tests**: 10,271 test cases (9,965 backend + 306 frontend) across 398 test files
- **MCP**: 8 servers, 64 tools, 28 permission patterns
- **Issues**: 62 verified (8 CRITICAL, 16 HIGH, 22 MEDIUM, 16 LOW)

**V8 分析基於 22 份深度代碼分析報告**，涵蓋 API 層 (3 份)、Domain 層 (3 份)、Integration 層 (11 份)、Core/Infrastructure (1 份)、Frontend (4 份)，加上 3 份 Phase 4 驗證報告 (E2E 流程、Plan vs Reality、Issue Registry)。所有數據均來自 AST 靜態分析和逐檔代碼審查，非估算。

**關鍵發現**:
- 70 項計畫功能中 59 項完全實現 (84.3%)，無任何功能完全缺失
- Sprint 130 修復了 V7 最大痛點 (Correlation/RootCause STUB)
- Sprint 132 解決了 HybridOrchestratorV2 God Object 問題
- 最大系統性風險仍是 InMemory 存儲 (C-01, 影響 20+ 模組)
- 5 條端到端流程中 2 條完全連通、2 條大部分連通、1 條部分連通

---

## 1. 平台定位與價值主張

### 1.1 為什麼是「智能體編排平台」而非「工作流自動化」

IPA Platform 的核心能力是**協調智能體集群**處理需要 AI 判斷力的複雜場景，而非替代 n8n/Power Automate 等確定性工作流工具。

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
│   特點：                                特點 (V8 驗證)：             │
│   • 視覺化流程設計                      • Agent 自主推理 (AsyncAnthropic) │
│   • 確定性執行                          • 多 Agent 協作 (9 MAF Builders) │
│   • 固定邏輯分支                        • Human-in-the-Loop (3 審批系統) │
│   • 無需 AI 判斷                        • 可觀測的決策過程 (AG-UI SSE)   │
│   • 成本低、速度快                      • 8 MCP Server + 64 工具          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 平台獨特價值

**場景一：使用者驅動的複雜 IT 任務（V8 已驗證 E2E 可行）**

```
使用者：「APAC Glider ETL Pipeline 連續第三天失敗，日報表完全無法產出」

IPA Platform 的處理方式 (V8 E2E Flow 1 驗證):
─────────────────────────────────────────────
1. [意圖路由] BusinessIntentRouter 三層路由識別：
   PatternMatcher (30+ regex) → INCIDENT, conf=0.95   ✅ V8 驗證
2. [完整性檢查] CompletenessChecker → 資訊不足
   → GuidedDialogEngine 追問：哪個 Pipeline？錯誤訊息？影響範圍？
   ⚠️ Dialog session 僅 InMemory (V8 Issue)
3. [風險評估] RiskAssessor (7 維度):
   intent=0.8 + production=0.3 + urgent=0.15 → HIGH    ✅ V8 驗證
4. [HITL 審批] HITLController → Teams Adaptive Card (繁中)
   等待審批 (timeout: 30min)
   ⚠️ 3 套審批系統互不連接 (V8 新發現)
5. [Agent 協作] HybridOrchestratorV2 → FrameworkSelector:
   ├─ 診斷 Agent → MCP Azure Server (24 tools) 查詢日誌
   ├─ 分析 Agent → Claude SDK Extended Thinking 分析根因
   └─ 修復 Agent → MCP Shell Server 執行修復腳本
   ⚠️ Shell/SSH HITL = log-only, 不阻擋 (V8 Issue H-12)
6. [執行驗證] Agent 驗證修復結果、更新 ServiceNow 工單
7. [學習記錄] LearningService 記錄案例
   ⚠️ 僅 InMemory，重啟遺失 (V8 Issue C-01)
```

**場景二：Swarm 模式多 Agent 協作（V8 E2E Flow 5 驗證）**

```
使用者：「幫我寫一份 Q1 技術策略報告」

IPA Platform Swarm 模式 (V8 驗證):
─────────────────────────────────
1. [Swarm 初始化] SwarmTracker (693 LOC) 創建群集，分派 Worker
2. [並行執行] ClaudeCoordinator (Sprint 81) + TaskAllocator
   ├─ RESEARCH Worker → 蒐集市場資料
   ├─ ANALYST Worker  → 分析技術趨勢
   ├─ WRITER Worker   → 撰寫報告草稿
   └─ REVIEWER Worker → 審查品質
3. [即時可視化] SwarmEventEmitter (634 LOC) 串流 9 種 SSE 事件
4. [Swarm Panel] 前端 15 組件 + 4 hooks 即時顯示每個 Worker 狀態
5. [結果彙總] Coordinator 整合所有 Worker 產出

⚠️ V8 發現: Demo API (/api/v1/swarm/demo) 使用模擬場景，
   非整合到主聊天流程。真實 Swarm 需透過 ClaudeCoordinator 觸發。
```

**場景三：確定性 IT 運維 → n8n（不在本平台範疇）**

```
事件：新員工入職 → 建立帳號 → 分配權限 → 發送歡迎郵件

這是 n8n/Power Automate 的強項：
────────────────────────────────
• 固定步驟、固定邏輯
• 不需要 AI 判斷
• 成本更低、更可靠
• IPA Platform 透過 n8n MCP Server (Sprint 124) 與之整合，而非取代
```

### 1.3 核心價值定位

| 維度 | IPA Platform 提供的價值 | V8 驗證狀態 | n8n 提供的價值 |
|------|------------------------|------------|----------------|
| **智能判斷** | Agent 自主分析、推理、決策 | ✅ AsyncAnthropic + Extended Thinking | 無 (固定規則) |
| **多 Agent 協作** | Handoff, GroupChat, 並行 Worker, Swarm | ✅ 9 MAF Builders (7/7 合規) | 無 |
| **人機互動** | 即時審批、引導對話、思考可視化 | ⚠️ 3 套獨立審批系統 | 固定審批節點 |
| **不確定性處理** | 三層路由 + 風險評估 + 適應性推理 | ✅ Pattern→Semantic→LLM | 無 |
| **治理可見性** | 完整決策追蹤、審計日誌 | ⚠️ AuditLogger 僅 InMemory | 基礎日誌 |
| **學習能力** | 案例學習、Few-shot 改進 | ⚠️ LearningService 僅 InMemory | 無 |
| **Swarm 可視化** | 群集即時追蹤、Worker 狀態串流 | ✅ 15 前端組件 + SSE | 無 |
| **跨系統整合** | MCP 統一工具層 | ✅ 8 Servers, 64 工具 (超越計劃) | 內建連接器 |
| **確定性流程** | 非核心場景 (透過 n8n MCP 整合) | ✅ n8n MCP Server (S124) | 核心強項 |

### 1.4 技術棧

```
Frontend:  React 18 + TypeScript + Vite + Tailwind + Shadcn UI + ReactFlow + Zustand
           214 files, 49,357 LOC, 153 components, 0 'any' types (V8 AST)
Backend:   FastAPI + Python 3.12 + Pydantic v2 + SQLAlchemy 2.0 (async)
           725 files, 258,904 LOC, 7,607 functions (96.3% implemented) (V8 AST)
Database:  PostgreSQL 16 (7 models) + Redis 7 (LLM cache + distributed locks)
Messaging: RabbitMQ (⚠️ stub only — 1 行代碼)
AI/LLM:    Azure OpenAI (gpt-4o) + Anthropic Claude (AsyncAnthropic)
Protocol:  AG-UI (SSE, 11 event types) + MCP (JSON-RPC 2.0 over stdio)
Auth:      JWT HS256 (python-jose) + bcrypt + router-level require_auth (Sprint 111)
Testing:   pytest (9,965 tests) + Vitest (306 tests) + Playwright (144 E2E tests)
```

### 1.5 計畫合規性（V8 Validator 2 驗證）

| 指標 | 數值 | 說明 |
|------|------|------|
| 計畫功能總數 | 70 | 9 類別 (A-I) |
| 完全實現 | 59 (84.3%) | 代碼完整 + 業務邏輯驗證通過 |
| 超越計畫 | 1 | MCP: 計劃 5 servers → 實際 8 servers + 64 tools |
| 部分實現 | 2 | ServiceNow (UAT only), A2A (InMemory only) |
| 分裂狀態 | 4 | Integration 層已修復 (S130) 但 API route 仍返回 mock |
| 完全缺失 | 0 | 所有計劃功能至少有部分實現 |
| 計畫外額外功能 | 15 | 包括 notifications, incident, OTel metrics 等 |
| 延遲 (低優先) | 4 | K8s/Production Scaling (Phase 25, P3) |

---

## 2. 完整架構設計

### 2.0 端到端執行流程圖

> **重要**: 此圖展示完整的請求處理流程，從用戶輸入到結果返回的每一步驟和決策點。V8 基於 22 Agent 全文閱讀 + 5 條端到端流程驗證繪製。所有數據、閾值、元件名稱均來自 V8 代碼分析。

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     IPA Platform 端到端執行流程圖 (Phase 34, V8)                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ╔═══════════════════════════════════════════════════════════════════════════════╗  │
│  ║                         入口層 + InputGateway                                 ║  │
│  ╠═══════════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                                ║  │
│  ║   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          ║  │
│  ║   │ ServiceNow  │  │   Teams     │  │ Prometheus  │  │  Chat UI    │          ║  │
│  ║   │  Webhook    │  │ (通知 only) │  │   Alert     │  │  (用戶輸入) │          ║  │
│  ║   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          ║  │
│  ║          │                │                │                │                   ║  │
│  ║          └────────────────┴────────────────┴────────────────┘                   ║  │
│  ║                                    │                                            ║  │
│  ║                                    ▼                                            ║  │
│  ║   ┌────────────────────────────────────────────────────────────────────────┐    ║  │
│  ║   │                         InputGateway                                   │    ║  │
│  ║   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │    ║  │
│  ║   │   │ ServiceNow   │  │  Prometheus  │  │  UserInput   │                │    ║  │
│  ║   │   │ Handler      │  │  Handler     │  │  Handler     │                │    ║  │
│  ║   │   │ (20+ 映射)   │  │ (41 regex)   │  │ (pass-thru)  │                │    ║  │
│  ║   │   └──────────────┘  └──────────────┘  └──────────────┘                │    ║  │
│  ║   │                        ↓ 來源識別 + 格式標準化                          │    ║  │
│  ║   │                   UnifiedRequestEnvelope                               │    ║  │
│  ║   └────────────────────────────────┬───────────────────────────────────────┘    ║  │
│  ╚════════════════════════════════════│════════════════════════════════════════════╝  │
│                                       │                                              │
│  ╔════════════════════════════════════│════════════════════════════════════════════╗  │
│  ║               Phase 28 三層意圖路由系統 (Orchestration Layer)                  ║  │
│  ║               54 files, ~15,570 LOC (V8 AST 精確)                             ║  │
│  ╠════════════════════════════════════│════════════════════════════════════════════╣  │
│  ║                                    ▼                                           ║  │
│  ║   ┌────────────────────────────────────────────────────────────────────────┐   ║  │
│  ║   │              BusinessIntentRouter (三層瀑布式路由)                      │   ║  │
│  ║   │                                                                        │   ║  │
│  ║   │   ┌──────────────────────────────────────────────────────────────┐    │   ║  │
│  ║   │   │ Layer 1: PatternMatcher (< 10ms)                             │    │   ║  │
│  ║   │   │ └─ 30+ pre-compiled regex (YAML, 中英雙語)                   │    │   ║  │
│  ║   │   │ └─ 置信度固定 0.95，命中 ≥ 0.90 直接輸出                     │    │   ║  │
│  ║   │   │                    ↓ (未命中)                                 │    │   ║  │
│  ║   │   │ Layer 2: SemanticRouter (< 100ms)                            │    │   ║  │
│  ║   │   │ └─ 15 routes, ~100+ utterances                               │    │   ║  │
│  ║   │   │ └─ 雙實現: Aurelio semantic-router 或 Azure AI Search (S115) │    │   ║  │
│  ║   │   │ └─ 相似度 > 0.85 輸出                                        │    │   ║  │
│  ║   │   │   ⚠️ 預設使用 MockSemanticRouter (需 API Key 啟用真實版)      │    │   ║  │
│  ║   │   │                    ↓ (未命中)                                 │    │   ║  │
│  ║   │   │ Layer 3: LLMClassifier (< 2000ms)                            │    │   ║  │
│  ║   │   │ └─ Azure OpenAI / Claude / Mock (LLMServiceFactory 自動偵測) │    │   ║  │
│  ║   │   │ └─ Structured JSON prompt + intent/sub-intent/completeness    │    │   ║  │
│  ║   │   │ └─ InMemory cache with TTL                                    │    │   ║  │
│  ║   │   │   ⚠️ 無 LLM 配置時返回 UNKNOWN (conf=0.0)，不 crash          │    │   ║  │
│  ║   │   └──────────────────────────────────────────────────────────────┘    │   ║  │
│  ║   │                                │                                       │   ║  │
│  ║   │                   RoutingDecision {intent, completeness, risk}         │   ║  │
│  ║   └────────────────────────────────┬───────────────────────────────────────┘   ║  │
│  ║                                    │                                           ║  │
│  ║                    ┌───────────────┴───────────────┐                           ║  │
│  ║                    │      is_sufficient?           │                           ║  │
│  ║                    │      (資訊是否足夠?)          │                           ║  │
│  ║                    └───────────────┬───────────────┘                           ║  │
│  ║                          ┌─────────┴─────────┐                                 ║  │
│  ║                         Yes                  No                                ║  │
│  ║                          │                    │                                ║  │
│  ║                          │                    ▼                                ║  │
│  ║                          │   ┌──────────────────────────┐                      ║  │
│  ║                          │   │   GuidedDialogEngine     │                      ║  │
│  ║                          │   │  (引導式對話收集資訊)    │                      ║  │
│  ║                          │   │  模板式中文問題生成       │                      ║  │
│  ║                          │   │  ⚠️ Session 僅 InMemory  │                      ║  │
│  ║                          │   └───────────┬──────────────┘                      ║  │
│  ║                          │               │ (補充後重新評估)                    ║  │
│  ║                          │   ←───────────┘                                     ║  │
│  ║                          ▼                                                     ║  │
│  ║   ┌──────────────────────────────────────────────────────────────────────┐     ║  │
│  ║   │                      RiskAssessor (7 維度風險評估)                    │     ║  │
│  ║   │   26 ITIL-aligned policies, 評估因素:                                │     ║  │
│  ║   │   • Intent Category (INCIDENT=0.8, CHANGE=0.6, REQUEST=0.4)         │     ║  │
│  ║   │   • Sub Intent (system_down=0.5, security_incident=0.5)             │     ║  │
│  ║   │   • Production Environment (weight=0.3)                              │     ║  │
│  ║   │   • Weekend (weight=0.2)                                             │     ║  │
│  ║   │   • Urgent (weight=0.15)                                             │     ║  │
│  ║   │   • Affected Systems Count (weight=min(0.1*count, 0.3))             │     ║  │
│  ║   │   • Low Confidence (weight=0.2*(1-confidence) when <0.8)            │     ║  │
│  ║   │   輸出: RiskLevel (LOW / MEDIUM / HIGH / CRITICAL)                   │     ║  │
│  ║   └────────────────────────────────┬─────────────────────────────────────┘     ║  │
│  ║                                    │                                           ║  │
│  ║                    ┌───────────────┴───────────────┐                           ║  │
│  ║                    │   需要人工審批?                │                           ║  │
│  ║                    │   (HIGH / CRITICAL 需審批)    │                           ║  │
│  ║                    └───────────────┬───────────────┘                           ║  │
│  ║                          ┌─────────┴─────────┐                                 ║  │
│  ║                         No                  Yes                                ║  │
│  ║                          │                    │                                ║  │
│  ║                          │                    ▼                                ║  │
│  ║                          │   ┌──────────────────────────────────────────────┐  ║  │
│  ║                          │   │            HITLController (人機協作)         │  ║  │
│  ║                          │   │  ┌─────────────┐  ┌─────────────┐            │  ║  │
│  ║                          │   │  │ Approval    │  │   Teams     │            │  ║  │
│  ║                          │   │  │ Handler     │  │ Notification│            │  ║  │
│  ║                          │   │  │ (Redis 或   │  │ (Adaptive   │            │  ║  │
│  ║                          │   │  │  InMemory)  │  │  Card 繁中) │            │  ║  │
│  ║                          │   │  └─────────────┘  └─────────────┘            │  ║  │
│  ║                          │   │  等待審批... (timeout: 30 min)               │  ║  │
│  ║                          │   │  ⚠️ 超時後直接 EXPIRED (無升級邏輯)          │  ║  │
│  ║                          │   │  ⚠️ MULTI 審批定義但 quorum 未強制           │  ║  │
│  ║                          │   │                                              │  ║  │
│  ║                          │   │  ⚠️ V8 發現: 3 套獨立審批系統互不連接:       │  ║  │
│  ║                          │   │     ①AG-UI ApprovalStorage                   │  ║  │
│  ║                          │   │     ②Orchestration HITLController            │  ║  │
│  ║                          │   │     ③Checkpoint ApprovalService              │  ║  │
│  ║                          │   └───────────┬──────────────────────────────────┘  ║  │
│  ║                          │               │ (審批通過)                          ║  │
│  ║                          │   ←───────────┘                                     ║  │
│  ║                          ▼                                                     ║  │
│  ╚══════════════════════════│═════════════════════════════════════════════════════╝  │
│                             │                                                        │
│  ╔══════════════════════════│═════════════════════════════════════════════════════╗  │
│  ║        MAF 編排層 + HybridOrchestratorV2 (Mediator Pattern, Sprint 132)       ║  │
│  ║        73 files, ~18,152 LOC (V8 AST 精確)                                    ║  │
│  ╠══════════════════════════│═════════════════════════════════════════════════════╣  │
│  ║                          ▼                                                     ║  │
│  ║   ┌────────────────────────────────────────────────────────────────────────┐   ║  │
│  ║   │          HybridOrchestratorV2 (1,254 LOC — DEPRECATED facade)         │   ║  │
│  ║   │          └── OrchestratorMediator (Sprint 132 重構):                   │   ║  │
│  ║   │              RoutingHandler → DialogHandler → ApprovalHandler →        │   ║  │
│  ║   │              ExecutionHandler → ContextHandler → ObservabilityHandler  │   ║  │
│  ║   │                                                                        │   ║  │
│  ║   │   FrameworkSelector 決策:                                              │   ║  │
│  ║   │   ┌────────────────────────────────────────────────────────────────┐  │   ║  │
│  ║   │   │ • 結構化任務 (已知模式) ────────────────→ MAF Builder          │  │   ║  │
│  ║   │   │ • 開放式推理 (Extended Thinking) ──────→ Claude SDK Worker     │  │   ║  │
│  ║   │   │ • 混合任務 ────────────────────────────→ MAF 編排 + Claude 執行│  │   ║  │
│  ║   │   │ • 多 Agent 群集 ─────────────────────→ Swarm Mode             │  │   ║  │
│  ║   │   │   ⚠️ Swarm 目前透過獨立 Demo API，非主流程                     │  │   ║  │
│  ║   │   └────────────────────────────────────────────────────────────────┘  │   ║  │
│  ║   │                                                                        │   ║  │
│  ║   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │   ║  │
│  ║   │   │ Checkpoint   │  │ Audit Logger │  │ AG-UI Server │                │   ║  │
│  ║   │   │ (4 系統統一  │  │ (⚠️ InMemory │  │ (SSE Stream  │                │   ║  │
│  ║   │   │  Registry)   │  │  非 DB 持久) │  │  11 事件類型)│                │   ║  │
│  ║   │   └──────────────┘  └──────────────┘  └──────────────┘                │   ║  │
│  ║   │                                                                        │   ║  │
│  ║   │   ⚠️ H-04: ContextBridge._context_cache 無 asyncio.Lock (競爭條件)    │   ║  │
│  ║   └────────────────────────────────┬───────────────────────────────────────┘   ║  │
│  ║                                    │                                           ║  │
│  ║                    ┌───────────────┴───────────────┐                           ║  │
│  ║                    │      Task Dispatcher          │                           ║  │
│  ║                    │   (任務分發到 Worker Pool)    │                           ║  │
│  ║                    └───────┬───────────┬───────────┘                           ║  │
│  ╚════════════════════════════│═══════════│═══════════════════════════════════════╝  │
│                               │           │                                          │
│              ┌────────────────┘           └────────────────┐                         │
│              ▼                                             ▼                         │
│  ╔═══════════════════════════════╗  ╔══════════════════════════════════════════╗    │
│  ║  Claude Worker 執行層          ║  ║        Swarm 群集執行層                  ║    │
│  ║  47 files, ~11,625 LOC        ║  ║        7 files, ~2,202 LOC              ║    │
│  ╠═══════════════════════════════╣  ╠══════════════════════════════════════════╣    │
│  ║  ┌─────────────────────────┐  ║  ║  ┌────────────────────────────────────┐  ║    │
│  ║  │     Worker Pool         │  ║  ║  │        SwarmTracker (693 LOC)      │  ║    │
│  ║  │  AsyncAnthropic Client  │  ║  ║  │  ┌──────────┐  ┌──────────┐       │  ║    │
│  ║  │  ┌──────┐ ┌──────┐     │  ║  ║  │  │ RESEARCH │  │ ANALYST  │       │  ║    │
│  ║  │  │Diag. │ │Remed.│     │  ║  ║  │  │  Worker  │  │  Worker  │  ...  │  ║    │
│  ║  │  │Worker│ │Worker│ ... │  ║  ║  │  └──────────┘  └──────────┘       │  ║    │
│  ║  │  └──────┘ └──────┘     │  ║  ║  │  ┌──────────┐  ┌──────────┐       │  ║    │
│  ║  │  10 built-in tools:    │  ║  ║  │  │  WRITER  │  │ REVIEWER │       │  ║    │
│  ║  │  Read,Write,Edit,Glob, │  ║  ║  │  │  Worker  │  │  Worker  │       │  ║    │
│  ║  │  Grep,Bash,MultiEdit,  │  ║  ║  │  └──────────┘  └──────────┘       │  ║    │
│  ║  │  Task,WebSearch,WebFetch│  ║  ║  └──────────────────┬───────────────┘  ║    │
│  ║  │  Hook Chain:           │  ║  ║                      │                  ║    │
│  ║  │  Approval(90)>Sandbox  │  ║  ║  ClaudeCoordinator (S81)                ║    │
│  ║  │  (85)>RateLimit(70)>   │  ║  ║  TaskAllocator + 並行/序列模式          ║    │
│  ║  │  Audit(50)             │  ║  ║  SwarmEventEmitter (634 LOC)            ║    │
│  ║  └─────────────────────────┘  ║  ║  9 種 SSE 事件即時串流                 ║    │
│  ║  Autonomous Engine:            ║  ║                                        ║    │
│  ║  Analyze→Plan→Execute→Verify   ║  ║  ⚠️ Demo API 使用模擬場景             ║    │
│  ║  + SmartFallback (6 策略)      ║  ║  ⚠️ 非整合到主聊天流程                ║    │
│  ╚════════════════│═══════════════╝  ╚══════════════════════│═════════════════╝    │
│                   │                                         │                       │
│                   └──────────────────┬──────────────────────┘                       │
│                                      │                                              │
│  ╔═══════════════════════════════════│══════════════════════════════════════════╗  │
│  ║                     統一 MCP 工具層 (8 Servers, 64 Tools)                    ║  │
│  ║                     73 files, ~17,000 LOC (V8 AST 精確)                     ║  │
│  ╠═══════════════════════════════════│══════════════════════════════════════════╣  │
│  ║   ┌───────────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │                         MCP Gateway Service                           │  ║  │
│  ║   │   ┌─────────┐  ┌───────┐  ┌────────┐  ┌──────┐  ┌─────┐             │  ║  │
│  ║   │   │  Azure   │  │ Shell │  │Filesys │  │ SSH  │  │LDAP │             │  ║  │
│  ║   │   │MCP Srvr  │  │MCP Srv│  │MCP Srv │  │MCP S │  │MCP S│             │  ║  │
│  ║   │   │ 24 tools │  │2 tools│  │6 tools │  │6 tool│  │6+AD │             │  ║  │
│  ║   │   └─────────┘  └───────┘  └────────┘  └──────┘  └─────┘             │  ║  │
│  ║   │   ┌─────────┐  ┌───────┐  ┌────────┐                                 │  ║  │
│  ║   │   │  n8n    │  │  ADF  │  │  D365  │  ← Phase 34 新增 (S124-S129)    │  ║  │
│  ║   │   │MCP Srv  │  │MCP Srv│  │MCP Srv │                                 │  ║  │
│  ║   │   │ 6 tools │  │8 tools│  │6 tools │                                 │  ║  │
│  ║   │   └─────────┘  └───────┘  └────────┘                                 │  ║  │
│  ║   │                                                                       │  ║  │
│  ║   │   Security: 4-level RBAC (NONE/READ/EXECUTE/ADMIN)                    │  ║  │
│  ║   │   CommandWhitelist: 26 blocked + 65 allowed patterns                  │  ║  │
│  ║   │   ⚠️ H-06: AuditLogger 已建構但未連線到任何 Server                    │  ║  │
│  ║   │   ⚠️ H-12: Shell/SSH HITL enforcement = log-only (不阻擋)            │  ║  │
│  ║   │   ⚠️ Permission default mode = 'log' (非 'enforce')                   │  ║  │
│  ║   └───────────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════════════════════════════════════════════════════╝  │
│                                                                                      │
│  ╔══════════════════════════════════════════════════════════════════════════════╗  │
│  ║                    可觀測性層 + AG-UI 即時串流 (含 Swarm 事件)                ║  │
│  ╠══════════════════════════════════════════════════════════════════════════════╣  │
│  ║   AG-UI SSE 即時串流到前端 (11 event types):                                 ║  │
│  ║   ┌────────────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │ • TEXT_MESSAGE_START/CONTENT/END  → 思考過程顯示                      │  ║  │
│  ║   │ • TOOL_CALL_START/ARGS/END       → 工具調用顯示                      │  ║  │
│  ║   │ • APPROVAL_REQUEST               → 內聯審批卡片                      │  ║  │
│  ║   │ • STATE_SNAPSHOT/DELTA           → 共享狀態更新                      │  ║  │
│  ║   │ • RUN_STARTED/FINISHED           → 執行生命週期                      │  ║  │
│  ║   │ • CUSTOM (swarm_*, workflow_*)   → Swarm + 工作流事件                │  ║  │
│  ║   │                                                                      │  ║  │
│  ║   │ ⚠️ 非真正 token-by-token streaming (LLM 回應完成後分塊模擬 100 char) │  ║  │
│  ║   └────────────────────────────────────────────────────────────────────────┘  ║  │
│  ║                                                                                ║  │
│  ║   Domain Layer (112+ files, 20 modules, ~47,200 LOC):                         ║  │
│  ║   sessions/ (12,272 LOC) | orchestration/ (11,487 LOC, 已棄用)               ║  │
│  ║   workflows/ (DAG 引擎) | agents/ | connectors/ | executions/ | checkpoints/ ║  │
│  ║   ⚠️ C-01: 6/10 domain 模組僅 InMemory (learning, templates, routing...)     ║  │
│  ║                                                                                ║  │
│  ║   Infrastructure (39+ files, ~6,300 LOC):                                     ║  │
│  ║   PostgreSQL (7 models) | Redis (LLM cache + locks) | Checkpoint (4 backends) ║  │
│  ║   ⚠️ messaging/ = STUB (1 行，RabbitMQ 無實現)                                ║  │
│  ╚══════════════════════════════════════════════════════════════════════════════╝  │
│                                                                                      │
│  V8 E2E 流程驗證結果 (22 Agent + 3 Validator 驗證):                                │
│  ══════════════════════════════════════════════════                                  │
│  • Flow 1 Chat Message:    MOSTLY CONNECTED (17 步驟, 需 LLM API Key 配置)         │
│  • Flow 2 Agent CRUD:      FULLY CONNECTED (6 步驟, PostgreSQL 全程持久化)          │
│  • Flow 3 Workflow Execute: MOSTLY CONNECTED (8 步驟, DAG 引擎完整)                 │
│  • Flow 4 HITL Approval:   CONNECTED but FRAGILE (12 步驟, 3 套審批系統互不連接)    │
│  • Flow 5 Swarm:           PARTIALLY CONNECTED (8 步驟, Demo 模擬非真實 LLM)        │
│                                                                                      │
│  ⚠️ 跨流程關鍵問題 (V8 新發現):                                                    │
│  • C-01: 20+ 模組 InMemory 存儲 → 重啟遺失所有運行狀態 (6 Agent 獨立確認)          │
│  • 3 套審批系統: AG-UI / Orchestration HITL / Checkpoint 各自獨立 (Validator 1 發現) │
│  • Mock 預設: SemanticRouter + LLMClassifier 預設使用 Mock → 需配置 API Key          │
│  • H-08: 前端 10 頁面靜默降級到 Mock 假資料，使用者無法區分真假                      │
│  • C-07: PostgresMemoryStorage SQL injection via f-string (Agent C2 發現)            │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.0.1 十一層架構總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IPA Platform：智能體編排平台架構 (V8)                      │
│                    725 .py + 214 .tsx/.ts = 939 files, 308,261 LOC          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║  Layer 1: Frontend (使用者介面)                                       ║  │
│  ║  214 .tsx/.ts | 49,357 LOC | 39 pages | 153 components | 17 hooks  ║  │
│  ╠═══════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                        ║  │
│  ║   React 18 + TypeScript + Vite (port 3005) + ReactFlow + Shadcn UI   ║  │
│  ║   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             ║  │
│  ║   │ Unified  │  │  Agent   │  │   HITL   │  │  Swarm   │             ║  │
│  ║   │ Chat UI  │  │ Dashboard│  │ Approval │  │  Panel   │             ║  │
│  ║   │ (27+comp)│  │          │  │  Cards   │  │(15 comp) │             ║  │
│  ║   └──────────┘  └──────────┘  └──────────┘  └──────────┘             ║  │
│  ║   ┌──────────┐                                                        ║  │
│  ║   │ Workflow │  Stores: authStore | unifiedChatStore | swarmStore     ║  │
│  ║   │ DAG Viz  │  Mock fallback: 115 patterns, 10 pages (H-08)        ║  │
│  ║   │(ReactFlow)│                                                       ║  │
│  ║   └──────────┘                                                        ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │ Fetch API (SSE)                         │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 2: API Gateway (560 endpoints, 52 route files, 47 routers)   ║  │
│  ║  143 .py | 46,133 LOC | FastAPI (port 8000) + 39 API route modules  ║  │
│  ║  Auth: 31 JWT endpoints (5.5%) + protected_router 全域保護           ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 3: AG-UI Protocol (即時 Agent UI + Swarm SSE)                 ║  │
│  ║  24 files, 9,836 LOC | 11 event types | 7 features                  ║  │
│  ║  SharedState, FileAttach, ThreadStore, ExtThinking, HITL, Swarm     ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 4: Input & Routing (輸入閘道 + 意圖路由)                      ║  │
│  ║  ~40 files, ~16,000 LOC | OrchestrationMetrics (OTel)               ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  InputGateway            │   BusinessIntentRouter              │  ║  │
│  ║   │                          │                                     │  ║  │
│  ║   │  • ServiceNow Handler   │   • PatternMatcher   (< 10ms)      │  ║  │
│  ║   │  • Prometheus Handler   │   • SemanticRouter   (< 100ms)     │  ║  │
│  ║   │  • UserInput Handler    │   • LLMClassifier    (< 2000ms)    │  ║  │
│  ║   │  • Schema Validator     │   • CompletenessChecker             │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  GuidedDialog (5 files) │  RiskAssessor (3 files)             │  ║  │
│  ║   │  ~3,050 LOC             │  ~1,200 LOC                         │  ║  │
│  ║   │  • Dialog Engine        │  • 7 維度風險因子                    │  ║  │
│  ║   │  • Context Manager      │  • Risk Policies                    │  ║  │
│  ║   │  • Question Generator   │                                     │  ║  │
│  ║   │  • Refinement Rules     │  HITLController (4 files, ~1,900)   │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 5: Hybrid Orchestration (混合編排層)                           ║  │
│  ║  73 files, 24,252 LOC — Sprint 132 Mediator Pattern 重構            ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │       HybridOrchestratorV2 → Mediator Pattern (6 Handlers)   │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │  ║  │
│  ║   │  │ Framework    │  │ Context      │  │ Unified      │         │  ║  │
│  ║   │  │ Selector     │  │ Bridge       │  │ ToolExecutor │         │  ║  │
│  ║   │  │ (7 files)    │  │ (⚠️ 無鎖)    │  │ (5 files)    │         │  ║  │
│  ║   │  └──────────────┘  └──────────────┘  └──────────────┘         │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │  ║  │
│  ║   │  │ Risk Engine  │  │ Switching    │  │ Checkpoint   │         │  ║  │
│  ║   │  │ (8 files)    │  │ Logic        │  │ Manager (4)  │         │  ║  │
│  ║   │  └──────────────┘  └──────────────┘  └──────────────┘         │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 6: MAF Builder Layer (MAF 編排模式層)                          ║  │
│  ║  57 files, 38,040 LOC — 9 Builder Adapters (7 MAF compliant)       ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  9 Builders (7 with agent_framework import, 100% compliant)  │  ║  │
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
│  ║   │    groupchat_voting, edge_routing, ACL layer (S126-128)       │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 7: Claude SDK Worker Layer (Claude 自主執行層)                 ║  │
│  ║  47 files, 15,180 LOC                                                ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║                              ▼                                        ║  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  ClaudeSDKClient (AsyncAnthropic) — 真實 SDK 整合             │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │  ║  │
│  ║   │  │ Autonomous   │  │ Hook System  │  │ Tool System  │         │  ║  │
│  ║   │  │ (7 files)    │  │ (6 files)    │  │ (10 tools)   │         │  ║  │
│  ║   │  └──────────────┘  └──────────────┘  └──────────────┘         │  ║  │
│  ║   │                                                                │  ║  │
│  ║   │  ┌──────────────┐  ┌──────────────┐                           │  ║  │
│  ║   │  │ MCP Client   │  │ Coordinator  │                           │  ║  │
│  ║   │  │ (manager)    │  │ (4 modes)    │                           │  ║  │
│  ║   │  └──────────────┘  └──────────────┘                           │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════│════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════│════════════════════════════════════════╗  │
│  ║  Layer 8: MCP Tool Layer (統一工具存取層)                             ║  │
│  ║  73 files, 20,920 LOC | 8 servers, 64 tools                         ║  │
│  ╠══════════════════════════════│════════════════════════════════════════╣  │
│  ║   ┌────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │  8 MCP Servers + Core Protocol + Security                     │  ║  │
│  ║   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  ║  │
│  ║   │  │  Azure   │  │  Shell   │  │Filesystem│  │SSH + LDAP│      │  ║  │
│  ║   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │  ║  │
│  ║   │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │  ║  │
│  ║   │  │   n8n    │  │   ADF    │  │   D365   │  (Phase 33 新增)   │  ║  │
│  ║   │  │ (6 tools)│  │ (8 tools)│  │ (6 tools)│                    │  ║  │
│  ║   │  └──────────┘  └──────────┘  └──────────┘                    │  ║  │
│  ║   │  core/: Protocol, Transport, Client, Types                    │  ║  │
│  ║   │  security/: 28 permission patterns, 16 audit modes            │  ║  │
│  ║   └────────────────────────────────────────────────────────────────┘  ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  Layer 9: Supporting Integrations + Swarm (支援整合層)               ║  │
│  ║  ~64 files, ~18,000+ LOC | Swarm 7 files, ~2,750 LOC              ║  │
│  ║  correlation (S130 fixed), rootcause (S130 fixed), patrol, audit  ║  │
│  ║  learning, a2a (S107-110), incident, memory (mem0)                ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  Layer 10: Domain Layer (業務邏輯層)                                  ║  │
│  ║  112+ files, 47,200+ LOC | 20 domain modules                      ║  │
│  ║  sessions (12,272), orchestration (11,487), connectors (3,686)    ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  Layer 11: Infrastructure (基礎設施)                                  ║  │
│  ║  39+ files, ~6,300 LOC | PostgreSQL 16 | Redis 7 | RabbitMQ (空殼) ║  │
│  ║  database (18 files), checkpoint (8 files, 4 backends)            ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  Core: Performance, Sandbox, Security utilities                      ║  │
│  ║  34+ files, ~10,200 LOC | performance (4,772), sandbox (2,555)    ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Layer 1: Frontend (214 files, 49,357 LOC)

**技術棧**: React 18 + TypeScript + Vite + Tailwind CSS + Shadcn UI + ReactFlow + Zustand

| 子目錄 | 檔案數 | 代碼行 | 元件數 | 介面數 | 說明 |
|--------|--------|--------|--------|--------|------|
| pages/ | 40 | 10,467 | 38 | 67 | 39 頁面 (含 DevUI 7 頁) |
| components/ | 137 | 18,538 | 90 | 220 | unified-chat (25+), agent-swarm (16), ag-ui, DevUI, ui (Shadcn) |
| hooks/ | 17 | 5,304 | 16 | 101 | 13 top-level + 4 swarm internal hooks |
| api/ | 6 | 797 | 3 | 65 | Fetch API client (非 Axios) |
| store/ + stores/ | 4 | 1,208 | 3 | 2 | authStore, swarmStore, unifiedChatStore |
| types/ | 3 | 816 | 0 | 87 | TypeScript 型別定義 |
| utils/ + lib/ | 6 | 299 | 2 | 37 | 工具函數 + cn() utility |

**核心元件架構**:

| 元件 | LOC | 職責 | 資料來源 |
|------|-----|------|----------|
| `UnifiedChat.tsx` | ~900 | 主聊天介面，模式切換，orchestration 狀態 | useUnifiedChat, useOrchestration |
| `useUnifiedChat.ts` | ~750 | SSE 連線管理，15 事件類型處理 | Fetch SSE → /api/v1/ag-ui |
| `useOrchestration.ts` | 353 | 意圖分類狀態機 (idle→routing→dialog→risk→executing) | POST /orchestration/intent/classify |
| `SwarmTestPage.tsx` | ~845 | Swarm 測試 (Real + Mock 雙模式) | useSwarmReal / useSwarmMock |
| `WorkflowDAGVisualization` | Sprint 133 | ReactFlow DAG 視覺化 (Phase 34 新增) | workflow definition |

**資料流分析**:
- **API 呼叫**: 99 處 API call sites (AST 偵測)
- **狀態管理**: Zustand (3 stores) + React Query (server state)
- **SSE 串流**: Fetch-based SSE (非 EventSource API)，支援 15 AG-UI event types
- **Mock 降級**: 115 處 mock data patterns (AST 偵測)，10 頁面有靜默 mock fallback (H-08)

**本層問題** (5 issues):
| ID | 問題 | 嚴重度 |
|----|------|--------|
| H-08 | 前端靜默降級 Mock，使用者無法區分真假資料 | HIGH |
| H-11 | Chat 歷史僅 localStorage，瀏覽器清除即遺失 | HIGH |
| H-15 | 缺少 React Error Boundaries (5+ 元件) | HIGH |
| L-01 | ui/index.ts 僅匯出 3/18 元件 | LOW |
| L-16 | UnifiedChat.tsx 含 2 處 TODO 註解 | LOW |

---

### 2.2 Layer 2: API Gateway (143 files, 46,133 LOC, 560 endpoints)

**技術棧**: FastAPI + Pydantic v2 + SQLAlchemy 2.0 async

| 維度 | 數值 | 說明 |
|------|------|------|
| 路由檔案 | 52 | 跨 39 modules |
| 註冊 Router | 47 | api_router 聚合 |
| 端點總數 | 560 | AST 掃描 |
| 有 Auth 端點 | 31 (5.5%) | JWT require_auth |
| 無 Auth 端點 | 529 (94.5%) | protected_router 全域保護 |
| 類別 | 701 | Pydantic models + route classes |
| 函數 | 896 | 全部已實現 (0 空函數) |

**模組分類**:

| 類別 | 模組 | 端點數 | 資料來源 | 狀態 |
|------|------|--------|----------|------|
| 核心 CRUD | agents, workflows, executions, sessions | ~80 | PostgreSQL | COMPLETE |
| 聊天/串流 | ag_ui, orchestration | ~30 | SSE + orchestrator | COMPLETE |
| 開發工具 | devtools (12 endpoints) | 12 | InMemory | COMPLETE |
| 可觀測性 | audit, patrol, correlation, rootcause | ~40 | ⚠️ API MOCK | SPLIT |
| MCP/工具 | mcp, sandbox, files | ~25 | MCP servers | COMPLETE |
| Swarm | swarm (8 endpoints) | 8 | InMemory | COMPLETE |
| 認證 | auth | ~5 | JWT + bcrypt | COMPLETE |
| 記憶 | memory (7 endpoints) | 7 | mem0 + Qdrant | COMPLETE |
| 其他 | dashboard, cache, connectors, templates... | ~350+ | Mixed | COMPLETE |

**Auth 架構 (Sprint 111)**:
```
api_router (/api/v1)
├── public_router → auth_router only (login, register)
└── protected_router → Depends(require_auth) → JWT 驗證
    ├── 輕量驗證: decode JWT → {user_id, role, email} (無 DB 查詢)
    └── 完整驗證: get_current_user → DB User model (需要時)
```

**本層問題** (8 issues):
| ID | 問題 | 嚴重度 |
|----|------|--------|
| C-02 | correlation/ API 100% Mock (7 endpoints) | CRITICAL |
| C-03 | autonomous/ API 100% Mock (UAT stub) | CRITICAL |
| C-04 | rootcause/ API 100% Mock (4 endpoints) | CRITICAL |
| C-05 | patrol/ API 100% Mock (9 endpoints) | CRITICAL |
| H-01 | cache clear, connector execute 無 RBAC | HIGH |
| H-02 | ag_ui /test/* 不受 APP_ENV 環境限制 | HIGH |
| M-03 | Dashboard chart N+1 查詢 (7天×3查詢=21) | MEDIUM |
| M-04 | Dashboard stats 靜默吞掉異常 | MEDIUM |

---

### 2.3 Layer 3: AG-UI Protocol (24 files, 9,836 LOC)

**定位**: AG-UI 協議實現層，提供 SSE 串流通訊框架

| 子模組 | 檔案數 | LOC | 職責 |
|--------|--------|-----|------|
| events/ | 5 | ~1,500 | 11 AG-UI event types (Pydantic models) |
| converters/ | 3 | ~1,200 | Result → AG-UI event 轉換 |
| bridge.py | 1 | 1,080 | HybridEventBridge — SSE 串流核心 |
| features/ | 4 | ~2,500 | Agentic Chat, Tool Rendering, HITL, Gen UI |
| features/advanced/ | 3 | ~1,500 | Tool UI, Shared State, Predictive State |
| thread/ | 3 | ~1,200 | Thread CRUD (InMemory + Redis) |

**AG-UI 協議完整性**:

| AG-UI Feature | 狀態 | 實現 |
|---------------|------|------|
| RUN_STARTED / RUN_FINISHED | ✅ | lifecycle.py, bridge.py |
| TEXT_MESSAGE_START/CONTENT/END | ✅ | message.py, converters.py |
| TOOL_CALL_START/ARGS/END | ✅ | tool.py, converters.py |
| STATE_SNAPSHOT / STATE_DELTA | ✅ | state.py, shared_state.py |
| CUSTOM events | ✅ | heartbeat, workflow_progress, approval_*, mode_switch |
| SSE streaming | ✅ | `data: {json}\n\n` format |
| Thread management | ✅ | InMemory (dev) + Redis (prod) Write-Through cache |
| HITL approval flow | ✅ | human_in_loop.py (745 LOC) |

**增強功能** (超出 Phase 15 計畫):

| 增強 | Sprint | 說明 |
|------|--------|------|
| HITL tool event | S66 | 高風險工具偵測 + HITL_APPROVAL_REQUIRED |
| Heartbeat | S67 | SSE keepalive 防斷線 |
| Step progress | S69 | 子步驟進度追蹤 + 節流 |
| File attachments | S75 | 多模態 (images, PDFs, text) |
| Swarm events | S101 | Agent Swarm SSE + throttle/batch |
| Redis thread | S119 | 生產環境持久化 thread 儲存 |

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| C-08 | API key prefix 暴露於 AG-UI 回應 | CRITICAL |
| C-01 | 4 個獨立 InMemory stores (Approval, Chat, SharedState, Predictive) | CRITICAL |
| M-10 | StateDeltaOperation(str) 應改用 Enum | MEDIUM |

---

### 2.4 Layer 4: Orchestration / Intent Routing (~40 files, ~16,000 LOC)

**定位**: 三層瀑布式意圖路由 + 完整性檢查 + 引導對話

| 子模組 | 檔案/LOC | 職責 |
|--------|---------|------|
| pattern_matcher/ | 3 files, ~900 LOC | L1: 30+ regex 規則 (YAML), 雙語 (EN+ZH-TW) |
| semantic_router/ | 3 files, ~1,200 LOC | L2: Embedding 相似度路由 |
| llm_classifier/ | 3 files, ~1,100 LOC | L3: LLM 意圖分類 (Azure OpenAI) |
| intent_router/ | 2 files, ~800 LOC | BusinessIntentRouter 協調器 |
| completeness/ | 3 files, ~1,000 LOC | 關鍵字段完整性檢查 |
| guided_dialog/ | 3 files, ~1,200 LOC | 多輪模板對話引擎 |
| input_gateway/ | 2 files, ~600 LOC | 輸入預處理 + 安全檢查 |
| metrics.py | 1 file, ~893 LOC | OrchestrationMetrics (OTel + fallback) |
| risk/ | 4 files, ~1,500 LOC | RiskAssessor 7 維度風險引擎 |
| hitl/ | 3 files, ~2,213 LOC | HITLController + Teams 通知 |

**三層路由效能分析**:

| 層級 | 延遲 | 信心閾值 | 資料來源 | 預設狀態 |
|------|------|----------|----------|----------|
| L1 Pattern | <10ms | ≥0.90 | 30+ YAML regex rules | REAL |
| L2 Semantic | <100ms | ≥0.85 | Embedding model | ⚠️ Mock (需配置) |
| L3 LLM | <2000ms | N/A | Azure OpenAI | ⚠️ Mock (需配置) |

**意圖分類 → 工作流映射**:

| Intent | Sub-Intent | Workflow Type | Risk Level |
|--------|-----------|---------------|------------|
| INCIDENT | system_unavailable, system_down | MAGENTIC | CRITICAL |
| INCIDENT | other | SEQUENTIAL | MEDIUM-HIGH |
| CHANGE | release_deployment, database_change | MAGENTIC | HIGH |
| CHANGE | other | SEQUENTIAL | MEDIUM |
| REQUEST | any | SIMPLE | LOW |
| QUERY | any | SIMPLE | LOW |
| UNKNOWN | any | HANDOFF | — |

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| M-06 | ~~report_generator.py 含空函數體~~ **(V9 已修復: 8 個函數均已實現)** | ~~MEDIUM~~ RESOLVED |
| C-01 | OrchestrationMetrics, Dialog sessions = InMemory | CRITICAL |

---

### 2.5 Layer 5: Hybrid Orchestrator (73 files, 24,252 LOC)

**定位**: MAF + Claude SDK 混合編排核心，動態框架選擇與上下文同步

| 子模組 | 檔案數 | LOC | 職責 |
|--------|--------|-----|------|
| intent/ | 7 | 1,223 | FrameworkSelector, 分類器, 分析器 |
| context/ | 10 | 3,080 | ContextBridge (932 LOC), 同步器, 映射器 |
| risk/ | 8 | 2,422 | RiskAssessmentEngine (560 LOC), 3 scoring strategies |
| execution/ | 5 | ~1,500 | UnifiedToolExecutor, 工具路由 |
| switching/ | 9 | ~2,000 | 框架切換 (user/failure/resource/complexity triggers) |
| checkpoint/ | 9 | ~2,000 | 4 backends (Memory/Redis/PostgreSQL/Filesystem) |
| hooks/ | 5 | ~1,200 | Pre/post execution hooks |
| orchestrator/ (Sprint 132) | 8 | ~3,500 | OrchestratorMediator + 6 Handlers |
| orchestrator_v2.py | 1 | 1,254 | DEPRECATED God Object → 代理到 Mediator |
| claude_maf_fusion.py | 1 | 892 | Claude 決策嵌入 MAF workflow |
| swarm_mode.py | 1 | ~500 | Swarm 執行模式 |

**Sprint 132 Mediator Pattern 重構**:

```
Before (V7):                          After (V8, Sprint 132):
HybridOrchestratorV2 (God Object)     OrchestratorMediator
├── 13 injectable dependencies         ├── RoutingHandler
├── 1,254 LOC monolith                 ├── DialogHandler
├── 直接耦合所有組件                     ├── ApprovalHandler
└── 難以測試和維護                       ├── ExecutionHandler
                                        ├── ContextHandler
                                        └── ObservabilityHandler
```

**FrameworkSelector 選擇策略** (`SelectionStrategy` enum):

| 策略 | 說明 | 預設 |
|------|------|------|
| `CAPABILITY_BASED` | 基於任務能力動態選擇 | ✅ 預設 |
| `PREFER_CLAUDE` | 始終偏好 Claude SDK | |
| `PREFER_MICROSOFT` | 始終偏好 MAF | |
| `COST_OPTIMIZED` | 成本最佳化 | |
| `PERFORMANCE_OPTIMIZED` | 效能最佳化 | |

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| H-04 | ContextBridge._context_cache 無 asyncio.Lock | HIGH |
| H-05 | Checkpoint storage 使用非官方 API | HIGH |
| C-01 | Memory checkpoint 為預設 (重啟遺失) | CRITICAL |

---

### 2.6 Layer 6: MAF Builder (57 files, 38,040 LOC)

**定位**: Microsoft Agent Framework 官方 API 封裝層

> **V8.1 更新 — MAF RC4 升級影響 (2026-03-16)**:
> - **MAF 版本**: `agent-framework>=1.0.0rc4,<2.0.0` (原 `1.0.0b260114`)
> - **Import 路徑遷移**: 6 條 Orchestration Builder import 從頂層遷移至 `agent_framework.orchestrations` 子模組
>   - `from agent_framework.orchestrations import ConcurrentBuilder` (concurrent.py)
>   - `from agent_framework.orchestrations import HandoffBuilder` (handoff.py)
>   - `from agent_framework.orchestrations import GroupChatBuilder` (groupchat.py)
>   - `from agent_framework.orchestrations import MagenticBuilder` (magentic.py, planning.py)
>   - 其餘核心類別 (Workflow, Edge, Agent, WorkflowExecutor 等) 仍從頂層 `agent_framework` import (RC4 re-export，GA 可能移除)
> - **Builder Constructor API 變更**: Fluent API → kwarg 方式
>   - 修正前: `Builder()` + `.participants(list)` (fluent chain)
>   - 修正後: `Builder(participants=list)` (constructor kwarg)
>   - 影響: MagenticBuilder, ConcurrentBuilder, GroupChatBuilder, HandoffBuilder
> - **類別重命名 (向後相容別名)**:
>   - `ChatAgent` → `Agent` (使用 `Agent as ChatAgent`)
>   - `ChatMessage` → `Message` (使用 `Message as ChatMessage`)
>   - `WorkflowStatusEvent` → `WorkflowEvent` (使用 `WorkflowEvent as WorkflowStatusEvent`)
>   - `ContextProvider` → `BaseContextProvider` (使用 `BaseContextProvider as ContextProvider`)
> - **ACL Layer**: `acl/adapter.py` 新增 `agent_framework.orchestrations` 子模組 fallback 映射
> - **驗證**: 17/17 integration tests pass, 221/222 adapter unit tests pass (詳見 `sdk-version-gap/POST-UPGRADE-Verification-Consensus.md`)

**合規性審計結果**: 7/7 Primary Builders **COMPLIANT** (RC4 import 路徑 + constructor 已更新)

| Builder | LOC | 職責 | 合規 |
|---------|-----|------|------|
| `workflow_executor.py` | ~1,800 | 工作流執行引擎 | ✅ |
| `handoff.py` | ~1,200 | Agent 切換 | ✅ |
| `groupchat.py` | ~1,500 | 群聊編排 | ✅ |
| `magentic.py` | ~1,600 | MagenticOne 動態規劃 | ✅ |
| `concurrent.py` | 1,633 | 並行執行 Worker Pool | ✅ |
| `nested_workflow.py` | ~1,000 | 巢狀工作流 | ✅ |
| `planning.py` | ~900 | 規劃整合 | ✅ |

**擴展 Builder** (非 MAF 直接封裝):

| Builder | LOC | 職責 |
|---------|-----|------|
| `handoff_hitl.py` | ~800 | HITL 審批切換 |
| `handoff_policy.py` | ~700 | 策略切換 |
| `handoff_capability.py` | ~600 | 能力匹配切換 |
| `handoff_context.py` | ~500 | 上下文切換 |
| `handoff_service.py` | ~500 | 服務路由切換 |
| `groupchat_voting.py` | ~700 | 投票機制 |
| `groupchat_orchestrator.py` | ~600 | 群聊編排器 |
| `edge_routing.py` | ~500 | 邊緣路由 |

**Core 模組** (9 files):

| 檔案 | LOC | 職責 |
|------|-----|------|
| `core/workflow.py` | ~800 | Workflow 原語 |
| `core/executor.py` | ~700 | 執行器基類 |
| `core/edge.py` | ~500 | 邊緣定義 |
| `core/events.py` | ~600 | 事件系統 |
| `core/state_machine.py` | ~500 | 狀態機 |
| `core/context.py` | ~400 | 上下文管理 |
| `core/execution.py` | ~400 | 執行管理 |
| `core/approval.py` | ~500 | 審批流程 |
| `core/approval_workflow.py` | ~400 | 審批工作流 |

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| C-07 | postgres_storage.py f-string SQL injection **(V9 修正: 檔名為 postgres_storage.py; 已添加 `_validate_table_name()` regex 驗證，風險降低)** | CRITICAL→MEDIUM |
| H-05 | Checkpoint storage 非官方 API (save/load/delete) | HIGH |
| W-1 | edge_routing.py 缺少 MAF imports | WARNING |
| R8 | *(V8.1 新增)* GA 升級風險：15 條頂層 import 在 RC4 仍有效 (re-export)，GA 可能移除 | MEDIUM |
| R6 | *(V8.1 新增)* BC-11/15/16 行為變更 (Checkpoint source_id, 模型重構, 輸出標準化) 未經功能測試驗證 | MEDIUM |

---

### 2.7 Layer 7: Claude SDK (47 files, 15,180 LOC)

**定位**: Anthropic Claude SDK 真正整合層 (非 Mock)

> **V8.1 更新 — Claude SDK 同步更新 (2026-03-16)**:
> - **anthropic 依賴**: `anthropic>=0.84.0` 正式加入 `requirements.txt` (原僅隱含依賴)
> - **預設模型 ID**: `claude-haiku-4-5-20251001` (client.py:38) — 經 commit `944034d` 修正，原升級時誤設為不存在的 `claude-sonnet-4-6-20260217`
> - **Extended Thinking header**: `interleaved-thinking-2025-05-14` (client.py:259) — 原 `extended-thinking-2025-04-30`
> - **殘留問題 (R1)**: 5 個源碼檔 + 8 個測試檔仍用舊模型 ID `claude-sonnet-4-20250514`，待下個 Sprint 統一
> - **殘留問題 (R5)**: client.py:221 docstring 仍提及 `extended-thinking`，應更新為 `interleaved-thinking`

**模組架構**:

| 子模組 | 檔案數 | LOC | 職責 |
|--------|--------|-----|------|
| Root (client, query, session, config, types) | 7 | ~3,500 | AsyncAnthropic client, agentic loop, session |
| hooks/ | 5 | ~1,800 | ApprovalHook, AuditHook, RateLimitHook, SandboxHook |
| tools/ | 5 | ~2,000 | 10 built-in tools (Read/Write/Edit/Glob/Grep/Bash/Task/WebSearch/WebFetch/MultiEdit) |
| mcp/ | 7 | ~3,000 | MCPStdioServer, MCPHTTPServer, MCPManager, Discovery |
| autonomous/ | 6 | ~2,000 | Analyzer → Planner → Executor → Verifier (Sprint 79) |
| hybrid/ | 5 | ~1,200 | CapabilityMatcher → FrameworkSelector |
| orchestrator/ | 4 | ~1,500 | ClaudeCoordinator multi-agent (Sprint 81) |

**核心功能**:
- `ClaudeSDKClient.query()` → 單次 agentic loop (工具呼叫 → 執行 → 回傳)
- `ClaudeSDKClient.create_session()` → 多輪 agentic loop
- `execute_with_thinking()` → Extended Thinking 串流 (Sprint 104)
- `send_with_attachments()` → 多模態附件 (Sprint 75)
- Hook Chain: Approval (priority 90) → Audit → RateLimit → Sandbox

**MCP 整合**:
- 2 Transport: Stdio (local process) + HTTP (remote)
- MCPManager: 多 Server 生命週期管理
- Tool Discovery: 跨 Server 工具索引 + 衝突解決 (prefix naming)
- Exception Hierarchy: 11 specialized exceptions

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| M-07 | Session.query() streaming 參數接受但未實現 | MEDIUM |
| M-08 | Registry MCP tool integration = TODO stub | MEDIUM |
| C-01 | Session state, conversation = InMemory | CRITICAL |

---

### 2.8 Layer 8: MCP Gateway (73 files, 20,920 LOC)

**定位**: Model Context Protocol 統一工具存取層

**8 MCP Servers 概覽**:

| Server | Tools | LOC | 外部 SDK | Sprint | 連線模式 |
|--------|-------|-----|----------|--------|----------|
| **Azure** | 24 | ~2,700 | azure-identity, azure-mgmt-* | Phase 9-10 | Azure SDK (DefaultAzureCredential) |
| **Filesystem** | 6 | ~1,300 | pathlib (stdlib) | Phase 9-10 | Local OS |
| **Shell** | 2 | ~700 | subprocess (stdlib) | Phase 9-10 | Local process |
| **LDAP** | 6+AD | ~2,000 | ldap3 | Phase 9-10, S114 | LDAP server |
| **SSH** | 6 | ~1,500 | paramiko | Phase 9-10 | Remote SSH/SFTP |
| **n8n** | 6 | ~1,100 | httpx | S124 | n8n REST API |
| **ADF** | 8 | ~1,300 | httpx + MSAL | S125 | Azure Data Factory REST |
| **D365** | 6 | ~1,800 | httpx + OAuth2 | S129 | Dynamics 365 OData v4 |
| **Total** | **64** | **~12,400** | — | — | — |

**Permission Model (4-level RBAC)**:

| Level | 權限 | 允許操作 |
|-------|------|----------|
| 0 (NONE) | 無權限 | — |
| 1 (READ) | 唯讀 | list, get, search |
| 2 (EXECUTE) | 執行 | activate, execute, trigger |
| 3 (ADMIN) | 管理 | delete, write, configure |

**安全特性**:
- 每工具明確 PERMISSION_LEVELS 定義
- deny-first 評估策略
- glob pattern 支援
- dual-mode: log (預設) / enforce
- Filesystem sandbox: 多層路徑驗證 + pattern 阻擋 + 大小限制

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| H-06 | MCP AuditLogger 未接線 (8 servers) | HIGH |
| H-12 | Shell/SSH HITL = log-only (不阻擋) | HIGH |
| H-13 | Azure run_command 可執行任意 VM 指令 | HIGH |
| M-05 | ServiceNow server 未呼叫 set_permission_checker() **(V9 路徑修正: mcp/servicenow_server.py, 非 mcp/servers/)** | MEDIUM |

---

### 2.9 Layer 9: Swarm / Supporting Integrations (~64 files, ~18,000+ LOC)

**定位**: Agent Swarm 系統 + 支援性整合模組

**Swarm 子系統** (7 files, ~2,800 LOC):

| 元件 | LOC | 職責 |
|------|-----|------|
| `tracker.py` | ~694 | Swarm/Worker 狀態管理 (InMemory + optional Redis) |
| `swarm_integration.py` | ~405 | ClaudeCoordinator ↔ SwarmTracker 橋接 |
| `events/emitter.py` | ~635 | 9 事件類型 + AG-UI CustomEvent 橋接 |
| `events/types.py` | ~400 | SwarmCreated, WorkerUpdate, SwarmCompleted... |
| `models.py` | ~300 | WorkerType (9), WorkerStatus (7), SwarmMode (3) |

**SwarmMode**: SEQUENTIAL / PARALLEL / HIERARCHICAL
**WorkerType**: RESEARCH, WRITER, DESIGNER, REVIEWER, COORDINATOR, ANALYST, CODER, TESTER, CUSTOM

**其他支援模組**:

| 模組 | Files | LOC | 狀態 | 資料來源 |
|------|-------|-----|------|----------|
| patrol/ | 11 | ~2,900 | COMPLETE | psutil, filesystem, HTTP |
| incident/ | 6 | 2,105 | COMPLETE | correlation + rootcause + LLM |
| correlation/ | 6 | 2,187 | FIXED (S130) | Azure Monitor / App Insights |
| rootcause/ | 5 | ~1,500 | FIXED (S130) | CaseRepository + 15 seed cases |
| memory/ | 5 | 1,817 | COMPLETE | mem0 + Qdrant + Redis + PostgreSQL |
| learning/ | 5 | 1,497 | COMPLETE | mem0 memory + embeddings |
| llm/ | 6 | 1,771 | COMPLETE | Azure OpenAI via openai SDK |
| audit/ | 4 | 1,170 | COMPLETE | InMemory (無 DB 持久化) |
| a2a/ | 4 | 892 | COMPLETE | InMemory (無外部 transport) |
| n8n/ | 3 | 1,191 | COMPLETE | n8n REST API via httpx |
| shared/ | 2 | ~300 | COMPLETE | Protocol definitions |

**Sprint 130 關鍵修復 (V7 → V8 最大變化)**:
- **Before**: Correlation `_get_event()` 等回傳虛構資料, RootCause 硬編碼 2 個 HistoricalCase
- **After**: Correlation 使用 `EventDataSource` 背接 Azure Monitor/App Insights REST API; RootCause 使用 `CaseRepository` + `CaseMatcher` + 15 真實 IT Ops seed cases
- **降級策略**: 外部服務不可用時回傳空結果 (不再回傳假資料)

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| C-01 | audit/, a2a/, swarm tracker = InMemory | CRITICAL |
| M-09 | CaseRepository PostgreSQL = interface-only (fallback InMemory) | MEDIUM |

---

### 2.10 Layer 10: Domain Layer (112+ files, ~47,200+ LOC, 20 modules)

**定位**: 業務邏輯層，包含核心領域模型和服務

| 模組 | Files | LOC | 類別 | 函數 | 持久化 | 說明 |
|------|-------|-----|------|------|--------|------|
| sessions/ | 33 | 12,272 | 80+ | 300+ | PostgreSQL + Redis | 最大最關鍵，SessionAgentBridge |
| orchestration/ | 22 | 11,487 | 82 | 424 | Mixed | ⚠️ 已棄用但仍引用 |
| connectors/ | 6 | 3,686 | 10 | 90 | InMemory | ServiceNow, JIRA, SAP |
| agents/ | 7 | 1,911 | 16 | 53 | PostgreSQL | Agent CRUD + Registry |
| checkpoints/ | 3 | 1,020 | 5 | 26 | DB + InMemory | CheckpointService |
| notifications/ | 2 | 816 | 7 | 25 | N/A | Teams webhook (httpx) |
| devtools/ | 2 | 803 | 9 | 30 | InMemory | ExecutionTracer |
| audit/ | 2 | 760 | 7 | 24 | InMemory | AuditLogger (FIFO) |
| learning/ | 2 | 680 | 5 | 27 | InMemory | Few-shot learning |
| routing/ | 2 | 689 | 7 | 22 | InMemory | ScenarioRouter |
| prompts/ | 2 | 599 | 7 | 24 | InMemory | PromptTemplate |
| files/ | 3 | 557 | 3 | 28 | Filesystem | FileService |
| executions/ | 2 | 467 | 3 | 21 | PostgreSQL | StateMachine |
| sandbox/ | 2 | 365 | 5 | 14 | InMemory | Simulated sandbox |
| auth/ | 3 | 353 | 7 | 8 | PostgreSQL | User + Role models |
| templates/ | 2 | ~400 | 5 | 20 | InMemory | WorkflowTemplate |
| triggers/ | 2 | ~350 | 5 | 18 | InMemory | TriggerManager |
| versioning/ | 2 | ~350 | 5 | 16 | InMemory | VersionManager |
| workflows/ | 11 | ~3,000+ | 30+ | 100+ | PostgreSQL | DAG engine + parallel |

**sessions/ 模組深度分析** (最大模組, 33 files, 12,272 LOC):

```
SessionAgentBridge (bridge.py, ~850 LOC)
├── SessionService (service.py, ~620 LOC)
│   ├── SessionRepository → SQLAlchemy/PostgreSQL
│   ├── SessionCache → Redis
│   └── SessionEventPublisher
├── AgentExecutor (executor.py)
│   ├── StreamingLLMHandler (streaming.py)
│   └── ConversationManager
├── ToolCallHandler (tool_handler.py)
│   └── ToolApprovalManager (approval.py)
├── SessionErrorHandler (error_handler.py)
├── SessionRecoveryManager (recovery.py)
└── MetricsCollector (metrics.py)
```

**workflows/ 並行執行架構**:

| 類別 | LOC | 說明 |
|------|-----|------|
| `ConcurrentExecutor` | ~580 | 並行分支執行，configurable max concurrency |
| `ConcurrentStateManager` | ~600 | 並行執行狀態追蹤 (Singleton) |
| `ParallelForkGateway` | ~700 | Fork-Join 模式，4 Join strategies, 4 Merge strategies |

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| C-01 | 6/10 modules InMemory only (learning, templates, routing, triggers, versioning, prompts) | CRITICAL |
| H-09 | Sandbox 模擬 (無真正 process isolation) | HIGH |
| H-10 | domain/orchestration 已棄用但仍被 API 引用 | HIGH |
| H-03 | DeadlockDetector, MetricsCollector 等 Singleton anti-pattern | HIGH |

---

### 2.11 Layer 11: Infrastructure (39+ files, ~6,300 LOC)

**定位**: 資料庫、快取、訊息佇列、儲存基礎設施

| 子模組 | Files | LOC | 職責 | 狀態 |
|--------|-------|-----|------|------|
| database/ | 18 | 2,793 | SQLAlchemy 2.0 async + models + repositories | COMPLETE |
| checkpoint/ | 8 | 1,876 | 4 backends (Memory/Redis/PG/FS) | COMPLETE |
| cache/ | 2 | 626 | Redis integration + fallback | COMPLETE |
| storage/ | 6 | ~800 | Protocol-based storage abstraction | COMPLETE |
| messaging/ | 1 | 2 | ⚠️ STUB (1 行: `# Messaging infrastructure`) | STUB |
| redis_client.py | 1 | ~300 | Centralized Redis client (Sprint 119) | COMPLETE |

**Database 架構**:
- SQLAlchemy 2.0 async engine
- Alembic migrations
- 5 ORM Models: Agent, Workflow, Execution, Session, User
- 5 Repositories: AgentRepository, WorkflowRepository, ExecutionRepository, SessionRepository, UserRepository
- Connection pooling + async session factory

**Core 模組** (34+ files, ~10,200 LOC):

| 子模組 | Files | LOC | 職責 |
|--------|-------|-----|------|
| performance/ | 9 | 4,772 | Benchmark, concurrent optimizer, profiler, metrics |
| sandbox/ | 7 | 2,555 | Process sandbox + IPC + config |
| security/ | 4 | 724 | JWT, bcrypt, data masking, sensitive filter |
| observability/ | 4 | 699 | OpenTelemetry, Azure Monitor, metrics |
| logging/ | 4 | 426 | Structured JSON logging, request correlation |
| auth.py | 1 | 115 | require_auth JWT dependency (Sprint 111) |
| config.py | 1 | 223 | Pydantic Settings (100+ config fields) |
| factories.py | 1 | 188 | ServiceFactory (environment-aware) |

**本層問題**:
| ID | 問題 | 嚴重度 |
|----|------|--------|
| C-06 | messaging/ STUB (RabbitMQ 計畫但無實現) | CRITICAL |
| H-14 | Rate limiter 使用 InMemory (多 worker 無效) | HIGH |
| M-02 | Health check 使用 os.environ 違反 pydantic Settings 規則 | MEDIUM |

---

### 2.12 資料流概覽

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
│  (意圖路由)     │    ⚠️ SemanticRouter/LLMClassifier 預設 Mock，需 API Key 啟用真實版
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
│  RiskAssessor   │ ← 7 維度風險因子評估
│  (風險評估)     │
└────────┬────────┘
         │ RiskLevel: LOW / MEDIUM / HIGH / CRITICAL
         │
    ┌────┴────┐
    │ 需要    │
    │ 審批?   │
    └────┬────┘
    No   │  Yes → HITLController → Teams Notification → 等待審批
         │          ⚠️ 3 套審批系統互不連接 (AG-UI / Orchestration HITL / Checkpoint)
         │       ←────────┘ (審批通過)
         ▼
┌─────────────────────────┐
│ HybridOrchestratorV2    │ ← Mediator Pattern (Sprint 132 重構)
│ ┌─────────────────────┐ │
│ │ FrameworkSelector   │ │ ← 選擇 MAF 模式 / Claude 自主 / Swarm
│ │ ContextBridge       │ │ ← 上下文同步 (⚠️ 無 asyncio.Lock — H-04)
│ │ UnifiedToolExecutor │ │ ← 統一工具路由
│ │ CheckpointManager   │ │ ← 4 個 Checkpoint backends
│ └─────────────────────┘ │
└────────────┬────────────┘
             │
    ┌────────┼────────────────┐
    │        │                │
    ▼        ▼                ▼
┌─────────┐ ┌──────────┐ ┌──────────────┐
│   MAF   │ │  Claude  │ │   Swarm      │
│ Builder │ │  SDK     │ │  Tracker     │
│ (9 種,  │ │ (Async   │ │ (9 Worker    │
│  7 合規)│ │ Anthropic)│ │   Types)    │
└────┬────┘ └────┬─────┘ └──────┬───────┘
     │           │               │
     └─────┬─────┘               │
           │                     │
           ▼                     │
    ┌──────────────┐             │
    │  MCP Layer   │ ← 8 MCP Servers, 64 tools
    │  (工具執行)  │    28 permission patterns, 16 audit modes
    └──────┬───────┘
           │
           ▼                     │
    ┌──────────────┐             │
    │ AG-UI SSE    │ ←───────────┘  SwarmEventEmitter (9 事件類型)
    │ (結果回傳)   │
    └──────────────┘
```

**持久化分層**:

| 資料類型 | 儲存 | 持久性 |
|----------|------|--------|
| Agent/Workflow/Execution/Session | PostgreSQL | ✅ 持久 |
| LLM Cache, Session Cache | Redis | ⚠️ TTL |
| Audit, Learning, Templates, Routing | InMemory | ❌ 重啟遺失 |
| Chat History (前端) | localStorage | ❌ 瀏覽器清除遺失 |
| MCP Permissions, Approval State | InMemory | ❌ 重啟遺失 |
| Checkpoints | 4 backends (預設 Memory) | ❌ 預設重啟遺失 |

---

## 3. 核心能力矩陣

### 3.1 Agent 編排能力

**MAF Builder 合規性**: 7/7 Primary Builders COMPLIANT (100%)

| Builder | 類型 | LOC | MAF API 合規 | 功能說明 |
|---------|------|-----|-------------|----------|
| workflow_executor | Primary | ~1,800 | ✅ | DAG 工作流執行，節點遍歷，狀態追蹤 |
| handoff | Primary | ~1,200 | ✅ | Agent 切換，上下文傳遞，策略路由 |
| groupchat | Primary | ~1,500 | ✅ | 群聊編排，輪次管理，發言策略 |
| magentic | Primary | ~1,600 | ✅ | MagenticOne 動態規劃，任務分解 |
| concurrent | Primary | 1,633 | ✅ | 並行 Worker Pool，4 模式 (ALL/ANY/MAJORITY/FIRST_SUCCESS) |
| nested_workflow | Primary | ~1,000 | ✅ | 巢狀工作流，子流程管理 |
| planning | Primary | ~900 | ✅ | 規劃整合，步驟生成 |

**擴展能力** (非 MAF 直接封裝):
- 6 個 Handoff 變體 (hitl, policy, capability, context, service, migration)
- 3 個 GroupChat 變體 (voting, orchestrator, migration)
- Edge routing, Code interpreter
- 5 個 Migration shims (Phase 2 向後相容)

**編排模式支援**:

| 模式 | 實現 | 說明 |
|------|------|------|
| 順序執行 | ✅ | Workflow DAG 線性遍歷 |
| 並行執行 | ✅ | ConcurrentBuilder + Gateway |
| 動態規劃 | ✅ | MagenticOne 動態步驟 |
| Agent 切換 | ✅ | 6 種 Handoff 策略 |
| 群聊協作 | ✅ | 投票 + 編排器 |
| 巢狀工作流 | ✅ | 子流程嵌入 |
| 人工審批 | ✅ | HITL + Teams 通知 |

---

### 3.2 Human-in-the-Loop 能力

**三套審批系統**:

| 系統 | 位置 | LOC | 儲存 | 觸發條件 |
|------|------|-----|------|----------|
| **Orchestration HITL** | orchestration/hitl/ | ~2,213 | InMemory + Redis | RiskAssessor HIGH/CRITICAL |
| **AG-UI HITL** | ag_ui/features/human_in_loop.py | 745 | InMemory (asyncio.Lock) | 高風險工具偵測 |
| **Claude SDK ApprovalHook** | claude_sdk/hooks/approval.py | ~300 | Hook chain | Write/Edit/Bash/Task 工具 |

**風險評估引擎** (`RiskAssessmentEngine`, 560 LOC):

| 維度 | 說明 | 基準風險 |
|------|------|----------|
| Tool risk | 工具固有風險 | Write=0.4, Bash=0.6 |
| Data sensitivity | 資料敏感度 | 依內容分析 |
| Operation scope | 操作範圍 | 系統級 > 檔案級 |
| User authorization | 使用者授權等級 | 依角色 |
| Historical patterns | 歷史行為模式 | 異常偵測 |
| Environment context | 環境上下文 | prod > dev |
| Compliance requirements | 合規要求 | 依行業 |

**風險等級 → 審批要求**:

| 風險等級 | 分數範圍 | 審批類型 | 說明 |
|----------|---------|---------|------|
| LOW | 0.0 - 0.3 | NONE | 自動執行 |
| MEDIUM | 0.3 - 0.6 | NONE | 自動執行 (記錄) |
| HIGH | 0.6 - 0.85 | SINGLE | 單人審批 |
| CRITICAL | 0.85 - 1.0 | MULTI | 多人審批 |

**審批流程**:
```
RiskAssessor.assess() → requires_approval=True
    → HITLController.request_approval()
        → 建立 ApprovalRequest (UUID, 30min expiry)
        → 儲存到 ApprovalStorage (Redis or InMemory)
        → Teams webhook → MessageCard (Approve/Reject 按鈕)
    → 使用者操作
    → HITLController.process_approval()
        → 驗證 PENDING 狀態 + 過期檢查
        → 更新狀態 → APPROVED / REJECTED
        → 觸發 on_approved/on_rejected callbacks
        → Teams 結果通知
```

**已知限制**:
- ⚠️ HITL 超時直接 EXPIRED，無升級到上級主管邏輯
- ⚠️ InMemory 儲存 (dev) 重啟遺失審批狀態
- ⚠️ 三套系統未統一介面

---

### 3.3 工具與資源存取能力

**MCP 工具總覽**: 8 Servers, 64 Tools

| Server | 工具類別 | 代表工具 | 外部連線 |
|--------|---------|---------|----------|
| **Azure** (24 tools) | VM, Storage, Network, Monitor | list_vms, create_vm, run_command, get_metrics | Azure SDK |
| **Filesystem** (6 tools) | 檔案操作 | read_file, write_file, list_dir, search | pathlib |
| **Shell** (2 tools) | 指令執行 | execute_command, get_environment | subprocess |
| **LDAP** (6+AD) | 目錄服務 | search_users, authenticate, manage_groups | ldap3 |
| **SSH** (6 tools) | 遠端存取 | execute_command, upload_file, download_file | paramiko |
| **n8n** (6 tools) | 工作流自動化 | list/get/execute_workflow, get_execution | httpx |
| **ADF** (8 tools) | 資料管線 | list/trigger/monitor pipeline, get_activity | httpx + MSAL |
| **D365** (6 tools) | CRM/ERP | query_entity, create/update_record | httpx + OAuth2 |

**Claude SDK 內建工具**: Read, Write, Edit, MultiEdit, Glob, Grep, Bash, Task, WebSearch, WebFetch

**工具安全控制**:
- MCP 4-level RBAC (NONE/READ/EXECUTE/ADMIN)
- Filesystem sandbox: 路徑驗證 + pattern 阻擋 + 大小限制
- Shell: 危險指令偵測 (rm -rf /, fork bombs)
- Bash tool: 可配置 allowed/denied 指令列表, 120s timeout

---

### 3.4 可觀測性與治理能力

| 系統 | Files | LOC | 資料來源 | 狀態 |
|------|-------|-----|----------|------|
| OrchestrationMetrics | 1 | 893 | OTel + dict fallback | COMPLETE |
| Patrol Agent | 11 | ~2,900 | psutil, HTTP, filesystem | COMPLETE (Integration); API MOCK |
| DecisionTracker | 4 | 1,170 | Redis + InMemory fallback | COMPLETE |
| CorrelationAnalyzer | 6 | 2,187 | Azure Monitor (S130 fix) | COMPLETE (Integration); API MOCK |
| RootCauseAnalyzer | 5 | ~1,500 | CaseRepository (S130 fix) | COMPLETE (Integration); API MOCK |
| ExecutionTracer | 2 | 803 | InMemory | COMPLETE |

**治理模式**: 每次 Agent 決策記錄 6 維度 audit trail:
1. Intent Classification → 意圖歸類理由
2. Risk Assessment → 風險判定理由
3. Framework Selection → MAF/Claude/Swarm 選擇理由
4. Tool Invocations → 工具呼叫結果
5. HITL Decisions → 人工審批決定
6. Execution Result → 最終結果驗證

---

### 3.5 記憶與學習能力

**三層記憶模型** (mem0 integration):

| 層級 | 記憶類型 | 持久化 | 用途 |
|------|---------|--------|------|
| Working Memory | 短期工作記憶 | Redis (TTL) | 當前對話上下文 |
| Episodic Memory | 情境記憶 | Qdrant + PostgreSQL | 特定事件/案例 |
| Semantic Memory | 語義知識 | Qdrant + PostgreSQL | 長期知識積累 |

**記憶操作** (7 API endpoints):
- `POST /memory/add` — 新增記憶
- `POST /memory/search` — 搜尋記憶
- `GET /memory/user/{user_id}` — 取得使用者記憶
- `DELETE /memory/{memory_id}` — 刪除記憶
- `POST /memory/promote` — 提升記憶層級 (working → episodic → semantic)
- `POST /memory/context` — 取得上下文相關記憶
- `GET /memory/health` — 記憶系統健康檢查

**Few-Shot 學習** (learning/, 5 files, 1,497 LOC):
- 從歷史案例提取 few-shot examples
- 相似度匹配 (embeddings planned, 目前文字匹配)
- 案例庫管理 (InMemory，生產應使用 embeddings)
- Integration with mem0 memory system

---

### 3.6 Agent Swarm 能力 (Phase 29)

Phase 29 (Sprint 100-106) 新增的多 Agent 群集即時視覺化系統，包含完整的後端追蹤、SSE 事件串流、API 端點與前端面板。

#### 3.6.1 後端 Swarm 模組

| 組件 | 檔案 | LOC | 職責 |
|------|------|-----|------|
| **SwarmTracker** | `swarm/tracker.py` | ~694 | 群集生命週期管理、Worker 追蹤、狀態轉換、threading.RLock |
| **SwarmEventEmitter** | `swarm/events/emitter.py` | ~635 | 9 種 SSE 事件類型的產生與分發、Throttling (200ms) + batch |
| **SwarmIntegration** | `swarm/swarm_integration.py` | ~400 | AG-UI Bridge 整合、CustomEvent 包裝 |
| **Swarm Models** | `swarm/models.py` | ~300 | 資料模型定義 (Worker, Swarm, Event) |
| **Swarm Events** | `swarm/events/` | ~400 | 事件類型定義與序列化 |

**Swarm 資料模型**:

```
WorkerType (9 enum):
├── RESEARCH     → 資料蒐集
├── WRITER       → 內容撰寫
├── DESIGNER     → 設計產出
├── REVIEWER     → 品質審查
├── COORDINATOR  → 協調管理
├── ANALYST      → 資料分析
├── CODER        → 代碼開發
├── TESTER       → 測試驗證
└── CUSTOM       → 自定義

WorkerStatus (7 lifecycle):
PENDING → RUNNING → THINKING → TOOL_CALLING → COMPLETED / FAILED / CANCELLED

SwarmMode (3 modes):
├── SEQUENTIAL    → 順序執行
├── PARALLEL      → 並行執行
└── HIERARCHICAL  → 階層執行

SwarmStatus (5 states):
INITIALIZING → RUNNING → PAUSED → COMPLETED / FAILED
```

**SwarmEventEmitter 9 種事件類型**:

```
Swarm 層級事件:
├── SwarmCreated        → 群集已建立
├── SwarmStatusUpdate   → 群集狀態變更
└── SwarmCompleted      → 群集執行完成

Worker 層級事件:
├── WorkerStarted       → Worker 開始執行
├── WorkerProgress      → Worker 進度更新
├── WorkerThinking      → Worker 思考過程 (Extended Thinking)
├── WorkerToolCall      → Worker 工具調用
├── WorkerMessage       → Worker 訊息產出
└── WorkerCompleted     → Worker 執行完成
```

#### 3.6.2 Swarm API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/v1/swarm/{swarm_id}` | 群集狀態查詢 |
| GET | `/api/v1/swarm/{swarm_id}/workers` | Worker 列表 |
| GET | `/api/v1/swarm/{swarm_id}/workers/{worker_id}` | Worker 詳情 |
| POST | `/api/v1/swarm/demo/start` | 啟動 Demo 群集 |
| GET | `/api/v1/swarm/demo/status/{swarm_id}` | Demo 狀態查詢 |
| POST | `/api/v1/swarm/demo/stop/{swarm_id}` | 停止 Demo |
| GET | `/api/v1/swarm/demo/scenarios` | 可用場景列表 |
| GET | `/api/v1/swarm/demo/events/{swarm_id}` | SSE 事件串流 |

#### 3.6.3 Swarm 前端面板

**15 個元件** (位於 `frontend/src/components/unified-chat/agent-swarm/`):

| 元件 | Sprint | 用途 |
|------|--------|------|
| AgentSwarmPanel | 102 | 主面板 (loading/empty/active 三態) |
| SwarmHeader | 102 | 模式和狀態顯示 |
| OverallProgress | 102 | 狀態感知進度條 |
| WorkerCard | 102 | 個別 Worker 狀態卡片 |
| WorkerCardList | 102 | Worker 卡片網格佈局 |
| SwarmStatusBadges | 102 | 狀態徽章集合 |
| WorkerDetailDrawer | 103 | 側邊抽屜 (Worker 詳情) |
| WorkerDetailHeader | 103 | 抽屜標題列 |
| CurrentTask | 103 | 當前任務顯示 |
| ToolCallItem | 103 | 工具調用視覺化 |
| ToolCallsPanel | 103 | 工具調用列表 |
| MessageHistory | 103 | Worker 對話歷史 |
| CheckpointPanel | 103 | Worker 檢查點 |
| ExtendedThinkingPanel | 104 | Extended Thinking 視覺化 |
| OrchestrationPanel | 105 | 編排控制面板整合 |

**4 個 Hooks + 1 個 Store**:

| Hook/Store | 用途 |
|------------|------|
| `useSwarmMock` | Mock 數據驅動 (開發/測試用) |
| `useSwarmReal` | 真實 SSE 串流驅動 |
| `useSwarmOrchestration` | 編排面板狀態管理 |
| `useSwarmWorkerDetail` | Worker 詳情管理 |
| `swarmStore` (Zustand) | 全域 Swarm 狀態 |

---

### 3.7 安全能力

| 安全層面 | 實現 | Sprint | 狀態 |
|----------|------|--------|------|
| **JWT Authentication** | HS256, 1-hour expiry | S70 | ✅ COMPLETE |
| **Global Auth Middleware** | protected_router + require_auth | S111 | ✅ COMPLETE |
| **Password Hashing** | bcrypt via passlib | S70 | ✅ COMPLETE |
| **Process Sandbox** | ProcessSandboxConfig + IPC | S77-78 | ✅ COMPLETE |
| **MCP RBAC** | 4-level (NONE/READ/EXECUTE/ADMIN) | S39 | ✅ COMPLETE |
| **Sensitive Data Masking** | structlog filter (passwords, secrets, tokens) | — | ✅ COMPLETE |
| **Path Traversal Prevention** | SandboxConfig sanitizers | — | ✅ COMPLETE |
| **Rate Limiting** | slowapi (InMemory storage) | — | ⚠️ Partial |

**安全問題**:
- H-01: 無 RBAC 在破壞性操作 (cache clear, connector execute)
- H-02: ag_ui /test/* 端點不受環境限制
- H-12: Shell/SSH HITL 為 log-only (不阻擋非白名單指令)
- H-14: Rate limiter InMemory → 多 worker 無效
- MCP permission mode 預設 "log" (不阻擋)

---

### 3.8 多框架代理協作

**MAF + Claude SDK 混合架構**:

| 維度 | MAF | Claude SDK | 混合 (選擇) |
|------|-----|-----------|-------------|
| 結構化編排 | ✅ 原生 | ❌ 需自建 | ✅ MAF 處理 |
| 自主推理 | ❌ 無 | ✅ Extended Thinking | ✅ Claude 處理 |
| 檢查點 | ✅ 內建 | ❌ 需自建 | ✅ MAF + 4 backends |
| 工具存取 | ⚠️ 有限 | ✅ MCP 原生 | ✅ 統一 MCP |
| 企業治理 | ✅ 審計追蹤 | ⚠️ 需 Hooks | ✅ 兩者結合 |

**任務-框架映射** (`TASK_FRAMEWORK_MAP`):

| 任務類型 | 選擇框架 | 原因 |
|----------|---------|------|
| multi_agent_collaboration | MAF | 多 Agent 協作原生支援 |
| agent_handoff | MAF | Agent 切換機制 |
| task_planning | MAF | 結構化規劃 |
| autonomous_research | Claude SDK | Extended Thinking |
| nlp_analysis | Claude SDK | 自然語言理解 |
| code_generation | Claude SDK | 代碼生成能力 |
| swarm_mode | Swarm | 群集協作 |

**Sprint 132 Mediator Pattern**:
- 將 1,254 LOC God Object 解耦為 6 個專責 Handler
- 每個 Handler 實現 `HandlerABC` 介面
- 透過 `OrchestratorMediator` 協調 Handler 鏈
- `HybridOrchestratorV2` 降級為向後相容 facade

---

## 4. 端到端流程驗證

> 基於 14 份 Phase 3 分析報告，追蹤 5 條端到端使用者旅程。

### 4.1 Flow 1: Chat Message (主要旅程)

**鏈路**: Frontend → useUnifiedChat → Fetch SSE → /api/v1/ag-ui → BusinessIntentRouter (3-tier) → LLMServiceFactory → Azure OpenAI → SSE → AG-UI EventBridge → Frontend

| 步驟 | 元件 | 狀態 | 說明 |
|------|------|------|------|
| 1 | UnifiedChat.tsx | CONNECTED | sendMessage() via useUnifiedChat |
| 2 | useUnifiedChat.ts | CONNECTED | POST /api/v1/ag-ui, 15 SSE events |
| 3 | useOrchestration.ts | CONNECTED | POST /orchestration/intent/classify |
| 4 | intent_routes.py | CONNECTED | BusinessIntentRouter or mock fallback |
| 5a | PatternMatcher | CONNECTED | 30+ regex, <10ms, REAL |
| 5b | SemanticRouter | CONNECTED | ⚠️ Mock 預設 (需配置) |
| 5c | LLMClassifier | CONNECTED | ⚠️ Mock 預設 (需配置) |
| 6 | LLMServiceFactory | CONNECTED | Azure OpenAI via openai SDK |
| 7 | CompletenessChecker | CONNECTED | 規則式欄位提取 |
| 8 | GuidedDialogEngine | CONNECTED | 多輪模板 (InMemory sessions) |
| 9 | AG-UI SSE endpoint | CONNECTED | HybridEventBridge.stream_events() |
| 10 | HybridEventBridge | CONNECTED | RUN_STARTED → events → RUN_FINISHED |
| 11 | HybridOrchestratorV2 | CONNECTED | Facade → OrchestratorMediator |
| 12 | OrchestratorMediator | CONNECTED | 6-handler chain |
| 13 | Framework execution | CONNECTED | Claude SDK query() or MAF executor |
| 14 | ClaudeSDKClient | CONNECTED | AsyncAnthropic (需 API key) |
| 15 | AG-UI SSE response | CONNECTED | TEXT/TOOL/STATE events |
| 16 | Frontend state update | CONNECTED | Zustand store sync |

**結果**: **MOSTLY CONNECTED** — 全 16 步驟已連通，但需 LLM API 配置才有真正 AI 路由。

---

### 4.2 Flow 2: Agent CRUD

**鏈路**: AgentsPage → React Query → Fetch API → /api/v1/agents/ → AgentService → AgentRepository → PostgreSQL

| 步驟 | 元件 | 狀態 | 說明 |
|------|------|------|------|
| 1 | AgentsPage.tsx | CONNECTED | GET /agents/ + mock fallback |
| 2 | CreateAgentPage.tsx | CONNECTED | 4-step wizard, POST /agents/ |
| 3 | agents/routes.py | CONNECTED | 6 endpoints, SQLAlchemy |
| 4 | AgentRepository | CONNECTED | Full async PostgreSQL |
| 5 | Agent DB model | CONNECTED | SQLAlchemy ORM |
| 6 | React Query cache | CONNECTED | invalidateQueries(['agents']) |

**結果**: **FULLY CONNECTED** — PostgreSQL 持久化，完整 CRUD + mock fallback。

---

### 4.3 Flow 3: Workflow Execution

**鏈路**: WorkflowDetailPage → POST /workflows/{id}/execute → WorkflowExecutionService → DAG Engine → Agent invocation → Checkpoint → DB

| 步驟 | 元件 | 狀態 | 說明 |
|------|------|------|------|
| 1 | WorkflowDetailPage.tsx | CONNECTED | POST execute, 無 mock fallback |
| 2 | workflows/routes.py | CONNECTED | WorkflowDefinitionAdapter.run() |
| 3 | WorkflowRepository | CONNECTED | PostgreSQL + graph visualization |
| 4 | WorkflowExecutionService | CONNECTED | DAG traversal, node dispatch |
| 5 | Agent node execution | CONNECTED | AgentService.invoke_agent() |
| 6 | ExecutionStateMachine | CONNECTED | CREATED→RUNNING→COMPLETED/FAILED |
| 7 | CheckpointService | CONNECTED | State persistence (backend 依配置) |
| 8 | ExecutionRepository | CONNECTED | PostgreSQL persistence |

**結果**: **MOSTLY CONNECTED** — DAG 引擎完整，checkpoint backend 預設 InMemory。

---

### 4.4 Flow 4: HITL Approval

**鏈路**: Tool call → RiskEngine → ApprovalHook → SSE approval event → ApprovalMessageCard → User action → Resume

| 步驟 | 元件 | 狀態 | 說明 |
|------|------|------|------|
| 1 | QueryExecutor | CONNECTED | 偵測 tool_use, run hook chain |
| 2 | ApprovalHook | CONNECTED | 檢查 Write/Edit/Bash/Task |
| 3 | RiskAssessmentEngine | CONNECTED | 7 factors, 3 strategies |
| 4 | HITLHandler | CONNECTED | create_approval_event → custom SSE |
| 5 | ApprovalStorage | CONNECTED | InMemory + asyncio.Lock, 5min TTL |
| 6 | SSE emission | CONNECTED | HITL_APPROVAL_REQUIRED event |
| 7 | Frontend ApprovalCard | CONNECTED | Approve/Reject buttons |
| 8 | POST /approve | CONNECTED | process_approval() |
| 9 | Resume execution | CONNECTED | Continue tool execution |
| 10 | Teams notification | CONNECTED | Webhook MessageCard |

**結果**: **CONNECTED but FRAGILE** — 全程連通但 InMemory 存儲 = 重啟遺失審批狀態。

---

### 4.5 Flow 5: Swarm Multi-Agent

**鏈路**: SwarmTestPage → POST /swarm/demo/start → SwarmManager → ClaudeCoordinator → Workers → SSE → SwarmPanel

| 步驟 | 元件 | 狀態 | 說明 |
|------|------|------|------|
| 1 | SwarmTestPage.tsx | CONNECTED | Real + Mock 雙模式 |
| 2 | swarm/routes.py | CONNECTED | start_demo + SSE events |
| 3 | SwarmIntegration | CONNECTED | Coordinator ↔ Tracker bridge |
| 4 | ClaudeCoordinator | CONNECTED | Task analysis → agent selection |
| 5 | SwarmTracker | CONNECTED | InMemory + optional Redis |
| 6 | SwarmEventEmitter | CONNECTED | 9 events, throttle 200ms |
| 7 | AG-UI bridge | CONNECTED | CustomEvent wrapping |
| 8 | SwarmPanel | CONNECTED | WorkerCards + Timeline |

**結果**: **PARTIALLY CONNECTED** — Demo 模式完整，但非主流程 (execute_with_routing 未整合)。

---

### 4.6 E2E 驗證總結

| Flow | 步驟 | 連通性 | 主要風險 |
|------|------|--------|----------|
| Chat Message | 16 | MOSTLY CONNECTED | Mock 預設, 需 LLM 配置 |
| Agent CRUD | 6 | FULLY CONNECTED | Mock fallback (H-08) |
| Workflow Execute | 8 | MOSTLY CONNECTED | Checkpoint 預設 InMemory |
| HITL Approval | 10 | CONNECTED but FRAGILE | InMemory 存儲 (C-01) |
| Swarm | 8 | PARTIALLY CONNECTED | Demo only, InMemory |

**跨流程問題**:
1. **C-01 InMemory**: 影響 Flow 4, 5 的生產可靠性，審批狀態和 Swarm 狀態重啟遺失
2. **Mock 預設**: SemanticRouter, LLMClassifier 預設 Mock → 需環境變數配置 Azure OpenAI 才有真正 AI 路由
3. **H-08 靜默 Mock**: 前端 10 頁面使用 try/catch + generateMock*() fallback，使用者無法區分真實 vs 假資料
4. **Swarm 未整合**: execute_with_routing() 主流程不包含 Swarm 路徑，Swarm 透過獨立 Demo API 運行
5. **Checkpoint 碎片化**: 4 套 Checkpoint 系統使用不同 API，無統一協調機制
6. **AG-UI 非真串流**: HybridEventBridge 接收完整 HybridResultV2 後分塊模擬 streaming，非 token-by-token

**各流程生產就緒度評估**:

| Flow | 開發環境 | 生產環境 | 缺口 |
|------|---------|---------|------|
| Chat Message | ✅ 可用 | ⚠️ 需配置 | LLM API keys, Redis, 關閉 Mock |
| Agent CRUD | ✅ 可用 | ✅ 可用 | PostgreSQL 即可 |
| Workflow Execute | ✅ 可用 | ⚠️ 需配置 | Checkpoint backend → Redis/PG |
| HITL Approval | ✅ 可用 | ❌ 不可靠 | ApprovalStorage → Redis 必要 |
| Swarm | ⚠️ Demo only | ❌ 未整合 | 需整合至主流程 + 持久化 |

**Plan vs Reality 功能分類合規性**:

| 功能類別 | 計畫數 | 完成 | 完成率 | 備註 |
|---------|--------|------|--------|------|
| A: Agent 編排 | 12 | 12 | 100% | 全部完成 |
| B: 前端 UI | 10 | 10 | 100% | 全部完成 |
| C: 狀態與記憶 | 5 | 5 | 100% | 全部完成 |
| D: AG-UI 協議 | 7 | 7 | 100% | 全部完成 + 6 增強 |
| E: 工具與連接 | 6 | 5.5 | 92% | ServiceNow 部分, MCP 超標 (8 vs 5) |
| F: 智能能力 | 7 | 6 | 86% | Autonomous API = stub |
| G: 可觀測性 | 5 | 3 | 60% | Patrol/Correlation/RootCause API stub |
| H: Agent Swarm | 4 | 4 | 100% | 全部完成 |
| I: 安全能力 | 4 | 4 | 100% | 全部完成 |
| K: 生產擴展 | 4 | 0 | 0% | 延遲 (P3 低優先) |
| **合計** | **70** | **59+** | **84.3%** | 無完全缺失功能 |

**計畫外額外功能** (15 項):
- n8n MCP Server (Sprint 124)
- ADF MCP Server (Sprint 125)
- D365 MCP Server (Sprint 129)
- Anti-Corruption Layer (Sprint 128)
- Mediator Pattern refactor (Sprint 132)
- ReactFlow Workflow DAG (Sprint 133)
- Redis centralization (Sprint 119)
- Extended Thinking streaming (Sprint 104)
- HITL metrics enhancement (Sprint 131)
- Swarm event throttling/batching
- AG-UI heartbeat mechanism
- AG-UI step progress tracking
- AG-UI file attachment support
- Redis thread storage
- Few-shot learning integration

---

## 5. 並行處理架構

### 5.1 各層並行能力現狀

| 層級 | 並行模式 | 現狀 | 限制 |
|------|----------|------|------|
| **L1: Frontend** | React 18 並行渲染 | 支援 | Concurrent features 正常 |
| **L2: API** | FastAPI async | 原生支援 | 單 Uvicorn Worker (dev) |
| **L3: AG-UI** | SSE 串流 | 原生支援 | 非並行，序列事件流 |
| **L4: Orchestration** | 瀑布式 (非並行) | 三層依序嘗試 | 設計如此 (Pattern→Semantic→LLM) |
| **L5: Hybrid** | asyncio 協程 | 支援並行任務分派 | ContextSynchronizer 無鎖 (H-04) |
| **L6: MAF** | ConcurrentBuilder Worker Pool | 原生並行支援 | 受 MAF SDK 限制 |
| **L7: Claude SDK** | AsyncAnthropic | 原生 async | 單 Worker 處理序列 |
| **L8: MCP** | 獨立 Server 進程 | 各 Server 獨立 | 無跨 Server 並行控制 |
| **L9: Swarm** | SwarmTracker | 支援 PARALLEL 模式 | Worker Pool 大小限制 |
| **L10: Domain** | asyncio (workflows) | 並行分支執行 | Singleton 狀態管理器 |
| **L11: Infrastructure** | SQLAlchemy async | 連線池並行 | 單 worker 限制 |

### 5.2 Concurrent Builder Worker Pool

**位置**: `integrations/agent_framework/builders/concurrent.py` (1,633 LOC)

**並行模式** (`ConcurrentMode` enum):

| 模式 | 說明 | 實現方式 | 使用場景 |
|------|------|----------|----------|
| `ALL` | 等待所有任務完成 | `asyncio.gather(*coroutines)` | 批次處理 |
| `ANY` | 任一任務完成即返回 | `asyncio.wait(FIRST_COMPLETED)` | 競速模式 |
| `MAJORITY` | 多數任務完成即返回 | counter + wait | 投票/共識 |
| `FIRST_SUCCESS` | 首個成功即返回 | task + 成功檢測 | 容錯模式 |

**Gateway Types** (Sprint 22):

| Gateway | 說明 | 用途 |
|---------|------|------|
| `PARALLEL_SPLIT` | 分支並行 | Fork 到多分支 |
| `PARALLEL_JOIN` | 合併等待 | Join 等待完成 |
| `INCLUSIVE_GATEWAY` | 條件式包含 | 選擇性分支 |

**Domain 層並行** (workflows/):

| 類別 | LOC | 說明 |
|------|-----|------|
| `ConcurrentExecutor` | ~580 | 並行分支執行，可配置最大並行數 |
| `ConcurrentStateManager` | ~600 | Singleton 狀態追蹤，Branch lifecycle |
| `ParallelForkGateway` | ~700 | Fork-Join 模式 |
| `ParallelJoinGateway` | — | 4 Join + 4 Merge strategies |

**Join Strategies**: WAIT_ALL, WAIT_ANY, WAIT_MAJORITY, WAIT_N
**Merge Strategies**: COLLECT_ALL, MERGE_DICT, FIRST_RESULT, AGGREGATE

### 5.3 asyncio 使用模式總結

| 模組 | asyncio.gather | asyncio.create_task | 用途 |
|------|---------------|--------------------|----|
| agent_framework/concurrent.py | 4 處 | 4 處 | 並行工作流執行 |
| claude_sdk/orchestrator/ | 2 處 | 0 | 任務分配 + 批次執行 |
| claude_sdk/mcp/manager.py | 1 處 | 0 | 多 server 生命週期 |
| hybrid/orchestrator/ | 1 處 | 0 | Handler chain 可選並行 |
| ag_ui/bridge.py | 0 | 1 處 | heartbeat background task |
| swarm/tracker.py | 0 | 0 | threading.RLock (非 asyncio) |
| domain/workflows/concurrent.py | 2 處 | 3 處 | 並行分支 + gateway |

### 5.4 Claude SDK 並行 Worker

**ClaudeCoordinator** (`orchestrator/coordinator.py`, 522 LOC):

```
Task Analysis → Agent Selection → Subtask Allocation → Execution → Aggregation
```

- `PARALLEL` mode: `asyncio.gather(*agent_tasks)` — 所有 agent 同時執行
- `SEQUENTIAL` mode: for loop 依序執行
- `PIPELINE` mode: 前一 agent 輸出作為下一 agent 輸入
- `ADAPTIVE` mode: 基於任務複雜度動態選擇

**TaskAllocator**:
- 依複雜度分析分配子任務
- Dependency-aware 執行順序
- 每子任務獨立 timeout + retry
- 跨 agent 負載平衡

### 5.5 已知並行問題

**問題 1: ContextBridge._context_cache 無 asyncio.Lock (嚴重度: 高, H-04)**

```python
# integrations/hybrid/context/bridge.py
# self._context_cache: Dict[str, HybridContext] = {}
#
# 無 asyncio.Lock 保護，同 session 多個並行操作時
# 可能導致 context 損壞或讀取不一致
#
# V9 補充: ContextSynchronizer (synchronizer.py:164-167) 已在 Sprint 109 添加
# self._state_lock = asyncio.Lock()，但此 lock 僅保護 Synchronizer 內部狀態，
# ContextBridge._context_cache 本身仍無 lock 保護。
#
# 建議:
# - 在 bridge.py 添加 asyncio.Lock (self._lock = asyncio.Lock())
# - 或遷移到 Redis (已有 redis_store.py 可復用)
```

**問題 2: ConcurrentStateManager 使用 Singleton (嚴重度: 高, H-03)**

```python
# domain/workflows/concurrent_state_manager.py
# 全域 Singleton — 所有 workflow 共享同一狀態管理器
# 測試困難 (隱式共享狀態，無法隔離)
# 多 workflow 並行時可能互相干擾
#
# 影響: 10+ modules 使用 Singleton pattern (DeadlockDetector, MetricsCollector 等)
```

**問題 3: SwarmTracker 使用 threading.RLock (嚴重度: 中)**

```python
# integrations/swarm/tracker.py
# self._lock = threading.RLock()  (而非 asyncio.Lock)
#
# 在 asyncio event loop 中使用 threading lock 可能:
# 1. 阻塞 event loop (threading.RLock.acquire 是同步的)
# 2. 與 asyncio 協程混用時產生 deadlock
#
# 建議: 改用 asyncio.Lock 或確保所有 lock 操作在 executor 中
```

**問題 4: Rate limiter InMemory (嚴重度: 高, H-14)**

```
# middleware/rate_limiter.py — slowapi 預設 InMemory storage
# 多 Uvicorn worker 時各 worker 獨立計數
# 實際限制 = 設定值 × worker 數
#
# 建議: 改用 Redis backend (slowapi 支援 redis storage)
```

**問題 5: 無跨 MCP Server 並行控制 (嚴重度: 中)**

```
# mcp/ — 8 servers 各自獨立
# 無全域並行控制或 rate limiting
# 高負載時可能同時觸發多 server 操作
```

**問題 6: 單 Uvicorn Worker (嚴重度: 高)**

```
# 現況:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 僅 1 個 Worker + reload=True (開發模式硬編碼)

# 建議 (生產環境):
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
# 或使用 Gunicorn:
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 5.6 並行處理改善規劃

```
Phase 目標                           優先級    依賴
────────────────────────────────────────────────────
1. ContextBridge + asyncio.Lock      高        無
2. Rate limiter → Redis backend      高        Redis
3. Multi-Worker Uvicorn              高        無
4. SwarmTracker → asyncio.Lock       中        無
5. Singleton 改為 DI 注入            中        重構
6. MCP 並行控制 (semaphore)          低        無
7. Worker Pool 容器化                低        K8s
```

---

## 6. 關鍵設計決策

### 6.1 為什麼 MAF + Claude SDK 混合而非單一框架

**決策背景**: MAF 擅長結構化 Agent 編排 (workflow, handoff, groupchat)，Claude SDK 擅長自主推理 (Extended Thinking, autonomous planning)。

| 考量 | MAF 單獨 | Claude SDK 單獨 | 混合架構 (選擇) |
|------|----------|----------------|-----------------|
| 結構化編排 | ✅ 原生支援 | ❌ 需自建 | ✅ MAF 處理 |
| 自主推理 | ❌ 無 | ✅ Extended Thinking | ✅ Claude 處理 |
| 檢查點 | ✅ 內建 | ❌ 需自建 | ✅ MAF + 4 backends |
| 工具存取 | ⚠️ 有限 | ✅ MCP 原生 | ✅ 統一 MCP |
| 企業治理 | ✅ 審計追蹤 | ⚠️ 需 Hooks | ✅ 兩者結合 |
| 動態切換 | ❌ | ❌ | ✅ SwitchingLogic |

**代價**: 需維護 ContextBridge 同步兩框架狀態 (932 LOC)，引入 FrameworkSelector 選擇邏輯。

### 6.2 三層意圖路由設計理由

**設計目標**: 平衡速度、準確度、成本

```
Layer 1: PatternMatcher (<10ms, 免費)
    ├── 30+ regex rules → 處理 ~70% 明確意圖
    ├── 雙語 (EN + ZH-TW)
    └── 失敗 → Layer 2

Layer 2: SemanticRouter (<100ms, embedding 計算)
    ├── Embedding 相似度 → 處理 ~15% 語義模糊
    └── 失敗 → Layer 3

Layer 3: LLMClassifier (<2000ms, LLM API 費用)
    ├── Azure OpenAI → 處理 ~15% 複雜意圖
    └── 失敗 → UNKNOWN → HANDOFF

結果: ~85% 請求不需要 LLM 調用
      平均延遲從 ~2000ms 降至 ~50ms
      API 成本降低 ~85%
```

**配置**:
- `PATTERN_CONFIDENCE_THRESHOLD`: 0.90
- `SEMANTIC_SIMILARITY_THRESHOLD`: 0.85
- `ENABLE_LLM_FALLBACK`: True (可關閉)

### 6.3 Checkpoint 4 後端設計

**為什麼需要 4 種 Checkpoint 儲存後端?**

| Backend | 用途 | 優點 | 限制 |
|---------|------|------|------|
| Memory | 開發/測試 | 快速, 無依賴 | 無持久化 |
| Redis | 生產推薦 | 快速, TTL | 記憶體限制 |
| PostgreSQL | 合規要求 | 持久化, 可查詢 | 較慢 |
| Filesystem | 備用方案 | 簡單, 無依賴 | I/O 限制 |

**V8 發現: 4 個獨立 Checkpoint 系統**:
1. `agent_framework/checkpoint.py` — MAF 原生 checkpoint
2. `hybrid/checkpoint/` — 混合層 checkpoint (4 backends)
3. `agent_framework/multiturn/checkpoint_storage.py` — 多輪對話 checkpoint
4. `domain/checkpoints/storage.py` — 業務層 checkpoint

**問題**: 4 系統需統一介面和協調機制。Hybrid checkpoint 使用非官方 API (save/load/delete) 與 MAF 官方 (save_checkpoint/load_checkpoint) 不相容 (H-05)。

### 6.4 AG-UI SSE vs WebSocket

**選擇 SSE (Server-Sent Events)**:

| 考量 | SSE (選擇) | WebSocket |
|------|-----------|-----------|
| 方向性 | Server → Client (單向) | 雙向 |
| 協議 | HTTP (標準) | 獨立協議 |
| 斷線重連 | 瀏覽器原生支援 | 需自建 |
| 負載平衡 | 標準 HTTP LB | 需 sticky session |
| 複雜度 | 低 | 高 |
| AG-UI 規範 | ✅ 符合 | ❌ 不符合 |

**實現**: `data: {json}\n\n` format, heartbeat keepalive, 15 event types。

**限制**: 
- 無真正 token-by-token streaming (結果分塊模擬)
- Client → Server 仍用 HTTP POST (非 SSE)

### 6.5 MCP 設計選擇

**為什麼選 MCP (Model Context Protocol)**:
- 標準化工具存取介面
- Transport 抽象 (Stdio for local, HTTP for remote)
- 工具發現機制 (ToolIndex)
- Permission model 整合
- 多 server 生命週期管理

**超出原始計畫**: 原計畫 5 servers，實際實現 8 servers (64 tools)。新增 n8n (S124), ADF (S125), D365 (S129)。

### 6.6 InMemory vs Persistent 存儲選擇

**V8 發現: 30 處 InMemory 模式 (AST 掃描)**

| 類別 | 模組數 | 風險等級 | 影響 |
|------|--------|---------|------|
| Approval 狀態 | 3 | CRITICAL | 審批遺失 |
| 對話記憶 | 2 | HIGH | 上下文遺失 |
| 指標/Metrics | 3 | MEDIUM | 統計歸零 |
| 學習/Templates | 4 | MEDIUM | 知識遺失 |
| 審計日誌 | 2 | HIGH | 合規風險 |
| Dialog sessions | 1 | MEDIUM | 對話中斷 |
| DevTools traces | 1 | LOW | 除錯資料 |
| 其他 | 14 | Various | — |

**根本原因**: 開發階段優先功能完整性，持久化作為後續改進。
**建議**: 至少 Approval、Audit、Metrics 應使用 Redis/PostgreSQL。

### 6.7 Mediator Pattern 重構 (Sprint 132)

**問題**: `HybridOrchestratorV2` 是 1,254 LOC God Object，13 injectable dependencies，直接耦合所有組件。

**解決方案**: Mediator Pattern + Chain of Responsibility

```
OrchestratorMediator
├── RoutingHandler    — BusinessIntentRouter, FrameworkSelector
├── DialogHandler     — GuidedDialogEngine
├── ApprovalHandler   — HITLController, RiskAssessor
├── ExecutionHandler  — UnifiedToolExecutor, claude_executor, maf_executor
├── ContextHandler    — ContextBridge
└── ObservabilityHandler — metrics, logging
```

**每個 Handler 實現**:
- `HandlerABC` 抽象基類
- `HandlerType` 枚舉標識
- `OrchestratorRequest` 統一請求物件
- `OrchestratorEvent` 事件通訊

**V8 狀態**: Mediator 已完成但 `HybridOrchestratorV2` 仍作為向後相容 facade 存在。完整遷移待後續 sprint。

---

## 7. 可觀測性設計

### 7.1 指標體系

**OrchestrationMetrics** (`orchestration/metrics.py`, 893 LOC):

```
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
│   └── 超時率 (無升級機制)
└── Execution Metrics
    ├── 框架選擇分布 (MAF vs Claude vs Swarm)
    ├── 任務完成率
    └── 執行時間分布
```

**指標分類**: 4 大類, 15+ 指標
- Counter: 請求數, 命中數, 錯誤數
- Histogram: 延遲分布, 執行時間
- Gauge: 並行任務數, 佇列深度

### 7.2 OpenTelemetry 整合

```
OrchestrationMetrics 設計:
─────────────────────────
• 優先使用 OpenTelemetry (如果可用)
• 自動降級到 fallback counters (dict-based InMemory)
• 零配置啟動，不因 OTel 不可用而失敗
• Counter、Histogram、Gauge 三種指標類型
• 生產環境接入 Azure Monitor / Grafana
```

**Core Observability** (4 files, 699 LOC):
- OpenTelemetry SDK 整合
- Azure Monitor exporter
- 請求相關 ID (correlation) 追蹤
- Structured metric collection

### 7.3 巡檢系統 (Patrol)

**位置**: `integrations/patrol/` (11 files, ~2,900 LOC)

```
Patrol Agent:
├── 5 種巡檢類型
│   ├── service_health   → 服務健康狀態
│   ├── api_response     → API 回應檢查
│   ├── resource_usage   → 資源使用率 (psutil)
│   ├── log_analysis     → 日誌分析
│   └── security_scan    → 安全合規
├── Scheduler            → 定時巡檢排程
└── Agent                → 自主巡檢 Agent (optional Claude)
```

**狀態**: Integration layer COMPLETE, API routes MOCK (C-05)
**風險**: 巡檢結果 InMemory，無持久化存儲

### 7.4 審計追蹤

**Decision Audit Trail** (`integrations/audit/`, 4 files, 1,170 LOC):

| 階段 | 記錄內容 |
|------|---------|
| 1. Intent Classification | 為什麼歸類為此意圖 |
| 2. Risk Assessment | 為什麼判定此風險等級 |
| 3. Framework Selection | 為什麼選擇 MAF/Claude/Swarm |
| 4. Tool Invocations | 調用了哪些工具，結果如何 |
| 5. HITL Decisions | 人工審批的決定和理由 |
| 6. Execution Result | 最終結果和驗證 |

**DecisionTracker**: 支援 Redis 快取 (有 fallback 到 InMemory)
**report_generator.py**: ⚠️ 含空函數體 (M-06)

**Domain Audit** (`domain/audit/`, 2 files, 760 LOC):
- AuditLogger: 20 action types, FIFO eviction
- InMemory only (Python list)
- 支援 CSV/JSON export, pub/sub 通知
- ⚠️ 無 PostgreSQL 持久化 (合規風險)

### 7.5 Correlation 與 Root Cause 分析 (Sprint 130 修復)

**Correlation Analyzer** (`integrations/correlation/`, 6 files, 2,187 LOC):

| 版本 | 狀態 | 資料來源 |
|------|------|----------|
| V7 (Before S130) | STUB — 所有底層方法回傳虛構資料 | 硬編碼 |
| V8 (After S130) | FIXED — EventDataSource 真實連線 | Azure Monitor / App Insights REST API |

**修復內容**:
- `_get_event()`, `_get_events_in_range()`, `_get_dependencies()` 等改為真實 API 呼叫
- 上層分析邏輯 (時間關聯、依賴關聯、語義關聯) 已存在
- 降級策略: 外部服務不可用時回傳空結果 (不再回傳假資料)

**Root Cause Analyzer** (`integrations/rootcause/`, 5 files, ~1,500 LOC):

| 版本 | 狀態 | 資料來源 |
|------|------|----------|
| V7 (Before S130) | STUB — 硬編碼 2 個 HistoricalCase | 固定資料 |
| V8 (After S130) | FIXED — CaseRepository + CaseMatcher | 15 真實 IT Ops seed cases |

**修復內容**:
- `CaseRepository`: 案例儲存 (InMemory, PostgreSQL interface 定義)
- `CaseMatcher`: 相似度匹配引擎
- 15 seed cases 涵蓋: Database Pool Exhaustion, Memory Leak, DNS Timeout, etc.
- Claude client 可用時提供 AI 分析

**重要**: API routes (`api/v1/correlation/`, `api/v1/rootcause/`) 仍為 MOCK (C-02, C-04)。Integration layer 已修復但未接線到 API。

### 7.6 日誌與追蹤

| 組件 | 狀態 | 說明 |
|------|------|------|
| Python logging | ✅ | main.py 配置 INFO 級別 |
| Structured JSON logging | ✅ | orchestration/audit/logger.py (281 LOC) |
| OpenTelemetry metrics | ✅ | 有 fallback 機制 |
| Request correlation | ✅ | core/logging 結構化日誌 + correlation ID |
| Sensitive data masking | ✅ | structlog filter (passwords, secrets, tokens) |
| Distributed tracing | ❌ | 無 Jaeger/Zipkin 整合 |
| Jaeger (Docker) | ⚠️ | docker-compose.yml 有定義但需 monitoring profile |

---

## 8. 安全架構詳解

### 8.1 認證架構

**JWT 認證 (Sprint 70, 111)**:

```
Login → POST /auth/login
    → verify_password (bcrypt)
    → create_access_token (HS256, 1-hour expiry)
    → return JWT token

Request → Authorization: Bearer {token}
    → protected_router → Depends(require_auth)
    → jwt.decode() → {user_id, role, email}
    → 輕量驗證 (無 DB 查詢)

Full User → Depends(get_current_user)
    → DB lookup → User model
```

### 8.2 API 安全

| 安全措施 | 實現 | 狀態 |
|----------|------|------|
| Global JWT auth | protected_router (Sprint 111) | ✅ |
| CORS | FastAPI middleware | ✅ |
| Rate limiting | slowapi (InMemory) | ⚠️ Partial |
| Input validation | Pydantic v2 | ✅ |
| RBAC | 無 (僅 JWT role field) | ❌ |

### 8.3 MCP 工具安全

| 安全層 | 實現 | 模式 |
|--------|------|------|
| Permission levels | 4-level RBAC per tool | ✅ |
| Permission checker | Protocol-based injection | ✅ |
| Deny-first evaluation | glob pattern matching | ✅ |
| Audit logging | AuditLogger (未接線 H-06) | ⚠️ |
| Enforcement mode | Log (預設) / Enforce | ⚠️ 預設不阻擋 |

### 8.4 資料安全

| 安全措施 | 實現 | 位置 |
|----------|------|------|
| Sensitive data masking | structlog filter | core/security |
| Path traversal prevention | SandboxConfig sanitizers | core/sandbox_config.py |
| Process isolation | ProcessSandbox + IPC | core/sandbox/ |
| Command injection prevention | Bash tool pattern detection | claude_sdk/tools/ |
| SQL injection risk | ⚠️ f-string in postgres_store.py (C-07) | agent_framework/ |
| API key exposure | ⚠️ key prefix in AG-UI response (C-08) | ag_ui/ |

### 8.5 安全問題總結

| ID | 問題 | 嚴重度 | 建議 |
|----|------|--------|------|
| C-07 | SQL injection via f-string | CRITICAL | 改用 parameterized queries |
| C-08 | API key prefix 暴露 | CRITICAL | 移除或遮罩 |
| H-01 | 無 RBAC on destructive ops | HIGH | 加入 role 檢查 |
| H-02 | Test endpoints in production | HIGH | 加入 APP_ENV 檢查 |
| H-12 | Shell/SSH HITL log-only | HIGH | 啟用 enforce mode |
| H-13 | Azure run_command 無內容驗證 | HIGH | 加入指令白名單 |
| H-14 | Rate limiter InMemory | HIGH | 改用 Redis backend |

---

## 9. Checkpoint 系統

### 9.1 四套 Checkpoint 系統

| 系統 | 位置 | LOC | 用途 | API |
|------|------|-----|------|-----|
| MAF 原生 | agent_framework/checkpoint.py | ~400 | MAF workflow checkpoint | 官方 save_checkpoint/load_checkpoint |
| 混合層 | hybrid/checkpoint/ (9 files) | ~2,000 | 混合編排 checkpoint | 非官方 save/load/delete (H-05) |
| 多輪對話 | agent_framework/multiturn/ | ~600 | 對話 checkpoint | 自訂 |
| 業務層 | domain/checkpoints/ (3 files) | 1,020 | CheckpointService | 自訂 |

### 9.2 混合層 4 Backend

| Backend | 實現 | LOC | 預設 | 生產建議 |
|---------|------|-----|------|----------|
| MemoryCheckpointStorage | dict | ~200 | ✅ 預設 | ❌ |
| RedisCheckpointStorage | Redis async | ~300 | | ✅ |
| PostgresCheckpointStorage | SQLAlchemy | ~400 | | ✅ (合規) |
| FilesystemCheckpointStorage | pathlib | ~250 | | ⚠️ 備用 |

### 9.3 統一問題

- 4 系統使用不同 API 介面，無統一協調
- 混合層 checkpoint 與 MAF 官方 API 不相容
- 預設 Memory backend → 重啟遺失
- 缺少跨系統 checkpoint 關聯機制

---

## 10. InMemory 存儲問題

### 10.1 問題規模

**AST 掃描**: 30 處 InMemory patterns (backend)
**報告交叉驗證**: 20+ 模組受影響，涵蓋 API、Domain、Integration 三層

### 10.2 受影響模組分類

| 風險等級 | 模組 | 資料類型 | 遺失影響 |
|---------|------|---------|---------|
| **CRITICAL** | ag_ui ApprovalStorage | 審批狀態 | 進行中審批遺失 |
| **CRITICAL** | ag_ui ChatSession | 聊天會話 | 活躍對話中斷 |
| **CRITICAL** | domain/audit AuditLogger | 審計日誌 | 合規違規 |
| **HIGH** | orchestration metrics | 路由指標 | 統計歸零 |
| **HIGH** | guided_dialog sessions | 對話補充 | 多輪中斷 |
| **HIGH** | swarm tracker | Swarm 狀態 | 群集遺失 |
| **MEDIUM** | domain/learning | 學習案例 | 知識遺失 |
| **MEDIUM** | domain/templates | 工作流模板 | 模板遺失 |
| **MEDIUM** | domain/routing | 路由場景 | 場景遺失 |
| **MEDIUM** | domain/prompts | 提示模板 | 模板遺失 |
| **LOW** | devtools traces | 除錯追蹤 | 除錯資料遺失 |

### 10.3 優先修復建議

1. **P0**: ApprovalStorage → Redis (已有 RedisApprovalStorage 實現)
2. **P0**: AuditLogger → PostgreSQL
3. **P1**: OrchestrationMetrics → Redis/Prometheus
4. **P1**: GuidedDialog sessions → Redis
5. **P2**: Domain learning/templates → PostgreSQL
6. **P2**: Checkpoint 預設 → Redis

---

## 11. 分析方法論

### 11.1 分析工具鏈

| 工具 | 用途 | 產出 |
|------|------|------|
| AST Scanner (Python) | 後端靜態分析 | backend_analysis_result.json |
| AST Scanner (TypeScript) | 前端靜態分析 | frontend_analysis_result.json |
| 8 Agent 並行分析 | 逐檔代碼審查 | 22 份 Phase 3 報告 |
| E2E Flow Validator | 端到端流程追蹤 | Phase 4 E2E 報告 |
| Plan vs Reality | 計畫合規驗證 | Phase 4 合規報告 |
| Issue Registry | 問題去重分類 | 62 項統一問題清單 |

### 11.2 分析範圍

| Phase | 範圍 | 報告數 |
|-------|------|--------|
| Phase 3A | API Layer (api/v1/) | 3 份 (part1-3) |
| Phase 3B | Domain Layer (domain/) | 3 份 (part1-3) |
| Phase 3C | Integration Layer | 11 份 (agent_framework x2, hybrid x2, orchestration x2, claude_sdk, mcp x2, ag_ui, remaining) |
| Phase 3D | Core + Infrastructure | 1 份 |
| Phase 3E | Frontend | 4 份 (part1-4) |
| Phase 4 | Validation | 3 份 (E2E, Plan vs Reality, Issue Registry) |

### 11.3 與 V7 差異

| 維度 | V7 | V8 |
|------|----|----|
| 分析時間 | Phase 29 | Phase 34 |
| Agent 數量 | 5+3 | 8+3 |
| AST 數據 | 無 | ✅ 精確 |
| Issue Registry | 無 | ✅ 62 項去重 |
| E2E 驗證 | 37 路徑 | 5 完整旅程 (48 步驟) |
| Plan 合規 | 無 | ✅ 70 功能逐項 |

---

## 12. 總結與展望

### 12.1 平台定位總結

IPA Platform 是一個**智能體編排平台**，其核心定位：

1. **不是 n8n 的替代品** --- 確定性工作流由 n8n/Power Automate 處理
2. **處理不確定性任務** --- 需要 AI 判斷力、推理能力、人機互動的複雜場景
3. **MAF + Claude SDK 混合** --- 結構化治理 + 自主智慧，各取所長
4. **企業級治理** --- 完整審計、HITL 審批 (3 套系統)、風險評估、可觀測性
5. **統一工具存取** --- MCP Protocol 提供 8 servers、64 tools 的安全統一介面
6. **Swarm 群集可視化** --- 多 Agent 協作的即時追蹤與 SSE 狀態串流
7. **Sprint 130-132 關鍵修復** --- Correlation/RootCause 真實數據 + Mediator Pattern 重構

### 12.2 實現成熟度

```
成熟度評估 (基於 V8 AST + 22 報告交叉驗證):

Layer 1:  Frontend        ████████████████████ 92% (214 files, 49,357 LOC, 153 components)
Layer 2:  API             ████████████████████ 95% (560 endpoints, 47 routers, 0 empty funcs)
Layer 3:  AG-UI           ████████████████████ 88% (9,836 LOC, 全 11 event types, 7 features)
Layer 4:  Orchestration   ████████████████████ 90% (~16,000 LOC, 含 17 Mock patterns)
Layer 5:  Hybrid          ████████████████████ 85% (24,252 LOC, Mediator 重構完成)
Layer 6:  MAF Builder     ████████████████████ 96% (38,040 LOC, 7/7 primary compliant)
Layer 7:  Claude SDK      ████████████████████ 84% (15,180 LOC, 47 files, 真正 SDK)
Layer 8:  MCP             ████████████████████ 88% (20,920 LOC, 8 servers, 64 tools)
Layer 9:  Supporting      ████████████████████ 82% (S130 修復 correlation/rootcause)
Layer 10: Domain          ████████████████████ 88% (47,200+ LOC, 20 modules, 6 InMemory)
Layer 11: Infrastructure  ████████████░░░░░░░░ 50% (messaging STUB, rate limiter InMemory)
```

### 12.3 後續規劃重點

| 優先級 | 項目 | 原因 |
|--------|------|------|
| **P0** | InMemory 存儲遷移 (C-01) | 20+ 模組重啟遺失所有狀態 |
| **P0→P1** | SQL injection 修復 (C-07) | postgres_storage.py f-string (已有 _validate_table_name 緩解，降級為 P1) |
| **P0** | API Key 暴露修復 (C-08) | AG-UI 回應中洩露 key prefix |
| **P0** | Mock API 路由清理 (C-02~C-05) | Correlation/RootCause/Patrol/Autonomous 100% Mock |
| **P0** | ContextBridge 並行安全 (H-04) | 無 asyncio.Lock，生產環境必要 |
| **P1** | RBAC 破壞性操作保護 (H-01) | cache clear/connector execute 無權限控制 |
| **P1** | Multi-Worker Uvicorn | 生產環境效能 |
| **P1** | Rate limiter → Redis | 多 worker 共享限制 |
| **P1** | 3 套審批系統統一 | AG-UI / Orchestration HITL / Checkpoint 各自獨立 |
| **P2** | RabbitMQ 訊息佇列實現 (C-06) | 非同步任務分派 |

### 12.4 架構演進方向

```
V1 → V2 → V3 → V7 → V8 演進:
═════════════════════════════

V1 (Phase 1-14): 企業 IT 事件智能處理平台
    ↓ 重新定位
V2 (Phase 15-28): 智能體編排平台 + 三層路由 + HITL + MCP (5 servers)
    ↓ Swarm 可視化
V3 (Phase 29): + Agent Swarm + 深度驗證
    ↓ Agent Team 交叉驗證
V6-V7 (Phase 29): 8 Agent 深度交叉驗證 + LOC 修正 (130K→229K)
    ↓ Phase 30-34 擴展
V8 (Phase 34, 現在): + 3 MCP Servers (n8n, ADF, D365) + Mediator Pattern
                      + Correlation/RootCause 真實數據 (S130)
                      + ReactFlow DAG (S133) + 62 問題統一 Registry
                      + AST 精確量化 (308,261 LOC, 10,271 tests)
    ↓ 生產化
下一階段目標:
    ├── 安全加固 (InMemory→Redis/PG, SQL injection, API Key 修復)
    ├── 生產化 (Multi-Worker, RabbitMQ, Container)
    ├── 審批統一 (3 套系統 → 1 統一審批引擎)
    └── Mock 清除 (API Mock routes → 真實實現)
```

---

## 更新歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 8.1 | 2026-03-16 | **MAF RC4 升級反映**: MAF `1.0.0b260114`→`1.0.0rc4`; 6 條 orchestration builder import 遷移至 `agent_framework.orchestrations`; 4 個 builder constructor 改為 kwarg 方式; 4 組類別重命名別名; Claude SDK 同步 (`anthropic>=0.84.0`, 模型 ID 修正, Extended Thinking header 更新); ACL fallback 新增; 新增 GA 升級風險 (R8) 追蹤; 驗證報告: `sdk-version-gap/POST-UPGRADE-Verification-Consensus.md` |
| 8.0 | 2026-03-15 | V8 全面 AST 分析: Phase 34 (S130-133); Backend 725 files, 258,904 LOC; 8 Agent 並行 + E2E 驗證 + 22 份報告; 62 項問題統一 Registry; Mediator Pattern 重構; Correlation/RootCause STUB→REAL; +3 MCP servers; ReactFlow DAG |
| 7.0 | 2026-02-11 | V7 交叉驗證: Backend LOC 重大修正 (130K→229K); 端到端流程驗證 (37 路徑); 4 Checkpoint 系統發現; 27 問題列表; 並行架構分析 |
| 6.0 | 2026-02-11 | V6 Agent Team 分析: Mock 18 個, Endpoints 530, 新增 Auth/Rate Limiting/CORS/Docker 問題 |
| 3.0 | 2026-02-09 | V3 全面更新: Phase 29 Agent Swarm; 5 分析 Agent 並行驗證; 已知問題 11 項 |
| 2.1 | 2026-01-28 | 架構層級命名統一：L1-L11 標準編號 |
| 2.0 | 2026-01-28 | 全面重寫：重新定位為 Agent Orchestration Platform |
| 1.3 | 2026-01-16 | Phase 28 三層意圖路由系統更新 |
| 1.2 | 2026-01-10 | Phase 20 AG-UI 整合更新 |
| 1.1 | 2025-12-20 | Phase 15 Claude SDK 整合 |
| 1.0 | 2025-12-01 | 初始版本 - 企業 IT 事件智能處理平台 |

---

## 附錄

### A. V7 → V8 差異摘要

| Sprint | Phase | 新增功能 | 對 V8 報告影響 |
|--------|-------|---------|---------------|
| S107-S110 | 30 | A2A Protocol, Extended Testing | 新增 a2a/ 模組分析 |
| S111 | 31 | Global Auth Middleware | Layer 2 安全架構更新 |
| S112-S118 | 31 | MCP Permission RBAC, Advanced Tools | Layer 8 安全模型更新 |
| S119-S123 | 32 | Redis centralization, HITL metrics | Infrastructure + 指標更新 |
| S124 | 33 | n8n MCP Server | 新增 MCP server (6 tools) |
| S125 | 33 | ADF MCP Server | 新增 MCP server (8 tools) |
| S126-S128 | 33 | ACL Layer, Swarm Enhancement | Agent Framework ACL + Swarm |
| S129 | 33 | D365 MCP Server | 新增 MCP server (6 tools) |
| S130 | 34 | Correlation/RootCause Real Data | 最重要修復: STUB → REAL |
| S131 | 34 | HITL/Metrics/Core Tests | 測試覆蓋增加 |
| S132 | 34 | Mediator Pattern Refactor | Layer 5 架構重構 |
| S133 | 34 | ReactFlow Workflow DAG | Layer 1 視覺化增強 |

### B. 代碼規模詳情 (AST 精確數據)

**Backend 逐目錄**:

| 目錄 | Files | Lines | Code Lines | Classes | Functions |
|------|-------|-------|------------|---------|-----------|
| api/v1 | 143 | 46,133 | 34,496 | 701 | 896 |
| integrations/agent_framework | 57 | 38,040 | 28,248 | 296 | 1,311 |
| integrations/hybrid | 73 | 24,252 | 18,152 | 208 | 749 |
| integrations/mcp | 73 | 20,920 | 17,000 | 117 | 583 |
| integrations/claude_sdk | 47 | 15,180 | 11,625 | 145 | 493 |
| domain/sessions | 33 | 12,272 | ~9,400 | 80+ | 300+ |
| domain/orchestration | 22 | 11,487 | 8,680 | 82 | 424 |
| integrations/ag_ui | 24 | 9,836 | 7,554 | 85 | 290 |
| core/performance | 9 | 4,772 | 3,763 | 43 | 171 |
| domain/connectors | 6 | 3,686 | 2,862 | 10 | 90 |
| infrastructure/database | 18 | 2,793 | 2,035 | — | — |
| core/sandbox | 7 | 2,555 | 1,824 | 19 | 76 |
| integrations/correlation | 6 | 2,187 | 1,695 | 16 | 62 |
| integrations/incident | 6 | 2,105 | 1,748 | 12 | 36 |
| infrastructure/checkpoint | 8 | 1,876 | 1,497 | 7 | 47 |

**Frontend 逐目錄**:

| 目錄 | Files | Code Lines | Components | Interfaces |
|------|-------|------------|------------|------------|
| components/ | 137 | 18,538 | 90 | 220 |
| pages/ | 40 | 10,467 | 38 | 67 |
| hooks/ | 17 | 5,304 | 16 | 101 |
| stores/ | 3 | 984 | 2 | — |
| api/ | 6 | 797 | 3 | 65 |
| types/ | 3 | 816 | 0 | 87 |

### C. 完整問題清單 (62 項)

#### CRITICAL (8 項)

| ID | 問題 | 影響模組 | 報告來源 |
|----|------|---------|---------|
| C-01 | 全域 InMemory 存儲 — 重啟遺失所有狀態 | 20+ modules (API, Domain, Integration) | 3A-1/2/3, 3B-3, 3C-ag-ui, 3C-remaining |
| C-02 | Correlation API routes 100% Mock — 未連接真實 CorrelationAnalyzer **(V9 精化: S130 已修復 integration 模組，但 API routes 仍未接線)** | api/v1/correlation/ (7 endpoints) | 3A-1, 3C-remaining |
| C-03 | Autonomous API routes 100% Mock — UAT stub 無真實規劃引擎 | api/v1/autonomous/ | 3A-1 |
| C-04 | RootCause API routes 100% Mock — 未連接真實 RootCauseAnalyzer | api/v1/rootcause/ (4 endpoints) | 3A-3, 3C-remaining |
| C-05 | Patrol API routes 100% Mock — 未連接真實 PatrolAgent | api/v1/patrol/ (9 endpoints) | 3A-3, 3C-remaining |
| C-06 | messaging/ infrastructure STUB — RabbitMQ 僅 1 行註解 | infrastructure/messaging/ | 3D-core-infra |
| C-07 | SQL injection via f-string table name — postgres_storage.py **(V9 修正: 檔名 postgres_storage.py; 已添加 _validate_table_name() 緩解)** | agent_framework/memory/postgres_storage.py | 3C-af-part2 |
| C-08 | API key prefix 暴露於 AG-UI 回應 | ag_ui/ response data | 3A-1 |

#### HIGH (16 項)

| ID | 問題 | 影響模組 |
|----|------|---------|
| H-01 | 無 RBAC 在破壞性操作 (cache clear, connector execute) | api/v1/cache, connectors, agents |
| H-02 | ag_ui /test/* 端點不受 APP_ENV 環境限制 | api/v1/ag_ui/ |
| H-03 | 全域 Singleton anti-pattern (10+ modules) | DeadlockDetector, MetricsCollector, SessionEventPublisher... |
| H-04 | ContextBridge._context_cache 無 asyncio.Lock | hybrid/context/bridge.py |
| H-05 | Checkpoint storage 使用非官方 API (save/load/delete) | hybrid/checkpoint/ |
| H-06 | MCP AuditLogger 未接線 (8 servers) | mcp/servers/* |
| H-07 | TypeScript enum 使用不一致 (string literal vs const) | frontend types/ |
| H-08 | 前端 10 頁面靜默降級 Mock — 使用者無法區分 | Dashboard, Agents, Workflows, Approvals... |
| H-09 | Sandbox 模擬 — 無真正 process isolation | domain/sandbox/ |
| H-10 | domain/orchestration 已棄用但 API 仍引用 | domain/orchestration/ (4 sub-modules) |
| H-11 | Chat 歷史僅 localStorage — 無後端同步 | frontend UnifiedChat.tsx |
| H-12 | Shell/SSH HITL = log-only (不阻擋非白名單指令) | mcp/servers/shell, ssh |
| H-13 | Azure run_command 可執行任意 VM 指令 | mcp/servers/azure |
| H-14 | Rate limiter InMemory — 多 worker 獨立限制 | middleware/ |
| H-15 | 缺少 React Error Boundaries (5+ components) | frontend components/ |
| H-16 | domain/orchestration raw SQL in postgres_store | domain/orchestration/ |

#### MEDIUM (22 項)

| ID | 問題 | 影響模組 |
|----|------|---------|
| M-01 | `datetime.utcnow()` deprecated in Python 3.12+ | 6+ files across modules |
| M-02 | Health check 使用 os.environ 違反 pydantic Settings 規則 | main.py |
| M-03 | Dashboard chart N+1 查詢 (7天×3查詢=21) | api/v1/dashboard/ |
| M-04 | Dashboard stats 靜默吞掉異常 | api/v1/dashboard/ |
| M-05 | ServiceNow MCP server 未呼叫 set_permission_checker() **(V9 路徑修正: mcp/servicenow_server.py)** | mcp/servicenow_server.py |
| M-06 | ~~report_generator.py 含空函數體~~ **(V9 已修復: 8 個函數均已實現)** | ~~integrations/audit/~~ RESOLVED |
| M-07 | Session.query() streaming 參數接受但未實現 | claude_sdk/session.py |
| M-08 | Registry MCP tool integration = TODO stub | claude_sdk/registry.py |
| M-09 | CaseRepository PostgreSQL = interface-only (fallback InMemory) | integrations/rootcause/ |
| M-10 | StateDeltaOperation(str) 應改用 Enum | ag_ui/events/ |
| M-11 | AG-UI thread InMemory 預設 — 對話遺失 | ag_ui/thread/ |
| M-12 | D365 OData filter 可能注入風險 | mcp/servers/d365/ |
| M-13 | SSH auto_add_host_keys 開發模式風險 | mcp/servers/ssh/ |
| M-14 | 無 inbound rate limiting at MCP protocol level | mcp/core/protocol.py |
| M-15 | Risk engine hooks 同步 — 可能阻塞 event loop | hybrid/risk/ |
| M-16 | Frontend useRef without cleanup in useEffect | frontend hooks/ |
| M-17 | Frontend console.log in production code (99 instances) | frontend (AST) |
| M-18 | AG-UI SharedState diffing 效能未測試 | ag_ui/features/advanced/ |
| M-19 | Workflow topological sort 無環檢測 | api/v1/workflows/ |
| M-20 | Agent capability matching O(n) linear scan | domain/agents/ |
| M-21 | Teams notification uses deprecated datetime.utcnow() | domain/notifications/ |
| M-22 | LLM retry logic 缺少 exponential backoff cap | integrations/llm/ |

#### LOW (16 項)

| ID | 問題 | 影響模組 |
|----|------|---------|
| L-01 | ui/index.ts 僅匯出 3/18 元件 | frontend components/ui/ |
| L-02 | dialog.tsx lowercase 與 PascalCase 不一致 | frontend components/ui/ |
| L-03 | pairedEvent prop 接收但未使用 | frontend DevUI/ |
| L-04 | Header search 無防抖 (debounce) | frontend components/layout/ |
| L-05 | CSS hover 效果缺少 focus-visible 可及性 | frontend components/ |
| L-06 | Frontend bundle size 未最佳化 | frontend config |
| L-07 | TypeScript strict mode 未啟用 | frontend tsconfig.json |
| L-08 | Backend missing __all__ exports | backend domain/ |
| L-09 | Inconsistent error response format | backend api/v1/ |
| L-10 | Missing OpenAPI tags on some endpoints | backend api/v1/ |
| L-11 | Unused import in some modules | backend various |
| L-12 | Docker compose monitoring profile undocumented | docker-compose.yml |
| L-13 | Missing health check for Redis in startup | backend main.py |
| L-14 | infrastructure/__init__.py content mismatch | backend infrastructure/ |
| L-15 | Hardcoded AG-UI health version "1.0.0" | api/v1/ag_ui/ |
| L-16 | UnifiedChat.tsx 含 2 處 TODO 註解 | frontend pages/ |

### D. 成熟度評估 (V8 更新)

```
成熟度評估 (基於 V8 AST + 22 報告交叉驗證):

Layer 1:  Frontend        ████████████████████ 92% (214 files, 49,357 LOC, 153 components)
Layer 2:  API             ████████████████████ 95% (560 endpoints, 47 routers, 0 empty funcs)
Layer 3:  AG-UI           ████████████████████ 88% (9,836 LOC, 全 11 event types, 7 features)
Layer 4:  Orchestration   ████████████████████ 90% (~16,000 LOC, 含 17 Mock patterns)
Layer 5:  Hybrid          ████████████████████ 85% (24,252 LOC, Mediator 重構完成)
Layer 6:  MAF Builder     ████████████████████ 96% (38,040 LOC, 7/7 primary compliant)
Layer 7:  Claude SDK      ████████████████████ 84% (15,180 LOC, 47 files, 真正 SDK)
Layer 8:  MCP             ████████████████████ 88% (20,920 LOC, 8 servers, 64 tools)
Layer 9:  Supporting      ████████████████████ 82% (S130 修復 correlation/rootcause)
Layer 10: Domain          ████████████████████ 88% (47,200+ LOC, 20 modules, 6 InMemory)
Layer 11: Infrastructure  ████████████░░░░░░░░ 50% (messaging STUB, rate limiter InMemory)
```

**V7 → V8 成熟度變化**:

| Layer | V7 | V8 | 變化 | 原因 |
|-------|----|----|------|------|
| L5 Hybrid | 82% | 85% | +3% | Sprint 132 Mediator Pattern |
| L8 MCP | 80% | 88% | +8% | +3 servers (n8n, ADF, D365) |
| L9 Supporting | 72% | 82% | +10% | Sprint 130 correlation/rootcause fix |
| L11 Infra | 45% | 50% | +5% | Redis centralization (S119) |

### E. Sprint 歷史 (Phase 29-34)

| Phase | Sprints | 主題 | Story Points (est.) |
|-------|---------|------|---------------------|
| Phase 29 | S100-S106 | Agent Swarm | ~160 |
| Phase 30 | S107-S110 | A2A Protocol + Extended Testing | ~120 |
| Phase 31 | S111-S118 | Security + MCP Permissions | ~200 |
| Phase 32 | S119-S123 | Redis Centralization + Metrics | ~150 |
| Phase 33 | S124-S129 | MCP Expansion (n8n, ADF, D365) + ACL | ~180 |
| Phase 34 | S130-S133 | Correlation Fix + Mediator + DAG Viz | ~160 |

---

> **文件結束**
> 
> 本報告基於 2026-03-15 的 AST 靜態分析和 22 份深度代碼分析報告生成。
> 所有數據來源已在各節標注。報告格式遵循 V7 結構，所有內容使用 V8 分析數據。
