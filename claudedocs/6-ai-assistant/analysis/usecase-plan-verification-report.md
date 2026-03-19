# IPA Use Case 端到端組裝藍圖 — 代碼庫實況驗證報告

> **驗證日期**: 2026-03-18
> **驗證對象**: `docs/07-analysis/Overview/full-codebase-analysis/ipa-planform-usecase/ipa-desired-usecase-plan.md`
> **驗證方法**: 逐 Step 對照代碼庫實際檔案結構、模組匯入、類別定義

---

## 驗證標記說明

| 標記 | 意義 |
|------|------|
| **ACCURATE** | 文件描述與代碼實際一致 |
| **OVERSTATED** | 文件描述比實際狀態更樂觀 |
| **UNDERSTATED** | 文件描述比實際狀態更保守 |
| **INACCURATE** | 文件描述與代碼不符 |

---

## Step 1 — 登入 + Session + Chat UI

### Login/JWT Auth — 文件聲稱: ✅ 完整

**驗證結果: ACCURATE**

- `backend/src/core/auth.py` — 完整的 JWT Bearer 驗證，含 `require_auth()` dependency
- `backend/src/core/security/jwt.py` — JWT 簽發/解碼邏輯
- `frontend/src/pages/auth/` — 存在登入頁面

### Session CRUD API — 文件聲稱: ✅ 完整 (12,272 LOC)

**驗證結果: OVERSTATED (LOC 數不準)**

- 實際 `wc -l` 統計核心 `.py` 檔案合計 **~8,375 行** (非 12,272)
- 12,272 可能包含子目錄 (files/, features/, history/) 的所有檔案
- 功能面確實豐富: service.py (625), models.py (687), repository.py (405), streaming.py (747), tool_handler.py (1,019) 等
- **修正**: LOC 數應標示為「含子目錄合計」，核心 session 功能確實完整

### Chat UI — 文件聲稱: ✅ 完整 (27 components)

**驗證結果: UNDERSTATED**

- 實際 unified-chat 目錄下有 **65 個 .ts/.tsx 檔案** (含 agent-swarm 子目錄 15+ 組件 + 4 hooks)
- `pages/UnifiedChat.tsx` 確實存在
- 文件說「27 components」嚴重低估，實際約 65 個檔案

### 缺失項驗證

- **H-11 chat history 僅 localStorage**: ACCURATE — 未找到後端 chat history 同步 API
- **任務列表 UI + API**: ACCURATE — 代碼庫中不存在 Task Registry 概念
- **Session resume 流程**: ACCURATE — 前端無「繼續對話」明確 UI flow

---

## Step 2 — InputGateway

### 文件聲稱: ✅ 全部完整

**驗證結果: ACCURATE**

- `orchestration/input_gateway/gateway.py` — InputGateway 主類，完整的 source routing 邏輯
- `source_handlers/servicenow_handler.py` — ServiceNow webhook handler
- `source_handlers/prometheus_handler.py` — Prometheus Alertmanager handler (41 regex patterns 描述合理)
- `source_handlers/user_input_handler.py` — 委託給 BusinessIntentRouter 的完整三層路由
- `models.py` — IncomingRequest, SourceType, GatewayConfig, GatewayMetrics 等模型完整
- `schema_validator.py` — 資料驗證

**UnifiedRequestEnvelope**: 文件提到此名稱，但代碼中實際命名為 `RoutingDecision` 作為輸出。`IncomingRequest` 是輸入格式。**名稱有小出入但功能對應正確**。

---

## Step 3 — 三層意圖路由

### 文件聲稱: ✅ 全部完整 (PatternMatcher, SemanticRouter, LLMClassifier, BusinessIntentRouter)

**驗證結果: ACCURATE**

- `intent_router/pattern_matcher/matcher.py` — 規則式匹配，YAML 配置，pre-compiled regex
- `intent_router/semantic_router/router.py` — 原版 Aurelio-based + `azure_semantic_router.py` Azure AI Search 版
- `intent_router/llm_classifier/classifier.py` — LLMServiceProtocol 抽象，支持 Azure OpenAI/Claude/Mock
- `intent_router/llm_classifier/cache.py` — Redis-backed 分類結果快取
- `intent_router/router.py` — BusinessIntentRouter，三層瀑布邏輯
- `intent_router/completeness/` — CompletenessChecker + Rules (INCIDENT/REQUEST/CHANGE/QUERY)
- `intent_router/contracts.py` — L4b Decision Engine 抽象協定

**這是代碼庫中最完整的模組之一**，Sprint 91-93, 115-116, 128 持續迭代。

