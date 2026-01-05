# Sprint 60 Checklist: AG-UI Advanced Features (5-7) + Integration

## Pre-Sprint Setup

- [ ] 確認 Sprint 59 已完成
- [ ] 確認 AgenticChatHandler 可用
- [ ] 確認 ToolRenderingHandler 可用
- [ ] 確認 HITLHandler 可用
- [ ] 確認 GenerativeUIHandler 可用
- [ ] 建立 `backend/src/integrations/ag_ui/features/advanced/` 目錄結構
- [ ] 建立 `frontend/src/components/ag-ui/advanced/` 目錄結構

---

## S60-1: Tool-based Generative UI (8 pts)

### 檔案建立 (後端)
- [ ] `backend/src/integrations/ag_ui/features/advanced/__init__.py`
- [ ] `backend/src/integrations/ag_ui/features/advanced/tool_ui.py`
  - [ ] `UIComponentType` 枚舉 (form, chart, card, table, custom)
  - [ ] `UIComponentDefinition` dataclass
  - [ ] `ToolBasedUIHandler` 類別
  - [ ] `emit_ui_component()` 方法
  - [ ] `validate_component_schema()` 方法
  - [ ] `_build_component_event()` 方法
  - [ ] 整合 `CustomEvent`

### 檔案建立 (前端)
- [ ] `frontend/src/components/ag-ui/advanced/CustomUIRenderer.tsx`
  - [ ] 組件類型路由
  - [ ] Schema 驗證
  - [ ] 錯誤邊界處理
- [ ] `frontend/src/components/ag-ui/advanced/DynamicForm.tsx`
  - [ ] 動態表單生成
  - [ ] 表單驗證
  - [ ] 提交處理
- [ ] `frontend/src/components/ag-ui/advanced/DynamicChart.tsx`
  - [ ] 圖表類型選擇
  - [ ] 數據格式化
  - [ ] 響應式設計
- [ ] `frontend/src/components/ag-ui/advanced/DynamicCard.tsx`
  - [ ] 卡片佈局
  - [ ] 圖標渲染
  - [ ] 操作按鈕
- [ ] `frontend/src/components/ag-ui/advanced/DynamicTable.tsx`
  - [ ] 分頁功能
  - [ ] 排序功能
  - [ ] 篩選功能
- [ ] `frontend/src/components/ag-ui/advanced/index.ts`

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/features/advanced/test_tool_ui.py`
- [ ] `frontend/tests/components/ag-ui/advanced/CustomUIRenderer.test.tsx`
- [ ] `frontend/tests/components/ag-ui/advanced/DynamicForm.test.tsx`
- [ ] 組件渲染測試
- [ ] Schema 驗證測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] UI 組件正確渲染
- [ ] Schema 驗證正確執行
- [ ] 錯誤狀態正確顯示
- [ ] 各組件類型正確路由

---

## S60-2: Shared State (8 pts)

### 檔案建立 (後端)
- [ ] `backend/src/integrations/ag_ui/features/advanced/shared_state.py`
  - [ ] `SharedStateHandler` 類別
  - [ ] `emit_state_snapshot()` 方法
  - [ ] `emit_state_delta()` 方法
  - [ ] `StateSyncManager` 類別
  - [ ] `_diff_state()` 方法
  - [ ] `_merge_state()` 方法
  - [ ] 整合 `StateSnapshotEvent`
  - [ ] 整合 `StateDeltaEvent`

### API 端點
- [ ] 修改 `backend/src/api/v1/ag_ui/routes.py`
  - [ ] `GET /api/v1/ag-ui/threads/{thread_id}/state`
  - [ ] `PATCH /api/v1/ag-ui/threads/{thread_id}/state`

### 檔案建立 (前端)
- [ ] `frontend/src/hooks/useSharedState.ts`
  - [ ] `state` 狀態
  - [ ] `updateState()` 方法
  - [ ] `subscribeToUpdates()` 方法
  - [ ] 自動同步邏輯
- [ ] `frontend/src/components/ag-ui/advanced/StateDebugger.tsx`
  - [ ] 狀態顯示
  - [ ] 變更歷史
  - [ ] 即時更新

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/features/advanced/test_shared_state.py`
- [ ] `backend/tests/unit/api/v1/ag_ui/test_state_routes.py`
- [ ] `frontend/tests/hooks/useSharedState.test.ts`
- [ ] Delta 計算測試
- [ ] 狀態合併測試
- [ ] 同步一致性測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] State Snapshot 正確發送
- [ ] State Delta 正確計算
- [ ] 前後端狀態同步
- [ ] 同步延遲 < 50ms

