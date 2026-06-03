# Sprint 57.76 Plan — Memory ops-history backend (memory_ops table + 3-layer emit + GET /memory/ops) (closes AD-Memory-OpsHistory-Backend backend half)

**Phase**: 57 (Frontend + SaaS Stage 1 ongoing)
**Scope class**: `medium-backend` (new table + migration + RLS + multi-layer emit + read endpoint)
**Branch**: `feature/sprint-57-76-memory-ops-history` (from `main` `245a9fed`)
**Status**: Day 0 (plan)

---

## 0. Background

`AD-Memory-OpsHistory-Backend` (Area-A program remaining item) requires **persisted** memory operation history (who/when/which scope+key did read/write/evict, with value snapshot), feeding the memory page's `RecentMemoryOpsCard` + `TimeTravelScrubber` (left on fixtures since Sprint 57.73). Sprint 57.75 delivered a **live-session SSE** Memory tab (`MemoryAccessed`, not persisted); this sprint delivers the **persisted** counterpart.

User chose **Option B (dedicated `memory_ops` table, supports value-snapshot / time-travel)** over Option A (emit to `audit_log`). **This sprint is backend-only** (table + emit + endpoint + tests); the frontend wiring (hook + 2 components + remove fixtures + e2e) is a clean follow-up Sprint 57.77 — mirrors the 57.70→57.71 backend-then-FE precedent (researcher-recommended split; keeps both sprints a healthy size).

### Day-0 ground-truth (3 researcher passes, main `245a9fed`)

- **D-DAY0-1 (no persistence — confirmed)**: memory 5 layers all `write()=plain INSERT, zero append_audit, no version log` (`user_layer.py:104-148`, `tenant_layer.py:79-136`, `role_layer.py:76`). `system_layer` write **raises `SystemReadOnlyError`** (admin-migration only); `session_layer` is **in-memory `self._store` dict** (`:142-143`, volatile). → emit applies to **user / tenant / role** (the 3 DB-backed write/evict layers).
- **D-DAY0-2 (migration head)**: latest = `0023_agent_catalog`; **next = `0024`** (`down_revision="0023_agent_catalog"`).
- **D-DAY0-3 (RLS mirror)**: `0023`:208-216 = `ENABLE` + `FORCE ROW LEVEL SECURITY` + 2 policies (`tenant_isolation_<t>` USING + `tenant_insert_<t>` FOR INSERT WITH CHECK), both `current_setting('app.tenant_id', true)::uuid`. `downgrade()` drops policies + index + table. `check_rls_policies.py` **requires both policies** for any tenant table.
- **D-DAY0-4 (layer signatures)**: `write(*, content, tenant_id, user_id, time_scale, confidence)→UUID` (value = `content` str). `evict(*, entry_id, tenant_id)` = **hard DELETE; old value NOT fetched** → must SELECT-before-DELETE to snapshot. `MemoryUser` cols (`memory.py:203-262`): tenant_id/user_id/category/content/vector_id/source/confidence/expires_at/metadata_/created_at.
- **D-DAY0-5 (Risk Class C ⚠️)**: each layer owns its `session_factory` and commits independently (`user_layer.py:134-146`). The memory_ops INSERT **must live in the same `async with session` block / same txn** (before `session.commit()`) to avoid double-commit + cross-session leaks.
- **D-DAY0-6 (TenantScopedMixin)**: `base.py:51-77` = `tenant_id` UUID NOT NULL + FK CASCADE + index; **no `created_at`** (add explicitly). `audit_log` has hash-chain; **memory_ops does NOT need a chain** (ops log, not tamper-evident audit; chain adds per-tenant serialization cost).
- **D-DAY0-7 (read endpoint precedent)**: mirror `GET /memory/matrix` (Sprint 57.73, `memory.py:418-501`) deps trio (`get_current_tenant` + `require_audit_role` + `get_db_session_with_tenant`) for `GET /memory/ops`.
- **Frontend (next sprint, informational)**: `_fixtures.ts:39-59` `RecentMemoryOp {op, scope, k, v, by, at}` + `TimeTravelMark`/`MemoryOpTimelinePoint {t, op, scope, k}`; `RecentMemoryOpsCard.tsx:43-103` 6-col table; mockup `page-governance.jsx:556-579` (verbatim CSS already ported). New `useMemoryOps` hook mirrors `useMemoryMatrix.ts`.

