# Sprint 84: 時間線可視化

> **Sprint**: 84
> **Story Points**: 16 pts
> **目標**: 實現執行事件的時間線可視化組件

---

## User Stories

### S84-1: 時間線組件設計和實現 (8 pts)

**描述**: 實現核心時間線可視化組件，直觀展示執行事件流程

**驗收標準**:
- [ ] 垂直時間線布局
- [ ] 事件節點顯示：
  - 事件類型圖標
  - 時間戳
  - 持續時間條
- [ ] 事件配對顯示：
  - LLM_REQUEST ↔ LLM_RESPONSE
  - TOOL_CALL ↔ TOOL_RESULT
  - WORKFLOW_START ↔ WORKFLOW_END
- [ ] 持續時間可視化（條形圖）
- [ ] 滾動和縮放功能
- [ ] 懸停顯示詳情

**API 調用**:
```typescript
GET /api/v1/devtools/traces/{execution_id}/timeline
```

**交付物**:
- `frontend/src/components/DevUI/Timeline.tsx`
- `frontend/src/components/DevUI/TimelineNode.tsx`
- `frontend/src/components/DevUI/DurationBar.tsx`

---

### S84-2: 事件樹形結構顯示 (5 pts)

**描述**: 實現嵌套事件的樹形結構顯示

**驗收標準**:
- [ ] 支持 parent_event_id 層級結構
- [ ] 展開/收起子事件
- [ ] 縮進顯示層級關係
- [ ] 連接線顯示父子關係
- [ ] 遞歸渲染子事件

**事件層級示例**:
```
WORKFLOW_START
├── EXECUTOR_START
│   ├── LLM_REQUEST
│   └── LLM_RESPONSE
│   └── TOOL_CALL
│       └── TOOL_RESULT
└── EXECUTOR_END
WORKFLOW_END
```

**交付物**:
- `frontend/src/components/DevUI/EventTree.tsx`
- `frontend/src/components/DevUI/TreeNode.tsx`

---

### S84-3: LLM/Tool 事件詳情面板 (3 pts)

**描述**: 實現 LLM 和工具事件的專用詳情面板

**驗收標準**:
- [ ] LLM 事件面板：
  - Prompt 顯示 (折疊長文本)
  - Response 顯示
  - Token 使用量
  - 模型名稱
  - 耗時
- [ ] Tool 事件面板：
  - 工具名稱
  - 參數 (JSON 格式化)
  - 結果
  - 耗時
- [ ] 複製功能（複製 prompt/result）
- [ ] JSON 格式化顯示

**交付物**:
- `frontend/src/components/DevUI/EventPanel.tsx`
- `frontend/src/components/DevUI/LLMEventPanel.tsx`
- `frontend/src/components/DevUI/ToolEventPanel.tsx`

---

## UI 設計參考

### 時間線樣式

```
時間軸                    事件                          持續時間
──────────────────────────────────────────────────────────────
10:00:00.000  ●────────  WORKFLOW_START                 0ms
10:00:00.050  │  ●──     LLM_REQUEST                    
10:00:02.150  │  ●──     LLM_RESPONSE              2100ms ████████
10:00:02.200  │  ●──     TOOL_CALL
10:00:02.350  │  ●──     TOOL_RESULT                150ms ██
10:00:02.400  ●────────  WORKFLOW_END               2400ms
──────────────────────────────────────────────────────────────
```

### 事件類型圖標

| 事件類型 | 圖標 | 顏色 |
|---------|------|------|
| WORKFLOW_* | ⚙️ | 藍色 |
| LLM_* | 🤖 | 紫色 |
| TOOL_* | 🔧 | 綠色 |
| CHECKPOINT_* | ✅ | 黃色 |
| ERROR | ❌ | 紅色 |
| WARNING | ⚠️ | 橙色 |

---

## 技術實現

### Timeline 組件 API

```typescript
interface TimelineProps {
  executionId: string;
  events: TimelineEntry[];
  onEventClick?: (event: TimelineEntry) => void;
  selectedEventId?: string;
}

interface TimelineEntry {
  timestamp: string;
  event_type: string;
  label: string;
  details: string;
  severity: string;
  duration_ms?: number;
  children: TimelineEntry[];
}
```

---

## 測試計劃

- [ ] 時間線渲染測試
- [ ] 事件配對邏輯測試
- [ ] 樹形結構展開/收起測試
- [ ] 持續時間計算測試
- [ ] 事件詳情面板測試

---

## 更新歷史

| 日期 | 說明 |
|------|------|
| 2026-01-13 | 初始規劃 |
