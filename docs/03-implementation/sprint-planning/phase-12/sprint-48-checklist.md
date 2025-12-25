# Sprint 48 Checklist: Core SDK Integration - Claude Agent SDK 核心整合

**Sprint 目標**: 實現 Claude Agent SDK 核心功能
**週期**: Week 1-2
**總點數**: 35 點
**狀態**: 📋 計劃中 (0/35 點)

---

## 快速驗證命令

```bash
# 啟動服務
cd backend
uvicorn main:app --reload --port 8000

# 執行單元測試
pytest tests/unit/integrations/claude_sdk/ -v

# 執行整合測試
pytest tests/integration/claude_sdk/ -v

# 測試 API 端點
curl -X POST http://localhost:8000/api/v1/claude-sdk/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"prompt": "What is 2+2?"}'

# 檢查型別
mypy src/integrations/claude_sdk/
```

---

## S48-1: ClaudeSDKClient 核心封裝 (10 點) 📋

### 檔案結構
- [ ] 建立 `backend/src/integrations/claude_sdk/` 目錄
- [ ] 建立 `backend/src/integrations/claude_sdk/__init__.py`
- [ ] 建立 `backend/src/integrations/claude_sdk/client.py`
- [ ] 建立 `backend/src/integrations/claude_sdk/config.py`
- [ ] 建立 `backend/src/integrations/claude_sdk/exceptions.py`

### ClaudeSDKClient 實現
- [ ] `ClaudeSDKClient.__init__()` 支援 api_key 參數
- [ ] `ClaudeSDKClient.__init__()` 支援 model 參數
- [ ] `ClaudeSDKClient.__init__()` 支援 max_tokens 參數
- [ ] `ClaudeSDKClient.__init__()` 支援 timeout 參數
- [ ] `ClaudeSDKClient.__init__()` 支援 system_prompt 參數
- [ ] `ClaudeSDKClient.__init__()` 支援 tools 參數
- [ ] `ClaudeSDKClient.__init__()` 支援 hooks 參數
- [ ] `ClaudeSDKClient.__init__()` 支援 mcp_servers 參數

### 配置管理
- [ ] `ClaudeSDKConfig` 從環境變數讀取 API Key
- [ ] `ClaudeSDKConfig` 從環境變數讀取模型設定
- [ ] `ClaudeSDKConfig.from_env()` 方法實現
- [ ] `ClaudeSDKConfig.from_yaml()` 方法實現

### 異常類別
- [ ] `ClaudeSDKError` 基礎異常類別
- [ ] `AuthenticationError` 認證錯誤
- [ ] `RateLimitError` 速率限制錯誤
- [ ] `TimeoutError` 超時錯誤
- [ ] `ToolError` 工具執行錯誤
- [ ] `HookRejectionError` Hook 拒絕錯誤
- [ ] `MCPError` MCP 相關錯誤
- [ ] `MCPConnectionError` MCP 連接錯誤
- [ ] `MCPToolError` MCP 工具錯誤

### 測試
- [ ] `test_client_init_with_api_key` 通過
- [ ] `test_client_init_from_env` 通過
- [ ] `test_client_init_missing_key_raises_error` 通過
- [ ] `test_config_from_yaml` 通過

---

## S48-2: Query API 實現 (8 點) 📋

### Query 模組
- [ ] 建立 `backend/src/integrations/claude_sdk/query.py`
- [ ] 建立 `backend/src/integrations/claude_sdk/types.py`

### QueryResult 類別
- [ ] `QueryResult.content` 屬性
- [ ] `QueryResult.tool_calls` 屬性
- [ ] `QueryResult.tokens_used` 屬性
- [ ] `QueryResult.duration` 屬性
- [ ] `QueryResult.status` 屬性
- [ ] `QueryResult.successful` 屬性

### execute_query 函數
- [ ] 接受 prompt 參數
- [ ] 接受 tools 參數
- [ ] 接受 max_tokens 參數
- [ ] 接受 timeout 參數
- [ ] 接受 working_directory 參數
- [ ] 實現 agentic loop (工具調用循環)
- [ ] 正確累計 token 使用量
- [ ] 超時處理實現
- [ ] 錯誤處理實現

### 型別定義
- [ ] `ToolCall` dataclass 定義
- [ ] `Message` dataclass 定義
- [ ] `ToolCallContext` dataclass 定義
- [ ] `ToolResultContext` dataclass 定義
- [ ] `QueryContext` dataclass 定義
- [ ] `HookResult` 類別定義

### 測試
- [ ] `test_query_returns_result` 通過
- [ ] `test_query_with_tools` 通過
- [ ] `test_query_timeout` 通過
- [ ] `test_query_error_handling` 通過

---

## S48-3: Session 管理實現 (10 點) 📋

### Session 模組
- [ ] 建立 `backend/src/integrations/claude_sdk/session.py`

