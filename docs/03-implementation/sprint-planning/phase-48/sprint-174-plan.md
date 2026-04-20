# Sprint 174 Plan — Bitemporal Support

**Phase**: 48 — Memory System Improvements
**Sprint**: 174
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Plan Version**: **v2** (integrated Batch 2 team review findings — 1 CRITICAL + 2 HIGH + 5 MEDIUM)
**Depends on**: Sprint 173 (scope context in place; bitemporal queries respect tenant)
**Tightly coupled with**: Sprint 177a (GDPR tombstone — MUST be co-designed)

---

## v2 Revision Notes

Batch 2 team review surfaced:

### CRITICAL (coordinates with Sprint 177a)
1. **[sec] GDPR Art.17 vs `as_of` queries** — superseded memories violate right-to-be-forgotten. Need **tombstone model** distinguishing "superseded" (keep for history) vs "erased" (hard-delete PII in ALL time views including as_of).

### HIGH (2)
2. **[sec] `superseded_at` server-only + immutable + audit-logged** — else audit hiding possible
3. **[py] `Pydantic extra='forbid'`** config (v2 correct) — NOT `Field(exclude=True)` which is serialization-only

### MEDIUM (5)
4. AC-4 missing scope filter — as_of MUST combine scope + event_time
5. `search_as_of(datetime)` must be tz-aware UTC (`AwareDatetime` or raise)
6. `claimed_event_time` abuse — length cap + reject >10yr skew
7. `auditor` grant path undefined; meta-audit missing (who audits the auditors?)
8. Tests need `freezegun`; supersede assertions incomplete

---

## Background

Enterprise research Doc 02 §2.4 identified bitemporal support (event time vs ingestion time) as the "enterprise killer feature" — enables audit, compliance, policy versioning, and "what did we know on date X" queries.

V9 audit confirms IPA only has `created_at` / `accessed_at` — single time axis.

Security Engineer v1 review added CRITICAL requirement: `event_time` must NOT be client-injectable to prevent audit log forgery (GDPR Art. 32 integrity requirement).

---

## User Stories

### US-1: Query Memory State At Any Point In History
- **As** an enterprise auditor
- **I want** to query "what did the agent know on 2026-04-01?"
- **So that** I can reconstruct past decisions for compliance review

### US-2: Distinguish When Fact Was True vs When System Learned It
- **As** a platform user
- **I want** separate tracking of when an event actually occurred (`event_time`) versus when it was recorded (`ingestion_time`)
- **So that** policy changes and backdated information are handled correctly

### US-3: Event Time Cannot Be Forged
- **As** a security engineer
- **I want** `event_time` to be server-assigned (or derived from signed events), never client-injectable
- **So that** audit trail integrity is maintained

---

## Technical Specifications

### Schema Changes

1. **`MemoryEntry` type extension** (`integrations/memory/types.py`)
   ```python
   @dataclass
   class MemoryEntry:
       # ... existing fields ...
       event_time: datetime          # when fact was true (server-determined)
       ingestion_time: datetime      # when system recorded (was `created_at`)
       claimed_event_time: Optional[datetime] = None  # client-provided, audit only
       superseded_at: Optional[datetime] = None       # for fact supersede flows
       superseded_by: Optional[str] = None
   ```

2. **PostgreSQL Migration**
   - ALTER `session_memory`: add `event_time`, `claimed_event_time`, `superseded_at`, `superseded_by`
   - Backfill: `event_time = created_at` for legacy rows
   - Index: `(org_id, event_time)` for as-of queries

3. **Qdrant Payload Schema Update**
   - Add `event_time` (ISO8601 string), `ingestion_time`, `superseded_at`
   - Backfill script: for each existing point, add `event_time = created_at`

### API — As-Of Query

4. **`UnifiedMemoryManager.search_as_of(query, scope, as_of_time: datetime)`** new method
   - Filters memories where `event_time <= as_of_time AND (superseded_at IS NULL OR superseded_at > as_of_time)`
   - Applied at both PostgreSQL layer (L2) and Qdrant payload filter (L3)
   - Default behavior unchanged — regular `search()` returns latest state

5. **REST API Endpoint**
   - `GET /api/v1/memory/search?query=X&as_of=2026-04-01T00:00:00Z`
   - Requires `auditor` role (RBAC check)
   - Cached 1min (historical queries are repeatable)

### Event Time Integrity

6. **Event Time Determination Logic**
   - **Default**: `event_time = ingestion_time` (most memories)
   - **From signed source events** (webhooks, SSE, n8n): use event signature's timestamp if within signed payload
   - **Client-asserted**: stored in `claimed_event_time` but NEVER used for retrieval; `event_time` still server-set to `ingestion_time`
   - Middleware rejects request body containing `event_time` field in memory create (validation via Pydantic)

