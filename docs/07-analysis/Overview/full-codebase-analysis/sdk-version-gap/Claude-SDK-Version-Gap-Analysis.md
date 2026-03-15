# Anthropic Claude SDK — 版本差異分析報告

**分析日期**: 2026-03-15
**目前已安裝版本**: `anthropic==0.84.0`（已在本地安裝，但**未列於 requirements.txt**）
**最新可用版本**: `anthropic==0.84.0`（2026-02-25 發佈）— 已是最新
**Claude Agent SDK**: `claude-agent-sdk==0.1.48`（2026-03-07 發佈）— 未安裝、未使用
**項目 SDK 凍結時間點**: ~2025-10（Sprint 48-50 時代，anthropic ~0.30-0.40 範圍）

---

## 執行摘要

IPA Platform 的 `backend/src/integrations/claude_sdk/` 模組（47 個檔案，~15K LOC）是一個**完全自建的抽象層**，包裝 `anthropic.AsyncAnthropic`。雖然本地安裝的 `anthropic` 套件已是 v0.84.0（最新），但項目的自建程式碼是基於 2025 年底的 SDK 模式設計，尚未更新以利用重要的新功能。更關鍵的是，Anthropic 已發佈**官方 `claude-agent-sdk` 套件**（v0.1.48），提供了 hooks、工具、MCP 整合和 session 管理的第一方實作 — 而這些功能是項目從零開始自建的。

### 關鍵發現

| 領域 | 狀態 | 風險等級 |
|------|------|----------|
| `anthropic` 套件版本 | 已是最新（0.84.0） | LOW |
| `anthropic` 未列入 requirements.txt | 缺少依賴宣告 | MEDIUM |
| Extended Thinking API 使用 | 使用已棄用的 beta header | MEDIUM |
| 模型識別符 | 寫死 `claude-sonnet-4-20250514` | MEDIUM |
| Prompt 快取 | 未利用自動快取功能 | LOW |
| MCP 工具轉換 | 自建實作，SDK 現已提供輔助工具 | LOW |
| `claude-agent-sdk` 採用 | 未安裝；存在 47 檔的自建替代品 | HIGH |
| 自建 hooks 系統 | 與官方 Agent SDK hooks 重複 | HIGH |
| 自建工具系統 | 與官方 Agent SDK 工具重複 | HIGH |
| 自建 MCP 整合 | 與官方 Agent SDK MCP 重複 | HIGH |

---

## 1. 版本時間線

### anthropic Python SDK（2025-10 至 2026-03）

| 版本 | 日期 | 關鍵變更 |
|------|------|----------|
| ~0.35-0.40 | 2025-10 | **項目設計時間點** — Messages API、基本串流、tool_use |
| 0.47.2 | 2025-02-25 | Bug 修復、穩定性改進 |
| 0.73.0 | 2025-11-14 | Extended thinking 改進 |
| 0.74.0 | 2025-11-18 | 模型更新 |
| 0.75.0 | 2025-11-24 | Opus 4.5 支援，串流改進 |
| 0.76.0 | 2026-01-13 | 文件字串新增，二進制請求串流，伺服器端工具執行器 |
| 0.77.0 | 2026-01-29 | 額外功能 |
| 0.78.0 | 2026-02-05 | **Claude Opus 4.6 支援**，自適應思維 |
| 0.79.0 | 2026-02-07 | Opus 4.6 快速模式，同步 beta count_tokens 速度參數 |
| 0.80.0 | 2026-02-17 | 功能更新 |
| 0.81.0 | 2026-02-18 | 功能更新 |
| 0.82.0 | 2026-02-18 | 修復共用 UserLocation 類型，為已移除的巢狀 UserLocation 新增向後相容別名 |
| 0.83.0 | 2026-02-19 | **頂層自動 prompt 快取（`cache_control`）** |
| 0.84.0 | 2026-02-25 | **MCP 工具/提示/資源轉換輔助工具**，品牌重塑為「Claude SDK」 |

