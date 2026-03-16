# 升級後 Import 驗證報告

**掃描範圍**: `C:\Users\Chris\Downloads\maf-upgrade\backend\src\`
**掃描日期**: 2026-03-16
**驗證目標**: 確認 MAF RC4 升級後沒有過時 import 路徑殘留

---

## 1. 過時 import 殘留檢查

### 1.1 Python 原始碼（`.py` 檔案）

| # | 搜索模式 | 結果 | 狀態 | 說明 |
|---|----------|------|------|------|
| 1 | `from agent_framework import.*Builder` | 3 matches | **PASS（有條件）** | 見 1.1.1 |
| 2 | `from agent_framework import ChatAgent`（直接使用，非別名） | 0 matches | **PASS** | 無直接使用舊名稱 |
| 3 | `from agent_framework import ChatMessage`（直接使用，非別名） | 0 matches | **PASS** | 無直接使用舊名稱 |
| 4 | `from agent_framework import WorkflowStatusEvent`（直接使用，非別名） | 0 matches | **PASS** | 無直接使用舊名稱 |
| 5 | `from agent_framework import Context,` | 0 matches | **PASS** | 已移除的類別未被引用 |
| 6 | `from agent_framework import ContextProvider`（直接使用，非別名） | 0 matches | **PASS** | 無直接使用舊名稱 |
| 7 | `from agent_framework import MemoryStorage` | 1 match | **WARN** | 見 1.1.2 |
| 8 | `from agent_framework.workflows import` | 1 match (active code) | **FAIL** | 見 1.1.3 |
| 9 | `from agent_framework.agents import` | 0 matches | **PASS** | 不存在的子模組未被引用 |
| 10 | `from agent_framework.workflows.orchestrations import` | 0 matches (comments only) | **PASS** | 舊路徑已被正確替換為 `agent_framework.orchestrations` |
| 11 | `from agent_framework.checkpoints import` | 0 matches | **PASS** | 不存在的子模組未被引用 |

#### 1.1.1 `from agent_framework import.*Builder` — 詳細分析

| 檔案 | 行號 | Import 內容 | 判定 |
|------|------|-------------|------|
| `workflow.py` | 425 | `from agent_framework import WorkflowBuilder` | **需確認**: `WorkflowBuilder` 是否仍在頂層？RC4 可能要求從 `agent_framework.orchestrations` 匯入 |
| `builders/nested_workflow.py` | 71 | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` | **需確認**: 同上，`WorkflowBuilder` 和 `WorkflowExecutor` 是否仍在頂層 |
| `core/workflow.py` | 37 | `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor` | **需確認**: `WorkflowBuilder` 是否應移至 `agent_framework.orchestrations` |

> **注意**: 根據 RC4 升級規則，orchestration builders 應從 `agent_framework.orchestrations` 匯入。但 `WorkflowBuilder` 可能屬於核心 API 而非 orchestration builder。需要對照 RC4 API 文件確認。如果 `WorkflowBuilder` 仍在頂層匯出，則這 3 個 match 為 PASS。

#### 1.1.2 `from agent_framework import MemoryStorage` — 詳細分析

| 檔案 | 行號 | 狀態 |
|------|------|------|
| `memory/base.py` | 169 | **WARN**: `MemoryStorage` 在 RC4 中已被移除。此處在 `MemoryStorageProtocol` docstring 下方的程式碼中引用，用於向後兼容型別檢查。需確認是否有替代方案。 |

#### 1.1.3 `from agent_framework.workflows import` — **FAIL**

| 檔案 | 行號 | Import 內容 | 嚴重度 |
|------|------|-------------|--------|
| `infrastructure/storage/storage_factories.py` | 308 | `from agent_framework.workflows import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage` | **HIGH** |

> **問題**: `agent_framework.workflows` 子模組在 RC4 中不存在。`InMemoryCheckpointStorage` 已被移到頂層（`from agent_framework import InMemoryCheckpointStorage`）。此行已有 `# TODO: verify submodule path` 註解，確認開發者已注意到但尚未修正。

**建議修正**:
```python
# 修正前（FAIL）:
from agent_framework.workflows import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage

# 修正後:
from agent_framework import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage
```

---

## 2. 正確 import 確認

### 2.1 `from agent_framework.orchestrations import` — Builders

| # | 檔案 | Import 內容 |
|---|------|-------------|
| 1 | `builders/groupchat.py:83` | `GroupChatBuilder, GroupChatRoundRobinBuilder, GroupChatSelectorBuilder` |
| 2 | `builders/concurrent.py:83` | `ConcurrentBuilder` |
| 3 | `builders/handoff.py:54` | `HandoffBuilder, HandoffAgentUserRequest` |
| 4 | `builders/magentic.py:39` | `MagenticBuilder` (及相關類別) |
| 5 | `builders/planning.py:31` | `MagenticBuilder` |
| 6 | `core/execution.py:35` | `SequentialBuilder` |

**狀態**: **PASS** — 6 個檔案正確使用 `agent_framework.orchestrations` 路徑

### 2.2 別名（Backward-Compatible Aliases）

| 別名模式 | 檔案 | 行號 | 狀態 |
|----------|------|------|------|
| `Agent as ChatAgent` | `core/execution.py` | 34 | **PASS** |
| `Agent as ChatAgent, Message as ChatMessage` | `builders/agent_executor.py` | 155 | **PASS** |
| `WorkflowEvent as WorkflowStatusEvent` | `core/events.py` | 34 | **PASS** |
| `BaseContextProvider as ContextProvider` | `memory/base.py` | 25 | **PASS** |

