"""
File: backend/src/agent_harness/prompt_builder/templates.py
Purpose: Cat 5 prompt section templates + shared format helpers.
Category: 範疇 5 (Prompt Construction)
Scope: Phase 52 / Sprint 52.2 (Day 1.5)

Description:
    String templates and pure-function format helpers used by
    DefaultPromptBuilder and all 3 PositionStrategy implementations:
    - SYSTEM_ROLE_TEMPLATE: default agent system role
    - MEMORY_SECTION_HEADER / MEMORY_HINT_FORMAT: layer header + hint line
    - _memory_as_messages: dict[layer -> hints] → list[Message]
    - _summarize: truncate Message.content for LostInMiddle echo anchor

    All helpers are stateless and IO-free. Memory layer ordering is the
    caller's responsibility (DefaultPromptBuilder pre-sorts by time_scale
    priority before calling _memory_as_messages).

Created: 2026-05-01 (Sprint 52.2 Day 1.5)

Related:
    - sprint-52-2-plan.md §2.4 / §2.5
    - 01-eleven-categories-spec.md §範疇 5 — Lost-in-Middle
"""

from __future__ import annotations

from agent_harness._contracts import ContentBlock, MemoryHint, Message

# ---------------------------------------------------------------------------
# Templates (constants)
# ---------------------------------------------------------------------------

SYSTEM_ROLE_TEMPLATE = (
    "You are an enterprise AI agent. Follow tool calling conventions "
    "and respect HITL approval gates. Stay grounded in the provided "
    "memory and refuse out-of-scope requests."
)
"""Default system role for DefaultPromptBuilder._build_system_section()."""

MEMORY_SECTION_HEADER = "=== {layer} Memory ==="
"""Header prefix for each memory layer's system message."""

MEMORY_HINT_FORMAT = "- {summary}"
"""Single-line format for one MemoryHint inside a layer section."""

# ---------------------------------------------------------------------------
# Format helpers (used by DefaultPromptBuilder + PositionStrategy implementations)
# ---------------------------------------------------------------------------


def _memory_as_messages(memory_layers: dict[str, list[MemoryHint]]) -> list[Message]:
    """Convert memory hints grouped by layer into system messages.

    Each non-empty layer becomes one system message containing the formatted
    hints. Caller controls layer ordering.

    Args:
        memory_layers: dict[layer_name -> list[MemoryHint]]. Layer names are
            from 51.2 MemoryHint.layer (e.g., "system", "tenant", "role",
            "user", "session"). Empty layers are skipped.

    Returns:
        One Message per non-empty layer, in dict insertion order.
    """
    out: list[Message] = []
    for layer_name, hints in memory_layers.items():
        if not hints:
            continue
        lines = [MEMORY_SECTION_HEADER.format(layer=layer_name.title())]
        for h in hints:
            # MemoryHint uses `summary` (token-cheap text); see _contracts/memory.py
            lines.append(MEMORY_HINT_FORMAT.format(summary=h.summary))
        out.append(
            Message(
                role="system",
                content="\n".join(lines),
                metadata={"memory_layer": layer_name, "hint_count": len(hints)},
            )
        )
    return out


def _content_to_text(content: str | list[ContentBlock]) -> str:
    """Best-effort flatten of Message.content to plain text for summarization."""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    return " ".join(parts)


def _summarize(content: str | list[ContentBlock], *, max_chars: int = 200) -> str:
    """Truncate content to max_chars (with ellipsis) for the LostInMiddle echo."""
    text = _content_to_text(content)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."
