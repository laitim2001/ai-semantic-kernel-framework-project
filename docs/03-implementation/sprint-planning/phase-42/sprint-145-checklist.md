# Sprint 145 Checklist: Orchestrator SSE 串流端點

**Sprint**: 145 | **Phase**: 42 | **Story Points**: 12
**Plan**: [sprint-145-plan.md](./sprint-145-plan.md)

---

## S145-1: 後端 SSE 端點 (5 SP)

### SSE 端點建立
- [ ] `api/v1/orchestration.py` — 新增 `POST /orchestrator/chat/stream` 路由
- [ ] 使用 FastAPI `StreamingResponse` + `text/event-stream` content type
- [ ] 接收 PipelineRequest（與同步端點相同格式）
- [ ] 保留原有 `POST /orchestrator/chat` 同步端點

### PipelineEventEmitter 實作
- [ ] `mediator.py` — 新增 `PipelineEventEmitter` class
- [ ] 使用 `asyncio.Queue` 作為事件通道
- [ ] `emit()` 方法：將事件放入 queue
- [ ] `stream()` 方法：AsyncGenerator 產出 SSE 格式字串
- [ ] PIPELINE_COMPLETE 事件後停止串流

### Mediator 事件整合
- [ ] `mediator.py` — `process()` 方法接受 optional `event_emitter` 參數
- [ ] 每個 Handler 執行前發射對應 START 事件
- [ ] 每個 Handler 執行後發射對應 COMPLETE/END 事件
- [ ] TEXT_DELTA 事件支援逐 token 發射

### SSE 事件模型
- [ ] `models.py` — 新增 `SSEEvent` dataclass
- [ ] `models.py` — 新增 `SSEEventType` enum（至少 8 種事件類型）
- [ ] 事件格式對齊 AG-UI 協議命名慣例

## S145-2: 前端 SSE 接收 (4 SP)

### useSSEChat Hook
- [ ] 新增 `hooks/useSSEChat.ts`
- [ ] 使用 `fetch` + `ReadableStream` 接收 SSE（POST 方式）
- [ ] SSE 格式解析：`event: TYPE\ndata: JSON\n\n`
- [ ] 事件分發到對應 handler（8 種事件類型）
- [ ] 支援連線中斷重試（最多 3 次）

### UnifiedChat 切換到 SSE
- [ ] `pages/UnifiedChat.tsx` — `handleSend()` 改用 `useSSEChat`
- [ ] 移除 typewriter 假串流
- [ ] TEXT_DELTA 驅動真實逐 token 串流
- [ ] ROUTING_COMPLETE 即時更新 IntentStatusChip
- [ ] TOOL_CALL_START/END 即時更新 ToolCallTracker
- [ ] TASK_DISPATCHED 填充 TaskProgressCard
- [ ] 保留同步 POST fallback

### SSE API 函數
- [ ] `api/endpoints/orchestrator.ts` — 新增 `streamMessage()` 函數
- [ ] 處理 SSE 格式解析
- [ ] 錯誤處理：網路斷線、timeout、server error

## S145-3: MediatorEventBridge 連接 AG-UI (3 SP)

### 事件映射
- [ ] `ag_ui/mediator_bridge.py` — 連接 PipelineEventEmitter
- [ ] 映射 ROUTING_COMPLETE → RunStarted
- [ ] 映射 AGENT_THINKING → AgentStateMessage
- [ ] 映射 TEXT_DELTA → TextMessageContent
- [ ] 映射 TOOL_CALL_START → ToolCallStart
- [ ] 映射 TOOL_CALL_END → ToolCallEnd
- [ ] 映射 PIPELINE_COMPLETE → RunFinished

### AG-UI 路由更新
- [ ] `ag_ui/routes.py` — 改用 MediatorEventBridge
- [ ] 統一事件來源為 Pipeline

### 整合測試
- [ ] 測試 Pipeline → AG-UI 事件映射正確性
- [ ] 測試 SSE 端點回傳正確格式
- [ ] 測試連線中斷 + 重連場景

## 驗收測試

- [ ] `POST /orchestrator/chat/stream` 回傳 SSE event stream
- [ ] 包含 PIPELINE_START、ROUTING_COMPLETE、TEXT_DELTA、PIPELINE_COMPLETE 事件
- [ ] 前端使用 SSE 接收即時事件
- [ ] 真實逐 token 串流（非 typewriter）
- [ ] IntentStatusChip 即時更新
- [ ] ToolCallTracker 即時更新
- [ ] 同步 POST fallback 仍可用
- [ ] MediatorEventBridge 映射正確
- [ ] SSE 連線中斷自動重試
- [ ] TypeScript 零錯誤、npm run build 通過
- [ ] `black . && isort . && flake8 .` 通過

---

**狀態**: 📋 計劃中