---

## S60-3: Predictive State Updates (6 pts)

### 檔案建立 (後端)
- [ ] `backend/src/integrations/ag_ui/features/advanced/predictive.py`
  - [ ] `PredictiveStateHandler` 類別
  - [ ] `predict_next_state()` 方法
  - [ ] `confirm_prediction()` 方法
  - [ ] `rollback_prediction()` 方法
  - [ ] `_calculate_confidence()` 方法
  - [ ] 整合 `StateDeltaEvent`

### 檔案建立 (前端)
- [ ] `frontend/src/hooks/useOptimisticState.ts`
  - [ ] `optimisticState` 狀態
  - [ ] `applyOptimistic()` 方法
  - [ ] `confirmOptimistic()` 方法
  - [ ] `rollbackOptimistic()` 方法
  - [ ] 版本追蹤
- [ ] `frontend/src/components/ag-ui/advanced/OptimisticIndicator.tsx`
  - [ ] 預測狀態顯示
  - [ ] 確認/回滾 UI

### 測試
- [ ] `backend/tests/unit/integrations/ag_ui/features/advanced/test_predictive.py`
- [ ] `frontend/tests/hooks/useOptimisticState.test.ts`
- [ ] 預測準確性測試
- [ ] 回滾機制測試
- [ ] 版本衝突處理測試
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 預測狀態正確應用
- [ ] 確認後正確合併
- [ ] 回滾後正確還原
- [ ] 回滾延遲 < 100ms

---

## S60-4: Integration & E2E Testing (5 pts)

### E2E 測試建立
- [ ] `backend/tests/e2e/ag_ui/test_full_flow.py`
  - [ ] 完整對話流程測試
  - [ ] 工具執行渲染測試
  - [ ] 審批流程測試
  - [ ] 進度更新測試
  - [ ] 動態 UI 渲染測試
  - [ ] 狀態同步測試
  - [ ] 預測更新測試
- [ ] `frontend/tests/e2e/ag-ui/full-flow.spec.ts`
  - [ ] Playwright E2E 測試

### 效能測試
- [ ] `backend/tests/performance/ag_ui/test_performance.py`
  - [ ] SSE 串流吞吐量測試
  - [ ] 狀態同步延遲測試
  - [ ] 並發連接測試

### 效能指標驗證
- [ ] 狀態同步延遲 < 50ms
- [ ] 預測回滾延遲 < 100ms
- [ ] UI 渲染延遲 < 200ms
- [ ] SSE 吞吐量 > 1000 events/sec

### 文檔更新
- [ ] `docs/api/ag-ui-api-reference.md`
  - [ ] SSE 端點文檔
  - [ ] Thread API 文檔
  - [ ] State API 文檔
  - [ ] Approvals API 文檔
- [ ] `docs/guides/ag-ui-integration-guide.md`
  - [ ] 整合指南
  - [ ] 前端組件使用說明
  - [ ] 最佳實踐

### 驗證
- [ ] 所有 E2E 測試通過
- [ ] 效能指標達標
- [ ] API 文檔完整
- [ ] 整合指南可用

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
- [ ] E2E 測試全部通過
- [ ] 效能測試達標
- [ ] 覆蓋率 > 85%

### Phase 15 完成驗證
- [ ] 所有 7 個 AG-UI 功能已實現
- [ ] API 文檔完整
- [ ] 整合指南完成
- [ ] 效能指標達標

---

## Notes

```
Sprint 60 開始日期: ___________
Sprint 60 結束日期: ___________
實際完成點數: ___ / 27 pts

Phase 15 總計: ___ / 85 pts
```
