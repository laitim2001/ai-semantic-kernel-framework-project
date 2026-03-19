# IPA Platform — Use Case 端到端組裝藍圖

> **文件版本**: 1.0
> **建立日期**: 2026-03-18
> **定位**: 將現有 70+ 功能組裝成可運行的端到端系統的實施指南
> **前置文件**: `MAF-Claude-Hybrid-Architecture-V8.md`、`MAF-Features-Architecture-Mapping-V8.md`
> **核心問題**: 280K+ LOC、70 個功能，但從未端到端組裝並真正運行

---

## 核心認知

本項目的問題不是「功能不夠多」— 相反，功能已經過多。問題是：

1. **組件之間的「最後一英里」接線沒有完成** — 整合層完成了但 API 路由沒接通（4 個 SPLIT 功能）
2. **沒有一個統一的「主角」驅動整個流程** — 缺少一個真正的 orchestrator agent 作為系統的中央智能
3. **持久化層有 20+ 個斷點** — InMemory 存儲意味著重啟就丟失一切
4. **從未定義過「什麼叫做跑起來」** — 缺少一個明確的 use case 作為組裝目標

本文件的核心就是定義這個目標，然後反向推導需要組裝什麼。

---

## Part 1: 目標 Use Case 定義

### Use Case: 企業 IT 運維智能助手

**一句話**: 企業用戶通過 Chat UI 與一個 AI 助手對話，這個助手能理解意圖、評估風險、分派任務給專業 Agent、調用企業工具、記住歷史、並在需要時請人工審批。

### 目標用戶畫像

- **台灣/香港企業的 IT 運維人員**
- 在瀏覽器中登入平台
- 用繁體中文描述問題或請求
- 期望助手能像一個資深 IT 主管那樣理解問題並協調處理

### 完整流程（10 步驟）

以下是一次完整互動的端到端流程，也是本項目需要組裝的目標效果：

---

## Part 2: 十步端到端流程規格

### Step 1 — 用戶登入並開始/繼續對話

```
用戶 ──[瀏覽器]──→ Login Page ──→ JWT Token ──→ Chat UI
                                                   │
                                            ┌──────┴──────┐
                                            │ 開始新對話   │
                                            │ 繼續舊對話   │
                                            │ 查看任務列表 │
                                            └─────────────┘
```

**用戶能做的事**:
- 登入後看到自己的對話歷史列表（可繼續、可刪除）
- 看到進行中/待處理的任務列表（跨 session 持久）
- 開始一個新對話，或點擊繼續之前的對話

**現有組件**:
| 組件 | 狀態 | 位置 |
|------|------|------|
| Login/Signup | ✅ 完整 | `pages/auth/` |
| JWT Auth | ✅ 完整 | `core/auth.py` |
| Session CRUD API | ✅ 完整 | `domain/sessions/` (12,272 LOC) |
| Chat UI | ✅ 完整 | `pages/UnifiedChat.tsx` + 27 components |

**缺失 / 需要組裝**:
| 缺失項 | 說明 | 優先級 |
|--------|------|--------|
| 對話歷史後端同步 | H-11: 目前 chat history 僅存在 localStorage，需同步到後端 | P1 |
| 任務列表 UI + API | 目前不存在。用戶無法跨 session 看到進行中的任務 | P1 |
| Session resume 流程 | Session state machine 有 SUSPENDED 狀態，但前端沒有「繼續對話」的 UI flow | P2 |

---

### Step 2 — InputGateway 接收並標準化輸入

```
Chat UI ──[POST /api/v1/ag-ui/chat]──→ InputGateway
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │ ServiceNow Handler   │ Prometheus Handler   │ UserInput Handler
                    │ (Webhook, 20+ maps)  │ (41 regex patterns)  │ (pass-through)
                    └──────────────────────┼──────────────────────┘
                                           │
                                           ▼
                                 UnifiedRequestEnvelope
                                 {source, content, user_id, session_id, metadata}
```

