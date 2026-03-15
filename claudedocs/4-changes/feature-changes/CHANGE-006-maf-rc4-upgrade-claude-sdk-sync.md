# CHANGE-006: MAF 1.0.0rc4 升級 + Claude SDK 同步修復 — 完整執行手冊

---

## 第一部分：概覽

### Summary

本變更將 IPA Platform 的 Microsoft Agent Framework (MAF) 從 `1.0.0b260114` 升級至 `1.0.0rc4`，跨越 9 個版本、約 2 個月的演進差距。升級涉及 18 項破壞性變更（BC），其中僅 BC-07（命名空間遷移）為唯一 CRITICAL 影響，涉及 18 個檔案中的 23 條 import 語句。同時修復 Claude SDK 的 3 個立即問題（缺少依賴宣告、已棄用 header、過時模型 ID），並採用 Phase A 新功能（OpenTelemetry MCP 追蹤、背景回應 + Continuation Tokens）。

| 屬性 | 值 |
|------|-----|
| **變更日期** | 2026-03-15（規劃）→ Sprint N 執行 |
| **Sprint / Phase** | Phase 35: SDK Upgrade & Modernization |
| **類型** | Framework Upgrade + Feature Enhancement |
| **狀態** | 🚧 規劃完成，待執行 |
| **預估工作量** | ~34 Story Points（2-3 個 Sprint） |

### 變更原因

**為什麼必須升級**:

| 因素 | 現在升級（rc4） | 延遲至 GA 後升級 |
|------|----------------|-----------------|
| 累積 BC 數量 | 18 項（僅 1 項 CRITICAL） | 預估 25-35 項（更多重構） |
| 估算工作量 | ~34 SP（2-3 Sprint） | ~60-80 SP（4-6 Sprint） |
| API 穩定性 | RC 階段，API 已趨穩定 | GA 後可能有最終重大重組 |
| 新功能可用性 | OTel 追蹤、背景回應、Agent Skills | 相同，但錯過 2+ 個月的早期整合優勢 |
| Bug 修復 | 立即獲得 UTC 時區、MCP 重複註冊等修復 | 繼續承受已知 bug |
| 安全漏洞 | 獲得最新安全修復 | 30% 概率暴露於未修補漏洞 |

**結論**: 越早升級成本越低。每延遲一個版本，累積的遷移成本約增加 ~5 SP。

### 版本資訊

| 項目 | 目前版本 | 目標版本 |
|------|---------|---------|
| Microsoft Agent Framework | `1.0.0b260114` | `1.0.0rc4` |
| `anthropic` Python SDK | `0.84.0`（已安裝但未宣告於 requirements.txt） | `0.84.0`（補宣告） |
| Claude 預設模型 ID | `claude-sonnet-4-20250514` | `claude-sonnet-4-6-20260217` |
| Extended Thinking header | `extended-thinking-2024-10` | `interleaved-thinking-2025-05-14` |

### 影響範圍統計

| 指標 | 數量 |
|------|------|
| 受影響 .py 檔案數 | **18**（+ 4 個 ACL 動態引用） |
| 需修改的 import 語句 | **23** |
| 引入的唯一 MAF 類別 | **28** |
| 配置檔案變更 | **1**（requirements.txt） |
| Claude SDK 修復檔案 | **2**（requirements.txt, client.py） |
| 不受影響的 .py 檔案數 | **900+**（佔總量 98%） |
| 影響集中度 | **95%** 在 `integrations/agent_framework/` 內 |

---

## 第二部分：前置準備（Pre-requisites）

所有命令均假設工作目錄為 `C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project`。

### 步驟 1：建立測試基線

```bash
cd backend
pytest --tb=no -q > test_baseline.txt 2>&1
```

記錄目前通過率，作為升級後的比較基準。

### 步驟 2：建立功能分支

```bash
git checkout -b feature/maf-rc4-upgrade
git push -u origin feature/maf-rc4-upgrade
```

### 步驟 3：在隔離虛擬環境測試 rc4 安裝

```bash
python -m venv .venv-rc4-test
.venv-rc4-test/Scripts/activate
pip install agent-framework==1.0.0rc4
python -c "from agent_framework.workflows.orchestrations import GroupChatBuilder; print('OK')"
python -c "from agent_framework.agents import ChatAgent; print('OK')"
python -c "from agent_framework.workflows import Workflow, Edge, Executor; print('OK')"
deactivate
```

### 步驟 4：更新 reference repo

```bash
cd reference/agent-framework
git fetch --all --tags
git checkout python-1.0.0rc4
cd ../..
```

### 步驟 5：驗證新 import 路徑

在測試虛擬環境中執行以下驗證，確認所有 28 個唯一 MAF 類別可從新路徑 import：

```bash
python -c "
from agent_framework.workflows.orchestrations import ConcurrentBuilder, GroupChatBuilder, HandoffBuilder, MagenticBuilder, MagenticManagerBase, StandardMagenticManager, SequentialBuilder
from agent_framework.workflows import Workflow, WorkflowBuilder, WorkflowExecutor, Edge, Executor, WorkflowContext, handler, WorkflowStatusEvent, WorkflowCheckpoint, CheckpointStorage, InMemoryCheckpointStorage, SubWorkflowRequestMessage, SubWorkflowResponseMessage, HandoffAgentUserRequest
from agent_framework.agents import ChatAgent, ChatMessage, Role, Context, ContextProvider, MemoryStorage
print('All 28 classes imported successfully')
"
```

### 步驟 6：確認前提條件清單

| # | 條件 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 1 | 功能分支已建立 | `git branch -a` 顯示 `feature/maf-rc4-upgrade` | □ |
| 2 | 測試基線已記錄 | `test_baseline.txt` 存在 | □ |
| 3 | rc4 安裝無依賴衝突 | `pip install agent-framework==1.0.0rc4` 成功 | □ |
| 4 | 新 import 路徑可用 | 步驟 5 的 Python import 測試成功 | □ |
| 5 | reference repo 已更新 | `reference/agent-framework/` 同步至 rc4 | □ |
| 6 | 團隊已知會升級計劃 | 會議紀錄 | □ |
| 7 | 2 個 Sprint 容量已確保 | Sprint 規劃確認 | □ |

