# IPA Platform -- End-to-End Blueprint Architecture Review

> **Review Date**: 2026-03-18
> **Reviewer**: System Architect (Claude Opus 4.6)
> **Subject**: `ipa-desired-usecase-plan.md` v1.0 vs 10 項需求
> **Scope**: Concurrency, Orchestrator, Checkpoint, Data Flow, Scalability, Security

---

## Executive Summary

本文件對 `ipa-desired-usecase-plan.md` 進行六維度系統架構評估，對照用戶的 10 項預期需求。

**整體評價**: 藍圖在功能覆蓋（70%+）和組件盤點上做得紮實，但在以下三個架構維度存在結構性缺口：

1. **併行架構** -- 文件幾乎未討論，是最大盲點
2. **Orchestrator Agent 生命週期管理** -- ClaudeAgent 方案可行但缺少容錯和多實例策略
3. **安全架構** -- 完全未提及，對於擁有 64 種工具的 Orchestrator 是嚴重遺漏

---

## A. 併行架構設計 (對應需求 #2)

### 問題描述

文件對需求 #2 「多 Session 和意圖路由如何並行執行」**幾乎沒有回答**。整份文件聚焦在「單一用戶單一請求」的線性流程，未討論：

- 多個用戶同時發送請求時的處理機制
- 同一用戶多個 Session 的隔離策略
- LLM 呼叫的併發控制和排隊機制
- 長時間任務與短查詢的資源爭奪

### 影響評估: CRITICAL

企業環境下 50-200 並發用戶是基本要求。缺乏併行設計意味著：
- 單一 LLM 慢回應（L3 LLMClassifier ~2s）會阻塞其他用戶
- Orchestrator Agent 若為 Singleton 則成為全局瓶頸
- Swarm 任務佔用大量 LLM token 額度時無法為其他用戶服務

### 現有代碼的併行能力盤點

根據代碼分析，現有基礎設施提供了一定的併行能力：

| 機制 | 位置 | 能力 | 限制 |
|------|------|------|------|
| FastAPI async | 全局 | 請求級併行（IO-bound） | 不處理 CPU-bound 或 LLM 排隊 |
| `asyncio.Lock` | 30 處使用 | 細粒度鎖 | ContextBridge 缺鎖 (H-04) |
| `asyncio.Semaphore` | claude_sdk/hooks | LLM 速率限制 | 僅 Claude SDK，未覆蓋 Azure OpenAI |
| `ThreadPoolExecutor` | sandbox/worker | CPU-bound 任務 | 未用於 LLM 呼叫 |
| `ConcurrentExecutor` | workflows/executors | 多任務並行 (ALL/ANY/MAJORITY) | 僅限 workflow 內部 |
| `threading.Lock` | SwarmTracker | 執行緒安全 | Swarm 獨立，未整合主流程 |

### 具體建議

#### B-1: LLM Call Pool (P0, Phase A)

```
                    ┌─────────────────────────────┐
                    │     LLM Call Pool            │
                    │  ┌─────┐ ┌─────┐ ┌─────┐   │
                    │  │Slot1│ │Slot2│ │Slot3│... │
                    │  └──┬──┘ └──┬──┘ └──┬──┘   │
                    │     │      │      │        │
                    │  Semaphore(max_concurrent)   │
                    │  + Priority Queue            │
                    │  + Token Budget Tracker      │
                    └─────────────────────────────┘

    設計要點:
    - asyncio.Semaphore 控制同時進行的 LLM 呼叫數量
    - 優先級佇列: 直接回答 > 意圖路由 > Extended Thinking > Swarm Worker
    - 每個 LLM provider (Azure OpenAI / Anthropic) 獨立池
    - Token 預算追蹤: 防止單一 Swarm 任務耗盡所有額度
    - 退避策略: 429 Too Many Requests 時自動退避
```

#### B-2: Orchestrator 實例策略 (P0, Phase A)

