# Sprint 56.1 Day 4 — RLS Coverage Audit

**Date**: 2026-05-06
**Sprint**: 56.1 / Day 4 / US-5 RLS Hardening
**Tool**: `scripts/lint/check_rls_policies.py` (8th V2 lint)

---

## Executive Summary

**0 RLS gaps**. All 14 `TenantScopedMixin` tables in `backend/src/infrastructure/db/models/` have Row-Level Security enabled + a per-tenant isolation policy installed via Alembic migration. Phase 56.1 added 2 new tables (`tenants`, `feature_flags`) — both are correctly excluded as registry tables (no `tenant_id` column), documented inline in their migrations.

The new 8th V2 lint `check_rls_policies.py` is the **continuous-enforcement gate** that prevents future regressions. Future PRs that add a `class X(Base, TenantScopedMixin)` without a corresponding `ALTER TABLE X ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation_X` Alembic migration will fail CI.

---

## Audit Methodology

`check_rls_policies.py` walks `backend/src/infrastructure/db/models/` for every `class X(Base, TenantScopedMixin)` declaration and extracts the `__tablename__`. It then walks `backend/src/infrastructure/db/migrations/versions/` for matching `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY ... ON <t>` clauses (or membership in `0009_rls_policies.py:RLS_TABLES` bootstrap tuple). A table is RLS-protected only when **both** ENABLE and POLICY appear.

Tables explicitly NOT under RLS (registry / global / chain-resolved junction) are whitelisted. The whitelist is small + documented inline in the lint file.

---

## RLS-Protected Tables (15)

| # | Table | Source | Migration |
|---|-------|--------|-----------|
| 1 | `users` | identity.py | 0009_rls_policies |
| 2 | `roles` | identity.py | 0009_rls_policies |
| 3 | `sessions` | sessions.py | 0009_rls_policies |
| 4 | `messages` | sessions.py | 0009_rls_policies |
| 5 | `message_events` | sessions.py | 0009_rls_policies |
| 6 | `tool_calls` | tools.py | 0009_rls_policies |
| 7 | `state_snapshots` | state.py | 0009_rls_policies |
| 8 | `loop_states` | state.py | 0009_rls_policies |
| 9 | `api_keys` | api_keys.py | 0009_rls_policies |
| 10 | `rate_limits` | api_keys.py | 0009_rls_policies |
| 11 | `audit_log` | audit.py | 0009_rls_policies |
| 12 | `memory_tenant` | memory.py | 0009_rls_policies |
| 13 | `memory_user` | memory.py | 0009_rls_policies |
| 14 | `incidents` | business/incident.py | 0012_incidents |
| 15 | `hitl_policies` | platform_layer/governance | 0013_hitl_policies |

---

## TenantScopedMixin Coverage

All 14 detected `TenantScopedMixin` tables are in the RLS-protected set above:

```
ApiKey, RateLimit, AuditLog, Incident, User, Role,
MemoryTenant, MemoryUser, Session, Message, MessageEvent,
StateSnapshot, LoopState, ToolCall
```

Note: `hitl_policies` does NOT use the `TenantScopedMixin` mixin (per 53.4 design — direct `tenant_id Mapped[PyUUID]` column with explicit `UNIQUE(tenant_id)` constraint), but it has full RLS via 0013.

---

## Whitelisted (Registry / Junction / Chain — 13)

These tables intentionally do NOT carry `tenant_id` and are NOT under RLS. Tenant scope is resolved via FK chain (per 09-db-schema-design.md L18-19) or the table is a global registry.

| Table | Reason | Whitelist Source |
|-------|--------|------------------|
| `tenants` | Registry root (Phase 56.1 Day 1) | 0014 migration header |
| `feature_flags` | Global registry; per-tenant overrides in JSONB (Phase 56.1 Day 3) | 0015 migration header + Day 3 D25 |
| `tools_registry` | Global tool metadata (shared across tenants) | tools.py L12 docstring |
| `tool_results` | Chain via tool_call_id → tool_calls.tenant_id | tools.py L14 docstring |
| `memory_system` | Layer 1: global system rules | memory.py L13 docstring |
| `memory_role` | Junction; chain via role_id | memory.py L161 |
| `memory_session_summary` | Junction; chain via session_id | memory.py L271 |
| `approvals` | Chain via session_id → sessions.tenant_id | governance.py L18-19 |
| `risk_assessments` | Chain via session_id | governance.py L18-19 |
| `guardrail_events` | Chain via session_id | governance.py L18-19 |
| `user_roles` | Junction (user × role) | identity.py:UserRole |
| `role_permissions` | Junction (role × permission) | identity.py:RolePermission |
| `alembic_version` | Alembic bookkeeping | tool-managed |

---

## D28 Drift Finding (Day 4)

Plan §4.3 anticipated an "Alembic RLS gap fix" migration. Day 4 audit reveals **0 gaps** — Sprint 56.1 did not add any new `TenantScopedMixin` tables (the 2 Phase 56.1 tables are registry/config tables correctly excluded). Therefore **no Alembic gap-fix migration is required**.

The deliverable for §4.3 is instead this audit report + the new 8th V2 lint that codifies the invariant going forward. Plan checklist item 4.3 marked complete with documentation evidence; future regressions caught at lint time, not at audit time.

---

## Lint Output

```
$ python scripts/lint/check_rls_policies.py
check_rls_policies: 14 TenantScopedMixin tables
check_rls_policies: 15 RLS-protected tables
check_rls_policies: 13 whitelisted (registry/junction)
OK: all TenantScopedMixin tables have RLS coverage.
```

Exit code: 0.

---

## Followups

- **Phase 56.x**: When `pg_partman` (0010) creates new partitions for `messages` + `audit_log`, ensure RLS enabled state propagates per 0010 partition policy logic. The 8th lint catches missing RLS on the parent table; partition-level inheritance is a Postgres-default behavior verified at table creation time but not by this lint.
- **Phase 56.x**: If Stage 2 commercial SaaS adds `subscriptions` / `billing_invoices` / `usage_meters` tables with `tenant_id`, the lint will require new Alembic RLS migrations.

---

## Related

- `scripts/lint/check_rls_policies.py` — the lint
- `scripts/lint/run_all.py` — orchestrator (now 8 lints)
- `0009_rls_policies.py` — bootstrap RLS_TABLES tuple
- `0012_incidents.py` / `0013_hitl_policies.py` — per-table RLS pattern
- `09-db-schema-design.md` §RLS Policies
- `.claude/rules/multi-tenant-data.md` §Rule 3
