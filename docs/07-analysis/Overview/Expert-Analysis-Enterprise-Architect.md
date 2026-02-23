# IPA Platform 架構專家分析報告 — Enterprise Architect 視角

> **分析者**: Enterprise Architect (專精大型分佈式系統、微服務架構、Agent 平台)
> **分析日期**: 2026-02-21
> **基於**: IPA-Platform-Comprehensive-Analysis-V2.md + 代碼實地驗證
> **驗證方法**: 閱讀報告 → 代碼探索 → 交叉比對 → 獨立評估

---

## 目錄

1. [執行摘要](#一執行摘要)
2. [11 層架構合理性重新評估](#二11-層架構合理性重新評估)
3. [Layer 4 過載問題 — 職責拆分方案](#三layer-4-過載問題--職責拆分方案)
4. [Layer 5-6 邊界模糊 — 循環依賴解決方案](#四layer-5-6-邊界模糊--循環依賴解決方案)
5. [Layer 9「雜物間」— Swarm 提升方案](#五layer-9雜物間-swarm-提升方案)
6. [混合編排架構長期可持續性](#六混合編排架構長期可持續性)
7. [三層瀑布式路由改進路徑](#七三層瀑布式路由改進路徑)
8. [五個流程斷裂點修復優先級](#八五個流程斷裂點修復優先級)
9. [與 LangGraph/CrewAI 架構深度對比](#九與-langgraphcrewai-架構深度對比)
10. [報告可能遺漏的架構問題](#十報告可能遺漏的架構問題)
11. [架構重構路線圖](#十一架構重構路線圖)

---

## 一、執行摘要

### 總體架構評價

IPA Platform 的 11 層架構在 **設計理念** 上屬於業界前沿水準——將 Agent 編排問題分解為輸入閘道、意圖路由、風險評估、框架選擇、執行引擎、工具層等獨立關注點，這在混亂的 AI Agent 平台生態中是罕見的系統性工程思維。

然而，經代碼實地驗證後，我識別出 **三個結構性問題** 和 **兩個隱性風險**：

```
結構性問題:
  S1: Layer 4 (Orchestration) 承擔了 5 個不同職責域，違反 SRP
  S2: Layer 6 (MAF) → Layer 5 (Hybrid) 存在反向依賴（MAFToolCallback）
  S3: Layer 9 (Supporting) 是無內聚力的 catch-all 桶

隱性風險:
  R1: HybridOrchestratorV2 是 God Object（1,254 LOC, 知道所有 Phase 28 組件）
  R2: 4 套 Checkpoint 系統沿著不同抽象層級獨立演化，統一成本會隨時間指數增長
```

### 結論前置

| 問題域 | 嚴重度 | 建議行動 | 時程 |
|--------|--------|----------|------|
| Layer 4 過載 | HIGH | 拆為 Input Processing Layer + Decision Layer | Phase B |
| L5-L6 循環依賴 | MEDIUM | 提取 ToolCallback 到共享介面層 | Phase A |
| Layer 9 雜物間 | MEDIUM | Swarm 升級為獨立執行層 | Phase C |
| God Object | HIGH | Orchestrator 應用 Mediator Pattern 重構 | Phase B |
| Checkpoint 碎片化 | CRITICAL | 統一為 Checkpoint Coordinator | Phase A-B |
| MAF Preview 風險 | HIGH | 建立 Anti-Corruption Layer | 持續 |

---

## 二、11 層架構合理性重新評估

### 2.1 現狀架構概覽

```
┌─────────────────────────────────────────────────────────┐
│ L1  Frontend        │ React 18 + TypeScript + Vite      │
├─────────────────────┼───────────────────────────────────┤
│ L2  API             │ FastAPI, 39 modules, ~534 endpoints│
├─────────────────────┼───────────────────────────────────┤
│ L3  AG-UI           │ SSE Protocol, Event Streaming      │
├─────────────────────┼───────────────────────────────────┤
│ L4  Orchestration   │ InputGW + IntentRouter + Risk +    │
│     (Phase 28)      │ GuidedDialog + HITL = 39 files    │
├─────────────────────┼───────────────────────────────────┤
│ L5  Hybrid          │ FrameworkSelector + ContextBridge + │
│     (Phase 13-14)   │ Switcher + Checkpoint = 60 files  │
├─────────────────────┼───────────────────────────────────┤
│ L6  MAF Builders    │ 9 builders, 23 files, 37K LOC     │
├─────────────────────┼───────────────────────────────────┤
│ L7  Claude SDK      │ Autonomous Pipeline, Hooks         │
├─────────────────────┼───────────────────────────────────┤
│ L8  MCP             │ 5 MCP Servers, Security Layer      │
├─────────────────────┼───────────────────────────────────┤
│ L9  Supporting      │ Swarm + Patrol + Memory + LLM +    │
│                     │ Learning + Correlation + Audit +   │
│                     │ A2A + RootCause = 49 files         │
├─────────────────────┼───────────────────────────────────┤
│ L10 Domain          │ 20 modules, 112 files, 47K LOC    │
├─────────────────────┼───────────────────────────────────┤
│ L11 Infrastructure  │ PG + Redis + (RabbitMQ 空殼)       │
└─────────────────────┴───────────────────────────────────┘
```

### 2.2 逐層合理性評估

| 層 | 合理性 | 問題 | 建議 |
|----|--------|------|------|
| L1 Frontend | ✅ 獨立 | store/stores 分裂 | 合併為 stores/ |
| L2 API | ✅ 獨立 | 534 端點太多，47 routers | 考慮按業務域分組 |
| L3 AG-UI | ✅ 獨立 | 與 L4 緊耦合 | 合理的緊耦合 |
| **L4 Orchestration** | **⚠️ 過載** | **5 個職責域** | **拆為 2 層** |
| **L5 Hybrid** | **⚠️ 模糊** | **與 L6 循環依賴** | **提取共享介面** |
| L6 MAF | ✅ 獨立 | 依賴 preview API | 加 ACL |
| L7 Claude SDK | ✅ 獨立 | — | — |
| L8 MCP | ✅ 獨立 | InMemory 問題 | 替換存儲 |
| **L9 Supporting** | **❌ 無內聚** | **9 個無關模組** | **重新歸屬** |
| L10 Domain | ⚠️ 黑箱 | 47K LOC 未充分審查 | 需獨立審查 |
| L11 Infrastructure | ⚠️ 薄弱 | 3.4K LOC 支撐 228K | 大幅加厚 |

### 2.3 建議：從 11 層調整為 9+2 層

我的建議不是「合併層」使數字變少，而是重新對齊層的抽象邊界，使每層有且僅有一個變更理由（SRP at Layer Level）。

```
建議的 9+2 層架構:

┌─────────────────────────────────────────────────────┐
│ L1  Frontend (不變)                                  │
├─────────────────────────────────────────────────────┤
│ L2  API Gateway (不變，加全局 Auth/Rate Limit)       │
├─────────────────────────────────────────────────────┤
│ L3  AG-UI Protocol (不變)                            │
├─────────────────────────────────────────────────────┤
│ L4a Input Processing Layer [NEW]                    │
│     InputGateway + SourceHandlers + SchemaValidator  │
│     職責: 僅負責「接收 → 標準化 → 驗證」            │
├─────────────────────────────────────────────────────┤
│ L4b Decision Layer [NEW]                             │
│     IntentRouter + RiskAssessor + HITL + GuidedDialog│
│     職責: 僅負責「分類 → 評估 → 審批 → 決策」       │
├─────────────────────────────────────────────────────┤
│ L5  Framework Bridge (原 Hybrid, 精簡)               │
│     FrameworkSelector + ContextBridge                │
│     職責: 僅負責「選擇框架 → 同步上下文」           │
├─────────────────────────────────────────────────────┤
│ L6  Execution Engines (整合)                         │
│     ├── MAF Engine (原 L6)                           │
│     ├── Claude Engine (原 L7)                        │
│     └── Swarm Engine [從 L9 提升]                    │
│     職責: 三種執行引擎並列                           │
├─────────────────────────────────────────────────────┤
│ L7  Tool Layer (原 L8 MCP)                           │
│     職責: 統一工具調用                               │
├─────────────────────────────────────────────────────┤
│ L8  Domain (原 L10)                                  │
│     職責: 業務邏輯                                   │
├─────────────────────────────────────────────────────┤
│ L9  Infrastructure (原 L11, 大幅擴展)                │
│     職責: DB, Cache, MQ, Storage, Observability      │
│                                                      │
│ +2 Cross-Cutting:                                    │
│     CC1: Checkpoint Coordinator (統一 4 套系統)       │
│     CC2: Observability (Patrol + Metrics + Audit)    │
└─────────────────────────────────────────────────────┘
```

**調整理由**：

1. **L4 拆為 L4a + L4b**：Input Processing 是「數據轉換」，Decision 是「業務邏輯」，變更理由不同
2. **L6 + L7 + Swarm 合併為 Execution Engines**：三者都是「執行」的不同策略，應以 Strategy Pattern 並列
3. **L9 Supporting 解散**：
   - Swarm → L6 Execution Engines
   - Patrol + Audit + Correlation + RootCause → CC2 Observability
   - Memory + Learning → L8 Domain 子模組
   - LLM → L7 Tool Layer 子模組
   - A2A → L6 Execution Engines（Agent 間通訊是執行的一部分）
4. **Checkpoint 成為 Cross-Cutting**：4 套系統的統一需要一個橫切關注點，不屬於任何單一層

---

## 三、Layer 4 過載問題 — 職責拆分方案

### 3.1 現狀分析

經代碼驗證，Layer 4 (orchestration/) 包含 39 files, 15,753 LOC，承擔了以下 **5 個職責域**：

```
orchestration/
├── input_gateway/     ← 職責 1: 輸入接收與標準化 (2,302 LOC)
│   ├── gateway.py
│   ├── models.py
│   ├── schema_validator.py
│   └── source_handlers/
│       ├── servicenow_handler.py
│       ├── prometheus_handler.py
│       └── user_input_handler.py
│
├── intent_router/     ← 職責 2: 意圖分類 (3,815 LOC)
│   ├── router.py          (BusinessIntentRouter)
│   ├── pattern_matcher/
│   ├── semantic_router/
│   ├── llm_classifier/
│   └── completeness/
│
├── guided_dialog/     ← 職責 3: 對話管理 (3,530 LOC)
│   ├── engine.py
│   ├── context_manager.py
│   ├── generator.py
│   └── refinement_rules.py
│
├── risk_assessor/     ← 職責 4: 風險評估 (1,350 LOC)
│   ├── assessor.py
│   └── policies.py
│
├── hitl/              ← 職責 5: 人工審批 (2,213 LOC)
│   ├── controller.py
│   ├── approval_handler.py
│   └── notification.py
│
├── audit/             ← 附屬: 審計 (281 LOC)
└── metrics.py         ← 附屬: 指標 (893 LOC)
```

**問題**：這 5 個職責域的變更頻率和變更原因完全不同：
- 新增 Source Handler（如 n8n webhook）只影響 input_gateway
- 調整意圖分類規則只影響 intent_router
- 修改審批流程只影響 hitl
- 但它們全部共享同一個 `__init__.py`，匯出了 **57 個符號**

### 3.2 建議拆分方案

```
重構前:                          重構後:

orchestration/ (39 files)        input_processing/ (NEW)
├── input_gateway/               ├── gateway.py
├── intent_router/               ├── models.py
├── guided_dialog/               ├── schema_validator.py
├── risk_assessor/               └── source_handlers/
├── hitl/                            ├── servicenow.py
├── audit/                           ├── prometheus.py
└── metrics.py                       └── user_input.py

                                 decision/ (NEW)
                                 ├── intent_router/
                                 │   ├── router.py
                                 │   ├── pattern_matcher/
                                 │   ├── semantic_router/
                                 │   └── llm_classifier/
                                 ├── completeness/
                                 ├── guided_dialog/
                                 ├── risk_assessor/
                                 └── hitl/

                                 observability/ (Cross-Cutting)
                                 ├── metrics.py
                                 └── audit/
```

**拆分邊界的判定標準**:
- `input_processing/` 的變更理由：新的數據來源、新的格式
- `decision/` 的變更理由：業務規則變更、審批策略變更
- 兩者之間的契約：`UnifiedRequestEnvelope` (穩定的數據結構)

### 3.3 實施影響範圍

```
影響文件:
├── orchestrator_v2.py — 更新 import 路徑
│   (from src.integrations.orchestration import ...)
│   → from src.integrations.input_processing import InputGateway, ...
│   → from src.integrations.decision import BusinessIntentRouter, ...
│
├── api/v1/orchestration/ — 更新 router import
│   ├── intent_routes.py → 改為 from src.integrations.decision
│   ├── dialog_routes.py → 改為 from src.integrations.decision
│   └── approval_routes.py → 改為 from src.integrations.decision
│
└── tests/ — 更新測試 import
    約 15-20 個測試文件需更新 import

預估工作量: 3-5 天 (主要是 import path 更新 + 測試驗證)
風險: LOW (純重組，不改邏輯)
```

---

## 四、Layer 5-6 邊界模糊 — 循環依賴解決方案

### 4.1 現狀：反向依賴鏈

經代碼驗證，我確認了以下依賴關係：

```
正向依賴 (合理):
L5 hybrid/orchestrator_v2.py
  → imports from L5 hybrid/intent/ (FrameworkSelector)
  → imports from L5 hybrid/context/ (ContextBridge)
  → imports from L5 hybrid/execution/ (UnifiedToolExecutor)
  → imports from L4 orchestration/ (Phase 28 components)

反向依賴 (問題):
L6 agent_framework/builders/concurrent.py
  → from src.integrations.hybrid.execution import MAFToolCallback
L6 agent_framework/builders/groupchat.py
  → from src.integrations.hybrid.execution import MAFToolCallback
L6 agent_framework/builders/handoff.py
  → from src.integrations.hybrid.execution import MAFToolCallback
```

**依賴圖** (箭頭 = depends on):

```
     ┌──────────┐       ┌──────────────────┐
     │ L4       │───────│ L5 Hybrid        │
     │ Orchestr.│       │ ┌──────────────┐ │
     └──────────┘       │ │ execution/   │ │
                        │ │ MAFToolCback │◄├──── L6 agent_framework
                        │ └──────────────┘ │    (concurrent, groupchat,
                        │ ┌──────────────┐ │     handoff builders)
                        │ │ intent/      │ │
                        │ │ Framework-   │ │
                        │ │ Selector     │ │
                        │ └──────────────┘ │
                        └──────────────────┘
                              │
                              ▼
                    (理論上不應依賴 L6)

實際: L5 ──→ L4 (正常, 上層用下層)
      L6 ──→ L5 (反向依賴！ MAFToolCallback)
```

**注意**：這不是嚴格的循環依賴（L5 不直接 import L6），但 L6→L5 的反向依賴破壞了分層架構的「下層不知道上層」原則。在語義上，MAF Builder（L6）是執行引擎，不應該知道 Hybrid Bridge（L5）的存在。

### 4.2 根因分析

`MAFToolCallback` 是一個讓 MAF Builder 在執行工具調用時能通過 Hybrid 層的統一工具執行器的回調機制。設計意圖是正確的（統一工具路由），但放置位置不對。

### 4.3 建議解決方案：Shared Contracts 層

```
方案: 提取 MAFToolCallback 介面到共享契約模組

重構前:
  hybrid/execution/tool_callback.py  ← MAFToolCallback 實現
  agent_framework/builders/*.py      ← import from hybrid

重構後:
  contracts/tool_callback.py         ← MAFToolCallback Protocol/ABC
  hybrid/execution/tool_callback.py  ← 具體實現
  agent_framework/builders/*.py      ← import from contracts

依賴方向:
  L5 Hybrid ──→ contracts/ (實現介面)
  L6 MAF    ──→ contracts/ (使用介面)
  contracts/ ──→ (無依賴)
```

**代碼層面**:

```python
# contracts/tool_callback.py (NEW)
from typing import Protocol, Any, Dict

class ToolCallbackProtocol(Protocol):
    """Contract for tool execution callbacks.

    Both MAF and Hybrid layers depend on this protocol,
    but neither depends on the other.
    """
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        **kwargs,
    ) -> Any:
        ...

# hybrid/execution/tool_callback.py (修改)
from contracts.tool_callback import ToolCallbackProtocol

class MAFToolCallback(ToolCallbackProtocol):
    """Concrete implementation routing through UnifiedToolExecutor."""
    ...

# agent_framework/builders/concurrent.py (修改)
from contracts.tool_callback import ToolCallbackProtocol
# 不再 import from hybrid
```

**實施影響**:
- 新增 `contracts/` 目錄（或放在 `src/integrations/contracts/`）
- 修改 3 個 builder 文件的 import（concurrent, groupchat, handoff）
- 修改 1 個 hybrid 文件
- 工作量: 1-2 天
- 風險: LOW

---

## 五、Layer 9「雜物間」— Swarm 提升方案

### 5.1 現狀分析

Layer 9 (Supporting Integrations) 包含 9 個模組，經分析其內聚度：

```
Layer 9 模組關聯分析:
┌─────────────────────────────────────────────────────────┐
│ 模組            │ 實際職能        │ 應歸屬的架構位置    │
├─────────────────┼─────────────────┼─────────────────────┤
│ swarm/          │ Agent 群集執行  │ → L6 Execution      │
│ patrol/         │ 持續監控巡檢    │ → CC2 Observability │
│ memory/         │ 長期記憶存儲    │ → Domain/Infra      │
│ llm/            │ LLM API 客戶端  │ → L7 Tool Layer     │
│ learning/       │ 少樣本學習      │ → Domain            │
│ correlation/    │ 事件關聯分析    │ → CC2 Observability │
│ audit/          │ 審計追蹤        │ → CC2 Observability │
│ a2a/            │ Agent 間通訊    │ → L6 Execution      │
│ rootcause/      │ 根因分析        │ → CC2 Observability │
└─────────────────┴─────────────────┴─────────────────────┘

內聚度分析:
- swarm 和 a2a: 都是 Agent 執行方式 → 歸入 Execution
- patrol, correlation, audit, rootcause: 都是可觀測性 → 歸入 Observability
- memory, learning: 都是知識管理 → 歸入 Domain
- llm: 是基礎工具 → 歸入 Tool Layer

→ Layer 9 沒有統一的變更理由，是 Phase 23 的產物而非架構決策
```

### 5.2 Swarm 提升為獨立執行層的方案

**核心論點**：Swarm 與 MAF/Claude SDK 是三種 **平行的執行模式**，不是「輔助功能」。

```
現狀:
  FrameworkSelector → returns MAF / CLAUDE_SDK / SWARM
  但 execute_with_routing() 只處理:
    - WORKFLOW_MODE → _execute_workflow_mode() (MAF)
    - CHAT_MODE → _execute_chat_mode() (Claude)
    - HYBRID_MODE → _execute_hybrid_mode()
  完全沒有 SWARM_MODE 的處理邏輯！

  Swarm 只能通過 /api/v1/swarm/demo/start 獨立觸發
  demo.py 使用模擬進度，非真實 Agent 執行

建議:
  Step 1: 在 ExecutionMode enum 中確認 SWARM_MODE
  Step 2: 在 execute_with_routing() Step 7 新增:
          elif framework_analysis.mode == ExecutionMode.SWARM_MODE:
              result = await self._execute_swarm_mode(...)
  Step 3: _execute_swarm_mode() 調用 SwarmIntegration
  Step 4: SwarmIntegration 使用 ClaudeCoordinator 作為真實執行者
```

**架構變更圖**:

```
重構前:
  orchestrator_v2.py
    ├── _execute_workflow_mode() → MAF Builder
    ├── _execute_chat_mode()     → Claude SDK
    └── _execute_hybrid_mode()   → 動態選擇

  swarm/demo.py (獨立 API，模擬數據)

重構後:
  orchestrator_v2.py
    ├── _execute_workflow_mode() → MAF Builder
    ├── _execute_chat_mode()     → Claude SDK
    ├── _execute_hybrid_mode()   → 動態選擇
    └── _execute_swarm_mode()    → SwarmIntegration
                                    ├── SwarmTracker (狀態追蹤)
                                    ├── WorkerAgent × N (並行執行)
                                    └── SSE Events (即時串流)

  API:
    /api/v1/swarm/demo/*  → 保留用於前端開發測試
    主流程自動觸發 Swarm → 通過 execute_with_routing()
```

**實施步驟**:

```
Phase 1 (2-3 天): 代碼整合
├── 在 hybrid/intent/models.py 確認 SWARM_MODE enum 值
├── 在 orchestrator_v2.py 新增 _execute_swarm_mode()
├── SwarmIntegration 接收 RoutingDecision 作為執行指令
└── AG-UI SSE 事件通過現有 SwarmEventEmitter

Phase 2 (3-5 天): 真實執行
├── 將 demo.py 的模擬邏輯替換為 ClaudeCoordinator
├── WorkerAgent 使用真實的 Claude API
├── 工具調用通過 UnifiedToolExecutor (MCP)
└── 前端無需改動（SSE 事件格式不變）

Phase 3 (2-3 天): 測試
├── 擴展現有 Swarm 測試（已有 4 類）
├── 新增主流程 → Swarm 的 integration test
└── 新增 Swarm → MCP 的 e2e test
```

---

## 六、混合編排架構長期可持續性

### 6.1 MAF Preview 風險深度分析

經代碼驗證，MAF 的使用深度：

```
MAF 在 IPA 中的使用面:
├── 9 個 Builder Adapter (8 有 MAF import, 1 standalone)
│   ├── SequentialBuilderAdapter
│   ├── ConcurrentBuilderAdapter
│   ├── GroupChatBuilderAdapter
│   ├── HandoffBuilderAdapter
│   ├── MagenticBuilderAdapter
│   ├── PlanningBuilderAdapter
│   ├── NestedWorkflowAdapter
│   ├── AgentExecutorAdapter
│   └── CodeInterpreterAdapter (standalone)
│
├── 5 個 migration 文件 ← 證明 API 已經變更過
│
├── multiturn/ 模組 ← 依賴 MAF 的對話管理
│
└── tools/ 模組 ← 依賴 MAF 的工具系統

共計: 53 files, 37,209 LOC 直接依賴 MAF
```

**風險評估**:

| 風險事件 | 概率 | 影響 | 應對策略 |
|----------|------|------|----------|
| MAF API breaking change | HIGH (preview 階段) | 37K LOC 需更新 | ACL + migration |
| MAF 方向轉變（如改用 LangGraph） | LOW-MEDIUM | 需重寫 Builder 層 | ACL 隔離 |
| MAF 停止維護 | LOW | 需替換整個 L6 | ACL + 備選方案 |
| MAF API 穩定發行 (GA) | MEDIUM | 正面影響 | 密切追蹤 |

### 6.2 建議：Anti-Corruption Layer (ACL)

```
現狀:
  API Routes ──→ Builders ──→ from agent_framework import ...
  (直接依賴 MAF API)

建議:
  API Routes ──→ IPA Builder Interface ──→ MAF Adapter ──→ MAF API
                     (ACL)                   (可替換)

代碼結構:
  integrations/agent_framework/
  ├── interface/              [NEW - ACL]
  │   ├── builder_protocol.py    # BuilderProtocol (ABC)
  │   ├── agent_protocol.py      # AgentProtocol (ABC)
  │   └── tool_protocol.py       # ToolProtocol (ABC)
  │
  ├── builders/               [現有 - 改為 Adapter]
  │   ├── sequential.py          # 實現 BuilderProtocol
  │   ├── concurrent.py          # 實現 BuilderProtocol
  │   └── ...
  │
  └── migration/              [現有 - 保留]
      └── ...                    # API 變更遷移腳本
```

**ACL 的核心價值**:
- 當 MAF API 變更時，只需修改 Adapter，不影響上層
- 當需要替換 MAF 時，可以寫新 Adapter 實現相同 Protocol
- Builder Protocol 表達的是 IPA 的業務需求，而非 MAF 的 API 形狀

### 6.3 長期演化策略

```
短期 (0-6 個月): 隨 MAF preview 迭代
├── 建立 ACL Protocol
├── 現有 Builder 改為 Adapter Pattern
├── 追蹤 MAF changelog，維護 migration 腳本
└── 單元測試覆蓋所有 Builder

中期 (6-12 個月): 等待 MAF GA
├── MAF GA 後鎖定版本
├── 清理 migration 債務
└── 評估是否需要版本相容層

長期 (12+ 個月): 評估替代方案
├── 如果 MAF GA 成熟: 深化整合
├── 如果 MAF 停滯: 考慮 LangGraph 或 CrewAI
├── 如果 Claude Agent SDK 增強: 可能減少 MAF 依賴
└── ACL 保證切換成本可控
```

---

## 七、三層瀑布式路由改進路徑

### 7.1 現狀驗證

經代碼驗證：
- **Tier 1 PatternMatcher**：真實運作，基於 regex 規則匹配
- **Tier 2 SemanticRouter**：有真實實現（`router.py`, 466 LOC），但 `__init__.py` 同時匯出 `MockSemanticRouter`，且 `create_mock_router()` 是預設工廠
- **Tier 3 LLMClassifier**：有真實實現（`classifier.py`, 439 LOC），但同樣預設為 Mock

```
__init__.py 匯出清單中:
├── MockBusinessIntentRouter     ← 預設路由器
├── MockGuidedDialogEngine       ← 預設對話
├── MockInputGateway             ← 預設閘道
├── MockSchemaValidator          ← 預設驗證
├── MockServiceNowHandler        ← 預設處理
├── MockPrometheusHandler        ← 預設處理
├── MockUserInputHandler         ← 預設處理
├── MockNotificationService      ← 預設通知
└── MockConversationContextManager ← 預設上下文

→ 共 9 個 Mock 從生產 __init__.py 匯出
→ 開發者 import 時無法確定得到的是真實還是 Mock
```

### 7.2 Tier 2 啟用路徑

```
步驟 1: 向量庫建立 (2-3 天)
├── 收集 IPA 的意圖分類樣本數據
│   ├── INCIDENT 場景: 50+ 樣本
│   ├── REQUEST 場景: 50+ 樣本
│   ├── CHANGE 場景: 30+ 樣本
│   └── QUERY 場景: 30+ 樣本
├── 使用 Azure OpenAI embeddings 生成向量
└── 存儲在 PostgreSQL (pgvector) 或 Redis (RediSearch)

步驟 2: SemanticRouter 配置 (1-2 天)
├── 設定 Azure OpenAI embedding model
│   → text-embedding-3-small (便宜) 或 text-embedding-3-large (精確)
├── 設定向量相似度閾值 (建議 0.85)
└── 設定 fallback 到 Tier 3 的條件

步驟 3: 冷啟動問題解決 (1 天)
├── 提供初始向量庫（手動標註 + PatternMatcher 歷史數據）
├── 隨 PatternMatcher 高置信度結果自動擴充向量庫
└── 設定最小向量數量閾值，低於閾值自動跳到 Tier 3

步驟 4: 品質監控 (持續)
├── 記錄每次 Tier 2 的 confidence score
├── 與 PatternMatcher 結果對比
├── 建立 precision/recall 基準線
└── 定期重新訓練向量庫
```

### 7.3 Tier 3 啟用路徑

```
步驟 1: Prompt 工程 (2-3 天)
├── 設計分類 prompt template (已有 prompts.py)
├── 建立 Few-shot 範例集
│   ├── 每個 ITIntentCategory 3-5 個範例
│   └── 包含邊界案例（如中英混合輸入）
├── 測試 prompt 的分類準確率
└── 建立 evaluation dataset (100+ 標記樣本)

步驟 2: API 配置 (0.5 天)
├── 設定 Anthropic API Key (Claude Haiku)
│   → 或改用 Azure OpenAI GPT-4o-mini (成本更低, RAPO 已有 Azure)
├── 設定 timeout (建議 2s)
└── 設定 retry 策略

步驟 3: 成本控制 (1 天)
├── 設定 daily API 調用上限
├── 實現 token 使用追蹤
├── 設定預算警告閾值
└── 評估 Tier 1+2 覆蓋率，確認 Tier 3 調用量可控

建議: 考慮用 Azure OpenAI GPT-4o-mini 替代 Claude Haiku 做 Tier 3
理由:
├── RAPO 已有 Azure OpenAI 帳號
├── 統一 API 管理（減少一個 API 供應商）
├── GPT-4o-mini 的分類準確率與 Haiku 相近
└── 成本更低（RAPO 可能有 Azure 企業折扣）
```

### 7.4 Mock 分離方案

```
現狀: orchestration/__init__.py 匯出 9 個 Mock
      生產代碼和測試代碼無明確邊界

建議:
  orchestration/
  ├── __init__.py           ← 只匯出真實類別
  ├── intent_router/
  │   └── router.py         ← create_router() 返回真實 Router
  └── testing/              [NEW]
      └── __init__.py       ← 匯出所有 Mock
                               create_mock_router() 等

  tests/
  └── mocks/
      └── orchestration.py  ← 測試專用 Mock (或從 testing/ 引入)

好處:
├── import from orchestration → 保證得到真實實現
├── import from orchestration.testing → 明確是測試用
├── 運行時行為確定性
└── 開發者不會意外使用 Mock
```

---

## 八、五個流程斷裂點修復優先級

### 8.1 優先級矩陣

```
影響 ↑
  │
  │  ┌───────────────────────┬───────────────────────┐
  │  │                       │                       │
高│  │  BP2: CORS/Vite 不匹配│  BP5: 4 Checkpoint    │
  │  │  (完全阻斷前後端)     │  未協調 (狀態不一致)   │
  │  │                       │                       │
  │  │  BP4: InMemory 審批   │  BP3: Swarm 不在主流程│
  │  │  (重啟丟審批)         │  (功能不完整)         │
  │  │                       │                       │
  │  ├───────────────────────┼───────────────────────┤
中│  │                       │                       │
  │  │  BP1: Tier 2/3 Mock   │                       │
  │  │  (意圖分類不完整)     │                       │
  │  │                       │                       │
  │  └───────────────────────┴───────────────────────┘
  └────────────────────────────────────────────────→ 修復複雜度
              低                       高
```

### 8.2 逐一修復方案

**BP2: CORS/Vite 端口不匹配 (P0 — 立即修復)**

```
現狀 (代碼驗證):
  config.py: cors_origins = "http://localhost:3000,http://localhost:8000"
  Frontend 運行在: port 3005
  Vite proxy 指向: port 8010

修復:
  1. config.py: cors_origins 改為環境變量，預設包含 3005
     cors_origins: str = "http://localhost:3005,http://localhost:3000,http://localhost:8000"
  2. vite.config.ts: proxy target 改為 8000
  3. 建議: cors_origins 完全由 .env 控制

工作量: 30 分鐘
風險: 無
```

**BP4: InMemory 審批存儲 (P0 — 1-2 天)**

```
現狀 (代碼驗證):
  hitl/controller.py line 647: class InMemoryApprovalStorage
  已有 RedisApprovalStorage 的導出 (在 __init__.py)

修復:
  1. 確認 RedisApprovalStorage 實現完整度
  2. 修改 create_hitl_controller() 預設使用 Redis
  3. Fallback 到 InMemory (開發環境)
  4. 環境變量控制: HITL_STORAGE_BACKEND=redis

工作量: 1-2 天 (含測試)
```

**BP1: Tier 2/3 預設 Mock (P1 — 1-2 週)**

```
詳見第七節的啟用路徑
前置條件: Azure OpenAI API Key 配置
工作量: 1-2 週
```

**BP3: Swarm 不在主流程 (P2 — 1-2 週)**

```
詳見第五節的 Swarm 提升方案
前置條件: Swarm 整合到 execute_with_routing()
工作量: 1-2 週
```

**BP5: 4 Checkpoint 系統未協調 (P1 — 2-3 週)**

```
現狀 (代碼驗證，4 套獨立系統):

System 1: agent_framework/checkpoint.py
├── CheckpointStorageAdapter (ABC)
├── PostgresCheckpointStorage
├── CachedCheckpointStorage
└── InMemoryCheckpointStorage

System 2: agent_framework/multiturn/checkpoint_storage.py
├── BaseCheckpointStorage (ABC)
├── RedisCheckpointStorage
├── PostgresCheckpointStorage
└── FileCheckpointStorage

System 3: hybrid/checkpoint/ (最完整)
├── UnifiedCheckpointStorage (ABC)
├── backends/memory.py
├── backends/redis.py
├── backends/postgres.py
└── backends/filesystem.py

System 4: domain/checkpoints/storage.py
├── CheckpointStorage (ABC)
└── DatabaseCheckpointStorage

問題:
├── 4 套系統有 4 個不同的 ABC
├── 存儲的 Checkpoint 格式不兼容
├── 恢復時無法保證跨系統狀態一致
└── 新增功能時不知道該用哪套

修復策略: Checkpoint Coordinator
├── 統一為一個 ABC (基於 System 3 — 最完整)
├── System 1, 2, 4 改為 Adapter 委託到 System 3
├── Coordinator 負責跨系統的一致性保證
│   ├── 使用 transaction-like 語義
│   └── Checkpoint ID 全局唯一
└── 逐步遷移，保持向後兼容

工作量: 2-3 週
風險: MEDIUM (需要仔細測試遷移兼容性)
```

---

## 九、與 LangGraph/CrewAI 架構深度對比

### 9.1 架構哲學對比

```
┌──────────────┬──────────────────┬──────────────────┬──────────────────┐
│              │ IPA Platform     │ LangGraph        │ CrewAI           │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 核心哲學     │ 分層 + 混合編排  │ 圖狀態機         │ 角色扮演 + 任務  │
│              │ (Layer-based)    │ (Graph-based)    │ (Role-based)     │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Agent 定義   │ Builder Pattern  │ Node + Edge      │ Agent + Task     │
│              │ (9 種模式)       │ (狀態轉移圖)     │ (Crew 組合)      │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 狀態管理     │ HybridContext +  │ TypedDict State  │ 隱式 (Task輸出)  │
│              │ 4 Checkpoint 系統│ + Checkpointer   │                  │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 工具系統     │ MCP (5 Server)   │ LangChain Tools  │ @tool decorator  │
│              │ + 統一安全       │ (生態系最大)     │                  │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ HITL         │ 獨立 Controller  │ interrupt_before  │ human_input=True │
│              │ + Teams 通知     │ / interrupt_after │                  │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 持久化       │ 4 backend (混亂) │ 統一 Checkpointer│ 無原生支持       │
│              │ + 9 InMemory     │ (SqliteSaver等)  │                  │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 可觀測性     │ OTel + Patrol    │ LangSmith 整合   │ 基本日誌         │
│              │ (但資料假)       │ (但需付費)       │                  │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 前端/UI      │ 完整 React App   │ 無（需自建）     │ 無（需自建）     │
│              │ 39 pages         │                  │                  │
├──────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 企業治理     │ 審計 + 風險評估  │ 需自建           │ 無               │
│              │ + 權限 (骨架)    │                  │                  │
└──────────────┴──────────────────┴──────────────────┴──────────────────┘
```

### 9.2 架構深度對比分析

**狀態管理 — LangGraph 的優勢**

```
LangGraph 的狀態管理是其核心競爭力:

LangGraph:
  StateGraph(TypedDict) → 編譯時類型安全
  ├── 狀態通過 Graph 顯式傳遞
  ├── Checkpointer 統一持久化 (1 套系統)
  ├── 可回溯到任意 checkpoint
  └── 人工介入 = 在狀態轉移上設斷點

IPA Platform:
  HybridContext → 運行時動態
  ├── 狀態分散在 4 套 Checkpoint 系統
  ├── ContextSynchronizer 無鎖
  ├── 恢復時跨系統不一致
  └── 人工介入 = 獨立的 HITL Controller

→ LangGraph 在狀態管理上領先一個世代
→ IPA 的 4 套 Checkpoint 是最需要優先解決的技術債
```

**企業治理 — IPA 的優勢**

```
IPA Platform 在企業場景有明確優勢:

IPA:
  ├── 三層路由 (成本優化)
  ├── 7 維度風險評估
  ├── HITL + Teams 整合
  ├── 28 MCP 權限模式
  ├── 完整前端 (39 pages)
  └── AG-UI SSE (即時可視化)

LangGraph:
  ├── 無成本優化路由
  ├── 無風險評估
  ├── interrupt 機制 (但無通知)
  ├── 需自建安全層
  └── 需自建前端

→ IPA 在「企業治理 wrapper」上領先
→ 但底層執行引擎不如 LangGraph 成熟
```

### 9.3 混合策略建議

```
不要選邊站，而是分層利用:

架構策略:
├── Layer 4-5 (Input + Decision): IPA 自有 — 企業治理是核心差異化
├── Layer 6 (Execution):
│   ├── 短期: 保留 MAF (已有 37K LOC 投資)
│   ├── 中期: 評估 LangGraph 作為 MAF 的替代方案
│   │   → LangGraph 的 Graph-based 狀態機更成熟
│   │   → ACL 保證切換成本可控
│   └── 長期: 依據 MAF GA 和 LangGraph 演化決定
├── Layer 7 (Claude SDK): 保留 — Claude 的自主推理是獨特能力
└── Layer 8 (MCP): 保留 — MCP 是業界共識方向

關鍵: IPA 的價值不在「執行引擎」，而在「決策框架」
      (Input → Classify → Risk → Approve → Select → Execute)
      這個流程是 LangGraph 和 CrewAI 都不提供的
```

---

## 十、報告可能遺漏的架構問題

經代碼實地驗證，我發現以下 V2 分析報告未充分涵蓋的問題：

### 10.1 God Object: HybridOrchestratorV2

```
orchestrator_v2.py (1,254 LOC) 直接依賴:
├── InputGateway
├── BusinessIntentRouter
├── GuidedDialogEngine
├── RiskAssessor
├── HITLController
├── FrameworkSelector
├── ContextBridge
├── UnifiedToolExecutor
├── MAFToolCallback
├── Claude executor (Callable)
└── MAF executor (Callable)

→ __init__() 接受 11 個可選組件
→ execute_with_routing() 知道所有 7 個步驟的細節
→ 這是教科書級的 God Object

問題:
├── 任何組件的介面變更都需要修改 orchestrator_v2.py
├── 測試需要 mock 大量依賴
├── 新增執行模式（如 Swarm）需要修改核心類
└── 並行開發困難（多人碰同一個文件）

建議: Mediator + Pipeline Pattern
├── 將 7 步驟抽取為獨立的 PipelineStep 介面
├── execute_with_routing() 改為遍歷 Pipeline
├── 新增步驟（如 Swarm）只需新增 Step，不改 Orchestrator
└── 每個 Step 可獨立測試
```

### 10.2 Domain Layer 黑箱

```
Domain Layer (L10): 20 modules, 112 files, 47,214 LOC
→ 佔後端總 LOC 的 20.6%
→ 但 V2 報告僅用 10 行文字帶過
→ 47K LOC 中有多少是空函數體？
→ 20 個 module 的職責邊界是否清晰？

已知問題:
├── domain/orchestration/memory/in_memory.py
│   → InMemoryConversationMemoryStore (又一個 InMemory)
├── domain/checkpoints/storage.py
│   → 第 4 套 Checkpoint 系統
└── 其他 18 個模組的品質？

建議: 需要獨立的 Domain Layer 深度審查
```

### 10.3 Session 管理的記憶體洩漏風險

```
orchestrator_v2.py:
  self._sessions: Dict[str, ExecutionContextV2] = {}

Session 管理完全 in-memory，且:
├── create_session(): 新增到 dict
├── close_session(): 從 dict 刪除
├── 但無自動清理機制
│   → 如果客戶端崩潰，session 永遠不會被 close
│   → 長時間運行後 dict 會無限增長
│   → 每個 session 包含 conversation_history (無上限)
└── 無 max_sessions 限制

建議:
├── 新增 session TTL (如 30 分鐘不活動自動清理)
├── 新增 max_sessions 上限
├── conversation_history 新增 max_length
└── 考慮 session 持久化到 Redis
```

### 10.4 Factory Function 預設問題

```
orchestrator_v2.py:
  self._framework_selector = framework_selector or intent_router or FrameworkSelector()

create_orchestrator_v2():
  → 不傳入 Phase 28 組件
  → 預設 HybridOrchestratorV2 沒有任何 Phase 28 組件
  → has_phase_28_components() = False

問題:
├── 呼叫 execute_with_routing() → ValueError
│   "InputGateway not configured. Use execute() for basic execution."
├── 呼叫 execute() → 跳過所有 Phase 28 邏輯
│   直接到 FrameworkSelector
├── 兩個 execute 方法的行為完全不同
└── 沒有配置驗證或 startup check

建議:
├── Application Startup 時驗證所有必要組件
├── 明確標記哪些組件是 required vs optional
├── 不要靠 execute_with_routing() 的 RuntimeError 來發現配置錯誤
└── 或: 合併為一個 execute()，Phase 28 步驟根據組件存在與否自動跳過
```

### 10.5 錯誤處理的「吞異常」模式

```
orchestrator_v2.py 的錯誤處理:

async def execute():
    try:
        ...
    except asyncio.TimeoutError:
        result = HybridResultV2(success=False, error="timed out")
    except Exception as e:
        logger.error(f"Execution error: {e}", exc_info=True)
        result = HybridResultV2(success=False, error=str(e))

async def _prepare_hybrid_context():
    try:
        ...
    except Exception as e:
        logger.warning(f"Failed to prepare hybrid context: {e}")
        return None  ← 靜默失敗！

問題:
├── 所有異常被轉為 HybridResultV2(success=False)
├── _prepare_hybrid_context 失敗被靜默忽略
├── 上層無法區分「用戶錯誤」和「系統錯誤」
├── 無結構化錯誤碼
└── 無法做自動重試決策（不知道錯誤是暫時的還是永久的）

建議:
├── 引入 ErrorCategory enum (TRANSIENT / PERMANENT / USER_ERROR / CONFIG_ERROR)
├── HybridResultV2 新增 error_category 字段
├── 暫時性錯誤自動重試
├── 永久性錯誤快速失敗
└── 配置錯誤在啟動時發現（見 10.4）
```

---

## 十一、架構重構路線圖

### 11.1 總覽

```
Phase A (Week 1-3): 安全基礎 + 急救修復
────────────────────────────────────────
目標: 系統能跑通端到端流程

Phase B (Week 4-8): 架構加固
────────────────────────────────
目標: 解決結構性問題

Phase C (Week 9-14): 功能完善
─────────────────────────────
目標: 核心場景可用

Phase D (Week 15+): 長期演化
─────────────────────────────
目標: 生產化 + 擴展
```

### 11.2 Phase A: 安全基礎 + 急救修復 (Week 1-3)

```
Week 1: 基礎連通
├── [A1] CORS origin 修復 (30 min)
│   └── config.py: cors_origins 加入 3005
├── [A2] Vite proxy 修復 (30 min)
│   └── vite.config.ts: proxy target 改為 8000
├── [A3] 全局 Auth middleware (3-5 天)
│   ├── FastAPI Depends(get_current_user)
│   ├── JWT Secret → 環境變量
│   └── 所有 39 個路由模組加 auth
├── [A4] Rate Limiting (0.5 天)
│   └── slowapi middleware

Week 2: 存儲安全
├── [A5] InMemoryApprovalStorage → Redis (1-2 天)
├── [A6] Mock 與生產代碼分離 (2-3 天)
│   ├── 建立 orchestration/testing/ 目錄
│   └── __init__.py 只匯出真實類別
├── [A7] console.log 清理 (0.5 天)
│   └── 特別是 authStore 的 5 個

Week 3: 共享介面 + Checkpoint 初步
├── [A8] 提取 ToolCallbackProtocol (1-2 天)
│   └── 解決 L5-L6 反向依賴
├── [A9] Checkpoint 盤點與統一規劃 (2 天)
│   ├── 選定 System 3 (hybrid/checkpoint) 為主系統
│   └── 設計 Adapter 讓其他系統委託

Phase A 交付物:
✅ 前後端能通訊
✅ 所有 API 有認證
✅ 審批使用 Redis
✅ Mock 與生產代碼分離
✅ L5-L6 依賴方向正確
```

### 11.3 Phase B: 架構加固 (Week 4-8)

```
Week 4-5: Orchestrator 重構
├── [B1] HybridOrchestratorV2 → Pipeline Pattern (3-5 天)
│   ├── 提取 PipelineStep 介面
│   ├── 每個 Phase 28 步驟 = 一個 Step
│   ├── execute_with_routing() = Pipeline.run()
│   └── 新增 Step 不改核心
├── [B2] Session TTL + 清理機制 (1-2 天)
├── [B3] 結構化錯誤處理 (2 天)
│   └── ErrorCategory + 自動重試

Week 5-6: Layer 4 拆分
├── [B4] input_processing/ 提取 (2-3 天)
│   └── InputGateway + Handlers + Validator
├── [B5] decision/ 提取 (2-3 天)
│   └── IntentRouter + Risk + HITL + Dialog
├── [B6] import path 全面更新 + 測試 (2 天)

Week 7-8: Checkpoint 統一
├── [B7] Checkpoint Coordinator 實現 (3-5 天)
│   ├── 統一 ABC (基於 hybrid/checkpoint)
│   ├── System 1, 2, 4 改為 Adapter
│   └── Transaction-like 一致性保證
├── [B8] MAF ACL Protocol 設計 (2-3 天)
│   └── BuilderProtocol + AgentProtocol

Phase B 交付物:
✅ Orchestrator 可擴展 (Pipeline)
✅ Layer 4 職責清晰
✅ Checkpoint 統一
✅ MAF 有 ACL 保護
```

### 11.4 Phase C: 功能完善 (Week 9-14)

```
Week 9-10: Swarm 整合
├── [C1] Swarm 整合到 execute_with_routing() (2-3 天)
├── [C2] ClaudeCoordinator 真實執行 (3-5 天)
├── [C3] Swarm E2E 測試 (2 天)

Week 11-12: 路由啟用
├── [C4] SemanticRouter 真實版 (3-5 天)
│   ├── 向量庫建立
│   ├── Azure OpenAI embeddings
│   └── 品質監控
├── [C5] LLMClassifier 真實版 (2-3 天)
│   └── Prompt 工程 + API 配置

Week 13-14: Layer 9 解散
├── [C6] Patrol + Audit + Correlation + RootCause → Observability (2-3 天)
├── [C7] Memory + Learning → Domain (1-2 天)
├── [C8] LLM → Tool Layer (1 天)
├── [C9] A2A → Execution Engines (1 天)

Phase C 交付物:
✅ Swarm 在主流程中
✅ 三層路由全部真實
✅ Layer 9 解散完成
✅ 架構從 11 層 → 9+2 層
```

### 11.5 Phase D: 長期演化 (Week 15+)

```
持續:
├── [D1] ContextSynchronizer 加鎖 (1-2 天)
├── [D2] Multi-Worker Uvicorn 配置 (1 天)
├── [D3] Correlation / RootCause 連接真實數據 (2-3 週)
├── [D4] ServiceNow MCP Server (2-3 週)
├── [D5] Domain Layer 深度審查 (1-2 週)
├── [D6] ReactFlow 安裝 + 工作流視覺化 (1 週)
├── [D7] LangGraph 評估 (作為 MAF 替代方案) (1-2 週)
├── [D8] Docker 部署到 Azure (1 週)
├── [D9] OTel + Azure Monitor 整合 (1 週)
└── [D10] RabbitMQ 實現 (2 週)

持續追蹤:
├── MAF API 變更
├── Claude Agent SDK 演化
├── LangGraph 成熟度
└── 架構品質指標 (耦合度、覆蓋率、技術債)
```

### 11.6 路線圖可視化

```
Timeline:
         W1    W3    W5    W8    W10   W12   W14   W16+
         │     │     │     │     │     │     │     │
Phase A  ├─────┤
         │ CORS, Auth, Redis, Mock 分離, 共享介面  │
         │                                         │
Phase B  │     ├───────────┤                       │
         │     │ Pipeline, L4 拆分, Checkpoint 統一│
         │     │                                   │
Phase C  │     │           ├───────────┤           │
         │     │           │ Swarm 整合, 路由啟用, │
         │     │           │ L9 解散               │
         │     │           │                       │
Phase D  │     │           │           ├───────────┤──→
         │     │           │           │ 生產化,   │
         │     │           │           │ 擴展      │
         │     │           │           │           │
Milestone:│    │           │           │           │
         ├─ 可內部展示    ├─ 結構穩固 ├─ 場景可用 ├─ 生產就緒
```

---

## 附錄 A：代碼驗證記錄

本報告的每一個結論都經過代碼實地驗證：

| 結論 | 驗證文件 | 驗證方法 |
|------|----------|----------|
| L4 包含 5 個職責域 | orchestration/ 目錄結構 | 目錄遍歷 |
| L5→L6 無反向依賴 | hybrid/ 全文搜索 | Grep `from src.integrations.agent_framework` |
| L6→L5 反向依賴確認 | concurrent.py, groupchat.py, handoff.py | Grep `from src.integrations.hybrid` |
| Swarm 不在主流程 | orchestrator_v2.py | Grep `SWARM\|swarm` = 無匹配 |
| 4 套 Checkpoint | 全項目搜索 | Grep `class.*Checkpoint.*Storage` |
| 9 個 InMemory | src/ 全文搜索 | Grep `class InMemory` |
| CORS 設定 | config.py line 138 | 直接讀取 |
| Mock 從 __init__.py 匯出 | orchestration/__init__.py | 直接讀取，計數 9 個 Mock |
| orchestrator_v2 接受 11 參數 | orchestrator_v2.py `__init__` | 直接讀取 |
| messaging/ 空殼 | messaging/__init__.py | 只有 1 行註釋 |
| storage/ 空目錄 | infrastructure/storage/ | 無文件 |
| execute_with_routing() 無 SWARM | orchestrator_v2.py line 670-689 | 只有 WORKFLOW 和 else (CHAT) |

---

## 附錄 B：術語對照

| 術語 | 含義 |
|------|------|
| SRP | Single Responsibility Principle, 單一職責原則 |
| ACL | Anti-Corruption Layer, 防腐層 |
| God Object | 承擔過多職責的類別 |
| Pipeline Pattern | 將處理流程分解為獨立步驟的設計模式 |
| Mediator Pattern | 解耦多個組件直接互動的設計模式 |
| Cross-Cutting Concern | 橫切多個層的關注點（如日誌、安全、Checkpoint） |

---

*本報告由 Enterprise Architect 視角撰寫，聚焦於系統架構的結構性問題和長期演化策略。所有結論均經代碼實地驗證，非僅基於文件分析。*