---

## 1. Sprint Goal

Persist memory write/evict operations (user/tenant/role layers) to a new append-only `memory_ops` table with value snapshots, and expose a tenant-scoped `GET /memory/ops` (time-ordered, paginated) — the backend half of `AD-Memory-OpsHistory-Backend`. Frontend wiring is Sprint 57.77.

---

## 2. User Stories

- **US-1** (schema): As the platform, a new append-only `memory_ops` table (tenant-scoped, RLS-enforced) records memory operations with a value snapshot.
- **US-2** (write emit): As the platform, when a user/tenant/role memory `write()` succeeds, a `memory_ops` row (operation=WRITE, scope, key, time_scale, value_snapshot=content, actor) is inserted **in the same transaction**.
- **US-3** (evict emit): As the platform, when a memory `evict()` runs, the old value is SELECT-ed before the DELETE and recorded (operation=EVICT, value_snapshot=old content) in the same transaction.
- **US-4** (read endpoint): As a memory-page operator, `GET /memory/ops` returns my tenant's recent memory ops (time-ordered DESC, paginated) so the frontend (57.77) can render RecentOps + TimeTravel.
- **US-5** (multi-tenant): As a tenant, I never see another tenant's memory ops (RLS 2-policy + FORCE + tenant_id filter; cross-tenant denial tested).
- **US-6** (tests): emit (write/evict per layer) + Risk-C session isolation + RLS enforcement + endpoint + cross-tenant denial are unit/integration-tested.

---

## 3. Technical Specifications

### 3.0 Architecture

A new Cat 3 (Memory) persistence sidecar: each DB-backed layer's write/evict additionally inserts an append-only `memory_ops` row in its own transaction (no separate session — Risk C). A tenant-scoped read endpoint mirrors the `/memory/matrix` facade. **No hash-chain** (ops log, not audit). **No LLM call** (pure DB). Frontend deferred to 57.77.

### 3.1 `memory_ops` table (US-1) — `infrastructure/db/models/memory.py`

`MemoryOp(Base, TenantScopedMixin)`:
- `id` BIGSERIAL PK
- `tenant_id` (from Mixin) + index
- `user_id` UUID NULL (set for user-layer ops)
- `scope` VARCHAR(32) NOT NULL (user / tenant / role)
- `key` VARCHAR(256) NULL (the memory key / category)
- `operation` VARCHAR(16) NOT NULL (WRITE / EVICT)
- `time_scale` VARCHAR(32) NULL
- `value_snapshot` TEXT NULL (content on WRITE; old content on EVICT)
- `actor` VARCHAR(128) NULL (user_id str / "system")
- `created_at` TIMESTAMPTZ NOT NULL default now()
- Index `idx_memory_ops_tenant_created (tenant_id, created_at DESC)` (read path is time-ordered DESC per tenant).
- Append-only (no UPDATE path). No hash-chain.

### 3.2 Migration + RLS (US-1/US-5) — Alembic `0024_memory_ops.py`

- `down_revision="0023_agent_catalog"`.
- `upgrade()`: create table + index; `ENABLE` + `FORCE ROW LEVEL SECURITY`; 2 policies mirroring `0023`:208-216 (`tenant_isolation_memory_ops` USING `tenant_id = current_setting('app.tenant_id', true)::uuid` + `tenant_insert_memory_ops` FOR INSERT WITH CHECK same).
- `downgrade()`: drop 2 policies + index + table.
- No data-seed (new empty log).

### 3.3 Layer emit (US-2/US-3) — `memory/layers/{user,tenant,role}_layer.py`

