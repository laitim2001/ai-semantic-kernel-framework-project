# Sprint 136 Checklist: 後台任務執行 + ARQ 整合

## Sprint 目標

| 項目 | 值 |
|------|-----|
| **總點數** | 10 點 |
| **狀態** | 📋 計劃中 |

---

## 開發任務

### S136-1: ARQ Worker 設置 (2 SP)
- [ ] 新增 `backend/src/infrastructure/workers/__init__.py`
- [ ] 新增 `backend/src/infrastructure/workers/arq_worker.py`
- [ ] 實作 `WorkerSettings` 類（Redis 連線、佇列名稱、max_jobs、job_timeout）
- [ ] 實作 `create_worker_settings()` — 從 app settings 建立 ARQ WorkerSettings
- [ ] 註冊 task functions：`execute_workflow_task`, `execute_swarm_task`
- [ ] 實作 startup/shutdown hooks（DB 連線池、Redis 連線初始化與清理）
- [ ] 新增 `backend/src/infrastructure/workers/task_functions.py`
- [ ] 實作 `execute_workflow_task(ctx, session_id, workflow_config)`
- [ ] 實作 `execute_swarm_task(ctx, session_id, swarm_config)`
- [ ] 任務結果寫入 TaskStore（L2 state）
- [ ] 異常處理：捕獲錯誤、記錄日誌、更新狀態為 FAILED
- [ ] 新增 `backend/arq_worker.py` — worker 啟動入口腳本

### S136-2: dispatch_workflow/swarm 改為 ARQ 提交 (3 SP)
- [ ] 新增 `backend/src/infrastructure/workers/arq_client.py`
- [ ] 實作 `ArqClient` 類（封裝 ARQ job 提交邏輯）
- [ ] 實作 `enqueue()` — 提交任務到佇列
- [ ] 實作 `get_job_result()` — 查詢任務結果
- [ ] 實作 `get_job_status()` — 查詢任務狀態
- [ ] 實作自動 Redis connection pool 管理
- [ ] 修改 `backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py`
- [ ] `dispatch_workflow()` 改為建立 ARQ job，返回 task_id
- [ ] `dispatch_swarm()` 改為建立 ARQ job，返回 task_id
- [ ] 新增 `_enqueue_arq_job(func_name, session_id, config)` 輔助方法
- [ ] 保留同步執行 fallback（ARQ 不可用時降級）
- [ ] 修改 `backend/src/integrations/hybrid/orchestrator/tools.py`
- [ ] `OrchestratorToolRegistry.execute()` 回傳 `{"task_id": "xxx", "status": "queued"}`

### S136-3: 任務狀態輪詢 API + SSE 完成推送 (2 SP)
- [ ] 修改 `backend/src/api/v1/tasks/routes.py`
- [ ] 實作 `GET /api/v1/tasks/{task_id}/status` — 查詢任務狀態
- [ ] 實作 `GET /api/v1/tasks/{task_id}/result` — 取得任務結果
- [ ] 實作 `GET /api/v1/tasks/{task_id}/stream` — SSE 完成推送
- [ ] 新增 `backend/src/infrastructure/workers/task_notifier.py`
- [ ] 實作 `TaskNotifier` 類（Redis Pub/Sub）
- [ ] 實作 `notify_completion(task_id, result)` — 發布完成通知
- [ ] 實作 `subscribe(task_id)` — 訂閱任務完成事件
- [ ] 支援多 SSE client 訂閱同一 task_id

### S136-4: Session Resume 接通後台任務 (3 SP)
- [ ] 新增 `backend/src/infrastructure/workers/task_tracker.py`
- [ ] 實作 `TaskTracker` 類（session_id ↔ task_id 映射）
- [ ] 實作 `register(session_id, task_id)` — 記錄活躍任務
- [ ] 實作 `get_active_tasks(session_id)` — 查詢活躍任務
- [ ] 實作 `mark_completed(task_id)` — 標記完成
- [ ] Redis-backed with TTL
- [ ] 修改 `backend/src/integrations/hybrid/orchestrator/session_recovery.py`
- [ ] `recover_session()` 增加 L4 層：ARQ 任務恢復
- [ ] 實作 `_recover_arq_tasks(session_id)` — 查詢 pending ARQ jobs
- [ ] 修改 `backend/src/api/v1/orchestrator/session_routes.py`
- [ ] `POST /sessions/{session_id}/resume` 回傳增加 `active_tasks` 欄位

## 驗證標準

- [ ] ARQ worker 可獨立啟動並連線 Redis
- [ ] dispatch_workflow 提交到 ARQ 佇列，HTTP 立即返回 task_id
- [ ] dispatch_swarm 提交到 ARQ 佇列，HTTP 立即返回 task_id
- [ ] ARQ 不可用時自動降級為同步執行
- [ ] `GET /tasks/{task_id}/status` 正確返回任務狀態
- [ ] `GET /tasks/{task_id}/stream` SSE 在任務完成時推送結果
- [ ] Session resume 能返回仍在執行的 active_tasks 列表
- [ ] Worker 異常時任務狀態正確標記為 FAILED
- [ ] TaskTracker 正確維護 session ↔ task 映射

## 相關連結

- [Phase 39 計劃](./README.md)
- [Sprint 136 Plan](./sprint-136-plan.md)
- [Sprint 135 Checklist](./sprint-135-checklist.md)

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 10
