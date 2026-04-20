# Sprint 174 Plan — Bitemporal Support

**Phase**: 48 — Memory System Improvements
**Sprint**: 174
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Depends on**: Sprint 173 (scope context in place; bitemporal queries respect tenant)

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
