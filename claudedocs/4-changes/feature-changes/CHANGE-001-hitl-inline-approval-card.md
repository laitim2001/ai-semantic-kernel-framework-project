# CHANGE-001: HITL 審批改為內嵌式訊息卡片

**變更日期**: 2026-01-22
**變更類型**: 功能改進
**影響範圍**: Chat 頁面 HITL 審批功能
**相關 Sprint**: Sprint 99
**狀態**: ✅ 已完成

---

## 變更摘要

將 HITL 審批請求從彈窗對話框 (ApprovalDialog) 改為內嵌式訊息卡片 (ApprovalMessageCard)，提供更自然的對話式體驗。

---

## 變更原因

### 原有設計問題
1. **彈窗打斷工作流程**: 模態對話框強制用戶處理，無法查看對話上下文
2. **風險分級不一致**: 低/中風險用 InlineApproval，高/危險用 ApprovalDialog
3. **缺乏歷史記錄**: 審批後卡片消失，無法回顧操作歷史
4. **體驗不連貫**: 審批介面與聊天介面風格不統一

### 新設計優勢
1. **對話式體驗**: 審批卡片像 AI 訊息一樣嵌入對話流
2. **統一風格**: 所有風險等級使用相同的卡片樣式
3. **保留歷史**: 審批後顯示已解決狀態，保留操作記錄
4. **上下文感知**: 用戶可同時查看對話內容和審批請求

---

## 詳細變更

### 新增組件: ApprovalMessageCard

**位置**: `frontend/src/components/unified-chat/ApprovalMessageCard.tsx`

**功能特性**:
| 特性 | 說明 |
|------|------|
| AI 頭像 | 根據風險等級顯示不同顏色的頭像 |
| 工具資訊 | 顯示工具名稱和參數（可折疊） |
| 風險等級徽章 | 低/中/高/危險四種等級 |
| 倒計時器 | 顯示審批剩餘時間 |
| 操作按鈕 | Approve/Reject 按鈕 |
| 已解決狀態 | 顯示 Approved/Rejected/Expired + 時間戳 |

**風險等級顏色**:
| 等級 | 圖標顏色 | 徽章顏色 |
|------|----------|----------|
| low | 綠色 | 綠色 |
| medium | 藍色 | 藍色 |
| high | 橙色 | 橙色 |
| critical | 紅色 | 紅色 |

### 類型更新

**PendingApproval 新增欄位**:
```typescript
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface PendingApproval {
  // ... 現有欄位 ...
  status?: ApprovalStatus;      // 審批狀態
  resolvedAt?: string;          // 解決時間
  rejectReason?: string;        // 拒絕原因
}
```

### Hook 函數更新

**useUnifiedChat 新增函數**:
```typescript
// 解決審批 - 更新狀態而非移除
resolveApproval: (
  approvalId: string,
  status: 'approved' | 'rejected' | 'expired',
  rejectReason?: string
) => void;

// 移除過期審批
removeExpiredApproval: (approvalId: string) => void;
```

### UI 狀態對照

| 狀態 | 圖標 | 顏色 | 說明 |
|------|------|------|------|
| pending | Clock | 藍色 | 等待用戶操作 |
| approved | CheckCircle | 綠色 | 用戶已批准 |
| rejected | XCircle | 紅色 | 用戶已拒絕（含原因） |
| expired | Timer | 灰色 | 審批已超時 |

---

## 修改文件清單

### 新增文件
| 文件 | 說明 |
|------|------|
| `frontend/src/components/unified-chat/ApprovalMessageCard.tsx` | 新的審批卡片組件 |

### 修改文件
| 文件 | 修改說明 |
|------|----------|
| `frontend/src/components/unified-chat/ChatArea.tsx` | 傳遞 onExpired 回調，添加自動滾動依賴 |
| `frontend/src/components/unified-chat/MessageList.tsx` | 整合 ApprovalMessageCard，修復 ID 傳遞 |
| `frontend/src/components/unified-chat/index.ts` | 導出新組件 |
| `frontend/src/hooks/useUnifiedChat.ts` | 添加 resolveApproval、removeExpiredApproval |
| `frontend/src/pages/UnifiedChat.tsx` | 移除 ApprovalDialog 使用，連接新函數 |
| `frontend/src/types/ag-ui.ts` | 添加 ApprovalStatus 和新欄位 |
| `frontend/src/types/unified-chat.ts` | 更新 ChatAreaProps 接口 |

---

## 遷移指南

### 舊代碼移除
```tsx
// ❌ 移除: ApprovalDialog 彈窗
<ApprovalDialog
  approval={currentApproval}
  onApprove={handleApprove}
  onReject={handleReject}
/>
```

### 新代碼使用
```tsx
// ✅ 新增: ApprovalMessageCard 在 MessageList 中渲染
{pendingApprovals.map((approval) => (
  <ApprovalMessageCard
    key={approval.approvalId}
    approval={approval}
    onApprove={() => onApprove(approval.approvalId)}
    onReject={(reason) => onReject(approval.approvalId, reason)}
    onExpired={() => onExpired?.(approval.approvalId)}
  />
))}
```

---

## 測試清單

- [x] 審批卡片正確顯示在對話流中
- [x] 風險等級顏色正確
- [x] 倒計時正常運作
- [x] Approve 後顯示綠色 Approved 狀態
- [x] Reject 後顯示紅色 Rejected 狀態 + 原因
- [x] 過期後顯示灰色 Expired 狀態
- [x] 3 秒後過期卡片自動移除
- [x] 自動滾動到新審批
- [x] 工具參數可折疊展開

---

## 相關連結

- **Commit**: f762059
- **相關 Bug Fixes**: FIX-001, FIX-002, FIX-003, FIX-004
- **設計參考**: Chat 頁面 AI 訊息卡片樣式

---

## 截圖對比

### 變更前
- 使用彈窗對話框
- 審批後完全消失
- 無狀態歷史

### 變更後
- 內嵌式訊息卡片
- 審批後保留並顯示狀態
- 完整操作歷史可見

---

**變更者**: AI 助手 (Claude)
**審核者**: Development Team
**版本**: v1.0
