"""
File: backend/src/agent_harness/_contracts/memory.py
Purpose: Single-source memory hint type (MemoryHint).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Description:
    MemoryHint represents a "lead-then-verify" memory entry. Memory
    layer returns hints (lightweight markers) that the loop later
    verifies + materializes only if relevant.

Owner: 01-eleven-categories-spec.md §範疇 3
Single-source: 17.md §1.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 3 (Memory)
    - 17-cross-category-interfaces.md §1.1
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class MemoryHint:
    """Lightweight hint pointing to a memory entry; verify before materializing."""

    hint_id: UUID
    layer: Literal["system", "tenant", "role", "user", "session"]
    summary: str  # short token-cheap summary
    relevance_score: float  # 0.0 - 1.0
    full_content_pointer: str  # DB ref or vector_id; resolve on demand
    timestamp: datetime
    expires_at: datetime | None = None
    tenant_id: UUID | None = None