**用戶感知**: 無（後台處理，<1ms）

**現有組件**:
| 組件 | 狀態 | 位置 |
|------|------|------|
| InputGateway | ✅ 完整 | `orchestration/input_gateway/` |
| 3 Handler | ✅ 完整 | ServiceNow (UAT only), Prometheus, UserInput |
| UnifiedRequestEnvelope | ✅ 完整 | 標準化輸出格式 |

**需要組裝**:
| 接線項 | 說明 | 優先級 |
|--------|------|--------|
| Chat API → InputGateway | 確認 AG-UI chat endpoint 是否經過 InputGateway | P0 |
| User context injection | UnifiedRequestEnvelope 需攜帶 user_id + session_id (from JWT) | P1 |

---

### Step 3 — 三層意圖路由

```
UnifiedRequestEnvelope
        │
        ▼
┌─────────────────────────────────────────────────┐
│ BusinessIntentRouter (三層瀑布)                    │
│                                                   │
│  L1: PatternMatcher (<10ms, 30+ regex)           │
│       ↓ miss                                      │
│  L2: SemanticRouter (<100ms, 15 routes)          │
│       ↓ miss                                      │
│  L3: LLMClassifier (<2000ms, Azure OpenAI)       │
│                                                   │
│  Output: RoutingDecision {                        │
│    intent: INCIDENT/REQUEST/CHANGE/QUERY/UNKNOWN, │
│    sub_intent: system_down/security_incident/..., │
│    confidence: 0.0-1.0,                           │
│    routing_layer: L1/L2/L3,                       │
│    is_sufficient: bool                            │
│  }                                                │
└─────────────────────────────────────────────────┘
```

**用戶感知**: 無（後台處理，<10ms 到 <2s）

**現有組件**: ✅ 全部完整（PatternMatcher、SemanticRouter、LLMClassifier、BusinessIntentRouter）

**需要組裝**:
| 接線項 | 說明 | 優先級 |
|--------|------|--------|
| API Key 配置 | SemanticRouter + LLMClassifier 預設使用 Mock，需配置真實 API Key | P0 |
| Session context 傳遞 | 路由結果需要寫入 session context 供後續步驟使用 | P1 |

---

### Step 4 — 完整性檢查 + 引導對話

```
RoutingDecision.is_sufficient?
        │
   ┌────┴────┐
  YES       NO ──→ GuidedDialogEngine
   │                 │ 狀態: INITIAL → GATHERING → COMPLETE
   │                 │ 模板式繁中問題生成
   │                 │ 後續回合用 rule-based 提取 (不重複呼叫 LLM)
   │              ←──┘ (補充後重新評估)
   ▼
 Forward to Step 5
```

**用戶感知**: 如果資訊不足，助手會用繁體中文追問（如「請問是哪個 Pipeline？錯誤訊息是什麼？影響範圍有多大？」）

**現有組件**: ✅ 全部完整（CompletenessChecker、GuidedDialogEngine、RefinementRules）

**需要組裝**:
| 接線項 | 說明 | 優先級 |
|--------|------|--------|
| Dialog session 持久化 | C-01: 目前 InMemory，多輪對話中途重啟會遺失 | P1 |
| AG-UI 串流整合 | 追問問題需要通過 SSE 串流回前端 | P1 |

---

### Step 5 — 風險評估 + 人工審批判斷

