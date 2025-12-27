# Real Functional Tests

> Phase 12 真實功能測試 - 使用實際 ANTHROPIC_API_KEY 進行完整功能驗證

## 概述

這個測試套件使用真實的 Claude API 進行完整功能驗證，包括：

- 🤖 真實 LLM 對話（預設使用 **claude-haiku-4-5**）
- 🔧 真實工具執行（文件讀寫、命令執行、計算器）
- 🔌 MCP Server 整合
- 📋 端到端使用案例

> **注意**: 從 2025-12-27 起，預設模型改為 Claude Haiku 4.5，以提供更快速度和更低成本。
> 如需使用其他模型，可在 `.env` 中設置 `MODEL_NAME=claude-sonnet-4-20250514`。

## 前置條件

1. **Python 3.9+**
2. **Anthropic Python SDK**:
   ```bash
   pip install anthropic
   ```
3. **ANTHROPIC_API_KEY** - 設置在 `.env` 文件或環境變數

## 配置

### 方法 1: 使用 .env 文件（推薦）

```bash
# 複製範例文件
cp .env.example .env

# 編輯 .env 設置 API Key
# ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 方法 2: 環境變數

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

## 運行測試

### 運行所有場景

```bash
python real_functional_test.py
```

### 運行特定場景

```bash
# 場景 A: 真實 LLM 對話
python real_functional_test.py --scenario A

# 場景 B: 真實工具執行
python real_functional_test.py --scenario B

# 場景 C: MCP 整合
python real_functional_test.py --scenario C

# 場景 D: 端到端用例
python real_functional_test.py --scenario D
```

## 測試場景

### Scenario A: Real LLM Conversation
測試真實的 Claude LLM 對話功能

| 測試 | 說明 |
|------|------|
| `test_simple_conversation` | 簡單的問答對話 |
| `test_multi_turn_conversation` | 多輪對話上下文維護 |
| `test_system_prompt` | 系統提示詞效果 |
| `test_streaming_response` | 串流響應處理 |

### Scenario B: Real Tool Execution
測試真實的工具調用和執行

| 測試 | 說明 |
|------|------|
| `test_tool_call_generation` | Claude 生成工具調用 |
| `test_file_read_tool` | 文件讀取工具 |
| `test_file_write_tool` | 文件寫入工具 |
| `test_command_execution_tool` | 命令執行工具（受限） |
| `test_calculator_tool` | 數學計算工具（安全的 AST 解析） |

### Scenario C: Real MCP Integration
測試真實的 FilesystemMCPServer 整合（沙盒化文件操作）

| 測試 | 說明 |
|------|------|
| `test_mcp_server_connection` | 創建 FilesystemMCPServer，驗證 server 屬性 |
| `test_mcp_tool_discovery` | 發現 6 個 MCP 工具 (read/write/list/search/info/delete) |
| `test_mcp_tool_execution` | 執行 write_file, read_file, list_directory |
| `test_mcp_resource_access` | 執行 get_file_info, search_files（含內容搜尋） |

> **Note**: Scenario C 使用專案內建的 FilesystemMCPServer，無需外部依賴。
> 測試在臨時目錄中執行，完成後自動清理。

### Scenario D: End-to-End Use Cases
完整的端到端使用案例

| 測試 | 說明 |
|------|------|
| `test_code_review_assistant` | 代碼審查助手 |
| `test_file_analysis_workflow` | 文件分析工作流 |
| `test_multi_step_task` | 多步驟任務 |
| `test_error_handling_recovery` | 錯誤處理和恢復 |

## 預期結果

```
============================================================
🚀 Phase 12: Claude Agent SDK Real Functional Test
============================================================
✅ Configuration loaded
   Model: claude-haiku-4-5
   Backend: http://localhost:8000

============================================================
📋 Scenario A: Real LLM Conversation
   測試真實的 Claude LLM 對話功能
============================================================

  🧪 test_simple_conversation... ✅ PASSED (1.23s)
  🧪 test_multi_turn_conversation... ✅ PASSED (2.45s)
  🧪 test_system_prompt... ✅ PASSED (1.12s)
  🧪 test_streaming_response... ✅ PASSED (1.89s)

... (更多場景)

============================================================
📊 Phase 12 Real Functional Test - Results
============================================================

✅ PASSED Scenario A: Real LLM Conversation
   Tests: 4/4 passed
   Duration: 6.69s

✅ PASSED Scenario B: Real Tool Execution
   Tests: 5/5 passed
   Duration: 3.21s

✅ PASSED Scenario C: Real MCP Integration
   Tests: 4/4 passed
   Duration: 0.12s

✅ PASSED Scenario D: End-to-End Use Cases
   Tests: 4/4 passed
   Duration: 5.43s

============================================================
Overall: 17/17 tests passed
Total Duration: 15.45s
============================================================
```

## 安全注意事項

### API Key 保護
- `.env` 文件已添加到 `.gitignore`
- 不要在公開代碼中暴露 API Key
- 定期輪換 API Key

### 工具執行限制
- 命令執行工具只允許特定命令前綴
- 計算器使用安全的 AST 解析（非 eval）
- 文件操作限制在臨時目錄

## 費用估算

| 場景 | 預估 Token | 預估費用 (Haiku 4.5) |
|------|-----------|---------------------|
| A: LLM Conversation | ~2000 | ~$0.002 |
| B: Tool Execution | ~1500 | ~$0.0015 |
| C: MCP Integration | ~500 | ~$0.0005 |
| D: E2E Use Cases | ~3000 | ~$0.003 |
| **Total** | **~7000** | **~$0.007** |

*費用基於 Claude Haiku 4.5 定價估算（比 Sonnet 便宜約 20 倍）*

## 故障排除

### API Key 錯誤
```
❌ Configuration error: ANTHROPIC_API_KEY is required
```
解決：確保 `.env` 文件存在且包含有效的 API Key

### 模組未安裝
```
❌ anthropic package not installed
```
解決：`pip install anthropic`

### 網路連接問題
```
❌ Failed to initialize Anthropic client
```
解決：檢查網路連接和防火牆設置

---

**Version**: Real Functional v1.0
**Created**: 2025-12-27
