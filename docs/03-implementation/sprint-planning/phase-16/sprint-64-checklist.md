# Sprint 64 Checklist: Approval Flow & Risk Indicators

## Pre-Sprint Verification

- [ ] Sprint 62-63 components completed
- [ ] Backend approval API endpoints operational
- [ ] Risk assessment service functioning
- [ ] AG-UI events include approval metadata

---

## S64-1: useApprovalFlow Hook (8 pts)

### Files Created
- [ ] `frontend/src/hooks/useApprovalFlow.ts`

### Implementation Checklist
- [ ] Hook tracks `pendingApprovals` array
- [ ] Hook manages `dialogApproval` state
- [ ] Hook provides `isProcessing` state
- [ ] `approve(toolCallId)` function implemented
- [ ] `reject(toolCallId, reason?)` function implemented
- [ ] `dismissDialog()` function implemented
- [ ] Timeout handling for expired approvals
- [ ] Integration with AG-UI TOOL_CALL events

### Hook API Verification
```typescript
const {
  pendingApprovals,      // PendingApproval[]
  dialogApproval,        // PendingApproval | null
  isProcessing,          // boolean
  approve,               // (id: string) => Promise<void>
  reject,                // (id: string, reason?: string) => Promise<void>
  dismissDialog,         // () => void
  hasPendingApprovals,   // boolean
  highRiskCount,         // number
} = useApprovalFlow();
```

### Verification Steps
- [ ] New approval adds to pendingApprovals
- [ ] High-risk approval sets dialogApproval
- [ ] approve() removes from pending
- [ ] reject() removes from pending
- [ ] Expired approvals handled correctly

---

## S64-2: ApprovalDialog Component (7 pts)

### Files Created
- [ ] `frontend/src/components/unified-chat/ApprovalDialog.tsx`

### Implementation Checklist
- [ ] Dialog opens for high/critical risk approvals
- [ ] Tool name displayed prominently
- [ ] Tool arguments shown (JSON formatted)
- [ ] Risk level badge with appropriate color
- [ ] Risk factors listed as bullet points
- [ ] Countdown timer for timeout (if applicable)
- [ ] Rejection reason textarea
- [ ] Approve button with loading state
- [ ] Reject button with loading state
- [ ] Close/dismiss button
- [ ] Keyboard accessible (Tab, Enter, Escape)

### Component Props Verification
```typescript
<ApprovalDialog
  approval={pendingApproval}
  onApprove={() => approve(id)}
  onReject={(reason) => reject(id, reason)}
  onDismiss={dismissDialog}
  isProcessing={isProcessing}
/>
```

### Verification Steps
- [ ] Dialog renders with correct approval data
- [ ] Risk level shows correct color
- [ ] Approve button calls onApprove
- [ ] Reject button calls onReject with reason
- [ ] Escape key closes dialog
- [ ] Click outside does NOT close (prevent accidental dismiss)

---

## S64-3: Risk Indicator System (5 pts)

### Files Created/Modified
- [ ] `frontend/src/components/unified-chat/RiskIndicator.tsx` - New
- [ ] `frontend/src/components/unified-chat/StatusBar.tsx` - Updated

### Implementation Checklist
- [ ] RiskIndicator component created
- [ ] Color coding for each level:
  - [ ] Low: Green (bg-green-500)
  - [ ] Medium: Yellow (bg-yellow-500)
  - [ ] High: Orange (bg-orange-500)
  - [ ] Critical: Red (bg-red-500)
- [ ] Risk score display (0-100)
- [ ] Tooltip with risk factors
- [ ] Size variants (sm, md, lg)
- [ ] Pulse animation for high/critical
- [ ] StatusBar integration

### Component Props Verification
```typescript
<RiskIndicator
  level="high"
  score={75}
  factors={['File deletion', 'External API call']}
  size="md"
  showScore={true}
  showTooltip={true}
/>
```

### Verification Steps
- [ ] Low risk shows green indicator
- [ ] Medium risk shows yellow indicator
- [ ] High risk shows orange with animation
- [ ] Critical risk shows red with strong animation
- [ ] Tooltip displays on hover
- [ ] Score displays when showScore=true
- [ ] Different sizes render correctly

---

## S64-4: Approval API Integration (5 pts)

### Files Modified
- [ ] `frontend/src/api/endpoints/ag-ui.ts` - Add approval endpoints
- [ ] `frontend/src/hooks/useApprovalFlow.ts` - API integration

### Implementation Checklist
- [ ] `approvalApi.approve(toolCallId)` function
- [ ] `approvalApi.reject(toolCallId, reason)` function
- [ ] Error handling for API failures
- [ ] Optimistic updates implemented
- [ ] Rollback on API failure
- [ ] Loading states during API calls
- [ ] Success/error toast notifications

### API Endpoints
```typescript
// Approve endpoint
POST /api/v1/ag-ui/tool-calls/:toolCallId/approve
Response: { success: true }

// Reject endpoint
POST /api/v1/ag-ui/tool-calls/:toolCallId/reject
Body: { reason?: string }
Response: { success: true }
```

### Verification Steps
- [ ] Approve API call succeeds
- [ ] Reject API call succeeds
- [ ] Network error shows error message
- [ ] Optimistic update removes approval immediately
- [ ] Failed API restores approval to list
- [ ] Loading spinner shows during API call

---

## Integration Tests

### Approval Flow - Inline (Low/Medium Risk)
- [ ] Tool call with low risk shows inline buttons
- [ ] Tool call with medium risk shows inline buttons
- [ ] Approve click sends API request
- [ ] Reject click sends API request
- [ ] Approval removes inline buttons

### Approval Flow - Dialog (High/Critical Risk)
- [ ] Tool call with high risk opens dialog
- [ ] Tool call with critical risk opens dialog
- [ ] Dialog shows correct tool information
- [ ] Approve from dialog works
- [ ] Reject from dialog works
- [ ] Dialog closes after action

### Risk Indicator
- [ ] StatusBar shows current risk level
- [ ] Risk level updates on new tool calls
- [ ] Risk level resets after completion

### Timeout Handling
- [ ] Countdown timer displays correctly
- [ ] Timer updates every second
- [ ] Expired approval handled (auto-reject or notify)

---

## Code Quality

### TypeScript
- [ ] All approval types properly defined
- [ ] No `any` types in new code
- [ ] API response types defined
- [ ] Event handler types correct

### Accessibility
- [ ] Dialog has aria-label
- [ ] Focus trapped in dialog
- [ ] Escape key closes dialog
- [ ] Buttons have accessible names
- [ ] Risk colors have text alternative

### Performance
- [ ] Dialog lazy-loaded
- [ ] No unnecessary re-renders
- [ ] Timeout cleanup on unmount
- [ ] API calls debounced if needed

---

## Definition of Done

- [ ] All 4 stories completed
- [ ] Manual testing passed
- [ ] TypeScript compilation succeeds
- [ ] ESLint passes
- [ ] Accessibility audit passed
- [ ] API integration verified

---

## Sprint Completion Sign-off

| Item | Status | Date | Notes |
|------|--------|------|-------|
| S64-1 Complete | ⬜ | | |
| S64-2 Complete | ⬜ | | |
| S64-3 Complete | ⬜ | | |
| S64-4 Complete | ⬜ | | |
| Integration Tested | ⬜ | | |
| Sprint Complete | ⬜ | | |

**Total Points**: 25 pts
**Completion Date**: TBD