### Session 類別
- [ ] `Session.__init__()` 實現
- [ ] `Session.session_id` 屬性
- [ ] `Session.is_closed` 屬性
- [ ] `Session.get_history()` 方法
- [ ] `Session.get_context()` 方法
- [ ] `Session.add_context()` 方法
- [ ] `Session.query()` 方法
- [ ] `Session.fork()` 方法
- [ ] `Session.close()` 方法

### SessionResponse 類別
- [ ] `SessionResponse.content` 屬性
- [ ] `SessionResponse.tool_calls` 屬性
- [ ] `SessionResponse.tokens_used` 屬性
- [ ] `SessionResponse.message_index` 屬性

### 歷史管理
- [ ] 用戶訊息正確加入歷史
- [ ] 助理回應正確加入歷史
- [ ] 工具調用記錄在歷史中
- [ ] `_build_messages()` 正確構建 API 訊息

### Hook 整合
- [ ] `on_session_start` 在建立時觸發
- [ ] `on_query_start` 在查詢前觸發
- [ ] `on_tool_call` 在工具調用前觸發
- [ ] `on_tool_result` 在工具完成後觸發
- [ ] `on_query_end` 在查詢完成後觸發
- [ ] `on_session_end` 在關閉時觸發

### ClaudeSDKClient Session 方法
- [ ] `create_session()` 方法實現
- [ ] `resume_session()` 方法實現
- [ ] Session 儲存在 `_sessions` 字典中

### 測試
- [ ] `test_create_session` 通過
- [ ] `test_session_query` 通過
- [ ] `test_session_history` 通過
- [ ] `test_session_fork` 通過
- [ ] `test_session_close` 通過
- [ ] `test_session_context` 通過

---

## S48-4: API 端點整合 (7 點) 📋

### API 路由
- [ ] 建立 `backend/src/api/v1/claude_sdk/` 目錄
- [ ] 建立 `backend/src/api/v1/claude_sdk/__init__.py`
- [ ] 建立 `backend/src/api/v1/claude_sdk/routes.py`
- [ ] 建立 `backend/src/api/v1/claude_sdk/schemas.py`

### 端點實現
- [ ] `POST /api/v1/claude-sdk/query` 端點
- [ ] `POST /api/v1/claude-sdk/sessions` 端點
- [ ] `POST /api/v1/claude-sdk/sessions/{id}/query` 端點
- [ ] `DELETE /api/v1/claude-sdk/sessions/{id}` 端點
- [ ] `GET /api/v1/claude-sdk/sessions/{id}/history` 端點

### Request/Response Schema
- [ ] `QueryRequest` schema
- [ ] `QueryResponse` schema
- [ ] `CreateSessionRequest` schema
- [ ] `SessionResponse` schema
- [ ] `SessionQueryRequest` schema
- [ ] `SessionQueryResponse` schema

### 整合
- [ ] 路由註冊到 FastAPI app
- [ ] 認證中間件整合
- [ ] 錯誤處理整合

### 測試
- [ ] `test_query_endpoint` 通過
- [ ] `test_create_session_endpoint` 通過
- [ ] `test_session_query_endpoint` 通過
- [ ] `test_close_session_endpoint` 通過
- [ ] `test_session_history_endpoint` 通過

---

## 測試完成

### 單元測試
- [ ] `tests/unit/integrations/claude_sdk/test_client.py`
- [ ] `tests/unit/integrations/claude_sdk/test_query.py`
- [ ] `tests/unit/integrations/claude_sdk/test_session.py`
- [ ] `tests/unit/integrations/claude_sdk/test_config.py`
- [ ] `tests/unit/integrations/claude_sdk/test_exceptions.py`

### 整合測試
- [ ] `tests/integration/claude_sdk/test_api.py`

### 覆蓋率
- [ ] 單元測試覆蓋率 ≥ 85%
- [ ] 整合測試覆蓋率 ≥ 70%

---

## 文檔完成

- [ ] API 文檔更新 (OpenAPI)
- [ ] Claude SDK 使用說明
- [ ] 配置指南
- [ ] 錯誤代碼參考

---

## Sprint 完成標準

- [ ] 所有 checkbox 完成
- [ ] 所有測試通過
- [ ] Code Review 完成
- [ ] 無 Critical/High Bug
- [ ] 文檔更新完成

---

## 依賴確認

### 外部依賴
- [ ] `anthropic` Python SDK 安裝
- [ ] `ANTHROPIC_API_KEY` 環境變數配置
- [ ] Redis 服務運行中

### 內部依賴
- [ ] Phase 11 Agent-Session Integration 完成
- [ ] 認證系統正常運作

---

## 完成統計表

| Story | 點數 | 狀態 | 完成日期 |
|-------|------|------|----------|
| S48-1 | 10 | 📋 | - |
| S48-2 | 8 | 📋 | - |
| S48-3 | 10 | 📋 | - |
| S48-4 | 7 | 📋 | - |
| **總計** | **35** | **0%** | - |
