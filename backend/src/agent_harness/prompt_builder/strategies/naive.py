"""
File: backend/src/agent_harness/prompt_builder/strategies/naive.py
Purpose: NaiveStrategy — sequential ordering [system, memory, conversation, user].
Category: 範疇 5 (Prompt Construction)
Scope: Phase 52 / Sprint 52.2 (Day 1.4)

Description:
    Simplest ordering with no lost-in-middle mitigation. Used for testing,
    debug, and as a baseline for comparing other strategies. Tools are NOT
    included in the message list (Adapter handles tools separately via
    chat() tools= kwarg).

Created: 2026-05-01 (Sprint 52.2 Day 1.4)
"""

from __future__ import annotations

from agent_harness._contracts import Message
from agent_harness.prompt_builder.strategies._abc import (
    PositionStrategy,
    PromptSections,
)
from agent_harness.prompt_builder.templates import _memory_as_messages


class NaiveStrategy(PositionStrategy):
    """Sequential order: [system, memory_msgs..., conversation..., user_message]."""

    def arrange(self, sections: PromptSections) -> list[Message]:
        result: list[Message] = [sections.system]
        result.extend(_memory_as_messages(sections.memory_layers))
        result.extend(sections.conversation)
        if sections.user_message is not None:
            result.append(sections.user_message)
        return result
