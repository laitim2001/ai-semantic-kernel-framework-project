# Sprint 59 Checklist: AG-UI Basic Features (1-4)

## Pre-Sprint Setup

- [ ] 確認 Sprint 58 已完成
- [ ] 確認 HybridEventBridge 可用
- [ ] 確認 Thread Manager 可用
- [ ] 確認 AG-UI Event Types 可用
- [ ] 建立 `backend/src/integrations/ag_ui/features/` 目錄結構
- [ ] 建立 `frontend/src/components/ag-ui/` 目錄結構

---

## S59-1: Agentic Chat (7 pts)

### 檔案建立 (後端)
- [ ] `backend/src/integrations/ag_ui/features/__init__.py`
- [ ] `backend/src/integrations/ag_ui/features/agentic_chat.py`
  - [ ] `AgenticChatHandler` 類別
  - [ ] `handle_chat()` async generator 方法
  - [ ] 整合 `HybridOrchestratorV2`
  - [ ] 整合 `HybridEventBridge`

### 檔案建立 (前端)
- [ ] `frontend/src/components/ag-ui/AgentChat.tsx`
  - [ ] 訊息列表渲染
  - [ ] 載入狀態顯示
  - [ ] 整合 `useAGUI` Hook
- [ ] `frontend/src/components/ag-ui/Message.tsx`
  - [ ] 用戶訊息樣式
  - [ ] 助理訊息樣式
  - [ ] 工具調用內嵌顯示
- [ ] `frontend/src/components/ag-ui/ChatInput.tsx`
  - [ ] 輸入框組件
  - [ ] 發送按鈕
  - [ ] disabled 狀態
- [ ] `frontend/src/components/ag-ui/index.ts`
- [ ] `frontend/src/hooks/useAGUI.ts`
  - [ ] `messages` 狀態
  - [ ] `sendMessage()` 方法
  - [ ] `isLoading` 狀態
  - [ ] SSE 連接管理
- [ ] `frontend/src/providers/AGUIProvider.tsx`

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/features/test_agentic_chat.py`
- [ ] `frontend/tests/components/ag-ui/AgentChat.test.tsx`
- [ ] SSE 串流測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 訊息正確串流顯示
- [ ] 工具調用正確內嵌
- [ ] 載入狀態正確切換

---

## S59-2: Backend Tool Rendering (7 pts)

### 檔案建立 (後端)
- [ ] `backend/src/integrations/ag_ui/features/tool_rendering.py`
  - [ ] `ToolRenderingHandler` 類別
  - [ ] `execute_and_format()` 方法
  - [ ] `_detect_result_type()` 方法
  - [ ] `_format_result()` 方法
  - [ ] 整合 `UnifiedToolExecutor`

### 檔案建立 (前端)
- [ ] `frontend/src/components/ag-ui/ToolResultRenderer.tsx`
  - [ ] text 類型渲染
  - [ ] json 類型渲染
  - [ ] table 類型渲染
  - [ ] image 類型渲染
- [ ] `frontend/src/components/ag-ui/ToolExecutingIndicator.tsx`
- [ ] `frontend/src/components/ag-ui/ToolErrorDisplay.tsx`

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/features/test_tool_rendering.py`
- [ ] `frontend/tests/components/ag-ui/ToolResultRenderer.test.tsx`
- [ ] 各種結果類型測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 結果類型正確檢測
- [ ] 各類型正確渲染
- [ ] 錯誤狀態正確顯示

---

## S59-3: Human-in-the-Loop (8 pts)

### 檔案建立 (後端)
- [ ] `backend/src/integrations/ag_ui/features/human_in_loop.py`
  - [ ] `HITLHandler` 類別
  - [ ] `check_approval_needed()` 方法
  - [ ] `create_approval_event()` 方法
  - [ ] `handle_approval_response()` 方法
  - [ ] `ApprovalStorage` 類別
  - [ ] 整合 `RiskAssessmentEngine`

### API 端點
- [ ] 修改 `backend/src/api/v1/ag_ui/routes.py`
  - [ ] `POST /api/v1/ag-ui/approvals/{id}/approve`
  - [ ] `POST /api/v1/ag-ui/approvals/{id}/reject`
  - [ ] `GET /api/v1/ag-ui/approvals/pending`

### 檔案建立 (前端)
- [ ] `frontend/src/components/ag-ui/ApprovalDialog.tsx`
  - [ ] 風險等級 Badge 顯示
  - [ ] 工具名稱顯示
  - [ ] 參數 JSON 顯示
  - [ ] 風險評估原因顯示
  - [ ] 批准按鈕
  - [ ] 拒絕按鈕
  - [ ] 處理中狀態

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/features/test_human_in_loop.py`
- [ ] `backend/tests/unit/api/v1/ag_ui/test_approval_routes.py`
- [ ] `frontend/tests/components/ag-ui/ApprovalDialog.test.tsx`
- [ ] 審批流程 E2E 測試
- [ ] 超時處理測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 高風險操作觸發審批
- [ ] 審批/拒絕正確處理
- [ ] 超時正確觸發
- [ ] 風險等級正確顯示

---

## S59-4: Agentic Generative UI (6 pts)

### 檔案建立 (後端)
- [ ] `backend/src/integrations/ag_ui/features/generative_ui.py`
  - [ ] `GenerativeUIHandler` 類別
  - [ ] `emit_progress_event()` 方法
  - [ ] `emit_mode_switch_event()` 方法
  - [ ] 整合 `ModeSwitcher`

### 檔案建立 (前端)
- [ ] `frontend/src/components/ag-ui/ProgressIndicator.tsx`
  - [ ] 進度條組件
  - [ ] 步驟狀態圖標
  - [ ] 步驟名稱顯示
  - [ ] 進度百分比
- [ ] `frontend/src/components/ag-ui/ModeSwitchNotification.tsx`
  - [ ] 模式切換通知
  - [ ] 切換原因顯示

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/features/test_generative_ui.py`
- [ ] `frontend/tests/components/ag-ui/ProgressIndicator.test.tsx`
- [ ] 進度更新測試
- [ ] 模式切換測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 進度事件正確發送
- [ ] 進度條正確更新
- [ ] 模式切換通知正確顯示
- [ ] 步驟狀態正確切換

---

## Quality Gates

### 代碼品質 (後端)
- [ ] `black .` 格式化通過
- [ ] `isort .` 導入排序通過
- [ ] `flake8 .` 無錯誤
- [ ] `mypy .` 類型檢查通過

### 代碼品質 (前端)
- [ ] `npm run lint` 通過
- [ ] `npm run build` 成功
- [ ] TypeScript 類型檢查通過

### 測試品質
- [ ] 後端單元測試全部通過
- [ ] 前端組件測試全部通過
- [ ] 覆蓋率 > 85%

### 整合測試
- [ ] 完整對話流程 E2E 測試
- [ ] 工具執行渲染 E2E 測試
- [ ] 審批流程 E2E 測試
- [ ] 進度更新 E2E 測試

---

## Notes

```
Sprint 59 開始日期: ___________
Sprint 59 結束日期: ___________
實際完成點數: ___ / 28 pts
```
