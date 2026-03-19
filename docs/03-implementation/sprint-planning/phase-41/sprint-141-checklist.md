# Sprint 141 Checklist: Chat → Orchestrator Pipeline 接通

**Sprint**: 141 | **Phase**: 41 | **Story Points**: 10
**Plan**: [sprint-141-plan.md](./sprint-141-plan.md)

---

## S141-1: UnifiedChat 統一走 Orchestrator Pipeline (4 SP)

### 消除雙路徑
- [ ] `pages/UnifiedChat.tsx` — `handleSend()` 統一走 `/orchestrator/chat`
- [ ] 移除 orchestration ON/OFF 分支邏輯
- [ ] POST `/orchestrator/chat` 使用 PipelineRequest 格式 (`{content, source, session_id}`)
- [ ] 解析 PipelineResponse → 提取 intent_category, risk_level, routing_layer, session_id, task_id
- [ ] 新增 `orchestratorSessionId` state 追蹤 pipeline session
- [ ] 保留 `isOrchestrationEnabled` flag 作為 fallback

### useOrchestratorChat 增強
- [ ] `hooks/useOrchestratorChat.ts` — `sendMessage()` POST `/orchestrator/chat`
- [ ] 從 PipelineResponse 提取 metadata 存入 `latestMetadata` state
- [ ] 新增 `activeTasks: string[]` state
- [ ] 新增 `orchestrationEvents` state

### API Response 類型對齊
- [ ] `api/endpoints/orchestrator.ts` — 更新 Response 類型匹配 PipelineResponse

## S141-2: IntentStatusChip 嵌入 Chat 訊息流 (3 SP)

### MessageList 擴展
- [ ] `components/unified-chat/MessageList.tsx` — 新增 `intentStatus` timeline item type
- [ ] assistant message 有 orchestration metadata 時，渲染 IntentStatusChip
- [ ] IntentStatusChip 數據從 message.metadata 讀取

### Message 類型擴展
- [ ] ChatMessage interface 新增 `orchestrationMetadata?` 欄位
- [ ] 含 intent, riskLevel, executionMode, routingLayer, confidence, processingTimeMs

### IntentStatusChip 樣式
- [ ] 在 MessageList timeline 中間距/寬度適當
- [ ] 展開時顯示 routing_layer + confidence + processing_time

## S141-3: LLM 回應串流顯示 (2 SP)

- [ ] 新增 `useTypewriterEffect(content, speed)` hook
- [ ] orchestrator 同步路徑：收到 PipelineResponse.content 後模擬打字效果
- [ ] 使用 `requestAnimationFrame` 避免 UI 卡頓
- [ ] 20ms/字元速度

## S141-4: 組件匯出 + 清理 (1 SP)

- [ ] `components/unified-chat/index.ts` — 匯出 IntentStatusChip
- [ ] `components/unified-chat/index.ts` — 匯出 TaskProgressCard
- [ ] `components/unified-chat/index.ts` — 匯出 MemoryHint
- [ ] 所有 import paths 正確
- [ ] TypeScript 編譯零錯誤

## 驗收測試

- [ ] 用戶發送訊息 → 經 `/orchestrator/chat` 處理 → 收到回應
- [ ] 每條 assistant 回應上方顯示 IntentStatusChip
- [ ] IntentStatusChip 可展開顯示詳細資訊
- [ ] AI 回應以打字效果出現
- [ ] Session ID 多輪對話保持一致
- [ ] 舊 orchestration flow 仍可作為 fallback
- [ ] 組件正確匯出
- [ ] TypeScript 零錯誤、npm run build 通過

---

**狀態**: 📋 計劃中
