# Sprint 147 Checklist: Session 持久化 + RAG + Checkpoint + QA

**Sprint**: 147 | **Phase**: 42 | **Story Points**: 8
**Plan**: [sprint-147-plan.md](./sprint-147-plan.md)

---

## S147-1: Session 持久化 (3 SP)

### ConversationStateStore 替換
- [ ] `mediator.py` — `self._sessions: dict` 替換為 ConversationStateStore
- [ ] Redis 作為主要存儲（快速讀寫）
- [ ] PostgreSQL 作為持久化備份
- [ ] SessionState 資料結構含 messages、pipeline_state、metadata

### Session Recovery API
- [ ] `session_recovery.py` — `GET /orchestrator/sessions/{session_id}` 取得狀態
- [ ] `session_recovery.py` — `POST /orchestrator/sessions/{session_id}/resume` 恢復
- [ ] `session_recovery.py` — `DELETE /orchestrator/sessions/{session_id}` 刪除
- [ ] Session Resume 恢復完整 pipeline 狀態（不只對話歷史）

### 路由註冊
- [ ] `api/v1/orchestration.py` — 新增 session 管理路由
- [ ] 驗證 session_id 所有權

## S147-2: Checkpoint PostgreSQL Backend (2 SP)

### PostgreSQL 實作
- [ ] `infrastructure/checkpoint/` — 實作 PostgresCheckpointStorage
- [ ] 建立 `pipeline_checkpoints` 資料表（Alembic migration）
- [ ] 新增 index：session_id + created_at
- [ ] 每個 Handler 執行完畢自動保存 Checkpoint

### Mediator Checkpoint 整合
- [ ] `mediator.py` — Handler 迴圈中加入 Checkpoint 保存邏輯
- [ ] Pipeline 啟動時檢查是否有 Checkpoint
- [ ] 有 Checkpoint → 恢復並跳過已完成步驟
- [ ] 無 Checkpoint → 正常從頭開始
- [ ] 恢復後發射 CHECKPOINT_RESTORED SSE 事件

## S147-3: RAG Pipeline 連接 (2 SP)

### search_knowledge 工具實作
- [ ] `tool_registry.py` — search_knowledge 連接 RAG Pipeline
- [ ] RAG 搜尋結果注入 LLM prompt（作為 context）
- [ ] LLM 在需要時自動調用 search_knowledge

### 前端知識來源顯示
- [ ] PipelineResponse.metadata 含 knowledge_sources
- [ ] MessageList 中 assistant 回應下方顯示來源引用
- [ ] 來源引用格式：文件名 + 相關度分數 + 摘要片段
- [ ] 可點擊展開查看完整來源內容

## S147-4: E2E 完整驗證 (1 SP)

### Scenario 驗證
- [ ] Scenario A: 簡單問答（CHAT_MODE 直接回答）
- [ ] Scenario B: 工作流程（WORKFLOW_MODE 多步執行）
- [ ] Scenario C: Swarm 協作（SWARM_MODE 多 Worker）
- [ ] Scenario D: 高風險審批（HITL 批准/拒絕）
- [ ] Scenario E: Session 恢復（重啟後恢復對話）
- [ ] Scenario F: 知識檢索（RAG 搜尋 + 引用回答）

### Playwright E2E 測試
- [ ] 測試 SSE 事件接收和 UI 即時更新
- [ ] 測試 HITL 審批互動
- [ ] 測試 Session 恢復流程
- [ ] 測試 Swarm Panel 顯示

### 覆蓋驗證
- [ ] 10 步流程每步至少被一個 Scenario 覆蓋
- [ ] 所有 SSE 事件類型至少在一個 Scenario 中出現
- [ ] Swarm Panel、InlineApproval、IntentStatusChip 都有可視化對應

## 驗收測試

- [ ] Mediator 使用 ConversationStateStore（非 dict）
- [ ] Session 重啟後可恢復
- [ ] Session Resume API 可用
- [ ] Checkpoint 每步自動保存到 PostgreSQL
- [ ] Checkpoint 恢復可用
- [ ] search_knowledge 工具可調用
- [ ] 知識來源在前端顯示
- [ ] Scenario A-F 全部通過
- [ ] 10 步流程全部有可視化
- [ ] Playwright E2E 測試通過
- [ ] TypeScript 零錯誤、npm run build 通過
- [ ] `black . && isort . && flake8 .` 通過

---

**狀態**: 📋 計劃中
