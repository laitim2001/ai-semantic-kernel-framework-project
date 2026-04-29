"""Spike: Temporal workflows for V2 agent_loop_worker comparison.

Workflows are DETERMINISTIC orchestration. No I/O, no random, no time.now() —
all side effects go through activities. The workflow's history is what gives
us durable resume.

KEY OBSERVATION for V2:
- Workflow can pause for hours/days via `workflow.wait_condition(...)` — this
  is exactly what Phase 53.1 HITL approval needs (no Cat 7 state checkpointing
  plumbing required).
- On worker death, workflow resumes from last completed activity in history.
  Compare with Celery which replays the entire parent task from scratch.

NOT production code.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow  # type: ignore[import-not-found]

with workflow.unsafe.imports_passed_through():
    from activities import (
        TurnInput,
        TurnOutput,
        call_llm,
        execute_tools,
        persist_turn,
    )


@workflow.defn
class AgentLoopWorkflow:
    """One end-to-end agent loop. Each turn = LLM call + tools + persist.

    Demonstrates Temporal patterns most relevant to V2:
    - Activity sequencing with await
    - Signal handling (pause/resume = HITL)
    - Durable resume from any activity boundary
    """

    def __init__(self) -> None:
        self._approved = False
        self._cancelled = False

    @workflow.signal
    def approve(self) -> None:
        """External signal — HITL operator approves continuation."""
        self._approved = True

    @workflow.signal
    def cancel(self) -> None:
        self._cancelled = True

    @workflow.run
    async def run(self, session_id: str, max_turns: int = 5) -> dict:
        results = []
        for turn in range(max_turns):
            if self._cancelled:
                break

            # Activity 1: LLM call (re-runs if worker dies; workflow resumes here)
            llm_out = await workflow.execute_activity(
                call_llm,
                TurnInput(session_id=session_id, turn=turn, user_input=f"Q{turn}"),
                start_to_close_timeout=timedelta(minutes=5),
            )

            # Activity 2: tool execution
            tools_n = await workflow.execute_activity(
                execute_tools,
                llm_out,
                start_to_close_timeout=timedelta(minutes=2),
            )

            # Activity 3: persist
            output = TurnOutput(
                session_id=session_id,
                turn=turn,
                llm_output=llm_out,
                tool_calls_executed=tools_n,
            )
            await workflow.execute_activity(
                persist_turn,
                output,
                start_to_close_timeout=timedelta(seconds=30),
            )
            results.append(output)

            # HITL pause: every 3 turns, wait for human approval
            if (turn + 1) % 3 == 0:
                # This `wait_condition` can wait HOURS or DAYS — workflow is
                # off the worker, no resources used. Caller signals via:
                # client.get_workflow_handle(...).signal(AgentLoopWorkflow.approve)
                self._approved = False
                await workflow.wait_condition(lambda: self._approved or self._cancelled)

        return {"session_id": session_id, "turns_done": len(results)}
