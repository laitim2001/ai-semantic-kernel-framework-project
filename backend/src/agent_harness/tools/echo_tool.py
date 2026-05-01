"""
File: backend/src/agent_harness/tools/echo_tool.py
Purpose: echo_tool built-in (carryover from 50.1 _inmemory.py).
Category: 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 5 — migrated out of _inmemory.py before deletion.

Description:
    `echo_tool` is the original 50.1 bring-up built-in (returns its `text`
    argument verbatim). 51.1 Day 5 migrates the spec + handler out of
    `_inmemory.py` into a non-deprecated location so register_builtin_tools
    can keep importing it after `_inmemory.py` is deleted in this sprint.

    No behavior change vs the 50.1 origin; only the file location moves.

Created: 2026-04-30 (Sprint 51.1 Day 5)
"""

from __future__ import annotations

from agent_harness._contracts import (
    ConcurrencyPolicy,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)

ECHO_TOOL_SPEC: ToolSpec = ToolSpec(
    name="echo_tool",
    description="Echoes the 'text' argument back verbatim. Test-only built-in.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to echo back.",
            },
        },
        "required": ["text"],
    },
    annotations=ToolAnnotations(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("builtin", "echo"),
)


async def echo_handler(call: ToolCall) -> str:
    """Return the 'text' argument verbatim."""
    return str(call.arguments.get("text", ""))


def make_echo_executor(
    *,
    tracer: "Tracer | None" = None,
) -> "tuple[ToolRegistryImpl, ToolExecutorImpl]":
    """Convenience factory: ToolRegistryImpl + ToolExecutorImpl wired with echo_tool.

    Replaces 50.1's _inmemory.make_echo_executor. Kept for tests + smoke
    scripts that just need a one-tool registry without going through
    register_builtin_tools (which adds 5 more specs).
    """
    from agent_harness.tools.executor import ToolExecutorImpl
    from agent_harness.tools.registry import ToolRegistryImpl

    registry = ToolRegistryImpl()
    registry.register(ECHO_TOOL_SPEC)
    executor = ToolExecutorImpl(
        registry=registry,
        handlers={"echo_tool": echo_handler},
        tracer=tracer,
    )
    return registry, executor


# Type-only imports avoided at module top to prevent import cycle (echo_tool
# is imported by tools/__init__.py before executor/registry are bound).
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from agent_harness.observability import Tracer
    from agent_harness.tools.executor import ToolExecutorImpl
    from agent_harness.tools.registry import ToolRegistryImpl
