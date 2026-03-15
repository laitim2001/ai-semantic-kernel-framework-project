# MAF 1.0.0rc4 升級萬全規劃策略

**文件版本**: 1.0
**分析日期**: 2026-03-15
**升級目標**: agent-framework 1.0.0b260114 → 1.0.0rc4
**基礎數據**: 3 份研究報告 + V8 全面分析 + Claude SDK 差異報告 + Architecture Review Board 共識報告

---

## 執行摘要

IPA Platform 目前運行 MAF `1.0.0b260114`，落後最新版 `1.0.0rc4` 達 **9 個版本、約 2 個月**。此差距包含 18 項破壞性變更（BC），但經完整掃描確認，**僅 BC-07（命名空間遷移）為唯一 CRITICAL 影響**，涉及 18 個檔案中的 23 條 import 語句。其餘 17 項 BC 對 IPA 的直接影響為零或需人工驗證。

**為什麼必須升級**: MAF 正積極邁向 GA（1.0.0 穩定版）。延遲升級將使遷移成本從目前的 ~34 SP 增長至 GA 後的 60+ SP。RC 階段的 API 已趨穩定，現在是最佳升級時機。

**風險評估**: MEDIUM-HIGH（可控）。IPA 的 Adapter Pattern 成功將影響範圍限制在 `backend/src/integrations/agent_framework/` 目錄內（17/18 受影響檔案）。升級不會惡化 V8 已知的 62 個問題，反而可自動修復 2-4 個 bug。

**工期預估**: 2-3 個 Sprint（~34 SP），採三階段漸進式執行。

**Go/No-Go 決策**: **GO — 有條件執行**。前提條件為：確認現有測試通過率基線、建立功能分支隔離、確保 2 個完整 Sprint 的團隊容量。

---

## 1. 升級決策論據

### 1.1 為什麼必須升級（延遲成本分析）

| 因素 | 現在升級（rc4） | 延遲至 GA 後升級 |
|------|----------------|-----------------|
| 累積 BC 數量 | 18 項（僅 1 項 CRITICAL） | 預估 25-35 項（更多重構） |
| 估算工作量 | ~34 SP（2-3 Sprint） | ~60-80 SP（4-6 Sprint） |
| API 穩定性 | RC 階段，API 已趨穩定 | GA 後可能有最終重大重組 |
| 新功能可用性 | Claude SDK BaseAgent、OTel 追蹤、背景回應 | 相同，但錯過 2+ 個月的早期整合優勢 |
| Bug 修復 | 立即獲得 UTC 時區、MCP 重複註冊等修復 | 繼續承受已知 bug |
| 安全漏洞 | 獲得最新安全修復 | 30% 概率暴露於未修補漏洞 |
| 開發者知識 | 團隊學習最新 API，投資有效 | 持續投入過時 API 的知識，浪費學習成本 |

**結論**: 越早升級成本越低。每延遲一個版本，累積的遷移成本約增加 ~5 SP。

### 1.2 升級的預期收益

**立即收益**:
- 獲得 2-4 個 bug 修復（UTC 時區、空內容驗證、MCP 重複工具註冊）
- API 與 RC 階段對齊，為 GA 做好準備
- 解鎖 OpenTelemetry MCP 自動追蹤（配置即用，幾乎零工作量）

**短期收益（1-2 Sprint 內）**:
- 背景回應 + Continuation Tokens — 解決長時間 Agent 任務的 HTTP timeout 問題
- Agent Skills — 標準化領域知識封裝，降低 prompt 管理複雜度
- HITL 工具呼叫審批 — 利用官方修復的 session/streaming 審批流程

**長期收益（3+ Sprint）**:
- Claude SDK BaseAgent — 原生 Claude 整合路徑，減少 47 檔自建 SDK 的維護負擔
- 宣告式 YAML 工作流程 — 簡化新工作流程定義
- 與 MAF GA 版本的無縫升級路徑

### 1.3 Go/No-Go 決策（含前提條件）

**決策: GO — 有條件執行**

| 決策因素 | 評估 | 詳情 |
|---------|------|------|
| 技術可行性 | **HIGH** | Adapter Pattern 隔離使變更範圍可控（18 檔, 23 import） |
| 依賴相容性 | **HIGH** | 無 pip 依賴衝突，pydantic-settings 獨立於 MAF |
| 測試覆蓋 | **MEDIUM** | 10 個 MAF 專用測試 + 35+ 相關測試 |
| 回滾能力 | **HIGH** | Git 分支策略確保 <5 分鐘回滾 |
| 業務價值 | **HIGH** | OTel 追蹤、背景回應、Agent Skills |
| 延遲成本 | **CRITICAL** | GA 後跳級遷移成本指數增長 |

**必要前提條件**（必須在升級前完成）:
1. 確認現有測試套件通過率基線 — 執行 `pytest --tb=no -q > baseline.txt` 記錄基線
2. 建立功能分支 `feature/maf-rc4-upgrade` 進行隔離開發
3. 確保 2 個完整 Sprint 的團隊容量（不與其他大型功能並行）
4. 閱讀 [Microsoft Learn Python 2026 重大變更指南](https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes)

---

## 2. 影響範圍精確地圖

### 2.1 受影響檔案完整清單（按 BC 編號分組）

#### BC-07（CRITICAL）：命名空間遷移 — 23 條 import 語句

所有路徑相對於 `backend/src/`。

