# Sprint 85 Checklist: 統計和進階功能

## Sprint Status

| Metric | Value |
|--------|-------|
| **Total Stories** | 3 |
| **Total Points** | 12 pts |
| **Completed** | 0 |
| **In Progress** | 0 |
| **Status** | 📋 規劃中 |

---

## Stories

### S85-1: 統計儀表板 (5 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `frontend/src/components/DevUI/Statistics.tsx`
- [ ] 創建 `frontend/src/components/DevUI/StatCard.tsx`
- [ ] 創建 `frontend/src/components/DevUI/EventPieChart.tsx`
- [ ] 實現 LLM 調用統計卡片 (調用次數、總耗時、平均耗時)
- [ ] 實現工具調用統計卡片 (調用次數、總耗時、成功率)
- [ ] 實現事件統計卡片 (總事件數、按類型分佈餅圖)
- [ ] 實現錯誤和警告統計
- [ ] 實現檢查點統計 (創建數量、批准/拒絕/超時)

**Acceptance Criteria**:
- [ ] 統計數據正確計算
- [ ] 統計卡片正確顯示
- [ ] 餅圖正確渲染
- [ ] 數據自動刷新

---

### S85-2: 實時追蹤功能 (5 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `frontend/src/hooks/useDevToolsStream.ts`
- [ ] 創建 `frontend/src/components/DevUI/LiveIndicator.tsx`
- [ ] 實現 SSE 連接建立
- [ ] 實現實時事件接收和顯示
- [ ] 實現自動滾動到最新事件
- [ ] 實現連接狀態指示器
- [ ] 實現斷線重連機制
- [ ] 實現暫停/繼續自動更新功能

**Acceptance Criteria**:
- [ ] SSE 連接正常建立
- [ ] 事件實時更新
- [ ] 自動滾動功能正常
- [ ] 連接狀態正確顯示
- [ ] 斷線能自動重連
- [ ] 暫停/繼續功能正常

---

### S85-3: 事件過濾和搜索 (2 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `frontend/src/components/DevUI/EventFilter.tsx`
- [ ] 創建 `frontend/src/hooks/useEventFilter.ts`
- [ ] 實現按事件類型過濾 (多選)
- [ ] 實現按嚴重性過濾
- [ ] 實現按執行器 ID 過濾
- [ ] 實現文本搜索 (事件數據)
- [ ] 實現過濾器組合
- [ ] 實現清除過濾器功能

**Acceptance Criteria**:
- [ ] 事件類型過濾正常
- [ ] 嚴重性過濾正常
- [ ] 執行器 ID 過濾正常
- [ ] 文本搜索功能正常
- [ ] 過濾器可組合使用
- [ ] 清除過濾器功能正常

---

## Files Summary

### New Files
| File | Story | Description |
|------|-------|-------------|
| `frontend/src/components/DevUI/Statistics.tsx` | S85-1 | 統計面板組件 |
| `frontend/src/components/DevUI/StatCard.tsx` | S85-1 | 統計卡片組件 |
| `frontend/src/components/DevUI/EventPieChart.tsx` | S85-1 | 事件餅圖組件 |
| `frontend/src/components/DevUI/LiveIndicator.tsx` | S85-2 | 實時狀態指示器 |
| `frontend/src/components/DevUI/EventFilter.tsx` | S85-3 | 事件過濾器組件 |
| `frontend/src/hooks/useDevToolsStream.ts` | S85-2 | SSE 連接 Hook |
| `frontend/src/hooks/useEventFilter.ts` | S85-3 | 過濾器 Hook |

---

## Verification Checklist

### Functional Tests
- [ ] 統計數據正確計算
- [ ] SSE 實時更新正常
- [ ] 過濾功能正常
- [ ] 搜索功能正常

### UI/UX Tests
- [ ] 統計面板視覺效果良好
- [ ] 實時指示器直觀
- [ ] 過濾器易於使用
- [ ] 整體用戶體驗流暢

---

**Last Updated**: 2026-01-13
