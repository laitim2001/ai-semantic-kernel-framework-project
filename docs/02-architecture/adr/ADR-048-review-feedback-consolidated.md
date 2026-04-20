# ADR-048 Review Feedback — Consolidated (2026-04-20)

**ADR**: [ADR-048: Tenant Scope for Memory System](ADR-048-tenant-scope-for-memory.md)
**Review request**: [ADR-048-review-request.md](ADR-048-review-request.md)
**Reviewers (3)**: backend-lead, sec-lead, SRE-lead
**Overall verdict**: **REJECT** (SRE BLOCKER; Security & Backend conditional APPROVE)
**Required action**: ADR rewrite to v0.2 addressing 3 BLOCKER + 7 HIGH findings; re-review by SRE mandatory.

---

## Aggregate findings

| Severity | Count | Source |
|----------|-------|--------|
| BLOCKER | **3** | SRE (B1/B2/B3) |
| HIGH | **10** | Backend 3 + Security 3 + SRE 4 |
| MEDIUM | **7** | Backend 2 + Security 3 + SRE 3 (one overlap) |
| LOW/NIT | **4** | Backend 2 + Security 2 |

---

## BLOCKER items (must resolve for sign-off)

### B1 — "500 orgs" threshold is unsourced (SRE, ADR §4)
**Issue**: Tier decision boundary lacks empirical basis.
**Resolution for v0.2**: Mark as "estimate — to be validated in Sprint 173 perf test" and add measurement AC.

### B2 — SMB→T1 live migration has no runbook (SRE, ADR §Risks)
**Issue**: Enterprise upgrade path is undefined; first customer upgrade = unplanned outage.
**Resolution for v0.2**: Add Runbook RB-MEM-01 skeleton in a new §11 Runbooks section covering: dual-write window → verify → cutover → rollback.

### B3 — Redis SPOF for new-org signup (SRE, ADR §4)
**Issue**: `SET NX` collection-creation lock — if Redis down, signup blocks (availability) or races (correctness).
**Resolution for v0.2**: Document degraded-mode: queue org creation → retry when Redis recovers; signup returns 202 with follow-up polling.

---

## HIGH items

### H1 (Security) — `org_id="default"` confused deputy (ADR §10)
Attacker minting JWT with `org_id="default"` reads cross-tenant legacy data.
**Resolution**: Reserve `default`/`*`/empty as system-only sentinels; middleware 403 on incoming JWT using these values.

### H2 (Security) — Cross-DC revocation gap exploitable (ADR §2, Open Issue #4)
5min+ replay window unbounded in multi-region.
**Resolution**: (a) Short JWT exp ≤15min + refresh rotation; (b) `jti` deny-list in Redis with replication SLA; (c) max-tolerable window with SRE sign-off.

### H3 (Security) — HS/RS confusion mitigation incomplete (ADR §2, §8)
Key registry must reject symmetric keys + lookup before alg inspection.
**Resolution**: Document key registry returns only RSA public keys; kid→key lookup precedes alg validation; `alg` header never influences key selection.

### H4 (Backend) — Legacy backfill batch concurrency unspecified (ADR §10)
Concurrent S172 writes during backfill could race.
**Resolution**: Add §10.1 with `FOR UPDATE SKIP LOCKED` + chunk size + coordination with live writes.

### H5 (Backend) — `ScopeContext` compile-fail enforcement unverified (ADR §9)
Claim that "code doesn't compile without scope" needs mypy-strict assertion.
**Resolution**: S173 plan AC: `mypy --strict` fails if any repo method has `Optional[ScopeContext]=None`.

### H6 (Backend) — Alembic rollback untested for scope columns (ADR §10)
No explicit `downgrade -1` test with populated scope columns.
**Resolution**: S173 AC adds rollback test fixture.

### H7 (SRE) — Cross-DC pub/sub lag unbounded (Open Issue #4)
Multi-region can see 5-30s pub/sub lag, partition can exceed 5min.
**Resolution**: Either commit to single-region for v1 OR add forced-revalidation for sensitive admin ops.

### H8 (SRE) — JWT key rotation overlap undocumented (ADR §2)
Split-brain risk during 90-day key rollover.
**Resolution**: Document key overlap window (≥1h), JWK TTL, rollout procedure — add to RB-MEM-03.

### H9 (SRE) — Salt rotation blast radius (ADR §7)
"Re-key only on compromise" without procedure = ad-hoc breach response.
**Resolution**: RB-MEM-04 runbook skeleton for salt compromise response.