```
RoutingDecision + UserInput
        │
        ▼
┌─────────────────────────────────────┐
│ RiskAssessor (7 維度)                │
│  Intent(0.8) + SubIntent(0.5) +    │
│  Production(0.3) + Weekend(0.2) +  │
│  Urgent(0.15) + AffectedSys +     │
│  LowConfidence                      │
│                                     │
│  Output: RiskLevel                  │
│  LOW(0-0.3) → 自動執行              │
│  MEDIUM(0.3-0.6) → 自動+記錄        │
│  HIGH(0.6-0.85) → 需單人審批        │
│  CRITICAL(0.85-1.0) → 需多人審批    │
└──────────────┬──────────────────────┘
               │
          ┌────┴────┐
        LOW/MED    HIGH/CRIT
          │           │
          │    HITLController
          │    → Teams Adaptive Card (繁中)
          │    → 等待審批 (timeout: 30min)
          │    → APPROVED / REJECTED / EXPIRED
          │        ←──┘
          ▼
       Forward to Step 6
```

**用戶感知**:
- LOW/MEDIUM: 無感知（自動進入下一步）
- HIGH/CRITICAL: 「此操作需要審批。已通知審批人 [姓名]，請等待...」

**現有組件**: ✅ 全部完整（RiskAssessor、HITLController、Teams Notification）

**需要組裝**:
| 接線項 | 說明 | 優先級 |
|--------|------|--------|
| 統一 3 套審批系統 | 目前 AG-UI / Orchestration HITL / Claude SDK 各自獨立 | P1 |
| 審批狀態持久化 | C-01: 審批狀態 InMemory，重啟遺失 | P1 |
| 等待期間的 session 處理 | 用戶可能關閉視窗，需要 checkpoint (→ Step 9) | P2 |

---

### Step 6 — Orchestrator Agent 接收任務並決策

```
(審批通過 or 自動通過)
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Orchestrator Agent (本項目的核心智能)                       │
│                                                           │
│ 身份: 一個持久的 Claude/GPT Agent 實例                     │
│ 角色: 企業 IT 運維主管 — 熟悉企業環境、系統架構、團隊分工   │
│                                                           │
│ 輸入:                                                     │
│  - RoutingDecision (意圖 + 風險)                          │
│  - UserInput (原始請求)                                    │
│  - SessionContext (對話歷史)                                │
│  - MemoryContext (用戶偏好 + 過去案例)                      │
│  - EnterpriseKnowledge (Agent Skills / RAG)               │
│                                                           │
│ 決策 (LLM 推理):                                          │
│  ├─ 直接回答 → 簡單問題/查詢，直接回應                     │
│  ├─ 單一 Agent → 明確任務，派給專業 Agent                  │
│  ├─ MAF Workflow → 結構化多步驟任務                        │
│  ├─ Claude Extended Thinking → 複雜分析推理                │
│  └─ Swarm → 需要多 Agent 並行協作                          │
│                                                           │
│ 工具 (Orchestrator 可用的 Tools):                          │
│  - route_intent() → 呼叫三層路由系統                       │
│  - assess_risk() → 呼叫 RiskAssessor                      │
│  - dispatch_workflow() → 啟動 MAF Workflow                 │
│  - dispatch_swarm() → 啟動 Swarm 群集                      │
│  - search_memory() → 查詢歷史記憶                          │
│  - search_knowledge() → 查詢企業知識庫 (Agentic RAG)       │
│  - request_approval() → 請求人工審批                        │
│  - respond_to_user() → 回覆用戶                            │
└──────────────────────────────────────────────────────────┘
```

**用戶感知**: 助手正在思考中...（通過 AG-UI SSE 串流展示思考過程）

**現有組件**:
| 組件 | 狀態 | 說明 |
|------|------|------|
| HybridOrchestratorV2 / OrchestratorMediator | ✅ 代碼邏輯存在 | 但不是 Agent，是程式碼 |
| FrameworkSelector | ✅ 完整 | 5 種策略 |
| ContextBridge | ✅ 完整 | 但無 asyncio.Lock (H-04) |