**狀態**: **PASS** — 所有 4 個重新命名的類別都使用了正確的 `NewName as OldName` 別名模式

### 2.3 頂層正確 import

| 檔案 | Import 內容 | 狀態 |
|------|-------------|------|
| `multiturn/checkpoint_storage.py:31` | `CheckpointStorage, InMemoryCheckpointStorage` | **PASS** |
| `multiturn/adapter.py:27` | `Agent, AgentRuntime, ...` (多個頂層類別) | **PASS** |
| `core/approval_workflow.py:36` | `Workflow, Edge` | **PASS** |
| `core/workflow.py:37` | `Workflow, WorkflowBuilder, Edge, Executor` | **PASS** |
| `core/approval.py:39` | `Executor, handler, WorkflowContext` | **PASS** |
| `core/executor.py:38` | `Executor, WorkflowContext, handler` | **PASS** |
| `core/edge.py:29` | `Edge` | **PASS** |
| `checkpoint.py:102` | `WorkflowCheckpoint` | **PASS** |
| `builders/workflow_executor.py:52` | 多個頂層類別 | **PASS** |
| `builders/planning.py:32` | `Workflow` | **PASS** |

---

## 3. 文件/註解中的過時引用（低優先級）

### 3.1 CLAUDE.md 檔案（`backend/src/` 內）

| 檔案 | 過時內容 | 優先級 |
|------|----------|--------|
| `integrations/agent_framework/CLAUDE.md:120` | `from agent_framework import XxxBuilder` — 範例仍使用頂層路徑，orchestration builders 應改為 `from agent_framework.orchestrations import XxxBuilder` | LOW |
| `integrations/agent_framework/CLAUDE.md:231` | `from agent_framework import GroupChatBuilder` — 應為 `from agent_framework.orchestrations import GroupChatBuilder` | LOW |

### 3.2 `.claude/skills/` 參考文件（`backend/src/` 外，全專案範圍）

| 檔案 | 問題 | 優先級 |
|------|------|--------|
| `.claude/skills/microsoft-agent-framework/SKILL.md` | 多處使用 `from agent_framework.workflows import` 舊路徑 | LOW |
| `.claude/skills/.../references/common-mistakes.md` | 使用 `from agent_framework.workflows import` 和 `from agent_framework.workflows.orchestrations import` | LOW |
| `.claude/skills/.../references/workflows-api.md` | 大量使用 `from agent_framework.workflows import` 舊路徑 | LOW |

> **注意**: `.claude/skills/` 目錄中的參考文件是 AI 輔助開發的指引文件，不是執行程式碼。這些過時路徑不會影響執行，但可能導致 AI 助手在未來生成錯誤的 import。建議在升級完成後統一更新。

### 3.3 Python 註解中的過時引用

| 檔案 | 行號 | 內容 | 優先級 |
|------|------|------|--------|
| `core/__init__.py` | 29-30 | `# from agent_framework.workflows import Executor, Edge, Workflow` | LOW |
| `core/__init__.py` | 31 | `# from agent_framework.workflows.orchestrations import SequentialOrchestration` | LOW |
| `core/approval_workflow.py` | 24 | `# from agent_framework.workflows import Workflow` | LOW |
| `core/approval.py` | 11, 24 | `# from agent_framework.workflows import RequestResponseExecutor, Executor` | LOW |
| `core/execution.py` | 11, 21 | `# from agent_framework.workflows.orchestrations import SequentialOrchestration` | LOW |
| `memory/__init__.py` | 27 | `# - Official API: from agent_framework import Memory, MemoryStorage` | LOW |

> 這些都是註解（`#` 開頭），不影響執行，但保留了升級前的舊路徑作為歷史參考。

---

## 4. 總結

### 統計

| 類別 | PASS | FAIL | WARN | 總計 |
|------|------|------|------|------|
| 過時 import 檢查 | 9 | 1 | 1 | 11 |
| 正確 import 確認 | 20 | 0 | 0 | 20 |
| 文件過時引用 | — | — | — | 9 處（低優先級） |

### 必須修正的問題（FAIL）

1. **`infrastructure/storage/storage_factories.py:308`** — `from agent_framework.workflows import InMemoryCheckpointStorage` 必須修正為 `from agent_framework import InMemoryCheckpointStorage`

### 需要確認的問題（WARN）

2. **`memory/base.py:169`** — `from agent_framework import MemoryStorage` — RC4 中 `MemoryStorage` 是否仍存在？若已移除，需要替代方案
3. **`workflow.py:425`、`builders/nested_workflow.py:71`、`core/workflow.py:37`** — `WorkflowBuilder` 是否仍在頂層匯出，或需要從 `agent_framework.orchestrations` 匯入？

### 低優先級改善項目

4. 更新 `CLAUDE.md` 中的範例 import 路徑（2 處）
5. 更新 `.claude/skills/` 參考文件中的過時路徑（3 個檔案，多處）
6. 清理 Python 原始碼中的舊路徑註解（6 個檔案）

### 整體判定

**有條件通過（Conditional PASS）** — 1 個確定的 FAIL 需要立即修正，2 個 WARN 需要對照 RC4 API 文件確認。升級後的別名策略（`NewName as OldName`）已正確實施，orchestration builders 已正確遷移至 `agent_framework.orchestrations` 路徑。
