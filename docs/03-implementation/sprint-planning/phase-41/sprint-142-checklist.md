# Sprint 142 Checklist: Inline 組件嵌入 + 工具調用顯示

**Sprint**: 142 | **Phase**: 41 | **Story Points**: 10
**Plan**: [sprint-142-plan.md](./sprint-142-plan.md)

---

## S142-1: TaskProgressCard 嵌入 Chat (3 SP)

### MessageList 擴展
- [ ] `components/unified-chat/MessageList.tsx` — 新增 `taskProgress` timeline item type
- [ ] assistant message 有 `taskId` 時，下方渲染 TaskProgressCard
- [ ] TaskProgressCard 使用 `useTask(taskId)` 自動 refetch（running 每 3 秒）
- [ ] 支援同時顯示多個 TaskProgressCard

### UnifiedChat 傳遞 task_id
- [ ] `pages/UnifiedChat.tsx` — 從 PipelineResponse 提取 `task_id`
- [ ] 將 task_id 附加到 assistant message metadata
- [ ] 維護 `activeTasks` state

### 樣式適配
- [ ] TaskProgressCard 在 MessageList 內寬度/間距合適
- [ ] 點擊 task ID 跳轉到 `/tasks/{id}`

## S142-2: ToolCallTracker 嵌入 Chat (3 SP)

### useToolCallEvents hook
- [ ] 新增 `hooks/useToolCallEvents.ts`
- [ ] 從 PipelineResponse.metadata 提取工具調用資訊
- [ ] 管理 `toolCalls: TrackedToolCall[]` state

### MessageList 擴展
- [ ] `components/unified-chat/MessageList.tsx` — 新增 `toolCalls` timeline item type
- [ ] 在 assistant message 前渲染工具調用列表

### ToolCallTracker 適配
- [ ] `components/unified-chat/ToolCallTracker.tsx` — 新增 inline 模式
- [ ] 接受 `toolCalls` prop 格式相容
- [ ] 顯示：工具名稱、狀態圖標、耗時

## S142-3: HITL 審批在 Chat 中顯示 (2 SP)

- [ ] 當 PipelineResponse `requires_approval=true` 時渲染 InlineApproval
- [ ] 用戶批准後繼續管線
- [ ] 連接 `GET /orchestration/approvals` 查詢狀態
- [ ] 連接 `POST /orchestration/approvals/{id}/decision` 提交決定

## S142-4: OrchestrationPanel 精簡 (2 SP)

- [ ] OrchestrationPanel 預設收起（collapsed）
- [ ] 新增「顯示詳細」按鈕
- [ ] 面板專注：Agent 工具清單、Pipeline 狀態、Debug 資訊
- [ ] 移除已由 inline 組件顯示的資訊
- [ ] 保留 Swarm 視覺化面板

## 驗收測試

- [ ] Chat 中顯示 TaskProgressCard（Agent dispatch 任務時）
- [ ] TaskProgressCard 即時更新（running 每 3 秒）
- [ ] 點擊 task ID 跳轉到 TaskDetailPage
- [ ] ToolCallTracker 在 Chat 中顯示
- [ ] 高風險操作顯示審批卡片
- [ ] 用戶可在 Chat 中批准/拒絕
- [ ] OrchestrationPanel 預設收起
- [ ] 多個 inline 組件 timeline 排列正確
- [ ] TypeScript 零錯誤、npm run build 通過

---

**狀態**: 📋 計劃中