```
    方案: Per-Session Orchestrator（推薦）

    用戶A ──→ OrchestratorAgent(session_A) ──→ LLM Pool
    用戶B ──→ OrchestratorAgent(session_B) ──→ LLM Pool
    用戶C ──→ OrchestratorAgent(session_C) ──→ LLM Pool

    - 每個 Session 建立獨立 ClaudeAgent 實例
    - 共享 LLM Pool 和 Tool Registry
    - Session 結束時回收 Agent 實例
    - 最大同時活躍 Session 數由 LLM Pool 容量決定

    為什麼不用 Singleton Orchestrator:
    - ClaudeAgent 維護對話 thread 狀態，Singleton 會混淆多用戶上下文
    - LLM system prompt + memory injection 是 per-user 的
    - 併發安全性需要額外的鎖機制，增加複雜度

    為什麼不用 ProcessPoolExecutor:
    - LLM 呼叫是 IO-bound，不是 CPU-bound
    - asyncio event loop 比多進程更適合此場景
    - 進程間共享狀態（Session context）成本太高
```

#### B-3: FastAPI async 是否足夠？

**結論：基礎足夠，但需要補充三層機制**

FastAPI + uvicorn 的 async 模型能處理數千並發連接，但 LLM 呼叫的特殊性需要額外機制：

| 層級 | 機制 | 用途 |
|------|------|------|
| L1: 連接層 | FastAPI async + uvicorn workers | HTTP 併發（已有） |
| L2: LLM 呼叫層 | Semaphore + Priority Queue | LLM API 速率控制（**需新建**） |
| L3: 任務排程層 | Background Task + Celery/ARQ | 長時間 Swarm/Workflow 任務（**需新建**） |

L3 層特別重要：Swarm 任務可能執行 5-30 分鐘，不應佔用 HTTP 連接。建議使用 ARQ (asyncio-compatible Redis queue) 而非 Celery，因為：
- 與 FastAPI 的 async 模型一致
- 已有 Redis 基礎設施
- 比 Celery 輕量，適合 LLM 呼叫場景

---

## B. Orchestrator Agent 架構 (對應需求 #4, #5, #8)

### 問題描述

文件提議將 Orchestrator 從「代碼邏輯」改造為 `ClaudeAgent` 實例，這是正確方向。但存在以下架構問題：

1. **ClaudeAgent 綁定 Anthropic** -- 文件使用 `agent_framework_claude.ClaudeAgent`，但現有系統主要使用 Azure OpenAI (GPT)
2. **與 OrchestratorMediator 的關係未釐清** -- Sprint 132 剛完成的 Mediator 6 Handler 架構會被完全取代嗎？
3. **Agent 實例生命週期** -- 何時建立？何時銷毀？重啟後如何恢復？
4. **Tools 的錯誤處理和超時** -- 10 個 function tools 中 `dispatch_swarm()` 可能執行數十分鐘

### 影響評估: HIGH

Orchestrator 是整個系統的中樞神經。選錯架構模式意味著大量返工。

### 具體建議

#### C-1: Hybrid Orchestrator 而非純 ClaudeAgent (P0)

```
    推薦架構: OrchestratorMediator 作為外殼 + LLM Agent 作為決策引擎

    ┌──────────────────────────────────────────────────────────┐
    │  OrchestratorMediator (保留，作為 Pipeline 控制器)         │
    │                                                          │
    │  1. ContextHandler    -- 準備上下文（保留）               │
    │  2. RoutingHandler    -- 三層意圖路由（保留）             │
    │  3. DialogHandler     -- 引導對話（保留）                 │
    │  4. ApprovalHandler   -- 風險+審批（保留）                │
    │  5. **AgentHandler**  -- 新增：LLM Agent 決策引擎        │
    │     └─ 內部持有 ClaudeAgent / AzureOpenAI Agent 實例      │
    │     └─ Agent 決定: 直接回答 / dispatch workflow / swarm   │
    │  6. ObservabilityHandler -- 觀測（保留）                  │
    │                                                          │
    └──────────────────────────────────────────────────────────┘

    為什麼這樣比純 ClaudeAgent 更好:

    1. 確定性邏輯不需要 LLM:
       - 意圖路由（PatternMatcher L1 已有 30+ regex）→ 確定性
       - 風險評估（7 維度加權計算）→ 確定性
       - 審批流程（狀態機）→ 確定性
       這些用 LLM function calling 反而更慢、更不可靠、更貴

    2. LLM 只處理需要推理的決策:
       - 資訊不足時如何追問？
       - 複雜任務如何分解？
       - 多個結果如何綜合？
       這些才是 LLM 的價值所在

    3. 保留已有投資:
       - OrchestratorMediator 6 Handler 是 Sprint 132 的成果
       - 三層意圖路由是 Phase 28 的成果
       - 完全丟棄改用 ClaudeAgent function calling 是浪費

    4. 供應商靈活性:
       - AgentHandler 內部可以是 ClaudeAgent 或 Azure OpenAI Agent
       - 切換 LLM provider 只需改 AgentHandler，不影響其他 Handler
```

