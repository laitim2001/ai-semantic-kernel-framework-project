"""
File: backend/src/agent_harness/_contracts/subagent.py
Purpose: Single-source subagent types (SubagentBudget / SubagentResult / SubagentMode).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Description:
    V2 supports 4 subagent dispatch modes (per 11-categories-spec §11):
    fork (parallel) / teammate (mailbox) / handoff (transfer control) /
    as_tool (LLM-callable). Worktree mode is INTENTIONALLY OMITTED — V2
    runs server-side, no per-process git worktree.

    Subagents enforce token / duration / concurrency budgets to prevent
    runaway cost.

Owner: 01-eleven-categories-spec.md §範疇 11
Single-source: 17.md §1.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Add AgentSpec dataclass (Sprint 54.2 US-2; needed by AsToolWrapper
      and Phase 55 multi-role subagent registries). Closes Day 0 D7 partial.
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 11 (Subagent Orchestration)
    - 17-cross-category-interfaces.md §1.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID


class SubagentMode(Enum):
    """4 subagent dispatch modes. Worktree DELIBERATELY ABSENT."""

    FORK = "fork"  # parallel sub-task; results merged back
    TEAMMATE = "teammate"  # peer-to-peer mailbox communication
    HANDOFF = "handoff"  # transfer control to another agent
    AS_TOOL = "as_tool"  # LLM calls subagent as if it were a tool


@dataclass(frozen=True)
class SubagentBudget:
    """Token / duration / concurrency caps for a subagent invocation."""

    max_tokens: int = 10_000
    max_duration_s: int = 300
    max_concurrent: int = 5
    max_subagent_depth: int = 3  # prevent recursive spawn explosion


@dataclass(frozen=True)
class SubagentResult:
    """Subagent.run() output. Includes mandatory ≤ N-token summary."""

    subagent_id: UUID
    mode: SubagentMode
    success: bool
    summary: str  # MUST be short (≤ 500 tokens by convention)
    full_artifact_pointer: str | None = None  # DB ref for full output
    tokens_used: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentSpec:
    """Spec for a subagent role; used by AsToolWrapper and TeammateExecutor.

    Sprint 54.2 US-2: minimal fields (role + prompt + model). Phase 55+ may
    extend with allowed tools / memory scopes / risk limits — those are
    role-config concerns NOT covered by Cat 11 dispatcher itself.
    """

    role: str  # short identifier, e.g. "researcher" / "writer"
    prompt: str | None = None  # initial system / role prompt
    model: str | None = None  # provider model id; None = inherit parent's
    metadata: dict[str, Any] = field(default_factory=dict)
