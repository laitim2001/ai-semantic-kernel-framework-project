"""
File: backend/src/agent_harness/_contracts/compaction.py
Purpose: Single-source dataclasses for Cat 4 Compactor outputs.
Category: cross-category single-source contracts (per 17.md §1.1)
Scope: Phase 52 / Sprint 52.1

Description:
    Defines the LLM-neutral compaction strategy enum + Compactor return type.
    Used by Cat 4 (compactor implementations) and Cat 1 (loop event payload
    for ContextCompacted). Frozen dataclasses to allow safe sharing across
    the trace_context propagation chain (range 12).

Key Components:
    - CompactionStrategy: enum of 3 strategies (STRUCTURAL / SEMANTIC / HYBRID)
    - CompactionResult: Compactor.compact_if_needed() return value (frozen)

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §1.1
Created: 2026-05-01 (Sprint 52.1, Day 1)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 1) — define CompactionStrategy + CompactionResult  # noqa: E501
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_harness._contracts.state import LoopState


class CompactionStrategy(str, Enum):
    """Compaction strategy selector. Owner: Cat 4."""

    STRUCTURAL = "structural"
    """Rule-based: drop redundant tool retries; keep system + recent N turns + HITL."""

    SEMANTIC = "semantic"
    """LLM-driven: summarize old turns into a single assistant message."""

    HYBRID = "hybrid"
    """Structural first; if still over budget, fall through to semantic."""


@dataclass(frozen=True)
class CompactionResult:
    """Compactor.compact_if_needed() return value. Single-source for Cat 1 event payload."""

    triggered: bool
    """True if compaction actually ran; False = passthrough (no work done)."""

    strategy_used: CompactionStrategy | None
    """Which strategy did the work; None if triggered=False."""

    tokens_before: int
    """Pre-compaction token count (per TokenCounter.count())."""

    tokens_after: int
    """Post-compaction token count; equal to tokens_before if triggered=False."""

    messages_compacted: int
    """Count of messages collapsed/redacted/summarized; 0 if triggered=False."""

    duration_ms: float
    """Wall-clock cost of the compaction call (for SLO + tracing)."""

    compacted_state: LoopState | None
    """The new compacted state; None if triggered=False (caller keeps original)."""
