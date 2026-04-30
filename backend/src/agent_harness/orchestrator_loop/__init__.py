"""Category 1: Orchestrator Loop (TAO/ReAct). See README.md."""

from agent_harness.orchestrator_loop._abc import AgentLoop
from agent_harness.orchestrator_loop.loop import AgentLoopImpl
from agent_harness.orchestrator_loop.termination import (
    TerminationReason,
    TripwireTerminator,
    should_terminate_by_cancellation,
    should_terminate_by_stop_reason,
    should_terminate_by_tokens,
    should_terminate_by_turns,
)

__all__ = [
    "AgentLoop",
    "AgentLoopImpl",
    "TerminationReason",
    "TripwireTerminator",
    "should_terminate_by_cancellation",
    "should_terminate_by_stop_reason",
    "should_terminate_by_tokens",
    "should_terminate_by_turns",
]