#### C-2: LLM Provider 策略 (P1)

```
    現實情況:
    - 目標市場台灣/香港企業多使用 Azure（合規要求）
    - 文件直接用 agent_framework_claude 的 ClaudeAgent
    - 但現有代碼主要配置 Azure OpenAI

    建議: 抽象 Agent 介面

    class OrchestratorLLMAgent(Protocol):
        async def decide(self, context: AgentContext) -> AgentDecision: ...
        async def synthesize(self, results: List[TaskResult]) -> str: ...

    class ClaudeOrchestratorAgent(OrchestratorLLMAgent):
        """使用 ClaudeAgent 實現"""
        ...

    class AzureOrchestratorAgent(OrchestratorLLMAgent):
        """使用 Azure OpenAI Responses API 實現"""
        ...

    這樣企業客戶可以根據合規要求選擇 LLM provider。
```

#### C-3: Tools 超時和隔離 (P1)

```
    10 個 function tools 的執行時間差異極大:

    | Tool | 預期延遲 | 是否可中斷 |
    |------|---------|-----------|
    | route_intent | <2s | 否 |
    | assess_risk | <100ms | 否 |
    | search_memory | <500ms | 否 |
    | search_knowledge | <2s | 否 |
    | respond_to_user | <100ms | 否 |
    | create_task | <200ms | 否 |
    | dispatch_workflow | 10s-5min | 是 |
    | dispatch_worker | 30s-10min | 是 |
    | dispatch_swarm | 1min-30min | 是 |
    | request_approval | 1min-24hr | 是 |

    建議將 tools 分為兩類:
    - Synchronous Tools: 直接 await，<5s 超時
    - Async Dispatch Tools: 返回 task_id，後台執行，通過 AG-UI SSE 推送進度

    dispatch_swarm() 不應該是一個需要 LLM 等待結果的 function tool。
    它應該返回 { task_id: "T-001", status: "dispatched" }，
    然後 Orchestrator 告訴用戶「任務已啟動，您可以隨時查看進度」。
```

---

## C. Checkpointing + Session Resume (對應需求 #9)

### 問題描述

文件提到了 Checkpoint 和 Task Registry，但架構設計不夠完整：

1. **Checkpoint 存什麼？** -- 文件未定義 checkpoint 的內容結構
2. **恢復的粒度** -- 是恢復整個 Orchestrator Agent 狀態，還是只恢復任務列表？
3. **ClaudeAgent thread 狀態** -- ClaudeAgent 的對話歷史如何持久化和恢復？
4. **跨進程恢復** -- 伺服器重啟後如何恢復？

### 影響評估: HIGH

Session Resume 是企業用戶的核心體驗。用戶關閉瀏覽器後回來，期望看到任務進度和之前的對話。

### 現有基礎盤點

| 組件 | 狀態 | 能力 | 缺口 |
|------|------|------|------|
| HybridCheckpoint 模型 | 完整 | 支援 session_id, execution_mode, data (BYTEA) | 未定義 Orchestrator Agent 狀態結構 |
| 4 個 Storage Backend | 代碼存在 | Memory/Redis/PostgreSQL/Filesystem | 預設使用 Memory（重啟丟失） |
| Session State Machine | 完整 | CREATED->ACTIVE->SUSPENDED->ENDED | 缺少 SUSPENDED 的觸發邏輯 |
| SessionRecoveryManager | 存在 | 基於 checkpoint 恢復 | 未整合到 Orchestrator 流程 |
| MAF RC4 checkpoint | 存在 | `agent_framework` 原生 checkpoint | 與 HybridCheckpoint 未統一 (H-05) |

### 具體建議

#### D-1: 三層 Checkpoint 模型 (P0)

