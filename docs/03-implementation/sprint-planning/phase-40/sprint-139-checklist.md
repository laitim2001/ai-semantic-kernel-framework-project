# Sprint 139 Checklist: Task Dashboard + 內聯進度組件

## Sprint 目標

| 項目 | 值 |
|------|-----|
| **總點數** | 10 點 |
| **狀態** | 📋 計劃中 |

---

## 開發任務

### S139-1: Task API + hooks (2 SP)
- [ ] 新增 `frontend/src/api/endpoints/tasks.ts`
- [ ] 實作 `getTasks(filters)` — GET /tasks（支援 status / priority / agent_id 篩選）
- [ ] 實作 `getTask(id)` — GET /tasks/{id}
- [ ] 實作 `getTaskSteps(id)` — GET /tasks/{id}/steps
- [ ] 實作 `cancelTask(id)` — POST /tasks/{id}/cancel
- [ ] 實作 `retryTask(id)` — POST /tasks/{id}/retry
- [ ] 新增 `frontend/src/hooks/useTasks.ts`
- [ ] 實作 `useTasks(filters)` — 任務列表查詢 hook（React Query，支援分頁）
- [ ] 實作 `useTask(id)` — 單一任務查詢 hook（含自動 refetch 間隔）
- [ ] 實作 `useTaskSteps(id)` — 任務步驟查詢 hook
- [ ] 實作 `useCancelTask()` — 取消任務 mutation hook
- [ ] 實作 `useRetryTask()` — 重試任務 mutation hook

### S139-2: Task Dashboard 頁面 (3 SP)
- [ ] 新增 `frontend/src/pages/tasks/TaskDashboardPage.tsx`
- [ ] 實作狀態篩選器（pending / running / completed / failed / cancelled）
- [ ] 實作優先級篩選器（LOW / MEDIUM / HIGH / CRITICAL）
- [ ] 實作表格欄位：Task ID、名稱、狀態、進度百分比、Agent、建立時間、耗時
- [ ] 實作狀態 Badge 色彩：pending=灰色、running=藍色、completed=綠色、failed=紅色、cancelled=黃色
- [ ] 實作操作按鈕：查看詳情、取消（running）、重試（failed）
- [ ] 實作分頁（每頁 20 筆）
- [ ] 實作自動 refetch（每 5 秒更新 running 狀態的任務）
- [ ] 使用 Shadcn UI DataTable 組件
- [ ] 新增 `frontend/src/pages/tasks/TaskDetailPage.tsx`
- [ ] 實作任務 metadata 顯示（ID、名稱、狀態、建立時間、完成時間、Agent 資訊）
- [ ] 實作進度條（百分比 + 視覺化）
- [ ] 實作步驟列表（每個步驟：名稱、狀態、耗時、輸出摘要）
- [ ] 實作執行結果區塊（成功顯示結果、失敗顯示錯誤）
- [ ] 實作操作按鈕：取消、重試、返回列表
- [ ] 使用 Shadcn UI Card + Progress + Table + Badge 組件

### S139-3: TaskProgressCard 內聯組件 (3 SP)
- [ ] 新增 `frontend/src/components/unified-chat/TaskProgressCard.tsx`
- [ ] 實作 Props interface: `{ taskId, taskName, status, progress, steps }`
- [ ] 實作頂部：Task ID + 名稱 + 狀態 Badge
- [ ] 實作中間：進度條（百分比 + 動畫效果，running 時脈動動畫）
- [ ] 實作下方：步驟列表（可摺疊，每個步驟顯示名稱 + 狀態圖標）
- [ ] 實作即時更新：使用 useTask hook 自動 refetch（running 狀態每 3 秒）
- [ ] 實作點擊 Task ID 跳轉到 TaskDetailPage
- [ ] 實作狀態轉換動畫（pending → running → completed）
- [ ] 使用 Shadcn UI Card + Progress + Collapsible + Badge 組件
- [ ] 支援多個 TaskProgressCard 同時顯示

### S139-4: 路由 + 導航更新 (2 SP)
- [ ] 修改 `frontend/src/App.tsx` — 新增路由 `/tasks` → TaskDashboardPage
- [ ] 修改 `frontend/src/App.tsx` — 新增路由 `/tasks/:id` → TaskDetailPage
- [ ] Lazy import 新增頁面組件
- [ ] 修改 `frontend/src/components/layout/Sidebar.tsx` — 新增「任務中心」導航項目
- [ ] 設定導航圖標（ListTodo 或 CheckSquare icon）
- [ ] 路由指向 `/tasks`
- [ ] 可選：顯示 running 任務數量 Badge

## 驗證標準

- [ ] Task API client 能正確呼叫所有 /tasks 端點
- [ ] useTasks hook 支援狀態/優先級篩選和分頁
- [ ] Task Dashboard 頁面能顯示任務列表並支援篩選
- [ ] Task Dashboard 自動更新 running 狀態的任務（每 5 秒）
- [ ] TaskDetailPage 能顯示完整任務詳情含步驟列表
- [ ] TaskProgressCard 在 Chat 中正確顯示任務進度
- [ ] TaskProgressCard 即時更新進度（running 狀態每 3 秒 refetch）
- [ ] 點擊 Task ID 可跳轉到 TaskDetailPage
- [ ] Sidebar 包含任務中心導航入口
- [ ] 所有新增組件使用 TypeScript + Shadcn UI
- [ ] 所有新增程式碼通過 ESLint 檢查
- [ ] npm run build 無錯誤

## 相關連結

- [Phase 40 計劃](./README.md)
- [Sprint 139 Plan](./sprint-139-plan.md)
- [Sprint 140 Plan](./sprint-140-plan.md)

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 10
