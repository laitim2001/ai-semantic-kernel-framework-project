# Sprint 18 Checklist: WorkflowExecutor 和整合

**Sprint 目標**: 完成 NestedWorkflow 遷移和 Phase 3 整合
**週期**: Week 37-38
**總點數**: 36 點
**狀態**: 待開始

---

## S18-1: WorkflowExecutor 適配器 (8 點)

- [ ] 創建 `builders/workflow_executor.py`
- [ ] WorkflowExecutorAdapter 類
- [ ] SubWorkflowRequestMessage 支持
- [ ] SubWorkflowResponseMessage 支持

---

## S18-2: NestedWorkflowManager 遷移 (8 點)

- [ ] 遷移 NestedWorkflowType
- [ ] 遷移 SubWorkflowReference
- [ ] 遷移嵌套執行邏輯
- [ ] 並發隔離測試

---

## S18-3: 整合測試 (8 點)

- [ ] Concurrent + GroupChat 測試
- [ ] Handoff + Magentic 測試
- [ ] Nested + Checkpoint 測試
- [ ] E2E 測試

---

## S18-4: 性能測試 (5 點)

- [ ] 響應時間測試
- [ ] 吞吐量測試
- [ ] 內存使用測試

---

## S18-5: 文檔更新 (5 點)

- [ ] API 文檔
- [ ] 遷移指南
- [ ] 範例代碼

---

## S18-6: 清理舊代碼 (2 點)

- [ ] 標記 deprecated
- [ ] 清理不需要文件

---

## Phase 3 最終驗證

- [ ] 所有適配器完成
- [ ] API 向後兼容
- [ ] 測試覆蓋率 >= 80%
- [ ] 性能達標
- [ ] 文檔完整

---

## 相關連結

- [Sprint 18 Plan](./sprint-18-plan.md)
- [Phase 3 Overview](./README.md)
