# Sprint 57.76 — Checklist (Memory ops-history backend: memory_ops table + 3-layer emit + GET /memory/ops)

**Plan**: `sprint-57-76-plan.md`
**Branch**: `feature/sprint-57-76-memory-ops-history` (from `main` `245a9fed`)
**Closes**: `AD-Memory-OpsHistory-Backend` (backend half; frontend = Sprint 57.77)

---

## Day 0 — Plan-vs-Repo Verify + Branch + Decisions

### 0.1 Day-0 verify (3 researcher passes, main `245a9fed`)
- [ ] **Prong 1 (path)** — confirm: `infrastructure/db/models/memory.py`, `migrations/versions/` (0023 head), `agent_harness/memory/layers/{user,tenant,role,system,session}_layer.py`, `api/v1/chat/memory.py` (matrix endpoint), `infrastructure/db/models/base.py` (TenantScopedMixin), `infrastructure/db/models/audit.py`.
- [ ] **Prong 2 (content)** — D-DAY0-1..7 in plan §0 (no persistence confirmed; layer signatures; Risk-C session; matrix deps trio).
- [ ] **Prong 3 (schema, PRIMARY)** —
  - `ls migrations/versions/ | sort -V | tail -3` → confirm 0023 head, 0024 free
  - grep `0023` RLS 2-policy + FORCE SQL (mirror template)
  - read `TenantScopedMixin` (base.py:51-77) — tenant_id shape, no created_at
  - read `MemoryUser` cols (memory.py:203-262) + layer `write`/`evict` signatures
  - confirm `check_rls_policies.py` 2-policy requirement
- [ ] **go/no-go** — schema confirmed; no >20% drift

### 0.2 Branch + decisions
- [ ] **Branch created** `feature/sprint-57-76-memory-ops-history`
- [ ] **Decisions locked**: Memory ops-history Option B (dedicated memory_ops table); backend-only this sprint (FE → 57.77); emit user/tenant/role write/evict (system raises, session in-memory skipped); no hash-chain; agent-delegated Track A backend + parent re-verify.
- [ ] **Day-0 commit** plan + checklist + progress.md Day 0

---

## Day 1 — Schema + migration + RLS (US-1)

### 1.1 MemoryOp ORM
- [ ] **`MemoryOp(Base, TenantScopedMixin)`** in `models/memory.py`
  - cols: id BIGSERIAL PK / user_id UUID NULL / scope VARCHAR(32) / key VARCHAR(256) NULL / operation VARCHAR(16) / time_scale VARCHAR(32) NULL / value_snapshot TEXT NULL / actor VARCHAR(128) NULL / created_at TIMESTAMPTZ default now()
  - index `idx_memory_ops_tenant_created (tenant_id, created_at DESC)`; append-only, no hash-chain
  - DoD: mypy clean; file header + MHist

### 1.2 Alembic 0024 + RLS
- [ ] **`0024_memory_ops.py`** migration
  - `down_revision="0023_agent_catalog"`; create table + index
  - RLS: ENABLE + FORCE + 2 policies (tenant_isolation + tenant_insert) mirroring 0023:208-216
  - downgrade: drop policies + index + table
  - Command: alembic upgrade head then downgrade -1 (round-trip clean)
- [ ] **Day-0/1 verify** `check_rls_policies.py` green for new table

---

## Day 2 — Layer emit (US-2/US-3)

### 2.1 Shared recorder helper
- [ ] **`_record_memory_op(session, *, tenant_id, user_id, scope, key, operation, time_scale, value_snapshot, actor)`** (Cat 3, in `memory/`)
  - `session.add(MemoryOp(...))` — takes the LAYER's session (Risk C: same txn, no separate session)

### 2.2 Write emit (user/tenant/role)
- [ ] **write() emit** in `{user,tenant,role}_layer.py`
  - inside existing `async with session`, BEFORE `session.commit()`: `_record_memory_op(session, operation="WRITE", value_snapshot=content, ...)`
  - DoD: same txn (Risk C); system layer write raises → no emit

### 2.3 Evict emit (SELECT-before-DELETE)
- [ ] **evict() emit** in `{user,tenant,role}_layer.py`
  - SELECT the row being deleted → capture old `content` → `_record_memory_op(operation="EVICT", value_snapshot=old_content)` before DELETE, same txn
  - DoD: row absent → no op row (no fabrication)

---

## Day 3 — Endpoint + tests (US-4/US-6)

### 3.1 GET /memory/ops
- [ ] **`GET /memory/ops?limit=&before=`** in `api/v1/chat/memory.py`
  - `MemoryOpsResponse{ops: [MemoryOpItem{op,scope,key,time_scale,value_snapshot,actor,created_at}], next_cursor}`
  - deps trio mirror /memory/matrix (get_current_tenant + require_audit_role + get_db_session_with_tenant); explicit tenant_id filter; created_at DESC; limit default 50 max 200; cursor = last created_at

### 3.2 Tests
- [ ] **emit tests** (`test_ops_emit.py`) — write→WRITE row; evict→EVICT row (old value); system write raises→0 rows; Risk-C rollback (layer write rollback → op row rolled back)
- [ ] **RLS test** (`test_memory_ops_rls.py`) — tenant A ops invisible to B (SET app.tenant_id; mirror test_rls_policy_enforced)
- [ ] **endpoint test** (`test_memory_ops_endpoint.py`) — tenant-scoped time-ordered; pagination cursor; require_audit_role 403; cross-tenant empty
- [ ] **Parent re-verify (Before-Commit item 7)** — read emit + endpoint; mypy + pytest (subset) + run_all

---

## Day 4 — Sweep + Closeout

### 4.1 Full sweep (parent re-verify, Before-Commit item 7)
- [ ] **Backend gates** — `mypy src/` 0 + `pytest` (new + regression) + `scripts/lint/run_all.py` 10/10 (esp. check_rls_policies + check_llm_sdk_leak) + Alembic up/down round-trip
- [ ] **Read all agent-changed code** — emit in same txn (no double-commit), SELECT-before-DELETE, RLS mirror correct, no fabrication, no LLM import

### 4.2 Closeout docs
- [ ] **CHANGE-044** in `claudedocs/4-changes/feature-changes/`
- [ ] **progress.md** Day 0-4 + **retrospective.md** Q1-Q7
- [ ] **Checklist** all `[x]` (no deletion of unchecked)
- [ ] **Calibration** record (medium-backend 0.80 + agent_factor 0.45; CAVEAT 14th consecutive)
- [ ] **AD status**: `AD-Memory-OpsHistory-Backend` backend half done → frontend half = Sprint 57.77 carryover; next-phase-candidates.md
- [ ] **MEMORY subfile + pointer** + **CLAUDE.md lean**
- [ ] **Design note?** — likely NO (feature-continuation: new table reuses 0023 RLS + TenantScopedMixin + matrix-endpoint pattern, like 57.70 agent_catalog); confirm at Day 4 retro

### 4.3 Ship
- [ ] **Commit mapping** Day-0 / schema+migration / emit / endpoint+tests / closeout
- [ ] **Push + PR** (user-gated — explicit authorization required)
