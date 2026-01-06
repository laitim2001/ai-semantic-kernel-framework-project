# Sprint 61 Checklist: AG-UI Frontend Integration & E2E Testing

## Pre-Sprint Setup

- [x] 確認 Sprint 60 已完成
- [x] 確認 useSharedState Hook 可用
- [x] 確認 useOptimisticState Hook 可用
- [x] 確認 AG-UI Types 已定義
- [x] 確認後端 AG-UI API 可用
- [x] 建立 UAT 測試規格文檔 (Phase F)
- [x] 建立 Python UAT 腳本框架

---

## S61-1: useAGUI 主 Hook (8 pts) ✅ 已完成

### 檔案建立
- [x] `frontend/src/hooks/useAGUI.ts`
  - [x] `UseAGUIOptions` 介面
  - [x] `UseAGUIReturn` 介面
  - [x] SSE 連接管理 (EventSource)
  - [x] 連接狀態追蹤 (connectionStatus)
  - [x] 消息狀態管理 (messages, addUserMessage)
  - [x] 工具調用追蹤 (toolCalls, getToolCall)
  - [x] 待審批管理 (pendingApprovals)
  - [x] 審批操作 (approveToolCall, rejectToolCall)
  - [x] 執行控制 (runAgent, cancelRun)
  - [x] 運行狀態 (runState, isRunning)
  - [x] 整合 useSharedState
  - [x] 整合 useOptimisticState
  - [x] 自動重連機制

### 類型擴展
- [x] `frontend/src/types/ag-ui.ts`
  - [x] `ChatMessage` 類型
  - [x] `ToolCallState` 類型
  - [x] `ToolCallStatus` 類型
  - [x] `PendingApproval` 類型
  - [x] `RiskLevel` 類型
  - [x] `RunAgentInput` 類型
  - [x] `ToolDefinition` 類型
  - [x] `SSEConnectionStatus` 類型
  - [x] `RunStatus` 類型
  - [x] `AGUIRunState` 類型

### 導出更新
- [x] `frontend/src/hooks/index.ts`
  - [x] 導出 useAGUI
  - [x] 導出相關類型

### 驗證
- [x] Hook 可正確導入
- [x] TypeScript 編譯通過
- [x] SSE 事件類型正確處理

---

## S61-2: Chat 組件 (8 pts)

### 檔案建立
- [ ] `frontend/src/components/ag-ui/chat/index.ts`
- [ ] `frontend/src/components/ag-ui/chat/ChatContainer.tsx`
  - [ ] 消息列表渲染
  - [ ] 工具調用內嵌顯示
  - [ ] 串流狀態指示
  - [ ] 錯誤處理
- [ ] `frontend/src/components/ag-ui/chat/MessageBubble.tsx`
  - [ ] User 消息樣式
  - [ ] Assistant 消息樣式
  - [ ] System 消息樣式
  - [ ] Tool 消息樣式
  - [ ] 時間戳顯示
- [ ] `frontend/src/components/ag-ui/chat/MessageInput.tsx`
  - [ ] 多行輸入支持
  - [ ] 發送按鈕
  - [ ] Enter 發送 / Shift+Enter 換行
  - [ ] 禁用狀態 (串流中)
- [ ] `frontend/src/components/ag-ui/chat/ToolCallCard.tsx`
  - [ ] 工具名稱顯示
  - [ ] 參數顯示 (JSON 格式化)
  - [ ] 執行狀態標籤
  - [ ] 結果顯示
  - [ ] 錯誤顯示
- [ ] `frontend/src/components/ag-ui/chat/StreamingIndicator.tsx`
  - [ ] 打字動畫
  - [ ] 脈動效果

### 測試
- [ ] ChatContainer 渲染測試
- [ ] MessageBubble 各角色測試
- [ ] MessageInput 交互測試
- [ ] ToolCallCard 狀態測試

### 驗證
- [ ] 消息正確渲染
- [ ] 工具調用卡片正確顯示
- [ ] 串流指示器正確動畫
- [ ] 輸入框功能正常