| # | 檔案路徑 | 行號 | 目前程式碼 | 需改為 |
|---|----------|------|-----------|--------|
| 1 | `integrations/agent_framework/builders/concurrent.py` | 83 | `from agent_framework import ConcurrentBuilder` | `from agent_framework.workflows.orchestrations import ConcurrentBuilder` |
| 2 | `integrations/agent_framework/builders/groupchat.py` | 83-87 | `from agent_framework import (GroupChatBuilder)` | `from agent_framework.workflows.orchestrations import (GroupChatBuilder)` |
| 3 | `integrations/agent_framework/builders/handoff.py` | 54-57 | `from agent_framework import (HandoffBuilder, HandoffAgentUserRequest)` | `from agent_framework.workflows.orchestrations import HandoffBuilder`; `from agent_framework.workflows import HandoffAgentUserRequest` |
| 4 | `integrations/agent_framework/builders/magentic.py` | 39-43 | `from agent_framework import (MagenticBuilder, MagenticManagerBase, StandardMagenticManager)` | `from agent_framework.workflows.orchestrations import (MagenticBuilder, MagenticManagerBase, StandardMagenticManager)` |
| 5 | `integrations/agent_framework/builders/planning.py` | 31 | `from agent_framework import MagenticBuilder, Workflow` | `from agent_framework.workflows.orchestrations import MagenticBuilder`; `from agent_framework.workflows import Workflow` |
| 6 | `integrations/agent_framework/builders/nested_workflow.py` | 71 | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` | `from agent_framework.workflows import Workflow, WorkflowBuilder, WorkflowExecutor` |
| 7 | `integrations/agent_framework/builders/workflow_executor.py` | 52-56 | `from agent_framework import (WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage)` | `from agent_framework.workflows import (WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage)` |
| 8 | `integrations/agent_framework/builders/agent_executor.py` | 155 | `from agent_framework import ChatAgent, ChatMessage, Role` | `from agent_framework.agents import ChatAgent, ChatMessage, Role` |
| 9 | `integrations/agent_framework/builders/agent_executor.py` | 156 | `from agent_framework.azure import AzureOpenAIResponsesClient` | 驗證路徑是否變更為 `from agent_framework.clients.azure import AzureOpenAIResponsesClient` |
| 10 | `integrations/agent_framework/core/workflow.py` | 37 | `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor` | `from agent_framework.workflows import Workflow, WorkflowBuilder, Edge, Executor` |
| 11 | `integrations/agent_framework/core/executor.py` | 38 | `from agent_framework import Executor, WorkflowContext, handler` | `from agent_framework.workflows import Executor, WorkflowContext, handler` |
| 12 | `integrations/agent_framework/core/execution.py` | 34 | `from agent_framework import ChatAgent, SequentialBuilder, Workflow` | `from agent_framework.agents import ChatAgent`; `from agent_framework.workflows.orchestrations import SequentialBuilder`; `from agent_framework.workflows import Workflow` |
| 13 | `integrations/agent_framework/core/edge.py` | 29 | `from agent_framework import Edge` | `from agent_framework.workflows import Edge` |
| 14 | `integrations/agent_framework/core/events.py` | 34 | `from agent_framework import WorkflowStatusEvent` | `from agent_framework.workflows import WorkflowStatusEvent` |
| 15 | `integrations/agent_framework/core/approval.py` | 39 | `from agent_framework import Executor, handler, WorkflowContext` | `from agent_framework.workflows import Executor, handler, WorkflowContext` |
| 16 | `integrations/agent_framework/core/approval_workflow.py` | 36 | `from agent_framework import Workflow, Edge` | `from agent_framework.workflows import Workflow, Edge` |
| 17 | `integrations/agent_framework/multiturn/adapter.py` | 27-31 | `from agent_framework import (CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint)` | `from agent_framework.workflows import (CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint)` |
| 18 | `integrations/agent_framework/multiturn/checkpoint_storage.py` | 31 | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage` | `from agent_framework.workflows import CheckpointStorage, InMemoryCheckpointStorage` |
| 19 | `integrations/agent_framework/memory/base.py` | 25 | `from agent_framework import Context, ContextProvider` | `from agent_framework.agents import Context, ContextProvider` |
| 20 | `integrations/agent_framework/memory/base.py` | 169 | `from agent_framework import MemoryStorage` | `from agent_framework.agents import MemoryStorage` |
| 21 | `integrations/agent_framework/checkpoint.py` | 102 | `from agent_framework import WorkflowCheckpoint` | `from agent_framework.workflows import WorkflowCheckpoint` |
| 22 | `integrations/agent_framework/workflow.py` | 425 | `from agent_framework import WorkflowBuilder` | `from agent_framework.workflows import WorkflowBuilder` |
| 23 | `infrastructure/storage/storage_factories.py` | 308 | `from agent_framework import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage` | `from agent_framework.workflows import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage` |

#### 動態引用（ACL 層 — 需特殊處理）

| # | 檔案路徑 | 行號 | 用途 | 處理方式 |
|---|----------|------|------|---------|
| 1 | `integrations/agent_framework/acl/version_detector.py` | 85 | `import agent_framework` — 讀取 `__version__` | 版本偵測邏輯需更新以支援 rc4 版本格式 |
| 2 | `integrations/agent_framework/acl/version_detector.py` | 135 | `hasattr(agent_framework, api_name)` 檢查 | API 名稱可能不再在頂層命名空間，需更新檢查路徑 |
| 3 | `integrations/agent_framework/acl/version_detector.py` | 165 | 批次 API 可用性檢查 | 同上 |
| 4 | `integrations/agent_framework/acl/adapter.py` | 139 | `getattr(agent_framework, maf_class_name)` 動態取類別 | 需更新為從子模組動態取類別 |

#### 其他 BC（LOW-MEDIUM 影響）

| BC | 直接受影響使用點 | 需人工驗證 | 說明 |
|-----|----------------|-----------|------|
| BC-01: `create_agent` → `as_agent` | 0 | 0 | IPA 的 `create_agent` 是自定義方法，非 MAF API |
| BC-02: `AgentRunResponse` → `AgentResponse` | 0 | 0 | IPA 的 `AgentRunResponse` 是自定義 Pydantic model |
| BC-03: `display_name` 移除 | 0 | 需驗證 builders | 未發現直接使用，但需人工驗證 dict/kwargs 傳遞 |
| BC-04: `context_providers` → `context_provider` | 0 | 1（memory/base.py） | 搜索未發現複數形式使用 |
| BC-05: `source_executor_id` → `source` | 0 | 1（core/edge.py） | IPA 使用自定義屬性名 |
| BC-06: Exception 重命名 | 0 | 0 | 未發現 `ServiceException` 等舊例外類別引用 |
| BC-08: `AFBaseSettings` 移除 | 0 | 0 | IPA 不使用 MAF 設定系統 |
| BC-09: `AggregateContextProvider` 移除 | 0 | 0 | 未發現使用 |
| BC-10: `FunctionTool` 泛型移除 | 0 | 0 | 未發現 `FunctionTool[` 使用 |
| BC-11: 事件 isinstance 變更 | 0 | 0 | 未發現 MAF 事件 isinstance 檢查 |
| BC-12: Entra auth token 變更 | 0 | 0 | 未發現 `ad_token_provider` 使用 |
| BC-13: `InMemoryHistoryProvider` 移除 | 0 | 0 | 未發現使用 |
| BC-14: `WorkflowOutputEvent` 移除 | 0 | 0 | 未發現使用 |
| BC-15: Checkpoint 模型重構 | 潛在 | 2（checkpoint.py, multiturn/） | 需驗證 API 差異 |
| BC-16: 標準化編排輸出 | 潛在 | 需驗證 | GroupChat 輸出處理 |
| BC-17: Azure Functions Schema | 0 | 0 | IPA 不使用 Azure Functions |
| BC-18: HITL 工具呼叫審批 | 潛在 | 1（magentic.py） | 新增功能，非必要遷移 |

### 2.2 不受影響的確認

以下層級**完全不受** MAF 升級波及：

| 層級 | 檔案數 | 不受影響原因 |
|------|--------|-------------|
| `backend/src/api/v1/` | 39 模組 | API 路由透過 Adapter 層間接使用 MAF，不直接 import |
| `backend/src/domain/` | 20 模組 | 業務邏輯層無 MAF 依賴 |
| `backend/src/infrastructure/` | 除 `storage_factories.py` 外 | 基礎設施層僅 1 個檔案引用 MAF |
| `backend/src/integrations/claude_sdk/` | 47 檔 | 完全自建抽象層，不依賴 MAF |
| `backend/src/integrations/ag_ui/` | 全部 | 透過 Adapter 間接使用，零直接 MAF import |
| `backend/src/integrations/hybrid/` | 全部 | 依賴 IPA 自建的 claude_sdk 和 adapter 層 |
| `backend/src/integrations/orchestration/` | 全部 | 透過 Adapter 間接使用 |
| `backend/src/integrations/mcp/` | 全部 | IPA 自建 MCP Server 實作 |
| `backend/tests/` | 全部 | 零直接 MAF import（透過 IPA Adapter 測試） |
| `frontend/` | 全部 | 純前端，無後端依賴 |

### 2.3 影響統計摘要

