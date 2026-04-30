"""
File: backend/src/agent_harness/_contracts/memory.py
Purpose: Single-source memory hint type (MemoryHint).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1 (initial); Phase 51 / Sprint 51.2 Day 1 (extension)

Description:
    MemoryHint represents a "lead-then-verify" memory entry. Memory layer
    returns hints (lightweight markers) that the loop later verifies +
    materializes only if relevant.

    Sprint 51.2 Day 1 extends with 5 new fields per 01-eleven-categories-spec.md
    §範疇 3:
    - time_scale: 2nd axis (short_term / long_term / semantic) — was missing
    - confidence: memory-intrinsic credibility (0.0-1.0) — distinct from
      relevance_score which is per-query top-k score
    - last_verified_at: when last verified against ground truth
    - verify_before_use: agent must call verification tool before trusting
    - source_tool_call_id: provenance for "lead-then-verify" workflow

    Required fields ordering: required ones first (no default), optional last.

Owner: 01-eleven-categories-spec.md §範疇 3
Single-source: 17.md §1.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-30 (Sprint 51.2 Day 1)

Modification History (newest-first):
    - 2026-04-30: Add 5 fields (time_scale, confidence, last_verified_at,
      verify_before_use, source_tool_call_id) per Sprint 51.2 plan §2.2 —
      breaking change at Phase 51.2 (cheap because 0 constructor callers in
      src/tests at Phase 49.1 stub stage)
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 3 (Memory) — dual-axis matrix +
      MemoryHint specification
    - 17-cross-category-interfaces.md §1.1 — single-source registry row
    - sprint-51-2-plan.md §2.2 — extension rationale
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class MemoryHint:
    """Lightweight hint pointing to a memory entry; verify before materializing.

    Two-axis memory model:
    - layer (scope): system / tenant / role / user / session
    - time_scale: short_term (working) / long_term (durable) / semantic (vector)

    Two distinct credibility scores:
    - confidence: memory-intrinsic credibility (independent of query)
    - relevance_score: per-query top-k ranking score
    """

    # Required fields (no default)
    hint_id: UUID
    layer: Literal["system", "tenant", "role", "user", "session"]
    time_scale: Literal["short_term", "long_term", "semantic"]
    summary: str  # short token-cheap summary
    confidence: float  # 0.0 - 1.0; intrinsic credibility
    relevance_score: float  # 0.0 - 1.0; per-query ranking score
    full_content_pointer: str  # DB ref or vector_id; resolve on demand
    timestamp: datetime

    # Optional fields (with defaults) — must come after required per dataclass rules
    last_verified_at: datetime | None = None
    verify_before_use: bool = False
    source_tool_call_id: str | None = None
    expires_at: datetime | None = None
    tenant_id: UUID | None = None