### claude-agent-sdk（官方 Agent SDK）

| 版本 | 日期 | 關鍵變更 |
|------|------|----------|
| 0.1.0 | 2025-Q3 | 初始發佈（前身為 `claude-code-sdk`） |
| 0.1.36-0.1.47 | 2025-2026 | Hooks、工具、MCP 標註、session 管理 |
| 0.1.48 | 2026-03-07 | 修復精細工具串流，附帶 CLI v2.1.71 |

### Claude 模型時間線

| 模型 | 發佈日期 | 模型 ID |
|------|---------|---------|
| Claude Sonnet 4 | 2025-05-22 | `claude-sonnet-4-20250514` |
| Claude Opus 4 | 2025-05-22 | `claude-opus-4-20250514` |
| Claude Sonnet 4.5 | 2025-09-29 | `claude-sonnet-4-5-20250929` |
| Claude Opus 4.5 | 2025-11-24 | `claude-opus-4-5-20251124` |
| Claude Opus 4.6 | 2026-02-05 | `claude-opus-4-6-20260205` |
| Claude Sonnet 4.6 | 2026-02-17 | `claude-sonnet-4-6-20260217` |

---

## 2. 破壞性變更

### 2.1 Extended Thinking API（MEDIUM 影響）

**項目目前使用方式**（`client.py:260`）：
```python
extra_headers = {"anthropic-beta": "extended-thinking-2024-10"}
```

**目前狀態**：
- Extended thinking 在 Claude Opus 4.6 上已是 **GA** — 不需要 beta header
- `interleaved-thinking-2025-05-14` beta header 在 Opus 4.6 上**已棄用**且會被安全忽略
- 其他 Claude 4.x 模型仍需要 beta header `interleaved-thinking-2025-05-14`
- 項目使用的是舊版 header 格式 `extended-thinking-2024-10`，可能無法正確運作

**必要變更**：更新為不使用 header（Opus 4.6 適用）或使用 `interleaved-thinking-2025-05-14`（舊版模型適用）。

### 2.2 UserLocation 類型變更（LOW 影響）

**v0.82.0**：移除巢狀 `UserLocation` 類別，新增向後相容別名。如果項目從巢狀命名空間使用 `UserLocation` 類型，引入可能需要更新。

### 2.3 SDK 品牌重塑（LOW 影響）

**v0.84.0**：從「Anthropic Python SDK」重新命名為「Claude SDK」。無 API 變更，但 README 和套件中繼資料已更新。

### 2.4 陣列格式變更（LOW 影響）

**v0.84.0**：將 `array_format` 改為 `brackets`。這影響 API 呼叫中陣列類型的查詢參數序列化。

---

## 3. 新增功能

### 3.1 Claude Agent SDK（官方 — `claude-agent-sdk` v0.1.48）

官方 Claude Agent SDK 是一個**獨立的 PyPI 套件**，提供：

| 功能 | 官方 SDK | IPA 自建 | 重疊程度 |
|------|---------|---------|----------|
| Agent 循環 + session 管理 | `ClaudeSDKClient` 類別 | `claude_sdk/client.py` + `session.py` | **完全重疊** |
| Hook 系統（審批、審計、沙箱） | `@hook` 裝飾器 + 生命週期 hooks | `claude_sdk/hooks/`（5 個檔案） | **完全重疊** |
| 內建工具（檔案、bash、網頁） | 內建工具集 | `claude_sdk/tools/`（5 個檔案） | **完全重疊** |
| MCP 整合 | 原生 MCP 支援帶標註 | `claude_sdk/mcp/`（7 個檔案） | **完全重疊** |
| 透過 MCP 伺服器的自定義工具 | 進程內 MCP 伺服器 | 自定義工具註冊表 | **完全重疊** |
| 工具串流 | `include_partial_messages=True` | 未實作 | **缺口** |
| 工具標註 | `@tool(annotations={...})` | 未實作 | **缺口** |
| Session 列表/篩選 | 內建 session 管理 | `claude_sdk/session_state.py` | **部分重疊** |

