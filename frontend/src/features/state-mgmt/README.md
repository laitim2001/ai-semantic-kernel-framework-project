# features/state-mgmt

UI components for **Category 7 (State Management)** — state timeline + time-travel.

**Backend pair**: `backend/src/agent_harness/state_mgmt/`
**First impl**: Phase 53.1

## Components (planned)

- `<StateTimeline>` — chronological view of `StateVersion` (transient + durable split)
- `<TimeTravelControl>` — reload state at past version (debugging / replay)
- `<DurableStateInspector>` — view pending_approval_ids, conversation_summary, metadata
