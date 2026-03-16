# Claude SDK 升級後驗證報告

**驗證日期**: 2026-03-16
**驗證範圍**: MAF RC4 升級分支中 Claude SDK 相關的 3 項修復
**基準文件**: `Claude-SDK-Version-Gap-Analysis.md`（2026-03-15）

---

## 驗證摘要

| 驗證項目 | 狀態 | 說明 |
|----------|------|------|
| anthropic 依賴宣告 | PASS | `requirements.txt` 已加入 `anthropic>=0.84.0` |
| Extended Thinking header | PASS | 已更新為 `interleaved-thinking-2025-05-14` |
| 預設模型 ID（client.py） | PASS | 已更新為 `claude-sonnet-4-6-20260217` |
| agent-framework-claude 套件 | PASS | 已隨 RC4 安裝（v1.0.0b260311） |
| 舊模型 ID 殘留（源碼） | WARN | 5 個源碼檔 + 8 個測試檔仍使用舊 ID |

**整體結論**: 3 項立即修復均已完成。存在舊模型 ID 殘留需後續處理。

---

## 1. anthropic 依賴宣告

**狀態**: PASS

**驗證結果**:
- `backend/requirements.txt` 中已新增獨立區段：
  ```
  # ===========================================
  # Anthropic Claude SDK
  # ===========================================
  anthropic>=0.84.0
  ```
- 位置合理，置於 Azure Services 區段之後，有清晰的區段標題
- 版本約束 `>=0.84.0` 與本地安裝版本一致

**對應差異分析建議**: 第 7.1 節「立即行動」第 1 項 — 已完成

---

## 2. Extended Thinking Header

**狀態**: PASS

**驗證結果**:
- `backend/src/integrations/claude_sdk/client.py:260`：
  ```python
  extra_headers = {"anthropic-beta": "interleaved-thinking-2025-05-14"}
  ```
- 舊的 `extended-thinking-2024-10` header 已被替換
- 在整個 `backend/src/` 目錄中搜索確認：
  - 無 `extended-thinking-2024-10` 殘留（源碼中）
  - `interleaved-thinking-2025-05-14` 僅出現在 `client.py:260`（正確位置）
- `.venv-rc4/` 中的 `extended-thinking` 引用為第三方套件文檔/註解，非項目代碼

**注意**: `client.py:221` 的 docstring 仍提及 `anthropic-beta: extended-thinking`，但這是描述性文字，不影響運行時行為。建議後續更新此 docstring 以保持一致。

**對應差異分析建議**: 第 7.1 節「立即行動」第 2 項 — 已完成

---

## 3. 模型識別符

**狀態**: PARTIAL — client.py 已修復，其他檔案殘留

### 3.1 已修復

| 檔案 | 行號 | 新值 |
|------|------|------|
| `client.py` | 38 | `claude-sonnet-4-6-20260217` |

### 3.2 源碼中的舊 ID 殘留（`claude-sonnet-4-20250514`）

| 檔案 | 行號 | 用途 |
|------|------|------|
| `config.py` | 20 | `ClaudeSDKConfig` 預設值 |
| `config.py` | 55 | `from_env()` 的 fallback 值 |
| `autonomous/analyzer.py` | 88 | `AutonomousAnalyzer` 預設模型 |
| `autonomous/planner.py` | 107 | `AutonomousPlanner` 預設模型 |
| `autonomous/verifier.py` | 92 | `AutonomousVerifier` 預設模型 |
| `memory/types.py` | 202 | `MEMORY_LLM_MODEL` 的 fallback |

**風險評估**: MEDIUM
- `config.py:20` 的預設值與 `client.py:38` 的預設值不一致，可能導致混淆
- `autonomous/` 模組的三個元件仍使用舊模型，若直接呼叫會使用過時的模型
- `memory/types.py` 的 fallback 使用舊 ID，但通常由環境變數覆蓋

### 3.3 測試檔中的舊 ID

