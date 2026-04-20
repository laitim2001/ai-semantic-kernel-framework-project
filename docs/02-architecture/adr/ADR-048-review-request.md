# ADR-048 Review Request

**ADR**: [ADR-048: Tenant Scope for Memory System](ADR-048-tenant-scope-for-memory.md)
**Status**: DRAFT — awaiting review
**Requested by**: Phase 48 planning track
**Request date**: 2026-04-20
**Target sign-off date**: 2026-04-24 (4 business days)
**Branch**: `research/memory-system-enterprise`

---

## Why this review is urgent

**Blocking impact**: ADR-048 sign-off unblocks Sprint 173 (Tenant Scope Foundation) code phase, which in turn is a hard dependency for:

- Sprint 173 → Sprint 174 (bitemporal needs scope context)
- Sprint 173 → Sprint 175 (active retrieval topic gen needs scope for safe LLM calls)
- Sprint 173 → Sprint 176 (multi-strategy rerank)
- Sprint 173 → Sprint 177a (GDPR saga builds on scope primitives)

Without ADR approval, 4 of 8 Phase 48 sprints (roughly 32 story points) remain blocked at specification-only state.

**Non-blocking**: Sprint 170 / 171 / 172 (Wave 1 — Fix) proceed in parallel and are unaffected by this ADR.

---

## Reviewers (3 required sign-offs)

| Role | Scope of review | Sign-off |
|------|----------------|----------|
| **backend-lead** | Tenant scope data model, schema migration strategy, backward compatibility for existing `user_id`-keyed memory | [ ] |
| **sec-lead** | JWT claim structure, key rotation, cross-tenant isolation guarantees, SCAN enumeration risk mitigation | [ ] |
| **SRE-lead** | Qdrant T1/SMB tiering operational cost, migration runbook feasibility, observability/alerting plan | [ ] |

Any one REJECT blocks the ADR until rewritten.

---

## Review scope — what needs decision

### Hard decisions (ADR must specify, reviewers must agree)

1. **4-level scope hierarchy**: `org_id / workspace_id / user_id / agent_id` — all four required or some optional?
2. **JWT claim structure**: which claims carry scope, rotation cadence, validation middleware responsibility
3. **Qdrant tiering model**: T1 (dedicated collection per org) vs SMB (shared collection with payload filter) — threshold for auto-upgrade from SMB → T1
4. **Backward compatibility**: legacy memory rows without scope fields — default to `org_id = "default"` with explicit migration path or force backfill
5. **Cross-tenant read prevention**: query-layer filter vs storage-layer partition — trade-offs
6. **Redis key enumeration mitigation**: hash `user_id` in keys vs Redis ACL limiting SCAN — pick one

### Soft decisions (recommended, reviewers can suggest alternatives)

7. Scope propagation path in pipeline (Step 1 memory read / Step 8 post-process write)
8. Agent-level scope source — from Expert Registry (Phase 46) or per-invocation override
9. Observability — scope-tagged metrics naming convention

---

## Sign-off checklist (12 items)

Reviewers confirm by checking each item during review:

**Data model & schema**:
- [ ] Scope fields additions to `session_memory` + Qdrant payload are non-destructive to existing data
- [ ] Alembic migration is forward-only with tested rollback (`downgrade -1` verified in local env)
- [ ] Legacy data default (`org_id = "default"`) is acceptable and documented

**Security & isolation**:
- [ ] JWT claim schema is forwards-compatible (new fields don't invalidate existing tokens)
- [ ] Cross-tenant read path has defense in depth (query filter + storage partition for T1)
- [ ] Redis key enumeration via `SCAN` is mitigated (hash or ACL — ADR picks one and justifies)

**Operational**:
- [ ] Qdrant tiering migration runbook is clear (SMB → T1 trigger, data move steps, rollback path)
- [ ] Observability plan covers cross-tenant isolation correctness (metric + alert)
- [ ] Cost model for T1 vs SMB documented (at least order-of-magnitude estimate)

**Process**:
- [ ] No open CRITICAL-level concerns (any HIGH concerns have agreed mitigation plan)
- [ ] ADR explicitly names what is Out of Scope (avoid scope creep during S173 implementation)
- [ ] ADR references all prior research (V9 memory architecture, knowledge-base-enterprise series, MIRIX/Zep/Graphiti surveys)

---

## How to review

1. Read [ADR-048](ADR-048-tenant-scope-for-memory.md) in full (≈ 284 lines, est. 30 min)
2. Cross-reference Sprint 173 plan for downstream implications: `docs/03-implementation/sprint-planning/phase-48/sprint-173-plan.md`
3. Write review comments directly in the ADR using the format:
   ```
   <!-- REVIEW:backend-lead:2026-04-22 -->
   Concern: ...
   Suggested change: ...
   Severity: BLOCKER | HIGH | MEDIUM | LOW | NIT
   <!-- /REVIEW -->
   ```
4. Check off your sign-off row in the table above
5. Commit with message: `review(adr-048): {role} review — {verdict}` where verdict is `APPROVE` / `APPROVE-WITH-COMMENTS` / `REJECT`

---

## Feedback integration protocol

- **APPROVE** (all 3): ADR status → `Accepted`, unblock Sprint 173 code phase
- **APPROVE-WITH-COMMENTS** (any): integrate feedback into ADR v2, notify reviewer, move to accepted on silent re-confirm (48h window)
- **REJECT** (any): planning track rewrites ADR, re-submits within 3 business days with delta explanation

---

## Contact

For clarifying questions during review, tag the planning track in the ADR itself (review comments above). Async-first; synchronous meeting only if 2+ reviewers flag REJECT.

---

**Status log**:
- 2026-04-20 — Review request opened, 3 sign-offs pending
- (pending reviewer updates)
