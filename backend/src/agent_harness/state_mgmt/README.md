# Category 7 — State Management

**ABCs**: `Checkpointer`, `Reducer` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 7
**Implementation Phase**: 53.1
**V1 Alignment**: 30% → V2 target 70%+

## Transient vs Durable split

- **TransientState**: messages buffer, pending tool_calls — recreatable
- **DurableState**: pending approvals, summary, tenant context — DB-persisted

## Reducer is sole mutator

All categories produce updates → Reducer merges with monotonic version.
This prevents `LoopState` mutation races between categories.

## Time-travel

`Checkpointer.time_travel(target_version)` lets us reload any past state.
Used for HITL resume, error recovery, debugging, replay.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 53.1   | Checkpointer + Reducer + DB schema + transient/durable split |
