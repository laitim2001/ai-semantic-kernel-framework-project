"""Tests for LLMRouteStep (Step 6) and Dispatch module."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.orchestration.dispatch.executors.swarm import SwarmExecutor
from src.integrations.orchestration.dispatch.executors.workflow import WorkflowExecutor
from src.integrations.orchestration.dispatch.models import (
    AgentResult,
    DispatchRequest,
    DispatchResult,
    ExecutionRoute,
)
from src.integrations.orchestration.dispatch.service import DispatchService
from src.integrations.orchestration.pipeline.context import PipelineContext
from src.integrations.orchestration.pipeline.steps.step6_llm_route import (
    LLMRouteStep,
)


# --- Mock data classes ---

class MockIntentCategory(Enum):
    QUERY = "query"
    INCIDENT = "incident"
    CHANGE = "change"


class MockRiskLevel(Enum):
    LOW = "low"
    HIGH = "high"


@dataclass
class MockRoutingDecision:
    intent_category: MockIntentCategory = MockIntentCategory.QUERY
    sub_intent: Optional[str] = "status_check"
    confidence: float = 0.92
    routing_layer: str = "pattern"

    def to_dict(self):
        return {"intent_category": self.intent_category.value}


@dataclass
class MockRiskAssessment:
    level: MockRiskLevel = MockRiskLevel.LOW
    score: float = 0.2
    requires_approval: bool = False

    def to_dict(self):
        return {"level": self.level.value}


# === LLMRouteStep Tests ===

class TestLLMRouteStep:
    """Tests for Step 6: LLM Route Decision."""

    def _make_context(self) -> PipelineContext:
        ctx = PipelineContext(
            user_id="test-user",
            session_id="test-session",
            task="Check VPN connectivity for Taipei office",
            memory_text="User is IT admin in Taipei",
            knowledge_text="VPN: connect to vpn.company.com",
        )
        ctx.routing_decision = MockRoutingDecision()
        ctx.risk_assessment = MockRiskAssessment()
        return ctx

    def test_step_properties(self):
        step = LLMRouteStep()
        assert step.name == "llm_route_decision"
        assert step.step_index == 5

    def test_extract_route_direct_answer(self):
        route, reasoning = LLMRouteStep._extract_route(
            "I'll select direct_answer because this is a simple status check."
        )
        assert route == "direct_answer"

    def test_extract_route_team(self):
        route, reasoning = LLMRouteStep._extract_route(
            "This requires team collaboration for investigation."
        )
        assert route == "team"

    def test_extract_route_subagent(self):
        route, reasoning = LLMRouteStep._extract_route(
            "Using subagent mode to check 3 systems in parallel."
        )
        assert route == "subagent"

    def test_extract_route_default(self):
        route, reasoning = LLMRouteStep._extract_route(
            "I don't know what to do."
        )
        assert route == "team"  # default

    def test_extract_route_with_reasoning(self):
        route, reasoning = LLMRouteStep._extract_route(
            "Route: direct_answer. Reason: Simple factual query."
        )
        assert route == "direct_answer"
        assert "reason" in reasoning.lower()

    def test_build_prompt_includes_all_context(self):
        step = LLMRouteStep()
        ctx = self._make_context()

        prompt = step._build_prompt(ctx)

        assert "Check VPN" in prompt
        assert "IT admin" in prompt
        assert "vpn.company.com" in prompt
        assert "query" in prompt.lower()
        assert "low" in prompt.lower()

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        """LLM failure defaults to 'team' route."""
        step = LLMRouteStep()

        # Mock _call_llm to fail
        with patch.object(
            step, "_call_llm", side_effect=ConnectionError("LLM down")
        ):
            ctx = self._make_context()
            result = await step._execute(ctx)

        assert result.selected_route == "team"
        assert "Fallback" in result.route_reasoning


# === ExecutionRoute Tests ===

class TestExecutionRoute:

    def test_from_string_valid(self):
        assert ExecutionRoute.from_string("direct_answer") == ExecutionRoute.DIRECT_ANSWER
        assert ExecutionRoute.from_string("subagent") == ExecutionRoute.SUBAGENT
        assert ExecutionRoute.from_string("team") == ExecutionRoute.TEAM

    def test_from_string_invalid_defaults_to_team(self):
        assert ExecutionRoute.from_string("invalid") == ExecutionRoute.TEAM


# === DispatchModels Tests ===

class TestDispatchModels:

    def test_dispatch_request_creation(self):
        req = DispatchRequest(
            route=ExecutionRoute.DIRECT_ANSWER,
            task="What is our VPN status?",
            user_id="u1",
            session_id="s1",
        )
        assert req.route == ExecutionRoute.DIRECT_ANSWER
        assert req.task == "What is our VPN status?"

    def test_agent_result_creation(self):
        r = AgentResult(agent_name="Agent-1", output="VPN is up", duration_ms=150)
        assert r.agent_name == "Agent-1"
        assert r.status == "completed"

    def test_dispatch_result_to_dict(self):
        result = DispatchResult(
            route=ExecutionRoute.TEAM,
            response_text="Investigation complete",
            agent_results=[
                AgentResult(agent_name="A1", output="finding 1"),
                AgentResult(agent_name="A2", output="finding 2"),
            ],
            synthesis="Combined findings",
            duration_ms=2500,
            status="completed",
        )
        d = result.to_dict()
        assert d["route"] == "team"
        assert d["agent_count"] == 2
        assert d["status"] == "completed"


# === Stub Executor Tests ===

class TestStubExecutors:

    @pytest.mark.asyncio
    async def test_swarm_returns_not_implemented(self):
        executor = SwarmExecutor()
        req = DispatchRequest(
            route=ExecutionRoute.SWARM,
            task="Investigate outage",
            user_id="u1",
            session_id="s1",
        )
        result = await executor.execute(req)
        assert result.status == "not_implemented"
        assert "Phase 46" in result.response_text

    @pytest.mark.asyncio
    async def test_workflow_returns_not_implemented(self):
        executor = WorkflowExecutor()
        req = DispatchRequest(
            route=ExecutionRoute.WORKFLOW,
            task="Deploy v2.0",
            user_id="u1",
            session_id="s1",
        )
        result = await executor.execute(req)
        assert result.status == "not_implemented"
        assert "Phase 46" in result.response_text


# === DispatchService Tests ===

class TestDispatchService:

    @pytest.mark.asyncio
    async def test_dispatches_to_correct_executor(self):
        """Service routes to the registered executor."""
        mock_executor = AsyncMock()
        mock_executor.name = "mock"
        mock_executor.execute = AsyncMock(
            return_value=DispatchResult(
                route=ExecutionRoute.DIRECT_ANSWER,
                response_text="mock result",
                status="completed",
            )
        )

        svc = DispatchService()
        svc.register_executor(ExecutionRoute.DIRECT_ANSWER, mock_executor)

        req = DispatchRequest(
            route=ExecutionRoute.DIRECT_ANSWER,
            task="test",
            user_id="u1",
            session_id="s1",
        )
        result = await svc.dispatch(req)

        assert result.response_text == "mock result"
        mock_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_route_returns_failed(self):
        """Service handles unregistered routes gracefully."""
        svc = DispatchService()
        # Remove all executors
        svc._executors.clear()

        req = DispatchRequest(
            route=ExecutionRoute.DIRECT_ANSWER,
            task="test",
            user_id="u1",
            session_id="s1",
        )
        result = await svc.dispatch(req)

        assert result.status == "failed"
        assert "No executor" in result.response_text

    @pytest.mark.asyncio
    async def test_emits_dispatch_start_event(self):
        """Service emits DISPATCH_START SSE event."""
        mock_executor = AsyncMock()
        mock_executor.name = "mock"
        mock_executor.execute = AsyncMock(
            return_value=DispatchResult(
                route=ExecutionRoute.TEAM,
                response_text="done",
                status="completed",
            )
        )

        svc = DispatchService()
        svc.register_executor(ExecutionRoute.TEAM, mock_executor)

        queue: asyncio.Queue = asyncio.Queue()
        req = DispatchRequest(
            route=ExecutionRoute.TEAM,
            task="test",
            user_id="u1",
            session_id="s1",
        )
        await svc.dispatch(req, event_queue=queue)

        events = []
        while not queue.empty():
            events.append(await queue.get())

        assert any(e.event_type.value == "DISPATCH_START" for e in events)

    def test_default_executors_registered(self):
        """Service has all 5 default executors."""
        svc = DispatchService()
        assert len(svc._executors) == 5
        assert ExecutionRoute.DIRECT_ANSWER in svc._executors
        assert ExecutionRoute.SUBAGENT in svc._executors
        assert ExecutionRoute.TEAM in svc._executors
        assert ExecutionRoute.SWARM in svc._executors
        assert ExecutionRoute.WORKFLOW in svc._executors
