"""
File: backend/src/agent_harness/prompt_builder/strategies/tools_at_end.py
Purpose: ToolsAtEndStrategy — sequential messages + tools_position hint marker.
Category: 範疇 5 (Prompt Construction)
Scope: Phase 52 / Sprint 52.2 (Day 1.4)

Description:
    Same conversation order as NaiveStrategy, but appends a system-role
    "tools_position_hint" message at the end. The Adapter layer detects
    this marker via metadata["tools_position_hint"]=True and chooses to
    render tool schemas at the end of the request — preferred by some
    models (e.g., gpt-4o variants).

    The hint message is detached by Adapter before being sent to the
    provider; it never reaches the LLM as content. It only signals
    intent to the rendering layer.

Created: 2026-05-01 (Sprint 52.2 Day 1.4)
"""

from __future__ import annotations

from agent_harness._contracts import Message
from agent_harness.prompt_builder.strategies._abc import (
    PositionStrategy,
    PromptSections,
)
from agent_harness.prompt_builder.templates import _memory_as_messages


class ToolsAtEndStrategy(PositionStrategy):
    """Order: [system, memory, conversation, user_message, tools_position_hint]."""

    def arrange(self, sections: PromptSections) -> list[Message]:
        result: list[Message] = [sections.system]
        result.extend(_memory_as_messages(sections.memory_layers))
        result.extend(sections.conversation)
        if sections.user_message is not None:
            result.append(sections.user_message)

        if sections.tools:
            result.append(
                Message(
                    role="system",
                    content=(
                        f"[Tools position hint: render {len(sections.tools)} "
                        f"tool schemas at end]"
                    ),
                    metadata={
                        "tools_position_hint": True,
                        "tool_count": len(sections.tools),
                    },
                )
            )
        return result
