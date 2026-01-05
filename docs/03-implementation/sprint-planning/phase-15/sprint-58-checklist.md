# Sprint 58 Checklist: AG-UI Core Infrastructure

## Pre-Sprint Setup

- [ ] 確認 Phase 14 已完成
- [ ] 確認 HybridOrchestratorV2 可用
- [ ] 建立 `backend/src/api/v1/ag_ui/` 目錄結構
- [ ] 建立 `backend/src/integrations/ag_ui/` 目錄結構

---

## S58-1: AG-UI SSE Endpoint (10 pts)

### 檔案建立
- [ ] `backend/src/api/v1/ag_ui/__init__.py`
- [ ] `backend/src/api/v1/ag_ui/routes.py`
  - [ ] `POST /api/v1/ag-ui` 主端點
  - [ ] SSE StreamingResponse 實現
  - [ ] CORS headers 設定
- [ ] `backend/src/api/v1/ag_ui/schemas.py`
  - [ ] `RunAgentInput` Pydantic 模型
  - [ ] `AGUIMessage` 模型
  - [ ] `AGUITool` 模型
- [ ] `backend/src/api/v1/ag_ui/dependencies.py`
  - [ ] `get_event_bridge()` 依賴
  - [ ] `get_thread_manager()` 依賴

### API 註冊
- [ ] 修改 `backend/src/api/v1/__init__.py` 註冊 ag_ui router

### 測試
- [ ] `backend/tests/unit/api/v1/ag_ui/test_routes.py`
- [ ] SSE 格式測試
- [ ] 請求驗證測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 端點返回 `text/event-stream` content-type
- [ ] SSE 格式正確 (`data: {...}\n\n`)
- [ ] CORS headers 正確設定

---

## S58-2: HybridEventBridge (10 pts)

### 檔案建立
- [ ] `backend/src/integrations/ag_ui/__init__.py`
- [ ] `backend/src/integrations/ag_ui/bridge.py`
  - [ ] `HybridEventBridge` 類別
  - [ ] `stream_events()` async generator
  - [ ] `_format_sse()` 方法
- [ ] `backend/src/integrations/ag_ui/converters.py`
  - [ ] `EventConverters` 類別
  - [ ] `convert()` 方法
  - [ ] `to_run_started()` 方法
  - [ ] `to_run_finished()` 方法
  - [ ] `to_text_message_start()` 方法
  - [ ] `to_text_message_content()` 方法
  - [ ] `to_text_message_end()` 方法
  - [ ] `to_tool_call_start()` 方法
  - [ ] `to_tool_call_args()` 方法
  - [ ] `to_tool_call_end()` 方法

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/test_bridge.py`
- [ ] `backend/tests/unit/integrations/ag_ui/test_converters.py`
- [ ] 事件轉換測試
- [ ] 串流測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] Hybrid 事件正確轉換為 AG-UI 事件
- [ ] 事件順序正確 (RUN_STARTED → ... → RUN_FINISHED)
- [ ] 錯誤處理正確

---

## S58-3: Thread Manager (5 pts)

### 檔案建立
- [ ] `backend/src/integrations/ag_ui/thread/__init__.py`
- [ ] `backend/src/integrations/ag_ui/thread/models.py`
  - [ ] `AGUIThread` dataclass
  - [ ] `AGUIMessage` dataclass
  - [ ] `ThreadStatus` 枚舉
- [ ] `backend/src/integrations/ag_ui/thread/manager.py`
  - [ ] `ThreadManager` 類別
  - [ ] `get_or_create()` 方法
  - [ ] `append_messages()` 方法
  - [ ] `update_state()` 方法
  - [ ] `delete()` 方法
- [ ] `backend/src/integrations/ag_ui/thread/storage.py`
  - [ ] `ThreadRepository` 類別
  - [ ] `ThreadCache` 類別

### API 端點
- [ ] 在 `backend/src/api/v1/ag_ui/routes.py` 添加:
  - [ ] `GET /api/v1/ag-ui/threads/{thread_id}`
  - [ ] `DELETE /api/v1/ag-ui/threads/{thread_id}`

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/thread/test_manager.py`
- [ ] `backend/tests/unit/integrations/ag_ui/thread/test_storage.py`
- [ ] Redis 緩存測試
- [ ] PostgreSQL 持久化測試

### 驗證
- [ ] Thread 正確創建和獲取
- [ ] 多 Run 共用同一 Thread
- [ ] Write-Through 策略正確

---

## S58-4: AG-UI Event Types (5 pts)

### 檔案建立
- [ ] `backend/src/integrations/ag_ui/events/__init__.py`
- [ ] `backend/src/integrations/ag_ui/events/base.py`
  - [ ] `AGUIEventType` 枚舉
  - [ ] `BaseAGUIEvent` 基類
- [ ] `backend/src/integrations/ag_ui/events/lifecycle.py`
  - [ ] `RunStartedEvent` 模型
  - [ ] `RunFinishedEvent` 模型
- [ ] `backend/src/integrations/ag_ui/events/message.py`
  - [ ] `TextMessageStartEvent` 模型
  - [ ] `TextMessageContentEvent` 模型
  - [ ] `TextMessageEndEvent` 模型
- [ ] `backend/src/integrations/ag_ui/events/tool.py`
  - [ ] `ToolCallStartEvent` 模型
  - [ ] `ToolCallArgsEvent` 模型
  - [ ] `ToolCallEndEvent` 模型
- [ ] `backend/src/integrations/ag_ui/events/state.py`
  - [ ] `StateSnapshotEvent` 模型
  - [ ] `StateDeltaEvent` 模型
  - [ ] `CustomEvent` 模型

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/events/test_base.py`
- [ ] `backend/tests/unit/integrations/ag_ui/events/test_message.py`
- [ ] `backend/tests/unit/integrations/ag_ui/events/test_tool.py`
- [ ] JSON 序列化測試
- [ ] 類型驗證測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 所有事件可正確序列化為 JSON
- [ ] Literal type 正確驗證
- [ ] timestamp 自動生成

---

## Quality Gates

### 代碼品質
- [ ] `black .` 格式化通過
- [ ] `isort .` 導入排序通過
- [ ] `flake8 .` 無錯誤
- [ ] `mypy .` 類型檢查通過

### 測試品質
- [ ] 單元測試全部通過
- [ ] 覆蓋率 > 85%

### 整合測試
- [ ] SSE 端點完整流程測試
- [ ] Thread 持久化測試
- [ ] 錯誤處理測試

---

## Notes

```
Sprint 58 開始日期: ___________
Sprint 58 結束日期: ___________
實際完成點數: ___ / 30 pts
```
