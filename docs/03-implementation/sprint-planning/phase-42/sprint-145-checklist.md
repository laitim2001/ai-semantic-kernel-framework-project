# Sprint 145 Checklist: Orchestrator SSE 串流端點

**Sprint**: 145 | **Phase**: 42 | **Story Points**: 12
**Plan**: [sprint-145-plan.md](./sprint-145-plan.md)

---

## S145-1: 後端 SSE 端點 (5 SP)

### SSE 端點建立
- [x] `api/v1/orchestrator/routes.py` — 新增 `POST /orchestrator/chat/stream` 路由
- [x] 使用 FastAPI `StreamingResponse` + `text/event-stream` content type
- [x] 接收 PipelineRequest（與同步端點相同格式，含 mode 欄位）
- [x] 保留原有 `POST /orchestrator/chat` 同步端點

### PipelineEventEmitter 實作
- [x] `sse_events.py` — 新增 `PipelineEventEmitter` class
- [x] 使用 `asyncio.Queue` 作為事件通道
- [x] `emit()` 方法：將事件放入 queue
- [x] `stream()` 方法：AsyncGenerator 產出 SSE 格式字串
- [x] PIPELINE_COMPLETE / PIPELINE_ERROR 事件後停止串流
- [x] 120 秒 keepalive comment 防止連線超時

### Mediator 事件整合
- [x] `mediator.py` — `execute()` 方法接受 optional `event_emitter` 參數
- [x] PIPELINE_START 事件：pipeline 開始
- [x] ROUTING_COMPLETE 事件：含 intent, risk_level, mode, confidence, routing_layer
- [x] AGENT_THINKING 事件：LLM 開始思考
- [x] TOOL_CALL_END 事件：工具調用完成
- [x] TEXT_DELTA 事件：回應文字
- [x] TASK_DISPATCHED 事件：任務分發
- [x] PIPELINE_COMPLETE 事件：完整回應 + 處理時間
- [x] `asyncio.sleep(0)` 後每次 emit 強制 yield（真正即時串流）
- [x] `_enum_val()` helper 確保 enum 用 .value 序列化

### SSE 事件模型
- [x] `sse_events.py` — `SSEEvent` dataclass（event_type, data, timestamp）
- [x] `sse_events.py` — `SSEEventType` enum（12 種事件類型）
- [x] `to_sse_string()` 格式化為 SSE wire protocol

## S145-2: 前端 SSE 接收 (4 SP)

### useSSEChat Hook
- [x] 新增 `hooks/useSSEChat.ts`
- [x] 使用 `fetch` + `ReadableStream` 接收 SSE（POST 方式）
- [x] SSE 格式解析：`event: TYPE\ndata: JSON\n\n`
- [x] 事件分發到 12 個 handler callbacks
- [x] AbortController 支援取消串流
- [x] isStreaming 狀態追蹤

### UnifiedChat 切換到 SSE
- [x] `pages/UnifiedChat.tsx` — `handleSend()` 改用 `sendSSE()`
- [x] ROUTING_COMPLETE 即時更新 IntentStatusChip（在 LLM 回應前就顯示）
- [x] TEXT_DELTA 即時更新 message content
- [x] TOOL_CALL_END 更新 pipelineToolCalls
- [x] PIPELINE_COMPLETE 設定最終 content + detail
- [x] PIPELINE_ERROR 顯示錯誤訊息
- [x] isSSEStreaming 驅動 ChatInput loading 狀態（"AI is responding..."）

### hooks/index.ts 匯出
- [x] 新增 useSSEChat 匯出

## S145-3: MediatorEventBridge 連接 AG-UI (3 SP)

### 事件映射（延後至 Sprint 146+）
- [ ] `ag_ui/mediator_bridge.py` — 連接 PipelineEventEmitter
- [ ] 映射 Pipeline 事件 -> AG-UI 事件

---

## 額外修復

- [x] `routing.py` — 三層路由永遠執行（不因 force_mode 跳過）
- [x] `mediator.py` — enum 用 .value 序列化（非 str()）
- [x] `routes.py` — 修復 `context` 變數未定義錯誤
- [x] `pipeline.py` — PipelineResponse 加入 execution_mode, suggested_mode, tool_calls
- [x] `pipeline.py` — PipelineRequest 加入 mode 欄位

## 驗收測試

- [x] `POST /orchestrator/chat/stream` 回傳 SSE event stream
- [x] 包含 PIPELINE_START、ROUTING_COMPLETE、TEXT_DELTA、PIPELINE_COMPLETE 事件
- [x] 前端使用 SSE 接收即時事件
- [x] IntentStatusChip 在回應前即時更新（意圖/風險/模式）
- [x] "AI is responding..." loading 狀態
- [x] 同步 POST fallback 仍可用
- [ ] MediatorEventBridge 映射（延後）
- [ ] SSE 連線中斷自動重試
- [x] TypeScript 零錯誤
- [ ] `black . && isort . && flake8 .` 通過

---

**Status**: Done (S145-3 AG-UI bridge deferred)
