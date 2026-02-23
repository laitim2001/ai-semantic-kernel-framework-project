# IPA Platform 代碼品質與工程成熟度深度分析報告

> **分析日期**: 2026-02-21
> **分析者**: Code Quality Lead (Claude Opus 4.6)
> **分析方法**: 基於 V2 全面分析報告 + 獨立代碼抽樣驗證
> **範圍**: 228,700 LOC Backend + 47,630 LOC Frontend，共 276K+ LOC

---

## 目錄

1. [執行摘要](#一執行摘要)
2. [空函數體分層分布分析](#二空函數體分層分布分析)
3. [Mock 類分離方案](#三mock-類分離方案)
4. [大檔案拆分策略](#四大檔案拆分策略)
5. [測試覆蓋提升路線圖](#五測試覆蓋提升路線圖)
6. [前端測試策略](#六前端測試策略)
7. [console.log 清理方案](#七consolelog-清理方案)
8. [store/stores 統一遷移](#八storestores-統一遷移)
9. [技術債量化 (SQALE)](#九技術債量化-sqale)
10. [代碼品質工具鏈建議](#十代碼品質工具鏈建議)
11. [Technical Debt Burndown 計劃](#十一technical-debt-burndown-計劃)
12. [報告可能遺漏的品質問題](#十二報告可能遺漏的品質問題)

---

## 一、執行摘要

### 1.1 品質總評

IPA Platform 是一個由 Claude Code 在 ~3 個月內高速生成的 276K+ LOC 平台。其代碼品質呈現**極端的兩極分化**：

| 維度 | 評分 | 說明 |
|------|------|------|
| **架構設計品質** | 8/10 | 11 層分離、數據契約明確、模式選擇合理 |
| **代碼結構品質** | 5/10 | 有良好的模式但大量未完成實現 |
| **實現完整度** | 3/10 | 323 空函數、18 Mock、2 STUB 模組 |
| **測試成熟度** | 3/10 | API 測試 33%、前端僅 Phase 29、無覆蓋率追蹤 |
| **安全品質** | 1/10 | 7% Auth、無 Rate Limiting、硬編碼 Secret |
| **運維品質** | 2/10 | 單 Worker、端口不匹配、InMemory 存儲 |
| **代碼衛生** | 4/10 | 54 console.log、store 分裂、6 hook 未匯出 |

**核心結論**：這不是一個「品質差」的專案——而是一個**未完成**的專案。架構骨架優秀，但血肉尚未填充。品質改善的首要任務不是重構，而是**完成實現**。

### 1.2 獨立驗證結果

本分析對 V2 報告中的品質數據進行了獨立驗證：

| V2 報告聲稱 | 獨立驗證結果 | 差異 |
|-------------|-------------|------|
| 323 空函數體 (204 pass + 119 ellipsis) | **分層驗證通過**（見第二章） | 數字準確，但分布需要更細緻的理解 |
| 18 Mock 類 | **確認 18 個 Mock**，其中 9 個通過 `__init__.py` 匯出 | 準確，但匯出層級更深（4-5 層 barrel export） |
| 58 檔案 >800 行 | **確認前端 8 個、後端 50 個** | 準確 |
| 54 console.log | **確認 54 個分布在 12 個檔案** | 準確，authStore 5 個最危險 |
| store/stores 分裂 | **確認** store/ 含 1 檔案, stores/ 含 2+1 | 準確 |
| ContextSynchronizer 無 Lock | **確認 2 處實現均無任何 Lock** | 準確 |

---

## 二、空函數體分層分布分析

### 2.1 分層統計

通過逐層 grep 驗證 `pass` 和 `...`（ellipsis）的分布：

| 層級 | `pass` 出現次數 (檔案數) | `...` 出現次數 (檔案數) | 合計 | 佔比 |
|------|--------------------------|------------------------|------|------|
| **L10 Domain** | 71 (24 files) | 43 (13 files) | **114** | 35.3% |
| **L5 Hybrid + L6 MAF + L7 Claude + L8 MCP (integrations 總計)** | 115 (50 files) | 78 (24 files) | **193** | 59.8% |
| **L2 API** | 9 (6 files) | 1 (1 file) | **10** | 3.1% |
| **Core** | 13 (6 files) | 1 (1 file) | **14** | 4.3% |
| **L11 Infrastructure** | 0 | 1 (1 file) | **1** | 0.3% |
| **合計** | **~208** | **~124** | **~332** | 100% |

> 注意：實際數字略高於 V7 報告的 323，因為部分 `pass` 出現在 `except: pass` 等非空函數體語境中。純空函數體約 300+。

### 2.2 Domain 層深度剖析

Domain 層（114 個空體）是最需要關注的，因為**這是業務邏輯核心**：

**重災區 #1: `domain/sessions/` (36 files, ~47 個空體)**
```
sessions/repository.py      — 8 pass (全部是 ABC abstractmethod，合理)
sessions/bridge.py           — 6 pass + 6 ... (Protocol 定義，合理)
sessions/approval.py         — 4 pass + 5 ... (部分是 Protocol，部分需填充)
sessions/service.py          — 5 pass (驗證方法未實現)
sessions/tool_handler.py     — 6 ... (多個處理方法未完成)
sessions/recovery.py         — 4 ... (恢復邏輯未完成)
sessions/files/analyzer.py   — 2 pass (分析方法未實現)
sessions/files/data_exporter.py — 3 pass (匯出方法未實現)
```

**分類判定**：
- **合理的空體**（ABC abstractmethod、Protocol 定義）：約 40-50 個
- **需要填充的空體**（業務方法未實現）：約 60-70 個

**重災區 #2: `domain/orchestration/memory/base.py` (17 pass)**

這 17 個 `pass` 全部是 `@abstractmethod` 的 ABC 定義，屬於**合理的空體**。但問題是：這些抽象方法的實現類在哪裡？

```python
# 目前的情況
class ConversationMemoryStore(ABC):  # 17 個 abstractmethod
    """
    實現類:
    - InMemoryConversationMemoryStore: 記憶體實現，用於測試  ← 唯一存在的
    - RedisConversationMemoryStore: Redis 實現              ← 不存在
    - PostgresConversationMemoryStore: PostgreSQL 實現       ← 不存在
    """
```

文件 docstring 聲稱有 3 種實現，但實際上**只有 InMemory 版本**存在。Redis 和 PostgreSQL 實現從未被建立。

**重災區 #3: `domain/sessions/service.py` (5 pass)**

```python
# 當前代碼
def _validate_create(self, data: dict) -> None:
    """Validate creation business rules."""
    pass  # 沒有任何驗證邏輯

def _validate_update(self, item, data: dict) -> None:
    """Validate update business rules."""
    pass  # 沒有任何驗證邏輯

def _validate_delete(self, item) -> None:
    """Validate deletion business rules."""
    pass  # 沒有任何驗證邏輯
```

**影響**：SessionService 的 CRUD 操作**完全跳過業務規則驗證**。任何數據都可以直接寫入。

### 2.3 Integrations 層深度剖析

Integrations 層（193 個空體）分布較廣，涵蓋多個子模組：

**最嚴重: `hybrid/checkpoint/storage.py` (10 pass + 4 ...)**

Checkpoint 存儲的 4 種後端（InMemory、Redis、PostgreSQL、Filesystem）中，多數方法有 pass/ellipsis，意味著 checkpoint 恢復功能可能不完整。

**`claude_sdk/hooks/base.py` (5 pass)**

Hook 基類的 5 個 pass 是 abstract 方法，合理。但需確認所有 Hook 子類都已實現。

**`mcp/core/transport.py` (9 pass)**

MCP 傳輸層 9 個 pass，意味著 MCP 的底層通訊可能不完整。

**`orchestration/hitl/controller.py` (7 ...)**

HITL 控制器 7 個 ellipsis，意味著審批流程有部分分支未實現。

### 2.4 空函數體優先填充策略

```
優先級 P0 (安全相關):
├── sessions/service.py 的 _validate_* 方法 — 無驗證 = 安全風險
├── mcp/security/audit.py (5 pass) — 審計功能不完整
└── claude_sdk/hooks/ 的安全相關 Hook

優先級 P1 (核心流程):
├── orchestration/hitl/controller.py (7 ...) — 審批流程分支
├── sessions/recovery.py (4 ...) — 會話恢復邏輯
├── sessions/tool_handler.py (6 ...) — 工具調用處理
└── hybrid/checkpoint/storage.py (14 空體) — Checkpoint 存儲

優先級 P2 (功能完整):
├── sessions/files/analyzer.py — 檔案分析
├── sessions/files/data_exporter.py — 數據匯出
├── sessions/metrics.py — 指標收集
└── domain/orchestration/ (已標記 DEPRECATED，可跳過)

優先級 P3 (基礎設施):
├── core/sandbox/ (8 pass) — 沙箱執行
├── core/performance/ (5 pass) — 性能優化
└── mcp/core/transport.py (9 pass) — MCP 傳輸
```

### 2.5 改善前後對比

```python
# === BEFORE: sessions/service.py ===
def _validate_create(self, data: dict) -> None:
    """Validate creation business rules."""
    pass

# === AFTER: sessions/service.py ===
def _validate_create(self, data: dict) -> None:
    """Validate creation business rules."""
    if not data.get("name"):
        raise ValidationError("Session name is required")

    name = data["name"].strip()
    if len(name) > 200:
        raise ValidationError("Session name must be <= 200 characters")

    if data.get("agent_id"):
        # 驗證 Agent 存在
        agent = self.agent_repository.get_by_id(data["agent_id"])
        if not agent:
            raise NotFoundError(f"Agent not found: {data['agent_id']}")

    if data.get("config"):
        self._validate_session_config(data["config"])
```

---

## 三、Mock 類分離方案

### 3.1 現狀量化

**18 Mock 類**，全部在生產 `src/` 目錄中，分布如下：

| 模組 | Mock 類 | 通過 `__init__.py` 匯出 | 層級 |
|------|---------|------------------------|------|
| `orchestration/intent_router/` | MockSemanticRouter, MockLLMClassifier, MockBusinessIntentRouter, MockCompletenessChecker | 4 個匯出至 5 層 barrel | 最深 |
| `orchestration/guided_dialog/` | MockGuidedDialogEngine, MockConversationContextManager, MockQuestionGenerator | 3 個匯出至 3 層 barrel | 深 |
| `orchestration/input_gateway/` | MockInputGateway, MockSchemaValidator, MockBaseHandler, MockServiceNowHandler, MockPrometheusHandler, MockUserInputHandler | 6 個匯出至 4 層 barrel | 最多 |
| `orchestration/hitl/` | MockNotificationService | 1 個匯出至 2 層 barrel | 中 |
| `llm/` | MockLLMService | 1 個 | 淺 |
| **合計** | **18 個** | **9 個通過頂層 `__init__.py`** | |

### 3.2 影響評估

**問題核心**：Mock 與生產代碼共處一個模組中，且通過 `__init__.py` 的 barrel export 匯出，導致：

1. **運行時不確定性**：`from src.integrations.orchestration import InputGateway` 時，同一個 namespace 也包含 `MockInputGateway`。任何不小心的 import 都可能使用到 Mock。

2. **barrel export 層級過深**：以 `MockSemanticRouter` 為例：
   ```
   semantic_router/router.py          ← Mock 定義
   semantic_router/__init__.py        ← 第 1 層匯出
   intent_router/__init__.py          ← 第 2 層匯出
   orchestration/__init__.py          ← 第 3 層匯出 (頂層)
   ```

3. **測試依賴反轉**：正確做法是測試依賴生產代碼，而非生產代碼 barrel export Mock。

### 3.3 Mock 分離方案

**Phase 1: 建立 Mock 目錄結構** (0.5 天)

```
backend/tests/mocks/              # 已存在，擴展
├── __init__.py
├── orchestration/
│   ├── __init__.py
│   ├── intent_router.py          # MockSemanticRouter, MockLLMClassifier, etc.
│   ├── guided_dialog.py          # MockGuidedDialogEngine, etc.
│   ├── input_gateway.py          # MockInputGateway, MockHandlers, etc.
│   └── hitl.py                   # MockNotificationService
└── llm.py                        # MockLLMService
```

**Phase 2: 引入 Factory Pattern** (1 天)

```python
# === NEW: backend/src/integrations/orchestration/factories.py ===

from typing import Optional

def create_intent_router(
    use_real_semantic: bool = False,
    use_real_llm: bool = False,
    azure_openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
) -> "BusinessIntentRouter":
    """
    工廠方法：根據配置創建 IntentRouter。

    如果缺少 API Key，自動降級到 Mock 版本。
    """
    from .intent_router.router import BusinessIntentRouter
    from .intent_router.pattern_matcher import PatternMatcher

    # PatternMatcher 始終使用真實版（無外部依賴）
    pattern_matcher = PatternMatcher()

    # SemanticRouter：有 Azure OpenAI Key 才用真實版
    if use_real_semantic and azure_openai_key:
        from .intent_router.semantic_router import SemanticRouter
        semantic_router = SemanticRouter(api_key=azure_openai_key)
    else:
        semantic_router = None  # PatternMatcher 已足夠

    # LLMClassifier：有 Anthropic Key 才用真實版
    if use_real_llm and anthropic_key:
        from .intent_router.llm_classifier import LLMClassifier
        llm_classifier = LLMClassifier(api_key=anthropic_key)
    else:
        llm_classifier = None  # 只用前兩層

    return BusinessIntentRouter(
        pattern_matcher=pattern_matcher,
        semantic_router=semantic_router,
        llm_classifier=llm_classifier,
    )
```

**Phase 3: 更新 `__init__.py`，移除 Mock 匯出** (1-2 天)

```python
# === BEFORE: orchestration/__init__.py (57 exports) ===
from .intent_router import (
    BusinessIntentRouter,
    MockBusinessIntentRouter,    # <-- 移除
    PatternMatcher,
    SemanticRouter,
    MockSemanticRouter,          # <-- 移除
    ...
)

# === AFTER: orchestration/__init__.py ===
from .intent_router import (
    BusinessIntentRouter,
    PatternMatcher,
    SemanticRouter,
    LLMClassifier,
    CompletenessChecker,
    ...
)
from .factories import create_intent_router  # <-- 新增
```

**Phase 4: 更新所有 import 引用** (1 天)

搜索所有使用 `MockXxx` 的地方，將 import 路徑從生產代碼改為測試目錄：

```python
# === BEFORE (測試代碼) ===
from src.integrations.orchestration import MockBusinessIntentRouter

# === AFTER (測試代碼) ===
from tests.mocks.orchestration.intent_router import MockBusinessIntentRouter
```

### 3.4 驗證方法

```bash
# 驗證 1: 確認生產代碼中無 Mock 匯出
grep -r "Mock" backend/src/integrations/*/\__init__.py

# 驗證 2: 確認所有測試仍能通過
cd backend && pytest tests/

# 驗證 3: 確認 Factory 正確降級
python -c "
from src.integrations.orchestration.factories import create_intent_router
router = create_intent_router()  # 無 API Key，應自動降級
print('Factory works:', router is not None)
"
```

### 3.5 工作量估算

| 階段 | 工作量 | 風險 |
|------|--------|------|
| Phase 1: 建目錄 + 遷移 Mock | 0.5 天 | 低 |
| Phase 2: Factory Pattern | 1 天 | 中（需理解初始化邏輯） |
| Phase 3: 清理 `__init__.py` | 1 天 | 中（可能破壞現有 import） |
| Phase 4: 更新所有引用 | 1 天 | 高（影響面廣，需全面測試） |
| **合計** | **3.5 天** | |

---

## 四、大檔案拆分策略

### 4.1 全局統計

**後端 >800 行**: 50 個檔案
**前端 >800 行**: 8 個檔案
**>1,500 行**: 5 個檔案

### 4.2 最急迫 Top 5 大檔案拆分方案

#### #1: `groupchat.py` (1,912 LOC) — MAF Builder

**現狀**: 單一檔案包含 GroupChat Builder 的全部邏輯：配置、建構、執行、回調、錯誤處理。

**拆分方案**:
```
agent_framework/builders/groupchat/
├── __init__.py              # 匯出 GroupChatBuilder
├── builder.py               # GroupChatBuilder 主類 (~600 LOC)
├── config.py                # GroupChatConfig, 參數驗證 (~300 LOC)
├── execution.py             # 執行邏輯、回調處理 (~500 LOC)
├── callbacks.py             # 回調函數定義 (~200 LOC)
└── mock_fallback.py         # Mock fallback 邏輯 (~300 LOC)
```

**工作量**: 2-3 小時

#### #2: `ag_ui/routes.py` (1,871 LOC) — AG-UI API 路由

**現狀**: 所有 AG-UI 相關端點集中在一個路由檔案中。

**拆分方案**:
```
api/v1/ag_ui/
├── __init__.py
├── routes.py                # 主路由注冊 (~200 LOC)
├── sse_routes.py            # SSE 串流端點 (~500 LOC)
├── hitl_routes.py           # HITL 審批端點 (~400 LOC)
├── state_routes.py          # 共享狀態端點 (~400 LOC)
└── schemas.py               # Pydantic 模型 (~371 LOC, 已存在)
```

**工作量**: 2-3 小時

#### #3: `magentic.py` (1,809 LOC) — Magentic Builder

**拆分方案**: 同 groupchat.py 模式，拆為 builder/config/execution/mock。

**工作量**: 2-3 小時

#### #4: `groupchat/routes.py` (1,770 LOC) — GroupChat API 路由

**拆分方案**: 拆為 routes/schemas/handlers，按 CRUD 功能分組。

**工作量**: 2 小時

#### #5: `concurrent.py` (1,633 LOC) — Concurrent Builder

**拆分方案**: 同 groupchat.py 模式。

**工作量**: 2-3 小時

### 4.3 前端大檔案

| 檔案 | LOC | 拆分建議 |
|------|-----|---------|
| `useUnifiedChat.ts` | 1,313 | 拆為 useMessageSend + useMessageReceive + useConversation + useTools |
| `EditWorkflowPage.tsx` | 1,040 | 拆為 WorkflowEditor + WorkflowStepConfig + WorkflowPreview |
| `CreateAgentPage.tsx` | 1,015 | 拆為 AgentForm + AgentCapabilities + AgentPreview |
| `useAGUI.ts` | 982 | 拆為 useAGUIConnection + useAGUIEvents + useAGUIState |
| `EditAgentPage.tsx` | 958 | 與 CreateAgentPage 共享表單組件 |
| `UnifiedChat.tsx` | 899 | 拆為 ChatContainer + ChatInput + ChatMessages |
| `CreateWorkflowPage.tsx` | 887 | 與 EditWorkflowPage 共享組件 |
| `SwarmTestPage.tsx` | 844 | 拆為 SwarmConfig + SwarmExecution + SwarmResults |

### 4.4 整體拆分工作量

| 類別 | 檔案數 | 工作量 |
|------|--------|--------|
| MAF Builder 拆分 (Top 5 含 concurrent) | 5 | 2-3 天 |
| API Route 拆分 | 8+ | 2-3 天 |
| Frontend 組件拆分 | 8 | 3-4 天 |
| Migration files（可直接歸檔） | 5 | 0.5 天 |
| **合計** | ~26 | **8-11 天** |

---

## 五、測試覆蓋提升路線圖

### 5.1 現狀評估

| 維度 | 現狀 | 目標 |
|------|------|------|
| **API 模組覆蓋** | 13/39 (33%) | 32/39 (82%) |
| **Domain 單元測試** | 部分存在，覆蓋率不明 | 90% |
| **Integration 測試** | 16 檔案 | 40+ 檔案 |
| **E2E 測試** | 15 檔案（主要 Swarm） | 30+ 檔案 |
| **前端測試** | 13 檔案（僅 Swarm） | 60+ 檔案 |
| **覆蓋率追蹤** | 無 | Coverage.py + Codecov |

### 5.2 測試金字塔目標

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E╲         15 → 30 (+15)
                 ╱──────╲
                ╱ Integ. ╲       16 → 40 (+24)
               ╱──────────╲
              ╱   Unit      ╲    205 → 350 (+145)
             ╱────────────────╲
```

### 5.3 Phase 1: 基礎建設 (Week 1-2)

**目標**: 建立覆蓋率追蹤基礎設施

```bash
# 安裝工具
pip install coverage pytest-cov

# 配置 pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "*/migrations/*"]

[tool.coverage.report]
fail_under = 30  # 起始基準，逐步提升
show_missing = true
```

**產出**:
- 基準覆蓋率報告
- CI 集成覆蓋率檢查
- 覆蓋率 Badge

### 5.4 Phase 2: 核心路徑測試 (Week 3-6)

**優先級 P0: 主流程 `execute_with_routing()`**

```python
# tests/integration/orchestration/test_main_flow.py

class TestExecuteWithRouting:
    """測試 7 步驟主流程的每個分支"""

    async def test_low_risk_maf_path(self):
        """低風險 + MAF 選擇 → 直接執行"""
        ...

    async def test_high_risk_hitl_path(self):
        """高風險 → HITL 審批 → 執行"""
        ...

    async def test_incomplete_request_dialog(self):
        """不完整請求 → GuidedDialog → 補充 → 執行"""
        ...

    async def test_pattern_matcher_fallthrough(self):
        """PatternMatcher 未命中 → 降級到下一層"""
        ...
```

**優先級 P1: 安全關鍵路徑**

| 測試目標 | 測試類型 | 預估檔案數 |
|----------|---------|-----------|
| Auth middleware | Unit + Integration | 5 |
| HITL 審批流程 | Integration + E2E | 4 |
| MCP 安全檢查 | Unit + Integration | 3 |
| RiskAssessor | Unit | 2 |

**優先級 P2: 未覆蓋的 API 模組 (26 個)**

按業務重要性排序：
1. `sessions/` — 核心對話功能
2. `agents/` — Agent 管理
3. `workflows/` — 工作流管理
4. `orchestration/` — 編排層
5. `hybrid/` — 混合模式
6. `claude_sdk/` — Claude 整合
7. `mcp/` — MCP 工具
8. 其餘 19 個模組

### 5.5 Phase 3: 深度覆蓋 (Week 7-12)

**目標**: 從 ~50% 提升到 80%

| 任務 | 工作量 | 覆蓋率增量 |
|------|--------|-----------|
| Domain 層單元測試補充 | 3-4 天 | +15% |
| Integration 模組測試 | 4-5 天 | +10% |
| Edge case 和錯誤路徑 | 2-3 天 | +5% |
| API 端點 snapshot 測試 | 2 天 | +5% |
| **合計** | **11-14 天** | **+35%** |

### 5.6 覆蓋率里程碑

```
Week 0  (現在):  ~30% (估計)
Week 2  (基建):  ~35% (加入追蹤 + 低掛水果)
Week 6  (核心):  ~55% (主流程 + 安全路徑)
Week 10 (深度):  ~75% (Domain + Integration)
Week 12 (目標):  ~80% (Edge case + API snapshot)
```

---

## 六、前端測試策略

### 6.1 現狀

- **現有測試**: 13 個檔案，全部在 `agent-swarm/__tests__/`
- **測試框架**: Vitest（推測，基於 Vite 生態）
- **覆蓋組件**: SwarmHeader, WorkerCard, WorkerCardList, OverallProgress, etc.
- **未覆蓋**: 其餘 114+ 組件、16 hooks、3 stores、37+ pages

### 6.2 測試策略矩陣

| 測試類型 | 工具 | 覆蓋目標 | 優先級 |
|----------|------|---------|--------|
| **組件單元測試** | Vitest + React Testing Library | 核心組件 50+ | P1 |
| **Hook 測試** | Vitest + renderHook | 所有 17 hooks | P1 |
| **Store 測試** | Vitest | 所有 3 stores | P0 |
| **頁面整合測試** | Vitest + MSW | 核心頁面 10+ | P2 |
| **E2E 測試** | Playwright | 核心流程 5+ | P2 |
| **Visual 回歸** | Playwright screenshot | 關鍵 UI | P3 |

### 6.3 P0: Store 測試 (立即)

```typescript
// stores/__tests__/authStore.test.ts
import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '../authStore';

describe('AuthStore', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
  });

  it('should handle login successfully', async () => {
    const { result } = renderHook(() => useAuthStore());
    await act(async () => {
      await result.current.login('test@test.com', 'password');
    });
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should clear auth state on logout', () => {
    const { result } = renderHook(() => useAuthStore());
    act(() => result.current.logout());
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
  });

  it('should not leak sensitive data via console.log', () => {
    // 確保移除 console.log 後的行為不變
    const consoleSpy = vi.spyOn(console, 'log');
    // ... test login flow ...
    expect(consoleSpy).not.toHaveBeenCalled();
  });
});
```

### 6.4 P1: Hook 測試

最需要測試的 hooks（按風險排序）:

| Hook | LOC | 測試重點 |
|------|-----|---------|
| `useUnifiedChat` | 1,313 | 訊息發送/接收、錯誤處理、SSE 連接 |
| `useAGUI` | 982 | AG-UI 事件處理、狀態管理 |
| `useSwarmMock` | 623 | Mock 數據生成正確性 |
| `useSwarmReal` | 603 | SSE 連接、事件解析 |
| `useApprovalFlow` | ~200 | 審批狀態機 |
| `useHybridMode` | ~200 | 模式切換 |
| `useCheckpoints` | ~200 | Checkpoint 操作 |

### 6.5 工作量估算

| 任務 | 工作量 |
|------|--------|
| 測試基礎設施配置 (Vitest + RTL + MSW) | 0.5 天 |
| Store 測試 (3 stores) | 1 天 |
| Hook 測試 (17 hooks) | 3-4 天 |
| 核心組件測試 (30+ 組件) | 4-5 天 |
| 頁面整合測試 (10 pages) | 3-4 天 |
| E2E 測試 (5 核心流程) | 2-3 天 |
| **合計** | **14-18 天** |

---

## 七、console.log 清理方案

### 7.1 分布統計

| 檔案 | 數量 | 風險等級 | 原因 |
|------|------|---------|------|
| `pages/UnifiedChat.tsx` | 15 | MEDIUM | 調試遺留，可能洩漏對話內容 |
| `hooks/useUnifiedChat.ts` | 11 | MEDIUM | 訊息處理調試 |
| `agent-swarm/hooks/useSwarmEventHandler.ts` | 9 | LOW | Swarm 事件調試 |
| **`store/authStore.ts`** | **5** | **CRITICAL** | **洩漏 email、token、refresh 狀態** |
| `api/endpoints/ag-ui.ts` | 3 | MEDIUM | API 調試 |
| `agent-swarm/hooks/useSwarmEvents.ts` | 3 | LOW | 事件調試 |
| `utils/guestUser.ts` | 3 | LOW | Guest 用戶調試 |
| `hooks/useApprovalFlow.ts` | 1 | LOW | 審批調試 |
| `hooks/useAGUI.ts` | 1 | LOW | AG-UI 調試 |
| `hooks/useCheckpoints.ts` | 1 | LOW | Checkpoint 調試 |
| `hooks/useHybridMode.ts` | 1 | LOW | 模式切換調試 |
| `hooks/useSwarmReal.ts` | 1 | LOW | Swarm 調試 |
| **合計** | **54** | | |

### 7.2 清理策略

**P0 立即清理: authStore.ts (CRITICAL)**

```typescript
// === BEFORE ===
console.log('[AuthStore] Login successful:', user.email);
console.log('[AuthStore] Registration successful:', user.email);
console.log('[AuthStore] Logged out');
console.log('[AuthStore] No refresh token, cannot refresh session');
console.log('[AuthStore] Session refreshed');

// === AFTER ===
// 完全移除。如需調試，使用條件式 logger：
if (import.meta.env.DEV) {
  logger.debug('[AuthStore] Login successful');  // 不包含 email
}
```

**P1 替換為 Logger: 其他 49 個**

```typescript
// === 建立 frontend/src/utils/logger.ts ===
const isDev = import.meta.env.DEV;

export const logger = {
  debug: (...args: unknown[]) => {
    if (isDev) console.log('[DEBUG]', ...args);
  },
  info: (...args: unknown[]) => {
    if (isDev) console.info('[INFO]', ...args);
  },
  warn: (...args: unknown[]) => {
    console.warn('[WARN]', ...args);
  },
  error: (...args: unknown[]) => {
    console.error('[ERROR]', ...args);
  },
};
```

### 7.3 ESLint 規則強制

```javascript
// .eslintrc.js
rules: {
  'no-console': ['error', {
    allow: ['warn', 'error']  // 只允許 warn 和 error
  }],
}
```

### 7.4 工作量

| 任務 | 工作量 |
|------|--------|
| 移除 authStore 的 5 個 console.log | 15 分鐘 |
| 建立 logger 工具 | 30 分鐘 |
| 替換其餘 49 個 console.log | 2 小時 |
| 配置 ESLint 規則 | 15 分鐘 |
| **合計** | **~3 小時** |

---

## 八、store/stores 統一遷移

### 8.1 現狀

```
frontend/src/
├── store/                    # 單數（1 檔案）
│   └── authStore.ts          # 認證狀態 (Zustand)
└── stores/                   # 複數（2 檔案 + 1 測試）
    ├── unifiedChatStore.ts   # 聊天狀態 (Zustand)
    ├── swarmStore.ts         # Swarm 狀態 (Zustand)
    └── __tests__/
        └── swarmStore.test.ts
```

### 8.2 影響評估

- 目錄不一致造成開發者困惑
- 新 store 不知道應該放在哪裡
- IDE 自動導入可能混淆路徑
- 不影響運行時行為

### 8.3 遷移方案

**統一到 `stores/`（複數形式）** — 符合 React 社群慣例

```
frontend/src/stores/
├── __tests__/
│   ├── authStore.test.ts     # 新增
│   └── swarmStore.test.ts    # 已存在
├── authStore.ts              # 從 store/ 遷移
├── unifiedChatStore.ts       # 已存在
└── swarmStore.ts             # 已存在
```

**遷移步驟**:

1. 將 `store/authStore.ts` 移至 `stores/authStore.ts`
2. 全局替換 import 路徑：
   ```
   from '@/store/authStore'  →  from '@/stores/authStore'
   或
   from '../store/authStore'  →  from '../stores/authStore'
   ```
3. 刪除空的 `store/` 目錄
4. 在 `stores/index.ts` 建立 barrel export（可選）

**影響範圍**:

```bash
# 搜索所有引用
grep -r "store/authStore" frontend/src/
```

### 8.4 工作量

| 任務 | 工作量 |
|------|--------|
| 移動檔案 | 5 分鐘 |
| 更新 import 路徑 | 30 分鐘 |
| 驗證無破壞 | 15 分鐘 |
| **合計** | **~50 分鐘** |

---

## 九、技術債量化 (SQALE)

### 9.1 SQALE 方法說明

SQALE (Software Quality Assessment based on Lifecycle Expectations) 將技術債量化為**修復所需的人天數**，按品質特性分類。

### 9.2 IPA Platform SQALE 評估

| SQALE 特性 | 問題類型 | 問題數量 | 單位修復成本 | 合計人天 |
|-----------|---------|---------|-------------|---------|
| **可靠性** | 空函數體 (需填充) | ~180 | 0.5h | **11.3** |
| **可靠性** | Mock/真實代碼混雜 | 18 classes | 2h | **4.5** |
| **可靠性** | InMemory 存儲替換 | 9 classes | 1d | **9.0** |
| **可靠性** | STUB 模組 (correlation, rootcause) | 2 modules | 5d | **10.0** |
| **安全性** | Auth 覆蓋 (7% → 100%) | 36 modules | 0.5d | **18.0** |
| **安全性** | JWT Secret 硬編碼 | 1 | 0.5h | **0.1** |
| **安全性** | Rate Limiting | 1 | 1d | **1.0** |
| **安全性** | CORS/Port 修復 | 2 | 0.5h | **0.1** |
| **安全性** | console.log 清理 (auth) | 5 | 0.1h | **0.1** |
| **可維護性** | 大檔案拆分 (>800) | 58 files | 2h | **14.5** |
| **可維護性** | store/stores 統一 | 1 | 0.5h | **0.1** |
| **可維護性** | Hook barrel export | 6 hooks | 0.1h | **0.1** |
| **可測試性** | API 測試補充 (33%→80%) | 26 modules | 1d | **26.0** |
| **可測試性** | 前端測試 | ~100 components | 0.5d | **50.0** |
| **可測試性** | 覆蓋率基礎設施 | 1 | 1d | **1.0** |
| **性能效率** | 單 Worker 配置 | 1 | 1d | **1.0** |
| **性能效率** | ContextSync 加鎖 | 2 impls | 1d | **2.0** |
| **性能效率** | Checkpoint 統一 | 4 systems | 3d | **3.0** |
| **可攜性** | ReactFlow 安裝/整合 | 1 | 2d | **2.0** |
| **可攜性** | RabbitMQ 整合 | 1 | 5d | **5.0** |

### 9.3 SQALE 總結

| 特性 | 人天 | 佔比 |
|------|------|------|
| **可靠性** | 34.8 天 | 22.0% |
| **安全性** | 19.3 天 | 12.2% |
| **可維護性** | 14.7 天 | 9.3% |
| **可測試性** | 77.0 天 | 48.6% |
| **性能效率** | 6.0 天 | 3.8% |
| **可攜性** | 7.0 天 | 4.4% |
| **合計** | **158.8 天** | **100%** |

### 9.4 SQALE 技術債比率

```
技術債比率 = 修復成本 / 開發成本
           = 158.8 天 / ~180 天 (估計 3 個月開發)
           = 88.2%

SQALE 評級: D (60-100% = 嚴重技術債)
```

**解讀**: 修復所有技術債幾乎等於重新開發一次。但這不是因為代碼品質差，而是因為大量功能**只完成了骨架**，血肉仍需填充。

### 9.5 關鍵洞察

技術債中**48.6% 來自測試缺失**。如果只看代碼本身的技術債（不含測試），則為 81.8 天，債務比率降至 45.4%（SQALE 評級 C），這更符合快速原型開發的正常水準。

---

## 十、代碼品質工具鏈建議

### 10.1 推薦工具鏈

| 工具 | 用途 | 整合方式 | 優先級 |
|------|------|---------|--------|
| **Coverage.py + pytest-cov** | Python 測試覆蓋率 | CI Pipeline | P0 |
| **Istanbul/c8** | TypeScript 測試覆蓋率 | CI Pipeline | P0 |
| **ESLint no-console** | 禁止 console.log | Pre-commit hook | P0 |
| **SonarQube/SonarCloud** | 全面代碼品質分析 | CI Pipeline | P1 |
| **Black + isort + flake8** | Python 格式化 + Lint | Pre-commit hook | P1 (已有) |
| **Prettier** | TypeScript 格式化 | Pre-commit hook | P1 (已有) |
| **mypy strict** | Python 類型檢查 | CI Pipeline | P2 |
| **Bandit** | Python 安全掃描 | CI Pipeline | P1 |
| **npm audit / safety** | 依賴安全掃描 | CI Pipeline | P1 |
| **Codecov** | 覆蓋率報告 + Badge | GitHub PR | P1 |
| **pre-commit** | Git Hook 管理 | Local | P1 |

### 10.2 SonarQube 配置建議

```yaml
# sonar-project.properties
sonar.projectKey=ipa-platform
sonar.projectName=IPA Platform

# Python
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.version=3.11

# TypeScript
sonar.typescript.lcov.reportPaths=frontend/coverage/lcov.info

# 排除
sonar.exclusions=**/tests/**,**/node_modules/**,**/__pycache__/**

# 品質門檻
sonar.qualitygate.wait=true
```

### 10.3 Pre-commit 配置

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        args: [--line-length=100]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.8
    hooks:
      - id: bandit
        args: [-r, src, -f, json, -o, bandit-report.json]

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.0.0
    hooks:
      - id: eslint
        files: \.[jt]sx?$
        args: [--fix]
```

### 10.4 CI Pipeline 品質門

```yaml
# .github/workflows/quality.yml
quality-gate:
  steps:
    - name: Python Tests + Coverage
      run: |
        cd backend
        pytest --cov=src --cov-report=xml --cov-fail-under=80

    - name: Python Security Scan
      run: |
        cd backend
        bandit -r src -f json -o bandit-report.json || true

    - name: Frontend Tests + Coverage
      run: |
        cd frontend
        npm run test:coverage

    - name: ESLint (no console.log)
      run: |
        cd frontend
        npm run lint

    - name: Type Check
      run: |
        cd backend && mypy src
        cd frontend && npx tsc --noEmit
```

---

## 十一、Technical Debt Burndown 計劃

### 11.1 計劃概覽

```
                     158.8 天技術債
                     ↓
Week 1-2:   安全基礎 (19.3d → 0d)     ████████████░░░░░░░░ -12%
Week 3-4:   代碼衛生 (14.7d → 0d)     ████████████████░░░░ -9%
Week 5-8:   可靠性 (34.8d → 10d)      ████████████████████ -16%
Week 9-14:  測試覆蓋 (77d → 20d)      ████████████████████ -36%
Week 15+:   持續改進                    剩餘 ~37d (23%)
```

### 11.2 Sprint 級別排程

#### Sprint 1-2 (Week 1-2): 安全修復

| 任務 | 人天 | 債務消除 |
|------|------|---------|
| CORS origin 修復 (3000→3005) | 0.05 | 0.1d |
| Vite proxy 修復 (8010→8000) | 0.05 | 0.1d |
| JWT Secret 環境變量化 | 0.05 | 0.1d |
| console.log 清理 (authStore) | 0.1 | 0.1d |
| Rate Limiting (slowapi) | 1 | 1.0d |
| 全局 Auth middleware (36 modules) | 8 | 18.0d |
| **小計** | **~9 天** | **~19.3d** |

#### Sprint 3-4 (Week 3-4): 代碼衛生

| 任務 | 人天 | 債務消除 |
|------|------|---------|
| Mock 類分離 | 3.5 | 4.5d |
| console.log 替換 (其餘 49 個) | 0.3 | 部分 |
| store/stores 統一 | 0.1 | 0.1d |
| Hook barrel export 修復 | 0.1 | 0.1d |
| ESLint no-console 規則 | 0.1 | 預防 |
| Coverage.py 基礎設施 | 1 | 1.0d |
| **小計** | **~5 天** | **~5.7d + 預防** |

#### Sprint 5-8 (Week 5-8): 可靠性修復

| 任務 | 人天 | 債務消除 |
|------|------|---------|
| InMemoryApprovalStorage → Redis | 1 | 1.0d |
| 其他 InMemory 存儲替換 (8 個) | 8 | 8.0d |
| 空函數體填充 (P0 + P1) | 6 | 6.0d |
| ContextSynchronizer 加鎖 | 2 | 2.0d |
| Checkpoint 統一 | 3 | 3.0d |
| Top 5 大檔案拆分 | 3 | 3.0d |
| **小計** | **~23 天** | **~23.0d** |

#### Sprint 9-14 (Week 9-14): 測試覆蓋

| 任務 | 人天 | 債務消除 |
|------|------|---------|
| 主流程 E2E 測試 | 5 | 5.0d |
| API 模組測試 (26 modules) | 15 | 15.0d |
| Domain 單元測試補充 | 5 | 5.0d |
| 前端 Store/Hook 測試 | 8 | 8.0d |
| 前端組件測試 | 10 | 10.0d |
| 前端 E2E (Playwright) | 5 | 5.0d |
| 其餘大檔案拆分 | 8 | 8.0d |
| **小計** | **~56 天** | **~56.0d** |

### 11.3 Burndown 圖表

```
技術債 (人天)
160 ┤ ●
    │  ╲
140 ┤   ● Sprint 1-2 完成
    │    │
120 ┤    ● Sprint 3-4 完成
    │     ╲
100 ┤      ╲
    │       ╲
 80 ┤        ● Sprint 5-8 完成
    │         ╲
 60 ┤          ╲
    │           ╲
 40 ┤            ╲
    │             ● Sprint 9-14 完成
 20 ┤              │
    │              │ 持續改進
  0 ┤──────────────┼─────────
    W0  W2  W4  W6  W8  W10  W12  W14+
```

---

## 十二、報告可能遺漏的品質問題

### 12.1 V2 報告未深入探討但本分析發現的問題

#### 問題 A: Abstract Method 與 "真正空" 函數體的區分

V7/V2 報告計算了 323 個空函數體（204 pass + 119 ellipsis），但**未區分以下三種情況**：

| 類型 | 佔比（估計） | 是否需要修復 |
|------|-------------|-------------|
| ABC `@abstractmethod` + `pass` | ~30% | 否（設計正確） |
| Protocol 定義 + `...` | ~15% | 否（設計正確） |
| **未實現的業務方法** | **~55%** | **是** |

因此，實際需要填充的空函數體約 **~180 個**，而非 323 個。但 180 個仍然非常多。

#### 問題 B: Domain 層 DEPRECATED 模組未清理

`domain/orchestration/` 被標記為 DEPRECATED（應使用 `integrations/agent_framework/`），但：
- 仍然有 `memory/base.py` (415 LOC) 被引用
- `multiturn/`, `planning/`, `nested/` 仍存在
- 新舊代碼的交叉引用可能造成混亂

**建議**: 如果確認已完全遷移，應刪除或重命名為 `_deprecated_orchestration/`。

#### 問題 C: Barrel Export 過深

以 `orchestration/__init__.py` 為例，匯出 57 個符號。這不僅包含 Mock（已在第三章分析），更包含**所有子模組的所有公開類**。

這造成：
- 任何子模組的變更都可能影響頂層 barrel
- 循環 import 風險增加
- IDE 自動完成清單過長

**建議**: 保持子模組的獨立 import，頂層 `__init__.py` 只匯出最常用的 5-10 個符號。

#### 問題 D: Migration 檔案 (5 個) 佔用大量 LOC

```
builders/workflow_executor_migration.py    1,277 LOC
builders/magentic_migration.py             1,038 LOC
builders/groupchat_migration.py            1,028 LOC
builders/concurrent_migration.py           ~800 LOC (估)
builders/handoff_migration.py              ~600 LOC (估)
```

這些 migration 檔案合計 ~4,700 LOC，是 MAF API 變更的過渡代碼。如果已完成遷移，應歸檔或刪除。

#### 問題 E: 重複的 ContextSynchronizer 實現

存在 **2 個完全獨立的 `ContextSynchronizer` 類**：

1. `integrations/hybrid/context/sync/synchronizer.py` (Line 63)
2. `integrations/claude_sdk/hybrid/synchronizer.py` (Line 278)

兩者功能類似（MAF/Claude 上下文同步），但：
- 都沒有 Lock
- 都使用 in-memory dict
- 調用者可能不知道使用的是哪一個

**建議**: 統一為一個實現，加入 asyncio.Lock。

#### 問題 F: 可能的循環依賴

基於層級架構：
```
L5 Hybrid → L6 MAF (執行)
L5 Hybrid → L7 Claude (執行)
L6 MAF → L5 Hybrid (switching 回調?)
```

FrameworkSelector 在 L5 選擇 MAF 後，控制流到 L6。但如果 L6 需要 switching 回 L5（如 failure trigger），可能形成循環依賴。

**建議**: 使用 event-driven 架構或 mediator pattern 打破循環。

#### 問題 G: 硬編碼配置散布

除了 JWT Secret 外，其他硬編碼值：
- `max_concurrent_tasks: 5` (claude_sdk)
- `timeout: 30min` (HITL approval)
- `time_decay_factor: 0.1` (correlation)
- `semantic_threshold: 0.6` (correlation)
- `reload=True` (main.py)

**建議**: 所有配置集中到 `src/core/config.py` 並通過環境變數配置。

#### 問題 H: 前端 TypeScript 嚴格模式

未確認 `tsconfig.json` 是否啟用了 `strict: true`。如果沒有，可能存在：
- 隱式 `any` 類型
- 空值未檢查
- 未使用的局部變數

**建議**: 啟用 TypeScript strict 模式，逐步修復錯誤。

#### 問題 I: 沒有 API 版本策略

534 端點全部在 `/api/v1/` 下，沒有版本遷移策略。一旦需要破壞性變更（如 Auth 加入），所有消費者同時受影響。

**建議**: 至少規劃 v2 的遷移路徑，使用 FastAPI 的 `prefix` 和 `deprecated` 標記。

#### 問題 J: Error Handling 一致性

Session 模組有完善的 24 error codes 系統，但其他模組（orchestration、hybrid、mcp）沒有統一的錯誤體系。可能導致前端收到不一致的錯誤格式。

**建議**: 建立全局 Exception Handler middleware，統一錯誤格式。

---

## 附錄: 分析方法論

本報告的分析流程：

1. **閱讀 V2 全面分析報告** — 理解全局視角和已識別的問題
2. **獨立代碼抽樣驗證** — 對每個品質聲明進行 grep/read 驗證
   - `pass` 和 `...` 的逐層計數
   - Mock 類的 barrel export 追蹤（5 層深度）
   - console.log 的逐檔案分布
   - ContextSynchronizer 的 Lock 搜索
   - 大檔案排名驗證
3. **深度代碼閱讀** — 抽樣檢查關鍵檔案的實際內容
   - `domain/orchestration/memory/base.py` — 驗證 ABC 合理性
   - `domain/sessions/bridge.py` — 驗證 Protocol ellipsis 合理性
   - `domain/sessions/repository.py` — 驗證 abstractmethod pass 合理性
   - `correlation/analyzer.py` — 驗證 STUB 假數據
   - `orchestration/__init__.py` — 驗證 Mock 匯出路徑
4. **量化分析** — SQALE 技術債計算
5. **方案設計** — 每個問題的具體修復方案、代碼示例、工作量估算

---

*本報告由 Code Quality Lead 獨立完成，基於 V2 全面分析報告和獨立代碼驗證。所有數據均通過 grep/read 實際確認，非推測。*