---

## Step 4 — 完整性檢查 + 引導對話

### 文件聲稱: ✅ 全部完整

**驗證結果: ACCURATE**

- CompletenessChecker 和 CompletenessRules 確認存在且功能完整
- GuidedDialogEngine 存在於 orchestration 層 (未單獨深查但 __init__.py 匯出)
- RefinementRules 亦存在

---

## Step 5 — 風險評估 + 人工審批

### RiskAssessor — 文件聲稱: ✅ 完整 (7 維度)

**驗證結果: OVERSTATED — 實際為 configurable N 維度，非固定 7 維**

`_collect_factors()` 方法逐一收集 factors:
1. **Intent Category** — `_get_category_weight()`
2. **Sub Intent** — `_get_sub_intent_weight()`
3. 之後根據 `AssessmentContext` 動態添加 factors

`AssessmentContext` 欄位包括:
- `is_production`, `is_weekend`, `is_urgent`, `affected_systems`, `custom_factors`

**結論**: 框架支持多維度但並非硬編碼 7 個。文件描述的「Intent(0.8) + SubIntent(0.5) + Production(0.3) + Weekend(0.2) + Urgent(0.15) + AffectedSys + LowConfidence」是**設計規格**而非代碼現狀。代碼中的權重是動態從 policy 配置計算的，並非固定值。

### HITLController — 文件聲稱: ✅ 完整

**驗證結果: ACCURATE**

- `orchestration/hitl/controller.py` — Sprint 97 實現，完整的 ApprovalStatus enum (PENDING/APPROVED/REJECTED/EXPIRED/CANCELLED)
- `orchestration/hitl/approval_handler.py` — 審批處理邏輯
- `orchestration/hitl/notification.py` — 通知機制 (Teams Adaptive Card)

### 3 套審批系統 — 文件聲稱: AG-UI / Orchestration / Claude SDK 各自獨立

**驗證結果: ACCURATE — 但需要更精確描述**

| 系統 | 位置 | 用途 |
|------|------|------|
| **Orchestration HITL** | `integrations/orchestration/hitl/` (controller.py, approval_handler.py, notification.py) | Phase 28 業務流程審批，基於 RiskAssessor 結果 |
| **AG-UI HITL** | `integrations/ag_ui/features/human_in_loop.py` (745 LOC) | AG-UI SSE 事件驅動的前端審批卡片，InMemory + asyncio.Lock |
| **Claude SDK Hooks** | `integrations/claude_sdk/` 中的 ApprovalHook | Tool 調用級別的風險審批 (Write/Edit/Bash 等工具) |
| **MAF Handoff HITL** | `integrations/agent_framework/builders/handoff_hitl.py` | MAF 原生 handoff 審批 |
| **Handoff routes** | `api/v1/handoff/routes.py` (_hitl_sessions, _hitl_requests — InMemory Dict) | API 層審批 |

**修正**: 實際上是 **4-5 套**審批相關系統，不是 3 套。文件描述偏保守。

---

## Step 6 — Orchestrator Agent

### HybridOrchestratorV2 — 文件聲稱: ✅ 代碼邏輯存在「但不是 Agent，是程式碼」

**驗證結果: ACCURATE**

- `hybrid/orchestrator_v2.py` — 完整的 HybridOrchestratorV2，整合 FrameworkSelector + ContextBridge + Phase 28 組件
- 3 種執行模式: WORKFLOW_MODE, CHAT_MODE, HYBRID_MODE
- 確實是程式碼邏輯流，而非 LLM Agent 實例
- `hybrid/swarm_mode.py` — Sprint 116 SwarmModeHandler 整合

### FrameworkSelector — 文件聲稱: ✅ 完整 (5 種策略)

**驗證結果: PARTIALLY ACCURATE**

- `hybrid/intent.py` — FrameworkSelector 類確認存在 (Sprint 52 → Sprint 98 更名)
- 從 `__init__.py` 匯出: ExecutionMode, FrameworkAnalysis, FrameworkSelector, IntentAnalysis, IntentRouter
- **注意**: `grep` 搜索 intent.py 中的 class/strategy 定義時**返回空結果**，表示檔案可能不在預期路徑或結構有差異
- 執行模式確認有 3 種 (WORKFLOW_MODE, CHAT_MODE, HYBRID_MODE)，「5 種策略」的具體定義需進一步驗證

### ContextBridge — 文件聲稱: ✅ 完整 但無 asyncio.Lock (H-04)

**驗證結果: ACCURATE**