**缺失 / 需要重新設計**:
| 缺失項 | 說明 | 優先級 |
|--------|------|--------|
| Orchestrator 作為 Agent | 目前是代碼邏輯，需要改造為 MAF ClaudeAgent 實例 | **P0** |
| Agent system prompt | 定義 orchestrator 的角色、能力、企業背景知識 | **P0** |
| Orchestrator tools | 將現有功能包裝為 orchestrator 的 function tools | **P0** |
| Memory context injection | 每次對話注入相關記憶 | P1 |
| Enterprise knowledge injection | 通過 Agent Skills 或 RAG 注入企業知識 | P1 |

> **這是整個組裝計劃中最關鍵的改造點**。現有的 OrchestratorMediator 6 個 Handler 
> 的邏輯不需要丟棄，而是重新定位為 Orchestrator Agent 的「tools」和「hooks」。
> Agent 用 LLM 推理來決定調用哪個 tool，而 tool 的內部實現就是現有的 Handler 邏輯。

---

### Step 7 — 任務分派與執行

```
Orchestrator Agent 的決策
        │
   ┌────┼────────────────────────────┐
   │    │                            │
   ▼    ▼                            ▼
┌─────────┐  ┌──────────────┐  ┌──────────────┐
│ Claude  │  │  MAF Workflow │  │    Swarm     │
│ Worker  │  │  (Sequential/ │  │  (Parallel   │
│ Pool    │  │   Concurrent/ │  │   Workers)   │
│         │  │   Magentic)   │  │              │
└────┬────┘  └──────┬───────┘  └──────┬───────┘
     │              │                  │
     │         各 Worker/Agent         │
     │         使用 MCP 工具           │
     │              │                  │
     └──────────────┼──────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │  MCP Tool Layer │
           │  8 Servers      │
           │  64 Tools       │
           └────────────────┘
```

**用戶感知**: 通過 AG-UI SSE 即時看到：
- Agent 正在執行的步驟
- 工具調用的過程和結果
- Swarm 模式下各 Worker 的即時進度

**現有組件**: ✅ 大部分完整

**需要組裝**:
| 接線項 | 說明 | 優先級 |
|--------|------|--------|
| Swarm 整合到主流程 | 目前 Swarm 是獨立 Demo API，需整合到 Orchestrator Agent 的 dispatch 路徑 | P1 |
| Worker 結果回傳 | 子 Agent 的結果需要統一格式回傳給 Orchestrator Agent | P1 |
| Checkpoint during execution | 長時間執行過程中自動 checkpoint | P2 |

---

### Step 8 — 可觀測性 + AG-UI 即時串流

```
所有層級的事件
        │
        ▼
┌───────────────────────────────────────────────┐
│ AG-UI SSE 即時串流 (11 event types)             │
│                                                │
│ TEXT_MESSAGE_START/CONTENT/END → 思考過程       │
│ TOOL_CALL_START/ARGS/END → 工具調用             │
│ APPROVAL_REQUEST → 審批卡片                    │
│ STATE_SNAPSHOT/DELTA → 狀態更新                │
│ RUN_STARTED/FINISHED → 生命週期                │
│ CUSTOM (swarm_*, workflow_*) → 群集+工作流     │
│                                                │
│ + AuditLogger 記錄每一步                        │
│ + OTel Metrics 記錄效能                         │
│ + DevUI Tracing 記錄執行追蹤                    │
└───────────────────────────────────────────────┘
```

**用戶感知**: Chat UI 中即時看到助手的思考過程、工具使用、進度更新

**現有組件**: ✅ AG-UI 完整；⚠️ Audit/Patrol/Correlation API 為 STUB

**需要組裝**:
| 接線項 | 說明 | 優先級 |
|--------|------|--------|
| G3/G4/G5 API 接通 | Patrol/Correlation/RootCause 整合層完成但 API 未接通 | P2 |
| Audit 持久化 | C-01: AuditLogger 從 InMemory 遷移到 PostgreSQL | P1 |
| token-by-token streaming | 目前是 100 char chunks，非真正串流 | P3 |

---

### Step 9 — 結果整合 + 回應 + Checkpointing

