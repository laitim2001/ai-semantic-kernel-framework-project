"""Tests for OrchestrationPipelineService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.orchestration.pipeline.context import PipelineContext
from src.integrations.orchestration.pipeline.exceptions import (
    DialogPauseException,
    HITLPauseException,
    PipelineError,
)
from src.integrations.orchestration.pipeline.service import (
    OrchestrationPipelineService,
    PipelineEvent,
    PipelineEventType,
)
from src.integrations.orchestration.pipeline.steps.base import PipelineStep


class MockStep(PipelineStep):
    """Configurable mock step for testing."""

    def __init__(self, name: str, index: int, side_effect=None):
        self._name = name
        self._index = index
        self._side_effect = side_effect
        self.called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def step_index(self) -> int:
        return self._index

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        self.called = True
        if self._side_effect:
            raise self._side_effect
        return context


class TestOrchestrationPipelineService:
    """Tests for the pipeline coordinator."""

    def _make_context(self) -> PipelineContext:
        return PipelineContext(
            user_id="test-user",
            session_id="test-session",
            task="Test task",
        )

    @pytest.mark.asyncio
    async def test_run_all_steps_in_order(self):
        """Pipeline executes all steps sequentially."""
        step1 = MockStep("step_a", 0)
        step2 = MockStep("step_b", 1)
        step3 = MockStep("step_c", 2)

        service = OrchestrationPipelineService(steps=[step1, step2, step3])
        ctx = self._make_context()

        result = await service.run(ctx)

        assert step1.called
        assert step2.called
        assert step3.called
        assert result.completed_steps == ["step_a", "step_b", "step_c"]
        assert result.paused_at is None

    @pytest.mark.asyncio
    async def test_no_steps_raises_error(self):
        """Pipeline raises error if no steps configured."""
        service = OrchestrationPipelineService(steps=[])
        ctx = self._make_context()

        with pytest.raises(PipelineError, match="No pipeline steps configured"):
            await service.run(ctx)

    @pytest.mark.asyncio
    async def test_hitl_pause_stops_pipeline(self):
        """Pipeline pauses when HITLPauseException is raised."""
        step1 = MockStep("step_a", 0)
        step2 = MockStep(
            "step_b",
            1,
            side_effect=HITLPauseException(
                approval_id="apr-123",
                checkpoint_id="cp-456",
                risk_level="high",
                approval_type="single",
            ),
        )
        step3 = MockStep("step_c", 2)

        service = OrchestrationPipelineService(steps=[step1, step2, step3])
        ctx = self._make_context()

        result = await service.run(ctx)

        assert step1.called
        assert step2.called
        assert not step3.called  # should NOT have been reached
        assert result.paused_at == "hitl"
        assert result.hitl_approval_id == "apr-123"
        assert result.checkpoint_id == "cp-456"

    @pytest.mark.asyncio
    async def test_dialog_pause_stops_pipeline(self):
        """Pipeline pauses when DialogPauseException is raised."""
        step1 = MockStep("step_a", 0)
        step2 = MockStep(
            "step_b",
            1,
            side_effect=DialogPauseException(
                dialog_id="dlg-789",
                questions=["What is the severity?", "Which systems are affected?"],
                missing_fields=["severity", "affected_systems"],
                checkpoint_id="cp-101",
                completeness_score=0.4,
            ),
        )
        step3 = MockStep("step_c", 2)

        service = OrchestrationPipelineService(steps=[step1, step2, step3])
        ctx = self._make_context()

        result = await service.run(ctx)

        assert step1.called
        assert step2.called
        assert not step3.called
        assert result.paused_at == "dialog"
        assert result.dialog_id == "dlg-789"
        assert len(result.dialog_questions) == 2
        assert result.checkpoint_id == "cp-101"

    @pytest.mark.asyncio
    async def test_resume_skips_completed_steps(self):
        """Pipeline can resume from a specific step index."""
        step1 = MockStep("step_a", 0)
        step2 = MockStep("step_b", 1)
        step3 = MockStep("step_c", 2)

        service = OrchestrationPipelineService(steps=[step1, step2, step3])
        ctx = self._make_context()

        result = await service.run(ctx, start_from_step=2)

        assert not step1.called  # skipped
        assert not step2.called  # skipped
        assert step3.called      # executed
        assert result.completed_steps == ["step_c"]

    @pytest.mark.asyncio
    async def test_unexpected_error_wrapped_as_pipeline_error(self):
        """Unexpected exceptions become PipelineError."""
        step1 = MockStep("step_a", 0, side_effect=ValueError("boom"))

        service = OrchestrationPipelineService(steps=[step1])
        ctx = self._make_context()

        with pytest.raises(PipelineError, match="Unexpected error in step step_a"):
            await service.run(ctx)

    @pytest.mark.asyncio
    async def test_events_emitted_to_queue(self):
        """Pipeline emits SSE events to the provided queue."""
        step1 = MockStep("step_a", 0)

        service = OrchestrationPipelineService(steps=[step1])
        ctx = self._make_context()

        queue: asyncio.Queue = asyncio.Queue()
        await service.run(ctx, event_queue=queue)

        events = []
        while not queue.empty():
            events.append(await queue.get())

        event_types = [e.event_type for e in events]
        assert PipelineEventType.PIPELINE_START in event_types
        assert PipelineEventType.STEP_START in event_types
        assert PipelineEventType.STEP_COMPLETE in event_types
        assert PipelineEventType.PIPELINE_COMPLETE in event_types

    @pytest.mark.asyncio
    async def test_hitl_event_emitted(self):
        """HITL_REQUIRED event is emitted when pipeline pauses for approval."""
        step1 = MockStep(
            "hitl_gate",
            0,
            side_effect=HITLPauseException(
                approval_id="apr-1",
                checkpoint_id="cp-1",
                risk_level="critical",
            ),
        )

        service = OrchestrationPipelineService(steps=[step1])
        ctx = self._make_context()

        queue: asyncio.Queue = asyncio.Queue()
        await service.run(ctx, event_queue=queue)

        events = []
        while not queue.empty():
            events.append(await queue.get())

        hitl_events = [
            e for e in events if e.event_type == PipelineEventType.HITL_REQUIRED
        ]
        assert len(hitl_events) == 1
        assert hitl_events[0].data["approval_id"] == "apr-1"
        assert hitl_events[0].data["risk_level"] == "critical"

    @pytest.mark.asyncio
    async def test_transcript_recording(self):
        """Pipeline records transcript entries when transcript_service provided."""
        mock_transcript = AsyncMock()
        mock_transcript.append = AsyncMock()

        step1 = MockStep("step_a", 0)

        service = OrchestrationPipelineService(
            steps=[step1],
            transcript_service=mock_transcript,
        )
        ctx = self._make_context()

        await service.run(ctx)

        assert mock_transcript.append.called

    @pytest.mark.asyncio
    async def test_no_events_when_queue_is_none(self):
        """Pipeline runs normally without an event queue."""
        step1 = MockStep("step_a", 0)

        service = OrchestrationPipelineService(steps=[step1])
        ctx = self._make_context()

        result = await service.run(ctx, event_queue=None)

        assert result.completed_steps == ["step_a"]


class TestPipelineEvent:
    """Tests for PipelineEvent."""

    def test_to_sse(self):
        event = PipelineEvent(
            PipelineEventType.STEP_COMPLETE,
            {"step_name": "memory_read", "latency_ms": 42},
            step_name="memory_read",
        )
        sse = event.to_sse()
        assert sse["event"] == "STEP_COMPLETE"
        assert sse["data"]["step_name"] == "memory_read"
