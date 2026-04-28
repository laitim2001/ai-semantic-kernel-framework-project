# api/v1/chat — V2 main flow

**Implementation Phase**: 50.2 (wires `AgentLoop.run()` over SSE to chat-v2 page)

## Endpoints (planned)

- `POST /api/v1/chat/sessions` — create session
- `GET /api/v1/chat/sessions/{id}/events` — SSE stream of `LoopEvent`
- `POST /api/v1/chat/sessions/{id}/messages` — submit user message
- `POST /api/v1/chat/sessions/{id}/resume` — resume after HITL approval

## Critical constraints (mainflow validation)

Per V2 約束 2 (Mainflow Validation): every feature must be reachable
from this endpoint chain. NO Potemkin features. Sprint 50.2 wires the
first end-to-end TAO loop here.
