# FIX-004: 審批請求出現時無自動滾動

**修復日期**: 2026-01-22
**嚴重程度**: 低
**影響範圍**: Chat 頁面 HITL 審批功能
**相關 Sprint**: Sprint 99
**狀態**: ✅ 已修復

---

## 問題描述

### 症狀
- 新的審批請求出現時，聊天區域不會自動滾動
- 用戶需要手動向下滾動才能看到審批卡片
- 可能錯過重要的審批請求

### 重現步驟
1. 進入 `/chat` 頁面
2. 滾動到聊天記錄上方
3. 發送觸發工具調用的消息
4. 觀察到審批卡片出現但頁面未滾動

### 預期行為
- 審批請求出現時應自動滾動到底部
- 用戶能立即看到需要處理的審批

### 實際行為
- 審批卡片在底部出現但不可見
- 用戶必須手動滾動

---

## 根本原因分析

### 原因
`ChatArea.tsx` 的自動滾動 `useEffect` 只監聽 `messages` 和 `isStreaming`，沒有監聽 `pendingApprovals` 的變化。

### 相關代碼
```tsx
// 問題代碼位置
// 文件: frontend/src/components/unified-chat/ChatArea.tsx

// ❌ 問題：沒有監聽 pendingApprovals 變化
useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
}, [messages, isStreaming]); // 缺少 pendingApprovals.length
```

### 影響分析
- **直接影響**: 用戶可能錯過審批請求
- **間接影響**: 審批超時率可能增加
- **用戶影響**: 需要手動滾動，體驗不佳

---

## 修復方案

### 解決方法
在自動滾動的 `useEffect` 依賴數組中添加 `pendingApprovals.length`

### 修改文件
| 文件 | 修改類型 | 說明 |
|------|----------|------|
| `frontend/src/components/unified-chat/ChatArea.tsx` | 修改 | 添加 pendingApprovals.length 依賴 |

### 修復代碼
```tsx
// 修復後的代碼
// 文件: frontend/src/components/unified-chat/ChatArea.tsx

// ✅ 修復：添加 pendingApprovals.length 到依賴數組
useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
}, [messages, isStreaming, pendingApprovals.length]);
```

---

## 測試驗證

### 測試用例
- [x] 新審批出現時自動滾動到底部
- [x] 多個審批連續出現時持續滾動
- [x] 現有消息滾動功能不受影響

### 驗證步驟
1. 滾動聊天區域到上方
2. 發送觸發審批的消息
3. 確認頁面自動滾動到審批卡片

### 回歸測試
- [x] 消息自動滾動正常
- [x] 串流時自動滾動正常
- [x] 性能無明顯影響

---

## 預防措施

### 短期措施
- [x] 添加 pendingApprovals.length 到依賴

### 長期措施
- [ ] 考慮添加「有新審批」的視覺提示
- [ ] 考慮添加滾動到審批的快捷按鈕

---

## 相關連結

- **Commit**: f762059
- **相關 Bug**: FIX-001, FIX-002, FIX-003

---

## 時間線

| 時間 | 事件 |
|------|------|
| 2026-01-22 23:00 | 問題發現 |
| 2026-01-22 23:05 | 開始調查 |
| 2026-01-22 23:08 | 確認根因 |
| 2026-01-22 23:10 | 完成修復 |
| 2026-01-22 23:15 | 驗證完成 |

---

**修復者**: AI 助手 (Claude)
**審核者**: Development Team
**版本**: v1.0
