# =============================================================================
# IPA Platform - Context Budget Manager
# =============================================================================
# CC-Inspired token-aware memory context assembly.
#
# CC Equivalent: buildEffectiveSystemPrompt() + 4-tier compression strategy
# Server-Side Adaptation: Priority-based section allocation with token budgets,
# replacing the hard [:500] truncation in the current pipeline.
#
# Architecture:
#   ContextBudgetManager
#   ├── assemble_context()  — Main entry: gather all memories, allocate budget
#   ├── _allocate_budgets() — Priority-based token allocation per section
#   ├── _smart_truncate()   — Sentence-boundary truncation (not mid-word)
#   └── _format_section()   — Render a section with header
#
# Priority order (highest first):
#   1. PINNED    — always loaded, like CC's CLAUDE.md
#   2. WORKING   — current session recent events
#   3. RELEVANT  — semantic search results from long-term
#   4. HISTORY   — conversation history summary
# =============================================================================

import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .types import MemoryLayer, MemoryRecord

logger = logging.getLogger(__name__)

# Approximate token count: ~4 chars per token for English, ~2 for CJK
# This is a fast heuristic; production can use tiktoken for exact counts.
_CHARS_PER_TOKEN_EN = 4
_CHARS_PER_TOKEN_CJK = 2


def estimate_tokens(text: str) -> int:
    """Estimate token count for mixed English/CJK text.

    Uses a blended heuristic: counts CJK characters separately (2 chars/token)
    and Latin characters (4 chars/token). Production should use tiktoken.
    """
    if not text:
        return 0

    cjk_count = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff'
                    or '\u3400' <= ch <= '\u4dbf'
                    or '\uf900' <= ch <= '\ufaff')
    non_cjk_count = len(text) - cjk_count

    tokens = (cjk_count / _CHARS_PER_TOKEN_CJK) + (non_cjk_count / _CHARS_PER_TOKEN_EN)
    return max(1, int(tokens))


@dataclass
class ContextBudgetConfig:
    """Configuration for context budget allocation.

    Total budget is split among sections by percentage.
    Higher-priority sections are preserved during overflow.
    """
    total_budget_tokens: int = 6000
    pinned_pct: float = 0.30        # 30% for pinned knowledge (highest priority)
    working_pct: float = 0.25       # 25% for recent working memory
    relevant_pct: float = 0.30      # 30% for semantic search results
    history_pct: float = 0.15       # 15% for conversation history summary


@dataclass
class ContextSection:
    """A single section of the assembled context."""
    name: str
    priority: int       # Lower number = higher priority (0 = highest)
    memories: List[MemoryRecord] = field(default_factory=list)
    content: str = ""
    token_count: int = 0
    max_tokens: int = 0
    truncated: bool = False


@dataclass
class AssembledContext:
    """Result of context assembly — ready for LLM prompt injection."""
    sections: Dict[str, str]
    total_tokens: int
    budget_used_pct: float
    pinned_count: int
    dropped_sections: List[str] = field(default_factory=list)
    section_details: Dict[str, dict] = field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """Render all sections into a single formatted prompt block.

        This replaces the old raw memory_text[:500] concatenation.
        """
        parts = []
        section_order = [
            "pinned_knowledge",
            "recent_context",
            "relevant_memories",
            "user_preferences",
            "history_summary",
        ]

        for name in section_order:
            content = self.sections.get(name, "")
            if content and content.strip():
                header = _SECTION_HEADERS.get(name, name.upper())
                parts.append(f"=== {header} ===\n{content}")

        if not parts:
            return "No memory context available."

        return "\n\n".join(parts)


_SECTION_HEADERS = {
    "pinned_knowledge": "YOUR KNOWLEDGE ABOUT THIS USER",
    "recent_context": "RECENT CONTEXT",
    "relevant_memories": "RELEVANT PAST EXPERIENCE",
    "user_preferences": "USER PREFERENCES",
    "history_summary": "SESSION HISTORY",
}


