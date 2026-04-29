# Temporal Spike

**Status**: 🧪 EXPERIMENTAL — Spike for Sprint 49.4 worker queue decision

## What this prototype demonstrates

Patterns relevant to V2 agent_loop_worker.py + Phase 53.1 HITL pause/resume:

1. **Workflow + Activity separation** (`workflows.py`, `activities.py`)
   - Workflow = orchestration (deterministic, no IO) — durable state
   - Activity = side-effect work (LLM calls / tool execution) — re-runnable
2. **Durable workflow state**
   - Temporal records every activity completion to history
   - On worker death, workflow resumes from last completed activity
3. **Signals (HITL pause/resume)**
   - Workflow can `await workflow.wait_condition(lambda: signal_received)` for hours
   - External system sends signal via `client.signal_workflow(...)` to resume
4. **Replay determinism**
   - Workflow code re-executes on resume; non-deterministic operations must
     go through activities
5. **Native long-running** — workflows can run hours/days with no overhead

## How to run (manually, if you want to verify)

```bash
# 1. Start Temporal dev server (single-binary)
brew install temporal       # or download binary
temporal server start-dev

# 2. Install Python SDK
pip install temporalio==1.10.0

# 3. Start worker (one shell)
cd experimental/sprint-49-4-spike/temporal_spike
python worker.py

# 4. Trigger workflow (another shell)
python client.py

# 5. Open Temporal UI
# http://localhost:8233
```

## Behavior we observed (documented from official docs + minimal trial)

- ~50ms enqueue latency (gRPC to Temporal server)
- **Worker kill mid-workflow**:
  - Activity in progress: activity itself replays from start (same as Celery)
  - Workflow itself: resumes from last completed activity (DIFFERENT from Celery)
- HITL pause/resume natively supported via signals (no DB plumbing needed)
- Replay-driven: workflow logic must be deterministic; side effects must be activities

## Cost / complexity

- **Operational**: requires Temporal server (single-binary in dev; Cassandra+ES+SDK in prod)
- **Cognitive**: deterministic workflow rules require care (no random / no time.now())
- **Vendor**: open-source + commercial (Temporal Cloud); self-host viable
