"""
End-to-end pipeline integration tests.

Tests the full 8-step pipeline with mocked dependencies,
verifying 3 execution routes (direct_answer, subagent, team)
and pause/resume flows (HITL, Dialog).

Phase 45: Orchestration Core (Sprint 158)
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.orchestration.pipeline.context import PipelineContext
from src.integrations.orchestration.pipeline.exceptions import (
    DialogPauseException,
    HITLPauseException,
)
from src.integrations.orchestration.pipeline.service import (
    OrchestrationPipelineService,
    PipelineEvent,
    PipelineEventType,
)
from src.integrations.orchestration.pipeline.steps.base import PipelineStep
from src.integrations.orchestration.pipeline.steps.step1_memory import MemoryStep
from src.integrations.orchestration.pipeline.steps.step2_knowledge import KnowledgeStep
from src.integrations.orchestration.pipeline.steps.step3_intent import IntentStep
from src.integrations.orchestration.pipeline.steps.step4_risk import RiskStep
from src.integrations.orchestration.pipeline.steps.step5_hitl import HITLGateStep
from src.integrations.orchestration.pipeline.steps.step6_llm_route import LLMRouteStep
from src.integrations.orchestration.pipeline.steps.step8_postprocess import PostProcessStep
from src.integrations.orchestration.dispatch.models import (
    DispatchRequest,
    DispatchResult,
    ExecutionRoute,
    AgentResult,
)
from src.integrations.orchestration.dispatch.service import DispatchService


# --- Mock V8 data classes ---

class MockIntentCategory(Enum):
    QUERY = "query"
    INCIDENT = "incident"
    CHANGE = "change"


class MockRiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MockCompletenessInfo:
    is_complete: bool = True
    missing_fields: List[str] = field(default_factory=list)
    optional_missing: List[str] = field(default_factory=list)
    completeness_score: float = 1.0
    suggestions: List[str] = field(default_factory=list)


@dataclass
class MockRoutingDecision:
    intent_category: MockIntentCategory = MockIntentCategory.QUERY
    sub_intent: Optional[str] = "status_check"
    confidence: float = 0.95
    routing_layer: str = "pattern"
    completeness: MockCompletenessInfo = field(default_factory=MockCompletenessInfo)

    def to_dict(self):
        return {"intent_category": self.intent_category.value, "confidence": self.confidence}


@dataclass
class MockRiskAssessment:
    level: MockRiskLevel = MockRiskLevel.LOW
    score: float = 0.2
    requires_approval: bool = False
    approval_type: str = "none"
    factors: list = field(default_factory=list)
    reasoning: str = "Low risk query"
    policy_id: Optional[str] = "query_information_request"
    adjustments_applied: list = field(default_factory=list)

    def to_dict(self):
        return {"level": self.level.value, "score": self.score}


# --- Helper: Build a full pipeline with all mocks ---

def _build_mocked_pipeline(
    routing_decision: MockRoutingDecision = None,
    risk_assessment: MockRiskAssessment = None,
    llm_route: str = "direct_answer",
) -> OrchestrationPipelineService:
    """Build a pipeline with all external dependencies mocked."""

    if routing_decision is None:
        routing_decision = MockRoutingDecision()
    if risk_assessment is None:
        risk_assessment = MockRiskAssessment()

    # Step 1: Memory — mock assembled context
    mock_assembled = MagicMock()
    mock_assembled.to_prompt_text.return_value = "User is IT admin in Taipei"
    mock_assembled.pinned_count = 1
    mock_assembled.budget_used_pct = 30.0

    mock_mgr = AsyncMock()
    mock_budget = AsyncMock()
    mock_budget.assemble_context = AsyncMock(return_value=mock_assembled)

    # Step 2: Knowledge — mock search
    mock_knowledge_step = KnowledgeStep()

    # Step 3: Intent — mock router
    mock_router = AsyncMock()
    mock_router.route = AsyncMock(return_value=routing_decision)

    # Step 4: Risk — mock assessor
    mock_assessor = MagicMock()
    mock_assessor.assess = MagicMock(return_value=risk_assessment)

    # Step 6: LLM Route — mock call
    mock_llm_step = LLMRouteStep()

    # Step 8: PostProcess — mock storage
    mock_storage = AsyncMock()
    mock_storage.save = AsyncMock(return_value="cp-e2e-001")

    steps = [
        MemoryStep(memory_manager=mock_mgr, budget_manager=mock_budget),
        mock_knowledge_step,
        IntentStep(router=mock_router),
        RiskStep(risk_assessor=mock_assessor),
        HITLGateStep(),
        mock_llm_step,
        PostProcessStep(checkpoint_storage=mock_storage),
    ]

    return OrchestrationPipelineService(steps=steps)


# === E2E: Direct Answer Route ===

class TestDirectAnswerE2E:
    """Full pipeline → direct_answer route."""

    @pytest.mark.asyncio
    async def test_low_risk_query_completes_all_steps(self):
        """A simple low-risk query should complete all steps without pause."""
        pipeline = _build_mocked_pipeline(
            routing_decision=MockRoutingDecision(
                intent_category=MockIntentCategory.QUERY,
                completeness=MockCompletenessInfo(is_complete=True),
            ),
            risk_assessment=MockRiskAssessment(
                level=MockRiskLevel.LOW,
                requires_approval=False,
            ),
        )

        # Mock knowledge step internal methods
        steps = pipeline._steps
        knowledge_step = steps[1]
        with patch.object(knowledge_step, "_get_embedding", return_value=[0.1] * 1536), \
             patch.object(knowledge_step, "_search_qdrant", return_value=[
                 {"source": "wiki", "content": "VPN guide", "score": 0.9}
             ]):
            # Mock LLM route step
            llm_step = steps[5]
            with patch.object(llm_step, "_call_llm", return_value=(
                "direct_answer", "Simple factual query", "I'll answer directly"
            )):
                ctx = PipelineContext(
                    user_id="test-user",
                    session_id="e2e-session",
                    task="What is our VPN server address?",
                )

                queue: asyncio.Queue = asyncio.Queue()
                result = await pipeline.run(ctx, event_queue=queue)

        # Verify all steps completed
        assert len(result.completed_steps) == 7  # 7 steps in pipeline
        assert "memory_read" in result.completed_steps
        assert "knowledge_search" in result.completed_steps
        assert "intent_analysis" in result.completed_steps
        assert "risk_assessment" in result.completed_steps
        assert "hitl_gate" in result.completed_steps
        assert "llm_route_decision" in result.completed_steps
        assert "post_process" in result.completed_steps

        # Verify no pause
        assert result.is_paused is False
        assert result.selected_route == "direct_answer"
        assert result.checkpoint_id == "cp-e2e-001"

        # Verify SSE events emitted
        events = []
        while not queue.empty():
            events.append(await queue.get())

        event_types = [e.event_type for e in events]
        assert PipelineEventType.PIPELINE_START in event_types
        assert PipelineEventType.PIPELINE_COMPLETE in event_types
        assert event_types.count(PipelineEventType.STEP_COMPLETE) == 7


# === E2E: HITL Pause Flow ===

class TestHITLPauseE2E:
    """Pipeline pauses for HITL approval on high-risk changes."""

    @pytest.mark.asyncio
    async def test_high_risk_change_pauses_at_hitl(self):
        """HIGH risk CHANGE intent should pause at HITL gate."""
        mock_approval = AsyncMock()
        mock_approval.create = AsyncMock(return_value="apr-e2e-001")

        mock_cp_storage = AsyncMock()
        mock_cp_storage.save = AsyncMock(return_value="cp-hitl-e2e")

        pipeline = _build_mocked_pipeline(
            routing_decision=MockRoutingDecision(
                intent_category=MockIntentCategory.CHANGE,
                sub_intent="production_restart",
                completeness=MockCompletenessInfo(is_complete=True),
            ),
            risk_assessment=MockRiskAssessment(
                level=MockRiskLevel.HIGH,
                score=0.8,
                requires_approval=True,
                approval_type="single",
            ),
        )

        # Replace HITL step with one that has mock services
        steps = pipeline._steps
        steps[4] = HITLGateStep(
            approval_service=mock_approval,
            checkpoint_storage=mock_cp_storage,
        )

        # Mock knowledge and LLM steps
        with patch.object(steps[1], "_get_embedding", return_value=[0.1] * 1536), \
             patch.object(steps[1], "_search_qdrant", return_value=[]):

            ctx = PipelineContext(
                user_id="test-user",
                session_id="e2e-hitl",
                task="Restart production ETL pipeline",
            )

            queue: asyncio.Queue = asyncio.Queue()
            result = await pipeline.run(ctx, event_queue=queue)

        # Pipeline should be paused at HITL
        assert result.is_paused is True
        assert result.paused_at == "hitl"
        assert result.hitl_approval_id == "apr-e2e-001"
        assert result.checkpoint_id == "cp-hitl-e2e"

        # Steps after HITL should NOT have run
        assert "llm_route_decision" not in result.completed_steps
        assert "post_process" not in result.completed_steps

        # HITL_REQUIRED event emitted
        events = []
        while not queue.empty():
            events.append(await queue.get())

        hitl_events = [e for e in events if e.event_type == PipelineEventType.HITL_REQUIRED]
        assert len(hitl_events) == 1
        assert hitl_events[0].data["approval_id"] == "apr-e2e-001"


# === E2E: Dialog Pause Flow ===

class TestDialogPauseE2E:
    """Pipeline pauses for dialog when intent is incomplete."""

    @pytest.mark.asyncio
    async def test_incomplete_intent_pauses_at_dialog(self):
        """Incomplete intent should pause at Step 3 with questions."""
        pipeline = _build_mocked_pipeline(
            routing_decision=MockRoutingDecision(
                intent_category=MockIntentCategory.INCIDENT,
                sub_intent="etl_failure",
                completeness=MockCompletenessInfo(
                    is_complete=False,
                    completeness_score=0.4,
                    missing_fields=["severity", "affected_systems"],
                    suggestions=["What is the severity?", "Which systems are affected?"],
                ),
            ),
        )

        # Mock knowledge step
        with patch.object(pipeline._steps[1], "_get_embedding", return_value=[0.1] * 1536), \
             patch.object(pipeline._steps[1], "_search_qdrant", return_value=[]):

            ctx = PipelineContext(
                user_id="test-user",
                session_id="e2e-dialog",
                task="ETL pipeline broke",
            )

            queue: asyncio.Queue = asyncio.Queue()
            result = await pipeline.run(ctx, event_queue=queue)

        # Pipeline should be paused at dialog
        assert result.is_paused is True
        assert result.paused_at == "dialog"
        assert result.dialog_questions is not None
        assert len(result.dialog_questions) == 2
        assert "severity" in result.dialog_questions[0].lower() or "severity" in (result.dialog_id or "")

        # Steps after intent should NOT have run
        assert "risk_assessment" not in result.completed_steps
        assert "hitl_gate" not in result.completed_steps

        # DIALOG_REQUIRED event emitted
        events = []
        while not queue.empty():
            events.append(await queue.get())

        dialog_events = [e for e in events if e.event_type == PipelineEventType.DIALOG_REQUIRED]
        assert len(dialog_events) == 1
        assert len(dialog_events[0].data["questions"]) == 2


# === E2E: Resume from HITL ===

class TestResumeE2E:
    """Pipeline resume after HITL approval."""

    @pytest.mark.asyncio
    async def test_resume_skips_completed_steps(self):
        """Resuming from step 5 should skip steps 0-4."""
        pipeline = _build_mocked_pipeline()

        # Mock knowledge and LLM
        with patch.object(pipeline._steps[1], "_get_embedding", return_value=[0.1] * 1536), \
             patch.object(pipeline._steps[1], "_search_qdrant", return_value=[]), \
             patch.object(pipeline._steps[5], "_call_llm", return_value=(
                 "team", "Complex investigation", "Using team mode"
             )):

            ctx = PipelineContext(
                user_id="test-user",
                session_id="e2e-resume",
                task="Investigate outage",
            )
            # Simulate prior steps already completed
            ctx.memory_text = "User context from checkpoint"
            ctx.knowledge_text = "Knowledge from checkpoint"

            result = await pipeline.run(ctx, start_from_step=5)

        # Only steps 5+ should have run
        assert "memory_read" not in result.completed_steps
        assert "knowledge_search" not in result.completed_steps
        assert "llm_route_decision" in result.completed_steps
        assert "post_process" in result.completed_steps
        assert result.selected_route == "team"


# === E2E: Dispatch Service Integration ===

class TestDispatchE2E:
    """Test DispatchService with mock executors."""

    @pytest.mark.asyncio
    async def test_dispatch_direct_answer_with_events(self):
        """Direct answer dispatch emits events and returns result."""
        mock_executor = AsyncMock()
        mock_executor.name = "direct_answer"
        mock_executor.execute = AsyncMock(return_value=DispatchResult(
            route=ExecutionRoute.DIRECT_ANSWER,
            response_text="VPN server is at vpn.company.com",
            status="completed",
            duration_ms=200,
        ))

        svc = DispatchService()
        svc.register_executor(ExecutionRoute.DIRECT_ANSWER, mock_executor)

        queue: asyncio.Queue = asyncio.Queue()
        req = DispatchRequest(
            route=ExecutionRoute.DIRECT_ANSWER,
            task="VPN address?",
            user_id="u1",
            session_id="s1",
        )

        result = await svc.dispatch(req, event_queue=queue)

        assert result.status == "completed"
        assert "vpn.company.com" in result.response_text

        events = []
        while not queue.empty():
            events.append(await queue.get())

        assert any(e.event_type == PipelineEventType.DISPATCH_START for e in events)

    @pytest.mark.asyncio
    async def test_dispatch_team_with_agent_results(self):
        """Team dispatch returns multiple agent results."""
        mock_executor = AsyncMock()
        mock_executor.name = "team"
        mock_executor.execute = AsyncMock(return_value=DispatchResult(
            route=ExecutionRoute.TEAM,
            response_text="Team investigation complete",
            agent_results=[
                AgentResult(agent_name="Investigator", output="Found root cause"),
                AgentResult(agent_name="Specialist", output="Confirmed diagnosis"),
                AgentResult(agent_name="Advisor", output="Recommend restart"),
            ],
            synthesis="Root cause identified, restart recommended",
            status="completed",
            duration_ms=3000,
        ))

        svc = DispatchService()
        svc.register_executor(ExecutionRoute.TEAM, mock_executor)

        req = DispatchRequest(
            route=ExecutionRoute.TEAM,
            task="Investigate ETL failure",
            user_id="u1",
            session_id="s1",
        )

        result = await svc.dispatch(req)

        assert result.status == "completed"
        assert len(result.agent_results) == 3
        assert result.synthesis == "Root cause identified, restart recommended"