7. **Supersede Flow**
   - When a memory is updated (e.g., policy changed), create new entry with new `event_time`, original marked `superseded_at=new.event_time`, `superseded_by=new.memory_id`
   - Old memory remains queryable via `as_of_time` < supersede point

### Testing

8. **Unit Tests**
   - `test_bitemporal_types.py` — MemoryEntry field defaults, validation
   - `test_event_time_integrity.py` — client-provided `event_time` rejected; `claimed_event_time` stored separately
   - `test_search_as_of.py` — returns correct memories for various as-of windows
   - `test_supersede_flow.py` — old entry remains for historical query

9. **Integration Test**
   - `test_bitemporal_policy_change.py` — policy memory at t1, changed at t2, query at t1 returns v1, query at t3 returns v2
   - `test_backfill_bitemporal.py` — backfill script idempotent

10. **Security Test**
    - `test_event_time_forgery.py` — attempt to set `event_time=2020-01-01` via API body → rejected / ignored (only `claimed_event_time` stored)

---

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `backend/src/integrations/memory/types.py` | Modify | Add 4 new fields to `MemoryEntry` |
| `backend/alembic/versions/XXX_add_bitemporal_cols.py` | Create | session_memory ALTER |
| `backend/src/integrations/memory/unified_memory.py` | Modify | `search_as_of()`, event_time logic, supersede flow |
| `backend/src/integrations/memory/mem0_client.py` | Modify | Qdrant payload additions |
| `backend/src/api/v1/memory/search_routes.py` | Modify | `as_of` query param, RBAC |
| `backend/scripts/backfill_bitemporal_qdrant.py` | Create | Backfill event_time in Qdrant |
| `backend/scripts/backfill_bitemporal_pg.py` | Create | Backfill event_time in session_memory |
| `backend/tests/unit/integrations/memory/test_bitemporal_types.py` | Create | Type tests |
| `backend/tests/unit/integrations/memory/test_event_time_integrity.py` | Create | Integrity tests |
| `backend/tests/unit/integrations/memory/test_search_as_of.py` | Create | As-of tests |
| `backend/tests/unit/integrations/memory/test_supersede_flow.py` | Create | Supersede tests |
| `backend/tests/integration/memory/test_bitemporal_policy_change.py` | Create | E2E scenario |
| `backend/tests/security/test_event_time_forgery.py` | Create | Forgery rejection |

---

## Acceptance Criteria

- [ ] **AC-1**: `MemoryEntry` has `event_time`, `ingestion_time`, `claimed_event_time`, `superseded_at`, `superseded_by`
- [ ] **AC-2**: `session_memory` table migrated with new columns; legacy rows backfilled `event_time = created_at`
- [ ] **AC-3**: Qdrant points backfilled with `event_time` payload (idempotent script)
- [ ] **AC-4**: `search_as_of(query, scope, as_of_time)` returns only memories where `event_time <= as_of AND (superseded_at IS NULL OR superseded_at > as_of)`
- [ ] **AC-5**: `GET /api/v1/memory/search?as_of=...` requires `auditor` role; returns 403 otherwise
- [ ] **AC-6**: Request body `event_time` field rejected by Pydantic validation (422 error)
- [ ] **AC-7**: Client-asserted event time stored in `claimed_event_time`, never used for retrieval
- [ ] **AC-8**: Supersede flow — old memory remains queryable via as_of; new memory returned by default search
- [ ] **AC-9**: Signed source event (webhook) with trusted timestamp IS used as `event_time` (integration-tested)
- [ ] **AC-10**: All unit + integration + security tests pass

---

## Out of Scope

- Full GraphRAG-style temporal reasoning (research Doc 06 — future phase)
- Automatic supersede detection via LLM comparison (manual API for now)
- Time-series memory analytics (separate analytics phase)
- Timezone normalization beyond UTC (all timestamps UTC internally)

---

## v2 Implementation Notes (from Batch 2 team review)

### CRITICAL — GDPR Tombstone Model (coordinates with Sprint 177a)

**Problem**: `as_of` query returns historical snapshots. If user requests GDPR erasure, their data still appears in historical views → Art.17 violation.

**Solution — new `forgotten_users` tombstone table** (introduced by Sprint 177a, consumed by Sprint 174 queries):

