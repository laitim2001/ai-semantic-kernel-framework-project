# Sprint 146 Checklist: Swarm UI 整合 + HITL 審批

**Sprint**: 146 | **Phase**: 42 | **Story Points**: 10
**Plan**: [sprint-146-plan.md](./sprint-146-plan.md)

---

## S146-1: AgentSwarmPanel 嵌入 Chat (4 SP)

### UnifiedChat 嵌入
- [x] `pages/UnifiedChat.tsx` — 嵌入 AgentSwarmPanel（右側 360px 面板）
- [x] 大螢幕（xl breakpoint）：右側面板
- [x] pipelineMode === 'swarm' 或 showSwarmPanel 時顯示

### SSE Swarm 事件處理
- [x] `UnifiedChat.tsx` — onSwarmWorkerStart handler -> swarmStore.setSwarmStatus + addWorker
- [x] `UnifiedChat.tsx` — onSwarmProgress handler -> swarmStore.updateWorkerProgress
- [x] swarmStore 透過 SSE 事件自動填充

### swarmStore 連接
- [x] import useSwarmStore 並讀取 swarmStatus
- [x] swarmSetStatus / swarmAddWorker / swarmUpdateProgress actions 連接
- [x] AgentSwarmPanel 接收 swarmStatus props

## S146-2: HITL 審批流程 (3 SP)

### 後端暫停機制
- [x] `mediator.py` — risk_level HIGH/CRITICAL 時發射 APPROVAL_REQUIRED 事件
- [x] APPROVAL_REQUIRED 含 approval_id, action, risk_level, description, details
- [x] `asyncio.Event` 暫停 Pipeline 等待審批（120s timeout）
- [x] resolve_approval() 方法解鎖等待中的 Pipeline
- [x] _pending_approvals / _approval_results 字典管理狀態

### 審批回傳端點
- [x] `routes.py` — `POST /orchestrator/approval/{approval_id}` 端點
- [x] 接受 approve / reject action
- [x] 通過 SessionFactory 找到對應 mediator 並 resolve

### 前端 InlineApproval
- [x] APPROVAL_REQUIRED SSE 事件觸發 pendingApproval state
- [x] InlineApproval 卡片：風險等級、操作描述、影響詳情
- [x] 批准按鈕 -> POST approve -> 清除 pendingApproval
- [x] 拒絕按鈕 -> POST reject -> 清除 pendingApproval

## S146-3: DialogHandler + HITLController 修復 (3 SP)

### DialogHandler 修復（延後）
- [ ] GuidedDialogEngine 初始化傳入 router 參數
- [ ] DialogHandler 在多輪對話場景正確觸發

### HITLController 修復（延後）
- [ ] HITLController 初始化傳入 storage 參數
- [ ] 管理待審批項目狀態

### Bootstrap 依賴注入（延後）
- [ ] bootstrap.py 傳入 IntentRouter 到 DialogHandler
- [ ] bootstrap.py 傳入 approval storage 到 HITLController

---

## 驗收測試

- [x] Swarm 模式時 AgentSwarmPanel 在 Chat 右側顯示
- [x] swarmStore 透過 SSE 事件連接（SWARM_WORKER_START/PROGRESS）
- [x] 高風險操作觸發 APPROVAL_REQUIRED SSE 事件
- [x] InlineApproval 卡片在 Chat 中渲染
- [x] 批准後 Pipeline 繼續；拒絕後取消
- [x] 審批端點 POST /orchestrator/approval/{id} 可用
- [ ] GuidedDialogEngine 正確初始化（延後）
- [ ] HITLController 正確初始化（延後）
- [x] TypeScript 零錯誤
- [ ] `black . && isort . && flake8 .` 通過

---

**Status**: Done (S146-3 deferred — non-critical path)
