# `tool_calls.message_id` FK Decision

**Sprint**: 49.4 Day 4.7
**Date**: 2026-04-29
**Status**: 🚧 DEFER to Phase 53.1+ (after PG 18 LTS available)
**49.3 retrospective Action item**: #4 (RESOLVED with explicit defer decision)

---

## Context

`tool_calls` table has a logical link to the `messages` table — every tool call
was emitted by some assistant message. Sprint 49.2 design intentionally omitted
the FK because:

- `messages` is **partitioned** by `created_at` (3 monthly partitions, +6 from
  pg_partman in Phase 49.4 onward)
- PostgreSQL ≤ 17 **cannot create a FK to a partitioned table** unless the FK
  references a UNIQUE / PRIMARY KEY that includes the partition key column
- That means the FK target would be `messages(id, created_at)` — a composite
  UNIQUE — and `tool_calls` would need both columns

PostgreSQL 18 (expected late 2026) is slated to support partial-partition FKs
natively, removing the composite workaround.

## Three options evaluated

### Option A — Composite FK now

```sql
ALTER TABLE messages
    ADD CONSTRAINT uq_messages_id_created UNIQUE (id, created_at);

ALTER TABLE tool_calls
    ADD COLUMN message_created_at TIMESTAMPTZ NOT NULL;

ALTER TABLE tool_calls
    ADD CONSTRAINT fk_tool_calls_message
    FOREIGN KEY (message_id, message_created_at)
    REFERENCES messages (id, message_created_at);
```

**Pros**:
- DB-enforced referential integrity NOW
- ON DELETE CASCADE works

**Cons**:
- Adds redundant `message_created_at` column to every `tool_calls` row
  (~20 bytes/row × millions of rows = real cost)
- All Cat 2 + Cat 6 code paths must populate `message_created_at` correctly;
  forgetting it = NOT NULL constraint failure
- Composite FK is awkward to model in SQLAlchemy (complex relationship config)
- Will be **redone** when PG 18 lands — wasted migration + ORM work

### Option B — App-layer integrity (current)

No FK; rely on application code (`tool_executor.py` / Cat 2 main path) to
ensure `tool_calls.message_id` always points to a valid `messages.id`.

**Pros**:
- No schema cost, no migration cost
- Forward-compatible with PG 18 partial-partition FK (just add the FK then)
- Simpler ORM models

**Cons**:
- A bug in app code could leave orphaned tool_calls rows
- No CASCADE — message deletion doesn't cascade tool_calls cleanup

### Option C — Trigger-based integrity

Plain trigger on `tool_calls` INSERT/UPDATE that verifies `message_id` exists in
some partition of `messages`.

**Pros**:
- Defense in depth without composite FK
- Simpler than option A in ORM

**Cons**:
- Trigger overhead on every insert (Cat 2 hot path)
- Extra SQL to maintain across migrations
- Still doesn't give CASCADE behavior

---

## Decision: Option B (defer FK to PG 18 / Phase 53.1+)

**Rationale**:

1. **PG 18 is on the roadmap** (late 2026 LTS). V2 production deployment
   targets ≥ Phase 55 = roughly mid-2026 → Q3 2026 → exactly when PG 18
   lands. Investing in composite FK now means **doing the work twice**
   (once in Phase 49.4, again to remove + replace with native FK in Phase 56+).

2. **App-layer integrity is sufficient for Phase 50.1 → 53.1**.
   Cat 2 (`tools/`) is the only writer to `tool_calls`. We will add an
   integration test (Phase 50.1) that asserts: "every `tool_calls.message_id`
   resolves to a real `messages.id`". This catches code bugs at PR time
   without DB cost.

3. **Cat 8 error handling already covers orphan recovery**.
   The `audit_log` hash chain + Cat 7 state checkpoint already detect
   inconsistent state. A `tool_calls` orphan would surface there.

4. **CASCADE delete is not a real requirement**.
   Production data retention rules require us to ARCHIVE messages, not delete.
   Phase 56+ retention policy will use logical archival + cold storage,
   not physical DELETE — so CASCADE is irrelevant.

## Carry-forward / re-evaluate triggers

Re-open this decision if:

| Trigger | Action |
|---------|--------|
| PostgreSQL 18 LTS released + adopted | Add native FK + drop this defer |
| Cat 2 integration test catches an orphan in CI more than once | Switch to Option C (trigger) immediately |
| Schema review in Phase 53.1 surfaces a hard requirement for CASCADE | Reconsider Option A or C |

## Action items

- [ ] **Phase 50.1**: add integration test `test_tool_calls_message_id_integrity`
      that joins `tool_calls.message_id` to `messages.id` across all partitions
      and asserts zero orphans on a populated test DB.
- [ ] **Phase 56+** (post-V2 production): track PG 18 release; when released
      and adopted, add the partial-partition FK in a clean migration.
- [x] **Sprint 49.4 closeout**: 49.3 Action item #4 RESOLVED (defer documented).

---

## Cross-references

- [`worker-queue-decision.md`](./worker-queue-decision.md) — sibling decision report
- [`09-db-schema-design.md`](../../../03-implementation/agent-harness-planning/09-db-schema-design.md) §messages partitioning
- Sprint 49.3 retrospective Action item #4
- PostgreSQL 18 release notes (when available)

---

**Sign-off**:
- [x] AI 助手 (this report)
- [ ] User review (await)
