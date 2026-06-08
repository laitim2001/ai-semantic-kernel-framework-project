"""
File: backend/tests/integration/api/test_chat_pause_resume_e2e.py
Purpose: E2E for durable HITL pause-resume (Sprint 57.88) — ESCALATE pause →
    checkpoint → governance decide → POST /chat/{id}/resume → continuation.
Category: Tests / integration / api / Cat 7 + Cat 9 + resume orchestration
Scope: Phase 57 / Sprint 57.88 (US-5)

Description:
    Drives the full durable pause-resume vertical against real PostgreSQL:

    RUN-1 (pause): an AgentLoopImpl wired with EscalateGuardrail + hitl_deferred=True
    + a real DBCheckpointer + DefaultReducer + DefaultHITLManager. On a tool call,
    the deferred ESCALATE branch persists a paused checkpoint (pending_approval +
    resume_messages in DurableState.metadata), emits ApprovalRequested, and
    terminates with stop_reason="awaiting_approval" (no blocking wait).

    [decision] The human approves via the EXISTING governance decide endpoint
    (happy path) or the manager records REJECTED (reject path).

    RUN-2 (resume): POST /api/v1/chat/{session_id}/resume drives ResumeService →
    AgentLoopImpl.resume(): loads the paused checkpoint, rebuilds messages from
    metadata (decision B), reads the recorded decision (non-blocking get_decision),
    and on APPROVED executes the pending tool + continues to end_turn (on REJECTED
    emits GuardrailTriggered block + terminates, no tool exec).

    Single-transaction isolation (Risk Class C): the loop checkpointer, the
    HITLManager, the governance factory, and the resume endpoint's get_db_session
    override ALL share the ONE test db_session (commit monkeypatched to flush) so
    every component sees the same uncommitted rows and the fixture rolls back at
    teardown. The resume endpoint's get_db_session is overridden so the new DB
    call lands on the test session (NOT a fresh pooled session — avoids the
    asyncpg cross-loop leak / FK-miss the autouse fixture would otherwise hit).

Created: 2026-06-08 (Sprint 57.88 Day 2 — US-5)

Related:
    - agent_harness/orchestrator_loop/loop.py (deferred pause + resume())
    - platform_layer/resume/service.py (ResumeService)
    - api/v1/chat/router.py (POST /chat/{id}/resume + get_resume_service)
    - governance/test_stage3_escalation_e2e.py (EscalateGuardrail pattern)
    - governance/test_hitl_centralization.py (single-session manager pattern)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters._base.chat_client import ChatClient
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo, StopReason, StreamEvent
from agent_harness._contracts import (
    ApprovalRequested,
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    ExecutionContext,
    LoopCompleted,
    LoopEvent,
    Message,
    TokenUsage,
    ToolCall,
    ToolSpec,
    TraceContext,
)
from agent_harness.guardrails._abc import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
)
from agent_harness.guardrails.engine import GuardrailEngine
from agent_harness.orchestrator_loop.loop import AgentLoopImpl
from agent_harness.output_parser import OutputParserImpl
from agent_harness.state_mgmt import DBCheckpointer, DefaultReducer
from agent_harness.tools import ToolExecutorImpl, ToolRegistryImpl
from infrastructure.db.models import StateSnapshot
from infrastructure.db.models.sessions import Session as SessionModel
from platform_layer.governance.hitl.manager import DefaultHITLManager
from platform_layer.governance.hitl.notifier import NoopNotifier
from platform_layer.resume import PAUSE_CHECKPOINT_REASON, ResumeService

pytestmark = pytest.mark.asyncio


# === Deterministic ESCALATE guardrail (mirrors test_stage3_escalation_e2e) ===


class EscalateGuardrail(Guardrail):
    """Always escalates tool calls — deterministically triggers the deferred pause."""

    guardrail_type = GuardrailType.TOOL

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        return GuardrailResult(
            action=GuardrailAction.ESCALATE,
            reason="policy escalation (test)",
            risk_level="HIGH",
        )


# === Scripted ChatClient (mirrors test_stage3_escalation_e2e FakeChatClient) ==


class FakeChatClient(ChatClient):
    """Returns canned (text, tool_calls?, stop_reason) tuples per chat() call."""

    def __init__(self, responses: list[tuple[str, list[ToolCall] | None, StopReason]]) -> None:
        self._responses = responses
        self._idx = 0

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        if self._idx >= len(self._responses):
            raise RuntimeError("Loop ran more turns than fake responses")
        text, tool_calls, stop = self._responses[self._idx]
        self._idx += 1
        return ChatResponse(
            model="fake",
            content=text,
            tool_calls=tool_calls,
            stop_reason=stop,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1),
        )

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        return self._dummy()

    async def _dummy(self) -> AsyncIterator[StreamEvent]:
        if False:
            yield  # type: ignore[unreachable]

    async def count_tokens(
        self, *, messages: list[Message], tools: list[ToolSpec] | None = None
    ) -> int:
        return 1

    def get_pricing(self) -> PricingInfo:
        return MagicMock(spec=PricingInfo)

    def supports_feature(
        self,
        feature: Literal[
            "thinking",
            "caching",
            "vision",
            "audio",
            "computer_use",
            "structured_output",
            "parallel_tool_calls",
        ],
    ) -> bool:
        return False

    def model_info(self) -> ModelInfo:
        return ModelInfo(
            model_name="fake",
            model_family="fake",
            provider="fake",
            context_window=8192,
            max_output_tokens=4096,
        )


# === Shared-session test rig =================================================


class _LoopRig:
    """Holds the shared collaborators so RUN-1 (pause) and RUN-2 (resume) reuse
    the SAME executor / registry / hitl_manager / checkpointer / reducer."""

    def __init__(
        self,
        *,
        registry: ToolRegistryImpl,
        executor: ToolExecutorImpl,
        manager: DefaultHITLManager,
        checkpointer: DBCheckpointer,
        reducer: DefaultReducer,
        tenant_id: UUID,
    ) -> None:
        self.registry = registry
        self.executor = executor
        self.manager = manager
        self.checkpointer = checkpointer
        self.reducer = reducer
        self.tenant_id = tenant_id
        self.tool_executed = False

    def make_loop(self, chat_client: ChatClient) -> AgentLoopImpl:
        engine = GuardrailEngine()
        engine.register(EscalateGuardrail(), priority=10)
        return AgentLoopImpl(
            chat_client=chat_client,
            output_parser=OutputParserImpl(),
            tool_executor=self.executor,
            tool_registry=self.registry,
            guardrail_engine=engine,
            tenant_id=self.tenant_id,
            hitl_manager=self.manager,
            hitl_timeout_s=10,
            hitl_deferred=True,  # 57.88: the chat-path deferred pause-resume mode
            reducer=self.reducer,
            checkpointer=self.checkpointer,
        )


@pytest_asyncio.fixture
async def rig(db_session: AsyncSession, monkeypatch) -> _LoopRig:
    """Seed tenant + user + session; build collaborators bound to ONE db_session.

    monkeypatch db_session.commit → flush so the HITLManager + checkpointer keep
    everything in the single rolled-back transaction (test_hitl_centralization
    pattern). All cross-session visibility collapses to this one session.
    """
    from tests.conftest import seed_tenant, seed_user

    tenant = await seed_tenant(db_session, code="PAUSE_RESUME")
    user = await seed_user(db_session, tenant, email="pauseresume@test.com")
    session_row = SessionModel(
        tenant_id=tenant.id, user_id=user.id, title="pause-resume", status="active"
    )
    db_session.add(session_row)
    await db_session.flush()
    await db_session.refresh(session_row)

    async def _flush_only() -> None:
        await db_session.flush()

    monkeypatch.setattr(db_session, "commit", _flush_only)

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncSession]:
        yield db_session

    manager = DefaultHITLManager(session_factory=factory, notifier=NoopNotifier().notify)

    registry = ToolRegistryImpl()
    registry.register(
        ToolSpec(
            name="sensitive_tool",
            description="tool requiring approval",
            input_schema={"type": "object", "properties": {"x": {"type": "integer"}}},
        )
    )

    rig_ref: dict[str, _LoopRig] = {}

    async def _ok(call: ToolCall, context: ExecutionContext) -> Any:
        rig_ref["rig"].tool_executed = True
        return "tool_executed_ok"

    executor = ToolExecutorImpl(registry=registry, handlers={"sensitive_tool": _ok})
    checkpointer = DBCheckpointer(db_session, session_id=session_row.id, tenant_id=tenant.id)

    rig_obj = _LoopRig(
        registry=registry,
        executor=executor,
        manager=manager,
        checkpointer=checkpointer,
        reducer=DefaultReducer(),
        tenant_id=tenant.id,
    )
    rig_ref["rig"] = rig_obj
    rig_obj.session_id = session_row.id  # type: ignore[attr-defined]
    rig_obj.user_id = user.id  # type: ignore[attr-defined]
    rig_obj.db_session = db_session  # type: ignore[attr-defined]
    return rig_obj


def _pause_chat() -> FakeChatClient:
    """Turn 1: emit a tool call (→ ESCALATE → deferred pause)."""
    return FakeChatClient(
        responses=[
            (
                "calling tool",
                [ToolCall(id="tc-1", name="sensitive_tool", arguments={"x": 42})],
                StopReason.TOOL_USE,
            ),
        ]
    )


def _resume_chat() -> FakeChatClient:
    """After the approved tool runs, the continuation LLM call ends the turn."""
    return FakeChatClient(responses=[("done", None, StopReason.END_TURN)])


async def _drive_to_pause(rig: _LoopRig) -> list[LoopEvent]:
    loop = rig.make_loop(_pause_chat())
    events: list[LoopEvent] = []
    ctx = TraceContext(
        tenant_id=rig.tenant_id,
        session_id=rig.session_id,  # type: ignore[attr-defined]
        user_id=rig.user_id,  # type: ignore[attr-defined]
    )
    async for ev in loop.run(
        session_id=rig.session_id,  # type: ignore[attr-defined]
        user_input="please call the sensitive tool",
        trace_context=ctx,
    ):
        events.append(ev)
    return events


# === Coroutine-driven endpoint drive (single test loop; Risk Class C) ========
# Why call the endpoint coroutines directly instead of via TestClient: the test
# db_session is an asyncpg connection bound to the pytest-asyncio test loop.
# TestClient runs the endpoint on its own anyio portal loop -> "Future attached
# to a different loop" on the shared asyncpg connection. Driving the endpoint
# coroutine on THIS loop keeps the connection single-loop. This still exercises
# the REAL endpoint function + ResumeService + loop.resume() + SSE serializer +
# the real governance decide endpoint; only the HTTP transport layer is bypassed
# (covered by the Stage-3 chat-v2 drive-through per the plan).


def _parse_sse(body: bytes) -> list[dict]:
    out: list[dict] = []
    for chunk in body.split(b"\n\n"):
        if not chunk.strip():
            continue
        chunk_lines = chunk.decode("utf-8").split("\n")
        event_line = next((ln for ln in chunk_lines if ln.startswith("event: ")), "")
        data_line = next((ln for ln in chunk_lines if ln.startswith("data: ")), "")
        out.append(
            {
                "type": event_line[len("event: ") :],
                "data": json.loads(data_line[len("data: ") :]) if data_line else None,
            }
        )
    return out


async def _collect_resume_sse(
    rig: _LoopRig,
    *,
    tenant_id: UUID,
    session_id: UUID,
) -> tuple[int, list[dict]]:
    """Drive the resume_chat endpoint coroutine; return (status_code, parsed_events).

    Injects a ResumeService whose build_loop reuses the rig's collaborators (so the
    pending tool runs on the SAME executor) + the rig's shared db_session.
    """
    from fastapi import HTTPException

    from api.v1.chat.router import resume_chat

    async def _build_loop(db: AsyncSession, sid: UUID, t: UUID, u: UUID) -> AgentLoopImpl:
        return rig.make_loop(_resume_chat())

    svc = ResumeService(build_loop=_build_loop)
    try:
        resp = await resume_chat(
            session_id=session_id,
            current_tenant=tenant_id,
            current_user=rig.user_id,  # type: ignore[attr-defined]
            db=rig.db_session,  # type: ignore[attr-defined]
            resume_service=svc,
        )
    except HTTPException as exc:
        return exc.status_code, []
    body = b"".join([chunk async for chunk in resp.body_iterator])  # type: ignore[union-attr]
    return resp.status_code, _parse_sse(body)


async def _decide(rig: _LoopRig, request_id: UUID, decision: str) -> None:
    """Record an approval decision via the REAL governance decide endpoint coroutine.

    Shares the rig's single db_session via a ServiceFactory bound to it (so the
    HITLManager the endpoint constructs sees the pending approval written during
    the pause). Faithful to plan section 3.8 (record a decision via the governance
    endpoint), driven as a coroutine on the test loop (Risk Class C).
    """
    from contextlib import asynccontextmanager as _acm

    from api.v1.governance.router import DecisionRequestBody, decide_approval
    from platform_layer.governance.service_factory import ServiceFactory

    @_acm
    async def _factory() -> AsyncIterator[AsyncSession]:
        yield rig.db_session  # type: ignore[attr-defined]

    svc_factory = ServiceFactory(
        session_factory=_factory,
        notification_config_path=None,
        risk_policy_config_path=None,
    )
    result = await decide_approval(
        request_id=request_id,
        body=DecisionRequestBody(decision=decision, reason=f"test {decision}"),
        current_tenant=rig.tenant_id,
        user_id=rig.user_id,  # type: ignore[attr-defined]
        factory=svc_factory,
    )
    # DecisionResponse.decision is the enum value (upper-cased, e.g. "APPROVED").
    assert result.decision.lower() == decision


def _request_id_of(events: list[LoopEvent]) -> UUID:
    rid = next(e.approval_request_id for e in events if isinstance(e, ApprovalRequested))
    assert rid is not None
    return rid


# === Tests ==================================================================


async def test_pause_persists_resumable_checkpoint(rig: _LoopRig) -> None:
    """RUN-1: deferred ESCALATE -> ApprovalRequested + awaiting_approval + checkpoint."""
    events = await _drive_to_pause(rig)

    requested = [e for e in events if isinstance(e, ApprovalRequested)]
    assert len(requested) == 1, "expected one ApprovalRequested at pause"

    completed = [e for e in events if isinstance(e, LoopCompleted)]
    assert len(completed) == 1
    assert completed[-1].stop_reason == "awaiting_approval"

    # Tool did NOT execute at pause time (it awaits approval).
    assert rig.tool_executed is False

    # A paused checkpoint persisted with pending_approval + resume_messages.
    # The loop also writes a post_llm checkpoint; the resumable one is the LATEST
    # snapshot whose reason == the pause sentinel (matching ResumeService's query).
    snapshot = (
        await rig.db_session.execute(  # type: ignore[attr-defined]
            select(StateSnapshot)
            .where(
                (StateSnapshot.session_id == rig.session_id)  # type: ignore[attr-defined]
                & (StateSnapshot.tenant_id == rig.tenant_id)
                & (StateSnapshot.reason == PAUSE_CHECKPOINT_REASON)
            )
            .order_by(StateSnapshot.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    assert snapshot is not None, "expected a hitl_pause checkpoint"
    cp = await rig.checkpointer.load(version=snapshot.version)
    pending = cp.durable.metadata.get("pending_approval")
    assert isinstance(pending, dict)
    assert pending["tool_call"]["name"] == "sensitive_tool"
    assert pending["tool_call"]["arguments"] == {"x": 42}
    assert "approval_request_id" in pending
    assert isinstance(cp.durable.metadata.get("resume_messages"), list)
    assert len(cp.durable.metadata["resume_messages"]) >= 1


async def test_resume_approved_runs_tool_and_completes(rig: _LoopRig) -> None:
    """Full happy path: pause -> governance decide(approved) -> resume -> end_turn."""
    pause_events = await _drive_to_pause(rig)
    request_id = _request_id_of(pause_events)

    # Approve via the EXISTING governance decide endpoint (sharing this session).
    await _decide(rig, request_id, "approved")

    # RUN-2: drive the resume endpoint.
    status_code, events = await _collect_resume_sse(
        rig, tenant_id=rig.tenant_id, session_id=rig.session_id  # type: ignore[attr-defined]
    )
    assert status_code == 200
    types = [e["type"] for e in events]

    # approval_received(APPROVED) -> tool executed -> loop_end(end_turn).
    received = [e for e in events if e["type"] == "approval_received"]
    assert received and received[0]["data"]["decision"] == "APPROVED"
    assert "tool_call_result" in types
    tool_result = next(e for e in events if e["type"] == "tool_call_result")
    assert tool_result["data"]["is_error"] is False
    assert "tool_executed_ok" in (tool_result["data"]["result"] or "")
    end = next(e for e in events if e["type"] == "loop_end")
    assert end["data"]["stop_reason"] == "end_turn"
    assert rig.tool_executed is True


async def test_resume_rejected_blocks_tool(rig: _LoopRig) -> None:
    """Reject path: decide(rejected) -> resume emits block + no tool exec."""
    pause_events = await _drive_to_pause(rig)
    request_id = _request_id_of(pause_events)
    await _decide(rig, request_id, "rejected")

    status_code, events = await _collect_resume_sse(
        rig, tenant_id=rig.tenant_id, session_id=rig.session_id  # type: ignore[attr-defined]
    )
    assert status_code == 200
    types = [e["type"] for e in events]

    blocks = [e for e in events if e["type"] == "guardrail_triggered"]
    assert blocks and blocks[0]["data"]["action"] == "block"
    end = next(e for e in events if e["type"] == "loop_end")
    assert end["data"]["stop_reason"] == "guardrail_blocked"
    # The pending tool must NOT have executed on reject.
    assert rig.tool_executed is False
    assert "tool_call_result" not in types


async def test_resume_cross_tenant_returns_404(rig: _LoopRig) -> None:
    """Multi-tenant rule: another tenant resuming this session -> 404 (no leak)."""
    pause_events = await _drive_to_pause(rig)
    request_id = _request_id_of(pause_events)
    await _decide(rig, request_id, "approved")

    other_tenant = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    status_code, events = await _collect_resume_sse(
        rig, tenant_id=other_tenant, session_id=rig.session_id  # type: ignore[attr-defined]
    )
    assert status_code == 404
    assert events == []
    # The approved tool must NOT have run for the foreign tenant.
    assert rig.tool_executed is False


async def test_resume_no_paused_checkpoint_returns_404(rig: _LoopRig) -> None:
    """Resuming a session with no paused checkpoint -> 404 (nothing to resume)."""
    status_code, _events = await _collect_resume_sse(
        rig, tenant_id=rig.tenant_id, session_id=uuid4()
    )
    assert status_code == 404
