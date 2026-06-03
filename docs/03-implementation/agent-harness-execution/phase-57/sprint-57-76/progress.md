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
