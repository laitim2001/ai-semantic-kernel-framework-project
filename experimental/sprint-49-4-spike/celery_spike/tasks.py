"""Spike: Celery task patterns for V2 agent_loop_worker comparison.

NOT production code. NOT imported by backend/src/.
"""

from __future__ import annotations

import time

from celery import Celery  # type: ignore[import-not-found]

# Local-only spike broker config
app = Celery(
    "agent_loop_spike",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

app.conf.update(
    task_acks_late=True,  # task NOT acked until done — survives worker death (replays from start)
    task_track_started=True,
    task_time_limit=600,  # 10 min hard cap
    task_soft_time_limit=540,  # 9 min soft cap → SoftTimeLimitExceeded raises
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # 1h
)


@app.task(bind=True, autoretry_for=(ConnectionError,), max_retries=3, retry_backoff=True)
def simulate_agent_loop_turn(self, *, session_id: str, turn: int) -> dict:
    """Simulate one TAO loop turn (LLM call + tool exec).

    Demonstrates:
    - Auto-retry on transient errors (autoretry_for + retry_backoff)
    - bind=True gives access to self.request.id / self.retries
    - acks_late=True (set globally) — survives worker death

    What's NOT shown (because Celery can't):
    - Mid-task durable state — if worker dies at line 30, replay from line 1
    - Cross-turn checkpoint — no native concept
    """
    print(f"[celery] turn {turn} for session {session_id} starting "
          f"(retries={self.request.retries})")
    time.sleep(2)  # simulate LLM call
    print(f"[celery] turn {turn} done")
    return {"session_id": session_id, "turn": turn, "result": "ok"}


@app.task
def simulate_long_running_session(session_id: str, max_turns: int = 5) -> dict:
    """Simulate a multi-turn session.

    Each turn is a separate task — wired by the caller via chord/group/chain.
    Celery has primitives for this but no built-in durable workflow state.
    """
    print(f"[celery] session {session_id} starting {max_turns} turns")
    results = []
    for i in range(max_turns):
        # In real code, this would chain via .delay() or canvas (chain/group/chord)
        results.append(simulate_agent_loop_turn(session_id=session_id, turn=i))
    return {"session_id": session_id, "turns_done": len(results)}
