# features/orchestrator-loop

UI components for **Category 1 (Orchestrator Loop)** events.

**Backend pair**: `backend/src/agent_harness/orchestrator_loop/`
**First impl**: Phase 50.2 (chat-v2 page consumes these)

## Components (planned)

- `<LoopEventStream>` — SSE consumer + auto-scroll log
- `<TurnCard>` — collapsible per-turn UI
- `<StopReasonBadge>` — visual indicator (END_TURN / TOOL_USE / MAX_TOKENS / SAFETY_REFUSAL)
- `useLoopEvents()` hook — Zustand-backed SSE subscription
