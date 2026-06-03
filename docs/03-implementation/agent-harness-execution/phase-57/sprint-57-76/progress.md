# Sprint 57.76 Progress — Memory ops-history backend

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-76-plan.md`
**Checklist**: `...sprint-57-76-checklist.md`
**Branch**: `feature/sprint-57-76-memory-ops-history` (from `main` `245a9fed`)
**Closes**: `AD-Memory-OpsHistory-Backend` (backend half; frontend = Sprint 57.77)

---

## Day 0 — 2026-06-04 — Plan-vs-Repo Verify + Decisions

### Decisions (user-locked, AskUserQuestion ×2 + researcher-recommended split)
- **Which Area-A item**: Memory ops-history (over /subagents) — user choice.
- **Persistence design**: **Option B — dedicated `memory_ops` table** (append-only + value-snapshot, supports time-travel) over Option A (emit to audit_log) — user choice.
- **Split**: backend-only this sprint (table + emit + endpoint + tests); **frontend → Sprint 57.77** (hook + RecentOps + TimeTravel + e2e). Researcher-recommended; mirrors 57.70→57.71 backend-then-FE precedent; keeps both a healthy size. User informed (may override to full-chain).
- **Emit scope**: user/tenant/role layers (DB-backed write/evict). system layer write/evict raise (read-only) → no emit. session layer in-memory volatile → no emit (§9).
- **No hash-chain** (ops log, not tamper-evident audit). **Agent-delegated: yes** (Track A backend + parent re-verify).

### Day-0 verify (3 researcher passes + parent grep/read, main `245a9fed`)
- **D-DAY0-1..7** catalogued in plan §0: no persistence confirmed (plain INSERT, zero audit); layer signatures (`write(*, content, tenant_id, user_id, time_scale, confidence)→UUID`; `evict(*, entry_id, tenant_id)` hard-DELETE, old value NOT fetched); Risk-C session (each layer owns session_factory + commits independently); TenantScopedMixin (no created_at); matrix-endpoint deps trio.

### Prong 1 (path) — GREEN
All confirmed: `models/memory.py` (MemoryUser :203-262), `migrations/versions/`, `memory/layers/{user,tenant,role,system,session}_layer.py`, `api/v1/chat/memory.py` (matrix :418-501), `models/base.py` (TenantScopedMixin :51-77), `models/audit.py`.

### Prong 2 (content) — researcher-confirmed
- no append_audit anywhere in `memory/`; `system_layer` write raises `SystemReadOnlyError`; `session_layer` in-memory `self._store`; layer write/evict commit-in-own-session (Risk C).

### Prong 3 (schema, PRIMARY) — parent-verified
- **migration head = `0023_agent_catalog`** (0022 + 0023; `__init__.py` not a migration) → **`0024` free** ✅
- **0023 RLS mirror template** (verified `0023_agent_catalog.py:167-178` + downgrade :212-213): `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation_<t> USING (tenant_id = current_setting('app.tenant_id', true)::uuid)` + `CREATE POLICY tenant_insert_<t> FOR INSERT WITH CHECK (...)`; downgrade drops both policies. 0023 itself mirrors 0019's 2-policy pattern. memory_ops `0024` mirrors verbatim (`tenant_isolation_memory_ops` + `tenant_insert_memory_ops`).
- `check_rls_policies.py` requires both policies for any tenant table (confirmed by researcher).

### go/no-go = **GO** (Day 1 schema). Migration slot 0024 free; RLS template confirmed; layer signatures + Risk-C session known. No >20% scope drift.

---

## Day 1-3 — Backend memory_ops (Track A, agent-delegated code-implementer)

Single backend track (no frontend this sprint). Agent wall-clock ~13.5 min; parent Day-0 research + full re-verify.

### Implemented
- **MemoryOp ORM** (`models/memory.py` +71): `MemoryOp(Base, TenantScopedMixin)` — id BigInteger PK / user_id NULL / scope / operation NOT NULL / key/time_scale/value_snapshot/actor NULL / created_at; index `idx_memory_ops_tenant_created(tenant_id, created_at DESC)`; append-only, no hash-chain. Registered in `models/__init__.py`.
- **Alembic 0024** (`0024_memory_ops.py`): `down_revision="0023_agent_catalog"`; create table+index; RLS **verbatim-mirrors 0023** (ENABLE + FORCE + `tenant_isolation_memory_ops` USING + `tenant_insert_memory_ops` WITH CHECK, `current_setting('app.tenant_id', true)::uuid`); downgrade drops 2 policies + index + table; no seed.
- **`_record_memory_op` helper** (`memory/_ops_recorder.py` NEW): `session.add(MemoryOp)` only — takes the LAYER's session, no new session, no commit (Risk C).
- **user + tenant layer emit** (`user_layer.py` +45, `tenant_layer.py` +42): write emit before `session.commit()` (same txn); evict **SELECT-before-DELETE** (capture old content → emit EVICT → DELETE; absent row → no op, no fabrication); tenant_id filter on evict.
- **GET /memory/ops** (`api/v1/memory.py` +70): `MemoryOpsResponse{ops:[MemoryOpItem], next_cursor}`; deps trio mirror `/matrix` (get_current_tenant + require_audit_role + get_db_session_with_tenant); explicit tenant_id filter; `created_at DESC, id DESC`; cursor = created_at_ms, `before` → strictly older; limit 50/max.

### Drift findings (agent-surfaced, parent-confirmed)
- **D1 (role layer — researcher误报 corrected)**: plan §0 D-DAY0-1 (from researcher) listed user/tenant/**role** emit. Parent re-read `role_layer.py:89-111`: write/evict **raise NotImplementedError** (51.2 admin-managed; the researcher's ":76 INSERT" was actually a `read()` SELECT). Emitting after the raise = unreachable dead code (AP-4). → emit wired only in user + tenant (the 2 live DB write/evict paths); role honestly documented (role_layer.py:24-31 + MHist). Matches plan §3.3's own system-layer reasoning.
- **D2 (endpoint path)**: plan §3.4 said `api/v1/chat/memory.py`; the matrix endpoint actually lives in `api/v1/memory.py` → ops endpoint added there (sibling of /matrix). Minor; agent correct.

### Tests
- NEW `test_ops_emit.py` (8: write/evict per layer + value_snapshot + system-raise→0 rows + Risk-C). `test_memory_ops_rls.py` (3: RLS select-scoped via **non-BYPASSRLS role**, INSERT WITH CHECK reject, **Risk-C same-txn rollback** — write→2 rows→rollback→0). `test_memory_ops_endpoint.py` (5: pagination cursor + require_audit_role gate + cross-tenant).
- Updated 2 existing layer tests (`test_user_layer.py` +30, `test_tenant_layer.py` +6): pick MemoryX from dual-add `call_args_list` (was single-add); evict test **strengthened** (configure SELECT result + assert EVICT op value_snapshot). None weakened/deleted.

### Parent re-verify (Before-Commit item 7) — all gates green (parent-run)
- mypy `0/331`; pytest **2105 passed, 4 skipped, 0 failed**; `scripts/lint/run_all.py` **10/10** (check_rls_policies + check_llm_sdk_leak green); black 612 / isort / flake8 clean.
- Read all agent-changed code: emit same-txn (Risk C, _ops_recorder no new session/commit); SELECT-before-DELETE; 0024 RLS verbatim mirror; endpoint deps+tenant filter+cursor; role drift correct (raise→no emit); RLS/Risk-C tests rigorous (real PG, non-BYPASSRLS role); existing tests not weakened. Alembic round-trip clean (agent-run; upgrade佐证 by RLS pytest passing).

---
