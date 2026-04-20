# Sprint 177 Plan — Integration Validation + E2E Benchmark + GDPR

**Phase**: 48 — Memory System Improvements
**Sprint**: 177 (final Phase 48 sprint)
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Depends on**: Sprint 170-176 (all prior Phase 48 work)

---

## Background

Phase 48's final sprint validates the full stack end-to-end and closes remaining enterprise gaps:

1. **Cross-sprint integration** — verify Sprint 170-176 features work together (tenant scope + bitemporal + active retrieval + multi-strategy + rerank all in one flow)
2. **GDPR compliance** — implement cross-layer `forget_user()` (Sprint 170 Implementation Notes MEDIUM #2)
3. **DLQ retention policy** — formalize dead-letter log lifecycle and redaction
4. **Benchmark vs V9 baseline** — document Phase 48 delivered improvements
5. **Documentation updates** — developer UI + API docs + phase closing summary

---

## User Stories

### US-1: Full Stack Works Together
- **As** a platform operator
- **I want** verification that Sprint 170-176 features compose correctly end-to-end
- **So that** Phase 48 delivers an integrated improvement, not a pile of disconnected fixes

### US-2: GDPR Right to Be Forgotten Works
- **As** a compliance officer
- **I want** `DELETE /api/v1/users/{user_id}/memory` to remove all user data across Redis, PostgreSQL, and Qdrant
- **So that** GDPR Article 17 ("right to erasure") requests can be honoured

### US-3: Dead-Letter Logs Have Retention Policy
- **As** a security engineer
- **I want** DLQ entries to auto-expire after 90 days with PII redacted after 30 days
- **So that** operational debugging window is preserved without indefinite PII storage

### US-4: Phase 48 Improvements Are Measured
- **As** a product owner
- **I want** a benchmark report comparing Phase 48 vs V9 baseline on retrieval precision, latency, and audit completeness
- **So that** ROI of 8-sprint investment is documented

---

## Technical Specifications

### 1. Cross-Sprint Integration Test Suite

**`tests/integration/memory/phase48/`** — new test package

- `test_full_stack_flow.py`:
  - Multi-tenant (org_A / org_B) setup
  - Scope-aware memory creation with event_time
  - Active retrieval with topic gen + multi-strategy + rerank
  - Verify org isolation still holds through all layers
  - Verify bitemporal query respects scope
  - Verify counter tracking + promotion trigger E2E

- `test_pipeline_step1_complete.py`:
  - Pipeline Step 1 with all features enabled
  - Measure latency breakdown: topic gen / multi-strategy / rerank / total

- `test_phase_47_regressions.py`:
  - Ensure Phase 47 execution log persistence still works
  - Ensure Agent Team orchestration unaffected

### 2. GDPR forget_user() Cross-Layer Deletion

**New endpoint**: `DELETE /api/v1/users/{user_id}/memory`
- Requires `gdpr-operator` or `admin` role
- Confirmation parameter required (`?confirm=true`)
- Returns deletion report JSON

**Backend**: `domain/auth/services/gdpr_service.py`
```python
class GDPRService:
    async def forget_user(self, user_id: str, scope: ScopeContext) -> ForgetReport:
        # 1. Validate: requester has right over this user
        # 2. Delete Redis counters: SCAN + DEL for all memory:counter:{hashed_prefix containing user}
        # 3. Delete Redis accessed_at keys (same pattern)
        # 4. Delete Redis working/session JSON entries
        # 5. Delete PostgreSQL session_memory rows WHERE user_id=...
        # 6. Delete Qdrant points WHERE payload.user_id=... (within org collection)
        # 7. Delete mem0 entries via mem0.delete_all(user_id)
        # 8. Delete user_memberships row
        # 9. Write GDPR audit log (hash-chained, separate from memory)
        # 10. Return ForgetReport {redis_keys_deleted, pg_rows, qdrant_points, mem0_entries, audit_id}
```

**GDPR Audit Log** (separate append-only table)
- `gdpr_audit_log` table: `id, operation, subject_user_id_hash, requester, timestamp, payload_hash, prev_hash` (hash chain for tamper evidence)
- NOT deleted by forget_user (required for compliance record)

### 3. DLQ Retention Policy

**Background task**: `memory_dlq_maintenance()`
- Every 1 hour:
  - Entries > 30 days old: redact PII fields (`user_id` → hash, `content` → hash)
  - Entries > 90 days old: delete entirely
- Implemented as structured log rotation (if file-based) or Redis key TTL policy

**Config**:
- `DLQ_REDACTION_AFTER_DAYS: int = 30`
- `DLQ_DELETION_AFTER_DAYS: int = 90`

### 4. Phase 48 Benchmark Report

**Script**: `scripts/benchmark_phase48_vs_v9.py`
- Measures:
  - Retrieval Precision@5 (vs V9 baseline via LongMemEval subset)
  - Memory Read latency P50/P95/P99 (Step 1)
  - Consolidation run duration + phases completed
  - Cross-tenant isolation correctness (100% pass required)
  - Bitemporal query correctness
  - DLQ event rate during load

**Output**: `claudedocs/5-status/phase-48-final-benchmark.md` (narrative) + `phase-48-metrics.json` (raw data)

### 5. Documentation Updates

- **API Docs**: `docs/api/memory-api.md` — document new endpoints and scope requirements
- **Developer UI**: `frontend/src/pages/DevUI/MemoryExplorer.tsx` — add scope context display, bitemporal as-of picker, topic gen visibility toggle
- **Phase 48 Closing Summary**: `docs/03-implementation/sprint-execution/phase-48-summary.md` — covers all 8 sprints with outcomes and deferred items
- **V9 → V10 readiness notes**: document changes for future V10 codebase analysis refresh

---

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `backend/src/domain/auth/services/gdpr_service.py` | Create | Cross-layer forget_user |
| `backend/src/api/v1/users/gdpr_routes.py` | Create | DELETE endpoint |
| `backend/src/domain/auth/models/gdpr_audit_log.py` | Create | Audit log ORM |
| `backend/alembic/versions/XXX_add_gdpr_audit_log.py` | Create | Migration |
| `backend/src/infrastructure/messaging/dlq_maintenance.py` | Create | Retention task |
| `backend/src/core/settings.py` | Modify | DLQ retention config |
| `backend/scripts/benchmark_phase48_vs_v9.py` | Create | Final benchmark |
| `backend/tests/integration/memory/phase48/test_full_stack_flow.py` | Create | Cross-sprint E2E |
| `backend/tests/integration/memory/phase48/test_pipeline_step1_complete.py` | Create | Step 1 full path |
| `backend/tests/integration/memory/phase48/test_phase_47_regressions.py` | Create | Regression |
| `backend/tests/integration/security/test_gdpr_forget_user.py` | Create | GDPR E2E |
| `backend/tests/integration/security/test_dlq_retention.py` | Create | DLQ retention test |
| `docs/api/memory-api.md` | Create/Update | Public API reference |
| `frontend/src/pages/DevUI/MemoryExplorer.tsx` | Modify | Admin UI features |
| `docs/03-implementation/sprint-execution/phase-48-summary.md` | Create | Closing summary |
| `claudedocs/5-status/phase-48-final-benchmark.md` | Create | Benchmark narrative |

---

## Acceptance Criteria

- [ ] **AC-1**: Full-stack test passes with tenant + bitemporal + active retrieval + multi-strategy + rerank all enabled
- [ ] **AC-2**: Phase 47 regression tests pass (no break to execution log persistence)
- [ ] **AC-3**: `DELETE /api/v1/users/{user_id}/memory?confirm=true` deletes across all 4 layers (Redis / PG / Qdrant / mem0) and returns report
- [ ] **AC-4**: GDPR audit log row created with hash chain (verifiable — chain validates on 100 sequential operations)
- [ ] **AC-5**: `forget_user` requires `gdpr-operator` or `admin` role; 403 otherwise
- [ ] **AC-6**: DLQ entries > 30 days: `user_id` + `content` fields redacted to SHA-256 hashes (PII gone, debugging context preserved)
- [ ] **AC-7**: DLQ entries > 90 days: deleted entirely
- [ ] **AC-8**: Benchmark script runs against V9 baseline vs Phase 48 current; produces comparison metrics
- [ ] **AC-9**: Precision@5 delivered improvement ≥ 15% vs V9 baseline (documented in benchmark narrative)
- [ ] **AC-10**: Cross-tenant isolation 100% pass (zero leak in 1000-query test)
- [ ] **AC-11**: API docs updated with scope requirements and new endpoints
- [ ] **AC-12**: Developer UI MemoryExplorer shows scope + as-of + topic gen visibility
- [ ] **AC-13**: `phase-48-summary.md` lists all 8 sprints with outcomes, deferred items, and V10 readiness notes

---

## Out of Scope

- Migrate InMemoryCheckpointStorage / InMemoryApprovalStorage (V9 P0 — dedicated infrastructure phase)
- Graphiti / Neo4j integration (evaluated, too large for Phase 48)
- A-MEM full memory evolution (long-term)
- Procedural memory schema (future phase)
- V10 codebase analysis (separate activity after Phase 48 closes)

---

## Phase 48 Closing Checklist (beyond this sprint)

After Sprint 177 completes:
- [ ] Merge `research/memory-system-enterprise` → `main` via PR with Phase 48 summary
- [ ] Tag release `phase-48-memory-improvements`
- [ ] Update project CLAUDE.md status to "Phase 48 Completed"
- [ ] Propose V10 codebase analysis refresh (V9 is 2026-03-31, Phase 48 closes at approx 2026-06)
- [ ] Propagate Phase 48 learnings to memory system research Doc for future architects
