# Phase 24 完成檢查清單

> **Phase**: 24 - DevUI 前端實現
> **Sprint**: S83-85
> **狀態**: 📋 規劃中

---

## Sprint 83: DevUI 核心頁面

### S83-1: 頁面路由和布局 (3 pts)
- [ ] 創建 `/devui` 路由配置
- [ ] 實現 DevUI 頁面布局
- [ ] 添加側邊欄導航菜單
- [ ] 實現麵包屑導航

### S83-2: 追蹤列表頁面 (5 pts)
- [ ] 追蹤列表表格組件
- [ ] 分頁功能實現
- [ ] 狀態過濾器
- [ ] 工作流 ID 過濾器
- [ ] 行點擊跳轉
- [ ] 加載狀態和錯誤處理

### S83-3: 追蹤詳情頁面 (6 pts)
- [ ] 追蹤基本信息顯示
- [ ] 事件列表視圖
- [ ] 事件詳情展開
- [ ] 刪除追蹤功能
- [ ] 返回列表導航

---

## Sprint 84: 時間線可視化

### S84-1: 時間線組件 (8 pts)
- [ ] 垂直時間線布局
- [ ] 事件節點渲染
- [ ] 事件配對顯示
- [ ] 持續時間條形圖
- [ ] 滾動和縮放
- [ ] 懸停詳情提示

### S84-2: 事件樹形結構 (5 pts)
- [ ] 樹形結構渲染
- [ ] 展開/收起功能
- [ ] 層級縮進
- [ ] 父子連接線

### S84-3: 事件詳情面板 (3 pts)
- [ ] LLM 事件面板
- [ ] Tool 事件面板
- [ ] JSON 格式化顯示
- [ ] 複製功能

---

## Sprint 85: 統計和進階功能

### S85-1: 統計儀表板 (5 pts)
- [ ] LLM 調用統計卡片
- [ ] 工具調用統計卡片
- [ ] 事件類型餅圖
- [ ] 錯誤/警告統計
- [ ] 檢查點統計

### S85-2: 實時追蹤 (5 pts)
- [ ] SSE 連接建立
- [ ] 實時事件接收
- [ ] 自動滾動
- [ ] 連接狀態指示器
- [ ] 暫停/繼續功能

### S85-3: 事件過濾和搜索 (2 pts)
- [ ] 事件類型多選過濾
- [ ] 嚴重性過濾
- [ ] 文本搜索
- [ ] 清除過濾器

---

## 技術驗收

### 代碼品質
- [ ] TypeScript 類型完整
- [ ] ESLint 無錯誤
- [ ] 組件文檔註釋

### 測試覆蓋
- [ ] 組件單元測試
- [ ] Hook 測試
- [ ] API 模擬測試

### 性能
- [ ] 大量事件時的虛擬列表
- [ ] 懶加載實現
- [ ] 無內存洩漏

### 可訪問性
- [ ] 鍵盤導航
- [ ] 螢幕閱讀器支持
- [ ] 顏色對比度

---

## 文件清單

### 頁面組件
- [ ] `frontend/src/pages/DevUI/index.tsx`
- [ ] `frontend/src/pages/DevUI/Layout.tsx`
- [ ] `frontend/src/pages/DevUI/TraceList.tsx`
- [ ] `frontend/src/pages/DevUI/TraceDetail.tsx`

### UI 組件
- [ ] `frontend/src/components/DevUI/Timeline.tsx`
- [ ] `frontend/src/components/DevUI/EventTree.tsx`
- [ ] `frontend/src/components/DevUI/EventPanel.tsx`
- [ ] `frontend/src/components/DevUI/Statistics.tsx`
- [ ] `frontend/src/components/DevUI/EventFilter.tsx`

### Hooks 和 API
- [ ] `frontend/src/hooks/useDevTools.ts`
- [ ] `frontend/src/hooks/useDevToolsStream.ts`
- [ ] `frontend/src/api/devtools.ts`

### 類型定義
- [ ] `frontend/src/types/devtools.ts`

---

## 更新歷史

| 日期 | 說明 |
|------|------|
| 2026-01-13 | 初始版本 |
