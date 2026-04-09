# Sprint 153 Checklist - U1: Redis Communication Persistence

## Reference
- Plan: [sprint-153-plan.md](sprint-153-plan.md)
- Phase: 45 (Agent Team V4 - P1 Upgrades)

---

## Implementation

- [ ] Create `redis_task_list.py` with RedisSharedTaskList class
  - [ ] Sync Redis client initialization
  - [ ] add_task() — HSET to tasks hash
  - [ ] claim_task() — Atomic HGET + HSET with lock
  - [ ] complete_task() / fail_task() — HSET status update
  - [ ] add_message() — XADD to messages stream + inbox stream
  - [ ] get_inbox() — XRANGE with cursor tracking
  - [ ] get_inbox_count() — XLEN
  - [ ] get_agent_current_task() — scan tasks hash
  - [ ] is_all_done() — check all task statuses
  - [ ] seconds_since_last_progress() — GET timestamp
  - [ ] to_dict() — HGETALL + XRANGE
  - [ ] cleanup() — DEL all session keys
  - [ ] TTL 3600s on all keys

- [ ] Modify `shared_task_list.py`
  - [ ] Add SharedTaskListProtocol (typing.Protocol)
  - [ ] Add create_shared_task_list(session_id, use_redis) factory

- [ ] Modify `agent_work_loop.py`
  - [ ] run_parallel_team() accepts session_id parameter
  - [ ] Use create_shared_task_list() factory
  - [ ] Pass session_id through to agents

- [ ] Modify `agent_team_poc.py`
  - [ ] Generate session_id per request
  - [ ] Pass to run_parallel_team()

## Verification

- [ ] Redis available → uses RedisSharedTaskList
- [ ] Redis unavailable → falls back to in-memory SharedTaskList
- [ ] E2E test: team execution completes with Redis backend
- [ ] Data visible in Redis after execution (redis-cli KEYS ipa:team:*)
