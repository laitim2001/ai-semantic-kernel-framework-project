# POST-UPGRADE Constructor 驗證報告

> 驗證日期：2026-03-16
> 驗證範圍：`backend/src/integrations/agent_framework/` 所有 Builder 建構參數
> 驗證方法：Grep 搜索 + 實際 Python import 驗證 + 執行時測試

---

## 重大發現：rc4 Builder 建構參數與程式碼不符

### rc4 實際 `__init__` 簽名（透過 `inspect.signature` 驗證）

| Builder | 實際簽名 | 是否接受 `participants=` 建構參數 |
|---------|----------|----------------------------------|
| `MagenticBuilder` | `(self) -> None` | **否 — TypeError** |
| `ConcurrentBuilder` | `(self) -> None` | **否 — TypeError** |
| `GroupChatBuilder` | `(self) -> None` | **否 — TypeError** |
| `HandoffBuilder` | `(self, *, name=None, participants=None, participant_factories=None, description=None)` | **是 — 可選** |
| `WorkflowBuilder` | `(self, max_iterations=100, name=None, description=None)` | **不適用** |

### rc4 正確用法：方法鏈式呼叫

```python
# MagenticBuilder / ConcurrentBuilder / GroupChatBuilder
builder = MagenticBuilder()            # 空建構
builder.participants(participant_list)  # 方法鏈設定 participants
workflow = builder.build()

# HandoffBuilder（兩種方式皆可）
builder = HandoffBuilder(participants=participant_list)  # 建構參數
# 或
builder = HandoffBuilder()
builder.participants(participant_list)                    # 方法鏈
```

---

## 逐檔案驗證結果

### 1. MagenticBuilder 實例化

| 檔案 | 行號 | 程式碼 | 狀態 |
|------|------|--------|------|
| `builders/planning.py` | 519 | `MagenticBuilder(participants=[])` | **CRITICAL — 執行時 TypeError** |
| `builders/magentic.py` | 1289 | `MagenticBuilder(participants=participant_agents)` | **CRITICAL — 執行時 TypeError** |

**修正方案**：
```python
# planning.py:519 修正
self._magentic_builder = MagenticBuilder()
# 在 build() 中如果有 participants，再用方法鏈設定

# magentic.py:1289 修正
self._builder = MagenticBuilder()
self._builder.participants(participant_agents)
```

### 2. ConcurrentBuilder 實例化

| 檔案 | 行號 | 程式碼 | 狀態 |
|------|------|--------|------|
| `builders/concurrent.py` | 1073 | `ConcurrentBuilder(participants=participants)` | **CRITICAL — 執行時 TypeError** |
| `base.py` | 190 | `ConcurrentBuilder(participants=[])` (docstring 範例) | **WARNING — 文件不正確** |

**修正方案**：
```python
# concurrent.py:1073 修正
self._builder = ConcurrentBuilder()
self._builder.participants(participants)
```

### 3. GroupChatBuilder 實例化

| 檔案 | 行號 | 程式碼 | 狀態 |
|------|------|--------|------|
| `builders/groupchat.py` | 1337 | `GroupChatBuilder(participants=participants)` | **CRITICAL — 執行時 TypeError** |
| `CLAUDE.md` | 51, 235 | `GroupChatBuilder()` (文件範例) | **OK — 但過時，缺少 participants 設定** |

**修正方案**：
```python
# groupchat.py:1337 修正
self._builder = GroupChatBuilder()
self._builder.participants(participants)
```

### 4. HandoffBuilder 實例化

| 檔案 | 行號 | 程式碼 | 狀態 |
|------|------|--------|------|
| `builders/handoff.py` | 584 | `HandoffBuilder(participants=participants)` | **OK — participants 為可選建構參數** |

### 5. WorkflowBuilder 實例化

