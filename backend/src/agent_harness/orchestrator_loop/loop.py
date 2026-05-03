"""
File: backend/src/agent_harness/orchestrator_loop/loop.py
Purpose: Cat 1 concrete AgentLoop — TAO/ReAct main loop (while-true driven).
Category: 範疇 1 (Orchestrator Loop)
Scope: Phase 50 / Sprint 50.1 (Day 2.2)

Description:
    Concrete `AgentLoopImpl(AgentLoop)` implementing the Think-Act-Observe
    cycle. This is the V2 cure for AP-1 (Pipeline disguised as Loop): the
    iteration is `while True` driven by `StopReason` / 4 termination
    conditions, NOT a fixed-step `for step in steps:` pipeline.

    Per-turn flow:
        1. Check 3 pre-LLM terminators (max_turns / token_budget / cancellation)
        2. Build ChatRequest from current messages + registered tools
        3. await chat_client.chat(request) — provider-neutral via adapter
        4. Update tokens_used from response.usage
        5. parser.parse(response) → ParsedOutput
        6. yield Thinking(text=parsed.text)
        7. Check stop_reason terminator (END_TURN exit)
        8. classify_output(response) → branch:
             - FINAL    → yield LoopCompleted(end_turn) + return
             - HANDOFF  → yield LoopCompleted(handoff_not_implemented) + return  [Cat 11 stub]
             - TOOL_USE → for each tool_call:
                              yield ToolCallRequested
                              await tool_executor.execute(tc)
                              append Message(role="tool", tool_call_id=tc.id, content=...)
                          turn_count += 1; continue
        9. Cancellation: asyncio.CancelledError caught at chat() / execute()
           boundary → yield LoopCompleted(cancelled) + raise.

    All cross-cat collaborators are CTOR-injected:
        - ChatClient (adapter; provider-neutral)
        - OutputParser (Cat 6; Day 1)
        - ToolExecutor (Cat 2; Day 3 InMemory impl, real impl Phase 51.1)
        - ToolRegistry (Cat 2; Day 3 InMemory impl)
        - Tracer (Cat 12; NoOpTracer fallback)

    System prompt + token budget + max_turns are CTOR-configured (per-Loop)
    rather than per-`run()` because the 49.1 ABC sig only allows
    (session_id, user_input, trace_context). Phase 53.1+ State Mgmt may
    revisit if per-run override is needed.

Created: 2026-04-30 (Sprint 50.1 Day 2.2)
Last Modified: 2026-05-01

Modification History (newest-first):
    - 2026-05-02: Cat 7 State Mgmt integration (Sprint 53.1 Day 3) — optional
        ctor kwargs `reducer`, `checkpointer`, `tenant_id`. When all three
        provided, AgentLoopImpl builds an internal LoopState snapshot at
        each safe point (post-LLM, post-tool) and emits StateCheckpointed
        events with monotonic DB chain version. tenant_id ctor kwarg also
        supersedes the prior `tenant_id=session_id` placeholder in
        compactor + prompt_builder LoopState building blocks (lines marked
        "Phase 53.1 wires real tenant"). Backward-compat: when reducer /
        checkpointer / tenant_id are None, behavior is identical to 52.x
        baseline (51.x integration tests stay green). Full sole-mutator
        refactor (every messages.append → reducer.merge) is deferred to
        Phase 54.x — see Sprint 53.1 retrospective Audit Debt.
    - 2026-05-01: Inject Cat 5 PromptBuilder (Sprint 52.2 Day 3.1) — optional
        ctor kwarg `prompt_builder: PromptBuilder | None = None`. When set,
        per-turn (post-compaction) call build() to rebuild chat() messages
        and forward artifact.cache_breakpoints to ChatClient.chat (already
        a 51.1 ABC kwarg). Emit PromptBuilt with full payload (messages_count
        / estimated_input_tokens / cache_breakpoints_count / memory_layers_used
        / position_strategy_used / duration_ms). When None, falls back to
        50.x baseline messages → backward-compat preserved (50.x tests intact).
    - 2026-04-30: Yield 5 additional LoopEvents per turn (Sprint 50.2 Day 2.4):
        TurnStarted at top of while → LLMRequested before chat() → LLMResponded
        after parse (canonical SSE llm_response carrier) → ToolCallExecuted
        (success) / ToolCallFailed (error) per tool call. Thinking emit retained
        for 50.1 test backward compat. Event sequence now Cat 1+2+6 cooperate.
    - 2026-04-30: Switch ToolExecutor/ToolRegistry import to public path
        `agent_harness.tools` (Sprint 50.2 Day 1.5) — clears
        check_cross_category_import lint warning per category-boundaries.md
        (re-export already in tools/__init__.py since 50.1).
    - 2026-04-30: Initial creation (Sprint 50.1 Day 2.2) — while-true main
        loop + 4 termination conditions + 3-way dispatch + cancellation safety.

Related:
    - ._abc (AgentLoop ABC; 49.1)
    - .termination (4 terminators + TerminationReason)
    - 01-eleven-categories-spec.md §範疇 1 (TAO loop spec)
    - 04-anti-patterns.md AP-1 (must use while, not for-step)
    - 17-cross-category-interfaces.md §4.1 (LoopEvent emit ownership)
"""