- **write emit**: inside the existing `async with session` block, **before `session.commit()`**, `session.add(MemoryOp(operation="WRITE", scope=<layer>, key=<category/key>, time_scale=..., value_snapshot=content, actor=<user_id|"system">, tenant_id=..., user_id=...))`. Same txn (Risk C).
- **evict emit**: `evict()` currently hard-DELETEs by entry_id. Add a SELECT (the row being deleted) to capture `content` → insert `MemoryOp(operation="EVICT", value_snapshot=old_content, ...)` before the DELETE, same txn. If the row doesn't exist (already gone), no op row.
- system layer: write/evict raise → no emit. session layer: in-memory volatile → **no emit this sprint** (§9).
- A shared helper `_record_memory_op(session, *, ...)` in `memory/` avoids 3× duplication (Cat 3 owned; mirrors `append_audit` ergonomics but writes MemoryOp).

### 3.4 Read endpoint (US-4) — `api/v1/chat/memory.py` (or memory router)

- `GET /memory/ops?limit=&before=` → `MemoryOpsResponse{ops: [MemoryOpItem], next_cursor}`.
- `MemoryOpItem`: `{op, scope, key, time_scale, value_snapshot, actor, created_at}` (maps to FE `RecentMemoryOp {op, scope, k, v, by, at}` in 57.77).
- Deps trio mirror `/memory/matrix`: `get_current_tenant` + `require_audit_role` + `get_db_session_with_tenant`. Explicit `tenant_id == current` filter (defense-in-depth on top of RLS). Time-ordered `created_at DESC`, `limit` default 50 / max 200, cursor = `created_at` of last row.

### 3.5 Tests (US-6)

- Emit: user/tenant/role write → 1 WRITE op row with correct value_snapshot; evict → 1 EVICT op row with old value (SELECT-before-DELETE). system write raises → 0 op rows.
- Risk C: emit shares the layer's session/txn (no double-commit; rollback of layer write rolls back the op row).
- RLS: tenant A's ops invisible to tenant B (SET app.tenant_id test, mirror `test_rls_policy_enforced`).
- Endpoint: `GET /memory/ops` returns tenant-scoped time-ordered ops; cross-tenant 404/empty; pagination cursor; `require_audit_role` 403 for non-audit role.

### 3.6 Lint / validation

- Backend: `mypy src/` 0; `pytest`; `scripts/lint/run_all.py` 10/10 (esp. `check_rls_policies` — new tenant table needs 2 policies; `check_llm_sdk_leak`).
- Alembic up/down round-trip (`0024` upgrade then downgrade clean).

---

## 4. File Change List

**Backend** (~6 files):
- `backend/src/infrastructure/db/models/memory.py` — NEW `MemoryOp` ORM (Cat 3).
- `backend/src/infrastructure/db/migrations/versions/0024_memory_ops.py` — NEW migration + RLS (build).
- `backend/src/agent_harness/memory/_ops_recorder.py` (or in an existing memory module) — NEW `_record_memory_op` helper (Cat 3).
- `backend/src/agent_harness/memory/layers/{user,tenant,role}_layer.py` — emit on write/evict (Cat 3).
- `backend/src/api/v1/chat/memory.py` — NEW `GET /memory/ops` + Pydantic models (api).

**Backend tests** (~3 files):
- `backend/tests/unit/agent_harness/memory/test_ops_emit.py` (NEW) — write/evict emit per layer + Risk-C isolation.
- `backend/tests/integration/.../test_memory_ops_rls.py` (NEW) — RLS cross-tenant denial.
- `backend/tests/integration/api/v1/chat/test_memory_ops_endpoint.py` (NEW) — endpoint + pagination + role gate.

**No frontend this sprint. No LLM call.**

---

## 5. Acceptance Criteria

- AC-1: `memory_ops` table exists with RLS 2-policy + FORCE + index; Alembic `0024` up/down clean; `check_rls_policies` green.
- AC-2: user/tenant/role write → WRITE op row (value_snapshot=content); evict → EVICT op row (value_snapshot=old content via SELECT-before-DELETE); same txn as the layer op (Risk C — rollback test).
- AC-3: system-layer write raises → no op row; session-layer not emitted (documented §9, honest gap not a Potemkin).
- AC-4: `GET /memory/ops` returns tenant-scoped, time-ordered DESC, paginated ops; cross-tenant invisible; `require_audit_role` enforced.
- AC-5: backend mypy 0; pytest green (new + regression); run_all 10/10; Alembic round-trip.
- AC-6: AP-4 (no Potemkin) — endpoint returns real persisted ops; AP-2 — emit wired into the live write/evict path (traceable from layer). LLM-neutrality green. Multi-tenant 鐵律 (tenant_id + RLS).

