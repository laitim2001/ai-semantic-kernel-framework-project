"""Spike: Temporal worker. Run via: python worker.py. NOT production code."""

from __future__ import annotations

import asyncio

from temporalio.client import Client  # type: ignore[import-not-found]
from temporalio.worker import Worker  # type: ignore[import-not-found]

from activities import call_llm, execute_tools, persist_turn
from workflows import AgentLoopWorkflow


async def main() -> None:
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="agent-loop-spike",
        workflows=[AgentLoopWorkflow],
        activities=[call_llm, execute_tools, persist_turn],
    )
    print("Worker started on task_queue=agent-loop-spike")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
