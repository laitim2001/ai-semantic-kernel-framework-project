# Sprint 177a Plan — GDPR + Cross-Layer Saga + Audit Chain (Compliance Critical)

**Phase**: 48 — Memory System Improvements
**Sprint**: 177a (split from original Sprint 177 after Batch 4 review)
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Plan Version**: **v2** (complete rewrite after Batch 4 RED verdict)
**Depends on**: Sprint 170-176 (all prior Phase 48 work)
**Gates**: Phase 48 cannot close without Sprint 177a compliance tests passing

---

## v2 Revision Notes — Split Rationale

Original Sprint 177 was judged RED by Batch 4 review due to 3 CRITICAL GDPR/compliance blockers. Scope split:

- **Sprint 177a (THIS PLAN)** — compliance critical work that blocks Phase 48 close:
  - GDPR `forget_user` with cross-layer saga pattern
  - Bitemporal tombstone filter (coordinates with Sprint 174)
  - HMAC-KMS audit chain + Merkle anchor
  - Append-only + maker/checker + signed tokens
  - DLQ retention with SOX-aware event classification
  - Integration + security + compliance tests

- **Sprint 177b (DEFER TO PHASE 49)** — UX/documentation (see `sprint-177b-deferred.md`):
  - Frontend DevUI MemoryExplorer
  - V9 baseline benchmark + `capture_v9_baseline.py` prereq
  - Phase-48-summary + V10 readiness notes + merge/tag
  - Pair with V10 codebase refresh

### Batch 4 CRITICAL Findings Addressed

1. **CRIT #1 — Bitemporal `as_of` ↔ `forget_user` GDPR Art.17**: tombstone model + query-path filter
2. **CRIT #2 — Cross-layer saga missing**: audit-row-first + per-layer retry + 202 Accepted
3. **CRIT #3 — Audit chain cryptography + concurrency**: HMAC-KMS pepper + SERIALIZABLE + daily Merkle anchor

---

## User Stories

### US-1: Complete and Auditable Right-to-Be-Forgotten
- **As** a compliance officer
- **I want** `DELETE /api/v1/users/{user_id}/memory` to erase ALL user data across Redis, PostgreSQL, Qdrant, and mem0, with transactional rollback on partial failure
- **So that** GDPR Article 17 obligations are met without leaving orphan PII

### US-2: Forgotten Users Disappear From Historical Views Too
- **As** a compliance officer
- **I want** bitemporal `as_of` queries to exclude forgotten users' data
- **So that** erasure is real, not just "current-state only"

### US-3: Tamper-Evident GDPR Audit Trail
- **As** a security engineer
- **I want** the GDPR audit log protected by HMAC-SHA256 with KMS-managed pepper + daily Merkle root anchored to WORM storage
- **So that** insider attacks cannot forge or erase audit entries undetectably

### US-4: Two-Person GDPR Operations
- **As** a security engineer
- **I want** destructive GDPR operations to require maker/checker two-person approval
- **So that** a single compromised account cannot erase evidence

---

## Technical Specifications

### 1. Forgotten Users Tombstone Table (CRITICAL #1)

```python
# domain/auth/models/forgotten_user.py
class ForgottenUser(Base):
    __tablename__ = "forgotten_users"

    id: UUID = mapped_column(primary_key=True)
    user_id_hash: str = mapped_column(String(64), nullable=False)
    org_id: str = mapped_column(String(64), nullable=False)
    forgotten_at: datetime = mapped_column(DateTime(timezone=True), nullable=False)
    reason: str = mapped_column(String(32), nullable=False)
    audit_chain_id: UUID = mapped_column(ForeignKey("gdpr_audit_log.id"))

    __table_args__ = (
        Index("ix_forgotten_org_user", "org_id", "user_id_hash"),
        UniqueConstraint("org_id", "user_id_hash"),
    )
```

**Coordination with Sprint 174**: bitemporal `search_as_of()` MUST filter against this table. Merge order must be S174 → S177a OR S177a→S174 with S174 v2 referencing the tombstone table; both Sprint 174 v2 and Sprint 177a v2 reference the same schema.

