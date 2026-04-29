"""Spike: Celery client demonstrating enqueue patterns. NOT production code."""

from __future__ import annotations

from tasks import simulate_agent_loop_turn, simulate_long_running_session


def demo_single_turn() -> None:
    """Pattern 1: enqueue + await single result."""
    result = simulate_agent_loop_turn.delay(session_id="sess-001", turn=0)
    print(f"task id: {result.id}")
    print(f"state: {result.state}")
    out = result.get(timeout=30)
    print(f"out: {out}")


def demo_full_session() -> None:
    """Pattern 2: parent task spawning child tasks (no native durable workflow)."""
    result = simulate_long_running_session.delay("sess-002", max_turns=3)
    out = result.get(timeout=60)
    print(f"session result: {out}")


def demo_kill_resume_limitations() -> None:
    """What we CAN'T demonstrate well in Celery:

    Imagine worker dies after turn 2 of a 5-turn session.
    - With acks_late=True: parent task retries from turn 0. Turns 0/1/2 redo.
    - Without: task lost.
    - In NEITHER case can the parent resume from turn 3.

    Compare with Temporal `temporal_spike/workflows.py` which checkpoints
    after every activity completion and resumes from the next activity.
    """
    print("(This is a documentation-only demo of Celery's limit.)")


if __name__ == "__main__":
    demo_single_turn()
    demo_full_session()
    demo_kill_resume_limitations()