**官方 Agent SDK 中 IPA 缺少的關鍵能力**：
- 精細工具串流，帶 `input_json_delta` 事件
- MCP 工具標註（`readOnlyHint`、`destructiveHint`、`idempotentHint`、`openWorldHint`）
- hook 輸入中的 `agent_id` 和 `agent_type` 欄位
- 向前相容的未知訊息類型處理
- 附帶 Claude CLI（v2.1.71）用於子進程執行

### 3.2 Anthropic Python SDK 新功能

| 功能 | 版本 | 描述 | IPA 影響 |
|------|------|------|----------|
| **自動 prompt 快取** | 0.83.0 | 頂層 `cache_control` 參數 | 未使用 — 可顯著降低成本 |
| **MCP 轉換輔助工具** | 0.84.0 | `anthropic.helpers.mcp` 用於工具/提示/資源轉換 | 自建 MCP 類型可簡化 |
| **Claude Opus 4.6** | 0.78.0 | 新模型支援，帶自適應思維 | 模型 ID 未被引用 |
| **快速模式** | 0.79.0 | Opus 4.6 速度參數 | 未利用 |
| **伺服器端工具執行器** | 0.76.0 | 帶預定義行為的伺服器工具 | 未利用 |
| **Token 計數（同步 beta）** | 0.79.0 | `messages.count_tokens()` 帶速度參數 | 未利用 |
| **二進制請求串流** | 0.76.0 | 請求中的串流二進制資料 | 未利用 |
| **server_tool_use 區塊** | 0.76+ | 程式碼執行伺服器工具 | 未利用 |

---

## 4. API 變更

| 類別 | 舊 API（IPA 目前） | 新 API（最新） | 影響 |
|------|-------------------|---------------|------|
| Extended Thinking header | `"anthropic-beta": "extended-thinking-2024-10"` | 不需要 header（Opus 4.6）或 `"interleaved-thinking-2025-05-14"` | **MEDIUM** — 目前 header 已過時 |
| 模型 ID | `claude-sonnet-4-20250514` | `claude-sonnet-4-6-20260217` / `claude-opus-4-6-20260205` | **MEDIUM** — 缺少最新模型 |
| Prompt 快取 | 每個區塊手動 `cache_control` | 頂層 `cache_control`（自動） | **LOW** — 最佳化機會 |
| MCP 工具 | 自建 `MCPToolDefinition.to_claude_format()` | `anthropic.helpers.mcp` 轉換輔助工具 | **LOW** — 簡化機會 |
| 工具串流 | 未實作 | `include_partial_messages=True` + `input_json_delta` | **LOW** — 增強機會 |
| 批次 API | 未使用 | `messages.batches.create()`（GA） | **LOW** — 新功能 |
| Token 計數 | 未使用 | `messages.count_tokens()` | **LOW** — 新功能 |

---

## 5. 對 IPA Platform 的影響

### 5.1 `integrations/claude_sdk/` 受影響分析

#### HIGH 優先級 — 與官方 SDK 重複

整個 47 檔、~15K LOC 的自建 `claude_sdk` 模組大量重複了官方 `claude-agent-sdk` v0.1.48 提供的功能：