from __future__ import annotations

import asyncio
import time

# Local import to avoid circular: only used at runtime for state placeholders
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

# Need imports from sibling adapter / tools / output_parser modules:
from adapters._base.chat_client import ChatClient
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    ContentBlock,
    ContextCompacted,
    DurableState,
    ExecutionContext,
    LLMRequested,
    LLMResponded,
    LoopCompleted,
    LoopEvent,
    LoopStarted,
    LoopState,
    LoopTerminated,
    Message,
    PromptBuilt,
    SpanCategory,
    StateCheckpointed,
    StateVersion,
    Thinking,
    ToolCallExecuted,
    ToolCallFailed,
    ToolCallRequested,
    TraceContext,
    TransientState,
    TurnStarted,
)
from agent_harness.context_mgmt import Compactor
from agent_harness.error_handling import (
    DefaultCircuitBreaker,
    DefaultErrorTerminator,
    ErrorClass,
    ErrorPolicy,
    RetryPolicyMatrix,
    TenantErrorBudget,
)
from agent_harness.error_handling import TerminationReason as Cat8TerminationReason
from agent_harness.observability import NoOpTracer, Tracer
from agent_harness.output_parser import OutputParser, OutputType, classify_output
from agent_harness.prompt_builder import PromptBuilder
from agent_harness.state_mgmt import Checkpointer, Reducer
from agent_harness.tools import ToolExecutor, ToolRegistry  # public path per category-boundaries.md

from ._abc import AgentLoop
from .termination import (
    TerminationReason,
    should_terminate_by_cancellation,
    should_terminate_by_stop_reason,
    should_terminate_by_tokens,
    should_terminate_by_turns,
)