| 指標 | 數量 |
|------|------|
| 受影響 .py 檔案數 | **18**（+ 4 個 ACL 動態引用） |
| 需修改的 import 語句 | **23** |
| 引入的唯一 MAF 類別 | **28** |
| 配置檔案變更 | **1**（requirements.txt） |
| 不受影響的 .py 檔案數 | **900+**（佔總量 98%） |
| 影響集中度 | **95%** 在 `integrations/agent_framework/` 內 |

---

## 3. 破壞性變更處理方案

### 3.1 BC-07（CRITICAL）：命名空間遷移 — 逐檔案變更指令

BC-07 是唯一的 CRITICAL 影響。所有 23 條活躍 import 均從頂層 `agent_framework` 引入，需遷移到子模組路徑。

#### 遷移規則映射

| 原始頂層 import | 新子模組路徑 | 涉及檔案數 |
|----------------|-------------|-----------|
| `ConcurrentBuilder` | `agent_framework.workflows.orchestrations` | 1 |
| `GroupChatBuilder` | `agent_framework.workflows.orchestrations` | 1 |
| `HandoffBuilder` | `agent_framework.workflows.orchestrations` | 1 |
| `HandoffAgentUserRequest` | `agent_framework.workflows` | 1 |
| `MagenticBuilder` | `agent_framework.workflows.orchestrations` | 2 |
| `MagenticManagerBase` | `agent_framework.workflows.orchestrations` | 1 |
| `StandardMagenticManager` | `agent_framework.workflows.orchestrations` | 1 |
| `SequentialBuilder` | `agent_framework.workflows.orchestrations` | 1 |
| `WorkflowBuilder` | `agent_framework.workflows` | 3 |
| `Workflow` | `agent_framework.workflows` | 4 |
| `WorkflowExecutor` | `agent_framework.workflows` | 2 |
| `SubWorkflowRequestMessage` | `agent_framework.workflows` | 1 |
| `SubWorkflowResponseMessage` | `agent_framework.workflows` | 1 |
| `Edge` | `agent_framework.workflows` | 3 |
| `Executor` | `agent_framework.workflows` | 3 |
| `WorkflowContext` | `agent_framework.workflows` | 2 |
| `handler` | `agent_framework.workflows` | 2 |
| `WorkflowStatusEvent` | `agent_framework.workflows` | 1 |
| `WorkflowCheckpoint` | `agent_framework.workflows` | 2 |
| `ChatAgent` | `agent_framework.agents` | 2 |
| `ChatMessage` | `agent_framework.agents` | 1 |
| `Role` | `agent_framework.agents` | 1 |
| `CheckpointStorage` | `agent_framework.workflows` | 2 |
| `InMemoryCheckpointStorage` | `agent_framework.workflows` | 3 |
| `Context` | `agent_framework.agents` | 1 |
| `ContextProvider` | `agent_framework.agents` | 1 |
| `MemoryStorage` | `agent_framework.agents` | 1 |
| `AzureOpenAIResponsesClient` | `agent_framework.clients.azure`（需驗證） | 1 |

#### 逐檔案變更指令

**檔案 1: `builders/concurrent.py` (L83)**
```python
# Before:
from agent_framework import ConcurrentBuilder

# After:
from agent_framework.workflows.orchestrations import ConcurrentBuilder
```

**檔案 2: `builders/groupchat.py` (L83-87)**
```python
# Before:
from agent_framework import (GroupChatBuilder)

# After:
from agent_framework.workflows.orchestrations import (GroupChatBuilder)
```

**檔案 3: `builders/handoff.py` (L54-57)**
```python
# Before:
from agent_framework import (HandoffBuilder, HandoffAgentUserRequest)

# After:
from agent_framework.workflows.orchestrations import HandoffBuilder
from agent_framework.workflows import HandoffAgentUserRequest
```

**檔案 4: `builders/magentic.py` (L39-43)**
```python
# Before:
from agent_framework import (MagenticBuilder, MagenticManagerBase, StandardMagenticManager)

# After:
from agent_framework.workflows.orchestrations import (
    MagenticBuilder, MagenticManagerBase, StandardMagenticManager
)
```

**檔案 5: `builders/planning.py` (L31)**
```python
# Before:
from agent_framework import MagenticBuilder, Workflow

# After:
from agent_framework.workflows.orchestrations import MagenticBuilder
from agent_framework.workflows import Workflow
```

**檔案 6: `builders/nested_workflow.py` (L71)**
```python
# Before:
from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor

# After:
from agent_framework.workflows import WorkflowBuilder, Workflow, WorkflowExecutor
```

**檔案 7: `builders/workflow_executor.py` (L52-56)**
```python
# Before:
from agent_framework import (WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage)

# After:
from agent_framework.workflows import (
    WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage
)
```

**檔案 8: `builders/agent_executor.py` (L155-156)**
```python
# Before:
from agent_framework import ChatAgent, ChatMessage, Role
from agent_framework.azure import AzureOpenAIResponsesClient

# After:
from agent_framework.agents import ChatAgent, ChatMessage, Role
from agent_framework.clients.azure import AzureOpenAIResponsesClient  # 需驗證實際路徑
```

**檔案 9: `core/workflow.py` (L37)**
```python
# Before:
from agent_framework import Workflow, WorkflowBuilder, Edge, Executor

# After:
from agent_framework.workflows import Workflow, WorkflowBuilder, Edge, Executor
```

**檔案 10: `core/executor.py` (L38)**
```python
# Before:
from agent_framework import Executor, WorkflowContext, handler

# After:
from agent_framework.workflows import Executor, WorkflowContext, handler
```

**檔案 11: `core/execution.py` (L34)**
```python
# Before:
from agent_framework import ChatAgent, SequentialBuilder, Workflow

# After:
from agent_framework.agents import ChatAgent
from agent_framework.workflows.orchestrations import SequentialBuilder
from agent_framework.workflows import Workflow
```

**檔案 12: `core/edge.py` (L29)**
```python
# Before:
from agent_framework import Edge

# After:
from agent_framework.workflows import Edge
```

**檔案 13: `core/events.py` (L34)**
```python
# Before:
from agent_framework import WorkflowStatusEvent

# After:
from agent_framework.workflows import WorkflowStatusEvent
```

**檔案 14: `core/approval.py` (L39)**
```python
# Before:
from agent_framework import Executor, handler, WorkflowContext

# After:
from agent_framework.workflows import Executor, handler, WorkflowContext
```

**檔案 15: `core/approval_workflow.py` (L36)**
```python
# Before:
from agent_framework import Workflow, Edge

# After:
from agent_framework.workflows import Workflow, Edge
```

**檔案 16: `multiturn/adapter.py` (L27-31)**
```python
# Before:
from agent_framework import (CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint)

# After:
from agent_framework.workflows import (
    CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint
)
```

**檔案 17: `multiturn/checkpoint_storage.py` (L31)**
```python
# Before:
from agent_framework import CheckpointStorage, InMemoryCheckpointStorage

# After:
from agent_framework.workflows import CheckpointStorage, InMemoryCheckpointStorage
```

**檔案 18: `memory/base.py` (L25)**
```python
# Before:
from agent_framework import Context, ContextProvider

# After:
from agent_framework.agents import Context, ContextProvider
```

**檔案 19: `memory/base.py` (L169, lazy import)**
```python
# Before:
from agent_framework import MemoryStorage

# After:
from agent_framework.agents import MemoryStorage
```

**檔案 20: `checkpoint.py` (L102, lazy import)**
```python
# Before:
from agent_framework import WorkflowCheckpoint

# After:
from agent_framework.workflows import WorkflowCheckpoint
```