```
    Layer 1: Conversation State (每次訊息後自動)
    ┌────────────────────────────────────────┐
    │ session_id, messages[], current_intent, │
    │ routing_decision, risk_level,           │
    │ approval_status                         │
    └────────────────────────────────────────┘
    存儲: Redis (快速讀寫，TTL 24h)
    恢復: 用戶重新開啟對話時載入

    Layer 2: Task State (任務狀態變更時)
    ┌────────────────────────────────────────┐
    │ task_id, task_type, status, progress,   │
    │ assigned_agent, input_params,           │
    │ partial_results, checkpoint_data        │
    └────────────────────────────────────────┘
    存儲: PostgreSQL (ACID, 持久)
    恢復: 伺服器重啟後掃描 active tasks

    Layer 3: Agent Execution State (長時間任務定期)
    ┌────────────────────────────────────────┐
    │ agent_type, execution_context,          │
    │ tool_call_history, intermediate_results,│
    │ swarm_worker_states                     │
    └────────────────────────────────────────┘
    存儲: PostgreSQL (ACID, 持久)
    恢復: 重建 Agent 實例 + 注入歷史上下文
```

#### D-2: Session Resume 流程 (P1)

```
    用戶回來:
    ┌─────────────────┐
    │ 用戶開啟瀏覽器   │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ GET /sessions   │ → 返回 session 列表 + 狀態
    │ (含 SUSPENDED)  │
    └────────┬────────┘
             │ 用戶選擇繼續
    ┌────────▼────────┐
    │ POST /sessions/ │
    │ {id}/resume     │
    └────────┬────────┘
             │
    ┌────────▼─────────────────────────────┐
    │ SessionRecoveryManager               │
    │ 1. 載入 L1 Conversation Checkpoint   │
    │ 2. 載入 L2 Task States              │
    │ 3. 重建 OrchestratorAgent 實例       │
    │    - 注入歷史 messages               │
    │    - 注入 memory context             │
    │ 4. 檢查進行中任務的最新狀態           │
    │ 5. 產生 resume summary 給用戶        │
    └──────────────────────────────────────┘
             │
    ┌────────▼────────┐
    │ AG-UI SSE 回應:  │
    │ 「歡迎回來！     │
    │  任務 T-001:     │
    │  已完成，結果是...│
    │  任務 T-002:     │
    │  等待審批中...」  │
    └─────────────────┘
```

#### D-3: ClaudeAgent Thread 持久化 (P1)

```
    問題: ClaudeAgent 的 thread（對話歷史）是 in-memory 的。
    伺服器重啟後 thread 狀態丟失。

    方案 A: 利用 MAF RC4 原生 checkpoint（推薦）
    - MAF RC4 提供 checkpoint 介面
    - 但目前 IPA 使用非官方 API (H-05)
    - 需要先修復 H-05，對齊官方 checkpoint 介面

    方案 B: 重建 thread
    - 從 L1 Checkpoint 載入 messages[]
    - 建立新的 ClaudeAgent 實例
    - 將歷史 messages 注入為 thread context
    - 缺點: 可能與原始 thread 行為有微小差異

    建議: Phase A 先用方案 B（可快速實現），Phase B 遷移到方案 A
```

---

## D. 端到端數據流分析 (對應全部 10 項需求)

### 數據流追蹤

