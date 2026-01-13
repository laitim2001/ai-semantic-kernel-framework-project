# Sprint 83 Checklist: DevUI 核心頁面

## Sprint Status

| Metric | Value |
|--------|-------|
| **Total Stories** | 3 |
| **Total Points** | 14 pts |
| **Completed** | 0 |
| **In Progress** | 0 |
| **Status** | 📋 規劃中 |

---

## Stories

### S83-1: DevUI 頁面路由和布局 (3 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `/devui` 路由配置
- [ ] 創建 `frontend/src/pages/DevUI/index.tsx`
- [ ] 創建 `frontend/src/pages/DevUI/Layout.tsx`
- [ ] 實現側邊欄導航菜單
- [ ] 實現麵包屑導航

**Acceptance Criteria**:
- [ ] `/devui` 路由可訪問
- [ ] 頁面布局正確 (側邊欄 + 主內容區)
- [ ] 導航菜單功能正常
- [ ] 麵包屑導航正確顯示

---

### S83-2: 追蹤列表頁面 (5 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `frontend/src/pages/DevUI/TraceList.tsx`
- [ ] 創建 `frontend/src/api/devtools.ts` API 客戶端
- [ ] 創建 `frontend/src/hooks/useDevTools.ts`
- [ ] 創建 `frontend/src/types/devtools.ts` 類型定義
- [ ] 實現追蹤列表表格
- [ ] 實現分頁功能 (每頁 20 條)
- [ ] 實現狀態過濾器
- [ ] 實現工作流 ID 過濾器
- [ ] 實現行點擊跳轉

**Acceptance Criteria**:
- [ ] 追蹤列表正確顯示
- [ ] 分頁功能正常
- [ ] 過濾功能正常
- [ ] 點擊行可跳轉到詳情頁
- [ ] 加載狀態和錯誤處理正確

---

### S83-3: 追蹤詳情頁面 (6 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `frontend/src/pages/DevUI/TraceDetail.tsx`
- [ ] 創建 `frontend/src/components/DevUI/EventList.tsx`
- [ ] 創建 `frontend/src/components/DevUI/EventDetail.tsx`
- [ ] 實現追蹤基本信息顯示
- [ ] 實現事件列表視圖
- [ ] 實現事件詳情展開
- [ ] 實現刪除追蹤功能
- [ ] 實現返回列表導航

**Acceptance Criteria**:
- [ ] 追蹤詳情正確顯示
- [ ] 事件列表按時間排序
- [ ] 事件詳情可展開/收起
- [ ] 刪除功能正常
- [ ] 返回導航正常

---

## Files Summary

### New Files
| File | Story | Description |
|------|-------|-------------|
| `frontend/src/pages/DevUI/index.tsx` | S83-1 | DevUI 主路由 |
| `frontend/src/pages/DevUI/Layout.tsx` | S83-1 | DevUI 布局組件 |
| `frontend/src/pages/DevUI/TraceList.tsx` | S83-2 | 追蹤列表頁面 |
| `frontend/src/pages/DevUI/TraceDetail.tsx` | S83-3 | 追蹤詳情頁面 |
| `frontend/src/components/DevUI/EventList.tsx` | S83-3 | 事件列表組件 |
| `frontend/src/components/DevUI/EventDetail.tsx` | S83-3 | 事件詳情組件 |
| `frontend/src/api/devtools.ts` | S83-2 | DevTools API 客戶端 |
| `frontend/src/hooks/useDevTools.ts` | S83-2 | DevTools Hook |
| `frontend/src/types/devtools.ts` | S83-2 | DevTools 類型定義 |

---

## Verification Checklist

### Functional Tests
- [ ] DevUI 頁面可正常訪問
- [ ] 追蹤列表正確加載
- [ ] 分頁功能正常
- [ ] 過濾功能正常
- [ ] 追蹤詳情正確顯示
- [ ] 事件列表正確顯示
- [ ] 刪除功能正常

### UI/UX Tests
- [ ] 響應式布局正確
- [ ] 加載狀態正確顯示
- [ ] 錯誤狀態正確處理
- [ ] 導航流程順暢

---

**Last Updated**: 2026-01-13
