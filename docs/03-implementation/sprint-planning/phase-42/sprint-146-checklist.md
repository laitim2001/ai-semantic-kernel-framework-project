# Sprint 146 Checklist: Swarm UI 整合 + HITL 審批

**Sprint**: 146 | **Phase**: 42 | **Story Points**: 10
**Plan**: [sprint-146-plan.md](./sprint-146-plan.md)

---

## S146-1: AgentSwarmPanel 嵌入 Chat (4 SP)

### UnifiedChat 嵌入
- [ ] `pages/UnifiedChat.tsx` — SWARM_WORKER_START 時顯示 AgentSwarmPanel
- [ ] 大螢幕（≥1280px）：右側面板（寬度 360px）
- [ ] 小螢幕（<1280px）：訊息流下方折疊面板

### SSE Swarm 事件處理
- [ ] `hooks/useSSEChat.ts` — 新增 SWARM_WORKER_START handler → swarmStore.addWorker
- [ ] `hooks/useSSEChat.ts` — 新增 SWARM_PROGRESS handler → swarmStore.updateWorkerProgress
- [ ] `hooks/useSSEChat.ts` — 新增 SWARM_WORKER_COMPLETE handler → swarmStore.completeWorker
- [ ] `hooks/useSSEChat.ts` — 新增 SWARM_COMPLETE handler → swarmStore.completeSwarm

### WorkerCard 即時更新
- [ ] WorkerCard 從 swarmStore 讀取即時數據
- [ ] 進度條依據 SWARM_PROGRESS 更新
- [ ] Worker 完成時顯示結果摘要
- [ ] Swarm 完成後面板顯示總結

## S146-2: HITL 審批流程 (3 SP)

### 後端暫停機制
- [ ] `mediator.py` — risk_level ≥ HIGH 時發射 APPROVAL_REQUIRED 事件
- [ ] APPROVAL_REQUIRED 事件含 approval_id、action、risk_level、description
- [ ] 使用 `asyncio.Event` 暫停 Pipeline 等待審批
- [ ] 審批通過 → 繼續執行；拒絕 → 取消並回傳訊息

### 審批回傳端點
- [ ] `api/v1/orchestration.py` — 新增 `POST /orchestrator/approval/{approval_id}`
- [ ] 接受 approve / reject action
- [ ] 通知對應 Pipeline 的 asyncio.Event

### 前端 InlineApproval
- [ ] APPROVAL_REQUIRED 事件時渲染 InlineApproval 卡片
- [ ] 顯示操作描述、風險等級、影響系統、預估時間
- [ ] 批准 / 拒絕按鈕（可附加理由）
- [ ] POST `/orchestrator/approval/{approval_id}` 回傳結果
- [ ] 審批後卡片變為只讀狀態

## S146-3: DialogHandler + HITLController 修復 (3 SP)

### DialogHandler 修復
- [ ] `dialog_handler.py` — GuidedDialogEngine 初始化傳入 router 參數
- [ ] 從 Bootstrap context 取得 IntentRouter instance
- [ ] DialogHandler 在多輪對話場景正確觸發

### HITLController 修復
- [ ] `hitl_handler.py` — HITLController 初始化傳入 storage 參數
- [ ] 從 Bootstrap context 取得 approval storage（Redis/PostgreSQL）
- [ ] 管理待審批項目狀態（pending → approved/rejected）

### Bootstrap 依賴注入
- [ ] `bootstrap.py` — 建立 IntentRouter instance 傳入 DialogHandler
- [ ] `bootstrap.py` — 建立 approval storage 傳入 HITLController
- [ ] 所有 Handler 依賴在 Bootstrap 階段完整注入

### 對話引導可視化
- [ ] SSE 事件 DIALOG_STEP 推送引導資訊
- [ ] 前端顯示引導進度和下一步提示

## 驗收測試

- [ ] Swarm 執行時 AgentSwarmPanel 顯示
- [ ] WorkerCard 即時反映各 Worker 狀態
- [ ] swarmStore 透過 SSE 正確填充
- [ ] 高風險操作觸發 APPROVAL_REQUIRED
- [ ] InlineApproval 卡片渲染正確
- [ ] 批准後 Pipeline 繼續；拒絕後取消
- [ ] GuidedDialogEngine 正確初始化
- [ ] HITLController 正確初始化
- [ ] 對話引導可視化運作
- [ ] TypeScript 零錯誤、npm run build 通過
- [ ] `black . && isort . && flake8 .` 通過

---

**狀態**: 📋 計劃中