---

## 第三部分：18 個 Breaking Changes 完整清單

### BC-01: `create_agent` 更名為 `as_agent`

- **PR**: [#3249](https://github.com/microsoft/agent-framework/pull/3249)
- **版本**: `1.0.0b260116`
- **舊 API**: `client.create_agent()`
- **新 API**: `client.as_agent()`
- **IPA 影響**: **NONE** — IPA 的 `create_agent` 是自定義方法（`builders/agent_executor.py:262`），非 MAF API 呼叫
- **必要變更**: 無。僅需人工驗證確認無衝突。

### BC-02: `AgentRunResponse` 更名為 `AgentResponse`

- **PR**: [#3207](https://github.com/microsoft/agent-framework/pull/3207)
- **版本**: `1.0.0b260116`
- **舊 API**: `from agent_framework import AgentRunResponse, AgentRunResponseUpdate`
- **新 API**: `from agent_framework import AgentResponse, AgentResponseUpdate`
- **IPA 影響**: **NONE** — IPA 的 `AgentRunResponse` 是自定義 Pydantic model（`domain/agents/schemas.py:125`），與 MAF 同名但不同源
- **必要變更**: 無。

### BC-03: `display_name` 移除 + `context_providers` 單數化 + `middleware` 列表化

- **PR**: [#3139](https://github.com/microsoft/agent-framework/pull/3139)
- **版本**: `1.0.0b260114`
- **變更內容**:
  1. `display_name` 參數從 agent 中移除
  2. `context_providers`（複數）→ `context_provider`（單數）
  3. `middleware` 現在必須為清單
  4. `AggregateContextProvider` 已移除
- **IPA 影響**: **LOW** — 搜索未發現直接使用。需人工驗證 builder adapter 內部是否透過 dict/kwargs 傳遞
- **必要變更**: 人工驗證 `grep -r "display_name" backend/src/integrations/agent_framework/`

### BC-04: `context_providers` 更名為 `context_provider`（單數）

- **PR**: [#3139](https://github.com/microsoft/agent-framework/pull/3139)（同 BC-03）
- **IPA 影響**: **NONE** — 搜索未發現 `context_providers` 的直接使用
- **必要變更**: 無。但 `memory/base.py:25` import 了 `ContextProvider`，如果此類別本身 API 有變則需注意。

### BC-05: `source_executor_id` 更名為 `source`

- **PR**: [#3166](https://github.com/microsoft/agent-framework/pull/3166)
- **版本**: `1.0.0b260116`
- **IPA 影響**: **NONE** — IPA 使用自定義屬性名（`builders/edge_routing.py:142`），非 MAF 屬性
- **必要變更**: 無。但需驗證 `core/edge.py` 是否透過參數傳遞此屬性。

### BC-06: Exception 類別重命名

- **PR**: [#4082](https://github.com/microsoft/agent-framework/pull/4082)
- **版本**: `1.0.0rc1`
- **舊 API**: `ServiceException`, `ServiceInitializationError`, `ServiceResponseException`, `AgentExecutionException`, `AgentInvocationError`, `AgentInitializationError`
- **新 API**: `AgentFrameworkException` 體系
- **IPA 影響**: **NONE** — 搜索未發現任何舊例外類別引用
- **必要變更**: 無。

### BC-07: 命名空間遷移（頂層 → 子模組）【CRITICAL】

- **版本**: `1.0.0b260210`
- **變更**: 所有類別從 `agent_framework` 頂層移至子模組（`agent_framework.agents`, `agent_framework.workflows`, `agent_framework.workflows.orchestrations`）
- **IPA 影響**: **CRITICAL** — 所有 23 條活躍 import 語句都從頂層 `agent_framework` import，全部需要遷移
- **必要變更**: 見第四部分「逐檔案變更指令表」

**遷移規則映射**:

| 原始頂層 import | 新子模組路徑 |
|----------------|-------------|
| `ConcurrentBuilder` | `agent_framework.workflows.orchestrations` |
| `GroupChatBuilder` | `agent_framework.workflows.orchestrations` |
| `HandoffBuilder` | `agent_framework.workflows.orchestrations` |
| `MagenticBuilder` | `agent_framework.workflows.orchestrations` |
| `MagenticManagerBase` | `agent_framework.workflows.orchestrations` |
| `StandardMagenticManager` | `agent_framework.workflows.orchestrations` |
| `SequentialBuilder` | `agent_framework.workflows.orchestrations` |
| `WorkflowBuilder` | `agent_framework.workflows` |
| `Workflow` | `agent_framework.workflows` |
| `WorkflowExecutor` | `agent_framework.workflows` |
| `SubWorkflowRequestMessage` | `agent_framework.workflows` |
| `SubWorkflowResponseMessage` | `agent_framework.workflows` |
| `HandoffAgentUserRequest` | `agent_framework.workflows` |
| `Edge` | `agent_framework.workflows` |
| `Executor` | `agent_framework.workflows` |
| `WorkflowContext` | `agent_framework.workflows` |
| `handler` | `agent_framework.workflows` |
| `WorkflowStatusEvent` | `agent_framework.workflows` |
| `WorkflowCheckpoint` | `agent_framework.workflows` |
| `CheckpointStorage` | `agent_framework.workflows` |
| `InMemoryCheckpointStorage` | `agent_framework.workflows` |
| `ChatAgent` | `agent_framework.agents` |
| `ChatMessage` | `agent_framework.agents` |
| `Role` | `agent_framework.agents` |
| `Context` | `agent_framework.agents` |
| `ContextProvider` | `agent_framework.agents` |
| `MemoryStorage` | `agent_framework.agents` |
| `AzureOpenAIResponsesClient` | `agent_framework.clients.azure`（需驗證） |

### BC-08: `AFBaseSettings` 移除（pydantic-settings 依賴移除）

- **PR**: [#3843](https://github.com/microsoft/agent-framework/pull/3843), [#4032](https://github.com/microsoft/agent-framework/pull/4032)
- **版本**: `1.0.0rc1`
- **IPA 影響**: **NONE** — IPA 不使用 MAF 設定系統。IPA 的 `pydantic-settings` 是獨立安裝（`core/config.py:11`）
- **必要變更**: 無。

### BC-09: `AggregateContextProvider` 移除

- **版本**: `1.0.0b260114`
- **IPA 影響**: **NONE** — 搜索未發現使用
- **必要變更**: 無。

### BC-10: `FunctionTool` 泛型移除

- **PR**: [#3907](https://github.com/microsoft/agent-framework/pull/3907)
- **版本**: `1.0.0rc1`
- **舊 API**: `FunctionTool[Any]`
- **新 API**: `FunctionTool`
- **IPA 影響**: **NONE** — 搜索未發現 `FunctionTool[` 使用
- **必要變更**: 無。

### BC-11: Provider 狀態依 `source_id` 範圍化

- **PR**: [#3995](https://github.com/microsoft/agent-framework/pull/3995)
- **版本**: `1.0.0rc1`
- **變更**: Provider hooks 接收範圍化的 state dict；`InMemoryHistoryProvider` 預設 `source_id` 從 `"memory"` 改為 `"in_memory"`
- **IPA 影響**: **MEDIUM** — `checkpoint.py` 和 `multiturn/` 使用 `InMemoryCheckpointStorage`
- **必要變更**: 執行 checkpoint 相關測試驗證 `source_id` 預設值行為。預估 1 SP。

### BC-12: Entra auth token 變更

- **PR**: [#4088](https://github.com/microsoft/agent-framework/pull/4088)
- **版本**: `1.0.0rc1`
- **舊 API**: `ad_token_provider`
- **新 API**: `credential` 參數
- **IPA 影響**: **NONE** — 搜索未發現 `ad_token_provider` 使用
- **必要變更**: 無。

### BC-13: `InMemoryHistoryProvider` 移除

- **版本**: `1.0.0rc1`
- **IPA 影響**: **NONE** — 搜索未發現使用
- **必要變更**: 無。

### BC-14: `WorkflowOutputEvent` 移除

- **版本**: `1.0.0rc1`
- **IPA 影響**: **NONE** — 搜索未發現使用
- **必要變更**: 無。

### BC-15: Checkpoint 模型和存儲行為重構

- **PR**: [#3744](https://github.com/microsoft/agent-framework/pull/3744)
- **版本**: `1.0.0rc1`
- **IPA 影響**: **MEDIUM** — `checkpoint.py` 和 `multiturn/adapter.py` 使用 `WorkflowCheckpoint`
- **必要變更**: 比較新舊 `WorkflowCheckpoint` API 差異，更新 `checkpoint.py`。預估 1 SP。

### BC-16: 標準化編排輸出為 `list[ChatMessage]`

- **PR**: [#2291](https://github.com/microsoft/agent-framework/pull/2291)
- **IPA 影響**: **LOW-MEDIUM** — 需驗證 GroupChat 輸出處理是否受影響
- **必要變更**: 驗證 GroupChat 輸出是否為 `list[ChatMessage]` 格式。預估 0.5 SP。

### BC-17: Azure Functions 套件的 Schema 變更

- **PR**: [#2151](https://github.com/microsoft/agent-framework/pull/2151)
- **IPA 影響**: **NONE** — IPA 不使用 Azure Functions
- **必要變更**: 無。

### BC-18: HITL 工具呼叫審批行為變更

- **PR**: [#2569](https://github.com/microsoft/agent-framework/pull/2569)
- **版本**: `1.0.0rc1`
- **IPA 影響**: **LOW** — 新增功能，非必要遷移。`magentic.py` 可在 Phase B 採用
- **必要變更**: Phase A 無需變更。Phase B 可選採用。

---

## 第四部分：逐檔案變更指令表

所有檔案路徑相對於 `backend/src/`。完整路徑前綴為 `C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\backend\src\`。

### 4.1 Builder Adapter 檔案（7 個檔案，10 條 import）

| # | 檔案路徑 | 行號 | 目前程式碼 | 改為 | 對應 BC | 複雜度 |
|---|----------|------|-----------|------|---------|--------|
| 1 | `integrations/agent_framework/builders/concurrent.py` | 83 | `from agent_framework import ConcurrentBuilder` | `from agent_framework.workflows.orchestrations import ConcurrentBuilder` | BC-07 | Low |
| 2 | `integrations/agent_framework/builders/groupchat.py` | 83-87 | `from agent_framework import (GroupChatBuilder)` | `from agent_framework.workflows.orchestrations import (GroupChatBuilder)` | BC-07 | Low |
| 3 | `integrations/agent_framework/builders/handoff.py` | 54-57 | `from agent_framework import (HandoffBuilder, HandoffAgentUserRequest)` | `from agent_framework.workflows.orchestrations import HandoffBuilder`<br>`from agent_framework.workflows import HandoffAgentUserRequest` | BC-07 | Low |
| 4 | `integrations/agent_framework/builders/magentic.py` | 39-43 | `from agent_framework import (MagenticBuilder, MagenticManagerBase, StandardMagenticManager)` | `from agent_framework.workflows.orchestrations import (`<br>`    MagenticBuilder, MagenticManagerBase, StandardMagenticManager`<br>`)` | BC-07 | Low |
| 5 | `integrations/agent_framework/builders/planning.py` | 31 | `from agent_framework import MagenticBuilder, Workflow` | `from agent_framework.workflows.orchestrations import MagenticBuilder`<br>`from agent_framework.workflows import Workflow` | BC-07 | Medium |
| 6 | `integrations/agent_framework/builders/nested_workflow.py` | 71 | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` | `from agent_framework.workflows import WorkflowBuilder, Workflow, WorkflowExecutor` | BC-07 | Low |
| 7 | `integrations/agent_framework/builders/workflow_executor.py` | 52-56 | `from agent_framework import (WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage)` | `from agent_framework.workflows import (`<br>`    WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage`<br>`)` | BC-07 | Low |
| 8 | `integrations/agent_framework/builders/agent_executor.py` | 155 | `from agent_framework import ChatAgent, ChatMessage, Role` | `from agent_framework.agents import ChatAgent, ChatMessage, Role` | BC-07 | Low |
| 9 | `integrations/agent_framework/builders/agent_executor.py` | 156 | `from agent_framework.azure import AzureOpenAIResponsesClient` | `from agent_framework.clients.azure import AzureOpenAIResponsesClient`（需驗證實際路徑） | BC-07 | Low |

### 4.2 Core 模組檔案（6 個檔案，8 條 import）

| # | 檔案路徑 | 行號 | 目前程式碼 | 改為 | 對應 BC | 複雜度 |
|---|----------|------|-----------|------|---------|--------|
| 10 | `integrations/agent_framework/core/workflow.py` | 37 | `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor` | `from agent_framework.workflows import Workflow, WorkflowBuilder, Edge, Executor` | BC-07 | Low |
| 11 | `integrations/agent_framework/core/executor.py` | 38 | `from agent_framework import Executor, WorkflowContext, handler` | `from agent_framework.workflows import Executor, WorkflowContext, handler` | BC-07 | Low |
| 12 | `integrations/agent_framework/core/execution.py` | 34 | `from agent_framework import ChatAgent, SequentialBuilder, Workflow` | `from agent_framework.agents import ChatAgent`<br>`from agent_framework.workflows.orchestrations import SequentialBuilder`<br>`from agent_framework.workflows import Workflow` | BC-07 | Medium |
| 13 | `integrations/agent_framework/core/edge.py` | 29 | `from agent_framework import Edge` | `from agent_framework.workflows import Edge` | BC-07 | Low |
| 14 | `integrations/agent_framework/core/events.py` | 34 | `from agent_framework import WorkflowStatusEvent` | `from agent_framework.workflows import WorkflowStatusEvent` | BC-07 | Low |
| 15 | `integrations/agent_framework/core/approval.py` | 39 | `from agent_framework import Executor, handler, WorkflowContext` | `from agent_framework.workflows import Executor, handler, WorkflowContext` | BC-07 | Low |
| 16 | `integrations/agent_framework/core/approval_workflow.py` | 36 | `from agent_framework import Workflow, Edge` | `from agent_framework.workflows import Workflow, Edge` | BC-07 | Low |

### 4.3 Multiturn / Memory / Checkpoint 檔案（5 個檔案，5 條 import）

| # | 檔案路徑 | 行號 | 目前程式碼 | 改為 | 對應 BC | 複雜度 |
|---|----------|------|-----------|------|---------|--------|
| 17 | `integrations/agent_framework/multiturn/adapter.py` | 27-31 | `from agent_framework import (CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint)` | `from agent_framework.workflows import (`<br>`    CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint`<br>`)` | BC-07, BC-15 | Medium |
| 18 | `integrations/agent_framework/multiturn/checkpoint_storage.py` | 31 | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage` | `from agent_framework.workflows import CheckpointStorage, InMemoryCheckpointStorage` | BC-07, BC-11 | Low |
| 19 | `integrations/agent_framework/memory/base.py` | 25 | `from agent_framework import Context, ContextProvider` | `from agent_framework.agents import Context, ContextProvider` | BC-07 | Low |
| 20 | `integrations/agent_framework/memory/base.py` | 169 | `from agent_framework import MemoryStorage`（lazy import） | `from agent_framework.agents import MemoryStorage` | BC-07 | Low |
| 21 | `integrations/agent_framework/checkpoint.py` | 102 | `from agent_framework import WorkflowCheckpoint`（lazy import） | `from agent_framework.workflows import WorkflowCheckpoint` | BC-07, BC-15 | Low |

### 4.4 根目錄 + Infrastructure 檔案（2 個檔案，2 條 import）

| # | 檔案路徑 | 行號 | 目前程式碼 | 改為 | 對應 BC | 複雜度 |
|---|----------|------|-----------|------|---------|--------|
| 22 | `integrations/agent_framework/workflow.py` | 425 | `from agent_framework import WorkflowBuilder`（lazy import） | `from agent_framework.workflows import WorkflowBuilder` | BC-07 | Low |
| 23 | `infrastructure/storage/storage_factories.py` | 308 | `from agent_framework import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage` | `from agent_framework.workflows import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage` | BC-07 | Low |

### 4.5 ACL 層特殊處理（2 個檔案，4 個動態引用）

ACL 層使用 `import agent_framework` + `hasattr()` / `getattr()` 進行動態偵測，不能簡單替換 import 路徑，需要更新邏輯。

**檔案 A: `integrations/agent_framework/acl/version_detector.py`**

行號 85, 135, 165 — 需更新 API 可用性檢查以支援子模組路徑：

```python
# Before（行 135 附近）:
hasattr(agent_framework, api_name)

# After — 擴充為子模組檢查:
import importlib

def _check_api_availability(api_name: str) -> bool:
    """檢查 API 在頂層或子模組中是否可用"""
    if hasattr(agent_framework, api_name):
        return True
    for submodule in ['agents', 'workflows', 'workflows.orchestrations', 'clients.azure']:
        try:
            mod = importlib.import_module(f'agent_framework.{submodule}')
            if hasattr(mod, api_name):
                return True
        except ImportError:
            continue
    return False
```

**檔案 B: `integrations/agent_framework/acl/adapter.py`**

行號 139 — 需更新動態類別載入以支援子模組搜索：

```python
# Before:
cls = getattr(agent_framework, maf_class_name)

# After — 擴充為子模組映射:
_SUBMODULE_MAP = {
    'ChatAgent': 'agent_framework.agents',
    'ChatMessage': 'agent_framework.agents',
    'Role': 'agent_framework.agents',
    'Context': 'agent_framework.agents',
    'ContextProvider': 'agent_framework.agents',
    'MemoryStorage': 'agent_framework.agents',
    'ConcurrentBuilder': 'agent_framework.workflows.orchestrations',
    'GroupChatBuilder': 'agent_framework.workflows.orchestrations',
    'HandoffBuilder': 'agent_framework.workflows.orchestrations',
    'MagenticBuilder': 'agent_framework.workflows.orchestrations',
    'MagenticManagerBase': 'agent_framework.workflows.orchestrations',
    'StandardMagenticManager': 'agent_framework.workflows.orchestrations',
    'SequentialBuilder': 'agent_framework.workflows.orchestrations',
    'Workflow': 'agent_framework.workflows',
    'WorkflowBuilder': 'agent_framework.workflows',
    'WorkflowExecutor': 'agent_framework.workflows',
    'Edge': 'agent_framework.workflows',
    'Executor': 'agent_framework.workflows',
    'WorkflowContext': 'agent_framework.workflows',
    'handler': 'agent_framework.workflows',
    'WorkflowStatusEvent': 'agent_framework.workflows',
    'WorkflowCheckpoint': 'agent_framework.workflows',
    'CheckpointStorage': 'agent_framework.workflows',
    'InMemoryCheckpointStorage': 'agent_framework.workflows',
    'SubWorkflowRequestMessage': 'agent_framework.workflows',
    'SubWorkflowResponseMessage': 'agent_framework.workflows',
    'HandoffAgentUserRequest': 'agent_framework.workflows',
}

def _get_maf_class(class_name: str):
    if class_name in _SUBMODULE_MAP:
        mod = importlib.import_module(_SUBMODULE_MAP[class_name])
        return getattr(mod, class_name)
    return getattr(agent_framework, class_name)
```

### 4.6 requirements.txt 版本約束更新

**檔案**: `backend/requirements.txt`

| 行號 | 目前程式碼 | 改為 |
|------|-----------|------|
| 20 | `agent-framework>=1.0.0b260114,<2.0.0` | `agent-framework>=1.0.0rc4,<2.0.0` |

### 4.7 不受影響的確認

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

---

## 第五部分：Claude SDK 同步修復

### 修復 1: `anthropic` 依賴宣告缺失（CRITICAL）

**問題**: `anthropic==0.84.0` 已在本地安裝但**未列於 `requirements.txt`**。這是部署風險 — 在 CI/CD 或新環境部署時會缺少此依賴。

**檔案**: `backend/requirements.txt`

```python
# 新增（在 requirements.txt 適當位置）:
anthropic>=0.84.0
```

### 修復 2: Extended Thinking header 已棄用（HIGH）

**問題**: `backend/src/integrations/claude_sdk/client.py:260` 使用已過時的 beta header。

**檔案**: `backend/src/integrations/claude_sdk/client.py`
**行號**: 260

```python
# Before:
extra_headers = {"anthropic-beta": "extended-thinking-2024-10"}

# After:
# Claude Opus 4.6 不需要 header（GA 功能）
# 其他 Claude 4.x 模型使用新 header:
extra_headers = {"anthropic-beta": "interleaved-thinking-2025-05-14"}
```

### 修復 3: 預設模型 ID 過時（HIGH）

**問題**: `backend/src/integrations/claude_sdk/client.py:38` 寫死舊模型 ID，落後 4 個世代。

**檔案**: `backend/src/integrations/claude_sdk/client.py`
**行號**: 38

```python
# Before:
model: str = "claude-sonnet-4-20250514"

# After:
model: str = "claude-sonnet-4-6-20260217"
```

**最新模型 ID 參考**:

| 模型 | ID |
|------|-----|
| Claude Sonnet 4.6 | `claude-sonnet-4-6-20260217` |
| Claude Opus 4.6 | `claude-opus-4-6-20260205` |
| Claude Opus 4.5 | `claude-opus-4-5-20251124` |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` |

---

## 第六部分：新功能採用計劃

### Phase A — 升級同步啟用（5-8 SP）

#### P1: OpenTelemetry MCP 追蹤（2-3 SP）

**來源**: rc1 [#3780](https://github.com/microsoft/agent-framework/pull/3780) + rc3 [#4278](https://github.com/microsoft/agent-framework/pull/4278)

**價值**: 自動追蹤上下文傳播至所有 MCP 請求，端到端分散式追蹤，與 Azure Monitor / Jaeger / Zipkin 整合。

**啟用方式**: 僅需安裝 OpenTelemetry 依賴並配置 exporter，MAF 自動 instrument — **無需修改應用程式碼**。

**具體步驟**:

1. 在 `backend/requirements.txt` 新增：
   ```
   opentelemetry-api>=1.22.0
   opentelemetry-sdk>=1.22.0
   opentelemetry-exporter-otlp>=1.22.0
   ```

2. 在 `backend/src/core/` 新增 OTel 初始化配置：
   ```python
   # backend/src/core/telemetry.py
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

   def init_telemetry():
       provider = TracerProvider()
       provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
       trace.set_tracer_provider(provider)
   ```

3. 在應用啟動時呼叫 `init_telemetry()`

**風險**: LOW — 純觀測功能，不影響業務邏輯。效能影響極小（非同步 span 匯出）。

#### P2: 背景回應 + Continuation Tokens（3-5 SP）

**來源**: b260210 [#3808](https://github.com/microsoft/agent-framework/pull/3808)

**價值**: 長時間 Agent 任務可暫停/恢復，避免 HTTP timeout，改善使用者體驗。

**具體步驟**:

1. 後端整合 `ContinuationToken` 到 `core/execution.py` 執行引擎（2 SP）
2. 前端輪詢機制和 UI 調整（顯示背景任務狀態）（1-3 SP）

**風險**: LOW-MEDIUM — 可選功能，不影響現有同步流程。需前後端協調確保 token 正確傳遞。

### Phase B — 升級後 1-2 Sprint 採用（10-16 SP）

#### P3: Agent Skills（5-8 SP）

**來源**: rc2，[Agent Skills 文件](https://learn.microsoft.com/en-us/agent-framework/agents/skills)

**價值**: 標準化 SKILL.md 格式封裝領域知識，漸進式揭示（Advertise → Load → Read Resources）對 context window 友好。

**具體步驟**:

1. 建立 `backend/skills/` 目錄，整合 `SkillsProvider` 作為 context provider（2 SP）
2. 將 MCP Server 操作指南、企業政策等 3-5 個領域知識轉換為 SKILL.md（3-6 SP）

**風險**: LOW — 純附加功能，不修改現有程式碼。

#### P4: HITL 工具呼叫審批改進（5-8 SP）

**來源**: rc1 [#4054](https://github.com/microsoft/agent-framework/pull/4054)

**價值**: 官方修復所有 session/streaming 組合的審批流程，可簡化 IPA 自建的雙套 HITL 系統。

**具體步驟**:

1. 重構 `core/approval.py` 使用官方 tool approval API（3 SP）
2. 整合 `orchestration/hitl/` 與 MAF 原生 HITL（2-5 SP）

**風險**: MEDIUM — 兩套 HITL 系統整合需仔細測試所有審批路徑。

### Phase C — 延後評估（Sprint 110+）

#### P5: 宣告式 YAML 工作流程（5-8 SP）

**來源**: b260114，套件 `agent-framework-declarative`

**策略**: 新工作流程優先使用 YAML 定義，**不遷移**現有 24 個 Builder。

**限制**: Python 的 `InvokeMcpTool` action 尚未支援（僅 C#）；GroupChat、Edge routing 無法用 YAML 表達。

#### P6: Claude SDK BaseAgent（8-30 SP）

**來源**: b260130，套件 `agent-framework-claude`

**策略**: 在 Adapter 層引入 `ClaudeAgent` 作為新的後端選項，逐步替代可替代組件（~40% 自建 SDK）。保留 `autonomous/`、`hybrid/`、`orchestrator/` 等獨有業務邏輯（~60%）。

**建議**: 在 Phase B 完成後，基於 rc4 實際使用經驗由架構委員會決定採用範圍。

### 不採用

#### 自主切換流程

**理由**: IPA 的 `hybrid/switching/`（12 檔案）是針對 MAF/Claude 混合架構的獨特設計（Complexity Trigger、Failure Trigger、Resource Trigger、User Trigger）。MAF 的 handoff 是代理間交接，**不是框架間切換** — 概念完全不同。IPA 的混合切換系統是獨特競爭優勢，MAF 無對應功能。

---

## 第七部分：Sprint 執行計劃

### Sprint N-1：前置準備（3.5 SP）

| # | User Story | SP | 驗收標準 |
|---|-----------|-----|---------|
| 1 | 建立測試基線 | 1 | `pytest --tb=no -q > baseline.txt` 成功記錄 |
| 2 | 建立功能分支 | 0 | 分支建立並推送至 remote |
| 3 | 在隔離虛擬環境測試 rc4 安裝 | 1 | `pip install agent-framework==1.0.0rc4` 無依賴衝突 |
| 4 | 驗證新 import 路徑 | 0.5 | 28 個 MAF 類別的新 import 路徑全部成功 |
| 5 | 更新 reference repo 至 rc4 tag | 1 | `reference/agent-framework/` 同步最新 |

### Sprint N：機械性遷移（~13 SP）

**目標**: 修復所有 import 路徑和版本約束，使代碼在 rc4 下可載入。

| # | User Story | 影響檔案 | SP | 驗收標準 |
|---|-----------|---------|-----|---------|
| 1 | BC-07: Builder adapter import 遷移（#1-#9） | 7 builder 檔案 | 3 | 所有 builder 可 import |
| 2 | BC-07: Core 模組 import 遷移（#10-#16） | 6 core 檔案 | 2 | 所有 core 模組可 import |
| 3 | BC-07: Multiturn/Memory/Checkpoint import 遷移（#17-#21） | 5 檔案 | 1.5 | 所有模組可 import |
| 4 | BC-07: Infrastructure import 遷移（#22-#23） | 2 檔案 | 0.5 | `storage_factories.py` 可 import |
| 5 | BC-07: ACL 動態引用更新（4.5 節） | 2 ACL 檔案 | 2 | `version_detector.py` 偵測 rc4 |
| 6 | 更新 `requirements.txt` 版本約束 | 1 檔案 | 0.5 | `pip install -r requirements.txt` 成功 |
| 7 | 單元測試修復（import 路徑相關） | ~15 測試檔案 | 2 | Tier 1 測試全部通過 |
| 8 | BC-03/04/05 人工驗證 | 3-5 檔案 | 1.5 | 驗證完成，記錄結果 |

**Sprint N 驗證閘門**:
- [ ] `pip install agent-framework==1.0.0rc4` 成功
- [ ] `python -c "from agent_framework.workflows.orchestrations import GroupChatBuilder"` 成功
- [ ] `python scripts/verify_official_api_usage.py` — 所有檢查通過（可能需更新腳本）
- [ ] `pytest tests/unit/integrations/agent_framework/ -v` — >90% 通過

### Sprint N+1：語意性遷移 + 新功能 Phase A（~15 SP）

**目標**: 處理行為變更、驗證 checkpoint 相容性、啟用 OTel 和背景回應。

| # | User Story | SP | 驗收標準 |
|---|-----------|-----|---------|
| 1 | BC-11: Provider state 範圍化驗證 | 1 | checkpoint 讀寫正常 |
| 2 | BC-15: Checkpoint 模型適配 | 2 | checkpoint 測試通過 |
| 3 | BC-16: 編排輸出格式驗證 | 1 | GroupChat 輸出格式正確 |
| 4 | Claude SDK 修復（第五部分 3 個修復） | 2 | header/model ID 更新，anthropic 宣告 |
| 5 | Phase A-P1: OpenTelemetry MCP 追蹤 | 3 | 追蹤 span 可見 |
| 6 | Phase A-P2: 背景回應 + Continuation Tokens | 4 | 長任務可暫停/恢復 |
| 7 | 整合測試 + 回歸驗證 | 2 | 完整測試套件通過 |

**Sprint N+1 驗證閘門**:
- [ ] `pytest tests/unit/ -v` — >95% 通過
- [ ] `pytest tests/integration/ -v` — >90% 通過
- [ ] `pytest tests/e2e/ -v` — >85% 通過
- [ ] 手動 E2E 驗證：Agent 建立/執行/GroupChat/Handoff/Magentic 正常

### Sprint N+2：新功能 Phase B + 合併準備（~13-19 SP）

| # | User Story | SP | 驗收標準 |
|---|-----------|-----|---------|
| 1 | Phase B-P3: Agent Skills 基礎架構 | 2 | SkillsProvider 整合 |
| 2 | Phase B-P3: 轉換 3-5 個領域知識為 SKILL.md | 3-6 | Skills 可正確載入 |
| 3 | Phase B-P4: HITL 工具呼叫審批重構 | 5-8 | 審批流程測試通過 |
| 4 | 效能基線比較 | 1 | 無顯著退化（<10%） |
| 5 | 合併準備和代碼審查 | 2 | review 通過 |

**合併至 main 閘門**:
- [ ] 完整測試套件通過率 >= 基線通過率
- [ ] 手動 E2E 驗證通過
- [ ] 效能基線比較無顯著退化
- [ ] 至少 1 人 code review
- [ ] 回滾測試已驗證

### 任務依賴關係

```
前置準備（Sprint N-1）
    │
    ▼
Sprint N: 機械性遷移
    ├── Story 1-4: import 遷移（可並行）
    ├── Story 5: ACL 更新（依賴 Story 1-4 的驗證）
    ├── Story 6: requirements.txt（獨立）
    ├── Story 7: 測試修復（依賴 Story 1-6）
    └── Story 8: 人工驗證（獨立）
    │
    ▼
Sprint N+1: 語意遷移 + Phase A
    ├── Story 1-3: BC 驗證（依賴 Sprint N 完成）
    ├── Story 4: Claude SDK 修復（獨立，可與 Sprint N 並行）
    ├── Story 5-6: 新功能（依賴 Story 1-3）
    └── Story 7: 整合測試（依賴全部）
    │
    ▼
Sprint N+2: Phase B + 合併
    ├── Story 1-2: Agent Skills（獨立）
    ├── Story 3: HITL 重構（依賴 Sprint N+1 的 HITL 驗證）
    └── Story 4-5: 合併準備（依賴全部）
```

---

## 第八部分：測試策略

### 5 階段測試計劃

#### Phase 1: Import 驗證（Day 1）

```bash
# 確認所有 28 個唯一 MAF 類別的新 import 路徑可用
python -c "from agent_framework.workflows.orchestrations import ConcurrentBuilder; print('OK')"
python -c "from agent_framework.workflows.orchestrations import GroupChatBuilder; print('OK')"
python -c "from agent_framework.workflows.orchestrations import HandoffBuilder; print('OK')"
python -c "from agent_framework.workflows.orchestrations import MagenticBuilder, MagenticManagerBase, StandardMagenticManager; print('OK')"
python -c "from agent_framework.workflows.orchestrations import SequentialBuilder; print('OK')"
python -c "from agent_framework.workflows import Workflow, WorkflowBuilder, WorkflowExecutor, Edge, Executor, WorkflowContext, handler; print('OK')"
python -c "from agent_framework.workflows import WorkflowStatusEvent, WorkflowCheckpoint, CheckpointStorage, InMemoryCheckpointStorage; print('OK')"
python -c "from agent_framework.workflows import SubWorkflowRequestMessage, SubWorkflowResponseMessage, HandoffAgentUserRequest; print('OK')"
python -c "from agent_framework.agents import ChatAgent, ChatMessage, Role, Context, ContextProvider, MemoryStorage; print('OK')"
```

#### Phase 2: Adapter 單元測試（Day 1-2）

```bash
pytest tests/unit/integrations/agent_framework/ -v
```

修復所有 import 路徑相關失敗。

#### Phase 3: Checkpoint/Storage 測試（Day 2-3）

```bash
pytest tests/unit/infrastructure/checkpoint/ -v
pytest tests/unit/infrastructure/storage/ -v
```

#### Phase 4: Integration 測試（Day 3-4）

```bash
pytest tests/integration/ -v -k "agent_framework or execution"
```

#### Phase 5: E2E 測試（Day 4-5）

```bash
pytest tests/e2e/ -v
```

### 預期失敗的測試清單

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

### 驗收標準

| 階段 | 驗收標準 | 通過門檻 |
|------|---------|---------|
| Sprint N 完成 | Adapter 單元測試 | >90% 通過 |
| Sprint N+1 完成 | 完整單元測試 | >95% 通過 |
| Sprint N+1 完成 | Integration 測試 | >90% 通過 |
| Sprint N+1 完成 | E2E 測試 | >85% 通過 |
| 合併至 main | 完整測試套件 | >= 基線通過率 |
| 合併至 main | 效能測試 | 退化 <10% |

---

## 第九部分：回滾策略

### 方案 A: Git 分支回滾（推薦，<5 分鐘）

```bash
# 所有升級工作在 feature/maf-rc4-upgrade 分支進行
# 回滾只需切回 main:
git checkout main

# 如已合併至 main:
git revert <merge-commit-hash>
```

**前提**: 所有升級變更在獨立功能分支，不在升級同時進行其他功能開發。

### 方案 B: requirements.txt 版本回退（<10 分鐘）

```bash
# 回退版本約束（必須配合 Git 回滾使用）
# requirements.txt: agent-framework>=1.0.0b260114,<1.0.0b260116
pip install agent-framework==1.0.0b260114
```

### 方案 C: 條件 Import 相容層（緊急過渡，不推薦長期使用）

```python
try:
    from agent_framework.workflows.orchestrations import GroupChatBuilder  # rc4+
except ImportError:
    from agent_framework import GroupChatBuilder  # b260114
```

### 不同失敗場景的處理方式

| 觸發條件 | 回滾方案 | 時間窗口 |
|---------|---------|---------|
| 升級後 >30% 單元測試失敗 | 方案 A（分支回滾） | 立即 |
| 發現 rc4 有未記錄的 BC | 方案 A + 回報 GitHub Issue | 24 小時內 |
| 生產環境 Agent 執行異常 | 方案 B + 方案 A | 1 小時內 |
| 部分 Builder 不可用但核心正常 | 方案 C（相容層）暫時過渡 | 視影響範圍 |

### 回滾驗證清單

```
□ requirements.txt 已還原為舊版本約束
□ 所有 builder adapter import 路徑已還原
□ pip install -r requirements.txt 成功
□ pytest tests/unit/integrations/agent_framework/ 全部通過
□ pytest tests/e2e/ 全部通過
□ 手動驗證 Agent 建立和執行流程
□ 手動驗證 GroupChat/Handoff/Magentic 工作流程
```

---

## 第十部分：風險矩陣

### 升級風險（概率 x 影響）

| # | 風險項 | 概率 | 影響 | 風險等級 | 緩解措施 |
|---|--------|------|------|---------|---------|
| R1 | BC-07 import 路徑變更導致 18 檔載入失敗 | **100%** | HIGH | **HIGH** | 機械性搜索替換，已有完整清單（第四部分） |
| R2 | ACL 動態引用失效 | **90%** | MEDIUM | **MEDIUM** | 更新 hasattr/getattr 邏輯（4.5 節） |
| R3 | BC-11/15 Checkpoint 行為異常 | **50%** | MEDIUM | **MEDIUM** | 隔離測試驗證 |
| R4 | BC-03 `display_name`/`context_providers` 潛在傳遞 | **30%** | LOW | **LOW** | 人工驗證 kwargs |
| R5 | 未記錄的破壞性變更 | **20%** | HIGH | **MEDIUM** | 充分 E2E 測試覆蓋 |
| R6 | pip 依賴衝突 | **5%** | LOW | **LOW** | 虛擬環境隔離測試（步驟 3） |
| R7 | 升級後效能退化 | **10%** | MEDIUM | **LOW** | 效能測試基線比較 |

### 不升級風險

| # | 風險項 | 概率 | 影響 | 風險等級 |
|---|--------|------|------|---------|
| NR1 | GA 後跳級遷移成本倍增（~60+ SP） | **95%** | HIGH | **CRITICAL** |
| NR2 | 錯過 Claude SDK BaseAgent 整合機會 | **100%** | MEDIUM | **HIGH** |
| NR3 | 繼續承受已知 bug（UTC 時區、MCP 重複） | **100%** | LOW | **MEDIUM** |
| NR4 | 安全漏洞未修補 | **30%** | HIGH | **MEDIUM** |

**風險比較結論**: 升級風險（短期痛苦 ~34 SP） **<** 不升級風險（長期累積 ~60+ SP）。

---

## 第十一部分：與 V8 架構問題的協調

### 升級是否影響 Architecture Review Board 的修復路線圖

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

### 建議的執行順序

**建議: 先升級 MAF，後修 V8 問題。**

理由：
1. **影響範圍不重疊** — MAF 在 `integrations/agent_framework/`，V8 問題在 API/Domain/Infrastructure 層
2. **升級自動修復 2-4 個 bug** — 減少 V8 問題清單
3. **V8 修復可能依賴最新 MAF API** — 先升級確保修復時使用最新 API
4. **時間敏感性** — MAF 正朝 GA 邁進，升級有時間壓力；V8 問題為技術債，壓力較低
5. **併行可行** — MAF 升級和 V8 修復可在不同分支併行進行，因影響範圍不重疊

### V8 問題會被升級自動改善

| V8 Issue | 改善機制 |
|----------|---------|
| 部分 C-01（InMemoryCheckpointStorage） | BC-11 標準化 `source_id` 為 `"in_memory"` |
| AgentRunResponse.created_at UTC 時區錯誤 | rc4 bug fix 修正 |
| 空文字內容 pydantic 驗證失敗 | rc4 bug fix 修正 |
| 重複 MCP 工具/提示註冊 | b251114 bug fix 修正 |

---

## 第十二部分：參考文件索引

| 文件 | 路徑 | 用途 |
|------|------|------|
| 萬全規劃策略 | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-RC4-Upgrade-Master-Plan.md` | 完整升級規劃，包含逐檔案變更指令 |
| 使用掃描報告 | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-Usage-Scan-Complete.md` | 23 import、28 類別、逐條影響分析 |
| 版本差異分析 | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-Version-Gap-Analysis.md` | 18 個 BC 完整清單和 API 變更摘要 |
| 風險評估 | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-Upgrade-Risk-Assessment.md` | 依賴、V8 交互、測試影響、回滾策略 |
| 新功能採用分析 | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/MAF-New-Features-Adoption-Analysis.md` | 7 功能、3 批次策略 |
| Claude SDK 差異 | `docs/07-analysis/Overview/full-codebase-analysis/sdk-version-gap/Claude-SDK-Version-Gap-Analysis.md` | anthropic SDK + claude-agent-sdk 分析 |
| V8 架構分析 | `docs/07-analysis/Overview/full-codebase-analysis/MAF-Claude-Hybrid-Architecture-V8.md` | 11 層架構、62 issues |
| V8 功能驗證 | `docs/07-analysis/Overview/full-codebase-analysis/MAF-Features-Architecture-Mapping-V8.md` | 70+ 功能驗證 |
| MS Learn 遷移指南 | [Python 2026 重大變更](https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes) | 官方遷移參考 |

---

## 審批

| 角色 | 姓名 | 狀態 |
|------|------|------|
| Technical Lead | -- | 待審批 |
| Project Owner | Chris | 待審批 |

---

**建立日期**: 2026-03-15
**最後更新**: 2026-03-15
**作者**: Architecture Review Board + AI Assistant
