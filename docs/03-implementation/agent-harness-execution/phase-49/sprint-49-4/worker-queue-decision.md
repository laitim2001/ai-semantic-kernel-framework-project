# Worker Queue Selection — Celery vs Temporal

**Sprint**: 49.4 Day 2
**Date**: 2026-04-29
**Author**: AI 助手 + 用戶
**Status**: 📋 Decision proposed — awaiting user sign-off
**Spike code**: [`experimental/sprint-49-4-spike/`](../../../../../experimental/sprint-49-4-spike/)

---

## TL;DR

**Recommendation: Temporal** for V2's `agent_loop_worker.py`.

**Why**: Phase 53.1 HITL pause/resume is a **hard requirement** that Temporal solves natively (`workflow.wait_condition` + signals; can pause hours/days). Celery's primitives can simulate it but require building durable state plumbing on top of DB tables — exactly the kind of «redo Cat 7 work» V2 should avoid (Anti-Pattern 6 — Hybrid Bridge Debt).

**Trade-off accepted**: Operational cost (Temporal server) + cognitive cost (deterministic workflow rules) > Celery's familiarity. We pay this once at platform level, not per-business-domain.

**Carry-forward conditions** (will revisit if): Temporal Cloud pricing changes radically, or Phase 53.1 HITL turns out to be simpler than 53.3 design assumed (then Celery sufficient).

---

## Context

V2's worker queue must support:

1. **Long-running TAO loops** — minutes to hours per session (Phase 50+)
2. **HITL pause/resume** — agent waits for human approval, sometimes hours later (Phase 53.1+53.4)
3. **Mid-flight resume on worker death** — kill worker → no partial progress lost (Phase 50.1 reliability)
4. **Re-entrant state via Cat 7** — checkpoint/resume integration (Phase 53.1)
5. **Multi-tenant isolation** — task metadata + audit trail (Phase 49.3 multi-tenant rules)

Two mainstream Python options: **Celery** (de facto since 2009) and **Temporal** (Uber/Cadence-derived, 2020+).

---

## 5-Axis Comparison

### Axis 1 — Latency (enqueue + execution overhead)

| | Celery | Temporal |
|--|--------|----------|
| **Enqueue** | Sub-100 ms (Redis broker) | ~50 ms (gRPC to Temporal server) |
| **Execution overhead** | Minimal — direct task fn call | Workflow replay + activity dispatch (~10-30ms/turn) |
| **Verdict** | ✅ Slightly faster for short tasks | ✅ Negligible difference for long agent loops |

**For V2**: Both adequate. Agent loops are LLM-bound (seconds to minutes); 30 ms framework overhead invisible.

### Axis 2 — Durable state / mid-flight resume

| Scenario | Celery | Temporal |
|----------|--------|----------|
| Worker dies mid-task | Default: task lost; with `acks_late=True`: task replays from start | Workflow resumes from last completed activity (no plumbing) |
| 5-turn loop, worker dies after turn 3 | Replay turns 0,1,2,3,4 — duplicates side effects unless tasks are idempotent | Resume from turn 4; turns 0-3 already persisted in workflow history |
| HITL pause for hours | Requires DB table + polling task + state machine | `workflow.wait_condition(...)` — workflow off worker, zero resources |
| **Verdict** | ❌ Manual durable plumbing every business domain | ✅ Native; matches V2 Cat 7 + HITL needs |

**For V2**: This is the **decisive axis**. Phase 53.1+53.4 HITL design assumes pause/resume is cheap; Celery makes it expensive.

### Axis 3 — Re-entrant / replay determinism

| | Celery | Temporal |
|--|--------|----------|
| **Replay rules** | None — tasks just re-run | Workflow code must be deterministic (no `random` / no `time.now()` outside activities) |
| **Cognitive load** | Low — write Python normally | Medium — need to understand which calls go through activities |
| **Bug risk** | Idempotency bugs (task replayed → side effect twice) | Non-determinism bugs (workflow drifts from history → InvalidWorkflowState) |
| **Verdict** | ✅ Easier to write correctly | ❌ Real cognitive tax; requires team training |

