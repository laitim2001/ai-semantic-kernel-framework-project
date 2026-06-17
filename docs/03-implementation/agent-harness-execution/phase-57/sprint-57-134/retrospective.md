# Sprint 57.134 Retrospective — per-tenant transcript retention (apply + preview)

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-134-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-134-checklist.md) · [Progress](./progress.md) · CHANGE-101 · design note 39

## Q1 — What shipped?
First transcript-retention enforcement: a manual admin **apply** (delete `messages` + `message_events` older than the tenant's window) + a dry-run **preview**, built on the EXISTING canonical `tenants.retention_days` column. Backend-only, NO migration. `apply_transcript_retention(db, tenant_id, retention_days, *, now, dry_run)` + POST `/apply` + GET `/preview`. +10 tests (3 unit + 7 integration incl. multi-tenant isolation + audit). Drive-through PASS (preview on acme-prod non-destructive + apply on a throwaway tenant destructive, real server + auth + DB). Design note 39 (new domain).

## Q2 — Estimate accuracy / calibration
- NEW scope class **`transcript-retention-apply-spike` 0.60** (1st data point) — new-domain backend spike (a bounded DELETE-by-age on partitioned RLS tables + apply/preview endpoints), kin to `config-tiering-model-policy-spike` 0.60 but the config half was REMOVED by the pivot.
- Bottom-up ~8.3 hr (plan estimate, with the parallel config) → committed ~5.0 hr (mult 0.60), parent-direct (agent_factor 1.0).
- Actual ~5-5.5 hr → ratio **~1.0-1.1 IN band**. The pivot REMOVED the config half (~policy/resolver/cache, ~2 hr saved) but ADDED the discovery + rework (write-then-drop `retention_policy.py`) + the dry-run preview + the 2-leg drive-through (seed script + cleanup). Net ≈ on-budget. KEEP 0.60 pending 2-3 sprint validation.

## Q3 — What went well?
- The pivot was caught **during Day-1** (not at PR / not post-merge): reading `identity.py` for the User-seed fields surfaced `Tenant.retention_days` — a serendipitous catch that prevented shipping an AP-6 parallel config. Surfaced to the user with options; the user chose pivot + preview.
- The drive-through fully drove BOTH paths on the real server: preview (non-destructive, on real acme-prod data) + apply (destructive, on a throwaway tenant with backdated rows) — the throwaway-tenant pattern solved the "time-based retention is hard to drive-through" problem without destroying real dev transcripts.
- The integration test seeds real backdated rows on the real PostgreSQL DB → the deletion + isolation + audit are genuinely proven, not mocked.
- RLS handled correctly for the cross-tenant admin DELETE (SET LOCAL app.tenant_id + explicit WHERE; safe whether RLS is FORCE'd or owner-bypassed).

## Q4 — What was hard / what to improve?
- **The pivot is an AD-Plan content-verify miss**: Day-0 D-meta-data-key grepped the `transcript_retention` KEY (free) but NOT for an existing `retention_days` COLUMN serving the same concept. **Lesson** (→ a candidate rule): when planning a NEW per-tenant config, Day-0 must grep the CONCEPT (e.g. `retention`), not just the proposed storage key — an existing canonical column/field for the same concept is the AP-6 trap. (Mirrors the Sprint 57.55/56/57 `AD-Day0-Prong2-WriteSide-Resource-Storage-Grep` family — grep the resource, not just the key.)
- Writing `retention_policy.py` then dropping it was ~30-40 min of throwaway work the Day-0 grep would have prevented.
- The preview on real acme-prod returned 0 (no real old transcripts) — a correct-but-unconvincing result; the throwaway-tenant apply leg was needed to show a non-zero. Noted: time-based features need either backdated seeding or a throwaway entity to drive-through a non-zero.

## Q5 — Anti-pattern self-check
- AP-2 (no orphan): apply/preview reachable from the live admin API; drive-through proves the real server reaches the DB. ✅
- AP-3 (no scatter): all in `platform_layer/transcripts/` + the `tenants.py` admin block + 2 test files. ✅
- AP-4 (no Potemkin): real deletion proven (integration + drive-through); preview returns real counts. ✅
- **AP-6 (no parallel config): the pivot's whole point** — dropped the parallel `meta_data` config, reused the canonical `tenants.retention_days`. ✅
- AP-8 (PromptBuilder): N/A. AP-11 (no version suffix): none. ✅
- v2 lints 10/10 (incl. check_rls_policies + check_cross_category_import + check_llm_sdk_leak).

## Q6 — Drive-through honesty (約束)
Full drive-through PASS on the real running server (PID 55768) + real admin auth + real PostgreSQL: preview (non-destructive, acme-prod) + apply (destructive primary path, throwaway tenant, deleted 1/1, recent survived). NOT gate-only. Evidence: `artifacts/drivethrough-results.md` + `seed_drivethrough.py` + progress.md Day 3.

## Q7 — Carryover
- **NEW (follow-on)**: scheduled background retention job (mirror the billing-outbox drainer) — the natural next slice now that deletion is proven.
- **NEW (follow-on)**: partition lifecycle (pg_partman activation + default partition) — adjacent gap; post-2026-06 writes + partition-drop (Option D / Ops).
- **NEW (follow-on)**: FE Tenant Settings retention tab (surface retention_days + preview/apply buttons).
- **NEW (candidate rule)**: Day-0 Prong-2 — grep the CONCEPT not just the proposed storage key when adding a per-tenant config (the AP-6 parallel-config trap; this sprint's pivot evidence).
- Pre-existing: `AD-Billing-Outbox-Drain-Test-Flake` (Risk Class C, did NOT surface).

## Design Note Extract
design note 39 (`docs/03-implementation/agent-harness-planning/39-transcript-retention.md`) — new domain (data lifecycle). 8-point gate self-checked: section→story ✅ / file:line ✅ / decision matrix ✅ / verification command ✅ / test fixtures ✅ / verified-vs-deferred fenced ✅ / rollback ✅ / 17.md cross-ref (no new contract — noted) ✅. Estimated verified ratio ~95%.