| 檔案 | 行號 | 程式碼 | 狀態 |
|------|------|--------|------|
| `workflow.py` | 437 | `WorkflowBuilder(max_iterations=..., name=..., description=...)` | **OK** |
| `builders/nested_workflow.py` | 615 | `WorkflowBuilder()` | **OK** |
| `core/workflow.py` | 204, 495, 542 | `WorkflowBuilder()` | **OK** |

### 6. SequentialBuilder

搜索結果：**未發現任何 `SequentialBuilder(` 實例化** — 不受影響。

---

## 延遲初始化模式驗證

### `self._builder = None` 位置

| 檔案 | 行號 | 後續初始化位置 | 安全性 |
|------|------|----------------|--------|
| `builders/concurrent.py` | 797 | `build()` 第 1073 行重新初始化 | **安全**（build 前必重建） |
| `builders/groupchat.py` | 1102 | `build()` 第 1337 行重新初始化 | **安全**（build 前必重建） |
| `builders/handoff.py` | 302 | `build()` 第 584 行重新初始化 | **安全**（build 前必重建） |
| `builders/magentic.py` | 1028 | `build()` 第 1289 行重新初始化 | **安全**（build 前必重建） |
| `base.py` | 306, 318 | `cleanup()` / `reset()` — 清理用途 | **安全**（不會直接使用） |

**結論**：延遲初始化模式本身是安全的。所有 `self._builder = None` 都在 `__init__` 或 `cleanup/reset` 中，在實際 `build()` 呼叫時都會重新建構。不會出現 `NoneType has no attribute X` 錯誤。

---

## 已移除 API 驗證

| 搜索項目 | 結果 | 狀態 |
|----------|------|------|
| `display_name=` | 未找到 | **PASS — 已清理** |
| `context_providers=`（複數） | 未找到 | **PASS — 已清理** |
| `AggregateContextProvider` | 未找到 | **PASS — 已清理** |

---

## 測試中的 Builder 實例化

搜索 `backend/tests/` 中所有直接實例化 Builder 的程式碼：**未找到**。

測試中未直接使用 `MagenticBuilder`、`ConcurrentBuilder`、`GroupChatBuilder`、`HandoffBuilder`、`WorkflowBuilder` 或 `SequentialBuilder`。

---

## 總結

### 嚴重問題（必須修正）

| # | 嚴重度 | 檔案 | 問題 | 影響 |
|---|--------|------|------|------|
| C1 | **CRITICAL** | `builders/planning.py:519` | `MagenticBuilder(participants=[])` | 執行時 TypeError |
| C2 | **CRITICAL** | `builders/magentic.py:1289` | `MagenticBuilder(participants=participant_agents)` | 執行時 TypeError |
| C3 | **CRITICAL** | `builders/concurrent.py:1073` | `ConcurrentBuilder(participants=participants)` | 執行時 TypeError |
| C4 | **CRITICAL** | `builders/groupchat.py:1337` | `GroupChatBuilder(participants=participants)` | 執行時 TypeError |

### 低風險問題

| # | 嚴重度 | 檔案 | 問題 |
|---|--------|------|------|
| W1 | WARNING | `base.py:190` | docstring 範例中的 `ConcurrentBuilder(participants=[])` 不正確 |
| W2 | WARNING | `CLAUDE.md:51,235` | `GroupChatBuilder()` 範例過時，缺少 participants 設定說明 |

### 已通過驗證

- HandoffBuilder — 建構參數正確（`participants` 為可選 kwarg）
- WorkflowBuilder — 5 處實例化均正確
- SequentialBuilder — 未使用
- 延遲初始化模式 — 安全（不會產生 NoneType 錯誤）
- 已移除 API（display_name, context_providers, AggregateContextProvider）— 全部已清理
- 測試檔案 — 無直接 Builder 實例化

### 修正優先順序

1. **立即修正** C1-C4：將 `Builder(participants=...)` 改為 `Builder().participants(...)` 方法鏈
2. **低優先** W1-W2：更新文件範例