---

## S61-3: HITL 審批組件 (5 pts)

### 檔案建立
- [ ] `frontend/src/components/ag-ui/hitl/index.ts`
- [ ] `frontend/src/components/ag-ui/hitl/ApprovalDialog.tsx`
  - [ ] 模態框佈局
  - [ ] 工具名稱和參數顯示
  - [ ] 風險等級顯示
  - [ ] 風險理由顯示
  - [ ] 批准按鈕
  - [ ] 拒絕按鈕
  - [ ] 超時倒計時
- [ ] `frontend/src/components/ag-ui/hitl/ApprovalBanner.tsx`
  - [ ] 內嵌提示樣式
  - [ ] 簡潔信息顯示
  - [ ] 快速操作按鈕
- [ ] `frontend/src/components/ag-ui/hitl/RiskBadge.tsx`
  - [ ] Low 樣式 (綠色)
  - [ ] Medium 樣式 (黃色)
  - [ ] High 樣式 (橙色)
  - [ ] Critical 樣式 (紅色)
- [ ] `frontend/src/components/ag-ui/hitl/ApprovalList.tsx`
  - [ ] 列表佈局
  - [ ] 排序 (按時間/風險)
  - [ ] 批量操作支持

### 測試
- [ ] ApprovalDialog 開啟/關閉測試
- [ ] 批准/拒絕操作測試
- [ ] RiskBadge 各等級測試
- [ ] 超時處理測試

### 驗證
- [ ] 對話框正確顯示
- [ ] 風險等級樣式正確
- [ ] 操作回調正確觸發
- [ ] 超時倒計時正確

---

## S61-4: AG-UI Demo 頁面 (10 pts)

### 檔案建立
- [ ] `frontend/src/pages/ag-ui/AGUIDemoPage.tsx`
  - [ ] Tab 導航 (7 個功能)
  - [ ] 響應式佈局 (8+4 cols)
  - [ ] 狀態欄顯示
- [ ] `frontend/src/pages/ag-ui/components/index.ts`
- [ ] `frontend/src/pages/ag-ui/components/AgenticChatDemo.tsx`
  - [ ] 基本對話功能
  - [ ] 消息歷史顯示
- [ ] `frontend/src/pages/ag-ui/components/ToolRenderingDemo.tsx`
  - [ ] 代碼結果語法高亮
  - [ ] JSON 結果格式化
  - [ ] 錯誤結果顯示
- [ ] `frontend/src/pages/ag-ui/components/HITLDemo.tsx`
  - [ ] 觸發審批場景
  - [ ] 審批操作演示
- [ ] `frontend/src/pages/ag-ui/components/GenerativeUIDemo.tsx`
  - [ ] 進度指示器演示
  - [ ] 模式切換動畫
- [ ] `frontend/src/pages/ag-ui/components/ToolUIDemo.tsx`
  - [ ] 表單生成演示
  - [ ] 圖表生成演示
  - [ ] 卡片生成演示
  - [ ] 表格生成演示
- [ ] `frontend/src/pages/ag-ui/components/SharedStateDemo.tsx`
  - [ ] 狀態顯示
  - [ ] 手動更新
  - [ ] 同步狀態
- [ ] `frontend/src/pages/ag-ui/components/PredictiveDemo.tsx`
  - [ ] 樂觀更新演示
  - [ ] 回滾演示
- [ ] `frontend/src/pages/ag-ui/components/EventLogPanel.tsx`
  - [ ] 事件列表
  - [ ] 事件過濾
  - [ ] 事件詳情展開

### 路由配置
- [ ] `frontend/src/App.tsx` 添加 `/ag-ui-demo` 路由

### 驗證
- [ ] 頁面可訪問 (/ag-ui-demo)
- [ ] 所有 Tab 可切換
- [ ] 事件日誌正確顯示
- [ ] 響應式佈局正確

---

## S61-5: Playwright E2E 測試 (7 pts)

