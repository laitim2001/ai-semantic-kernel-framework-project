"""
File: backend/src/agent_harness/prompt_builder/strategies/lost_in_middle.py
Purpose: LostInMiddleStrategy — anchor important content at start AND end.
Category: 範疇 5 (Prompt Construction)
Scope: Phase 52 / Sprint 52.2 (Day 1.4)

Description:
    Default strategy for DefaultPromptBuilder. Mitigates "Lost in the Middle"
    (Liu et al. 2023) finding: LLMs underweight content in the middle of long
    contexts. Order:

        [system, user_echo, memory_msgs..., mid_history..., recent_assistants..., user_actual]

    The user message appears twice — once as a system-role echo near the top
    (metadata-marked) for top-anchor recall, and once at the bottom as the
    primary user turn. Recent assistants (last N) are kept near the bottom
    for short-term coherence. Older history sits in the middle (where loss
    is acceptable).

Created: 2026-05-01 (Sprint 52.2 Day 1.4)

Related:
    - 01-eleven-categories-spec.md §範疇 5 — Lost-in-Middle reference
    - sprint-52-2-plan.md §2.3 / Story 2 — strategy specification
"""

from __future__ import annotations

from agent_harness._contracts import Message
from agent_harness.prompt_builder.strategies._abc import (
    PositionStrategy,
    PromptSections,
)
from agent_harness.prompt_builder.templates import (
    _memory_as_messages,
    _summarize,
)


class LostInMiddleStrategy(PositionStrategy):
    """Anchor system + user at start and user at end; mid history compresses naturally."""

    def __init__(self, *, recent_assistant_count: int = 3, echo_max_chars: int = 200) -> None:
        self.recent_assistant_count = recent_assistant_count
        self.echo_max_chars = echo_max_chars

    def arrange(self, sections: PromptSections) -> list[Message]:
        result: list[Message] = [sections.system]

        # Anchor 1: user echo at top (only if user_message present)
        if sections.user_message is not None:
            echo_text = _summarize(sections.user_message.content, max_chars=self.echo_max_chars)
            result.append(
                Message(
                    role="system",
                    content=f"[Recent user query echo]\n{echo_text}",
                    metadata={"echo": True, "from_user_message": True},
                )
            )

        # Memory section (already sorted by time_scale priority by caller)
        result.extend(_memory_as_messages(sections.memory_layers))

        # Split conversation into mid_history vs recent_assistants
        # Recent = last N assistant messages; everything else (including all user turns) is mid
        assistant_msgs = [m for m in sections.conversation if m.role == "assistant"]
        recent_assistants = (
            assistant_msgs[-self.recent_assistant_count :]
            if self.recent_assistant_count > 0
            else []
        )
        recent_ids = {id(m) for m in recent_assistants}
        mid_history = [m for m in sections.conversation if id(m) not in recent_ids]

        result.extend(mid_history)
        result.extend(recent_assistants)

        # Anchor 2: user message actual at end (primary anchor)
        if sections.user_message is not None:
            result.append(sections.user_message)

        return result
