# Celery Spike

**Status**: 🧪 EXPERIMENTAL — Spike for Sprint 49.4 worker queue decision

## What this prototype demonstrates

Patterns relevant to V2 agent_loop_worker.py:

1. **Task definition + retry** (`tasks.py`)
   - `@celery.task(bind=True, autoretry_for=..., max_retries=N, retry_backoff=True)`
   - Result backend (Redis) for caller to poll/await
2. **Worker startup** (`worker.py`)
   - `celery -A tasks worker --loglevel=info`
3. **Caller-side enqueue** (`client.py`)
   - `task.delay(args)` → returns AsyncResult
   - `result.get(timeout=N)` to await

## What CANNOT be tested in this spike (relevant to decision)

- **Mid-task durable checkpoint** — Celery has no native concept; if worker dies
  mid-task, the task either retries from scratch (`acks_late=True`) or is lost
  (default). No way to resume from line 50 of a 100-line task.
- **Long-running tasks (10+ min)** — possible but requires `task_soft_time_limit`
  + `task_time_limit` tuning; result backend must hold result for N seconds
  beyond completion.
- **Replay / time-travel** — not supported.

## How to run (manually, if you want to verify)

```bash
# 1. Start Redis
docker run -d -p 6379:6379 --name spike-redis redis:7-alpine

# 2. Install Celery
pip install celery[redis]==5.4.0

# 3. Start worker (in one shell)
cd experimental/sprint-49-4-spike/celery_spike
celery -A tasks worker --loglevel=info --concurrency=4

# 4. Run client (in another shell)
python client.py

# 5. Cleanup
docker stop spike-redis && docker rm spike-redis
```

## Behavior we observed (documented from official docs + minimal local trial)

- Sub-100ms enqueue latency (Redis broker)
- Automatic retry on transient errors
- Workers survive Redis restart (with `BROKER_CONNECTION_RETRY_ON_STARTUP=True`)
- **Worker kill mid-task**:
  - Default: task is lost (no `acks_late`)
  - With `acks_late=True`: task retries from start; partial work re-executed
  - **No way to resume mid-task** without manual checkpoint plumbing