| IPA 自建模組 | 檔案數 | LOC | 官方對應功能 |
|-------------|--------|-----|-------------|
| `client.py` + `session.py` + `query.py` | 3 | ~986 | `claude-agent-sdk.ClaudeSDKClient` |
| `hooks/`（base、approval、audit、rate_limit、sandbox） | 5 | ~1,384 | `claude-agent-sdk` hooks 系統 |
| `tools/`（file、command、web、registry） | 5 | ~1,462 | `claude-agent-sdk` 內建工具 |
| `mcp/`（types、base、stdio、http、discovery、manager） | 7 | ~3,207 | `claude-agent-sdk` 原生 MCP |
| `autonomous/`（analyzer、planner、executor、verifier、retry、fallback） | 7 | ~2,587 | **無直接對應** — IPA 獨有 |
| `hybrid/`（capability、selector、orchestrator、synchronizer） | 5 | ~2,166 | **無直接對應** — IPA 獨有 |
| `orchestrator/`（context_manager、task_allocator、coordinator） | 4 | ~1,630 | **無直接對應** — IPA 獨有 |
| `config.py` + `types.py` + `exceptions.py` + `session_state.py` | 4 | ~1,578 | 部分由官方 SDK 覆蓋 |

**總結**：~40% 的自建程式碼（hooks、工具、MCP、基本客戶端）與官方 SDK 重複。~60%（自主規劃、混合編排、多代理協調）是獨有的業務邏輯。

#### MEDIUM 優先級 — 過時的 API 模式

| 檔案 | 問題 | 行號 |
|------|------|------|
| `client.py` | 寫死模型 `claude-sonnet-4-20250514` | L38 |
| `client.py` | 已棄用的 extended thinking beta header `extended-thinking-2024-10` | L260 |
| `config.py` | 不支援最新模型別名 | — |
| `mcp/types.py` | 自建 `to_claude_format()` 可使用 SDK 輔助工具 | — |
| `query.py` | 不支援自動 prompt 快取 | — |

### 5.2 與官方 SDK 的重疊和衝突

| 關注點 | 詳情 |
|--------|------|
| **命名衝突** | 項目引入 `from claude_sdk.hooks import ...`，但官方套件為 `claude-agent-sdk` — 目前無引入衝突 |
| **維護負擔** | 47 個自建 SDK 包裝檔案需要維護 vs 使用經過測試的官方 SDK |
| **功能滯後** | 官方 SDK 自動獲得新功能（工具串流、標註）；自建程式碼需要手動實作 |
| **Bug 修復** | 官方 SDK 獲得社群測試的 bug 修復；自建程式碼僅依賴項目團隊 |
| **測試開銷** | 自建 SDK 需要獨立的測試套件（估計 ~20+ 個測試檔案） |

---

## 6. 遷移工作量估算

### 選項 A：增量更新（建議短期方案）

修復關鍵問題，不進行結構重組：

| 任務 | 工時 | 優先級 |
|------|------|--------|
| 將 `anthropic>=0.84.0` 加入 requirements.txt | 0.5h | CRITICAL |
| 更新 extended thinking beta header | 2h | HIGH |
| 將最新模型 ID 加入設定 | 1h | HIGH |
| 在適用處啟用自動 prompt 快取 | 4h | MEDIUM |
| 使用 SDK 的 MCP 轉換輔助工具 | 2h | LOW |
| **合計** | **~10h（1 Sprint）** | |

### 選項 B：採用官方 Claude Agent SDK（建議長期方案）

將自建 hooks/工具/MCP 替換為官方 `claude-agent-sdk`：

| 任務 | 工時 | 優先級 |
|------|------|--------|
| 安裝 `claude-agent-sdk>=0.1.48` | 0.5h | — |
| 將 `hooks/` 遷移到官方 hook 系統 | 8h | HIGH |
| 將 `tools/` 遷移到官方工具集 | 6h | HIGH |
| 將 `mcp/` 遷移到官方 MCP 整合 | 12h | HIGH |
| 將 `client.py` + `session.py` 遷移到官方客戶端 | 8h | HIGH |
| 適配 `autonomous/` 以配合官方 SDK | 16h | MEDIUM |
| 適配 `hybrid/` 以配合官方 SDK | 12h | MEDIUM |
| 適配 `orchestrator/` 以配合官方 SDK | 8h | MEDIUM |
| 更新所有引入自建 SDK 的 API 路由 | 8h | HIGH |
| 更新測試套件 | 16h | HIGH |
| 整合測試 | 8h | HIGH |
| **合計** | **~100h（4-5 Sprint）** | |

