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
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 2 (Tools)
    - 17-cross-category-interfaces.md §3 (cross-category tools)
    - 08b-business-tools-spec.md (business-domain tools)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class ConcurrencyPolicy(Enum):
    """How a tool may be parallelized within a single LLM turn."""

    SEQUENTIAL = "sequential"
    READ_ONLY_PARALLEL = "read_only_parallel"
    ALL_PARALLEL = "all_parallel"


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
