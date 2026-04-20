# Sprint 177 Checklist — Integration Validation + GDPR + Phase 48 Close

**Sprint**: 177 (Phase 48 final sprint)
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-177-plan.md](sprint-177-plan.md)

---

## Backend — GDPR forget_user Service

- [ ] `domain/auth/services/gdpr_service.py` — `GDPRService.forget_user(user_id, scope)`
- [ ] Permission check: requester has right over target user
- [ ] Redis counter keys deletion (SCAN + DEL)
- [ ] Redis accessed_at keys deletion
- [ ] Redis working/session JSON entries deletion
- [ ] PostgreSQL `session_memory` rows deleted
- [ ] Qdrant points deleted (payload filter `user_id=...` within org collection)
- [ ] mem0 entries deleted via `mem0.delete_all(user_id)`
- [ ] `user_memberships` row deleted
- [ ] GDPR audit log row written (hash-chained)
- [ ] Returns `ForgetReport` dataclass

## Backend — GDPR Audit Log

- [ ] `GDPRAuditLog` ORM model
- [ ] Alembic migration
- [ ] Columns: id, operation, subject_user_id_hash, requester, timestamp, payload_hash, prev_hash
- [ ] Append-only (no UPDATE/DELETE permitted at DB level via trigger/revoke)
- [ ] Hash chain: `prev_hash` links to previous row; validate on read

## Backend — GDPR API

- [ ] `DELETE /api/v1/users/{user_id}/memory` endpoint
- [ ] `?confirm=true` required
- [ ] RBAC: `gdpr-operator` or `admin` role
- [ ] Returns JSON report

## Backend — DLQ Retention

- [ ] `dlq_maintenance.py` background task, runs every 1 hour
- [ ] Entries > 30 days: redact `user_id` + `content` to SHA-256
- [ ] Entries > 90 days: delete
- [ ] `DLQ_REDACTION_AFTER_DAYS` + `DLQ_DELETION_AFTER_DAYS` in settings
- [ ] Metrics: `dlq_redacted_total`, `dlq_deleted_total`

## Backend — Cross-Sprint Integration Tests

- [ ] `test_full_stack_flow.py` — multi-tenant end-to-end with all features enabled
- [ ] `test_full_stack_flow.py` — scope isolation verified at each layer
- [ ] `test_full_stack_flow.py` — bitemporal query respects scope
- [ ] `test_full_stack_flow.py` — counter tracking + promotion trigger E2E
- [ ] `test_pipeline_step1_complete.py` — latency breakdown logged
- [ ] `test_phase_47_regressions.py` — execution log persistence still works
- [ ] `test_phase_47_regressions.py` — Agent Team orchestration unaffected

## Backend — GDPR & DLQ Tests

- [ ] `test_gdpr_forget_user.py` — creates data across 4 layers → forget → verify all gone
- [ ] `test_gdpr_forget_user.py` — audit log row created with correct hash chain
- [ ] `test_gdpr_forget_user.py` — permission check: non-admin 403
- [ ] `test_gdpr_forget_user.py` — report JSON accurate (counts match actual)
- [ ] `test_dlq_retention.py` — seed entries at various ages → run maintenance → verify redaction + deletion
- [ ] `test_dlq_retention.py` — redacted entries still queryable but PII gone

## Benchmark — Phase 48 vs V9

- [ ] `scripts/benchmark_phase48_vs_v9.py` script
- [ ] Precision@5 measurement (LongMemEval subset)
- [ ] Step 1 latency P50/P95/P99
- [ ] Consolidation run duration + phases
- [ ] Cross-tenant isolation (1000 queries, 0 leaks expected)
- [ ] Bitemporal correctness sample
- [ ] DLQ event rate under load
- [ ] Output: `claudedocs/5-status/phase-48-final-benchmark.md` + `.json`
- [ ] Precision@5 ≥ 15% improvement vs V9
- [ ] Cross-tenant leaks: 0

## Documentation

- [ ] `docs/api/memory-api.md` — scope-aware API reference
- [ ] `docs/api/memory-api.md` — new endpoints (as-of search, GDPR forget)
- [ ] `frontend/src/pages/DevUI/MemoryExplorer.tsx` — scope display
- [ ] `frontend/src/pages/DevUI/MemoryExplorer.tsx` — bitemporal as-of date picker
- [ ] `frontend/src/pages/DevUI/MemoryExplorer.tsx` — topic gen visibility toggle
- [ ] `docs/03-implementation/sprint-execution/phase-48-summary.md` — all 8 sprints summarized
- [ ] V10 readiness notes section in phase-48-summary
- [ ] Phase 48 README status updated: all sprints marked Completed

## Verification

- [ ] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Alembic: `upgrade head` + `downgrade -1`
- [ ] Frontend: `npm run lint && npm run build`
- [ ] `pytest backend/tests/integration/memory/phase48/ -v`
- [ ] `pytest backend/tests/integration/security/test_gdpr_forget_user.py test_dlq_retention.py -v`
- [ ] Full test suite: `pytest backend/tests/ -v` (no regressions)
- [ ] Manual: forget user → verify all 4 layers cleaned
- [ ] Manual: check DLQ redaction after manual TTL fast-forward
- [ ] Benchmark report committed and reviewed
- [ ] PR ready for merge to `main` with comprehensive description

## Phase 48 Close

- [ ] Merge `research/memory-system-enterprise` → `main`
- [ ] Tag `phase-48-memory-improvements`
- [ ] Update project CLAUDE.md status
- [ ] Propose V10 codebase analysis (if triggered by scope)
- [ ] Update Phase 48 README all Sprints → Completed status
