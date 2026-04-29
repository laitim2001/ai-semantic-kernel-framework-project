"""
File: backend/src/agent_harness/output_parser/classifier.py
Purpose: Cat 6 dispatcher classifier — ChatResponse → OutputType.
Category: 範疇 6 (Output Parsing)
Scope: Phase 50 / Sprint 50.1 (Day 1.2)

Description:
    Pure-function classifier consumed by Cat 1 (orchestrator_loop) to drive
    main TAO loop branching. Decoupled from `OutputParserImpl.parse()` so the
    Loop can call `classify_output()` directly on a ChatResponse without
    materializing a full ParsedOutput when only branching is needed.

    Decision rules (priority order):
        1. tool_calls is empty / None → FINAL (assistant final answer)
        2. any tool_call.name == "handoff" → HANDOFF (Cat 11; 50.1 leaves
           dispatch unimplemented — Loop yields LoopCompleted with reason
           HANDOFF_NOT_IMPLEMENTED until Phase 54.2)
        3. otherwise → TOOL_USE (Loop executes tool_calls and feeds back)

    "handoff" tool name is reserved per 17.md §3.1 single-source registry
    (owner: Cat 11 Subagent Orchestration).

Key Components:
    - HANDOFF_TOOL_NAME: reserved tool name constant
    - classify_output(response): pure function returning OutputType

Created: 2026-04-29 (Sprint 50.1 Day 1.2)
Last Modified: 2026-04-29

Modification History (newest-first):
    - 2026-04-29: Initial creation (Sprint 50.1 Day 1.2) — 3-way classifier
        with handoff-priority detection via reserved tool name.

Related:
    - .types (OutputType enum)
    - 17-cross-category-interfaces.md §3.1 (cross-cat tool registry; handoff
      owned by Cat 11)
    - 01-eleven-categories-spec.md §範疇 6 (classify_output spec)
"""

from __future__ import annotations

from agent_harness._contracts import ChatResponse

from .types import OutputType

HANDOFF_TOOL_NAME = "handoff"
"""Reserved tool name for Cat 11 handoff dispatch (per 17.md §3.1)."""


def classify_output(response: ChatResponse) -> OutputType:
    """Classify a ChatResponse into one of three dispatch branches.

    Args:
        response: provider-neutral ChatResponse from any LLM adapter.

    Returns:
        OutputType.FINAL if no tool_calls (assistant final answer).
        OutputType.HANDOFF if any tool_call.name == "handoff".
        OutputType.TOOL_USE for any other non-empty tool_calls list.

    Pure function: no side effects, no async, no tracer span — caller is
    expected to be inside an existing span (Cat 1 or Cat 6).
    """
    tool_calls = response.tool_calls or []
    if not tool_calls:
        return OutputType.FINAL
    if any(tc.name == HANDOFF_TOOL_NAME for tc in tool_calls):
        return OutputType.HANDOFF
    return OutputType.TOOL_USE
