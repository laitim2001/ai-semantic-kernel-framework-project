# FIX-001: HITL 審批 API 使用錯誤的 ID 類型

**修復日期**: 2026-01-22
**嚴重程度**: 高
**影響範圍**: Chat 頁面 HITL 審批功能
**相關 Sprint**: Sprint 99
**狀態**: ✅ 已修復

---

## 問題描述

### 症狀
- 點擊 Approve 或 Reject 按鈕後，API 返回 404 錯誤
- Console 顯示 `APPROVAL_NOT_FOUND` 錯誤訊息
- 審批操作無法完成

### 重現步驟
1. 進入 `/chat` 頁面
2. 發送一條會觸發工具調用的消息（如 "create a file"）
3. 等待 ApprovalMessageCard 出現
4. 點擊 "Approve" 或 "Reject" 按鈕
5. 觀察到 404 錯誤

### 預期行為
- 點擊按鈕後，API 請求成功
- 審批狀態更新為 approved 或 rejected
- 工具調用繼續執行（如果批准）

### 實際行為
- API 返回 `404 Not Found`
- 錯誤訊息：`Approval request not found: tc-Bash-dc46c1a5`

---

## 根本原因分析

### 原因
前端 `MessageList.tsx` 在調用 `onApprove` 和 `onReject` 時傳遞了 `toolCallId`，但後端 API 期望的是 `approvalId`。

這兩個 ID 是不同的：
- `toolCallId`: 工具調用的 ID（如 `tc-Bash-dc46c1a5`）
- `approvalId`: 審批請求的 ID（如 `appr-xxx-xxx`）

### 相關代碼
```tsx
// 問題代碼位置
// 文件: frontend/src/components/unified-chat/MessageList.tsx
// 行數: 196-197

// ❌ 錯誤：傳遞 toolCallId
onApprove={() => onApprove(approval.toolCallId)}
onReject={(reason) => onReject(approval.toolCallId, reason)}
```

### 影響分析
- **直接影響**: HITL 審批功能完全無法使用
- **間接影響**: 所有需要審批的工具調用都會卡住
- **用戶影響**: 用戶無法批准或拒絕工具執行請求

---

## 修復方案

### 解決方法
將傳遞給回調函數的 ID 從 `toolCallId` 改為 `approvalId`

### 修改文件
| 文件 | 修改類型 | 說明 |
|------|----------|------|
| `frontend/src/components/unified-chat/MessageList.tsx` | 修改 | 改用 approvalId |
| `frontend/src/pages/UnifiedChat.tsx` | 修改 | 更新參數命名為 approvalId |

### 修復代碼
```tsx
// 修復後的代碼
// 文件: frontend/src/components/unified-chat/MessageList.tsx

// ✅ 正確：傳遞 approvalId
onApprove={() => onApprove(approval.approvalId)}
onReject={(reason) => onReject(approval.approvalId, reason)}
```

---

## 測試驗證

### 測試用例
- [x] 點擊 Approve 後 API 返回 200 OK
- [x] 點擊 Reject 後 API 返回 200 OK
- [x] 審批狀態正確更新

### 驗證步驟
1. 進入 `/chat` 頁面
2. 發送觸發工具調用的消息
3. 點擊 Approve/Reject 按鈕
4. 確認 Console 無 404 錯誤
5. 確認審批狀態更新

### 回歸測試
- [x] 現有 Chat 功能不受影響
- [x] 工具調用正常執行
- [x] SSE 事件處理正常

---

## 預防措施

### 短期措施
- [x] 在代碼中添加註釋說明 approvalId vs toolCallId 的區別
- [x] 更新 TypeScript 接口文檔

### 長期措施
- [ ] 考慮統一使用 approvalId 作為唯一標識
- [ ] 添加 API 請求 ID 驗證

---

## 相關連結

- **Commit**: f762059
- **相關文檔**: `claudedocs/6-ai-assistant/changelogs/2026-01-22-HITL-CHAT-IMPROVEMENTS.md`

---

## 時間線

| 時間 | 事件 |
|------|------|
| 2026-01-22 22:00 | 問題發現 |
| 2026-01-22 22:05 | 開始調查 |
| 2026-01-22 22:10 | 確認根因 |
| 2026-01-22 22:15 | 完成修復 |
| 2026-01-22 22:20 | 驗證完成 |

---

**修復者**: AI 助手 (Claude)
**審核者**: Development Team
**版本**: v1.0