class AgentLoopImpl(AgentLoop):
    """Concrete TAO/ReAct loop. While-true driven, StopReason-terminated."""

    def __init__(
        self,
        *,
        chat_client: ChatClient,
        output_parser: OutputParser,
        tool_executor: ToolExecutor,
        tool_registry: ToolRegistry,
        system_prompt: str = "",
        max_turns: int = 50,
        token_budget: int = 100_000,
        tracer: Tracer | None = None,
        compactor: Compactor | None = None,
        prompt_builder: PromptBuilder | None = None,
        reducer: Reducer | None = None,
        checkpointer: Checkpointer | None = None,
        tenant_id: UUID | None = None,
        error_policy: ErrorPolicy | None = None,
        retry_policy: RetryPolicyMatrix | None = None,
        circuit_breaker: DefaultCircuitBreaker | None = None,
        error_budget: TenantErrorBudget | None = None,
        error_terminator: DefaultErrorTerminator | None = None,
    ) -> None:
        self._chat_client = chat_client
        self._output_parser = output_parser
        self._tool_executor = tool_executor
        self._tool_registry = tool_registry
        self._system_prompt = system_prompt
        self._max_turns = max_turns
        self._token_budget = token_budget
        self._tracer = tracer or NoOpTracer()
        # 52.1 Day 2.7: compactor is OPTIONAL for backward-compat with 50.x callers.
        # When None, compaction step is a no-op; pre-existing tests stay green.
        self._compactor = compactor
        # 52.2 Day 3.1: prompt_builder is OPTIONAL for 50.x backward-compat.
        # When None, per-turn LLM call uses raw `messages` (50.x baseline).
        # When set, Cat 5 build() runs each turn, replacing chat()'s messages
        # with artifact.messages and forwarding artifact.cache_breakpoints to
        # the adapter (Anthropic cache_control / OpenAI prompt_cache_key).
        self._prompt_builder = prompt_builder
        # 53.1 Day 3 Cat 7 integration: Reducer + Checkpointer + tenant_id are
        # OPTIONAL. When all three provided, AgentLoopImpl persists a state
        # snapshot at each safe point (post-LLM, post-tool) via reducer.merge
        # → checkpointer.save → emit StateCheckpointed. When any is None,
        # the integration is no-op (preserves 51.x baseline). tenant_id
        # also fixes the prior `tenant_id=session_id` placeholder in the
        # compactor + prompt_builder LoopState building blocks.
        self._reducer = reducer
        self._checkpointer = checkpointer
        self._tenant_id = tenant_id
        # 53.2 Day 3 Cat 8 integration: 5 opt-in deps. When any is None
        # the corresponding Cat 8 path is skipped (preserves 53.1
        # baseline). Day 4 wires `_handle_tool_error` into the main tool
        # execution path. Until then the helper exists but is unused —
        # explicitly opt-in via constructor.
        self._error_policy = error_policy
        self._retry_policy = retry_policy
        self._circuit_breaker = circuit_breaker
        self._error_budget = error_budget
        self._error_terminator = error_terminator

    async def _handle_tool_error(
        self,
        *,
        error: BaseException,
        tool_name: str,
        attempt_num: int,
        state_version: int | None,
        trace_context: TraceContext,
    ) -> tuple[bool, ErrorClass | None, Cat8TerminationReason | None, str | None]:
        """Cat 8 chain: classify → record budget → check terminator.

        Day 3 helper (Day 4 wires into main loop). Returns:
            (should_terminate, error_class, termination_reason, detail)

        When Cat 8 deps are None, returns (False, None, None, None) — caller
        re-raises (preserves 53.1 behavior).
        """
        if self._error_policy is None:
            return False, None, None, None

        from agent_harness._contracts.errors import ErrorContext

        # 1. Classify
        cls = self._error_policy.classify(error)

        # 2. Record budget (skip FATAL — bug, not tenant-attributable)
        if self._error_budget is not None and self._tenant_id is not None:
            await self._error_budget.record(self._tenant_id, cls)

        # 3. Check terminator
        if self._error_terminator is not None and self._tenant_id is not None:
            decision = await self._error_terminator.evaluate(
                error=error,
                error_class=cls,
                context=ErrorContext(
                    source_category="tools",
                    tool_name=tool_name,
                    attempt_num=attempt_num,
                    state_version=state_version,
                    tenant_id=self._tenant_id,
                ),
                tenant_id=self._tenant_id,
            )
            if decision.terminate:
                return True, cls, decision.reason, decision.detail

        return False, cls, None, None

    async def run(
        self,
        *,
        session_id: UUID,
        user_input: str,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[LoopEvent]:
        """TAO main loop. Yields LoopEvent stream until terminated."""
        ctx = trace_context or TraceContext.create_root()
        messages: list[Message] = []
        if self._system_prompt:
            messages.append(Message(role="system", content=self._system_prompt))
        messages.append(Message(role="user", content=user_input))

        turn_count = 0
        tokens_used = 0

        async with self._tracer.start_span(
            name="agent_loop.run",
            category=SpanCategory.ORCHESTRATOR,
            trace_context=ctx,
        ):
            yield LoopStarted(session_id=session_id, trace_context=ctx)

            while True:
                # === Pre-LLM termination checks ============================
                if should_terminate_by_turns(turn_count, self._max_turns):
                    yield LoopCompleted(
                        stop_reason=TerminationReason.MAX_TURNS.value,
                        total_turns=turn_count,
                        trace_context=ctx,
                    )
                    return
                if should_terminate_by_tokens(tokens_used, self._token_budget):
                    yield LoopCompleted(
                        stop_reason=TerminationReason.TOKEN_BUDGET.value,
                        total_turns=turn_count,
                        trace_context=ctx,
                    )
                    return
                if should_terminate_by_cancellation():
                    yield LoopCompleted(
                        stop_reason=TerminationReason.CANCELLED.value,
                        total_turns=turn_count,
                        trace_context=ctx,
                    )
                    return

                # === Compaction check (Sprint 52.1 Day 2.7) =================
                # Cat 4 Compactor: Pre-LLM context compaction. Optional injection
                # — when None, this is a no-op (50.x backward compat).
                if self._compactor is not None:
                    compact_state = LoopState(
                        transient=TransientState(
                            messages=list(messages),
                            current_turn=turn_count,
                            token_usage_so_far=tokens_used,
                        ),
                        durable=DurableState(
                            session_id=session_id,
                            # 53.1: real tenant when ctor-injected; else session_id fallback
                            tenant_id=self._tenant_id or session_id,
                        ),
                        version=StateVersion(
                            version=turn_count,
                            parent_version=turn_count - 1 if turn_count > 0 else None,
                            created_at=datetime.now(),
                            created_by_category="orchestrator_loop",
                        ),
                    )
                    compaction_result = await self._compactor.compact_if_needed(
                        compact_state, trace_context=ctx
                    )
                    if (
                        compaction_result.triggered
                        and compaction_result.compacted_state is not None
                    ):
                        messages = list(compaction_result.compacted_state.transient.messages)
                        tokens_used = compaction_result.tokens_after
                        strategy_label = (
                            compaction_result.strategy_used.value
                            if compaction_result.strategy_used is not None
                            else "unknown"
                        )
                        yield ContextCompacted(
                            tokens_before=compaction_result.tokens_before,
                            tokens_after=compaction_result.tokens_after,
                            compaction_strategy=strategy_label,
                            messages_compacted=compaction_result.messages_compacted,
                            duration_ms=compaction_result.duration_ms,
                            trace_context=ctx,
                        )

                # === Per-turn marker (Sprint 50.2) ==========================
                yield TurnStarted(turn_num=turn_count, trace_context=ctx)

                # === Cat 5 PromptBuilder (Sprint 52.2 Day 3.1) ==============
                # When prompt_builder is injected, build a per-turn artifact
                # replacing the raw `messages` list at LLM call time. Conversation
                # accumulator (`messages`) continues to grow with assistant + tool
                # messages — only the chat() input is rebuilt each turn.
                # When None, falls back to 50.x baseline (raw messages, no cache).
                chat_messages: list[Message] = messages
                cache_breakpoints: list[CacheBreakpoint] | None = None
                if self._prompt_builder is not None:
                    build_state = LoopState(
                        transient=TransientState(
                            messages=list(messages),
                            current_turn=turn_count,
                            token_usage_so_far=tokens_used,
                        ),
                        durable=DurableState(
                            session_id=session_id,
                            # 53.1: real tenant when ctor-injected; else session_id fallback
                            tenant_id=self._tenant_id or session_id,
                        ),
                        version=StateVersion(
                            version=turn_count,
                            parent_version=turn_count - 1 if turn_count > 0 else None,
                            created_at=datetime.now(),
                            created_by_category="orchestrator_loop",
                        ),
                    )
                    t0 = time.perf_counter()
                    artifact = await self._prompt_builder.build(
                        state=build_state,
                        tenant_id=self._tenant_id or session_id,  # 53.1: real tenant when set
                        user_id=None,
                        tools=self._tool_registry.list(),
                        trace_context=ctx,
                    )
                    duration_ms = (time.perf_counter() - t0) * 1000.0
                    chat_messages = list(artifact.messages)
                    cache_breakpoints = (
                        list(artifact.cache_breakpoints) if artifact.cache_breakpoints else None
                    )
                    layers_used = artifact.layer_metadata.get("memory_layers_used", [])
                    strategy_used = artifact.layer_metadata.get("position_strategy", "")
                    yield PromptBuilt(
                        messages_count=len(artifact.messages),
                        estimated_input_tokens=artifact.estimated_input_tokens,
                        cache_breakpoints_count=len(artifact.cache_breakpoints),
                        memory_layers_used=(
                            tuple(layers_used) if isinstance(layers_used, (list, tuple)) else ()
                        ),
                        position_strategy_used=str(strategy_used),
                        duration_ms=duration_ms,
                        trace_context=ctx,
                    )

                # === LLM call ===============================================
                model_name = self._chat_client.model_info().model_name
                yield LLMRequested(
                    model=model_name,
                    tokens_in=0,  # Phase 52.1 wires count_tokens()
                    trace_context=ctx,
                )
                try:
                    request = ChatRequest(
                        messages=chat_messages,
                        tools=self._tool_registry.list(),
                    )
                    response: ChatResponse = await self._chat_client.chat(
                        request,
                        cache_breakpoints=cache_breakpoints,
                        trace_context=ctx,
                    )
                except asyncio.CancelledError:
                    yield LoopCompleted(
                        stop_reason=TerminationReason.CANCELLED.value,
                        total_turns=turn_count,
                        trace_context=ctx,
                    )
                    raise

                # Update token usage
                if response.usage is not None:
                    tokens_used += response.usage.total_tokens

                # === Parse + emit LLMResponded + Thinking ==================
                parsed = await self._output_parser.parse(response, trace_context=ctx)
                # 50.2: LLMResponded carries the canonical (content, tool_calls, thinking) tuple
                # per 02-architecture-design.md §SSE llm_response schema. Thinking event is kept
                # for 50.1 test backward compatibility but no longer the SSE-canonical form.
                yield LLMResponded(
                    content=parsed.text,
                    tool_calls=tuple(parsed.tool_calls),
                    thinking=None,
                    trace_context=ctx,
                )
                yield Thinking(text=parsed.text, trace_context=ctx)

                # === Cat 7 post-LLM checkpoint (53.1 Day 3) =================
                # When reducer + checkpointer + tenant_id all set, persist a
                # state snapshot after LLM response so verifier / HITL pause /
                # error recovery have a recent restore point. No-op when any
                # is None (51.x backward-compat path).
                post_llm_event = await self._emit_state_checkpoint(
                    session_id=session_id,
                    messages=messages,
                    turn_count=turn_count,
                    tokens_used=tokens_used,
                    source_category="orchestrator_loop:post_llm",
                    ctx=ctx,
                )
                if post_llm_event is not None:
                    yield post_llm_event

                # === stop_reason terminator =================================
                if should_terminate_by_stop_reason(response):
                    yield LoopCompleted(
                        stop_reason=TerminationReason.END_TURN.value,
                        total_turns=turn_count,
                        trace_context=ctx,
                    )
                    return

                # === Dispatch on OutputType =================================
                output_type = classify_output(response)

                if output_type == OutputType.FINAL:
                    yield LoopCompleted(
                        stop_reason=TerminationReason.END_TURN.value,
                        total_turns=turn_count,
                        trace_context=ctx,
                    )
                    return

                if output_type == OutputType.HANDOFF:
                    # Cat 11 not implemented yet; reserve enum for Phase 54.2.
                    yield LoopCompleted(
                        stop_reason=TerminationReason.HANDOFF_NOT_IMPLEMENTED.value,
                        total_turns=turn_count,
                        trace_context=ctx,
                    )
                    return

                # output_type == TOOL_USE
                # Append assistant message carrying the tool_calls so the
                # next chat() round-trip can correlate tool_call_id.
                messages.append(
                    Message(
                        role="assistant",
                        content=parsed.text,
                        tool_calls=parsed.tool_calls,
                    )
                )

                for tc in parsed.tool_calls:
                    yield ToolCallRequested(
                        tool_call_id=tc.id,
                        tool_name=tc.name,
                        arguments=tc.arguments,
                        trace_context=ctx,
                    )
                    try:
                        # Sprint 52.5 P0 #18: build ExecutionContext from
                        # trace_context so memory_tools (and future scoped
                        # tools) get server-authoritative tenant_id /
                        # user_id / session_id instead of trusting LLM args.
                        exec_ctx = ExecutionContext(
                            tenant_id=ctx.tenant_id,
                            user_id=ctx.user_id,
                            session_id=ctx.session_id or session_id,
                        )
                        result = await self._tool_executor.execute(
                            tc, trace_context=ctx, context=exec_ctx
                        )
                    except asyncio.CancelledError:
                        yield LoopCompleted(
                            stop_reason=TerminationReason.CANCELLED.value,
                            total_turns=turn_count,
                            trace_context=ctx,
                        )
                        raise
                    except Exception as exc:
                        # 53.2 Day 4 Cat 8 chain: classify → record budget →
                        # check terminator. When Cat 8 deps None → re-raise
                        # (preserves 53.1 baseline).
                        terminate, _err_class, term_reason, term_detail = (
                            await self._handle_tool_error(
                                error=exc,
                                tool_name=tc.name,
                                attempt_num=1,
                                state_version=None,
                                trace_context=ctx,
                            )
                        )
                        if self._error_policy is None:
                            # Opt-out path: no Cat 8 deps → preserve 53.1 raise behavior
                            raise
                        if terminate:
                            yield LoopTerminated(
                                reason=(term_reason.value if term_reason is not None else ""),
                                detail=term_detail,
                                last_state_version=None,
                                trace_context=ctx,
                            )
                            return
                        # Synthesize LLM-recoverable error ToolResult so the
                        # LLM sees the failure on next turn and can self-correct
                        # (Cat 8 §LLM-recoverable; Anthropic / LangGraph pattern).
                        from agent_harness._contracts import ToolResult

                        result = ToolResult(
                            tool_call_id=tc.id,
                            tool_name=tc.name,
                            content=f"Error: {exc!r}. Please adjust your approach.",
                            success=False,
                            error=repr(exc),
                            duration_ms=0.0,
                        )

                    # 53.2 Day 4 Cat 8 chain on soft failure: ToolExecutorImpl
                    # catches handler exceptions internally → ToolResult(success=
                    # False). Reconstruct a synthetic exception so the Cat 8
                    # chain can classify + check terminator. When deps None →
                    # fall through to existing 53.1 baseline (LLM-recoverable
                    # via tool message).
                    if not result.success and self._error_policy is not None:
                        synthetic = Exception(result.error or "tool soft failure")
                        terminate, _err_class, term_reason, term_detail = (
                            await self._handle_tool_error(
                                error=synthetic,
                                tool_name=tc.name,
                                attempt_num=1,
                                state_version=None,
                                trace_context=ctx,
                            )
                        )
                        if terminate:
                            yield LoopTerminated(
                                reason=(term_reason.value if term_reason is not None else ""),
                                detail=term_detail,
                                last_state_version=None,
                                trace_context=ctx,
                            )
                            return

                    # Feed back as tool message — KEY V2 cure for AP-1.
                    tool_content = self._tool_result_to_text(result.content)

                    # 50.2: emit Cat 2-owned completion event so SSE / frontend
                    # see tool result text + success/failure.
                    if result.success:
                        yield ToolCallExecuted(
                            tool_call_id=tc.id,
                            tool_name=tc.name,
                            duration_ms=result.duration_ms or 0.0,
                            result_content=tool_content,
                            trace_context=ctx,
                        )
                    else:
                        yield ToolCallFailed(
                            tool_call_id=tc.id,
                            tool_name=tc.name,
                            error=result.error or "unknown tool error",
                            trace_context=ctx,
                        )

                    messages.append(
                        Message(
                            role="tool",
                            content=tool_content,
                            tool_call_id=tc.id,
                        )
                    )

                # === Cat 7 post-tool checkpoint (53.1 Day 3) ================
                # After all tool results are appended for this turn, persist
                # a snapshot so HITL pause / replay can resume from
                # complete-tool-batch boundary. No-op when not configured.
                post_tool_event = await self._emit_state_checkpoint(
                    session_id=session_id,
                    messages=messages,
                    turn_count=turn_count,
                    tokens_used=tokens_used,
                    source_category="orchestrator_loop:post_tool",
                    ctx=ctx,
                )
                if post_tool_event is not None:
                    yield post_tool_event

                turn_count += 1
                # loop continues to next while iteration

    async def resume(
        self,
        *,
        state: LoopState,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[LoopEvent]:
        """Resume from checkpointed state.

        50.1 Day 2 stub — full implementation in Phase 53.1 when
        Checkpointer + State Mgmt land. Until then, calling resume()
        yields a single LoopCompleted with reason=ERROR and a clear
        message rather than silently breaking.
        """
        yield LoopCompleted(
            stop_reason=TerminationReason.ERROR.value,
            total_turns=0,
            trace_context=trace_context,
        )

    async def _emit_state_checkpoint(
        self,
        *,
        session_id: UUID,
        messages: list[Message],
        turn_count: int,
        tokens_used: int,
        source_category: str,
        ctx: TraceContext,
    ) -> StateCheckpointed | None:
        """Build LoopState from loop locals, reducer.merge → checkpointer.save.

        Returns StateCheckpointed event with DB chain version (caller yields).
        Returns None if reducer/checkpointer/tenant_id not all configured
        (i.e., 51.x backward-compat caller path). Errors are NOT swallowed;
        the loop should fail loud rather than silently miss a checkpoint.
        """
        if self._reducer is None or self._checkpointer is None or self._tenant_id is None:
            return None

        # Build snapshot state from current loop locals.
        snapshot_state = LoopState(
            transient=TransientState(
                messages=list(messages),
                current_turn=turn_count,
                token_usage_so_far=tokens_used,
            ),
            durable=DurableState(
                session_id=session_id,
                tenant_id=self._tenant_id,
            ),
            version=StateVersion(
                version=turn_count,
                parent_version=turn_count - 1 if turn_count > 0 else None,
                created_at=datetime.now(),
                created_by_category=source_category,
            ),
        )

        # In-memory version bump via Reducer (audit trail).
        bumped = await self._reducer.merge(
            snapshot_state,
            {"transient": {"current_turn": turn_count, "token_usage_so_far": tokens_used}},
            source_category=source_category,
            trace_context=ctx,
        )

        # Persist to DB; persisted version is from DB chain (authoritative).
        persisted = await self._checkpointer.save(bumped, trace_context=ctx)
        return StateCheckpointed(version=persisted.version, trace_context=ctx)

    @staticmethod
    def _tool_result_to_text(
        content: str | list[dict[str, object]] | list[ContentBlock],
    ) -> str:
        """Convert ToolResult.content to plain text for the next LLM round-trip.

        ToolResult.content can be `str` or `list[dict]` (per 49.1 spec).
        50.1 normalizes to str — image / json blocks left for Phase 51.1.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text_val = item.get("text") or item.get("content") or str(item)
                    parts.append(str(text_val))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)
