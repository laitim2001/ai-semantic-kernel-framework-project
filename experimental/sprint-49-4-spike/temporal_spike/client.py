"""Spike: Temporal client + signal demo. NOT production code."""

from __future__ import annotations

import asyncio

from temporalio.client import Client  # type: ignore[import-not-found]

from workflows import AgentLoopWorkflow


async def demo_basic_run() -> None:
    """Pattern 1: trigger workflow + await result."""
    client = await Client.connect("localhost:7233")
    handle = await client.start_workflow(
        AgentLoopWorkflow.run,
        args=("sess-001", 2),
        id="agent-loop-sess-001",
        task_queue="agent-loop-spike",
    )
    result = await handle.result()
    print(f"workflow result: {result}")


async def demo_hitl_signal() -> None:
    """Pattern 2: workflow pauses at HITL gate, external system signals approve.

    Compare with Celery: this would require:
    - DB-backed approval table
    - Periodic polling task to check approvals
    - State machine to track 'paused' vs 'running'
    All replaced by `workflow.wait_condition` + `client.signal`.
    """
    client = await Client.connect("localhost:7233")
    handle = await client.start_workflow(
        AgentLoopWorkflow.run,
        args=("sess-hitl", 5),  # 5 turns; HITL pause at turn 3
        id="agent-loop-sess-hitl",
        task_queue="agent-loop-spike",
    )
    # Workflow runs turns 0-2 then awaits approve. We signal after 10 sec.
    await asyncio.sleep(10)
    print("Signaling approve...")
    await handle.signal(AgentLoopWorkflow.approve)

    result = await handle.result()
    print(f"hitl workflow result: {result}")


async def main() -> None:
    await demo_basic_run()
    await demo_hitl_signal()


if __name__ == "__main__":
    asyncio.run(main())
