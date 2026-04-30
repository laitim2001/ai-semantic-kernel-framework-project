"""
File: backend/src/agent_harness/_contracts/prompt.py
Purpose: Single-source PromptBuilder output type (PromptArtifact).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Description:
    PromptBuilder.build() returns a PromptArtifact: the assembled
    layered prompt (system / memory / tools / history / user) plus
    cache breakpoints for prompt caching (Anthropic-style cache_control).

Owner: 01-eleven-categories-spec.md §範疇 5
Single-source: 17.md §1.1

Note:
    CacheBreakpoint is also re-exported from _contracts.chat for
    convenience since it lives at the LLM API boundary.

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 5 (Prompt Construction)
    - 17-cross-category-interfaces.md §1.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_harness._contracts.chat import CacheBreakpoint, Message


@dataclass(frozen=True)
class PromptArtifact:
    """PromptBuilder.build() output. Layered + cache-aware."""

    messages: list[Message]
    cache_breakpoints: list[CacheBreakpoint] = field(default_factory=list)
    estimated_input_tokens: int = 0
    layer_metadata: dict[str, Any] = field(default_factory=dict)


# Re-export for convenience
__all__ = ["PromptArtifact", "CacheBreakpoint"]
