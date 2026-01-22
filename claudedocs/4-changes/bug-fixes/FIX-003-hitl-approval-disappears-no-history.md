# FIX-003: 審批操作後卡片消失無歷史記錄

**修復日期**: 2026-01-22
**嚴重程度**: 中
**影響範圍**: Chat 頁面 HITL 審批功能
**相關 Sprint**: Sprint 99
**狀態**: ✅ 已修復

---

## 問題描述

### 症狀
- 點擊 Approve 或 Reject 後，審批卡片立即消失
- 用戶無法知道自己選擇了什麼選項
- 沒有操作歷史記錄

### 重現步驟
1. 進入 `/chat` 頁面
2. 觸發工具調用審批請求
3. 點擊 "Approve" 或 "Reject"
4. 觀察到審批卡片立即消失
5. 無法確認剛才的操作

### 預期行為
- 審批後卡片應保留並顯示已解決狀態
- 用戶能看到自己選擇了 Approved 還是 Rejected
- 如果是 Rejected，應顯示拒絕原因

### 實際行為
- 審批完成後卡片被直接從列表中移除
- 用戶失去對操作的視覺確認

---

## 根本原因分析

### 原因
`approveToolCall` 和 `rejectToolCall` 函數調用 `removePendingApproval`，直接從 `pendingApprovals` 列表中過濾掉該審批項目。

### 相關代碼
```tsx
// 問題代碼位置
// 文件: frontend/src/hooks/useUnifiedChat.ts

// ❌ 問題：直接移除，沒有保留歷史
const removePendingApproval = useCallback((approvalId: string) => {
  setPendingApprovals((prev) =>
    prev.filter((a) => a.approvalId !== approvalId)
  );
}, []);

// 在 approveToolCall 中調用
removePendingApproval(approvalId);
```

### 影響分析
- **直接影響**: 用戶失去操作確認
- **間接影響**: 無法追溯審批歷史
- **用戶影響**: 用戶可能不確定操作是否成功

---

## 修復方案

### 解決方法
1. 將 `removePendingApproval` 改為 `resolveApproval`
2. 更新審批狀態而非移除
3. 在 `PendingApproval` 類型中添加 `status`、`resolvedAt`、`rejectReason` 欄位
4. 更新 `ApprovalMessageCard` 顯示已解決狀態

### 修改文件
| 文件 | 修改類型 | 說明 |
|------|----------|------|
| `frontend/src/types/ag-ui.ts` | 修改 | 添加 ApprovalStatus 類型和新欄位 |
| `frontend/src/hooks/useUnifiedChat.ts` | 修改 | 改用 resolveApproval 更新狀態 |
| `frontend/src/components/unified-chat/ApprovalMessageCard.tsx` | 修改 | 顯示已解決狀態 UI |

### 修復代碼
```tsx
// 文件: frontend/src/types/ag-ui.ts

// ✅ 新增：審批狀態類型
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface PendingApproval {
  // ... 現有欄位 ...
  status?: ApprovalStatus;
  resolvedAt?: string;
  rejectReason?: string;
}
```

```tsx
// 文件: frontend/src/hooks/useUnifiedChat.ts

// ✅ 修復：更新狀態而非移除
const resolveApproval = useCallback((
  approvalId: string,
  status: 'approved' | 'rejected' | 'expired',
  rejectReason?: string
) => {
  setPendingApprovals((prev) =>
    prev.map((a) =>
      a.approvalId === approvalId
        ? {
            ...a,
            status,
            resolvedAt: new Date().toISOString(),
            rejectReason,
          }
        : a
    )
  );
}, []);
```

---

## 測試驗證

### 測試用例
- [x] Approve 後卡片顯示綠色 "Approved" 狀態
- [x] Reject 後卡片顯示紅色 "Rejected" 狀態
- [x] 拒絕原因正確顯示
- [x] 解決時間正確顯示

### 驗證步驟
1. 觸發審批請求
2. 點擊 Approve → 確認顯示 "Approved" + 時間戳
3. 觸發新審批請求
4. 點擊 Reject 並輸入原因 → 確認顯示 "Rejected" + 原因

### 回歸測試
- [x] 審批功能正常工作
- [x] 已解決的審批不影響新審批
- [x] UI 顯示正確

---

## 預防措施

### 短期措施
- [x] 添加狀態追蹤欄位
- [x] 更新 UI 顯示已解決狀態

### 長期措施
- [ ] 考慮將審批歷史持久化到後端
- [ ] 添加審批歷史列表頁面

---

## 相關連結

- **Commit**: f762059
- **相關 Bug**: FIX-001, FIX-002

---

## 時間線

| 時間 | 事件 |
|------|------|
| 2026-01-22 22:30 | 問題發現 |
| 2026-01-22 22:40 | 開始調查 |
| 2026-01-22 22:45 | 確認根因 |
| 2026-01-22 23:00 | 完成修復 |
| 2026-01-22 23:10 | 驗證完成 |

---

**修復者**: AI 助手 (Claude)
**審核者**: Development Team
**版本**: v1.0