```
所有子 Agent 結果
        │
        ▼
┌───────────────────────────────────────────────┐
│ Orchestrator Agent (最終整合)                    │
│                                                │
│ 1. 收集所有子 Agent/Worker 的結果               │
│ 2. 用 LLM 推理綜合分析                          │
│ 3. 產出結構化回應 (問題摘要 + 執行結果 + 建議)   │
│ 4. 寫入 Audit Trail                             │
│ 5. 寫入 Memory (對話記錄 + 任務結果)             │
│ 6. 建立 Checkpoint (如果任務未完成)              │
│ 7. 通過 AG-UI SSE 回應用戶                       │
└──────────────┬────────────────────────────────┘
               │
          ┌────┴────┐
        完成       未完成 (需等待審批/外部事件)
          │           │
    直接回應用戶   建立 Checkpoint
                    │
              存入 Task Registry
              │
        通知用戶: 「任務 #T-001 正在處理中，
                  需要 [某人] 審批。
                  您可以隨時回來查看進度。」
```

**用戶感知**:
- 任務完成: 收到完整的回應
- 任務進行中: 收到進度更新 + 任務編號，可以安心關閉視窗

**缺失 / 需要建立**:
| 缺失項 | 說明 | 優先級 |
|--------|------|--------|
| Task Registry | 獨立於 session 的任務管理表（PostgreSQL） | **P0** |
| Checkpoint 切換到 PostgreSQL | 預設 InMemory，需要切換 | P1 |
| Background Response | 利用 MAF RC4 的 continuation_token 機制 | P1 |
| 結果寫入 Memory | Orchestrator 完成後自動寫入 episodic memory | P1 |

---

### Step 10 — 記憶 + 知識系統

