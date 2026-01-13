# Sprint 83: DevUI 核心頁面

> **Sprint**: 83
> **Story Points**: 14 pts
> **目標**: 實現 DevUI 的核心頁面框架和基本功能

---

## User Stories

### S83-1: DevUI 頁面路由和布局 (3 pts)

**描述**: 建立 DevUI 的基礎頁面結構和路由配置

**驗收標準**:
- [ ] 創建 `/devui` 路由
- [ ] 實現頁面布局 (側邊欄 + 主內容區)
- [ ] 添加導航菜單
- [ ] 實現麵包屑導航

**交付物**:
- `frontend/src/pages/DevUI/index.tsx`
- `frontend/src/pages/DevUI/Layout.tsx`

---

### S83-2: 追蹤列表頁面 (5 pts)

**描述**: 實現追蹤列表頁面，顯示所有執行追蹤

**驗收標準**:
- [ ] 顯示追蹤列表表格
- [ ] 實現分頁功能 (每頁 20 條)
- [ ] 過濾功能：
  - 按狀態過濾 (running/completed/failed)
  - 按工作流 ID 過濾
- [ ] 顯示追蹤信息：
  - 執行 ID
  - 工作流 ID
  - 開始時間
  - 狀態 (彩色標籤)
  - 事件數量
  - 持續時間
- [ ] 點擊行跳轉到詳情頁

**API 調用**:
```typescript
GET /api/v1/devtools/traces?workflow_id={}&status={}&limit={}
```

**交付物**:
- `frontend/src/pages/DevUI/TraceList.tsx`
- `frontend/src/api/devtools.ts`
- `frontend/src/hooks/useDevTools.ts`

---

### S83-3: 追蹤詳情頁面 (6 pts)

**描述**: 實現追蹤詳情頁面，顯示執行的完整信息

**驗收標準**:
- [ ] 顯示追蹤基本信息
  - 執行 ID、工作流 ID
  - 開始/結束時間
  - 狀態、持續時間
- [ ] 事件列表視圖
  - 按時間排序
  - 顯示事件類型、時間戳、嚴重性
  - 過濾功能
- [ ] 事件詳情展開
  - 顯示事件數據 (JSON)
  - 顯示元數據
- [ ] 刪除追蹤功能

**API 調用**:
```typescript
GET /api/v1/devtools/traces/{execution_id}
GET /api/v1/devtools/traces/{execution_id}/events
DELETE /api/v1/devtools/traces/{execution_id}
```

**交付物**:
- `frontend/src/pages/DevUI/TraceDetail.tsx`
- `frontend/src/components/DevUI/EventList.tsx`
- `frontend/src/components/DevUI/EventDetail.tsx`

---

## 技術實現

### 類型定義

```typescript
// frontend/src/types/devtools.ts
interface Trace {
  id: string;
  execution_id: string;
  workflow_id: string;
  started_at: string;
  ended_at?: string;
  duration_ms?: number;
  status: 'running' | 'completed' | 'failed';
  event_count: number;
  span_count: number;
  metadata: Record<string, any>;
}

interface TraceEvent {
  id: string;
  trace_id: string;
  event_type: string;
  timestamp: string;
  data: Record<string, any>;
  severity: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  parent_event_id?: string;
  executor_id?: string;
  step_number?: number;
  duration_ms?: number;
  tags: string[];
  metadata: Record<string, any>;
}
```

### API 客戶端

```typescript
// frontend/src/api/devtools.ts
export const devToolsApi = {
  listTraces: (params: ListTracesParams) => 
    api.get('/devtools/traces', { params }),
  
  getTrace: (executionId: string) =>
    api.get(`/devtools/traces/${executionId}`),
  
  getEvents: (executionId: string, params: ListEventsParams) =>
    api.get(`/devtools/traces/${executionId}/events`, { params }),
  
  deleteTrace: (executionId: string) =>
    api.delete(`/devtools/traces/${executionId}`),
};
```

---

## 測試計劃

- [ ] 追蹤列表渲染測試
- [ ] 分頁功能測試
- [ ] 過濾功能測試
- [ ] 追蹤詳情渲染測試
- [ ] 事件列表渲染測試
- [ ] API 錯誤處理測試

---

## 更新歷史

| 日期 | 說明 |
|------|------|
| 2026-01-13 | 初始規劃 |
