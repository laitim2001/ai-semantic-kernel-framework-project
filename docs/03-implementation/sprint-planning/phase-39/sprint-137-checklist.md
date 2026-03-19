# Sprint 137 Checklist: 安全加固 + E2E 整合測試

## Sprint 目標

| 項目 | 值 |
|------|-----|
| **總點數** | 10 點 |
| **狀態** | 📋 計劃中 |

---

## 開發任務

### S137-1: ToolSecurityGateway 接入 (2 SP)
- [ ] 修改 `backend/src/integrations/hybrid/orchestrator/tools.py`
- [ ] `OrchestratorToolRegistry.execute()` 調用前過 `ToolSecurityGateway.check()`
- [ ] 安全檢查失敗返回 `{"error": "blocked", "reason": "..."}` 而非拋出異常
- [ ] 記錄所有安全攔截事件到 audit log
- [ ] 修改 `backend/src/core/security/tool_gateway.py`
- [ ] 確保 `check()` 接受 tool_name + params + user_context
- [ ] 新增 `audit_blocked_call(tool_name, reason, user_id)`
- [ ] 與 RBAC 系統 (`rbac.py`) 整合驗證

### S137-2: HITL 審批持久化到 PostgreSQL (2 SP)
- [ ] 修改 `backend/src/infrastructure/storage/approval_store.py`
- [ ] 新增 `PostgresApprovalStore` 類
- [ ] 實作 `save_approval()` — 寫入 PostgreSQL
- [ ] 實作 `load_approval()` — 從 PostgreSQL 讀取
- [ ] 實作 `list_pending()` — 查詢 pending 審批
- [ ] 實作 `update_status()` — 更新審批狀態
- [ ] 保留 `InMemoryApprovalStore` 作為 fallback
- [ ] 修改 `backend/src/infrastructure/storage/storage_factories.py`
- [ ] `create_approval_store()` 優先建立 PostgresApprovalStore
- [ ] PostgreSQL 不可用時 fallback 到 InMemoryApprovalStore
- [ ] 修改 `backend/src/integrations/hybrid/orchestrator/handlers/approval.py`
- [ ] `ApprovalHandler` 透過 StorageFactory 取得持久化 store

### S137-3: 統一 RiskAssessor 和 RiskAssessmentEngine (2 SP)
- [ ] 修改 `backend/src/integrations/orchestration/risk_assessor/assessor.py`
- [ ] `RiskAssessor` 整合 `RiskAssessmentEngine` 的評估邏輯
- [ ] 統一風險評分算法（合併評估維度）
- [ ] 統一回傳格式 `RiskAssessmentResult(score, level, factors, recommendation)`
- [ ] 修改 `backend/src/integrations/hybrid/risk/engine.py`
- [ ] `RiskAssessmentEngine` 改為 `RiskAssessor` 的 thin wrapper
- [ ] 標記為 `@deprecated`
- [ ] 修改 `backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py`
- [ ] 統一使用 `RiskAssessor` 進行風險評估
- [ ] 修改 `backend/src/integrations/orchestration/risk_assessor/__init__.py`
- [ ] 更新匯出：`RiskAssessor` + `RiskAssessmentResult`
- [ ] 修改 `backend/src/integrations/hybrid/risk/__init__.py`
- [ ] 匯出 deprecated wrapper

### S137-4: E2E 整合煙霧測試 (2 SP)
- [ ] 新增 `tests/integration/test_e2e_smoke.py`
- [ ] Step 1: Auth — JWT token 取得
- [ ] Step 2: Session — 建立新 session
- [ ] Step 3: InputGateway — 發送用戶訊息
- [ ] Step 4: Routing — 驗證路由決策
- [ ] Step 5: Risk Assessment — 風險評估通過
- [ ] Step 6: Agent Execution — agent 處理（mock LLM）
- [ ] Step 7: Tool Call — 工具調用（mock tool）
- [ ] Step 8: Result — 結果返回
- [ ] Step 9: Checkpoint — 狀態持久化驗證
- [ ] Step 10: Session Resume — 恢復 session 驗證
- [ ] 使用 `pytest` + `httpx.AsyncClient` 測試 FastAPI app
- [ ] Mock 外部依賴（LLM API、Redis、PostgreSQL）
- [ ] 修改 `backend/src/integrations/hybrid/orchestrator/e2e_validator.py`
- [ ] 新增 `validate_full_pipeline()` — 完整 10 步管線驗證

### S137-5: Extended Thinking 執行模式 (2 SP)
- [ ] 新增 `backend/src/integrations/claude_sdk/extended_thinking.py`
- [ ] 實作 `ExtendedThinkingConfig` model（enabled, budget_tokens, max_thinking_time）
- [ ] 實作 `ExtendedThinkingExecutor` 類
- [ ] 實作 `execute(prompt, config)` — 帶 thinking 的 Claude API 調用
- [ ] 實作 `stream_thinking(prompt, config)` — 串流 thinking tokens
- [ ] 整合 AG-UI 事件：thinking tokens 作為中間事件串流
- [ ] 修改 `backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py`
- [ ] 新增 `dispatch_extended_thinking(session_id, prompt, thinking_config)`
- [ ] 根據 routing decision 自動啟用 extended thinking
- [ ] 修改 `backend/src/integrations/claude_sdk/__init__.py`
- [ ] 匯出 `ExtendedThinkingConfig`, `ExtendedThinkingExecutor`

## 驗證標準

- [ ] ToolSecurityGateway 攔截所有 OrchestratorToolRegistry.execute() 調用
- [ ] 安全攔截事件記錄到 audit log
- [ ] HITL 審批記錄持久化到 PostgreSQL
- [ ] 系統重啟後審批狀態不丟失
- [ ] PostgreSQL 不可用時 fallback 到 InMemoryApprovalStore
- [ ] RiskAssessor 統一兩個引擎的評估邏輯
- [ ] RiskAssessmentEngine 標記為 deprecated 並保持向後兼容
- [ ] E2E 10 步煙霧測試全部通過
- [ ] Extended Thinking 模式可正確執行並串流 thinking tokens
- [ ] 完整管線端到端可跑通

## 相關連結

- [Phase 39 計劃](./README.md)
- [Sprint 137 Plan](./sprint-137-plan.md)
- [Sprint 136 Checklist](./sprint-136-checklist.md)

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 10