```
┌─────────────────────────────────────────────────────────────┐
│                    記憶與知識系統 (持續運行)                    │
│                                                              │
│  ┌─────────────── Memory (記憶) ───────────────┐             │
│  │                                              │             │
│  │  Working Memory (Redis, TTL)                 │             │
│  │  └─ 當前對話上下文、最近的工具結果            │             │
│  │                                              │             │
│  │  Episodic Memory (Qdrant + PostgreSQL)        │             │
│  │  └─ 每次對話摘要、任務執行記錄、學到的教訓    │             │
│  │                                              │             │
│  │  Semantic Memory (Qdrant + PostgreSQL)        │             │
│  │  └─ 用戶偏好、常見問題模式、企業系統關係圖    │             │
│  │                                              │             │
│  │  自動記憶流程:                                │             │
│  │  對話結束 → 摘要寫入 Episodic                 │             │
│  │  多次重複模式 → 提升為 Semantic               │             │
│  │  新對話開始 → 檢索相關記憶注入 Context         │             │
│  └──────────────────────────────────────────────┘             │
│                                                              │
│  ┌─────────── Knowledge (知識 / Agentic RAG) ────────────┐   │
│  │                                                        │   │
│  │  知識來源:                                              │   │
│  │  ├─ ITIL 流程文檔 (SOP, Runbooks)                      │   │
│  │  ├─ 企業系統架構文檔                                    │   │
│  │  ├─ 歷史事件報告                                        │   │
│  │  └─ 政策與合規要求                                      │   │
│  │                                                        │   │
│  │  實現方式 (二擇一或混合):                                │   │
│  │                                                        │   │
│  │  方式 A: Agent Skills (MAF 原生)                        │   │
│  │  ├─ SKILL.md 打包 ITIL 流程指引                         │   │
│  │  ├─ scripts/ 打包可執行的檢查腳本                       │   │
│  │  ├─ references/ 打包政策文檔                            │   │
│  │  └─ SkillsProvider 自動注入 orchestrator context        │   │
│  │                                                        │   │
│  │  方式 B: Vector RAG (Agentic)                           │   │
│  │  ├─ 文檔 → chunking → embedding → Qdrant               │   │
│  │  ├─ search_knowledge() 作為 MCP Tool 或 Function Tool   │   │
│  │  └─ Orchestrator Agent 自主決定何時/如何檢索             │   │
│  │                                                        │   │
│  │  建議: 混合使用                                          │   │
│  │  Agent Skills → 結構化流程知識 (ITIL SOP)               │   │
│  │  Vector RAG → 非結構化文檔檢索 (歷史報告、郵件等)       │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**用戶感知**:
- 「你好，我上次提到的 APAC Pipeline 問題解決了嗎？」→ 助手記得之前的對話和任務
- 「依照公司的變更管理流程，這個操作需要怎麼做？」→ 助手查閱知識庫後回答

**現有組件**:
| 組件 | 狀態 | 說明 |
|------|------|------|
| mem0 三層記憶 | ✅ 基礎完成 | 但未接線到 orchestrator |
| Memory API (7 endpoints) | ✅ 完整 | 可用但未被自動調用 |
| Qdrant 向量庫 | ✅ 已整合 | mem0 後端 |
| LearningService | ⚠️ InMemory | 需遷移 |

**缺失 / 需要建立**:
| 缺失項 | 說明 | 優先級 |
|--------|------|--------|
| 自動記憶寫入 | 對話結束時自動摘要→寫入 episodic memory | P1 |
| 記憶檢索注入 | 新對話開始時自動檢索相關記憶→注入 orchestrator context | P1 |
| 知識庫攝入管線 | 文檔→chunking→embedding→Qdrant 的 pipeline | P1 |
| search_knowledge tool | Orchestrator 的 Agentic RAG 工具 | P1 |
| Agent Skills 打包 | 將 ITIL 流程打包為 MAF Agent Skills | P2 |
| 知識庫管理 UI | 上傳/管理知識文檔的前端介面 | P3 |

---

## Part 3: 組裝狀態總覽

### 每步驟的組件準備度

```
Step 1  登入+Session      ████████████████░░░░  70%  缺 chat 後端同步 + 任務列表
Step 2  InputGateway      ██████████████████░░  90%  缺 user context injection
Step 3  意圖路由          ██████████████████░░  90%  缺 API Key 配置
Step 4  完整性+引導對話    ████████████████░░░░  80%  缺 dialog session 持久化
Step 5  風險+審批         ████████████████░░░░  80%  缺 審批系統統一
Step 6  Orchestrator Agent ████████░░░░░░░░░░░░  40%  核心改造: 代碼→Agent
Step 7  任務分派+執行     ██████████████░░░░░░  65%  缺 Swarm 主流程整合
Step 8  可觀測性+串流     ██████████████░░░░░░  65%  缺 STUB API 接通
Step 9  結果+Checkpoint   ██████████░░░░░░░░░░  50%  缺 Task Registry + 持久化
Step 10 記憶+知識         ██████░░░░░░░░░░░░░░  35%  最大 gap: RAG + 記憶接線
```

### 三類工作

| 類型 | 說明 | 工作量佔比 |
|------|------|-----------|
| **接線** (Wiring) | 已有組件之間的連接 — API 接通、context 傳遞、event 橋接 | ~40% |
| **改造** (Refactoring) | 將現有邏輯重新定位 — Orchestrator 代碼→Agent、InMemory→PostgreSQL | ~35% |
| **新建** (New Build) | 全新功能 — Task Registry、RAG Pipeline、Agent Skills 打包 | ~25% |

---

## Part 4: 組裝優先順序

### Phase A: 基礎可跑 (3 Sprints, ~40 SP)

**目標**: 最簡端到端流程可以跑通 — 用戶發消息 → 意圖路由 → Orchestrator 回應

| # | 任務 | SP | 說明 |
|---|------|-----|------|
| A1 | Orchestrator Agent 原型 | 8 | 建立 ClaudeAgent 實例，system prompt 定義角色，基礎 tools (respond, route_intent) |
| A2 | Chat → InputGateway → Router → Orchestrator 接線 | 5 | 確保消息能從前端到 orchestrator 並回應 |
| A3 | API Key 配置 + SemanticRouter 啟用 | 3 | 讓三層路由真正工作 |
| A4 | InMemory → Redis/PG 遷移 (核心 5 模組) | 8 | Dialog sessions, approval state, audit log, checkpoint, rate limiter |
| A5 | Chat history 後端同步 | 5 | localStorage → PostgreSQL |
| A6 | 統一審批系統 | 5 | 3 套→1 套，以 HITLController 為主 |
| A7 | MAF RC4 遺漏修復 | 5 | 執行 SCAN-1 到 SCAN-8 的修復 |

**Phase A 交付物**: 用戶可以登入→對話→Orchestrator 理解意圖→直接回答簡單問題→高風險時觸發審批

### Phase B: 任務執行 (3 Sprints, ~40 SP)

**目標**: Orchestrator 能派發任務給子 Agent，子 Agent 能使用 MCP 工具

| # | 任務 | SP | 說明 |
|---|------|-----|------|
| B1 | Orchestrator dispatch tools | 5 | dispatch_workflow(), dispatch_to_claude(), dispatch_swarm() 作為 tools |
| B2 | MAF Workflow 接通 | 5 | Orchestrator 能啟動 Sequential/Concurrent workflow |
| B3 | Claude Worker 接通 | 5 | Orchestrator 能派任務給 Claude worker pool |
| B4 | Swarm 整合到主流程 | 8 | 從 Demo API 移到 Orchestrator 的 dispatch 路徑 |
| B5 | Task Registry | 5 | PostgreSQL 任務表 + CRUD API + 前端任務列表 |
| B6 | Checkpoint 持久化 | 5 | 切換到 PostgreSQL backend，MAF RC4 checkpoint 介面對齊 |
| B7 | Background Response | 5 | 利用 MAF continuation_token 實現長時間任務 |
| B8 | STUB API 接通 | 3 | G3/G4/G5 Patrol/Correlation/RootCause |

**Phase B 交付物**: 用戶請求→Orchestrator 分派→子 Agent 執行→MCP 工具操作→結果回傳→用戶收到回應

### Phase C: 記憶 + 知識 (2 Sprints, ~25 SP)

**目標**: Orchestrator 有記憶和知識，能像資深員工一樣工作

| # | 任務 | SP | 說明 |
|---|------|-----|------|
| C1 | 自動記憶寫入 | 5 | 對話結束自動摘要→寫入 mem0 episodic |
| C2 | 記憶檢索注入 | 5 | 新對話開始→檢索相關記憶→注入 orchestrator context_provider |
| C3 | RAG Pipeline | 5 | 文檔攝入→chunking→embedding→Qdrant |
| C4 | search_knowledge tool | 3 | Orchestrator 的 Agentic RAG function tool |
| C5 | Agent Skills 打包 | 5 | ITIL SOP 打包為 SKILL.md + scripts/ |
| C6 | 知識庫管理 UI | 3 | 基礎的文檔上傳+管理頁面 |

**Phase C 交付物**: 助手記得之前的對話和任務，能查閱企業知識庫回答專業問題

---

## Part 5: Orchestrator Agent 設計規格

這是整個組裝計劃的核心，值得單獨展開。

### System Prompt (草稿)

```
你是 [企業名稱] 的 IT 運維智能助手。你的角色是一位資深的 IT 運維主管，
熟悉企業的系統架構、團隊分工、和標準操作流程。

