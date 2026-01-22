# HITL Chat Page Improvements - 2026-01-22

## Overview

This document records all bug fixes and feature changes related to the Human-in-the-Loop (HITL) functionality in the `/chat` page.

---

## Bug Fixes

### BF-1: Approval Request Uses Wrong ID Type

**Problem**: When clicking Approve/Reject buttons, the frontend sent `toolCallId` instead of `approvalId` to the backend API, causing 404 errors.

**Root Cause**:
- `MessageList.tsx` passed `approval.toolCallId` to `onApprove()` and `onReject()`
- Backend API expects `approvalId` as the URL parameter

**Error Log**:
```
POST /api/v1/ag-ui/approvals/tc-Bash-dc46c1a5/approve 404
{"error":"APPROVAL_NOT_FOUND","message":"Approval request not found: tc-Bash-dc46c1a5"}
```

**Fix**:
- Changed `MessageList.tsx` to pass `approval.approvalId` instead of `approval.toolCallId`
- Updated parameter naming in `UnifiedChat.tsx` for clarity

**Files Changed**:
- `frontend/src/components/unified-chat/MessageList.tsx`
- `frontend/src/pages/UnifiedChat.tsx`

---

### BF-2: Expired Approval Blocks New Approvals

**Problem**: After an approval request expired, sending the same message again would not trigger a new approval request.

**Root Cause**:
- Expired approvals remained in `pendingApprovals` list
- No cleanup mechanism existed for expired items
- This potentially blocked new approvals from being added

**Fix**:
- Added `removeExpiredApproval()` function in `useUnifiedChat.ts`
- `ApprovalMessageCard` calls `onExpired()` callback 3 seconds after expiry
- Parent component removes the expired approval, allowing new ones

**Files Changed**:
- `frontend/src/hooks/useUnifiedChat.ts`
- `frontend/src/components/unified-chat/ApprovalMessageCard.tsx`
- `frontend/src/components/unified-chat/MessageList.tsx`
- `frontend/src/components/unified-chat/ChatArea.tsx`
- `frontend/src/pages/UnifiedChat.tsx`

---

### BF-3: Approval Card Disappears After Action

**Problem**: When user clicked Approve or Reject, the approval card immediately disappeared, leaving no record of what action was taken.

**Root Cause**:
- `removePendingApproval()` function filtered out the approval from the list
- No history was preserved

**Fix**:
- Replaced `removePendingApproval()` with `resolveApproval()` that updates status instead of removing
- Added `status`, `resolvedAt`, and `rejectReason` fields to `PendingApproval` type
- `ApprovalMessageCard` now shows resolved state with appropriate styling

**Files Changed**:
- `frontend/src/types/ag-ui.ts`
- `frontend/src/hooks/useUnifiedChat.ts`
- `frontend/src/components/unified-chat/ApprovalMessageCard.tsx`

---

### BF-4: No Auto-Scroll When Approval Appears

**Problem**: When a new approval request appeared, the chat did not auto-scroll to show it. Users had to manually scroll down.

**Root Cause**:
- `ChatArea.tsx` only watched `messages` and `isStreaming` for scroll triggers
- `pendingApprovals` changes were not monitored

**Fix**:
- Added `pendingApprovals.length` to the `useEffect` dependency array for auto-scroll

**Files Changed**:
- `frontend/src/components/unified-chat/ChatArea.tsx`

---

## Feature Changes

### FC-1: Inline Approval as AI Message (ApprovalMessageCard)

**Previous Behavior**:
- Low/medium risk approvals used `InlineApproval` component
- High/critical risk approvals used `ApprovalDialog` modal

**New Behavior**:
- All approvals now display as `ApprovalMessageCard` - a card that looks like an AI message in the chat flow
- This provides a more natural conversational experience
- Modal dialog is no longer used

**Features**:
- AI avatar with risk-based coloring
- Tool name, arguments (collapsible), and risk level badge
- Countdown timer showing time until expiry
- Approve/Reject buttons with optional rejection reason input
- Resolved state display (Approved/Rejected/Expired) with timestamp

**Files Changed**:
- `frontend/src/components/unified-chat/ApprovalMessageCard.tsx` (NEW)
- `frontend/src/components/unified-chat/MessageList.tsx`
- `frontend/src/components/unified-chat/index.ts`
- `frontend/src/pages/UnifiedChat.tsx` (removed ApprovalDialog usage)

---

### FC-2: Approval Status Tracking

**New Fields in `PendingApproval`**:
```typescript
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface PendingApproval {
  // ... existing fields ...
  status?: ApprovalStatus;
  resolvedAt?: string;
  rejectReason?: string;
}
```

**UI States**:
| Status | Icon | Color | Description |
|--------|------|-------|-------------|
| pending | Clock | Blue | Waiting for user action |
| approved | CheckCircle | Green | User approved the tool call |
| rejected | XCircle | Red | User rejected with optional reason |
| expired | Timer | Gray | Approval timed out |

**Files Changed**:
- `frontend/src/types/ag-ui.ts`
- `frontend/src/types/unified-chat.ts`

---

### FC-3: New Hook Functions

**Added to `useUnifiedChat` return value**:

```typescript
// Resolve approval - update status instead of removing
resolveApproval: (approvalId: string, status: 'approved' | 'rejected' | 'expired', rejectReason?: string) => void;

// Remove expired approval completely
removeExpiredApproval: (approvalId: string) => void;
```

**Files Changed**:
- `frontend/src/hooks/useUnifiedChat.ts`

---

## Backend Changes (Related)

### BE-1: HITL Approval Flow Fixes (Previous Session)

The following backend fixes were applied to enable the HITL flow:

1. **All approval-required tools now require approval** - Removed condition that skipped approval for low/medium risk
2. **Support for `session_id=None`** - Fixed filtering logic in `get_pending()` to include approvals with no session
3. **Heartbeat interval reduced** - Changed from 10s to 2s for better responsiveness

**Files Changed**:
- `backend/src/api/v1/ag_ui/dependencies.py`
- `backend/src/integrations/ag_ui/features/human_in_loop.py`
- `backend/src/integrations/ag_ui/bridge.py`

---

## Testing Checklist

- [ ] Send a message that triggers a tool call (e.g., "create a file")
- [ ] Verify approval card appears at bottom of chat
- [ ] Verify chat auto-scrolls to show the approval card
- [ ] Click "Approve" - verify card shows "Approved" status with timestamp
- [ ] Click "Reject" with reason - verify card shows "Rejected" status with reason
- [ ] Wait for approval to expire - verify card shows "Expired" and disappears after 3s
- [ ] After expiry, send same message - verify new approval appears

---

## Summary of File Changes

### Frontend (New)
- `frontend/src/components/unified-chat/ApprovalMessageCard.tsx`

### Frontend (Modified)
- `frontend/src/components/unified-chat/ChatArea.tsx`
- `frontend/src/components/unified-chat/MessageList.tsx`
- `frontend/src/components/unified-chat/index.ts`
- `frontend/src/hooks/useUnifiedChat.ts`
- `frontend/src/pages/UnifiedChat.tsx`
- `frontend/src/types/ag-ui.ts`
- `frontend/src/types/unified-chat.ts`

### Backend (Modified)
- `backend/src/api/v1/ag_ui/dependencies.py`
- `backend/src/integrations/ag_ui/bridge.py`
- `backend/src/integrations/ag_ui/features/human_in_loop.py`

---

**Author**: Claude Code
**Date**: 2026-01-22
**Sprint**: 99 (HITL UX Improvement)
