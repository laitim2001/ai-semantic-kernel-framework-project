# CHANGE-044: Memory ops-history backend (memory_ops table + user/tenant emit + GET /memory/ops)

**Change Date**: 2026-06-04
**Change Type**: New Feature (backend persistence + read endpoint)
**Sprint**: 57.76
**Scope**: Cat 3 (Memory) persistence + api/v1/memory (read endpoint) + Infrastructure (migration)
**Status**: ✅ Completed (push/PR user-gated)

## Change Summary
Closes the **backend half** of `AD-Memory-OpsHistory-Backend` (Area-A program remaining item). Adds a dedicated append-only `memory_ops` table (Option B, chosen by user over Option A audit_log), emits a `memory_ops` row on user/tenant memory write/evict (with value snapshot), and exposes a tenant-scoped paginated `GET /memory/ops`. The frontend wiring (RecentMemoryOpsCard + TimeTravelScrubber + remove fixtures + e2e) is **Sprint 57.77** (backend-then-FE split, mirrors 57.70→57.71).

## Change Reason
Sprint 57.75 delivered a **live-session SSE** Memory tab (`MemoryAccessed`, not persisted). The memory page's `RecentMemoryOpsCard` + `TimeTravelScrubber` (on fixtures since 57.73) need **persisted** ops-history. Memory layers had zero persistence of ops (plain INSERT, no audit, no version log — confirmed Day-0). Option B (dedicated table + value-snapshot) supports the TimeTravel value reconstruction the fixtures imply.

## Detailed Changes
**Backend**:
- `infrastructure/db/models/memory.py` — NEW `MemoryOp(Base, TenantScopedMixin)`: id BigInteger PK / user_id NULL / scope / operation NOT NULL / key/time_scale/value_snapshot/actor NULL / created_at; index `idx_memory_ops_tenant_created(tenant_id, created_at DESC)`; append-only, no hash-chain (ops log, not tamper-evident audit). Registered in `models/__init__.py`.
- `infrastructure/db/migrations/versions/0024_memory_ops.py` — NEW; `down_revision="0023_agent_catalog"`; create table + index; RLS **verbatim-mirrors 0023** (ENABLE + FORCE + `tenant_isolation_memory_ops` USING + `tenant_insert_memory_ops` WITH CHECK); downgrade drops 2 policies + index + table; no seed.
- `agent_harness/memory/_ops_recorder.py` — NEW `_record_memory_op(session, *, ...)`: `session.add(MemoryOp)` into the LAYER's session only — **no new session, no commit** (Risk Class C: same txn as the underlying write/evict).
- `agent_harness/memory/layers/{user,tenant}_layer.py` — write emit (operation=WRITE, value_snapshot=content) before `session.commit()`; evict **SELECT-before-DELETE** (capture old content → emit operation=EVICT → DELETE; absent row → no op row, no fabrication).
- `agent_harness/memory/layers/role_layer.py` — documented NO emit (write/evict raise NotImplementedError — admin-managed; emitting would be unreachable dead code = AP-4).
- `api/v1/memory.py` — NEW `GET /memory/ops?limit=&before=` → `MemoryOpsResponse{ops:[MemoryOpItem], next_cursor}`; deps trio mirror `/matrix` (get_current_tenant + require_audit_role + get_db_session_with_tenant); explicit tenant_id filter (defense-in-depth on RLS); created_at DESC; cursor pagination (created_at_ms).

## Modified Files List
- `infrastructure/db/models/memory.py` + `models/__init__.py`; `migrations/versions/0024_memory_ops.py` (NEW); `agent_harness/memory/_ops_recorder.py` (NEW); `agent_harness/memory/layers/{user,tenant,role}_layer.py`; `api/v1/memory.py`
- Tests: `test_ops_emit.py` (NEW, 8), `test_memory_ops_rls.py` (NEW, 3 incl. Risk-C rollback), `test_memory_ops_endpoint.py` (NEW, 5); `test_user_layer.py` + `test_tenant_layer.py` (adjusted for dual-add; evict strengthened)

## Verification (parent-run, Before-Commit item 7)
- `mypy src/` 0/331; `pytest` 2105 passed, 4 skipped, 0 failed; `scripts/lint/run_all.py` 10/10 (check_rls_policies + check_llm_sdk_leak green); black 612 / isort / flake8 clean; Alembic round-trip clean (upgrade佐证 by RLS pytest passing against alembic-upgraded test DB).
- Parent read all changed code: emit same-txn (Risk C); SELECT-before-DELETE; 0024 RLS verbatim mirror; endpoint deps+tenant filter+cursor; role drift correct (raise→no emit, researcher misreport corrected); RLS/Risk-C tests rigorous (real PG, non-BYPASSRLS role); existing tests not weakened.

## Impact
Backend only; memory persistence + read endpoint. New `memory_ops` table + Alembic 0024 (migration required, per Option B). No frontend this sprint (57.77). No LLM call. **Drift**: role/system layers raise (admin-managed/read-only) → emit only user+tenant 2 live DB paths; session layer in-memory volatile → not emitted. READ-path ops not emitted (write/evict only — bounds row volume). Full point-in-time state reconstruction deferred (this sprint = time-ordered ops log, sufficient for RecentOps + TimeTravel marks). Frontend half + these deeper options remain carryover.
