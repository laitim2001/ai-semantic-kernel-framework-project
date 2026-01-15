# Sprint 98 Checklist: HybridOrchestratorV2 整合

## 開發任務

### Story 98-1: 重命名 IntentRouter → FrameworkSelector
- [ ] 更新 `hybrid/intent/router.py`
  - [ ] 類名: `IntentRouter` → `FrameworkSelector`
  - [ ] 類名: `IntentAnalysis` → `FrameworkAnalysis`
  - [ ] 方法: `analyze_intent()` → `select_framework()`
- [ ] 更新 imports
  - [ ] `orchestrator_v2.py`
  - [ ] 其他引用文件
- [ ] 更新測試文件
- [ ] 確認無破壞性變更

### Story 98-2: 整合 BusinessIntentRouter
- [ ] 更新 `orchestrator_v2.py`
- [ ] 添加 `input_gateway` 參數
- [ ] 添加 `business_router` 參數
- [ ] 添加 `guided_dialog` 參數
- [ ] 添加 `risk_assessor` 參數
- [ ] 添加 `hitl_controller` 參數
- [ ] 更新 `execute()` 方法
  - [ ] Step 1: InputGateway 處理
  - [ ] Step 2: 完整度檢查
  - [ ] Step 3: GuidedDialog (如需要)
  - [ ] Step 4: RiskAssessor 評估
  - [ ] Step 5: HITL (如需要)
  - [ ] Step 6: FrameworkSelector 選擇
  - [ ] Step 7: 執行

### Story 98-3: 整合 GuidedDialogEngine 到 API 層
- [ ] 創建 `dialog_routes.py`
- [ ] 實現 `POST /dialog/start` 端點
- [ ] 實現 `POST /dialog/{dialog_id}/respond` 端點
- [ ] 實現 `GET /dialog/{dialog_id}/status` 端點
- [ ] 實現 `DELETE /dialog/{dialog_id}` 端點
- [ ] 定義 Pydantic 請求/回應模型

### Story 98-4: 整合 HITL 到現有審批流程
- [ ] 創建 `approval_routes.py`
- [ ] 實現 `GET /approvals` 端點
- [ ] 實現 `GET /approvals/{approval_id}` 端點
- [ ] 實現 `POST /approvals/{approval_id}/decision` 端點
- [ ] 實現 `POST /approvals/{approval_id}/callback` 端點
- [ ] 整合現有 ApprovalHook

## 品質檢查

### 代碼品質
- [ ] Black 格式化通過
- [ ] isort 排序通過
- [ ] flake8 檢查通過
- [ ] mypy 類型檢查通過

### 測試
- [ ] 所有現有測試通過
- [ ] 新增整合測試通過
- [ ] API 測試通過

### 向後相容性
- [ ] 重命名無破壞性變更
- [ ] 現有功能正常運作
- [ ] API 向後相容

## 驗收標準

- [ ] 重命名完成，無破壞性變更
- [ ] HybridOrchestratorV2 整合完成
- [ ] GuidedDialog API 正常工作
- [ ] HITL API 正常工作
- [ ] 所有測試通過

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 25
