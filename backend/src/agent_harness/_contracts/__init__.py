"""
File: backend/src/agent_harness/_contracts/__init__.py
Purpose: Unified re-export of all single-source cross-category types.
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Usage:
    from agent_harness._contracts import (
        Message, ChatRequest, ChatResponse, StopReason,
        ToolSpec, ToolCall, ToolResult, ToolAnnotations, ConcurrencyPolicy,
        LoopState, TransientState, DurableState, StateVersion,
        LoopEvent, ToolCallRequested, ToolCallExecuted,
        MemoryHint,
        PromptArtifact, CacheBreakpoint,
        VerificationResult,
        SubagentBudget, SubagentResult, SubagentMode,
        TraceContext, MetricEvent, SpanCategory,
        ApprovalRequest, ApprovalDecision, HITLPolicy, RiskLevel, DecisionType,
    )

DO NOT redefine these types anywhere else; always import from here.

Owner: 17-cross-category-interfaces.md §1
Created: 2026-04-29 (Sprint 49.1)
"""

from agent_harness._contracts.chat import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    ContentBlock,
    Message,
    StopReason,
    TokenUsage,
    ToolCall,
)
from agent_harness._contracts.events import (
    ApprovalReceived,
    ApprovalRequested,
    ContextCompacted,
    ErrorRetried,
    GuardrailTriggered,
    LoopCompleted,
    LoopEvent,
    LoopStarted,
    MemoryAccessed,
    MetricRecorded,
    PromptBuilt,
    SpanEnded,
    SpanStarted,
    StateCheckpointed,
    SubagentCompleted,
    SubagentSpawned,
    Thinking,
    ToolCallExecuted,
    ToolCallFailed,
    ToolCallRequested,
    TripwireTriggered,
    VerificationFailed,
    VerificationPassed,
)
from agent_harness._contracts.hitl import (
    ApprovalDecision,
    ApprovalRequest,
    DecisionType,
    HITLPolicy,
    RiskLevel,
)
from agent_harness._contracts.memory import MemoryHint
from agent_harness._contracts.observability import (
    MetricEvent,
    SpanCategory,
    TraceContext,
)
from agent_harness._contracts.prompt import PromptArtifact
from agent_harness._contracts.state import (
    DurableState,
    LoopState,
    StateVersion,
    TransientState,
)
from agent_harness._contracts.subagent import (
    SubagentBudget,
    SubagentMode,
    SubagentResult,
)
from agent_harness._contracts.tools import (
    ConcurrencyPolicy,
    ToolAnnotations,
    ToolResult,
    ToolSpec,
)
from agent_harness._contracts.verification import VerificationResult

__all__ = [
    # chat
    "Message",
    "ChatRequest",
    "ChatResponse",
    "StopReason",
    "ContentBlock",
    "ToolCall",
    "TokenUsage",
    "CacheBreakpoint",
    # tools
    "ToolSpec",
    "ToolResult",
    "ToolAnnotations",
    "ConcurrencyPolicy",
    # state
    "LoopState",
    "TransientState",
    "DurableState",
    "StateVersion",
    # events
    "LoopEvent",
    "LoopStarted",
    "Thinking",
    "LoopCompleted",
    "ToolCallRequested",
    "ToolCallExecuted",
    "ToolCallFailed",
    "MemoryAccessed",
    "ContextCompacted",
    "PromptBuilt",
    "StateCheckpointed",
    "ErrorRetried",
    "GuardrailTriggered",
    "TripwireTriggered",
    "VerificationPassed",
    "VerificationFailed",
    "SubagentSpawned",
    "SubagentCompleted",
    "ApprovalRequested",
    "ApprovalReceived",
    "SpanStarted",
    "SpanEnded",
    "MetricRecorded",
    # memory
    "MemoryHint",
    # prompt
    "PromptArtifact",
    # verification
    "VerificationResult",
    # subagent
    "SubagentBudget",
    "SubagentResult",
    "SubagentMode",
    # observability
    "TraceContext",
    "MetricEvent",
    "SpanCategory",
    # hitl
    "ApprovalRequest",
    "ApprovalDecision",
    "HITLPolicy",
    "RiskLevel",
    "DecisionType",
]