### 測試工具建立
- [ ] `frontend/e2e/ag-ui/fixtures.ts`
  - [ ] AGUITestPage 類別
  - [ ] 常用操作封裝
  - [ ] 斷言輔助函數

### 功能測試建立
- [ ] `frontend/e2e/ag-ui/agentic-chat.spec.ts`
  - [ ] 發送消息測試
  - [ ] 接收串流響應測試
  - [ ] 消息列表顯示測試
- [ ] `frontend/e2e/ag-ui/tool-rendering.spec.ts`
  - [ ] 代碼結果渲染測試
  - [ ] JSON 結果渲染測試
  - [ ] 錯誤結果渲染測試
- [ ] `frontend/e2e/ag-ui/hitl.spec.ts`
  - [ ] 審批對話框觸發測試
  - [ ] 批准操作測試
  - [ ] 拒絕操作測試
  - [ ] 超時處理測試
- [ ] `frontend/e2e/ag-ui/generative-ui.spec.ts`
  - [ ] 進度指示器測試
  - [ ] 模式切換測試
- [ ] `frontend/e2e/ag-ui/tool-ui.spec.ts`
  - [ ] 表單驗證測試
  - [ ] 圖表渲染測試
  - [ ] 表格排序測試
- [ ] `frontend/e2e/ag-ui/shared-state.spec.ts`
  - [ ] 狀態同步測試
  - [ ] 衝突解決測試
- [ ] `frontend/e2e/ag-ui/predictive-state.spec.ts`
  - [ ] 樂觀更新測試
  - [ ] 回滾動畫測試
- [ ] `frontend/e2e/ag-ui/integration.spec.ts`
  - [ ] 完整對話流程測試
  - [ ] 多功能組合測試

### 驗證
- [ ] 所有 E2E 測試通過
- [ ] 測試覆蓋所有 7 個功能
- [ ] 測試可重複執行

---

## S61-6: Backend Test Endpoints for Feature 4 & 5 (5 pts) ✅ 已完成

### 檔案修改
- [x] `backend/src/api/v1/ag_ui/schemas.py`
  - [x] `TestWorkflowProgressRequest` schema
  - [x] `TestWorkflowProgressResponse` schema
  - [x] `TestModeSwitchRequest` schema
  - [x] `TestModeSwitchResponse` schema
  - [x] `TestUIComponentRequest` schema
  - [x] `TestUIComponentResponse` schema
- [x] `backend/src/api/v1/ag_ui/routes.py`
  - [x] `POST /test/progress` 端點
  - [x] `POST /test/mode-switch` 端點
  - [x] `POST /test/ui-component` 端點
- [x] `scripts/uat/phase_tests/phase_15_ag_ui/phase_15_ag_ui_test.py`
  - [x] Feature 4 測試更新 (使用 /test/progress, /test/mode-switch)
  - [x] Feature 5 測試更新 (使用 /test/ui-component)

### 驗證
- [x] 測試端點可正常調用
- [x] 返回正確的 AG-UI 事件
- [x] UAT 測試 16/17 通過 (94.1%), 1 skipped (需要真實工具執行)

---

## Quality Gates

### 代碼品質 (前端)
- [ ] `npm run lint` 通過
- [ ] `npm run build` 成功
- [ ] TypeScript 類型檢查通過

### 測試品質
- [ ] 組件測試全部通過
- [ ] E2E 測試全部通過

### 可訪問性
- [ ] 所有組件有 data-testid
- [ ] 關鍵元素有 ARIA labels
- [ ] 鍵盤導航支持

### Phase 15 完成驗證
- [ ] 所有 Sprint 61 Stories 完成
- [ ] Demo 頁面可正常使用
- [ ] E2E 測試全部通過

---

## Notes

```
Sprint 61 開始日期: 2026-01-06
Sprint 61 結束日期: TBD
計劃點數: 43 pts (38 原始 + 5 S61-6)
已完成: 13 pts (S61-1: 8 pts + S61-6: 5 pts)
待完成: 30 pts (S61-2 ~ S61-5)
```