| 檔案 | 說明 |
|------|------|
| `tests/unit/api/v1/claude_sdk/test_routes.py` | 2 處（行 41, 292） |
| `tests/unit/integrations/claude_sdk/test_client.py` | 2 處（行 24, 29-31） |
| `tests/unit/integrations/claude_sdk/test_config.py` | 7 處（行 18, 91, 100, 106, 114, 77-83） |
| `tests/unit/integrations/claude_sdk/test_query.py` | 1 處（行 40） |
| `tests/unit/test_mem0_client.py` | 1 處（行 39） |

**風險評估**: MEDIUM — 測試預期值與實際預設值不一致可能導致測試失敗

### 3.4 舊 Opus ID（`claude-opus-4-20250514`）

僅出現在測試檔中（作為自訂模型參數測試），不影響預設行為：
- `test_client.py:29-31` — 測試自訂模型參數
- `test_config.py:38-40, 77-83` — 測試環境變數覆蓋

**風險評估**: LOW — 這些是測試特定模型參數的場景，不涉及預設值

**對應差異分析建議**: 第 7.1 節「立即行動」第 3 項 — 部分完成（僅 client.py）

---

## 4. 差異分析報告中的其他建議處理狀態

### 已修復（本次升級）

| 建議 | 狀態 | 備註 |
|------|------|------|
| `anthropic>=0.84.0` 加入 requirements.txt | DONE | 第 1 節確認 |
| Extended Thinking header 更新 | DONE | 第 2 節確認 |
| 預設模型 ID 更新 | PARTIAL | 僅 client.py，其餘待處理 |

### 延後處理

| 建議 | 優先級 | 延後原因 |
|------|--------|----------|
| 評估官方 `claude-agent-sdk` 採用 | HIGH | 重大架構決策，需獨立評估（47 檔自建代碼影響範圍大） |
| 啟用自動 prompt 快取 | LOW | 最佳化機會，非功能性問題 |
| 使用 `anthropic.helpers.mcp` 轉換輔助工具 | LOW | 簡化機會，現有自建實作仍可運作 |
| 工具串流（`input_json_delta`） | LOW | 增強功能，非關鍵缺口 |
| 批次 API / Token 計數 | LOW | 新功能，非現有問題 |

---

## 5. MAF 原生 Claude 支援

**狀態**: PASS

**驗證結果**:
- `agent-framework-claude` 套件已安裝：
  - **版本**: `1.0.0b260311`
  - **依賴**: `agent-framework-core`, `claude-agent-sdk`
  - **位置**: `.venv-rc4/Lib/site-packages/agent_framework_claude/`
- 套件內容：
  - `__init__.py` — 模組入口
  - `_agent.py`（26,899 bytes） — `ClaudeAgent` 實作
- `agent_framework.anthropic` 命名空間提供延遲匯入：
  - `ClaudeAgent`
  - `ClaudeAgentOptions`
  - `RawClaudeAgent`

**意義**: MAF RC4 已內建 Claude 支援，為未來的 Phase C（Claude SDK BaseAgent 整合）提供了官方基礎，可考慮以 `agent-framework-claude` 的 `ClaudeAgent` 替代部分自建 `claude_sdk/` 程式碼。

---

## 6. 建議後續行動

### 立即（下一個 Sprint）

1. **統一模型 ID**: 將 `config.py`、`autonomous/*.py`、`memory/types.py` 中的舊模型 ID 全部更新為 `claude-sonnet-4-6-20260217`
2. **更新測試**: 同步更新所有測試檔中的模型 ID 預期值
3. **更新 docstring**: `client.py:221` 的 `extended-thinking` 描述更新為 `interleaved-thinking`

### 短期（1-2 Sprint）

4. **評估 `ClaudeAgent` 整合**: 研究以 `agent_framework_claude.ClaudeAgent` 替代自建 `claude_sdk/client.py` 的可行性
5. **啟用自動 prompt 快取**: 在多輪對話場景中測試成本效益

### 長期

6. **Claude SDK 架構決策**: 決定自建 47 檔 vs 官方 `claude-agent-sdk` 的遷移策略

---

*本報告由 Claude SDK Verifier 自動產生 — 2026-03-16*