### 2. Cross-Layer Saga Pattern (CRITICAL #2)

Implementation pattern:
1. **Audit-row-first** with `status=pending`
2. **Per-layer attempts**: Redis → PG → Qdrant → mem0, each independent try/except
3. **Per-layer status tracking**: `{redis: completed|failed:reason, pg: ..., qdrant: ..., mem0: ...}`
4. **Retry queue**: failed layers scheduled via `gdpr_retry_queue` with exponential backoff
5. **Tombstone write** (atomic with audit update)
6. **HTTP response**: `200 OK` if all complete; `202 Accepted` if any pending retry

See `domain/auth/services/gdpr_service.py` pseudocode in §3 of `phase-48-review-consolidated.md`.

### 3. HMAC-KMS Audit Chain + Merkle Anchor (CRITICAL #3)

```python
# domain/auth/models/gdpr_audit_log.py
class GDPRAuditLog(Base):
    __tablename__ = "gdpr_audit_log"

    id: UUID = mapped_column(primary_key=True)
    sequence: int = mapped_column(BigInteger, nullable=False, unique=True)  # monotonic
    operation: str
    subject_user_id_hash: str
    requester: str
    approver: Optional[str]
    timestamp: datetime
    payload_hash: str
    prev_hash: str
    hmac: str           # HMAC-SHA256(prev_hash || payload_hash, KMS_PEPPER)
    status: str         # pending | done | failed
    per_layer_status: JSONB
```

**Write path key points**:
- `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE`
- `SELECT pg_advisory_xact_lock(0x01)` to prevent sequence race
- Pepper fetched from KMS (e.g., AWS KMS/Azure Key Vault), cached briefly
- Sequence is strictly monotonic (DB constraint + advisory lock)

**Daily Merkle Anchor**:
- Nightly cron job collects past 24h audit rows
- Builds Merkle tree, root written to S3 Object Lock (`COMPLIANCE` mode, 7-year retention)
- Anchors tamper evidence to immutable external storage

### 4. Append-Only Enforcement (HIGH)

```sql
CREATE OR REPLACE FUNCTION prevent_audit_modification() RETURNS trigger AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        RAISE EXCEPTION 'gdpr_audit_log is append-only — % forbidden', TG_OP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER gdpr_audit_append_only
BEFORE UPDATE OR DELETE ON gdpr_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

CREATE ROLE gdpr_audit_writer;
GRANT INSERT ON gdpr_audit_log TO gdpr_audit_writer;
REVOKE UPDATE, DELETE, TRUNCATE ON gdpr_audit_log FROM gdpr_audit_writer, PUBLIC;
```

### 5. Signed Confirm Token + Maker/Checker (HIGH)

Replace `?confirm=true` with two-step flow:

1. `POST /api/v1/users/{user_id}/forget/prepare` — requires `gdpr-operator` or `admin`; issues signed time-bound token (5min expiry, KMS-signed)
2. `DELETE /api/v1/users/{user_id}/memory?confirm_token=...&approver_token=...` — validates token; if two-person required, approver token must be from different principal

### 6. DLQ Retention with SOX Awareness (HIGH)

```python
class DLQEventCategory(Enum):
    OPERATIONAL = "operational"   # 90d retention
    AUTH = "auth"                 # SOX 7yr
    GDPR = "gdpr"                 # indefinite (legal hold)
    SECURITY = "security"         # SOX 7yr

RETENTION_POLICY = {
    DLQEventCategory.OPERATIONAL: {"redact_after": 30, "delete_after": 90},
    DLQEventCategory.AUTH: {"redact_after": 90, "delete_after": 365 * 7},
    DLQEventCategory.GDPR: {"redact_after": None, "delete_after": None},
    DLQEventCategory.SECURITY: {"redact_after": 90, "delete_after": 365 * 7},
}
```

### 7. Integration + Compliance Tests