你的職責：
1. 理解用戶的 IT 相關請求或問題
2. 評估請求的風險等級和緊急程度
3. 決定最佳的處理方式：直接回答、派任務給專業 Agent、或啟動多步驟工作流
4. 在執行過程中保持透明，讓用戶了解進度
5. 整合所有結果，給出清晰的回應和建議

你可以使用以下工具：
- route_intent: 分析用戶意圖的類別和風險
- assess_risk: 評估操作的風險等級
- search_memory: 查詢歷史記錄和過去的處理經驗
- search_knowledge: 查詢企業知識庫（SOP、Runbook、政策文檔）
- dispatch_workflow: 啟動結構化工作流（多步驟、需協調的任務）
- dispatch_worker: 派任務給專業 Agent（分析、診斷、修復等）
- dispatch_swarm: 啟動多 Agent 並行協作（大型複合任務）
- request_approval: 請求人工審批
- create_task: 建立長期任務記錄
- update_task_status: 更新任務進度

注意事項：
- 使用繁體中文回應
- 涉及生產環境的操作必須先經過風險評估
- 高風險操作必須獲得人工審批才能執行
- 記錄所有決策的理由，確保可追溯性
```

### Orchestrator Agent 的 Tools 映射到現有代碼

| Tool | 實現來源 | 需要改造 |
|------|---------|---------|
| `route_intent()` | `BusinessIntentRouter.classify()` | 包裝為 function tool |
| `assess_risk()` | `RiskAssessor.assess()` | 包裝為 function tool |
| `search_memory()` | `mem0 MemoryService.search()` | 包裝為 function tool |
| `search_knowledge()` | 新建 (RAG pipeline) | 全新 |
| `dispatch_workflow()` | `WorkflowExecutor.run()` | 包裝為 function tool |
| `dispatch_worker()` | `ClaudeCoordinator.execute()` | 包裝為 function tool |
| `dispatch_swarm()` | `SwarmTracker.create()` | 包裝 + 接通到主流程 |
| `request_approval()` | `HITLController.request_approval()` | 包裝為 function tool |
| `create_task()` | 新建 (Task Registry) | 全新 |
| `update_task_status()` | 新建 (Task Registry) | 全新 |

### 技術實現方式 (利用 MAF RC4 原生 Claude 整合)

```python
from agent_framework_claude import ClaudeAgent
from agent_framework import FileAgentSkillsProvider

