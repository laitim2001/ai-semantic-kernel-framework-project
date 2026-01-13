# Phase 24: DevUI 前端實現

> **Phase**: 24
> **Sprint**: S83-85
> **Story Points**: 42 pts (預估)
> **狀態**: 📋 規劃中

---

## 概述

### 目標

實現 DevUI (Developer User Interface) 開發者調試介面的前端 UI，提供完整的執行追蹤、時間線可視化和統計分析功能。

### 背景

DevUI 後端 API 已在 Phase 16 完成實現，包含：
- 13 個 REST API 端點 (`/api/v1/devtools/`)
- 25 種事件類型 (工作流、LLM、工具、檢查點等)
- 完整的追蹤、事件、時間跨度管理
- 時間線可視化和統計數據 API
- 56+ 個測試確保可靠性

現在需要實現對應的前端 UI 來充分利用這些 API。

---

## Sprint 規劃

| Sprint | 內容 | Story Points |
|--------|------|--------------|
| S83 | DevUI 核心頁面 | 14 pts |
| S84 | 時間線可視化 | 16 pts |
| S85 | 統計和進階功能 | 12 pts |

---

## 技術架構

```
frontend/src/
├── pages/
│   └── DevUI/
│       ├── index.tsx           # 主路由和布局
│       ├── TraceList.tsx       # 追蹤列表頁面
│       └── TraceDetail.tsx     # 追蹤詳情頁面
├── components/
│   └── DevUI/
│       ├── Timeline.tsx        # 時間線可視化組件
│       ├── EventTree.tsx       # 事件樹形結構
│       ├── EventPanel.tsx      # 事件詳情面板
│       ├── Statistics.tsx      # 統計儀表板
│       └── EventFilter.tsx     # 事件過濾器
├── hooks/
│   └── useDevTools.ts          # DevTools API hooks
└── api/
    └── devtools.ts             # API 客戶端
```

---

## 功能需求

### 1. 追蹤列表 (TraceList)

- 顯示所有執行追蹤
- 支持分頁 (limit: 100)
- 過濾功能：
  - 按工作流 ID
  - 按狀態 (running, completed, failed)
- 顯示基本信息：
  - 執行 ID
  - 開始時間
  - 狀態
  - 事件數量
  - 持續時間

### 2. 追蹤詳情 (TraceDetail)

- 事件列表視圖
- 時間線視圖
- 統計面板
- 事件詳情展開

### 3. 時間線可視化 (Timeline)

- 按時間排序的事件流
- 事件配對顯示 (如 LLM_REQUEST → LLM_RESPONSE)
- 持續時間可視化
- 嵌套事件結構

### 4. 統計儀表板 (Statistics)

- LLM 調用次數和總耗時
- 工具調用次數和總耗時
- 錯誤和警告計數
- 檢查點統計

---

## 後端 API 對照

| 前端功能 | 後端 API |
|---------|---------|
| 追蹤列表 | `GET /api/v1/devtools/traces` |
| 追蹤詳情 | `GET /api/v1/devtools/traces/{execution_id}` |
| 事件列表 | `GET /api/v1/devtools/traces/{execution_id}/events` |
| 時間線 | `GET /api/v1/devtools/traces/{execution_id}/timeline` |
| 統計數據 | `GET /api/v1/devtools/traces/{execution_id}/statistics` |
| 健康檢查 | `GET /api/v1/devtools/health` |

---

## 依賴項

### 前端依賴

已有：
- React 18
- TypeScript
- Zustand (狀態管理)
- TanStack Query (數據獲取)
- Tailwind CSS

建議新增：
- `@tanstack/react-virtual` - 虛擬列表 (大量事件時)
- 或使用現有的組件庫

---

## 驗收標準

### 功能驗收

- [ ] 可以查看所有追蹤列表
- [ ] 可以過濾和分頁追蹤
- [ ] 可以查看追蹤詳情和事件
- [ ] 時間線正確顯示事件順序
- [ ] 統計數據準確顯示
- [ ] 實時追蹤功能正常

### 技術驗收

- [ ] 所有組件有 TypeScript 類型
- [ ] 響應式設計 (桌面/平板)
- [ ] 加載狀態和錯誤處理
- [ ] 單元測試覆蓋

---

## 相關文檔

- 後端 API: `backend/src/api/v1/devtools/routes.py`
- 領域層: `backend/src/domain/devtools/tracer.py`
- API 測試: `backend/tests/unit/test_devtools.py`

---

## 更新歷史

| 日期 | 版本 | 說明 |
|------|------|------|
| 2026-01-13 | 1.0 | 初始規劃 |
