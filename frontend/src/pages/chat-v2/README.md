# pages/chat-v2

V2 main chat flow — `/chat-v2` route.

**Implementation Phase**: 50.2
**Backend pair**: `backend/src/api/v1/chat/`

## Phase 50.2 deliverables

- Wire `POST /api/v1/chat/sessions` (create) + SSE `GET /sessions/{id}/events`
- Render `LoopEvent` stream (Thinking / ToolCallRequested / ToolCallExecuted / etc.)
- Submit user messages via `POST /sessions/{id}/messages`
- HITL pause/resume support via `POST /sessions/{id}/resume`

## Sprint 49.1 status

Placeholder only — `index.tsx` shows "Coming in Phase 50.2" message.
