# Category 7 — State Management

**ABCs**: `Checkpointer`, `Reducer` (in `_abc.py`)
**Implementations**: `DBCheckpointer` (`checkpointer.py`), `DefaultReducer` (`reducer.py`)
**Spec**: `01-eleven-categories-spec.md` §范疇 7
**Reuses**: Sprint 49.2 infrastructure (state_snapshots ORM + append_snapshot helper + 0004_state migration)

## Status

| Sprint | Delivery |
|--------|----------|
| 49.1 | ABCs (Checkpointer + Reducer) — stub |
| 49.2 | DB schema (`state_snapshots` + `loop_states`), append-only trigger, ORM model, `append_snapshot` helper, `compute_state_hash` |
| **53.1** | **DefaultReducer + DBCheckpointer concrete impl** — wire to AgentLoop in 53.x US-4 |

## Reducer is sole mutator

`DefaultReducer` is the **only mutation point** for `LoopState`. All other categories submit dict updates via `Reducer.merge(state, update, source_category=...)`; Reducer rebuilds frozen `StateVersion` (parent_version preserved) and returns a NEW `LoopState`.

`asyncio.Lock` serializes merges so version sequence has no holes under concurrent submissions.

Update protocol (dict-based):

```python
{
  "transient": {
    "messages_append": [...],         # additive list
    "current_turn": int,              # scalar replace
    "elapsed_ms": float,
    "token_usage_so_far": int,
    "pending_tool_calls_set": [...],  # replace
    "pending_tool_calls_clear": True, # set to []
  },
  "durable": {
    "pending_approval_ids_add": [UUID, ...],     # additive
    "pending_approval_ids_remove": [UUID, ...],  # set-removal
    "metadata_set": {"key": "value"},            # dict update (not replace)
    "conversation_summary": str,                 # scalar replace
    "last_checkpoint_version": int,
    "user_id": UUID,                             # rare; on session start
  },
}
```

`session_id` and `tenant_id` are **immutable post-creation** — no patch handlers.

## Transient vs Durable split — runtime behavior

`DBCheckpointer.save()` persists ONLY:
- All `DurableState` fields (session_id / tenant_id / user_id / pending_approval_ids / last_checkpoint_version / conversation_summary / metadata)
- `TransientState` SCALAR summary (`current_turn` / `elapsed_ms` / `token_usage_so_far`)

`DBCheckpointer.save()` does NOT persist:
- `TransientState.messages` (list of `Message` objects) — recreatable from `messages` table
- `TransientState.pending_tool_calls` — ephemeral; refilled on resume by AgentLoop

`DBCheckpointer.load(version=N)` rehydrates with empty buffers:
```python
state.transient.messages == []          # caller restores from messages history
state.transient.pending_tool_calls == []
state.transient.current_turn == <preserved>
```

DB row size constraint: < 5KB per snapshot (verified by `test_db_row_size_under_5kb`).

## Time-travel

```python
state_at_v3 = await checkpointer.time_travel(target_version=3)
```

Used for HITL pause/resume, error recovery debugging, and replay scenarios. Same query path as `load()` — semantic difference is intent.

## Bound Checkpointer pattern

`DBCheckpointer` is constructed with `(session_id, tenant_id)` binding:

```python
checkpointer = DBCheckpointer(
    db_session=async_session,
    session_id=session_uuid,
    tenant_id=tenant_uuid,
)
```

This:
- Simplifies `Checkpointer.load(version=N)` ABC (no need to pass session_id each call)
- Enforces tenant isolation (every save/load query filters by binding's tenant_id)
- Raises `StateMismatchError` if `state.durable.{session_id,tenant_id}` doesn't match the binding (caller bug guard)

## Optimistic Concurrency (StateVersion 雙因子)

Inherited from Sprint 49.2 `append_snapshot` helper: each save provides `parent_version` + `expected_parent_hash`; concurrent writers race on `UNIQUE(session_id, version)` and one gets `StateConflictError`.

For Sprint 53.1 (single-writer per AgentLoop assumption), `DBCheckpointer.save()` automatically looks up the latest snapshot to derive parent_version + parent_hash before each append.

## DB chain version vs in-memory state.version

`Reducer` bumps `state.version.version` on every merge (in-memory chain).
`Checkpointer` may NOT save every Reducer merge — only at safe points (post-LLM, post-tool, post-verify, on HITL pause). Therefore the DB chain version (set by `append_snapshot`) is independent from the in-memory chain.

After `load(version=N)`, the returned `state.version` reflects the **DB chain authoritative** values:
- `state.version.version` == DB row version (1, 2, 3, ...)
- `state.version.parent_version` == DB row parent_version
- `state.version.created_at` == DB row created_at
- `state.version.created_by_category` == DB row reason

The `version_meta` embedded in `state_data` JSONB is informational snapshot of in-memory state at save time but is NOT used during deserialization.

## Files

| File | Purpose |
|------|---------|
| `_abc.py` | Checkpointer + Reducer ABCs (Sprint 49.1) |
| `reducer.py` | DefaultReducer concrete impl (Sprint 53.1) |
| `checkpointer.py` | DBCheckpointer concrete impl (Sprint 53.1) — wraps Sprint 49.2 ORM |
| `__init__.py` | Re-exports public API |
| `README.md` | This file |

## Tests

| Path | Purpose |
|------|---------|
| `tests/unit/agent_harness/state_mgmt/test_reducer.py` | DefaultReducer unit tests (13 tests) |
| `tests/unit/agent_harness/state_mgmt/test_checkpointer_serialization.py` | Pure serialization helpers (10 tests) |
| `tests/integration/agent_harness/state_mgmt/test_checkpointer_db.py` | Real-PG round-trip / time-travel / tenant isolation (7 tests) |

Cat 7 coverage: 99% (per `code-quality.md` target ≥ 85%).

## Related

- `01-eleven-categories-spec.md` §范疇 7
- `17-cross-category-interfaces.md` §2.1 (Checkpointer + Reducer ABCs)
- `09-db-schema-design.md` Group 5 State (L508-555)
- `infrastructure/db/models/state.py` (StateSnapshot ORM + append_snapshot)
- `infrastructure/db/migrations/versions/0004_state.py`
- Sprint 53.1 plan: `docs/03-implementation/agent-harness-planning/phase-53-1-state-mgmt/sprint-53-1-plan.md`
