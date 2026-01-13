# Sprint 84 Checklist: 時間線可視化

## Sprint Status

| Metric | Value |
|--------|-------|
| **Total Stories** | 3 |
| **Total Points** | 16 pts |
| **Completed** | 0 |
| **In Progress** | 0 |
| **Status** | 📋 規劃中 |

---

## Stories

### S84-1: 時間線組件設計和實現 (8 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `frontend/src/components/DevUI/Timeline.tsx`
- [ ] 創建 `frontend/src/components/DevUI/TimelineNode.tsx`
- [ ] 創建 `frontend/src/components/DevUI/DurationBar.tsx`
- [ ] 實現垂直時間線布局
- [ ] 實現事件節點顯示 (類型圖標、時間戳、持續時間條)
- [ ] 實現事件配對顯示 (LLM_REQUEST ↔ LLM_RESPONSE 等)
- [ ] 實現持續時間可視化 (條形圖)
- [ ] 實現滾動和縮放功能
- [ ] 實現懸停顯示詳情

**Acceptance Criteria**:
- [ ] 時間線正確渲染
- [ ] 事件配對正確顯示
- [ ] 持續時間條形圖正確
- [ ] 滾動和縮放功能正常
- [ ] 懸停詳情正確顯示

---

### S84-2: 事件樹形結構顯示 (5 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `frontend/src/components/DevUI/EventTree.tsx`
- [ ] 創建 `frontend/src/components/DevUI/TreeNode.tsx`
- [ ] 實現 parent_event_id 層級結構解析
- [ ] 實現展開/收起子事件功能
- [ ] 實現縮進顯示層級關係
- [ ] 實現連接線顯示父子關係
- [ ] 實現遞歸渲染子事件

**Acceptance Criteria**:
- [ ] 樹形結構正確渲染
- [ ] 展開/收起功能正常
- [ ] 層級縮進正確
- [ ] 父子連接線正確顯示

---

### S84-3: LLM/Tool 事件詳情面板 (3 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `frontend/src/components/DevUI/EventPanel.tsx`
- [ ] 創建 `frontend/src/components/DevUI/LLMEventPanel.tsx`
- [ ] 創建 `frontend/src/components/DevUI/ToolEventPanel.tsx`
- [ ] 實現 LLM 事件面板 (Prompt、Response、Token、模型、耗時)
- [ ] 實現 Tool 事件面板 (工具名稱、參數、結果、耗時)
- [ ] 實現複製功能 (複製 prompt/result)
- [ ] 實現 JSON 格式化顯示

**Acceptance Criteria**:
- [ ] LLM 事件面板正確顯示
- [ ] Tool 事件面板正確顯示
- [ ] 複製功能正常
- [ ] JSON 格式化正確

---

## Files Summary

### New Files
| File | Story | Description |
|------|-------|-------------|
| `frontend/src/components/DevUI/Timeline.tsx` | S84-1 | 時間線組件 |
| `frontend/src/components/DevUI/TimelineNode.tsx` | S84-1 | 時間線節點組件 |
| `frontend/src/components/DevUI/DurationBar.tsx` | S84-1 | 持續時間條組件 |
| `frontend/src/components/DevUI/EventTree.tsx` | S84-2 | 事件樹組件 |
| `frontend/src/components/DevUI/TreeNode.tsx` | S84-2 | 樹節點組件 |
| `frontend/src/components/DevUI/EventPanel.tsx` | S84-3 | 事件面板基礎組件 |
| `frontend/src/components/DevUI/LLMEventPanel.tsx` | S84-3 | LLM 事件面板 |
| `frontend/src/components/DevUI/ToolEventPanel.tsx` | S84-3 | Tool 事件面板 |

---

## Verification Checklist

### Functional Tests
- [ ] 時間線正確渲染所有事件
- [ ] 事件配對邏輯正確
- [ ] 樹形結構展開/收起正常
- [ ] 事件詳情面板正確顯示
- [ ] 複製功能正常

### UI/UX Tests
- [ ] 時間線視覺效果良好
- [ ] 持續時間條形圖直觀
- [ ] 樹形結構縮進清晰
- [ ] 事件類型圖標正確

---

**Last Updated**: 2026-01-13