### H10 (SRE) — Observability gaps
4 metrics missing (scope-mismatch, T1 RAM, JWT failure rate, cache pub/sub lag).
**Resolution**: Add §12 Observability section to ADR with 6 required metrics.

---

## MEDIUM items (track but non-blocking)

### M1 (Backend) — §5 BackgroundTasks context propagation not covered
FastAPI `BackgroundTasks` may lose context.
**Track**: Add one-liner in §5; explicit `copy_context()` requirement.

### M2 (Backend) — Tier classification ownership unresolved (Open Issue #1)
Pin default = "smb"; defer tier-upgrade flow to S178.

### M3 (Security) — SHA-256[:24] side-channel note
Already covered by salt; document in §7 that salt compromise requires full re-key.

### M4 (Security) — `has_more_memberships` fallback auth path undefined
DB lookup on overflow must fail-closed on error.
**Resolution**: Add to §2: fail-closed on DB lookup error; log + alert.

### M5 (Security) — Salt rotation runbook deferred (Open Issue #2)
Overlaps with H9; resolve via RB-MEM-04.

### M6 (SRE) — Legacy `default` ops playbook missing
Accumulates silently without segregation/deletion procedure.
**Resolution**: RB-MEM-06 legacy segregation runbook.

### M7 (SRE) — Strict-mode CI check only verifies raise
Missing prod smoke test asserting strict mode active.
**Resolution**: S173 AC adds production smoke check.

---

## UNEXPECTED THREAT (Security found)

**Timing side-channel on `user_memberships` cross-check**: cache-hit vs cache-miss has measurable latency delta; attacker can enumerate active users across tenants by timing 401 responses.

**Resolution**: constant-time response path or randomized jitter on auth failures. Add to §8 JWT attack matrix as row 13.

---

## LOW / NIT items

- L1 (Security): §8 row 12 "body-injected scope override" — add schema-level prevention via Pydantic models forbidding `org_id` / `workspace_id` in request bodies.
- L2 (Security): Document 90-day RS256 rotation with ≤7-day overlap window.
- L3 (Backend): Hash length collision math (96-bit) can be shown in ADR for clarity.
- L4 (Backend): Update revision history when v0.2 lands.

---

## Required for v0.2 re-submission

1. **§4 Qdrant tiering**: mark "500 orgs" as estimate + add AC for S173 perf test
2. **§11 Runbooks (new)**: 6 skeletons (RB-MEM-01 to RB-MEM-06)
3. **§12 Observability (new)**: 6 required metrics with alert thresholds
4. **§2 JWT**: short `exp` + jti deny-list + key registry pre-alg check
5. **§10.1 Backfill concurrency**: batch + lock strategy + coordination with S172
6. **§10.2 Reserved sentinels**: reject `default`/`*`/empty in middleware
7. **§7 Salt rotation**: procedure reference RB-MEM-04
8. **§8 Attack matrix**: add timing-side-channel row + body-injection schema-level prevention
9. **Open Issues closure**:
   - #1 → pin "smb" default, defer upgrade to S178
   - #2 → RB-MEM-04
   - #3 → KMS-backed (Azure Key Vault / AWS KMS)
   - #4 → single-region v1 OR forced revalidation for admin ops (documented)
   - #5 → split membership schema to ADR-048a (not blocking S173)

---

## Sign-off after v0.2

| Role | Verdict v0.1 | Conditional for v0.2 | Final signature |
|------|-------------|---------------------|-----------------|
| Backend | APPROVE-WITH-COMMENTS | H4/H5/H6 addressed | _pending v0.2_ |
| Security | APPROVE-WITH-COMMENTS | H1/H2/H3/M4 addressed | _pending v0.2_ |
| SRE | **REJECT** | B1/B2/B3 + H7/H8/H9/H10 addressed | _pending v0.2 re-review_ |
| Compliance | N/A | GDPR coordination via §6 + Sprint 177a | _not yet requested_ |

---

## Timeline

- 2026-04-20: v0.1 submitted, review complete, REJECT on SRE lens
- 2026-04-20 (same day): v0.2 rewrite integrating B1-B3 + 10 HIGHs
- 2026-04-20: re-submit v0.2 for SRE re-review (conditional re-approval)
- 2026-04-21+: S173 code phase unblocked

---

**Feedback compiled by**: ADR review coordinator
**Storage**: Git-tracked in ADR directory for audit
