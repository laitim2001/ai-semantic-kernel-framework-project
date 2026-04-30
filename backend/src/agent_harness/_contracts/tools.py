"""
File: backend/src/agent_harness/_contracts/tools.py
Purpose: Single-source tool contracts (ToolSpec / ToolCall / ToolResult / annotations).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Description:
    Defines tool definitions, calls, and results in an LLM-neutral form.
    Adapters convert these to/from provider-native formats (OpenAI
    function calling / Anthropic tools / etc.).

Key Components:
    - ToolSpec: tool definition (name + schema + annotations + concurrency)
    - ToolAnnotations: MCP 4-hint flags (read_only / destructive / etc.)
    - ConcurrencyPolicy: how the executor may parallelize this tool
    - ToolCall: shared with chat.py (re-exported for convenience)
    - ToolResult: tool execution outcome

Owner: 01-eleven-categories-spec.md §範疇 2
Single-source: 17.md §1.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Add first-class ToolHITLPolicy enum + risk_level field on
      ToolSpec (Sprint 51.1 Day 1; CARRY-021 from 51.0 retro). Replaces
      tags-encoded `hitl_policy:*` / `risk:*` workaround. Reuses existing
      RiskLevel enum from _contracts.hitl (single-source). ToolHITLPolicy
      named distinctly from per-tenant HITLPolicy dataclass to avoid
      collision; values map to 51.0 tag strings (auto / ask_once /
      always_ask).
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 2 (Tools)
    - 17-cross-category-interfaces.md §1.1 (ToolSpec dataclass) / §3 (cross-category tools)
    - 08b-business-tools-spec.md (business-domain tools)
    - sprint-51-1-plan.md §決策 1 (CARRY-021)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from agent_harness._contracts.hitl import RiskLevel


class ConcurrencyPolicy(Enum):
    """How a tool may be parallelized within a single LLM turn."""

    SEQUENTIAL = "sequential"
    READ_ONLY_PARALLEL = "read_only_parallel"
    ALL_PARALLEL = "all_parallel"


class ToolHITLPolicy(Enum):
    """Per-tool HITL behavior policy.

    Distinct from per-tenant HITLPolicy (in _contracts.hitl) which encodes
    tenant-level approval routing. This enum encodes the tool's intrinsic
    HITL stance: whether each invocation requires human approval before
    handler execution. PermissionChecker (Sprint 51.1 Day 2) consumes this
    plus risk_level to compute PermissionDecision.
    """

    AUTO = "auto"  # no HITL required (subject to risk_level + tenant policy)
    ASK_ONCE = "ask_once"  # first call in session requires approval
    ALWAYS_ASK = "always_ask"  # every call requires approval


@dataclass(frozen=True)
class ToolAnnotations:
    """MCP-style 4 hints; used by guardrails + concurrency planner."""

    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False  # accesses external systems / network


@dataclass(frozen=True)
class ToolSpec:
    """LLM-neutral tool definition. Adapters convert to provider format."""

    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema
    annotations: ToolAnnotations = field(default_factory=ToolAnnotations)
    concurrency_policy: ConcurrencyPolicy = ConcurrencyPolicy.SEQUENTIAL
    hitl_policy: ToolHITLPolicy = ToolHITLPolicy.AUTO
    risk_level: RiskLevel = RiskLevel.LOW
    version: str = "1.0"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolResult:
    """Output of a single tool execution.

    `result_content_types` indicates which content forms are present;
    Anthropic supports image content, OpenAI is string-only.
    """

    tool_call_id: str
    tool_name: str
    success: bool
    content: str | list[dict[str, Any]]  # text or content blocks
    result_content_types: tuple[Literal["text", "image", "json"], ...] = ("text",)
    error: str | None = None
    duration_ms: float | None = None
