"""
File: backend/src/infrastructure/db/exceptions.py
Purpose: Domain exceptions raised by infrastructure/db helpers.
Category: Infrastructure / ORM core
Scope: Sprint 49.2 (StateVersion 雙因子樂觀鎖)
Owner: infrastructure/db owner

Description:
    Defines exceptions raised by infrastructure/db helpers (notably the
    StateVersion 雙因子 mechanism in models/state.py).

    These are NOT business / agent_harness exceptions — they live at the
    persistence layer. Upper layers (agent_harness or platform_layer)
    catch and translate as appropriate.

Key Components:
    - DBException: base for all infrastructure/db errors
    - StateConflictError: optimistic concurrency conflict on state_snapshots
        (parent_version mismatch OR parent_hash mismatch OR UNIQUE violation)
    - MigrationError: migration helper failure (rare; used for stamp / verify helpers)

Created: 2026-04-29 (Sprint 49.2 Day 1.3)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 1.3)

Related:
    - sprint-49-2-plan.md §技術設計 §4 (StateVersion 雙因子)
    - infrastructure/db/models/state.py (Sprint 49.2 Day 4 — raises StateConflictError)
"""

from __future__ import annotations


class DBException(Exception):
    """Base for all infrastructure/db domain exceptions."""


class StateConflictError(DBException):
    """
    Optimistic concurrency violation when appending a state snapshot.

    Raised when:
        - parent_version is provided but no row matches (deleted or never existed)
        - parent_version matches but parent_hash differs (state was advanced
          elsewhere between read and write)
        - UNIQUE(session_id, version) violation at INSERT time (another
          worker won the race)

    Upper layer should typically retry by re-reading current state +
    rebasing the change.
    """


class MigrationError(DBException):
    """Failure of a migration helper (verification / stamp / etc.)."""


__all__ = ["DBException", "StateConflictError", "MigrationError"]
