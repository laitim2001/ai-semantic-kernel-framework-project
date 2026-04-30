"""
File: backend/src/agent_harness/_contracts/events.py
Purpose: Single-source LoopEvent type tree (22 subclasses per 17.md §4).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Description:
    AgentLoop.run() yields AsyncIterator[LoopEvent]. Different categories
    emit different subclasses (e.g. category 6 emits ToolCallRequested,
    category 2 emits ToolCallExecuted). API / SSE handlers consume the
    stream.

Key Components:
    - LoopEvent: abstract base (timestamp + trace_context)
    - 22 concrete subclasses (one per emit point in 17.md §4.1)

Sync callbacks NOT supported (per 17.md §4.2 — Anti-Pattern 11).

Owner: 01-eleven-categories-spec.md §範疇 1
Single-source: 17.md §4.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History (newest-first):
    - 2026-04-30: Add 3 new Cat 1-owned events (Sprint 50.2 Day 2.2) —
        TurnStarted / LLMRequested / LLMResponded for per-turn SSE granularity.
        Extend ToolCallExecuted with `result_content: str = ""` so tool result
        text reaches frontend (backward-compatible default).
    - 2026-04-30: Fix `datetime.utcnow()` → `datetime.now(UTC)` (Sprint 50.2 Day 0
        CARRY-002) — clears 28+ DeprecationWarning emitted per loop test run.
    - 2026-04-29: Initial creation (Sprint 49.1) — 22 stub subclasses

Related:
    - 01-eleven-categories-spec.md §範疇 1
    - 17-cross-category-interfaces.md §4 (LoopEvent table)
    - 02-architecture-design.md §SSE 事件規範
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from agent_harness._contracts.observability import TraceContext


@dataclass(frozen=True)
class LoopEvent:
    """Abstract base. Concrete subclasses are emitted by specific categories."""

    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    trace_context: TraceContext | None = None


# === Category 1: Orchestrator Loop ===========================================


@dataclass(frozen=True)
class LoopStarted(LoopEvent):
    session_id: UUID | None = None


@dataclass(frozen=True)
class TurnStarted(LoopEvent):
    """Emitted by Cat 1 at the top of each TAO loop iteration. (Sprint 50.2)"""

    turn_num: int = 0


@dataclass(frozen=True)
class LLMRequested(LoopEvent):
    """Emitted by Cat 1 immediately before chat_client.chat(). (Sprint 50.2)

    `tokens_in` is the prompt token count if available (best-effort; 0 when
    Loop hasn't yet wired count_tokens()).
    """

    model: str = ""
    tokens_in: int = 0


@dataclass(frozen=True)
class LLMResponded(LoopEvent):
    """Emitted by Cat 1 after parser.parse(response). (Sprint 50.2)

    Carries the canonical (content, tool_calls, thinking) tuple per
    02-architecture-design.md §SSE `llm_response` schema. Replaces SSE-level
    Thinking in 50.2; Thinking event itself stays for 50.1 test backward-compat.
    """

    content: str = ""
    tool_calls: tuple[Any, ...] = field(default_factory=tuple)  # tuple[ToolCall, ...]
    thinking: str | None = None


@dataclass(frozen=True)
class Thinking(LoopEvent):
    text: str = ""


@dataclass(frozen=True)
class LoopCompleted(LoopEvent):
    stop_reason: str = "end_turn"
    total_turns: int = 0


# === Category 6: Output Parser ==============================================


@dataclass(frozen=True)
class ToolCallRequested(LoopEvent):
    tool_call_id: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


# === Category 2: Tools ======================================================


@dataclass(frozen=True)
class ToolCallExecuted(LoopEvent):
    tool_call_id: str = ""
    tool_name: str = ""
    duration_ms: float = 0.0
    result_content: str = ""  # Sprint 50.2: tool output text (default empty for backward compat)


@dataclass(frozen=True)
class ToolCallFailed(LoopEvent):
    tool_call_id: str = ""
    tool_name: str = ""
    error: str = ""


# === Category 3: Memory =====================================================


@dataclass(frozen=True)
class MemoryAccessed(LoopEvent):
    layer: str = ""  # system / tenant / role / user / session
    operation: str = ""  # read / write / evict
    key: str = ""


# === Category 4: Context Mgmt ==============================================


@dataclass(frozen=True)
class ContextCompacted(LoopEvent):
    tokens_before: int = 0
    tokens_after: int = 0
    compaction_strategy: str = ""


# === Category 5: Prompt Builder =============================================


@dataclass(frozen=True)
class PromptBuilt(LoopEvent):
    layer_count: int = 0
    total_tokens: int = 0
    cache_breakpoints: int = 0


# === Category 7: State Mgmt =================================================


@dataclass(frozen=True)
class StateCheckpointed(LoopEvent):
    version: int = 0


# === Category 8: Error Handling =============================================


@dataclass(frozen=True)
class ErrorRetried(LoopEvent):
    attempt: int = 0
    error_class: str = ""
    backoff_ms: float = 0.0


# === Category 9: Guardrails =================================================


@dataclass(frozen=True)
class GuardrailTriggered(LoopEvent):
    guardrail_type: str = ""  # input / output / tool
    action: str = ""  # block / sanitize / escalate / reroll
    reason: str = ""


@dataclass(frozen=True)
class TripwireTriggered(LoopEvent):
    """Severe policy violation — terminates loop immediately (per 17.md §6)."""

    violation_type: str = ""
    detail: str = ""


# === Category 10: Verification ==============================================


@dataclass(frozen=True)
class VerificationPassed(LoopEvent):
    verifier: str = ""


@dataclass(frozen=True)
class VerificationFailed(LoopEvent):
    verifier: str = ""
    reason: str = ""
    correction_attempt: int = 0


# === Category 11: Subagent ==================================================


@dataclass(frozen=True)
class SubagentSpawned(LoopEvent):
    subagent_id: UUID | None = None
    mode: str = ""  # fork / teammate / handoff / as_tool
    parent_session_id: UUID | None = None


@dataclass(frozen=True)
class SubagentCompleted(LoopEvent):
    subagent_id: UUID | None = None
    summary: str = ""
    tokens_used: int = 0


# === HITL Centralization ====================================================


@dataclass(frozen=True)
class ApprovalRequested(LoopEvent):
    approval_request_id: UUID | None = None
    risk_level: str = ""


@dataclass(frozen=True)
class ApprovalReceived(LoopEvent):
    approval_request_id: UUID | None = None
    decision: str = ""  # APPROVED / REJECTED / ESCALATED


# === Category 12: Observability ============================================


@dataclass(frozen=True)
class SpanStarted(LoopEvent):
    span_name: str = ""
    span_id: str = ""


@dataclass(frozen=True)
class SpanEnded(LoopEvent):
    span_name: str = ""
    span_id: str = ""
    duration_ms: float = 0.0


@dataclass(frozen=True)
class MetricRecorded(LoopEvent):
    metric_name: str = ""
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)