```
用戶輸入 "ETL Pipeline 掛了，請幫忙處理"
    │
    │ [1] POST /api/v1/ag-ui/chat
    │     { content, session_id, jwt_token }
    │
    ▼ ─── 斷點 #1: ag-ui chat endpoint 是否經過 InputGateway？ ───
    │     (文件 Step 2 標記為 P0 接線項，意味著目前未連通)
    │
    ▼ InputGateway.process()
    │     → UnifiedRequestEnvelope { source: "user", content, user_id, session_id }
    │
    ▼ ─── 斷點 #2: UnifiedRequestEnvelope 如何傳遞給 Mediator？ ───
    │     (InputGateway 在 orchestration/ 模組，Mediator 在 hybrid/ 模組
    │      兩者之間沒有直接的 import 或 event 連接)
    │
    ▼ OrchestratorMediator.process()
    │   │
    │   ├── ContextHandler → 準備 HybridContext
    │   │   ─── 斷點 #3: memory context 未自動注入 ───
    │   │
    │   ├── RoutingHandler → BusinessIntentRouter.classify()
    │   │   L1: PatternMatcher → "ETL.*fail" 匹配 INCIDENT
    │   │   → RoutingDecision { intent: INCIDENT, confidence: 0.95 }
    │   │
    │   ├── DialogHandler → CompletenessChecker
    │   │   → is_sufficient: false (缺少: 哪個 Pipeline？影響範圍？)
    │   │   → GuidedDialogEngine → 追問問題
    │   │   ─── 斷點 #4: 追問問題如何通過 SSE 回前端？ ───
    │   │   (AG-UI SSE bridge 在 ag_ui/ 模組，Dialog 在 orchestration/ 模組)
    │   │
    │   ├── ApprovalHandler → RiskAssessor.assess()
    │   │   → RiskLevel.MEDIUM (INCIDENT + production 但 confidence 高)
    │   │   → 自動通過，記錄 audit
    │   │
    │   ├── [AgentHandler] → LLM 決策 (目前不存在)
    │   │   → 決定: dispatch_worker(type=DIAGNOSTIC)
    │   │
    │   ├── ExecutionHandler → dispatch
    │   │   ─── 斷點 #5: ExecutionHandler 的 claude_executor 是可選的 ───
    │   │   (Optional[Callable]，如果未注入則無法執行)
    │   │
    │   └── ObservabilityHandler → 記錄 metrics
    │       ─── 斷點 #6: AuditLogger InMemory (C-01) ───
    │
    ▼ 子 Agent 執行結果
    │   ─── 斷點 #7: 結果如何回傳給 Orchestrator？ ───
    │   (文件 Step 7 標記為 P1: Worker 結果回傳格式未統一)
    │
    ▼ Orchestrator 整合回應
    │   ─── 斷點 #8: 整合邏輯目前不存在 ───
    │   (需要 LLM 推理來綜合多個結果)
    │
    ▼ AG-UI SSE → 用戶收到回應
```

### 斷點清單與優先級

| # | 斷點 | 類型 | 影響 | 建議優先級 |
|---|------|------|------|-----------|
| 1 | AG-UI chat → InputGateway 未連通 | 接線 | 整個流程無法啟動 | **P0** |
| 2 | InputGateway → Mediator 無連接 | 接線 | 跨模組邊界未定義 | **P0** |
| 3 | Memory context 未自動注入 | 新建 | 助手無記憶 | P1 |
| 4 | Dialog → AG-UI SSE 橋接 | 接線 | 追問問題無法顯示 | P1 |
| 5 | ExecutionHandler executor 未注入 | 接線 | 實際執行不會發生 | **P0** |
| 6 | AuditLogger InMemory | 改造 | 重啟丟失審計記錄 | P1 |
| 7 | Worker 結果回傳格式 | 新建 | 無法整合結果 | P1 |
| 8 | 結果整合 LLM 邏輯 | 新建 | 無法產出綜合回應 | P1 |

**關鍵發現**: 斷點 #1 和 #2 意味著整個 10 步流程的前兩步就已斷開。文件正確識別了這個問題（A2 任務），但低估了跨模組邊界的複雜性。`orchestration/` 和 `hybrid/` 是兩個獨立的整合模組，它們之間缺少明確的合約介面。

### 建議: 定義跨模組合約

```python
# 新建: src/integrations/contracts/pipeline.py

from typing import Protocol

class PipelineInput(Protocol):
    """InputGateway 到 Mediator 的合約"""
    content: str
    source: str
    user_id: str
    session_id: str
    metadata: dict

class PipelineOutput(Protocol):
    """Mediator 到 AG-UI 的合約"""
    response_text: str
    task_id: Optional[str]
    is_complete: bool
    sse_events: List[AGUIEvent]
```

---

## E. 可擴展性和故障恢復 (企業級要求)

### 問題描述

文件假設單一伺服器部署，未討論：
- 多實例部署時的狀態一致性
- LLM API 故障時的降級策略
- 長時間任務失敗後的重試機制
- 資料庫連接池和 Redis 連接管理

### 影響評估: MEDIUM (Phase A 不需要，Phase B/C 之前需要規劃)

### 具體建議

#### E-1: 水平擴展路徑

