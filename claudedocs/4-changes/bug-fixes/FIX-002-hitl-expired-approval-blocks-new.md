# FIX-002: 過期的審批請求阻擋新審批

**修復日期**: 2026-01-22
**嚴重程度**: 中
**影響範圍**: Chat 頁面 HITL 審批功能
**相關 Sprint**: Sprint 99
**狀態**: ✅ 已修復

---

## 問題描述

### 症狀
- 審批請求超時後，再次發送相同消息無法觸發新的審批請求
- 過期的審批卡片繼續顯示在介面上
- 用戶被卡住無法繼續操作

### 重現步驟
1. 進入 `/chat` 頁面
2. 發送觸發工具調用的消息
3. 等待審批請求超時（5 分鐘）
4. 再次發送相同消息
5. 觀察到沒有新的審批請求出現

### 預期行為
- 過期的審批請求應該被清理
- 新的消息應該能夠觸發新的審批請求

### 實際行為
- 過期的審批請求仍然留在 `pendingApprovals` 列表中
- 新的審批請求無法被正確添加或顯示

---

## 根本原因分析

### 原因
1. `ApprovalMessageCard` 在過期時只更新本地狀態 `isExpired`
2. 沒有機制通知父組件清理過期的審批
3. `pendingApprovals` 列表持續佔用空間

### 相關代碼
```tsx
// 問題代碼位置
// 文件: frontend/src/components/unified-chat/ApprovalMessageCard.tsx

// ❌ 問題：過期時只設置本地狀態，沒有通知父組件
const handleExpired = useCallback(() => {
  setIsExpired(true);
  // 沒有 onExpired?.() 調用
}, []);
```

### 影響分析
- **直接影響**: 過期審批佔用記憶體和介面空間
- **間接影響**: 可能影響新審批的添加
- **用戶影響**: 用戶需要刷新頁面才能重新觸發審批

---

## 修復方案

### 解決方法
1. 添加 `onExpired` 回調屬性到 `ApprovalMessageCard`
2. 過期時調用 `onExpired`，延遲 3 秒後移除
3. 在 `useUnifiedChat` 中添加 `removeExpiredApproval` 函數

### 修改文件
| 文件 | 修改類型 | 說明 |
|------|----------|------|
| `frontend/src/components/unified-chat/ApprovalMessageCard.tsx` | 修改 | 添加 onExpired 回調 |
| `frontend/src/hooks/useUnifiedChat.ts` | 修改 | 添加 removeExpiredApproval 函數 |
| `frontend/src/components/unified-chat/MessageList.tsx` | 修改 | 傳遞 onExpired 回調 |
| `frontend/src/components/unified-chat/ChatArea.tsx` | 修改 | 傳遞 onExpired 回調 |
| `frontend/src/pages/UnifiedChat.tsx` | 修改 | 連接 removeExpiredApproval |
| `frontend/src/types/unified-chat.ts` | 修改 | 更新 ChatAreaProps 接口 |

### 修復代碼
```tsx
// 修復後的代碼
// 文件: frontend/src/components/unified-chat/ApprovalMessageCard.tsx

// ✅ 修復：過期後通知父組件移除
const handleExpired = useCallback(() => {
  setLocalExpired(true);
  // 延遲 3 秒後移除，讓用戶看到過期狀態
  setTimeout(() => {
    onExpired?.();
  }, 3000);
}, [onExpired]);
```

```tsx
// 文件: frontend/src/hooks/useUnifiedChat.ts

// ✅ 新增：移除過期審批的函數
const removeExpiredApproval = useCallback((approvalId: string) => {
  setPendingApprovals((prev) =>
    prev.filter((a) => a.approvalId !== approvalId)
  );
  storeRemovePendingApproval(approvalId);
}, [storeRemovePendingApproval]);
```

---

## 測試驗證

### 測試用例
- [x] 審批過期後顯示 "Expired" 狀態
- [x] 過期 3 秒後審批卡片自動移除
- [x] 移除後可以重新觸發新審批

### 驗證步驟
1. 進入 `/chat` 頁面
2. 觸發審批請求
3. 等待超時或手動等待倒計時結束
4. 觀察卡片顯示 "Expired"
5. 3 秒後卡片消失
6. 再次發送相同消息，確認新審批出現

### 回歸測試
- [x] 正常審批流程不受影響
- [x] Approve/Reject 功能正常
- [x] SSE 事件處理正常

---

## 預防措施

### 短期措施
- [x] 添加過期清理機制
- [x] 顯示過期狀態給用戶

### 長期措施
- [ ] 考慮後端自動清理過期審批
- [ ] 添加審批請求的生命週期管理

---

## 相關連結

- **Commit**: f762059
- **相關 Bug**: FIX-001

---

## 時間線

| 時間 | 事件 |
|------|------|
| 2026-01-22 22:30 | 問題發現 |
| 2026-01-22 22:35 | 開始調查 |
| 2026-01-22 22:40 | 確認根因 |
| 2026-01-22 22:50 | 完成修復 |
| 2026-01-22 23:00 | 驗證完成 |

---

**修復者**: AI 助手 (Claude)
**審核者**: Development Team
**版本**: v1.0