- `test_gdpr_forget_user_full.py` — 4-layer deletion + tombstone + audit chain
- `test_gdpr_forget_partial_failure.py` — Qdrant down → 202 Accepted + retry queue
- `test_as_of_filters_forgotten.py` — forget at t2, query as_of=t1 → NOT in results
- `test_audit_chain_integrity.py` — 100 rows sequentially → verify each HMAC
- `test_audit_chain_concurrent.py` — 10 concurrent writes → unique sequences + chain intact
- `test_audit_chain_tamper_detection.py` — modify payload → verify fails
- `test_append_only_trigger.py` — UPDATE raises
- `test_dlq_retention.py` — freezegun + category-specific retention
- `test_2p_approval.py` — single-person approval rejected

---

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `backend/src/domain/auth/services/gdpr_service.py` | Create | Cross-layer saga forget_user |
| `backend/src/domain/auth/models/forgotten_user.py` | Create | Tombstone ORM |
| `backend/src/domain/auth/models/gdpr_audit_log.py` | Create | HMAC-chained audit |
| `backend/src/domain/auth/services/gdpr_retry_worker.py` | Create | Per-layer retry job |
| `backend/src/domain/auth/services/merkle_anchor_job.py` | Create | Daily Merkle anchor to S3 WORM |
| `backend/src/api/v1/users/gdpr_routes.py` | Create | `/forget/prepare` + `DELETE /memory` |
| `backend/alembic/versions/XXX_add_forgotten_users.py` | Create | Tombstone table |
| `backend/alembic/versions/XXX_add_gdpr_audit_log.py` | Create | Audit + trigger + INSERT role |
| `backend/src/integrations/memory/unified_memory.py` | Modify | `search_as_of` filters forgotten_users |
| `backend/src/infrastructure/messaging/dlq_maintenance.py` | Create | Category-aware retention |
| `backend/src/infrastructure/kms/audit_pepper.py` | Create | KMS pepper fetch + cache |
| `backend/src/core/settings.py` | Modify | DLQ retention + KMS config |
| Compliance test files (§7) | Create | 9 test files |

---

## Acceptance Criteria

- [ ] **AC-1**: `forget_user` deletes across Redis/PG/Qdrant/mem0; returns per-layer status map
- [ ] **AC-2**: Partial failure → `202 Accepted` + retry queue entry; successful retry completes all layers
- [ ] **AC-3**: `forgotten_users` tombstone written atomically with audit row; `search_as_of` excludes forgotten users in ALL time views
- [ ] **AC-4**: Audit chain uses HMAC-SHA256 with KMS pepper; SERIALIZABLE transaction + advisory lock prevents race
- [ ] **AC-5**: Daily Merkle root written to S3 Object Lock (7-year retention); verifiable via script
- [ ] **AC-6**: PG trigger rejects UPDATE/DELETE on `gdpr_audit_log`; separate INSERT-only role grant verified
- [ ] **AC-7**: `/forget/prepare` issues signed time-bound (5min) confirm token; invalid/expired tokens rejected
- [ ] **AC-8**: Maker/checker enforced for sensitive user deletions; self-approval rejected
- [ ] **AC-9**: DLQ events classified; AUTH/SECURITY categories retained 7yr; GDPR category retained indefinitely
- [ ] **AC-10**: Audit chain tamper detection: modifying payload → verify script flags
- [ ] **AC-11**: Concurrent `forget_user` (10 parallel) → all complete with unique sequence numbers + chain intact
- [ ] **AC-12**: Cross-layer integration test passes with testcontainers (Redis + PG + Qdrant + mem0 mock)

---

## Out of Scope (deferred to Sprint 177b / Phase 49)

- Frontend DevUI MemoryExplorer UI
- V9 baseline benchmark + `capture_v9_baseline.py`
- Phase-48-summary documentation + V10 readiness notes
- Merge/tag/README closing tasks
- GDPR dashboards / audit query UI
- Multi-region erasure coordination

---

## Exit Gate

Phase 48 CANNOT close until:
1. All 12 ACs pass
2. Compliance tests 100% pass (no skips)
3. Audit chain integrity verified via 1000-row script
4. DPIA (Data Protection Impact Assessment) draft written (part of Sprint 177b in Phase 49)
5. Sign-off: backend-lead + sec-lead + compliance officer