```
    Stage 1 (Phase A): 單實例
    ┌──────────────────────┐
    │ FastAPI (1 instance)  │
    │ + Redis               │
    │ + PostgreSQL          │
    └──────────────────────┘

    Stage 2 (Phase B): 多 Worker
    ┌──────────────────────┐   ┌──────────────────────┐
    │ FastAPI (N instances) │──▶│ ARQ Worker (M inst.) │
    │ (HTTP + SSE)         │   │ (Long tasks)         │
    └──────────┬───────────┘   └──────────┬───────────┘
               │                          │
    ┌──────────▼──────────────────────────▼───────────┐
    │              Redis (Session + Queue)              │
    │              PostgreSQL (Persistent State)        │
    └─────────────────────────────────────────────────┘

    Stage 3 (企業級): 完整分離
    ┌───────┐  ┌───────┐  ┌───────┐
    │API GW │  │API GW │  │API GW │  ← Load Balancer + Sticky Session (SSE)
    └───┬───┘  └───┬───┘  └───┬───┘
        └──────────┼──────────┘
                   │
    ┌──────────────▼──────────────────┐
    │  Redis Cluster (Session + PubSub)│ ← SSE 跨實例廣播
    │  PostgreSQL (Primary + Replica)  │
    │  ARQ Workers (Auto-scaling)      │
    └─────────────────────────────────┘

    關鍵: SSE 連接是有狀態的，需要 Sticky Session 或 Redis PubSub 跨實例廣播
```

#### E-2: 故障恢復策略

| 故障場景 | 影響 | 恢復策略 |
|---------|------|---------|
| LLM API 超時 | 單一請求失敗 | 重試 3 次 + 指數退避 + 降級回 L1 PatternMatcher |
| LLM API 宕機 | 所有 LLM 功能停止 | 降級模式: 僅使用 L1 PatternMatcher + 預建回應模板 |
| Redis 宕機 | Session 狀態丟失 | 從 PostgreSQL L2 Checkpoint 恢復 |
| PostgreSQL 宕機 | 持久化失敗 | 寫入本地 WAL 文件，恢復後重播 |
| 伺服器重啟 | 進行中任務中斷 | L2 Checkpoint 掃描 + 任務重啟 |
| Swarm Worker 失敗 | 部分結果丟失 | 單一 Worker 重試，不重啟整個 Swarm |

#### E-3: Circuit Breaker 模式

```
    對 LLM API 建議使用 Circuit Breaker:

    CLOSED (正常) → 連續 5 次超時 → OPEN (熔斷)
    OPEN → 30 秒後 → HALF-OPEN (試探)
    HALF-OPEN → 1 次成功 → CLOSED
    HALF-OPEN → 1 次失敗 → OPEN

    熔斷時的降級:
    - L3 LLMClassifier → 回退到 L2 SemanticRouter
    - Orchestrator LLM 決策 → 使用 rule-based 預設策略
    - Extended Thinking → 降級為普通回應
```

---

## F. 安全架構 (文件完全未提及)

### 問題描述

這是文件最大的遺漏。Orchestrator Agent 擁有 10 個 function tools，其中包括：
- `dispatch_workflow()` -- 可啟動任何工作流
- `dispatch_swarm()` -- 可啟動多 Agent 並行執行
- Shell/SSH MCP Server -- 可執行系統命令

如果 LLM 被 prompt injection 攻擊，可能導致：
- 繞過風險評估，直接執行高風險操作
- 通過 Shell MCP 執行任意命令
- 存取其他用戶的 Session 數據

### 影響評估: CRITICAL

### 現有安全機制盤點

| 機制 | 位置 | 狀態 | 覆蓋 |
|------|------|------|------|
| JWT Auth | core/auth.py | 完整 | 僅 5.5% 端點受保護 (H-01) |
| RBAC | -- | **不存在** | 破壞性操作無權限控制 |
| Shell/SSH HITL | mcp/servers | log-only (H-12) | 無實際審批攔截 |
| MCP Audit | mcp/security | 未接線 (H-06) | 8 servers 無審計 |
| API Key 暴露 | ag_ui | 部分修復 | C-08 |
| SQL Injection | postgres_store | 存在 | C-07 |

### 具體建議

#### F-1: Tool 執行安全層 (P0)