### 選項 C：混合方案（務實方案）

保留獨有業務邏輯，替換重複的基礎設施：

| 任務 | 工時 | 優先級 |
|------|------|--------|
| 選項 A 任務（立即修復） | 10h | Sprint N |
| 將 `hooks/` 替換為官方 SDK hooks | 8h | Sprint N+1 |
| 將 `tools/` 替換為官方 SDK 工具 | 6h | Sprint N+1 |
| 將 `mcp/` 替換為官方 SDK MCP | 12h | Sprint N+2 |
| 保留 `autonomous/`、`hybrid/`、`orchestrator/` 不變 | 0h | — |
| 自建模組使用官方 SDK 的 adapter 層 | 8h | Sprint N+2 |
| 測試更新 | 12h | Sprint N+2 |
| **合計** | **~56h（2-3 Sprint）** | |

---

## 7. 遷移建議

### 立即行動（本 Sprint）

1. **將 `anthropic>=0.84.0` 加入 `requirements.txt`** — 套件已安裝但未宣告為依賴。這是部署風險。

2. **更新 extended thinking header**（`client.py:260`）：
   ```python
   # 變更前
   extra_headers = {"anthropic-beta": "extended-thinking-2024-10"}
   # 變更後（Opus 4.6 — 不需要 header）
   # 舊版模型適用：
   extra_headers = {"anthropic-beta": "interleaved-thinking-2025-05-14"}
   ```

3. **更新預設模型**（`client.py:38`）：
   ```python
   # 變更前
   model: str = "claude-sonnet-4-20250514"
   # 變更後
   model: str = "claude-sonnet-4-6-20260217"
   ```

### 短期（未來 1-2 Sprint）

4. **評估官方 `claude-agent-sdk`** 的採用 — 安裝並先以替換 `hooks/` 模組作為概念驗證原型。

5. **啟用自動 prompt 快取** — 在多輪對話流程中降低成本。

6. **使用 `anthropic.helpers.mcp` 的 MCP 轉換輔助工具** — 簡化自建 MCP 類型定義。

### 長期（下一季度）

7. **採用選項 C（混合方案）** — 將基礎設施程式碼（hooks、工具、MCP）替換為官方 SDK，同時保留獨有業務邏輯（自主規劃、混合編排、多代理協調）。

8. **新功能考慮使用 `claude-agent-sdk`** — 任何新的代理功能都應基於官方 SDK 構建，而非擴展自建實作。

---

## 附錄：來源參考

- [Anthropic Python SDK 版本發佈](https://github.com/anthropics/anthropic-sdk-python/releases)
- [Anthropic Python SDK 變更日誌](https://github.com/anthropics/anthropic-sdk-python/blob/main/CHANGELOG.md)
- [Claude Agent SDK — PyPI](https://pypi.org/project/claude-agent-sdk/)
- [Claude Agent SDK — GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [Claude Agent SDK 變更日誌](https://github.com/anthropics/claude-agent-sdk-python/blob/main/CHANGELOG.md)
- [Claude Agent SDK Python 參考](https://platform.claude.com/docs/en/agent-sdk/python)
- [Claude Agent SDK Hooks](https://platform.claude.com/docs/en/agent-sdk/hooks)
- [Claude Agent SDK MCP](https://platform.claude.com/docs/en/agent-sdk/mcp)
- [Extended Thinking 文件](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)
- [Prompt 快取文件](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [模型棄用資訊](https://platform.claude.com/docs/en/about-claude/model-deprecations)
- [遷移至 Claude 4.5+ 指南](https://docs.anthropic.com/en/docs/about-claude/models/migrating-to-claude-4)
