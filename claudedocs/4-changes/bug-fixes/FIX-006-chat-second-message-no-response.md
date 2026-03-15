# FIX-006: Chat 第二則訊息無 AI 回覆 — Orchestration 完成後未觸發執行

**修復日期**: 2026-03-14
**嚴重程度**: 高
**影響範圍**: Unified Chat 頁面 — 所有經 Orchestration 路由的訊息
**相關 Sprint**: Sprint 99 (Phase 28 Orchestration 整合)
**狀態**: ✅ 已修復

---

## 問題描述

### 症狀
- Chat 頁面第一則訊息有 AI 回覆，第二則訊息只顯示 Orchestration 結果但無 AI 回覆
- Orchestration 面板正確顯示 intent 分類和 risk 評估，但後續的 LLM 執行未被觸發
- 後端日誌顯示 `POST /orchestration/intent/classify` 成功但無 `POST /hybrid/execute` 請求

### 重現步驟
1. 進入 `/chat` 頁面
2. 發送第一則訊息（例如 "hello, what can you do for me"）→ 正常回覆
3. 發送第二則訊息（例如 "show me about code writing"）→ 無回覆，只顯示 Orchestration 結果

### 預期行為
- 每則訊息在 Orchestration 分類完成後，自動呼叫 `/hybrid/execute` 取得 AI 回覆

### 實際行為
- Orchestration 分類完成後，前端設定 `phase='completed'` 但不觸發執行
- `onExecutionComplete` 回調永遠不被呼叫

---

## 根本原因分析

### 原因
`UnifiedChat.tsx` 第 397 行配置 `useOrchestration` hook 時設定 `autoExecute: false`，
但沒有對應的自動執行邏輯來處理 "不需審批、不需對話" 的正常路徑。

### 呼叫鏈分析

```
handleSend (UnifiedChat.tsx:633)
  → startOrchestration(content) (UnifiedChat.tsx:667)
    → orchestrationApi.classify() → 成功分類 ✅
    → riskAssessment.requires_approval === false → 不需審批 ✅
    → autoExecute === false → 進入 else 分支 ❌
      → updateState({ phase: 'completed', isLoading: false }) → 結束，無後續動作

// 以下代碼永遠不會被執行到（除非用戶手動點審批）：
    → executeInternal(message)
      → orchestrationApi.execute() → POST /hybrid/execute
        → onExecutionComplete → 將回覆加入聊天
```

### 相關代碼

**Bug 位置 1** — `frontend/src/pages/UnifiedChat.tsx:393-397`
```typescript
} = useOrchestration({
    sessionId,
    userId,
    includeRiskAssessment: true,
    autoExecute: false, // ← 設為 false，但沒有替代的執行觸發機制
```

**Bug 位置 2** — `frontend/src/hooks/useOrchestration.ts:212-217`
```typescript
// Phase 4: Auto Execute (if enabled and no approval needed)
if (autoExecute) {
  await executeInternal(message);    // ← autoExecute=false 時永遠不執行
} else {
  updateState({ phase: 'completed', isLoading: false }); // ← 死路
}
```

**觸發執行的唯一路徑**（目前都無法在正常流程中觸發）：
- `proceedWithExecution()` — 只由 `handleOrchestrationApprove`（用戶點擊核准按鈕）觸發
- `executeInternal()` — 只在 `autoExecute: true` 時觸發
- `executeDirectly()` — 暴露給外部但未被使用

### 第一則訊息為何成功
第一則訊息走了不同的初始化路徑（首次 session 建立 + HybridOrchestratorV2 初始化），
且 `handleSend` 中 `orchestrationEnabled` 在首次可能還未穩定為 true，
導致部分情況走了直接 `sendMessage()` 路徑（第 674 行）。

### 次要問題
`useOrchestration.ts` 第 222-232 行的 `startOrchestration` 依賴陣列缺少 `executeInternal`，
這是 React hooks 規則違規，可能導致 stale closure 問題。

### 影響分析
- **直接影響**: 所有經 Orchestration 的訊息在第二則起無 AI 回覆
- **用戶影響**: 聊天功能基本不可用（僅第一則訊息有回覆）
- **功能影響**: Orchestration 的分類結果無法轉化為實際執行

---

## 修復方案

### 方案選擇

| 方案 | 描述 | 複雜度 | 風險 |
|------|------|--------|------|
| **A: autoExecute=true** | 將 `autoExecute` 改為 `true` | 低 | 低 |
| B: 監聽 phase 變化 | 加 `useEffect` 監聽 `phase=completed` 觸發執行 | 中 | 中 |
| C: 直接呼叫 sendMessage | Orchestration 完成後走 SSE 路徑 | 高 | 高 |

### 採用方案 A（最小改動）

將 `autoExecute` 設為 `true`，讓 Orchestration 在分類 + 風險評估完成後，
當不需審批時自動執行 `/hybrid/execute`。

這是最安全的改動因為：
1. `onExecutionComplete` 回調已完整實現（第 408-431 行），能正確處理回覆
2. 需審批的流程不受影響（`requires_approval` 時會在 Phase 3 return，不會到 Phase 4）
3. `executeInternal` 已完整實現並經測試

### 修改檔案

| 檔案 | 變更 |
|------|------|
| `frontend/src/pages/UnifiedChat.tsx` | `autoExecute: false` → `autoExecute: true` |
| `frontend/src/hooks/useOrchestration.ts` | 將 `executeInternal` 加入 `startOrchestration` 依賴陣列 |

---

## 測試驗證

### 驗證步驟
1. 進入 `/chat` 頁面
2. 發送第一則訊息 → 確認有 AI 回覆
3. 發送第二則訊息 → 確認有 AI 回覆
4. 連續發送多則訊息 → 確認每則都有回覆
5. 觀察 Orchestration 面板 → 確認每則都有分類結果
6. 測試高風險訊息 → 確認仍然觸發審批流程（不會自動執行）

### 預期結果
- 每則訊息都經過 Orchestration 分類後自動執行
- Orchestration 面板顯示分類和風險評估
- 低風險訊息自動獲得 AI 回覆
- 需審批訊息仍然等待用戶核准

---

## 相關文件

| 文件 | 關聯 |
|------|------|
| `frontend/src/pages/UnifiedChat.tsx` | Bug 位置（autoExecute 設定）和 handleSend 流程 |
| `frontend/src/hooks/useOrchestration.ts` | Orchestration hook 的 startOrchestration / executeInternal 邏輯 |
| `frontend/src/api/endpoints/orchestration.ts` | orchestrationApi.execute 呼叫 /hybrid/execute |
| `backend/src/api/v1/hybrid/core_routes.py` | /hybrid/execute 端點 |
