# Sprint 105 Checklist: OrchestrationPanel 整合 + 狀態管理

## 開發任務

### Story 105-1: Swarm Zustand Store
- [ ] 創建 `frontend/src/stores/swarmStore.ts`
- [ ] 定義 SwarmState 接口
- [ ] 實現 setSwarmStatus action
- [ ] 實現 updateWorkerProgress action
- [ ] 實現 updateWorkerThinking action
- [ ] 實現 updateWorkerToolCall action
- [ ] 實現 completeWorker action
- [ ] 實現 selectWorker action
- [ ] 實現 setWorkerDetail action
- [ ] 實現 openDrawer/closeDrawer actions
- [ ] 實現 reset action
- [ ] 配置 immer middleware
- [ ] 配置 devtools middleware

### Story 105-2: 擴展 OrchestrationPanel
- [ ] 修改 `OrchestrationPanel.tsx`
- [ ] 導入 AgentSwarmPanel
- [ ] 導入 WorkerDetailDrawer
- [ ] 使用 useSwarmStore
- [ ] 實現 handleWorkerClick
- [ ] 實現 handleDrawerClose
- [ ] 整合 AgentSwarmPanel 到面板
- [ ] 整合 WorkerDetailDrawer
- [ ] 測試響應式佈局

### Story 105-3: SSE 事件處理整合
- [ ] 修改 `useAgentExecution.ts`
- [ ] 整合 useSwarmEvents hook
- [ ] 處理 onSwarmCreated
- [ ] 處理 onSwarmStatusUpdate
- [ ] 處理 onSwarmCompleted
- [ ] 處理 onWorkerStarted
- [ ] 處理 onWorkerProgress
- [ ] 處理 onWorkerThinking
- [ ] 處理 onWorkerToolCall
- [ ] 處理 onWorkerCompleted
- [ ] 測試事件流

### Story 105-4: useSwarmStatus Hook
- [ ] 創建 `hooks/useSwarmStatus.ts`
- [ ] 封裝 store 訪問
- [ ] 實現 isSwarmActive 計算屬性
- [ ] 實現 completedWorkers 計算屬性
- [ ] 實現 runningWorkers 計算屬性
- [ ] 實現 failedWorkers 計算屬性
- [ ] 實現 handleWorkerSelect
- [ ] 實現 handleDrawerClose

### Story 105-5: 組件通信優化
- [ ] 添加必要的 useMemo
- [ ] 添加必要的 useCallback
- [ ] 實現選擇性訂閱
- [ ] 優化批量更新
- [ ] 使用 React DevTools 驗證

### Story 105-6: 單元測試與整合測試
- [ ] 創建 `stores/__tests__/swarmStore.test.ts`
- [ ] 測試所有 actions
- [ ] 測試狀態更新
- [ ] 創建整合測試
- [ ] 測試事件處理流程

## 品質檢查

### 代碼品質
- [ ] ESLint 檢查通過
- [ ] Prettier 格式化通過
- [ ] TypeScript 編譯通過
- [ ] 無 any 類型

### 測試
- [ ] 單元測試覆蓋率 > 85%
- [ ] 所有測試通過
- [ ] 整合測試通過

### 性能
- [ ] React DevTools 無警告
- [ ] 無不必要的重渲染
- [ ] 狀態更新流暢

## 驗收標準

- [ ] Store 正確定義和工作
- [ ] OrchestrationPanel 整合成功
- [ ] SSE 事件正確處理
- [ ] 組件間通信正常
- [ ] 無記憶體洩漏
- [ ] 測試覆蓋率達標

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 25
**開始日期**: 2026-03-06
