"""Spike: Temporal activities for V2 agent_loop_worker comparison.

Activities are where side effects happen (LLM calls, tool exec, DB writes).
Activities are RE-RUNNABLE; if they fail mid-execution they retry from start.

NOT production code. NOT imported by backend/src/.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from temporalio import activity  # type: ignore[import-not-found]


@dataclass
class TurnInput:
    session_id: str
    turn: int
    user_input: str


@dataclass
class TurnOutput:
    session_id: str
    turn: int
    llm_output: str
    tool_calls_executed: int


@activity.defn
async def call_llm(turn_input: TurnInput) -> str:
    """Activity: simulate LLM call. Side effect — stays in activity, not workflow."""
    activity.logger.info(f"call_llm turn={turn_input.turn}")
    await asyncio.sleep(2)  # simulate LLM latency
    return f"LLM responded to: {turn_input.user_input}"


@activity.defn
async def execute_tools(llm_output: str) -> int:
    """Activity: simulate tool execution. Returns count of tools called."""
    activity.logger.info(f"execute_tools for output={llm_output[:30]}")
    await asyncio.sleep(1)
    return 1  # 1 tool executed


@activity.defn
async def persist_turn(turn_output: TurnOutput) -> None:
    """Activity: persist turn to DB. Side effect — must be activity not workflow."""
    activity.logger.info(f"persist turn={turn_output.turn}")
    await asyncio.sleep(0.1)
