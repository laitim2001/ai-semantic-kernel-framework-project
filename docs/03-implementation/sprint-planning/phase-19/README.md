# Phase 19: UI Enhancement - Sidebar + Chat History + Metrics

## Overview

Phase 19 fixes three UI issues to improve user experience:

1. **Sidebar Collapse** - Collapsible sidebar for more screen space
2. **Chat History Panel** - Conversation history list (like ChatGPT)
3. **Token/Time Fix** - Fix metrics display not updating

## Phase Status

| Status | Value |
|--------|-------|
| **Phase Status** | In Progress |
| **Duration** | 2 sprints |
| **Total Story Points** | 21 pts |
| **Start Date** | 2026-01-09 |

## Problem Analysis

### Problem 1: Sidebar Cannot Collapse (Medium Priority)
- **Current**: Sidebar fixed at `w-64` (256px), no collapse feature
- **Need**: Collapsible to `w-16` (64px), showing only icons

### Problem 2: Chat Page Missing History (High Priority)
- **Current**: Chat page only has chat window, no history panel
- **Need**: ChatGPT-like layout with history on left, chat on right

### Problem 3: Token/Time Not Updating (High Priority)
- **Current**:
  - Time hardcoded to 0 (`time: { total: 0, isRunning: isStreaming }`)
  - Token depends on `TOKEN_UPDATE` SSE event, but backend doesn't send it
- **Need**: Correct display of execution time and token usage

## Sprint Overview

| Sprint | Focus | Story Points | Status | Documents |
|--------|-------|--------------|--------|-----------|
| **Sprint 73** | Token/Time Fix + Sidebar Collapse | 8 pts | In Progress | [Plan](sprint-73-plan.md) / [Checklist](sprint-73-checklist.md) |
| **Sprint 74** | Chat History Panel | 13 pts | Pending | [Plan](sprint-74-plan.md) / [Checklist](sprint-74-checklist.md) |
| **Total** | | **21 pts** | | |

### Sprint 73 Stories

| Story | Feature | Points | Status |
|-------|---------|--------|--------|
| S73-1 | Token/Time Metrics Fix | 3 pts | Pending |
| S73-2 | Sidebar Collapse | 5 pts | Pending |
| **Total** | | **8 pts** | |

### Sprint 74 Stories

| Story | Feature | Points | Status |
|-------|---------|--------|--------|
| S74-1 | ChatHistoryPanel Component | 5 pts | Pending |
| S74-2 | useChatThreads Hook | 3 pts | Pending |
| S74-3 | UnifiedChat Layout Integration | 5 pts | Pending |
| **Total** | | **13 pts** | |

## Architecture

### Target Layout
```
+----------------------------------------------------------+
| AppLayout Header                                          |
+----------+-----------------------------------------------+
| Sidebar  |  +-------------+-----------------------------+
| (w-64 or |  | ChatHistory |      ChatArea               |
|  w-16    |  |  - New Chat |                             |
| collapse)|  |  - Thread 1 |                             |
|          |  |  - Thread 2 |                             |
|          |  |  - ...      |                             |
|          |  +-------------+-----------------------------+
|          |  |      ChatInput + StatusBar               |
+----------+-----------------------------------------------+
```

### Component Structure
```
frontend/src/
+-- components/
|   +-- layout/
|   |   +-- AppLayout.tsx         # + sidebarCollapsed state
|   |   +-- Sidebar.tsx           # + isCollapsed prop + toggle
|   +-- unified-chat/
|       +-- ChatHistoryPanel.tsx  # NEW: History panel
|       +-- index.ts              # + export ChatHistoryPanel
+-- hooks/
|   +-- useChatThreads.ts         # NEW: Thread management
|   +-- useExecutionMetrics.ts    # EXISTING: Timer logic
+-- pages/
    +-- UnifiedChat.tsx           # + useExecutionMetrics + ChatHistoryPanel
```

## Technology Stack

- **No New Dependencies** - Uses existing React, Zustand, Tailwind
- **localStorage** - Thread persistence (MVP approach)
- **useExecutionMetrics** - Existing hook for timer functionality

## Success Criteria

### Sprint 73 Verification
- [ ] Time starts counting when streaming begins
- [ ] Time stops when streaming ends
- [ ] Time displays correctly (0ms -> 1.5s -> 2m 30s)
- [ ] Sidebar can collapse (256px -> 64px)
- [ ] Collapsed sidebar shows only icons
- [ ] Expanded sidebar shows full text
- [ ] Smooth transition animation (300ms)

### Sprint 74 Verification
- [ ] Chat page shows history panel on left
- [ ] "New Chat" button creates new thread
- [ ] Click history to switch conversations
- [ ] Thread title generated from first message
- [ ] History persists after page refresh (localStorage)
- [ ] History panel can collapse/expand

## Dependencies

### Prerequisites
- Phase 18 completed (Authentication)
- `useExecutionMetrics` hook exists
- UnifiedChat page exists with working chat

### No New Dependencies
- All features use existing React, Zustand, Tailwind

## Related Documentation

- [Phase 18: Authentication System](../phase-18/README.md)
- [UnifiedChat Component](../../../../frontend/src/pages/UnifiedChat.tsx)
- [useExecutionMetrics Hook](../../../../frontend/src/hooks/useExecutionMetrics.ts)

---

**Phase Status**: In Progress
**Created**: 2026-01-09
**Total Story Points**: 21 pts
