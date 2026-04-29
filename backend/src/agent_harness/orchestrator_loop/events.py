"""
File: backend/src/agent_harness/orchestrator_loop/events.py
Purpose: Cat 1 owner-attribution shim — re-exports LoopEvent subclasses from
         single-source `_contracts.events`. NO redefinition (per 17.md §1).
Category: 範疇 1 (Orchestrator Loop)
Scope: Phase 50 / Sprint 50.1 (Day 3.1)

Description:
    `_contracts/events.py` is the single-source for all 22 LoopEvent
    subclasses (per 17.md §4.1). This module is a thin re-export layer
    that documents which subclasses Cat 1 OWNS and EMITS — not a
    redefinition. Other categories continue to import from `_contracts`.

Owner attribution (per 17.md §4.1):
    - LoopStarted   — Cat 1 emits at run() entry
    - Thinking      — Cat 1 emits per turn after parser.parse()
    - LoopCompleted — Cat 1 emits on termination

    `ToolCallRequested` is OWNED by Cat 6 (output_parser semantically) but
    EMITTED by Cat 1 from parsed.tool_calls — both modules re-export for
    discoverability.

Created: 2026-04-30 (Sprint 50.1 Day 3.1)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 50.1 Day 3.1) — owner-attribution
        re-export shim. NO redefinition of LoopEvent or its subclasses
        (preserves 17.md §1 single-source). Re-exports 5 classes used by
        AgentLoopImpl.run() events.

Related:
    - agent_harness._contracts.events (single-source for all 22 LoopEvent subclasses)
    - 17-cross-category-interfaces.md §4.1 (LoopEvent emit ownership table)
    - 01-eleven-categories-spec.md §範疇 1 (events emitted by Cat 1)
"""

from __future__ import annotations

from agent_harness._contracts.events import (
    LoopCompleted,
    LoopEvent,
    LoopStarted,
    Thinking,
    ToolCallRequested,
)

__all__ = [
    "LoopCompleted",
    "LoopEvent",
    "LoopStarted",
    "Thinking",
    "ToolCallRequested",
]
