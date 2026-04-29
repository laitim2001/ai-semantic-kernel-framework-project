# Sprint 49.4 Worker Queue Spike

**Status**: 🧪 EXPERIMENTAL — DO NOT IMPORT FROM `backend/src/`
**Created**: 2026-04-29 (Sprint 49.4 Day 2)
**Deadline**: Sprint 49.4 close (2026-05-04) — must be merged into decision OR deleted
**Owner**: AI助手 + 用戶（決策審核）

---

## Purpose

Compare **Celery** vs **Temporal** as the worker queue backend for V2's
`agent_loop_worker.py`. Phase 53.1 (HITL pause / resume) has hard requirements
on durable workflow state that Celery does not provide natively. Phase 50+ TAO
loops may run minutes to hours per session and need re-entrant state.

This spike produces:
1. Prototype code for each framework showing the patterns we'd actually use
2. A 5-axis comparison report
3. A decision: which to build the V2 worker on

The spike code itself is **not run in CI** and **not imported by production code**.
The decision report (in `docs/03-implementation/agent-harness-execution/phase-49/
sprint-49-4/worker-queue-decision.md`) is the deliverable.

## Anti-Pattern Compliance

- **AP-5 No Undocumented PoC**: deadline (Sprint 49.4 close) + explicit decision required. After Sprint 49.4 closes, this folder is either:
  - Merged into chosen framework's adapter under `backend/src/runtime/workers/<framework>/`, OR
  - Deleted entirely (chosen framework lives only in production code, not in `experimental/`)
- **AP-6 No Future-Proofing**: not building both Celery + Temporal in production; pick ONE, the other gets deleted.

## Layout

```
experimental/sprint-49-4-spike/
├── README.md                  # this file
├── celery_spike/              # Celery + Redis prototype
│   ├── README.md
│   ├── tasks.py               # @celery.task definitions
│   ├── worker.py              # worker startup
│   └── client.py              # caller-side enqueue + result
└── temporal_spike/            # Temporal Python SDK prototype
    ├── README.md
    ├── workflows.py           # @workflow.defn workflows
    ├── activities.py          # @activity.defn activities
    ├── worker.py              # worker startup
    └── client.py              # caller-side trigger + signal
```

## Cleanup (after Sprint 49.4 closeout)

```bash
# Option A — chose Celery: keep celery_spike as reference, delete temporal_spike
rm -rf experimental/sprint-49-4-spike/temporal_spike

# Option B — chose Temporal: vice versa
rm -rf experimental/sprint-49-4-spike/celery_spike

# Option C — chose neither (defer): delete the whole spike folder
rm -rf experimental/sprint-49-4-spike
```

The chosen framework's production adapter lives in `backend/src/runtime/workers/<framework>/`,
NOT in `experimental/`.