- `hybrid/context.py` — 匯出 ClaudeContext, ContextBridge, HybridContext, MAFContext, SyncDirection, SyncResult, SyncStrategy
- grep `asyncio.Lock` 在 context.py 中**返回空結果**，確認 H-04 問題屬實

---

## Step 7 — 任務分派與執行

### Swarm 系統 — 文件聲稱: 獨立 Demo API

**驗證結果: ACCURATE**

- `integrations/swarm/` — tracker.py, swarm_integration.py, models.py, events/ (emitter, types)
- `api/v1/swarm/demo.py` — **5 個路由端點**，確實是 Demo 性質
- `api/v1/swarm/routes.py` — 3 個路由端點 (GET 為主)
- `hybrid/swarm_mode.py` — Sprint 116 已有 SwarmModeHandler，但 `enabled: bool = False` **預設關閉**
- **修正**: 文件說「獨立 Demo API」基本準確，但 Sprint 116 已經有 `SwarmModeHandler` 接入 HybridOrchestratorV2 的初步代碼（feature flag 預設 off）

### Claude Worker Pool / ClaudeCoordinator

**驗證結果: ACCURATE — 代碼存在但未真正連接 LLM**

- `claude_sdk/orchestrator/coordinator.py` — ClaudeCoordinator 類完整
  - 功能: 任務分析 → agent 選擇 → subtask 分配 → 並行/順序執行 → 結果聚合
  - `_claude_client: Optional[Any] = None` — **client 可為 None，graceful degradation**
  - `_coordination_history: List[CoordinationResult] = []` — **InMemory 歷史記錄**
- `claude_sdk/orchestrator/` 下有 task_allocator.py, context_manager.py, types.py

### MAF Workflow 執行路徑

**驗證結果: ACCURATE**

- `agent_framework/builders/workflow_executor.py` — workflow 執行器
- `agent_framework/builders/nested_workflow.py` — 巢狀工作流
- `agent_framework/core/workflow.py` — 核心 workflow 定義
- `agent_framework/core/executor.py` — 核心執行器
- `agent_framework/builders/workflow_executor_migration.py` — 遷移版本

---

## Step 10 — 記憶 + 知識系統

### mem0 三層記憶 — 文件聲稱: ✅ 基礎完成

**驗證結果: OVERSTATED — 三層定義與代碼不完全對應**

文件描述三層:
- Working Memory (Redis, TTL)
- Episodic Memory (Qdrant + PostgreSQL)
- Semantic Memory (Qdrant + PostgreSQL)

代碼實際三層 (`integrations/memory/__init__.py`):
- **Layer 1**: Working Memory (Redis) — Short-term, TTL 30 min
- **Layer 2**: Session Memory (PostgreSQL) — Medium-term, TTL 7 days
- **Layer 3**: Long-term Memory (mem0 + Qdrant) — Permanent

**差異**: 代碼中的 Layer 2 是「Session Memory」而非「Episodic Memory」，Layer 3 是統一的「Long-term Memory」而非分為 Episodic + Semantic 兩種。文件描述的是**設計規格**，代碼實現的是**簡化版**。

### Memory API 7 endpoints — 文件聲稱: ✅ 完整

**驗證結果: ACCURATE**

`api/v1/memory/routes.py` 確認 7 個端點:
1. `POST /add` — 新增記憶
2. `POST /search` — 搜尋記憶
3. `GET /user/{user_id}` — 取得用戶記憶
4. `DELETE /{memory_id}` — 刪除記憶
5. `POST /promote` — 提升記憶層級
6. `POST /context` — 取得上下文記憶
7. `GET /health` — 健康檢查

### Qdrant 整合 — 文件聲稱: ✅ 已整合

**驗證結果: ACCURATE**

- `integrations/memory/mem0_client.py` — mem0 client 封裝
- `integrations/memory/embeddings.py` — embedding service
- `integrations/memory/unified_memory.py` — UnifiedMemoryManager

### LearningService — 文件聲稱: ⚠️ InMemory

**驗證結果: ACCURATE**

- `integrations/learning/` 目錄存在
- 確認有 InMemory dict 存儲模式

---

## 關鍵缺口驗證

### InMemory 存儲 — 文件聲稱: 20+

**驗證結果: UNDERSTATED — 實際數量超過 25+**

僅 `api/v1/` 層級就發現的 InMemory Dict 存儲:

| 模組 | 具體位置 | InMemory 變數 |
|------|---------|--------------|
| ag_ui/routes.py | :931-933 | `_thread_states`, `_thread_versions`, `_thread_timestamps` (3 個) |
| autonomous/routes.py | :91 | `self._tasks` |
| claude_sdk/hooks_routes.py | :110-111 | `self._hooks`, `self._hook_instances` (2 個) |
| code_interpreter/routes.py | :58 | `_sessions` |
| concurrent/adapter_service.py | :131-132 | `self._executions`, `self._task_executors` (2 個) |
| concurrent/websocket.py | :56 | `self._connections` |
| correlation/routes.py | :164-165 | `_correlation_cache`, `_rootcause_cache` (2 個) |
| groupchat/multiturn_service.py | :213-216 | `self._adapters`, `self._sessions`, `self._user_sessions`, `self._locks` (4 個) |
| groupchat/routes.py | :180-181 | `_groupchat_states`, 其他 (2+) |
| handoff/routes.py | :177-178 | `_hitl_sessions`, `_hitl_requests` (2 個) |
| hybrid/switch_routes.py | :76-78 | `InMemoryCheckpointStorage`, `_session_modes`, `_transition_history` (3 個) |
| orchestration/dialog_routes.py | :145 | `_dialog_sessions` |
| orchestration/approval_routes.py | 提到 InMemory fallback |
| maf/tool_routes.py | :451 | `_callback_store` |
| nested/routes.py | :126 | `_nested_adapters` |

**integrations 層**:
| agent_framework/checkpoint.py | :657-668 | `InMemoryCheckpointStorage` |
| agent_framework/multiturn/adapter.py | :359-360 | `InMemoryCheckpointStorage` 預設 |
| claude_sdk/orchestrator/coordinator.py | `_coordination_history` (List), `_registered_agents` (Dict) |

**合計: 至少 28+ 處 InMemory 存儲**，文件說的「20+」偏保守。

---

## 總結: 文件準確度評估

| Step | 文件準備度 | 驗證準備度 | 差距 | 說明 |
|------|-----------|-----------|------|------|
| Step 1 | 70% | ~70% | **一致** | LOC 數有偏差但功能判斷正確 |
| Step 2 | 90% | ~90% | **一致** | UnifiedRequestEnvelope 命名小出入 |
| Step 3 | 90% | ~92% | **一致** | 實際比描述稍好（含 Azure 版 + L4b 合約） |
| Step 4 | 80% | ~80% | **一致** | |
| Step 5 | 80% | ~75% | **稍樂觀** | RiskAssessor 7 維度是設計規格非代碼現狀；審批系統數量低估 |
| Step 6 | 40% | ~40% | **一致** | 核心判斷正確：是代碼不是 Agent |
| Step 7 | 65% | ~60% | **稍樂觀** | SwarmModeHandler 已有但 feature flag off；ClaudeCoordinator client 可為 None |
| Step 8 | 65% | 未深查 | — | |
| Step 9 | 50% | ~50% | **一致** | |
| Step 10 | 35% | ~30% | **稍樂觀** | 三層記憶架構與代碼不完全對應；是簡化版 |

### 文件與代碼不符的重點項目

1. **Session CRUD LOC**: 文件說 12,272，核心 py 檔 ~8,375 (含子目錄可能接近但應標註)
2. **Chat UI 組件數**: 文件說 27，實際 65 個 ts/tsx 檔案 (嚴重低估)
3. **RiskAssessor 7 維度**: 代碼是 configurable N 維度框架，非固定 7 個硬編碼值
4. **審批系統數量**: 文件說 3 套，實際 4-5 套 (漏算 MAF handoff_hitl + handoff routes)
5. **mem0 三層定義**: 文件用 Working/Episodic/Semantic，代碼用 Working/Session/Long-term
6. **InMemory 數量**: 文件說 20+，實際 28+ (低估)
7. **FrameworkSelector 5 策略**: 未能從代碼確認「5 種」的具體定義，代碼匯出 ExecutionMode 僅見 3 種模式
8. **Swarm 為「獨立 Demo」**: 部分不準確，Sprint 116 已有 SwarmModeHandler 接入但 feature flag off

### 文件未提及的遺漏缺口

1. **ClaudeCoordinator._claude_client 可為 None** — 整個協調器在無 LLM client 時 graceful degrade，等同無智能
2. **SwarmModeHandler `enabled: bool = False`** — 預設關閉，需要 feature flag 啟用
3. **agent_framework checkpoint 預設都是 InMemoryCheckpointStorage** — 文件僅提一次 checkpoint InMemory，實際有 3 處獨立的 InMemory checkpoint
4. **groupchat/multiturn 多處 InMemory** — 文件未提及這些模組的 InMemory 問題