**檔案 21: `workflow.py` (L425, lazy import)**
```python
# Before:
from agent_framework import WorkflowBuilder

# After:
from agent_framework.workflows import WorkflowBuilder
```

**檔案 22: `infrastructure/storage/storage_factories.py` (L308)**
```python
# Before:
from agent_framework import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage

# After:
from agent_framework.workflows import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage
```

#### ACL 層特殊處理

**檔案 23-26: `acl/version_detector.py` 和 `acl/adapter.py`**

ACL 層使用 `import agent_framework` + `hasattr()` / `getattr()` 進行動態偵測。需更新為支援子模組路徑的偵測邏輯：

```python
# version_detector.py — 更新 API 可用性檢查
# Before:
hasattr(agent_framework, api_name)

# After — 需要擴充為子模組檢查:
def _check_api_availability(api_name: str) -> bool:
    """檢查 API 在頂層或子模組中是否可用"""
    if hasattr(agent_framework, api_name):
        return True
    # 嘗試子模組
    for submodule in ['agents', 'workflows', 'workflows.orchestrations', 'clients.azure']:
        try:
            mod = importlib.import_module(f'agent_framework.{submodule}')
            if hasattr(mod, api_name):
                return True
        except ImportError:
            continue
    return False
```

```python
# adapter.py — 更新動態類別載入
# Before:
cls = getattr(agent_framework, maf_class_name)

# After — 需要擴充為子模組搜索:
_SUBMODULE_MAP = {
    'ChatAgent': 'agent_framework.agents',
    'ConcurrentBuilder': 'agent_framework.workflows.orchestrations',
    'GroupChatBuilder': 'agent_framework.workflows.orchestrations',
    'Workflow': 'agent_framework.workflows',
    'WorkflowBuilder': 'agent_framework.workflows',
    'Edge': 'agent_framework.workflows',
    # ... 其餘映射
}

def _get_maf_class(class_name: str):
    if class_name in _SUBMODULE_MAP:
        mod = importlib.import_module(_SUBMODULE_MAP[class_name])
        return getattr(mod, class_name)
    return getattr(agent_framework, class_name)
```

### 3.2 其他 BC（LOW-MEDIUM）：潛在影響和驗證方式

| BC | 影響等級 | 驗證方式 | 預估工作量 |
|-----|---------|---------|-----------|
| BC-03: `display_name` 移除 | LOW | `grep -r "display_name" integrations/agent_framework/` — 確認無 dict/kwargs 傳遞 | 0.5 SP |
| BC-04: `context_providers` 單數化 | LOW | 驗證 `memory/base.py` 的 `ContextProvider` 類 API 是否變更 | 0.5 SP |
| BC-05: `source_executor_id` → `source` | LOW | 驗證 `core/edge.py` 是否透過參數傳遞此屬性 | 0.5 SP |
| BC-11: Provider state 範圍化 | MEDIUM | 執行 checkpoint 相關測試，驗證 `source_id` 預設值行為 | 1 SP |
| BC-15: Checkpoint 模型重構 | MEDIUM | 比較 `WorkflowCheckpoint` 新舊 API 差異，更新 `checkpoint.py` | 1 SP |
| BC-16: 標準化編排輸出 | MEDIUM | 驗證 GroupChat 輸出是否為 `list[ChatMessage]` 格式 | 0.5 SP |

---

## 4. 新功能採用決策

### 4.1 Phase A — 升級時同步啟用

#### P1: OpenTelemetry MCP 追蹤（2-3 SP）