# 企業知識 Skills Provider
skills_provider = FileAgentSkillsProvider(
    skill_paths=[
        "skills/itil-incident-management",
        "skills/change-management",
        "skills/enterprise-architecture",
    ]
)

# Orchestrator Agent 定義
async with ClaudeAgent(
    name="orchestrator",
    instructions=ORCHESTRATOR_SYSTEM_PROMPT,
    tools=[
        route_intent,        # function tool
        assess_risk,         # function tool
        search_memory,       # function tool
        search_knowledge,    # function tool (RAG)
        dispatch_workflow,   # function tool
        dispatch_worker,     # function tool
        dispatch_swarm,      # function tool
        request_approval,    # function tool
        create_task,         # function tool
        update_task_status,  # function tool
    ],
    context_providers=[skills_provider],  # Agent Skills 自動注入
    default_options={
        "permission_mode": "acceptEdits",
    },
) as orchestrator:
    # 處理用戶請求
    response = await orchestrator.run(
        user_input,
        thread=session_thread,  # 維持對話上下文
    )
```

---

## Part 6: 總工作量估算

| Phase | Sprints | Story Points | 交付物 |
|-------|---------|-------------|--------|
| Phase A: 基礎可跑 | 3 | ~40 SP | 端到端對話 + 意圖路由 + 審批 |
| Phase B: 任務執行 | 3 | ~40 SP | 任務分派 + MCP 工具 + Checkpoint |
| Phase C: 記憶+知識 | 2 | ~25 SP | 記憶接線 + RAG + Agent Skills |
| **合計** | **8** | **~105 SP** | **完整 Use Case 可運行** |

**注意**: 這不是在原有 2500+ SP 的基礎上再加 105 SP 的新功能。這 105 SP 的核心工作是 **接線和改造** — 把已經建好的 70 個功能組裝成一個可以真正端到端運行的系統。