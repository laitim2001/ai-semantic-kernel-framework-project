# Sprint 63 Checklist: Mode Switching & State Management

## Pre-Sprint Verification

- [ ] Sprint 62 components completed
- [ ] AG-UI SSE endpoint operational
- [ ] Backend IntentRouter functioning
- [ ] Development environment ready

---

## S63-1: useUnifiedChat Hook (8 pts)

### Files Created
- [ ] `frontend/src/hooks/useUnifiedChat.ts`

### Implementation Checklist
- [ ] Hook creates and manages SSE connection
- [ ] Connection state tracked (connecting, connected, disconnected)
- [ ] `sendMessage()` function implemented
- [ ] `cancelStream()` function implemented
- [ ] `clearMessages()` function implemented
- [ ] `reconnect()` function implemented
- [ ] Hook integrates with Zustand store
- [ ] Hook provides mode and workflow state

### Hook API Verification
```typescript
// Test hook returns expected interface
const {
  messages,           // ChatMessage[]
  isConnected,        // boolean
  isStreaming,        // boolean
  error,              // Error | null
  sendMessage,        // (content: string) => Promise<void>
  cancelStream,       // () => void
  clearMessages,      // () => void
  reconnect,          // () => void
  currentMode,        // ExecutionMode
  workflowState,      // WorkflowState | null
  pendingApprovals,   // PendingApproval[]
} = useUnifiedChat({ threadId, sessionId });
```

### Verification Steps
- [ ] Hook initializes without errors
- [ ] SSE connection established on mount
- [ ] Connection cleanup on unmount
- [ ] sendMessage sends to backend
- [ ] Messages update in real-time

---

## S63-2: AG-UI Event Integration (7 pts)

### Files Modified
- [ ] `frontend/src/hooks/useUnifiedChat.ts` - Event handlers
- [ ] `frontend/src/stores/unifiedChatStore.ts` - Event-driven updates

### Event Handlers Implemented
- [ ] `RUN_STARTED` - Initialize run state
- [ ] `RUN_FINISHED` - Complete run state
- [ ] `RUN_ERROR` - Handle run errors
- [ ] `TEXT_MESSAGE_START` - Start new message
- [ ] `TEXT_MESSAGE_CONTENT` - Append content delta
- [ ] `TEXT_MESSAGE_END` - Finalize message
- [ ] `TOOL_CALL_START` - Start tool call tracking
- [ ] `TOOL_CALL_ARGS` - Update tool arguments
- [ ] `TOOL_CALL_END` - Complete tool call
- [ ] `STATE_SNAPSHOT` - Full state replacement
- [ ] `STATE_DELTA` - Incremental state update
- [ ] `CUSTOM` - Handle custom events

### Verification Steps
```typescript
// Test each event type
const mockEvents = [
  { type: 'RUN_STARTED', runId: 'test-run' },
  { type: 'TEXT_MESSAGE_START', messageId: 'msg-1', role: 'assistant' },
  { type: 'TEXT_MESSAGE_CONTENT', messageId: 'msg-1', delta: 'Hello ' },
  { type: 'TEXT_MESSAGE_CONTENT', messageId: 'msg-1', delta: 'world!' },
  { type: 'TEXT_MESSAGE_END', messageId: 'msg-1' },
  { type: 'RUN_FINISHED', runId: 'test-run' },
];
```
- [ ] Events process in correct order
- [ ] Message content accumulates correctly
- [ ] Tool calls tracked with proper status
- [ ] State updates reflect in UI

---

## S63-3: Real Mode Detection (5 pts)

### Files Modified
- [ ] `frontend/src/hooks/useHybridMode.ts` - External update support
- [ ] `frontend/src/hooks/useUnifiedChat.ts` - Mode detection handling

### Implementation Checklist
- [ ] Listen for `CUSTOM` events with mode payload
- [ ] Parse `MODE_DETECTED` event type
- [ ] Update `autoMode` when confidence >= 0.7
- [ ] Respect existing manual override
- [ ] Show mode change indicator (optional toast/notification)
- [ ] Log mode changes to console (dev mode)

### Verification Steps
```typescript
// Test mode detection events
const modeEvent = {
  type: 'CUSTOM',
  payload: {
    type: 'MODE_DETECTED',
    mode: 'workflow',
    confidence: 0.85,
    reason: 'Detected multi-step task pattern',
  },
};
```
- [ ] Low confidence (< 0.7) does not change mode
- [ ] High confidence (>= 0.7) updates autoMode
- [ ] Manual override is not overwritten
- [ ] Layout updates when mode changes
- [ ] Mode indicator reflects new mode

---

## S63-4: State Persistence (5 pts)

### Files Modified
- [ ] `frontend/src/stores/unifiedChatStore.ts` - Persistence middleware

### Implementation Checklist
- [ ] Add Zustand `persist` middleware
- [ ] Configure localStorage storage
- [ ] Limit persisted messages (max 100)
- [ ] Persist mode preference
- [ ] Persist manual override setting
- [ ] Handle storage quota errors
- [ ] Clear history function removes persisted data

### Verification Steps
- [ ] Send messages, refresh page
- [ ] Messages restored after refresh
- [ ] Mode preference restored
- [ ] Manual override state restored
- [ ] Clear messages removes persisted data
- [ ] Storage limit respected (no quota errors)

### Storage Schema
```typescript
// Expected localStorage structure
{
  "state": {
    "messages": [...], // max 100
    "mode": "chat",
    "manualOverride": null
  },
  "version": 1
}
```

---

## Integration Tests

### SSE Connection
- [ ] Connection establishes on page load
- [ ] Connection reconnects after disconnect
- [ ] Connection cleanup on page unload
- [ ] No duplicate connections

### Message Flow
- [ ] User message appears immediately (optimistic)
- [ ] Assistant message streams in real-time
- [ ] Tool calls render within messages
- [ ] Error messages display properly

### Mode Switching
- [ ] Auto mode changes layout
- [ ] Manual override persists
- [ ] Mode indicator accurate
- [ ] Side panel shows/hides correctly

### State Persistence
- [ ] Page refresh preserves state
- [ ] Different threads have separate state
- [ ] Clear history works

---

## Code Quality

### TypeScript
- [ ] All event types properly typed
- [ ] No `any` types in new code
- [ ] Hook return types explicit
- [ ] Event handlers have type guards

### Performance
- [ ] SSE connection doesn't block UI
- [ ] Message updates are debounced if needed
- [ ] No memory leaks detected
- [ ] Cleanup functions called properly

### Error Handling
- [ ] Network errors handled gracefully
- [ ] Parse errors don't crash app
- [ ] User notified of errors
- [ ] Retry logic implemented

---

## Definition of Done

- [ ] All 4 stories completed
- [ ] Manual testing passed
- [ ] TypeScript compilation succeeds
- [ ] ESLint passes
- [ ] No console errors
- [ ] State persists correctly

---

## Sprint Completion Sign-off

| Item | Status | Date | Notes |
|------|--------|------|-------|
| S63-1 Complete | ⬜ | | |
| S63-2 Complete | ⬜ | | |
| S63-3 Complete | ⬜ | | |
| S63-4 Complete | ⬜ | | |
| Integration Tested | ⬜ | | |
| Sprint Complete | ⬜ | | |

**Total Points**: 25 pts
**Completion Date**: TBD