```python
# domain/auth/models/forgotten_users.py (created in Sprint 177a)
class ForgottenUser(Base):
    user_id_hash: str  # SHA-256 with salt
    org_id: str
    forgotten_at: datetime  # ingestion_time of erasure
    reason: str  # "gdpr_request", "policy", "admin"
    audit_id: UUID  # link to GDPR audit log

# Sprint 174 bitemporal query MUST filter:
async def search_as_of(self, query, scope, as_of_time):
    # Existing bitemporal filter: event_time <= as_of AND (superseded_at IS NULL OR superseded_at > as_of)
    base_filter = {...}

    # NEW: exclude forgotten users (check tombstone)
    forgotten = await self.forgotten_users_repo.list_by_org(scope.org_id)
    forgotten_hashes = {f.user_id_hash for f in forgotten}

    results = await self._execute_search(query, base_filter)
    return [r for r in results if hash_user_id(r.user_id, scope) not in forgotten_hashes]
```

**AC Addition**: as_of queries MUST filter against `forgotten_users` tombstone; test case: GDPR-erase user at t2, query as_of=t1 → user's historical data NOT returned.

**Coordination with Sprint 177a**: The tombstone table is **created by Sprint 177a but CONSUMED by Sprint 174**. Merge order: S173 → S177a (table + forget_user service) → S174 (bitemporal query filter using tombstone). This breaks the simple linear dependency.

### HIGH — Server-only immutable superseded_at

```python
# types.py
@dataclass
class MemoryEntry:
    superseded_at: Optional[datetime] = None  # server-set only
    superseded_by: Optional[str] = None       # server-set only

# API layer — Pydantic model
class MemoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')  # NOT Field(exclude)

    content: str
    # superseded_at / superseded_by / event_time NOT in request model

# Setting superseded fields → ONLY via consolidation service
# Audit log entry on every supersede write
```

### HIGH — Pydantic v2 correct syntax

```python
# CORRECT (Pydantic v2):
class MemoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    content: str
    # event_time NOT listed → body containing "event_time": ... → ValidationError

# WRONG (doesn't achieve rejection):
class MemoryCreateRequest(BaseModel):
    event_time: datetime = Field(exclude=True)  # This only excludes from serialization
```

### MEDIUM — AC-4 scope filter

Revised AC-4: `search_as_of(query, scope, as_of_time)` MUST combine:
- `scope.org_id/workspace_id/user_id/agent_id` filter (from S173)
- `event_time <= as_of_time AND (superseded_at IS NULL OR superseded_at > as_of_time)` temporal filter
- `NOT IN (forgotten_users.user_id_hash WHERE org_id=scope.org_id)` GDPR filter
- Missing scope → `ScopeNotProvidedError` even in as-of path

### MEDIUM — tz-aware datetime

```python
from pydantic import AwareDatetime
from datetime import timezone

async def search_as_of(self, query, scope, as_of_time: AwareDatetime):
    if as_of_time.tzinfo is None:
        raise ValueError("as_of_time must be timezone-aware (UTC preferred)")
    # Normalize to UTC for storage comparison
    as_of_utc = as_of_time.astimezone(timezone.utc)
    # ... proceed with UTC
```

### MEDIUM — claimed_event_time abuse cap

```python
class ClaimedEventTimeValidator:
    @validator("claimed_event_time")
    def bound_skew(cls, v, values):
        if v is None:
            return v
        # Length cap: JSON-serialized representation
        if len(str(v)) > 64:  # ISO8601 ~25 chars, prevent oversized strings
            raise ValueError("claimed_event_time format invalid")
        # Skew cap: reject >10yr past or >1yr future
        now = datetime.now(timezone.utc)
        if v < now - timedelta(days=365*10) or v > now + timedelta(days=365):
            raise ValueError("claimed_event_time out of acceptable range")
        return v
```

### MEDIUM — Auditor grant + meta-audit

- `auditor` role granted via admin-only API (`POST /api/v1/admin/grant-auditor` requires `admin` role)
- Every `auditor` action (successful or denied) logged to `auditor_access_log` table (separate from memory audit)
- Query: `who auditor-queried as_of X, when, result_count` — visible to `super-admin` only

### MEDIUM — freezegun tests

```python
from freezegun import freeze_time

def test_bitemporal_supersede_flow():
    with freeze_time("2026-04-01"):
        memory_v1 = create_memory(content="policy v1")

    with freeze_time("2026-04-15"):
        memory_v2 = supersede(memory_v1, content="policy v2")

    # As-of before supersede:
    with freeze_time("2026-04-10"):
        results = search_as_of(query, scope, as_of_time="2026-04-10T00:00:00Z")
        assert memory_v1 in results
        assert memory_v2 not in results

    # As-of after supersede:
    with freeze_time("2026-05-01"):
        results = search_as_of(query, scope, as_of_time="2026-05-01T00:00:00Z")
        assert memory_v2 in results
        assert memory_v1 not in results  # superseded
```
