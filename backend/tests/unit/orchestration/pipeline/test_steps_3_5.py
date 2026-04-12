"""Tests for IntentStep (Step 3), RiskStep (Step 4), HITLGateStep (Step 5)."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.orchestration.pipeline.context import PipelineContext
from src.integrations.orchestration.pipeline.exceptions import (
    DialogPauseException,
    HITLPauseException,
)
from src.integrations.orchestration.pipeline.steps.step3_intent import IntentStep
from src.integrations.orchestration.pipeline.steps.step4_risk import RiskStep
from src.integrations.orchestration.pipeline.steps.step5_hitl import HITLGateStep


# --- Mock V8 data classes for testing ---

class MockIntentCategory(Enum):
    INCIDENT = "incident"
    CHANGE = "change"
    QUERY = "query"
    UNKNOWN = "unknown"


class MockRiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


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
    sub_intent: Optional[str] = None
    confidence: float = 0.95
    routing_layer: str = "pattern"
    completeness: MockCompletenessInfo = field(default_factory=MockCompletenessInfo)

    def to_dict(self):
        return {
            "intent_category": self.intent_category.value,
            "confidence": self.confidence,
        }


@dataclass
class MockRiskAssessment:
    level: MockRiskLevel = MockRiskLevel.LOW
    score: float = 0.2
    requires_approval: bool = False
    approval_type: str = "none"
    factors: list = field(default_factory=list)
    reasoning: str = ""
    policy_id: Optional[str] = None
    adjustments_applied: list = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        return {"level": self.level.value, "score": self.score}


# === IntentStep Tests ===

class TestIntentStep:
    """Tests for Step 3: Intent Analysis."""

    def _make_context(self) -> PipelineContext:
        return PipelineContext(
            user_id="test-user",
            session_id="test-session",
            task="Check VPN connectivity for Taipei office",
            memory_text="User is IT admin",
            knowledge_text="VPN runbook available",
        )

    @pytest.mark.asyncio
    async def test_complete_intent_passes_through(self):
        """Complete intent populates context and continues."""
        decision = MockRoutingDecision(
            intent_category=MockIntentCategory.QUERY,
            sub_intent="status_check",
            confidence=0.95,
            completeness=MockCompletenessInfo(is_complete=True),
        )

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value=decision)

        step = IntentStep(router=mock_router)
        ctx = self._make_context()

        result = await step._execute(ctx)

        assert result.routing_decision is decision
        assert result.completeness_info.is_complete is True
        mock_router.route.assert_called_once_with("Check VPN connectivity for Taipei office")

    @pytest.mark.asyncio
    async def test_incomplete_intent_raises_dialog_pause(self):
        """Incomplete intent triggers DialogPauseException when score < 50%."""
        decision = MockRoutingDecision(
            intent_category=MockIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.85,
            completeness=MockCompletenessInfo(
                is_complete=False,
                completeness_score=0.3,
                missing_fields=["severity", "affected_systems"],
                suggestions=["What is the severity?", "Which systems are affected?"],
            ),
        )

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value=decision)

        step = IntentStep(router=mock_router)
        ctx = self._make_context()

        with pytest.raises(DialogPauseException) as exc_info:
            await step._execute(ctx)

        assert exc_info.value.missing_fields == ["severity", "affected_systems"]
        assert len(exc_info.value.questions) == 2
        assert exc_info.value.completeness_score == 0.3

    @pytest.mark.asyncio
    async def test_incomplete_with_checkpoint(self):
        """Incomplete intent saves checkpoint before pausing."""
        decision = MockRoutingDecision(
            completeness=MockCompletenessInfo(
                is_complete=False,
                completeness_score=0.3,
                missing_fields=["severity"],
                suggestions=["What severity?"],
            ),
        )

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value=decision)

        mock_storage = AsyncMock()
        mock_storage.save = AsyncMock(return_value="cp-dialog-001")

        step = IntentStep(router=mock_router, checkpoint_storage=mock_storage)
        ctx = self._make_context()

        with pytest.raises(DialogPauseException) as exc_info:
            await step._execute(ctx)

        assert exc_info.value.checkpoint_id == "cp-dialog-001"
        mock_storage.save.assert_called_once()

    def test_step_properties(self):
        step = IntentStep()
        assert step.name == "intent_analysis"
        assert step.step_index == 2


# === RiskStep Tests ===

class TestRiskStep:
    """Tests for Step 4: Risk Assessment."""

    def _make_context(self, **overrides) -> PipelineContext:
        defaults = {
            "user_id": "test-user",
            "session_id": "test-session",
            "task": "Restart production ETL pipeline",
            "memory_text": "User manages production databases",
            "knowledge_text": "ETL pipeline runs on production cluster",
        }
        defaults.update(overrides)
        ctx = PipelineContext(**defaults)
        ctx.routing_decision = MockRoutingDecision(
            intent_category=MockIntentCategory.CHANGE,
            sub_intent="production_restart",
        )
        return ctx

    @pytest.mark.asyncio
    async def test_risk_assessment_populated(self):
        """RiskStep populates context.risk_assessment."""
        mock_assessor = MagicMock()
        mock_assessor.assess = MagicMock(return_value=MockRiskAssessment(
            level=MockRiskLevel.HIGH,
            score=0.75,
            requires_approval=True,
            approval_type="single",
            policy_id="change_infrastructure_change",
        ))

        step = RiskStep(risk_assessor=mock_assessor)
        ctx = self._make_context()

        result = await step._execute(ctx)

        assert result.risk_assessment is not None
        assert result.risk_assessment.level == MockRiskLevel.HIGH
        assert result.risk_assessment.requires_approval is True
        mock_assessor.assess.assert_called_once()

    @pytest.mark.asyncio
    async def test_assessment_context_detects_production(self):
        """AssessmentContext builder detects production keywords."""
        step = RiskStep()

        ctx = self._make_context(
            memory_text="This is a production system",
            knowledge_text="Running on prod cluster",
        )

        ac = step._build_assessment_context(ctx)
        assert ac.is_production is True

    @pytest.mark.asyncio
    async def test_assessment_context_detects_urgency(self):
        """AssessmentContext builder detects urgency keywords."""
        step = RiskStep()

        ctx = self._make_context(task="URGENT: fix database issue immediately")
        ac = step._build_assessment_context(ctx)
        assert ac.is_urgent is True

    @pytest.mark.asyncio
    async def test_skips_when_no_routing_decision(self):
        """RiskStep skips gracefully when routing_decision is None."""
        step = RiskStep()
        ctx = PipelineContext(
            user_id="u", session_id="s", task="test"
        )

        result = await step._execute(ctx)
        assert result.risk_assessment is None

    def test_extract_systems(self):
        systems = RiskStep._extract_systems("check etl pipeline and redis cluster")
        assert "etl" in systems
        assert "redis" in systems
        assert "pipeline" in systems

    def test_step_properties(self):
        step = RiskStep()
        assert step.name == "risk_assessment"
        assert step.step_index == 3


# === HITLGateStep Tests ===

class TestHITLGateStep:
    """Tests for Step 5: HITL Gate."""

    def _make_context_with_risk(
        self, requires_approval: bool = False, risk_level=MockRiskLevel.LOW
    ) -> PipelineContext:
        ctx = PipelineContext(
            user_id="test-user",
            session_id="test-session",
            task="Deploy new version to production",
            memory_text="Previous deploy caused outage",
            knowledge_text="Deploy runbook",
        )
        ctx.routing_decision = MockRoutingDecision(
            intent_category=MockIntentCategory.CHANGE,
        )
        ctx.risk_assessment = MockRiskAssessment(
            level=risk_level,
            score=0.8 if requires_approval else 0.2,
            requires_approval=requires_approval,
            approval_type="single" if requires_approval else "none",
            policy_id="change_release_deployment",
            reasoning="Production deployment requires approval",
        )
        return ctx

    @pytest.mark.asyncio
    async def test_low_risk_passes_through(self):
        """Low risk without approval requirement passes through."""
        step = HITLGateStep()
        ctx = self._make_context_with_risk(requires_approval=False)

        result = await step._execute(ctx)

        assert result.paused_at is None
        assert result.hitl_approval_id is None

    @pytest.mark.asyncio
    async def test_high_risk_raises_hitl_pause(self):
        """High risk with approval triggers HITLPauseException."""
        mock_approval_svc = AsyncMock()
        mock_approval_svc.create = AsyncMock(return_value="apr-001")

        mock_storage = AsyncMock()
        mock_storage.save = AsyncMock(return_value="cp-hitl-001")

        step = HITLGateStep(
            approval_service=mock_approval_svc,
            checkpoint_storage=mock_storage,
        )
        ctx = self._make_context_with_risk(
            requires_approval=True,
            risk_level=MockRiskLevel.HIGH,
        )

        with pytest.raises(HITLPauseException) as exc_info:
            await step._execute(ctx)

        assert exc_info.value.approval_id == "apr-001"
        assert exc_info.value.checkpoint_id == "cp-hitl-001"
        assert exc_info.value.risk_level == "high"
        assert exc_info.value.approval_type == "single"

        mock_storage.save.assert_called_once()
        mock_approval_svc.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_no_risk_assessment(self):
        """HITL gate passes through when risk_assessment is None."""
        step = HITLGateStep()
        ctx = PipelineContext(
            user_id="u", session_id="s", task="test"
        )

        result = await step._execute(ctx)
        assert result.paused_at is None

    @pytest.mark.asyncio
    async def test_checkpoint_saved_before_approval(self):
        """Checkpoint is saved before approval request is created."""
        call_order = []

        mock_storage = AsyncMock()
        async def save_side_effect(checkpoint):
            call_order.append("checkpoint_saved")
            return "cp-001"
        mock_storage.save = save_side_effect

        mock_approval = AsyncMock()
        async def create_side_effect(request):
            call_order.append("approval_created")
            return "apr-001"
        mock_approval.create = create_side_effect

        step = HITLGateStep(
            approval_service=mock_approval,
            checkpoint_storage=mock_storage,
        )
        ctx = self._make_context_with_risk(
            requires_approval=True,
            risk_level=MockRiskLevel.CRITICAL,
        )

        with pytest.raises(HITLPauseException):
            await step._execute(ctx)

        assert call_order == ["checkpoint_saved", "approval_created"]

    def test_step_properties(self):
        step = HITLGateStep()
        assert step.name == "hitl_gate"
        assert step.step_index == 4
