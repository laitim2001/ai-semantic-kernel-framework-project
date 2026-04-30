# Category 1 — Orchestrator Loop (TAO/ReAct)

**ABC**: `AgentLoop` (in `_abc.py`)
**Spec**: `docs/03-implementation/agent-harness-planning/01-eleven-categories-spec.md` §範疇 1
**Owner ABCs in 17.md**: §2.1 — `AgentLoop`
**Implementation Phase**: 50.1
**V1 Alignment**: 18% → V2 target 80%+

## Responsibility

Drives the Think-Act-Observe (TAO) loop. Composes other categories
without absorbing them. The loop continues `while True` until
`stop_reason` indicates termination (end_turn / max_turns /
budget_exhausted / tripwire / error_terminator).

## Key constraints

- **Async iterator output** (`AsyncIterator[LoopEvent]`) — never sync callbacks (17.md §4.2)
- **While-true driven** by stop_reason — NOT a for-loop pipeline (04-anti-patterns AP-1)
- **Tool results MUST flow back to LLM** via messages append, not stay inside steps
- Composes: category 4 (compactor) → 5 (prompt) → 6 (parser) → 2 (tools) → 9 (guardrail) → 10 (verifier) → 7 (checkpointer)

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 50.1   | TAO loop implementation + LoopState init + termination conditions |
| 50.2   | UnifiedChat-V2 page wires `/api/chat` to AgentLoop.run() over SSE |
| 53.x+  | HITL pause/resume integration |