**來源**: rc1 [#3780](https://github.com/microsoft/agent-framework/pull/3780) + rc3 [#4278](https://github.com/microsoft/agent-framework/pull/4278)

**價值**: 自動追蹤上下文傳播至所有 MCP 請求，端到端分散式追蹤，與 Azure Monitor / Jaeger / Zipkin 整合。

**啟用方式**: 僅需安裝 OpenTelemetry 依賴並配置 exporter，MAF 自動 instrument — **無需修改應用程式碼**。

**工作內容**:
- 1 SP: 在 `requirements.txt` 新增 `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`
- 1-2 SP: 在 `backend/src/core/` 新增 OTel 初始化配置，整合 Azure Monitor 或 Jaeger

**風險**: LOW — 純觀測功能，不影響業務邏輯。效能影響極小（非同步 span 匯出）。

#### P2: 背景回應 + Continuation Tokens（3-5 SP）

**來源**: b260210 [#3808](https://github.com/microsoft/agent-framework/pull/3808)

**價值**: 長時間 Agent 任務可暫停/恢復，避免 HTTP timeout，改善使用者體驗。

**工作內容**:
- 2 SP: 後端整合 `ContinuationToken` 到 `core/execution.py` 執行引擎
- 1-3 SP: 前端輪詢機制和 UI 調整（顯示背景任務狀態）

**風險**: LOW-MEDIUM — 可選功能，不影響現有同步流程。需前後端協調確保 token 正確傳遞。

### 4.2 Phase B — 升級後 1-2 Sprint 採用

#### P3: Agent Skills（5-8 SP）

**來源**: rc2，[Agent Skills 文件](https://learn.microsoft.com/en-us/agent-framework/agents/skills)

**價值**: 標準化 SKILL.md 格式封裝領域知識，漸進式揭示（Advertise → Load → Read Resources）對 context window 友好。

**工作內容**:
- 2 SP: 建立 `backend/skills/` 目錄，整合 `SkillsProvider` 作為 context provider
- 3-6 SP: 將 MCP Server 操作指南、企業政策等 3-5 個領域知識轉換為 SKILL.md

**風險**: LOW — 純附加功能，不修改現有程式碼。

#### P4: HITL 工具呼叫審批改進（5-8 SP）

**來源**: rc1 [#4054](https://github.com/microsoft/agent-framework/pull/4054)

**價值**: 官方修復所有 session/streaming 組合的審批流程，可簡化 IPA 自建的雙套 HITL 系統。

**工作內容**:
- 3 SP: 重構 `core/approval.py` 使用官方 tool approval API
- 2-5 SP: 整合 `orchestration/hitl/` 與 MAF 原生 HITL

**風險**: MEDIUM — 兩套 HITL 系統整合需仔細測試所有審批路徑。

### 4.3 Phase C — 延後評估

#### P5: 宣告式 YAML 工作流程（5-8 SP）

**來源**: b260114，套件 `agent-framework-declarative`

**策略**: 新工作流程優先使用 YAML 定義，**不遷移**現有 24 個 Builder。

**限制**: Python 的 `InvokeMcpTool` action 尚未支援（僅 C#）；GroupChat、Edge routing 無法用 YAML 表達。

#### P6: Claude SDK BaseAgent（8-30 SP）

**來源**: b260130，套件 `agent-framework-claude`

**策略**: 在 Adapter 層引入 `ClaudeAgent` 作為新的後端選項，逐步替代可替代組件（~40% 自建 SDK）。保留 `autonomous/`、`hybrid/`、`orchestrator/` 等獨有業務邏輯（~60%）。

**建議**: 在 Phase B 完成後，基於 rc4 實際使用經驗由架構委員會決定採用範圍。

### 4.4 不採用

#### 自主切換流程

**理由**: IPA 的 `hybrid/switching/`（12 檔案）是針對 MAF/Claude 混合架構的獨特設計（Complexity Trigger、Failure Trigger、Resource Trigger、User Trigger）。MAF 的 handoff 是代理間交接，**不是框架間切換** — 概念完全不同。IPA 的混合切換系統是獨特競爭優勢，MAF 無對應功能。

---

## 5. 分階段執行計劃

### 5.1 前置準備（Sprint N-1）

| # | 任務 | 負責人需求 | 驗證標準 | SP |
|---|------|-----------|---------|-----|
| 1 | 建立測試基線 | 1 人 | `pytest --tb=no -q > baseline.txt` 成功記錄 | 1 |
| 2 | 建立功能分支 `feature/maf-rc4-upgrade` | 1 人 | 分支建立並推送至 remote | 0 |
| 3 | 在隔離虛擬環境測試 `pip install agent-framework==1.0.0rc4` | 1 人 | 無依賴衝突 | 1 |
| 4 | 驗證新 import 路徑 | 1 人 | `python -c "from agent_framework.workflows.orchestrations import GroupChatBuilder"` 成功 | 0.5 |
| 5 | 更新 reference repo 至 rc4 tag | 1 人 | `reference/agent-framework/` 同步最新 | 1 |
| 6 | 閱讀 [MS Learn 遷移指南](https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes) | 全員 | 確認理解所有 BC | 0 |
| | **小計** | | | **3.5** |

### 5.2 Sprint N：機械性遷移（~13 SP）

**目標**: 修復所有 import 路徑和版本約束，使代碼在 rc4 下可載入。

| # | 任務 | 影響檔案 | 變更類型 | SP | 驗證標準 |
|---|------|---------|---------|-----|---------|
| 1 | BC-07: Builder adapter import 遷移 | 7 builder 檔案 | import 路徑 | 3 | 所有 builder 可 import |
| 2 | BC-07: Core 模組 import 遷移 | 6 core 檔案 | import 路徑 | 2 | 所有 core 模組可 import |
| 3 | BC-07: Multiturn/Memory/Checkpoint import 遷移 | 5 檔案 | import 路徑 | 1.5 | 所有模組可 import |
| 4 | BC-07: Infrastructure import 遷移 | 1 檔案 | import 路徑 | 0.5 | `storage_factories.py` 可 import |
| 5 | BC-07: ACL 動態引用更新 | 2 ACL 檔案 | 邏輯變更 | 2 | `version_detector.py` 偵測 rc4 |
| 6 | 更新 `requirements.txt` 版本約束 | 1 檔案 | 版本約束 | 0.5 | `pip install -r requirements.txt` 成功 |
| 7 | 單元測試修復（import 路徑相關） | ~15 測試檔案 | mock/patch 路徑 | 2 | Tier 1 測試全部通過 |
| 8 | BC-03/04/05 人工驗證 | 3-5 檔案 | 潛在修改 | 1.5 | 驗證完成，記錄結果 |
| | **Sprint N 小計** | **~21 檔案** | | **13** | |

**Sprint N 驗證閘門**:
- `pip install agent-framework==1.0.0rc4` 成功
- `python -c "from agent_framework.workflows.orchestrations import GroupChatBuilder"` 成功
- `python scripts/verify_official_api_usage.py` — 所有檢查通過（可能需更新腳本）
- `pytest tests/unit/integrations/agent_framework/ -v` — >90% 通過

### 5.3 Sprint N+1：語意性遷移 + 新功能 Phase A（~15 SP）

**目標**: 處理行為變更、驗證 checkpoint 相容性、啟用 OTel 和背景回應。

| # | 任務 | 影響檔案 | 變更類型 | SP | 驗證標準 |
|---|------|---------|---------|-----|---------|
| 1 | BC-11: Provider state 範圍化驗證 | checkpoint 相關 | 行為驗證 | 1 | checkpoint 讀寫正常 |
| 2 | BC-15: Checkpoint 模型適配 | `checkpoint.py`, multiturn/ | API 適配 | 2 | checkpoint 測試通過 |
| 3 | BC-16: 編排輸出格式驗證 | GroupChat 相關 | 行為驗證 | 1 | 輸出格式正確 |
| 4 | Phase A-P1: OpenTelemetry MCP 追蹤 | requirements.txt, core/ | 新功能 | 3 | 追蹤 span 可見 |
| 5 | Phase A-P2: 背景回應 + Continuation Tokens | execution.py, API 路由 | 新功能 | 5 | 長任務可暫停/恢復 |
| 6 | 整合測試 + 回歸驗證 | 全域 | 測試 | 2 | 完整測試套件通過 |
| 7 | `CLAUDE.md` 文件更新 | 文件 | 文件 | 1 | 反映 rc4 API |
| | **Sprint N+1 小計** | | | **15** | |

**Sprint N+1 驗證閘門**:
- `pytest tests/unit/ -v` — >95% 通過
- `pytest tests/integration/ -v` — >90% 通過
- `pytest tests/e2e/ -v` — >85% 通過
- 手動 E2E 驗證：Agent 建立/執行/GroupChat/Handoff/Magentic 正常

### 5.4 Sprint N+2：新功能 Phase B + 回歸驗證（~13-16 SP）

| # | 任務 | SP | 驗證標準 |
|---|------|-----|---------|
| 1 | Phase B-P3: Agent Skills 基礎架構 | 2 | SkillsProvider 整合 |
| 2 | Phase B-P3: 轉換 3-5 個領域知識為 SKILL.md | 3-6 | Skills 可正確載入 |
| 3 | Phase B-P4: HITL 工具呼叫審批重構 | 5-8 | 審批流程測試通過 |
| 4 | 效能基線比較 | 1 | 無顯著退化（<10%） |
| 5 | 合併準備和代碼審查 | 2 | review 通過 |
| | **Sprint N+2 小計** | **13-19** | |

**合併至 main 閘門**:
- 完整測試套件通過率 >= 基線通過率
- 手動 E2E 驗證通過
- 效能基線比較無顯著退化
- 至少 1 人 code review
- 回滾測試已驗證

### 5.5 Sprint N+3+：新功能 Phase C（可選）

| # | 任務 | SP | 時機 | 前提 |
|---|------|-----|------|------|
| 1 | 宣告式 YAML 工作流程基礎架構 + 範例 | 5-8 | Sprint N+3 | Phase B 完成 |
| 2 | Claude SDK BaseAgent 評估 + PoC | 8-12 | Sprint N+4 | 架構委員會決策 |
| 3 | Claude SDK BaseAgent 全面整合（如決定） | 20-30 | Sprint N+5-7 | PoC 通過 |

---

## 6. 測試策略

### 6.1 測試執行優先級（5 階段）

```
Phase 1 (Day 1): Import 驗證
  → python -c "from agent_framework.workflows.orchestrations import GroupChatBuilder"
  → python -c "from agent_framework.agents import ChatAgent"
  → python -c "from agent_framework.workflows import Workflow, Edge, Executor"
  → 確認所有 28 個唯一 MAF 類別的新 import 路徑可用

Phase 2 (Day 1-2): Adapter 單元測試
  → pytest tests/unit/integrations/agent_framework/ -v
  → 修復所有 import 路徑相關失敗

Phase 3 (Day 2-3): Checkpoint/Storage 測試
  → pytest tests/unit/infrastructure/checkpoint/ -v
  → pytest tests/unit/infrastructure/storage/ -v

Phase 4 (Day 3-4): Integration 測試
  → pytest tests/integration/ -v -k "agent_framework or execution"

Phase 5 (Day 4-5): E2E 測試
  → pytest tests/e2e/ -v
  → 完整回歸驗證
```

### 6.2 預期失敗的測試（Tier 1-3）

#### Tier 1 — 幾乎確定失敗（直接引用變更的 import 路徑）

| 測試檔案 | 失敗原因 | 影響的 BC | 修復方式 |
|---------|---------|---------|---------|
| `tests/unit/integrations/agent_framework/builders/test_planning_llm_injection.py` | `planning.py` import 路徑變更導致 patch 失敗 | BC-07 | 更新 patch 路徑 |
| `tests/unit/integrations/agent_framework/builders/test_concurrent_builder_adapter.py` | ConcurrentBuilder import 路徑 | BC-07 | 更新 mock |
| `tests/unit/integrations/agent_framework/builders/test_groupchat_builder_adapter.py` | GroupChatBuilder import 路徑 | BC-07 | 更新 mock |
| `tests/unit/integrations/agent_framework/builders/test_magentic_builder_adapter.py` | MagenticBuilder import 路徑 | BC-07 | 更新 mock |
| `tests/unit/integrations/agent_framework/builders/test_handoff_builder_adapter.py` | HandoffBuilder import 路徑 | BC-07 | 更新 mock |
| `tests/unit/integrations/agent_framework/builders/test_nested_workflow_adapter.py` | WorkflowBuilder import 路徑 | BC-07 | 更新 mock |

#### Tier 2 — 很可能失敗（間接依賴變更的類型或行為）

| 測試檔案 | 失敗原因 | 影響的 BC |
|---------|---------|---------|
| `tests/unit/infrastructure/checkpoint/adapters/test_agent_framework_adapter.py` | Checkpoint 行為變更 | BC-15 |
| `tests/unit/infrastructure/checkpoint/adapters/test_multi_provider_integration.py` | Provider state 範圍化 | BC-11 |
| `tests/unit/infrastructure/storage/test_storage_factories_sprint120.py` | `create_agent_framework_checkpoint_storage` 工廠 | BC-15 |
| `tests/unit/integrations/agent_framework/assistant/test_exceptions.py` | 例外處理類變更 | BC-09 |

#### Tier 3 — 可能受影響（E2E/Integration）

| 測試檔案 | 失敗原因 |
|---------|---------|
| `tests/e2e/test_concurrent_workflow.py` | ConcurrentBuilder 端到端流程 |
| `tests/e2e/test_groupchat_workflow.py` | GroupChatBuilder 端到端流程 |
| `tests/e2e/test_agent_execution.py` | Agent 執行流程 |
| `tests/e2e/test_ai_autonomous_decision.py` | Planning adapter 流程 |
| `tests/integration/test_execution_adapter_e2e.py` | 執行 adapter 整合 |

### 6.3 新增測試需求

| 測試類型 | 內容 | SP |
|---------|------|-----|
| Import 驗證測試 | 驗證所有 28 個 MAF 類別可從新路徑 import | 0.5 |
| ACL 版本偵測測試 | 驗證 `version_detector.py` 正確偵測 rc4 | 0.5 |
| ACL 動態載入測試 | 驗證 `adapter.py` 從子模組正確載入類別 | 0.5 |
| Checkpoint 相容性測試 | 驗證新舊 checkpoint 資料的相容性 | 1 |
| OTel 追蹤驗證測試 | 驗證 MCP 請求產生正確的追蹤 span | 1 |
| 背景回應測試 | 驗證 ContinuationToken 的暫停/恢復流程 | 1 |

### 6.4 驗收標準

| 階段 | 驗收標準 | 通過門檻 |
|------|---------|---------|
| Sprint N 完成 | Adapter 單元測試 | >90% 通過 |
| Sprint N+1 完成 | 完整單元測試 | >95% 通過 |
| Sprint N+1 完成 | Integration 測試 | >90% 通過 |
| Sprint N+1 完成 | E2E 測試 | >85% 通過 |
| 合併至 main | 完整測試套件 | >= 基線通過率 |
| 合併至 main | 效能測試 | 退化 <10% |

---

## 7. 風險緩解

### 7.1 回滾策略

#### 方案 A: Git 分支回滾（推薦，<5 分鐘）

```bash
# 所有升級工作在 feature/maf-rc4-upgrade 分支進行
git checkout main

# 如已合併:
git revert <merge-commit-hash>
```

**前提**: 所有升級變更在獨立功能分支，不在升級同時進行其他功能開發。

#### 方案 B: requirements.txt 版本回退（<10 分鐘）

```bash
# 回退版本約束（必須配合 Git 回滾使用）
# requirements.txt: agent-framework>=1.0.0b260114,<1.0.0b260116
pip install agent-framework==1.0.0b260114
```

#### 方案 C: 條件 Import 相容層（緊急過渡，不推薦長期使用）

```python
try:
    from agent_framework.workflows.orchestrations import GroupChatBuilder  # rc4+
except ImportError:
    from agent_framework import GroupChatBuilder  # b260114
```

#### 回滾驗證清單

```
□ requirements.txt 已還原為舊版本約束
□ 所有 builder adapter import 路徑已還原
□ pip install -r requirements.txt 成功
□ pytest tests/unit/integrations/agent_framework/ 全部通過
□ pytest tests/e2e/ 全部通過
□ 手動驗證 Agent 建立和執行流程
□ 手動驗證 GroupChat/Handoff/Magentic 工作流程
```

### 7.2 漸進式切換方案

#### 功能分支策略

```
main
  └── feature/maf-rc4-upgrade          # 主升級分支
        ├── maf-upgrade/phase1-imports  # 階段 1: import 遷移
        ├── maf-upgrade/phase2-semantics # 階段 2: 語意遷移 + Phase A 功能
        └── maf-upgrade/phase3-features # 階段 3: Phase B 功能（可選）
```

每個子分支完成後 merge 回 `feature/maf-rc4-upgrade`，全部完成後合併回 `main`。

#### 回滾觸發條件

| 觸發條件 | 回滾方案 | 時間窗口 |
|---------|---------|---------|
| 升級後 >30% 單元測試失敗 | 方案 A（分支回滾） | 立即 |
| 發現 rc4 有未記錄的 BC | 方案 A + 回報 GitHub Issue | 24 小時內 |
| 生產環境 Agent 執行異常 | 方案 B + 方案 A | 1 小時內 |
| 部分 Builder 不可用但核心正常 | 方案 C（相容層）暫時過渡 | 視影響範圍 |

### 7.3 風險矩陣（概率 × 影響）

#### 升級風險

| # | 風險項 | 概率 | 影響 | 風險等級 | 緩解措施 |
|---|--------|------|------|---------|---------|
| R1 | BC-07 import 路徑變更導致 18 檔載入失敗 | **100%** | HIGH | **HIGH** | 機械性搜索替換，已有完整清單 |
| R2 | ACL 動態引用失效 | **90%** | MEDIUM | **MEDIUM** | 更新 hasattr/getattr 邏輯 |
| R3 | BC-11/15 Checkpoint 行為異常 | **50%** | MEDIUM | **MEDIUM** | 隔離測試驗證 |
| R4 | BC-03 `display_name`/`context_providers` 潛在傳遞 | **30%** | LOW | **LOW** | 人工驗證 kwargs |
| R5 | 未記錄的破壞性變更 | **20%** | HIGH | **MEDIUM** | 充分 E2E 測試覆蓋 |
| R6 | pip 依賴衝突 | **5%** | LOW | **LOW** | 虛擬環境隔離測試 |
| R7 | 升級後效能退化 | **10%** | MEDIUM | **LOW** | 效能測試基線比較 |

#### 不升級風險

| # | 風險項 | 概率 | 影響 | 風險等級 |
|---|--------|------|------|---------|
| NR1 | GA 後跳級遷移成本倍增 | **95%** | HIGH | **CRITICAL** |
| NR2 | 錯過 Claude SDK BaseAgent 整合機會 | **100%** | MEDIUM | **HIGH** |
| NR3 | 繼續承受已知 bug | **100%** | LOW | **MEDIUM** |
| NR4 | 安全漏洞未修補 | **30%** | HIGH | **MEDIUM** |

**風險比較結論**: 升級風險（短期痛苦 ~34 SP） **<** 不升級風險（長期累積 ~60+ SP）。

---

## 8. 與 V8 架構問題的協調

### 8.1 升級是否影響 Architecture Review Board 的修復路線圖

**結論: 不影響，反而有輕微正面效果。**

| V8 問題類別 | 升級交互 | 說明 |
|------------|---------|------|
| CR-01: InMemory 存儲（25+ 模組） | **不影響** | InMemory 問題在 IPA 自訂層（AG-UI、Swarm、A2A），非 MAF 層 |
| CR-02: 4 個 Mock API 假數據 | **不影響** | Mock 問題在 IPA API 層 |
| CR-03: SQL Injection | **不影響** | `postgres_store.py` 是 IPA 自訂代碼 |
| CR-04: MCP 權限 log-only | **不影響** | MCP 安全模型是 IPA 配置問題 |
| CR-05: Shell/SSH 無控制 | **不影響** | IPA MCP Server 層 |
| CR-06: RabbitMQ 空殼 | **不影響** | IPA 基礎設施層 |
| HI-01~HI-10: 安全/前端 | **不影響** | 全部 IPA 層問題 |
| 架構健康度 52/100 | **不影響** | Adapter Pattern 已隔離 MAF 依賴 |
| InMemoryCheckpointStorage | **輕微正面** | BC-11 標準化 `source_id`，可能自動修復 C-01 的部分問題 |
| Bug: UTC 時區/MCP 重複 | **正面** | 升級自動修復 2-4 個已知 bug |

### 8.2 建議的執行順序（先升級還是先修 V8 問題）

**建議: 先升級 MAF，後修 V8 問題。**

理由：
1. **MAF 升級不觸及 V8 問題的檔案** — 兩者的影響範圍完全不重疊（MAF 在 `integrations/agent_framework/`，V8 問題在 API/Domain/Infrastructure 層）
2. **升級自動修復 2-4 個 bug** — 減少 V8 問題清單
3. **V8 修復可能依賴最新 MAF API** — 先升級確保修復時使用最新 API
4. **時間敏感性** — MAF 正朝 GA 邁進，升級有時間壓力；V8 問題為技術債，壓力較低
5. **併行可行** — 如團隊容量允許，MAF 升級（`integrations/agent_framework/`）和 V8 修復（API/Domain/Infrastructure）可在不同分支併行進行，因影響範圍不重疊

---

## 9. Claude SDK 同步升級考量

### 9.1 anthropic 依賴修復（requirements.txt）

**問題**: `anthropic==0.84.0` 已在本地安裝但**未列於 `requirements.txt`**。這是部署風險。

**修復**（0.5 SP）:
```python
# requirements.txt — 新增：
anthropic>=0.84.0
```

### 9.2 Extended Thinking header 更新

**問題**: `backend/src/integrations/claude_sdk/client.py:260` 使用已棄用的 beta header：
```python
# 目前（已過時）:
extra_headers = {"anthropic-beta": "extended-thinking-2024-10"}
```

**修復**（1 SP）:
```python
# Claude Opus 4.6 — 不需要 header（GA 功能）
# Claude 4.x 其他模型 — 使用新 header:
extra_headers = {"anthropic-beta": "interleaved-thinking-2025-05-14"}
```

### 9.3 模型 ID 更新

**問題**: `client.py:38` 寫死舊模型 ID：
```python
# 目前:
model: str = "claude-sonnet-4-20250514"
```

**修復**（0.5 SP）:
```python
# 更新為最新模型:
model: str = "claude-sonnet-4-6-20260217"

# 或更好的做法 — 從設定系統讀取:
model: str = get_settings().claude_model_id
```

最新模型 ID 參考:
| 模型 | ID |
|------|-----|
| Claude Sonnet 4.6 | `claude-sonnet-4-6-20260217` |
| Claude Opus 4.6 | `claude-opus-4-6-20260205` |
| Claude Opus 4.5 | `claude-opus-4-5-20251124` |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` |

### 9.4 與 MAF Claude SDK BaseAgent 的關係

MAF rc4 提供的 `agent-framework-claude` 套件包含 `ClaudeAgent`（BaseAgent 實作），與 IPA 自建的 47 檔 `claude_sdk/` 模組存在大量功能重疊（~40%）。

**短期策略（與 MAF 升級同步）**:
- 僅修復 9.1-9.3 的立即問題（`anthropic` 依賴聲明、header、模型 ID）
- 不進行 Claude SDK 模組的結構重組
- 工作量: ~2 SP

**中期策略（Phase B 完成後評估）**:
- 安裝 `claude-agent-sdk>=0.1.48`，以替換 `hooks/` 模組作為 PoC
- 評估官方 SDK 與自建系統的整合可行性
- 工作量: ~8 SP

**長期策略（Phase C，架構委員會決策後）**:
- 採用混合方案：替換重複的基礎設施（hooks、tools、MCP ~40%），保留獨有業務邏輯（autonomous、hybrid、orchestrator ~60%）
- 工作量: ~56 小時（2-3 Sprint）

---

## 10. Go/No-Go 檢查清單

### 升級前檢查

| # | 條件 | 狀態 | 驗證方式 |
|---|------|------|---------|
| 1 | 功能分支 `feature/maf-rc4-upgrade` 已建立 | □ 待完成 | `git branch -a` |
| 2 | 現有測試通過率基線已記錄 | □ 待完成 | `pytest --tb=no -q > baseline.txt` |
| 3 | 虛擬環境已隔離 | □ 待完成 | 新 venv 安裝 rc4 |
| 4 | `pip install agent-framework==1.0.0rc4` 無依賴衝突 | □ 待完成 | pip install 成功 |
| 5 | 新 import 路徑可用 | □ 待完成 | Python import 測試 |
| 6 | MS Learn 遷移指南已讀 | □ 待完成 | 全員確認 |
| 7 | 團隊已知會升級計劃 | □ 待完成 | 會議紀錄 |
| 8 | 2 個 Sprint 容量已確保 | □ 待完成 | Sprint 規劃確認 |

### Sprint N 完成閘門

| # | 條件 | 狀態 | 驗證方式 |
|---|------|------|---------|
| 1 | 所有 23 條 import 已更新 | □ 待完成 | `grep -r "from agent_framework import" backend/src/` 無結果 |
| 2 | ACL 層動態引用已更新 | □ 待完成 | `version_detector.py` 偵測 rc4 |
| 3 | `requirements.txt` 已更新 | □ 待完成 | `agent-framework>=1.0.0rc4,<2.0.0` |
| 4 | `verify_official_api_usage.py` 通過 | □ 待完成 | 5 項檢查全部通過 |
| 5 | Adapter 單元測試 >90% 通過 | □ 待完成 | pytest 報告 |

### Sprint N+1 完成閘門

| # | 條件 | 狀態 | 驗證方式 |
|---|------|------|---------|
| 1 | 完整單元測試 >95% 通過 | □ 待完成 | pytest 報告 |
| 2 | Integration 測試 >90% 通過 | □ 待完成 | pytest 報告 |
| 3 | E2E 測試 >85% 通過 | □ 待完成 | pytest 報告 |
| 4 | Checkpoint 相容性驗證通過 | □ 待完成 | 手動 + 自動測試 |
| 5 | OTel 追蹤 span 可見（如啟用） | □ 待完成 | Jaeger/Monitor 驗證 |

### 合併至 main 閘門

| # | 條件 | 狀態 | 驗證方式 |
|---|------|------|---------|
| 1 | 完整測試套件 >= 基線通過率 | □ 待完成 | 與 baseline.txt 比較 |
| 2 | 手動 E2E 驗證通過 | □ 待完成 | Agent/GroupChat/Handoff/Magentic |
| 3 | 效能無顯著退化（<10%） | □ 待完成 | 效能測試報告 |
| 4 | 代碼審查通過 | □ 待完成 | 至少 1 人 review |
| 5 | 回滾測試已驗證 | □ 待完成 | `git revert` 可恢復 |
| 6 | `CLAUDE.md` 和文件已更新 | □ 待完成 | 反映 rc4 API |

---

## 附錄

### A. 受影響檔案完整對照表

| # | 檔案路徑（相對 `backend/src/`） | BC | 影響等級 | 變更類型 |
|---|-------------------------------|-----|---------|---------|
| 1 | `integrations/agent_framework/builders/concurrent.py` | BC-07 | CRITICAL | import 路徑 |
| 2 | `integrations/agent_framework/builders/groupchat.py` | BC-07 | CRITICAL | import 路徑 |
| 3 | `integrations/agent_framework/builders/handoff.py` | BC-07 | CRITICAL | import 路徑 |
| 4 | `integrations/agent_framework/builders/magentic.py` | BC-07 | CRITICAL | import 路徑 |
| 5 | `integrations/agent_framework/builders/planning.py` | BC-07 | CRITICAL | import 路徑 |
| 6 | `integrations/agent_framework/builders/nested_workflow.py` | BC-07 | CRITICAL | import 路徑 |
| 7 | `integrations/agent_framework/builders/workflow_executor.py` | BC-07 | CRITICAL | import 路徑 |
| 8 | `integrations/agent_framework/builders/agent_executor.py` | BC-07 | HIGH | import 路徑 + 驗證 |
| 9 | `integrations/agent_framework/core/workflow.py` | BC-07 | HIGH | import 路徑 |
| 10 | `integrations/agent_framework/core/executor.py` | BC-07 | HIGH | import 路徑 |
| 11 | `integrations/agent_framework/core/execution.py` | BC-07 | HIGH | import 路徑 |
| 12 | `integrations/agent_framework/core/edge.py` | BC-07 | MEDIUM | import 路徑 |
| 13 | `integrations/agent_framework/core/events.py` | BC-07 | MEDIUM | import 路徑 |
| 14 | `integrations/agent_framework/core/approval.py` | BC-07 | HIGH | import 路徑 |
| 15 | `integrations/agent_framework/core/approval_workflow.py` | BC-07 | MEDIUM | import 路徑 |
| 16 | `integrations/agent_framework/multiturn/adapter.py` | BC-07, BC-15 | MEDIUM | import 路徑 + 行為驗證 |
| 17 | `integrations/agent_framework/multiturn/checkpoint_storage.py` | BC-07, BC-11 | MEDIUM | import 路徑 + 行為驗證 |
| 18 | `integrations/agent_framework/memory/base.py` | BC-07 | MEDIUM | import 路徑（2 處） |
| 19 | `integrations/agent_framework/checkpoint.py` | BC-07, BC-15 | MEDIUM | import 路徑 + 行為驗證 |
| 20 | `integrations/agent_framework/workflow.py` | BC-07 | MEDIUM | import 路徑 |
| 21 | `infrastructure/storage/storage_factories.py` | BC-07 | LOW | import 路徑 |
| 22 | `integrations/agent_framework/acl/version_detector.py` | BC-07 | HIGH | 動態引用邏輯更新 |
| 23 | `integrations/agent_framework/acl/adapter.py` | BC-07 | HIGH | 動態類別載入更新 |
| 24 | `integrations/claude_sdk/client.py` | Claude SDK | MEDIUM | header + 模型 ID |
| 25 | `backend/requirements.txt` | 版本 | CRITICAL | 版本約束更新 |

### B. 新功能 API 參考

| 功能 | 套件 | 關鍵 API | 文件 |
|------|------|---------|------|
| OpenTelemetry MCP 追蹤 | `agent-framework[otel]` | 自動 instrument | [Observability](https://learn.microsoft.com/en-us/agent-framework/tutorials/agents/enable-observability) |
| 背景回應 | `agent-framework` | `ContinuationToken`, `background` option | PR [#3808](https://github.com/microsoft/agent-framework/pull/3808) |
| Agent Skills | `agent-framework` | `SkillsProvider`, `SKILL.md` format | [Agent Skills](https://learn.microsoft.com/en-us/agent-framework/agents/skills) |
| HITL 審批 | `agent-framework` | Tool approval API | PR [#4054](https://github.com/microsoft/agent-framework/pull/4054) |
| Claude BaseAgent | `agent-framework-claude` | `ClaudeAgent` | PR [#3653](https://github.com/microsoft/agent-framework/pull/3653) |
| YAML 工作流程 | `agent-framework-declarative` | `WorkflowFactory` | [Declarative Workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/declarative) |

### C. 相關文件索引

| 文件 | 路徑 | 用途 |
|------|------|------|
| 版本差異分析 | `sdk-version-gap/MAF-Version-Gap-Analysis.md` | 18 個 BC 完整清單 |
| 完整使用掃描 | `sdk-version-gap/MAF-Usage-Scan-Complete.md` | 23 import、28 類別、逐條影響分析 |
| 風險評估 | `sdk-version-gap/MAF-Upgrade-Risk-Assessment.md` | 依賴、V8 交互、測試、回滾 |
| 新功能採用分析 | `sdk-version-gap/MAF-New-Features-Adoption-Analysis.md` | 7 功能、3 批次策略 |
| Claude SDK 差異 | `sdk-version-gap/Claude-SDK-Version-Gap-Analysis.md` | anthropic SDK + claude-agent-sdk |
| V8 架構分析 | `full-codebase-analysis/MAF-Claude-Hybrid-Architecture-V8.md` | 11 層架構、62 issues |
| V8 功能驗證 | `full-codebase-analysis/MAF-Features-Architecture-Mapping-V8.md` | 70+ 功能驗證 |
| MS Learn 遷移指南 | [Python 2026 重大變更](https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes) | 官方遷移參考 |
| MAF Builder CLAUDE.md | `integrations/agent_framework/CLAUDE.md` | 官方 import 模式和規範 |

---

*Report generated: 2026-03-15*
*整合分析師: Architecture Integration Agent*
*基礎數據: MAF Version Gap Analysis + Usage Scan Complete + Upgrade Risk Assessment + New Features Adoption Analysis + Claude SDK Version Gap Analysis + V8 Full Codebase Analysis*