**For V2**: Cognitive cost real but bounded — only `agent_loop_worker.py` + future workflow files care. Business-domain tools (Cat 2) are activities, not workflows; team writes them normally.

### Axis 4 — Python ergonomics

| | Celery | Temporal |
|--|--------|----------|
| **API style** | `@app.task`, `result = func.delay(args)` | `@workflow.defn`, `await workflow.execute_activity(...)` |
| **Async/await** | Sync-first; async support via `gevent` / `eventlet` (questionable) | Async-native (`temporalio` SDK) |
| **Pydantic / dataclass** | Manual JSON serialization | Built-in (data converter) |
| **Type checking** | Loose (Celery's task signatures hard to type strictly) | Strict (workflows + activities fully typed) |
| **Verdict** | ❌ Sync-first conflicts with V2 async-first stance | ✅ Aligns with V2 (FastAPI / SQLAlchemy 2 async) |

**For V2**: Celery's sync-first model conflicts with our async-everywhere stance (CLAUDE.md). Temporal `temporalio` SDK is async-first and fits naturally.

### Axis 5 — Operational cost

| | Celery | Temporal |
|--|--------|----------|
| **Dependencies** | Redis (we already run it) | Temporal server (Cassandra+Elasticsearch, OR managed Cloud) |
| **Dev environment** | `redis:7-alpine` (already in `docker-compose.dev.yml`) | `temporalio/auto-setup:1.24` single-binary; ~600 MB image |
| **Production complexity** | Trivial (Redis cluster) | Real (Cassandra+ES OR Temporal Cloud subscription) |
| **Cost (production)** | ~$50/mo Redis | ~$200/mo Temporal Cloud Starter, OR self-host 3 nodes (~$300/mo + ops) |
| **Skill curve** | Mainstream — most Python devs know Celery | Niche — fewer team members familiar |
| **Verdict** | ✅ Cheaper, easier ops | ❌ Higher infra + ops + skill cost |

**For V2**: This is Celery's strongest case. We accept Temporal's higher operational cost because Axis 2 (durable resume) eliminates expensive design debt elsewhere.

---

## Decision Matrix

| Axis | Weight | Celery | Temporal | Why this weight |
|------|--------|--------|----------|-----------------|
| 1. Latency | 5% | A | A- | Both adequate; LLM-bound workload |
| 2. Durable resume / HITL | **40%** | C | A+ | Phase 53.1 hard requirement |
| 3. Replay determinism | 15% | A | B | Cognitive tax, but bounded scope |
| 4. Python ergonomics | 15% | C | A | Async-first alignment matters |
| 5. Operational cost | 25% | A+ | C+ | Real cost, but pay once at platform level |
| **Weighted score** | | **B-** | **A-** | |

---

## Decision

### Chosen: **Temporal**

### Justification (3 reasons, ranked)

1. **HITL pause/resume is non-negotiable in Phase 53.1+53.4.**
   The whole governance Phase assumes agents can wait hours for human approval.
   With Temporal: `workflow.wait_condition(...)` solves this in 3 lines.
   With Celery: requires `approvals` table polling + state machine + DB-backed
   resume — exactly the «scattered approval logic across 6 places» V1 disaster
   we're escaping (Anti-Pattern 3 evidence).

2. **Async-first alignment with V2 stack.**
   FastAPI (Phase 49.4 Day 5), SQLAlchemy 2 async (Sprint 49.2),
   `temporalio` Python SDK — same paradigm. Celery's sync-first model
   would force `asyncio.run()` boundaries inside tasks, fighting our stack.

3. **Cat 7 (State Mgmt) integration is cheaper.**
   Temporal's workflow history IS Cat 7's checkpoint — same data, no double
   serialization. Celery would require us to build Cat 7 plumbing twice
   (once in workflow state, once for HITL resume).

### Trade-offs accepted

- ✅ Operational cost: $200/mo Temporal Cloud (or 3-node self-host)
- ✅ Skill curve: 2-3 days team training on workflow vs activity boundaries
- ✅ Image size: ~600 MB Temporal dev image (vs Redis 50 MB)
- ✅ Determinism cognitive tax: bounded to `agent_loop_worker.py` + future workflow files

### Rejected alternatives

- **Celery**: as analyzed above — Axis 2 fail decisive
- **Dramatiq**: lighter Celery alternative — same Axis 2 limitation
- **RQ**: simpler — same Axis 2 limitation
- **Apache Airflow**: built for ETL DAGs, not interactive agent loops
- **Manual asyncio + DB**: building a workflow engine = Anti-Pattern 6 (re-inventing Temporal)
- **Defer decision to Phase 53.1**: rejected — `agent_loop_worker.py` framework needs to be built in Phase 49.4 to unblock Phase 50.1

---

## Carry-Forward Conditions (re-evaluate if)

Re-evaluate this decision **only if** one of these triggers:

| Trigger | Re-evaluation action |
|---------|----------------------|
| Temporal Cloud raises Starter from $200 → $1000/mo | Switch to self-host or revisit Celery + custom HITL |
| Phase 53.1 HITL design simplifies to «approve within 5 min or auto-cancel» | Celery + simple approval table sufficient — switch back |
| Team shrinks below 3 people, ops capacity halves | Self-host Temporal becomes infeasible — Temporal Cloud OR fall back |
| `temporalio` Python SDK abandoned (>1 year no release) | Reconsider Cadence (parent project) or fall back to Celery |

---

## Implementation Plan (Phase 49.4 Day 2 + Phase 53.1)

### Phase 49.4 Day 2 (this sprint)

- [x] Spike both frameworks (`experimental/sprint-49-4-spike/`)
- [x] Decision report (this file)
- [ ] Build `runtime/workers/queue_backend.py` — abstract QueueBackend ABC + MockQueueBackend (no broker dependency)
- [ ] Build `runtime/workers/agent_loop_worker.py` — stub AgentLoopWorker accepting QueueBackend
- [ ] 4 unit tests against MockQueueBackend (no broker required for CI)
- [ ] **Do NOT build Temporal adapter yet** — defer to Phase 53.1 when HITL needs are concrete

### Phase 53.1 (later)

- [ ] Build `runtime/workers/temporal/` — TemporalQueueBackend implementing QueueBackend ABC
- [ ] Build `AgentLoopWorkflow` (workflows.py) + activities (activities.py)
- [ ] Wire HITL signals through Cat 9 governance + Cat 7 state
- [ ] Add Temporal server to `docker-compose.dev.yml`
- [ ] Production: provision Temporal Cloud OR self-host 3 nodes

### Phase 49.4 cleanup (Day 5 closeout)

- [ ] Move chosen framework's spike code → archived OR delete
- [ ] Update `experimental/sprint-49-4-spike/README.md` to mark "Decision: Temporal"
- [ ] Or delete `experimental/sprint-49-4-spike/celery_spike/` (rejected alternative)

---

## Cross-references

- [`06-phase-roadmap.md`](../../../../03-implementation/agent-harness-planning/06-phase-roadmap.md) §Phase 53.1 (HITL)
- [`07-tech-stack-decisions.md`](../../../../03-implementation/agent-harness-planning/07-tech-stack-decisions.md)
- [`13-deployment-and-devops.md`](../../../../03-implementation/agent-harness-planning/13-deployment-and-devops.md) §Worker queue (will update with this decision)
- [`04-anti-patterns.md`](../../../../03-implementation/agent-harness-planning/04-anti-patterns.md) §AP-3 (cross-directory) §AP-6 (hybrid bridge debt)

---

**Sign-off**:
- [ ] User approval (await)
- [x] AI 助手 (this report)
