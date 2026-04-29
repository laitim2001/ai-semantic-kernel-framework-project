"""
File: backend/tests/unit/test_imports.py
Purpose: Sprint 49.1 acceptance — verify 11+1 categories + HITL + adapters skeleton imports.
Category: tests
Scope: Phase 49 / Sprint 49.1 Day 5

This test exists to satisfy Sprint 49.1 plan "Import 全面驗收"
acceptance criterion: every ABC + every contract type must be
importable. Subsequent sprints will add real behavior tests.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_eleven_plus_one_categories_importable() -> None:
    """Each of the 11 categories + Cat 12 (Observability) + HITL exposes its ABC."""
    from agent_harness.context_mgmt import (
        Compactor,
        PromptCacheManager,
        TokenCounter,
    )
    from agent_harness.error_handling import (
        CircuitBreaker,
        ErrorClass,
        ErrorPolicy,
        ErrorTerminator,
    )
    from agent_harness.guardrails import (
        Guardrail,
        GuardrailAction,
        GuardrailResult,
        GuardrailType,
        Tripwire,
    )
    from agent_harness.hitl import HITLManager
    from agent_harness.memory import MemoryLayer, MemoryScope
    from agent_harness.observability import Tracer
    from agent_harness.orchestrator_loop import AgentLoop
    from agent_harness.output_parser import OutputParser, ParsedOutput
    from agent_harness.prompt_builder import PromptBuilder
    from agent_harness.state_mgmt import Checkpointer, Reducer
    from agent_harness.subagent import SubagentDispatcher
    from agent_harness.tools import ToolExecutor, ToolRegistry
    from agent_harness.verification import Verifier

    # All ABCs are abstract (cannot be instantiated directly)
    abcs = [
        AgentLoop,
        ToolRegistry,
        ToolExecutor,
        MemoryLayer,
        Compactor,
        TokenCounter,
        PromptCacheManager,
        PromptBuilder,
        OutputParser,
        Checkpointer,
        Reducer,
        ErrorPolicy,
        CircuitBreaker,
        ErrorTerminator,
        Guardrail,
        Tripwire,
        Verifier,
        SubagentDispatcher,
        Tracer,
        HITLManager,
    ]
    for abc_cls in abcs:
        with pytest.raises(TypeError):
            abc_cls()  # type: ignore[abstract]

    # Enums + value classes are constructible
    assert MemoryScope.SYSTEM.value == "system"
    assert ErrorClass.TRANSIENT.value == "transient"
    assert GuardrailType.INPUT.value == "input"
    assert GuardrailAction.BLOCK.value == "block"
    assert ParsedOutput is not None
    assert GuardrailResult is not None


@pytest.mark.unit
def test_contracts_unified_export() -> None:
    """All cross-category single-source types come from agent_harness._contracts."""
    from agent_harness._contracts import (
        ApprovalDecision,
        ApprovalReceived,
        ApprovalRequest,
        ApprovalRequested,
        CacheBreakpoint,
        ChatRequest,
        ChatResponse,
        ConcurrencyPolicy,
        ContentBlock,
        ContextCompacted,
        DecisionType,
        DurableState,
        ErrorRetried,
        GuardrailTriggered,
        HITLPolicy,
        LoopCompleted,
        LoopEvent,
        LoopStarted,
        LoopState,
        MemoryAccessed,
        MemoryHint,
        Message,
        MetricEvent,
        MetricRecorded,
        PromptArtifact,
        PromptBuilt,
        RiskLevel,
        SpanCategory,
        SpanEnded,
        SpanStarted,
        StateCheckpointed,
        StateVersion,
        StopReason,
        SubagentBudget,
        SubagentCompleted,
        SubagentMode,
        SubagentResult,
        SubagentSpawned,
        Thinking,
        TokenUsage,
        ToolAnnotations,
        ToolCall,
        ToolCallExecuted,
        ToolCallFailed,
        ToolCallRequested,
        ToolResult,
        ToolSpec,
        TraceContext,
        TransientState,
        TripwireTriggered,
        VerificationFailed,
        VerificationPassed,
        VerificationResult,
    )

    # 22 LoopEvent subclasses per 17.md §4.1
    loop_event_subclasses = {
        ApprovalReceived,
        ApprovalRequested,
        ContextCompacted,
        ErrorRetried,
        GuardrailTriggered,
        LoopCompleted,
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
    }
    assert len(loop_event_subclasses) == 22
    for cls in loop_event_subclasses:
        assert issubclass(cls, LoopEvent)

    # StopReason has all 6 expected values
    assert StopReason.END_TURN.value == "end_turn"
    assert StopReason.TOOL_USE.value == "tool_use"
    assert StopReason.MAX_TOKENS.value == "max_tokens"
    assert StopReason.STOP_SEQUENCE.value == "stop_sequence"
    assert StopReason.SAFETY_REFUSAL.value == "safety_refusal"
    assert StopReason.PROVIDER_ERROR.value == "provider_error"

    # SubagentMode has 4 modes (NO worktree per V2 design)
    modes = {m.value for m in SubagentMode}
    assert modes == {"fork", "teammate", "handoff", "as_tool"}

    # SpanCategory has 13 values (11+1 categories + HITL)
    assert len(SpanCategory) == 13

    # HITL: RiskLevel + DecisionType
    assert RiskLevel.LOW.value == "LOW"
    assert DecisionType.APPROVED.value == "APPROVED"

    # Construct sample dataclasses
    msg = Message(role="user", content="hi")
    assert msg.role == "user"
    tc = TraceContext.create_root()
    assert tc.trace_id  # non-empty
    assert tc.parent_span_id is None

    # Reference unused names for mypy strict
    _ = (
        ApprovalDecision,
        ApprovalRequest,
        CacheBreakpoint,
        ChatRequest,
        ChatResponse,
        ConcurrencyPolicy,
        ContentBlock,
        DurableState,
        HITLPolicy,
        LoopState,
        MemoryHint,
        MetricEvent,
        PromptArtifact,
        StateVersion,
        SubagentBudget,
        SubagentResult,
        TokenUsage,
        ToolAnnotations,
        ToolCall,
        ToolResult,
        ToolSpec,
        TransientState,
        VerificationResult,
    )


@pytest.mark.unit
def test_chat_client_abc_importable() -> None:
    """ChatClient ABC is in adapters/_base/ — single LLM interface for all categories."""
    from adapters._base import ChatClient, ModelInfo, PricingInfo, StreamEvent

    # ABC, can't instantiate
    with pytest.raises(TypeError):
        ChatClient()  # type: ignore[abstract]

    # Value classes constructible
    info = ModelInfo(
        model_name="test",
        model_family="test",
        provider="test",
        context_window=1000,
        max_output_tokens=100,
    )
    assert info.model_name == "test"

    pricing = PricingInfo(input_per_million=1.0, output_per_million=2.0)
    assert pricing.currency == "USD"

    event = StreamEvent(event_type="content_delta", payload={"text": "hi"})
    assert event.event_type == "content_delta"


@pytest.mark.unit
def test_no_llm_sdk_imports_in_agent_harness() -> None:
    """LLM-provider-neutrality: agent_harness/** must not import openai/anthropic/agent_framework."""
    import re
    from pathlib import Path

    repo_root = Path(__file__).parent.parent.parent  # backend/
    agent_harness_dir = repo_root / "src" / "agent_harness"
    assert agent_harness_dir.exists()

    forbidden = re.compile(
        r"^(from |import )(openai|anthropic|agent_framework)\b", re.MULTILINE
    )
    leaks = []
    for py_file in agent_harness_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if forbidden.search(text):
            leaks.append(str(py_file))

    assert not leaks, f"Forbidden LLM SDK imports found in agent_harness: {leaks}"
