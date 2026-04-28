"""
File: backend/src/agent_harness/_contracts/observability.py
Purpose: Single-source observability types (TraceContext / MetricEvent / SpanCategory).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Description:
    Category 12 (Observability) is cross-cutting: every other category's
    ABC accepts `trace_context: TraceContext`. TraceContext propagates
    through the loop and into all SSE events / OTel spans.

Key Components:
    - TraceContext: trace_id + span_id + tenant baggage
    - MetricEvent: 3-axis metric (latency / token / cost)
    - SpanCategory: 12 enum values mirroring the 11+1 categories

Owner: 01-eleven-categories-spec.md §範疇 12
Single-source: 17.md §1.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 12 (Observability)
    - 17-cross-category-interfaces.md §7.2 (cross-cutting rule)
    - observability-instrumentation.md (.claude/rules/)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4


class SpanCategory(Enum):
    """One enum value per 11+1 category for span attribution."""

    ORCHESTRATOR = "orchestrator_loop"
    TOOLS = "tools"
    MEMORY = "memory"
    CONTEXT_MGMT = "context_mgmt"
    PROMPT_BUILDER = "prompt_builder"
    OUTPUT_PARSER = "output_parser"
    STATE_MGMT = "state_mgmt"
    ERROR_HANDLING = "error_handling"
    GUARDRAILS = "guardrails"
    VERIFICATION = "verification"
    SUBAGENT = "subagent"
    OBSERVABILITY = "observability"  # meta
    HITL = "hitl"  # centralization


@dataclass(frozen=True)
class TraceContext:
    """OTel-compatible trace context. Propagates through every category ABC."""

    trace_id: str = field(default_factory=lambda: uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid4().hex[:16])
    parent_span_id: str | None = None
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    session_id: UUID | None = None
    baggage: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create_root(cls) -> "TraceContext":
        """Create a top-level trace context with no parent."""
        return cls()


@dataclass(frozen=True)
class MetricEvent:
    """3-axis metric: latency / token / cost. Emitted via Tracer.record_metric()."""

    metric_name: str
    metric_type: Literal["counter", "gauge", "histogram"]
    value: float
    timestamp: datetime
    category: SpanCategory
    labels: dict[str, str] = field(default_factory=dict)
    trace_context: TraceContext | None = None