---

## 6. Deliverables

- [ ] `MemoryOp` ORM + `memory_ops` table
- [ ] Alembic `0024` migration + RLS 2-policy + FORCE + index
- [ ] `_record_memory_op` helper (Cat 3)
- [ ] user/tenant/role write emit (same txn)
- [ ] user/tenant/role evict emit (SELECT-before-DELETE, same txn)
- [ ] `GET /memory/ops` endpoint + Pydantic + pagination + role gate
- [ ] emit tests (write/evict/system-raise + Risk-C rollback)
- [ ] RLS cross-tenant denial test
- [ ] endpoint test (pagination + role gate + cross-tenant)
- [ ] CHANGE-044 + progress.md + retrospective.md + closeout

---

## 7. Workload Calibration

Bottom-up est: table+ORM+migration+RLS ~3 hr + 3-layer write/evict emit (incl. SELECT-before-DELETE) ~3 hr + endpoint+pagination ~2 hr + tests (emit+isolation+RLS+endpoint+cross-tenant) ~3 hr = **~11 hr**.
→ class-calibrated commit (`medium-backend` ×0.80) ~**8.8 hr**.
**Agent-delegated: yes** — single Track A backend (code-implementer) + parent re-verify (Before-Commit item 7). With `agent_factor` `mixed-multidomain-bundle-mechanical` 0.45 (multi-file backend bundle): agent-adjusted ~**4 hr**. CAVEATED per `AD-Calibration-AgentDelegated-WallClock-Measure` (14th consecutive agent-delegated). `medium-backend` 3-sprint-mean recalibration watch active.

---

## 8. Dependencies & Risks

- **R1 (Risk Class C — session/txn isolation, PRIMARY)**: emit must share the layer's existing session + commit in the same txn (D-DAY0-5). A separate service-session would double-commit + risk cross-event-loop leaks. Mitigation: `_record_memory_op(session, ...)` takes the layer's session, `session.add()` before the layer's `commit()`; rollback test proves atomicity.
- **R2 (evict snapshot)**: `evict()` hard-DELETEs without reading; must SELECT the row first to capture `value_snapshot`. Mitigation: SELECT-before-DELETE inside the same txn; if row absent, skip op row (no fabrication).
- **R3 (RLS lint)**: new tenant table needs 2 policies + FORCE or `check_rls_policies` fails. Mitigation: mirror `0023` verbatim (D-DAY0-3); Alembic round-trip + lint in Day-0 verify.
- **R4 (read-path volume)**: NOT emitting READ ops this sprint (write/evict only) — keeps row volume bounded; a future sprint may add sampled reads if the tab needs them (§9).
- **R5 (schema drift)**: Day-0 Prong 3 must confirm `0024` not occupied, TenantScopedMixin shape, MemoryUser columns (done in research; re-verify at Day-0 grep).

---

## 9. Out of Scope (this sprint; carryover)

- **Frontend wiring** (`useMemoryOps` hook + `RecentMemoryOpsCard` + `TimeTravelScrubber` real data + remove fixtures + e2e) → **Sprint 57.77** (backend-then-FE split).
- **READ-path emit** — write/evict only this sprint; sampled read ops a future option (R4).
- **session-layer ops** — in-memory volatile; persisting its ops is a separate decision (low value).
- **system-layer ops** — write/evict raise (read-only); no ops to record except admin migration.
- **Full point-in-time state reconstruction** — this sprint provides the time-ordered ops log (sufficient for RecentOps + TimeTravel timeline marks); reconstructing full memory state at an arbitrary timestamp (replaying snapshots) is a deeper future capability.
- **FE `/subagents` real list** (`AD-Subagent-RealList-Phase58`) — the other Area-A remaining item.