class ContextBudgetManager:
    """Token-aware context assembly — CC's buildEffectiveSystemPrompt equivalent.

    Assembles memory context within a configurable token budget, using
    priority-based allocation. Higher-priority sections (pinned > working >
    relevant > history) are preserved when the budget is tight.

    Replaces the hard [:500] truncation in the current pipeline with
    smart sentence-boundary truncation and structured templates.
    """

    def __init__(
        self,
        config: Optional[ContextBudgetConfig] = None,
        token_counter: Optional[Callable[[str], int]] = None,
    ):
        self.config = config or ContextBudgetConfig()
        self._count_tokens = token_counter or estimate_tokens

    async def assemble_context(
        self,
        user_id: str,
        query: str,
        memory_manager,  # UnifiedMemoryManager — avoid circular import
        session_id: Optional[str] = None,
        history_summary: str = "",
    ) -> AssembledContext:
        """Assemble complete memory context within token budget.

        Args:
            user_id: User identifier.
            query: Current user query (for semantic search).
            memory_manager: UnifiedMemoryManager instance.
            session_id: Optional session identifier.
            history_summary: Optional conversation history summary.

        Returns:
            AssembledContext ready for prompt injection.
        """
        cfg = self.config
        budget = cfg.total_budget_tokens

        # ── Gather memories from all layers ──

        # Priority 1: Pinned (always loaded)
        pinned_memories = await memory_manager.get_pinned(user_id)

        # Priority 2: Working memory (recent)
        working_memories = []
        if memory_manager._redis:
            try:
                import json
                pattern = f"memory:working:{user_id}:*"
                keys = []
                async for key in memory_manager._redis.scan_iter(match=pattern, count=50):
                    keys.append(key)
                for key in keys[:10]:
                    data = await memory_manager._redis.get(key)
                    if data:
                        working_memories.append(MemoryRecord.from_dict(json.loads(data)))
            except Exception as e:
                logger.warning(f"ContextBudget: working memory scan failed: {e}")

        # Priority 3: Relevant long-term memories (semantic search)
        relevant_memories = []
        if query:
            try:
                search_results = await memory_manager.search(
                    query=query,
                    user_id=user_id,
                    layers=[MemoryLayer.LONG_TERM],
                    limit=10,
                )
                relevant_memories = [r.memory for r in search_results]
            except Exception as e:
                logger.warning(f"ContextBudget: semantic search failed: {e}")

        # ── Separate preferences from pinned for dedicated section ──
        from .types import MemoryType
        preference_types = {
            MemoryType.USER_PREFERENCE,
            MemoryType.EXTRACTED_PREFERENCE,
        }

        pinned_prefs = [m for m in pinned_memories if m.memory_type in preference_types]
        pinned_knowledge = [m for m in pinned_memories if m.memory_type not in preference_types]

        # Also extract preferences from relevant results
        relevant_prefs = [m for m in relevant_memories if m.memory_type in preference_types]
        relevant_other = [m for m in relevant_memories if m.memory_type not in preference_types]

        all_prefs = pinned_prefs + relevant_prefs

        # ── Build sections ──
        sections = [
            ContextSection(
                name="pinned_knowledge",
                priority=0,
                memories=pinned_knowledge,
                max_tokens=int(budget * cfg.pinned_pct),
            ),
            ContextSection(
                name="recent_context",
                priority=1,
                memories=working_memories,
                max_tokens=int(budget * cfg.working_pct),
            ),
            ContextSection(
                name="relevant_memories",
                priority=2,
                memories=relevant_other,
                max_tokens=int(budget * cfg.relevant_pct),
            ),
            ContextSection(
                name="user_preferences",
                priority=0,  # Same priority as pinned — preferences are critical
                memories=all_prefs,
                max_tokens=int(budget * cfg.pinned_pct * 0.5),  # sub-budget
            ),
            ContextSection(
                name="history_summary",
                priority=3,
                memories=[],
                content=history_summary,
                max_tokens=int(budget * cfg.history_pct),
            ),
        ]

        # ── Render and allocate ──
        result_sections: Dict[str, str] = {}
        section_details: Dict[str, dict] = {}
        dropped: List[str] = []
        total_tokens = 0

        # Sort by priority (lowest number = highest priority)
        sections.sort(key=lambda s: s.priority)

        remaining_budget = budget

        for section in sections:
            if remaining_budget <= 0:
                dropped.append(section.name)
                continue

            # Render memories to text
            if section.memories:
                rendered = self._render_memories(section.memories)
            elif section.content:
                rendered = section.content
            else:
                rendered = ""

            if not rendered.strip():
                result_sections[section.name] = ""
                section_details[section.name] = {"tokens": 0, "truncated": False}
                continue

            token_count = self._count_tokens(rendered)
            max_for_section = min(section.max_tokens, remaining_budget)

            if token_count > max_for_section:
                rendered = self._smart_truncate(rendered, max_for_section)
                token_count = self._count_tokens(rendered)
                section.truncated = True

            result_sections[section.name] = rendered
            section_details[section.name] = {
                "tokens": token_count,
                "memories": len(section.memories),
                "truncated": section.truncated,
            }
            total_tokens += token_count
            remaining_budget -= token_count

        return AssembledContext(
            sections=result_sections,
            total_tokens=total_tokens,
            budget_used_pct=round(total_tokens / budget * 100, 1) if budget > 0 else 0,
            pinned_count=len(pinned_memories),
            dropped_sections=dropped,
            section_details=section_details,
        )

    def _render_memories(self, memories: List[MemoryRecord]) -> str:
        """Render a list of memories into formatted text."""
        if not memories:
            return ""

        lines = []
        for mem in memories:
            # Include type context for extracted memories
            type_prefix = ""
            if mem.memory_type.value.startswith("extracted_"):
                type_prefix = f"[{mem.memory_type.value.replace('extracted_', '').upper()}] "
            elif mem.memory_type.value == "pinned_knowledge":
                type_prefix = ""  # Clean display for pinned

            lines.append(f"- {type_prefix}{mem.content}")

        return "\n".join(lines)

    def _smart_truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text at sentence boundaries, not mid-word.

        Unlike the old [:500] hard cut, this respects sentence structure.
        Falls back to word boundary if no sentence boundary found.
        """
        if self._count_tokens(text) <= max_tokens:
            return text

        # Estimate character limit from token budget
        char_limit = max_tokens * _CHARS_PER_TOKEN_EN  # conservative estimate

        if len(text) <= char_limit:
            return text

        truncated = text[:char_limit]

        # Try to find the last sentence boundary
        sentence_end = max(
            truncated.rfind('。'),    # CJK period
            truncated.rfind('. '),   # English period + space
            truncated.rfind('.\n'),  # English period + newline
            truncated.rfind('\n- '), # Bullet point boundary
            truncated.rfind('\n'),   # Line boundary
        )

        if sentence_end > char_limit * 0.5:  # Only use if we keep > 50% of content
            return truncated[:sentence_end + 1].rstrip()

        # Fall back to word boundary
        word_end = truncated.rfind(' ')
        if word_end > char_limit * 0.5:
            return truncated[:word_end].rstrip()

        # Last resort: hard cut with ellipsis
        return truncated.rstrip() + "..."
