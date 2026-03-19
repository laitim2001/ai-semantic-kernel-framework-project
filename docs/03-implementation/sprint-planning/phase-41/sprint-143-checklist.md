# Sprint 143 Checklist: Memory 整合 + Session Resume UI + 完善

**Sprint**: 143 | **Phase**: 41 | **Story Points**: 8
**Plan**: [sprint-143-plan.md](./sprint-143-plan.md)

---

## S143-1: MemoryHint 嵌入 Chat (2 SP)

### 記憶顯示
- [ ] `pages/UnifiedChat.tsx` — ChatInput 上方渲染 MemoryHint
- [ ] 新增 `relatedMemories` state
- [ ] 從 PipelineResponse.metadata.memories 或 `/memory/search` 取得記憶
- [ ] 用戶可關閉 MemoryHint（dismiss）

### 新對話自動搜索記憶
- [ ] 用戶發送第一條訊息後背景呼叫 `POST /memory/search`
- [ ] 找到 ≥1 條記憶時顯示 MemoryHint
- [ ] 記憶以摘要形式顯示（前 100 字）

## S143-2: Session Resume 在 Chat 中完整運作 (3 SP)

### Resume 流程
- [ ] ChatHistoryPanel Resume 按鈕 → POST `/sessions/{id}/resume`
- [ ] 成功後載入對話歷史 GET `/sessions/{id}/messages`
- [ ] 歷史訊息渲染到 MessageList
- [ ] 有活躍任務時顯示 TaskProgressCard
- [ ] 更新 `orchestratorSessionId`

### 對話歷史還原
- [ ] 歷史訊息保留 orchestrationMetadata
- [ ] Resume 後的歷史訊息也顯示 IntentStatusChip
- [ ] 歷史/新訊息視覺一致性

### 後台任務狀態同步
- [ ] Resume 後檢查 active_tasks
- [ ] 活躍 task 顯示 TaskProgressCard
- [ ] 已完成任務顯示完成狀態

## S143-3: 跨 Session 記憶場景 (1 SP)

- [ ] PipelineResponse 含 memory_context 時在 MemoryHint 中顯示
- [ ] Scenario F：Session 1 記憶寫入 → Session 2 引用
- [ ] MemoryHint 顯示「找到 N 條相關記憶」

## S143-4: 整體 QA + 10 步驗證 (2 SP)

### 10 步流程驗證
- [ ] Step 1: 登入 → Chat 頁面 ✅
- [ ] Step 2: Session 管理 → ChatHistoryPanel ✅
- [ ] Step 3: 意圖+風險 → IntentStatusChip
- [ ] Step 4: Agent 決策 → IntentStatusChip executionMode
- [ ] Step 5: 任務分發 → TaskProgressCard
- [ ] Step 6: 工具調用 → ToolCallTracker
- [ ] Step 7: SSE 串流 → 打字效果
- [ ] Step 8: 結果回應 → MessageList
- [ ] Step 9: Session Resume → 歷史還原
- [ ] Step 10: 記憶+知識 → MemoryHint

### Scenario 測試
- [ ] Scenario A: 簡單問答
- [ ] Scenario B: 工作流任務
- [ ] Scenario C: 高風險審批
- [ ] Scenario D: 多工具調用
- [ ] Scenario E: Session Resume
- [ ] Scenario F: 跨 Session 記憶

## 驗收測試

- [ ] MemoryHint 在 ChatInput 上方顯示
- [ ] MemoryHint 可展開/關閉
- [ ] Session Resume 後完整對話歷史
- [ ] Resume 後活躍任務 TaskProgressCard 正確
- [ ] 新對話自動搜索歷史記憶
- [ ] Scenario F 可演示
- [ ] 10 步流程測試全部通過
- [ ] 6 Scenario 全部可演示
- [ ] TypeScript 零錯誤、npm run build 通過

---

**狀態**: 📋 計劃中
