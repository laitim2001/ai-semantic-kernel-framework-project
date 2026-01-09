# Sprint 73 Checklist: Token/Time Fix + Sidebar Collapse

## Sprint Information

| Field | Value |
|-------|-------|
| **Sprint** | 73 |
| **Phase** | 19 - UI Enhancement |
| **Focus** | Metrics Fix, Sidebar Collapse |
| **Points** | 8 pts |
| **Status** | In Progress |

---

## Pre-Sprint Checklist

- [x] Phase 18 completed
- [x] `useExecutionMetrics` hook exists
- [x] Sidebar component exists
- [x] AppLayout component exists

---

## Story Completion Tracking

### S73-1: Token/Time Metrics Fix (3 pts)

| Task | Status | Notes |
|------|--------|-------|
| Import `useExecutionMetrics` hook | [ ] | |
| Add `startTimer()` call when streaming starts | [ ] | |
| Add `stopTimer()` call when streaming ends | [ ] | |
| Update `metrics.time` to use hook value | [ ] | |
| Verify time displays correctly (0ms -> 1.5s -> 2m 30s) | [ ] | |

**Files Modified**:
- [ ] `frontend/src/pages/UnifiedChat.tsx`

**Test Cases**:
- [ ] Send message, time starts counting
- [ ] Response complete, time stops
- [ ] Time format correct for different durations
- [ ] No memory leaks (timer cleanup)

---

### S73-2: Sidebar Collapse (5 pts)

| Task | Status | Notes |
|------|--------|-------|
| Add `sidebarCollapsed` state to AppLayout | [ ] | useState(false) |
| Add `isCollapsed` prop to Sidebar | [ ] | |
| Add `onToggle` prop to Sidebar | [ ] | |
| Change Sidebar width based on state | [ ] | w-64 / w-16 |
| Hide text labels when collapsed | [ ] | Conditional render |
| Add toggle button to Sidebar | [ ] | ChevronLeft/Right |
| Add smooth transition animation | [ ] | transition-all duration-300 |
| Add tooltip for collapsed icons | [ ] | title attribute |

**Files Modified**:
- [ ] `frontend/src/components/layout/AppLayout.tsx`
- [ ] `frontend/src/components/layout/Sidebar.tsx`

**Test Cases**:
- [ ] Click toggle, Sidebar collapses
- [ ] Click toggle again, Sidebar expands
- [ ] Collapsed shows only icons
- [ ] Expanded shows icons + text
- [ ] Animation smooth (no jumps)
- [ ] Hover on collapsed icon shows tooltip
- [ ] Page content adjusts to Sidebar width

---

## Integration Testing

| Scenario | Status | Notes |
|----------|--------|-------|
| Chat page with new timer | [ ] | |
| Sidebar collapse while chatting | [ ] | |
| Refresh page, Sidebar state reset | [ ] | Expected behavior |
| Mobile responsiveness | [ ] | Optional |

---

## Post-Sprint Checklist

- [ ] All stories complete (8 pts)
- [ ] Time display works correctly
- [ ] Sidebar collapse works correctly
- [ ] No visual regressions
- [ ] Code reviewed

---

**Checklist Status**: In Progress
**Last Updated**: 2026-01-09
