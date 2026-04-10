# Sprint 153 Plan - U1: Redis Communication Persistence

## Phase 45: Agent Team V4 - P1 Upgrades

### Sprint Goal
Replace in-memory SharedTaskList with Redis-backed persistence for crash-safe inter-agent communication, matching CC's file-based mailbox pattern.

---

## User Stories

### US-153-1: Redis SharedTaskList
**As** the agent team system,
**I want** tasks and messages persisted in Redis,
**So that** inter-agent communication survives process restarts.

### US-153-2: Factory Pattern with Fallback
**As** a developer,
**I want** automatic Redis/in-memory selection,
**So that** the system works with or without Redis.

---

## Technical Specification

### Redis Key Structure
All keys prefixed with `ipa:team:{session_id}:`:

| Data | Redis Structure | Key |
|------|----------------|-----|
| Tasks | Hash (field=task_id, value=JSON) | `ipa:team:{sid}:tasks` |
| Messages | Stream | `ipa:team:{sid}:messages` |
| Directed Inbox | Stream per agent | `ipa:team:{sid}:inbox:{agent_name}` |
| Progress tracking | String (timestamp) | `ipa:team:{sid}:last_progress` |

### Sync/Async Bridge
- Tools run in OS threads (asyncio.to_thread) - need sync Redis client
- Use `redis.Redis` (sync) for all SharedTaskList operations
- Create from same config as async client (REDIS_HOST, REDIS_PORT)

### TTL & Cleanup
- All keys: TTL 3600s (1 hour)
- Explicit cleanup after Phase 2 synthesis

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/integrations/poc/redis_task_list.py` | NEW | RedisSharedTaskList (~250 LOC) |
| `backend/src/integrations/poc/shared_task_list.py` | MODIFY | Add Protocol + create_shared_task_list() factory |
| `backend/src/integrations/poc/agent_work_loop.py` | MODIFY | Accept session_id, use factory |
| `backend/src/api/v1/poc/agent_team_poc.py` | MODIFY | Pass session_id to run_parallel_team |

---

## Acceptance Criteria

- [ ] RedisSharedTaskList implements same API as SharedTaskList
- [ ] Factory auto-detects Redis availability
- [ ] Fallback to in-memory when Redis unavailable
- [ ] Tasks persist across process restarts (Redis available)
- [ ] Messages and inboxes persist in Redis Streams
- [ ] TTL 3600s auto-cleanup
- [ ] All existing E2E tests pass unchanged
