"""
File: backend/src/agent_harness/prompt_builder/strategies/_abc.py
Purpose: PositionStrategy ABC + PromptSections dataclass — pure stateless rearrangement of prompt sections.
Category: 範疇 5 (Prompt Construction)
Scope: Phase 52 / Sprint 52.2 (Day 1.3)

Description:
    PromptSections is the input dataclass that DefaultPromptBuilder feeds
    to a PositionStrategy. The strategy's `arrange()` is a pure function
    that takes the 5 sections and emits the final ordered list[Message]
    sent to ChatClient. Three concrete strategies live in sibling modules:
    naive / lost_in_middle / tools_at_end.

    "Lost in the Middle" (Liu et al. 2023): LLMs underweight content placed
    in the middle of long contexts. LostInMiddleStrategy mitigates by
    placing the user message both at top (echo) and bottom (actual).

Owner: 01-eleven-categories-spec.md §範疇 5 / 17.md §2.1 PositionStrategy

Created: 2026-05-01 (Sprint 52.2 Day 1.3)

Related:
    - 01-eleven-categories-spec.md §範疇 5 — Lost-in-Middle strategy
    - 17-cross-category-interfaces.md §1.1 PromptSections / §2.1 PositionStrategy
    - sprint-52-2-plan.md §2.3 + §2.4
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from agent_harness._contracts import MemoryHint, Message, ToolSpec


@dataclass(frozen=True)
class PromptSections:
    """Input to PositionStrategy.arrange(); 5 prompt building blocks.

    Owner: 17.md §1.1 PromptSections (Cat 5).

    Fields:
        system: The system role message.
        tools: Tool schemas to expose to the model (passthrough; arrange() does
            not mutate; Adapter layer renders tools per provider).
        memory_layers: Memory hints grouped by layer (system / tenant / role /
            user / session). Keys are layer names from 51.2 MemoryHint.layer.
            Within each layer, hints are pre-sorted by time_scale priority
            (permanent > quarterly > daily) by DefaultPromptBuilder before
            calling arrange().
        conversation: Past messages (user/assistant/tool turns) excluding
            the current user message.
        user_message: The current user message (the one being responded to).
    """

    system: Message
    tools: list[ToolSpec] = field(default_factory=list)
    memory_layers: dict[str, list[MemoryHint]] = field(default_factory=dict)
    conversation: list[Message] = field(default_factory=list)
    user_message: Message | None = None


class PositionStrategy(ABC):
    """Pure stateless rearrangement of PromptSections into ordered messages.

    Owner: 17.md §2.1 PositionStrategy (Cat 5).

    Implementations MUST be stateless and IO-free. They receive a
    fully-resolved PromptSections (memory already retrieved + sorted) and
    emit a list[Message] in the order to send to ChatClient.

    The three concrete strategies trade off readability vs lost-in-middle
    mitigation vs tool-at-end model preferences. See 01-spec §範疇 5.
    """

    @abstractmethod
    def arrange(self, sections: PromptSections) -> list[Message]:
        """Rearrange sections into final ordered message list.

        Args:
            sections: The 5 prompt building blocks (system, tools,
                memory_layers, conversation, user_message). Caller guarantees
                memory_layers is sorted by time_scale priority.

        Returns:
            Ordered list[Message] ready for ChatClient.chat(messages=...).
            Strategy does NOT include tool schemas in the return; tools are
            passed separately to chat() via tools= kwarg (the Adapter layer
            handles per-provider tool rendering).
        """
        ...
