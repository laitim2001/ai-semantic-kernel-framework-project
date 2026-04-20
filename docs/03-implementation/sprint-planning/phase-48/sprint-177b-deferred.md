# Sprint 177b — DEFERRED TO PHASE 49

**Status**: **DEFERRED**
**Original parent**: Sprint 177 (Phase 48 final sprint)
**Reason for deferral**: Batch 4 agent team review (2026-04-20) judged original Sprint 177 as RED due to 3 CRITICAL GDPR/compliance blockers. Scope split into:
- Sprint 177a — compliance critical (retained in Phase 48)
- Sprint 177b — UX / documentation / benchmark (THIS DOC, deferred)

**Deferral Target**: **Phase 49**, paired with V10 codebase analysis refresh

---

## Sprint 177b Scope (when resumed in Phase 49)

### Frontend DevUI MemoryExplorer

- Scope context display (show current org/workspace/user)
- Bitemporal as-of date picker
- Topic generation visibility toggle
- GDPR audit log query UI (for auditor role)
- Forgotten users tombstone viewer (admin only)

### V9 Baseline Benchmark

- Prereq script: `scripts/capture_v9_baseline.py` — runs against main branch at Phase 47 merge point to establish concrete runtime baseline (V9 analysis doc is qualitative, not runtime)
- `scripts/benchmark_phase48_vs_v9.py` — compares Phase 48 final state against captured V9 baseline
- Metrics: Precision@5, Step 1 latency P50/P95/P99, consolidation run duration, cross-tenant isolation correctness, DLQ event rate under load

### Documentation

- `docs/03-implementation/sprint-execution/phase-48-summary.md` — covers all 8 sprints (170, 171, 172, 173, 174, 175, 176, 177a) with outcomes and deferred items
- V9 → V10 readiness notes
- DPIA (Data Protection Impact Assessment) draft — references Sprint 177a GDPR implementation
- API docs: `docs/api/memory-api.md` with scope/as-of/gdpr endpoints
- Updated V9 `06-cross-cutting/memory-architecture.md` reflecting Phase 48 changes

### Phase 48 Close Tasks

- Merge `research/memory-system-enterprise` → `main` via PR
- Tag `phase-48-memory-improvements`
- Update project CLAUDE.md status to "Phase 48 Completed"
- Update Phase 48 README all sprints → Completed status

---

## Why Paired with V10?

V9 was frozen at 2026-03-31 (Phase 1-44 baseline). Phase 48 adds significant changes:
- New modules (`forgotten_users`, `gdpr_audit_log`, `scope`, `active_retrieval/*`)
- Schema changes (`session_memory` scope + bitemporal columns)
- New patterns (cross-layer saga, HMAC-KMS audit chain)
- New dependencies (Cohere, KMS)

V10 codebase refresh captures these foundationally; V9 baseline benchmark captures runtime deltas. Doing both together ensures consistent snapshot.

---

## Phase 49 Readiness Gate

Before Phase 49 begins:
- [ ] Sprint 177a complete + all compliance tests passing
- [ ] Phase 48 exit gate signed off (backend + sec + compliance)
- [ ] Sprint 177a merged into `research/memory-system-enterprise` branch
- [ ] V10 codebase refresh scope agreed (which phases to cover?)
- [ ] DPIA review scheduled with legal/compliance

---

## Estimated Effort When Resumed

- Sprint 177b in Phase 49: ~1-2 sprints (5-8 pts)
- V10 codebase refresh: ~1 phase-level activity (separate from Sprint 177b but paired scheduling)

Original Sprint 177 was 5 pts; after split:
- Sprint 177a: ~8 pts (increased due to saga + HMAC + Merkle complexity)
- Sprint 177b: ~5 pts