```
    所有 Orchestrator tool 呼叫必須經過安全層:

    LLM 決定呼叫 tool
        │
        ▼
    ┌──────────────────────────────┐
    │ Tool Security Gateway        │
    │                              │
    │ 1. Input Sanitization        │
    │    - 檢查參數是否包含注入語法 │
    │    - 限制字串長度            │
    │    - 禁止特殊字符           │
    │                              │
    │ 2. Permission Check          │
    │    - 用戶是否有此操作權限？   │
    │    - 操作是否在允許範圍內？   │
    │    - 是否需要額外審批？       │
    │                              │
    │ 3. Rate Limiting             │
    │    - 每用戶每分鐘 tool 呼叫上限 │
    │    - 高風險 tool 更嚴格限制   │
    │                              │
    │ 4. Audit Logging             │
    │    - 記錄每次 tool 呼叫       │
    │    - 包括：誰、什麼、何時、結果│
    └──────────────────────────────┘
        │
        ▼
    Tool 實際執行
```

#### F-2: Prompt Injection 防護 (P0)

```
    多層防護策略:

    L1: Input Filtering
    - 移除已知的 injection 模式
    - 檢測 role confusion 嘗試 ("ignore previous instructions")
    - 長度限制 (用戶輸入 < 4000 tokens)

    L2: System Prompt 隔離
    - Orchestrator system prompt 使用 <system> 標籤
    - 用戶輸入嚴格在 <user> 標籤內
    - 不允許用戶輸入包含角色標籤

    L3: Tool Call 驗證
    - LLM 輸出的 tool call 必須匹配白名單
    - 參數值必須通過 schema validation
    - 高風險 tool (shell, ssh) 永遠需要人工審批

    L4: Output Monitoring
    - 檢測回應中是否洩露系統信息
    - 監控 tool 呼叫模式是否異常
    - 記錄所有 tool 呼叫供事後審計
```

#### F-3: RBAC 強化路線圖 (P1)

```
    Phase A: 基礎 RBAC
    - 角色: Admin, Operator, Viewer
    - 範圍: 用戶只能存取自己的 Session
    - Tool 權限: 不同角色可使用的 tools 不同

    Phase B: 細粒度權限
    - 操作級別: read/write/execute/approve
    - 資源級別: 特定 workflow / agent / 系統的存取控制
    - 審批鏈: 高風險操作需要特定角色審批

    Phase C: 企業整合
    - LDAP/AD 整合 (已有 LDAP MCP Server)
    - SSO 支援
    - 審計合規報告
```

---

## 總結: 修改優先級矩陣

| 優先級 | 建議 | 對應需求 | 工作量 | Phase |
|--------|------|---------|--------|-------|
| **P0** | 定義跨模組合約 (D-1, D-2 斷點修復) | 全部 | 3 SP | A |
| **P0** | Hybrid Orchestrator (C-1) 而非純 ClaudeAgent | #4, #5, #8 | 8 SP | A |
| **P0** | LLM Call Pool (B-1) | #2 | 5 SP | A |
| **P0** | Tool Security Gateway (F-1) | 安全 | 5 SP | A |
| **P0** | Prompt Injection 防護 (F-2) | 安全 | 3 SP | A |
| **P1** | Per-Session Orchestrator (B-2) | #2 | 3 SP | A |
| **P1** | 三層 Checkpoint (D-1) | #9 | 8 SP | B |
| **P1** | Session Resume 流程 (D-2) | #9 | 5 SP | B |
| **P1** | Tools 超時隔離 (C-3) | #4, #5 | 3 SP | B |
| **P1** | LLM Provider 抽象 (C-2) | #4 | 3 SP | B |
| **P1** | RBAC 基礎 (F-3 Phase A) | 安全 | 5 SP | B |
| **P2** | ARQ 任務排程 (B-3 L3) | #2 | 8 SP | B |
| **P2** | 水平擴展準備 (E-1 Stage 2) | 擴展 | 8 SP | C |
| **P2** | Circuit Breaker (E-3) | 容錯 | 3 SP | B |

### 對文件的整體建議

1. **補充 Part 0: 非功能需求** -- 併行、安全、擴展性、容錯應在功能設計之前定義
2. **修改 Part 5: Orchestrator 設計** -- 改為 Hybrid 方案，保留 Mediator 架構
3. **新增 Part 7: 安全架構** -- Tool Security Gateway + Prompt Injection 防護 + RBAC
4. **修改 Phase A 估算** -- 加入安全和併行的 P0 項目，估計增加 ~16 SP
5. **新增 Part 8: 跨模組合約** -- 定義 orchestration/ 和 hybrid/ 之間的介面

---

**File**: `claudedocs/6-ai-assistant/analysis/IPA-E2E-Blueprint-Architecture-Review.md`
**Last Updated**: 2026-03-18
